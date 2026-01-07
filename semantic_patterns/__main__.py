"""Command-line interface for semantic-patterns."""

from __future__ import annotations

import os
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
            tree = _build_file_tree(files, project_path)
            console.print(tree)

        # Looker push/sync if enabled
        if cfg.looker.enabled:
            _handle_looker_push(cfg, all_files, push=push, dry_run=dry_run, debug=debug)

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


def _handle_looker_push(
    config: SPConfig,
    all_files: dict[Path, str],
    *,
    push: bool,
    dry_run: bool,
    debug: bool,
) -> None:
    """Handle Looker push/sync after build completes.

    Args:
        config: Parsed configuration
        all_files: Dictionary of file paths to content
        push: If True, skip confirmation prompt
        dry_run: If True, simulate without pushing
        debug: If True, show full stacktraces
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
        console.print(f"  [dim]Looker:[/dim] {looker_cfg.base_url} ({looker_cfg.project_id})")

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
                console.print(f"[dim]Commit:[/dim] {result.destination_url}", overflow="ignore")
            if result.looker_url:
                console.print(f"[dim]Looker:[/dim] {result.looker_url}", overflow="ignore")

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

    # Ensure all models have data_model (for sql_table_name generation)
    # Must be done BEFORE prefix is applied so table name uses original model name
    from semantic_patterns.domain import ConnectionType, DataModel

    for model in models:
        if not model.data_model:
            # Create data_model using model name as table name
            # Schema will be applied below during generation
            model.data_model = DataModel(
                name=model.name,
                schema_name=config.schema_name,
                table=model.name,  # model name = table name (1:1)
                connection=ConnectionType.REDSHIFT,
            )

    # Apply view prefix to model names BEFORE generation
    # This ensures view names, refinements, and join references all use prefixed names
    if view_prefix:
        for model in models:
            model.name = f"{view_prefix}{model.name}"

    # Create model lookup (with prefixed names)
    model_dict = {m.name: m for m in models}

    # Build model-to-explore mapping for PoP calendar references
    # Maps each model to its parent explore name
    model_to_explore: dict[str, str] = {}
    if config.explores:
        for explore in config.explores:
            # Apply prefixes to explore and fact names
            explore_name = (
                f"{explore_prefix}{explore.effective_name}"
                if explore_prefix
                else explore.effective_name
            )
            fact_model_name = f"{view_prefix}{explore.fact}" if view_prefix else explore.fact

            # Map fact model to its explore
            model_to_explore[fact_model_name] = explore_name

            # Map joined_facts to this parent explore
            for joined_fact in explore.joined_facts:
                joined_fact_name = f"{view_prefix}{joined_fact}" if view_prefix else joined_fact
                model_to_explore[joined_fact_name] = explore_name

    # Generate views
    generator = LookMLGenerator(
        dialect=config.options.dialect,
        model_to_explore=model_to_explore,
    )
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
                # Use prefixed fact name to match prefixed model names
                fact=(f"{view_prefix}{e.fact}" if view_prefix else e.fact),
                label=e.label,
                description=e.description,
                joins=e.joins,
                join_exclusions=e.join_exclusions,
                joined_facts=[
                    f"{view_prefix}{fact}" if view_prefix else fact
                    for fact in e.joined_facts
                ],
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


# ============================================================================
# Auth Command Group
# ============================================================================


@cli.group()
def auth() -> None:
    """Manage authentication credentials."""
    pass


def _get_github_username(token: str) -> str:
    """Fetch GitHub username from token.

    Args:
        token: GitHub personal access token

    Returns:
        The GitHub username

    Raises:
        Exception: If API call fails
    """
    import httpx

    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        response.raise_for_status()
        data: dict[str, str] = response.json()
        return data["login"]


@auth.command()
def status() -> None:
    """Show configured credentials and their status."""
    import httpx

    from semantic_patterns.credentials import CredentialType, get_credential_store

    store = get_credential_store(console)

    console.print()
    console.print("[bold]Credential Status[/bold]")
    console.print()

    # GitHub
    github_token = store.get(CredentialType.GITHUB, prompt_if_missing=False)
    if github_token:
        # Try to fetch user info
        try:
            username = _get_github_username(github_token)
            console.print(f"[green]✓[/green] GitHub:      Configured")
            console.print(f"             User: @{username}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                console.print("[red]✗[/red] GitHub:      Invalid token")
            else:
                console.print(
                    f"[yellow]⚠[/yellow] GitHub:      Error (HTTP {e.response.status_code})"
                )
        except httpx.TimeoutException:
            console.print(
                "[yellow]⚠[/yellow] GitHub:      Configured (network timeout during verification)"
            )
        except Exception:
            console.print(
                "[yellow]⚠[/yellow] GitHub:      Configured (unable to verify)"
            )
    else:
        console.print("[dim]○[/dim] GitHub:      Not configured")

    # Check env var override
    if os.environ.get("GITHUB_TOKEN"):
        console.print(
            "             [yellow]Note: GITHUB_TOKEN env var will override keychain[/yellow]"
        )

    console.print()

    # Looker
    looker_client_id = store.get("looker-client-id", prompt_if_missing=False)
    looker_client_secret = store.get(
        "looker-client-secret", prompt_if_missing=False
    )

    if looker_client_id and looker_client_secret:
        console.print("[green]✓[/green] Looker:      Configured")
        console.print(f"             Client ID: {looker_client_id[:10]}...")
    elif looker_client_id or looker_client_secret:
        console.print(
            "[yellow]⚠[/yellow] Looker:      Partially configured (missing ID or secret)"
        )
    else:
        console.print("[dim]○[/dim] Looker:      Not configured")

    # Check env var overrides
    if os.environ.get("LOOKER_CLIENT_ID") or os.environ.get("LOOKER_CLIENT_SECRET"):
        console.print(
            "             [yellow]Note: LOOKER_* env vars will override keychain[/yellow]"
        )

    console.print()


@auth.command()
@click.argument("service", type=click.Choice(["github", "looker", "all"]))
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def clear(service: str, force: bool) -> None:
    """Clear stored credentials.

    SERVICE: Which credentials to clear (github, looker, or all)

    Examples:

        # Clear GitHub token
        sp auth clear github

        # Clear all credentials
        sp auth clear all
    """
    from semantic_patterns.credentials import CredentialType, get_credential_store

    store = get_credential_store(console)

    # Determine what to clear
    to_clear: list[tuple[str, str]] = []
    if service == "github" or service == "all":
        to_clear.append((CredentialType.GITHUB.value, "GitHub token"))
    if service == "looker" or service == "all":
        to_clear.append(("looker-client-id", "Looker client ID"))
        to_clear.append(("looker-client-secret", "Looker client secret"))

    # Confirm
    if not force:
        console.print()
        console.print("This will clear:")
        for _, label in to_clear:
            console.print(f"  • {label}")
        console.print()

        if not click.confirm("Continue?", default=False):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Clear credentials
    for key, label in to_clear:
        if store.delete(key):
            console.print(f"[green]✓[/green] Cleared {label}")
        else:
            console.print(f"[dim]○[/dim] {label} was not set")

    console.print()
    console.print("[dim]Run 'sp build' to re-authenticate[/dim]")


@auth.command()
@click.argument("service", type=click.Choice(["github", "looker"]))
@click.option("--debug", is_flag=True, help="Show detailed error messages")
def test(service: str, debug: bool) -> None:
    """Test if credentials are valid.

    SERVICE: Which credentials to test (github or looker)

    Examples:

        # Test GitHub token
        sp auth test github

        # Test Looker credentials
        sp auth test looker
    """
    import httpx

    from semantic_patterns.credentials import CredentialType, get_credential_store

    store = get_credential_store(console)

    console.print()

    if service == "github":
        token = store.get(CredentialType.GITHUB, prompt_if_missing=False)
        if not token:
            console.print("[red]✗[/red] No GitHub token configured")
            console.print()
            console.print("[dim]Run 'sp build' to authenticate[/dim]")
            return

        console.print("Testing GitHub credentials...")
        try:
            with httpx.Client(timeout=10.0) as client:
                # Get user info
                user_response = client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                    },
                )

                if user_response.status_code != 200:
                    console.print(
                        f"[red]✗[/red] Invalid token (HTTP {user_response.status_code})"
                    )
                    if debug:
                        console.print(f"[dim]{user_response.text}[/dim]")
                    return

                user_data = user_response.json()
                username = user_data.get("login", "unknown")

                console.print(f"[green]✓[/green] Token is valid")
                console.print(f"[green]✓[/green] User: @{username}")

                # Check token scopes
                scopes = user_response.headers.get("x-oauth-scopes", "")
                if scopes:
                    console.print(f"[green]✓[/green] Scopes: {scopes}")

                    if "repo" not in scopes:
                        console.print(
                            f"[yellow]⚠[/yellow] Warning: 'repo' scope required for pushing"
                        )

        except Exception as e:
            console.print(f"[red]✗[/red] Test failed: {e}")
            if debug:
                console.print(traceback.format_exc())

    elif service == "looker":
        # Load config to get base_url
        try:
            client_id = store.get("looker-client-id", prompt_if_missing=False)
            client_secret = store.get("looker-client-secret", prompt_if_missing=False)

            if not client_id or not client_secret:
                console.print("[red]✗[/red] Looker credentials not configured")
                console.print()
                console.print(
                    "[dim]Run 'sp build --push' to configure Looker credentials[/dim]"
                )
                return

            config_path = find_config()
            if not config_path:
                console.print(
                    "[yellow]⚠[/yellow] No sp.yml found (cannot determine Looker instance)"
                )
                console.print()

            config = load_config(config_path) if config_path else None

            if not config or not config.looker.base_url:
                console.print(
                    "[yellow]⚠[/yellow] Credentials found but not tested"
                )
                console.print(
                    "[dim]Cannot test without looker.base_url in sp.yml[/dim]"
                )
                console.print()
                console.print(
                    "[dim]Credential files exist in keychain only[/dim]"
                )
                return

            console.print(
                f"Testing Looker credentials for {config.looker.base_url}..."
            )

            with httpx.Client(timeout=10.0) as client:
                # Attempt login
                response = client.post(
                    f"{config.looker.base_url}/api/4.0/login",
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                )

                if response.status_code != 200:
                    console.print(
                        f"[red]✗[/red] Authentication failed (HTTP {response.status_code})"
                    )
                    if debug:
                        console.print(f"[dim]{response.text}[/dim]")
                    return

                data = response.json()
                access_token = data.get("access_token")

                console.print(f"[green]✓[/green] Authentication successful")

                # Get current user
                me_response = client.get(
                    f"{config.looker.base_url}/api/4.0/user",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if me_response.status_code == 200:
                    user_data = me_response.json()
                    email = user_data.get("email", "unknown")
                    console.print(f"[green]✓[/green] User: {email}")

                # Check project access (if configured)
                if config.looker.project_id:
                    project_response = client.get(
                        f"{config.looker.base_url}/api/4.0/projects/{config.looker.project_id}",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )

                    if project_response.status_code == 200:
                        console.print(
                            f"[green]✓[/green] Project '{config.looker.project_id}': Access confirmed"
                        )
                    else:
                        console.print(
                            f"[yellow]⚠[/yellow] Project '{config.looker.project_id}': Access denied"
                        )

        except Exception as e:
            console.print(f"[red]✗[/red] Test failed: {e}")
            if debug:
                console.print(traceback.format_exc())

    console.print()


@auth.command()
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def reset(ctx: click.Context, force: bool) -> None:
    """Clear all stored credentials (fresh start).

    Examples:

        # Clear all credentials
        sp auth reset
    """
    # Invoke the clear command with service="all"
    ctx.invoke(clear, service="all", force=force)


@auth.command()
def whoami() -> None:
    """Show current authenticated user identity.

    Examples:

        # Show who you're authenticated as
        sp auth whoami
    """
    from semantic_patterns.credentials import CredentialType, get_credential_store

    store = get_credential_store(console)

    console.print()
    console.print("[bold]Current Identity[/bold]")
    console.print()

    # GitHub
    github_token = store.get(CredentialType.GITHUB, prompt_if_missing=False)
    if github_token:
        try:
            username = _get_github_username(github_token)
            console.print(f"GitHub:  @{username}")
        except Exception:
            console.print(
                "GitHub:  [yellow]Unable to verify (token may be invalid)[/yellow]"
            )
    else:
        console.print("GitHub:  [dim]Not authenticated[/dim]")

    # Looker
    looker_client_id = store.get("looker-client-id", prompt_if_missing=False)
    if looker_client_id:
        console.print(f"Looker:  {looker_client_id[:10]}...")
    else:
        console.print("Looker:  [dim]Not authenticated[/dim]")

    console.print()


if __name__ == "__main__":
    cli()
