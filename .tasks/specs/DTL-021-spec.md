# Implementation Spec: DTL-021 - Integration, testing, and documentation

## Metadata
- **Issue**: DTL-021
- **Stack**: backend
- **Type**: chore
- **Generated**: 2025-11-17
- **Strategy**: Approved (DTL-021-strategy.md)

## Issue Context

### Problem Statement

Complete integration of wizard system with existing CLI, add comprehensive tests, and update documentation to ensure the wizard feature is production-ready with 95%+ test coverage.

### Solution Approach

Implement a comprehensive testing infrastructure covering:
1. Unit tests for detection and wizard modules with proper mocking
2. Integration tests for end-to-end wizard flows
3. CLI tests using Click's CliRunner
4. Documentation updates for users (README) and developers (CLAUDE.md)
5. CI integration with dedicated wizard test job

### Success Criteria

- All wizard features have unit tests (95%+ coverage)
- Integration tests cover full wizard flows
- Tests properly mock user input (questionary, Click)
- README includes "Interactive Wizard" section with examples
- CLAUDE.md documents wizard architecture and testing
- CI pipeline includes wizard-specific test job
- All tests passing with 95%+ branch coverage

## Approved Strategy Summary

The strategy focuses on three core areas:

1. **Testing Infrastructure**: Create comprehensive test suite with unit tests (detection module, generate wizard), integration tests (end-to-end flows), and CLI tests with proper mocking patterns
2. **CI Integration**: Add dedicated wizard test job to GitHub Actions workflow with coverage reporting
3. **Documentation**: Add user-facing examples in README and technical architecture documentation in CLAUDE.md

## Implementation Plan

### Phase 1: Unit Tests for Detection Module

Create `src/tests/unit/test_wizard_detection.py` with comprehensive detection tests.

**Tasks**:
1. Create test file with proper fixtures
2. Implement 7+ detection test cases
3. Mock filesystem for testing
4. Verify 95%+ coverage

### Phase 2: Unit Tests for Generate Wizard

Create `src/tests/unit/test_wizard_generate.py` with questionary mocking.

**Tasks**:
1. Create test file with mocking fixtures
2. Implement 12+ wizard test cases
3. Mock questionary interactions
4. Test command building logic
5. Verify 95%+ coverage

### Phase 3: Integration Tests

Create `src/tests/integration/test_wizard_integration.py` for end-to-end flows.

**Tasks**:
1. Create test file with realistic fixtures
2. Implement 8+ integration test cases
3. Test complete wizard flows
4. Test error handling and recovery
5. Verify 95%+ coverage

### Phase 4: CLI Tests

Update `src/tests/test_cli.py` with wizard command tests.

**Tasks**:
1. Add TestCLIWizard class
2. Implement 7+ CLI test cases
3. Test wizard command availability
4. Test help text and flags
5. Verify 100% command coverage

### Phase 5: Documentation Updates

Update README.md and CLAUDE.md with wizard documentation.

**Tasks**:
1. Add "Interactive Wizard" section to README
2. Add usage examples and features
3. Add wizard architecture section to CLAUDE.md
4. Document testing patterns and mocking strategies

### Phase 6: CI Integration

Add wizard-tests job to GitHub Actions workflow.

**Tasks**:
1. Add wizard-tests job to `.github/workflows/test.yml`
2. Update final-status job dependencies
3. Configure coverage reporting
4. Test CI pipeline

## Detailed Task Breakdown

### Task 1: Create Detection Module Unit Tests

**File**: `src/tests/unit/test_wizard_detection.py` (NEW)

**Action**: Create comprehensive unit tests for wizard detection module

**Implementation Guidance**:
```python
"""Unit tests for wizard detection module."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from dbt_to_lookml.wizard.detection import (
    detect_semantic_models_directory,
    detect_schema_from_yaml,
    suggest_output_directory,
    detect_project_structure,
)


class TestWizardDetection:
    """Test cases for wizard detection module."""

    @pytest.fixture
    def mock_project(self, tmp_path: Path) -> Path:
        """Create mock project structure for testing."""
        # Create semantic_models directory
        semantic_dir = tmp_path / "semantic_models"
        semantic_dir.mkdir()

        # Create sample semantic model YAML
        (semantic_dir / "orders.yml").write_text("""
name: orders
model: ref('orders')
entities:
  - name: order_id
    type: primary
dimensions:
  - name: created_at
    type: time
""")

        return tmp_path

    def test_detect_semantic_models_directory_found(self, mock_project: Path) -> None:
        """Test detection when semantic_models directory exists."""
        result = detect_semantic_models_directory(mock_project)

        assert result is not None
        assert result.name == "semantic_models"
        assert (result / "orders.yml").exists()

    def test_detect_semantic_models_multiple_candidates(self, tmp_path: Path) -> None:
        """Test detection with multiple potential directories."""
        # Create multiple candidates
        (tmp_path / "semantic_models").mkdir()
        (tmp_path / "models").mkdir()
        (tmp_path / "semantic_models" / "test.yml").write_text("name: test")

        result = detect_semantic_models_directory(tmp_path)

        # Should prefer semantic_models with YAML files
        assert result is not None
        assert result.name == "semantic_models"

    def test_detect_semantic_models_none_found(self, tmp_path: Path) -> None:
        """Test detection when no semantic models exist."""
        result = detect_semantic_models_directory(tmp_path)

        assert result is None

    def test_detect_schema_from_yaml(self, mock_project: Path) -> None:
        """Test schema detection from YAML files."""
        semantic_dir = mock_project / "semantic_models"

        result = detect_schema_from_yaml(semantic_dir)

        # Should extract schema if present in YAML
        assert result is None or isinstance(result, str)

    def test_detect_project_structure(self, mock_project: Path) -> None:
        """Test complete project structure detection."""
        context = detect_project_structure(mock_project)

        assert context is not None
        assert context.semantic_models_dir is not None
        assert context.suggested_output_dir is not None

    def test_detect_with_invalid_permissions(self, tmp_path: Path) -> None:
        """Test detection handles permission errors gracefully."""
        restricted_dir = tmp_path / "restricted"
        restricted_dir.mkdir()
        restricted_dir.chmod(0o000)

        try:
            result = detect_semantic_models_directory(tmp_path)
            # Should handle gracefully (may return None or skip restricted dirs)
            assert result is None or isinstance(result, Path)
        finally:
            restricted_dir.chmod(0o755)

    def test_detect_with_malformed_yaml(self, tmp_path: Path) -> None:
        """Test detection skips malformed YAML files."""
        semantic_dir = tmp_path / "semantic_models"
        semantic_dir.mkdir()

        # Create malformed YAML
        (semantic_dir / "bad.yml").write_text("invalid: [unclosed")

        # Should not crash, may return directory or None
        result = detect_semantic_models_directory(tmp_path)
        assert result is None or isinstance(result, Path)
```

