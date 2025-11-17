# Implementation Strategy: DTL-016

**Issue**: DTL-016 - Enhance help text with rich examples and formatting
**Analyzed**: 2025-11-17T12:00:00Z
**Stack**: backend
**Type**: feature

## Approach

Enhance the CLI help text with rich formatting, syntax-highlighted examples, and structured information displays. This issue focuses on:

1. Creating a custom Click help formatter that integrates Rich panels, tables, and syntax highlighting
2. Adding comprehensive usage examples with syntax highlighting for bash commands
3. Restructuring help text to use Rich panels for better visual organization
4. Building an options table that clearly distinguishes required vs optional flags
5. Standardizing error message formatting across the CLI using Rich components

This builds upon the wizard infrastructure (DTL-015) and sets the foundation for interactive wizards (DTL-018+) by establishing consistent, visually appealing CLI patterns.

## Architecture Impact

**Layer**: CLI Presentation (enhances DTL-015 foundation)

**New Module Structure**:
```
src/dbt_to_lookml/
├── cli/                       # NEW package for CLI utilities
│   ├── __init__.py           # Public exports
│   ├── help_formatter.py     # Custom Rich-based Click help formatter
│   └── formatting.py         # Reusable formatting utilities (panels, tables, syntax)
```

**Modified Files**:
- `src/dbt_to_lookml/__main__.py`: Enhanced help text, better error formatting
- All existing commands updated to use Rich panels and examples

**New Test Files**:
- `src/tests/unit/test_cli_formatting.py`: Unit tests for formatting utilities
- `src/tests/test_cli_help.py`: CLI tests for help text output

## Dependencies

- **Depends on**: DTL-015 (wizard infrastructure provides foundation)
- **Blocking**:
  - DTL-018: Build simple prompt-based wizard (uses formatting patterns)
  - DTL-019: Add validation preview (uses formatting utilities)
  - DTL-020: Implement TUI wizard mode (inherits formatting patterns)

- **Related to**:
  - DTL-014 (parent epic for CLI wizard enhancements)
  - DTL-017 (contextual detection will use same formatting patterns)

## Detailed Implementation Plan

### 1. Create CLI Utilities Package

#### Module: src/dbt_to_lookml/cli/__init__.py

**Purpose**: Public API for CLI formatting utilities

**Implementation**:
```python
"""CLI utilities for dbt-to-lookml.

This module provides Rich-based formatting utilities for the CLI,
including help text formatters, syntax highlighting, and structured displays.
"""

from dbt_to_lookml.cli.formatting import (
    create_example_panel,
    create_options_table,
    format_error,
    format_success,
    format_warning,
    syntax_highlight_bash,
)
from dbt_to_lookml.cli.help_formatter import RichHelpFormatter

__all__ = [
    "RichHelpFormatter",
    "create_example_panel",
    "create_options_table",
    "format_error",
    "format_success",
    "format_warning",
    "syntax_highlight_bash",
]
```

**Design rationale**:
- Clean public API for CLI components
- Separate concerns: help formatting vs general formatting utilities
- All exports are reusable across wizard and command modules

#### Module: src/dbt_to_lookml/cli/formatting.py

**Purpose**: Reusable Rich formatting utilities for CLI output

