# Implementation Spec: DTL-016 - Enhance Help Text with Rich Examples and Formatting

## Metadata
- **Issue**: `DTL-016`
- **Stack**: backend
- **Type**: feature
- **Generated**: 2025-11-17T12:00:00Z
- **Strategy**: Approved 2025-11-17
- **Parent**: DTL-014 (CLI Wizard Enhancements)

## Issue Context

### Problem Statement

The current CLI help text for dbt-to-lookml is functional but lacks visual appeal and clear examples. Users need rich-formatted help text with syntax-highlighted examples, structured information displays, and clear usage patterns to understand available options and common workflows.

### Solution Approach

Create a new `cli` package with Rich-based formatting utilities and a custom Click help formatter. Enhance the generate and validate commands with comprehensive examples, options tables, and formatted error/success messages. This provides users with:

1. Visual hierarchy through Rich panels and tables
2. Syntax-highlighted code examples for common patterns
3. Clear distinction between required and optional flags
4. Context-rich error messages with hints for resolution
5. Consistent formatting across all CLI output

### Success Criteria

- `dbt-to-lookml generate --help` shows rich-formatted output
- Examples section includes: basic usage, with prefixes, dry-run, timezone conversion
- Options table clearly shows required vs optional flags
- Help text fits in standard 80-column terminal
- Error messages use Rich formatting consistently
- All tests passing with 95%+ branch coverage

## Approved Strategy Summary

The approved strategy creates a modular CLI utilities package with three core components:

1. **formatting.py**: Reusable Rich formatting utilities (panels, tables, syntax highlighting)
2. **help_formatter.py**: Custom Click help formatter that integrates Rich components
3. Enhanced command help text in **__main__.py** with comprehensive examples

This architecture allows:
- Consistent visual presentation across all CLI commands
- Reusable formatting utilities for future features (wizards, TUI)
- Type-safe implementation compliant with mypy --strict
- Backward compatibility (purely visual enhancements)

## Implementation Plan

### Phase 1: Create CLI Utilities Package (80 minutes)

Create the foundational CLI module with formatting utilities and custom help formatter.

#### Task 1.1: Create `src/dbt_to_lookml/cli/__init__.py`

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
from dbt_to_lookml.cli.help_formatter import RichCommand, RichHelpFormatter

__all__ = [
    "RichCommand",
    "RichHelpFormatter",
    "create_example_panel",
    "create_options_table",
    "format_error",
    "format_success",
    "format_warning",
    "syntax_highlight_bash",
]
```

**Lines**: ~25 lines
**Time**: 5 minutes

#### Task 1.2: Create `src/dbt_to_lookml/cli/formatting.py`

**Purpose**: Reusable Rich formatting utilities for CLI output

**Key Functions**:

1. **`syntax_highlight_bash(code: str, line_numbers: bool = False) -> Syntax`**
   - Creates syntax-highlighted bash code blocks
   - Uses Monokai theme with default background
   - Optional line numbers for multiline examples

2. **`create_example_panel(title: str, examples: Sequence[tuple[str, str]], width: int = 78) -> Panel`**
   - Creates Rich panel containing code examples
   - Each example is a (description, code) tuple
   - Description in bold cyan, code syntax-highlighted
   - Blank lines between examples for readability

3. **`create_options_table(options: Sequence[tuple[str, str, str, bool]]) -> Table`**
   - Creates table showing command options
   - Columns: Option name, Short flag, Description, Required
   - Required flags marked in red, optional in dim gray
   - 78-character width for 80-column terminals

4. **`format_error(message: str, context: str | None = None) -> Panel`**
   - Red-bordered panel with error icon
   - Optional context provides hints for resolution
   - Consistent red color scheme for errors

5. **`format_warning(message: str, context: str | None = None) -> Panel`**
   - Yellow-bordered panel with warning icon
   - Optional context for additional information
   - Consistent yellow color scheme for warnings

6. **`format_success(message: str, details: str | None = None) -> Panel`**
   - Green-bordered panel with checkmark
   - Optional details for success context
   - Consistent green color scheme for success

**Reference Implementation**: See strategy lines 100-284

**Lines**: ~180 lines
**Time**: 45 minutes

**Type Safety Requirements**:
- All functions have explicit type hints
- Uses `Sequence[tuple[...]]` for immutable inputs
- Returns Rich renderables (Panel, Table, Syntax)
- No implicit `Any` types

**Testing Notes**:
- Each function tested in isolation (unit tests)
- Edge cases: empty inputs, special characters, unicode
- Visual verification in terminal for aesthetics

#### Task 1.3: Create `src/dbt_to_lookml/cli/help_formatter.py`

**Purpose**: Custom Click help formatter using Rich

**Key Classes**:

1. **`RichHelpFormatter(HelpFormatter)`**
   - Extends Click's HelpFormatter for compatibility
   - Stores examples and options data during formatting
   - Renders Rich components to string in `getvalue()`
   - Methods:
     - `add_examples(examples: list[tuple[str, str]]) -> None`
     - `add_options_table(options: list[tuple[str, str, str, bool]]) -> None`
     - `getvalue() -> str` (override)

2. **`RichCommand(click.Command)`**
   - Custom Click command class using RichHelpFormatter
   - Auto-populates options table from Click parameters
   - Inspects `self.get_params(ctx)` to extract option metadata
   - Usage: `@click.command(cls=RichCommand)`

**Reference Implementation**: See strategy lines 303-454

**Lines**: ~150 lines
**Time**: 30 minutes

**Type Safety Requirements**:
- Type hints on all methods
- Uses `click.Context` and `click.Command` types
- Return types explicit for all methods

**Design Pattern**:
```python
# Usage in command definition
@click.command(cls=RichCommand)
@click.option("--input-dir", "-i", required=True, help="...")
def my_command(input_dir: Path) -> None:
    """Command description with examples in docstring."""
    pass
