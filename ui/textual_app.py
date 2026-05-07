import json
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Markdown, Static, Label, Button, TextArea, RichLog
from textual.containers import VerticalScroll, Grid, Vertical, Horizontal
from textual.screen import ModalScreen
from textual import work
from textual.events import Paste
from agent.event import AgentEventType


class GitCommitScreen(ModalScreen[str | None]):
    """Modal that shows an AI-generated commit message for review and editing."""

    CSS = """
    GitCommitScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }
    #git-dialog {
        padding: 1 2;
        width: 90;
        height: auto;
        max-height: 40;
        border: thick green;
        background: $surface;
        layout: vertical;
    }
    #git-title {
        text-style: bold;
        color: green;
        margin-bottom: 1;
    }
    #commit-msg {
        height: 12;
        margin-bottom: 1;
        border: solid $accent;
    }
    #git-btn-row {
        grid-size: 3;
        grid-gutter: 1 2;
        height: 3;
    }
    #git-btn-row Button { width: 100%; }
    """

    def __init__(self, message: str):
        super().__init__()
        self._initial_message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="git-dialog"):
            yield Label("🤖 AI-Generated Commit Message (edit if needed):", id="git-title")
            yield TextArea(self._initial_message, id="commit-msg")
            with Grid(id="git-btn-row"):
                yield Button("✅ Commit", variant="success", id="do-commit")
                yield Button("✏️ Clear", variant="default", id="clear-msg")
                yield Button("❌ Cancel", variant="error", id="cancel-commit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "do-commit":
            msg = self.query_one("#commit-msg", TextArea).text.strip()
            self.dismiss(msg if msg else None)
        elif event.button.id == "clear-msg":
            self.query_one("#commit-msg", TextArea).clear()
        else:
            self.dismiss(None)


class GitPRScreen(ModalScreen[bool]):
    """Modal that previews an AI-generated PR title + body before creating."""

    CSS = """
    GitPRScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }
    #pr-dialog {
        padding: 1 2;
        width: 90;
        height: auto;
        max-height: 45;
        border: thick cyan;
        background: $surface;
        layout: vertical;
    }
    #pr-title-label { text-style: bold; color: cyan; }
    #pr-title-input { margin-bottom: 1; border: solid $accent; }
    #pr-body-area { height: 15; margin-bottom: 1; border: solid $accent; }
    #pr-btn-row { grid-size: 2; grid-gutter: 1 2; height: 3; }
    #pr-btn-row Button { width: 100%; }
    """

    def __init__(self, title: str, body: str):
        super().__init__()
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        with Vertical(id="pr-dialog"):
            yield Label("🐙 AI-Generated Pull Request (edit if needed):", id="pr-title-label")
            yield Input(self._title, id="pr-title-input", placeholder="PR Title")
            yield TextArea(self._body, id="pr-body-area")
            with Grid(id="pr-btn-row"):
                yield Button("🚀 Create PR", variant="success", id="do-pr")
                yield Button("❌ Cancel", variant="error", id="cancel-pr")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "do-pr")

    def get_title(self) -> str:
        """Return the (possibly edited) PR title."""
        return self.query_one("#pr-title-input", Input).value.strip()

    def get_body(self) -> str:
        """Return the (possibly edited) PR body."""
        return self.query_one("#pr-body-area", TextArea).text.strip()


