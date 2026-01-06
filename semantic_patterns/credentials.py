"""Secure credential storage using system keychain.

This module provides a unified interface for storing and retrieving
credentials across the application. It supports:
- System keychain storage (macOS Keychain, Windows Credential Locker,
  Linux Secret Service)
- Environment variable fallback
- Interactive prompts for one-time setup

Usage:
    from semantic_patterns.credentials import CredentialStore

    store = CredentialStore()

    # Get a credential (checks env → keychain → prompt)
    token = store.get("github", prompt_if_missing=True)

    # Store a credential
    store.set("github", token)

    # Delete a credential
    store.delete("github")
"""

from __future__ import annotations

import os
from collections.abc import Callable
from enum import Enum

import keyring
from rich.console import Console

# Service name used for all keychain entries
SERVICE_NAME = "semantic-patterns"


class CredentialType(str, Enum):
    """Known credential types with their environment variable names."""

    GITHUB = "github"
    LOOKER_CLIENT_ID = "looker-client-id"
    LOOKER_CLIENT_SECRET = "looker-client-secret"

    @property
    def env_var(self) -> str:
        """Environment variable name for this credential type."""
        return f"SP_{self.value.upper().replace('-', '_')}"

    @property
    def display_name(self) -> str:
        """Human-readable name for prompts."""
        names = {
            "github": "GitHub Token",
            "looker-client-id": "Looker Client ID",
            "looker-client-secret": "Looker Client Secret",
        }
        return names.get(self.value, self.value)


# Environment variable mappings (can be extended)
ENV_VAR_MAPPING: dict[str, str] = {
    "github": "GITHUB_TOKEN",  # Standard GitHub env var
    "looker-client-id": "LOOKER_CLIENT_ID",
    "looker-client-secret": "LOOKER_CLIENT_SECRET",
}


