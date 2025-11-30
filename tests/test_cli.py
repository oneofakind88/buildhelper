import click
from click.testing import CliRunner
import pytest
import yaml

from backends import AnalysisBackend, ReviewBackend, SCMBackend, register_backend
from cli import cli, load_config
from runners import LocalRunner


@pytest.fixture(autouse=True)
def reset_registry(monkeypatch):
    monkeypatch.setattr("backends.BACKEND_REGISTRY", {"scm": {}, "analysis": {}, "review": {}})


@pytest.fixture
def restore_commands():
    original_commands = dict(cli.commands)
    yield
    cli.commands.clear()
    cli.commands.update(original_commands)


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


def test_cli_initializes_context(tmp_path):
    config_data = {"feature": True}
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    with cli.make_context(
        "cli",
        ["--env", "staging", "--config", str(config_path), "--verbose"],
    ) as ctx:
        cli.invoke(ctx)
        assert ctx.obj["config"] == config_data
        assert ctx.obj["env"] == "staging"
        assert ctx.obj["sessions"] == {}
        assert isinstance(ctx.obj["runner"], LocalRunner)
        assert ctx.obj["workflow_state"] == {}
        assert ctx.obj["verbose"] is True


def test_cli_group_invocation(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({}), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path)])

    assert result.exit_code == 0


def test_cli_selects_runner_for_environment(monkeypatch, tmp_path):
    config_data = {"envs": {"staging": {"runner": {"type": "local", "custom": True}}}}
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    created_runners = []

    def fake_get_runner(env, config):
        runner = object()
        created_runners.append((env, config, runner))
        return runner

    monkeypatch.setattr("cli.get_runner", fake_get_runner)

    runner = CliRunner()
    result = runner.invoke(cli, ["--env", "staging", "--config", str(config_path)])

    assert result.exit_code == 0
    assert created_runners == [("staging", config_data, created_runners[0][2])]


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

        def submit(self, message: str = ""):
            return {"submitted": True, "message": message}

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

        def report(self, format: str = "text"):
            return {"format": format}

    register_backend("analysis", "dummy", DummyAnalysis)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({"backends": {}}), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "analysis", "scan"])

    assert result.exit_code != 0
    assert "No backend configured for domain" in result.output


def test_ensure_session_reports_missing_backends_section(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({}), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "scm", "status"])

    assert result.exit_code != 0
    assert "missing required 'backends' section" in result.output


def test_ensure_session_rejects_non_mapping_backends(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({"backends": []}), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "scm", "status"])

    assert result.exit_code != 0
    assert "must be a mapping" in result.output


def test_ensure_session_calls_backend_connect_and_command(monkeypatch, tmp_path):
    class StubBackend:
        def __init__(self):
            self.connect_calls = 0
            self.status_calls = 0

        def connect(self):
            self.connect_calls += 1

        def status(self):
            self.status_calls += 1
            return "stub-status"

    backend_instances = []

    def fake_get_backend(domain, name, config=None, env=None):
        backend = StubBackend()
        backend_instances.append((domain, name, config, env, backend))
        return backend

    monkeypatch.setattr("cli.get_backend", fake_get_backend)

    config = {"backends": {"scm": "stub"}, "backend_configs": {"stub": {}}}
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["--env", "dev", "--config", str(config_path), "scm", "status"])

    assert result.exit_code == 0
    assert "stub-status" in result.output
    assert backend_instances[0][0:4] == ("scm", "stub", config, "dev")
    assert backend_instances[0][4].connect_calls == 1
    assert backend_instances[0][4].status_calls == 1


def test_ensure_session_wraps_connection_errors(tmp_path):
    class FailingSCM(SCMBackend):
        def connect(self):
            raise RuntimeError("unreachable host")

        def sync(self):
            return "nope"

        def status(self):
            return "nope"

        def submit(self, message: str = ""):
            return message

    register_backend("scm", "failing", FailingSCM)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"backends": {"scm": "failing"}, "backend_configs": {"failing": {}}}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "scm", "status"])

    assert result.exit_code != 0
    assert "Failed to connect to backend 'failing'" in result.output


