import functools
import pathlib
from typing import Any, Callable, Dict

import click
import yaml

from backends import get_backend


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


def ensure_session(domain: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Ensure a connected backend session exists for ``domain``.

    The decorator checks ``ctx.obj["sessions"][domain]``. When missing, it
    resolves the backend name from ``ctx.obj["config"]["backends"][domain]``,
    instantiates it via :func:`backends.get_backend`, calls ``connect()``, and
    stores the connected backend on the context for reuse.
    """

    def decorator(command: Callable[..., Any]) -> Callable[..., Any]:
        @click.pass_context
        @functools.wraps(command)
        def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
            ctx.ensure_object(dict)
            sessions = ctx.obj.setdefault("sessions", {})

            if domain not in sessions:
                try:
                    backend_name = ctx.obj.get("config", {})["backends"][domain]
                except KeyError as exc:
                    raise click.ClickException(
                        f"No backend configured for domain '{domain}'"
                    ) from exc

                backend = get_backend(
                    domain,
                    backend_name,
                    config=ctx.obj.get("config", {}),
                    env=ctx.obj.get("env"),
                )
                backend.connect()
                sessions[domain] = backend

            return command(ctx, *args, **kwargs)

        return wrapper

    return decorator


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


@scm.command()
@ensure_session("scm")
def sync(ctx: click.Context) -> None:
    backend = ctx.obj["sessions"]["scm"]
    result = backend.sync()
    if result is not None:
        click.echo(result)


@scm.command()
@ensure_session("scm")
def status(ctx: click.Context) -> None:
    backend = ctx.obj["sessions"]["scm"]
    result = backend.status()
    if result is not None:
        click.echo(result)


@scm.command()
@ensure_session("scm")
@click.option("--message", "message", default="", show_default=True, help="Submission message")
def submit(ctx: click.Context, message: str) -> None:
    backend = ctx.obj["sessions"]["scm"]
    result = backend.submit(message=message)
    if result is not None:
        click.echo(result)


@analysis.command()
@ensure_session("analysis")
def scan(ctx: click.Context) -> None:
    backend = ctx.obj["sessions"]["analysis"]
    result = backend.scan()
    if result is not None:
        click.echo(result)


@analysis.command()
@ensure_session("analysis")
@click.option(
    "--format",
    "format_",
    default="text",
    show_default=True,
    help="Output format for the analysis report",
)
def report(ctx: click.Context, format_: str) -> None:
    backend = ctx.obj["sessions"]["analysis"]
    result = backend.report(format=format_)
    if result is not None:
        click.echo(result)


@review.command()
@ensure_session("review")
@click.option("--subject", default="", show_default=True)
def create(ctx: click.Context, subject: str) -> None:
    backend = ctx.obj["sessions"]["review"]
    result = backend.create_review(subject=subject)
    if result is not None:
        click.echo(result)


@review.command()
@ensure_session("review")
@click.option("--body", default="", show_default=True)
def comment(ctx: click.Context, body: str) -> None:
    backend = ctx.obj["sessions"]["review"]
    result = backend.comment(body=body)
    if result is not None:
        click.echo(result)


@review.command()
@ensure_session("review")
@click.option("--message", default="", show_default=True)
def approve(ctx: click.Context, message: str) -> None:
    backend = ctx.obj["sessions"]["review"]
    result = backend.approve(message=message)
    if result is not None:
        click.echo(result)


if __name__ == "__main__":
    cli()
