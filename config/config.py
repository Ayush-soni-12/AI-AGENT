import json
import os
from pathlib import Path

class ConfigManager:
    _instance = None
    _config_path = Path.home() / ".config" / "neuralclaude" / "settings.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._settings = {}
            cls._instance._load()
        return cls._instance

    def _load(self):
        if self._config_path.exists():
            try:
                self._settings = json.loads(self._config_path.read_text(encoding="utf-8"))
            except Exception:
                self._settings = {}
        else:
            self._settings = {}

    def _save(self):
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(json.dumps(self._settings, indent=2), encoding="utf-8")

    def get(self, key: str, default=None):
        return self._settings.get(key, default)

    def set(self, key: str, value):
        self._settings[key] = value
        self._save()

    def has_api_key(self) -> bool:
        return bool(self.get("api_key"))

config_mgr = ConfigManager()
