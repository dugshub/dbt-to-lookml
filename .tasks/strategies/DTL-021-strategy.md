# Implementation Strategy: DTL-021

**Issue**: DTL-021 - Integration, testing, and documentation
**Analyzed**: 2025-11-12T21:00:00Z
**Stack**: backend
**Type**: chore

## Approach

Complete the wizard system implementation by adding comprehensive tests, integrating with existing CLI infrastructure, and updating documentation. This issue ensures the wizard feature is production-ready with 95%+ test coverage, proper mocking of user interactions, and clear documentation for both users and developers.

The strategy focuses on three core areas:
1. **Testing Infrastructure**: Unit tests, integration tests, and CLI tests with proper mocking
2. **CI Integration**: Dedicated test job for wizard features in GitHub Actions
3. **Documentation**: User-facing wizard examples (README) and technical architecture (CLAUDE.md)

## Architecture Impact

**Layer**: Testing, Documentation, and CI/CD Integration

**Modified Files**:
- `src/tests/unit/test_wizard_detection.py` (NEW) - Unit tests for detection module
- `src/tests/unit/test_wizard_generate.py` (NEW) - Unit tests for generate wizard
- `src/tests/integration/test_wizard_integration.py` (NEW) - End-to-end wizard tests
- `src/tests/test_cli.py` (UPDATE) - Add wizard command tests
- `README.md` (UPDATE) - Add "Interactive Wizard" section
- `CLAUDE.md` (UPDATE) - Add wizard architecture and testing documentation
- `.github/workflows/test.yml` (UPDATE) - Add wizard-specific test job
- `pyproject.toml` (UPDATE) - Add wizard test markers if needed

**Dependencies on prior issues**:
- DTL-015: Base wizard infrastructure (wizard module, dependencies)
- DTL-016: Enhanced help text
- DTL-017: Detection module
- DTL-018: Prompt-based wizard
- DTL-019: Validation preview
- DTL-020: TUI wizard (optional)

## Dependencies

- **Depends on**:
  - DTL-015 (wizard infrastructure and dependencies installed)
  - DTL-017 (detection module exists and functional)
  - DTL-018 (generate_wizard module exists and functional)
  - DTL-020 (TUI wizard module exists, if implemented)

- **Blocking**: None (this is the final integration issue)

- **Related to**: DTL-014 (parent epic)

## Detailed Implementation Plan

### 1. Unit Tests for Detection Module

**File**: `src/tests/unit/test_wizard_detection.py`

**Test Class**: `TestWizardDetection`

**Test Cases**:

1. **test_detect_semantic_models_directory_found**
   - Create temp directory with semantic model YAML files
   - Call detection function
   - Verify: Returns correct path and confidence score

2. **test_detect_semantic_models_multiple_candidates**
   - Create multiple potential directories (semantic_models/, models/, etc.)
   - Verify: Returns most likely candidate with highest confidence

3. **test_detect_semantic_models_none_found**
   - Create directory with no semantic models
   - Verify: Returns None or empty result

4. **test_detect_schema_from_yaml**
   - Create YAML file with schema information
   - Parse and detect schema name
   - Verify: Extracts schema correctly

5. **test_detect_project_structure**
   - Create typical dbt project structure
   - Verify: Detects output directory suggestions, model patterns

6. **test_detect_with_invalid_permissions**
   - Create directory without read permissions
   - Verify: Handles gracefully with proper error

7. **test_detect_with_malformed_yaml**
   - Create directory with invalid YAML files
   - Verify: Skips invalid files, continues detection

**Coverage Target**: 95%+ for all detection module functions

### 2. Unit Tests for Generate Wizard

**File**: `src/tests/unit/test_wizard_generate.py`

**Test Class**: `TestGenerateWizard`

**Mocking Strategy**: Use `pytest-mock` to mock questionary prompts

**Test Cases**:

1. **test_prompt_sequence_all_required_fields**
   - Mock questionary responses for required fields
   - Run wizard
   - Verify: All prompts shown in correct order
   - Verify: Command string built correctly