```

### Phase 2: Enhance Generate Command (50 minutes)

Update the generate command with rich help text, examples, and formatted messages.

#### Task 2.1: Add Imports to `__main__.py`

**Location**: After line 7 (after existing imports)

**Add**:
```python
from dbt_to_lookml.cli.formatting import (
    format_error,
    format_success,
    format_warning,
)
from dbt_to_lookml.cli.help_formatter import RichCommand
```

**Time**: 2 minutes

#### Task 2.2: Update Generate Command Decorator

**Location**: Line 28 (generate command)

**Change**:
```python
# Before
@cli.command()

# After
@cli.command(cls=RichCommand)
```

**Time**: 1 minute

#### Task 2.3: Enhance Generate Command Docstring

**Location**: Lines 121-122 (generate function)

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

**Lines**: Add ~20 lines to docstring
**Time**: 10 minutes

**Examples Included**:
1. Basic generation (minimal required flags)
2. With prefixes and dry-run (demonstrates optional flags)
3. With timezone conversion (demonstrates DTL-008 feature)
4. With custom connection/model (demonstrates all options)
5. Reference to wizard mode (demonstrates discoverability)

#### Task 2.4: Replace Error Messages with Formatted Panels

Replace inline `console.print()` error messages with `format_error()` panels.

**Location 1**: Lines 123-128 (dependency error)

**Before**:
```python
if not GENERATOR_AVAILABLE:
    console.print(
        "[bold red]Error: LookML generator dependencies not available[/bold red]"
    )
    console.print("Please install required dependencies: pip install lkml")
    raise click.ClickException("Missing dependencies for LookML generation")
```

**After**:
```python
if not GENERATOR_AVAILABLE:
    error_panel = format_error(
        "LookML generator dependencies not available",
        context="Install with: pip install lkml",
    )
    console.print(error_panel)
    raise click.ClickException("Missing dependencies for LookML generation")
```

**Location 2**: Lines 131-138 (mutual exclusivity error)

**Before**:
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

**After**:
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

**Additional Locations**: Search for all `console.print()` calls with `[bold red]` and replace with `format_error()` panels.

**Time**: 15 minutes

#### Task 2.5: Replace Success/Warning Messages

Replace inline success and warning messages with formatted panels.

**Success Messages**:
- Locate `console.print()` calls with `[bold green]` or `✓`
- Replace with `format_success()` panels
- Add details parameter for context

**Warning Messages**:
- Locate `console.print()` calls with `[yellow]`
- Replace with `format_warning()` panels
- Add context parameter for additional information

**Example - Success**:
```python
# Before
console.print("[bold green]✓ LookML generation completed successfully[/bold green]")

