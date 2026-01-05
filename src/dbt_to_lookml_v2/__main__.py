"""Command-line interface for dbt-to-lookml v2."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from dbt_to_lookml_v2.config import D2LConfig, find_config, load_config

console = Console()


@click.group()
@click.version_option()
def cli() -> None:
    """Convert dbt semantic models to LookML.

    Config-driven generation from d2l.yml:

        $ d2l build

    Or with explicit config:

        $ d2l build --config path/to/d2l.yml
    """
    pass


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to d2l.yml config file (auto-detected if not specified)",
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
def build(config: Path | None, dry_run: bool, verbose: bool) -> None:
    """Generate LookML from semantic models.

    Reads configuration from d2l.yml and generates:
    - View files (.view.lkml)
    - Metric refinements (.metrics.view.lkml)
    - Explore files (.explore.lkml) if explores configured
    - Calendar views for date selection

    Examples:

        # Build using d2l.yml in current directory
        d2l build

        # Preview without writing files
        d2l build --dry-run

        # Use specific config file
        d2l build --config ./configs/d2l.yml
    """
    # Load config
    try:
        if config:
            cfg = load_config(config)
            config_path = config
        else:
            config_path = find_config()
            if config_path is None:
                console.print("[red]No d2l.yml found[/red]")
                console.print("\nCreate a d2l.yml file:")
                console.print("""
[dim]input: ./semantic_models
output: ./lookml
schema: gold

explores:
  - fact: rentals[/dim]
""")
                raise click.ClickException("Config file not found")
            cfg = load_config(config_path)
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        raise click.ClickException(str(e))

    console.print(f"[blue]Config:[/blue] {config_path}")

    if dry_run:
        console.print("[yellow]Dry run mode - no files will be written[/yellow]")

    # Run build
    try:
        files = run_build(cfg, dry_run=dry_run, verbose=verbose)

        if dry_run:
            console.print(f"\n[green]Would generate {len(files)} files[/green]")
        else:
            console.print(f"\n[green]Generated {len(files)} files[/green]")

        if verbose or dry_run:
            for f in sorted(files):
                console.print(f"  {f}")

    except Exception as e:
        console.print(f"[red]Build failed:[/red] {e}")
        raise click.ClickException(str(e))


def run_build(
    config: D2LConfig,
    dry_run: bool = False,
    verbose: bool = False,
) -> list[Path]:
    """
    Execute the build process.

    Args:
        config: Parsed D2LConfig
        dry_run: If True, don't write files
        verbose: If True, show detailed output

    Returns:
        List of generated file paths
    """
    from dbt_to_lookml_v2.adapters.lookml import LookMLGenerator
    from dbt_to_lookml_v2.adapters.lookml.explore_generator import ExploreGenerator
    from dbt_to_lookml_v2.adapters.lookml.types import ExploreConfig as LookMLExploreConfig
    from dbt_to_lookml_v2.ingestion import DomainBuilder

    # Parse semantic models
    console.print(f"[blue]Input:[/blue] {config.input_path}")
    builder = DomainBuilder()
    models = builder.from_directory(config.input_path)

    if not models:
        raise click.ClickException(f"No semantic models found in {config.input_path}")

    console.print(f"  Found {len(models)} models")

    if verbose:
        for model in models:
            metrics_count = len(model.metrics)
            dims_count = len(model.dimensions)
            console.print(f"    {model.name}: {dims_count} dims, {metrics_count} metrics")

    # Create model lookup
    model_dict = {m.name: m for m in models}

    # Generate views
    console.print(f"[blue]Output:[/blue] {config.output_path}")

    generator = LookMLGenerator(dialect=config.options.dialect)
    all_files: dict[str, str] = {}

    for model in models:
        # Override schema from config
        if model.data_model:
            # Create new data model with schema override
            from dbt_to_lookml_v2.domain import DataModel
            model.data_model = DataModel(
                name=model.data_model.name,
                schema_name=config.schema_name,
                table=model.data_model.table,
                connection=model.data_model.connection,
            )

        files = generator.generate_model(model)
        all_files.update(files)

    console.print(f"  Generated {len(all_files)} view files")

    # Generate explores if configured
    if config.explores:
        explore_configs = [
            LookMLExploreConfig(
                name=e.effective_name,
                fact_model=e.fact,
                label=e.label,
                description=e.description,
            )
            for e in config.explores
        ]

        explore_gen = ExploreGenerator(dialect=config.options.dialect)
        explore_files = explore_gen.generate(explore_configs, model_dict)
        all_files.update(explore_files)

        console.print(f"  Generated {len(explore_files)} explore files")

    # Write files
    output_path = config.output_path
    written: list[Path] = []

    if not dry_run:
        output_path.mkdir(parents=True, exist_ok=True)

        for filename, content in all_files.items():
            file_path = output_path / filename
            file_path.write_text(content, encoding="utf-8")
            written.append(file_path)
    else:
        # Dry run - just return what would be written
        written = [output_path / f for f in all_files.keys()]

    return written


@cli.command()
def init() -> None:
    """Create a d2l.yml config file.

    Generates a starter config file in the current directory
    with sensible defaults.
    """
    config_path = Path("d2l.yml")

    if config_path.exists():
        console.print(f"[yellow]{config_path} already exists[/yellow]")
        raise click.ClickException("Config file already exists")

    template = """\
