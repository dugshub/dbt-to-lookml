# Implementation Strategy: DTL-018

**Issue**: DTL-018 - Build simple prompt-based wizard for generate command
**Analyzed**: 2025-11-17T15:30:00Z
**Stack**: backend
**Type**: feature

## Approach

Implement an interactive, prompt-based wizard that guides users through building a complete `generate` command by asking sequential questions with smart defaults, real-time validation, and contextual hints. The wizard uses questionary for styled prompts, integrates with DTL-017's detection module for intelligent defaults, and produces a fully-formed command string that can be displayed, copied to clipboard (if available), and optionally executed.

This implementation focuses on developer experience by:
1. Providing clear, contextual prompts with descriptions and format hints
2. Offering smart defaults based on project structure detection
3. Validating inputs in real-time to prevent errors
4. Building confidence by showing the final command before execution
5. Supporting both quick flows (accepting defaults) and detailed customization

The wizard follows the established project patterns (strict typing, rich output, comprehensive testing) and integrates seamlessly with the existing CLI architecture.

## Architecture Impact

**Layer**: CLI Wizard Layer (integrates with existing command system and detection module)

**New Files**:
- `src/dbt_to_lookml/wizard/generate_wizard.py`:
  - `GenerateWizardConfig` dataclass - typed configuration container
  - `PathValidator` class - validates directory paths with contextual messages
  - `SchemaValidator` class - validates schema name format
  - `GenerateWizard` class - main wizard implementation
  - `run_generate_wizard()` - entry point function

**Modified Files**:
- `src/dbt_to_lookml/__main__.py`:
  - Add `@wizard.command(name="generate")` command
  - Wire up to `run_generate_wizard()` from generate_wizard module
  - Handle wizard output (display command, optional execution)

**New Test Files**:
- `src/tests/unit/test_generate_wizard.py`:
  - Unit tests for validators (PathValidator, SchemaValidator)
  - Tests for GenerateWizard configuration building
  - Tests for command string generation
- `src/tests/test_cli_wizard.py`:
  - CLI tests for `wizard generate` command (modify existing if present)
  - Integration tests with mock questionary inputs
  - Test cancellation and error scenarios

## Dependencies

- **Depends on**:
  - DTL-015: Add wizard dependencies and base infrastructure (provides BaseWizard, types, questionary)
  - DTL-017: Implement contextual project detection and smart defaults (provides detection module)
  - Existing CLI infrastructure in `__main__.py` (generate command for reference)

- **Blocking**:
  - DTL-019: Add validation preview and confirmation step (will integrate wizard with preview)
  - DTL-021: Integration, testing, and documentation (comprehensive wizard testing)

- **Related to**:
  - DTL-014 (parent epic - Enhanced CLI with Rich wizard)
  - DTL-016 (enhanced help text - complementary UX improvement)
  - DTL-020 (TUI wizard mode - alternative wizard interface)

## Detailed Implementation Plan

### 1. Create GenerateWizard Module Structure

**File**: `src/dbt_to_lookml/wizard/generate_wizard.py`

#### 1.1 Configuration Dataclass

Define a typed configuration container for wizard outputs:

```python
"""Interactive wizard for building generate commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import questionary
from questionary import Validator, ValidationError
from rich.console import Console

from dbt_to_lookml.wizard.base import BaseWizard
from dbt_to_lookml.wizard.types import WizardConfig, WizardMode

console = Console()


@dataclass
class GenerateWizardConfig:
    """Typed configuration from generate wizard.

    Attributes:
        input_dir: Directory containing semantic model YAML files
        output_dir: Directory to output LookML files
        schema: Database schema name for sql_table_name
        view_prefix: Optional prefix for view names
        explore_prefix: Optional prefix for explore names
        connection: Looker connection name
        model_name: Model file name (without extension)
        convert_tz: Timezone conversion setting (True/False/None)
        dry_run: Preview without writing files
        no_validation: Skip LookML syntax validation
        show_summary: Show detailed generation summary
    """

    input_dir: Path
    output_dir: Path
    schema: str
    view_prefix: str = ""
    explore_prefix: str = ""
    connection: str = "redshift_test"
    model_name: str = "semantic_model"
    convert_tz: Optional[bool] = None
    dry_run: bool = False
    no_validation: bool = False
    show_summary: bool = False

    def to_command_parts(self) -> list[str]:
        """Convert configuration to command line arguments.

        Returns:
            List of command parts for building shell command.
        """
        parts = ["dbt-to-lookml", "generate"]

        # Required arguments
        parts.extend(["-i", str(self.input_dir)])
        parts.extend(["-o", str(self.output_dir)])
        parts.extend(["-s", self.schema])

        # Optional string arguments
        if self.view_prefix:
            parts.extend(["--view-prefix", self.view_prefix])
        if self.explore_prefix:
            parts.extend(["--explore-prefix", self.explore_prefix])
        if self.connection != "redshift_test":
            parts.extend(["--connection", self.connection])
        if self.model_name != "semantic_model":
            parts.extend(["--model-name", self.model_name])

        # Timezone conversion flags
        if self.convert_tz is True:
            parts.append("--convert-tz")
        elif self.convert_tz is False:
            parts.append("--no-convert-tz")

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
            multiline: Format with line continuations for readability.

        Returns:
            Formatted shell command string.
        """
        parts = self.to_command_parts()

        if multiline:
            return " \\\n  ".join(parts)
        else:
            return " ".join(parts)
```

