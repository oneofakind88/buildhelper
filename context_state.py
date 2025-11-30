from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, MutableMapping

from session_cache import SessionCache
from telemetry import TelemetryCollector


@dataclass
class ContextState(MutableMapping[str, Any]):
    """Typed wrapper around Click's context store."""

    config: Dict[str, Any] | None = field(default_factory=dict)
    env: str | None = None
    sessions: Dict[str, Any] = field(default_factory=dict)
    runner: Any | None = None
    workflow_state: Dict[str, Any] = field(default_factory=dict)
    verbose: bool = False
    quiet: bool = False
    session_cache: SessionCache = field(default_factory=SessionCache)
    telemetry: TelemetryCollector = field(default_factory=TelemetryCollector)
    initialized: bool = False

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __delitem__(self, key: str) -> None:
        if hasattr(self, key):
            setattr(self, key, None)
        else:  # pragma: no cover - defensive
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(
            [
                "config",
                "env",
                "sessions",
                "runner",
                "workflow_state",
                "verbose",
                "quiet",
                "session_cache",
                "telemetry",
                "initialized",
            ]
        )

    def __len__(self) -> int:
        return len(list(iter(self)))

    def ensure(self) -> "ContextState":
        """Compatibility helper mirroring ``ctx.ensure_object`` semantics."""

        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config,
            "env": self.env,
            "sessions": self.sessions,
            "runner": self.runner,
            "workflow_state": self.workflow_state,
            "verbose": self.verbose,
            "quiet": self.quiet,
            "session_cache": self.session_cache,
            "telemetry": self.telemetry,
            "initialized": self.initialized,
        }
