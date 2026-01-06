"""Command-line interface for semantic-patterns."""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import click
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree

from semantic_patterns.config import SPConfig, find_config, load_config

if TYPE_CHECKING:
    from semantic_patterns.adapters.lookml.paths import OutputPaths

console = Console()


def _build_file_tree(files: list[Path], project_path: Path) -> Tree:
    """Build a Rich Tree from generated file paths."""
    tree = Tree(f"[bold]{project_path.name}/[/bold]")
    nodes: dict[str, Tree] = {}

    for f in sorted(files):
        try:
            rel = f.relative_to(project_path)
        except ValueError:
            continue

        parts = rel.parts
        parent = tree

        # Build directory nodes
        for i, part in enumerate(parts[:-1]):
            key = "/".join(parts[: i + 1])
            if key not in nodes:
                nodes[key] = parent.add(f"[blue]{part}/[/blue]")
            parent = nodes[key]

        # Add file with color based on type
        fname = parts[-1]
        if ".explore.lkml" in fname:
            parent.add(f"[yellow]{fname}[/yellow]")
        elif ".model.lkml" in fname:
            parent.add(f"[magenta]{fname}[/magenta]")
        else:
            parent.add(f"[green]{fname}[/green]")

    return tree


@dataclass
class BuildStatistics:
    """Statistics collected during a build."""

    dimensions: int = 0
    measures: int = 0
    metrics: int = 0
    explores: int = 0
    files: int = 0


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
@click.option(
    "--debug",
    is_flag=True,
    help="Show full exception stacktraces for troubleshooting",
)
@click.option(
    "--push",
    is_flag=True,
    help="Push to GitHub without confirmation (when github.enabled=true)",
)
def build(
    config: Path | None, dry_run: bool, verbose: bool, debug: bool, push: bool
) -> None:
    """Generate LookML from semantic models.

    Reads configuration from sp.yml and generates:
    - View files (.view.lkml)
    - Metric refinements (.metrics.view.lkml)
    - Explore files (.explore.lkml) if explores configured
    - Calendar views for date selection

    If github.enabled=true in config, prompts to push to GitHub after build.
    Use --push to skip confirmation.

    Examples:

        # Build using sp.yml in current directory
        sp build

        # Preview without writing files
        sp build --dry-run

        # Use specific config file
        sp build --config ./configs/sp.yml

        # Build and push to GitHub (skip confirmation)
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
            tree = _build_file_tree(files, project_path)
            console.print(tree)

        # GitHub push if enabled
        if cfg.github.enabled:
            _handle_github_push(cfg, all_files, push=push, dry_run=dry_run, debug=debug)

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


def _handle_github_push(
    config: SPConfig,
    all_files: dict[Path, str],
    *,
    push: bool,
    dry_run: bool,
    debug: bool,
) -> None:
    """Handle GitHub push after build completes.

    Args:
        config: Parsed configuration
        all_files: Dictionary of file paths to content
        push: If True, skip confirmation prompt
        dry_run: If True, simulate without pushing
        debug: If True, show full stacktraces
    """
    from semantic_patterns.destinations import GitHubDestination
    from semantic_patterns.destinations.github import GitHubAPIError

    github_cfg = config.github

    # Show what will be pushed
    console.print()
    console.print("[bold]GitHub Push[/bold]")
    console.print(f"  [dim]Repo:[/dim]   {github_cfg.repo}")
    console.print(f"  [dim]Branch:[/dim] {github_cfg.branch}")
    console.print(f"  [dim]Files:[/dim]  {len(all_files)}")

    # Confirm unless --push flag or dry-run
    if not push and not dry_run:
        console.print()
        if not click.confirm("Push to GitHub?", default=True):
            console.print("[yellow]Push skipped[/yellow]")
            return

    # Create destination and push
    try:
        dest = GitHubDestination(github_cfg, config.project, console=console)
        result = dest.write(all_files, dry_run=dry_run)

        if dry_run:
            console.print(f"\n[yellow]{result.message}[/yellow]")
        else:
            console.print(f"\n[bold green]{result.message}[/bold green]")
            if result.destination_url:
                console.print(f"[dim]Commit:[/dim] {result.destination_url}")

    except GitHubAPIError as e:
        if debug:
            console.print(traceback.format_exc())
        console.print(f"\n[red]GitHub push failed:[/red] {e}")
        raise click.ClickException(str(e))
    except Exception as e:
        if debug:
            console.print(traceback.format_exc())
        console.print(f"\n[red]GitHub push failed:[/red] {e}")
        raise click.ClickException(str(e))


def _generate_model_file_content(
    config: SPConfig,
    all_files: dict[Path, str],
    paths: OutputPaths,
) -> str:
    """Generate the .model.lkml file content with domain-structured includes."""
    lines = [f'connection: "{config.model.connection}"']

    if config.model.label:
        lines.append(f'label: "{config.model.label}"')

    lines.append("")

    # Include all view files with relative paths
    view_files = sorted(p for p in all_files.keys() if str(p).endswith(".view.lkml"))
    for view_path in view_files:
        rel_path = paths.relative_path(view_path)
        lines.append(f'include: "{rel_path}"')

    # Include all explore files
    explore_files = sorted(
        p for p in all_files.keys() if str(p).endswith(".explore.lkml")
    )
    for explore_path in explore_files:
        rel_path = paths.relative_path(explore_path)
        lines.append(f'include: "{rel_path}"')

    lines.append("")
    return "\n".join(lines)


def run_build(
    config: SPConfig,
    dry_run: bool = False,
    verbose: bool = False,
) -> tuple[list[Path], BuildStatistics, Path, dict[Path, str]]:
    """
    Execute the build process with domain-based output structure.

    Args:
        config: Parsed SPConfig
        dry_run: If True, don't write files
        verbose: If True, show detailed output

    Returns:
        Tuple of (list of generated file paths, build statistics,
        project_path, all_files)
    """
    from semantic_patterns.adapters.lookml import LookMLGenerator
    from semantic_patterns.adapters.lookml.explore_generator import ExploreGenerator
    from semantic_patterns.adapters.lookml.paths import OutputPaths
    from semantic_patterns.adapters.lookml.types import (
        ExploreConfig as LookMLExploreConfig,
    )
    from semantic_patterns.domain import ProcessedModel
    from semantic_patterns.ingestion import DbtLoader, DbtMapper, DomainBuilder
    from semantic_patterns.manifest import (
        ModelSummary,
        OutputInfo,
        SPManifest,
        compute_config_hash,
        compute_content_hash,
    )

    view_prefix = config.options.view_prefix
    explore_prefix = config.options.effective_explore_prefix
    stats = BuildStatistics()

    # Initialize output paths with domain-based structure
    paths = OutputPaths(project=config.project, base_path=config.output_path)

    # Parse semantic models
    console.print(f"[dim]Input:[/dim]  {config.input_path}")
    console.print(f"[dim]Output:[/dim] {paths.project_path}")
    console.print()

    models: list[ProcessedModel] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        # Loading models
        task = progress.add_task("Loading semantic models...", total=None)

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
                builder.add_document(doc)
            models = builder.build()
        else:
            # Use native semantic-patterns format
            models = DomainBuilder.from_directory(config.input_path)

        progress.update(task, completed=True)

    if not models:
        raise click.ClickException(f"No semantic models found in {config.input_path}")

    # Collect statistics and model summaries
    model_summaries: list[ModelSummary] = []
    for model in models:
        stats.dimensions += len(model.dimensions)
        stats.measures += len(model.measures)
        stats.metrics += len(model.metrics)
        model_summaries.append(
            ModelSummary(
                name=model.name,
                dimension_count=len(model.dimensions),
                measure_count=len(model.measures),
                metric_count=len(model.metrics),
                entities=[e.name for e in model.entities],
            )
        )

    if verbose:
        console.print(f"[dim]Models:[/dim]  {len(models)} semantic models")
        for model in models:
            dims_count = len(model.dimensions)
            metrics_count = len(model.metrics)
            console.print(
                f"          [cyan]{model.name}[/cyan] "
                f"[dim]({dims_count} dims, {metrics_count} metrics)[/dim]"
            )

    # Apply view prefix to model names BEFORE generation
    # This ensures view names, refinements, and join references all use prefixed names
    if view_prefix:
        for model in models:
            model.name = f"{view_prefix}{model.name}"

    # Create model lookup (with prefixed names)
    model_dict = {m.name: m for m in models}

    # Generate views
    generator = LookMLGenerator(dialect=config.options.dialect)
    all_files: dict[Path, str] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Generating view files...", total=len(models))

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

            files = generator.generate_model_with_paths(model, paths)
            all_files.update(files)
            progress.advance(task)

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
                fact_model=(f"{view_prefix}{e.fact}" if view_prefix else e.fact),
                label=e.label,
                description=e.description,
                join_exclusions=e.join_exclusions,
            )
            for e in config.explores
        ]

        explore_gen = ExploreGenerator(dialect=config.options.dialect)
        explore_files = explore_gen.generate_with_paths(
            explore_configs, model_dict, paths
        )

        all_files.update(explore_files)
        stats.explores = len(config.explores)

    # Generate model file (rollup with includes)
    model_content = _generate_model_file_content(config, all_files, paths)
    model_file_path = paths.model_file_path()
    all_files[model_file_path] = model_content

    # Write files
    written: list[Path] = []
    stats.files = len(all_files)

    if not dry_run:
        # Create directory structure
        paths.ensure_directories()

        # Create domain folders for each model
        for model in models:
            paths.ensure_view_domain(model.name)

        # Also create domain folders for calendar views
        for e in config.explores:
            explore_name = (
                f"{explore_prefix}{e.effective_name}"
                if explore_prefix
                else e.effective_name
            )
            calendar_name = f"{explore_name}_calendar"
            paths.ensure_view_domain(calendar_name)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Writing files...", total=len(all_files))

            for file_path, content in all_files.items():
                # Ensure parent directory exists (for any edge cases)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
                written.append(file_path)
                progress.advance(task)

        # Generate and write manifest if enabled
        if config.output_options.manifest:
            output_infos = [
                OutputInfo(
                    path=str(p.relative_to(paths.project_path)),
                    hash=compute_content_hash(all_files[p]),
                    type="view"
                    if ".view.lkml" in str(p)
                    else ("explore" if ".explore.lkml" in str(p) else "model"),
                )
                for p in all_files.keys()
            ]

            manifest = SPManifest.create(
                project=config.project,
                config_hash=compute_config_hash(config),
                outputs=output_infos,
                models=model_summaries,
            )
            paths.manifest_path.write_text(manifest.to_json(), encoding="utf-8")
    else:
        # Dry run - just return what would be written
        written = list(all_files.keys())

    return written, stats, paths.project_path, all_files


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

# GitHub destination (optional)
# github:
#   enabled: true
#   repo: myorg/looker-models
#   branch: semantic-patterns/dev    # Cannot be main or master
#   path: lookml/                     # Path within repo (optional)
#   commit_message: "semantic-patterns: Update LookML"
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

    Examples:

        # Validate using sp.yml in current directory
        sp validate

        # Show full stacktraces for debugging
        sp validate --debug
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


if __name__ == "__main__":
    cli()