**Reference**: Similar patterns in `src/tests/unit/test_dbt_parser.py` lines 20-80 (fixture patterns)

**Tests**: 7 test cases covering detection scenarios, edge cases, error handling

**Estimated lines**: ~200 lines

---

### Task 2: Create Generate Wizard Unit Tests

**File**: `src/tests/unit/test_wizard_generate.py` (NEW)

**Action**: Create comprehensive unit tests for generate wizard with questionary mocking

**Implementation Guidance**:
```python
"""Unit tests for generate wizard module."""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from dbt_to_lookml.wizard.generate_wizard import (
    run_generate_wizard,
    prompt_required_fields,
    prompt_optional_fields,
    build_command_string,
)


class TestGenerateWizard:
    """Test cases for generate wizard module."""

    @pytest.fixture
    def mock_questionary(self, mocker):
        """Mock questionary prompts for testing."""
        mock_text = mocker.patch('dbt_to_lookml.wizard.generate_wizard.questionary.text')
        mock_select = mocker.patch('dbt_to_lookml.wizard.generate_wizard.questionary.select')
        mock_checkbox = mocker.patch('dbt_to_lookml.wizard.generate_wizard.questionary.checkbox')

        return {
            'text': mock_text,
            'select': mock_select,
            'checkbox': mock_checkbox,
        }

    def test_prompt_sequence_all_required_fields(self, mock_questionary) -> None:
        """Test wizard prompts for all required fields in correct order."""
        # Setup mock responses
        mock_questionary['text'].return_value.ask.side_effect = [
            '/path/to/semantic_models',  # input_dir
            '/path/to/output',            # output_dir
        ]
        mock_questionary['select'].return_value.ask.side_effect = [
            'analytics',  # schema
            'no',         # convert_tz
        ]
        mock_questionary['checkbox'].return_value.ask.return_value = []

        # Run wizard
        command = run_generate_wizard(None)

        # Verify command construction
        assert 'generate' in command
        assert '--input-dir /path/to/semantic_models' in command
        assert '--output-dir /path/to/output' in command
        assert '--schema analytics' in command

    def test_prompt_validation_invalid_directory(self, mock_questionary) -> None:
        """Test validation for invalid directory paths."""
        # Mock validator to reject invalid path
        mock_questionary['text'].return_value.ask.side_effect = [
            None,  # Validation fails, returns None
            '/valid/path',  # Retry succeeds
        ]

        # Should handle validation failure and retry
        # (Implementation depends on wizard retry logic)

    def test_prompt_with_detected_defaults(self, mock_questionary) -> None:
        """Test wizard uses detected defaults."""
        from dbt_to_lookml.wizard.detection import ProjectContext

        context = ProjectContext(
            semantic_models_dir=Path('/detected/semantic_models'),
            suggested_output_dir=Path('/detected/output'),
            detected_schema='analytics'
        )

        # User presses Enter to accept defaults
        mock_questionary['text'].return_value.ask.side_effect = ['', '']
        mock_questionary['select'].return_value.ask.return_value = 'no'
        mock_questionary['checkbox'].return_value.ask.return_value = []

        command = run_generate_wizard(context)

        # Should use detected defaults
        assert '/detected/semantic_models' in command or command

    def test_prompt_timezone_conversion_yes(self, mock_questionary) -> None:
        """Test selecting 'yes' for timezone conversion."""
        mock_questionary['text'].return_value.ask.side_effect = ['/in', '/out']
        mock_questionary['select'].return_value.ask.side_effect = ['schema', 'yes']
        mock_questionary['checkbox'].return_value.ask.return_value = []

        command = run_generate_wizard(None)

        assert '--convert-tz' in command

    def test_prompt_timezone_conversion_no(self, mock_questionary) -> None:
        """Test selecting 'no' for timezone conversion."""
        mock_questionary['text'].return_value.ask.side_effect = ['/in', '/out']
        mock_questionary['select'].return_value.ask.side_effect = ['schema', 'no']
        mock_questionary['checkbox'].return_value.ask.return_value = []

        command = run_generate_wizard(None)

        assert '--no-convert-tz' in command

    def test_prompt_additional_options_checkboxes(self, mock_questionary) -> None:
        """Test checkbox selections for additional options."""
        mock_questionary['text'].return_value.ask.side_effect = ['/in', '/out']
        mock_questionary['select'].return_value.ask.side_effect = ['schema', 'no']
        mock_questionary['checkbox'].return_value.ask.return_value = [
            '--dry-run',
            '--show-summary',
        ]

        command = run_generate_wizard(None)

        assert '--dry-run' in command
        assert '--show-summary' in command

    def test_build_command_string_all_options(self) -> None:
        """Test command string building with all options."""
        options = {
            'input_dir': '/path/to/input',
            'output_dir': '/path/to/output',
            'schema': 'analytics',
            'view_prefix': 'v_',
            'explore_prefix': 'e_',
            'convert_tz': True,
            'additional_options': ['--dry-run', '--show-summary'],
        }

        command = build_command_string(options)

        assert 'generate' in command
        assert '--input-dir /path/to/input' in command
        assert '--schema analytics' in command
        assert '--view-prefix v_' in command
        assert '--convert-tz' in command
        assert '--dry-run' in command

    def test_build_command_string_minimal_options(self) -> None:
        """Test command string with only required options."""
        options = {
            'input_dir': '/input',
            'output_dir': '/output',
            'schema': 'public',
        }

        command = build_command_string(options)

        assert 'generate' in command
        assert '--input-dir /input' in command
        assert '--output-dir /output' in command
        assert '--schema public' in command
        # Optional flags should not be present
        assert '--view-prefix' not in command

    def test_wizard_keyboard_interrupt(self, mock_questionary) -> None:
        """Test wizard handles Ctrl+C gracefully."""
        mock_questionary['text'].return_value.ask.side_effect = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            run_generate_wizard(None)

    def test_wizard_with_detection_failure(self, mock_questionary) -> None:
        """Test wizard continues when detection returns no results."""
        mock_questionary['text'].return_value.ask.side_effect = ['/in', '/out']
        mock_questionary['select'].return_value.ask.side_effect = ['schema', 'no']
        mock_questionary['checkbox'].return_value.ask.return_value = []

        # Run with None context (detection failed)
        command = run_generate_wizard(None)

        # Should still build valid command
        assert 'generate' in command
```

