import click

from command_groups.common import normalize_step
from context_state import ContextState


@click.group()
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

    root_command = ctx.find_root().command

    click.echo(f"[workflow] Running '{name}' with {len(raw_steps)} step(s)")
    failures = 0
    for index, raw_step in enumerate(raw_steps, start=1):
        step_args = normalize_step(raw_step)
        if not step_args:
            continue

        try:
            with root_command.make_context("cli", step_args, obj=ctx.obj) as step_ctx:
                with state.telemetry.track(f"workflow.step.{name}.{index}"):
                    root_command.invoke(step_ctx)
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
