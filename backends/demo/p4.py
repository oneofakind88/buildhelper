from __future__ import annotations

from typing import Any

from ..registry import register_backend
from ..scm import SCMBackend
from ..base import require_connection


class P4Backend(SCMBackend):
    """Dummy Perforce SCM backend."""

    def connect(self) -> None:
        self.config.setdefault("server", "perforce:1666")
        self.config.setdefault("workspace", "demo-workspace")
        super().connect()

    @require_connection
    def sync(self) -> str:
        return f"p4 sync against {self.config['server']} in workspace {self.config['workspace']}"

    @require_connection
    def status(self) -> str:
        return "p4 opened files: none (clean workspace)"

    @require_connection
    def submit(self, *args: Any, **kwargs: Any) -> str:
        message = kwargs.get("message", "")
        return f"p4 submit from {self.config['workspace']} with message: {message}"


register_backend("scm", "p4", P4Backend)
