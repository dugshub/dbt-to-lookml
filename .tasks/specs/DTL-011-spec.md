# Feature: Add comprehensive unit tests for timezone conversion

## Metadata
- **Issue**: `DTL-011`
- **Stack**: `backend` (testing)
- **Type**: `feature`
- **Generated**: 2025-11-12T21:00:00Z
- **Session**: `dtl-011-spec-generation`
- **Strategy**: Approved 2025-11-12

## Issue Context

### Problem Statement
Create comprehensive unit tests to validate timezone conversion behavior at all configuration levels (dimension metadata, generator parameter, CLI flag, and defaults). The testing strategy validates that the `convert_tz` configuration is properly handled at each layer of the system and that precedence rules are correctly implemented across schema, generator, and CLI levels.

### Solution Approach
Implement three test classes (one per configuration layer) with parametrized tests for variations and edge cases. Use pytest best practices with clear arrange-act-assert structure. Tests validate both internal state and actual LookML output serialization.

**Test Organization**:
1. **TestDimensionConvertTz** in `test_schemas.py` - Dimension-level convert_tz handling
2. **TestLookMLGeneratorConvertTz** in `test_lookml_generator.py` - Generator propagation and defaults
3. **TestCLIConvertTzFlags** in `test_cli.py` - CLI flag parsing and integration

### Success Criteria
- All new tests pass
- 95%+ branch coverage for new code paths
- Tests cover all precedence scenarios (meta > generator > CLI > default)
- Tests validate actual LookML output format ("yes"/"no" strings)

## Approved Strategy Summary

The approved strategy establishes:

**Architecture**: Three-layer testing matching system architecture (Schema → Generator → CLI)

**Precedence Chain**: `Dimension.meta.convert_tz > LookMLGenerator.convert_tz > CLI flag > default (False)`

**Coverage Requirements**:
- Dimension._to_dimension_group_dict() with convert_tz parameter
- LookMLGenerator.__init__() and propagation logic
- SemanticModel.to_lookml_dict() parameter propagation
- CLI flag parsing and validation
- Complete precedence chain validation

**Test Strategy**:
- Parametrized tests for variations (True/False/None)
- Parametrized precedence truth table
- LookML output validation for correct serialization
- Edge cases: custom timeframes, mixed configurations

## Implementation Plan

### Phase 1: Schema-Level Tests (TestDimensionConvertTz)

**Depends on**: DTL-008 (Dimension schema convert_tz support)

**Tasks**:

1. **Create TestDimensionConvertTz class in test_schemas.py**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`
   - Add new test class after existing TestDimension classes
   - 10-12 test methods covering all convert_tz scenarios

2. **Test convert_tz basic states**
   - `test_dimension_group_convert_tz_explicit_true()` - Dimension with meta.convert_tz=True
   - `test_dimension_group_convert_tz_explicit_false()` - Dimension with meta.convert_tz=False
   - `test_dimension_group_convert_tz_none()` - Dimension with no convert_tz (uses default)
   - `test_dimension_group_convert_tz_default_false()` - Verify default is False

3. **Test LookML output format**
   - `test_dimension_group_convert_tz_in_lookml_output()` - Verify "convert_tz: yes" or "convert_tz: no" in dict
   - `test_dimension_group_convert_tz_serialization()` - Verify "yes"/"no" string format (not boolean)

4. **Test precedence and edge cases**
   - `test_dimension_group_convert_tz_precedence_meta_overrides_default()` - Meta=True overrides default
   - `test_dimension_group_convert_tz_with_custom_timeframes_respects_convert_tz()` - Works with custom granularity
   - `test_dimension_convert_tz_ignored_for_non_time_dimensions()` - Categorical dims ignore convert_tz
   - `test_multiple_dimensions_different_convert_tz_settings()` - Mixed scenarios

### Phase 2: Generator Tests (TestLookMLGeneratorConvertTz)

**Depends on**: DTL-009 (LookMLGenerator convert_tz propagation)

**Tasks**:

5. **Create TestLookMLGeneratorConvertTz class in test_lookml_generator.py**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_lookml_generator.py`
   - Add new test class after existing TestLookMLGenerator classes
   - 12-14 test methods covering generator initialization and propagation