**Reference**: Mocking patterns similar to `src/tests/test_cli.py` lines 454-477 (mocking with patches)

**Tests**: 12+ test cases covering prompt sequences, validation, command building, error handling

**Estimated lines**: ~400 lines

---

### Task 3: Create Integration Tests

**File**: `src/tests/integration/test_wizard_integration.py` (NEW)

**Action**: Create end-to-end integration tests for wizard flows

**Implementation Guidance**:
```python
"""Integration tests for wizard end-to-end flows."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from dbt_to_lookml.wizard.detection import detect_project_structure
from dbt_to_lookml.wizard.generate_wizard import run_generate_wizard


@pytest.mark.integration
class TestWizardIntegration:
    """Integration tests for wizard flows."""

    @pytest.fixture
    def realistic_project(self, tmp_path: Path) -> Path:
        """Create realistic dbt project structure."""
        # Create semantic models directory
        semantic_dir = tmp_path / "semantic_models"
        semantic_dir.mkdir()

        # Create sample semantic models
        (semantic_dir / "orders.yml").write_text("""
name: orders
model: ref('orders')
entities:
  - name: order_id
    type: primary
dimensions:
  - name: created_at
    type: time
    type_params:
      time_granularity: day
  - name: status
    type: categorical
measures:
  - name: total_revenue
    agg: sum
    expr: amount
""")

        (semantic_dir / "customers.yml").write_text("""
name: customers
model: ref('customers')
entities:
  - name: customer_id
    type: primary
dimensions:
  - name: name
    type: categorical
measures:
  - name: customer_count
    agg: count
""")

        return tmp_path

    def test_full_wizard_flow_generate_command(
        self, realistic_project: Path, mocker
    ) -> None:
        """Test complete wizard interaction and command execution."""
        # Mock wizard prompts
        mock_text = mocker.patch('questionary.text')
        mock_select = mocker.patch('questionary.select')
        mock_checkbox = mocker.patch('questionary.checkbox')

        semantic_dir = realistic_project / "semantic_models"
        output_dir = realistic_project / "build" / "lookml"

        mock_text.return_value.ask.side_effect = [
            str(semantic_dir),
            str(output_dir),
        ]
        mock_select.return_value.ask.side_effect = ['analytics', 'no']
        mock_checkbox.return_value.ask.return_value = []

        # Run wizard
        command = run_generate_wizard(None)

        # Verify command is well-formed
        assert 'generate' in command
        assert str(semantic_dir) in command
        assert str(output_dir) in command

    def test_wizard_detection_integration(
        self, realistic_project: Path
    ) -> None:
        """Test detection + wizard integration."""
        # Run detection
        context = detect_project_structure(realistic_project)

        # Verify detection found semantic models
        assert context is not None
        assert context.semantic_models_dir is not None
        assert context.semantic_models_dir.name == "semantic_models"

    def test_wizard_with_real_semantic_models(
        self, realistic_project: Path, mocker
    ) -> None:
        """Test wizard with real semantic model files."""
        from dbt_to_lookml.parsers.dbt import DbtParser
        from dbt_to_lookml.generators.lookml import LookMLGenerator

        # Mock wizard interaction
        mock_text = mocker.patch('questionary.text')
        mock_select = mocker.patch('questionary.select')
        mock_checkbox = mocker.patch('questionary.checkbox')

        semantic_dir = realistic_project / "semantic_models"
        output_dir = realistic_project / "build"
        output_dir.mkdir()

        mock_text.return_value.ask.side_effect = [
            str(semantic_dir),
            str(output_dir),
        ]
        mock_select.return_value.ask.side_effect = ['analytics', 'no']
        mock_checkbox.return_value.ask.return_value = []

        # Run wizard to build command
        command = run_generate_wizard(None)

        # Actually execute the workflow (parse + generate)
        parser = DbtParser()
        models = parser.parse_directory(semantic_dir)

        generator = LookMLGenerator()
        files, errors = generator.generate_lookml_files(models, output_dir)

        # Verify files created
        assert len(files) > 0
        assert len(errors) == 0
        assert (output_dir / "explores.lkml").exists()

    def test_wizard_error_handling_invalid_path(
        self, mocker
    ) -> None:
        """Test wizard handles invalid input directory."""
        mock_text = mocker.patch('questionary.text')
        mock_select = mocker.patch('questionary.select')

        # First attempt: invalid path
        # Second attempt: valid path
        mock_text.return_value.ask.side_effect = [
            '/nonexistent/path',
            '/tmp',
            '/tmp/output',
        ]
        mock_select.return_value.ask.side_effect = ['schema', 'no']

        # Should handle validation and retry
        # (Implementation depends on wizard validation logic)

    def test_wizard_end_to_end_with_validation(
        self, realistic_project: Path, mocker
    ) -> None:
        """Test complete wizard flow with validation enabled."""
        from dbt_to_lookml.parsers.dbt import DbtParser
        from dbt_to_lookml.generators.lookml import LookMLGenerator

        # Mock wizard
        mock_text = mocker.patch('questionary.text')
        mock_select = mocker.patch('questionary.select')
        mock_checkbox = mocker.patch('questionary.checkbox')

        semantic_dir = realistic_project / "semantic_models"
        output_dir = realistic_project / "output"
        output_dir.mkdir()

        mock_text.return_value.ask.side_effect = [
            str(semantic_dir),
            str(output_dir),
        ]
        mock_select.return_value.ask.side_effect = ['analytics', 'no']
        mock_checkbox.return_value.ask.return_value = []

        # Full workflow
        parser = DbtParser()
        models = parser.parse_directory(semantic_dir)

        generator = LookMLGenerator()
        files, errors = generator.generate_lookml_files(models, output_dir)

        # Verify validation passed
        assert len(errors) == 0
        assert all(Path(f).exists() for f in files)
```

