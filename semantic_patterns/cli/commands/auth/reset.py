"""Auth reset command for semantic-patterns."""

from __future__ import annotations

import click
from rich.console import Console

from semantic_patterns.cli import RichCommand
from semantic_patterns.cli.commands.auth.clear import clear

console = Console()


@click.command(cls=RichCommand)
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def reset(ctx: click.Context, force: bool) -> None:
    """Clear all stored credentials (fresh start).

    Examples:

        # Clear all credentials
        sp auth reset
    """
    # Invoke the clear command with service="all"
    ctx.invoke(clear, service="all", force=force)
