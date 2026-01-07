"""Looker destination for pushing LookML and syncing dev environments.

This module provides unified handling for:
1. Pushing generated LookML to a Git repository (backing the Looker project)
2. Syncing the user's Looker dev environment to see changes immediately
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from rich.console import Console

from semantic_patterns.config import LookerConfig
from semantic_patterns.credentials import (
    CredentialType,
    get_credential_store,
    github_device_flow,
    register_credential_env_var,
)
from semantic_patterns.destinations.base import WriteResult

# Register Looker credential environment variables
register_credential_env_var("looker-client-id", "LOOKER_CLIENT_ID")
register_credential_env_var("looker-client-secret", "LOOKER_CLIENT_SECRET")

# Credential keys for Looker API
LOOKER_CLIENT_ID_KEY = "looker-client-id"
LOOKER_CLIENT_SECRET_KEY = "looker-client-secret"


class LookerAPIError(Exception):
    """Error from Looker or GitHub API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


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

    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_API_VERSION = "2022-11-28"

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
        self._github_token: str | None = None
        self._looker_token: str | None = None

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
        github_token = self._get_github_token()
        if not github_token:
            raise LookerAPIError(
                "No GitHub token available. Set GITHUB_TOKEN or run interactively."
            )

        # Transform local paths to Git blob paths
        blobs = self._prepare_blobs(files)

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
        commit_sha = self._create_github_commit(github_token, blobs)
        commit_url = f"https://github.com/{self.config.repo}/commit/{commit_sha}"

        # Step 2: Sync Looker dev environment (if configured)
        looker_synced = False
        if self.config.looker_sync_enabled:
            try:
                self._sync_looker_dev()
                looker_synced = True
            except LookerAPIError as e:
                # Log but don't fail - Git push succeeded
                self.console.print(f"[yellow]Looker sync failed: {e}[/yellow]")

        repo_ref = f"{self.config.repo}@{self.config.branch}"
        message = f"Pushed {len(blobs)} files to {repo_ref}"
        if looker_synced:
            message += f" and synced Looker dev"

        # Generate Looker IDE URL for first explore (if available)
        looker_url = self._build_looker_explore_url(blobs)

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
            },
        )

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

    # -------------------------------------------------------------------------
    # GitHub Token Management
    # -------------------------------------------------------------------------

    def _get_github_token(self) -> str | None:
        """Get GitHub token from env, keychain, or device flow.

        Returns:
            GitHub token or None if not available
        """
        if self._github_token:
            return self._github_token

        store = get_credential_store(self.console)

        # Check env/keychain first
        token = store.get(CredentialType.GITHUB, prompt_if_missing=False)
        if token:
            self._github_token = token
            return token

        # No token found - offer device flow or manual token entry
        self.console.print()
        self.console.print("[bold]GitHub Authentication Required[/bold]")
        self.console.print()
        self.console.print(
            f"To push LookML to [bold]{self.config.repo}[/bold], "
            "you need to authenticate with GitHub."
        )
        self.console.print()
        self.console.print("Choose authentication method:")
        self.console.print("  [bold]1.[/bold] Browser login (recommended)")
        self.console.print("  [bold]2.[/bold] Personal Access Token (PAT)")
        self.console.print()

        choice = self.console.input("Select [1-2]: ").strip()

        if choice == "1" or choice == "":
            # Device flow authentication
            token = github_device_flow(self.console)
            if token:
                # Save to keychain
                if store.set(CredentialType.GITHUB, token):
                    self.console.print(
                        "[green]Saved token to keychain[/green] "
                        "[dim](semantic-patterns/github)[/dim]"
                    )
                self._github_token = token
                return token
            else:
                return None

        elif choice == "2":
            # Manual token entry
            token = store.get(
                CredentialType.GITHUB,
                prompt_if_missing=True,
                prompt_instructions=(
                    "Create a Personal Access Token:\n\n"
                    "1. Go to: [link]https://github.com/settings/tokens/new[/link]\n"
                    "2. Create a token with [bold]repo[/bold] scope\n"
                    "3. Paste your token below"
                ),
                validator=lambda t: len(t) >= 20,
            )
            self._github_token = token
            return token

        else:
            self.console.print("[red]Invalid choice[/red]")
            return None

    # -------------------------------------------------------------------------
    # Looker Credentials Management
    # -------------------------------------------------------------------------

    def _get_looker_credentials(self) -> tuple[str, str] | None:
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

    def _get_looker_access_token(self, client_id: str, client_secret: str) -> str:
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
                    raise LookerAPIError(
                        f"Looker authentication failed: {response.text}",
                        status_code=response.status_code,
                    )
        except httpx.HTTPError as e:
            raise LookerAPIError(f"Network error during Looker auth: {e}")

    # -------------------------------------------------------------------------
    # Looker Dev Sync
    # -------------------------------------------------------------------------

    def _sync_looker_dev(self) -> None:
        """Sync Looker dev environment to the pushed branch.

        This performs a non-destructive branch switch (git checkout).
        User's uncommitted changes are preserved if there are no conflicts.

        Raises:
            LookerAPIError: If sync fails
        """
        # Get Looker credentials
        creds = self._get_looker_credentials()
        if not creds:
            raise LookerAPIError("No Looker credentials available")

        client_id, client_secret = creds

        # Get access token
        access_token = self._get_looker_access_token(client_id, client_secret)

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

                # Step 2: Check if branch exists in Looker
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

                # Step 3: Switch to the branch (non-destructive checkout)
                # Using only 'name' parameter does a checkout, not a hard reset
                switch_response = client.put(
                    f"/projects/{self.config.project_id}/git_branch",
                    json={"name": self.config.branch},
                )

                if switch_response.status_code != 200:
                    raise LookerAPIError(
                        f"Failed to switch branch: {switch_response.text}",
                        status_code=switch_response.status_code,
                    )

                # Step 4: Reset to remote (pull latest)
                # This fetches the latest from origin and resets to it
                reset_response = client.post(
                    f"/projects/{self.config.project_id}/reset_to_remote"
                )

                if reset_response.status_code not in (200, 204):
                    raise LookerAPIError(
                        f"Failed to reset to remote: {reset_response.text}",
                        status_code=reset_response.status_code,
                    )

                self.console.print(
                    f"[green]✓[/green] Looker dev synced to branch '{self.config.branch}'"
                )

        except httpx.HTTPError as e:
            raise LookerAPIError(f"Network error during Looker sync: {e}")

    def _build_looker_explore_url(self, blobs: list[dict[str, str]]) -> str | None:
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

    # -------------------------------------------------------------------------
    # GitHub Operations
    # -------------------------------------------------------------------------

    def _prepare_blobs(self, files: dict[Path, str]) -> list[dict[str, str]]:
        """Transform local file paths to GitHub blob format.

        Args:
            files: Dictionary mapping local paths to content

        Returns:
            List of blob dictionaries with 'path' and 'content' keys
        """
        blobs: list[dict[str, str]] = []

        for local_path, content in files.items():
            # Build GitHub path: config.path + relative path from project
            parts = local_path.parts
            try:
                project_idx = parts.index(self.project)
                relative_parts = parts[project_idx:]
            except ValueError:
                relative_parts = parts[-3:] if len(parts) >= 3 else parts

            relative_path = "/".join(relative_parts)

            if self.config.path:
                github_path = f"{self.config.path.rstrip('/')}/{relative_path}"
            else:
                github_path = relative_path

            blobs.append(
                {
                    "path": github_path,
                    "content": content,
                }
            )

        return blobs

    def _get_or_create_branch(self, client: httpx.Client, base_url: str) -> str:
        """Get branch SHA, creating the branch if it doesn't exist.

        Args:
            client: Configured httpx client
            base_url: Base API URL for the repo

        Returns:
            The branch HEAD commit SHA

        Raises:
            LookerAPIError: If the API request fails
        """
        ref_response = client.get(f"{base_url}/git/ref/heads/{self.config.branch}")

        if ref_response.status_code == 200:
            sha: str = ref_response.json()["object"]["sha"]
            return sha

        if ref_response.status_code != 404:
            self._check_github_response(ref_response, "get branch ref")

        # Branch doesn't exist - prompt to create it
        self.console.print()
        self.console.print(
            f"[yellow]Branch '{self.config.branch}' does not exist[/yellow]"
        )

        repo_response = client.get(base_url)
        self._check_github_response(repo_response, "get repository info")
        default_branch = repo_response.json()["default_branch"]

        import click

        if not click.confirm(
            f"Create '{self.config.branch}' from '{default_branch}'?", default=True
        ):
            raise LookerAPIError(
                f"Branch creation cancelled. Create '{self.config.branch}' manually or "
                f"update sp.yml to use an existing branch.",
                status_code=None,
            )

        self.console.print(f"[dim]Creating branch '{self.config.branch}'...[/dim]")

        default_ref_response = client.get(f"{base_url}/git/ref/heads/{default_branch}")
        self._check_github_response(default_ref_response, "get default branch ref")
        default_sha: str = default_ref_response.json()["object"]["sha"]

        create_ref_response = client.post(
            f"{base_url}/git/refs",
            json={
                "ref": f"refs/heads/{self.config.branch}",
                "sha": default_sha,
            },
        )
        self._check_github_response(create_ref_response, "create branch")

        self.console.print(
            f"[green]✓[/green] Branch '{self.config.branch}' created "
            f"from '{default_branch}'"
        )
        self.console.print()

        return default_sha

    def _create_github_commit(self, token: str, blobs: list[dict[str, str]]) -> str:
        """Create an atomic commit with all files via GitHub API.

        Args:
            token: GitHub Personal Access Token
            blobs: List of blob dictionaries with 'path' and 'content'

        Returns:
            The commit SHA

        Raises:
            LookerAPIError: If the API request fails
        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.GITHUB_API_VERSION,
        }
        base_url = f"{self.GITHUB_API_BASE}/repos/{self.config.repo}"

        with httpx.Client(headers=headers, timeout=30.0) as client:
            current_sha = self._get_or_create_branch(client, base_url)

            commit_response = client.get(f"{base_url}/git/commits/{current_sha}")
            self._check_github_response(commit_response, "get current commit")
            base_tree = commit_response.json()["tree"]["sha"]

            tree_items = [
                {
                    "path": blob["path"],
                    "mode": "100644",
                    "type": "blob",
                    "content": blob["content"],
                }
                for blob in blobs
            ]

            tree_response = client.post(
                f"{base_url}/git/trees",
                json={"base_tree": base_tree, "tree": tree_items},
            )
            self._check_github_response(tree_response, "create tree")
            new_tree_sha = tree_response.json()["sha"]

            commit_message = self.config.commit_message
            if not commit_message.endswith(")"):
                commit_message = f"{commit_message}\n\n{len(blobs)} files updated"

            new_commit_response = client.post(
                f"{base_url}/git/commits",
                json={
                    "message": commit_message,
                    "tree": new_tree_sha,
                    "parents": [current_sha],
                },
            )
            self._check_github_response(new_commit_response, "create commit")
            new_commit_sha: str = new_commit_response.json()["sha"]

            update_ref_response = client.patch(
                f"{base_url}/git/refs/heads/{self.config.branch}",
                json={"sha": new_commit_sha},
            )
            self._check_github_response(update_ref_response, "update branch ref")

            return new_commit_sha

    def _check_github_response(self, response: httpx.Response, action: str) -> None:
        """Check GitHub API response and raise on error.

        Args:
            response: The httpx response
            action: Description of the action for error messages

        Raises:
            LookerAPIError: If the response indicates an error
        """
        if response.status_code >= 400:
            try:
                error_data: dict[str, Any] = response.json()
                message = error_data.get("message", response.text)
            except Exception:
                message = response.text

            if response.status_code == 401:
                raise LookerAPIError(
                    "GitHub authentication failed. Your token may be invalid "
                    "or expired. Create a new token at "
                    "https://github.com/settings/tokens",
                    status_code=401,
                )
            elif response.status_code == 403:
                raise LookerAPIError(
                    f"GitHub permission denied: {message}. "
                    "Ensure your token has 'repo' scope.",
                    status_code=403,
                )
            elif response.status_code == 404:
                if "repository" in action.lower() or "get repository" in action:
                    error_detail = (
                        f"Repository '{self.config.repo}' not found or not accessible."
                    )
                else:
                    error_detail = f"Resource not found: {message}"
                raise LookerAPIError(
                    f"GitHub resource not found while trying to {action}: "
                    f"{error_detail}",
                    status_code=404,
                )
            elif response.status_code == 409:
                raise LookerAPIError(
                    f"GitHub conflict while trying to {action}: {message}. "
                    "The branch may have been updated. Try again.",
                    status_code=409,
                )
            elif response.status_code == 422:
                raise LookerAPIError(
                    f"GitHub validation error while trying to {action}: {message}",
                    status_code=422,
                )
            else:
                raise LookerAPIError(
                    f"GitHub API error ({response.status_code}) while "
                    f"trying to {action}: {message}",
                    status_code=response.status_code,
                )
