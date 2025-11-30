from __future__ import annotations

import pathlib
from typing import Any, Dict, Mapping

import yaml

DEFAULT_CACHE_PATH = pathlib.Path.home() / ".buildhelper" / "sessions.yaml"


class SessionCache:
    """Lightweight persistent cache for backend session metadata."""

    def __init__(self, path: pathlib.Path | str | None = None) -> None:
        self.path = pathlib.Path(path) if path else DEFAULT_CACHE_PATH
        self._data: Dict[str, Any] = {}
        self._loaded = False

    @classmethod
    def from_config(cls, config: Mapping[str, Any] | None) -> "SessionCache":
        cache_cfg = (config or {}).get("cache", {})
        path = cache_cfg.get("sessions_path")
        return cls(path)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        self._loaded = True
        if not self.path.exists():
            return

        try:
            content = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
            if isinstance(content, dict):
                self._data = content
        except Exception:  # pragma: no cover - defensive
            self._data = {}

    def get(self, domain: str, default: Any | None = None) -> Any:
        self._ensure_loaded()
        return self._data.get(domain, default)

    def set(self, domain: str, payload: Any) -> None:
        self._ensure_loaded()
        self._data[domain] = payload

    def persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as cache_file:
            cache_file.write(yaml.safe_dump(self._data))