# dbt-to-lookml configuration
# https://github.com/your-org/dbt-to-lookml

input: ./semantic_models
output: ./lookml
schema: gold

# Explores (optional - omit for views only)
# explores:
#   - fact: rentals
#   - fact: orders
#     label: Order Analysis

# Generator options (defaults shown)
options:
  dialect: redshift
  pop_strategy: dynamic
  date_selector: true
"""

    config_path.write_text(template, encoding="utf-8")
    console.print(f"[green]Created {config_path}[/green]")
    console.print("\nEdit the file and run:")
    console.print("  d2l build")


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to d2l.yml config file",
)
def validate(config: Path | None) -> None:
    """Validate configuration and semantic models.

    Checks that:
    - d2l.yml is valid
    - Input directory exists
    - Semantic models parse correctly
    - Explore fact models exist
    """
    from dbt_to_lookml_v2.ingestion import DomainBuilder

    # Load config
    try:
        if config:
            cfg = load_config(config)
            config_path = config
        else:
            config_path = find_config()
            if config_path is None:
                raise click.ClickException("No d2l.yml found")
            cfg = load_config(config_path)
        console.print(f"[green]Config valid:[/green] {config_path}")
    except Exception as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise click.ClickException(str(e))

    # Check input directory
    if not cfg.input_path.exists():
        console.print(f"[red]Input directory not found:[/red] {cfg.input_path}")
        raise click.ClickException("Input directory not found")
    console.print(f"[green]Input exists:[/green] {cfg.input_path}")

    # Parse models
    try:
        builder = DomainBuilder()
        models = builder.from_directory(cfg.input_path)
        console.print(f"[green]Models valid:[/green] {len(models)} models")

        model_names = {m.name for m in models}
        for model in models:
            console.print(f"  - {model.name}")
    except Exception as e:
        console.print(f"[red]Parse error:[/red] {e}")
        raise click.ClickException(str(e))

    # Check explore facts exist
    if cfg.explores:
        for explore in cfg.explores:
            if explore.fact not in model_names:
                console.print(
                    f"[red]Explore fact not found:[/red] {explore.fact}"
                )
                raise click.ClickException(f"Fact model '{explore.fact}' not found")
        console.print(f"[green]Explores valid:[/green] {len(cfg.explores)} explores")

    console.print("\n[bold green]All checks passed[/bold green]")


if __name__ == "__main__":
    cli()
