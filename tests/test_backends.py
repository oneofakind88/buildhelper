import click
import pytest

from backends import (
    BACKEND_REGISTRY,
    AnalysisBackend,
    ReviewBackend,
    SCMBackend,
    get_backend,
    register_backend,
)


@pytest.fixture(autouse=True)
def reset_registry(monkeypatch):
    monkeypatch.setattr(
        "backends.BACKEND_REGISTRY", {"scm": {}, "analysis": {}, "review": {}}
    )


class DummySCM(SCMBackend):
    def sync(self):
        return "synced"

    def status(self):
        return {"state": "clean", "config": self.config}

    def submit(self, message: str = ""):
        return {"submitted": message}


class DummyAnalysis(AnalysisBackend):
    def scan(self):
        return {"results": [], "env": self.env}

    def report(self, format: str = "text"):
        return {"report": format}


class DummyReview(ReviewBackend):
    def create_review(self, *args, **kwargs):
        return {"review": True, "args": args, "kwargs": kwargs}

    def comment(self, *args, **kwargs):
        return {"commented": True, "args": args, "kwargs": kwargs}

    def approve(self, *args, **kwargs):
        return {"approved": True, "args": args, "kwargs": kwargs}


def test_registers_and_returns_backend_with_env_overrides():
    register_backend("scm", "dummy", DummySCM)
    config = {
        "backend_configs": {"dummy": {"token": "base", "url": "http://example"}},
        "envs": {"prod": {"backend_configs": {"dummy": {"token": "override"}}}},
    }

    backend = get_backend("scm", "dummy", config=config, env="prod")

    assert isinstance(backend, DummySCM)
    assert backend.config == {"token": "override", "url": "http://example"}
    assert backend.env == "prod"


def test_get_backend_defaults_to_base_config_when_no_env():
    register_backend("analysis", "dummy", DummyAnalysis)
    config = {"backend_configs": {"dummy": {"level": "info"}}}

    backend = get_backend("analysis", "dummy", config=config)

    assert isinstance(backend, DummyAnalysis)
    assert backend.config == {"level": "info"}
    assert backend.env is None


def test_get_backend_raises_for_unknown_backend():
    with pytest.raises(click.ClickException):
        get_backend("review", "unknown", config={}, env="local")


def test_backend_methods_are_callable():
    register_backend("review", "dummy", DummyReview)
    backend = get_backend("review", "dummy", config={"backend_configs": {"dummy": {}}})

    assert backend.create_review(subject="demo") == {"review": True, "args": (), "kwargs": {"subject": "demo"}}
    assert backend.comment(body="note") == {"commented": True, "args": (), "kwargs": {"body": "note"}}
    assert backend.approve(message="ship") == {"approved": True, "args": (), "kwargs": {"message": "ship"}}
