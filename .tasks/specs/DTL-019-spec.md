# Implementation Specification: DTL-019 - Add Validation Preview and Confirmation Step

## Metadata
- **Issue**: `DTL-019`
- **Stack**: backend
- **Type**: feature
- **Generated**: 2025-11-17
- **Strategy**: Approved 2025-11-12
- **Estimated Time**: 3 hours

## Issue Context

### Problem Statement
The CLI currently executes generation commands immediately without showing users what will happen. This creates uncertainty and risk, especially for users unfamiliar with the tool or working with large directories. Users need visibility into:
- How many files will be processed
- Where output will be written
- What configuration settings are active
- The exact command that will execute

This implementation adds a rich-formatted preview panel showing all command details before execution, with a confirmation prompt to prevent accidental operations.

### Solution Approach
Create a reusable preview module using the Rich library (already available in dependencies) that:
1. Counts YAML files in the input directory
2. Estimates output files based on conversion patterns
3. Displays a formatted preview panel with all configuration details
4. Shows the complete command with syntax highlighting
5. Prompts for user confirmation (defaults to No for safety)
6. Supports `--yes` flag for automation/CI scenarios
7. Supports `--preview` flag for preview-only mode (no execution)

The module integrates into the existing `generate` command in `__main__.py` and is designed for reuse in the wizard system (DTL-018) and other commands.

### Success Criteria
- [x] Preview shows rich-formatted summary panel with file counts
- [x] Command displayed with bash syntax highlighting
- [x] Confirmation prompt defaults to No for safety
- [x] User can cancel without side effects
- [x] `--yes` flag bypasses confirmation for automation
- [x] `--preview` flag shows preview without execution
- [x] 95%+ test coverage maintained
- [x] All type checks pass (mypy --strict)
- [x] Integration with existing CLI without breaking changes

## Approved Strategy Summary

The implementation creates a standalone `preview.py` module containing:
- **PreviewData**: Dataclass holding structured preview information
- **CommandPreview**: Class for rendering Rich panels and syntax-highlighted commands
- **Utility functions**: File counting, output estimation, command formatting
- **Orchestration function**: `show_preview_and_confirm()` handles the full flow

Key architectural decisions:
- Uses Rich library components (Panel, Syntax, Console) already in dependencies
- Separates data structure (PreviewData) from presentation (CommandPreview)
- Supports both interactive and automated execution modes
- Default to No for safety (explicit user confirmation required)
- Preview-only mode for testing without side effects

## Implementation Plan

### Phase 1: Create Preview Module Foundation (30 minutes)

#### Task 1.1: Create preview.py with PreviewData dataclass

**File**: `src/dbt_to_lookml/preview.py` (new)

**Action**: Create new module with imports and PreviewData structure

**Implementation Guidance**:
```python
"""Preview and confirmation utilities for CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

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
```

**Pattern**: Follow dataclass pattern from `schemas.py` (typed attributes, docstrings)

**Tests**: `test_preview.py::TestPreviewData::test_dataclass_initialization`

#### Task 1.2: Implement utility functions

**File**: `src/dbt_to_lookml/preview.py`

**Action**: Add file counting, output estimation, and command formatting functions

**Implementation Guidance**:
```python
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

    # Optional arguments (only add if non-default)
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
```

**Pattern**: Follow function typing pattern from `types.py` (explicit type hints, detailed docstrings)

**Reference**: `types.py:20-50` for similar utility functions

**Tests**:
- `test_preview.py::TestCountYamlFiles` (4 test cases)
- `test_preview.py::TestEstimateOutputFiles` (3 test cases)
- `test_preview.py::TestFormatCommandParts` (4 test cases)

### Phase 2: Implement CommandPreview Class (30 minutes)

#### Task 2.1: Create CommandPreview class with panel rendering

**File**: `src/dbt_to_lookml/preview.py`

**Action**: Implement class with Rich panel generation methods

**Implementation Guidance**:
```python
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

        content = "\n".join(lines)

        # Create panel
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
```

