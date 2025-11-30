import functools
import pathlib
import shlex
from typing import Any, Callable, Dict, Iterable, List, Mapping

from logging_utils import configure_logging, get_logger

import click
import yaml

from backends import get_backend
from context_state import ContextState
from plugins import discover_plugins
from runners import get_runner
from session_cache import SessionCache
from telemetry import TelemetryCollector, telemetry_event


DEFAULT_ENV = "local"
DEFAULT_CONFIG_PATH = "config.yaml"


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


logger = get_logger(__name__)


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
            ctx.ensure_object(ContextState)
            state: ContextState = ctx.obj
            sessions = state.sessions

            if domain not in sessions:
                config = state.config or {}
                backends_config = config.get("backends")

                if backends_config is None:
                    raise click.ClickException(
                        "Config is missing required 'backends' section"
                    )

                if not isinstance(backends_config, dict):
                    raise click.ClickException(
                        "Config 'backends' section must be a mapping"
                    )

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
                        logger.debug(
                            "Restored cached session for domain '%s'", domain
                        )
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
                logger.debug(
                    "Connected backend '%s' for domain '%s'", backend_name, domain
                )

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
@click.option("--verbose", is_flag=True, help="Enable verbose logging output")
@click.option("--quiet", is_flag=True, help="Reduce logging output to errors only")
@click.pass_context
def cli(ctx: click.Context, env: str, config: str, verbose: bool, quiet: bool) -> None:
    ctx.ensure_object(dict)
    if ctx.obj:
        return

    if verbose and quiet:
        raise click.ClickException("--verbose and --quiet are mutually exclusive")

    configuration = load_config(config)
    configure_logging(verbose=verbose, quiet=quiet)
    logger.debug("Loaded configuration from %s", config)
    runner = get_runner(env, configuration)
    ctx.obj = {
        "config": configuration,
        "env": env,
        "sessions": {},
        "runner": runner,
        "workflow_state": {},
        "verbose": verbose,
        "quiet": quiet,
    }


@cli.group()
@click.pass_context
def scm(ctx: click.Context) -> None:
    ctx.ensure_object(ContextState)


@cli.group()
@click.pass_context
def analysis(ctx: click.Context) -> None:
    ctx.ensure_object(ContextState)


@cli.group()
@click.pass_context
def review(ctx: click.Context) -> None:
    ctx.ensure_object(ContextState)


@cli.group()
@click.pass_context
def workflow(ctx: click.Context) -> None:
    ctx.ensure_object(ContextState)


@workflow.command("run")
@click.argument("name")
@click.option(
    "--continue-on-error",
    is_flag=True,
    help="Continue executing remaining steps even if a step fails",
)
@click.pass_context
def workflow_run(ctx: click.Context, name: str, continue_on_error: bool) -> None:
    state: ContextState = ctx.obj
    config = state.config or {}
    workflows = config.get("workflows", {})

    if not isinstance(workflows, dict):
        raise click.ClickException("Config 'workflows' section must be a mapping")

    if name not in workflows:
        raise click.ClickException(f"Workflow '{name}' is not defined in config")

    raw_steps = workflows[name]
    if not isinstance(raw_steps, list):
        raise click.ClickException("Workflow steps must be defined as a list")

    click.echo(f"[workflow] Running '{name}' with {len(raw_steps)} step(s)")
    failures = 0
    for index, raw_step in enumerate(raw_steps, start=1):
        step_args = _normalize_step(raw_step)
        if not step_args:
            continue

        try:
            with cli.make_context("cli", step_args, obj=ctx.obj) as step_ctx:
                with state.telemetry.track(f"workflow.step.{name}.{index}"):
                    cli.invoke(step_ctx)
        except click.ClickException as exc:
            failures += 1
            click.echo(
                f"Step '{' '.join(step_args)}' failed: {exc.format_message()}",
                err=True,
            )
            if not continue_on_error:
                raise
        except Exception as exc:  # pragma: no cover - safeguard for unexpected errors
            failures += 1
            click.echo(
                f"Step '{' '.join(step_args)}' failed: {exc}",
                err=True,
            )
            if not continue_on_error:
                raise click.ClickException(str(exc)) from exc

    if failures:
        raise click.ClickException(
            f"Workflow '{name}' completed with {failures} failed step(s)"
        )


def _normalize_step(step: Any) -> List[str]:
    if isinstance(step, str):
        return shlex.split(step)

    if isinstance(step, Iterable):
        return [str(part) for part in step]

    raise click.ClickException("Workflow steps must be strings or iterables of arguments")


@scm.command()
@ensure_session("scm")
@telemetry_event("scm.sync")
def sync(ctx: click.Context) -> None:
    click.echo("[scm] Executing sync")
    backend = ctx.obj["sessions"]["scm"]
    result = backend.sync()
    if result is not None:
        click.echo(result)


@scm.command()
@ensure_session("scm")
@telemetry_event("scm.status")
def status(ctx: click.Context) -> None:
    click.echo("[scm] Checking status")
    backend = ctx.obj["sessions"]["scm"]
    result = backend.status()
    if result is not None:
        click.echo(result)


@scm.command()
@ensure_session("scm")
@telemetry_event("scm.submit")
@click.option("--message", "message", default="", show_default=True, help="Submission message")
def submit(ctx: click.Context, message: str) -> None:
    click.echo(f"[scm] Submitting with message: {message}")
    backend = ctx.obj["sessions"]["scm"]
    result = backend.submit(message=message)
    if result is not None:
        click.echo(result)


@analysis.command()
@ensure_session("analysis")
@telemetry_event("analysis.scan")
def scan(ctx: click.Context) -> None:
    click.echo("[analysis] Running scan")
    backend = ctx.obj["sessions"]["analysis"]
    result = backend.scan()
    if result is not None:
        click.echo(result)


@analysis.command()
@ensure_session("analysis")
@telemetry_event("analysis.report")
@click.option(
    "--format",
    "format_",
    default="text",
    show_default=True,
    help="Output format for the analysis report",
)
def report(ctx: click.Context, format_: str) -> None:
    click.echo(f"[analysis] Generating report in {format_} format")
    backend = ctx.obj["sessions"]["analysis"]
    result = backend.report(format=format_)
    if result is not None:
        click.echo(result)


@review.command()
@ensure_session("review")
@telemetry_event("review.create")
@click.option("--subject", default="", show_default=True)
def create(ctx: click.Context, subject: str) -> None:
    click.echo(f"[review] Creating review with subject: {subject}")
    backend = ctx.obj["sessions"]["review"]
    result = backend.create_review(subject=subject)
    if result is not None:
        click.echo(result)


@review.command()
@ensure_session("review")
@telemetry_event("review.comment")
@click.option("--body", default="", show_default=True)
def comment(ctx: click.Context, body: str) -> None:
    click.echo("[review] Adding comment")
    backend = ctx.obj["sessions"]["review"]
    result = backend.comment(body=body)
    if result is not None:
        click.echo(result)


@review.command()
@ensure_session("review")
@telemetry_event("review.approve")
@click.option("--message", default="", show_default=True)
def approve(ctx: click.Context, message: str) -> None:
    click.echo("[review] Approving change")
    backend = ctx.obj["sessions"]["review"]
    result = backend.approve(message=message)
    if result is not None:
        click.echo(result)


if __name__ == "__main__":
    cli()
