# Implementation Strategy: DTL-015

**Issue**: DTL-015 - Add wizard dependencies and base infrastructure
**Analyzed**: 2025-11-12T21:30:00Z
**Stack**: backend
**Type**: feature

## Approach

Establish the foundational infrastructure for a hybrid wizard system that enhances the CLI with interactive guidance. This issue focuses on:

1. Adding appropriate dependencies for prompt-based interactions (questionary) and optional TUI (Textual)
2. Creating a wizard module structure following established project patterns
3. Integrating a base wizard command into the existing CLI architecture
4. Ensuring strict type safety and mypy compliance
5. Setting up a testing foundation for wizard functionality

This is the foundation layer for the CLI wizard enhancement epic (DTL-014), enabling future issues to build interactive experiences on top of a well-structured base.

## Architecture Impact

**Layer**: CLI Infrastructure (foundation for DTL-016 through DTL-021)

**New Module Structure**:
```
src/dbt_to_lookml/
├── wizard/                    # NEW module
│   ├── __init__.py           # Public exports and version
│   ├── base.py              # Base wizard class with common functionality
│   └── types.py             # Type definitions for wizard system
```

**Modified Files**:
- `pyproject.toml`: Add questionary and Textual dependencies
- `src/dbt_to_lookml/__main__.py`: Add wizard command group
- `uv.lock`: Updated via `uv lock` after dependency changes

**New Test Files**:
- `src/tests/unit/test_wizard_base.py`: Unit tests for base wizard functionality
- `src/tests/test_cli_wizard.py`: CLI tests for wizard command group

## Dependencies

- **Depends on**: None (this is the foundation layer)

- **Blocking**:
  - DTL-016: Enhance help text with rich examples and formatting
  - DTL-017: Implement contextual project detection and smart defaults
  - DTL-018: Build simple prompt-based wizard for generate command
  - DTL-019: Add validation preview and confirmation step
  - DTL-020: Implement optional TUI wizard mode with Textual
  - DTL-021: Integration, testing, and documentation

- **Related to**: DTL-014 (parent epic defining overall wizard strategy)

## Detailed Implementation Plan

### 1. Dependency Selection and Installation

#### Primary Dependencies

**questionary** (prompt-based wizard):
- **Purpose**: Rich, interactive prompts for CLI wizard experience
- **Advantages over alternatives**:
  - Better than `click.prompt()`: Supports validation, autocomplete, fuzzy search
  - Better than `prompt_toolkit` directly: Higher-level API with sensible defaults
  - Type-safe: Full type hints and mypy support
  - Rich integration: Works well with Rich console output
- **Version**: Latest stable (>=2.0.0)
- **License**: MIT (compatible)

**Textual** (TUI framework):
- **Purpose**: Optional full-screen TUI for advanced wizard mode
- **Advantages**:
  - Modern reactive framework built on Rich
  - Excellent type safety and mypy support
  - CSS-like styling for consistent UI
  - Async/await support for responsive UIs
- **Version**: Latest stable (>=0.40.0)
- **License**: MIT (compatible)
- **Deployment**: Optional dependency with graceful degradation

#### pyproject.toml Changes

**Location**: `pyproject.toml` lines 30-36 (dependencies section)

**Change 1**: Add to main dependencies (questionary is required):
```toml
dependencies = [
    "pydantic>=2.0",
    "pyyaml",
    "lkml",
    "click>=8.0",
    "rich",
    "questionary>=2.0.0",  # NEW: Interactive prompts for wizard
]
```

**Change 2**: Add optional dependency group for TUI features:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "mypy",
    "ruff",
    "build",
    "twine",
]
tui = [
    "textual>=0.40.0",  # NEW: Optional TUI mode for wizard
]
```

**Rationale**:
- questionary is core dependency: Simple prompts should always work
- Textual is optional: TUI mode gracefully degrades if not installed
- Follows existing pattern: dev dependencies are already optional
- Package size: questionary is lightweight (~100KB), Textual is heavier (~2MB)

#### Installation Commands

```bash
# Update dependencies in pyproject.toml (manual edit)
# Lock new dependencies
uv lock

