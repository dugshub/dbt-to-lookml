"""Preview and confirmation utilities for CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


@dataclass
class PreviewData:
    """Structured data for command preview display.

    Attributes:
        input_dir: Path to input directory
        output_dir: Path to output directory
        schema: Database schema name
        input_file_count: Number of YAML files found
        estimated_views: Estimated number of view files
        estimated_explores: Number of explores files (typically 1)
        estimated_models: Number of model files (typically 1)
        command_parts: List of command components for display
        additional_config: Dict of additional configuration options
    """

    input_dir: Path
    output_dir: Path
    schema: str
    input_file_count: int
    estimated_views: int
    estimated_explores: int
    estimated_models: int
    command_parts: list[str]
    additional_config: dict[str, Any]


def count_yaml_files(directory: Path) -> int:
    """Count YAML files recursively in a directory.

    Args:
        directory: Path to directory to scan (searched recursively)

    Returns:
        Number of .yml and .yaml files found
    """
    yml_files = list(directory.rglob("*.yml"))
    yaml_files = list(directory.rglob("*.yaml"))
    return len(yml_files) + len(yaml_files)


def estimate_output_files(input_file_count: int) -> tuple[int, int, int]:
    """Estimate number of output files to be generated.

    Args:
        input_file_count: Number of input YAML files

    Returns:
        Tuple of (views, explores, models) counts
        - views: Equal to input file count (1 view per semantic model)
        - explores: Always 1 (consolidated explores file)
        - models: Always 1 (consolidated model file)
    """
    views = input_file_count
    explores = 1  # Single explores.lkml file
    models = 1  # Single .model.lkml file
    return views, explores, models


def format_command_parts(
    command_name: str,
    input_dir: Path,
    output_dir: Path,
    schema: str,
    view_prefix: str = "",
    explore_prefix: str = "",
    connection: str = "",
    model_name: str = "",
    convert_tz: bool | None = None,
    dry_run: bool = False,
    no_validation: bool = False,
    no_formatting: bool = False,
    show_summary: bool = False,
) -> list[str]:
    """Format command into parts for display.

    Args:
        command_name: Base command (e.g., "dbt-to-lookml generate")
        input_dir: Input directory path
        output_dir: Output directory path
        schema: Database schema name
        view_prefix: Optional view prefix
        explore_prefix: Optional explore prefix
        connection: Looker connection name
        model_name: Model file name
        convert_tz: Timezone conversion setting
        dry_run: Dry run flag
        no_validation: Skip validation flag
        no_formatting: Skip formatting flag
        show_summary: Show summary flag

    Returns:
        List of command parts for line-wrapped display
    """
    parts = [command_name]

    # Required arguments
    parts.append(f"-i {input_dir}")
    parts.append(f"-o {output_dir}")
    parts.append(f"-s {schema}")

    # Optional arguments (only add if non-default)
    if view_prefix:
        parts.append(f"--view-prefix {view_prefix}")
    if explore_prefix:
        parts.append(f"--explore-prefix {explore_prefix}")
    if connection and connection != "redshift_test":
        parts.append(f"--connection {connection}")
    if model_name and model_name != "semantic_model":
        parts.append(f"--model-name {model_name}")

    # Boolean flags
    if convert_tz is True:
        parts.append("--convert-tz")
    elif convert_tz is False:
        parts.append("--no-convert-tz")

    if dry_run:
        parts.append("--dry-run")
    if no_validation:
        parts.append("--no-validation")
    if no_formatting:
        parts.append("--no-formatting")
    if show_summary:
        parts.append("--show-summary")

    return parts


class CommandPreview:
    """Generates rich-formatted preview panels for CLI commands."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize preview generator.

        Args:
            console: Rich console for output (creates new if None)
        """
        self.console = console or Console()

    def render_preview_panel(self, preview_data: PreviewData) -> Panel:
        """Render a preview panel with command details.

        Args:
            preview_data: Structured preview data

        Returns:
            Rich Panel object ready for display
        """
        # Build content sections
        lines = []

        # Input/Output section
        lines.append(
            f"[bold cyan]Input:[/bold cyan]  {preview_data.input_dir} "
            f"([green]{preview_data.input_file_count} YAML files[/green])"
        )
        lines.append(f"[bold cyan]Output:[/bold cyan] {preview_data.output_dir}")
        lines.append(f"[bold cyan]Schema:[/bold cyan] {preview_data.schema}")

        # Additional config (if present)
        if preview_data.additional_config:
            lines.append("")
            lines.append("[bold cyan]Configuration:[/bold cyan]")
            for key, value in preview_data.additional_config.items():
                lines.append(f"  • {key}: {value}")

        # Estimated output section
        lines.append("")
        lines.append("[bold cyan]Estimated output:[/bold cyan]")
        lines.append(f"  • [green]{preview_data.estimated_views}[/green] view files")
        lines.append(
            f"  • [green]{preview_data.estimated_explores}[/green] explores file"
        )
        lines.append(f"  • [green]{preview_data.estimated_models}[/green] model file")

        content = "\n".join(lines)

        # Create panel
        panel = Panel(
            content,
            title="[bold white]Command Preview[/bold white]",
            border_style="cyan",
            padding=(1, 2),
        )

        return panel

    def render_command_syntax(self, command_parts: list[str]) -> Syntax:
        """Render command with syntax highlighting.

        Args:
            command_parts: List of command components

        Returns:
            Syntax object with highlighted shell command
        """
        command_text = " \\\n  ".join(command_parts)
        return Syntax(
            command_text,
            "bash",
            theme="monokai",
            line_numbers=False,
            word_wrap=True,
        )

    def show(self, preview_data: PreviewData) -> None:
        """Display preview panel and command syntax.

        Args:
            preview_data: Structured preview data
        """
        panel = self.render_preview_panel(preview_data)
        self.console.print(panel)

        # Show command separately with syntax highlighting
        self.console.print()
        syntax = self.render_command_syntax(preview_data.command_parts)
        self.console.print(syntax)


def show_preview_and_confirm(
    preview_data: PreviewData,
    auto_confirm: bool = False,
) -> bool:
    """Show preview panel and prompt for confirmation.

    Args:
        preview_data: Structured preview data
        auto_confirm: Skip confirmation prompt (--yes flag)

    Returns:
        True if user confirmed (or auto_confirm=True), False otherwise
    """
    preview = CommandPreview()
    preview.show(preview_data)

    if auto_confirm:
        console.print("\n[yellow]Auto-confirming (--yes flag)[/yellow]")
        return True

    console.print()
    response = console.input(
        "[bold yellow]Execute this command?[/bold yellow] [dim][Y/n][/dim]: "
    )

    # Default to Yes (empty response = yes)
    response_lower = response.strip().lower()
    confirmed = response_lower in ("y", "yes", "")

    if not confirmed:
        console.print("[yellow]Command execution cancelled[/yellow]")

    return confirmed