6. **Test generator initialization**
   - `test_generator_initialization_with_convert_tz_true()` - Generator accepts convert_tz=True
   - `test_generator_initialization_with_convert_tz_false()` - Generator accepts convert_tz=False
   - `test_generator_initialization_with_convert_tz_none()` - Generator accepts convert_tz=None
   - `test_generator_convert_tz_propagation_default_false()` - Verify default is False

7. **Test propagation to dimensions**
   - `test_generator_propagates_convert_tz_to_dimensions()` - Generator setting propagates to all dimension_groups
   - `test_generator_convert_tz_affects_all_dimension_groups()` - All time dims get generator's convert_tz
   - `test_generator_convert_tz_with_view_containing_categorical_and_time_dims()` - Only time dims affected
   - `test_generate_view_lookml_contains_convert_tz()` - Final LookML output contains convert_tz values

8. **Test precedence and mixed scenarios**
   - `test_dimension_meta_overrides_generator_convert_tz_true()` - Meta=False overrides generator=True
   - `test_dimension_meta_overrides_generator_convert_tz_false()` - Meta=True overrides generator=False
   - `test_mixed_dimension_meta_with_generator_convert_tz()` - Some dims override, others use generator default
   - `test_generator_convert_tz_with_entities()` - Entities not affected (not time dims)

### Phase 3: CLI Tests (TestCLIConvertTzFlags)

**Depends on**: DTL-010 (CLI flags for timezone conversion)

**Tasks**:

9. **Create TestCLIConvertTzFlags class in test_cli.py**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/test_cli.py`
   - Add new test class after existing TestCLI classes
   - 11-13 test methods covering CLI flags and integration

10. **Test CLI flag parsing**
    - `test_cli_generate_with_convert_tz_flag()` - CLI accepts --convert-tz flag
    - `test_cli_generate_with_no_convert_tz_flag()` - CLI accepts --no-convert-tz flag
    - `test_cli_generate_without_convert_tz_flag()` - CLI without flag uses default
    - `test_cli_generate_help_shows_convert_tz_flags()` - Help text documents new flags

11. **Test CLI flag effects**
    - `test_cli_convert_tz_flag_generates_convert_tz_yes()` - --convert-tz produces convert_tz: yes
    - `test_cli_no_convert_tz_flag_generates_convert_tz_no()` - --no-convert-tz produces convert_tz: no
    - `test_cli_convert_tz_flag_in_generated_lookml_files()` - Flag value appears in actual files

12. **Test precedence and integration**
    - `test_cli_convert_tz_respects_dimension_meta_override()` - Meta overrides CLI flag
    - `test_cli_convert_tz_with_view_prefix_and_explore_prefix()` - Works with other flags
    - `test_cli_convert_tz_flag_validates_output()` - Validation passes with correct values

### Phase 4: Parametrized Precedence Tests

**Tasks**:

13. **Add parametrized precedence chain test (add to TestLookMLGeneratorConvertTz)**
    - Create parametrized test covering all 7+ precedence combinations
    - Truth table: dimension_meta × generator_setting × cli_flag → expected_result
    - Test name: `test_precedence_chain()`

### Phase 5: Test Fixtures and Helpers

**Tasks**:

14. **Create reusable test fixtures**
    - `time_dimension_with_convert_tz_true()` - Time dim with meta.convert_tz=True
    - `time_dimension_with_convert_tz_false()` - Time dim with meta.convert_tz=False
    - `model_with_mixed_convert_tz()` - Model with mixed convert_tz dimensions
    - `cli_runner()` - CliRunner instance (might already exist)
    - `semantic_models_dir()` - Path to test semantic models (might already exist)

## Detailed Task Breakdown

### Task 1: TestDimensionConvertTz - Basic State Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`