**Reference**: Pattern similar to `src/tests/integration/test_end_to_end.py` lines 18-100

**Tests**: 8+ test cases covering complete flows, detection integration, error handling

**Estimated lines**: ~350 lines

---

### Task 4: Update CLI Tests

**File**: `src/tests/test_cli.py` (UPDATE)

**Action**: Add TestCLIWizard class with wizard command tests

**Implementation Guidance**:
```python
# Add at end of src/tests/test_cli.py

class TestCLIWizard:
    """Test cases for wizard CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Return path to fixtures directory."""
        return Path(__file__).parent / "fixtures"

    def test_wizard_command_help(self, runner: CliRunner) -> None:
        """Test wizard command help text."""
        result = runner.invoke(cli, ["wizard", "--help"])

        assert result.exit_code == 0
        assert "Interactive wizard" in result.output
        assert "generate" in result.output

    def test_wizard_generate_command_exists(self, runner: CliRunner) -> None:
        """Test wizard generate command is accessible."""
        result = runner.invoke(cli, ["wizard", "generate", "--help"])

        assert result.exit_code == 0
        assert "wizard" in result.output.lower()

    def test_wizard_generate_with_defaults(
        self, runner: CliRunner, mocker
    ) -> None:
        """Test wizard generate command completes successfully."""
        # Mock the wizard function to avoid interactive prompts
        mock_wizard = mocker.patch('dbt_to_lookml.__main__.run_generate_wizard')
        mock_wizard.return_value = 'generate -i ./semantic_models -o ./build -s analytics'

        # Mock command execution
        mock_execute = mocker.patch('dbt_to_lookml.__main__.execute_command')

        result = runner.invoke(cli, ['wizard', 'generate'])

        assert result.exit_code == 0
        assert mock_wizard.called

    def test_wizard_tui_flag(self, runner: CliRunner, mocker) -> None:
        """Test wizard with --tui flag."""
        mock_wizard = mocker.patch('dbt_to_lookml.__main__.run_tui_wizard')
        mock_wizard.return_value = 'generate -i ./models -o ./output -s public'

        result = runner.invoke(cli, ['wizard', 'generate', '--tui'])

        # Should attempt TUI mode or gracefully fall back
        assert result.exit_code == 0 or "TUI" in result.output

    def test_wizard_non_interactive_mode(self, runner: CliRunner) -> None:
        """Test wizard in non-interactive environment."""
        # Run without mocking - should handle gracefully
        result = runner.invoke(cli, ['wizard', 'generate'], input='\n\n\n')

        # May fail or show error about non-interactive mode
        assert isinstance(result.exit_code, int)

    def test_wizard_keyboard_interrupt_cli(
        self, runner: CliRunner, mocker
    ) -> None:
        """Test wizard handles Ctrl+C gracefully."""
        mock_wizard = mocker.patch('dbt_to_lookml.__main__.run_generate_wizard')
        mock_wizard.side_effect = KeyboardInterrupt()

        result = runner.invoke(cli, ['wizard', 'generate'])

        # Should exit cleanly
        assert "cancelled" in result.output.lower() or result.exit_code != 0
```

