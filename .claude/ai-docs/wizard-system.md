# Wizard System Architecture

The wizard system provides interactive command building through project detection, prompt sequencing, and validation.

## Module Structure

```
src/dbt_to_lookml/wizard/
├── __init__.py              # Public API exports
├── base.py                  # BaseWizard abstract class (mode, config storage)
├── types.py                 # Type definitions (WizardConfig, WizardMode)
├── detection.py             # ProjectDetector (structure analysis, smart defaults)
├── generate_wizard.py       # GenerateWizard (prompts, validation, command building)
├── tui.py                   # GenerateWizardTUI (Textual-based UI, optional)
└── tui_widgets.py           # Custom Textual widgets (input, preview panels)
```

## Design Patterns

### 1. Detection-First

Analyze project structure before prompting:
- `ProjectDetector` scans for semantic_models directories
- Extracts schema hints from YAML files
- Suggests output directories based on conventions
- Results cached with 5-minute TTL

### 2. Progressive Enhancement

Graceful degradation when dependencies missing:
- Core wizard uses `questionary` (required)
- TUI mode uses `textual` (optional)
- Falls back to prompt mode automatically

### 3. Validation Pipeline

Multi-stage input validation:
- Real-time validation using `questionary.Validator`
- `PathValidator`: Path existence and type checks
- `SchemaValidator`: Schema name format validation
- Final config validation before command building

## Key Components

### ProjectDetector (`detection.py`)

```python
from dbt_to_lookml.wizard.detection import ProjectDetector

detector = ProjectDetector(working_dir=Path.cwd())
result = detector.detect()

if result.has_semantic_models():
    print(f"Found: {result.input_dir}")
```

**Classes**:
- `ProjectDetector`: Scans filesystem, caches results
- `DetectionResult`: NamedTuple with input_dir, output_dir, schema_name, file counts
- `DetectionCache`: TTL cache for detection results

### GenerateWizard (`generate_wizard.py`)

**Classes**:
- `GenerateWizardConfig`: Dataclass with all command options
- `PathValidator`: Custom questionary validator
- `SchemaValidator`: Custom questionary validator
- `GenerateWizard`: Main wizard orchestrating prompts

**Prompt Sequence**:
1. Input directory (with detection default)
2. Output directory (with suggested default)
3. Schema name (with detected default)
4. View prefix (optional)
5. Explore prefix (optional)
6. Connection name (default: "redshift_test")
7. Model name (default: "semantic_model")
8. Timezone conversion (three-choice select)
9. Additional options (checkboxes)

**Command Building**:
```python
config = GenerateWizardConfig(
    input_dir=Path("semantic_models"),
    output_dir=Path("build/lookml"),
    schema="analytics",
)
command = config.to_command_string(multiline=True)
```

## Testing Strategy

### Mocking Patterns

```python
# Mock questionary prompts
@patch("dbt_to_lookml.wizard.generate_wizard.questionary.text")
def test_wizard(mock_text):
    mock_text.return_value.ask.return_value = "user_input"
    wizard = GenerateWizard()
    result = wizard._prompt_schema()
    assert result == "user_input"

# Mock filesystem detection
@patch("dbt_to_lookml.wizard.detection.ProjectDetector")
def test_detection(mock_detector_class):
    mock_detector = MagicMock()
    mock_detector_class.return_value = mock_detector
    mock_detector.detect.return_value = MagicMock(input_dir=Path(...))
```

### Test Locations

- **Unit**: `src/tests/unit/test_wizard_detection.py`, `test_generate_wizard.py`
- **Integration**: `src/tests/integration/test_wizard_integration.py`
- **CLI**: `src/tests/test_cli.py::TestCLIWizard`

### Coverage Targets

- `wizard/detection.py`: 95%+
- `wizard/generate_wizard.py`: 95%+
- `wizard/base.py`: 95%+
- `wizard/tui.py`: 85%+ (optional feature)

## Error Handling

| Category | Handling |
|----------|----------|
| User Input | Real-time validation prevents invalid input |
| Filesystem | Detection skips restricted directories |
| Detection Failures | Continue with empty defaults |
| Execution | Config validation before command execution |

## Performance

- Detection: < 500ms target
- Caching: 5-minute TTL
- Directory depth: Max 3 levels
- Skips: .git, node_modules, .venv

## Common Pitfalls

1. **Wizard mocking**: Mock at module level (`dbt_to_lookml.wizard.generate_wizard.questionary`)
2. **Detection caching**: Use `cache_enabled=False` for tests
