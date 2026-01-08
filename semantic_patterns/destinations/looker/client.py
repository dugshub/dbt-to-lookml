"""Looker API client operations."""

from __future__ import annotations

import os
import ssl
from typing import Any

import httpx
from rich.console import Console

from semantic_patterns.config import LookerConfig
from semantic_patterns.credentials import get_credential_store
from semantic_patterns.destinations.looker.errors import LookerAPIError

# Credential keys for Looker API
LOOKER_CLIENT_ID_KEY = "looker-client-id"
LOOKER_CLIENT_SECRET_KEY = "looker-client-secret"

# Environment variables for HTTPS configuration
LOOKER_HTTPS_VERIFY_ENV = "LOOKER_HTTPS_VERIFY"
LOOKER_TIMEOUT_ENV = "LOOKER_TIMEOUT"


def _get_ssl_verify() -> bool | ssl.SSLContext:
    """Get SSL verification setting from environment.

    Set LOOKER_HTTPS_VERIFY=false to disable SSL verification
    (useful for self-signed certificates).

    Returns:
        True for default verification, False to disable
    """
    verify_env = os.environ.get(LOOKER_HTTPS_VERIFY_ENV, "").lower()
    if verify_env in ("false", "0", "no", "off"):
        return False
    return True


def _get_timeout() -> float:
    """Get timeout setting from environment.

    Set LOOKER_TIMEOUT to override default 30s timeout.

    Returns:
        Timeout in seconds
    """
    timeout_env = os.environ.get(LOOKER_TIMEOUT_ENV)
    if timeout_env:
        try:
            return float(timeout_env)
        except ValueError:
            pass
    return 30.0


