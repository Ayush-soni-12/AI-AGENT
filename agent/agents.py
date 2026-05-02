from __future__ import annotations
from typing import Any , AsyncGenerator
from client.llm_client import LLMClient
from client.response import StreamEventType
from agent.event import AgentEvent,AgentEventType
from agent.process_manager import ProcessManager
from context.manager import ContextManager
from tools.registry import create_tool_registry
from tools.base import ToolResult

from typing import Any, AsyncGenerator, Callable, Awaitable

class Agent:

    def __init__(self, confirm_callback: Callable[[Any], Awaitable[bool]] | None = None):
        self.client = LLMClient()
        self.context_manager = ContextManager()
        self.process_manager = ProcessManager()
        self._confirm_callback = confirm_callback

        # MCPManager is created empty here; connect_mcp() must be awaited
        # inside the running event loop (e.g. Textual's on_mount) so that
        # anyio cancel scopes are always entered and exited in the same loop.
        from tools.mcp_client import MCPManager
        self.mcp_manager = MCPManager()

        # Build registry without MCP tools for now; they are added after connect
        self.tool_registry = create_tool_registry(mcp_manager=None)

    async def start_mcp(self) -> int:
        """Connect to all configured MCP servers and register their tools.

        Must be called from within the running event loop (e.g. Textual on_mount).
        Returns the number of servers successfully connected.
        """
        connected = await self.mcp_manager.connect_all()
        if connected > 0:
            # Dynamically register newly discovered MCP tools
            from tools.mcp_tool import MCPTool
            for tool_meta in self.mcp_manager.get_all_tools():
                self.tool_registry.register(MCPTool(tool_meta, self.mcp_manager))
        return connected

    async def stop_mcp(self):
        """Disconnect all MCP servers cleanly.

        Must be called from within the same event loop that called start_mcp().
        """
        await self.mcp_manager.disconnect_all()




    def _parse_message(self, text: str) -> Any:
        import pathlib
        import mimetypes
        import shlex

        try:
            words = shlex.split(text)
        except ValueError:
            words = text.split()

        images = []
        for word in words:
            clean_word = word.strip(" ,.;:!?\"'")
            try:
                p = pathlib.Path(clean_word).resolve()
                if p.exists() and p.is_file():
                    mime, _ = mimetypes.guess_type(str(p))
                    if mime and mime.startswith("image/") and not mime.endswith("svg+xml"):
                        images.append(str(p))
            except Exception:
                pass
                
        if not images:
            return text
            
        content = [{"type": "text", "text": text}]
        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"file://{img}"}
            })
        return content

    async def run(self , message:str) -> AsyncGenerator[AgentEvent,None]:
        parsed_message = self._parse_message(message)
        yield AgentEvent.agent_start(str(parsed_message))

        self.context_manager.add_user_message(parsed_message)
        
        final_response = None
        async for event in self._agentic_loop(parsed_message):
            yield event

            
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")

        yield AgentEvent.agent_end(final_response)
       

    async def _agentic_loop(self, message: Any) -> AsyncGenerator[AgentEvent,None]:
        import json
        tool_schema = self.tool_registry.get_schema()

        while True:
            response_text = ""
            tool_calls = []

            async for event in self.client.chat_completion(self.context_manager.get_messages(),tools=tool_schema if tool_schema else None,stream=True):
                if event.type == StreamEventType.TEXT_DELTA:
                    if event.text_delta:
                        content = event.text_delta.content
                        response_text += content
                        yield AgentEvent.text_delta(content)
                elif event.type == StreamEventType.TOOL_CALL:
                    tool_calls = event.tool_calls
                elif event.type == StreamEventType.MESSAGE_COMPLETION:
                    # Capture real API token usage from each LLM turn
                    if event.usage:
                        self.context_manager.record_api_usage(
                            prompt_tokens=event.usage.prompt_token or 0,
                            completion_tokens=event.usage.completion_token or 0,
                            cached_tokens=event.usage.cached_token or 0,
                        )
                elif event.type == StreamEventType.ERROR:
                    yield AgentEvent.agent_error(event.error)
                    return # Exit loop completely on error

            import copy
            saved_tool_calls = copy.deepcopy(tool_calls) if tool_calls else None
            if saved_tool_calls:
                for tc in saved_tool_calls:
                    args = tc.get("function", {}).get("arguments", "")
                    if args:
                        try:
                            json.loads(args)
                        except json.JSONDecodeError:
                            # Gemini's backend API crashes if invalid JSON is passed back in assistant history
                            tc["function"]["arguments"] = '{"error": "invalid_json_redacted"}'

            self.context_manager.add_assistant_message(response_text or None, tool_calls=saved_tool_calls)
            
            if response_text:
                yield AgentEvent.text_complete(response_text)

            if not tool_calls:
                break # Agent is done, no tools requested

            # Execute tool calls and feed results back into the loop
            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                args = tc["function"]["arguments"]
                
                try:
                    params = json.loads(args) if args else {}
                    yield AgentEvent.tool_call(tool_name, params)
                    
                    tool_instance = self.tool_registry.get(tool_name)
                    if tool_instance:
                        from tools.base import ToolInvocation
                        import pathlib
                        invocation = ToolInvocation(params=params, cwd=pathlib.Path.cwd(), agent=self)
                        confirmation = await tool_instance.get_confirmation(invocation)
                        
                        if confirmation:
                            yield AgentEvent.tool_confirmation(confirmation)
                            
                            if self._confirm_callback:
                                approved = await self._confirm_callback(confirmation)
                            else:
                                approved = True
                                
                            if not approved:
                                result = ToolResult.error_result("User explicitly denied permission to execute this tool. Please cancel the action, apologize, and ask for further instructions.")
                                yield AgentEvent.tool_result(tool_name, result.to_model_output())
                                self.context_manager.add_tool_message(tc["id"], tool_name, result.to_model_output())
                                continue

                    # Run the actual python code
                    result = await self.tool_registry.invoke(tool_name, params, None, agent=self)
                except json.JSONDecodeError as e:
                    yield AgentEvent.tool_call(tool_name, {"_raw_args": args})
                    result = ToolResult.error_result(f"Failed to parse tool arguments as JSON: {e}")
                
                diff_str = result.diff.to_diff() if result.diff else None
                out_str = result.to_model_output()
                parsed_out = self._parse_message(out_str)
                yield AgentEvent.tool_result(tool_name, out_str, diff=diff_str)
                
                if isinstance(parsed_out, list):
                    # Tool returned an image! Tool messages must be text only.
                    self.context_manager.add_tool_message(tc["id"], tool_name, out_str)
                    
                    # Inject a user message containing the actual image payload
                    image_parts = [p for p in parsed_out if p.get("type") == "image_url"]
                    if image_parts:
                        user_content = [{"type": "text", "text": f"System Image Injection for tool {tool_name}:"}] + image_parts
                        self.context_manager.add_user_message(user_content)
                else:
                    self.context_manager.add_tool_message(tc["id"], tool_name, out_str)

            # Loop automatically continues since while True!

    async def __aenter__(self) -> Agent:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.client:
            await self.client.close()
            self.client = None