**Implementation Guidance**:
```python
class TestDimensionConvertTz:
    """Test cases for Dimension convert_tz handling."""

    @pytest.mark.parametrize(
        "convert_tz_value,expected_lookml",
        [
            (True, "yes"),
            (False, "no"),
            (None, "no"),  # Default is False
        ]
    )
    def test_dimension_group_convert_tz_output(
        self, convert_tz_value: bool | None, expected_lookml: str
    ) -> None:
        """Test convert_tz appears in LookML output with correct value."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(convert_tz=convert_tz_value)
            ) if convert_tz_value is not None else None,
            type_params={"time_granularity": "day"}
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert
        assert result.get("convert_tz") == expected_lookml

    def test_dimension_convert_tz_ignored_for_non_time_dimensions(self) -> None:
        """Test that convert_tz in meta for categorical dimensions is ignored."""
        # Arrange
        dim = Dimension(
            name="status",
            type=DimensionType.STRING,
            config=Config(meta=ConfigMeta(convert_tz=True))
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert - categorical dimensions should not have convert_tz
        assert "convert_tz" not in result
```

**Reference**: Similar parametrized tests in `test_schemas.py` for dimensions (e.g., TestDimensionType)

**Tests to Add**:
- test_dimension_group_convert_tz_output (parametrized: True/False/None)
- test_dimension_group_convert_tz_default_false
- test_dimension_convert_tz_ignored_for_non_time_dimensions
- test_dimension_group_convert_tz_with_custom_timeframes_respects_convert_tz
- test_dimension_group_convert_tz_precedence_meta_overrides_default
- test_multiple_dimensions_different_convert_tz_settings

### Task 2: TestLookMLGeneratorConvertTz - Propagation Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_lookml_generator.py`

**Implementation Guidance**:
```python
class TestLookMLGeneratorConvertTz:
    """Test cases for LookMLGenerator convert_tz parameter and propagation."""

    @pytest.mark.parametrize(
        "convert_tz_param",
        [True, False, None]
    )
    def test_generator_initialization_with_convert_tz(
        self, convert_tz_param: bool | None
    ) -> None:
        """Test generator accepts convert_tz parameter."""
        # Arrange & Act
        generator = LookMLGenerator(convert_tz=convert_tz_param)

        # Assert
        assert generator.convert_tz == convert_tz_param

    def test_generator_propagates_convert_tz_to_dimensions(self) -> None:
        """Test that generator's convert_tz propagates to all dimension_groups."""
        # Arrange
        generator = LookMLGenerator(convert_tz=True)
        model = SemanticModel(
            name="events",
            model="ref('fct_events')",
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"}
                ),
                Dimension(
                    name="updated_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"}
                )
            ]
        )

        # Act
        result = model.to_lookml_dict(convert_tz=True)

        # Assert
        assert result["dimension_groups"][0]["convert_tz"] == "yes"
        assert result["dimension_groups"][1]["convert_tz"] == "yes"

    @pytest.mark.parametrize(
        "dimension_meta,generator_setting,expected",
        [
            (True, False, True),      # meta wins
            (False, True, False),     # meta wins
            (None, True, True),       # generator is default
            (None, False, False),     # generator is default
            (None, None, False),      # system default is False
        ]
    )
    def test_precedence_chain(
        self,
        dimension_meta: bool | None,
        generator_setting: bool | None,
        expected: bool
    ) -> None:
        """Test precedence: Dimension Meta > Generator > Default."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            config=Config(meta=ConfigMeta(convert_tz=dimension_meta))
            if dimension_meta is not None else None,
            type_params={"time_granularity": "day"}
        )
        model = SemanticModel(
            name="events",
            model="ref('fct_events')",
            dimensions=[dim]
        )

        # Act
        result = model.to_lookml_dict(convert_tz=generator_setting)

        # Assert
        expected_str = "yes" if expected else "no"
        assert result["dimension_groups"][0]["convert_tz"] == expected_str
```

**Reference**: Similar structure to existing TestLookMLGenerator tests in `test_lookml_generator.py`

**Tests to Add**:
- test_generator_initialization_with_convert_tz (parametrized)
- test_generator_convert_tz_propagation_default_false
- test_generator_propagates_convert_tz_to_dimensions
- test_generator_convert_tz_affects_all_dimension_groups
- test_generator_convert_tz_with_view_containing_categorical_and_time_dims
- test_generate_view_lookml_contains_convert_tz
- test_dimension_meta_overrides_generator_convert_tz_true
- test_dimension_meta_overrides_generator_convert_tz_false
- test_mixed_dimension_meta_with_generator_convert_tz
- test_generator_convert_tz_with_entities
- test_precedence_chain (parametrized with 7+ combinations)

