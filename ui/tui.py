from rich.console import Console
from rich.theme import Theme
from rich.rule import Rule
from rich.text import Text

AGENT_THEME = Theme(
    {
        # General
        "info": "cyan",
        "warning": "yellow",
        "error": "bright_red bold",
        "success": "green",
        "dim": "dim",
        "muted": "grey50",
        "border": "grey35",
        "highlight": "bold cyan",
        # Roles
        "user": "bright_blue bold",
        "assistant": "bright_white",
        # Tools
        "tool": "bright_magenta bold",
        "tool.read": "cyan",
        "tool.write": "yellow",
        "tool.shell": "magenta",
        "tool.network": "bright_blue",
        "tool.memory": "green",
        "tool.mcp": "bright_cyan",
        # Code / blocks
        "code": "white",
    }
)



_console: Console | None = None


def get_console() -> Console:
    global _console
    if _console is None:
        _console = Console(theme=AGENT_THEME, highlight=False)

    return _console


from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

class TUI:

    def __init__(self,console:Console | None=None)->None:
        self.console = console or get_console()
        self._assistant_stream_open = False
        self._live: Live | None = None
        self._current_markdown = ""
    

    def begin_assistant(self)->None:
        self.console.print()
        self._assistant_stream_open = True
        self._current_markdown = ""
        panel = Panel(Markdown(self._current_markdown), title="[bold blue]🤖 Neural Claude[/bold blue]", border_style="blue", padding=(1, 2))
        self._live = Live(panel, console=self.console, refresh_per_second=15, transient=False)
        self._live.start()

    def end_assistand(self)-> None:
        if self._live:
            self._live.stop()
            self._live = None
        if self._assistant_stream_open:
            self.console.print()
        self._assistant_stream_open = False

    def stream_assistant_detail(self,content:str)->None:
        if self._live:
            self._current_markdown += content
            panel = Panel(Markdown(self._current_markdown), title="[bold blue]🤖 Neural Claude[/bold blue]", border_style="blue", padding=(1, 2))
            self._live.update(panel)
        else:
            self.console.print(content,end="",markup=False)

    def show_tool_call(self, name: str, args: str) -> None:
        title = f"[tool]⚙️  Thinking... Calling Tool:[/tool] [highlight]{name}[/highlight]"
        try:
            import json
            from rich.json import JSON
            parsed = json.loads(args)
            content = JSON.from_data(parsed)
        except Exception:
            content = Text(args, style="dim")
            
        panel = Panel(content, title=title, border_style="cyan", expand=False)
        self.console.print()
        self.console.print(panel)

    def show_tool_result(self, name: str, success: bool = True) -> None:
        if success:
            self.console.print(f"[success]✅ Tool {name} Finished![/success]")
        else:
            self.console.print(f"[error]❌ Tool {name} Failed![/error]")

    async def confirm_tool(self, confirmation) -> bool:
        from rich.prompt import Confirm
        from rich.syntax import Syntax
        
        self.console.print()
        
        if confirmation.diff:
            diff_text = confirmation.diff.to_diff()
            if diff_text:
                self.console.print(Panel(Syntax(diff_text, "diff", theme="monokai", background_color="default"), title="[bold yellow]Proposed File Changes[/bold yellow]", border_style="yellow"))
                
        warning_msg = f"[warning]⚠️  The agent would like to execute a potentially dangerous action:[/warning]\n\n[bold]{confirmation.description}[/bold]"
        self.console.print(Panel(warning_msg, border_style="red", title="[bold red]Action Required[/bold red]"))
        
        # Await user input. Since this is a simple CLI, a synchronous Console.input block is fine!
        return Confirm.ask("[bold red]Allow this action?[/bold red]", default=False, console=self.console)