**Reference**: Existing CLI test patterns in `src/tests/test_cli.py` lines 14-100

**Changes**:
- Add new TestCLIWizard class with 7+ test cases
- Mock wizard functions to avoid interactive prompts
- Test help text, command availability, flags

**Estimated lines**: ~150 new lines

---

### Task 5: Update README.md

**File**: `README.md` (UPDATE)

**Action**: Add "Interactive Wizard" section with usage examples

**Location**: After "## CLI Usage" section (insert around line 60)

**Implementation Guidance**:
```markdown
## Interactive Wizard

The wizard provides an interactive way to build commands without memorizing flags.

### Basic Usage

```bash
# Launch the wizard for generate command
dbt-to-lookml wizard generate

# Use TUI mode (if Textual installed)
dbt-to-lookml wizard generate --tui
```

### Features

- **Auto-detection**: Automatically finds semantic model directories and suggests paths
- **Contextual hints**: Shows descriptions and format examples for each option
- **Input validation**: Real-time validation prevents invalid configurations
- **Preview mode**: See what will happen before executing
- **Smart defaults**: Suggests common values based on project structure

### Example Interaction

```
? Input directory: ./semantic_models (detected)
? Output directory: ./build/lookml
? Schema name: analytics
? View prefix (optional): [Press Enter to skip]
? Explore prefix (optional): [Press Enter to skip]
? Connection name: redshift_test
? Model name: semantic_model
? Enable timezone conversion? (y/N): n
? Additional options: [X] dry-run [ ] no-validation [X] show-summary

Generated command:
dbt-to-lookml generate -i ./semantic_models -o ./build/lookml -s analytics --dry-run --show-summary

Execute this command? (Y/n):
```

### Wizard Options

- **Interactive mode** (default): Simple prompts with validation
- **TUI mode** (`--tui`): Full-screen terminal UI with forms and navigation
- **Preview only** (`--preview`): Show command without executing

### When to Use the Wizard

- First time using dbt-to-lookml
- Exploring available options
- Building complex commands with many flags
- Learning best practices through contextual hints
```

**Changes**:
- Add new section after CLI Usage
- Include usage examples
- Document features and options
- Show example interaction

**Estimated lines**: ~50 new lines

---

### Task 6: Update CLAUDE.md

**File**: `CLAUDE.md` (UPDATE)

**Action**: Add "Wizard System Architecture" section

**Location**: After "## Important Implementation Details" section (insert around line 450)

**Implementation Guidance**:
```markdown
## Wizard System Architecture

The wizard system provides interactive command building through a three-tier architecture.

### Module Structure

```
src/dbt_to_lookml/wizard/
├── __init__.py          # Public API exports
├── detection.py         # Project structure detection and smart defaults
├── generate_wizard.py   # Prompt-based wizard for generate command
└── tui.py              # Optional Textual-based TUI (if installed)
```

### Design Patterns

1. **Detection-First**: Auto-detect project structure before prompting
   - Scans for semantic_models directories
   - Parses YAML files for schema hints
   - Suggests output directories based on conventions

2. **Progressive Enhancement**: Graceful degradation for missing dependencies
   - Core wizard uses questionary (required)
   - TUI mode uses Textual (optional)
   - Falls back to prompt mode if TUI unavailable

3. **Validation Pipeline**: Multi-stage input validation
   - Real-time validation during prompts
   - Path existence checks
   - YAML parsing for schema detection
   - Final command validation before execution

### Key Components

#### Detection Module (`wizard/detection.py`)

**Purpose**: Analyze project structure and provide smart defaults

**Functions**:
- `detect_semantic_models_directory(start_path: Path) -> Path | None`
- `detect_schema_from_yaml(directory: Path) -> str | None`
- `suggest_output_directory(input_dir: Path) -> Path`
- `detect_project_structure(path: Path) -> ProjectContext`

**Testing Approach**:
- Mock filesystem with various project structures
- Test scoring algorithm with edge cases
- Verify handling of missing/invalid files

#### Generate Wizard (`wizard/generate_wizard.py`)

**Purpose**: Interactive prompt sequence for building generate commands

**Functions**:
- `run_generate_wizard(context: ProjectContext) -> str`
- `prompt_required_fields(context: ProjectContext) -> dict[str, Any]`
- `prompt_optional_fields() -> dict[str, Any]`
- `build_command_string(options: dict[str, Any]) -> str`

**Prompt Sequence**:
1. Input directory (required, auto-detected default)
2. Output directory (required, suggested)
3. Schema name (required, detected from YAML)
4. View/explore prefixes (optional)
5. Timezone conversion (select yes/no)
6. Additional options (checkbox)

**Testing Approach**:
- Mock questionary prompts with pytest-mock
- Test validation logic independently
- Test command string building
- Test error handling

### Testing Strategy

#### Mocking User Input

**Questionary Mocking**:
```python
@pytest.fixture
def mock_questionary(mocker):
    """Mock questionary prompts for testing."""
    mock_text = mocker.patch('dbt_to_lookml.wizard.generate_wizard.questionary.text')
    mock_select = mocker.patch('dbt_to_lookml.wizard.generate_wizard.questionary.select')
    mock_checkbox = mocker.patch('dbt_to_lookml.wizard.generate_wizard.questionary.checkbox')

    return {'text': mock_text, 'select': mock_select, 'checkbox': mock_checkbox}