# After
success_panel = format_success(
    "LookML generation completed successfully",
    details=f"Generated {len(generated_files)} files in {output_dir}",
)
console.print(success_panel)
```

**Time**: 12 minutes

#### Task 2.6: Manual Verification

Test the enhanced generate command:

```bash
# Test help text
dbt-to-lookml generate --help

# Test error formatting
dbt-to-lookml generate  # Missing required args

# Test success formatting (dry-run)
dbt-to-lookml generate -i semantic_models/ -o /tmp/test -s test --dry-run
```

**Time**: 10 minutes

### Phase 3: Enhance Validate Command (35 minutes)

Apply similar enhancements to the validate command.

#### Task 3.1: Update Validate Command Decorator

**Location**: Line 281 (validate command in `__main__.py`)

**Change**:
```python
# Before
@cli.command()

# After
@cli.command(cls=RichCommand)
```

**Time**: 1 minute

#### Task 3.2: Enhance Validate Command Docstring

**Location**: Lines 300-301 (validate function)

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

**Lines**: Add ~18 lines to docstring
**Time**: 8 minutes

#### Task 3.3: Replace Validate Command Messages

Apply same formatting pattern as generate command:
- Replace error messages with `format_error()` panels
- Replace success messages with `format_success()` panels
- Replace warning messages with `format_warning()` panels

**Time**: 15 minutes

#### Task 3.4: Manual Verification

Test the enhanced validate command:

```bash
# Test help text
dbt-to-lookml validate --help

# Test error formatting
dbt-to-lookml validate -i /nonexistent

# Test success formatting
dbt-to-lookml validate -i semantic_models/
```

**Time**: 11 minutes

### Phase 4: Enhance Main CLI Group (15 minutes)

Add comprehensive help text to the main CLI group.

#### Task 4.1: Enhance Main CLI Docstring

**Location**: Lines 21-25 (cli group in `__main__.py`)

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

**Lines**: Add ~32 lines to docstring
**Time**: 10 minutes

#### Task 4.2: Verify Main Help

```bash
dbt-to-lookml --help
```

**Time**: 5 minutes

### Phase 5: Testing Strategy (105 minutes)

Comprehensive test coverage for CLI formatting utilities and help text.

#### Task 5.1: Create Unit Tests - `src/tests/unit/test_cli_formatting.py`

**Purpose**: Test formatting utilities in isolation

**Test Classes**:

1. **`TestSyntaxHighlighting`** (4 tests)
   - `test_syntax_highlight_bash_basic`: Basic bash highlighting
   - `test_syntax_highlight_bash_with_line_numbers`: Line numbers enabled
   - `test_syntax_highlight_bash_multiline`: Multiline code with backslashes
   - `test_empty_code_highlighting`: Edge case - empty string

2. **`TestExamplePanel`** (3 tests)
   - `test_create_example_panel_single_example`: Single example
   - `test_create_example_panel_multiple_examples`: Multiple examples with blank lines
   - `test_create_example_panel_custom_width`: Custom width parameter

3. **`TestOptionsTable`** (3 tests)
   - `test_create_options_table_basic`: Basic table with multiple options
   - `test_create_options_table_required_flags`: Visual distinction of required flags
   - `test_create_options_table_empty`: Empty options list

4. **`TestMessageFormatting`** (6 tests)
   - `test_format_error_basic`: Error without context
   - `test_format_error_with_context`: Error with context hint
   - `test_format_warning_basic`: Warning without context
   - `test_format_warning_with_context`: Warning with context
   - `test_format_success_basic`: Success without details
   - `test_format_success_with_details`: Success with details

5. **`TestFormattingEdgeCases`** (4 tests)
   - `test_empty_code_highlighting`: Empty code string
   - `test_long_code_highlighting`: Very long code (1000+ chars)
   - `test_special_characters_in_messages`: Brackets, slashes in messages
   - `test_unicode_in_messages`: Unicode and emojis

**Reference Implementation**: See strategy lines 787-986

**Lines**: ~200 lines
**Time**: 60 minutes

**Assertions**:
- Type checks: `isinstance(result, Panel)`, `isinstance(result, Syntax)`
- Content checks: Verify title, styles, dimensions
- Edge case handling: Empty inputs, special characters, unicode

**Coverage Target**: 100% of formatting.py functions

#### Task 5.2: Create CLI Tests - `src/tests/test_cli_help.py`

**Purpose**: Test help text output and formatting via Click

**Test Classes**:

1. **`TestCLIHelp`** (8 tests)
   - `test_main_help_shows_commands`: Main help lists all commands
   - `test_main_help_shows_examples`: Main help includes examples
   - `test_generate_help_shows_examples`: Generate help has examples section
   - `test_generate_help_shows_options`: Generate help lists all options
   - `test_generate_help_shows_required_flags`: Required flags marked
   - `test_validate_help_shows_examples`: Validate help has examples
   - `test_validate_help_shows_options`: Validate help lists options
   - `test_help_text_fits_80_columns`: Help fits 80-column terminal

2. **`TestErrorFormatting`** (2 tests)
   - `test_missing_required_option_formatted`: Missing arg shows formatted error
   - `test_invalid_path_formatted`: Invalid path shows formatted error

3. **`TestSuccessFormatting`** (1 test)
   - `test_validation_success_formatted`: Success message formatted correctly

**Reference Implementation**: See strategy lines 999-1156

**Lines**: ~160 lines
**Time**: 45 minutes

**Assertions**:
- Help text content: `assert "Examples" in result.output`
- Option presence: `assert "--input-dir" in result.output`
- Column constraint: Check lines longer than 82 chars (less than 10%)
- Exit codes: `assert result.exit_code == 0` for success

**Coverage Target**: All commands tested for help output and error formatting

### Phase 6: Type Safety and Quality Gates (30 minutes)

Verify mypy compliance and test coverage.

#### Task 6.1: Run Type Checking

```bash
# Check CLI package
mypy src/dbt_to_lookml/cli/ --strict

