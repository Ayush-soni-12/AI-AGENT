from dataclasses import dataclass
from prompt.system_prompt import get_system_prompt
from utils.text import count_tokens
from typing import Any


@dataclass
class MessageItem:
    role:str
    content:str
    token_count:str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class ContextManager:
    def __init__(self) -> None:
        from pathlib import Path
        from config.config import config_mgr
        
        self._model_name = config_mgr.get("model", "gemini-2.5-flash")
        self._messages: list[MessageItem] = []

        import uuid
        self.sessions_dir = Path.cwd() / ".agent_sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        self.active_session_id = str(uuid.uuid4())

        # Build system prompt now that we know the CWD (needed for AGENTS.md loading)
        self._system_prompt = get_system_prompt(cwd=Path.cwd())
        
        # Always start fresh — user can resume old sessions with /past
        self.api_prompt_tokens: int = 0
        self.api_completion_tokens: int = 0
        self._inject_memory()

    def _get_latest_session(self) -> str | None:
        try:
            files = list(self.sessions_dir.glob("*.json"))
            if not files: return None
            latest = max(files, key=lambda p: p.stat().st_mtime)
            return latest.stem
        except Exception:
            return None

    def _inject_memory(self):
        import sqlite3
        from pathlib import Path
        db_path = Path.cwd() / ".agent_memory.db"
        if not db_path.exists():
            return
            
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value, category FROM memories LIMIT 30")
                rows = cursor.fetchall()
                if rows:
                    memory_block = "\n\n--- LONG TERM MEMORY ---\nYou have access to the following long-term memory notes from previous sessions:\n"
                    for row in rows:
                        memory_block += f"- [{row[2]}] {row[0]}: {row[1]}\n"
                    memory_block += "Use the 'memory' tool to search for more, edit, or delete existing records."
                    self._system_prompt += memory_block
        except Exception:
            pass

    def add_user_message(self,content:str) -> None:
        item = MessageItem(
            role='user',
            content=content,
            token_count=count_tokens(self._model_name,content)
        )
        self._messages.append(item)
        self._save_session()

    def add_assistant_message(self,content:str, tool_calls: list[dict] | None = None) -> None:
        item = MessageItem(
            role='assistant',
            content=content or "",
            token_count=count_tokens(self._model_name,content or ""),
            tool_calls=tool_calls
        )
        self._messages.append(item)
        self._save_session()

    def add_tool_message(self, tool_call_id: str, name: str, content: str) -> None:
        item = MessageItem(
            role='tool',
            content=content,
            token_count=count_tokens(self._model_name, content),
            tool_call_id=tool_call_id,
            name=name
        )
        self._messages.append(item)
        self._save_session()

    def get_total_tokens(self) -> int:
        """Return real API-reported tokens (prompt + completion). Falls back to estimate."""
        api_total = self.api_prompt_tokens + self.api_completion_tokens
        if api_total > 0:
            return api_total
        # Fallback: sum locally-estimated token counts if API hasn't reported yet
        return sum(item.token_count or 0 for item in self._messages)

    def record_api_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Accumulate real API token usage from each LLM turn."""
        self.api_prompt_tokens += prompt_tokens
        self.api_completion_tokens += completion_tokens

    def get_messages(self) -> list[dict[str, Any]]:
        messages =[]
        if self._system_prompt:
            messages.append({"role":"system", "content":self._system_prompt})

        for item in self._messages:
            msg = {"role":item.role, "content":item.content}
            if item.tool_calls:
                msg["tool_calls"] = item.tool_calls
            if item.tool_call_id:
                msg["tool_call_id"] = item.tool_call_id
            if item.name:
                msg["name"] = item.name
            messages.append(msg)
        return messages

    def list_sessions(self) -> list[dict]:
        import json
        sessions = []
        for file in self.sessions_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                # Grab a snippet of the first user message for context
                snippet = "Empty Session"
                for record in data:
                    if record.get("role") == "user":
                        snippet = record.get("content", "")[:40] + "..."
                        break
                sessions.append({
                    "id": file.stem,
                    "mtime": file.stat().st_mtime,
                    "snippet": snippet
                })
            except Exception:
                pass
        # Sort by most recently modified
        sessions.sort(key=lambda x: x["mtime"], reverse=True)
        return sessions

    def create_new_session(self) -> None:
        import uuid
        self.active_session_id = str(uuid.uuid4())
        self._messages = []
        self.api_prompt_tokens = 0
        self.api_completion_tokens = 0

    def delete_all_sessions(self) -> int:
        """Delete every session JSON file in sessions_dir. Returns count deleted."""
        deleted = 0
        for f in self.sessions_dir.glob("*.json"):
            try:
                f.unlink()
                deleted += 1
            except Exception:
                pass
        # Start fresh so next save won't re-create an old file
        self.create_new_session()
        return deleted

    def load_session(self, session_id: str) -> bool:
        import json
        session_file = self.sessions_dir / f"{session_id}.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
                self._messages = []
                self.active_session_id = session_id
                for record in data:
                    item = MessageItem(
                        role=record.get("role"),
                        content=record.get("content"),
                        token_count=record.get("token_count", 0),
                        tool_calls=record.get("tool_calls"),
                        tool_call_id=record.get("tool_call_id"),
                        name=record.get("name")
                    )
                    self._messages.append(item)
                return True
            except Exception:
                return False
        return False
                
    def _save_session(self) -> None:
        import json
        session_file = self.sessions_dir / f"{self.active_session_id}.json"
        try:
            data = []
            for item in self._messages:
                data.append({
                    "role": item.role,
                    "content": item.content,
                    "token_count": item.token_count,
                    "tool_calls": item.tool_calls,
                    "tool_call_id": item.tool_call_id,
                    "name": item.name
                })
            session_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