**Pattern**: Follow Rich usage pattern from `__main__.py:17,140-180` and `generators/lookml.py:250-300`

**Reference**:
- `__main__.py:17` - Console initialization
- `generators/lookml.py:250-300` - Rich Panel/Table usage

**Tests**: `test_preview.py::TestCommandPreview` (4 test cases)

### Phase 3: Add Confirmation Logic (15 minutes)

#### Task 3.1: Implement show_preview_and_confirm function

**File**: `src/dbt_to_lookml/preview.py`

**Action**: Create orchestration function handling preview display and user confirmation

**Implementation Guidance**:
```python
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

**Pattern**: Follow confirmation pattern from Click documentation (user input with default)

**Tests**: `test_preview.py::TestShowPreviewAndConfirm` (4 test cases)

### Phase 4: Integrate with CLI (30 minutes)

#### Task 4.1: Add --yes and --preview flags to generate command

**File**: `src/dbt_to_lookml/__main__.py`

**Action**: Add two new Click options after existing flags (around line 105)

**Implementation Guidance**:
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

**Changes**:
- Insert after `--no-convert-tz` option (line 105)
- Update function signature to accept `yes: bool, preview: bool` parameters

**Pattern**: Follow existing Click option pattern in same file (lines 28-105)

**Reference**: `__main__.py:28-105` - Existing Click options

**Tests**: Updated in CLI tests below

#### Task 4.2: Insert preview logic into generate command

**File**: `src/dbt_to_lookml/__main__.py`

**Action**: Add preview integration after timezone validation (around line 140)

**Implementation Guidance**:
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

**Changes**:
- Insert after line 137 (after timezone validation)
- Before line 140 (before existing "Parsing semantic models" output)
- Remove or consolidate duplicate console output at lines 140-149

**Pattern**: Follow existing CLI flow in `__main__.py:generate()`

**Reference**: `__main__.py:106-200` - Existing generate command structure

**Tests**: `test_cli.py::TestCLI::test_generate_with_*` (3 new test cases)

### Phase 5: Write Comprehensive Tests (60 minutes)

#### Task 5.1: Create test_preview.py with unit tests

**File**: `src/tests/test_preview.py` (new)

**Action**: Create comprehensive test suite for preview module

**Implementation Guidance**:
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
        command = " ".join(parts)
        assert "-i input" in command
        assert "-o output" in command
        assert "-s public" in command

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

**Pattern**: Follow pytest patterns from existing test files

**Reference**:
- `src/tests/test_cli.py:13-100` - Test class structure and fixtures
- `src/tests/unit/test_dbt_parser.py` - Unit test patterns

**Estimated lines**: ~250

#### Task 5.2: Add CLI integration tests

**File**: `src/tests/test_cli.py`

**Action**: Add three new test methods to TestCLI class

**Implementation Guidance**:
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

**Changes**: Insert after existing test methods (around line 200)

**Pattern**: Follow existing CLI test pattern in same file

**Reference**: `test_cli.py:60-91` - Existing generate tests with TemporaryDirectory

**Estimated lines**: ~60

### Phase 6: Documentation and Validation (15 minutes)

#### Task 6.1: Update CLAUDE.md with preview examples

**File**: `CLAUDE.md`

**Action**: Add Preview and Confirmation section to Development Commands

**Implementation Guidance**:
Insert after line 71 (after "LookML Generation" section):

```markdown
### Preview and Confirmation

```bash
# Show preview before generation
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public --preview

# Auto-confirm without prompt (CI/automation)
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public --yes

# Interactive mode with confirmation (default)
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public
```
```

**Changes**: Insert new section with 3 example commands

**Pattern**: Follow existing command example format in CLAUDE.md

**Reference**: `CLAUDE.md:46-71` - Existing command examples

**Estimated lines**: ~10

#### Task 6.2: Run validation commands

**Action**: Execute quality gates to verify implementation

**Validation Commands**:
```bash
# Type checking
make type-check

# Linting
make lint

# Unit tests
make test-fast

# Coverage check
make test-coverage

