from __future__ import annotations

from typing import Any

from ..base import require_connection
from ..registry import register_backend
from ..review import ReviewBackend


class PerforceSwarmReviewBackend(ReviewBackend):
    """Dummy Perforce Swarm review backend."""

    def connect(self) -> None:
        self.config.setdefault("host", "https://swarm.example.com")
        self.config.setdefault("project", "demo")
        super().connect()

    @require_connection
    def create_review(self, *args: Any, **kwargs: Any) -> str:
        subject = kwargs.get("subject", "")
        return f"swarm create review in project {self.config['project']} with subject: {subject}"

    @require_connection
    def comment(self, *args: Any, **kwargs: Any) -> str:
        body = kwargs.get("body", "")
        return f"swarm comment: {body}"

    @require_connection
    def approve(self, *args: Any, **kwargs: Any) -> str:
        message = kwargs.get("message", "")
        return f"swarm approve review with message: {message}"


register_backend("review", "perforce-swarm", PerforceSwarmReviewBackend)