# Check __main__ with new imports
mypy src/dbt_to_lookml/__main__.py --strict

# Full codebase check
make type-check
```

**Fix any mypy errors**:
- Missing return types
- Implicit Any types
- Incorrect type annotations

**Time**: 15 minutes

#### Task 6.2: Run Test Suite

```bash
# Run new unit tests
pytest src/tests/unit/test_cli_formatting.py -v

# Run new CLI tests
pytest src/tests/test_cli_help.py -v

# Run full test suite
make test-fast
make test-full

# Check coverage
make test-coverage
```

**Time**: 10 minutes

#### Task 6.3: Quality Gate

```bash
make quality-gate
```

Must pass:
- Lint (ruff)
- Type check (mypy)
- Tests (pytest)

**Time**: 5 minutes

## Detailed Task Breakdown

### Files to Create

#### 1. `src/dbt_to_lookml/cli/__init__.py`
**Why**: Public API for CLI utilities module

**Structure**:
```python
"""CLI utilities module."""
# Imports from submodules
# __all__ exports
```

**Estimated lines**: ~25 lines

#### 2. `src/dbt_to_lookml/cli/formatting.py`
**Why**: Reusable Rich formatting utilities

**Structure**:
- Module docstring
- Imports (Rich components)
- `console = Console()` singleton
- Formatting functions (syntax, panels, tables, messages)

**Functions**:
1. `syntax_highlight_bash()` - 15 lines
2. `create_example_panel()` - 30 lines
3. `create_options_table()` - 35 lines
4. `format_error()` - 25 lines
5. `format_warning()` - 25 lines
6. `format_success()` - 25 lines

**Estimated lines**: ~180 lines

**Reference**: Similar implementation at `src/dbt_to_lookml/__main__.py` (console usage)

#### 3. `src/dbt_to_lookml/cli/help_formatter.py`
**Why**: Custom Click help formatter with Rich integration

**Structure**:
- Module docstring
- Imports (Click, Rich)
- `RichHelpFormatter` class
- `RichCommand` class

**Classes**:
1. `RichHelpFormatter(HelpFormatter)` - 60 lines
   - `__init__()`
   - `add_examples()`
   - `add_options_table()`
   - `getvalue()` (override)

2. `RichCommand(click.Command)` - 40 lines
   - `format_help()` (override)

**Estimated lines**: ~150 lines

**Reference**: Click's `HelpFormatter` class, Rich's `Console` rendering

#### 4. `src/tests/unit/test_cli_formatting.py`
**Why**: Unit tests for formatting utilities

**Structure**:
- Module docstring
- Imports (pytest, Rich types, formatting functions)
- Test classes (one per function group)
- Test methods (one per scenario)

**Test Classes**:
1. `TestSyntaxHighlighting` - 40 lines
2. `TestExamplePanel` - 35 lines
3. `TestOptionsTable` - 35 lines
4. `TestMessageFormatting` - 60 lines
5. `TestFormattingEdgeCases` - 30 lines

**Estimated lines**: ~200 lines

**Reference**: Similar test structure at `src/tests/unit/test_dbt_parser.py`

#### 5. `src/tests/test_cli_help.py`
**Why**: CLI tests for help text and formatting

**Structure**:
- Module docstring
- Imports (CliRunner, cli)
- Test classes (by functional area)
- Test methods with assertions

**Test Classes**:
1. `TestCLIHelp` - 90 lines
2. `TestErrorFormatting` - 35 lines
3. `TestSuccessFormatting` - 35 lines

**Estimated lines**: ~160 lines

**Reference**: Similar test structure at `src/tests/test_cli.py`

### Files to Modify

#### 1. `src/dbt_to_lookml/__main__.py`
**Why**: Enhance help text and use formatting utilities

**Changes**:
1. **Line 7**: Add imports for formatting utilities and RichCommand
   - Add 6 lines

2. **Line 28**: Update generate command decorator to use RichCommand
   - Change 1 line: `@cli.command()` → `@cli.command(cls=RichCommand)`

3. **Lines 121-122**: Enhance generate command docstring
   - Add ~20 lines of examples

4. **Lines 123-128, 131-138, etc.**: Replace error messages with formatted panels
   - Modify ~10 locations, change ~30 lines

5. **Line 281**: Update validate command decorator to use RichCommand
   - Change 1 line

6. **Lines 300-301**: Enhance validate command docstring
   - Add ~18 lines of examples

7. **Validate command messages**: Replace with formatted panels
   - Modify ~5 locations, change ~15 lines

8. **Lines 21-25**: Enhance main CLI group docstring
   - Add ~32 lines

**Estimated changes**: ~120 lines added/modified

## Validation Commands

### Type Checking
```bash
# Check CLI package
mypy src/dbt_to_lookml/cli/ --strict

