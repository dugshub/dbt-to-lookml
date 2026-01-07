"""Auth test command for semantic-patterns."""

from __future__ import annotations

import traceback

import click
from rich.console import Console

from semantic_patterns.cli import RichCommand
from semantic_patterns.config import find_config, load_config

console = Console()


@click.command(cls=RichCommand, name="test")
@click.argument("service", type=click.Choice(["github", "looker"]))
@click.option("--debug", is_flag=True, help="Show detailed error messages")
def test(service: str, debug: bool) -> None:
    """Test if credentials are valid.

    SERVICE: Which credentials to test (github or looker)

    Examples:

        # Test GitHub token
        sp auth test github

        # Test Looker credentials
        sp auth test looker
    """
    import httpx

    from semantic_patterns.credentials import CredentialType, get_credential_store

    store = get_credential_store(console)

    console.print()

    if service == "github":
        token = store.get(CredentialType.GITHUB, prompt_if_missing=False)
        if not token:
            console.print("[red]\u2717[/red] No GitHub token configured")
            console.print()
            console.print("[dim]Run 'sp build' to authenticate[/dim]")
            return

        console.print("Testing GitHub credentials...")
        try:
            with httpx.Client(timeout=10.0) as client:
                # Get user info
                user_response = client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                    },
                )

                if user_response.status_code != 200:
                    console.print(
                        f"[red]\u2717[/red] Invalid token (HTTP {user_response.status_code})"
                    )
                    if debug:
                        console.print(f"[dim]{user_response.text}[/dim]")
                    return

                user_data = user_response.json()
                username = user_data.get("login", "unknown")

                console.print("[green]\u2713[/green] Token is valid")
                console.print(f"[green]\u2713[/green] User: @{username}")

                # Check token scopes
                scopes = user_response.headers.get("x-oauth-scopes", "")
                if scopes:
                    console.print(f"[green]\u2713[/green] Scopes: {scopes}")

                    if "repo" not in scopes:
                        console.print(
                            "[yellow]\u26a0[/yellow] Warning: 'repo' scope required for pushing"
                        )

        except Exception as e:
            console.print(f"[red]\u2717[/red] Test failed: {e}")
            if debug:
                console.print(traceback.format_exc())

    elif service == "looker":
        # Load config to get base_url
        try:
            client_id = store.get("looker-client-id", prompt_if_missing=False)
            client_secret = store.get("looker-client-secret", prompt_if_missing=False)

            if not client_id or not client_secret:
                console.print("[red]\u2717[/red] Looker credentials not configured")
                console.print()
                console.print(
                    "[dim]Run 'sp build --push' to configure Looker credentials[/dim]"
                )
                return

            config_path = find_config()
            if not config_path:
                console.print(
                    "[yellow]\u26a0[/yellow] No sp.yml found (cannot determine Looker instance)"
                )
                console.print()

            config = load_config(config_path) if config_path else None

            if not config or not config.looker.base_url:
                console.print("[yellow]\u26a0[/yellow] Credentials found but not tested")
                console.print(
                    "[dim]Cannot test without looker.base_url in sp.yml[/dim]"
                )
                console.print()
                console.print("[dim]Credential files exist in keychain only[/dim]")
                return

            console.print(f"Testing Looker credentials for {config.looker.base_url}...")

            with httpx.Client(timeout=10.0) as client:
                # Attempt login
                response = client.post(
                    f"{config.looker.base_url}/api/4.0/login",
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                )

                if response.status_code != 200:
                    console.print(
                        f"[red]\u2717[/red] Authentication failed (HTTP {response.status_code})"
                    )
                    if debug:
                        console.print(f"[dim]{response.text}[/dim]")
                    return

                data = response.json()
                access_token = data.get("access_token")

                console.print("[green]\u2713[/green] Authentication successful")

                # Get current user
                me_response = client.get(
                    f"{config.looker.base_url}/api/4.0/user",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if me_response.status_code == 200:
                    user_data = me_response.json()
                    email = user_data.get("email", "unknown")
                    console.print(f"[green]\u2713[/green] User: {email}")

                # Check project access (if configured)
                if config.looker.project_id:
                    project_response = client.get(
                        f"{config.looker.base_url}/api/4.0/projects/{config.looker.project_id}",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )

                    if project_response.status_code == 200:
                        console.print(
                            f"[green]\u2713[/green] Project '{config.looker.project_id}': Access confirmed"
                        )
                    else:
                        console.print(
                            f"[yellow]\u26a0[/yellow] Project '{config.looker.project_id}': Access denied"
                        )

        except Exception as e:
            console.print(f"[red]\u2717[/red] Test failed: {e}")
            if debug:
                console.print(traceback.format_exc())

    console.print()