# Full test suite
make test-full
```

**Success Criteria**:
- mypy passes with 0 errors
- ruff passes with 0 violations
- All tests pass (25+ tests with new additions)
- Coverage remains at 95%+

## Detailed Task Breakdown

### File Changes Summary

#### Files to Create

##### `src/dbt_to_lookml/preview.py`
**Purpose**: Reusable preview and confirmation module

**Structure**:
- Imports (pathlib, typing, Rich components)
- `PreviewData` dataclass (9 fields with type hints)
- `CommandPreview` class (3 methods for rendering)
- `count_yaml_files()` function
- `estimate_output_files()` function
- `format_command_parts()` function
- `show_preview_and_confirm()` orchestration function

**Estimated lines**: ~200

##### `src/tests/test_preview.py`
**Purpose**: Comprehensive unit tests for preview module

**Test Classes**:
- `TestCountYamlFiles` (4 test cases)
- `TestEstimateOutputFiles` (3 test cases)
- `TestFormatCommandParts` (4 test cases)
- `TestCommandPreview` (4 test cases)
- `TestShowPreviewAndConfirm` (4 test cases)

**Estimated lines**: ~250

#### Files to Modify

##### `src/dbt_to_lookml/__main__.py`
**Changes**:
1. Add two new Click options (lines 106-115)
2. Update `generate()` function signature (line 106)
3. Insert preview logic block (60 lines after line 137)
4. Consolidate duplicate console output (remove lines 140-149)

**Estimated additions**: ~75 lines
**Estimated deletions**: ~10 lines

##### `src/tests/test_cli.py`
**Changes**:
1. Add `test_generate_with_preview_flag()` method
2. Add `test_generate_with_yes_flag()` method
3. Add `test_generate_with_confirmation_cancelled()` method

**Estimated additions**: ~60 lines

##### `CLAUDE.md`
**Changes**:
1. Add "Preview and Confirmation" section with 3 example commands

**Estimated additions**: ~10 lines

## Testing Strategy

### Unit Tests (test_preview.py)

#### TestCountYamlFiles
1. **test_count_yml_files**: Create directory with .yml files, verify count
2. **test_count_yaml_files**: Create directory with .yaml files, verify count
3. **test_count_mixed_extensions**: Mix of .yml and .yaml files
4. **test_count_empty_directory**: Empty directory returns 0

#### TestEstimateOutputFiles
1. **test_estimate_single_input**: 1 input → (1, 1, 1)
2. **test_estimate_multiple_inputs**: 5 inputs → (5, 1, 1)
3. **test_estimate_zero_inputs**: 0 inputs → (0, 1, 1)

#### TestFormatCommandParts
1. **test_minimal_command**: Required args only
2. **test_command_with_prefixes**: View/explore prefixes added
3. **test_command_with_timezone_flags**: --convert-tz and --no-convert-tz
4. **test_command_with_boolean_flags**: Multiple boolean flags

#### TestCommandPreview
1. **test_preview_initialization**: Default console created
2. **test_preview_with_custom_console**: Custom console accepted
3. **test_render_preview_panel**: Panel contains expected content
4. **test_render_command_syntax**: Syntax object has bash lexer

#### TestShowPreviewAndConfirm
1. **test_confirm_yes**: User types 'y', returns True
2. **test_confirm_no**: User types 'n', returns False
3. **test_confirm_empty_defaults_to_no**: Empty input returns False
4. **test_auto_confirm_bypasses_prompt**: auto_confirm=True returns True

### CLI Integration Tests (test_cli.py)

1. **test_generate_with_preview_flag**:
   - Run with --preview
   - Verify preview shown
   - Verify no files created
   - Exit code 0

2. **test_generate_with_yes_flag**:
   - Run with --yes
   - Verify auto-confirmation message
   - Verify generation completes
   - Files created

3. **test_generate_with_confirmation_cancelled**:
   - Run without --yes
   - Simulate user typing 'n'
   - Verify cancellation message
   - No files created

### Edge Cases

1. **Empty input directory**:
   - Preview shows 0 files
   - Error before confirmation
   - No unnecessary prompts

2. **Preview + dry-run flags**:
   - Both flags coexist
   - Preview takes precedence
   - No duplicate messages

3. **Long command strings**:
   - Command parts wrapped with backslash
   - Rich Syntax handles wrapping
   - Terminal width respected

4. **User interruption (Ctrl-C)**:
   - Rich Console handles gracefully
   - No special handling needed

## Validation Commands

### Type Checking
```bash
cd /Users/dug/Work/repos/dbt-to-lookml
make type-check
# Expected: 0 errors
```

### Linting
```bash
make lint
# Expected: 0 violations
```

### Unit Tests
```bash
make test-fast
# Expected: All unit tests pass
```

### Coverage
```bash
make test-coverage
# Expected: 95%+ coverage maintained
```

### Full Test Suite
```bash
make test-full
# Expected: All test suites pass
```

### Manual Testing
```bash
# Test preview mode
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public --preview

