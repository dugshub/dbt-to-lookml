"""Looker dev environment synchronization."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import httpx
from rich.console import Console

from semantic_patterns.config import LookerConfig
from semantic_patterns.destinations.looker.client import LookerClient
from semantic_patterns.destinations.looker.errors import LookerAPIError


class DevSync:
    """Handle Looker dev environment synchronization."""

    def __init__(
        self,
        config: LookerConfig,
        looker_client: LookerClient,
        console: Console,
    ) -> None:
        """Initialize dev sync.

        Args:
            config: Looker configuration
            looker_client: Looker API client
            console: Rich console for output
        """
        self.config = config
        self.looker_client = looker_client
        self.console = console

    def sync_to_branch(self) -> None:
        """Sync Looker dev environment to the pushed branch.

        This performs a non-destructive branch switch (git checkout).
        User's uncommitted changes are preserved if there are no conflicts.

        Raises:
            LookerAPIError: If sync fails
        """
        # Get Looker credentials
        creds = self.looker_client.get_credentials()
        if not creds:
            raise LookerAPIError("No Looker credentials available")

        client_id, client_secret = creds

        # Get access token
        access_token = self.looker_client.get_access_token(client_id, client_secret)

        self.console.print()
        self.console.print(
            f"[dim]Syncing Looker dev environment to branch '{self.config.branch}'...[/dim]"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(
                base_url=f"{self.config.base_url}/api/4.0",
                headers=headers,
                timeout=30.0,
            ) as client:
                # Step 1: Switch to dev workspace
                session_response = client.patch(
                    "/session",
                    json={"workspace_id": "dev"},
                )
                if session_response.status_code != 200:
                    raise LookerAPIError(
                        f"Failed to switch to dev workspace: {session_response.text}",
                        status_code=session_response.status_code,
                    )

                # Step 1.5: Check for validation errors on current branch
                # This prevents "cannot switch branches with errors" issue
                self._check_and_handle_validation_errors(client)

                # Step 2: Check if branch exists in Looker
                self._ensure_branch_exists(client)

                # Step 3: Switch to the branch
                self._switch_to_branch(client)

                # Step 4: Reset to remote (pull latest from origin)
                self._pull_latest_changes(client)

        except httpx.TimeoutException:
            self.console.print()
            self.console.print(
                "[yellow]⚠[/yellow] Looker sync timed out (Looker instance may be slow)"
            )
            self.console.print()
            self.console.print(
                f"[dim]Note: GitHub push succeeded. Your changes are in "
                f"{self.config.repo}@{self.config.branch}[/dim]"
            )
            self.console.print()
            self.console.print(
                "[dim]Try manually syncing in Looker IDE: "
                "Development → Configure Git → Reset to Remote[/dim]"
            )
            raise LookerAPIError("Looker sync timed out")
        except httpx.HTTPError as e:
            self.console.print()
            self.console.print(f"[red]✗[/red] Network error during Looker sync: {e}")
            self.console.print()
            self.console.print(
                f"[dim]Note: GitHub push succeeded. Your changes are in "
                f"{self.config.repo}@{self.config.branch}[/dim]"
            )
            raise LookerAPIError("Network error during Looker sync")

    def _check_and_handle_validation_errors(self, client: httpx.Client) -> None:
        """Check for validation errors and handle them if found.

        Args:
            client: Configured httpx client

        Raises:
            LookerAPIError: If reset fails
        """
        validation_response = client.get(
            f"/projects/{self.config.project_id}/validate"
        )

        if validation_response.status_code != 200:
            return  # Validation check failed, proceed anyway

        validation_data = validation_response.json()
        errors = validation_data.get("errors", [])

        if not errors:
            return  # No errors, proceed

        # Group errors by message to match Looker's UI display
        error_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for error in errors:
            message = error.get("message", "Unknown error")
            error_groups[message].append(error)

        unique_count = len(error_groups)
        total_count = len(errors)

        # Current branch has validation errors - Looker won't allow checkout
        self.console.print()
        self.console.print(f"[red]⚠ WARNING[/red] LookML Errors ({unique_count})")
        if total_count != unique_count:
            self.console.print(f"[dim]{total_count} total occurrences[/dim]")
        self.console.print()

        # Show first 3 unique error types with occurrence counts
        for i, (message, occurrences) in enumerate(
            list(error_groups.items())[:3], 1
        ):
            count = len(occurrences)
            if count > 1:
                self.console.print(
                    f"  {i}. {message} [dim]({count} occurrences)[/dim]"
                )
            else:
                self.console.print(f"  {i}. {message}")

            # Show first location for this error type
            first_error = occurrences[0]
            file_path = first_error.get("file_path", "")
            line = first_error.get("line_number", "")
            if file_path:
                location = f"{file_path}:{line}" if line else file_path
                self.console.print(f"     [dim]{location}[/dim]")

        if unique_count > 3:
            self.console.print(f"  ... and {unique_count - 3} more error type(s)")

        self.console.print()
        self.console.print(
            "Looker won't allow branch switching with validation errors in your workspace."
        )
        self.console.print()
        self.console.print(
            "[bold red]This will DISCARD all uncommitted changes in your Looker dev workspace.[/bold red]"
        )
        self.console.print()
        self.console.print(
            "Any LookML edits you haven't committed and pushed will be PERMANENTLY LOST."
        )
        self.console.print()

        import click

        if not click.confirm(
            "Discard all uncommitted changes and reset workspace?", default=False
        ):
            self.console.print("[yellow]Sync cancelled[/yellow]")
            self.console.print()
            self.console.print(
                f"[dim]Note: GitHub push succeeded. Your changes are in "
                f"{self.config.repo}@{self.config.branch}[/dim]"
            )
            raise LookerAPIError("User cancelled workspace reset")

        # User agreed to hard reset - reset current branch to remote first
        self.console.print()
        self.console.print("[dim]Resetting current branch to remote...[/dim]")

        reset_current_response = client.post(
            f"/projects/{self.config.project_id}/reset_to_remote"
        )

        if reset_current_response.status_code not in (200, 204):
            # Reset failed - try to provide helpful error
            error_msg = reset_current_response.text
            self.console.print(f"[yellow]⚠[/yellow] Reset failed: {error_msg}")
            self.console.print()
            self.console.print(
                "[dim]You may need to manually reset in Looker IDE: "
                "Development → Reset to Production[/dim]"
            )
            raise LookerAPIError(
                "Failed to reset workspace to remote",
                status_code=reset_current_response.status_code,
            )

        self.console.print("[green]✓[/green] Workspace reset to remote")

    def _ensure_branch_exists(self, client: httpx.Client) -> None:
        """Ensure the target branch exists in Looker, creating if needed.

        Args:
            client: Configured httpx client

        Raises:
            LookerAPIError: If branch check or creation fails
        """
        branch_response = client.get(
            f"/projects/{self.config.project_id}/git_branch/{self.config.branch}"
        )

        if branch_response.status_code == 404:
            # Branch doesn't exist locally - create it
            self.console.print(
                f"[dim]Creating local branch '{self.config.branch}'...[/dim]"
            )
            create_response = client.post(
                f"/projects/{self.config.project_id}/git_branch",
                json={
                    "name": self.config.branch,
                    "ref": f"origin/{self.config.branch}",
                },
            )
            if create_response.status_code not in (200, 201):
                raise LookerAPIError(
                    f"Failed to create branch: {create_response.text}",
                    status_code=create_response.status_code,
                )
        elif branch_response.status_code != 200:
            raise LookerAPIError(
                f"Failed to check branch: {branch_response.text}",
                status_code=branch_response.status_code,
            )

    def _switch_to_branch(self, client: httpx.Client) -> None:
        """Switch to the target branch.

        Args:
            client: Configured httpx client

        Raises:
            LookerAPIError: If branch switch fails
        """
        self.console.print(f"[dim]Switching to branch '{self.config.branch}'...[/dim]")

        switch_response = client.put(
            f"/projects/{self.config.project_id}/git_branch",
            json={"name": self.config.branch},
        )

        if switch_response.status_code != 200:
            # Branch switch failed - provide helpful error
            error_text = switch_response.text
            self.console.print()
            self.console.print(
                f"[red]✗[/red] Failed to switch to branch '{self.config.branch}'"
            )
            self.console.print()
            self.console.print(f"[dim]Error: {error_text}[/dim]")
            self.console.print()
            self.console.print(
                "[dim]You may need to manually switch branches in Looker IDE[/dim]"
            )

            raise LookerAPIError(
                "Failed to switch branch",
                status_code=switch_response.status_code,
            )

    def _pull_latest_changes(self, client: httpx.Client) -> None:
        """Pull latest changes from remote.

        Args:
            client: Configured httpx client
        """
        self.console.print(
            f"[dim]Pulling latest changes from origin/{self.config.branch}...[/dim]"
        )

        reset_response = client.post(
            f"/projects/{self.config.project_id}/reset_to_remote"
        )

        if reset_response.status_code not in (200, 204):
            error_text = reset_response.text
            self.console.print()
            self.console.print(
                f"[yellow]⚠[/yellow] Failed to pull latest changes: {error_text}"
            )
            self.console.print()
            self.console.print(
                "[dim]Branch switched, but workspace may not be up to date[/dim]"
            )
            # Don't raise - branch switch succeeded, just pull failed
        else:
            self.console.print(
                f"[green]✓[/green] Looker dev synced to branch '{self.config.branch}'"
            )
