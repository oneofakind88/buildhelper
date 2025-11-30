from __future__ import annotations

from importlib import metadata
from typing import Iterable

from logging_utils import get_logger

logger = get_logger(__name__)


def discover_plugins(entry_point_group: str = "buildhelper.plugins") -> None:
    """Load plugin entry points to register external command groups/backends."""

    try:
        raw_entries = metadata.entry_points()
        if hasattr(raw_entries, "select"):
            entries: Iterable = raw_entries.select(group=entry_point_group)
        else:  # pragma: no cover - compatibility for Python<3.10
            entries = raw_entries.get(entry_point_group, [])
    except Exception:  # pragma: no cover - defensive for older Python versions
        entries = []

    for entry in entries:
        try:
            loader = entry.load()
            loader()
            logger.debug("Loaded plugin '%s'", getattr(entry, "name", repr(entry)))
        except Exception as exc:  # pragma: no cover - plugin isolation
            logger.debug("Failed to load plugin '%s': %s", getattr(entry, "name", entry), exc)