**Implementation**:
```python
"""Rich formatting utilities for CLI output."""

from typing import Sequence

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


def syntax_highlight_bash(code: str, line_numbers: bool = False) -> Syntax:
    """Create syntax-highlighted bash code block.

    Args:
        code: Bash command(s) to highlight.
        line_numbers: Whether to show line numbers.

    Returns:
        Rich Syntax object for rendering.
    """
    return Syntax(
        code,
        "bash",
        theme="monokai",
        line_numbers=line_numbers,
        word_wrap=False,
        background_color="default",
    )


def create_example_panel(
    title: str,
    examples: Sequence[tuple[str, str]],
    width: int = 78,
) -> Panel:
    """Create a Rich panel containing code examples.

    Args:
        title: Panel title.
        examples: List of (description, code) tuples.
        width: Panel width in characters (default 78 for 80-col terminals).

    Returns:
        Rich Panel with syntax-highlighted examples.
    """
    from rich.console import Group
    from rich.text import Text

    content_items = []
    for i, (description, code) in enumerate(examples):
        if i > 0:
            content_items.append(Text())  # Blank line between examples

        # Description
        content_items.append(Text(description, style="bold cyan"))

        # Code with syntax highlighting
        content_items.append(syntax_highlight_bash(code))

    group = Group(*content_items)
    return Panel(
        group,
        title=f"[bold]{title}[/bold]",
        title_align="left",
        border_style="blue",
        width=width,
        padding=(1, 2),
    )


def create_options_table(
    options: Sequence[tuple[str, str, str, bool]],
) -> Table:
    """Create a Rich table showing command options.

    Args:
        options: List of (name, short_flag, description, required) tuples.

    Returns:
        Rich Table with formatted options.
    """
    table = Table(
        title="Options",
        title_style="bold",
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
        width=78,
    )

    table.add_column("Option", style="green", width=20)
    table.add_column("Flag", style="yellow", width=8)
    table.add_column("Description", width=38)
    table.add_column("Required", width=8, justify="center")

    for name, short_flag, description, required in options:
        required_marker = "[red]Yes[/red]" if required else "[dim]No[/dim]"
        table.add_row(name, short_flag, description, required_marker)

    return table


def format_error(message: str, context: str | None = None) -> Panel:
    """Format an error message with Rich panel.

    Args:
        message: Error message.
        context: Optional context/hint for resolving the error.

    Returns:
        Rich Panel with error formatting.
    """
    from rich.text import Text

    content = Text(message, style="bold red")

    if context:
        content.append("\n\n")
        content.append(Text(f"💡 {context}", style="yellow"))

    return Panel(
        content,
        title="[bold red]Error[/bold red]",
        title_align="left",
        border_style="red",
        padding=(1, 2),
    )


def format_warning(message: str, context: str | None = None) -> Panel:
    """Format a warning message with Rich panel.

    Args:
        message: Warning message.
        context: Optional context/additional information.

    Returns:
        Rich Panel with warning formatting.
    """
    from rich.text import Text

    content = Text(f"⚠ {message}", style="bold yellow")

    if context:
        content.append("\n\n")
        content.append(Text(context, style="dim"))

    return Panel(
        content,
        title="[bold yellow]Warning[/bold yellow]",
        title_align="left",
        border_style="yellow",
        padding=(1, 2),
    )


def format_success(message: str, details: str | None = None) -> Panel:
    """Format a success message with Rich panel.

    Args:
        message: Success message.
        details: Optional additional details.

    Returns:
        Rich Panel with success formatting.
    """
    from rich.text import Text

    content = Text(f"✓ {message}", style="bold green")

    if details:
        content.append("\n\n")
        content.append(Text(details, style="dim"))

    return Panel(
        content,
        title="[bold green]Success[/bold green]",
        title_align="left",
        border_style="green",
        padding=(1, 2),
    )
```

**Design patterns**:
- Factory functions for creating Rich components (panels, tables, syntax)
- Consistent color scheme: blue (info), green (success), yellow (warning), red (error)
- 78-character width by default (fits 80-column terminals with margin)
- All functions return Rich renderables (can be composed)
- Type hints use `Sequence` for immutable inputs, `str | None` for optional strings

**Type checking compliance**:
- All parameters and return types explicitly typed
- Uses `Sequence[tuple[...]]` for structured data
- No `Any` types

#### Module: src/dbt_to_lookml/cli/help_formatter.py

**Purpose**: Custom Click help formatter using Rich

