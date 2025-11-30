from __future__ import annotations

from abc import abstractmethod
from typing import Any

from .base import BaseBackend


class ReviewBackend(BaseBackend):
    """Interface for review backends."""

    @abstractmethod
    def create_review(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - interface only
        """Create a review or review request."""

    @abstractmethod
    def comment(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - interface only
        """Create a comment on a review or change."""

    @abstractmethod
    def approve(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - interface only
        """Approve a review or change."""
