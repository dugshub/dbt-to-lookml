# Implementation Strategy: DTL-019

**Issue**: DTL-019 - Add validation preview and confirmation step
**Analyzed**: 2025-11-12T21:15:00Z
**Stack**: backend
**Type**: feature

## Approach

Implement a preview and confirmation system that displays rich-formatted summary panels showing what the command will do before execution. This enhances user confidence and prevents accidental operations by providing clear visibility into file counts, estimated outputs, configuration settings, and the full command that will be executed. The system supports both interactive confirmation prompts and automatic execution via `--yes` flag.

The implementation creates a reusable preview module that can be integrated into multiple CLI commands (validate, generate) and serves as the foundation for the wizard system (DTL-018). It uses Rich library components already available in the project for consistent, visually appealing output.

## Architecture Impact

**Layer**: CLI Interface Layer (integrates with existing command system)

**New Files**:
- `src/dbt_to_lookml/preview.py`:
  - `PreviewData` dataclass - structured data for preview display
  - `CommandPreview` class - main preview panel generator
  - `count_yaml_files()` - utility function for file counting
  - `estimate_output_files()` - output estimation logic
  - `format_command()` - command syntax highlighting
  - `show_preview_and_confirm()` - orchestration function

**Modified Files**:
- `src/dbt_to_lookml/__main__.py`:
  - Add `--yes` flag to `generate` command (skip confirmation)
  - Add `--preview` flag to show preview without execution
  - Insert preview/confirmation step before generation logic
  - Add preview-only mode for validation command

**No changes needed to**:
- Core schemas, parsers, or generators
- Existing test fixtures
- Generator interfaces

## Dependencies

- **Depends on**:
  - Rich library (already in dependencies)
  - Click library (already in dependencies)
  - Existing CLI infrastructure in `__main__.py`

- **Blocking**:
  - DTL-018: Build simple prompt-based wizard (will use preview module)
  - DTL-019 should be implemented before DTL-018 to avoid duplication

- **Related to**:
  - DTL-014 (parent epic - Enhanced CLI with Rich wizard)
  - DTL-015 (wizard dependencies - shares some infrastructure)
  - DTL-016 (enhanced help text - complementary UX improvement)

## Detailed Implementation Plan

### 1. Create Preview Module Structure

**File**: `src/dbt_to_lookml/preview.py`

