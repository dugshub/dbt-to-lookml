"""Looker API client operations."""

from __future__ import annotations

from typing import Any

import httpx
from rich.console import Console

from semantic_patterns.config import LookerConfig
from semantic_patterns.credentials import get_credential_store
from semantic_patterns.destinations.looker.errors import LookerAPIError

# Credential keys for Looker API
LOOKER_CLIENT_ID_KEY = "looker-client-id"
LOOKER_CLIENT_SECRET_KEY = "looker-client-secret"


class LookerClient:
    """Handle Looker API operations."""

    def __init__(
        self,
        config: LookerConfig,
        console: Console,
    ) -> None:
        """Initialize Looker client.

        Args:
            config: Looker configuration
            console: Rich console for output
        """
        self.config = config
        self.console = console

    def get_credentials(self) -> tuple[str, str] | None:
        """Get Looker API credentials from env, keychain, or prompt.

        Returns:
            Tuple of (client_id, client_secret) or None if not available
        """
        store = get_credential_store(self.console)

        # Build instructions with instance-specific URL
        admin_url = f"{self.config.base_url}/admin/users"
        instructions = (
            "To sync your Looker dev environment, you need API credentials:\n\n"
            f"1. Go to: [link]{admin_url}[/link]\n"
            "2. Click your user → Edit → API Keys\n"
            "3. Create new API credentials (or use existing)\n"
            "4. Enter your Client ID and Client Secret below"
        )

        client_id = store.get(
            LOOKER_CLIENT_ID_KEY,
            prompt_if_missing=True,
            prompt_instructions=instructions,
            validator=lambda t: len(t) >= 10,
        )

        if not client_id:
            return None

        client_secret = store.get(
            LOOKER_CLIENT_SECRET_KEY,
            prompt_if_missing=True,
            validator=lambda t: len(t) >= 10,
        )

        if not client_secret:
            return None

        return client_id, client_secret

    def get_access_token(self, client_id: str, client_secret: str) -> str:
        """Exchange Looker API credentials for an access token.

        Args:
            client_id: Looker API client ID
            client_secret: Looker API client secret

        Returns:
            Access token for Looker API

        Raises:
            LookerAPIError: If authentication fails
        """
        url = f"{self.config.base_url}/api/4.0/login"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    url,
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                )

                if response.status_code == 200:
                    data: dict[str, Any] = response.json()
                    access_token: str = data["access_token"]
                    return access_token
                else:
                    # Print helpful error message for user
                    self.console.print()
                    self.console.print("[red]✗[/red] Looker authentication failed")
                    self.console.print()
                    self.console.print(
                        "Your Looker credentials may be invalid or expired."
                    )
                    self.console.print()
                    self.console.print("To fix this:")
                    self.console.print(
                        "  1. Clear your credentials: [bold]sp auth clear looker[/bold]"
                    )
                    self.console.print(
                        "  2. Re-authenticate: [bold]sp build --push[/bold]"
                    )
                    self.console.print()
                    self.console.print(
                        "Or test your credentials: [bold]sp auth test looker --debug[/bold]"
                    )
                    self.console.print()

                    # Raise exception with minimal message (detailed output already printed)
                    raise LookerAPIError(
                        "Authentication failed",
                        status_code=response.status_code,
                    )
        except httpx.HTTPError as e:
            # Print helpful error message for user
            self.console.print()
            self.console.print(f"[red]✗[/red] Network error: {e}")
            self.console.print()
            self.console.print(
                f"Cannot reach Looker instance at {self.config.base_url}"
            )
            self.console.print()

            # Raise exception with minimal message (detailed output already printed)
            raise LookerAPIError("Network error")

    def build_explore_url(self, blobs: list[dict[str, str]]) -> str | None:
        """Build Looker IDE URL for the first explore file.

        URL format:
        {base_url}/projects/{project_id}/files/{path}{relative_path}

        Example:
        https://spothero.looker.com/projects/analytics-dbt/files/semantic-patterns-generated/semantic-patterns/explores/sp_rentals.explore.lkml

        Args:
            blobs: List of blob dictionaries with 'path' keys

        Returns:
            URL to first explore file in Looker IDE, or None if no explores or Looker not configured
        """
        # Require base_url and project_id for Looker IDE links
        if not self.config.base_url or not self.config.project_id:
            return None

        # Find first explore file
        for blob in blobs:
            if "/explores/" in blob["path"] and blob["path"].endswith(".explore.lkml"):
                # URL-encode the path properly
                file_path = blob["path"]
                return f"{self.config.base_url}/projects/{self.config.project_id}/files/{file_path}"

        return None
