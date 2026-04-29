"""
Tests for ConfigManager — read, write, and default fallback behaviour.

ConfigManager is a singleton that reads from ~/.config/neuralclaude/settings.json.
We monkeypatch the config path to use a temp file so real settings are untouched.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch


def make_config(tmp_path: Path, initial: dict | None = None):
    """Return a fresh (non-singleton) ConfigManager pointing at tmp_path."""
    config_file = tmp_path / "settings.json"
    if initial:
        config_file.write_text(json.dumps(initial), encoding="utf-8")

    # Reset singleton so each test gets a clean instance
    import config.config as cfg_module
    cfg_module.ConfigManager._instance = None

    with patch.object(cfg_module.ConfigManager, "_config_path", config_file):
        mgr = cfg_module.ConfigManager()
        mgr._config_path = config_file  # ensure instance also points to tmp
        return mgr, config_file


class TestConfigRead:

    def test_get_returns_default_when_key_missing(self, tmp_path):
        mgr, _ = make_config(tmp_path)
        assert mgr.get("nonexistent_key", "fallback") == "fallback"

    def test_get_returns_none_by_default(self, tmp_path):
        mgr, _ = make_config(tmp_path)
        assert mgr.get("nonexistent_key") is None

    def test_get_existing_key(self, tmp_path):
        mgr, _ = make_config(tmp_path, {"model": "gemini-2.5-flash"})
        assert mgr.get("model") == "gemini-2.5-flash"

    def test_load_from_existing_file(self, tmp_path):
        mgr, _ = make_config(tmp_path, {"api_key": "sk-test-123"})
        assert mgr.get("api_key") == "sk-test-123"


class TestConfigWrite:

    def test_set_persists_value(self, tmp_path):
        mgr, config_file = make_config(tmp_path)
        mgr.set("model", "gemini-2.5-pro")

        # Re-read from disk
        data = json.loads(config_file.read_text())
        assert data["model"] == "gemini-2.5-pro"

    def test_set_multiple_values(self, tmp_path):
        mgr, config_file = make_config(tmp_path)
        mgr.set("model", "gemini-2.5-flash")
        mgr.set("api_key", "test-key")

        data = json.loads(config_file.read_text())
        assert data["model"] == "gemini-2.5-flash"
        assert data["api_key"] == "test-key"

    def test_set_overwrites_existing_value(self, tmp_path):
        mgr, config_file = make_config(tmp_path, {"model": "old-model"})
        mgr.set("model", "new-model")

        data = json.loads(config_file.read_text())
        assert data["model"] == "new-model"


class TestHasApiKey:

    def test_has_api_key_true_when_key_set(self, tmp_path):
        mgr, _ = make_config(tmp_path, {"api_key": "sk-real-key"})
        assert mgr.has_api_key() is True

    def test_has_api_key_false_when_missing(self, tmp_path):
        mgr, _ = make_config(tmp_path)
        assert mgr.has_api_key() is False

    def test_has_api_key_false_when_empty_string(self, tmp_path):
        mgr, _ = make_config(tmp_path, {"api_key": ""})
        assert mgr.has_api_key() is False


class TestCorruptedConfig:

    def test_corrupt_json_falls_back_to_empty(self, tmp_path):
        config_file = tmp_path / "settings.json"
        config_file.write_text("{invalid json!!}", encoding="utf-8")

        import config.config as cfg_module
        cfg_module.ConfigManager._instance = None
        with patch.object(cfg_module.ConfigManager, "_config_path", config_file):
            mgr = cfg_module.ConfigManager()
            mgr._config_path = config_file
            # Should not crash, should fallback to empty
            assert mgr.get("model", "default") == "default"
