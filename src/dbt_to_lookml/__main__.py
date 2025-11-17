"""Command-line interface for dbt-to-lookml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from rich.console import Console

from dbt_to_lookml.cli.formatting import (
    format_error,
    format_success,
    format_warning,
)
from dbt_to_lookml.cli.help_formatter import RichCommand
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
    """Convert dbt semantic models to LookML views and explores.

    A command-line tool for transforming dbt semantic layer definitions
    into Looker's LookML format. Supports validation, generation, and
    interactive wizards for building commands.

    Quick Start:

      1. Validate your semantic models:
         $ dbt-to-lookml validate -i semantic_models/

      2. Generate LookML files:
         $ dbt-to-lookml generate -i semantic_models/ -o lookml/ -s prod_schema

      3. Use the interactive wizard:
         $ dbt-to-lookml wizard generate

    Common Workflows:

      Development workflow with dry-run:
      $ dbt-to-lookml generate -i models/ -o lookml/ -s dev --dry-run

      Production generation with validation:
      $ dbt-to-lookml validate -i models/ --strict && \\
        dbt-to-lookml generate -i models/ -o dist/ -s prod --no-validation

      Custom prefixes and timezone handling:
      $ dbt-to-lookml generate -i models/ -o lookml/ -s analytics \\
          --view-prefix "sm_" --explore-prefix "exp_" --convert-tz

    For more information on a specific command:
      $ dbt-to-lookml COMMAND --help
    """
    pass


@cli.group()
def wizard() -> None:
    """Interactive wizard for building and running commands.

    Run 'dbt-to-lookml wizard --help' to see available wizard commands.

    Examples:
      dbt-to-lookml wizard generate    # Wizard for generate command
      dbt-to-lookml wizard validate    # Wizard for validate command
    """
    pass


@wizard.command(name="test")
@click.option(
    "--mode",
    type=click.Choice(["prompt", "tui"], case_sensitive=False),
    default="prompt",
    help="Wizard interaction mode (prompt or tui)",
)
def wizard_test(mode: str) -> None:
    """Test wizard infrastructure (temporary command for DTL-015).

    This command tests that the wizard module is properly installed
    and the base infrastructure is working. Will be replaced by
    actual wizard commands in DTL-016+.
    """
    from dbt_to_lookml.wizard.base import BaseWizard
    from dbt_to_lookml.wizard.types import WizardMode

    # Test implementation to verify infrastructure
    class TestWizard(BaseWizard):
        """Minimal wizard implementation for testing."""

        def run(self) -> dict[str, Any]:
            """Run test wizard."""
            console.print("[bold green]Wizard infrastructure working![/bold green]")
            console.print(f"Mode: {self.mode.value}")
            console.print(f"TUI available: {self.check_tui_available()}")
            return {"test": "success"}

        def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
            """Validate test config."""
            return (True, "")

    wizard_mode = WizardMode.TUI if mode == "tui" else WizardMode.PROMPT
    test_wizard = TestWizard(mode=wizard_mode)

    # Check TUI availability if requested
    if wizard_mode == WizardMode.TUI and not test_wizard.check_tui_available():
        test_wizard.handle_tui_unavailable()

    # Run wizard
    config = test_wizard.run()
    console.print("[dim]Test config:[/dim]", config)


@wizard.command(name="generate")
@click.option(
    "--execute",
    "-x",
    is_flag=True,
    help="Execute the generated command immediately after wizard completes",
)
@click.option(
    "--wizard-tui",
    is_flag=True,
    help="Use TUI interface (requires textual)",
)
def wizard_generate(execute: bool, wizard_tui: bool) -> None:
    """Interactive wizard for building generate commands.

    The wizard will guide you through all generate command options:
    - Input directory (semantic model YAML files)
    - Output directory (LookML files)
    - Database schema name
    - View and explore prefixes
    - Connection and model names
    - Timezone conversion settings
    - Additional flags (dry-run, validation, summary)

    The wizard provides smart defaults based on your project structure
    and validates inputs in real-time.

    Examples:
      # Run wizard and display command
      dbt-to-lookml wizard generate

      # Run wizard with TUI interface
      dbt-to-lookml wizard generate --wizard-tui

      # Run wizard and execute command immediately
      dbt-to-lookml wizard generate --execute
    """
    if wizard_tui:
        try:
            from dbt_to_lookml.wizard import launch_tui_wizard

            # Get smart defaults (DTL-017 - if implemented)
            defaults: dict[str, Any] = {}
            # TODO: Add detection module integration when DTL-017 is complete
            # from dbt_to_lookml.wizard.detection import ProjectDetector
            # detector = ProjectDetector()
            # detection_result = detector.detect()
            # if detection_result.success:
            #     defaults = detection_result.to_dict()

            # Launch TUI
            result = launch_tui_wizard(defaults)

            if result:
                # Execute the generate command with form data
                console.print("[bold blue]Executing command...[/bold blue]")

                # Convert form data to click context and invoke generate
                ctx = click.get_current_context()
                ctx.invoke(
                    generate,
                    input_dir=Path(result["input_dir"]),
                    output_dir=Path(result["output_dir"]),
                    schema=result["schema"],
                    view_prefix=result.get("view_prefix", ""),
                    explore_prefix=result.get("explore_prefix", ""),
                    dry_run=result.get("dry_run", False),
                    no_validation=result.get("skip_validation", False),
                    no_formatting=result.get("skip_formatting", False),
                    show_summary=result.get("show_summary", False),
                    connection=result.get("connection", "redshift_test"),
                    model_name=result.get("model_name", "semantic_model"),
                    convert_tz=result.get("convert_tz") == "yes",
                    no_convert_tz=result.get("convert_tz") == "no",
                    yes=False,
                    preview=False,
                )
            else:
                console.print("[yellow]Wizard cancelled[/yellow]")

        except ImportError as e:
            console.print(f"[bold red]Error: {e}[/bold red]")
            console.print(
                "\nTo use TUI mode, install wizard dependencies:\n"
                "  pip install dbt-to-lookml[wizard]\n"
                "  or: uv pip install -e '.[wizard]'\n"
                "\nOr use the prompt-based wizard:\n"
                "  dbt-to-lookml wizard generate"
            )
            raise click.ClickException("Textual library not available")
    else:
        from dbt_to_lookml.wizard.generate_wizard import run_generate_wizard
        from dbt_to_lookml.wizard.types import WizardMode

        try:
            command_str = run_generate_wizard(
                mode=WizardMode.PROMPT,
                execute=execute,
            )

            if command_str is None:
                # Wizard was cancelled
                return

            if not execute:
                console.print("\n[dim]To execute this command, run it in your terminal")
                console.print("or use: dbt-to-lookml wizard generate --execute[/dim]")

        except Exception as e:
            console.print(f"[bold red]Error: {e}[/bold red]")
            raise click.ClickException(str(e))


@cli.command(cls=RichCommand)
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
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt and execute immediately",
)
@click.option(
    "--preview",
    is_flag=True,
    help="Show preview without executing (dry run with detailed preview)",
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
    yes: bool,
    preview: bool,
) -> None:
    """Generate LookML views and explores from semantic models.

    This command parses dbt semantic model YAML files and generates
    corresponding LookML view files (.view.lkml) and a consolidated
    explores file (explores.lkml).

    Examples:

      Basic generation:
      $ dbt-to-lookml generate -i semantic_models/ -o build/lookml -s prod_schema

      With prefixes and dry-run preview:
      $ dbt-to-lookml generate -i models/ -o lookml/ -s analytics \\
          --view-prefix "sm_" --explore-prefix "exp_" --dry-run

      With timezone conversion:
      $ dbt-to-lookml generate -i models/ -o lookml/ -s dwh --convert-tz

      With custom connection and model name:
      $ dbt-to-lookml generate -i models/ -o lookml/ -s redshift_prod \\
          --connection "redshift_analytics" --model-name "semantic_layer"

    For interactive mode, use:
      $ dbt-to-lookml wizard generate
    """
    if not GENERATOR_AVAILABLE:
        error_panel = format_error(
            "LookML generator dependencies not available",
            context="Install with: pip install lkml",
        )
        console.print(error_panel)
        raise click.ClickException("Missing dependencies for LookML generation")

    # Validate mutual exclusivity of timezone flags
    if convert_tz and no_convert_tz:
        error_panel = format_error(
            "Conflicting timezone options provided",
            context="Use either --convert-tz OR --no-convert-tz, not both",
        )
        console.print(error_panel)
        raise click.ClickException(
            "--convert-tz and --no-convert-tz cannot be used together"
        )

    # Preview mode implies dry run
    if preview:
        dry_run = True

    # Import preview utilities
    from dbt_to_lookml.preview import (
        PreviewData,
        count_yaml_files,
        estimate_output_files,
        format_command_parts,
        show_preview_and_confirm,
    )

    # Count input files for preview
    input_file_count = count_yaml_files(input_dir)

    if input_file_count == 0:
        console.print(
            "[bold red]Error: No YAML files found in input directory[/bold red]"
        )
        raise click.ClickException(f"No YAML files in {input_dir}")

    # Estimate output files
    estimated_views, estimated_explores, estimated_models = estimate_output_files(
        input_file_count
    )

    # Build command parts for display
    command_parts = format_command_parts(
        "dbt-to-lookml generate",
        input_dir,
        output_dir,
        schema,
        view_prefix=view_prefix,
        explore_prefix=explore_prefix,
        connection=connection,
        model_name=model_name,
        convert_tz=convert_tz if convert_tz else (False if no_convert_tz else None),
        dry_run=dry_run,
        no_validation=no_validation,
        no_formatting=no_formatting,
        show_summary=show_summary,
    )

    # Build additional config dict
    additional_config = {}
    if view_prefix:
        additional_config["View prefix"] = view_prefix
    if explore_prefix:
        additional_config["Explore prefix"] = explore_prefix
    if connection != "redshift_test":
        additional_config["Connection"] = connection
    if model_name != "semantic_model":
        additional_config["Model name"] = model_name
    if convert_tz:
        additional_config["Timezone conversion"] = "enabled"
    elif no_convert_tz:
        additional_config["Timezone conversion"] = "disabled"

    # Create preview data
    preview_data = PreviewData(
        input_dir=input_dir,
        output_dir=output_dir,
        schema=schema,
        input_file_count=input_file_count,
        estimated_views=estimated_views,
        estimated_explores=estimated_explores,
        estimated_models=estimated_models,
        command_parts=command_parts,
        additional_config=additional_config,
    )

    # Show preview and get confirmation (unless --yes or preview-only)
    if preview:
        # Preview-only mode - show and exit
        from dbt_to_lookml.preview import CommandPreview

        preview_panel = CommandPreview()
        preview_panel.show(preview_data)
        console.print("\n[yellow]Preview mode - no files will be generated[/yellow]")
        return

    # Show preview and confirm (unless --yes flag)
    if not show_preview_and_confirm(preview_data, auto_confirm=yes):
        return  # User cancelled

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
                "[bold red]No semantic models found or all files failed to "
                "parse[/bold red]"
            )
            raise click.ClickException("No valid semantic models to generate from")

        console.print(
            f"Found {len(semantic_models)} semantic models from {file_count} files"
        )

        if error_count > 0:
            console.print(
                f"[yellow]Warning: {error_count} files had parse errors and "
                f"were skipped[/yellow]"
            )

        if not dry_run:
            console.print(
                f"[bold blue]Generating LookML files to {output_dir}[/bold blue]"
            )
        else:
            console.print(
                f"[bold yellow]Previewing LookML generation for "
                f"{output_dir}[/bold yellow]"
            )

        # Determine convert_tz value for generator
        # If neither flag specified: None (use generator default)
        # If --convert-tz specified: True
        # If --no-convert-tz specified: False
        convert_tz_value: bool | None = None
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
            success_panel = format_success(
                "LookML generation completed successfully",
                details=f"Generated {len(generated_files)} files in {output_dir}",
            )
            console.print(success_panel)
        else:
            success_panel = format_success(
                "LookML generation preview completed",
                details=f"Would generate {len(generated_files)} files in {output_dir}",
            )
            console.print(success_panel)

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
        error_panel = format_error(
            "Generation failed",
            context=f"Error: {e}",
        )
        console.print(error_panel)
        raise click.ClickException(str(e))


@cli.command(cls=RichCommand)
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
    """Validate semantic model YAML files without generating LookML.

    This command parses and validates semantic model files to check
    for syntax errors, schema violations, and structural issues.

    Examples:

      Basic validation:
      $ dbt-to-lookml validate -i semantic_models/

      Strict mode (fail on first error):
      $ dbt-to-lookml validate -i semantic_models/ --strict

      Verbose output with model details:
      $ dbt-to-lookml validate -i semantic_models/ --verbose

      Quick check before generation:
      $ dbt-to-lookml validate -i models/ && \\
        dbt-to-lookml generate -i models/ -o lookml/ -s prod
    """
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
        success_panel = format_success(
            f"Validated {count} semantic models from {file_count} files"
        )
        console.print(success_panel)

        if error_count > 0:
            warning_panel = format_warning(
                f"{error_count} files had validation errors",
                context="Review the errors above for details",
            )
            console.print(warning_panel)

        if verbose:
            console.print("\n[bold]Summary:[/bold]")
            for model in semantic_models:
                console.print(f"  - {model.name}")

    except Exception as e:
        error_panel = format_error(
            "Validation failed",
            context=f"Error: {e}",
        )
        console.print(error_panel)
        raise click.ClickException(str(e))


if __name__ == "__main__":
    cli()
