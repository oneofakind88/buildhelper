import click
from click.testing import CliRunner
import pytest
import yaml

from backends import AnalysisBackend, SCMBackend, register_backend
from cli import cli, derive_runner, load_config


@pytest.fixture(autouse=True)
def reset_registry(monkeypatch):
    monkeypatch.setattr("backends.BACKEND_REGISTRY", {"scm": {}, "analysis": {}, "review": {}})


def test_load_config_missing_returns_empty(tmp_path):
    missing_config = tmp_path / "missing.yaml"
    assert load_config(str(missing_config)) == {}


def test_load_config_reads_mapping(tmp_path):
    config_data = {"key": "value", "nested": {"inner": 1}}
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    assert load_config(str(config_path)) == config_data


def test_load_config_rejects_non_mapping(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump([1, 2, 3]), encoding="utf-8")

    with pytest.raises(click.ClickException):
        load_config(str(config_path))


def test_derive_runner_uses_environment_name():
    assert derive_runner("prod") == "runner_prod"


def test_cli_initializes_context(tmp_path):
    config_data = {"feature": True}
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    with cli.make_context(
        "cli",
        ["--env", "staging", "--config", str(config_path), "--verbose"],
    ) as ctx:
        cli.invoke(ctx)
        assert ctx.obj == {
            "config": config_data,
            "env": "staging",
            "sessions": {},
            "runner": "runner_staging",
            "workflow_state": {},
            "verbose": True,
        }


def test_cli_group_invocation(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({}), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path)])

    assert result.exit_code == 0


def test_ensure_session_connects_and_stores_backend(tmp_path):
    class DummySCM(SCMBackend):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.connected = False

        def connect(self):
            self.connected = True

        def sync(self):
            return "synced"

        def status(self):
            return {"connected": self.connected}

    register_backend("scm", "dummy", DummySCM)
    config = {"backends": {"scm": "dummy"}, "backend_configs": {"dummy": {}}}
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "scm", "status"])

    assert result.exit_code == 0
    assert "{'connected': True}" in result.output


def test_ensure_session_raises_when_backend_missing(tmp_path):
    class DummyAnalysis(AnalysisBackend):
        def scan(self):
            return {"ran": True}

    register_backend("analysis", "dummy", DummyAnalysis)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({"backends": {}}), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "analysis", "scan"])

    assert result.exit_code != 0
    assert "No backend configured for domain" in result.output