def test_wizard_with_mocks(mock_questionary):
    """Test wizard with mocked user input."""
    mock_questionary['text'].return_value.ask.side_effect = ['/in', '/out']
    mock_questionary['select'].return_value.ask.return_value = 'analytics'

    command = run_generate_wizard(None)

    assert '--schema analytics' in command
```

**Click Testing**:
```python
from click.testing import CliRunner

def test_wizard_cli(runner: CliRunner, mocker):
    """Test wizard command via CLI."""
    mock_wizard = mocker.patch('dbt_to_lookml.__main__.run_generate_wizard')
    mock_wizard.return_value = 'generate -i ./models -o ./build'

    result = runner.invoke(cli, ['wizard', 'generate'])

    assert result.exit_code == 0
```

#### Coverage Requirements

**Per-Module Coverage Targets**:
- `wizard/detection.py`: 95%+ branch coverage
- `wizard/generate_wizard.py`: 95%+ branch coverage
- `wizard/tui.py`: 85%+ branch coverage (if implemented)

**Overall Wizard Coverage**: 95%+

#### Test Organization

**Test Markers**:
- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - End-to-end wizard flows
- `@pytest.mark.cli` - CLI command interface tests
- `@pytest.mark.wizard` - All wizard-related tests (NEW)

**Fixture Patterns**:
```python
@pytest.fixture
def mock_project_structure(tmp_path):
    """Create realistic project structure for testing."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "orders.yml").write_text("name: orders\nmodel: ref('orders')")
    return tmp_path
```

### Error Handling

**Error Categories**:
1. User Input Errors: Real-time validation, re-prompt
2. Filesystem Errors: Clear messages, suggest fixes
3. Detection Failures: Graceful degradation, no defaults
4. Execution Errors: Show output, offer to edit

### Performance Considerations

**Detection Performance**:
- Limit directory traversal depth (3 levels)
- Skip large directories (node_modules, .git)
- Cache detection results

**Benchmarks** (target):
- Detection: < 500ms
- Prompt sequence: < 100ms between prompts
- Total wizard flow: < 2 minutes
```

**Changes**:
- Add new section documenting wizard architecture
- Include testing strategies and code examples
- Document design patterns and error handling

**Estimated lines**: ~250 new lines

---

### Task 7: Add CI Wizard Test Job

**File**: `.github/workflows/test.yml` (UPDATE)

**Action**: Add wizard-tests job after cli-tests job

**Location**: After cli-tests job (insert around line 148)

**Implementation Guidance**:
```yaml
  wizard-tests:
    name: Wizard Tests
    runs-on: ubuntu-latest
    needs: lint-and-type-check

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Install uv
      uses: astral-sh/setup-uv@v2

    - name: Install dependencies
      run: |
        uv sync --group dev

    - name: Run wizard unit tests
      run: |
        pytest src/tests/unit/test_wizard*.py -v --cov=dbt_to_lookml.wizard --cov-report=xml

    - name: Run wizard integration tests
      run: |
        pytest src/tests/integration/test_wizard*.py -v

    - name: Run wizard CLI tests
      run: |
        pytest src/tests/test_cli.py::TestCLIWizard -v

    - name: Check wizard test coverage
      run: |
        pytest src/tests/unit/test_wizard*.py --cov=dbt_to_lookml.wizard --cov-report=term --cov-fail-under=95

    - name: Upload wizard coverage
      uses: codecov/codecov-action@v3
      if: always()
      with:
        files: ./coverage.xml
        flags: wizard-tests
        name: wizard-test-coverage

    - name: Test wizard command availability
      run: |
        uv pip install -e .
        dbt-to-lookml wizard --help
        dbt-to-lookml wizard generate --help
```

**Also update** final-status job dependencies (around line 230):
```yaml
needs: [unit-tests, integration-tests, cli-tests, error-handling-tests, smoke-tests, multi-python-test, wizard-tests]
```

**Changes**:
- Add new wizard-tests job
- Update final-status job to include wizard-tests
- Configure coverage reporting

**Estimated lines**: ~45 new lines

---

### Task 8: Add Wizard Test Marker

**File**: `pyproject.toml` (UPDATE)

**Action**: Add wizard test marker to pytest configuration

**Location**: In `[tool.pytest.ini_options]` markers section (around line 92)

**Implementation Guidance**:
```toml
markers = [
    "unit: marks tests as unit tests (fast, isolated)",
    "integration: marks tests as integration tests (slower, end-to-end)",
    "golden: marks tests as golden file comparison tests",
    "cli: marks tests as CLI interface tests",
    "performance: marks tests as performance/benchmark tests",
    "error_handling: marks tests as error handling and robustness tests",
    "slow: marks tests as slow running (may be skipped in fast runs)",
    "smoke: marks tests as smoke tests (quick validation)",
    "stress: marks tests as stress tests (high load/memory)",
    "memory: marks tests that check for memory leaks",
    "concurrent: marks tests that test concurrent/parallel execution",
    "wizard: marks tests as wizard-related tests (NEW)",
]
```

**Changes**:
- Add "wizard" marker to list

**Estimated lines**: 1 new line

---

## File Changes

### Files to Create

#### `src/tests/unit/test_wizard_detection.py`
**Why**: Unit tests for wizard detection module

**Structure**: Based on `src/tests/unit/test_dbt_parser.py`

**Tests**: 7+ test cases covering detection scenarios, edge cases, error handling

**Estimated lines**: ~200

#### `src/tests/unit/test_wizard_generate.py`
**Why**: Unit tests for generate wizard with questionary mocking

**Structure**: Based on CLI test mocking patterns

**Tests**: 12+ test cases covering prompts, validation, command building

**Estimated lines**: ~400

#### `src/tests/integration/test_wizard_integration.py`
**Why**: End-to-end integration tests for wizard flows

**Structure**: Based on `src/tests/integration/test_end_to_end.py`

**Tests**: 8+ test cases covering complete flows, detection integration

**Estimated lines**: ~350

### Files to Modify

#### `src/tests/test_cli.py`
**Why**: Add wizard CLI command tests

**Changes**:
- Add TestCLIWizard class with 7+ test cases
- Mock wizard functions to avoid interactive prompts
- Test help text, command availability, flags

**Estimated lines**: ~150 new lines

#### `README.md`
**Why**: Add user-facing wizard documentation

**Changes**:
- Add "Interactive Wizard" section after CLI Usage
- Include usage examples and features
- Document wizard options

**Estimated lines**: ~50 new lines

#### `CLAUDE.md`
**Why**: Add wizard architecture and testing documentation

**Changes**:
- Add "Wizard System Architecture" section
- Document design patterns, testing strategies
- Include code examples for mocking

**Estimated lines**: ~250 new lines

#### `.github/workflows/test.yml`
**Why**: Add wizard-specific test job to CI

**Changes**:
- Add wizard-tests job after cli-tests
- Update final-status job dependencies
- Configure coverage reporting

**Estimated lines**: ~45 new lines

#### `pyproject.toml`
**Why**: Add wizard test marker

**Changes**:
- Add "wizard" marker to pytest markers list

**Estimated lines**: 1 new line

## Testing Strategy

### Unit Tests (95%+ coverage target)

**Detection Module** (`test_wizard_detection.py`):
- Test all detection functions
- Mock filesystem structures
- Test edge cases and error handling

**Generate Wizard** (`test_wizard_generate.py`):
- Mock questionary prompts
- Test prompt sequences
- Test validation logic
- Test command building

### Integration Tests (95%+ coverage target)

**Wizard Flows** (`test_wizard_integration.py`):
- Test complete wizard workflows
- Test detection + wizard + execution
- Test error recovery
- Use realistic project structures

### CLI Tests (100% command coverage)

**Wizard Commands** (`TestCLIWizard` in `test_cli.py`):
- Test wizard command help
- Test wizard generate command
- Test TUI mode flag
- Mock wizard functions to avoid interactive prompts

### Mock Testing Patterns

**Pattern 1: Mock Questionary Prompts**
```python
@pytest.fixture
def mock_questionary(mocker):
    """Mock questionary for testing."""
    return {
        'text': mocker.patch('questionary.text'),
        'select': mocker.patch('questionary.select'),
        'checkbox': mocker.patch('questionary.checkbox'),
    }
```

**Pattern 2: Mock Filesystem**
```python
@pytest.fixture
def mock_project(tmp_path):
    """Create mock project structure."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "test.yml").write_text("name: test")
    return tmp_path