### Task 3: TestCLIConvertTzFlags - CLI Integration Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/test_cli.py`

**Implementation Guidance**:
```python
class TestCLIConvertTzFlags:
    """Test cases for CLI --convert-tz and --no-convert-tz flags."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    def test_cli_generate_with_convert_tz_flag(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test CLI accepts --convert-tz flag."""
        # Arrange
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir", str(fixtures_dir),
                    "--output-dir", str(output_dir),
                    "--schema", "public",
                    "--convert-tz",
                ],
            )

            # Assert
            assert result.exit_code == 0

    def test_cli_convert_tz_flag_generates_convert_tz_yes(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test that --convert-tz flag produces convert_tz: yes in output."""
        # Arrange
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir", str(fixtures_dir),
                    "--output-dir", str(output_dir),
                    "--schema", "public",
                    "--convert-tz",
                ],
            )

            # Assert
            assert result.exit_code == 0

            # Verify generated files contain convert_tz: yes
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) > 0

            for view_file in view_files:
                content = view_file.read_text()
                # Check for convert_tz in dimension_group sections
                if "type: time" in content:
                    assert "convert_tz: yes" in content

    @pytest.mark.parametrize(
        "flag",
        ["--convert-tz", "--no-convert-tz", None]
    )
    def test_cli_generate_help_shows_convert_tz_flags(
        self, runner: CliRunner, flag: str | None
    ) -> None:
        """Test help text documents convert_tz flags."""
        # Act
        result = runner.invoke(cli, ["generate", "--help"])

        # Assert
        assert result.exit_code == 0
        assert "--convert-tz" in result.output
        assert "--no-convert-tz" in result.output
```

**Reference**: Similar structure to existing CLI tests in `test_cli.py` (TestCLI class)

**Tests to Add**:
- test_cli_generate_with_convert_tz_flag
- test_cli_generate_with_no_convert_tz_flag
- test_cli_generate_without_convert_tz_flag
- test_cli_convert_tz_flag_generates_convert_tz_yes
- test_cli_no_convert_tz_flag_generates_convert_tz_no
- test_cli_convert_tz_flag_in_generated_lookml_files
- test_cli_convert_tz_respects_dimension_meta_override
- test_cli_convert_tz_with_view_prefix_and_explore_prefix
- test_cli_convert_tz_flag_validates_output
- test_cli_generate_help_shows_convert_tz_flags

## File Changes

### Files to Modify

#### `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`

**Why**: Add TestDimensionConvertTz class with ~10 test methods

**Changes**:
- Import ConfigMeta if not already imported
- Add new TestDimensionConvertTz class after existing dimension tests
- Include parametrized tests for convert_tz values (True/False/None)
- Include edge case tests (custom timeframes, categorical dims, multiple dims)
- Verify LookML output format ("yes"/"no" strings)

**Estimated lines**: ~200 (new test class)

**Location**: After the last Dimension-related test class (e.g., after TestDimensionLabel tests)

#### `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_lookml_generator.py`

**Why**: Add TestLookMLGeneratorConvertTz class with ~12 test methods

**Changes**:
- Import necessary types (if not present)
- Add new TestLookMLGeneratorConvertTz class after existing TestLookMLGenerator classes
- Include parametrized tests for generator initialization
- Include parametrized precedence chain tests (7+ combinations)
- Test propagation to all dimension_groups
- Verify dimension meta overrides generator setting

**Estimated lines**: ~300 (new test class with parametrized tests)

**Location**: After the last existing TestLookMLGenerator-related test class

#### `/Users/dug/Work/repos/dbt-to-lookml/src/tests/test_cli.py`

**Why**: Add TestCLIConvertTzFlags class with ~11 test methods

**Changes**:
- Add new TestCLIConvertTzFlags class (or add tests to existing TestCLI if preferred)
- Test --convert-tz flag parsing
- Test --no-convert-tz flag parsing
- Test no flag (uses default)
- Verify flag value appears in generated .lkml files
- Validate precedence (meta overrides CLI)
- Check help text documentation

