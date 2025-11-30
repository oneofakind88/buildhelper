import pathlib
from typing import Any, Dict, Mapping

import click
import yaml

from command_groups import register_command_groups
from context_state import ContextState
from logging_utils import configure_logging, get_logger
from runners import get_runner
from session_cache import SessionCache
from telemetry import TelemetryCollector


DEFAULT_ENV = "local"
DEFAULT_CONFIG_FILENAME = "config.yaml"


def _validate_config_shape(config: Mapping[str, Any]) -> None:
    if not isinstance(config, Mapping):
        raise click.ClickException("Config file must contain a YAML mapping")

    backends_section = config.get("backends")
    if backends_section is not None and not isinstance(backends_section, Mapping):
        raise click.ClickException("Config 'backends' section must be a mapping")

    backend_configs = config.get("backend_configs")
    if backend_configs is not None and not isinstance(backend_configs, Mapping):
        raise click.ClickException("Config 'backend_configs' section must be a mapping")

    envs_section = config.get("envs")
    if envs_section is not None and not isinstance(envs_section, Mapping):
        raise click.ClickException("Config 'envs' section must be a mapping")

    workflows_section = config.get("workflows")
    if workflows_section is not None and not isinstance(workflows_section, Mapping):
        raise click.ClickException("Config 'workflows' section must be a mapping")


def load_config(config_path: str) -> Dict[str, Any]:
    path = pathlib.Path(config_path)
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as config_file:
            data = yaml.safe_load(config_file) or {}
    except yaml.YAMLError as exc:
        raise click.ClickException(f"Failed to parse config file: {exc}") from exc

    _validate_config_shape(data)

    return data


def _default_config_path() -> pathlib.Path:
    return pathlib.Path.cwd() / DEFAULT_CONFIG_FILENAME


logger = get_logger(__name__)


@click.group(invoke_without_command=True)
@click.option("--verbose", is_flag=True, help="Enable verbose logging output")
@click.option("--quiet", is_flag=True, help="Reduce logging output to errors only")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    ctx.ensure_object(ContextState)
    state: ContextState = ctx.obj
    if state.initialized:
        return

    if verbose and quiet:
        raise click.ClickException("--verbose and --quiet are mutually exclusive")

    config_path = _default_config_path()
    configuration = load_config(str(config_path))
    configure_logging(verbose=verbose, quiet=quiet)
    logger.debug("Loaded configuration from %s", config_path)

    env = DEFAULT_ENV
    runner = get_runner(env, configuration)

    state.config = configuration
    state.env = env
    state.sessions = {}
    state.runner = runner
    state.workflow_state = {}
    state.verbose = verbose
    state.quiet = quiet
    state.session_cache = SessionCache.from_config(configuration)
    state.telemetry = TelemetryCollector()
    state.initialized = True


register_command_groups(cli)


if __name__ == "__main__":
    cli()
