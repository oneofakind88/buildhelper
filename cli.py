import pathlib
from typing import Any, Dict

import click
import yaml


DEFAULT_ENV = "local"
DEFAULT_CONFIG_PATH = "config.yaml"


def load_config(config_path: str) -> Dict[str, Any]:
    path = pathlib.Path(config_path)
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as config_file:
            data = yaml.safe_load(config_file) or {}
    except yaml.YAMLError as exc:
        raise click.ClickException(f"Failed to parse config file: {exc}") from exc

    if not isinstance(data, dict):
        raise click.ClickException("Config file must contain a YAML mapping")

    return data


def derive_runner(env: str) -> str:
    return f"runner_{env}"


@click.group(invoke_without_command=True)
@click.option("--env", default=DEFAULT_ENV, show_default=True, help="Execution environment")
@click.option(
    "--config",
    default=DEFAULT_CONFIG_PATH,
    show_default=True,
    type=click.Path(exists=False, dir_okay=False, resolve_path=True, path_type=str),
    help="Path to configuration file",
)
@click.option("--verbose/--quiet", default=False, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, env: str, config: str, verbose: bool) -> None:
    configuration = load_config(config)
    ctx.ensure_object(dict)
    ctx.obj = {
        "config": configuration,
        "env": env,
        "sessions": {},
        "runner": derive_runner(env),
        "workflow_state": {},
        "verbose": verbose,
    }


@cli.group()
@click.pass_context
def scm(ctx: click.Context) -> None:
    ctx.ensure_object(dict)


@cli.group()
@click.pass_context
def analysis(ctx: click.Context) -> None:
    ctx.ensure_object(dict)


@cli.group()
@click.pass_context
def review(ctx: click.Context) -> None:
    ctx.ensure_object(dict)


@cli.group()
@click.pass_context
def workflow(ctx: click.Context) -> None:
    ctx.ensure_object(dict)


if __name__ == "__main__":
    cli()
