"""Init command for semantic-patterns CLI."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from semantic_patterns.cli import RichCommand

console = Console()


@click.command(cls=RichCommand)
def init() -> None:
    """Create a sp.yml config file.

    Generates a starter config file in the current directory
    with sensible defaults.

    ## Examples

    Create a new config file:

        $ sp init

    Then edit sp.yml and run:

        $ sp build
    """
    config_path = Path("sp.yml")

    if config_path.exists():
        console.print(f"[yellow]{config_path} already exists[/yellow]")
        raise click.ClickException("Config file already exists")

    template = """\
# semantic-patterns configuration

# Project name (used for output folder)
# project: my_project

input: ./semantic_models
output: ./lookml
schema: gold

# Looker model file settings
model:
  connection: database

# Explores (optional - omit for views only)
# explores:
#   - fact: rentals
#   - fact: orders
#     label: Order Analysis
#     join_exclusions:
#       - some_model_to_skip

# Output options
output_options:
  manifest: true
  # clean: clean  # or 'warn' or 'ignore'

# Generator options (defaults shown)
options:
  dialect: redshift
  pop_strategy: dynamic
  date_selector: true
  convert_tz: false
  # view_prefix: ""
  # explore_prefix: ""

# Looker destination (optional - pushes to Git and syncs Looker dev)
# looker:
#   enabled: true
#   repo: myorg/looker-models         # Git repo backing Looker project
#   branch: sp-generated              # Branch for generated LookML
#   path: lookml/                     # Path within repo (optional)
#   base_url: https://mycompany.looker.com  # Looker instance (optional)
#   project_id: my_project            # Looker project name (optional)
#   sync_dev: true                    # Sync user's dev environment
"""

    config_path.write_text(template, encoding="utf-8")
    console.print(f"[green]Created {config_path}[/green]")
    console.print("\nEdit the file and run:")
    console.print("  sp build")
