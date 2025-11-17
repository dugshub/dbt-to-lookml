# Implementation Specification: DTL-018

**Issue**: DTL-018 - Build simple prompt-based wizard for generate command
**Stack**: backend
**Generated**: 2025-11-17
**Strategy**: Approved 2025-11-17

## Metadata

- **Issue ID**: DTL-018
- **Type**: feature
- **Status**: refinement → ready (after spec approval)
- **Parent Epic**: DTL-014 (Enhanced CLI with Rich wizard)
- **Dependencies**: DTL-015 (wizard infrastructure), DTL-017 (detection module)

## Issue Context

### Problem Statement

The current `generate` command requires users to remember and correctly specify many command-line flags and options. This creates friction for new users and increases the likelihood of errors. Users need an interactive, guided experience that:

1. Prompts sequentially for each configuration option
2. Provides smart defaults based on project structure detection
3. Validates inputs in real-time to prevent errors
4. Shows contextual help and format hints
5. Previews the final command before execution
6. Supports both quick flows (accepting defaults) and detailed customization

### Solution Approach

Implement an interactive wizard using the `questionary` library that guides users through all `generate` command options with a sequential prompt flow. The wizard integrates with DTL-017's detection module to provide intelligent defaults, validates inputs using custom validator classes, and produces a fully-formed command string that can be displayed, copied to clipboard (if available), and optionally executed.

This implementation leverages:
- **questionary** for styled, interactive prompts
- **rich** for syntax-highlighted command display
- **DTL-017 detection module** for smart defaults
- **BaseWizard** (from DTL-015) for common wizard functionality
- **pyperclip** (optional) for clipboard integration

### Success Criteria

- [ ] Wizard prompts for all 9+ generate command options sequentially
- [ ] Each prompt displays: description, default value, format hints
- [ ] Real-time input validation using custom validators
- [ ] Required fields (input-dir, output-dir, schema) are enforced
- [ ] Optional fields can be skipped with Enter
- [ ] Final command displayed with syntax highlighting
- [ ] Command copied to clipboard (if pyperclip available)
- [ ] `--execute` flag allows immediate command execution
- [ ] All tests pass with 95%+ coverage
- [ ] mypy type checking passes with --strict
- [ ] Manual testing confirms excellent UX

## Approved Strategy Summary

The implementation creates a new `generate_wizard.py` module in the wizard package with:

1. **GenerateWizardConfig dataclass**: Typed configuration container with methods to convert configuration to command-line arguments
2. **Custom Validators**: PathValidator and SchemaValidator for real-time input validation
3. **GenerateWizard class**: Main wizard implementation extending BaseWizard with 9+ sequential prompts
4. **Detection integration**: Uses DTL-017 module to auto-detect input directories, output directories, and schema names
5. **CLI integration**: Adds `wizard generate` command to __main__.py
6. **Comprehensive testing**: Unit tests for validators, config, and wizard flow; CLI tests for command integration

## Implementation Plan

### Phase 1: Create Core Data Structures (30 minutes)

**Goal**: Define typed configuration and custom validators for the wizard

#### Task 1.1: Create GenerateWizardConfig Dataclass

**File**: `src/dbt_to_lookml/wizard/generate_wizard.py` (new)

**Implementation**:

```python
"""Interactive wizard for building generate commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import questionary
from questionary import Validator, ValidationError
from rich.console import Console

# Will import from DTL-015's base wizard infrastructure
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
    convert_tz: Optional[bool] = None
    dry_run: bool = False
    no_validation: bool = False
    show_summary: bool = False

    def to_command_parts(self) -> list[str]:
        """Convert configuration to command line arguments.

        Returns:
            List of command parts suitable for subprocess or display.
            Example: ["dbt-to-lookml", "generate", "-i", "input", "-o", "output", ...]
        """
        parts = ["dbt-to-lookml", "generate"]

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
```

**Testing**: Create unit tests for command part generation in `test_generate_wizard.py`

#### Task 1.2: Create PathValidator Class

**Same file**: `src/dbt_to_lookml/wizard/generate_wizard.py`

**Implementation**:

```python
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
```

**Testing**: Create validator tests with various edge cases

#### Task 1.3: Create SchemaValidator Class

**Same file**: `src/dbt_to_lookml/wizard/generate_wizard.py`

**Implementation**:

```python
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
            raise ValidationError(
                message="Schema name can only contain letters, numbers, underscores, and hyphens",
                cursor_position=len(document.text),
            )
```

**Testing**: Test with valid and invalid schema names

### Phase 2: Implement GenerateWizard Class (60 minutes)

**Goal**: Create the main wizard class with all prompts and logic

#### Task 2.1: Create GenerateWizard Class Structure

**Same file**: `src/dbt_to_lookml/wizard/generate_wizard.py`

**Implementation**:

