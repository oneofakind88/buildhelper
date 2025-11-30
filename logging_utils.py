"""Lightweight logging helpers for the CLI commands.

The module centralizes logging configuration so that the ``--verbose/--quiet``
flag behaves consistently across commands. ``configure_logging`` is idempotent
and safe to call multiple times because it only attaches handlers when none are
configured yet.
"""

from __future__ import annotations

import logging

DEFAULT_LOG_FORMAT = "%(levelname)s %(name)s: %(message)s"


def configure_logging(*, verbose: bool = False, quiet: bool = False) -> None:
    """Configure the root logger based on verbosity flags."""

    level = logging.INFO

    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.ERROR

    if not logging.getLogger().handlers:
        logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT)
    else:  # pragma: no cover - defensive branch for embedded runtimes
        logging.getLogger().setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""

    return logging.getLogger(name)
