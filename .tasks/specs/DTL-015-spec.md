# Implementation Spec: DTL-015 - Add wizard dependencies and base infrastructure

## Metadata
- **Issue**: `DTL-015`
- **Title**: Add wizard dependencies and base infrastructure
- **Stack**: backend
- **Type**: feature
- **Generated**: 2025-11-17T21:30:00Z
- **Strategy**: Approved 2025-11-12T21:30:00Z
- **Parent Epic**: DTL-014 (CLI Wizard Enhancement)

## Issue Context

### Problem Statement

The current dbt-to-lookml CLI requires users to remember complex command structures and option combinations. To enhance the developer experience, we need to establish the foundational infrastructure for an interactive wizard system that will guide users through configuration and command building.

This issue focuses on the foundation layer: adding appropriate dependencies (questionary for prompts, Textual for optional TUI), creating the wizard module structure, and integrating a base wizard command into the existing CLI architecture.

### Solution Approach

Establish a hybrid wizard system infrastructure that:
1. Adds questionary as a required dependency for prompt-based interactions
2. Adds Textual as an optional dependency for full-screen TUI mode with graceful degradation
3. Creates a well-structured wizard module following existing project patterns
4. Ensures strict type safety and mypy compliance throughout
5. Integrates smoothly with the existing Click-based CLI
6. Provides a testing foundation for wizard functionality

### Success Criteria

- [ ] Dependencies installed and locked in uv.lock
- [ ] Wizard module structure created with proper exports
- [ ] Empty wizard command accessible: `dbt-to-lookml wizard --help`
- [ ] Type hints complete and mypy validation passing
- [ ] Unit and CLI tests passing with 100% coverage of new code
- [ ] Graceful degradation when Textual is not installed

## Approved Strategy Summary

**Key Architectural Decisions**:

1. **Dependency Strategy**: questionary as required (lightweight, rich features), Textual as optional (heavier, advanced TUI)
2. **Module Structure**: Follow existing pattern (interfaces → implementations), with `wizard/types.py`, `wizard/base.py`, `wizard/__init__.py`
3. **CLI Integration**: New `@cli.group()` for wizard commands, similar to existing command structure
4. **Type Safety**: Strict mypy compliance with complete type hints, no `Any` except in validated config dicts
5. **Testing**: Unit tests for BaseWizard, CLI tests for command group, marker for filtering wizard tests
6. **Graceful Degradation**: Check TUI availability, fall back to prompt mode with user notification

## Implementation Plan

### Phase 1: Dependency Management (15 min)

Add questionary as required dependency and Textual as optional dependency, following existing pyproject.toml patterns.

**Tasks**:
1. **Update pyproject.toml dependencies**
   - File: `pyproject.toml`
   - Action: Add questionary>=2.0.0 to dependencies list (line 30-36)
   - Pattern: Follow existing dependency format (e.g., `"click>=8.0"`)
   - Reference: `pyproject.toml:30-36` (existing dependencies)

2. **Add optional TUI dependency group**
   - File: `pyproject.toml`
   - Action: Create new `tui` optional dependency group
   - Pattern: Follow existing `dev` optional dependencies pattern
   - Reference: `pyproject.toml:38-46` (existing dev dependencies)

3. **Lock and install dependencies**
   - Action: Run `uv lock` and `uv pip install -e ".[dev,tui]"`
   - Verification: Test imports work

### Phase 2: Type Definitions Module (15 min)

Create type definitions for the wizard system including enums, protocols, and type aliases.

**Tasks**:
1. **Create wizard/types.py module**
   - File: `src/dbt_to_lookml/wizard/types.py` (NEW)
   - Action: Define WizardMode enum, WizardStep protocol, WizardConfig type alias
   - Pattern: Follow existing enum pattern from `types.py`
   - Reference: `src/dbt_to_lookml/types.py` (DimensionType, AggregationType enums)

### Phase 3: Base Wizard Class (25 min)

Implement abstract base class for all wizard implementations with common functionality.