```python
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
        detected_input_dir: Optional[Path] = None,
        detected_output_dir: Optional[Path] = None,
        detected_schema: Optional[str] = None,
    ) -> None:
        """Initialize generate wizard.

        Args:
            mode: Wizard interaction mode (PROMPT or TUI).
            detected_input_dir: Auto-detected input directory from DTL-017.
            detected_output_dir: Auto-detected output directory from DTL-017.
            detected_schema: Auto-detected schema name from YAML files.
        """
        super().__init__(mode=mode)
        self.detected_input_dir = detected_input_dir
        self.detected_output_dir = detected_output_dir
        self.detected_schema = detected_schema
        self.wizard_config: Optional[GenerateWizardConfig] = None

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
```

**Pattern reference**: Similar to validator pattern used in existing parsers

#### Task 2.2: Implement Prompt Methods (Required Fields)

**Same file**: Add prompt methods to GenerateWizard class

**Implementation**:

```python
    def _prompt_input_dir(self) -> Path:
        """Prompt for input directory containing semantic model YAML files.

        Returns:
            Path to input directory selected by user.

        Raises:
            ValueError: If user cancels prompt.
        """
        default = str(self.detected_input_dir) if self.detected_input_dir else "semantic_models"
        hint = " (auto-detected)" if self.detected_input_dir else ""

        result = questionary.path(
            f"Input directory{hint}:",
            default=default,
            validate=PathValidator(
                must_be_dir=True,
                message_prefix="Input directory"
            ),
            only_directories=True,
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return Path(result)

    def _prompt_output_dir(self) -> Path:
        """Prompt for output directory for generated LookML files.

        Returns:
            Path to output directory selected by user.

        Raises:
            ValueError: If user cancels prompt.
        """
        default = str(self.detected_output_dir) if self.detected_output_dir else "build/lookml"
        hint = " (auto-detected)" if self.detected_output_dir else ""

        result = questionary.text(
            f"Output directory{hint}:",
            default=default,
            validate=PathValidator(message_prefix="Output directory"),
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return Path(result)

    def _prompt_schema(self) -> str:
        """Prompt for database schema name.

        Returns:
            Schema name entered by user.

        Raises:
            ValueError: If user cancels prompt.
        """
        default = self.detected_schema if self.detected_schema else "public"
        hint = " (from YAML)" if self.detected_schema else ""

        result = questionary.text(
            f"Database schema name{hint}:",
            default=default,
            validate=SchemaValidator(),
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return result
```

#### Task 2.3: Implement Prompt Methods (Optional String Fields)

**Same file**: Add optional field prompts

**Implementation**:

```python
    def _prompt_view_prefix(self) -> str:
        """Prompt for optional view prefix.

        Returns:
            View prefix string (may be empty).

        Raises:
            ValueError: If user cancels prompt.
        """
        result = questionary.text(
            "View prefix (optional, press Enter to skip):",
            default="",
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return result

    def _prompt_explore_prefix(self) -> str:
        """Prompt for optional explore prefix.

        Returns:
            Explore prefix string (may be empty).

        Raises:
            ValueError: If user cancels prompt.
        """
        result = questionary.text(
            "Explore prefix (optional, press Enter to skip):",
            default="",
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return result

    def _prompt_connection(self) -> str:
        """Prompt for Looker connection name.

        Returns:
            Connection name string.

        Raises:
            ValueError: If user cancels prompt.
        """
        result = questionary.text(
            "Looker connection name:",
            default="redshift_test",
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return result

    def _prompt_model_name(self) -> str:
        """Prompt for model file name (without extension).

        Returns:
            Model name string.

        Raises:
            ValueError: If user cancels prompt.
        """
        result = questionary.text(
            "Model file name (without extension):",
            default="semantic_model",
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return result
```

#### Task 2.4: Implement Prompt Methods (Timezone and Flags)

**Same file**: Add timezone and boolean flag prompts

**Implementation**:

```python
    def _prompt_convert_tz(self) -> Optional[bool]:
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

        return result

    def _prompt_additional_options(self) -> list[str]:
        """Prompt for additional boolean options using checkboxes.

        Returns:
            List of selected option keys (e.g., ["dry-run", "show-summary"]).

        Raises:
            ValueError: If user cancels prompt.
        """
        result = questionary.checkbox(
            "Additional options (use Space to select, Enter to continue):",
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
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return result

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
```

**Pattern reference**: Similar to CLI option handling in `__main__.py`

### Phase 3: Create Entry Point and Detection Integration (20 minutes)

**Goal**: Wire up detection module and create CLI entry point

#### Task 3.1: Implement run_generate_wizard Entry Point

**Same file**: `src/dbt_to_lookml/wizard/generate_wizard.py`

**Implementation**:

