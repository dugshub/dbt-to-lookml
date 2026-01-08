"""Looker destination for pushing LookML and syncing dev environments.

This module provides unified handling for:
1. Pushing generated LookML to a Git repository (backing the Looker project)
2. Syncing the user's Looker dev environment to see changes immediately
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from semantic_patterns.config import LookerConfig
from semantic_patterns.destinations.base import WriteResult
from semantic_patterns.destinations.looker.client import LookerClient
from semantic_patterns.destinations.looker.errors import LookerAPIError
from semantic_patterns.destinations.looker.github import GitHubClient
from semantic_patterns.destinations.looker.sync import DevSync


class LookerDestination:
    """Push generated LookML to Git and sync Looker dev environment.

    This destination handles the complete workflow:
    1. Push LookML files to a GitHub repository (backing the Looker project)
    2. Optionally sync the user's Looker dev environment to the pushed branch

    Example:
        from semantic_patterns.destinations import LookerDestination
        from semantic_patterns.config import LookerConfig

        config = LookerConfig(
            enabled=True,
            repo="myorg/looker-models",
            branch="sp-generated",
            base_url="https://mycompany.looker.com",
            project_id="my_project",
        )
        dest = LookerDestination(config, project="my-project")
        result = dest.write(files)
    """

    def __init__(
        self,
        config: LookerConfig,
        project: str,
        console: Console | None = None,
    ) -> None:
        """Initialize Looker destination.

        Args:
            config: Looker configuration
            project: Project name (used in commit messages)
            console: Rich console for output (optional)
        """
        self.config = config
        self.project = project
        self.console = console or Console()

        # Initialize sub-clients
        self.github = GitHubClient(config, project, self.console)
        self.looker = LookerClient(config, self.console)
        self.sync = DevSync(config, self.looker, self.console)

    def write(
        self,
        files: dict[Path, str],
        dry_run: bool = False,
    ) -> WriteResult:
        """Push files to Git and sync Looker dev environment.

        Args:
            files: Dictionary mapping local file paths to their content
            dry_run: If True, simulate without pushing

        Returns:
            WriteResult with commit URL and metadata
        """
        # Validate configuration
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid Looker configuration: {'; '.join(errors)}")

        # Resolve GitHub token
        github_token = self.github.get_token()
        if not github_token:
            raise LookerAPIError(
                "No GitHub token available. Set GITHUB_TOKEN or run interactively."
            )

        # Transform local paths to Git blob paths
        blobs = self.github.prepare_blobs(files)

        if dry_run:
            repo_ref = f"{self.config.repo}@{self.config.branch}"
            message = f"Would push {len(blobs)} files to {repo_ref}"
            if self.config.looker_sync_enabled:
                message += f" and sync Looker project '{self.config.project_id}'"
            return WriteResult(
                files_written=[b["path"] for b in blobs],
                message=message,
                metadata={
                    "repo": self.config.repo,
                    "branch": self.config.branch,
                    "file_count": str(len(blobs)),
                    "looker_sync": str(self.config.looker_sync_enabled),
                },
            )

        # Step 1: Push to GitHub
        commit_sha = self.github.create_commit(github_token, blobs)
        commit_url = f"https://github.com/{self.config.repo}/commit/{commit_sha}"

        # Step 2: Sync Looker dev environment (if configured)
        looker_synced = False
        validation_passed = True
        if self.config.looker_sync_enabled:
            try:
                self.sync.sync_to_branch()
                looker_synced = True

                # Step 3: Validate LookML after sync
                validation_passed = self._validate_and_maybe_rollback(
                    github_token, commit_sha
                )
            except LookerAPIError as e:
                # Log but don't fail - Git push succeeded
                self.console.print(f"[yellow]Looker sync failed: {e}[/yellow]")

        repo_ref = f"{self.config.repo}@{self.config.branch}"
        message = f"Pushed {len(blobs)} files to {repo_ref}"
        if looker_synced:
            if validation_passed:
                message += " and synced Looker dev"
            else:
                message += " (rolled back due to validation errors)"

        # Generate Looker IDE URL for first explore (if available)
        looker_url = self.looker.build_explore_url(blobs) if validation_passed else None

        return WriteResult(
            files_written=[b["path"] for b in blobs],
            destination_url=commit_url,
            looker_url=looker_url,
            message=message,
            commit_sha=commit_sha,
            metadata={
                "repo": self.config.repo,
                "branch": self.config.branch,
                "file_count": str(len(blobs)),
                "looker_synced": str(looker_synced),
                "validation_passed": str(validation_passed),
            },
        )

    def _validate_and_maybe_rollback(
        self, github_token: str, commit_sha: str
    ) -> bool:
        """Validate LookML and offer rollback if errors found.

        Args:
            github_token: GitHub token for rollback
            commit_sha: SHA of commit to potentially rollback

        Returns:
            True if validation passed or user declined rollback,
            False if rollback was performed
        """
        # Get Looker access token for validation
        creds = self.looker.get_credentials()
        if not creds:
            return True  # Can't validate without creds, assume OK

        client_id, client_secret = creds
        try:
            access_token = self.looker.get_access_token(client_id, client_secret)
        except LookerAPIError:
            return True  # Can't validate, assume OK

        # Run validation
        self.console.print()
        self.console.print("[dim]Validating LookML...[/dim]")
        errors = self.sync.validate_lookml(access_token)

        if not errors:
            self.console.print("[green]✓[/green] LookML validation passed")
            return True

        # Validation failed - show errors and offer rollback
        self.sync.display_validation_errors(errors)

        import click

        if not click.confirm(
            "Rollback this commit to fix errors?", default=False
        ):
            self.console.print(
                "[yellow]Keeping commit with validation errors[/yellow]"
            )
            self.console.print(
                f"[dim]Fix errors and push again, or revert manually[/dim]"
            )
            return True  # User chose to keep the commit

        # Perform rollback
        self.console.print()
        self.console.print(f"[dim]Rolling back commit {commit_sha[:7]}...[/dim]")

        revert_sha = self.github.rollback_commit(github_token, commit_sha)
        if not revert_sha:
            self.console.print(
                "[red]✗[/red] Rollback failed - please revert manually"
            )
            return False

        self.console.print(
            f"[green]✓[/green] Rolled back to previous state ({revert_sha[:7]})"
        )

        # Re-sync Looker to get the reverted state
        self.console.print("[dim]Re-syncing Looker dev environment...[/dim]")
        try:
            self.sync.sync_to_branch()
            self.console.print(
                "[green]✓[/green] Looker dev synced to reverted state"
            )
        except LookerAPIError as e:
            self.console.print(
                f"[yellow]⚠[/yellow] Could not re-sync Looker: {e}"
            )
            self.console.print(
                "[dim]Manually sync in Looker IDE: Development → Reset to Remote[/dim]"
            )

        return False

    def validate(self) -> list[str]:
        """Validate Looker configuration.

        Returns:
            List of error messages (empty if valid)
        """
        errors: list[str] = []

        if not self.config.enabled:
            errors.append("Looker is not enabled")
            return errors

        if not self.config.repo:
            errors.append("looker.repo is required")

        if not self.config.branch:
            errors.append("looker.branch is required")

        # Defense in depth: re-check protected branches
        if self.config.branch.lower() in self.config.ALWAYS_PROTECTED:
            errors.append(f"Cannot push to protected branch '{self.config.branch}'")

        return errors
