"""Auth clear command for semantic-patterns."""

from __future__ import annotations

import click
from rich.console import Console

from semantic_patterns.cli import RichCommand

console = Console()


@click.command(cls=RichCommand)
@click.argument("service", type=click.Choice(["github", "looker", "all"]))
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def clear(service: str, force: bool) -> None:
    """Clear stored credentials.

    SERVICE: Which credentials to clear (github, looker, or all)

    Examples:

        # Clear GitHub token
        sp auth clear github

        # Clear all credentials
        sp auth clear all
    """
    from semantic_patterns.credentials import CredentialType, get_credential_store

    store = get_credential_store(console)

    # Determine what to clear
    to_clear: list[tuple[str, str]] = []
    if service == "github" or service == "all":
        to_clear.append((CredentialType.GITHUB.value, "GitHub token"))
    if service == "looker" or service == "all":
        to_clear.append(("looker-client-id", "Looker client ID"))
        to_clear.append(("looker-client-secret", "Looker client secret"))

    # Confirm
    if not force:
        console.print()
        console.print("This will clear:")
        for _, label in to_clear:
            console.print(f"  \u2022 {label}")
        console.print()

        if not click.confirm("Continue?", default=False):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Clear credentials
    for key, label in to_clear:
        if store.delete(key):
            console.print(f"[green]\u2713[/green] Cleared {label}")
        else:
            console.print(f"[dim]\u25cb[/dim] {label} was not set")

    console.print()
    console.print("[dim]Run 'sp build' to re-authenticate[/dim]")
