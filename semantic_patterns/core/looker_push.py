"""Looker push functionality for semantic-patterns.

This module handles pushing generated LookML to Git and syncing
with Looker's dev environment.
"""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console

if TYPE_CHECKING:
    from semantic_patterns.config import SPConfig

# Module-level console for output
console = Console()


def handle_looker_push(
    config: SPConfig,
    all_files: dict[Path, str],
    *,
    push: bool,
    dry_run: bool,
    debug: bool,
) -> None:
    """Handle Looker push/sync after build completes.

    This function pushes generated LookML files to a Git repository
    and optionally syncs the user's Looker dev environment.

    Args:
        config: Parsed configuration with looker settings
        all_files: Dictionary of file paths to content
        push: If True, skip confirmation prompt
        dry_run: If True, simulate without pushing
        debug: If True, show full stacktraces on error

    Raises:
        click.ClickException: If push fails
    """
    from semantic_patterns.destinations import LookerAPIError, LookerDestination

    looker_cfg = config.looker

    # Show what will be pushed
    console.print()
    console.print("[bold]Looker Push[/bold]")
    console.print(f"  [dim]Repo:[/dim]   {looker_cfg.repo}")
    console.print(f"  [dim]Branch:[/dim] {looker_cfg.branch}")
    console.print(f"  [dim]Files:[/dim]  {len(all_files)}")
    if looker_cfg.looker_sync_enabled:
        console.print(
            f"  [dim]Looker:[/dim] {looker_cfg.base_url} ({looker_cfg.project_id})"
        )

    # Confirm unless --push flag or dry-run
    if not push and not dry_run:
        console.print()
        prompt = "Push to Git"
        if looker_cfg.looker_sync_enabled:
            prompt += " and sync Looker dev"
        prompt += "?"
        if not click.confirm(prompt, default=True):
            console.print("[yellow]Push skipped[/yellow]")
            return

    # Create destination and push
    try:
        dest = LookerDestination(looker_cfg, config.project, console=console)
        result = dest.write(all_files, dry_run=dry_run)

        if dry_run:
            console.print(f"\n[yellow]{result.message}[/yellow]")
        else:
            console.print(f"\n[bold green]{result.message}[/bold green]")
            if result.destination_url:
                console.print(
                    f"[dim]Commit:[/dim] {result.destination_url}", overflow="ignore"
                )
            if result.looker_url:
                console.print(
                    f"[dim]Looker:[/dim] {result.looker_url}", overflow="ignore"
                )

    except LookerAPIError as e:
        if debug:
            console.print(traceback.format_exc())
        console.print(f"\n[red]Looker push failed:[/red] {e}")
        raise click.ClickException(str(e))
    except Exception as e:
        if debug:
            console.print(traceback.format_exc())
        console.print(f"\n[red]Looker push failed:[/red] {e}")
        raise click.ClickException(str(e))