**Implementation**:
```python
"""Custom Click help formatter using Rich for enhanced output."""

import click
from click.formatting import HelpFormatter
from rich.console import Console

from dbt_to_lookml.cli.formatting import (
    create_example_panel,
    create_options_table,
)

console = Console()


class RichHelpFormatter(HelpFormatter):
    """Custom Click help formatter that uses Rich for output.

    This formatter enhances Click's default help text with:
    - Syntax-highlighted code examples
    - Structured panels for examples sections
    - Tables for options with clear required/optional distinction
    - Consistent Rich styling throughout

    Usage:
        @click.command(cls=RichCommand)
        def my_command():
            ...

    Where RichCommand uses this formatter via context settings.
    """

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Initialize the Rich help formatter."""
        super().__init__(*args, **kwargs)
        self.examples: list[tuple[str, str]] = []
        self.options_data: list[tuple[str, str, str, bool]] = []

    def add_examples(
        self,
        examples: list[tuple[str, str]],
    ) -> None:
        """Add examples section to help text.

        Args:
            examples: List of (description, code) tuples.
        """
        self.examples = examples

    def add_options_table(
        self,
        options: list[tuple[str, str, str, bool]],
    ) -> None:
        """Add options table to help text.

        Args:
            options: List of (name, short_flag, description, required) tuples.
        """
        self.options_data = options

    def getvalue(self) -> str:
        """Get the formatted help text.

        Returns:
            Formatted help text string.
        """
        # Get base help text from Click
        base_help = super().getvalue()

        # Render Rich components to string
        if self.examples or self.options_data:
            from io import StringIO

            from rich.console import Console as RichConsole

            buffer = StringIO()
            rich_console = RichConsole(file=buffer, width=78, force_terminal=False)

            # Render base help first
            rich_console.print(base_help)

            # Render examples panel if present
            if self.examples:
                rich_console.print("\n")
                panel = create_example_panel("Common Usage Patterns", self.examples)
                rich_console.print(panel)

            # Render options table if present
            if self.options_data:
                rich_console.print("\n")
                table = create_options_table(self.options_data)
                rich_console.print(table)

            return buffer.getvalue()

        return base_help


class RichCommand(click.Command):
    """Click command class that uses Rich help formatter.

    This command class automatically uses RichHelpFormatter for help text
    and provides helper methods for adding examples and options tables.

    Usage:
        @click.command(cls=RichCommand)
        @click.option("--input-dir", "-i", required=True)
        def my_command(input_dir):
            '''Command description.'''
            pass

        # Add examples and options via command.params inspection
    """

    def format_help(self, ctx: click.Context, formatter: HelpFormatter) -> None:
        """Format help text using Rich formatter.

        Args:
            ctx: Click context.
            formatter: Help formatter instance.
        """
        # Use custom formatter if available
        if isinstance(formatter, RichHelpFormatter):
            # Auto-populate options table from command parameters
            options_data = []
            for param in self.get_params(ctx):
                if isinstance(param, click.Option):
                    name = f"--{param.name.replace('_', '-')}"
                    short_flag = ""
                    if param.secondary_opts:
                        short_flag = param.secondary_opts[0]

                    description = param.help or ""
                    required = param.required

                    options_data.append((name, short_flag, description, required))

            if options_data:
                formatter.add_options_table(options_data)

        # Call parent to format standard sections
        super().format_help(ctx, formatter)


def get_rich_context_settings() -> dict[str, type[RichHelpFormatter]]:
    """Get Click context settings for Rich help formatting.

    Returns:
        Dictionary of context settings to pass to click.command().
    """
    return {"formatter_class": RichHelpFormatter}
```

**Design patterns**:
- Extends Click's `HelpFormatter` for compatibility
- Custom `RichCommand` class automatically populates options table
- Factory function `get_rich_context_settings()` for easy usage
- Renders Rich components to string (Click expects string help text)
- Maintains Click's standard help structure, enhances with Rich components

**Type checking compliance**:
- Type hints on all public methods
- Uses `click.Context` and `click.Command` types
- Return types explicit (`str`, `dict[str, type[RichHelpFormatter]]`)

### 2. Enhance Generate Command Help Text

#### Changes to src/dbt_to_lookml/__main__.py

**Location**: Lines 28-121 (generate command)

**Change 1**: Import formatting utilities (after line 7)

```python
from rich.console import Console

from dbt_to_lookml.cli.formatting import (
    create_example_panel,
    format_error,
    format_success,
    format_warning,
)
from dbt_to_lookml.cli.help_formatter import RichCommand
```

**Change 2**: Update generate command decorator (line 28)

**Current**:
```python
@cli.command()
```

**New**:
```python
@cli.command(cls=RichCommand)
```

**Change 3**: Enhance docstring with examples (lines 121-122)

**Current**:
```python
def generate(...) -> None:
    """Generate LookML views and explores from semantic models."""
```

**New**:
```python
def generate(...) -> None:
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
```

**Change 4**: Replace error messages with formatted panels (multiple locations)

**Example - Lines 124-128 (dependency error)**:

**Current**:
```python
if not GENERATOR_AVAILABLE:
    console.print(
        "[bold red]Error: LookML generator dependencies not available[/bold red]"
    )
    console.print("Please install required dependencies: pip install lkml")
    raise click.ClickException("Missing dependencies for LookML generation")
```