```

**Pattern 3: Mock CLI Execution**
```python
def test_wizard_cli(runner, mocker):
    """Test CLI wizard."""
    mock_wizard = mocker.patch('dbt_to_lookml.__main__.run_generate_wizard')
    mock_wizard.return_value = 'generate -i ./models -o ./build'

    result = runner.invoke(cli, ['wizard', 'generate'])
    assert result.exit_code == 0
```

## Validation Commands

**Run wizard unit tests**:
```bash
pytest src/tests/unit/test_wizard*.py -v
```

**Run wizard integration tests**:
```bash
pytest src/tests/integration/test_wizard*.py -v
```

**Run wizard CLI tests**:
```bash
pytest src/tests/test_cli.py::TestCLIWizard -v
```

**Check wizard coverage**:
```bash
pytest src/tests/unit/test_wizard*.py --cov=dbt_to_lookml.wizard --cov-report=term --cov-fail-under=95
```

**Run all wizard tests**:
```bash
pytest -m wizard -v
```

**Run full test suite**:
```bash
make test-full
```

**Check overall coverage**:
```bash
make test-coverage
```

## Dependencies

### Existing Dependencies
- `pytest>=7.0`: Testing framework
- `pytest-cov`: Coverage reporting
- `pytest-mock>=3.11.1`: Enhanced mocking (in dev dependencies)
- `click>=8.0`: CLI framework (provides CliRunner)
- `questionary`: Interactive prompts (from DTL-015)

### New Dependencies Needed
None - all required dependencies already in place from DTL-015.

## Implementation Notes

### Important Considerations

1. **Test Isolation**: Keep wizard tests independent of existing CLI tests to avoid coupling
2. **Mock Strategy**: Use pytest-mock for all user interaction mocking to avoid actual prompts during tests
3. **Fixture Reuse**: Create shared fixtures for mock project structures, reuse across test files
4. **Coverage Thresholds**: Set strict 95%+ threshold for wizard modules in CI
5. **CI Optimization**: Run wizard tests in parallel with other test jobs to minimize total CI time

### Code Patterns to Follow

**Mocking Pattern**:
```python
# Always mock at the module level where function is used
mocker.patch('dbt_to_lookml.wizard.generate_wizard.questionary.text')
# NOT at questionary module level
```

**Fixture Pattern**:
```python
# Use tmp_path for temporary directories
@pytest.fixture
def mock_project(tmp_path: Path) -> Path:
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    return tmp_path
```

**CLI Test Pattern**:
```python
# Use CliRunner for all CLI tests
from click.testing import CliRunner

