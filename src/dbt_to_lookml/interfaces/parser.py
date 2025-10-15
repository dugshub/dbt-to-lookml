"""Abstract base class for all parsers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List

import yaml

from dbt_to_lookml.schemas import SemanticModel


class Parser(ABC):
    """Base parser interface for all semantic layer formats."""

    def __init__(self, strict_mode: bool = False) -> None:
        """Initialize the parser.

        Args:
            strict_mode: If True, raise errors on validation issues.
                        If False, log warnings and continue.
        """
        self.strict_mode = strict_mode

    @abstractmethod
    def parse_file(self, path: Path) -> List[SemanticModel]:
        """Parse a single file into semantic models.

        Args:
            path: Path to the file to parse.

        Returns:
            List of parsed semantic models.
        """
        pass

    @abstractmethod
    def parse_directory(self, path: Path) -> List[SemanticModel]:
        """Parse all files in a directory.

        Args:
            path: Path to the directory to parse.

        Returns:
            List of all parsed semantic models.
        """
        pass

    @abstractmethod
    def validate(self, content: Dict[str, Any]) -> bool:
        """Validate format-specific schema.

        Args:
            content: Parsed content to validate.

        Returns:
            True if valid, False otherwise.
        """
        pass

    # Common utility methods
    def read_yaml(self, path: Path) -> Dict[str, Any]:
        """Shared YAML reading logic.

        Args:
            path: Path to YAML file.

        Returns:
            Parsed YAML content as dictionary.
        """
        with open(path, encoding='utf-8') as f:
            return yaml.safe_load(f)

    def handle_error(self, error: Exception, context: str = "") -> None:
        """Common error handling based on strict mode.

        Args:
            error: The exception that occurred.
            context: Additional context about where the error occurred.

        Raises:
            Exception: Re-raises the error if in strict mode.
        """
        if self.strict_mode:
            raise error
        else:
            print(f"Warning: {context}: {error}")