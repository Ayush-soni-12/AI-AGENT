import asyncio
import sys
import click
from agent.agents import Agent
from ui.textual_app import ChatApp

class CLI:
    def __init__(self):
        self.agent = None

    async def run_single(self, message: str) -> str | None:
        # Fallback for single-shot execution still uses basic terminal so it doesn't open TUI
        from ui.tui import TUI, get_console
        from agent.event import AgentEventType
        
        console = get_console()
        tui = TUI(console)
        
        async with Agent(confirm_callback=tui.confirm_tool) as agent:
            assistant_streaming = False
            final_response = None
            async for event in agent.run(message):
                if event.type == AgentEventType.TEXT_DELTA:
                    content = event.data.get("content","")
                    if not assistant_streaming:
                        tui.begin_assistant()
                        assistant_streaming = True
                    tui.stream_assistant_detail(content)
                elif event.type == AgentEventType.TEXT_COMPLETE:
                    final_response = event.data.get("content")
                    if assistant_streaming:
                        tui.end_assistand()
                        assistant_streaming = False
                elif event.type == AgentEventType.TOOL_CALL:
                    if assistant_streaming:
                        tui.end_assistand()
                        assistant_streaming = False
                    name = event.data.get("name")
                    args = event.data.get("arguments")
                    tui.show_tool_call(name, str(args))
                elif event.type == AgentEventType.TOOL_RESULT:
                    name = event.data.get("name")
                    tui.show_tool_result(name)
                elif event.type == AgentEventType.AGENT_ERROR:
                    error = event.data.get("error","Unknown error")
                    console.print(f"\n[error]Error:{error}[/error]")
            
            console.print()
            return final_response

    async def run_interactive(self) -> None:
        from config.config import config_mgr

        if not config_mgr.has_api_key():
            from prompt_toolkit.shortcuts import radiolist_dialog, input_dialog
            import sys
            
            provider = radiolist_dialog(
                title="Neural Claude Setup",
                text="Please select your inference engine provider using Arrow Keys:",
                values=[
                    ("gemini", "Google Gemini (Recommended)"),
                    ("openrouter", "OpenRouter (Claude, GPT, etc.)")
                ]
            ).run()
            
            if not provider:
                print("Setup cancelled.")
                sys.exit(1)

            if provider == "gemini":
                model_values = [
                    ("gemini-2.5-flash", "Gemini 2.5 Flash (Fastest)"),
                    ("gemini-2.5-pro", "Gemini 2.5 Pro (Powerful)"),
                    ("gemini-2.0-flash", "Gemini 2.0 Flash")
                ]
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
            else:
                model_values = [
                    ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet"),
                    ("anthropic/claude-3.7-sonnet", "Claude 3.7 Sonnet (Latest)"),
                    ("openai/gpt-4o", "OpenAI GPT-4o"),
                    ("google/gemini-2.5-flash", "Gemini 2.5 Flash")
                ]
                base_url = "https://openrouter.ai/api/v1"

            model_name = radiolist_dialog(
                title="Select Default Model",
                text="Choose your preferred reasoning model:",
                values=model_values
            ).run()

            if not model_name:
                print("Setup cancelled.")
                sys.exit(1)

            api_key = input_dialog(
                title="API Key Configuration",
                text=f"Paste your {provider.title()} API Key below:\n(It will be safely encrypted in ~/.config/neuralclaude/settings.json)",
                password=True
            ).run()

            if not api_key:
                print("Setup cancelled.")
                sys.exit(1)

            config_mgr.set("provider", provider)
            config_mgr.set("base_url", base_url)
            config_mgr.set("model", model_name)
            config_mgr.set("api_key", api_key.strip())

        import pathlib
        resume_session = False
        
        # Simple Terminal fallback to handle Pre-Boot session logic
        if (pathlib.Path.cwd() / ".agent_session.json").exists():
            print("Detected a previous session. Do you want to resume? [Y/n]: ", end="", flush=True)
            ans = sys.stdin.readline().strip().lower()
            if ans in ["", "y", "yes"]:
                resume_session = True
            else:
                (pathlib.Path.cwd() / ".agent_session.json").unlink(missing_ok=True)

        async with Agent(confirm_callback=None) as agent:
            if resume_session:
                agent.context_manager.load_session()
                
            self.agent = agent
            app = ChatApp(agent)
            
            # Since we are already inside an event loop via asyncio.run(),
            # we must use app.run_async() so Textual bonds with our current loop!
            await app.run_async()

@click.command()
@click.argument("prompt", required=False)
def main(prompt: str | None):
    cli = CLI()
    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)
    else:
        asyncio.run(cli.run_interactive())

if __name__ == "__main__":
    main()