**New**:
```python
if not GENERATOR_AVAILABLE:
    error_panel = format_error(
        "LookML generator dependencies not available",
        context="Install with: pip install lkml",
    )
    console.print(error_panel)
    raise click.ClickException("Missing dependencies for LookML generation")
```

**Example - Lines 132-138 (mutual exclusivity error)**:

**Current**:
```python
if convert_tz and no_convert_tz:
    console.print(
        "[bold red]Error: --convert-tz and --no-convert-tz are "
        "mutually exclusive[/bold red]"
    )
    raise click.ClickException(
        "--convert-tz and --no-convert-tz cannot be used together"
    )
```

**New**:
```python
if convert_tz and no_convert_tz:
    error_panel = format_error(
        "Conflicting timezone options provided",
        context="Use either --convert-tz OR --no-convert-tz, not both",
    )
    console.print(error_panel)
    raise click.ClickException(
        "--convert-tz and --no-convert-tz cannot be used together"
    )
```

**Example - Lines 188-191 (no models found)**:

**Current**:
```python
if len(semantic_models) == 0:
    console.print(
        "[bold red]No semantic models found or all files failed to parse[/bold red]"
    )
    raise click.ClickException("No valid semantic models to generate from")
```

**New**:
```python
if len(semantic_models) == 0:
    error_panel = format_error(
        "No semantic models found or all files failed to parse",
        context=f"Check that {input_dir} contains valid semantic model YAML files",
    )
    console.print(error_panel)
    raise click.ClickException("No valid semantic models to generate from")
```

**Example - Lines 240-242 (success message)**:

**Current**:
```python
if not dry_run:
    console.print(
        "[bold green]✓ LookML generation completed successfully[/bold green]"
    )
```

**New**:
```python
if not dry_run:
    success_panel = format_success(
        "LookML generation completed successfully",
        details=f"Generated {len(generated_files)} files in {output_dir}",
    )
    console.print(success_panel)
```

**Example - Lines 197-200 (warning message)**:

**Current**:
```python
if error_count > 0:
    console.print(
        f"[yellow]Warning: {error_count} files had parse errors and were skipped[/yellow]"
    )
```

**New**:
```python
if error_count > 0:
    warning_panel = format_warning(
        f"{error_count} files had parse errors and were skipped",
        context="Generation continued with successfully parsed models",
    )
    console.print(warning_panel)
```

**Rationale**:
- Consistent visual presentation across all messages
- Better context and hints for resolving issues
- Panels draw attention to important messages
- Examples in docstring provide immediate guidance
- `RichCommand` auto-generates options table from Click parameters

### 3. Enhance Validate Command Help Text

#### Changes to src/dbt_to_lookml/__main__.py

**Location**: Lines 281-396 (validate command)

**Change 1**: Update validate command decorator (line 281)

**Current**:
```python
@cli.command()
```

**New**:
```python
@cli.command(cls=RichCommand)
```

**Change 2**: Enhance docstring (lines 300-301)

**Current**:
```python
def validate(input_dir: Path, strict: bool, verbose: bool) -> None:
    """Validate semantic model files."""
```

**New**:
```python
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
```

**Change 3**: Apply consistent error/success formatting

Similar pattern to generate command - replace inline `console.print()` calls
with `format_error()`, `format_warning()`, `format_success()` panel functions.

### 4. Add Examples to Main CLI Group

#### Changes to src/dbt_to_lookml/__main__.py

**Location**: Lines 21-25 (main CLI group)

**Enhancement**: Add examples to main help text

**Current**:
```python
@click.group()
@click.version_option()
def cli() -> None:
    """Convert dbt semantic models to LookML views and explores."""
    pass
```

**New**:
```python
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
```

**Rationale**:
- Immediate examples in top-level help guide new users
- Common workflows demonstrate best practices
- Quick start section provides fast path to success
- Mentions wizard for discoverability

### 5. Testing Strategy

#### Unit Tests: src/tests/unit/test_cli_formatting.py

**Purpose**: Test formatting utilities in isolation

**Test cases**:

```python
"""Unit tests for CLI formatting utilities."""

import pytest
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from dbt_to_lookml.cli.formatting import (
    create_example_panel,
    create_options_table,
    format_error,
    format_success,
    format_warning,
    syntax_highlight_bash,
)


class TestSyntaxHighlighting:
    """Test suite for syntax highlighting functions."""

    def test_syntax_highlight_bash_basic(self) -> None:
        """Test basic bash syntax highlighting."""
        code = "echo 'hello world'"
        result = syntax_highlight_bash(code)

        assert isinstance(result, Syntax)
        assert result.lexer_name == "bash"
        assert code in result.code

    def test_syntax_highlight_bash_with_line_numbers(self) -> None:
        """Test bash syntax highlighting with line numbers."""
        code = "echo 'hello'\necho 'world'"
        result = syntax_highlight_bash(code, line_numbers=True)

        assert isinstance(result, Syntax)
        assert result.line_numbers is True

    def test_syntax_highlight_bash_multiline(self) -> None:
        """Test bash syntax highlighting with multiline code."""
        code = """dbt-to-lookml generate \\
  -i semantic_models/ \\
  -o lookml/ \\
  -s prod_schema"""
        result = syntax_highlight_bash(code)

        assert isinstance(result, Syntax)
        assert "dbt-to-lookml" in result.code


class TestExamplePanel:
    """Test suite for example panel creation."""

    def test_create_example_panel_single_example(self) -> None:
        """Test creating panel with single example."""
        examples = [
            ("Basic usage", "dbt-to-lookml generate -i models/ -o lookml/ -s prod"),
        ]
        panel = create_example_panel("Examples", examples)

        assert isinstance(panel, Panel)
        assert panel.title == "[bold]Examples[/bold]"

    def test_create_example_panel_multiple_examples(self) -> None:
        """Test creating panel with multiple examples."""
        examples = [
            ("Basic", "command 1"),
            ("Advanced", "command 2"),
            ("Expert", "command 3"),
        ]
        panel = create_example_panel("Usage Patterns", examples)

        assert isinstance(panel, Panel)
        assert panel.title == "[bold]Usage Patterns[/bold]"

    def test_create_example_panel_custom_width(self) -> None:
        """Test creating panel with custom width."""
        examples = [("Test", "echo test")]
        panel = create_example_panel("Test", examples, width=100)

        assert panel.width == 100


class TestOptionsTable:
    """Test suite for options table creation."""

    def test_create_options_table_basic(self) -> None:
        """Test creating basic options table."""
        options = [
            ("--input-dir", "-i", "Input directory", True),
            ("--output-dir", "-o", "Output directory", True),
            ("--dry-run", "", "Preview mode", False),
        ]
        table = create_options_table(options)

        assert isinstance(table, Table)
        assert table.title == "Options"
        assert len(table.columns) == 4

    def test_create_options_table_required_flags(self) -> None:
        """Test options table distinguishes required flags."""
        options = [
            ("--required", "-r", "Required option", True),
            ("--optional", "-o", "Optional option", False),
        ]
        table = create_options_table(options)

        assert isinstance(table, Table)
        # Table should visually distinguish required from optional
        # (verified through manual inspection of rendered output)

    def test_create_options_table_empty(self) -> None:
        """Test creating options table with no options."""
        options: list[tuple[str, str, str, bool]] = []
        table = create_options_table(options)

        assert isinstance(table, Table)
        assert len(table.rows) == 0


class TestMessageFormatting:
    """Test suite for error/warning/success message formatting."""

    def test_format_error_basic(self) -> None:
        """Test basic error formatting."""
        panel = format_error("Something went wrong")

        assert isinstance(panel, Panel)
        assert "Error" in str(panel.title)

    def test_format_error_with_context(self) -> None:
        """Test error formatting with context."""
        panel = format_error(
            "File not found",
            context="Check that the path exists and is readable",
        )

        assert isinstance(panel, Panel)
        # Panel should contain both message and context
        # (verified through rendered output)

    def test_format_warning_basic(self) -> None:
        """Test basic warning formatting."""
        panel = format_warning("This might be an issue")

        assert isinstance(panel, Panel)
        assert "Warning" in str(panel.title)

    def test_format_warning_with_context(self) -> None:
        """Test warning formatting with context."""
        panel = format_warning(
            "Deprecated option used",
            context="Use --new-option instead",
        )

        assert isinstance(panel, Panel)

    def test_format_success_basic(self) -> None:
        """Test basic success formatting."""
        panel = format_success("Operation completed")

        assert isinstance(panel, Panel)
        assert "Success" in str(panel.title)

    def test_format_success_with_details(self) -> None:
        """Test success formatting with details."""
        panel = format_success(
            "Files generated",
            details="Created 10 view files and 1 explore file",
        )

        assert isinstance(panel, Panel)


class TestFormattingEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_code_highlighting(self) -> None:
        """Test syntax highlighting with empty code."""
        result = syntax_highlight_bash("")
        assert isinstance(result, Syntax)
        assert result.code == ""

    def test_long_code_highlighting(self) -> None:
        """Test syntax highlighting with very long code."""
        code = "echo " + "x" * 1000
        result = syntax_highlight_bash(code)
        assert isinstance(result, Syntax)
        assert len(result.code) == len(code)

    def test_special_characters_in_messages(self) -> None:
        """Test formatting handles special characters."""
        panel = format_error("Path: /path/to/[special]/chars")
        assert isinstance(panel, Panel)

    def test_unicode_in_messages(self) -> None:
        """Test formatting handles unicode characters."""
        panel = format_success("✓ Unicode: 你好世界 🎉")
        assert isinstance(panel, Panel)
```