```python
"""Preview and confirmation utilities for CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


@dataclass
class PreviewData:
    """Structured data for command preview display.

    Attributes:
        input_dir: Path to input directory
        output_dir: Path to output directory
        schema: Database schema name
        input_file_count: Number of YAML files found
        estimated_views: Estimated number of view files
        estimated_explores: Number of explores files (typically 1)
        estimated_models: Number of model files (typically 1)
        command_parts: List of command components for display
        additional_config: Dict of additional configuration options
    """

    input_dir: Path
    output_dir: Path
    schema: str
    input_file_count: int
    estimated_views: int
    estimated_explores: int
    estimated_models: int
    command_parts: list[str]
    additional_config: dict[str, Any]


class CommandPreview:
    """Generates rich-formatted preview panels for CLI commands."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize preview generator.

        Args:
            console: Rich console for output (creates new if None)
        """
        self.console = console or Console()

    def render_preview_panel(self, preview_data: PreviewData) -> Panel:
        """Render a preview panel with command details.

        Args:
            preview_data: Structured preview data

        Returns:
            Rich Panel object ready for display
        """
        # Build content sections
        lines = []

        # Input/Output section
        lines.append(
            f"[bold cyan]Input:[/bold cyan]  {preview_data.input_dir} "
            f"([green]{preview_data.input_file_count} YAML files[/green])"
        )
        lines.append(f"[bold cyan]Output:[/bold cyan] {preview_data.output_dir}")
        lines.append(f"[bold cyan]Schema:[/bold cyan] {preview_data.schema}")

        # Additional config (if present)
        if preview_data.additional_config:
            lines.append("")
            lines.append("[bold cyan]Configuration:[/bold cyan]")
            for key, value in preview_data.additional_config.items():
                lines.append(f"  • {key}: {value}")

        # Estimated output section
        lines.append("")
        lines.append("[bold cyan]Estimated output:[/bold cyan]")
        lines.append(f"  • [green]{preview_data.estimated_views}[/green] view files")
        lines.append(
            f"  • [green]{preview_data.estimated_explores}[/green] explores file"
        )
        lines.append(f"  • [green]{preview_data.estimated_models}[/green] model file")

        # Command section with syntax highlighting
        lines.append("")
        lines.append("[bold cyan]Command:[/bold cyan]")

        # Join command parts with line continuation
        command_text = " \\\n  ".join(preview_data.command_parts)

        content = "\n".join(lines)

        # Create panel with command at bottom
        panel = Panel(
            content,
            title="[bold white]Command Preview[/bold white]",
            border_style="cyan",
            padding=(1, 2),
        )

        return panel

    def render_command_syntax(self, command_parts: list[str]) -> Syntax:
        """Render command with syntax highlighting.

        Args:
            command_parts: List of command components

        Returns:
            Syntax object with highlighted shell command
        """
        command_text = " \\\n  ".join(command_parts)
        return Syntax(
            command_text,
            "bash",
            theme="monokai",
            line_numbers=False,
            word_wrap=True,
        )

    def show(self, preview_data: PreviewData) -> None:
        """Display preview panel and command syntax.

        Args:
            preview_data: Structured preview data
        """
        panel = self.render_preview_panel(preview_data)
        self.console.print(panel)

        # Show command separately with syntax highlighting
        self.console.print()
        syntax = self.render_command_syntax(preview_data.command_parts)
        self.console.print(syntax)


def count_yaml_files(directory: Path) -> int:
    """Count YAML files in a directory.

    Args:
        directory: Path to directory to scan

    Returns:
        Number of .yml and .yaml files found
    """
    yml_files = list(directory.glob("*.yml"))
    yaml_files = list(directory.glob("*.yaml"))
    return len(yml_files) + len(yaml_files)


def estimate_output_files(input_file_count: int) -> tuple[int, int, int]:
    """Estimate number of output files to be generated.

    Args:
        input_file_count: Number of input YAML files

    Returns:
        Tuple of (views, explores, models) counts
        - views: Equal to input file count (1 view per semantic model)
        - explores: Always 1 (consolidated explores file)
        - models: Always 1 (consolidated model file)
    """
    # Each semantic model YAML typically generates one view
    views = input_file_count
    explores = 1  # Single explores.lkml file
    models = 1    # Single .model.lkml file

    return views, explores, models


def format_command_parts(
    command_name: str,
    input_dir: Path,
    output_dir: Path,
    schema: str,
    view_prefix: str = "",
    explore_prefix: str = "",
    connection: str = "",
    model_name: str = "",
    convert_tz: bool | None = None,
    dry_run: bool = False,
    no_validation: bool = False,
    no_formatting: bool = False,
    show_summary: bool = False,
) -> list[str]:
    """Format command into parts for display.

    Args:
        command_name: Base command (e.g., "dbt-to-lookml generate")
        input_dir: Input directory path
        output_dir: Output directory path
        schema: Database schema name
        view_prefix: Optional view prefix
        explore_prefix: Optional explore prefix
        connection: Looker connection name
        model_name: Model file name
        convert_tz: Timezone conversion setting
        dry_run: Dry run flag
        no_validation: Skip validation flag
        no_formatting: Skip formatting flag
        show_summary: Show summary flag

    Returns:
        List of command parts for line-wrapped display
    """
    parts = [command_name]

    # Required arguments
    parts.append(f"-i {input_dir}")
    parts.append(f"-o {output_dir}")
    parts.append(f"-s {schema}")

    # Optional arguments
    if view_prefix:
        parts.append(f"--view-prefix {view_prefix}")
    if explore_prefix:
        parts.append(f"--explore-prefix {explore_prefix}")
    if connection and connection != "redshift_test":
        parts.append(f"--connection {connection}")
    if model_name and model_name != "semantic_model":
        parts.append(f"--model-name {model_name}")

    # Boolean flags
    if convert_tz is True:
        parts.append("--convert-tz")
    elif convert_tz is False:
        parts.append("--no-convert-tz")

    if dry_run:
        parts.append("--dry-run")
    if no_validation:
        parts.append("--no-validation")
    if no_formatting:
        parts.append("--no-formatting")
    if show_summary:
        parts.append("--show-summary")

    return parts


def show_preview_and_confirm(
    preview_data: PreviewData,
    auto_confirm: bool = False,
) -> bool:
    """Show preview panel and prompt for confirmation.

    Args:
        preview_data: Structured preview data
        auto_confirm: Skip confirmation prompt (--yes flag)

    Returns:
        True if user confirmed (or auto_confirm=True), False otherwise
    """
    preview = CommandPreview()
    preview.show(preview_data)

    if auto_confirm:
        console.print("\n[yellow]Auto-confirming (--yes flag)[/yellow]")
        return True

    console.print()
    response = console.input(
        "[bold yellow]Execute this command?[/bold yellow] [dim]\\[y/N][/dim]: "
    )

    # Default to No for safety
    confirmed = response.strip().lower() in ("y", "yes")

    if not confirmed:
        console.print("[yellow]Command execution cancelled[/yellow]")

    return confirmed
```

