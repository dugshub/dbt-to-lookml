"""Abstract base class for all generators."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from rich.console import Console

from dbt_to_lookml.schemas import SemanticModel

console = Console()


class Generator(ABC):
    """Base generator interface for all output formats."""

    def __init__(
        self, validate_syntax: bool = True, format_output: bool = True, **config: Any
    ) -> None:
        """Initialize the generator with common configuration.

        Args:
            validate_syntax: Whether to validate generated output syntax.
            format_output: Whether to format output for readability.
            **config: Additional format-specific configuration.
        """
        self.validate_syntax = validate_syntax
        self.format_output = format_output
        self.config = config

    @abstractmethod
    def generate(self, models: list[SemanticModel]) -> dict[str, str]:
        """Generate output files from semantic models.

        Args:
            models: List of semantic models to generate from.

        Returns:
            Dictionary mapping filename to file content.
        """
        pass

    @abstractmethod
    def validate_output(self, content: str) -> tuple[bool, str]:
        """Validate generated output syntax.

        Args:
            content: Generated content to validate.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is empty string if valid.
        """
        pass

    def write_files(
        self,
        output_dir: Path,
        files: dict[str, str],
        dry_run: bool = False,
        verbose: bool = True,
    ) -> tuple[list[Path], list[str]]:
        """Common file writing logic shared by all generators.

        Args:
            output_dir: Directory to write files to.
            files: Dictionary mapping filename to content.
            dry_run: If True, don't actually write files.
            verbose: If True, print progress messages.

        Returns:
            Tuple of (written_files, validation_errors).
        """
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)

        written_files = []
        validation_errors = []

        for filename, content in files.items():
            file_path = output_dir / filename

            # Validate if enabled
            if self.validate_syntax:
                is_valid, error_msg = self.validate_output(content)
                if not is_valid:
                    validation_errors.append(f"{filename}: {error_msg}")
                    if verbose:
                        console.print(
                            f"    [red]✗[/red] Validation error in {filename}: {error_msg}"
                        )

            if dry_run:
                if verbose:
                    console.print(f"    [yellow]Would create:[/yellow] {file_path}")
                    # Show preview
                    lines = content.strip().split("\n")[:3]
                    console.print("    [dim]Content preview (first 3 lines):[/dim]")
                    for line in lines:
                        console.print(f"    [dim]  {line}[/dim]")
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                if verbose:
                    console.print(f"    [green]✓[/green] Created {file_path.name}")

            written_files.append(file_path)

        return written_files, validation_errors

    def format_content(self, content: str) -> str:
        """Format content for better readability.

        Default implementation returns content as-is.
        Override in subclasses for format-specific formatting.

        Args:
            content: Content to format.

        Returns:
            Formatted content.
        """
        return content