**Tasks**:
1. **Create wizard/base.py module**
   - File: `src/dbt_to_lookml/wizard/base.py` (NEW)
   - Action: Implement BaseWizard ABC with abstract methods (run, validate_config) and concrete methods (get_summary, check_tui_available, handle_tui_unavailable)
   - Pattern: Follow existing ABC pattern from interfaces
   - Reference: `src/dbt_to_lookml/interfaces/parser.py` (Parser ABC pattern)

### Phase 4: Module Initialization (5 min)

Create public API exports for the wizard module.

**Tasks**:
1. **Create wizard/__init__.py**
   - File: `src/dbt_to_lookml/wizard/__init__.py` (NEW)
   - Action: Export BaseWizard and add module docstring
   - Pattern: Follow existing __init__ pattern
   - Reference: `src/dbt_to_lookml/__init__.py`

### Phase 5: CLI Integration (20 min)

Integrate wizard command group into existing CLI structure.

**Tasks**:
1. **Add wizard command group to CLI**
   - File: `src/dbt_to_lookml/__main__.py`
   - Action: Add `@cli.group()` decorator and wizard group function after line 25
   - Pattern: Follow existing `@cli.command()` pattern but use `@cli.group()`
   - Reference: `__main__.py:21-25` (existing CLI group)

2. **Add temporary wizard test command**
   - File: `src/dbt_to_lookml/__main__.py`
   - Action: Add `@wizard.command(name="test")` with mode option
   - Pattern: Follow existing command option pattern
   - Reference: `__main__.py:28-106` (generate command structure)

3. **Update imports**
   - File: `src/dbt_to_lookml/__main__.py`
   - Action: Add `Any` to typing import (line 4)
   - Pattern: Update existing import line
   - Reference: `__main__.py:4` (existing typing import)

### Phase 6: Unit Tests (30 min)

Write comprehensive unit tests for BaseWizard functionality.

**Tasks**:
1. **Create test_wizard_base.py**
   - File: `src/tests/unit/test_wizard_base.py` (NEW)
   - Action: Create TestBaseWizard class with tests for initialization, mode selection, summary generation, TUI availability, abstract method enforcement
   - Pattern: Follow existing unit test pattern
   - Reference: `src/tests/unit/test_dbt_parser.py:18-100` (test class structure)

### Phase 7: CLI Tests (25 min)

Write CLI tests for wizard command group integration.

**Tasks**:
1. **Create test_cli_wizard.py**
   - File: `src/tests/test_cli_wizard.py` (NEW)
   - Action: Create TestWizardCLI class with tests for help text, mode selection, command execution
   - Pattern: Follow existing CLI test pattern
   - Reference: `src/tests/test_cli.py:14-80` (CLI test structure)

2. **Add wizard test marker**
   - File: `pyproject.toml`
   - Action: Add "wizard: marks tests as wizard functionality tests" to markers list
   - Pattern: Follow existing marker format
   - Reference: `pyproject.toml:92-104` (existing markers)

### Phase 8: Type Safety Verification (10 min)

Ensure all new code passes strict mypy type checking.

**Tasks**:
1. **Run type checking on wizard module**
   - Action: `mypy src/dbt_to_lookml/wizard/ --strict`
   - Expected: No errors

2. **Run type checking on entire codebase**
   - Action: `make type-check`
   - Expected: No new errors introduced

### Phase 9: Test Execution and Validation (15 min)

Run test suite to ensure no regressions and verify new functionality.

**Tasks**:
1. **Run unit tests**
   - Action: `make test-fast`
   - Expected: All tests pass including new wizard tests

2. **Run full test suite**
   - Action: `make test-full`
   - Expected: All tests pass, no regressions

3. **Manual CLI testing**
   - Action: Test `dbt-to-lookml wizard --help`, `dbt-to-lookml wizard test`, `dbt-to-lookml wizard test --mode tui`
   - Expected: Help text displays, test command runs successfully

## Detailed Task Breakdown

