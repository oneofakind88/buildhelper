from __future__ import annotations

from abc import ABC
from typing import Any, Mapping


class BaseBackend(ABC):
    """Base class for all backend implementations."""

    def __init__(self, name: str, config: Mapping[str, Any] | None = None, env: str | None = None) -> None:
        self.name = name
        self.config = dict(config or {})
        self.env = env

    def connect(self) -> None:
        """Establish a connection to the backend.

        Subclasses may override this method to perform setup such as
        authentication or network handshakes. The default implementation is a
        no-op to keep simple backends lightweight.
        """

        return None