# Install for development (includes TUI)
uv pip install -e ".[dev,tui]"

# Verify installation
python -c "import questionary; import textual; print('Dependencies OK')"
```

### 2. Create Wizard Module Structure

#### Module: src/dbt_to_lookml/wizard/__init__.py

**Purpose**: Public API exports and version information

**Implementation**:
```python
"""Interactive wizard system for dbt-to-lookml CLI.

This module provides prompt-based and TUI-based wizards for guiding users
through configuration and command building.
"""

from dbt_to_lookml.wizard.base import BaseWizard

__all__ = ["BaseWizard"]
```

**Type checking**:
- All exports must have complete type hints
- No `Any` types at module boundary
- Mypy strict mode compatible

#### Module: src/dbt_to_lookml/wizard/types.py

**Purpose**: Type definitions for wizard system (enums, protocols, type aliases)

**Implementation**:
```python
"""Type definitions for wizard system."""

from enum import Enum
from typing import Any, Protocol


class WizardMode(Enum):
    """Wizard interaction modes."""

    PROMPT = "prompt"  # Simple prompt-based wizard
    TUI = "tui"  # Full-screen Textual TUI


class WizardStep(Protocol):
    """Protocol for wizard step implementations."""

    def validate(self) -> tuple[bool, str]:
        """Validate step input.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is empty string if valid.
        """
        ...

    def get_summary(self) -> str:
        """Get summary of step configuration.

        Returns:
            Human-readable summary string.
        """
        ...


