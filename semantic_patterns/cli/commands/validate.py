"""Validate command for semantic-patterns CLI."""

from __future__ import annotations

import traceback
from pathlib import Path

import click
import yaml
from pydantic import ValidationError
from rich.console import Console

from semantic_patterns.cli import RichCommand
from semantic_patterns.config import find_config, load_config

console = Console()


@click.command(cls=RichCommand)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to sp.yml config file",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Show full exception stacktraces for troubleshooting",
)
def validate(config: Path | None, debug: bool) -> None:
    """Validate configuration and semantic models.

    Checks that:
    - sp.yml is valid
    - Input directory exists
    - Semantic models parse correctly
    - Explore fact models exist

    ## Examples

    Validate using sp.yml in current directory:

        $ sp validate

    Show full stacktraces for debugging:

        $ sp validate --debug

    Validate before building:

        $ sp validate && sp build
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
                raise click.ClickException("No sp.yml found")
            config_path = found_config
            cfg = load_config(config_path)
        console.print(f"[green]Config valid:[/green] {config_path}")
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

    # Check input directory
    if not cfg.input_path.exists():
        console.print(f"[red]Input directory not found:[/red] {cfg.input_path}")
        raise click.ClickException("Input directory not found")
    console.print(f"[green]Input exists:[/green] {cfg.input_path}")

    # Parse models
    try:
        from semantic_patterns.ingestion import DbtLoader, DbtMapper, DomainBuilder

        if cfg.format == "dbt":
            # Load dbt format
            dbt_loader = DbtLoader(cfg.input_path)
            semantic_models, metrics = dbt_loader.load_all()

            # Map and build
            mapper = DbtMapper()
            mapper.add_semantic_models(semantic_models)
            mapper.add_metrics(metrics)
            documents = mapper.get_documents()

            builder = DomainBuilder()
            for doc in documents:
                builder.add_document(doc)
            models = builder.build()
        else:
            models = DomainBuilder.from_directory(cfg.input_path)

        console.print(f"[green]Models valid:[/green] {len(models)} models")

        model_names = {m.name for m in models}
        for model in models:
            console.print(f"  - {model.name}")
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

    # Check explore facts exist
    if cfg.explores:
        for explore in cfg.explores:
            if explore.fact not in model_names:
                console.print(f"[red]Explore fact not found:[/red] {explore.fact}")
                raise click.ClickException(f"Fact model '{explore.fact}' not found")
        console.print(f"[green]Explores valid:[/green] {len(cfg.explores)} explores")

    console.print("\n[bold green]All checks passed[/bold green]")
