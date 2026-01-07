"""Looker destination for pushing LookML and syncing dev environments.

This package handles:
- GitHub operations (pushing LookML files)
- Looker API operations (authentication, validation)
- Dev environment synchronization (branch switching)
"""

from semantic_patterns.credentials import register_credential_env_var
from semantic_patterns.destinations.looker.client import LookerClient
from semantic_patterns.destinations.looker.destination import LookerDestination
from semantic_patterns.destinations.looker.errors import LookerAPIError
from semantic_patterns.destinations.looker.github import GitHubClient
from semantic_patterns.destinations.looker.sync import DevSync

# Register Looker credential environment variables
register_credential_env_var("looker-client-id", "LOOKER_CLIENT_ID")
register_credential_env_var("looker-client-secret", "LOOKER_CLIENT_SECRET")

__all__ = [
    "LookerDestination",
    "LookerAPIError",
    "GitHubClient",
    "LookerClient",
    "DevSync",
]
