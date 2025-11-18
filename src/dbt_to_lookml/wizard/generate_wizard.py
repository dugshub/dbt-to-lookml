"""Interactive wizard for building generate commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import questionary
from questionary import ValidationError, Validator
from rich.console import Console

from dbt_to_lookml.wizard.base import BaseWizard
from dbt_to_lookml.wizard.types import WizardConfig, WizardMode

console = Console()


@dataclass
class GenerateWizardConfig:
    """Typed configuration from generate wizard.

    This dataclass represents all configuration options for the generate command,
    providing type safety and methods to convert to command-line arguments.

    Attributes:
        input_dir: Directory containing semantic model YAML files (required)
        output_dir: Directory to output LookML files (required)
        schema: Database schema name for sql_table_name (required)
        view_prefix: Optional prefix for view names (default: "")
        explore_prefix: Optional prefix for explore names (default: "")
        connection: Looker connection name (default: "redshift_test")
        model_name: Model file name without extension (default: "semantic_model")
        convert_tz: Timezone conversion setting (True/False/None for default)
        dry_run: Preview without writing files (default: False)
        no_validation: Skip LookML syntax validation (default: False)
        show_summary: Show detailed generation summary (default: False)
    """

    # Required fields
    input_dir: Path
    output_dir: Path
    schema: str

    # Optional string fields with defaults
    view_prefix: str = ""
    explore_prefix: str = ""
    connection: str = "redshift_test"
    model_name: str = "semantic_model"

    # Optional boolean/None fields
    convert_tz: bool | None = None
    dry_run: bool = False
    no_validation: bool = False
    show_summary: bool = False

    def to_command_parts(self) -> list[str]:
        """Convert configuration to command line arguments.

        Returns:
            List of command parts suitable for subprocess or display.
            Example: ["dbt-to-lookml", "generate", "-i", "input", "-o", "output", ...]
        """
        parts: list[str] = ["dbt-to-lookml", "generate"]

        # Required arguments
        parts.extend(["-i", str(self.input_dir)])
        parts.extend(["-o", str(self.output_dir)])
        parts.extend(["-s", self.schema])

        # Optional string arguments (only include if non-default)
        if self.view_prefix:
            parts.extend(["--view-prefix", self.view_prefix])
        if self.explore_prefix:
            parts.extend(["--explore-prefix", self.explore_prefix])
        if self.connection != "redshift_test":
            parts.extend(["--connection", self.connection])
        if self.model_name != "semantic_model":
            parts.extend(["--model-name", self.model_name])

        # Timezone conversion flags (mutually exclusive)
        if self.convert_tz is True:
            parts.append("--convert-tz")
        elif self.convert_tz is False:
            parts.append("--no-convert-tz")
        # If None, omit both flags (use default behavior)

        # Boolean flags
        if self.dry_run:
            parts.append("--dry-run")
        if self.no_validation:
            parts.append("--no-validation")
        if self.show_summary:
            parts.append("--show-summary")

        return parts

    def to_command_string(self, multiline: bool = True) -> str:
        """Convert configuration to shell command string.

        Args:
            multiline: If True, format with line continuations for readability.
                      If False, format as single line.

        Returns:
            Formatted shell command string.

        Examples:
            Multiline format:
            ```
            dbt-to-lookml generate \\
              -i semantic_models \\
              -o build/lookml \\
              -s public
            ```

            Single-line format:
            ```
            dbt-to-lookml generate -i semantic_models -o build/lookml -s public
            ```
        """
        parts = self.to_command_parts()

        if multiline:
            # Join with backslash continuation and indentation
            return " \\\n  ".join(parts)
        else:
            # Simple space-separated single line
            return " ".join(parts)


class PathValidator(Validator):
    """Validator for file system paths.

    Validates that:
    - Paths are non-empty
    - Paths exist on filesystem (if must_exist=True)
    - Paths are directories (if must_be_dir=True)

    Provides contextual error messages based on message_prefix.
    """

    def __init__(
        self,
        must_exist: bool = False,
        must_be_dir: bool = False,
        message_prefix: str = "Path",
    ) -> None:
        """Initialize path validator.

        Args:
            must_exist: Require that path exists on filesystem.
            must_be_dir: Require that path is a directory (implies must_exist).
            message_prefix: Prefix for error messages (e.g., "Input directory").
        """
        self.must_exist = must_exist or must_be_dir
        self.must_be_dir = must_be_dir
        self.message_prefix = message_prefix

    def validate(self, document: Any) -> None:
        """Validate path input.

        Args:
            document: Prompt document with user input (from questionary).

        Raises:
            ValidationError: If path is invalid, with descriptive message.
        """
        text = document.text.strip()

        # Check for empty input
        if not text:
            raise ValidationError(
                message=f"{self.message_prefix} cannot be empty",
                cursor_position=len(document.text),
            )

        path = Path(text)

        # Check existence if required
        if self.must_exist and not path.exists():
            raise ValidationError(
                message=f"{self.message_prefix} does not exist: {path}",
                cursor_position=len(document.text),
            )

        # Check if directory when required
        if self.must_be_dir and not path.is_dir():
            raise ValidationError(
                message=f"{self.message_prefix} must be a directory: {path}",
                cursor_position=len(document.text),
            )


class SchemaValidator(Validator):
    """Validator for database schema names.

    Ensures schema names follow basic naming conventions:
    - Non-empty
    - Alphanumeric with underscores and hyphens
    - No leading/trailing whitespace

    This prevents common errors and ensures generated LookML has valid identifiers.
    """

    def validate(self, document: Any) -> None:
        """Validate schema name.

        Args:
            document: Prompt document with user input (from questionary).

        Raises:
            ValidationError: If schema name is invalid.
        """
        text = document.text.strip()

        # Check for empty input
        if not text:
            raise ValidationError(
                message="Schema name cannot be empty",
                cursor_position=len(document.text),
            )

        # Check for leading/trailing whitespace
        if text != document.text:
            raise ValidationError(
                message="Schema name cannot have leading/trailing whitespace",
                cursor_position=len(document.text),
            )

        # Validate character set (alphanumeric, underscore, hyphen)
        if not all(c.isalnum() or c in ("_", "-") for c in text):
            msg = (
                "Schema name can only contain letters, numbers, "
                "underscores, and hyphens"
            )
            raise ValidationError(
                message=msg,
                cursor_position=len(document.text),
            )


class GenerateWizard(BaseWizard):
    """Interactive wizard for building generate commands.

    Guides users through all generate command options with:
    - Smart defaults from project detection (DTL-017 integration)
    - Real-time validation using custom validators
    - Contextual help text for each option
    - Sequential prompts for all configuration
    - Command preview and optional execution

    The wizard supports two modes:
    - PROMPT mode: Sequential command-line prompts (default)
    - TUI mode: Text-based UI interface (future DTL-020)
    """

    def __init__(
        self,
        mode: WizardMode = WizardMode.PROMPT,
        detected_input_dir: Path | None = None,
        detected_output_dir: Path | None = None,
        detected_schema: str | None = None,
        saved_config: dict | None = None,
    ) -> None:
        """Initialize generate wizard.

        Args:
            mode: Wizard interaction mode (PROMPT or TUI).
            detected_input_dir: Auto-detected input directory from DTL-017.
            detected_output_dir: Auto-detected output directory from DTL-017.
            detected_schema: Auto-detected schema name from YAML files.
            saved_config: Previously saved configuration from last run.
        """
        super().__init__(mode=mode)
        self.detected_input_dir = detected_input_dir
        self.detected_output_dir = detected_output_dir
        self.detected_schema = detected_schema
        self.saved_config = saved_config or {}
        self.wizard_config: GenerateWizardConfig | None = None

    def run(self) -> WizardConfig:
        """Run the wizard and collect configuration.

        Returns:
            Dictionary of configuration values collected from user.

        Raises:
            ValueError: If wizard is cancelled by user (Ctrl-C or quit).
        """
        console.print("\n[bold cyan]Generate Command Wizard[/bold cyan]")
        console.print("[dim]Press Ctrl-C to cancel at any time[/dim]\n")

        try:
            # Run sequential prompts for all options
            config = GenerateWizardConfig(
                input_dir=self._prompt_input_dir(),
                output_dir=self._prompt_output_dir(),
                schema=self._prompt_schema(),
                view_prefix=self._prompt_view_prefix(),
                explore_prefix=self._prompt_explore_prefix(),
                connection=self._prompt_connection(),
                model_name=self._prompt_model_name(),
                convert_tz=self._prompt_convert_tz(),
            )

            # Prompt for additional boolean flags
            additional_options = self._prompt_additional_options()
            config.dry_run = "dry-run" in additional_options
            config.no_validation = "no-validation" in additional_options
            config.show_summary = "show-summary" in additional_options

            self.wizard_config = config

            # Convert to dict for BaseWizard compatibility
            self.config = {
                "input_dir": str(config.input_dir),
                "output_dir": str(config.output_dir),
                "schema": config.schema,
                "view_prefix": config.view_prefix,
                "explore_prefix": config.explore_prefix,
                "connection": config.connection,
                "model_name": config.model_name,
                "convert_tz": config.convert_tz,
                "dry_run": config.dry_run,
                "no_validation": config.no_validation,
                "show_summary": config.show_summary,
            }

            return self.config

        except KeyboardInterrupt:
            console.print("\n[yellow]Wizard cancelled by user[/yellow]")
            raise ValueError("Wizard cancelled")

    def validate_config(self, config: WizardConfig) -> tuple[bool, str]:
        """Validate wizard configuration.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is empty string if valid.
        """
        # Check required fields
        if not config.get("input_dir"):
            return (False, "Input directory is required")
        if not config.get("output_dir"):
            return (False, "Output directory is required")
        if not config.get("schema"):
            return (False, "Schema name is required")

        # Validate input path existence
        input_path = Path(config["input_dir"])
        if not input_path.exists():
            return (False, f"Input directory does not exist: {input_path}")
        if not input_path.is_dir():
            return (False, f"Input path is not a directory: {input_path}")

        return (True, "")

    def _prompt_input_dir(self) -> Path:
        """Prompt for input directory containing semantic model YAML files.

        Returns:
            Path to input directory selected by user.

        Raises:
            ValueError: If user cancels prompt.
        """
        # Priority: detection > saved config > hardcoded default
        if self.detected_input_dir:
            default = str(self.detected_input_dir)
            hint = " (auto-detected)"
        elif self.saved_config.get("input_dir"):
            default = self.saved_config["input_dir"]
            hint = " (from last run)"
        else:
            default = "models/semantic_models"
            hint = ""

        result = questionary.path(
            f"Input directory{hint}:",
            default=default,
            validate=PathValidator(must_be_dir=True, message_prefix="Input directory"),
            only_directories=True,
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return Path(cast(str, result))

    def _prompt_output_dir(self) -> Path:
        """Prompt for output directory for generated LookML files.

        Returns:
            Path to output directory selected by user.

        Raises:
            ValueError: If user cancels prompt.
        """
        # Priority: detection > saved config > hardcoded default
        if self.detected_output_dir:
            default = str(self.detected_output_dir)
            hint = " (auto-detected)"
        elif self.saved_config.get("output_dir"):
            default = self.saved_config["output_dir"]
            hint = " (from last run)"
        else:
            default = "build/lookml"
            hint = ""

        result = questionary.text(
            f"Output directory{hint}:",
            default=default,
            validate=PathValidator(message_prefix="Output directory"),
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return Path(cast(str, result))

    def _prompt_schema(self) -> str:
        """Prompt for database schema name.

        Returns:
            Schema name entered by user.

        Raises:
            ValueError: If user cancels prompt.
        """
        # Priority: detection > saved config > hardcoded default
        if self.detected_schema:
            default = self.detected_schema
            hint = " (from YAML)"
        elif self.saved_config.get("schema"):
            default = self.saved_config["schema"]
            hint = " (from last run)"
        else:
            default = "public"
            hint = ""

        result = questionary.text(
            f"Database schema name{hint}:",
            default=default,
            validate=SchemaValidator(),
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return cast(str, result)

    def _prompt_view_prefix(self) -> str:
        """Prompt for optional view prefix.

        Returns:
            View prefix string (may be empty).

        Raises:
            ValueError: If user cancels prompt.
        """
        default = self.saved_config.get("view_prefix", "")
        result = questionary.text(
            "View prefix (optional, press Enter to skip):",
            default=default,
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return cast(str, result)

    def _prompt_explore_prefix(self) -> str:
        """Prompt for optional explore prefix.

        Returns:
            Explore prefix string (may be empty).

        Raises:
            ValueError: If user cancels prompt.
        """
        default = self.saved_config.get("explore_prefix", "")
        result = questionary.text(
            "Explore prefix (optional, press Enter to skip):",
            default=default,
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return cast(str, result)

    def _prompt_connection(self) -> str:
        """Prompt for Looker connection name.

        Returns:
            Connection name string.

        Raises:
            ValueError: If user cancels prompt.
        """
        default = self.saved_config.get("connection", "redshift_test")
        result = questionary.text(
            "Looker connection name:",
            default=default,
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return cast(str, result)

    def _prompt_model_name(self) -> str:
        """Prompt for model file name (without extension).

        Returns:
            Model name string.

        Raises:
            ValueError: If user cancels prompt.
        """
        default = self.saved_config.get("model_name", "semantic_model")
        result = questionary.text(
            "Model file name (without extension):",
            default=default,
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return cast(str, result)

    def _prompt_convert_tz(self) -> bool | None:
        """Prompt for timezone conversion setting.

        Returns:
            True for --convert-tz, False for --no-convert-tz, None for default.

        Raises:
            ValueError: If user cancels prompt.
        """
        result = questionary.select(
            "Timezone conversion for time dimensions:",
            choices=[
                questionary.Choice(
                    title="No (default) - Use database timezone as-is",
                    value=None,
                ),
                questionary.Choice(
                    title="Yes - Convert timestamps to user timezone",
                    value=True,
                ),
                questionary.Choice(
                    title="Explicitly disable - Add convert_tz: no",
                    value=False,
                ),
            ],
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        # result is guaranteed to be bool | None by questionary.select
        return result  # type: ignore[no-any-return]

    def _prompt_additional_options(self) -> list[str]:
        """Prompt for additional boolean options using checkboxes.

        Returns:
            List of selected option keys (e.g., ["dry-run", "show-summary"]).

        Raises:
            ValueError: If user cancels prompt.
        """
        result = questionary.checkbox(
            "Additional options:",
            choices=[
                questionary.Choice(
                    title="dry-run - Preview without writing files",
                    value="dry-run",
                    checked=False,
                ),
                questionary.Choice(
                    title="no-validation - Skip LookML syntax validation",
                    value="no-validation",
                    checked=False,
                ),
                questionary.Choice(
                    title="show-summary - Display detailed generation summary",
                    value="show-summary",
                    checked=False,
                ),
            ],
            instruction="(Space to select, Enter to continue)",
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return cast(list[str], result)

    def get_command_string(self, multiline: bool = True) -> str:
        """Get the final command string from wizard configuration.

        Args:
            multiline: Format with line continuations for readability.

        Returns:
            Formatted shell command string.

        Raises:
            ValueError: If wizard has not been run yet.
        """
        if self.wizard_config is None:
            raise ValueError("Wizard has not been run yet")

        return self.wizard_config.to_command_string(multiline=multiline)


def run_generate_wizard(
    mode: WizardMode = WizardMode.PROMPT,
    execute: bool = False,
) -> str | None:
    """Run the generate command wizard.

    This is the main entry point for the wizard, called from the CLI.

    Args:
        mode: Wizard interaction mode (PROMPT or TUI).
        execute: If True, execute the generated command after wizard completes.

    Returns:
        Generated command string, or None if wizard was cancelled.

    Raises:
        ValueError: If wizard validation fails.
    """
    # Load saved config from last run
    from dbt_to_lookml.config import load_last_run

    saved_config = load_last_run()

    # Import detection module for smart defaults (DTL-017 integration)
    try:
        from dbt_to_lookml.wizard.detection import ProjectDetector

        detector = ProjectDetector()
        detection_result = detector.detect()

        detected_input = detection_result.input_dir
        detected_output = detection_result.output_dir
        detected_schema = detection_result.schema_name
    except Exception:
        # Detection module not available or failed, use None defaults
        detected_input = None
        detected_output = None
        detected_schema = None

    # Create and run wizard
    wizard = GenerateWizard(
        mode=mode,
        detected_input_dir=detected_input,
        detected_output_dir=detected_output,
        detected_schema=detected_schema,
        saved_config=saved_config,
    )

    try:
        config = wizard.run()
    except ValueError:
        # Wizard was cancelled
        return None

    # Validate configuration
    is_valid, error_msg = wizard.validate_config(config)
    if not is_valid:
        console.print(f"[bold red]Configuration error:[/bold red] {error_msg}")
        raise ValueError(f"Invalid configuration: {error_msg}")

    # Display final command with syntax highlighting
    command_str = wizard.get_command_string(multiline=True)
    console.print("\n[bold green]Generated Command:[/bold green]")

    from rich.syntax import Syntax

    syntax = Syntax(command_str, "bash", theme="monokai", line_numbers=False)
    console.print(syntax)

    # Try to copy to clipboard (optional feature)
    try:
        import pyperclip  # type: ignore[import-not-found]

        pyperclip.copy(wizard.get_command_string(multiline=False))
        console.print("\n[dim]✓ Command copied to clipboard[/dim]")
    except ImportError:
        # pyperclip not available, skip clipboard silently
        pass
    except Exception:
        # Clipboard access failed (e.g., no display), skip silently
        pass

    # Prompt for execution if not already specified via --execute flag
    if not execute:
        execute_now = questionary.confirm(
            "Execute this command now?",
            default=False,
        ).ask()

        if execute_now is None:
            # User cancelled
            console.print("\n[yellow]Wizard cancelled[/yellow]")
            return command_str

        execute = execute_now

    # Execute if requested
    if execute:
        console.print("\n[yellow]Executing command...[/yellow]\n")

        import click

        from dbt_to_lookml.__main__ import generate

        # Build complete parameter set for generate command
        generate_params = {
            "input_dir": Path(config["input_dir"]),
            "output_dir": Path(config["output_dir"]),
            "schema": config["schema"],
            "view_prefix": config.get("view_prefix", ""),
            "explore_prefix": config.get("explore_prefix", ""),
            "connection": config.get("connection", "redshift_test"),
            "model_name": config.get("model_name", "semantic_model"),
            "dry_run": config.get("dry_run", False),
            "no_validation": config.get("no_validation", False),
            "no_formatting": False,  # Not exposed in wizard
            "show_summary": config.get("show_summary", False),
            "yes": True,  # Auto-confirm in wizard execution mode
            "preview": False,  # Not applicable in wizard mode
        }

        # Handle timezone conversion flags (mutually exclusive)
        convert_tz_value = config.get("convert_tz")
        if convert_tz_value is True:
            generate_params["convert_tz"] = True
            generate_params["no_convert_tz"] = False
        elif convert_tz_value is False:
            generate_params["convert_tz"] = False
            generate_params["no_convert_tz"] = True
        else:
            # None - use default behavior
            generate_params["convert_tz"] = False
            generate_params["no_convert_tz"] = False

        # Invoke the generate command
        ctx = click.get_current_context()
        ctx.invoke(generate, **generate_params)

    return command_str
