"""GitHub destination for pushing LookML to a repository."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from rich.console import Console

from semantic_patterns.config import GitHubConfig
from semantic_patterns.credentials import (
    CredentialType,
    get_credential_store,
    github_device_flow,
)
from semantic_patterns.destinations.base import WriteResult


class GitHubAPIError(Exception):
    """Error from GitHub API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubDestination:
    """Push generated files to a GitHub repository.

    Uses the GitHub API to create atomic commits with all files
    in a single operation. Requires a GitHub Personal Access Token
    with 'repo' scope.

    Example:
        from semantic_patterns.destinations import GitHubDestination
        from semantic_patterns.config import GitHubConfig

        config = GitHubConfig(
            enabled=True,
            repo="myorg/looker-models",
            branch="semantic-patterns/dev",
            path="lookml/",
        )
        dest = GitHubDestination(config, project="my-project")
        result = dest.write(files)
    """

    API_BASE = "https://api.github.com"
    API_VERSION = "2022-11-28"

    def __init__(
        self,
        config: GitHubConfig,
        project: str,
        console: Console | None = None,
    ) -> None:
        """Initialize GitHub destination.

        Args:
            config: GitHub configuration
            project: Project name (used in commit messages)
            console: Rich console for output (optional)
        """
        self.config = config
        self.project = project
        self.console = console or Console()
        self._token: str | None = None

    def write(
        self,
        files: dict[Path, str],
        dry_run: bool = False,
    ) -> WriteResult:
        """Push files to GitHub as a single commit.

        Args:
            files: Dictionary mapping local file paths to their content
            dry_run: If True, simulate without pushing

        Returns:
            WriteResult with commit URL and metadata
        """
        # Validate configuration
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid GitHub configuration: {'; '.join(errors)}")

        # Resolve token
        token = self._get_token()
        if not token:
            raise GitHubAPIError(
                "No GitHub token available. Set GITHUB_TOKEN or run interactively."
            )

        # Transform local paths to GitHub blob paths
        blobs = self._prepare_blobs(files)

        if dry_run:
            repo_ref = f"{self.config.repo}@{self.config.branch}"
            return WriteResult(
                files_written=[b["path"] for b in blobs],
                message=f"Would push {len(blobs)} files to {repo_ref}",
                metadata={
                    "repo": self.config.repo,
                    "branch": self.config.branch,
                    "file_count": str(len(blobs)),
                },
            )

        # Create commit via GitHub API
        commit_sha = self._create_commit(token, blobs)

        repo_ref = f"{self.config.repo}@{self.config.branch}"
        commit_url = f"https://github.com/{self.config.repo}/commit/{commit_sha}"
        return WriteResult(
            files_written=[b["path"] for b in blobs],
            destination_url=commit_url,
            message=f"Pushed {len(blobs)} files to {repo_ref}",
            commit_sha=commit_sha,
            metadata={
                "repo": self.config.repo,
                "branch": self.config.branch,
                "file_count": str(len(blobs)),
            },
        )

    def validate(self) -> list[str]:
        """Validate GitHub configuration.

        Returns:
            List of error messages (empty if valid)
        """
        errors: list[str] = []

        if not self.config.enabled:
            errors.append("GitHub is not enabled")
            return errors

        if not self.config.repo:
            errors.append("github.repo is required")

        if not self.config.branch:
            errors.append("github.branch is required")

        # Defense in depth: re-check protected branches
        if self.config.branch.lower() in self.config.ALWAYS_PROTECTED:
            errors.append(f"Cannot push to protected branch '{self.config.branch}'")

        return errors

    def _get_token(self) -> str | None:
        """Get GitHub token from env, keychain, or device flow.

        Returns:
            GitHub token or None if not available
        """
        if self._token:
            return self._token

        store = get_credential_store(self.console)

        # Check env/keychain first
        token = store.get(CredentialType.GITHUB, prompt_if_missing=False)
        if token:
            self._token = token
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
                self._token = token
                return token
            else:
                # Device flow failed/cancelled
                return None

        elif choice == "2":
            # Manual token entry (legacy method)
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
            self._token = token
            return token

        else:
            self.console.print("[red]Invalid choice[/red]")
            return None

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
            # The local_path is typically: output/project/views/model/file.lkml
            # We want: config.path/project/views/model/file.lkml

            # Find the project folder in the path
            parts = local_path.parts
            try:
                # Look for the project name in the path
                project_idx = parts.index(self.project)
                relative_parts = parts[project_idx:]
            except ValueError:
                # Project not in path, use just the filename parts
                relative_parts = parts[-3:] if len(parts) >= 3 else parts

            relative_path = "/".join(relative_parts)

            # Prepend config.path if specified
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
            GitHubAPIError: If the API request fails
        """
        # Try to get the branch
        ref_response = client.get(f"{base_url}/git/ref/heads/{self.config.branch}")

        # If branch exists, return its SHA
        if ref_response.status_code == 200:
            sha: str = ref_response.json()["object"]["sha"]
            return sha

        # If not 404, it's an unexpected error
        if ref_response.status_code != 404:
            self._check_response(ref_response, "get branch ref")

        # Branch doesn't exist - prompt to create it from default branch
        self.console.print()
        self.console.print(
            f"[yellow]Branch '{self.config.branch}' does not exist[/yellow]"
        )

        # Get the repository's default branch first to show user
        repo_response = client.get(base_url)
        self._check_response(repo_response, "get repository info")
        default_branch = repo_response.json()["default_branch"]

        # Import click here to avoid circular dependency
        import click

        if not click.confirm(
            f"Create '{self.config.branch}' from '{default_branch}'?", default=True
        ):
            raise GitHubAPIError(
                f"Branch creation cancelled. Create '{self.config.branch}' manually or "
                f"update sp.yml to use an existing branch.",
                status_code=None,
            )

        self.console.print(f"[dim]Creating branch '{self.config.branch}'...[/dim]")

        # Get the default branch's HEAD SHA
        default_ref_response = client.get(f"{base_url}/git/ref/heads/{default_branch}")
        self._check_response(default_ref_response, "get default branch ref")
        default_sha: str = default_ref_response.json()["object"]["sha"]

        # Create the new branch
        create_ref_response = client.post(
            f"{base_url}/git/refs",
            json={
                "ref": f"refs/heads/{self.config.branch}",
                "sha": default_sha,
            },
        )
        self._check_response(create_ref_response, "create branch")

        self.console.print(
            f"[green]✓[/green] Branch '{self.config.branch}' created "
            f"from '{default_branch}'"
        )
        self.console.print()

        return default_sha

    def _create_commit(self, token: str, blobs: list[dict[str, str]]) -> str:
        """Create an atomic commit with all files via GitHub API.

        Args:
            token: GitHub Personal Access Token
            blobs: List of blob dictionaries with 'path' and 'content'

        Returns:
            The commit SHA

        Raises:
            GitHubAPIError: If the API request fails
        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
        }
        base_url = f"{self.API_BASE}/repos/{self.config.repo}"

        with httpx.Client(headers=headers, timeout=30.0) as client:
            # 1. Get or create branch
            current_sha = self._get_or_create_branch(client, base_url)

            # 2. Get current commit to find base tree
            commit_response = client.get(f"{base_url}/git/commits/{current_sha}")
            self._check_response(commit_response, "get current commit")
            base_tree = commit_response.json()["tree"]["sha"]

            # 3. Create new tree with all files
            tree_items = [
                {
                    "path": blob["path"],
                    "mode": "100644",  # Regular file
                    "type": "blob",
                    "content": blob["content"],
                }
                for blob in blobs
            ]

            tree_response = client.post(
                f"{base_url}/git/trees",
                json={"base_tree": base_tree, "tree": tree_items},
            )
            self._check_response(tree_response, "create tree")
            new_tree_sha = tree_response.json()["sha"]

            # 4. Create commit
            commit_message = self.config.commit_message
            if not commit_message.endswith(")"):
                # Add file count to message if not already formatted
                commit_message = f"{commit_message}\n\n{len(blobs)} files updated"

            new_commit_response = client.post(
                f"{base_url}/git/commits",
                json={
                    "message": commit_message,
                    "tree": new_tree_sha,
                    "parents": [current_sha],
                },
            )
            self._check_response(new_commit_response, "create commit")
            new_commit_sha: str = new_commit_response.json()["sha"]

            # 5. Update branch ref to point to new commit
            update_ref_response = client.patch(
                f"{base_url}/git/refs/heads/{self.config.branch}",
                json={"sha": new_commit_sha},
            )
            self._check_response(update_ref_response, "update branch ref")

            return new_commit_sha

    def _check_response(self, response: httpx.Response, action: str) -> None:
        """Check API response and raise on error.

        Args:
            response: The httpx response
            action: Description of the action for error messages

        Raises:
            GitHubAPIError: If the response indicates an error
        """
        if response.status_code >= 400:
            try:
                error_data: dict[str, Any] = response.json()
                message = error_data.get("message", response.text)
            except Exception:
                message = response.text

            # Provide helpful error messages for common issues
            if response.status_code == 401:
                raise GitHubAPIError(
                    "GitHub authentication failed. Your token may be invalid "
                    "or expired. Create a new token at "
                    "https://github.com/settings/tokens",
                    status_code=401,
                )
            elif response.status_code == 403:
                raise GitHubAPIError(
                    f"GitHub permission denied: {message}. "
                    "Ensure your token has 'repo' scope.",
                    status_code=403,
                )
            elif response.status_code == 404:
                # More specific error message based on what resource wasn't found
                if "repository" in action.lower() or "get repository" in action:
                    error_detail = (
                        f"Repository '{self.config.repo}' not found or not accessible."
                    )
                else:
                    error_detail = f"Resource not found: {message}"
                raise GitHubAPIError(
                    f"GitHub resource not found while trying to {action}: "
                    f"{error_detail}",
                    status_code=404,
                )
            elif response.status_code == 409:
                raise GitHubAPIError(
                    f"GitHub conflict while trying to {action}: {message}. "
                    "The branch may have been updated. Try again.",
                    status_code=409,
                )
            elif response.status_code == 422:
                raise GitHubAPIError(
                    f"GitHub validation error while trying to {action}: {message}",
                    status_code=422,
                )
            else:
                error_msg = (
                    f"GitHub API error ({response.status_code}) while "
                    f"trying to {action}: {message}"
                )
                raise GitHubAPIError(
                    error_msg,
                    status_code=response.status_code,
                )
