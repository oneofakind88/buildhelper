from __future__ import annotations

from abc import abstractmethod
from typing import Any

from .base import BaseBackend


class SCMBackend(BaseBackend):
    """Interface for source control management backends."""

    @abstractmethod
    def sync(self) -> Any:  # pragma: no cover - interface only
        """Synchronize the working tree."""

    @abstractmethod
    def status(self) -> Any:  # pragma: no cover - interface only
        """Return status information for the working tree."""

    @abstractmethod
    def submit(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - interface only
        """Submit changes to the remote repository or review system."""
