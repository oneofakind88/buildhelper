from __future__ import annotations

from abc import abstractmethod
from typing import Any

from .base import BaseBackend


class AnalysisBackend(BaseBackend):
    """Interface for analysis backends."""

    @abstractmethod
    def scan(self) -> Any:  # pragma: no cover - interface only
        """Run an analysis scan."""

    @abstractmethod
    def report(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - interface only
        """Generate and return an analysis report."""