# Check main module
mypy src/dbt_to_lookml/__main__.py --strict

# Full codebase
make type-check
```

### Testing
```bash
# Unit tests for formatting
pytest src/tests/unit/test_cli_formatting.py -v

# CLI help tests
pytest src/tests/test_cli_help.py -v

# All CLI-related tests
pytest -m cli -v

# Fast unit tests
make test-fast

# Full test suite
make test-full

# Coverage report
make test-coverage
```

### Manual Verification
```bash
# Test main help
dbt-to-lookml --help

# Test generate help
dbt-to-lookml generate --help

# Test validate help
dbt-to-lookml validate --help

# Test error formatting (missing args)
dbt-to-lookml generate

# Test error formatting (invalid path)
dbt-to-lookml validate -i /nonexistent

# Test success formatting (dry-run)
dbt-to-lookml generate -i semantic_models/ -o /tmp/test -s test --dry-run

# Test validation success
dbt-to-lookml validate -i semantic_models/
```

### Quality Gate
```bash
# Run all quality checks
make quality-gate

# Individual checks
make lint
make format
make type-check
make test-fast
```

## Dependencies

### Existing Dependencies
- **rich**: Already a dependency, used for console output
  - Version: Latest stable (check pyproject.toml)
  - Components used: Console, Panel, Table, Syntax, Group, Text

- **click**: Already a dependency, used for CLI
  - Version: Latest stable (check pyproject.toml)
  - Extensions: Custom command class, help formatter

### New Dependencies Needed
None - all required dependencies already in pyproject.toml

## Implementation Notes

### Important Considerations

1. **80-Column Constraint**
   - Default panel/table width: 78 characters (2-char margin)
   - Test on actual 80-column terminal
   - Allow slight overflow for borders (up to 82 chars)

2. **Color Scheme Consistency**
   - Blue: Informational, borders, headers
   - Green: Success messages
   - Yellow: Warnings
   - Red: Errors
   - Cyan: Emphasis, headers

3. **Rich Component Patterns**
   - Always use `Panel` for important messages
   - Use `Table` for structured data (options)
   - Use `Syntax` for code examples
   - Use `Group` to combine multiple renderables

4. **Click Integration**
   - `RichCommand` auto-populates options table from params
   - Docstrings become help text (Click convention)
   - Examples in docstring render as-is (preserve formatting)

5. **Type Safety**
   - All functions must have explicit type hints
   - Use `Sequence[tuple[...]]` for immutable lists
   - Use `str | None` for optional strings (Python 3.10+)
   - No implicit `Any` types allowed

6. **Backward Compatibility**
   - All existing commands work unchanged
   - Only visual/formatting enhancements
   - No breaking changes to CLI API

### Code Patterns to Follow

#### Pattern 1: Creating Formatted Messages
```python
# Error with context
error_panel = format_error(
    "Primary error message",
    context="Hint: How to fix this issue",
)
console.print(error_panel)