```python
def run_generate_wizard(
    mode: WizardMode = WizardMode.PROMPT,
    execute: bool = False,
) -> Optional[str]:
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
    # Import detection module for smart defaults (DTL-017 integration)
    try:
        from dbt_to_lookml.wizard.detection import (
            detect_semantic_models_dir,
            detect_output_dir,
            detect_schema_name,
        )

        detected_input = detect_semantic_models_dir()
        detected_output = detect_output_dir()
        detected_schema = detect_schema_name(detected_input) if detected_input else None
    except ImportError:
        # Detection module not available yet, use None defaults
        detected_input = None
        detected_output = None
        detected_schema = None

    # Create and run wizard
    wizard = GenerateWizard(
        mode=mode,
        detected_input_dir=detected_input,
        detected_output_dir=detected_output,
        detected_schema=detected_schema,
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
        import pyperclip

        pyperclip.copy(wizard.get_command_string(multiline=False))
        console.print("\n[dim]✓ Command copied to clipboard[/dim]")
    except ImportError:
        # pyperclip not available, skip clipboard silently
        pass
    except Exception:
        # Clipboard access failed (e.g., no display), skip silently
        pass

    # Execute if requested
    if execute:
        console.print("\n[yellow]Executing command...[/yellow]\n")
        from dbt_to_lookml.__main__ import generate
        import click

        # Convert config to Click context and invoke
        ctx = click.Context(generate)
        ctx.params = config
        ctx.invoke(generate, **config)

    return command_str
```

**Pattern reference**: Similar to CLI command implementation in `__main__.py`

#### Task 3.2: Create Detection Module Stub (if DTL-017 not ready)

**File**: `src/dbt_to_lookml/wizard/detection.py` (new, temporary)

**Implementation**:

```python
"""Stub for project detection module (DTL-017).

This stub provides minimal functionality until DTL-017 is fully implemented.
Once DTL-017 is complete, this file will be replaced with the full implementation.
"""

from pathlib import Path
from typing import Optional


def detect_semantic_models_dir() -> Optional[Path]:
    """Detect semantic models directory.

    Searches for common directory names containing YAML files.

    Returns:
        Path to semantic_models directory if found, None otherwise.
    """
    # Check common locations
    candidates = [
        Path("semantic_models"),
        Path("models"),
        Path("dbt_models"),
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            # Check if it contains YAML files
            yaml_files = list(candidate.glob("*.yml")) + list(candidate.glob("*.yaml"))
            if yaml_files:
                return candidate

    return None


def detect_output_dir() -> Optional[Path]:
    """Detect likely output directory.

    Returns:
        Path to build/lookml or lookml directory if exists, None otherwise.
    """
    candidates = [
        Path("build/lookml"),
        Path("lookml"),
        Path("output"),
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate

    return None


def detect_schema_name(input_dir: Optional[Path] = None) -> Optional[str]:
    """Detect schema name from YAML files.

    Args:
        input_dir: Directory containing YAML files.

    Returns:
        Schema name extracted from first YAML file, None if not found.
    """
    if input_dir is None:
        return None

    # Try to parse first YAML file for schema
    try:
        import yaml

        yaml_files = list(input_dir.glob("*.yml")) + list(input_dir.glob("*.yaml"))
        if not yaml_files:
            return None

        with open(yaml_files[0], "r") as f:
            data = yaml.safe_load(f)

        # Look for schema in semantic_model -> model -> schema
        if isinstance(data, dict):
            if "semantic_model" in data:
                model = data["semantic_model"].get("model", {})
                if "schema" in model:
                    return model["schema"]

    except Exception:
        # Parsing failed, return None
        pass

    return None
```

**Note**: This stub will be replaced when DTL-017 is implemented

### Phase 4: CLI Integration (15 minutes)

**Goal**: Add wizard command to CLI

#### Task 4.1: Add wizard Command Group (if not exists from DTL-015)

**File**: `src/dbt_to_lookml/__main__.py`

**Implementation**: Add after the `validate` command (around line 397):

```python
# Wizard command group (from DTL-015)
@cli.group()
def wizard() -> None:
    """Interactive wizards for building commands."""
    pass


@wizard.command(name="generate")
@click.option(
    "--execute",
    "-x",
    is_flag=True,
    help="Execute the generated command immediately after wizard completes",
)
def wizard_generate(execute: bool) -> None:
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

      # Run wizard and execute command immediately
      dbt-to-lookml wizard generate --execute
    """
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
```

**Pattern reference**: Follows existing CLI command patterns

### Phase 5: Comprehensive Testing (40 minutes)

**Goal**: Create thorough unit and CLI tests

#### Task 5.1: Create Unit Tests for GenerateWizardConfig

**File**: `src/tests/unit/test_generate_wizard.py` (new)

**Implementation**:

```python
"""Unit tests for generate wizard."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from questionary import ValidationError

from dbt_to_lookml.wizard.generate_wizard import (
    GenerateWizard,
    GenerateWizardConfig,
    PathValidator,
    SchemaValidator,
)
from dbt_to_lookml.wizard.types import WizardMode


class TestGenerateWizardConfig:
    """Test suite for GenerateWizardConfig dataclass."""

    def test_to_command_parts_minimal(self) -> None:
        """Test command parts generation with minimal config."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
        )

        parts = config.to_command_parts()

        assert "dbt-to-lookml" in parts
        assert "generate" in parts
        assert "-i" in parts
        assert "input" in parts
        assert "-o" in parts
        assert "output" in parts
        assert "-s" in parts
        assert "public" in parts

    def test_to_command_parts_with_prefixes(self) -> None:
        """Test command parts with view and explore prefixes."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
            view_prefix="v_",
            explore_prefix="e_",
        )

        parts = config.to_command_parts()

        assert "--view-prefix" in parts
        assert "v_" in parts
        assert "--explore-prefix" in parts
        assert "e_" in parts

    def test_to_command_parts_with_timezone(self) -> None:
        """Test command parts with timezone conversion."""
        # Test convert_tz=True
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
            convert_tz=True,
        )
        assert "--convert-tz" in config.to_command_parts()

        # Test convert_tz=False
        config.convert_tz = False
        assert "--no-convert-tz" in config.to_command_parts()

        # Test convert_tz=None (not in output)
        config.convert_tz = None
        parts = config.to_command_parts()
        assert "--convert-tz" not in parts
        assert "--no-convert-tz" not in parts

    def test_to_command_parts_with_flags(self) -> None:
        """Test command parts with boolean flags."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
            dry_run=True,
            no_validation=True,
            show_summary=True,
        )

        parts = config.to_command_parts()

        assert "--dry-run" in parts
        assert "--no-validation" in parts
        assert "--show-summary" in parts

    def test_to_command_string_multiline(self) -> None:
        """Test multiline command string formatting."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
        )

        command = config.to_command_string(multiline=True)

        assert "\\\n" in command
        assert "dbt-to-lookml" in command

    def test_to_command_string_single_line(self) -> None:
        """Test single-line command string formatting."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
        )

        command = config.to_command_string(multiline=False)

        assert "\\\n" not in command
        assert "dbt-to-lookml" in command
```

#### Task 5.2: Create Unit Tests for Validators

**Same file**: Add validator test classes

**Implementation**:

```python
class TestPathValidator:
    """Test suite for PathValidator."""

    def test_validates_empty_path(self) -> None:
        """Test that empty paths are rejected."""
        validator = PathValidator()

        doc = MagicMock()
        doc.text = ""

        with pytest.raises(ValidationError, match="cannot be empty"):
            validator.validate(doc)

    def test_validates_nonexistent_path_when_required(self, tmp_path: Path) -> None:
        """Test that nonexistent paths are rejected when must_exist=True."""
        validator = PathValidator(must_exist=True)

        nonexistent = tmp_path / "does_not_exist"
        doc = MagicMock()
        doc.text = str(nonexistent)

        with pytest.raises(ValidationError, match="does not exist"):
            validator.validate(doc)

    def test_validates_file_when_directory_required(self, tmp_path: Path) -> None:
        """Test that files are rejected when must_be_dir=True."""
        validator = PathValidator(must_be_dir=True)

        test_file = tmp_path / "test.txt"
        test_file.touch()

        doc = MagicMock()
        doc.text = str(test_file)

        with pytest.raises(ValidationError, match="must be a directory"):
            validator.validate(doc)

    def test_accepts_valid_directory(self, tmp_path: Path) -> None:
        """Test that valid directories are accepted."""
        validator = PathValidator(must_be_dir=True)

        doc = MagicMock()
        doc.text = str(tmp_path)

        # Should not raise
        validator.validate(doc)

    def test_custom_message_prefix(self) -> None:
        """Test custom error message prefix."""
        validator = PathValidator(message_prefix="Input directory")

        doc = MagicMock()
        doc.text = ""

        with pytest.raises(ValidationError, match="Input directory cannot be empty"):
            validator.validate(doc)


class TestSchemaValidator:
    """Test suite for SchemaValidator."""

    def test_rejects_empty_schema(self) -> None:
        """Test that empty schema names are rejected."""
        validator = SchemaValidator()

        doc = MagicMock()
        doc.text = ""

        with pytest.raises(ValidationError, match="cannot be empty"):
            validator.validate(doc)

    def test_rejects_leading_whitespace(self) -> None:
        """Test that leading whitespace is rejected."""
        validator = SchemaValidator()

        doc = MagicMock()
        doc.text = " public"

        with pytest.raises(ValidationError, match="leading/trailing whitespace"):
            validator.validate(doc)

    def test_rejects_trailing_whitespace(self) -> None:
        """Test that trailing whitespace is rejected."""
        validator = SchemaValidator()

        doc = MagicMock()
        doc.text = "public "

        with pytest.raises(ValidationError, match="leading/trailing whitespace"):
            validator.validate(doc)

    def test_rejects_invalid_characters(self) -> None:
        """Test that invalid characters are rejected."""
        validator = SchemaValidator()

        doc = MagicMock()
        doc.text = "public.schema"

        with pytest.raises(ValidationError, match="can only contain"):
            validator.validate(doc)

    def test_accepts_valid_schema_names(self) -> None:
        """Test that valid schema names are accepted."""
        validator = SchemaValidator()

        valid_names = [
            "public",
            "my_schema",
            "schema123",
            "my-schema",
            "schema_123_test",
        ]

        for name in valid_names:
            doc = MagicMock()
            doc.text = name

            # Should not raise
            validator.validate(doc)
```