### 2. Update CLI Command with Preview Integration

**File**: `src/dbt_to_lookml/__main__.py`

**Changes to `generate` command** (around line 28):

1. **Add new flags**:
```python
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
```

2. **Update function signature** (around line 107):
```python
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
```

3. **Add preview logic** (insert after timezone validation, around line 140):
```python
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
```

4. **Update existing console output** (around line 142-149):
   - Remove or consolidate the existing "Parsing semantic models" output
   - The preview panel already shows this information

### 3. Testing Strategy

**File**: `src/tests/test_preview.py` (new file)

Create comprehensive unit tests:

```python
"""Tests for preview and confirmation utilities."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from rich.console import Console

from dbt_to_lookml.preview import (
    PreviewData,
    CommandPreview,
    count_yaml_files,
    estimate_output_files,
    format_command_parts,
    show_preview_and_confirm,
)


class TestCountYamlFiles:
    """Tests for count_yaml_files function."""

    def test_count_yml_files(self, tmp_path: Path) -> None:
        """Test counting .yml files."""
        # Create test files
        (tmp_path / "model1.yml").touch()
        (tmp_path / "model2.yml").touch()
        (tmp_path / "readme.txt").touch()

        count = count_yaml_files(tmp_path)
        assert count == 2

    def test_count_yaml_files(self, tmp_path: Path) -> None:
        """Test counting .yaml files."""
        (tmp_path / "model1.yaml").touch()
        (tmp_path / "model2.yaml").touch()

        count = count_yaml_files(tmp_path)
        assert count == 2

    def test_count_mixed_extensions(self, tmp_path: Path) -> None:
        """Test counting both .yml and .yaml files."""
        (tmp_path / "model1.yml").touch()
        (tmp_path / "model2.yaml").touch()
        (tmp_path / "model3.yml").touch()

        count = count_yaml_files(tmp_path)
        assert count == 3

    def test_count_empty_directory(self, tmp_path: Path) -> None:
        """Test counting in empty directory."""
        count = count_yaml_files(tmp_path)
        assert count == 0


class TestEstimateOutputFiles:
    """Tests for estimate_output_files function."""

    def test_estimate_single_input(self) -> None:
        """Test estimation with single input file."""
        views, explores, models = estimate_output_files(1)
        assert views == 1
        assert explores == 1
        assert models == 1

    def test_estimate_multiple_inputs(self) -> None:
        """Test estimation with multiple input files."""
        views, explores, models = estimate_output_files(5)
        assert views == 5
        assert explores == 1
        assert models == 1

    def test_estimate_zero_inputs(self) -> None:
        """Test estimation with zero input files."""
        views, explores, models = estimate_output_files(0)
        assert views == 0
        assert explores == 1
        assert models == 1


class TestFormatCommandParts:
    """Tests for format_command_parts function."""

    def test_minimal_command(self) -> None:
        """Test formatting minimal command with required args only."""
        parts = format_command_parts(
            "dbt-to-lookml generate",
            Path("input/"),
            Path("output/"),
            "public",
        )

        assert "dbt-to-lookml generate" in parts
        assert "-i input/" in " ".join(parts)
        assert "-o output/" in " ".join(parts)
        assert "-s public" in " ".join(parts)

    def test_command_with_prefixes(self) -> None:
        """Test formatting command with view/explore prefixes."""
        parts = format_command_parts(
            "dbt-to-lookml generate",
            Path("input/"),
            Path("output/"),
            "public",
            view_prefix="v_",
            explore_prefix="e_",
        )

        command = " ".join(parts)
        assert "--view-prefix v_" in command
        assert "--explore-prefix e_" in command

    def test_command_with_timezone_flags(self) -> None:
        """Test formatting command with timezone conversion flags."""
        # Test --convert-tz
        parts = format_command_parts(
            "dbt-to-lookml generate",
            Path("input/"),
            Path("output/"),
            "public",
            convert_tz=True,
        )
        assert "--convert-tz" in parts

        # Test --no-convert-tz
        parts = format_command_parts(
            "dbt-to-lookml generate",
            Path("input/"),
            Path("output/"),
            "public",
            convert_tz=False,
        )
        assert "--no-convert-tz" in parts

    def test_command_with_boolean_flags(self) -> None:
        """Test formatting command with boolean flags."""
        parts = format_command_parts(
            "dbt-to-lookml generate",
            Path("input/"),
            Path("output/"),
            "public",
            dry_run=True,
            no_validation=True,
            show_summary=True,
        )

        command = " ".join(parts)
        assert "--dry-run" in command
        assert "--no-validation" in command
        assert "--show-summary" in command


class TestCommandPreview:
    """Tests for CommandPreview class."""

    @pytest.fixture
    def sample_preview_data(self) -> PreviewData:
        """Create sample preview data for testing."""
        return PreviewData(
            input_dir=Path("semantic_models/"),
            output_dir=Path("build/lookml/"),
            schema="production_analytics",
            input_file_count=5,
            estimated_views=5,
            estimated_explores=1,
            estimated_models=1,
            command_parts=[
                "dbt-to-lookml generate",
                "-i semantic_models/",
                "-o build/lookml/",
                "-s production_analytics",
            ],
            additional_config={"View prefix": "stg_"},
        )

    def test_preview_initialization(self) -> None:
        """Test CommandPreview initialization."""
        preview = CommandPreview()
        assert preview.console is not None

    def test_preview_with_custom_console(self) -> None:
        """Test CommandPreview with custom console."""
        console = Console()
        preview = CommandPreview(console=console)
        assert preview.console is console

    def test_render_preview_panel(
        self, sample_preview_data: PreviewData
    ) -> None:
        """Test rendering preview panel."""
        preview = CommandPreview()
        panel = preview.render_preview_panel(sample_preview_data)

        assert panel is not None
        assert "Command Preview" in panel.title

    def test_render_command_syntax(
        self, sample_preview_data: PreviewData
    ) -> None:
        """Test rendering command with syntax highlighting."""
        preview = CommandPreview()
        syntax = preview.render_command_syntax(sample_preview_data.command_parts)

        assert syntax is not None
        assert syntax.lexer_name == "bash"


class TestShowPreviewAndConfirm:
    """Tests for show_preview_and_confirm function."""

    @pytest.fixture
    def sample_preview_data(self) -> PreviewData:
        """Create sample preview data."""
        return PreviewData(
            input_dir=Path("input/"),
            output_dir=Path("output/"),
            schema="public",
            input_file_count=3,
            estimated_views=3,
            estimated_explores=1,
            estimated_models=1,
            command_parts=["dbt-to-lookml generate", "-i input/", "-o output/"],
            additional_config={},
        )

    @patch("dbt_to_lookml.preview.console.input")
    def test_confirm_yes(
        self, mock_input: MagicMock, sample_preview_data: PreviewData
    ) -> None:
        """Test confirmation with 'yes' response."""
        mock_input.return_value = "y"

        result = show_preview_and_confirm(sample_preview_data, auto_confirm=False)
        assert result is True

    @patch("dbt_to_lookml.preview.console.input")
    def test_confirm_no(
        self, mock_input: MagicMock, sample_preview_data: PreviewData
    ) -> None:
        """Test confirmation with 'no' response."""
        mock_input.return_value = "n"

        result = show_preview_and_confirm(sample_preview_data, auto_confirm=False)
        assert result is False

    @patch("dbt_to_lookml.preview.console.input")
    def test_confirm_empty_defaults_to_no(
        self, mock_input: MagicMock, sample_preview_data: PreviewData
    ) -> None:
        """Test that empty response defaults to No for safety."""
        mock_input.return_value = ""

        result = show_preview_and_confirm(sample_preview_data, auto_confirm=False)
        assert result is False

    def test_auto_confirm_bypasses_prompt(
        self, sample_preview_data: PreviewData
    ) -> None:
        """Test that auto_confirm=True bypasses prompt."""
        result = show_preview_and_confirm(sample_preview_data, auto_confirm=True)
        assert result is True
```

