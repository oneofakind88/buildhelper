from __future__ import annotations

import shlex
import subprocess
from abc import ABC, abstractmethod
from typing import Any, Iterable, Mapping, Sequence

import click


class Runner(ABC):
    """Interface for executing shell commands in different environments."""

    def __init__(self, env: str) -> None:
        self.env = env

    @abstractmethod
    def run_command(self, cmd: str | Iterable[str], **kwargs: Any) -> subprocess.CompletedProcess:
        """Execute ``cmd`` and return the :class:`subprocess.CompletedProcess`."""


class LocalRunner(Runner):
    """Run commands directly on the host."""

    def __init__(self, env: str, default_kwargs: Mapping[str, Any] | None = None) -> None:
        super().__init__(env)
        self.default_kwargs = dict(default_kwargs or {})

    def run_command(self, cmd: str | Iterable[str], **kwargs: Any) -> subprocess.CompletedProcess:
        merged_kwargs = {"check": True, "text": True, **self.default_kwargs, **kwargs}
        command = _normalize_cmd(cmd)
        return subprocess.run(command, **merged_kwargs)


class DockerRunner(Runner):
    """Run commands inside a Docker container using ``docker exec``."""

    def __init__(self, env: str, container: str | None = None, docker_bin: str = "docker", default_kwargs: Mapping[str, Any] | None = None) -> None:
        super().__init__(env)
        self.container = container or "app"
        self.docker_bin = docker_bin
        self.default_kwargs = dict(default_kwargs or {})

    def run_command(self, cmd: str | Iterable[str], **kwargs: Any) -> subprocess.CompletedProcess:
        merged_kwargs = {"check": True, "text": True, **self.default_kwargs, **kwargs}
        command = [self.docker_bin, "exec", self.container, *_normalize_cmd(cmd)]
        return subprocess.run(command, **merged_kwargs)


class K8sRunner(Runner):
    """Run commands inside a Kubernetes pod using ``kubectl exec``."""

    def __init__(
        self,
        env: str,
        pod: str | None = None,
        namespace: str | None = None,
        kubectl_bin: str = "kubectl",
        default_kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(env)
        self.pod = pod or "app"
        self.namespace = namespace
        self.kubectl_bin = kubectl_bin
        self.default_kwargs = dict(default_kwargs or {})

    def run_command(self, cmd: str | Iterable[str], **kwargs: Any) -> subprocess.CompletedProcess:
        merged_kwargs = {"check": True, "text": True, **self.default_kwargs, **kwargs}
        command: list[str] = [self.kubectl_bin, "exec", self.pod, "--", *_normalize_cmd(cmd)]

        if self.namespace:
            command = [self.kubectl_bin, "-n", self.namespace, "exec", self.pod, "--", *_normalize_cmd(cmd)]

        return subprocess.run(command, **merged_kwargs)


def _normalize_cmd(cmd: str | Iterable[str]) -> Sequence[str]:
    if isinstance(cmd, str):
        return tuple(shlex.split(cmd))

    return tuple(cmd)


def get_runner(env: str, config: Mapping[str, Any] | None = None) -> Runner:
    """Instantiate a runner based on the requested environment."""

    env_config = (config or {}).get("envs", {}).get(env, {}).get("runner", {})
    runner_type = env_config.get("type", env)

    if runner_type == "local":
        return LocalRunner(env, default_kwargs=env_config)

    if runner_type == "docker":
        default_kwargs = {k: v for k, v in env_config.items() if k not in {"container", "docker_bin"}}
        return DockerRunner(
            env,
            container=env_config.get("container"),
            docker_bin=env_config.get("docker_bin", "docker"),
            default_kwargs=default_kwargs,
        )

    if runner_type in {"k8s", "kubernetes"}:
        default_kwargs = {k: v for k, v in env_config.items() if k not in {"pod", "namespace", "kubectl_bin"}}
        return K8sRunner(
            env,
            pod=env_config.get("pod"),
            namespace=env_config.get("namespace"),
            kubectl_bin=env_config.get("kubectl_bin", "kubectl"),
            default_kwargs=default_kwargs,
        )

    if env_config:
        raise click.ClickException(f"Unknown environment '{runner_type}'")

    return LocalRunner(env)