#### Task 5.3: Create Unit Tests for GenerateWizard

**Same file**: Add wizard test class

**Implementation**:

```python
class TestGenerateWizard:
    """Test suite for GenerateWizard class."""

    def test_initialization_default(self) -> None:
        """Test wizard initialization with defaults."""
        wizard = GenerateWizard()

        assert wizard.mode == WizardMode.PROMPT
        assert wizard.detected_input_dir is None
        assert wizard.detected_output_dir is None
        assert wizard.detected_schema is None

    def test_initialization_with_detected_values(self) -> None:
        """Test wizard initialization with detected values."""
        wizard = GenerateWizard(
            detected_input_dir=Path("semantic_models"),
            detected_output_dir=Path("build/lookml"),
            detected_schema="analytics",
        )

        assert wizard.detected_input_dir == Path("semantic_models")
        assert wizard.detected_output_dir == Path("build/lookml")
        assert wizard.detected_schema == "analytics"

    def test_validate_config_valid(self) -> None:
        """Test configuration validation with valid config."""
        wizard = GenerateWizard()

        config = {
            "input_dir": str(Path.cwd()),
            "output_dir": "build",
            "schema": "public",
        }

        is_valid, error = wizard.validate_config(config)

        assert is_valid is True
        assert error == ""

    def test_validate_config_missing_required(self) -> None:
        """Test configuration validation with missing required fields."""
        wizard = GenerateWizard()

        # Missing input_dir
        config = {"output_dir": "build", "schema": "public"}
        is_valid, error = wizard.validate_config(config)
        assert is_valid is False
        assert "Input directory is required" in error

    def test_validate_config_invalid_path(self, tmp_path: Path) -> None:
        """Test configuration validation with invalid paths."""
        wizard = GenerateWizard()

        nonexistent = tmp_path / "does_not_exist"
        config = {
            "input_dir": str(nonexistent),
            "output_dir": "output",
            "schema": "public",
        }

        is_valid, error = wizard.validate_config(config)

        assert is_valid is False
        assert "does not exist" in error

    def test_get_command_string_before_run(self) -> None:
        """Test that get_command_string raises error before wizard runs."""
        wizard = GenerateWizard()

        with pytest.raises(ValueError, match="has not been run yet"):
            wizard.get_command_string()

    @patch("questionary.path")
    @patch("questionary.text")
    @patch("questionary.select")
    @patch("questionary.checkbox")
    def test_run_wizard_success(
        self,
        mock_checkbox: MagicMock,
        mock_select: MagicMock,
        mock_text: MagicMock,
        mock_path: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful wizard run with mocked prompts."""
        # Setup mock returns
        mock_path.return_value.ask.return_value = str(tmp_path)
        mock_text.return_value.ask.side_effect = [
            "build/lookml",
            "analytics",
            "",
            "",
            "redshift_test",
            "semantic_model",
        ]
        mock_select.return_value.ask.return_value = None
        mock_checkbox.return_value.ask.return_value = ["dry-run", "show-summary"]

        wizard = GenerateWizard()
        config = wizard.run()

        assert config["input_dir"] == str(tmp_path)
        assert config["output_dir"] == "build/lookml"
        assert config["schema"] == "analytics"
        assert config["dry_run"] is True
        assert config["show_summary"] is True
        assert config["no_validation"] is False
```

**Pattern reference**: Similar to existing test patterns in `test_lookml_generator.py`

#### Task 5.4: Create CLI Tests

**File**: `src/tests/test_cli_wizard.py` (new or update existing)

**Implementation**:

```python
"""CLI tests for wizard commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dbt_to_lookml.__main__ import cli


class TestWizardGenerateCommand:
    """Test suite for wizard generate command."""

    def test_wizard_generate_command_exists(self) -> None:
        """Test that wizard generate command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["wizard", "generate", "--help"])

        assert result.exit_code == 0
        assert "Interactive wizard" in result.output
        assert "--execute" in result.output

    def test_wizard_generate_command_cancelled(self) -> None:
        """Test wizard generate command when user cancels."""
        runner = CliRunner()

        # Simulate Ctrl-C cancellation
        result = runner.invoke(
            cli,
            ["wizard", "generate"],
            input="\x03",  # Ctrl-C
        )

        # Should exit gracefully
        assert "cancelled" in result.output.lower()

    @patch("dbt_to_lookml.wizard.generate_wizard.questionary")
    def test_wizard_generate_with_mocked_inputs(
        self, mock_questionary: MagicMock, tmp_path: Path
    ) -> None:
        """Test wizard generate with mocked questionary inputs."""
        runner = CliRunner()

        # Setup comprehensive mock chain for all prompts
        mock_questionary.path.return_value.ask.return_value = str(tmp_path)
        mock_questionary.text.return_value.ask.side_effect = [
            "build/lookml",
            "public",
            "",
            "",
            "redshift_test",
            "semantic_model",
        ]
        mock_questionary.select.return_value.ask.return_value = None
        mock_questionary.checkbox.return_value.ask.return_value = []

        result = runner.invoke(cli, ["wizard", "generate"])

        assert result.exit_code == 0
        assert "Generated Command" in result.output
```

