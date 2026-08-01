import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = {
    "style": "apa",
    "api_endpoint": "http://localhost:8000",
    "output_dir": ".",
    "page_size": "A4",
    "font_family": "Times New Roman",
    "font_size": 12,
    "line_spacing": 2.0,
    "include_toc": False,
    "include_page_numbers": True,
    "include_running_header": True,
    "verbose": False,
}


class AMFConfig:
    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or self._default_config_path()
        self._config: dict[str, Any] = {}
        self.load()

    @staticmethod
    def _default_config_path() -> Path:
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:
            base = Path.home() / ".config"
        return base / "amf" / "config.json"

    def load(self):
        self._config = DEFAULT_CONFIG.copy()
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    user_config = json.load(f)
                    self._config.update(user_config)
            except (json.JSONDecodeError, OSError):
                pass  # intentionally ignored

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self._config, f, indent=2)

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        self._config[key] = value

    def get_all(self) -> dict[str, Any]:
        return self._config.copy()

    def __repr__(self):
        return f"AMFConfig(path={self.config_path})"
