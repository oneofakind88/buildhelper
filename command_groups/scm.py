import click

from command_groups.common import ensure_session
from context_state import ContextState
from telemetry import telemetry_event


@click.group()
@click.pass_context
def scm(ctx: click.Context) -> None:
    ctx.ensure_object(ContextState)


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