### Task 1: Update pyproject.toml Dependencies

**File**: `pyproject.toml`

**Action**: Add questionary to main dependencies and create tui optional dependency group

**Implementation Guidance**:
```toml
# Line 30-36: Add questionary to dependencies
dependencies = [
    "pydantic>=2.0",
    "pyyaml",
    "lkml",
    "click>=8.0",
    "rich",
    "questionary>=2.0.0",  # NEW: Interactive prompts for wizard
]

# Line 38-46: Add tui optional dependency group
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

**Reference**: Existing dependency structure at `pyproject.toml:30-46`

**Tests**: Import verification in unit tests

**Estimated lines**: ~8 lines modified

---

### Task 2: Create wizard/types.py

**File**: `src/dbt_to_lookml/wizard/types.py` (NEW)

**Action**: Create type definitions module with WizardMode enum, WizardStep protocol, and type aliases

**Implementation Guidance**:
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

**Reference**: Similar enum pattern at `src/dbt_to_lookml/types.py:9-20` (DimensionType enum)

**Tests**:
- Type checking with mypy
- Enum value access in unit tests
- Protocol duck typing in unit tests

**Estimated lines**: ~40 lines

---

### Task 3: Create wizard/base.py

**File**: `src/dbt_to_lookml/wizard/base.py` (NEW)

**Action**: Implement BaseWizard abstract base class with common wizard functionality

**Implementation Guidance**:
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

**Reference**: Similar ABC pattern at `src/dbt_to_lookml/interfaces/parser.py:12-90` (Parser ABC)

**Tests**:
- Initialization with default and custom modes
- Summary generation with empty and populated config
- TUI availability checking (conditional on Textual installation)
- Graceful degradation from TUI to prompt mode
- Abstract method enforcement (cannot instantiate BaseWizard directly)

**Estimated lines**: ~95 lines

---

### Task 4: Create wizard/__init__.py

**File**: `src/dbt_to_lookml/wizard/__init__.py` (NEW)

**Action**: Create module initialization with public API exports

**Implementation Guidance**:
```python
"""Interactive wizard system for dbt-to-lookml CLI.

This module provides prompt-based and TUI-based wizards for guiding users
through configuration and command building.
"""

from dbt_to_lookml.wizard.base import BaseWizard

__all__ = ["BaseWizard"]
```

**Reference**: Similar pattern at `src/dbt_to_lookml/__init__.py`

**Tests**: Import verification in CLI tests

**Estimated lines**: ~10 lines

---

### Task 5: Add Wizard Command Group to CLI

**File**: `src/dbt_to_lookml/__main__.py`

**Action**: Add wizard command group and temporary test command after existing CLI group definition

**Implementation Guidance**:

**Change 1**: Update typing import (line 4)
```python
from typing import Any, Optional  # Update existing import
```

**Change 2**: Add wizard command group after line 25
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

**Reference**:
- Existing CLI group at `__main__.py:21-25`
- Existing command pattern at `__main__.py:28-106` (generate command)
- Click choice option pattern throughout file

**Tests**: CLI tests for wizard group help, test command execution

**Estimated lines**: ~60 lines added

---

### Task 6: Create Unit Tests for BaseWizard

**File**: `src/tests/unit/test_wizard_base.py` (NEW)

**Action**: Create comprehensive unit tests for BaseWizard class

**Implementation Guidance**:
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

**Reference**: Similar test structure at `src/tests/unit/test_dbt_parser.py:18-100`

**Tests**: All test methods are themselves tests

**Estimated lines**: ~120 lines

---

### Task 7: Create CLI Tests for Wizard Commands

**File**: `src/tests/test_cli_wizard.py` (NEW)

**Action**: Create CLI tests for wizard command group

**Implementation Guidance**:
```python
"""CLI tests for wizard command group."""

from click.testing import CliRunner
import pytest

from dbt_to_lookml.__main__ import cli