**Coverage requirements**:
- Target: 100% coverage of all formatting functions
- Test all parameters and variations
- Test edge cases (empty inputs, special characters, unicode)

#### CLI Tests: src/tests/test_cli_help.py

**Purpose**: Test help text output and formatting

**Test cases**:

```python
"""CLI tests for help text formatting."""

from click.testing import CliRunner

from dbt_to_lookml.__main__ import cli


class TestCLIHelp:
    """Test suite for CLI help text."""

    def test_main_help_shows_commands(self) -> None:
        """Test main help text shows available commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "generate" in result.output
        assert "validate" in result.output
        assert "wizard" in result.output

    def test_main_help_shows_examples(self) -> None:
        """Test main help text includes examples."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Quick Start" in result.output or "Examples" in result.output
        assert "dbt-to-lookml" in result.output

    def test_generate_help_shows_examples(self) -> None:
        """Test generate command help includes usage examples."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--help"])

        assert result.exit_code == 0
        assert "Examples" in result.output or "example" in result.output.lower()
        assert "semantic_models" in result.output

    def test_generate_help_shows_options(self) -> None:
        """Test generate command help shows all options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--help"])

        assert result.exit_code == 0
        assert "--input-dir" in result.output
        assert "--output-dir" in result.output
        assert "--schema" in result.output
        assert "--view-prefix" in result.output
        assert "--dry-run" in result.output
        assert "--convert-tz" in result.output

    def test_generate_help_shows_required_flags(self) -> None:
        """Test generate help distinguishes required flags."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--help"])

        assert result.exit_code == 0
        # Required flags should be marked in the help text
        assert "required" in result.output.lower()

    def test_validate_help_shows_examples(self) -> None:
        """Test validate command help includes examples."""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--help"])

        assert result.exit_code == 0
        assert "Examples" in result.output or "example" in result.output.lower()

    def test_validate_help_shows_options(self) -> None:
        """Test validate command help shows options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--help"])

        assert result.exit_code == 0
        assert "--input-dir" in result.output
        assert "--strict" in result.output
        assert "--verbose" in result.output

    def test_help_text_fits_80_columns(self) -> None:
        """Test help text fits within 80 columns."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--help"])

        assert result.exit_code == 0
        lines = result.output.split("\n")
        # Most lines should fit in 80 columns (allow some overflow for borders)
        long_lines = [line for line in lines if len(line) > 82]
        assert len(long_lines) < len(lines) * 0.1  # Less than 10% overflow


class TestErrorFormatting:
    """Test suite for error message formatting."""

    def test_missing_required_option_formatted(self) -> None:
        """Test missing required option shows formatted error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate"])

        assert result.exit_code != 0
        # Should show error about missing required options
        assert "Error" in result.output or "Missing" in result.output

    def test_invalid_path_formatted(self) -> None:
        """Test invalid path shows formatted error."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "generate",
                "-i",
                "/nonexistent/path",
                "-o",
                "/tmp/output",
                "-s",
                "schema",
            ],
        )

        assert result.exit_code != 0
        # Should show path error
        assert "Error" in result.output or "does not exist" in result.output


class TestSuccessFormatting:
    """Test suite for success message formatting."""

    def test_validation_success_formatted(self, tmp_path) -> None:
        """Test successful validation shows formatted success message."""
        # Create a minimal valid semantic model file
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        model_file = models_dir / "test_model.yml"
        model_file.write_text(
            """
semantic_models:
  - name: test_model
    model: ref('test')
    entities:
      - name: id
        type: primary
    dimensions:
      - name: name
        type: categorical
    measures:
      - name: count
        agg: count
"""
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "-i", str(models_dir)])

        assert result.exit_code == 0
        # Should show success formatting
        assert "✓" in result.output or "Success" in result.output
```

