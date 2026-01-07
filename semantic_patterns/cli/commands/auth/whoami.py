"""Auth whoami command for semantic-patterns."""

from __future__ import annotations

import click
from rich.console import Console

from semantic_patterns.cli import RichCommand
from semantic_patterns.cli.commands.auth.status import get_github_username

console = Console()


@click.command(cls=RichCommand)
def whoami() -> None:
    """Show current authenticated user identity.

    Examples:

        # Show who you're authenticated as
        sp auth whoami
    """
    from semantic_patterns.credentials import CredentialType, get_credential_store

    store = get_credential_store(console)

    console.print()
    console.print("[bold]Current Identity[/bold]")
    console.print()

    # GitHub
    github_token = store.get(CredentialType.GITHUB, prompt_if_missing=False)
    if github_token:
        try:
            username = get_github_username(github_token)
            console.print(f"GitHub:  @{username}")
        except Exception:
            console.print(
                "GitHub:  [yellow]Unable to verify (token may be invalid)[/yellow]"
            )
    else:
        console.print("GitHub:  [dim]Not authenticated[/dim]")

    # Looker
    looker_client_id = store.get("looker-client-id", prompt_if_missing=False)
    if looker_client_id:
        console.print(f"Looker:  {looker_client_id[:10]}...")
    else:
        console.print("Looker:  [dim]Not authenticated[/dim]")

    console.print()