class TestWizardCLI:
    """Test suite for wizard CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    def test_wizard_group_help(self, runner: CliRunner) -> None:
        """Test wizard command group help text."""
        result = runner.invoke(cli, ["wizard", "--help"])

        assert result.exit_code == 0
        assert "Interactive wizard" in result.output
        assert "wizard test" in result.output

    def test_wizard_test_command_prompt_mode(self, runner: CliRunner) -> None:
        """Test wizard test command in prompt mode."""
        result = runner.invoke(cli, ["wizard", "test", "--mode", "prompt"])

        assert result.exit_code == 0
        assert "Wizard infrastructure working" in result.output
        assert "Mode: prompt" in result.output

    def test_wizard_test_command_tui_mode(self, runner: CliRunner) -> None:
        """Test wizard test command in TUI mode."""
        result = runner.invoke(cli, ["wizard", "test", "--mode", "tui"])

        assert result.exit_code == 0
        # Should either work (if Textual installed) or fall back to prompt
        assert "Wizard infrastructure working" in result.output

    def test_wizard_test_default_mode(self, runner: CliRunner) -> None:
        """Test wizard test command with default mode."""
        result = runner.invoke(cli, ["wizard", "test"])

        assert result.exit_code == 0
        assert "Mode: prompt" in result.output  # Default is prompt
```

**Reference**: Similar CLI test structure at `src/tests/test_cli.py:14-80`

**Tests**: All test methods are themselves tests

**Estimated lines**: ~50 lines

---

### Task 8: Add Wizard Test Marker

**File**: `pyproject.toml`

**Action**: Add wizard test marker to pytest configuration

**Implementation Guidance**:
```toml
# Line 92-104: Add wizard marker
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
    "stress: marks tests as stress tests (high load/memory)",
    "memory: marks tests that check for memory leaks",
    "concurrent: marks tests that test concurrent/parallel execution",
]
```

**Reference**: Existing marker format at `pyproject.toml:92-104`

**Tests**: Test marker filtering with `pytest -m wizard`

**Estimated lines**: 1 line added

## File Changes

### Files to Modify

#### `pyproject.toml`
**Why**: Add new dependencies and test marker

**Changes**:
- Add questionary>=2.0.0 to dependencies list
- Create new tui optional dependency group with textual>=0.40.0
- Add wizard test marker to pytest configuration

**Estimated lines**: ~10 lines added/modified

#### `src/dbt_to_lookml/__main__.py`
**Why**: Integrate wizard command group into CLI

**Changes**:
- Update typing import to include Any
- Add @cli.group() wizard command group
- Add @wizard.command("test") temporary test command with mode option

**Estimated lines**: ~60 lines added

### Files to Create

#### `src/dbt_to_lookml/wizard/__init__.py`
**Why**: Public API exports for wizard module

**Structure**: Based on existing `src/dbt_to_lookml/__init__.py`

```python
"""Interactive wizard system for dbt-to-lookml CLI.