**Coverage requirements**:
- All commands tested for help output
- Error formatting verified through CLI tests
- Success/warning formatting verified
- 80-column constraint checked

#### Integration with Existing Test Suite

**Markers**: Already added in DTL-015 (wizard marker)

**Test organization**:
```bash
# Run CLI help tests
pytest src/tests/test_cli_help.py -v

# Run formatting unit tests
pytest src/tests/unit/test_cli_formatting.py -v

# Run all CLI-related tests
pytest -m cli -v
```

### 6. Type Safety and Mypy Compliance

#### Type Checking Strategy

**All CLI module files must pass `mypy --strict`**:

```bash
# Check CLI package
mypy src/dbt_to_lookml/cli/ --strict

# Check __main__ with new imports
mypy src/dbt_to_lookml/__main__.py --strict

# Full codebase check
make type-check
```

**Type hints checklist**:
- [ ] All function signatures have parameter types
- [ ] All function signatures have return types
- [ ] Rich component types properly imported (`Panel`, `Table`, `Syntax`)
- [ ] Sequence types used for immutable inputs
- [ ] Optional types use `str | None` syntax (Python 3.10+) or `Optional[str]` (3.9)
- [ ] No implicit `Any` types

**Common patterns**:
```python
# Good: Explicit types for Rich components
def create_panel(message: str) -> Panel:
    return Panel(message)

# Good: Sequence for immutable lists
def format_examples(examples: Sequence[tuple[str, str]]) -> Panel:
    ...

# Good: Optional with union syntax
def format_error(msg: str, context: str | None = None) -> Panel:
    ...

# Avoid: Missing return type
def bad_function(msg: str):  # Missing return type
    return Panel(msg)
```

## Implementation Checklist

- [ ] Create `src/dbt_to_lookml/cli/__init__.py` with public exports
- [ ] Create `src/dbt_to_lookml/cli/formatting.py` with formatting utilities
- [ ] Create `src/dbt_to_lookml/cli/help_formatter.py` with Rich help formatter
- [ ] Update `src/dbt_to_lookml/__main__.py` imports
- [ ] Add `RichCommand` to generate command decorator
- [ ] Enhance generate command docstring with examples
- [ ] Replace generate command error messages with formatted panels
- [ ] Replace generate command success messages with formatted panels
- [ ] Add `RichCommand` to validate command decorator
- [ ] Enhance validate command docstring with examples
- [ ] Replace validate command messages with formatted panels
- [ ] Enhance main CLI group docstring with examples
- [ ] Create `src/tests/unit/test_cli_formatting.py` with unit tests
- [ ] Create `src/tests/test_cli_help.py` with CLI tests
- [ ] Run `make type-check` to verify mypy compliance
- [ ] Run `make test-fast` to verify unit tests pass
- [ ] Run `make test-full` to verify no regressions
- [ ] Test help text: `dbt-to-lookml --help`
- [ ] Test generate help: `dbt-to-lookml generate --help`
- [ ] Test validate help: `dbt-to-lookml validate --help`
- [ ] Verify 80-column formatting in terminal

## Implementation Order

1. **Create formatting utilities** - 45 min
   - Create `cli/formatting.py`
   - Implement syntax highlighting, panels, tables
   - Implement error/warning/success formatters

2. **Create help formatter** - 30 min
   - Create `cli/help_formatter.py`
   - Implement `RichHelpFormatter` class
   - Implement `RichCommand` class

3. **Create module exports** - 5 min
   - Create `cli/__init__.py`
   - Export all public functions and classes

4. **Enhance generate command** - 30 min
   - Update command decorator
   - Enhance docstring with examples
   - Replace error/success messages with panels

5. **Enhance validate command** - 20 min
   - Update command decorator
   - Enhance docstring with examples
   - Replace messages with panels

6. **Enhance main CLI group** - 15 min
   - Add examples to main docstring
   - Add quick start guide
   - Add common workflows

7. **Write formatting unit tests** - 60 min
   - Create `test_cli_formatting.py`
   - Test all formatting functions
   - Test edge cases

8. **Write CLI help tests** - 45 min
   - Create `test_cli_help.py`
   - Test help output for all commands
   - Test error/success formatting

