import subprocess

import click
import pytest

from runners import DockerRunner, K8sRunner, LocalRunner, get_runner


def test_local_runner_invokes_subprocess(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return "ok"

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = LocalRunner("local")
    result = runner.run_command("echo hello", capture_output=True)

    assert result == "ok"
    assert calls == [(("echo", "hello"), {"check": True, "text": True, "capture_output": True})]


def test_docker_runner_builds_exec_command(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return "docker"

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = DockerRunner("docker", container="builder")
    result = runner.run_command(["ls", "/app"])

    assert result == "docker"
    assert calls == [
        (["docker", "exec", "builder", "ls", "/app"], {"check": True, "text": True}),
    ]


def test_k8s_runner_honors_namespace(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return "k8s"

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = K8sRunner("k8s", pod="api", namespace="demo")
    result = runner.run_command("whoami")

    assert result == "k8s"
    assert calls == [
        (["kubectl", "-n", "demo", "exec", "api", "--", "whoami"], {"check": True, "text": True}),
    ]


def test_get_runner_selects_by_env():
    assert isinstance(get_runner("local", {}), LocalRunner)
    assert isinstance(get_runner("docker", {}), DockerRunner)
    assert isinstance(get_runner("k8s", {}), K8sRunner)


def test_get_runner_unknown_env_raises():
    config = {"envs": {"unknown": {"runner": {"type": "mystery"}}}}

    with pytest.raises(click.ClickException):
        get_runner("unknown", config)