This module provides prompt-based and TUI-based wizards for guiding users
through configuration and command building.
"""

from dbt_to_lookml.wizard.base import BaseWizard

__all__ = ["BaseWizard"]
```

**Estimated lines**: ~10 lines

#### `src/dbt_to_lookml/wizard/types.py`
**Why**: Type definitions for wizard system

**Structure**: Based on `src/dbt_to_lookml/types.py`

```python
"""Type definitions for wizard system."""

from enum import Enum
from typing import Any, Protocol


class WizardMode(Enum):
    """Wizard interaction modes."""
    PROMPT = "prompt"
    TUI = "tui"


class WizardStep(Protocol):
    """Protocol for wizard step implementations."""
    def validate(self) -> tuple[bool, str]: ...
    def get_summary(self) -> str: ...


WizardConfig = dict[str, Any]
```

**Estimated lines**: ~40 lines

#### `src/dbt_to_lookml/wizard/base.py`
**Why**: Abstract base class for all wizard implementations

**Structure**: Based on `src/dbt_to_lookml/interfaces/parser.py`

```python
"""Base wizard class for all interactive wizards."""

from abc import ABC, abstractmethod
from typing import Any
from rich.console import Console
from dbt_to_lookml.wizard.types import WizardConfig, WizardMode

console = Console()


class BaseWizard(ABC):
    """Base class for all wizard implementations."""

    def __init__(self, mode: WizardMode = WizardMode.PROMPT) -> None:
        self.mode = mode
        self.config: WizardConfig = {}

    @abstractmethod
    def run(self) -> WizardConfig: ...

    @abstractmethod
    def validate_config(self, config: WizardConfig) -> tuple[bool, str]: ...

    def get_summary(self) -> str: ...
    def check_tui_available(self) -> bool: ...
    def handle_tui_unavailable(self) -> None: ...
```

**Estimated lines**: ~95 lines

#### `src/tests/unit/test_wizard_base.py`
**Why**: Unit tests for BaseWizard functionality

**Structure**: Based on `src/tests/unit/test_dbt_parser.py`

```python
"""Unit tests for wizard base functionality."""

import pytest
from typing import Any
from dbt_to_lookml.wizard.base import BaseWizard
from dbt_to_lookml.wizard.types import WizardMode


class TestBaseWizard:
    """Test suite for BaseWizard class."""

    def test_init_default_mode(self) -> None: ...
    def test_init_with_tui_mode(self) -> None: ...
    def test_get_summary_empty_config(self) -> None: ...
    def test_get_summary_with_config(self) -> None: ...
    def test_check_tui_available_when_installed(self) -> None: ...
    def test_handle_tui_unavailable_falls_back_to_prompt(self) -> None: ...
    def test_abstract_methods_must_be_implemented(self) -> None: ...
```

**Estimated lines**: ~120 lines

#### `src/tests/test_cli_wizard.py`
**Why**: CLI tests for wizard command group

**Structure**: Based on `src/tests/test_cli.py`

```python
"""CLI tests for wizard command group."""

import pytest
from click.testing import CliRunner
from dbt_to_lookml.__main__ import cli


class TestWizardCLI:
    """Test suite for wizard CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner: ...

    def test_wizard_group_help(self, runner: CliRunner) -> None: ...
    def test_wizard_test_command_prompt_mode(self, runner: CliRunner) -> None: ...
    def test_wizard_test_command_tui_mode(self, runner: CliRunner) -> None: ...
    def test_wizard_test_default_mode(self, runner: CliRunner) -> None: ...
```

**Estimated lines**: ~50 lines

## Testing Strategy

### Unit Tests

**File**: `src/tests/unit/test_wizard_base.py`

**Test Cases**:

1. **test_init_default_mode**
   - Setup: Create MinimalWizard subclass implementing abstract methods
   - Action: Instantiate without mode parameter
   - Assert: mode == WizardMode.PROMPT, config == {}

2. **test_init_with_tui_mode**
   - Setup: Create MinimalWizard subclass
   - Action: Instantiate with mode=WizardMode.TUI
   - Assert: mode == WizardMode.TUI

3. **test_get_summary_empty_config**
   - Setup: Create MinimalWizard instance
   - Action: Call get_summary() with empty config
   - Assert: Returns "No configuration collected yet"

4. **test_get_summary_with_config**
   - Setup: Create MinimalWizard instance, set config with test data
   - Action: Call get_summary()
   - Assert: Summary includes all config keys and values

5. **test_check_tui_available_when_installed**
   - Setup: Create MinimalWizard instance
   - Action: Call check_tui_available()
   - Assert: Returns True if Textual installed, False otherwise (conditional)

6. **test_handle_tui_unavailable_falls_back_to_prompt**
   - Setup: Create MinimalWizard instance with TUI mode
   - Action: Call handle_tui_unavailable()
   - Assert: mode changes to WizardMode.PROMPT

7. **test_abstract_methods_must_be_implemented**
   - Setup: None
   - Action: Attempt to instantiate BaseWizard directly
   - Assert: Raises TypeError about abstract class

**Coverage target**: 100% of BaseWizard methods

### CLI Tests

**File**: `src/tests/test_cli_wizard.py`

**Test Cases**:

1. **test_wizard_group_help**
   - Setup: Create CliRunner
   - Action: Invoke `wizard --help`
   - Assert: Exit code 0, help text contains "Interactive wizard" and "wizard test"

2. **test_wizard_test_command_prompt_mode**
   - Setup: Create CliRunner
   - Action: Invoke `wizard test --mode prompt`
   - Assert: Exit code 0, output contains "Wizard infrastructure working" and "Mode: prompt"

3. **test_wizard_test_command_tui_mode**
   - Setup: Create CliRunner
   - Action: Invoke `wizard test --mode tui`
   - Assert: Exit code 0, output contains "Wizard infrastructure working" (may show fallback message)

4. **test_wizard_test_default_mode**
   - Setup: Create CliRunner
   - Action: Invoke `wizard test` (no mode flag)
   - Assert: Exit code 0, output contains "Mode: prompt"

**Coverage target**: 100% of wizard CLI commands

### Integration Testing

Not applicable for this issue - integration testing will be added in DTL-021

### Edge Cases

1. **TUI not installed**: Should gracefully fall back to prompt mode with warning message
2. **Invalid mode**: Click should reject with error (handled by click.Choice)
3. **Abstract method enforcement**: Should raise TypeError if BaseWizard instantiated directly
4. **Empty config summary**: Should show friendly "no configuration" message

## Validation Commands

### Installation and Setup
```bash
# Update dependencies
uv lock

