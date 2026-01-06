"""Command-line interface for semantic-patterns."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from semantic_patterns.config import SPConfig, find_config, load_config

console = Console()


@click.group()
@click.version_option()
def cli() -> None:
    """Transform semantic models into BI tool patterns.

    Config-driven generation:

        $ sp build

    Or with explicit config:

        $ sp build --config sp.yml
    """
    pass


@cli.command()
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
def build(config: Path | None, dry_run: bool, verbose: bool) -> None:
    """Generate LookML from semantic models.

    Reads configuration from sp.yml and generates:
    - View files (.view.lkml)
    - Metric refinements (.metrics.view.lkml)
    - Explore files (.explore.lkml) if explores configured
    - Calendar views for date selection

    Examples:

        # Build using sp.yml in current directory
        sp build

        # Preview without writing files
        sp build --dry-run

        # Use specific config file
        sp build --config ./configs/sp.yml
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


def _generate_model_file(
    config: SPConfig,
    all_files: dict[str, str],
    view_prefix: str,
) -> str:
    """Generate the .model.lkml file content."""
    lines = [f'connection: "{config.model.connection}"']

    if config.model.label:
        lines.append(f'label: "{config.model.label}"')

    lines.append("")

    # Include all view files
    view_files = sorted(f for f in all_files.keys() if f.endswith(".view.lkml"))
    for view_file in view_files:
        lines.append(f'include: "/{view_file}"')

    # Include all explore files
    explore_files = sorted(f for f in all_files.keys() if f.endswith(".explore.lkml"))
    for explore_file in explore_files:
        lines.append(f'include: "/{explore_file}"')

    lines.append("")
    return "\n".join(lines)


def run_build(
    config: SPConfig,
    dry_run: bool = False,
    verbose: bool = False,
) -> list[Path]:
    """
    Execute the build process.

    Args:
        config: Parsed SPConfig
        dry_run: If True, don't write files
        verbose: If True, show detailed output

    Returns:
        List of generated file paths
    """
    from semantic_patterns.adapters.lookml import LookMLGenerator
    from semantic_patterns.adapters.lookml.explore_generator import ExploreGenerator
    from semantic_patterns.adapters.lookml.types import (
        ExploreConfig as LookMLExploreConfig,
    )
    from semantic_patterns.ingestion import DbtLoader, DbtMapper, DomainBuilder

    view_prefix = config.options.view_prefix
    explore_prefix = config.options.effective_explore_prefix

    # Parse semantic models
    console.print(f"[blue]Input:[/blue] {config.input_path}")
    console.print(f"[blue]Format:[/blue] {config.format}")

    if config.format == "dbt":
        # Load dbt format and transform to our format
        dbt_loader = DbtLoader(config.input_path)
        semantic_models, metrics = dbt_loader.load_all()

        # Map dbt format to our format
        mapper = DbtMapper()
        mapper.add_semantic_models(semantic_models)
        mapper.add_metrics(metrics)
        documents = mapper.get_documents()

        # Build domain models from mapped documents
        builder = DomainBuilder()
        for doc in documents:
            builder._collect_from_document(doc)
        models = builder.build()
    else:
        # Use native semantic-patterns format
        builder = DomainBuilder()
        models = builder.from_directory(config.input_path)

    if not models:
        raise click.ClickException(f"No semantic models found in {config.input_path}")

    console.print(f"  Found {len(models)} models")

    if verbose:
        for model in models:
            metrics_count = len(model.metrics)
            dims_count = len(model.dimensions)
            console.print(
                f"    {model.name}: {dims_count} dims, {metrics_count} metrics"
            )

    # Apply view prefix to model names BEFORE generation
    # This ensures view names, refinements, and join references all use prefixed names
    if view_prefix:
        for model in models:
            model.name = f"{view_prefix}{model.name}"

    # Create model lookup (with prefixed names)
    model_dict = {m.name: m for m in models}

    # Generate views
    console.print(f"[blue]Output:[/blue] {config.output_path}")

    generator = LookMLGenerator(dialect=config.options.dialect)
    all_files: dict[str, str] = {}

    for model in models:
        # Override schema from config
        if model.data_model:
            from semantic_patterns.domain import DataModel

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
                name=(
                    f"{explore_prefix}{e.effective_name}"
                    if explore_prefix
                    else e.effective_name
                ),
                # Use prefixed fact_model name to match prefixed model names
                fact_model=(
                    f"{view_prefix}{e.fact}" if view_prefix else e.fact
                ),
                label=e.label,
                description=e.description,
            )
            for e in config.explores
        ]

        explore_gen = ExploreGenerator(dialect=config.options.dialect)
        explore_files = explore_gen.generate(explore_configs, model_dict)

        # Note: explore prefix is already in the explore name, so filenames are correct
        all_files.update(explore_files)
        console.print(f"  Generated {len(explore_files)} explore files")

    # Generate model file
    model_content = _generate_model_file(config, all_files, view_prefix)
    model_filename = f"{config.model.name}.model.lkml"
    all_files[model_filename] = model_content
    console.print(f"  Generated model file: {model_filename}")

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
    """Create a sp.yml config file.

    Generates a starter config file in the current directory
    with sensible defaults.
    """
    config_path = Path("sp.yml")

    if config_path.exists():
        console.print(f"[yellow]{config_path} already exists[/yellow]")
        raise click.ClickException("Config file already exists")

    template = """\
# semantic-patterns configuration

input: ./semantic_models
output: ./lookml
schema: gold

# Looker model file settings
model:
  name: semantic_model
  connection: database

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
  convert_tz: false
  # view_prefix: ""
  # explore_prefix: ""
"""

    config_path.write_text(template, encoding="utf-8")
    console.print(f"[green]Created {config_path}[/green]")
    console.print("\nEdit the file and run:")
    console.print("  sp build")


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to sp.yml config file",
)
def validate(config: Path | None) -> None:
    """Validate configuration and semantic models.

    Checks that:
    - sp.yml is valid
    - Input directory exists
    - Semantic models parse correctly
    - Explore fact models exist
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
                builder._collect_from_document(doc)
            models = builder.build()
        else:
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
                console.print(f"[red]Explore fact not found:[/red] {explore.fact}")
                raise click.ClickException(f"Fact model '{explore.fact}' not found")
        console.print(f"[green]Explores valid:[/green] {len(cfg.explores)} explores")

    console.print("\n[bold green]All checks passed[/bold green]")


if __name__ == "__main__":
    cli()
