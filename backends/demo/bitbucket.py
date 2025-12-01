from __future__ import annotations

from typing import Any

from ..base import require_connection
from ..registry import register_backend
from ..review import ReviewBackend


class BitbucketReviewBackend(ReviewBackend):
    """Dummy Bitbucket review backend."""

    def connect(self) -> None:
        self.config.setdefault("host", "https://bitbucket.example.com")
        self.config.setdefault("project_key", "DEMO")
        super().connect()

    @require_connection
    def create_review(self, *args: Any, **kwargs: Any) -> str:
        subject = kwargs.get("subject", "")
        return f"bitbucket create PR in {self.config['project_key']} with subject: {subject}"

    @require_connection
    def comment(self, *args: Any, **kwargs: Any) -> str:
        body = kwargs.get("body", "")
        return f"bitbucket comment on PR: {body}"

    @require_connection
    def approve(self, *args: Any, **kwargs: Any) -> str:
        message = kwargs.get("message", "")
        return f"bitbucket approve PR with message: {message}"


register_backend("review", "bitbucket", BitbucketReviewBackend)