**File**: `src/tests/test_cli.py` (modifications)

Add new test cases:

```python
def test_generate_with_preview_flag(
    self, runner: CliRunner, fixtures_dir: Path
) -> None:
    """Test generate command with --preview flag."""
    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)

        result = runner.invoke(
            cli,
            [
                "generate",
                "--input-dir", str(fixtures_dir),
                "--output-dir", str(output_dir),
                "--schema", "public",
                "--preview",
            ],
        )

        assert result.exit_code == 0
        assert "Command Preview" in result.output
        assert "Preview mode - no files will be generated" in result.output

        # Verify no files were created
        view_files = list(output_dir.glob("*.view.lkml"))
        assert len(view_files) == 0

def test_generate_with_yes_flag(
    self, runner: CliRunner, fixtures_dir: Path
) -> None:
    """Test generate command with --yes flag."""
    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)

        result = runner.invoke(
            cli,
            [
                "generate",
                "--input-dir", str(fixtures_dir),
                "--output-dir", str(output_dir),
                "--schema", "public",
                "--yes",
            ],
        )

        assert result.exit_code == 0
        assert "Auto-confirming" in result.output
        assert "✓ LookML generation completed successfully" in result.output

def test_generate_with_confirmation_cancelled(
    self, runner: CliRunner, fixtures_dir: Path
) -> None:
    """Test generate command when user cancels confirmation."""
    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)

        result = runner.invoke(
            cli,
            [
                "generate",
                "--input-dir", str(fixtures_dir),
                "--output-dir", str(output_dir),
                "--schema", "public",
            ],
            input="n\n",  # Simulate user typing 'n' at prompt
        )

        assert result.exit_code == 0
        assert "Command execution cancelled" in result.output

        # Verify no files were created
        view_files = list(output_dir.glob("*.view.lkml"))
        assert len(view_files) == 0
```