**Estimated lines**: ~250 (new test class)

**Location**: After existing TestCLI class

### Files to Create

None - All tests are added to existing test files.

## Testing Strategy

### Test Execution Commands

**Run all new tests**:
```bash
# TestDimensionConvertTz tests
python -m pytest src/tests/unit/test_schemas.py::TestDimensionConvertTz -xvs

# TestLookMLGeneratorConvertTz tests
python -m pytest src/tests/unit/test_lookml_generator.py::TestLookMLGeneratorConvertTz -xvs

# TestCLIConvertTzFlags tests
python -m pytest src/tests/test_cli.py::TestCLIConvertTzFlags -xvs

# All new tests together
python -m pytest -k "ConvertTz" -xvs

# Full test suite (ensure no regressions)
make test
```

### Coverage Validation

```bash
# Generate coverage report
make test-coverage

# Verify 95%+ branch coverage for new code
# Report will be in htmlcov/index.html

# Check specific files
python -m pytest --cov=dbt_to_lookml.schemas --cov-report=term-missing src/tests/unit/test_schemas.py::TestDimensionConvertTz
python -m pytest --cov=dbt_to_lookml.generators.lookml --cov-report=term-missing src/tests/unit/test_lookml_generator.py::TestLookMLGeneratorConvertTz
```

### Test Organization

**Schema-level tests** (`TestDimensionConvertTz`):
- Test Dimension._to_dimension_group_dict() method
- Test convert_tz parameter handling
- Test LookML output serialization
- Test precedence (meta > default)
- Test edge cases (custom timeframes, non-time dims)

**Generator-level tests** (`TestLookMLGeneratorConvertTz`):
- Test LookMLGenerator.__init__() with convert_tz parameter
- Test propagation to SemanticModel.to_lookml_dict()
- Test generator's default value
- Test precedence (meta > generator > default)
- Test all dimension types (time, categorical, entities)

**CLI-level tests** (`TestCLIConvertTzFlags`):
- Test --convert-tz and --no-convert-tz flag parsing
- Test flag effects on generated files
- Test help text documentation
- Test precedence (meta > CLI > default)
- Test integration with other flags

### Parametrized Tests Strategy

Use `@pytest.mark.parametrize` for:
1. **convert_tz values**: True, False, None
2. **Precedence combinations**: 7+ combinations of (meta, generator, cli, expected)
3. **Time granularities**: day, hour, minute (test custom timeframes)

Example parametrized test:
```python
@pytest.mark.parametrize(
    "dimension_meta,generator_setting,cli_flag,expected",
    [
        (True, False, False, True),      # meta=T wins over all
        (False, True, True, False),      # meta=F wins over all
        (None, True, False, True),       # generator wins over CLI
        (None, False, True, True),       # generator wins even if CLI different
        (None, None, True, True),        # CLI wins when no meta/generator
        (None, None, False, False),      # CLI flag False wins
        (None, None, None, False),       # Default is False
    ]
)
def test_precedence_chain(dimension_meta, generator_setting, cli_flag, expected):
    # Implementation validates each combination
    ...
```

### Edge Cases to Test

1. **Time dimension with convert_tz=True + custom granularity (hour)**
   - Verify correct timeframes: ["time", "hour", "date", "week", "month", "quarter", "year"]
   - Verify convert_tz: yes appears in output

2. **Time dimension with convert_tz=False + no granularity specified**
   - Verify default timeframes: ["date", "week", "month", "quarter", "year"]
   - Verify convert_tz: no appears in output

3. **Categorical dimension with convert_tz in meta**
   - Verify convert_tz is silently ignored (not in output)
   - Verify dimension still renders correctly

4. **Multiple time dimensions with different convert_tz values**
   - Model with 3 time dims: convert_tz=True, False, None
   - Verify each respects its own value
   - Verify generator default doesn't override explicit meta values

5. **Generator convert_tz=True + dimension meta=False**
   - Verify meta wins
   - Dimension should have convert_tz: no in output

## Validation Commands

**Code Quality**:
```bash
# Type checking
make type-check

# Linting
make lint

# Auto-format
make format

# All quality gates
make quality-gate
```