class ConfirmScreen(ModalScreen[bool]):
    CSS = """
    ConfirmScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 1;
        width: 80;
        height: auto;
        max-height: 80%;
        border: thick red;
        background: $surface;
    }
    #question-container {
        column-span: 2;
        height: auto;
        max-height: 100%;
    }
    #question {
        width: 1fr;
        color: yellow;
        text-style: bold;
    }
    Button {
        width: 100%;
    }
    """
    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        yield Grid(
            VerticalScroll(Label(self.message, id="question"), id="question-container"),
            Button("Deny (n)", variant="error", id="deny"),
            Button("Approve (y)", variant="success", id="approve"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve":
            self.dismiss(True)
        else:
            self.dismiss(False)


from config.config import config_mgr

class ConfigScreen(ModalScreen[bool]):
    CSS = """
    ConfigScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #config-dialog {
        padding: 1 2;
        width: 80;
        height: auto;
        border: thick cyan;
        background: $surface;
        layout: vertical;
    }
    #config-title {
        content-align: center middle;
        text-style: bold;
        color: cyan;
        margin-bottom: 1;
        width: 100%;
    }
    .config-label {
        margin-top: 1;
        color: yellow;
    }
    #button-row {
        grid-size: 2;
        grid-gutter: 1 2;
        margin-top: 2;
    }
    #button-row Button {
        width: 100%;
    }
    """
    def compose(self) -> ComposeResult:
        from textual.widgets import Select
        from textual.containers import Container
        
        current_model = config_mgr.get("model", "gemini-2.5-flash")
        
        valid_models = [
            ("Gemini 2.5 Flash", "gemini-2.5-flash"),
            ("Gemini 2.5 Pro", "gemini-2.5-pro"),
            ("Claude 3.5 Sonnet", "anthropic/claude-3.5-sonnet"),
            ("Claude 3.7 Sonnet", "anthropic/claude-3.7-sonnet"),
            ("GPT-4o", "openai/gpt-4o")
        ]
        
        current_val = current_model if any(current_model == v[1] for v in valid_models) else "gemini-2.5-flash"

        yield Container(
            Label("⚙️ Neural Claude Configuration", id="config-title"),
            Label("Select Model:", classes="config-label"),
            Select(valid_models, value=current_val, id="model-select"),
            Label("Update API Key (Leave blank to keep unchanged):", classes="config-label"),
            Input(placeholder="Paste new API key here...", password=True, id="apikey-input"),
            Grid(
                Button("Cancel", variant="error", id="cancel"),
                Button("Save and Apply", variant="success", id="save"),
                id="button-row"
            ),
            id="config-dialog"
        )
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            from textual.widgets import Select
            model_val = self.query_one("#model-select", Select).value
            key_val = self.query_one("#apikey-input", Input).value.strip()
            
            if model_val:
                config_mgr.set("model", model_val)
                # Ensure provider logic bridges over accurately for dynamic URLs
                if "gemini" in model_val and "google" not in model_val:
                    config_mgr.set("provider", "gemini")
                    config_mgr.set("base_url", "https://generativelanguage.googleapis.com/v1beta/openai/")
                else:
                    config_mgr.set("provider", "openrouter")
                    config_mgr.set("base_url", "https://openrouter.ai/api/v1")
                    
            if key_val:
                config_mgr.set("api_key", key_val)
                
            self.dismiss(True)
        else:
            self.dismiss(False)


class ChatApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    #main-layout {
        height: 1fr;
    }
    #chat-container {
        width: 65%;
        height: 1fr;
        border: solid cyan;
        padding: 1;
        overflow-y: scroll;
    }
    #log-panel {
        width: 35%;
        height: 1fr;
        border: solid yellow;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
    }
    Input {
        dock: bottom;
        margin: 1;
    }
    .assistant-msg {
        border: solid blue;
        margin-top: 1;
        margin-bottom: 1;
        padding: 1;
        background: rgba(0, 0, 255, 0.1);
    }
    .user-msg {
        color: ansi_bright_cyan;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
    }
    .tool-msg {
        border: solid magenta;
        color: ansi_bright_magenta;
        margin-left: 2;
        background: rgba(255, 0, 255, 0.05);
    }
    .system-msg {
        color: yellow;
        text-style: italic;
    }
    """
    
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+d", "quit", "Quit")
    ]

    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        # We bind the callback directly to the app
        self.agent._confirm_callback = self.confirm_tool_async

    def compose(self) -> ComposeResult:
        from textual.suggester import SuggestFromList
        yield Header(show_clock=True)
        
        with Horizontal(id="main-layout"):
            yield VerticalScroll(id="chat-container")
            yield RichLog(id="log-panel", highlight=True, markup=False, wrap=True)

        commands = ["/help", "/mcp", "/commit", "/pr", "/test", "/status", "/config", "/init", "/new", "/past", "/clear", "/clear memory", "/exit", "/quit"]
        yield Input(
            placeholder="Ask Neural Claude... (Type '/' for commands)", 
            id="prompt",
            suggester=SuggestFromList(commands, case_sensitive=False)
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Neural Claude"
        chat = self.query_one("#chat-container", VerticalScroll)
        chat.mount(Static("⚡ Neural Claude ready. Type /help to see available commands.", classes="system-msg"))
        self._update_token_display()
        
        # Wire up process logs to the log panel
        self.agent.process_manager.set_log_callback(self._on_process_log)
        
        # Connect to MCP servers inside Textual's event loop to avoid anyio scope issues
        self.run_worker(self._start_mcp_worker(), exclusive=False)

    def _on_process_log(self, message: str) -> None:
        """Callback from ProcessManager to update the UI log panel."""
        try:
            log_panel = self.query_one("#log-panel", RichLog)
            log_panel.write(message)
        except:
            pass

    async def _start_mcp_worker(self):
        """Connect MCP servers in the same event loop as Textual."""
        try:
            count = await self.agent.start_mcp()
            if count > 0:
                chat = self.query_one("#chat-container", VerticalScroll)
                tools = self.agent.mcp_manager.get_all_tools()
                names = ", ".join(f"`{t['name']}`" for t in tools)
                await chat.mount(Static(
                    f"🔌 MCP: {count} server(s) connected — {len(tools)} tool(s) available ({names})",
                    classes="system-msg"
                ))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[MCP] startup error: {e}")

    async def on_unmount(self) -> None:
        """Disconnect MCP servers cleanly when the app exits."""
        try:
            await self.agent.stop_mcp()
        except Exception:
            pass

    def _update_token_display(self) -> None:
        """Refresh the header subtitle with the live session token count and cache savings."""
        cm = self.agent.context_manager
        model = cm._model_name.split("/")[-1]

        if cm.api_prompt_tokens > 0:
            total = cm.api_prompt_tokens + cm.api_completion_tokens
            parts = [
                f"󰊤 {model}  │",
                f"In: {cm.api_prompt_tokens:,}",
                f"Out: {cm.api_completion_tokens:,}",
                f"Total: {total:,}",
            ]
            if cm.api_cached_tokens > 0:
                saved_pct = int((cm.api_cached_tokens / cm.api_prompt_tokens) * 100)
                parts.append(f"⚡ {cm.api_cached_tokens:,} cached ({saved_pct}% saved)")
            self.sub_title = "  ".join(parts)
        else:
            estimated = cm.get_total_tokens()
            self.sub_title = f"󰊤 {model}  │  ~{estimated:,} tokens (estimated)"

    def _wipe_project_data(self) -> str:
        """Wipe ALL project data: memory DB + all session files + reset active session."""
        import sqlite3
        lines = []

        # 1. Wipe memory database
        db_path = self.agent.context_manager.sessions_dir.parent / ".agent_memory.db"
        if db_path.exists():
            try:
                with sqlite3.connect(db_path) as conn:
                    deleted_mem = conn.execute("DELETE FROM memories").rowcount
                    conn.commit()
                lines.append(f"🗑️  Wiped {deleted_mem} memory record(s).")
            except Exception as e:
                lines.append(f"⚠️  Memory wipe failed: {e}")
        else:
            lines.append("ℹ️  No memory database found.")

        # 2. Delete all session files via ContextManager (uses same sessions_dir)
        deleted_sessions = self.agent.context_manager.delete_all_sessions()
        lines.append(f"🗑️  Deleted {deleted_sessions} session file(s).")
        lines.append("✨ Started a fresh session.")

        return "\n".join(lines)


    async def confirm_tool_async(self, confirmation) -> bool:
        diff_text = ""
        if confirmation.diff:
            diff_text = confirmation.diff.to_diff()
            if diff_text:
                diff_text = f"\n\n[Diff Preview]\n{diff_text}"
        
        msg = f"⚠️ ACTION REQUIRED: {confirmation.description}{diff_text}"
        
        import os
        is_ide = any(key in os.environ for key in ["VSCODE_PID", "JETBRAINS_IDE"]) or \
                 os.environ.get("TERM_PROGRAM") in ["vscode", "cursor", "warp"]
                 
        if not is_ide:
            # Natively await the modal screen result
            return await self.push_screen_wait(ConfirmScreen(msg))
        else:
            # Inline chat prompt for small IDE terminals
            chat = self.query_one("#chat-container", VerticalScroll)
            await chat.mount(Markdown(msg + "\n\n**[IDE Mode] Type `y` to approve or `n` to reject.**", classes="tool-msg"))
            chat.scroll_end(animate=False)
            
            # Temporarily unlock input for the y/n response
            inp = self.query_one(Input)
            inp.disabled = False
            inp.focus()
            
            import asyncio
            self._awaiting_confirmation = asyncio.get_running_loop().create_future()
            result = await self._awaiting_confirmation
            
            # Re-lock input as the agent resumes processing
            inp.disabled = True
            return result

    def on_paste(self, event: Paste) -> None:
        """Capture drag-and-drop or terminal pastes and append to the input box."""
        inp = self.query_one(Input)
        
        # When dragging a file, terminals often surround the path in single quotes
        # We strip surrounding whitespace and single quotes for clean file paths
        pasted_text = event.text.strip()
        if pasted_text.startswith("'") and pasted_text.endswith("'"):
            pasted_text = pasted_text[1:-1]
            
        if pasted_text:
            if inp.value and not inp.value.endswith(" "):
                inp.value += " "
            inp.value += pasted_text
            inp.focus()
                    
    async def on_input_submitted(self, message: Input.Submitted) -> None:
        if not message.value.strip(): return
        
        user_text = message.value
        
        # Check if the agent is blocked waiting for a y/n inline confirmation
        if hasattr(self, '_awaiting_confirmation') and self._awaiting_confirmation and not self._awaiting_confirmation.done():
            self.query_one(Input).value = ""
            chat = self.query_one("#chat-container", VerticalScroll)
            if user_text.lower() in ['y', 'yes']:
                await chat.mount(Static("✅ Approved inline.", classes="system-msg"))
                self._awaiting_confirmation.set_result(True)
            else:
                await chat.mount(Static("❌ Rejected inline.", classes="system-msg"))
                self._awaiting_confirmation.set_result(False)
            self._awaiting_confirmation = None
            chat.scroll_end(animate=False)
            return

        if user_text.lower() in ["/exit", "/quit"]:
            self.exit()
            return

        # /clear — only clears the visual screen (like bash 'clear')
        # The session continues invisibly; nothing is added to /past
        if user_text.lower() in ["clear", "/clear"] or user_text.lower().startswith("/clear"):
            wipe_memory = "memory" in user_text.lower()
            self.query_one(Input).value = ""
            chat = self.query_one("#chat-container", VerticalScroll)
            chat.remove_children()

            if wipe_memory:
                msg = self._wipe_project_data()  # wipes memory DB + all sessions + new session
                await chat.mount(Static(
                    f"🧹 Full project reset:\n{msg}",
                    classes="system-msg"
                ))
                self._update_token_display()
            else:
                await chat.mount(Static(
                    "🧹 Screen cleared. Your session is still active. "
                    "Use /new to start a fresh thread, or /clear memory to wipe ALL project data.",
                    classes="system-msg"
                ))
            return

        if user_text.lower() == "/help":
            self.query_one(Input).value = ""
            chat = self.query_one("#chat-container", VerticalScroll)
            help_text = """## 🤖 Neural Claude — Available Commands

