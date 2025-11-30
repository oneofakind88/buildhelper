import click
from click.testing import CliRunner
import pytest
import yaml

from cli import cli, derive_runner, load_config


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