#### 1.2 Custom Validators

Create validators for path and schema inputs:

```python
class PathValidator(Validator):
    """Validator for file system paths.

    Validates that paths are non-empty and optionally checks existence.
    """

    def __init__(
        self,
        must_exist: bool = False,
        must_be_dir: bool = False,
        message_prefix: str = "Path"
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

    def validate(self, document) -> None:
        """Validate path input.

        Args:
            document: Prompt document with user input.

        Raises:
            ValidationError: If path is invalid.
        """
        text = document.text.strip()

        if not text:
            raise ValidationError(
                message=f"{self.message_prefix} cannot be empty",
                cursor_position=len(document.text),
            )

        path = Path(text)

        if self.must_exist and not path.exists():
            raise ValidationError(
                message=f"{self.message_prefix} does not exist: {path}",
                cursor_position=len(document.text),
            )

        if self.must_be_dir and not path.is_dir():
            raise ValidationError(
                message=f"{self.message_prefix} must be a directory: {path}",
                cursor_position=len(document.text),
            )


class SchemaValidator(Validator):
    """Validator for database schema names.

    Ensures schema names follow basic naming conventions:
    - Non-empty
    - Alphanumeric with underscores
    - No leading/trailing whitespace
    """

    def validate(self, document) -> None:
        """Validate schema name.

        Args:
            document: Prompt document with user input.

        Raises:
            ValidationError: If schema name is invalid.
        """
        text = document.text.strip()

        if not text:
            raise ValidationError(
                message="Schema name cannot be empty",
                cursor_position=len(document.text),
            )

        if text != document.text:
            raise ValidationError(
                message="Schema name cannot have leading/trailing whitespace",
                cursor_position=len(document.text),
            )

        # Allow alphanumeric, underscores, and hyphens
        if not all(c.isalnum() or c in ('_', '-') for c in text):
            raise ValidationError(
                message="Schema name can only contain letters, numbers, underscores, and hyphens",
                cursor_position=len(document.text),
            )
```

#### 1.3 GenerateWizard Class

Implement the main wizard logic:

```python
class GenerateWizard(BaseWizard):
    """Interactive wizard for building generate commands.

    Guides users through all generate command options with:
    - Smart defaults from project detection
    - Real-time validation
    - Contextual help text
    - Sequential prompts for all options
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
            mode: Wizard interaction mode (prompt or TUI).
            detected_input_dir: Auto-detected input directory from detection module.
            detected_output_dir: Auto-detected output directory from detection module.
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
            ValueError: If wizard is cancelled by user.
        """
        console.print("\n[bold cyan]Generate Command Wizard[/bold cyan]")
        console.print("[dim]Press Ctrl-C to cancel at any time[/dim]\n")

        try:
            # Run sequential prompts
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

            # Prompt for additional flags
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
        # Required fields
        if not config.get("input_dir"):
            return (False, "Input directory is required")
        if not config.get("output_dir"):
            return (False, "Output directory is required")
        if not config.get("schema"):
            return (False, "Schema name is required")

        # Path validation
        input_path = Path(config["input_dir"])
        if not input_path.exists():
            return (False, f"Input directory does not exist: {input_path}")
        if not input_path.is_dir():
            return (False, f"Input path is not a directory: {input_path}")

        return (True, "")

    def _prompt_input_dir(self) -> Path:
        """Prompt for input directory."""
        default = str(self.detected_input_dir) if self.detected_input_dir else "semantic_models"
        hint = " (auto-detected)" if self.detected_input_dir else ""

        result = questionary.path(
            f"Input directory{hint}:",
            default=default,
            validate=PathValidator(must_be_dir=True, message_prefix="Input directory"),
            only_directories=True,
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return Path(result)

    def _prompt_output_dir(self) -> Path:
        """Prompt for output directory."""
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
        """Prompt for database schema name."""
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

    def _prompt_view_prefix(self) -> str:
        """Prompt for view prefix (optional)."""
        result = questionary.text(
            "View prefix (optional, press Enter to skip):",
            default="",
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return result

    def _prompt_explore_prefix(self) -> str:
        """Prompt for explore prefix (optional)."""
        result = questionary.text(
            "Explore prefix (optional, press Enter to skip):",
            default="",
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return result

    def _prompt_connection(self) -> str:
        """Prompt for Looker connection name."""
        result = questionary.text(
            "Looker connection name:",
            default="redshift_test",
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return result

    def _prompt_model_name(self) -> str:
        """Prompt for model file name."""
        result = questionary.text(
            "Model file name (without extension):",
            default="semantic_model",
        ).ask()

        if result is None:
            raise ValueError("Wizard cancelled")

        return result

    def _prompt_convert_tz(self) -> Optional[bool]:
        """Prompt for timezone conversion setting."""
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
        """Prompt for additional boolean options using checkboxes."""
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

#### 1.4 Entry Point Function

Create a simple entry point for CLI integration:

```python
def run_generate_wizard(
    mode: WizardMode = WizardMode.PROMPT,
    execute: bool = False,
) -> Optional[str]:
    """Run the generate command wizard.

    Args:
        mode: Wizard interaction mode (prompt or TUI).
        execute: Execute the generated command after wizard completes.

    Returns:
        Generated command string, or None if wizard was cancelled.

    Raises:
        ValueError: If wizard validation fails.
    """
    # Import detection module for smart defaults
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
        # Detection module not available, use None defaults
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
    except ValueError as e:
        # Wizard was cancelled
        return None

    # Validate configuration
    is_valid, error_msg = wizard.validate_config(config)
    if not is_valid:
        console.print(f"[bold red]Configuration error:[/bold red] {error_msg}")
        raise ValueError(f"Invalid configuration: {error_msg}")

    # Display final command
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
        # pyperclip not available, skip clipboard
        pass
    except Exception:
        # Clipboard access failed (e.g., no display), skip silently
        pass

    # Execute if requested
    if execute:
        console.print("\n[yellow]Executing command...[/yellow]\n")
        from dbt_to_lookml.__main__ import generate
        import click

        # Convert config to Click context
        ctx = click.Context(generate)
        ctx.params = config
        ctx.invoke(generate, **config)

    return command_str
```

### 2. Integrate with CLI

**File**: `src/dbt_to_lookml/__main__.py`

Add wizard generate command after the existing wizard command group:

```python
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

### 3. Integration with Detection Module (DTL-017)

The wizard imports and uses the detection module for smart defaults. If DTL-017 is not implemented yet, create a stub:

**File**: `src/dbt_to_lookml/wizard/detection.py` (temporary stub if DTL-017 not ready)

```python
"""Stub for project detection module (DTL-017).

This stub provides minimal functionality until DTL-017 is implemented.
"""

from pathlib import Path
from typing import Optional


def detect_semantic_models_dir() -> Optional[Path]:
    """Detect semantic models directory.

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

        with open(yaml_files[0], 'r') as f:
            data = yaml.safe_load(f)

        # Look for schema in common locations
        if isinstance(data, dict):
            # Check semantic_model -> model -> schema
            if 'semantic_model' in data:
                model = data['semantic_model'].get('model', {})
                if 'schema' in model:
                    return model['schema']

    except Exception:
        # Parsing failed, return None
        pass

    return None
```

**Note**: This stub will be replaced when DTL-017 is fully implemented.

### 4. Testing Strategy

**File**: `src/tests/unit/test_generate_wizard.py`

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


class TestPathValidator:
    """Test suite for PathValidator."""

    def test_validates_empty_path(self) -> None:
        """Test that empty paths are rejected."""
        validator = PathValidator()

        # Create mock document with empty text
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

        # Create a file
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
            "input_dir": str(Path.cwd()),  # Use current dir (guaranteed to exist)
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

        # Missing output_dir
        config = {"input_dir": "input", "schema": "public"}
        is_valid, error = wizard.validate_config(config)
        assert is_valid is False
        assert "Output directory is required" in error

        # Missing schema
        config = {"input_dir": "input", "output_dir": "output"}
        is_valid, error = wizard.validate_config(config)
        assert is_valid is False
        assert "Schema name is required" in error

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
            "build/lookml",  # output_dir
            "analytics",     # schema
            "",             # view_prefix
            "",             # explore_prefix
            "redshift_test", # connection
            "semantic_model", # model_name
        ]
        mock_select.return_value.ask.return_value = None  # convert_tz
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