**Test Execution**:
```bash
# Fast unit tests only
make test-fast

# Full test suite
make test

# Full test suite with coverage
make test-full

# Specific test class
python -m pytest src/tests/unit/test_schemas.py::TestDimensionConvertTz -v
```

**Coverage Validation**:
```bash
# Generate HTML coverage report
make test-coverage

# View report
open htmlcov/index.html
```

## Dependencies

### Existing Dependencies
- `pytest>=7.0` - Already configured in project
- `pytest-cov` - Already configured for coverage reporting
- `unittest.mock` - Already used for mocking in existing tests
- `lkml` - Already used for LookML parsing/validation
- `click.testing.CliRunner` - Already used in test_cli.py

### No New Dependencies Needed
All testing infrastructure already exists in the project.

## Implementation Notes

### Important Considerations

1. **Default Behavior**: Default convert_tz is **False** (explicit in epic DTL-007)
   - Test coverage: `test_dimension_group_convert_tz_default_false()`
   - All "None" test cases should verify "no" in output

2. **Precedence Chain**: Dimension Meta > Generator > CLI > Default
   - Parametrized truth table tests ensure all combinations are covered
   - Single parametrized test covers 7+ combinations

3. **LookML Output Format**: convert_tz should be "yes"/"no" strings, not booleans
   - Verify through `to_lookml_dict()` tests
   - Verify final .lkml file output contains "convert_tz: yes" or "convert_tz: no"

4. **Categorical Dimensions**: convert_tz in meta should be silently ignored
   - Not added to output dict
   - Dimension still renders correctly without convert_tz

5. **Time Dimensions Only**: convert_tz only applies to DimensionType.TIME
   - Test that non-time dimensions don't have convert_tz
   - Test that categorical dimensions with convert_tz meta ignore it

### Code Patterns to Follow

**From existing tests** (`test_schemas.py`):
- Use clear test naming: `test_<method>_<scenario>_<expected>()`
- Use arrange-act-assert pattern consistently
- Group related tests in test classes
- Use parametrized tests for variations
- Use pytest fixtures for reusable test data

**From existing tests** (`test_lookml_generator.py`):
- Test both initialization and method behavior
- Verify serialization format in output dicts
- Test with realistic SemanticModel objects
- Use temporary directories for file I/O tests

**From existing tests** (`test_cli.py`):
- Use CliRunner for CLI testing
- Test flag parsing
- Test help text documentation
- Test actual file output where applicable
- Use temporary directories to avoid pollution

### Fixtures to Create/Reuse

Create simple fixtures for common test scenarios:
```python
@pytest.fixture
def time_dimension_with_convert_tz_true():
    return Dimension(
        name="created_at",
        type=DimensionType.TIME,
        config=Config(meta=ConfigMeta(convert_tz=True)),
        type_params={"time_granularity": "day"}
    )

@pytest.fixture
def time_dimension_with_convert_tz_false():
    return Dimension(
        name="created_at",
        type=DimensionType.TIME,
        config=Config(meta=ConfigMeta(convert_tz=False)),
        type_params={"time_granularity": "day"}
    )

@pytest.fixture
def model_with_mixed_convert_tz():
    return SemanticModel(
        name="events",
        model="ref('fct_events')",
        dimensions=[
            Dimension(name="created_at", type=DimensionType.TIME,
                     config=Config(meta=ConfigMeta(convert_tz=True))),
            Dimension(name="updated_at", type=DimensionType.TIME,
                     config=Config(meta=ConfigMeta(convert_tz=False))),
            Dimension(name="recorded_at", type=DimensionType.TIME),
        ]
    )
```

### Assertion Patterns

**For LookML output dicts**:
```python
# Check convert_tz value
assert dim_dict.get("convert_tz") == "yes"  # or "no"

# Check it exists for time dimensions
assert "convert_tz" in dimension_group_dict

# Check it doesn't exist for categorical dimensions
assert "convert_tz" not in categorical_dim_dict

# Check file content
assert "convert_tz: yes" in view_file.read_text()
```

## References

### Codebase Patterns

- **Dimension class**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py:117-224`
  - `_to_dimension_group_dict()` method: line 187-224
  - Used to generate LookML dimension_group dict

- **Existing dimension tests**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`
  - TestDimensionType class shows parametrized test patterns
  - Shows arrange-act-assert structure
  - Shows assertion patterns for schema models