# Type alias for wizard configuration
WizardConfig = dict[str, Any]
```

**Type checking considerations**:
- `WizardMode` enum provides type-safe mode selection
- `WizardStep` protocol allows duck-typed step implementations
- `WizardConfig` is explicit `dict[str, Any]` (validated by Pydantic later)

#### Module: src/dbt_to_lookml/wizard/base.py

**Purpose**: Base wizard class with common functionality shared by all wizards

**Implementation**:
```python
"""Base wizard class for all interactive wizards."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from rich.console import Console

from dbt_to_lookml.wizard.types import WizardConfig, WizardMode

console = Console()


class BaseWizard(ABC):
    """Base class for all wizard implementations.

    Provides common functionality:
    - Mode detection (prompt vs TUI)
    - Configuration validation
    - Summary generation
    - Error handling
    """

    def __init__(self, mode: WizardMode = WizardMode.PROMPT) -> None:
        """Initialize the wizard.

        Args:
            mode: Wizard interaction mode (prompt or TUI).
        """
        self.mode = mode
        self.config: WizardConfig = {}

    @abstractmethod
    def run(self) -> WizardConfig:
        """Run the wizard and collect configuration.

        Returns:
            Dictionary of configuration values collected from user.

        Raises:
            ValueError: If wizard is cancelled or invalid input provided.
        """
        pass

    @abstractmethod
    def validate_config(self, config: WizardConfig) -> tuple[bool, str]:
        """Validate wizard configuration.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is empty string if valid.
        """
        pass

    def get_summary(self) -> str:
        """Get summary of wizard configuration.

        Returns:
            Human-readable summary of configuration.
        """
        if not self.config:
            return "[dim]No configuration collected yet[/dim]"

        lines = ["[bold]Wizard Configuration:[/bold]"]
        for key, value in self.config.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def check_tui_available(self) -> bool:
        """Check if Textual TUI mode is available.

        Returns:
            True if Textual is installed and TUI mode can be used.
        """
        try:
            import textual  # noqa: F401

            return True
        except ImportError:
            return False

    def handle_tui_unavailable(self) -> None:
        """Handle graceful degradation when TUI is not available."""
        console.print(
            "[yellow]Warning: Textual TUI not available. "
            "Install with: pip install dbt-to-lookml[tui][/yellow]"
        )
        console.print("[dim]Falling back to prompt-based wizard...[/dim]")
        self.mode = WizardMode.PROMPT
```

**Design patterns**:
- Abstract base class (ABC) for extensibility
- Template method pattern: `run()` is abstract, `get_summary()` is concrete
- Graceful degradation: `check_tui_available()` and `handle_tui_unavailable()`
- Rich console integration: All output uses Rich for consistency
- Type-safe configuration: `WizardConfig` dict validated by subclasses

**Type checking compliance**:
- All methods have complete type hints
- Abstract methods use `@abstractmethod` decorator
- Return types are explicit (no implicit `None`)
- Dict types use `dict[str, Any]` for config (validated later)

### 3. Integrate Wizard Command Group into CLI

#### Changes to src/dbt_to_lookml/__main__.py

**Current structure** (lines 21-25):
```python
@click.group()
@click.version_option()
def cli() -> None:
    """Convert dbt semantic models to LookML views and explores."""
    pass
```

**Location**: After line 25, before the first `@cli.command()` decorator (line 28)

**Addition**: New wizard command group

```python
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
```

**Import additions** (top of file, after line 7):
```python
from typing import Any, Optional  # Update existing import
```

**Rationale**:
- Command group pattern: Follows Click best practices for nested commands
- Test command: Temporary command to validate infrastructure (removed in DTL-018)
- Mode selection: CLI flag for choosing prompt vs TUI mode
- Graceful degradation: TUI unavailable handling is demonstrated
- Help text: Clear examples and usage guidance

**CLI structure after change**:
```
dbt-to-lookml
├── generate            # Existing command
├── validate            # Existing command
└── wizard              # NEW command group
    └── test            # NEW test command (temporary)
```

### 4. Type Safety and Mypy Compliance

#### Type Checking Configuration

**Current state** (pyproject.toml lines 66-70):
```toml
[tool.mypy]
python_version = "3.9"
strict = true
warn_return_any = true
warn_unused_configs = true
```

**No changes needed**: Existing strict mode configuration is sufficient

#### Type Checking Strategy

1. **All wizard module files must pass `mypy --strict`**:
   ```bash
   mypy src/dbt_to_lookml/wizard/
   ```

2. **Type hints checklist**:
   - [ ] All function signatures have parameter types
   - [ ] All function signatures have return types
   - [ ] No use of `Any` except in validated config dicts
   - [ ] Protocol definitions are complete
   - [ ] Enum values are properly typed
   - [ ] Abstract methods use `@abstractmethod`

3. **Common type patterns**:
   ```python
   # Good: Explicit dict typing
   def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
       ...

   # Good: Optional with explicit None
   def get_mode(self) -> WizardMode | None:
       ...

   # Good: Protocol for duck typing
   class WizardStep(Protocol):
       def validate(self) -> tuple[bool, str]: ...

   # Avoid: Implicit Any
   def bad_function(config):  # Missing type hints
       ...
   ```

4. **Third-party library type stubs**:
   - questionary: Built-in type stubs (no additional packages needed)
   - textual: Built-in type stubs (no additional packages needed)
   - Both libraries are mypy-strict compatible

#### Verification Commands

```bash
# Type check wizard module
mypy src/dbt_to_lookml/wizard/ --strict

# Type check entire codebase (should still pass)
make type-check

# Verify no new mypy errors introduced
mypy src/dbt_to_lookml/ --strict
```

### 5. Testing Approach

#### Unit Tests: src/tests/unit/test_wizard_base.py

**Purpose**: Test BaseWizard abstract class and common functionality

**Test cases**:

```python
"""Unit tests for wizard base functionality."""

from typing import Any

import pytest

from dbt_to_lookml.wizard.base import BaseWizard
from dbt_to_lookml.wizard.types import WizardMode


class TestBaseWizard:
    """Test suite for BaseWizard class."""

    def test_init_default_mode(self) -> None:
        """Test wizard initializes with default prompt mode."""

        class MinimalWizard(BaseWizard):
            def run(self) -> dict[str, Any]:
                return {}

            def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
                return (True, "")

        wizard = MinimalWizard()
        assert wizard.mode == WizardMode.PROMPT
        assert wizard.config == {}

    def test_init_with_tui_mode(self) -> None:
        """Test wizard initializes with TUI mode."""

        class MinimalWizard(BaseWizard):
            def run(self) -> dict[str, Any]:
                return {}

            def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
                return (True, "")

        wizard = MinimalWizard(mode=WizardMode.TUI)
        assert wizard.mode == WizardMode.TUI

    def test_get_summary_empty_config(self) -> None:
        """Test summary generation with empty config."""

        class MinimalWizard(BaseWizard):
            def run(self) -> dict[str, Any]:
                return {}

            def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
                return (True, "")

        wizard = MinimalWizard()
        summary = wizard.get_summary()
        assert "No configuration collected yet" in summary

    def test_get_summary_with_config(self) -> None:
        """Test summary generation with configuration."""

        class MinimalWizard(BaseWizard):
            def run(self) -> dict[str, Any]:
                return {}

            def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
                return (True, "")

        wizard = MinimalWizard()
        wizard.config = {"input_dir": "semantic_models/", "output_dir": "build/"}
        summary = wizard.get_summary()

        assert "Wizard Configuration" in summary
        assert "input_dir: semantic_models/" in summary
        assert "output_dir: build/" in summary

    def test_check_tui_available_when_installed(self) -> None:
        """Test TUI availability check when Textual is installed."""

        class MinimalWizard(BaseWizard):
            def run(self) -> dict[str, Any]:
                return {}

            def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
                return (True, "")

        wizard = MinimalWizard()

        # This test will pass if Textual is installed, fail otherwise
        # In CI/dev environments with [tui] extra, should pass
        try:
            import textual  # noqa: F401

            assert wizard.check_tui_available() is True
        except ImportError:
            assert wizard.check_tui_available() is False

    def test_handle_tui_unavailable_falls_back_to_prompt(self) -> None:
        """Test graceful degradation from TUI to prompt mode."""

        class MinimalWizard(BaseWizard):
            def run(self) -> dict[str, Any]:
                return {}

            def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
                return (True, "")

        wizard = MinimalWizard(mode=WizardMode.TUI)
        assert wizard.mode == WizardMode.TUI

        wizard.handle_tui_unavailable()
        assert wizard.mode == WizardMode.PROMPT

    def test_abstract_methods_must_be_implemented(self) -> None:
        """Test that BaseWizard cannot be instantiated without abstract methods."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseWizard()  # type: ignore[abstract]