def _get_http_client(timeout: float | None = None) -> httpx.Client:
    """Create HTTP client with proper SSL and proxy configuration.

    Respects standard proxy environment variables (HTTP_PROXY, HTTPS_PROXY).

    Args:
        timeout: Request timeout in seconds (default from env or 30s)

    Returns:
        Configured httpx.Client
    """
    return httpx.Client(
        timeout=timeout or _get_timeout(),
        verify=_get_ssl_verify(),
        # httpx automatically respects HTTP_PROXY, HTTPS_PROXY, NO_PROXY env vars
    )


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

        # First check if both credentials already exist (env or keychain)
        client_id = store.get(LOOKER_CLIENT_ID_KEY, prompt_if_missing=False)
        client_secret = store.get(LOOKER_CLIENT_SECRET_KEY, prompt_if_missing=False)

        if client_id and client_secret:
            return client_id, client_secret

        # Need to prompt - collect both credentials together
        # Build instructions with instance-specific URL
        # Note: Direct API key URL requires knowing user ID, so we link to account page
        account_url = f"{self.config.base_url}/account"
        instructions = (
            "To sync your Looker dev environment, you need API credentials:\n\n"
            f"1. Go to: [link]{account_url}[/link]\n"
            "2. Scroll to 'API Keys' section\n"
            "3. Click 'Edit Keys' → 'New API Key'\n"
            "4. Copy your Client ID and Client Secret below\n\n"
            "[dim]Note: API keys can also be found at /admin/users/api3_key/<user_id>[/dim]"
        )

        self.console.print()
        self.console.print("[bold]Looker API Credentials Required[/bold]")
        self.console.print()
        self.console.print(instructions)
        self.console.print()

        # Prompt for client ID
        client_id = self.console.input("[bold]Client ID:[/bold] ", password=False)
        if not client_id or len(client_id) < 10:
            self.console.print("[yellow]Cancelled or invalid Client ID[/yellow]")
            return None

        # Prompt for client secret
        client_secret = self.console.input("[bold]Client Secret:[/bold] ", password=True)
        if not client_secret or len(client_secret) < 10:
            self.console.print("[yellow]Cancelled or invalid Client Secret[/yellow]")
            return None

        # Single prompt to save both credentials
        self.console.print()
        save_prompt = self.console.input(
            "Save both credentials to system keychain for future use? [Y/n]: "
        )
        if save_prompt.lower() != "n":
            saved_id = store.set(LOOKER_CLIENT_ID_KEY, client_id)
            saved_secret = store.set(LOOKER_CLIENT_SECRET_KEY, client_secret)
            if saved_id and saved_secret:
                self.console.print(
                    "[green]✓ Saved credentials to keychain[/green]"
                )
            elif saved_id or saved_secret:
                self.console.print(
                    "[yellow]⚠ Partially saved to keychain[/yellow]"
                )
            else:
                self.console.print(
                    "[yellow]Could not save to keychain (keychain unavailable)[/yellow]"
                )

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
            with _get_http_client() as client:
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
        except httpx.ConnectError as e:
            self._print_connection_error(e)
            raise LookerAPIError("Connection error")
        except httpx.TimeoutException as e:
            self._print_timeout_error(e)
            raise LookerAPIError("Timeout error")
        except httpx.HTTPError as e:
            self._print_network_error(e)
            raise LookerAPIError("Network error")

    def _print_connection_error(self, e: httpx.ConnectError) -> None:
        """Print helpful diagnostics for connection errors."""
        self.console.print()
        self.console.print(f"[red]✗[/red] Connection failed: {e}")
        self.console.print()
        self.console.print(
            f"Cannot connect to Looker instance at {self.config.base_url}"
        )
        self.console.print()

        error_str = str(e).lower()

        # SSL/TLS specific guidance
        if "ssl" in error_str or "certificate" in error_str:
            self.console.print("[bold]SSL/Certificate Issue Detected[/bold]")
            self.console.print()
            self.console.print("Try one of these solutions:")
            self.console.print(
                "  • For self-signed certs: [bold]LOOKER_HTTPS_VERIFY=false sp build --push[/bold]"
            )
            self.console.print(
                "  • Check if your VPN/proxy intercepts HTTPS traffic"
            )
            self.console.print(
                "  • Verify the Looker URL is correct in sp.yml"
            )
        # Proxy/network guidance
        elif "proxy" in error_str or "connect" in error_str:
            self.console.print("[bold]Network/Proxy Issue Detected[/bold]")
            self.console.print()
            self.console.print("Try one of these solutions:")
            self.console.print(
                "  • Set proxy: [bold]HTTPS_PROXY=http://proxy:port sp build --push[/bold]"
            )
            self.console.print(
                "  • Check firewall/VPN settings"
            )
            self.console.print(
                "  • Verify Looker instance is accessible from this network"
            )
        else:
            self.console.print("Possible causes:")
            self.console.print("  • Looker instance is down or unreachable")
            self.console.print("  • Network/firewall blocking the connection")
            self.console.print("  • Incorrect base_url in sp.yml")

        self.console.print()

    def _print_timeout_error(self, e: httpx.TimeoutException) -> None:
        """Print helpful diagnostics for timeout errors."""
        self.console.print()
        self.console.print(f"[red]✗[/red] Request timed out: {e}")
        self.console.print()
        self.console.print(
            f"Looker instance at {self.config.base_url} did not respond in time"
        )
        self.console.print()
        self.console.print("Try one of these solutions:")
        self.console.print(
            f"  • Increase timeout: [bold]LOOKER_TIMEOUT=60 sp build --push[/bold]"
        )
        self.console.print(
            "  • Check if the Looker instance is under heavy load"
        )
        self.console.print(
            "  • Verify network connectivity"
        )
        self.console.print()

    def _print_network_error(self, e: httpx.HTTPError) -> None:
        """Print helpful diagnostics for general network errors."""
        self.console.print()
        self.console.print(f"[red]✗[/red] Network error: {e}")
        self.console.print()
        self.console.print(
            f"Cannot reach Looker instance at {self.config.base_url}"
        )
        self.console.print()

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
