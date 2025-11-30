from .analysis import analysis
from .review import review
from .scm import scm
from .workflow import workflow

__all__ = ["analysis", "review", "scm", "workflow"]


def register_command_groups(cli) -> None:
    cli.add_command(scm)
    cli.add_command(analysis)
    cli.add_command(review)
    cli.add_command(workflow)
