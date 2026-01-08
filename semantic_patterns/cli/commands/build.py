"""Build command for semantic-patterns CLI."""

from __future__ import annotations

import traceback
from pathlib import Path

import click
import yaml
from pydantic import ValidationError
from rich.console import Console

from semantic_patterns.cli import RichCommand
from semantic_patterns.cli.utils import build_file_tree
from semantic_patterns.config import find_config, load_config
from semantic_patterns.core.builder import run_build
from semantic_patterns.core.looker_push import handle_looker_push

console = Console()


@click.command(cls=RichCommand)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to sp.yml config file (auto-detected if not specified)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be generated without writing files",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed output",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Show full exception stacktraces for troubleshooting",
)
@click.option(
    "--push",
    is_flag=True,
    help="Push to Looker without confirmation (when looker.enabled=true)",
)
def build(
    config: Path | None,
    dry_run: bool,
    verbose: bool,
    debug: bool,
    push: bool,
) -> None:
    """Generate LookML from semantic models.

    Reads configuration from sp.yml and generates:
    - View files (.view.lkml)
    - Metric refinements (.metrics.view.lkml)
    - Explore files (.explore.lkml) if explores configured
    - Calendar views for date selection

    If looker.enabled=true in config, prompts to push to Git and sync Looker
    dev environment after build. Use --push to skip confirmation.

    Examples:

        # Build using sp.yml in current directory
        sp build

        # Preview without writing files
        sp build --dry-run

        # Use specific config file
        sp build --config ./configs/sp.yml

        # Build and push to Looker (skip confirmation)
        sp build --push

        # Show full stacktraces for debugging
        sp build --debug
    """
    # Load config
    config_path: Path
    try:
        if config:
            cfg = load_config(config)
            config_path = config
        else:
            found_config = find_config()
            if found_config is None:
                console.print("[red]No sp.yml found[/red]")
                console.print("\nCreate a sp.yml file:")
                console.print("""
[dim]input: ./semantic_models
output: ./lookml
schema: gold

explores:
  - fact: rentals[/dim]
""")
                raise click.ClickException("Config file not found")
            config_path = found_config
            cfg = load_config(config_path)
    except FileNotFoundError as e:
        if debug:
            console.print(traceback.format_exc())
        console.print(f"[red]Config file not found:[/red] {e}")
        raise click.ClickException(str(e))
    except yaml.YAMLError as e:
        if debug:
            console.print(traceback.format_exc())
        console.print(f"[red]YAML parsing error:[/red] {e}")
        raise click.ClickException(str(e))
    except ValidationError as e:
        if debug:
            console.print(traceback.format_exc())
        console.print(f"[red]Config validation error:[/red] {e}")
        raise click.ClickException(str(e))

    console.print()
    console.print("[bold]semantic-patterns[/bold]", highlight=False)
    console.print()
    console.print(f"[dim]Config:[/dim] {config_path}")

    if dry_run:
        console.print("[yellow]Dry run mode[/yellow]")
        console.print()

    # Run build
    try:
        files, stats, project_path, all_files = run_build(
            cfg, dry_run=dry_run, verbose=verbose
        )

        # Summary line
        action = "Would generate" if dry_run else "Generated"
        console.print(
            f"\n[bold green]{action} {stats.files} files[/bold green] "
            f"[dim]({stats.dimensions} dims, {stats.measures} measures, "
            f"{stats.metrics} metrics, {stats.explores} explores)[/dim]"
        )

        # Show file tree in verbose/dry-run mode
        if verbose or dry_run:
            console.print()
            tree = build_file_tree(files, project_path)
            console.print(tree)

        # Looker push/sync if enabled
        if cfg.looker.enabled:
            handle_looker_push(cfg, all_files, push=push, dry_run=dry_run, debug=debug)

    except FileNotFoundError as e:
        if debug:
            console.print(traceback.format_exc())
        console.print(f"[red]File not found:[/red] {e}")
        raise click.ClickException(str(e))
    except yaml.YAMLError as e:
        if debug:
            console.print(traceback.format_exc())
        console.print(f"[red]YAML parsing error:[/red] {e}")
        raise click.ClickException(str(e))
    except ValidationError as e:
        if debug:
            console.print(traceback.format_exc())
        console.print(f"[red]Model validation error:[/red] {e}")
        raise click.ClickException(str(e))