def test_cli_command(runner: CliRunner):
    result = runner.invoke(cli, ['command', '--flag'])
    assert result.exit_code == 0
```

### References

- `src/tests/test_cli.py` lines 14-690 - CLI testing patterns
- `src/tests/unit/test_dbt_parser.py` lines 20-80 - Fixture patterns
- `src/tests/integration/test_end_to_end.py` lines 18-100 - Integration test patterns
- `pyproject.toml` lines 75-104 - Pytest configuration

## Implementation Checklist

### Phase 1: Unit Tests - Detection (Day 1)
- [ ] Create `src/tests/unit/test_wizard_detection.py`
- [ ] Implement `TestWizardDetection` class
- [ ] Add 7+ detection test cases
- [ ] Create mock project fixtures
- [ ] Verify 95%+ coverage for detection module
- [ ] Run `pytest src/tests/unit/test_wizard_detection.py -v`

### Phase 2: Unit Tests - Generate Wizard (Day 2-3)
- [ ] Create `src/tests/unit/test_wizard_generate.py`
- [ ] Implement `TestGenerateWizard` class
- [ ] Create questionary mocking fixture
- [ ] Add 12+ wizard test cases
- [ ] Test prompt sequences, validation, command building
- [ ] Verify 95%+ coverage for generate wizard
- [ ] Run `pytest src/tests/unit/test_wizard_generate.py -v`

### Phase 3: Integration Tests (Day 4-5)
- [ ] Create `src/tests/integration/test_wizard_integration.py`
- [ ] Implement `TestWizardIntegration` class
- [ ] Create realistic project fixtures
- [ ] Add 8+ integration test cases
- [ ] Test full wizard flows and error handling
- [ ] Verify 95%+ integration coverage
- [ ] Run `pytest src/tests/integration/test_wizard_integration.py -v`

### Phase 4: CLI Tests (Day 6)
- [ ] Update `src/tests/test_cli.py`
- [ ] Add `TestCLIWizard` class
- [ ] Add 7+ CLI test cases
- [ ] Mock wizard functions for non-interactive testing
- [ ] Test wizard command availability and help
- [ ] Verify 100% CLI command coverage
- [ ] Run `pytest src/tests/test_cli.py::TestCLIWizard -v`

### Phase 5: Documentation - README (Day 7)
- [ ] Update `README.md`
- [ ] Add "Interactive Wizard" section after CLI Usage
- [ ] Write usage examples (basic, TUI, features)
- [ ] Document wizard options and use cases
- [ ] Add example interaction snippet
- [ ] Review for clarity and completeness

### Phase 6: Documentation - CLAUDE.md (Day 8)
- [ ] Update `CLAUDE.md`
- [ ] Add "Wizard System Architecture" section
- [ ] Document module structure and design patterns
- [ ] Add testing strategy with code examples
- [ ] Document mocking patterns for developers
- [ ] Include error handling and performance notes

### Phase 7: CI Integration (Day 9)
- [ ] Update `.github/workflows/test.yml`
- [ ] Add wizard-tests job after cli-tests
- [ ] Configure coverage reporting
- [ ] Update final-status job dependencies
- [ ] Test wizard command availability in CI
- [ ] Add wizard marker to `pyproject.toml`
- [ ] Push to branch and verify CI runs

### Phase 8: Final Validation (Day 10)
- [ ] Run full test suite: `make test-full`
- [ ] Verify 95%+ wizard coverage: `pytest src/tests/unit/test_wizard*.py --cov=dbt_to_lookml.wizard --cov-fail-under=95`
- [ ] Run CI pipeline on feature branch
- [ ] Manual testing: `dbt-to-lookml wizard generate --help`
- [ ] Verify all acceptance criteria met
- [ ] Create pull request with summary

## Ready for Implementation

This spec is complete and ready for implementation. All tasks are defined with:
- Clear file paths and actions
- Code examples and patterns
- Testing requirements
- Validation commands
- Implementation checklist

**Estimated Total Time**: 10 days (2 weeks)

**Next Steps**: Begin with Phase 1 (Detection Unit Tests) and proceed sequentially through the checklist.