**File**: `src/tests/test_cli_wizard.py` (additions)

```python
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

### 5. Documentation Updates

Update CLAUDE.md with wizard usage examples in the "Development Commands" section:

```markdown
### Wizard Commands

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

## Type Checking Considerations

All code follows strict mypy compliance:

1. **Dataclass typing**: `GenerateWizardConfig` fully typed with explicit types
2. **Validator classes**: Inherit from `questionary.Validator` with typed methods
3. **Optional returns**: Use `Optional[T]` for values that can be None
4. **Path handling**: Use `pathlib.Path` consistently, not strings
5. **Exception handling**: Explicit exception types in raise statements
6. **Method signatures**: All parameters and returns have type annotations
7. **Dict types**: Use `dict[str, Any]` for config dicts (validated by dataclass)

Verification:
```bash
mypy src/dbt_to_lookml/wizard/generate_wizard.py --strict
make type-check
```

## Testing Coverage Goals

- **Unit tests**: 95%+ coverage of generate_wizard module
  - `GenerateWizardConfig`: 6 test cases (command parts, strings, flags)
  - `PathValidator`: 5 test cases (empty, nonexistent, file vs dir, valid, custom message)
  - `SchemaValidator`: 5 test cases (empty, whitespace, invalid chars, valid names)
  - `GenerateWizard`: 7 test cases (initialization, validation, run, command string)

- **CLI tests**: 3 test cases
  - `test_wizard_generate_command_exists()`: Command registration
  - `test_wizard_generate_command_cancelled()`: User cancellation
  - `test_wizard_generate_with_mocked_inputs()`: Full wizard flow

- **Integration**: End-to-end testing in DTL-021

**Target**: 95%+ coverage for generate_wizard module, maintain 95%+ overall

## Implementation Checklist

- [ ] Create `src/dbt_to_lookml/wizard/generate_wizard.py` with full implementation
- [ ] Implement `GenerateWizardConfig` dataclass with command generation methods
- [ ] Implement `PathValidator` and `SchemaValidator` classes
- [ ] Implement `GenerateWizard` class with all 9+ prompts
- [ ] Implement `run_generate_wizard()` entry point function
- [ ] Add clipboard integration (optional pyperclip)
- [ ] Create detection module stub (if DTL-017 not ready)
- [ ] Update `__main__.py` with `wizard generate` command
- [ ] Create `src/tests/unit/test_generate_wizard.py` with 23+ test cases
- [ ] Update `src/tests/test_cli_wizard.py` with 3 new test cases
- [ ] Run `make test-fast` to verify unit tests pass
- [ ] Run `make type-check` to verify mypy compliance
- [ ] Run `make test-coverage` to verify 95%+ coverage
- [ ] Update CLAUDE.md with wizard command examples
- [ ] Manual testing: `dbt-to-lookml wizard generate`
- [ ] Test with detected defaults (if DTL-017 available)
- [ ] Test clipboard copy (if pyperclip installed)
- [ ] Test command execution with `--execute` flag

## Implementation Order

1. **Create dataclass and validators** - 30 min
   - `GenerateWizardConfig` with command generation
   - `PathValidator` and `SchemaValidator`
   - Unit tests for validators

2. **Implement GenerateWizard class** - 60 min
   - All 9 prompt methods
   - Configuration building
   - Command string generation
   - Unit tests for wizard

3. **Create entry point function** - 20 min
   - `run_generate_wizard()`
   - Detection module integration
   - Clipboard support
   - Command display with syntax highlighting

4. **CLI integration** - 15 min
   - Add `wizard generate` command
   - Wire up to entry point
   - CLI tests

5. **Detection module stub** - 15 min (if DTL-017 not ready)
   - Basic directory detection
   - Schema name extraction
   - Fallback to None

6. **Testing and validation** - 40 min
   - Write comprehensive unit tests (23 cases)
   - Write CLI tests (3 cases)
   - Run quality gates
   - Fix any issues

7. **Documentation and manual testing** - 20 min
   - Update CLAUDE.md
   - Manual wizard testing
   - Test all prompt paths
   - Test cancellation

**Estimated total**: 3.5 hours

## Edge Cases and Error Handling