# Test interactive confirmation (type 'n')
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public

# Test auto-confirm
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public --yes
```

## Dependencies

### Existing Dependencies Used
- **Rich** (already in dependencies): Panel, Syntax, Console components
- **Click** (already in dependencies): Flag options, command structure
- **pathlib** (stdlib): Path handling
- **typing** (stdlib): Type hints
- **pytest** (dev dependency): Testing framework
- **unittest.mock** (stdlib): Mocking for tests

### New Dependencies Needed
**None** - All required libraries already in project dependencies

## Implementation Notes

### Type Checking Considerations
- All functions have explicit return type annotations
- Use `Type | None` syntax (Python 3.9+ compatible, not 3.10+ `Type | None`)
- Rich library types properly imported (`Panel`, `Syntax`, `Console`)
- Dataclass fields fully typed
- Optional parameters use `= None` with `Type | None` annotation

### Code Patterns to Follow
1. **Rich formatting**: Use markup tags like `[bold cyan]`, `[green]`
2. **Console reuse**: Accept optional Console parameter in constructors
3. **Dataclass pattern**: Follow `schemas.py` dataclass style
4. **Function typing**: All params and returns explicitly typed
5. **Docstrings**: Google-style with Args/Returns sections
6. **Default values**: Safe defaults (confirmation defaults to No)

### Important Considerations
1. **Safety first**: Confirmation defaults to No (explicit user action required)
2. **Automation support**: `--yes` flag essential for CI/CD
3. **Preview testing**: `--preview` allows dry-run without confirmation
4. **Command accuracy**: Reconstructed command must match actual execution
5. **File counting**: Read-only operation, no modifications
6. **Rich theming**: "monokai" theme for syntax highlighting (good contrast)
7. **Terminal compatibility**: Rich automatically adjusts to terminal width

## Implementation Checklist

### Phase 1: Preview Module Foundation
- [ ] Create `src/dbt_to_lookml/preview.py`
- [ ] Add module docstring and imports
- [ ] Implement `PreviewData` dataclass with all 9 fields
- [ ] Implement `count_yaml_files()` function
- [ ] Implement `estimate_output_files()` function
- [ ] Implement `format_command_parts()` function
- [ ] Verify mypy passes for preview module

### Phase 2: CommandPreview Class
- [ ] Implement `CommandPreview.__init__()`
- [ ] Implement `CommandPreview.render_preview_panel()`
- [ ] Implement `CommandPreview.render_command_syntax()`
- [ ] Implement `CommandPreview.show()`
- [ ] Verify Rich formatting works as expected

### Phase 3: Confirmation Logic
- [ ] Implement `show_preview_and_confirm()` function
- [ ] Test auto-confirm behavior
- [ ] Test user input handling
- [ ] Verify default-to-No safety

### Phase 4: CLI Integration
- [ ] Add `--yes` flag to generate command
- [ ] Add `--preview` flag to generate command
- [ ] Update generate function signature
- [ ] Insert preview logic after timezone validation
- [ ] Handle preview-only mode
- [ ] Handle auto-confirm mode
- [ ] Handle user cancellation
- [ ] Remove duplicate console output

### Phase 5: Testing
- [ ] Create `src/tests/test_preview.py`
- [ ] Implement TestCountYamlFiles (4 tests)
- [ ] Implement TestEstimateOutputFiles (3 tests)
- [ ] Implement TestFormatCommandParts (4 tests)
- [ ] Implement TestCommandPreview (4 tests)
- [ ] Implement TestShowPreviewAndConfirm (4 tests)
- [ ] Add 3 CLI integration tests to test_cli.py
- [ ] Run `make test-fast` - all tests pass
- [ ] Run `make test-coverage` - 95%+ coverage

### Phase 6: Validation
- [ ] Run `make type-check` - 0 errors
- [ ] Run `make lint` - 0 violations
- [ ] Run `make test-full` - all suites pass
- [ ] Update CLAUDE.md with preview examples
- [ ] Manual test: --preview flag
- [ ] Manual test: --yes flag
- [ ] Manual test: interactive cancellation

## Implementation Order

1. **Phase 1: Preview Module Foundation** (30 min)
   - Write PreviewData dataclass
   - Implement utility functions
   - Run mypy verification

2. **Phase 2: CommandPreview Class** (30 min)
   - Implement panel rendering
   - Implement syntax highlighting
   - Test Rich output manually

3. **Phase 3: Confirmation Logic** (15 min)
   - Implement orchestration function
   - Test auto-confirm and cancellation

4. **Phase 4: CLI Integration** (30 min)
   - Add flags to generate command
   - Insert preview step
   - Handle all execution modes

5. **Phase 5: Comprehensive Testing** (60 min)
   - Write 19 unit tests
   - Write 3 CLI integration tests
   - Verify coverage

6. **Phase 6: Documentation and Validation** (15 min)
   - Update CLAUDE.md
   - Run quality gates
   - Manual testing

**Total Estimated Time**: 3 hours

## Rollout Impact

### Breaking Changes
**None** - All changes are backward compatible:
- New flags are optional
- Default behavior adds confirmation (but can be skipped with --yes)
- Existing CLI commands continue to work

### Migration Guide for Automation
CI/CD scripts should add `--yes` flag to skip interactive prompts:

```bash
# Before
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public

