from __future__ import annotations

from typing import Any

from ..registry import register_backend
from ..scm import SCMBackend
from ..base import require_connection


class GitBackend(SCMBackend):
    """Dummy Git SCM backend."""

    def connect(self) -> None:
        self.config.setdefault("repo", "https://example.com/demo.git")
        self.config.setdefault("branch", "main")
        super().connect()

    @require_connection
    def sync(self) -> str:
        return f"git pull {self.config['repo']} {self.config['branch']}"

    @require_connection
    def status(self) -> str:
        return "git status --short: clean"

    @require_connection
    def submit(self, *args: Any, **kwargs: Any) -> str:
        message = kwargs.get("message", "")
        return f"git push with commit message: {message}"


register_backend("scm", "git", GitBackend)