1. **User cancellation (Ctrl-C)**:
   - Caught by KeyboardInterrupt in `run()`
   - Displays friendly "cancelled" message
   - Returns None from `run_generate_wizard()`

2. **questionary returns None**:
   - Happens when user cancels prompt
   - Raise ValueError("Wizard cancelled") immediately
   - Prevents partial configurations

3. **Empty input directory**:
   - Validator rejects before proceeding
   - User sees error and can retry

4. **Detection module unavailable**:
   - Try/except ImportError
   - Fall back to None defaults
   - Wizard still works, just no auto-detection

5. **Clipboard unavailable**:
   - Try/except ImportError for pyperclip
   - Skip clipboard silently if unavailable
   - Command still displayed on screen

6. **Invalid configuration**:
   - `validate_config()` catches issues
   - Display error message
   - Raise ValueError with details

7. **Command execution fails**:
   - Errors from generate command propagate
   - User sees original error message
   - Wizard shows command for manual execution

## Rollout Impact

### User-Facing Changes

- **New command**: `dbt-to-lookml wizard generate`
- **Interactive experience**: Sequential prompts guide users
- **Smart defaults**: Auto-detected values from project structure
- **Command preview**: Shows final command before execution
- **Clipboard support**: Copies command (if pyperclip installed)

### Developer-Facing Changes

- **New module**: `generate_wizard.py` in wizard package
- **Validators**: Reusable PathValidator and SchemaValidator
- **Detection integration**: Uses DTL-017 module for defaults
- **Testing patterns**: Mock questionary prompts in tests

### Backward Compatibility

- **Fully backward compatible**: Existing commands unchanged
- **Optional feature**: Wizard is opt-in, doesn't affect normal CLI usage
- **No new required dependencies**: questionary already added in DTL-015

### Performance Impact

- **Wizard startup**: Negligible (detection module runs fast)
- **Interactive prompts**: Instant response, no delays
- **Validation**: Real-time, no noticeable lag
- **Memory**: Minimal (single config object in memory)

## Future Extensibility

This wizard design enables:

1. **DTL-019 integration**: Add preview panel before execution
2. **DTL-020 TUI mode**: Replace prompts with Textual widgets
3. **Validate wizard**: Create similar wizard for validate command
4. **Config save/load**: Add ability to save wizard answers
5. **Wizard templates**: Pre-filled wizards for common scenarios

## Notes for Implementation

1. **questionary patterns**:
   - Use `.ask()` to get user input
   - Check for None return (user cancelled)
   - Use validators for real-time validation
   - Use checkbox for multi-select options

2. **Command building**:
   - Build command in dataclass methods
   - Separate multiline and single-line formats
   - Match exact CLI argument names

3. **Detection integration**:
   - Import detection functions
   - Handle ImportError gracefully
   - Pass detected values to wizard
   - Show "(auto-detected)" hint in prompts

4. **Clipboard handling**:
   - pyperclip is optional dependency
   - Try import, skip if unavailable
   - Catch all exceptions (display issues)
   - Don't block on clipboard failures

5. **Validation philosophy**:
   - Validate early (during prompts)
   - Validate again before execution
   - Provide helpful error messages
   - Allow retry on validation errors

6. **Testing strategy**:
   - Mock questionary for deterministic tests
   - Test validators independently
   - Test command building separately
   - Test full wizard flow with mocks

## Security Considerations

- **Path validation**: Prevents path traversal attacks
- **Input sanitization**: Schema validator ensures safe names
- **Command display**: Shows exact command to be executed
- **No shell injection**: All paths validated before use
- **Safe defaults**: Connection and model names are safe

## Success Metrics

- [ ] Wizard prompts for all 9+ generate options
- [ ] Each prompt shows description and default value
- [ ] Input validation happens in real-time
- [ ] Required fields (input-dir, output-dir, schema) enforced
- [ ] Optional fields can be skipped with Enter
- [ ] Final command displayed with syntax highlighting
- [ ] Command copied to clipboard (if pyperclip available)
- [ ] `dbt-to-lookml wizard generate` runs successfully
- [ ] `dbt-to-lookml wizard generate --execute` executes command
- [ ] Detection module integration works (if DTL-017 available)
- [ ] `make type-check` passes with no mypy errors
- [ ] `make test-fast` passes all tests
- [ ] `make test-coverage` shows 95%+ coverage
- [ ] Manual testing shows good UX

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-018.md`
3. Change status from `refinement` to `awaiting-strategy-review`, then to `strategy-approved`
4. Run: `/implement:1-spec DTL-018`