2. **test_prompt_validation_invalid_directory**
   - Mock invalid directory path input
   - Verify: Validation fails, re-prompts user

3. **test_prompt_validation_missing_required_field**
   - Mock empty response for required field
   - Verify: Validation fails, re-prompts

4. **test_prompt_with_detected_defaults**
   - Mock detection returning smart defaults
   - Verify: Defaults shown to user
   - Verify: Defaults used if user presses Enter

5. **test_prompt_optional_fields_skippable**
   - Mock pressing Enter for optional fields
   - Verify: Optional fields not included in command

6. **test_prompt_timezone_conversion_yes**
   - Mock "yes" selection for timezone conversion
   - Verify: --convert-tz flag in command

7. **test_prompt_timezone_conversion_no**
   - Mock "no" selection
   - Verify: --no-convert-tz flag in command

8. **test_prompt_additional_options_checkboxes**
   - Mock checkbox selections for dry-run, no-validation, show-summary
   - Verify: Correct flags in final command

9. **test_build_command_string_all_options**
   - Provide all possible inputs
   - Verify: Command string is well-formed and complete

10. **test_build_command_string_minimal_options**
    - Provide only required inputs
    - Verify: Command string has only required flags

11. **test_wizard_keyboard_interrupt**
    - Mock KeyboardInterrupt during prompts
    - Verify: Graceful exit with appropriate message

12. **test_wizard_with_detection_failure**
    - Mock detection returning no results
    - Verify: Wizard continues with no defaults

**Mocking Example**:
```python
def test_prompt_sequence_all_required_fields(mocker):
    """Test wizard prompts for all required fields."""
    # Mock questionary prompts
    mock_text = mocker.patch('questionary.text')
    mock_select = mocker.patch('questionary.select')
    mock_checkbox = mocker.patch('questionary.checkbox')

    # Set up mock return values
    mock_text.return_value.ask.side_effect = [
        '/path/to/semantic_models',  # input_dir
        '/path/to/output',            # output_dir
    ]
    mock_select.return_value.ask.side_effect = [
        'analytics',  # schema
        'no',         # convert_tz
    ]
    mock_checkbox.return_value.ask.return_value = ['--dry-run', '--show-summary']

    # Run wizard
    command = generate_wizard()

    # Verify command construction
    assert 'generate' in command
    assert '--input-dir /path/to/semantic_models' in command
    assert '--output-dir /path/to/output' in command
    assert '--schema analytics' in command
    assert '--dry-run' in command
    assert '--show-summary' in command
```

**Coverage Target**: 95%+ for all wizard module functions

### 3. Integration Tests for Wizard Flows

**File**: `src/tests/integration/test_wizard_integration.py`

**Test Class**: `TestWizardIntegration`

**Test Cases**:

1. **test_full_wizard_flow_generate_command**
   - Mock complete wizard interaction
   - Execute generated command
   - Verify: Files are created as expected

2. **test_wizard_preview_before_execution**
   - Mock wizard with preview enabled
   - Verify: Preview shown before execution
   - Verify: User can confirm/cancel

3. **test_wizard_tui_mode_if_available**
   - Check if Textual is installed
   - If available, test TUI wizard flow
   - If not available, verify graceful degradation

4. **test_wizard_detection_integration**
   - Create realistic project structure
   - Run wizard
   - Verify: Detection results influence prompts

5. **test_wizard_with_real_semantic_models**
   - Use fixture semantic models
   - Complete wizard flow
   - Execute command
   - Verify: LookML files generated correctly

6. **test_wizard_error_handling_invalid_path**
   - Mock invalid input directory
   - Verify: Error message shown
   - Verify: Wizard allows retry

7. **test_wizard_error_handling_permission_denied**
   - Mock permission error on output directory
   - Verify: Error handled gracefully

8. **test_wizard_end_to_end_with_validation**
   - Complete wizard flow
   - Enable validation preview
   - Confirm execution
   - Verify: All steps complete successfully

