"""Thin YAML config wrapper (application preferences only, no business data)."""
from __future__ import annotations

import os
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - guarded per spec §4
    yaml = None

DEFAULTS: dict[str, Any] = {
    "last_workspace": None,
    "recent_workspaces": [],
    "window": [900, 600],
    "reopen_last": True,
    "toolbar_style": "beside",  # "beside" | "below"
    "ui_backend": "gtk3",       # only gtk3 implemented at this stage
    "skin_tone": "none",
    "emoji_block": "favourites",
    "profile": None,
    "include_disclaimer": True,
}

_VALID_TOOLBAR = {"beside", "below"}
_VALID_BACKEND = {"gtk3", "gtk4"}


def _config_dir() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "qdvc-nicemail")


def _config_path() -> str:
    return os.path.join(_config_dir(), "config.yml")


class Config:
    """get(key, default) / set(key, value) over DEFAULTS; no schema migration."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        path = _config_path()
        data: dict[str, Any] = {}
        if yaml is not None and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    loaded = yaml.safe_load(fh)
                if isinstance(loaded, dict):
                    data = loaded
            except Exception:
                data = {}
        self._data = data

    def save(self) -> None:
        if yaml is None:
            return
        d = _config_dir()
        os.makedirs(d, exist_ok=True)
        tmp = _config_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self._data, fh, default_flow_style=False, allow_unicode=True)
        os.replace(tmp, _config_path())

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._data:
            return self._data[key]
        if default is not None:
            return default
        return DEFAULTS.get(key)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    # ---- validated accessors ---------------------------------------------
    @property
    def toolbar_style(self) -> str:
        v = str(self.get("toolbar_style", "beside")).lower()
        return v if v in _VALID_TOOLBAR else "beside"

    @property
    def ui_backend(self) -> str:
        v = str(self.get("ui_backend", "gtk3")).lower()
        return v if v in _VALID_BACKEND else "gtk3"
