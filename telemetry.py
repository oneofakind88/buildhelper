from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Dict, List, Optional

from logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class TelemetryEvent:
    name: str
    status: str
    duration_ms: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TelemetryCollector:
    """Capture command timings and failures."""

    def __init__(self) -> None:
        self.events: List[TelemetryEvent] = []

    @contextlib.contextmanager
    def track(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        start = time.perf_counter()
        try:
            yield
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            self.events.append(
                TelemetryEvent(
                    name=name,
                    status="error",
                    duration_ms=duration_ms,
                    error=str(exc),
                    metadata=metadata or {},
                )
            )
            logger.debug("Telemetry captured error for %s: %s", name, exc)
            raise
        else:
            duration_ms = (time.perf_counter() - start) * 1000
            self.events.append(
                TelemetryEvent(
                    name=name,
                    status="success",
                    duration_ms=duration_ms,
                    metadata=metadata or {},
                )
            )
            logger.debug("Telemetry recorded %s in %.2fms", name, duration_ms)

    def record_event(
        self, name: str, *, status: str, duration_ms: float, error: str | None = None
    ) -> None:
        self.events.append(
            TelemetryEvent(name=name, status=status, duration_ms=duration_ms, error=error)
        )


def telemetry_event(name: str):
    """Decorator to capture telemetry around command execution."""

    def decorator(func):
        @wraps(func)
        def wrapper(ctx, *args, **kwargs):
            collector = getattr(getattr(ctx, "obj", None), "telemetry", None)
            start = time.perf_counter()
            try:
                result = func(ctx, *args, **kwargs)
            except Exception:
                if collector is not None:
                    duration_ms = (time.perf_counter() - start) * 1000
                    collector.record_event(name, status="error", duration_ms=duration_ms)
                raise
            else:
                if collector is not None:
                    duration_ms = (time.perf_counter() - start) * 1000
                    collector.record_event(name, status="success", duration_ms=duration_ms)
                return result

        return wrapper

    return decorator
