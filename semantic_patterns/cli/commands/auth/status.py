"""Auth status command for semantic-patterns."""

from __future__ import annotations

import os

import click
from rich.console import Console

from semantic_patterns.cli import RichCommand

console = Console()


def get_github_username(token: str) -> str:
    """Fetch GitHub username from token.

    Args:
        token: GitHub personal access token

    Returns:
        The GitHub username

    Raises:
        Exception: If API call fails
    """
    import httpx

    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        response.raise_for_status()
        data: dict[str, str] = response.json()
        return data["login"]


@click.command(cls=RichCommand)
def status() -> None:
    """Show configured credentials and their status."""
    import httpx

    from semantic_patterns.credentials import CredentialType, get_credential_store

    store = get_credential_store(console)

    console.print()
    console.print("[bold]Credential Status[/bold]")
    console.print()

    # GitHub
    github_token = store.get(CredentialType.GITHUB, prompt_if_missing=False)
    if github_token:
        # Try to fetch user info
        try:
            username = get_github_username(github_token)
            console.print("[green]\u2713[/green] GitHub:      Configured")
            console.print(f"             User: @{username}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                console.print("[red]\u2717[/red] GitHub:      Invalid token")
            else:
                console.print(
                    f"[yellow]\u26a0[/yellow] GitHub:      Error (HTTP {e.response.status_code})"
                )
        except httpx.TimeoutException:
            console.print(
                "[yellow]\u26a0[/yellow] GitHub:      Configured (network timeout during verification)"
            )
        except Exception:
            console.print(
                "[yellow]\u26a0[/yellow] GitHub:      Configured (unable to verify)"
            )
    else:
        console.print("[dim]\u25cb[/dim] GitHub:      Not configured")

    # Check env var override
    if os.environ.get("GITHUB_TOKEN"):
        console.print(
            "             [yellow]Note: GITHUB_TOKEN env var will override keychain[/yellow]"
        )

    console.print()

    # Looker
    looker_client_id = store.get("looker-client-id", prompt_if_missing=False)
    looker_client_secret = store.get("looker-client-secret", prompt_if_missing=False)

    if looker_client_id and looker_client_secret:
        console.print("[green]\u2713[/green] Looker:      Configured")
        console.print(f"             Client ID: {looker_client_id[:10]}...")
    elif looker_client_id or looker_client_secret:
        console.print(
            "[yellow]\u26a0[/yellow] Looker:      Partially configured (missing ID or secret)"
        )
    else:
        console.print("[dim]\u25cb[/dim] Looker:      Not configured")

    # Check env var overrides
    if os.environ.get("LOOKER_CLIENT_ID") or os.environ.get("LOOKER_CLIENT_SECRET"):
        console.print(
            "             [yellow]Note: LOOKER_* env vars will override keychain[/yellow]"
        )

    console.print()