# After (for automation)
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public --yes
```

### User Experience Changes
- **Interactive mode**: Now shows preview and requires confirmation
- **Preview testing**: Can use `--preview` to see what would happen
- **Automation**: Use `--yes` to skip confirmation
- **Cancellation**: Can safely abort with 'n' or Ctrl-C

### Performance Impact
**Negligible**:
- File counting: O(n) directory scan (fast)
- Preview rendering: Instant with Rich
- User confirmation: Waits for input (interactive only)

## Future Extensibility

This preview module is designed for reuse:

1. **DTL-018 (Wizard)**: Can import `CommandPreview` to show final configuration
2. **DTL-017 (Project detection)**: Can pass detected defaults to `PreviewData`
3. **Validate command**: Can add preview showing validation plan
4. **Other commands**: Reusable for any CLI command needing confirmation

### Extension Points

- **PreviewData**: Easily extended with new fields
- **CommandPreview**: Can add custom panel renderers
- **format_command_parts**: Can support new CLI flags
- **show_preview_and_confirm**: Can add custom confirmation prompts

## Success Metrics

### Test Coverage
- Target: 95%+ overall coverage (maintained)
- New module: 100% coverage (19 unit tests)
- CLI integration: 3 new test cases

### Code Quality
- mypy --strict: 0 errors
- ruff: 0 violations
- All existing tests: Pass
- All new tests: Pass

### User Experience
- Clear preview panel with file counts
- Accurate command reconstruction
- Safe defaults (No for confirmation)
- Support for automation (--yes)
- Preview-only mode (--preview)

## Ready for Implementation

This specification is complete and ready for implementation. All design decisions are documented, code patterns are referenced, and test cases are defined. The implementation can proceed systematically through the 6 phases with clear validation at each step.
