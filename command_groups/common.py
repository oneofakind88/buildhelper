from __future__ import annotations

import functools
import shlex
from typing import Any, Callable, Iterable, List, Mapping

import click

from backends import get_backend
from context_state import ContextState
from logging_utils import get_logger

logger = get_logger(__name__)


def ensure_session(domain: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Ensure a connected backend session exists for ``domain``."""

    def decorator(command: Callable[..., Any]) -> Callable[..., Any]:
        @click.pass_context
        @functools.wraps(command)
        def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
            ctx.ensure_object(ContextState)
            state: ContextState = ctx.obj
            sessions = state.sessions

            if domain not in sessions:
                config = state.config or {}
                backends_config = config.get("backends")

                if backends_config is None:
                    raise click.ClickException("Config is missing required 'backends' section")

                if not isinstance(backends_config, dict):
                    raise click.ClickException("Config 'backends' section must be a mapping")

                try:
                    backend_name = backends_config[domain]
                except KeyError as exc:
                    raise click.ClickException(
                        f"No backend configured for domain '{domain}'"
                    ) from exc

                backend = get_backend(
                    domain,
                    backend_name,
                    config=config,
                    env=state.env,
                )

                cached_session = state.session_cache.get(domain)
                if cached_session and hasattr(backend, "restore_session"):
                    try:
                        backend.restore_session(cached_session)
                        logger.debug("Restored cached session for domain '%s'", domain)
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.debug("Failed to restore cached session: %s", exc)

                try:
                    backend.connect()
                except click.ClickException:
                    raise
                except Exception as exc:
                    raise click.ClickException(
                        f"Failed to connect to backend '{backend_name}' for domain '{domain}': {exc}"
                    ) from exc

                if hasattr(backend, "export_session"):
                    try:
                        exported = backend.export_session()
                        state.session_cache.set(domain, exported)
                        state.session_cache.persist()
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.debug("Failed to export session for caching: %s", exc)

                sessions[domain] = backend
                logger.debug("Connected backend '%s' for domain '%s'", backend_name, domain)

            return command(ctx, *args, **kwargs)

        return wrapper

    return decorator


def normalize_step(step: Any) -> List[str]:
    if isinstance(step, str):
        return shlex.split(step)

    if isinstance(step, Iterable):
        return [str(part) for part in step]

    raise click.ClickException("Workflow steps must be strings or iterables of arguments")