class CredentialStore:
    """Unified credential storage with keychain and environment fallback.

    Priority order for credential resolution:
    1. Environment variable (for CI/automation)
    2. System keychain (for local development)
    3. Interactive prompt (one-time setup, saves to keychain)
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize credential store.

        Args:
            console: Rich console for interactive prompts. If None, creates one.
        """
        self.console = console or Console()

    def get(
        self,
        credential_type: str | CredentialType,
        *,
        prompt_if_missing: bool = False,
        prompt_message: str | None = None,
        prompt_instructions: str | None = None,
        save_to_keychain: bool = True,
        validator: Callable[[str], bool] | None = None,
    ) -> str | None:
        """Get a credential, checking env → keychain → optional prompt.

        Args:
            credential_type: Type of credential (e.g., "github",
                CredentialType.GITHUB)
            prompt_if_missing: If True, prompt user when credential not found
            prompt_message: Custom message for the prompt
            prompt_instructions: Instructions shown before prompt (e.g.,
                how to create token)
            save_to_keychain: If True, save prompted credential to keychain
            validator: Optional function to validate the credential

        Returns:
            The credential string, or None if not found and no prompt
        """
        key = (
            credential_type.value
            if isinstance(credential_type, CredentialType)
            else credential_type
        )

        # 1. Check environment variable
        env_var = ENV_VAR_MAPPING.get(key, f"SP_{key.upper().replace('-', '_')}")
        env_value = os.environ.get(env_var)
        if env_value:
            return env_value

        # 2. Check keychain
        try:
            keychain_value = keyring.get_password(SERVICE_NAME, key)
            if keychain_value:
                return keychain_value
        except keyring.errors.KeyringError:
            # Keychain not available (e.g., headless CI without keychain)
            pass

        # 3. Interactive prompt (if enabled)
        if prompt_if_missing:
            return self._prompt_for_credential(
                key,
                prompt_message=prompt_message,
                prompt_instructions=prompt_instructions,
                save_to_keychain=save_to_keychain,
                validator=validator,
            )

        return None

    def set(self, credential_type: str | CredentialType, value: str) -> bool:
        """Store a credential in the system keychain.

        Args:
            credential_type: Type of credential
            value: The credential value to store

        Returns:
            True if stored successfully, False if keychain unavailable
        """
        key = (
            credential_type.value
            if isinstance(credential_type, CredentialType)
            else credential_type
        )

        try:
            keyring.set_password(SERVICE_NAME, key, value)
            return True
        except keyring.errors.KeyringError:
            return False

    def delete(self, credential_type: str | CredentialType) -> bool:
        """Delete a credential from the system keychain.

        Args:
            credential_type: Type of credential to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        key = (
            credential_type.value
            if isinstance(credential_type, CredentialType)
            else credential_type
        )

        try:
            keyring.delete_password(SERVICE_NAME, key)
            return True
        except keyring.errors.PasswordDeleteError:
            # Password didn't exist
            return False
        except keyring.errors.KeyringError:
            return False

    def exists(self, credential_type: str | CredentialType) -> bool:
        """Check if a credential exists in env or keychain.

        Args:
            credential_type: Type of credential to check

        Returns:
            True if credential exists, False otherwise
        """
        return self.get(credential_type, prompt_if_missing=False) is not None

    def _prompt_for_credential(
        self,
        key: str,
        *,
        prompt_message: str | None = None,
        prompt_instructions: str | None = None,
        save_to_keychain: bool = True,
        validator: Callable[[str], bool] | None = None,
    ) -> str | None:
        """Interactively prompt user for a credential.

        Args:
            key: Credential key name
            prompt_message: Custom prompt message
            prompt_instructions: Instructions to show before prompt
            save_to_keychain: Whether to offer saving to keychain
            validator: Optional validation function

        Returns:
            The entered credential, or None if cancelled
        """
        # Get display name
        try:
            cred_type = CredentialType(key)
            display_name = cred_type.display_name
        except ValueError:
            display_name = key.replace("-", " ").title()

        self.console.print()
        self.console.print(f"[bold]{display_name} Required[/bold]")
        self.console.print()

        if prompt_instructions:
            self.console.print(prompt_instructions)
            self.console.print()

        if prompt_message:
            self.console.print(prompt_message)

        # Prompt for credential (hidden input)
        while True:
            value = self.console.input(f"[bold]{display_name}:[/bold] ", password=True)

            if not value:
                self.console.print("[yellow]Cancelled[/yellow]")
                return None

            # Validate if validator provided
            if validator and not validator(value):
                self.console.print("[red]Invalid credential. Please try again.[/red]")
                continue

            break

        # Offer to save to keychain
        if save_to_keychain:
            self.console.print()
            save_prompt = self.console.input(
                "Save to system keychain for future use? [Y/n]: "
            )
            if save_prompt.lower() != "n":
                if self.set(key, value):
                    self.console.print(
                        f"[green]Saved to keychain ({SERVICE_NAME}/{key})[/green]"
                    )
                else:
                    msg = (
                        "[yellow]Could not save to keychain "
                        "(keychain unavailable)[/yellow]"
                    )
                    self.console.print(msg)

        return value


# Module-level convenience functions
_default_store: CredentialStore | None = None


def get_credential_store(console: Console | None = None) -> CredentialStore:
    """Get or create the default credential store.

    Args:
        console: Optional Rich console for prompts

    Returns:
        The credential store instance
    """
    global _default_store
    if _default_store is None:
        _default_store = CredentialStore(console)
    return _default_store


def get_github_token(
    *,
    prompt_if_missing: bool = False,
    console: Console | None = None,
) -> str | None:
    """Convenience function to get GitHub token.

    Args:
        prompt_if_missing: If True, prompt user when token not found
        console: Optional Rich console for prompts

    Returns:
        GitHub token or None
    """
    store = get_credential_store(console)
    return store.get(
        CredentialType.GITHUB,
        prompt_if_missing=prompt_if_missing,
        prompt_instructions=(
            "To push LookML to GitHub, you need a Personal Access Token:\n\n"
            "1. Go to: [link]https://github.com/settings/tokens/new[/link]\n"
            "2. Create a token with [bold]repo[/bold] scope\n"
            "3. Paste your token below"
        ),
        validator=lambda t: len(t) >= 20,  # Basic length check
    )