### 4. Documentation Updates

**Update CLAUDE.md** (add to Development Commands section):

```markdown
### Preview and Confirmation

# Show preview before generation
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public --preview

# Auto-confirm without prompt (CI/automation)
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public --yes

# Interactive mode with confirmation (default)
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public
```

## Type Checking Considerations

All new code follows strict mypy typing:
- `PreviewData`: Fully typed dataclass with explicit types
- `CommandPreview`: All methods have return type annotations
- Function signatures: All parameters and returns typed
- Rich library types: `Panel`, `Syntax`, `Console` properly imported and typed
- Optional parameters: Use `Type | None` syntax (Python 3.9+ compatible)

## Testing Coverage Goals

- **Unit tests**: 100% coverage of preview module
  - `count_yaml_files()`: 4 test cases (empty, yml, yaml, mixed)
  - `estimate_output_files()`: 3 test cases (zero, single, multiple)
  - `format_command_parts()`: 4 test cases (minimal, prefixes, timezone, flags)
  - `CommandPreview`: 4 test cases (initialization, panel, syntax, custom console)
  - `show_preview_and_confirm()`: 4 test cases (yes, no, empty, auto-confirm)

- **CLI tests**: 3 new test cases
  - `test_generate_with_preview_flag()`: Preview-only mode
  - `test_generate_with_yes_flag()`: Auto-confirm mode
  - `test_generate_with_confirmation_cancelled()`: User cancellation

- **Integration**: Covered by existing end-to-end tests (no changes needed)

**Target coverage**: 95%+ for preview module, maintain 95%+ overall

## Implementation Checklist

