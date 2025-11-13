"""Command-line interface for dbt-to-lookml."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from dbt_to_lookml.parsers.dbt import DbtParser as SemanticModelParser

try:
    from dbt_to_lookml.generators.lookml import LookMLGenerator

    GENERATOR_AVAILABLE = True
except ImportError:
    GENERATOR_AVAILABLE = False

console = Console()


@click.group()
@click.version_option()
def cli() -> None:
    """Convert dbt semantic models to LookML views and explores."""
    pass


@cli.command()
@click.option(
    "--input-dir",
    "-i",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory containing semantic model YAML files",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory to output LookML files",
)
@click.option(
    "--schema",
    "-s",
    type=str,
    required=True,
    help="Database schema name for sql_table_name (e.g., 'redshift_gold')",
)
@click.option(
    "--view-prefix",
    type=str,
    default="",
    help="Prefix to add to view names",
)
@click.option(
    "--explore-prefix",
    type=str,
    default="",
    help="Prefix to add to explore names",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be generated without writing files",
)
@click.option(
    "--no-validation",
    is_flag=True,
    help="Skip LookML syntax validation",
)
@click.option(
    "--no-formatting",
    is_flag=True,
    help="Skip LookML output formatting",
)
@click.option(
    "--show-summary",
    is_flag=True,
    help="Show detailed generation summary at the end",
)
@click.option(
    "--connection",
    "-c",
    type=str,
    default="redshift_test",
    help="Looker connection name for the model file (default: redshift_test)",
)
@click.option(
    "--model-name",
    "-m",
    type=str,
    default="semantic_model",
    help="Name for the generated model file without extension "
    "(default: semantic_model)",
)
@click.option(
    "--convert-tz",
    is_flag=True,
    help="Convert time dimensions to UTC (mutually exclusive with --no-convert-tz)",
)
@click.option(
    "--no-convert-tz",
    is_flag=True,
    help="Don't convert time dimensions to UTC (mutually exclusive with --convert-tz)",
)
def generate(
    input_dir: Path,
    output_dir: Path,
    schema: str,
    view_prefix: str,
    explore_prefix: str,
    dry_run: bool,
    no_validation: bool,
    no_formatting: bool,
    show_summary: bool,
    connection: str,
    model_name: str,
    convert_tz: bool,
    no_convert_tz: bool,
) -> None:
    """Generate LookML views and explores from semantic models."""
    if not GENERATOR_AVAILABLE:
        console.print(
            "[bold red]Error: LookML generator dependencies not available[/bold red]"
        )
        console.print("Please install required dependencies: pip install lkml")
        raise click.ClickException("Missing dependencies for LookML generation")

    # Validate mutual exclusivity of timezone flags
    if convert_tz and no_convert_tz:
        console.print(
            "[bold red]Error: --convert-tz and --no-convert-tz are "
            "mutually exclusive[/bold red]"
        )
        raise click.ClickException(
            "--convert-tz and --no-convert-tz cannot be used together"
        )

    try:
        # Show configuration
        if dry_run:
            console.print(
                "[bold yellow]DRY RUN MODE - No files will be created[/bold yellow]"
            )

        console.print(
            f"[bold blue]Parsing semantic models from {input_dir}[/bold blue]"
        )

        parser = SemanticModelParser()
        semantic_models = []
        file_count = 0
        error_count = 0

        # Parse files individually to provide better error reporting
        for yaml_file in input_dir.glob("*.yml"):
            file_count += 1
            try:
                models = parser.parse_file(yaml_file)
                semantic_models.extend(models)
                console.print(
                    f"  [green]✓[/green] {yaml_file.name}: {len(models)} models"
                )
            except Exception as e:
                error_count += 1
                console.print(f"  [red]✗[/red] {yaml_file.name}: {e}")
                console.print(
                    "    [yellow]Skipping file due to parse error...[/yellow]"
                )

        for yaml_file in input_dir.glob("*.yaml"):
            file_count += 1
            try:
                models = parser.parse_file(yaml_file)
                semantic_models.extend(models)
                console.print(
                    f"  [green]✓[/green] {yaml_file.name}: {len(models)} models"
                )
            except Exception as e:
                error_count += 1
                console.print(f"  [red]✗[/red] {yaml_file.name}: {e}")
                console.print(
                    "    [yellow]Skipping file due to parse error...[/yellow]"
                )

        if len(semantic_models) == 0:
            console.print(
                "[bold red]No semantic models found or all files failed to parse[/bold red]"
            )
            raise click.ClickException("No valid semantic models to generate from")

        console.print(
            f"Found {len(semantic_models)} semantic models from {file_count} files"
        )

        if error_count > 0:
            console.print(
                f"[yellow]Warning: {error_count} files had parse errors and were skipped[/yellow]"
            )

        if not dry_run:
            console.print(
                f"[bold blue]Generating LookML files to {output_dir}[/bold blue]"
            )
        else:
            console.print(
                f"[bold yellow]Previewing LookML generation for {output_dir}[/bold yellow]"
            )

        # Determine convert_tz value for generator
        # If neither flag specified: None (use generator default)
        # If --convert-tz specified: True
        # If --no-convert-tz specified: False
        convert_tz_value: Optional[bool] = None
        if convert_tz:
            convert_tz_value = True
        elif no_convert_tz:
            convert_tz_value = False

        # Configure generator
        generator = LookMLGenerator(
            view_prefix=view_prefix,
            explore_prefix=explore_prefix,
            validate_syntax=not no_validation,
            format_output=not no_formatting,
            schema=schema,
            connection=connection,
            model_name=model_name,
            convert_tz=convert_tz_value,
        )

        # Generate files
        generated_files, validation_errors = generator.generate_lookml_files(
            semantic_models, output_dir, dry_run=dry_run
        )

        # Show results
        if not dry_run:
            console.print(
                "[bold green]✓ LookML generation completed successfully[/bold green]"
            )
        else:
            console.print(
                "[bold yellow]✓ LookML generation preview completed[/bold yellow]"
            )

        # Show validation results
        if validation_errors:
            console.print(
                f"[yellow]⚠ Found {len(validation_errors)} validation errors:[/yellow]"
            )
            for error in validation_errors:
                console.print(f"  [red]•[/red] {error}")
        elif not no_validation:
            console.print(
                "[green]✓ All generated LookML passed syntax validation[/green]"
            )

        # Show summary if requested
        if show_summary:
            console.print(
                "\n"
                + generator.get_generation_summary(
                    semantic_models, generated_files, validation_errors
                )
            )

        # Exit with error code if there were validation issues
        if validation_errors and not dry_run:
            console.print(
                "[yellow]Generation completed with validation errors[/yellow]"
            )
            raise click.ClickException("LookML validation failed")

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise click.ClickException(str(e))


@cli.command()
@click.option(
    "--input-dir",
    "-i",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory containing semantic model YAML files",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Enable strict validation mode",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed validation results",
)
def validate(input_dir: Path, strict: bool, verbose: bool) -> None:
    """Validate semantic model files."""
    try:
        console.print(
            f"[bold blue]Validating semantic models in {input_dir}[/bold blue]"
        )

        parser = SemanticModelParser(strict_mode=strict)
        semantic_models = []
        file_count = 0
        error_count = 0

        # Parse files individually to provide better error reporting
        for yaml_file in input_dir.glob("*.yml"):
            file_count += 1
            try:
                models = parser.parse_file(yaml_file)
                semantic_models.extend(models)

                if verbose:
                    console.print(
                        f"  [green]✓[/green] {yaml_file.name}: {len(models)} models"
                    )
                    for model in models:
                        console.print(
                            f"    - {model.name}: "
                            f"{len(model.entities)} entities, "
                            f"{len(model.dimensions)} dimensions, "
                            f"{len(model.measures)} measures"
                        )
                        if model.config and model.config.meta:
                            console.print(
                                f"      Config: domain={model.config.meta.domain}"
                            )
                else:
                    console.print(f"  [green]✓[/green] {yaml_file.name}")
            except Exception as e:
                error_count += 1
                console.print(f"  [red]✗[/red] {yaml_file.name}: {e}")
                if not strict:
                    console.print(
                        "    [yellow]Continuing in non-strict mode...[/yellow]"
                    )
                else:
                    raise

        for yaml_file in input_dir.glob("*.yaml"):
            file_count += 1
            try:
                models = parser.parse_file(yaml_file)
                semantic_models.extend(models)

                if verbose:
                    console.print(
                        f"  [green]✓[/green] {yaml_file.name}: {len(models)} models"
                    )
                    for model in models:
                        console.print(
                            f"    - {model.name}: "
                            f"{len(model.entities)} entities, "
                            f"{len(model.dimensions)} dimensions, "
                            f"{len(model.measures)} measures"
                        )
                        if model.config and model.config.meta:
                            console.print(
                                f"      Config: domain={model.config.meta.domain}"
                            )
                else:
                    console.print(f"  [green]✓[/green] {yaml_file.name}")
            except Exception as e:
                error_count += 1
                console.print(f"  [red]✗[/red] {yaml_file.name}: {e}")
                if not strict:
                    console.print(
                        "    [yellow]Continuing in non-strict mode...[/yellow]"
                    )
                else:
                    raise

        count = len(semantic_models)
        console.print(
            f"\n[bold green]✓ Validated {count} semantic models from {file_count} files[/bold green]"
        )

        if error_count > 0:
            console.print(
                f"[yellow]Warning: {error_count} files had validation errors[/yellow]"
            )

        if verbose:
            console.print("\n[bold]Summary:[/bold]")
            for model in semantic_models:
                console.print(f"  - {model.name}")

    except Exception as e:
        console.print(f"[bold red]Validation failed: {e}[/bold red]")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    cli()