9. **Verify type safety** - 15 min
   - Run `make type-check`
   - Fix any mypy errors
   - Verify strict mode compliance

10. **Run test suite and manual verification** - 30 min
    - Run `make test-fast`
    - Run `make test-full`
    - Manually test all help commands
    - Verify 80-column constraint
    - Test error/success messages

**Estimated total**: 4.5 hours

## Rollout Impact

### User-Facing Changes

- **Enhanced help text**: All commands show rich-formatted help with examples
- **Better error messages**: Errors displayed in panels with context
- **Success/warning messages**: Consistently formatted with panels
- **Examples in help**: Every command includes usage examples
- **Options table**: Clear distinction between required and optional flags

### Developer-Facing Changes

- **New package**: `dbt_to_lookml.cli` with formatting utilities
- **Import changes**: `from dbt_to_lookml.cli import format_error, ...`
- **Reusable components**: Panels, tables, syntax highlighting available
- **RichCommand**: Custom Click command class for enhanced help

### Backward Compatibility

- **Fully backward compatible**: All existing commands work unchanged
- **No breaking changes**: Only visual/formatting enhancements
- **Optional features**: RichCommand is opt-in per command

### Performance Impact

- **CLI startup**: Minimal impact (Rich already dependency)
- **Help rendering**: Slightly slower due to Rich formatting (<50ms)
- **Memory**: Negligible (Rich objects short-lived)

## Notes for Implementation

1. **Color scheme consistency**:
   - Blue: Informational messages, panels, borders
   - Green: Success messages, checkmarks
   - Yellow: Warnings, hints
   - Red: Errors, failures
   - Cyan: Emphasis, headers

2. **80-column constraint**:
   - Default panel/table width: 78 chars (2-char margin for 80-col terminals)
   - Long code examples: Use backslash continuation
   - Test on actual 80-column terminal

3. **Rich component patterns**:
   ```python
   # Panel for important messages
   panel = Panel(content, title="Title", border_style="blue")

   # Table for structured data
   table = Table(title="Title", show_header=True)
   table.add_column("Name", style="green")
   table.add_row("value")

   # Syntax for code examples
   syntax = Syntax(code, "bash", theme="monokai")
   ```

4. **Click integration patterns**:
   ```python
   # Use RichCommand for enhanced help
   @click.command(cls=RichCommand)
   def my_command():
       '''Docstring becomes help text with examples.'''
       pass

   # Access formatter in custom commands
   def format_help(self, ctx, formatter):
       if isinstance(formatter, RichHelpFormatter):
           formatter.add_examples([...])
   ```

5. **Testing philosophy**:
   - Unit tests: Test formatting functions in isolation
   - CLI tests: Test help text rendering via Click
   - Integration: Verify error/success formatting in real commands
   - Visual: Manual verification in terminal for aesthetics

6. **Error message best practices**:
   - Primary message: What went wrong
   - Context: How to fix it or what to try
   - Examples: Show correct usage if relevant

## Success Metrics

- [ ] `dbt-to-lookml --help` shows rich-formatted help with examples
- [ ] `dbt-to-lookml generate --help` shows examples and options table
- [ ] `dbt-to-lookml validate --help` shows examples and options table
- [ ] Error messages use panels with context
- [ ] Success messages use panels with details
- [ ] Warning messages use panels with context
- [ ] All help text fits in 80 columns (with 2-char margin)
- [ ] `make type-check` passes with no mypy errors
- [ ] `make test-fast` passes all tests
- [ ] `make test-full` passes with no regressions
- [ ] Unit test coverage for CLI formatting at 100%
- [ ] CLI test coverage for help commands at 100%
- [ ] Examples include: basic usage, prefixes, dry-run, timezone conversion

## Pre-Implementation Checklist

Before starting DTL-016 implementation:

- [ ] DTL-015 completed (wizard infrastructure in place)
- [ ] Review existing Rich usage in `__main__.py`
- [ ] Check Click documentation for custom help formatters
- [ ] Confirm Rich version supports Panel, Table, Syntax (should be OK)
- [ ] Review project's color scheme preferences
- [ ] Set up 80-column terminal for testing
- [ ] Test existing help text: `dbt-to-lookml --help`

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-016.md`
3. Change status from `refinement` to `awaiting-strategy-review`, then to `strategy-approved`
4. Run: `/implement:1-spec DTL-016`
