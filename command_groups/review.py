import click

from command_groups.common import ensure_session
from context_state import ContextState
from telemetry import telemetry_event


@click.group()
@click.pass_context
def review(ctx: click.Context) -> None:
    ctx.ensure_object(ContextState)


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