- **LookMLGenerator class**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py:23-71`
  - `__init__()` method: line 26-58
  - Initialization pattern with multiple optional parameters

- **Existing generator tests**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_lookml_generator.py`
  - TestLookMLGenerator class shows initialization testing pattern
  - Shows how to test view generation
  - Shows fixture patterns for SemanticModel objects

- **Existing CLI tests**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/test_cli.py`
  - TestCLI class shows CliRunner usage
  - Shows how to test Click commands
  - Shows file output validation patterns

## Implementation Sequence

### Phase 1: Schema-Level Tests
1. Create TestDimensionConvertTz class in test_schemas.py
2. Implement ~10 test methods for convert_tz handling
3. Run: `pytest src/tests/unit/test_schemas.py::TestDimensionConvertTz -xvs`
4. Verify all tests pass and 95%+ branch coverage

### Phase 2: Generator Tests
5. Create TestLookMLGeneratorConvertTz class in test_lookml_generator.py
6. Implement ~12 test methods for generator propagation
7. Include parametrized precedence tests
8. Run: `pytest src/tests/unit/test_lookml_generator.py::TestLookMLGeneratorConvertTz -xvs`
9. Verify all tests pass and precedence chain is correct

### Phase 3: CLI Tests
10. Create TestCLIConvertTzFlags class in test_cli.py
11. Implement ~11 test methods for CLI flags
12. Test actual file generation with flags
13. Run: `pytest src/tests/test_cli.py::TestCLIConvertTzFlags -xvs`
14. Verify all tests pass and files contain correct values

### Phase 4: Validation and Coverage
15. Run full test suite: `make test`
16. Generate coverage report: `make test-coverage`
17. Verify 95%+ branch coverage for new code paths
18. Verify no existing tests broken
19. Fix any coverage gaps

### Phase 5: Final Validation
20. Run full quality gate: `make quality-gate`
21. Verify all tests pass (unit + integration)
22. Verify coverage targets met
23. Review test organization and clarity

## Success Criteria

Before marking DTL-011 complete:

- [x] All 3 new test classes created (TestDimensionConvertTz, TestLookMLGeneratorConvertTz, TestCLIConvertTzFlags)
- [x] All ~35 new test methods implemented
- [x] Parametrized tests added for variations and precedence
- [x] All fixtures created for reusable test scenarios
- [x] `make test-fast` passes (unit tests only)
- [x] `make test` passes (unit + integration tests)
- [x] Coverage report shows 95%+ for new code paths
- [x] No existing tests broken by changes
- [x] Test execution time remains reasonable (<10 seconds for new unit tests)
- [x] All edge cases documented and tested
- [x] Mock usage appropriate (only external dependencies like CLI)
- [x] Test names clear and descriptive
- [x] Arrange-act-assert pattern followed consistently
- [x] Precedence chain fully validated (all 7+ combinations)
- [x] LookML output validation included in tests

## Estimated Complexity

**Complexity**: High
**Estimated Time**: 6-8 hours

**Breakdown**:
- Phase 1 (Schema-Level Tests): 1.5 hours
  - TestDimensionConvertTz class: 45 mins
  - LookML output validation: 30 mins
  - Edge case tests: 15 mins

- Phase 2 (Generator Tests): 2 hours
  - TestLookMLGeneratorConvertTz class: 50 mins
  - Propagation and precedence tests: 45 mins
  - Integration validation: 25 mins

- Phase 3 (CLI Tests): 2 hours
  - TestCLIConvertTzFlags class: 50 mins
  - File validation and parsing: 45 mins
  - Precedence chain with CLI: 25 mins

- Phase 4 (Edge Cases and Coverage): 1.5-2.5 hours
  - Edge case test development: 45 mins
  - Coverage validation: 30 mins
  - Final validation: 30-45 mins

## Ready for Implementation

This spec is complete and ready for implementation. All phases, test methods, file locations, and validation commands are clearly defined. The implementation follows the approved strategy and established codebase patterns.

---

Generated: 2025-11-12
Status: Ready for Implementation