def test_command_outputs_include_backend_results(tmp_path):
    class DummySCM(SCMBackend):
        def sync(self):
            return "synced"

        def status(self):
            return "clean"

        def submit(self, message: str = ""):
            return f"submitted:{message}"

    class DummyAnalysis(AnalysisBackend):
        def scan(self):
            return "scanned"

        def report(self, format: str = "text"):
            return f"report:{format}"

    class DummyReview(ReviewBackend):
        def create_review(self, *args, **kwargs):
            return {"review": kwargs}

        def comment(self, *args, **kwargs):
            return {"comment": kwargs}

        def approve(self, *args, **kwargs):
            return f"approved:{kwargs.get('message', '')}"

    register_backend("scm", "dummy", DummySCM)
    register_backend("analysis", "dummy", DummyAnalysis)
    register_backend("review", "dummy", DummyReview)

    config = {
        "backends": {"scm": "dummy", "analysis": "dummy", "review": "dummy"},
        "backend_configs": {"dummy": {}},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    runner = CliRunner()

    submit_result = runner.invoke(
        cli, ["--config", str(config_path), "scm", "submit", "--message", "ready"]
    )
    assert submit_result.exit_code == 0
    assert "submitted:ready" in submit_result.output

    report_result = runner.invoke(
        cli, ["--config", str(config_path), "analysis", "report", "--format", "json"]
    )
    assert report_result.exit_code == 0
    assert "report:json" in report_result.output

    approve_result = runner.invoke(
        cli, ["--config", str(config_path), "review", "approve", "--message", "ship"]
    )
    assert approve_result.exit_code == 0
    assert "approved:ship" in approve_result.output


def test_workflow_run_executes_steps(tmp_path, restore_commands):
    @click.command("remember")
    @click.pass_context
    def remember(ctx):
        ctx.obj["workflow_state"]["greeting"] = "hello"

    @click.command("recall")
    @click.pass_context
    def recall(ctx):
        click.echo(ctx.obj["workflow_state"].get("greeting"))

    cli.add_command(remember)
    cli.add_command(recall)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"workflows": {"demo": [["remember"], ["recall"]]}}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "workflow", "run", "demo"])

    assert result.exit_code == 0
    assert "hello" in result.output


def test_workflow_run_stops_on_error(tmp_path, restore_commands):
    @click.command("fail")
    def fail():
        raise click.ClickException("boom")

    @click.command("after")
    def after():
        click.echo("after")

    cli.add_command(fail)
    cli.add_command(after)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"workflows": {"demo": [["fail"], ["after"]]}}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "workflow", "run", "demo"])

    assert result.exit_code != 0
    assert "after" not in result.output
    assert "Step 'fail' failed" in result.output


def test_workflow_run_continues_when_requested(tmp_path, restore_commands):
    @click.command("fail")
    def fail():
        raise click.ClickException("boom")

    @click.command("after")
    def after():
        click.echo("after")

    cli.add_command(fail)
    cli.add_command(after)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"workflows": {"demo": [["fail"], ["after"]]}}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", str(config_path), "workflow", "run", "demo", "--continue-on-error"],
    )

    assert result.exit_code != 0
    assert "after" in result.output
    assert "completed with 1 failed step(s)" in result.output


def test_workflow_steps_share_runner(monkeypatch, tmp_path, restore_commands):
    class StubRunner:
        def __init__(self):
            self.calls = []

        def run_command(self, cmd):
            self.calls.append(cmd)
            return "ok"

    stub_runner = StubRunner()

    def fake_get_runner(env, config):
        return stub_runner

    monkeypatch.setattr("cli.get_runner", fake_get_runner)

    @click.command("run-shell")
    @click.pass_context
    def run_shell(ctx):
        click.echo(ctx.obj["runner"].run_command(["echo", "hello"]))

    cli.add_command(run_shell)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"workflows": {"demo": [["run-shell"], ["run-shell"]]}}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--config", str(config_path), "workflow", "run", "demo"])

    assert result.exit_code == 0
    assert stub_runner.calls == [["echo", "hello"], ["echo", "hello"]]
