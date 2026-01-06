"""Destination adapters for semantic-patterns output.

Destinations handle where generated LookML files are written:
- LocalDestination: Write to local filesystem (default)
- GitHubDestination: Push to GitHub repository
"""

from semantic_patterns.destinations.base import Destination, WriteResult
from semantic_patterns.destinations.github import GitHubDestination

__all__ = [
    "Destination",
    "WriteResult",
    "GitHubDestination",
]
