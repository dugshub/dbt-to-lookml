"""Base classes and protocols for destination adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class WriteResult:
    """Result of a destination write operation.

    Attributes:
        files_written: List of file paths that were written
        destination_url: Optional URL to the destination (e.g., GitHub commit URL)
        looker_url: Optional URL to view files in Looker IDE
        message: Human-readable summary message
        commit_sha: Git commit SHA if applicable
        metadata: Additional metadata about the write operation
    """

    files_written: list[str]
    destination_url: str | None = None
    looker_url: str | None = None
    message: str | None = None
    commit_sha: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class Destination(Protocol):
    """Protocol for output destinations.

    Destinations handle writing generated files to their target location,
    whether that's a local filesystem, GitHub repository, or other target.
    """

    def write(
        self,
        files: dict[Path, str],
        dry_run: bool = False,
    ) -> WriteResult:
        """Write files to the destination.

        Args:
            files: Dictionary mapping file paths to their content
            dry_run: If True, simulate the write without making changes

        Returns:
            WriteResult with information about what was written
        """
        ...

    def validate(self) -> list[str]:
        """Validate destination configuration.

        Returns:
            List of error messages (empty if valid)
        """
        ...