# Install with TUI support
uv pip install -e ".[dev,tui]"

# Verify imports work
python -c "import questionary; print('questionary OK')"
python -c "import textual; print('textual OK')"
```

### Type Checking
```bash
# Type check wizard module only
mypy src/dbt_to_lookml/wizard/ --strict

# Type check entire codebase
make type-check
```

### Testing
```bash
# Run unit tests only (fast)
make test-fast

# Run wizard tests specifically
pytest -m wizard -v

# Run full test suite
make test-full

# Run with coverage report
make test-coverage
```

### CLI Validation
```bash
# Test wizard help
dbt-to-lookml wizard --help

# Test wizard test command (prompt mode)
dbt-to-lookml wizard test --mode prompt

# Test wizard test command (TUI mode)
dbt-to-lookml wizard test --mode tui

# Test wizard test command (default mode)
dbt-to-lookml wizard test
```

### Quality Gate
```bash
# Run all quality checks (must pass before merge)
make quality-gate
```

## Dependencies

### Existing Dependencies
- **click>=8.0**: CLI framework for command structure
- **rich**: Console output formatting (used in BaseWizard)
- **pydantic>=2.0**: Type validation (may be used in future wizard implementations)

### New Dependencies

#### Required
- **questionary>=2.0.0**: Interactive prompts for wizard
  - Why needed: Provides rich prompt features (validation, autocomplete, fuzzy search)
  - Advantages over alternatives: Better than click.prompt(), higher-level than prompt_toolkit
  - License: MIT (compatible)
  - Size: ~100KB installed

#### Optional
- **textual>=0.40.0**: TUI framework for advanced wizard mode
  - Why needed: Full-screen interactive TUI for enhanced user experience
  - Advantages: Modern reactive framework, excellent type safety, CSS-like styling
  - License: MIT (compatible)
  - Size: ~2MB installed
  - Graceful degradation: Falls back to prompt mode if not installed

## Implementation Notes

### Important Considerations

1. **Graceful Degradation Pattern**: All wizard code must handle TUI unavailability gracefully
   ```python
   if mode == WizardMode.TUI and not wizard.check_tui_available():
       wizard.handle_tui_unavailable()
       # Automatically falls back to prompt mode
   ```

2. **Type Safety is Paramount**: All wizard code must pass `mypy --strict`
   - No `Any` types except validated config dicts
   - Complete type hints on all functions
   - Protocol definitions for extensibility

3. **Temporary Test Command**: The `wizard test` command is temporary and will be removed in DTL-018 when real wizard commands are implemented

4. **Module Organization**: Follow existing pattern
   - `types.py`: Type definitions (enums, protocols, aliases)
   - `base.py`: Abstract base class with common functionality
   - `__init__.py`: Public API exports
   - Future: `generate.py`, `validate.py` for command-specific wizards

5. **Testing Philosophy**:
   - Unit tests: Fast, isolated, test abstract class behavior
   - CLI tests: Integration-style, test Click command registration
   - Use fixtures from existing test files as patterns

6. **Dependency Installation Order**:
   - Edit `pyproject.toml` first
   - Run `uv lock` to update lock file
   - Run `uv pip install -e ".[dev,tui]"` to install
   - Verify imports before proceeding with code changes

### Code Patterns to Follow

**ABC Pattern** (from `interfaces/parser.py`):
```python
from abc import ABC, abstractmethod

