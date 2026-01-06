"""Interactive prompts for first-run configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import click
import yaml
from rich.console import Console

console = Console()

CleanMode = Literal["clean", "warn", "ignore"]


def prompt_for_clean_setting(config_path: Path) -> CleanMode:
    """
    Prompt user for clean setting on first run.

    Returns:
        "clean" for auto-clean, "warn" for warn-only, "ignore" to skip
    """
    console.print("\n[bold yellow]First-run setup[/bold yellow]")
    console.print(
        "\nHow should semantic-patterns handle existing files in the output directory?"
    )
    console.print("")
    console.print("  [bold]1.[/bold] Clean automatically - Remove orphaned files")
    console.print("  [bold]2.[/bold] Warn only - Show orphaned files but keep them")
    console.print("  [bold]3.[/bold] Ignore - Don't track orphaned files")
    console.print("")

    choice = click.prompt(
        "Choose an option",
        type=click.Choice(["1", "2", "3"]),
        default="1",
    )

    clean_value: CleanMode
    if choice == "1":
        clean_value = "clean"
    elif choice == "2":
        clean_value = "warn"
    else:
        clean_value = "ignore"

    # Ask if they want to save this choice
    save = click.confirm(
        "\nSave this choice to sp.yml?",
        default=True,
    )

    if save:
        _update_config_clean_setting(config_path, clean_value)
        console.print(f"[green]Saved to {config_path}[/green]")

    return clean_value


def _update_config_clean_setting(config_path: Path, clean_value: CleanMode) -> None:
    """Update sp.yml with the clean setting."""
    content = config_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    if "output_options" not in data:
        data["output_options"] = {}

    data["output_options"]["clean"] = clean_value

    # Write back preserving general structure
    config_path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def confirm_overwrite_modified(modified_files: list[str]) -> bool:
    """
    Prompt user to confirm overwriting modified files.

    Args:
        modified_files: List of file paths that have been modified

    Returns:
        True if user confirms, False otherwise
    """
    console.print("\n[yellow]Modified files detected:[/yellow]")
    for f in modified_files[:10]:  # Show first 10
        console.print(f"  - {f}")
    if len(modified_files) > 10:
        console.print(f"  ... and {len(modified_files) - 10} more")

    console.print(
        "\nThese files were modified since last generation and will be overwritten."
    )

    return click.confirm("Continue?", default=True)


def confirm_clean_orphaned(orphaned_files: list[str]) -> bool:
    """
    Prompt user to confirm removing orphaned files.

    Args:
        orphaned_files: List of file paths that are no longer generated

    Returns:
        True if user confirms, False otherwise
    """
    console.print("\n[yellow]Orphaned files detected:[/yellow]")
    for f in orphaned_files[:10]:  # Show first 10
        console.print(f"  - {f}")
    if len(orphaned_files) > 10:
        console.print(f"  ... and {len(orphaned_files) - 10} more")

    console.print("\nThese files are no longer generated and will be removed.")

    return click.confirm("Continue?", default=True)
