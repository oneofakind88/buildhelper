from __future__ import annotations

from typing import Any

from ..analysis import AnalysisBackend
from ..base import require_connection
from ..registry import register_backend


class KlocworkAnalysisBackend(AnalysisBackend):
    """Dummy Klocwork analysis backend."""

    def connect(self) -> None:
        self.config.setdefault("host", "https://klocwork.example.com")
        self.config.setdefault("project", "demo-project")
        super().connect()

    @require_connection
    def scan(self) -> str:
        return f"klocwork scan for project {self.config['project']}"

    @require_connection
    def report(self, *args: Any, **kwargs: Any) -> str:
        format_ = kwargs.get("format", "text")
        return f"klocwork report in {format_} for {self.config['project']}"


register_backend("analysis", "klocwork", KlocworkAnalysisBackend)