```

**Coverage requirements**:
- Target: 100% coverage of BaseWizard methods
- All branches in `check_tui_available()` and `handle_tui_unavailable()`
- Abstract method enforcement verified

#### CLI Tests: src/tests/test_cli_wizard.py

**Purpose**: Test wizard command group integration with CLI

**Test cases**:

```python
"""CLI tests for wizard command group."""

from click.testing import CliRunner

from dbt_to_lookml.__main__ import cli


class TestWizardCLI:
    """Test suite for wizard CLI commands."""

    def test_wizard_group_help(self) -> None:
        """Test wizard command group help text."""
        runner = CliRunner()
        result = runner.invoke(cli, ["wizard", "--help"])

        assert result.exit_code == 0
        assert "Interactive wizard" in result.output
        assert "wizard generate" in result.output or "wizard test" in result.output

    def test_wizard_test_command_prompt_mode(self) -> None:
        """Test wizard test command in prompt mode."""
        runner = CliRunner()
        result = runner.invoke(cli, ["wizard", "test", "--mode", "prompt"])

        assert result.exit_code == 0
        assert "Wizard infrastructure working" in result.output
        assert "Mode: prompt" in result.output

    def test_wizard_test_command_tui_mode(self) -> None:
        """Test wizard test command in TUI mode."""
        runner = CliRunner()
        result = runner.invoke(cli, ["wizard", "test", "--mode", "tui"])

        assert result.exit_code == 0
        # Should either work (if Textual installed) or fall back to prompt
        assert "Wizard infrastructure working" in result.output

    def test_wizard_test_default_mode(self) -> None:
        """Test wizard test command with default mode."""
        runner = CliRunner()
        result = runner.invoke(cli, ["wizard", "test"])

        assert result.exit_code == 0
        assert "Mode: prompt" in result.output  # Default is prompt
