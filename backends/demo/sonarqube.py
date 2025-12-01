from __future__ import annotations

from typing import Any

from ..analysis import AnalysisBackend
from ..base import require_connection
from ..registry import register_backend


class SonarqubeAnalysisBackend(AnalysisBackend):
    """Dummy SonarQube analysis backend."""

    def connect(self) -> None:
        self.config.setdefault("host", "https://sonarqube.example.com")
        self.config.setdefault("project", "demo-project")
        super().connect()

    @require_connection
    def scan(self) -> str:
        return f"sonarqube scan for project {self.config['project']} at {self.config['host']}"

    @require_connection
    def report(self, *args: Any, **kwargs: Any) -> str:
        format_ = kwargs.get("format", "text")
        return f"sonarqube report in {format_} for {self.config['project']}"


register_backend("analysis", "sonarqube", SonarqubeAnalysisBackend)