**Pattern reference**: Similar to existing CLI tests

### Phase 6: Documentation and Validation (20 minutes)

**Goal**: Update documentation and run quality gates

#### Task 6.1: Update CLAUDE.md

**File**: `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md`

**Add to "Development Commands" section**:

```markdown
### Wizard Commands

```bash
# Run interactive wizard for generate command
dbt-to-lookml wizard generate

# Run wizard and execute command immediately
dbt-to-lookml wizard generate --execute

# Wizard provides:
# - Smart defaults from project detection
# - Real-time input validation
# - Contextual help for each option
# - Final command preview
# - Clipboard copy (if pyperclip available)
```
```

#### Task 6.2: Run Quality Gates

**Execute validation commands**:

```bash
# Type checking
make type-check

# Unit tests
make test-fast

# Coverage check
make test-coverage

# Lint check
make lint
```

#### Task 6.3: Manual Testing

**Test scenarios**:

1. Run wizard with defaults: `dbt-to-lookml wizard generate`
2. Test cancellation with Ctrl-C
3. Test invalid inputs (empty paths, invalid schema names)
4. Test with detected defaults (if DTL-017 available)
5. Test --execute flag
6. Test clipboard copy (if pyperclip installed)

## File Changes

### Files to Create

#### `src/dbt_to_lookml/wizard/generate_wizard.py`

**Purpose**: Main wizard implementation module

**Size**: ~650 lines

**Structure**:
- Imports and setup
- GenerateWizardConfig dataclass (~80 lines)
- PathValidator class (~40 lines)
- SchemaValidator class (~30 lines)
- GenerateWizard class (~300 lines)
  - `__init__`, `run`, `validate_config`
  - 9+ prompt methods
  - `get_command_string`
- run_generate_wizard entry point (~80 lines)

#### `src/dbt_to_lookml/wizard/detection.py` (stub)

**Purpose**: Project detection stub (until DTL-017)

**Size**: ~80 lines

**Structure**:
- detect_semantic_models_dir()
- detect_output_dir()
- detect_schema_name()

**Note**: Will be replaced by DTL-017 implementation

#### `src/tests/unit/test_generate_wizard.py`

**Purpose**: Unit tests for wizard module

**Size**: ~350 lines

**Structure**:
- TestGenerateWizardConfig (7 tests)
- TestPathValidator (5 tests)
- TestSchemaValidator (5 tests)
- TestGenerateWizard (7 tests)

#### `src/tests/test_cli_wizard.py`

**Purpose**: CLI integration tests

**Size**: ~80 lines

**Structure**:
- TestWizardGenerateCommand (3 tests)

### Files to Modify

#### `src/dbt_to_lookml/__main__.py`

**Changes**:
- Add wizard command group (if not exists from DTL-015)
- Add wizard_generate command (~40 lines)

**Location**: After validate command (line ~397)

**Estimated additions**: ~45 lines

#### `CLAUDE.md`

**Changes**:
- Add wizard commands section to Development Commands

**Location**: Development Commands section

**Estimated additions**: ~15 lines

## Testing Strategy

### Unit Tests Coverage

**Module**: `generate_wizard.py`

**Test Coverage Goals**: 95%+

**Test Breakdown**:

1. **GenerateWizardConfig** (7 tests, 100% coverage):
   - test_to_command_parts_minimal
   - test_to_command_parts_with_prefixes
   - test_to_command_parts_with_timezone
   - test_to_command_parts_with_flags
   - test_to_command_string_multiline
   - test_to_command_string_single_line
   - test_to_command_parts_with_custom_connection_and_model

2. **PathValidator** (5 tests, 100% coverage):
   - test_validates_empty_path
   - test_validates_nonexistent_path_when_required
   - test_validates_file_when_directory_required
   - test_accepts_valid_directory
   - test_custom_message_prefix

3. **SchemaValidator** (5 tests, 100% coverage):
   - test_rejects_empty_schema
   - test_rejects_leading_whitespace
   - test_rejects_trailing_whitespace
   - test_rejects_invalid_characters
   - test_accepts_valid_schema_names