| Command | Description |
|---|---|
| `/new` | Branch into a fresh session thread (old thread saved to /past) |
| `/init` | Initialize the project with AGENTS.md |
| `/past` | List all saved session threads for this project |
| `/past [N]` | Resume session thread number N |
| `/clear` | Clear the screen only — session keeps going, nothing saved to /past |
| `/clear memory` | Clear the screen AND wipe ALL project data (memory + sessions) |
| `/commit` | AI writes a commit message for your changes, opens preview |
| `/pr` | AI writes a PR title + description, opens preview to create PR |
| `/test` | Run project tests/linter; if they fail the agent auto-fixes and retries |
| `/mcp` | Show connected MCP servers and their available tools |
| `/config` | Open the Settings panel (model, API key) |
| `/help` | Show this help message |
| `exit` or `quit` | Quit Neural Claude |

**Tips:**
- Sessions and memory are **isolated per project directory**
- Type `/` and press `→` to autocomplete commands
- Your config is stored globally at `~/.config/neuralclaude/settings.json`
- Add MCP servers in `~/.config/neuralclaude/mcp_servers.json`
- Project-level rules go in an `AGENTS.md` file in your project root"""
            await chat.mount(Markdown(help_text, classes="system-msg"))
            chat.scroll_end(animate=False)
            return

        if user_text.lower() == "/mcp":
            self.query_one(Input).value = ""
            chat = self.query_one("#chat-container", VerticalScroll)
            mcp_mgr = self.agent.mcp_manager
            if mcp_mgr is None:
                await chat.mount(Static("🔌 MCP is not initialised.", classes="system-msg"))
            else:
                status = mcp_mgr.status()
                if not status:
                    text = "🔌 No MCP servers configured.\nAdd entries to `~/.config/neuralclaude/mcp_servers.json` to connect tools."
                else:
                    lines = ["## 🔌 Connected MCP Servers\n"]
                    for s in status:
                        icon = "✅" if s["connected"] else "❌"
                        lines.append(f"{icon} **{s['name']}** — {s['tools']} tool(s)")
                    # List tool names
                    all_tools = mcp_mgr.get_all_tools()
                    if all_tools:
                        lines.append("\n**Available Tools:**")
                        for t in all_tools:
                            lines.append(f"- `{t['name']}` — {t['description'][:80]}")
                    text = "\n".join(lines)
                await chat.mount(Markdown(text, classes="system-msg"))
            chat.scroll_end(animate=False)
            return

        if user_text.lower() == "/new":
            self.agent.context_manager.create_new_session()
            chat = self.query_one("#chat-container", VerticalScroll)
            chat.remove_children()
            self.query_one(Input).value = ""
            await chat.mount(Static("✨ Started a fresh conversation context.", classes="system-msg"))
            self._update_token_display()
            return
            
        if user_text.lower() == "/config":
            self.query_one(Input).value = ""
            self.action_launch_config()
            return
            
        if user_text.lower().startswith("/past"):
            parts = user_text.split()
            chat = self.query_one("#chat-container", VerticalScroll)
            self.query_one(Input).value = ""
            
            if len(parts) == 1:
                sessions = self.agent.context_manager.list_sessions()
                if not sessions:
                    await chat.mount(Static("📭 No past sessions found.", classes="system-msg"))
                else:
                    msg = "📚 **Past Sessions Thread Archive:**\n"
                    for idx, s in enumerate(sessions):
                        msg += f"**[{idx}]** {s['snippet']} (`{s['id'][:6]}`)\n"
                    msg += "\n*Type `/past [number]` to warp to a session.*"
                    await chat.mount(Markdown(msg, classes="system-msg"))
            else:
                try:
                    idx = int(parts[1])
                    sessions = self.agent.context_manager.list_sessions()
                    if 0 <= idx < len(sessions):
                        session_id = sessions[idx]['id']
                        if self.agent.context_manager.load_session(session_id):
                            chat.remove_children()
                            await chat.mount(Static(f"🔄 Successfully resumed internal thread [{idx}].", classes="system-msg"))
                            # Rehydrate UI with existing memory nodes
                            for item in self.agent.context_manager._messages:
                                if item.role == "user":
                                    await chat.mount(Static(f"❯ You: {item.content}", classes="user-msg"))
                                elif item.role == "assistant":
                                    await chat.mount(Markdown(item.content, classes="assistant-msg"))
                        else:
                            await chat.mount(Static("❌ Corrupted. Failed to load session.", classes="tool-msg"))
                    else:
                        await chat.mount(Static("❌ Invalid session index.", classes="tool-msg"))
                except ValueError:
                    await chat.mount(Static("❌ Please provide a valid index number (e.g. `/past 1`).", classes="tool-msg"))
            chat.scroll_end(animate=False)
            return

        if user_text.lower() in ["/commit", "commit"]:
            self.query_one(Input).value = ""
            self.run_worker(self._handle_commit(), exclusive=False)
            return

        if user_text.lower() == "/init":
            self.query_one(Input).value = ""
            chat = self.query_one("#chat-container", VerticalScroll)
            await chat.mount(Static("🔍 Analyzing repository to generate AGENTS.md...", classes="system-msg"))
            chat.scroll_end(animate=False)
            
            init_prompt = (
                "Please analyze this repository's structure and configuration files "
                "(e.g., package.json, requirements.txt, framework configs). Based on your analysis, "
                "write a comprehensive `AGENTS.md` file in the root directory. "
                "This file should establish project-specific instructions, coding standards, styling rules, "
                "and architectural patterns that you and future AI agents should follow in this repo. "
                "Use the write_to_file tool to save it. When you finish, tell the user that the initialization is complete."
            )
            self.query_one(Input).disabled = True
            self.process_agent(init_prompt)
            return

        if user_text.lower() in ["/status", "status"]:
            self.query_one(Input).value = ""
            chat = self.query_one("#chat-container", VerticalScroll)
            
            cm = self.agent.context_manager
            model = cm._model_name.split("/")[-1]
            total_tokens = cm.api_prompt_tokens + cm.api_completion_tokens
            saved_pct = int((cm.api_cached_tokens / max(cm.api_prompt_tokens, 1)) * 100) if cm.api_cached_tokens > 0 else 0
            
            import os
            import pathlib
            cwd = pathlib.Path.cwd()
            is_ide = any(key in os.environ for key in ["VSCODE_PID", "JETBRAINS_IDE"]) or os.environ.get("TERM_PROGRAM") in ["vscode", "cursor", "warp"]
            
            status_md = f"""
