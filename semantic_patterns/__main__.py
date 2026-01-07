"""Command-line interface for semantic-patterns."""

from __future__ import annotations

import click

from semantic_patterns.cli import RichGroup
from semantic_patterns.cli.commands import auth, build, init, validate


@click.group(cls=RichGroup)
@click.version_option()
def cli() -> None:
    """Transform semantic models into BI tool patterns.

    A CLI tool for generating LookML views and explores from semantic models.
    Supports both native semantic-patterns format and dbt Semantic Layer.

    ## Quick Start

    Create a config file:

        $ sp init

    Generate LookML from semantic models:

        $ sp build

    Validate your configuration:

        $ sp validate

    ## Common Workflows

    **Development workflow with dry-run preview:**

        $ sp build --dry-run --verbose

    **Production build and push to Looker:**

        $ sp build --push

    **Build with specific config:**

        $ sp build --config ./configs/production.yml

    **Validate before building:**

        $ sp validate && sp build

    ## Authentication

    Manage credentials for GitHub and Looker:

        $ sp auth status          # Check credential status
        $ sp auth test github     # Test GitHub token
        $ sp auth clear all       # Clear all credentials

    For detailed help on any command:

        $ sp COMMAND --help
    """
    pass


# Register commands
cli.add_command(build)
cli.add_command(init)
cli.add_command(validate)
cli.add_command(auth)


if __name__ == "__main__":
    cli()