**Coverage Target**: 95%+ for wizard integration flows

### 4. CLI Tests for Wizard Commands

**File**: `src/tests/test_cli.py` (UPDATE existing file)

**New Test Class**: `TestCLIWizard`

**Test Cases**:

1. **test_wizard_command_help**
   - Run: `dbt-to-lookml wizard --help`
   - Verify: Help text displayed

2. **test_wizard_generate_command_exists**
   - Run: `dbt-to-lookml wizard generate --help`
   - Verify: Command is accessible

3. **test_wizard_generate_with_defaults**
   - Mock wizard interaction
   - Run: `dbt-to-lookml wizard generate`
   - Verify: Command completes successfully

4. **test_wizard_tui_flag**
   - Run: `dbt-to-lookml wizard generate --tui`
   - Verify: TUI mode attempted (or graceful fallback)

5. **test_wizard_non_interactive_mode**
   - Run wizard in non-interactive environment
   - Verify: Appropriate error or fallback

6. **test_wizard_with_existing_options**
   - Run: `dbt-to-lookml wizard generate --input-dir /path`
   - Verify: Pre-filled options skip prompts

7. **test_wizard_keyboard_interrupt_cli**
   - Simulate Ctrl+C during wizard
   - Verify: Clean exit with message

**CLI Testing Pattern** (using Click's CliRunner):
```python
def test_wizard_command_help(runner: CliRunner) -> None:
    """Test wizard command help text."""
    result = runner.invoke(cli, ["wizard", "--help"])
    assert result.exit_code == 0
    assert "Interactive wizard" in result.output
    assert "generate" in result.output
```

### 5. Documentation Updates

#### 5.1 README.md Updates

**Location**: After "## CLI Usage" section (around line 56)

**New Section**: "## Interactive Wizard"

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

#### 5.2 CLAUDE.md Updates

**Location**: After "## Important Implementation Details" section

**New Section**: "## Wizard System Architecture"

```markdown
## Wizard System Architecture

The wizard system provides interactive command building through a three-tier architecture:

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
   - Real-time validation during prompts (questionary validators)
   - Path existence checks for directories
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

**Algorithm**:
1. Walk directory tree from current path
2. Score directories based on:
   - Presence of YAML files with semantic model structure
   - Directory naming patterns (semantic_models, models, etc.)
   - File count and structure
3. Return highest-scored candidate

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
1. Input directory (required, path validation, auto-detected default)
2. Output directory (required, path validation, suggested)
3. Schema name (required, detected from YAML if available)
4. View prefix (optional, empty default)
5. Explore prefix (optional, empty default)
6. Connection name (optional, redshift_test default)
7. Model name (optional, semantic_model default)
8. Timezone conversion (select: yes/no, default: no)
9. Additional options (checkbox: dry-run, no-validation, show-summary)

**Validation**:
- Paths: Existence checks, permissions, absolute vs relative
- Schema: Non-empty string
- Prefixes: Valid identifier characters
- Timezone: Boolean selection
- Checkboxes: Multi-select validation

**Testing Approach**:
- Mock questionary prompts with various inputs
- Test validation logic independently
- Test command string building with all combinations
- Test error handling for invalid inputs

#### TUI Module (`wizard/tui.py`)

**Purpose**: Full-screen terminal UI using Textual library

**Implementation** (if DTL-020 completed):
- Textual App with form widgets
- Real-time validation indicators
- Navigation between fields with Tab/Arrow keys
- Submit with Enter, Cancel with Esc

**Testing Approach**:
- Use Textual's testing utilities (pilot)
- Mock form submissions
- Test navigation flow
- Test validation display

### Testing Strategy

#### Mocking User Input

**Questionary Mocking** (prompt-based wizard):
```python
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_questionary(mocker):
    """Mock questionary prompts for testing."""
    mock_text = mocker.patch('dbt_to_lookml.wizard.generate_wizard.questionary.text')
    mock_select = mocker.patch('dbt_to_lookml.wizard.generate_wizard.questionary.select')
    mock_checkbox = mocker.patch('dbt_to_lookml.wizard.generate_wizard.questionary.checkbox')

    return {
        'text': mock_text,
        'select': mock_select,
        'checkbox': mock_checkbox,
    }

def test_wizard_with_mocks(mock_questionary):
    """Test wizard with mocked user input."""
    mock_questionary['text'].return_value.ask.side_effect = [
        '/path/to/input',
        '/path/to/output',
    ]
    mock_questionary['select'].return_value.ask.return_value = 'analytics'

    command = run_generate_wizard(context)

    assert '--input-dir /path/to/input' in command
    assert '--schema analytics' in command
```

**Click Testing** (CLI commands):
```python
from click.testing import CliRunner

def test_wizard_cli(runner: CliRunner, mocker):
    """Test wizard command via CLI."""
    # Mock the wizard function to avoid interactive prompts
    mock_wizard = mocker.patch('dbt_to_lookml.__main__.run_generate_wizard')
    mock_wizard.return_value = 'generate -i ./semantic_models -o ./build'

    result = runner.invoke(cli, ['wizard', 'generate'])

    assert result.exit_code == 0
    assert mock_wizard.called
```

**Textual Testing** (TUI mode):
```python
from textual.pilot import Pilot

async def test_tui_wizard():
    """Test TUI wizard with Textual pilot."""
    app = WizardApp()
    async with app.run_test() as pilot:
        # Navigate to input field
        await pilot.press("tab")
        # Type value
        await pilot.press("s", "e", "m", "a", "n", "t", "i", "c")
        # Submit form
        await pilot.press("enter")

        # Verify command built
        assert app.command_string == expected_command
```

#### Coverage Requirements

**Per-Module Coverage Targets**:
- `wizard/detection.py`: 95%+ branch coverage
- `wizard/generate_wizard.py`: 95%+ branch coverage
- `wizard/tui.py`: 85%+ branch coverage (Textual harder to test)

**Overall Wizard Coverage**: 95%+

**Coverage Gaps to Address**:
- Error handling paths (invalid input, permissions, etc.)
- Edge cases (empty directories, malformed YAML, etc.)
- Keyboard interrupts and cancellations
- Non-interactive environments

#### Test Organization

**Test Markers**:
- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - End-to-end wizard flows
- `@pytest.mark.cli` - CLI command interface tests
- `@pytest.mark.wizard` - All wizard-related tests (NEW marker)

**Fixture Organization**:
```python
@pytest.fixture
def mock_project_structure(tmp_path):
    """Create realistic project structure for testing."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()

    # Create sample YAML
    (semantic_dir / "orders.yml").write_text("""
    name: orders
    model: ref('orders')
    # ... rest of semantic model
    """)

    return tmp_path

@pytest.fixture
def wizard_context(mock_project_structure):
    """Create wizard context from mock project."""
    return detect_project_structure(mock_project_structure)
```

### Error Handling in Wizard

**Error Categories**:
1. **User Input Errors**: Invalid paths, empty required fields
   - Strategy: Real-time validation, re-prompt
2. **Filesystem Errors**: Missing directories, permission denied
   - Strategy: Clear error messages, suggest fixes
3. **Detection Failures**: No semantic models found
   - Strategy: Graceful degradation, no defaults
4. **Execution Errors**: Command fails when executed
   - Strategy: Show error output, offer to edit command

**Implementation Pattern**:
```python
def prompt_input_directory(detected_default: Path | None) -> Path:
    """Prompt for input directory with validation."""
    while True:
        try:
            response = questionary.path(
                "Input directory:",
                default=str(detected_default) if detected_default else "",
                validate=PathValidator(must_exist=True, must_be_dir=True)
            ).ask()

            if response is None:  # User cancelled
                raise KeyboardInterrupt()

            path = Path(response)
            if not path.exists():
                console.print("[red]Directory does not exist[/red]")
                continue

            return path

        except KeyboardInterrupt:
            console.print("\n[yellow]Wizard cancelled[/yellow]")
            raise
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            continue
```

### Integration with Existing CLI

**Command Structure**:
```
dbt-to-lookml
├── generate (existing)
├── validate (existing)
└── wizard (NEW)
    ├── generate (NEW)
    └── validate (NEW, future)
```

**CLI Implementation** (`__main__.py`):
```python
@cli.group()
def wizard():
    """Interactive wizard for building commands."""
    pass

@wizard.command()
@click.option('--tui', is_flag=True, help='Use full-screen TUI mode')
@click.option('--preview', is_flag=True, help='Preview command without executing')
def generate(tui: bool, preview: bool):
    """Interactive wizard for generate command."""
    try:
        # Detect project structure
        context = detect_project_structure(Path.cwd())

        # Run appropriate wizard
        if tui and TEXTUAL_AVAILABLE:
            command = run_tui_wizard(context)
        else:
            command = run_generate_wizard(context)

        # Preview or execute
        if preview:
            console.print(f"[blue]Generated command:[/blue] {command}")
        else:
            execute_command(command)

    except KeyboardInterrupt:
        console.print("\n[yellow]Wizard cancelled[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
```

### Performance Considerations

**Detection Performance**:
- Limit directory traversal depth (default: 3 levels)
- Cache detection results for session
- Skip large directories (node_modules, .git, etc.)

**Memory Usage**:
- Stream YAML parsing (don't load all files)
- Lazy load TUI components
- Release resources after wizard completes

**Benchmarks** (target):
- Detection: < 500ms for typical project
- Prompt sequence: < 100ms between prompts
- TUI startup: < 1 second
- Total wizard flow: < 2 minutes (user interaction dependent)
```

### 6. CI Integration

**File**: `.github/workflows/test.yml`

**New Job**: `wizard-tests`

**Location**: After `cli-tests` job (around line 142)

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

**Update**: `final-status` job (line 409)

Add wizard-tests to dependencies:
```yaml
needs: [unit-tests, integration-tests, cli-tests, error-handling-tests, smoke-tests, multi-python-test, wizard-tests]
```

Update status check:
```yaml
if [ "${{ needs.wizard-tests.result }}" = "success" ] && \
```

## Testing Strategy

### Test Coverage Breakdown

**Unit Tests** (target: 95%+ coverage):
- Detection module: All detection functions, edge cases, error handling
- Generate wizard: Prompt sequence, validation, command building
- TUI module: Form creation, validation, navigation (if implemented)

**Integration Tests** (target: 95%+ coverage):
- Full wizard flow with mocked interactions
- Preview and execution modes
- Detection + wizard + command execution
- Error recovery flows

**CLI Tests** (target: 100% command coverage):
- Wizard command help text
- Wizard generate command
- TUI mode flag
- Preview mode flag
- Integration with existing CLI

### Mock Testing Patterns

**Pattern 1: Mock Questionary Prompts**
```python
@pytest.fixture
def mock_wizard_responses(mocker):
    """Mock all wizard prompt responses."""
    responses = {
        'input_dir': '/path/to/semantic_models',
        'output_dir': '/path/to/output',
        'schema': 'analytics',
        'view_prefix': '',
        'explore_prefix': '',
        'convert_tz': 'no',
        'additional_options': ['--dry-run'],
    }

    # Mock questionary functions
    mocker.patch('questionary.text', side_effect=[
        Mock(ask=Mock(return_value=responses['input_dir'])),
        Mock(ask=Mock(return_value=responses['output_dir'])),
        Mock(ask=Mock(return_value=responses['view_prefix'])),
        Mock(ask=Mock(return_value=responses['explore_prefix'])),
    ])
    mocker.patch('questionary.select', return_value=Mock(ask=Mock(return_value=responses['schema'])))
    mocker.patch('questionary.checkbox', return_value=Mock(ask=Mock(return_value=responses['additional_options'])))

    return responses
```

**Pattern 2: Mock Filesystem for Detection**
```python
@pytest.fixture
def mock_project(tmp_path):
    """Create mock project structure."""
    # Create semantic_models directory
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()

    # Create sample semantic model
    (semantic_dir / "orders.yml").write_text("""
    name: orders
    model: ref('orders')
    entities:
      - name: order_id
        type: primary
    """)

    return tmp_path
```

**Pattern 3: Mock CLI Execution**
```python
def test_wizard_cli_execution(runner, mocker):
    """Test CLI wizard execution."""
    # Mock the wizard to return a command
    mock_run_wizard = mocker.patch('dbt_to_lookml.__main__.run_generate_wizard')
    mock_run_wizard.return_value = 'generate -i ./semantic_models -o ./build -s analytics'

    # Mock command execution
    mock_execute = mocker.patch('dbt_to_lookml.__main__.execute_command')

    result = runner.invoke(cli, ['wizard', 'generate'])

    assert result.exit_code == 0
    assert mock_execute.called
```

### Coverage Verification

**Commands**:
```bash
# Check wizard module coverage
pytest src/tests/unit/test_wizard*.py --cov=dbt_to_lookml.wizard --cov-report=term-missing --cov-fail-under=95

# Check integration coverage
pytest src/tests/integration/test_wizard*.py --cov=dbt_to_lookml.wizard --cov-report=html

# Check overall test coverage including wizard
make test-coverage

# Generate coverage report for wizard only
pytest src/tests/ -k wizard --cov=dbt_to_lookml.wizard --cov-report=html:htmlcov/wizard
```

**Coverage Goals**:
- Detection module: 95%+
- Generate wizard: 95%+
- TUI module: 85%+ (if implemented)
- CLI wizard commands: 100%
- Overall wizard package: 95%+

## Implementation Checklist

### Phase 1: Unit Tests (Week 1)
- [ ] Create `src/tests/unit/test_wizard_detection.py`
- [ ] Implement detection module test cases (7+ tests)
- [ ] Create `src/tests/unit/test_wizard_generate.py`
- [ ] Implement generate wizard test cases (12+ tests)
- [ ] Verify 95%+ unit test coverage
- [ ] Run `make test-fast` to ensure unit tests pass

### Phase 2: Integration Tests (Week 1-2)
- [ ] Create `src/tests/integration/test_wizard_integration.py`
- [ ] Implement end-to-end wizard test cases (8+ tests)
- [ ] Test detection + wizard + execution flow
- [ ] Test error handling and recovery flows
- [ ] Verify 95%+ integration coverage

### Phase 3: CLI Tests (Week 2)
- [ ] Update `src/tests/test_cli.py` with `TestCLIWizard` class
- [ ] Implement wizard CLI test cases (7+ tests)
- [ ] Test help text, command availability, execution
- [ ] Verify 100% CLI command coverage

### Phase 4: Documentation (Week 2)
- [ ] Update README.md with "Interactive Wizard" section
- [ ] Add usage examples and feature descriptions
- [ ] Update CLAUDE.md with wizard architecture section
- [ ] Document testing strategy and patterns
- [ ] Add code examples for mocking

### Phase 5: CI Integration (Week 2)
- [ ] Add `wizard-tests` job to `.github/workflows/test.yml`
- [ ] Update `final-status` job to include wizard tests
- [ ] Test CI pipeline with wizard tests
- [ ] Verify coverage reporting works

### Phase 6: Validation (Week 2-3)
- [ ] Run full test suite: `make test-full`
- [ ] Verify 95%+ wizard coverage: `make test-coverage`
- [ ] Run CI pipeline on feature branch
- [ ] Manual testing of wizard flows
- [ ] Performance benchmarking of detection

## Implementation Order

1. **Unit Tests - Detection** (Day 1)
   - Create test file
   - Implement 7 detection test cases
   - Verify coverage

2. **Unit Tests - Generate Wizard** (Day 2-3)
   - Create test file
   - Implement 12 wizard test cases
   - Mock questionary interactions
   - Verify coverage

3. **Integration Tests** (Day 4-5)
   - Create test file
   - Implement 8 end-to-end test cases
   - Test full wizard flows
   - Verify coverage

4. **CLI Tests** (Day 6)
   - Update test_cli.py
   - Implement 7 CLI test cases
   - Test command availability

5. **Documentation - README** (Day 7)
   - Add Interactive Wizard section
   - Write usage examples
   - Document features

6. **Documentation - CLAUDE.md** (Day 8)
   - Add architecture section
   - Document testing patterns
   - Add code examples

7. **CI Integration** (Day 9)
   - Add wizard-tests job
   - Update final-status job
   - Test CI pipeline

8. **Final Validation** (Day 10)
   - Run full test suite
   - Verify coverage
   - Manual testing
   - Performance check

**Estimated Total**: 10 days (2 weeks)

## Rollout Impact

### Test Infrastructure
- **New Test Files**: 3 new test files (~800 lines of test code)
- **Updated Test Files**: 1 file (test_cli.py) with ~200 new lines
- **Test Execution Time**: +30-60 seconds to test suite
- **CI Pipeline**: +2-3 minutes for wizard-specific job

### Coverage Impact
- **Overall Project Coverage**: Should increase due to wizard coverage
- **Wizard Module Coverage**: Target 95%+, critical for production readiness
- **Regression Risk**: Low (wizard is new feature, doesn't modify existing code)

### Documentation Impact
- **User Documentation**: README.md clearer with wizard examples
- **Developer Documentation**: CLAUDE.md comprehensive testing guide
- **Onboarding**: Easier for new developers to understand wizard testing

### CI/CD Impact
- **Build Time**: Slightly longer due to additional test job
- **Failure Detection**: Better (wizard-specific tests catch wizard issues)
- **Coverage Reporting**: More granular with wizard flags

## Notes for Implementation

1. **Test Isolation**: Keep wizard tests independent of existing CLI tests to avoid coupling

2. **Mock Strategy**: Use pytest-mock for all user interaction mocking to avoid actual prompts during tests

3. **Fixture Reuse**: Create shared fixtures for mock project structures, reuse across test files

4. **Coverage Thresholds**: Set strict 95%+ threshold for wizard modules in pytest config

5. **CI Optimization**: Run wizard tests in parallel with other test jobs to minimize total CI time

6. **Documentation First**: Write documentation examples before implementing tests to validate user experience

7. **Performance Monitoring**: Add basic performance assertions to ensure wizard stays responsive

8. **Graceful Degradation**: Test that wizard works even when detection fails or Textual is unavailable

9. **Error Messages**: Ensure all error paths have clear, actionable messages for users

10. **Test Maintenance**: Use parametrized tests where possible to reduce duplication and improve maintainability

## Success Metrics

**Test Coverage**:
- ✅ Wizard detection module: 95%+ branch coverage
- ✅ Wizard generate module: 95%+ branch coverage
- ✅ Wizard integration tests: 95%+ coverage
- ✅ CLI wizard commands: 100% coverage

**Test Quality**:
- ✅ All wizard features have unit tests
- ✅ All error paths tested
- ✅ Mocking strategy documented and reusable
- ✅ Tests run fast (< 60 seconds for all wizard tests)

**Documentation**:
- ✅ README has Interactive Wizard section with examples
- ✅ CLAUDE.md documents wizard architecture and testing
- ✅ Code examples for mocking are clear and complete
- ✅ Test patterns are documented and reusable

**CI Integration**:
- ✅ Wizard-specific test job in CI pipeline
- ✅ Coverage reporting works for wizard modules
- ✅ CI pipeline passes with all wizard tests
- ✅ Test failures are clearly identified in CI output

**Overall**:
- ✅ 95%+ test coverage for all wizard code
- ✅ All acceptance criteria met from issue DTL-021
- ✅ Documentation complete and accurate
- ✅ CI pipeline stable and comprehensive
