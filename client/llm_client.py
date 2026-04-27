from openai import AsyncOpenAI,RateLimitError,APIConnectionError,APIError
from typing import Any ,AsyncGenerator
from dotenv import load_dotenv
from client.response import TextDelta,TokenUsage,StreamEvent,StreamEventType
import os
import asyncio

load_dotenv()   


class LLMClient:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self._max_retries : int   =3 

    def get_client(self) -> AsyncOpenAI:
        if self._client is None:
            from config.config import config_mgr
            self._client = AsyncOpenAI(
                base_url=config_mgr.get("base_url", "https://generativelanguage.googleapis.com/v1beta/openai/"),
                api_key=config_mgr.get("api_key", os.getenv("API_KEY")),
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None


    
    def _build_tools(self, tools: list[dict[str, Any]]):
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get(
                        "parameters",
                        {
                            "type": "object",
                            "properties": {},
                        },
                    ),
                },
            }
            for tool in tools
        ]


    async def chat_completion(self,messages:list[dict[str,Any]],tools:list[dict[str,Any]] | None = None,stream:bool = True)->AsyncGenerator[StreamEvent,None]:
        client = self.get_client()
        from config.config import config_mgr
        
        kwargs = {
            "model": config_mgr.get("model", "gemini-2.5-flash"),
            "messages":messages,
            "stream":stream,
            }
        if tools:
            kwargs["tools"] = self._build_tools(tools)
            kwargs["tool_choice"] = "auto"
    
        for attempt in range(self._max_retries+1):
            try:
                if stream:
                   async for event in self._stream_response(client ,kwargs):
                       yield event
                else:
                   async for event in self._non_stream_response(client,kwargs):
                       yield event
                return  
            except RateLimitError as e:
                if attempt < self._max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"Rate limit exceeded after {self._max_retries} retries: {e.status_code} - {e.message}",
                    )
                    return
            except APIConnectionError as e:
                if attempt < self._max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"API Connection Error after {self._max_retries} retries: {str(e)}",
                    )
                    return
            except APIError as e:
                if attempt < self._max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"API Error after {self._max_retries} retries: {e.status_code} - {e.message}",
                    )
                    return
            except Exception as e:
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    error=f"Unexpected error: {type(e).__name__}: {str(e)}",
                )
                return
            
  
    
    async def _stream_response(self,client:AsyncOpenAI,kwargs:dict[str,Any])->AsyncGenerator[StreamEvent,None]:
        response = await client.chat.completions.create(**kwargs)

        finish_reason : str | None = None
        usage :TokenUsage | None = None
        tool_calls : list[dict] = []

        async for chunk in response:
            if hasattr(chunk,"usage") and chunk.usage:
                # Some API providers might not provide prompt_tokens_details
                cached = 0
                if hasattr(chunk.usage, "prompt_tokens_details") and chunk.usage.prompt_tokens_details:
                     cached = chunk.usage.prompt_tokens_details.cached_tokens
                     
                usage = TokenUsage(
                    prompt_token = chunk.usage.prompt_tokens,
                    completion_token = chunk.usage.completion_tokens,
                    total_token = chunk.usage.total_tokens,
                    cached_token=cached,
                )
                
            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            if getattr(choice, "finish_reason", None):
                finish_reason=choice.finish_reason
            
            # Catch tool_calls chunks and stitch the JSON strings together
            if getattr(delta, "tool_calls", None):
                for tc in delta.tool_calls:
                    idx = tc.index if tc.index is not None else 0
                    while len(tool_calls) <= idx:
                        tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                    if getattr(tc, "id", None):
                        tool_calls[idx]["id"] = tc.id
                    if getattr(tc, "function", None):
                        if getattr(tc.function, "name", None):
                            tool_calls[idx]["function"]["name"] = tc.function.name
                        if getattr(tc.function, "arguments", None):
                            tool_calls[idx]["function"]["arguments"] += tc.function.arguments

            if getattr(delta, "content", None):
                yield StreamEvent(
                    type=StreamEventType.TEXT_DELTA,
                    text_delta=TextDelta(content=delta.content),
                )
        
        # If the AI asked for any tools, yield them now before completion
        if tool_calls:
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL,
                tool_calls=tool_calls
            )

        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETION,
            finish_reason=finish_reason,
            usage=usage,
        )
        
    async def _non_stream_response(self,client:AsyncOpenAI,kwargs:dict[str,Any])->AsyncGenerator[StreamEvent,None]:
        response  = await client.chat.completions.create(**kwargs)
        choice  = response.choices[0]
        message = choice.message
        
        usage = None
        if hasattr(response,"usage") and response.usage:
            cached = 0
            if hasattr(response.usage, "prompt_tokens_details") and response.usage.prompt_tokens_details:
                 cached = response.usage.prompt_tokens_details.cached_tokens
            usage = TokenUsage(
                prompt_token = response.usage.prompt_tokens,
                completion_token = response.usage.completion_tokens,
                total_token = response.usage.total_tokens,
                cached_token=cached,
            )

        if getattr(message, "tool_calls", None):
            tool_calls = []
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": getattr(tc, "id", ""),
                    "type": getattr(tc, "type", "function"),
                    "function": {
                        "name": tc.function.name if getattr(tc, "function", None) else "",
                        "arguments": tc.function.arguments if getattr(tc, "function", None) else ""
                    }
                })
            
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL,
                tool_calls=tool_calls
            )

        if message.content:
            yield StreamEvent(
                type=StreamEventType.TEXT_DELTA,
                text_delta=TextDelta(content=message.content)
            )

        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETION,
            finish_reason=choice.finish_reason,
            usage=usage,
        )
            