4. **GenerateWizard** (7 tests, 95% coverage):
   - test_initialization_default
   - test_initialization_with_detected_values
   - test_validate_config_valid
   - test_validate_config_missing_required
   - test_validate_config_invalid_path
   - test_get_command_string_before_run
   - test_run_wizard_success

**Total**: 24 unit tests

### CLI Tests Coverage

**Module**: `__main__.py` (wizard command)

**Test Cases** (3 tests):
- test_wizard_generate_command_exists
- test_wizard_generate_command_cancelled
- test_wizard_generate_with_mocked_inputs

### Integration Testing

**Manual test cases**:

1. **Happy path**: Run wizard, accept all defaults, generate command
2. **Custom values**: Enter custom values for all prompts
3. **Cancellation**: Test Ctrl-C at various stages
4. **Validation errors**: Test invalid paths, invalid schema names
5. **Detection integration**: Test with and without detected defaults
6. **Execution**: Test --execute flag
7. **Clipboard**: Test clipboard copy (if pyperclip available)

### Edge Cases

1. **No detection module**: Graceful fallback to hardcoded defaults
2. **No clipboard module**: Silent skip of clipboard functionality
3. **Invalid input directory**: Validator rejects with clear message
4. **User cancels mid-wizard**: Clean exit with cancellation message
5. **questionary returns None**: Proper ValueError handling
6. **Empty project**: No detected defaults, use hardcoded values

## Validation Commands

**Type checking**:
```bash
mypy src/dbt_to_lookml/wizard/generate_wizard.py --strict
make type-check
```

**Unit tests**:
```bash
pytest src/tests/unit/test_generate_wizard.py -v
make test-fast
```

**Coverage check**:
```bash
make test-coverage
# Verify generate_wizard.py shows 95%+ coverage
```

**Lint check**:
```bash
make lint
make format  # Auto-fix issues
```

**Full quality gate**:
```bash
make quality-gate
```

## Dependencies

### Existing Dependencies

**From DTL-015** (wizard infrastructure):
- `questionary`: Interactive prompts and validation
- `prompt_toolkit`: Underlying prompt library
- `rich`: Syntax highlighting and console output
- `click`: CLI framework

**From existing codebase**:
- `pathlib`: Path handling
- `dataclasses`: Configuration dataclass
- `typing`: Type annotations

### New Dependencies

**Optional**:
- `pyperclip`: Clipboard integration (optional, graceful degradation)

**To add** (if not in DTL-015):
```toml
[project.optional-dependencies]
wizard = [
    "questionary>=2.0",
    "pyperclip>=1.8",  # Optional clipboard support
]
```

### Dependency on Other Issues

**Blocking dependencies**:
- DTL-015: Must provide BaseWizard, WizardMode, WizardConfig types
- DTL-017: Should provide detection module (can use stub if not ready)

**Blocked issues**:
- DTL-019: Validation preview integration
- DTL-021: Comprehensive wizard testing

## Implementation Notes

### Design Decisions

1. **Sequential prompts vs. form**: Sequential prompts chosen for simplicity and better focus
2. **questionary vs. click.prompt**: questionary provides better UX with validation
3. **Dataclass for config**: Type safety and easy conversion to command args
4. **Optional clipboard**: Graceful degradation if pyperclip unavailable
5. **Detection integration**: Try/except import for graceful fallback

### Code Patterns

1. **questionary usage**:
   ```python
   result = questionary.text("Prompt:", default="value").ask()
   if result is None:
       raise ValueError("Wizard cancelled")
   ```

2. **Validator pattern**:
   ```python
   class CustomValidator(Validator):
       def validate(self, document):
           if not valid:
               raise ValidationError(message="...", cursor_position=...)
   ```

3. **Command building**:
   ```python
   parts = ["command", "subcommand"]
   if optional_value:
       parts.extend(["--flag", optional_value])
   ```

### Type Safety

All code follows mypy --strict:
- Explicit type annotations on all methods
- Optional[T] for nullable values
- Path type for filesystem paths
- Proper exception types in raises

### Error Handling

1. **User cancellation**: Catch KeyboardInterrupt, raise ValueError
2. **questionary None return**: Check and raise ValueError
3. **Validation errors**: ValidationError with cursor position
4. **Import errors**: Try/except for optional dependencies
5. **Invalid config**: validate_config returns (bool, str) tuple

## Security Considerations

1. **Path validation**: Prevents path traversal attacks
2. **Schema validation**: Ensures safe SQL identifiers
3. **Input sanitization**: Validators reject invalid characters
4. **Command display**: Shows exact command before execution
5. **No shell injection**: All values validated before use

## Performance Considerations

1. **Wizard startup**: <100ms with detection
2. **Prompt response**: Instant (no delays)
3. **Validation**: Real-time, <10ms per validation
4. **Memory usage**: Minimal (~1MB for config object)
5. **Detection scan**: <100ms (from DTL-017 requirement)

## Success Metrics

After implementation, verify:

