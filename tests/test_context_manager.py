"""
Tests for ContextManager — session lifecycle, save/load/delete.
Uses a temporary directory to avoid touching the real .agent_sessions/.
"""

import json
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_manager(tmp_path: Path, monkeypatch):
    """Return a ContextManager whose sessions_dir lives inside tmp_path."""
    # ContextManager reads CWD and creates .agent_sessions/ there.
    # We monkeypatch Path.cwd so it points to our temp directory.
    monkeypatch.chdir(tmp_path)

    # Also patch get_system_prompt to avoid loading real AGENTS.md / memory
    import prompt.system_prompt as sp
    monkeypatch.setattr(sp, "get_system_prompt", lambda cwd=None: "test-prompt")

    # Avoid importing the real singleton config
    from unittest.mock import MagicMock
    import config.config as cfg
    monkeypatch.setattr(cfg, "config_mgr", MagicMock(get=lambda k, d=None: d))

    from context.manager import ContextManager
    return ContextManager()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSessionLifecycle:

    def test_new_manager_starts_with_empty_messages(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        assert cm._messages == []

    def test_sessions_dir_created(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        assert cm.sessions_dir.exists()
        assert cm.sessions_dir.is_dir()

    def test_create_new_session_resets_state(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        old_id = cm.active_session_id
        cm.add_user_message("hello")
        assert len(cm._messages) == 1

        cm.create_new_session()

        assert cm.active_session_id != old_id
        assert cm._messages == []
        assert cm.api_prompt_tokens == 0
        assert cm.api_completion_tokens == 0

    def test_add_user_message_saves_session(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        cm.add_user_message("test message")

        session_file = cm.sessions_dir / f"{cm.active_session_id}.json"
        assert session_file.exists()

        data = json.loads(session_file.read_text())
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "test message"

    def test_add_assistant_message(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        cm.add_assistant_message("I can help with that.")

        assert len(cm._messages) == 1
        assert cm._messages[0].role == "assistant"

    def test_add_tool_message(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        cm.add_tool_message("call_001", "shell", "command output")

        assert cm._messages[0].role == "tool"
        assert cm._messages[0].tool_call_id == "call_001"


class TestListSessions:

    def test_list_sessions_empty(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        # No messages added → no session file saved yet
        sessions = cm.list_sessions()
        assert isinstance(sessions, list)

    def test_list_sessions_returns_saved_sessions(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        cm.add_user_message("first message in session A")

        sessions = cm.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["id"] == cm.active_session_id
        assert "first message" in sessions[0]["snippet"]

    def test_list_sessions_sorted_by_mtime(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        cm.add_user_message("session A")
        id_a = cm.active_session_id

        cm.create_new_session()
        cm.add_user_message("session B")

        sessions = cm.list_sessions()
        # Most recently modified should be first
        assert sessions[0]["id"] != id_a or len(sessions) == 1


class TestLoadSession:

    def test_load_existing_session(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        cm.add_user_message("remember me")
        session_id = cm.active_session_id

        # Start fresh then reload
        cm.create_new_session()
        assert cm._messages == []

        success = cm.load_session(session_id)
        assert success is True
        assert len(cm._messages) == 1
        assert cm._messages[0].content == "remember me"

    def test_load_nonexistent_session_returns_false(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        result = cm.load_session("00000000-0000-0000-0000-000000000000")
        assert result is False


class TestDeleteAllSessions:

    def test_delete_all_sessions_removes_files(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)

        # Create two sessions with messages
        cm.add_user_message("session one")
        cm.create_new_session()
        cm.add_user_message("session two")

        assert len(list(cm.sessions_dir.glob("*.json"))) == 2

        deleted = cm.delete_all_sessions()

        assert deleted == 2
        assert len(list(cm.sessions_dir.glob("*.json"))) == 0

    def test_delete_all_sessions_resets_state(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        old_id = cm.active_session_id
        cm.add_user_message("some message")
        cm.delete_all_sessions()

        assert cm.active_session_id != old_id
        assert cm._messages == []

    def test_delete_all_sessions_on_empty_dir(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        deleted = cm.delete_all_sessions()
        assert deleted == 0


class TestTokenTracking:

    def test_record_api_usage_accumulates(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        cm.record_api_usage(100, 50)
        cm.record_api_usage(200, 100)

        assert cm.api_prompt_tokens == 300
        assert cm.api_completion_tokens == 150
        assert cm.get_total_tokens() == 450

    def test_get_total_tokens_falls_back_to_estimate(self, tmp_path, monkeypatch):
        cm = make_manager(tmp_path, monkeypatch)
        # No API usage recorded → falls back to local estimate
        cm.add_user_message("hello")
        total = cm.get_total_tokens()
        assert total >= 0  # Should be a non-negative estimate
