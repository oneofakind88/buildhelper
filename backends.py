from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Dict, Mapping, MutableMapping, Type

import click


class BaseBackend(ABC):
    """Base class for all backend implementations."""

    def __init__(self, name: str, config: Mapping[str, Any] | None = None, env: str | None = None) -> None:
        self.name = name
        self.config: Dict[str, Any] = dict(config or {})
        self.env = env


class SCMBackend(BaseBackend):
    """Interface for source control management backends."""

    @abstractmethod
    def sync(self) -> Any:  # pragma: no cover - interface only
        """Synchronize the working tree."""

    @abstractmethod
    def status(self) -> Any:  # pragma: no cover - interface only
        """Return status information for the working tree."""


class AnalysisBackend(BaseBackend):
    """Interface for analysis backends."""

    @abstractmethod
    def scan(self) -> Any:  # pragma: no cover - interface only
        """Run an analysis scan."""


class ReviewBackend(BaseBackend):
    """Interface for review backends."""

    @abstractmethod
    def create_review(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - interface only
        """Create a review or review request."""

    @abstractmethod
    def comment(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - interface only
        """Create a comment on a review or change."""


BackendType = Type[BaseBackend]
BackendRegistry = MutableMapping[str, MutableMapping[str, BackendType]]


BACKEND_REGISTRY: BackendRegistry = {
    "scm": {},
    "analysis": {},
    "review": {},
}


def register_backend(domain: str, name: str, backend_cls: BackendType) -> None:
    """Register a backend implementation for a given domain."""

    if domain not in BACKEND_REGISTRY:
        BACKEND_REGISTRY[domain] = {}

    BACKEND_REGISTRY[domain][name] = backend_cls


def _lookup_config(config: Mapping[str, Any] | None, name: str, env: str | None = None) -> Dict[str, Any]:
    """Fetch backend config and merge environment overrides when present."""

    config = config or {}
    base_config = deepcopy(config.get("backend_configs", {}).get(name, {}))

    if env is None:
        return dict(base_config)

    env_overrides = config.get("envs", {}).get(env, {}).get("backend_configs", {}).get(name, {})

    return {**base_config, **env_overrides}


def get_backend(domain: str, name: str, config: Mapping[str, Any] | None = None, env: str | None = None) -> BaseBackend:
    """Instantiate a registered backend using configuration from ``backend_configs``.

    The ``config`` mapping should correspond to ``ctx.obj["config"]`` from the CLI
    layer. Base backend settings are read from ``backend_configs[name]`` and merged
    with ``envs[env]["backend_configs"][name]`` when an environment is provided.
    """

    try:
        backend_cls = BACKEND_REGISTRY[domain][name]
    except KeyError as exc:  # pragma: no cover - defensive error path
        raise click.ClickException(
            f"Backend '{name}' is not registered for domain '{domain}'"
        ) from exc

    backend_config = _lookup_config(config, name, env=env)

    return backend_cls(name=name, config=backend_config, env=env)