- [ ] `dbt-to-lookml wizard generate` command exists
- [ ] Wizard prompts for all 9+ options sequentially
- [ ] Each prompt shows description, default, hints
- [ ] Real-time validation works for all inputs
- [ ] Required fields are enforced (cannot skip)
- [ ] Optional fields can be skipped with Enter
- [ ] Final command displayed with syntax highlighting
- [ ] Clipboard copy works (if pyperclip available)
- [ ] --execute flag executes command
- [ ] Ctrl-C cancellation works at any stage
- [ ] Detection integration provides smart defaults
- [ ] mypy --strict passes with no errors
- [ ] pytest shows 95%+ coverage
- [ ] make quality-gate passes
- [ ] Manual testing shows excellent UX

## Implementation Checklist

### Core Implementation
- [ ] Create `src/dbt_to_lookml/wizard/generate_wizard.py`
- [ ] Implement `GenerateWizardConfig` dataclass
- [ ] Implement `to_command_parts()` method
- [ ] Implement `to_command_string()` method
- [ ] Implement `PathValidator` class
- [ ] Implement `SchemaValidator` class
- [ ] Implement `GenerateWizard.__init__()`
- [ ] Implement `GenerateWizard.run()`
- [ ] Implement `GenerateWizard.validate_config()`
- [ ] Implement `_prompt_input_dir()`
- [ ] Implement `_prompt_output_dir()`
- [ ] Implement `_prompt_schema()`
- [ ] Implement `_prompt_view_prefix()`
- [ ] Implement `_prompt_explore_prefix()`
- [ ] Implement `_prompt_connection()`
- [ ] Implement `_prompt_model_name()`
- [ ] Implement `_prompt_convert_tz()`
- [ ] Implement `_prompt_additional_options()`
- [ ] Implement `get_command_string()`
- [ ] Implement `run_generate_wizard()` entry point
- [ ] Add clipboard integration (optional)
- [ ] Add syntax highlighting for command display

### Detection Integration
- [ ] Create `src/dbt_to_lookml/wizard/detection.py` (stub if needed)
- [ ] Implement `detect_semantic_models_dir()`
- [ ] Implement `detect_output_dir()`
- [ ] Implement `detect_schema_name()`
- [ ] Add import with try/except in generate_wizard.py
- [ ] Pass detected values to wizard constructor

### CLI Integration
- [ ] Add wizard command group to `__main__.py` (if not from DTL-015)
- [ ] Add `wizard_generate` command
- [ ] Add --execute flag
- [ ] Wire up to `run_generate_wizard()`
- [ ] Handle exceptions and display errors

### Testing
- [ ] Create `src/tests/unit/test_generate_wizard.py`
- [ ] Write 7 tests for GenerateWizardConfig
- [ ] Write 5 tests for PathValidator
- [ ] Write 5 tests for SchemaValidator
- [ ] Write 7 tests for GenerateWizard
- [ ] Create `src/tests/test_cli_wizard.py`
- [ ] Write 3 CLI integration tests
- [ ] Run `make test-fast` - all tests pass
- [ ] Run `make test-coverage` - 95%+ coverage
- [ ] Run `make type-check` - no mypy errors
- [ ] Run `make lint` - no lint errors

### Documentation and Validation
- [ ] Update CLAUDE.md with wizard commands
- [ ] Run `make quality-gate` - all checks pass
- [ ] Manual test: Basic wizard flow
- [ ] Manual test: Cancellation (Ctrl-C)
- [ ] Manual test: Invalid inputs
- [ ] Manual test: Detected defaults
- [ ] Manual test: --execute flag
- [ ] Manual test: Clipboard copy

### Final Verification
- [ ] All 24 unit tests passing
- [ ] All 3 CLI tests passing
- [ ] Coverage 95%+ for generate_wizard.py
- [ ] mypy --strict passes
- [ ] All manual test scenarios verified
- [ ] Issue status updated to ready
- [ ] Spec approved and committed

## Estimated Implementation Time

- **Phase 1**: Core data structures - 30 minutes
- **Phase 2**: GenerateWizard class - 60 minutes
- **Phase 3**: Entry point and detection - 20 minutes
- **Phase 4**: CLI integration - 15 minutes
- **Phase 5**: Testing - 40 minutes
- **Phase 6**: Documentation and validation - 20 minutes

**Total**: ~3 hours

## Next Steps

After DTL-018 completion:

1. **DTL-019**: Add validation preview step to wizard
2. **DTL-020**: Implement TUI mode for wizard
3. **DTL-021**: Comprehensive integration testing
4. Update DTL-017 detection module (replace stub)
5. Consider wizard for validate command
6. Consider config save/load feature

---

## Approval and Execution

This specification is complete and ready for implementation.

**To proceed**:

1. Review this specification
2. Update `.tasks/issues/DTL-018.md` status: `refinement` → `ready`
3. Begin implementation following the checklist
4. Run quality gates after each phase
5. Manual testing before marking complete

**Questions or concerns**: Review with team before proceeding.
