import click

from command_groups.common import ensure_session
from context_state import ContextState
from telemetry import telemetry_event


@click.group()
@click.pass_context
def analysis(ctx: click.Context) -> None:
    ctx.ensure_object(ContextState)


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