# Success with details
success_panel = format_success(
    "Operation completed",
    details=f"Processed {count} items",
)
console.print(success_panel)
```

#### Pattern 2: Creating Example Panels
```python
examples = [
    ("Basic usage", "command --flag value"),
    ("Advanced usage", "command --flag1 value1 --flag2 value2"),
]
panel = create_example_panel("Examples", examples, width=78)
console.print(panel)
```

#### Pattern 3: Using RichCommand
```python
@click.command(cls=RichCommand)
@click.option("--input-dir", "-i", required=True, help="Input directory")
def my_command(input_dir: Path) -> None:
    """Command description.

    Examples:

      Basic usage:
      $ my-command --input-dir /path/to/input
    """
    pass
```

#### Pattern 4: Type Hints for Rich Components
```python
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

def create_panel(message: str) -> Panel:
    """Create panel with message."""
    return Panel(message)

def create_table(data: Sequence[tuple[str, str]]) -> Table:
    """Create table from data."""
    table = Table()
    # ...
    return table
```

### References

**Similar Implementations in Codebase**:
- `src/dbt_to_lookml/__main__.py`: Console usage patterns (lines 18, 140+)
- `src/tests/test_cli.py`: CLI test patterns (lines 1-100)
- `src/tests/unit/test_dbt_parser.py`: Unit test patterns (lines 1-50)

**External References**:
- Rich documentation: https://rich.readthedocs.io/
- Click documentation: https://click.palletsprojects.com/
- Pydantic for schemas: Used in existing codebase

## Implementation Checklist

### Phase 1: Create CLI Utilities Package
- [ ] Create `src/dbt_to_lookml/cli/__init__.py`
- [ ] Create `src/dbt_to_lookml/cli/formatting.py`
  - [ ] Implement `syntax_highlight_bash()`
  - [ ] Implement `create_example_panel()`
  - [ ] Implement `create_options_table()`
  - [ ] Implement `format_error()`
  - [ ] Implement `format_warning()`
  - [ ] Implement `format_success()`
- [ ] Create `src/dbt_to_lookml/cli/help_formatter.py`
  - [ ] Implement `RichHelpFormatter` class
  - [ ] Implement `RichCommand` class

### Phase 2: Enhance Generate Command
- [ ] Add formatting imports to `__main__.py`
- [ ] Update generate command decorator to use `RichCommand`
- [ ] Enhance generate command docstring with examples
- [ ] Replace generate error messages with formatted panels
- [ ] Replace generate success messages with formatted panels
- [ ] Replace generate warning messages with formatted panels
- [ ] Manual test: `dbt-to-lookml generate --help`

### Phase 3: Enhance Validate Command
- [ ] Update validate command decorator to use `RichCommand`
- [ ] Enhance validate command docstring with examples
- [ ] Replace validate error messages with formatted panels
- [ ] Replace validate success messages with formatted panels
- [ ] Replace validate warning messages with formatted panels
- [ ] Manual test: `dbt-to-lookml validate --help`

### Phase 4: Enhance Main CLI Group
- [ ] Enhance main CLI group docstring with examples
- [ ] Add quick start section
- [ ] Add common workflows section
- [ ] Manual test: `dbt-to-lookml --help`

### Phase 5: Testing
- [ ] Create `src/tests/unit/test_cli_formatting.py`
  - [ ] Test syntax highlighting functions
  - [ ] Test example panel creation
  - [ ] Test options table creation
  - [ ] Test message formatting (error/warning/success)
  - [ ] Test edge cases
- [ ] Create `src/tests/test_cli_help.py`
  - [ ] Test main help output
  - [ ] Test generate help output
  - [ ] Test validate help output
  - [ ] Test error formatting in CLI
  - [ ] Test success formatting in CLI
  - [ ] Test 80-column constraint

### Phase 6: Quality Gates
- [ ] Run `mypy src/dbt_to_lookml/cli/ --strict`
- [ ] Run `mypy src/dbt_to_lookml/__main__.py --strict`
- [ ] Run `make type-check`
- [ ] Run `pytest src/tests/unit/test_cli_formatting.py -v`
- [ ] Run `pytest src/tests/test_cli_help.py -v`
- [ ] Run `make test-fast`
- [ ] Run `make test-full`
- [ ] Run `make test-coverage` (verify 95%+ branch coverage)
- [ ] Run `make quality-gate`

### Manual Verification
- [ ] Verify main help: `dbt-to-lookml --help`
- [ ] Verify generate help: `dbt-to-lookml generate --help`
- [ ] Verify validate help: `dbt-to-lookml validate --help`
- [ ] Test in 80-column terminal
- [ ] Test error formatting (invalid path)
- [ ] Test success formatting (dry-run)
- [ ] Test validation success

## Implementation Order

1. **Create CLI utilities package** (80 min)
   - formatting.py (45 min)
   - help_formatter.py (30 min)
   - __init__.py (5 min)

2. **Enhance generate command** (50 min)
   - Imports and decorator (3 min)
   - Docstring examples (10 min)
   - Error/success messages (27 min)
   - Manual verification (10 min)

3. **Enhance validate command** (35 min)
   - Decorator (1 min)
   - Docstring examples (8 min)
   - Messages (15 min)
   - Manual verification (11 min)

4. **Enhance main CLI group** (15 min)
   - Docstring (10 min)
   - Verification (5 min)

5. **Create unit tests** (60 min)
   - Test formatting utilities (60 min)

6. **Create CLI tests** (45 min)
   - Test help output (45 min)

7. **Type safety and quality gates** (30 min)
   - Type checking (15 min)
   - Test suite (10 min)
   - Quality gate (5 min)

**Total estimated time**: 5.2 hours

## Success Metrics

### Functional Requirements
- [ ] `dbt-to-lookml --help` shows rich-formatted help with examples
- [ ] `dbt-to-lookml generate --help` shows examples section
- [ ] `dbt-to-lookml generate --help` shows options table
- [ ] `dbt-to-lookml validate --help` shows examples section
- [ ] `dbt-to-lookml validate --help` shows options table
- [ ] Error messages use Rich panels with context
- [ ] Success messages use Rich panels with details
- [ ] Warning messages use Rich panels with context

### Technical Requirements
- [ ] All help text fits in 80 columns (with 2-char margin)
- [ ] `make type-check` passes with no mypy errors
- [ ] `make test-fast` passes all tests
- [ ] `make test-full` passes with no regressions
- [ ] Unit test coverage for CLI formatting at 100%
- [ ] Overall branch coverage remains 95%+

### Example Coverage
- [ ] Basic usage example in generate help
- [ ] Prefixes example in generate help
- [ ] Dry-run example in generate help
- [ ] Timezone conversion example in generate help
- [ ] Basic validation example in validate help
- [ ] Strict mode example in validate help
- [ ] Chained commands example in validate help

## Ready for Implementation

This spec is complete and ready for implementation. All design decisions are documented, code patterns are specified, and test coverage is planned. Proceed with implementation following the checklist and implementation order.

**Next Steps**:
1. Review this spec for completeness
2. Begin Phase 1: Create CLI utilities package
3. Follow implementation order through Phase 6
4. Verify all success metrics are met
5. Update issue status to "ready" after review
