"""Core build logic for semantic-patterns.

This module contains the main build function and supporting utilities
for generating LookML from semantic models.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

if TYPE_CHECKING:
    from semantic_patterns.adapters.lookml.paths import OutputPaths
    from semantic_patterns.config import SPConfig

# Module-level console for output
console = Console()


@dataclass
class BuildStatistics:
    """Statistics collected during a build."""

    dimensions: int = 0
    measures: int = 0
    metrics: int = 0
    explores: int = 0
    files: int = 0


def generate_model_file_content(
    config: SPConfig,
    all_files: dict[Path, str],
    paths: OutputPaths,
) -> str:
    """Generate the .model.lkml file content with domain-structured includes.

    Args:
        config: Parsed SPConfig with model settings
        all_files: Dictionary of file paths to content
        paths: Output paths helper for relative path calculation

    Returns:
        The content of the .model.lkml file
    """
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
    """Execute the build process with domain-based output structure.

    Args:
        config: Parsed SPConfig
        dry_run: If True, don't write files
        verbose: If True, show detailed output

    Returns:
        Tuple of (list of generated file paths, build statistics,
        project_path, all_files)

    Raises:
        click.ClickException: If no semantic models are found
    """
    import click

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
            fact_model_name = (
                f"{view_prefix}{explore.fact}" if view_prefix else explore.fact
            )

            # Map fact model to its explore
            model_to_explore[fact_model_name] = explore_name

            # Map joined_facts to this parent explore
            for joined_fact in explore.joined_facts:
                joined_fact_name = (
                    f"{view_prefix}{joined_fact}" if view_prefix else joined_fact
                )
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
    model_content = generate_model_file_content(config, all_files, paths)
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