```

**Coverage requirements**:
- All wizard CLI commands accessible via Click testing
- Help text displayed correctly
- Mode selection works (prompt/TUI)
- Graceful degradation tested

#### Integration with Existing Test Suite

**Markers**: Add to pyproject.toml test markers (lines 92-103):
```toml
markers = [
    "unit: marks tests as unit tests (fast, isolated)",
    "integration: marks tests as integration tests (slower, end-to-end)",
    "golden: marks tests as golden file comparison tests",
    "cli: marks tests as CLI interface tests",
    "wizard: marks tests as wizard functionality tests",  # NEW
    "performance: marks tests as performance/benchmark tests",
    "error_handling: marks tests as error handling and robustness tests",
    "slow: marks tests as slow running (may be skipped in fast runs)",
    "smoke: marks tests as smoke tests (quick validation)",
]
```

**Test organization**:
```bash
# Run only wizard tests
pytest -m wizard

# Run wizard tests with unit tests
pytest -m "unit or wizard"

# Exclude wizard tests (for fast feedback loop)
pytest -m "not wizard"
```

## Implementation Checklist

- [ ] Update `pyproject.toml` dependencies (questionary required, textual optional)
- [ ] Run `uv lock` to update lock file
- [ ] Install dependencies: `uv pip install -e ".[dev,tui]"`
- [ ] Create `src/dbt_to_lookml/wizard/__init__.py` with public exports
- [ ] Create `src/dbt_to_lookml/wizard/types.py` with type definitions
- [ ] Create `src/dbt_to_lookml/wizard/base.py` with BaseWizard class
- [ ] Add wizard command group to `src/dbt_to_lookml/__main__.py`
- [ ] Add temporary `wizard test` command for validation
- [ ] Create `src/tests/unit/test_wizard_base.py` with unit tests
- [ ] Create `src/tests/test_cli_wizard.py` with CLI tests
- [ ] Run `make type-check` to verify mypy compliance
- [ ] Run `make test-fast` to verify unit tests pass
- [ ] Run `make test-full` to verify no regressions
- [ ] Test CLI: `dbt-to-lookml wizard --help`
- [ ] Test CLI: `dbt-to-lookml wizard test --mode prompt`
- [ ] Test CLI: `dbt-to-lookml wizard test --mode tui` (if Textual installed)

## Implementation Order

1. **Update dependencies** - 10 min
   - Edit `pyproject.toml`
   - Run `uv lock`
   - Install with `uv pip install -e ".[dev,tui]"`

2. **Create type definitions** - 10 min
   - Create `wizard/types.py`
   - Define `WizardMode`, `WizardStep`, `WizardConfig`

3. **Create base wizard class** - 20 min
   - Create `wizard/base.py`
   - Implement `BaseWizard` with abstract methods
   - Add TUI availability checking

4. **Create module exports** - 5 min
   - Create `wizard/__init__.py`
   - Export `BaseWizard`

5. **Integrate CLI command group** - 15 min
   - Add `@cli.group()` for wizard
   - Add temporary `wizard test` command
   - Test with `dbt-to-lookml wizard --help`

6. **Write unit tests** - 30 min
   - Create `test_wizard_base.py`
   - Test all BaseWizard methods
   - Test abstract method enforcement

7. **Write CLI tests** - 20 min
   - Create `test_cli_wizard.py`
   - Test wizard command group
   - Test mode selection

8. **Verify type safety** - 10 min
   - Run `make type-check`
   - Fix any mypy errors
   - Verify strict mode compliance

9. **Run test suite** - 10 min
   - Run `make test-fast`
   - Run `make test-full`
   - Fix any regressions

**Estimated total**: 2 hours

## Rollout Impact

### User-Facing Changes

- **New CLI command group**: `dbt-to-lookml wizard`
- **New dependency**: questionary (required, ~100KB installed)
- **Optional dependency**: textual (optional, ~2MB installed)
- **Help text**: Wizard commands appear in `--help` output

### Developer-Facing Changes

- **New module**: `dbt_to_lookml.wizard` package
- **Import changes**: `from dbt_to_lookml.wizard import BaseWizard`
- **Type definitions**: `WizardMode`, `WizardStep`, `WizardConfig` available
- **Testing**: New test marker `wizard` for filtering tests

### Backward Compatibility

- **Fully backward compatible**: All existing commands continue to work
- **No breaking changes**: Existing code/tests require no modifications
- **Optional features**: TUI mode is opt-in, graceful degradation if unavailable

### Performance Impact

- **CLI startup**: Negligible impact (wizard modules lazy-loaded)
- **Package size**: +100KB for questionary, +2MB for textual (optional)
- **Memory**: Wizard classes instantiated only when used

## Notes for Implementation

1. **Dependency choice rationale**:
   - questionary over prompt_toolkit: Higher-level API, better DX
   - questionary over click.prompt(): Richer features (validation, fuzzy search)
   - Textual over alternatives (urwid, npyscreen): Modern, type-safe, Rich integration

2. **Graceful degradation pattern**:
   ```python
   if mode == WizardMode.TUI and not wizard.check_tui_available():
       wizard.handle_tui_unavailable()
       # Falls back to prompt mode
   ```

3. **Module organization**:
   - `types.py`: Type definitions (enums, protocols, aliases)
   - `base.py`: Abstract base class with common functionality
   - Future: `generate.py`, `validate.py` for command-specific wizards

4. **Testing philosophy**:
   - Unit tests: Fast, isolated, test abstract class behavior
   - CLI tests: Integration-style, test Click command registration
   - Future: End-to-end tests in DTL-021

5. **Type safety is paramount**:
   - All wizard code must pass `mypy --strict`
   - No `Any` types except validated config dicts
   - Protocol definitions for extensibility

6. **Temporary test command**:
   - `wizard test` command is temporary (removed in DTL-018)
   - Purpose: Validate infrastructure before building real wizards
   - Demonstrates TUI availability checking

## Success Metrics

- [ ] questionary installed and importable
- [ ] Textual installed and importable (in dev environment)
- [ ] `dbt-to-lookml wizard --help` shows command group
- [ ] `dbt-to-lookml wizard test` runs successfully
- [ ] `dbt-to-lookml wizard test --mode tui` falls back gracefully if Textual not installed
- [ ] `make type-check` passes with no mypy errors
- [ ] `make test-fast` passes all tests
- [ ] `make test-full` passes with no regressions
- [ ] Unit test coverage for wizard module at 100%
- [ ] CLI test coverage for wizard commands at 100%

## Pre-Implementation Checklist

Before starting DTL-015 implementation:

- [ ] Review DTL-014 epic to understand overall wizard vision
- [ ] Confirm Python 3.9+ environment (for `|` union type syntax)
- [ ] Verify uv package manager is available
- [ ] Check existing CLI structure in `__main__.py`
- [ ] Review existing interface patterns (Parser, Generator)
- [ ] Confirm test infrastructure is working (`make test-fast`)

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-015.md`
3. Change status from `refinement` to `awaiting-strategy-review`, then to `strategy-approved`
4. Run: `/implement:1-spec DTL-015`