## 📊 System Status

**Environment**
* **Active Model:** `{model}`
* **Working Directory:** `{cwd}`
* **IDE Detection:** `{"Active (Popups suppressed)" if is_ide else "Inactive (Native modals enabled)"}`

**Session Statistics**
* **Memory Nodes in Context:** `{len(cm._messages)}`
* **Input Tokens:** `{cm.api_prompt_tokens:,}`
* **Output Tokens:** `{cm.api_completion_tokens:,}`
* **Total Tokens Used:** `{total_tokens:,}`
* **Context Caching:** `{cm.api_cached_tokens:,} tokens ({saved_pct}% saved)`

**Capabilities**
* **Active Tools:** `{len(self.agent.tool_registry.get_tools())} functions available`
"""
            await chat.mount(Markdown(status_md, classes="system-msg"))
            chat.scroll_end(animate=False)
            return

        if user_text.lower() in ["/test", "test"]:
            self.query_one(Input).value = ""
            # Dispatch as a regular agent task so the LLM can see
            # the output and self-correct in a natural agentic loop
            test_prompt = (
                "Run the project tests now using the `run_tests` tool. "
                "If they fail, read the errors, fix the root cause in the code, "
                "then call `run_tests` again. Repeat until they pass (max 3 attempts). "
                "Report the final status."
            )
            chat = self.query_one("#chat-container", VerticalScroll)
            await chat.mount(Static("🧪 Running tests...", classes="system-msg"))
            chat.scroll_end(animate=False)
            self.query_one(Input).disabled = True
            self.process_agent(test_prompt)
            return

        if user_text.lower() in ["/pr", "pr"]:
            self.query_one(Input).value = ""
            self.run_worker(self._handle_pr(), exclusive=False)
            return

        self.query_one(Input).value = ""
        chat = self.query_one("#chat-container", VerticalScroll)
        await chat.mount(Static(f"❯ You: {user_text}", classes="user-msg"))
        chat.scroll_end(animate=False)
        
        # Disable input while processing
        self.query_one(Input).disabled = True
        self.process_agent(user_text)

    async def _handle_commit(self) -> None:
        """Stage all changes, generate an AI commit message, show preview modal, commit."""
        from pathlib import Path
        from utils.git import (
            is_git_repo, stage_all, get_staged_diff,
            generate_commit_message, commit as git_commit,
        )
        chat = self.query_one("#chat-container", VerticalScroll)
        cwd = Path.cwd()

        if not await is_git_repo(cwd):
            await chat.mount(Static("❌ Not a git repository.", classes="tool-msg"))
            return

        await chat.mount(Static("⏳ Staging all changes...", classes="system-msg"))
        chat.scroll_end(animate=False)
        await stage_all(cwd)

        diff = await get_staged_diff(cwd)
        if not diff.strip():
            await chat.mount(Static("ℹ️ Nothing to commit — working tree is clean.", classes="system-msg"))
            return

        await chat.mount(Static("🤖 Generating commit message...", classes="system-msg"))
        chat.scroll_end(animate=False)

        msg = await generate_commit_message(diff, self.agent.client)
        if not msg:
            await chat.mount(Static("⚠️ AI returned an empty message. Aborting.", classes="tool-msg"))
            return

        final_msg = await self.push_screen_wait(GitCommitScreen(msg))
        if not final_msg:
            await chat.mount(Static("❌ Commit cancelled.", classes="system-msg"))
            return

        success, output = await git_commit(final_msg, cwd)
        icon = "✅" if success else "❌"
        await chat.mount(Static(f"{icon} {output}", classes="system-msg" if success else "tool-msg"))
        chat.scroll_end(animate=False)

    async def _handle_pr(self) -> None:
        """Generate an AI PR description and create a GitHub PR via gh CLI."""
        from pathlib import Path
        from utils.git import (
            is_git_repo, get_current_branch, get_branch_diff_vs_main,
            get_branch_commits, generate_pr_description, has_gh_cli, 
            create_pr, push_branch,
        )
        chat = self.query_one("#chat-container", VerticalScroll)
        cwd = Path.cwd()

        if not await is_git_repo(cwd):
            await chat.mount(Static("❌ Not a git repository.", classes="tool-msg"))
            return

        if not await has_gh_cli():
            await chat.mount(Static(
                "❌ GitHub CLI (`gh`) not installed or not authenticated.\n"
                "Install: https://cli.github.com  then run `gh auth login`.",
                classes="tool-msg"
            ))
            return

        branch = await get_current_branch(cwd)
        if branch in ("main", "master", "HEAD"):
            await chat.mount(Static(
                f"⚠️ You are on `{branch}`. Switch to a feature branch first.",
                classes="tool-msg"
            ))
            return

        await chat.mount(Static(f"⏳ Analysing branch `{branch}` vs main...", classes="system-msg"))
        chat.scroll_end(animate=False)

        commits = await get_branch_commits(cwd)
        diff = await get_branch_diff_vs_main(cwd)

        if not commits and not diff:
            await chat.mount(Static("ℹ️ No commits ahead of main. Nothing to PR.", classes="system-msg"))
            return

        await chat.mount(Static("🤖 Generating PR description...", classes="system-msg"))
        chat.scroll_end(animate=False)

        title, body = await generate_pr_description(commits, diff, branch, self.agent.client)

        screen = GitPRScreen(title, body)
        confirmed = await self.push_screen_wait(screen)
        if not confirmed:
            await chat.mount(Static("❌ PR creation cancelled.", classes="system-msg"))
            return

        final_title = screen.get_title() or title
        final_body = screen.get_body() or body

        await chat.mount(Static(f"🚀 Pushing branch `{branch}` to origin...", classes="system-msg"))
        chat.scroll_end(animate=False)
        push_success, push_out = await push_branch(branch, cwd)
        if not push_success:
            await chat.mount(Static(f"❌ Failed to push branch:\n{push_out}", classes="tool-msg"))
            return

        await chat.mount(Static("🚀 Creating PR on GitHub...", classes="system-msg"))
        success, output = await create_pr(final_title, final_body, cwd)
        icon = "✅" if success else "❌"
        await chat.mount(Static(f"{icon} {output}", classes="system-msg" if success else "tool-msg"))
        chat.scroll_end(animate=False)

    @work
    async def action_launch_config(self) -> None:

        saved = await self.push_screen_wait(ConfigScreen())
        if saved:
            # Update ContextManager's mapped variables so they dynamically switch mid-thread without restarting!
            self.agent.context_manager._model_name = config_mgr.get("model", "gemini-2.5-flash")
            # Reload LLM Client with new endpoint bindings
            self.agent.client._client = None 
            chat = self.query_one("#chat-container", VerticalScroll)
            await chat.mount(Static("✅ Configuration automatically hot-reloaded! Switched model engines seamlessly.", classes="system-msg"))
            chat.scroll_end(animate=False)

    @work
    async def process_agent(self, text: str) -> None:
        chat = self.query_one("#chat-container", VerticalScroll)
        
        current_md = None
        current_md_text = ""
        
        try:
            async for event in self.agent.run(text):
                if event.type == AgentEventType.TEXT_DELTA:
                    content = event.data.get("content","")
                    if current_md is None:
                        current_md = Markdown(content, classes="assistant-msg")
                        await chat.mount(current_md)
                        current_md_text = content
                    else:
                        current_md_text += content
                        current_md.update(current_md_text)
                        
                    chat.scroll_end(animate=False)

                elif event.type == AgentEventType.TEXT_COMPLETE:
                    current_md = None
                    
                elif event.type == AgentEventType.TOOL_CALL:
                    name = event.data.get("name")
                    args = event.data.get("arguments")
                    try:
                        args_str = json.dumps(args, indent=2)
                    except:
                        args_str = str(args)
                    msg_text = f"⚙️ Thinking... Calling Tool: {name}\n{args_str}"
                    await chat.mount(Static(msg_text, classes="tool-msg", markup=False))
                    chat.scroll_end(animate=False)
                    current_md = None

                elif event.type == AgentEventType.TOOL_RESULT:
                    name = event.data.get("name")
                    diff_str = event.data.get("diff")
                    await chat.mount(Static(f"✅ Tool {name} Finished!", classes="tool-msg", markup=False))
                    if diff_str:
                        diff_md = Markdown(f"```diff\n{diff_str}\n```", classes="tool-msg")
                        await chat.mount(diff_md)
                    chat.scroll_end(animate=False)
                    current_md = None

                elif event.type == AgentEventType.AGENT_ERROR:
                    error = event.data.get("error","Unknown error")
                    await chat.mount(Static(f"❌ Error: {error}", classes="tool-msg", markup=False))
                    chat.scroll_end(animate=False)
                    current_md = None
                    
        finally:
            # Re-enable input
            inp = self.query_one(Input)
            inp.disabled = False
            inp.focus()
            # Refresh token counter in header
            self._update_token_display()
