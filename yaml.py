"""Minimal YAML support for environments without external dependencies.

This module provides a small subset of PyYAML's public API, limited to
`safe_load` and `safe_dump`, backed by JSON parsing/serialization. It supports
YAML content that is compatible with JSON syntax, which is sufficient for the
project's configuration needs in offline environments.
"""

from __future__ import annotations

import json
from typing import Any, IO


class YAMLError(Exception):
    """Raised when YAML content cannot be parsed."""


def _read_stream(stream: str | bytes | IO[str] | IO[bytes]) -> str:
    if hasattr(stream, "read"):
        return stream.read()  # type: ignore[no-any-return]

    if isinstance(stream, bytes):
        return stream.decode()

    return str(stream)


def safe_load(stream: str | bytes | IO[str] | IO[bytes]) -> Any:
    """Parse JSON-compatible YAML content."""

    content = _read_stream(stream)
    if content is None:
        return None

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:  # pragma: no cover - precise message unimportant
        raise YAMLError("Unable to parse YAML content as JSON-compatible text") from exc


def safe_dump(data: Any, **_: Any) -> str:
    """Serialize data to YAML (JSON-compatible) string."""

    return json.dumps(data, indent=2)
