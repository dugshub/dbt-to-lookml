"""GitHub operations for Looker destination."""

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
)
from semantic_patterns.destinations.looker.errors import LookerAPIError


class GitHubClient:
    """Handle GitHub API operations for pushing LookML."""

    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_API_VERSION = "2022-11-28"

    def __init__(
        self,
        config: LookerConfig,
        project: str,
        console: Console,
    ) -> None:
        """Initialize GitHub client.

        Args:
            config: Looker configuration
            project: Project name (for blob path resolution)
            console: Rich console for output
        """
        self.config = config
        self.project = project
        self.console = console
        self._token: str | None = None

    def get_token(self) -> str | None:
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
            self._token = token
            return token

        else:
            self.console.print("[red]Invalid choice[/red]")
            return None

    def prepare_blobs(self, files: dict[Path, str]) -> list[dict[str, str]]:
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

    def create_commit(self, token: str, blobs: list[dict[str, str]]) -> str:
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
            self._check_response(commit_response, "get current commit")
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
            self._check_response(tree_response, "create tree")
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
            self._check_response(new_commit_response, "create commit")
            new_commit_sha: str = new_commit_response.json()["sha"]

            update_ref_response = client.patch(
                f"{base_url}/git/refs/heads/{self.config.branch}",
                json={"sha": new_commit_sha},
            )
            self._check_response(update_ref_response, "update branch ref")

            return new_commit_sha

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
            self._check_response(ref_response, "get branch ref")

        # Branch doesn't exist - prompt to create it
        self.console.print()
        self.console.print(
            f"[yellow]Branch '{self.config.branch}' does not exist[/yellow]"
        )

        repo_response = client.get(base_url)
        self._check_response(repo_response, "get repository info")
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
        self._check_response(default_ref_response, "get default branch ref")
        default_sha: str = default_ref_response.json()["object"]["sha"]

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

    def _check_response(self, response: httpx.Response, action: str) -> None:
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
