"""Auth command group for semantic-patterns.

Manages authentication credentials for GitHub and Looker integrations.
"""

from __future__ import annotations

import click
from rich.console import Console

from semantic_patterns.cli import RichGroup
from semantic_patterns.cli.commands.auth.clear import clear
from semantic_patterns.cli.commands.auth.reset import reset
from semantic_patterns.cli.commands.auth.status import status
from semantic_patterns.cli.commands.auth.test_cmd import test
from semantic_patterns.cli.commands.auth.whoami import whoami

console = Console()


@click.group(cls=RichGroup, invoke_without_command=True)
@click.pass_context
def auth(ctx: click.Context) -> None:
    """Manage authentication credentials.

    When called without a subcommand, displays credential status and available commands.

    ## Available Commands

    **status** - Show configured credentials and their status
    **test** - Test if credentials are valid
    **clear** - Clear stored credentials
    **reset** - Clear all stored credentials (fresh start)
    **whoami** - Show current authenticated user identity

    ## Quick Examples

    Check credential status:

        $ sp auth
        $ sp auth status

    Test GitHub credentials:

        $ sp auth test github

    Clear all credentials:

        $ sp auth clear all
    """
    # If no subcommand provided, run status and then show help
    if ctx.invoked_subcommand is None:
        ctx.invoke(status)
        console.print()
        console.print("[dim]Available commands:[/dim]")
        console.print(ctx.get_help())


# Register all subcommands
auth.add_command(status)
auth.add_command(test)
auth.add_command(clear)
auth.add_command(reset)
auth.add_command(whoami)

__all__ = [
    "auth",
    "clear",
    "reset",
    "status",
    "test",
    "whoami",
]
