"""Destination adapters for semantic-patterns output.

Destinations handle where generated LookML files are written:
- LocalDestination: Write to local filesystem (default)
- LookerDestination: Push to Git repository and sync Looker dev environment
"""

from semantic_patterns.destinations.base import Destination, WriteResult
from semantic_patterns.destinations.looker import LookerAPIError, LookerDestination

__all__ = [
    "Destination",
    "WriteResult",
    "LookerDestination",
    "LookerAPIError",
]