- [ ] Create `src/dbt_to_lookml/preview.py` with full implementation
- [ ] Add `PreviewData` dataclass with all required fields
- [ ] Implement `CommandPreview` class with panel rendering
- [ ] Implement utility functions (count, estimate, format)
- [ ] Implement `show_preview_and_confirm()` orchestration
- [ ] Update `__main__.py` with `--yes` and `--preview` flags
- [ ] Add preview integration to `generate` command
- [ ] Create `src/tests/test_preview.py` with 19+ test cases
- [ ] Update `src/tests/test_cli.py` with 3 new test cases
- [ ] Run `make test-fast` to verify all tests pass
- [ ] Run `make type-check` to verify mypy compliance
- [ ] Run `make test-coverage` to verify 95%+ coverage
- [ ] Update CLAUDE.md with preview command examples
- [ ] Manual testing of interactive confirmation flow

## Implementation Order

1. **Create preview module foundation** - 30 min
   - Write `PreviewData` dataclass
   - Implement utility functions (count, estimate, format)

2. **Implement CommandPreview class** - 30 min
   - Panel rendering with Rich
   - Command syntax highlighting
   - Console output methods

3. **Add confirmation logic** - 15 min
   - Implement `show_preview_and_confirm()`
   - Handle auto-confirm and cancellation

4. **Integrate with CLI** - 30 min
   - Add flags to `generate` command
   - Insert preview step before generation
   - Handle preview-only mode

5. **Write comprehensive tests** - 60 min
   - Unit tests for preview module (19 test cases)
   - CLI tests (3 test cases)
   - Edge case coverage

6. **Documentation and validation** - 15 min
   - Update CLAUDE.md
   - Run quality gates
   - Manual testing

**Estimated total**: 3 hours

## Edge Cases and Error Handling

1. **Empty input directory**:
   - Preview shows 0 YAML files
   - Error message before confirmation prompt
   - Prevents unnecessary confirmation for no-op

2. **Non-existent directories**:
   - Click validation handles this (exists=True)
   - No preview-specific handling needed

3. **User interruption (Ctrl-C)**:
   - Rich Console handles gracefully
   - No special handling needed

4. **Preview-only mode with --dry-run**:
   - Both flags can coexist (--preview implies --dry-run)
   - Preview shows but doesn't duplicate dry-run output

5. **Long command strings**:
   - Command parts use line continuation (backslash)
   - Rich Syntax handles word wrapping

6. **Terminal width limitations**:
   - Rich Panel automatically adjusts to terminal width
   - No manual width calculations needed

## Rollout Impact

- **CLI Interface**: Two new flags (`--yes`, `--preview`) - backward compatible
- **User Experience**: Adds confirmation step to interactive usage (breaking for scripts without --yes)
- **Automation**: CI/CD scripts should add `--yes` flag to skip prompts
- **Dependencies**: No new dependencies (Rich already included)
- **Performance**: Negligible (file counting is O(n) for directory listing)
- **Test Suite**: 22 new test cases, no modifications to existing tests

## Future Extensibility

This preview module is designed for reuse:

1. **DTL-018 (Wizard)**: Can import `CommandPreview` to show final command
2. **DTL-017 (Project detection)**: Can pass detected defaults to `PreviewData`
3. **Validate command**: Can add preview showing validation plan
4. **Other commands**: Reusable for any CLI command needing confirmation

## Notes for Implementation

1. **Rich library patterns**: Follow existing patterns from `__main__.py` and `lookml.py`
2. **Console instance reuse**: Preview module creates its own console but accepts custom ones
3. **Dataclass vs dict**: Use dataclass for type safety and IDE support
4. **Command reconstruction**: Build command parts list for easy modification/display
5. **Default to No**: Confirmation prompt defaults to No for safety (explicit confirmation required)
6. **Auto-confirm for automation**: `--yes` flag essential for CI/CD pipelines
7. **Preview-only testing**: `--preview` allows testing command without side effects
8. **Syntax highlighting theme**: "monokai" theme for good contrast in most terminals

## Security Considerations

- **Command display**: Shows exact command that will execute (transparency)
- **No shell injection**: All paths validated by Click before preview
- **Safe defaults**: Confirmation defaults to No (user must explicitly confirm)
- **File counting**: Read-only operation, no file modifications