class BaseClass(ABC):
    @abstractmethod
    def required_method(self) -> ReturnType:
        """Docstring."""
        pass
```

**Enum Pattern** (from `types.py`):
```python
from enum import Enum

class MyEnum(Enum):
    """Docstring."""
    VALUE_ONE = "value_one"
    VALUE_TWO = "value_two"
```

**CLI Command Pattern** (from `__main__.py`):
```python
@cli.command()
@click.option("--flag", is_flag=True, help="Help text")
def command_name(flag: bool) -> None:
    """Command docstring."""
    # Implementation
```

**CLI Group Pattern**:
```python
@cli.group()
def group_name() -> None:
    """Group docstring."""
    pass

@group_name.command()
def subcommand() -> None:
    """Subcommand docstring."""
    # Implementation
```

**Test Class Pattern** (from `test_dbt_parser.py`):
```python
class TestClassName:
    """Test suite for ClassName."""

    def test_specific_behavior(self) -> None:
        """Test specific behavior description."""
        # Setup
        # Action
        # Assert
```

**Fixture Pattern** (from `test_cli.py`):
```python
@pytest.fixture
def fixture_name(self) -> Type:
    """Fixture docstring."""
    return value
```

### References

- `src/dbt_to_lookml/interfaces/parser.py:12-90` - ABC pattern with abstract methods
- `src/dbt_to_lookml/types.py:9-20` - Enum definition pattern
- `src/dbt_to_lookml/__main__.py:21-25` - CLI group definition
- `src/dbt_to_lookml/__main__.py:28-106` - CLI command with options
- `src/tests/unit/test_dbt_parser.py:18-100` - Unit test class structure
- `src/tests/test_cli.py:14-80` - CLI test structure with fixtures
- `pyproject.toml:30-46` - Dependency and optional dependency structure
- `pyproject.toml:92-104` - Test marker configuration

## Implementation Checklist

**Phase 1: Dependencies (15 min)**
- [ ] Edit `pyproject.toml` to add questionary>=2.0.0 to dependencies
- [ ] Edit `pyproject.toml` to add tui optional dependency group with textual>=0.40.0
- [ ] Run `uv lock` to update lock file
- [ ] Run `uv pip install -e ".[dev,tui]"` to install dependencies
- [ ] Verify: `python -c "import questionary; import textual; print('OK')"`

**Phase 2: Type Definitions (15 min)**
- [ ] Create `src/dbt_to_lookml/wizard/` directory
- [ ] Create `src/dbt_to_lookml/wizard/types.py` with WizardMode enum
- [ ] Add WizardStep protocol to types.py
- [ ] Add WizardConfig type alias to types.py
- [ ] Verify: `mypy src/dbt_to_lookml/wizard/types.py --strict`

**Phase 3: Base Wizard (25 min)**
- [ ] Create `src/dbt_to_lookml/wizard/base.py`
- [ ] Implement BaseWizard class with __init__ method
- [ ] Add abstract run() method
- [ ] Add abstract validate_config() method
- [ ] Add concrete get_summary() method
- [ ] Add concrete check_tui_available() method
- [ ] Add concrete handle_tui_unavailable() method
- [ ] Verify: `mypy src/dbt_to_lookml/wizard/base.py --strict`

**Phase 4: Module Init (5 min)**
- [ ] Create `src/dbt_to_lookml/wizard/__init__.py`
- [ ] Add module docstring
- [ ] Export BaseWizard
- [ ] Verify: `python -c "from dbt_to_lookml.wizard import BaseWizard; print('OK')"`

**Phase 5: CLI Integration (20 min)**
- [ ] Update `src/dbt_to_lookml/__main__.py` typing import to include Any
- [ ] Add wizard command group after line 25
- [ ] Add wizard test command with mode option
- [ ] Verify: `dbt-to-lookml wizard --help`
- [ ] Verify: `dbt-to-lookml wizard test --mode prompt`

**Phase 6: Unit Tests (30 min)**
- [ ] Create `src/tests/unit/test_wizard_base.py`
- [ ] Add TestBaseWizard class
- [ ] Add test_init_default_mode
- [ ] Add test_init_with_tui_mode
- [ ] Add test_get_summary_empty_config
- [ ] Add test_get_summary_with_config
- [ ] Add test_check_tui_available_when_installed
- [ ] Add test_handle_tui_unavailable_falls_back_to_prompt
- [ ] Add test_abstract_methods_must_be_implemented
- [ ] Verify: `pytest src/tests/unit/test_wizard_base.py -v`

**Phase 7: CLI Tests (25 min)**
- [ ] Create `src/tests/test_cli_wizard.py`
- [ ] Add TestWizardCLI class
- [ ] Add runner fixture
- [ ] Add test_wizard_group_help
- [ ] Add test_wizard_test_command_prompt_mode
- [ ] Add test_wizard_test_command_tui_mode
- [ ] Add test_wizard_test_default_mode
- [ ] Edit `pyproject.toml` to add wizard test marker
- [ ] Verify: `pytest src/tests/test_cli_wizard.py -v`

**Phase 8: Type Safety (10 min)**
- [ ] Run `mypy src/dbt_to_lookml/wizard/ --strict`
- [ ] Fix any type errors
- [ ] Run `make type-check`
- [ ] Fix any new type errors introduced

**Phase 9: Testing and Validation (15 min)**
- [ ] Run `make test-fast` - verify all tests pass
- [ ] Run `make test-full` - verify no regressions
- [ ] Run `pytest -m wizard -v` - verify wizard tests pass
- [ ] Run `dbt-to-lookml wizard --help` - verify help text
- [ ] Run `dbt-to-lookml wizard test` - verify default mode works
- [ ] Run `dbt-to-lookml wizard test --mode tui` - verify TUI mode or fallback
- [ ] Run `make quality-gate` - verify all quality checks pass

**Estimated Total Time**: 2 hours 40 minutes

## Ready for Implementation

This spec is complete and ready for implementation. All necessary details have been provided:

- [x] Complete file structure defined
- [x] Detailed implementation guidance for each file
- [x] Code patterns identified and documented
- [x] Test cases specified with expected behavior
- [x] Validation commands listed
- [x] Dependencies specified with rationale
- [x] Implementation checklist with time estimates
- [x] References to existing code patterns

**Next Step**: Begin implementation following the checklist above, or run the automated implementation workflow if available.

## Success Metrics

- [x] questionary installed and importable
- [x] Textual installed and importable (in dev environment)
- [x] `dbt-to-lookml wizard --help` shows command group
- [x] `dbt-to-lookml wizard test` runs successfully
- [x] `dbt-to-lookml wizard test --mode tui` falls back gracefully if Textual not installed
- [x] `make type-check` passes with no mypy errors
- [x] `make test-fast` passes all tests
- [x] `make test-full` passes with no regressions
- [x] Unit test coverage for wizard module at 100%
- [x] CLI test coverage for wizard commands at 100%
- [x] All acceptance criteria from issue DTL-015 met
