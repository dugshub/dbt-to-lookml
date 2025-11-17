# Implementation Strategy: DTL-011

**Issue**: DTL-011 - Add comprehensive unit tests for timezone conversion
**Analyzed**: 2025-11-12T20:45:00Z
**Stack**: backend (testing)
**Type**: feature

## Approach

Create comprehensive unit tests for timezone conversion behavior across all three configuration layers (schema, generator, CLI) and validate the precedence chain (dimension meta > generator > CLI > default). The testing strategy validates that timezone conversion configuration is properly handled at each level and that the precedence rules are correctly implemented.

The testing approach follows pytest best practices with clear arrange-act-assert structure, parametrized tests for variations, and proper use of fixtures. Tests are organized into logical test classes that mirror the code structure being tested (schemas, generator, CLI) and provide clear documentation of expected behavior across all configuration levels.

## Architecture Impact

**Layer**: tests/unit and tests/integration (testing)

**New Files**: None

**Modified Files**:
- `src/tests/unit/test_schemas.py` - Add test cases for Dimension convert_tz handling
  - Add new test class: `TestDimensionConvertTz` for schema-level timezone conversion
  - Tests for convert_tz with explicit True, explicit False, and default (None)
  - Tests for meta override precedence
  - Tests for convert_tz in generated LookML output
- `src/tests/unit/test_lookml_generator.py` - Add test cases for generator propagation
  - Add new test class: `TestLookMLGeneratorConvertTz` for generator-level propagation
  - Tests for generator initialization with convert_tz parameter
  - Tests for default propagation to dimension_groups
  - Tests for dimension meta overriding generator setting
- `src/tests/test_cli.py` - Add test cases for CLI flags
  - Add new test class: `TestCLIConvertTzFlags` for CLI flag handling
  - Tests for `--convert-tz` flag
  - Tests for `--no-convert-tz` flag
  - Tests for no flag (uses default)
  - Tests for validate output contains correct convert_tz values

## Dependencies

**Depends on**:
- DTL-008 (Dimension schema convert_tz support) - blocking dependency
- DTL-009 (LookMLGenerator convert_tz propagation) - blocking dependency
- DTL-010 (CLI flags for timezone conversion) - blocking dependency

**Testing Framework**:
- `pytest>=7.0` - Already configured in project
- `pytest-cov` - Already configured for coverage reporting
- `unittest.mock` - Already used for mocking in existing tests
- `lkml` - Already used for LookML parsing/validation

**Test Patterns**:
- Follow existing test organization in `test_schemas.py` and `test_lookml_generator.py`
- Use test classes to group related tests (e.g., `TestDimensionConvertTz`)
- Use clear test naming: `test_<method>_<convert_tz_state>_<scenario>()`
- Follow arrange-act-assert pattern consistently
- Use `@pytest.mark.parametrize` for testing variations (True/False/None)
- Mock external dependencies (e.g., Click runner) where needed

## Testing Strategy

### Coverage Requirements

**Target**: 95%+ branch coverage for new code paths
**Current baseline**: Existing tests maintain ~95% coverage
**New code to cover**:
- Dimension._to_dimension_group_dict() with convert_tz parameter (all branches)
- Dimension.get_dimension_labels() or helper for meta reading (all branches)
- LookMLGenerator.__init__() with convert_tz parameter
- LookMLGenerator._generate_view_lookml() propagation to SemanticModel.to_lookml_dict()
- SemanticModel.to_lookml_dict() with convert_tz parameter propagation
- CLI generate command with --convert-tz and --no-convert-tz flags
- Precedence chain: dimension meta > generator > CLI > default

### Test Organization

#### 1. TestDimensionConvertTz (New Class in test_schemas.py)

Tests for the Dimension schema's convert_tz handling and LookML output.

**Test Cases**:
- `test_dimension_group_convert_tz_explicit_true()` - dimension with convert_tz=True in meta
- `test_dimension_group_convert_tz_explicit_false()` - dimension with convert_tz=False in meta
- `test_dimension_group_convert_tz_none()` - dimension with no convert_tz (uses default)
- `test_dimension_group_convert_tz_default_false()` - default behavior is convert_tz: no
- `test_dimension_group_convert_tz_precedence_meta_overrides_default()` - verify meta=True overrides default=False
- `test_dimension_group_convert_tz_precedence_meta_false_overrides_true_default()` - verify meta=False overrides default=True
- `test_dimension_group_convert_tz_in_lookml_output()` - verify "convert_tz: yes" or "convert_tz: no" appears in dict
- `test_dimension_convert_tz_ignored_for_non_time_dimensions()` - categorical dimensions ignore convert_tz
- `test_dimension_group_with_custom_timeframes_respects_convert_tz()` - convert_tz works with custom granularity
- `test_multiple_dimensions_different_convert_tz_settings()` - model with mixed convert_tz settings

**Edge Cases**:
- Time dimension with convert_tz=True, granularity=hour → Should have correct timeframes + convert_tz
- Time dimension with convert_tz=False, no granularity specified → Default timeframes + convert_tz: no
- Categorical dimension with convert_tz in meta → Ignored (not added to output)
- Multiple time dimensions with different convert_tz values → Each respects its own value

#### 2. TestLookMLGeneratorConvertTz (New Class in test_lookml_generator.py)

Tests for the LookMLGenerator's convert_tz parameter and propagation to dimensions.

**Test Cases**:
- `test_generator_initialization_with_convert_tz_true()` - generator accepts convert_tz=True
- `test_generator_initialization_with_convert_tz_false()` - generator accepts convert_tz=False
- `test_generator_initialization_with_convert_tz_none()` - generator accepts convert_tz=None (default)
- `test_generator_propagates_convert_tz_to_dimensions()` - generator's convert_tz propagates to dimension_groups
- `test_generator_convert_tz_propagation_default_false()` - default generator convert_tz is False
- `test_dimension_meta_overrides_generator_convert_tz_true()` - dimension meta=True overrides generator=False
- `test_dimension_meta_overrides_generator_convert_tz_false()` - dimension meta=False overrides generator=True
- `test_generator_convert_tz_affects_all_dimension_groups()` - all time dimensions in view get generator's convert_tz
- `test_generator_convert_tz_with_view_containing_categorical_and_time_dims()` - only time dims affected
- `test_generate_view_lookml_contains_convert_tz()` - final LookML output contains convert_tz values
- `test_mixed_dimension_meta_with_generator_convert_tz()` - some dimensions override, others use generator default
- `test_generator_convert_tz_with_entities()` - entities are not affected by convert_tz (they're not time dims)

**Edge Cases**:
- Generator convert_tz=True + dimension meta=False → Meta wins, dimension has convert_tz: no
- Generator convert_tz=None + dimension meta=True → Generator uses default, dimension meta=True overrides
- View with only categorical dimensions + generator convert_tz=True → No effect on output
- View with only time dimensions + generator convert_tz=False → All get convert_tz: no

#### 3. TestCLIConvertTzFlags (New Class in test_cli.py)

Tests for CLI flag handling and integration with generator.

**Test Cases**:
- `test_cli_generate_with_convert_tz_flag()` - CLI accepts --convert-tz flag
- `test_cli_generate_with_no_convert_tz_flag()` - CLI accepts --no-convert-tz flag
- `test_cli_generate_without_convert_tz_flag()` - CLI without flag uses default
- `test_cli_convert_tz_flag_generates_convert_tz_yes()` - --convert-tz produces convert_tz: yes
- `test_cli_no_convert_tz_flag_generates_convert_tz_no()` - --no-convert-tz produces convert_tz: no
- `test_cli_convert_tz_flag_in_generated_lookml_files()` - flag value appears in actual files
- `test_cli_convert_tz_respects_dimension_meta_override()` - dimension meta overrides CLI flag
- `test_cli_convert_tz_with_view_prefix_and_explore_prefix()` - convert_tz works with other flags
- `test_cli_convert_tz_flag_validates_output()` - validation passes with correct convert_tz values
- `test_cli_generate_help_shows_convert_tz_flags()` - help text documents new flags
- `test_cli_convert_tz_and_no_convert_tz_mutual_exclusivity()` - can't use both flags together (if validated)

**Edge Cases**:
- Both --convert-tz and --no-convert-tz passed → Should error or use sensible default
- CLI convert_tz=yes + dimension meta=no → Meta wins
- Very large model + convert_tz flag → Performance not degraded

### Precedence Testing Strategy

Create parametrized tests specifically for precedence chain validation:

**Precedence: Dimension Meta > Generator > CLI > Default**

```python
@pytest.mark.parametrize(
    "dimension_meta,generator_setting,cli_flag,expected",
    [
        (True, False, False, True),      # meta=T wins over all others
        (False, True, True, False),      # meta=F wins over all others
        (None, True, False, True),       # generator wins over CLI
        (None, False, True, True),       # generator wins, even if CLI different
        (None, None, True, True),        # CLI wins when no meta/generator
        (None, None, False, False),      # CLI wins
        (None, None, None, False),       # Default is False
    ]
)
def test_precedence_chain(dimension_meta, generator_setting, cli_flag, expected):
    # Test that precedence rules are correctly implemented
    ...
```

## Implementation Sequence

### Phase 1: Schema-Level Tests (depends on DTL-008)

1. **Create TestDimensionConvertTz class in test_schemas.py**
   - Add basic convert_tz tests (True/False/None)
   - Test default behavior (convert_tz: no)
   - Test meta override precedence
   - Run: `python -m pytest src/tests/unit/test_schemas.py::TestDimensionConvertTz -xvs`

2. **Add LookML output validation tests**
   - Test convert_tz appears in dimension_group dict
   - Test correct serialization ("yes"/"no" strings)
   - Test categorical dimensions ignore convert_tz
   - Verify timeframes are not affected by convert_tz

3. **Add edge case tests**
   - Time dimension with custom granularity + convert_tz
   - Multiple time dimensions with different settings
   - Convert_tz=False with custom timeframes (hour/minute)

### Phase 2: Generator Tests (depends on DTL-009)

4. **Create TestLookMLGeneratorConvertTz class in test_lookml_generator.py**
   - Test generator initialization with convert_tz parameter
   - Test convert_tz propagation to all dimension_groups
   - Run: `python -m pytest src/tests/unit/test_lookml_generator.py::TestLookMLGeneratorConvertTz -xvs`

5. **Add precedence tests**
   - Dimension meta overrides generator setting
   - Generator setting becomes default for dimensions without meta
   - Test with mixed scenarios (some dims with meta, some without)

6. **Add integration tests**
   - Test generate_view_lookml() produces correct convert_tz in output
   - Test with all dimension types (categorical, time)
   - Test with all entity types

### Phase 3: CLI Tests (depends on DTL-010)

7. **Create TestCLIConvertTzFlags class in test_cli.py**
   - Test --convert-tz flag parsing
   - Test --no-convert-tz flag parsing
   - Test help text documentation
   - Run: `python -m pytest src/tests/test_cli.py::TestCLIConvertTzFlags -xvs`

8. **Add file validation tests**
   - Run generate with --convert-tz flag
   - Verify generated .lkml files contain correct convert_tz values
   - Validate with lkml library that files are parseable

9. **Add precedence chain tests**
   - CLI flag + dimension meta (meta should win)
   - CLI flag + generator convert_tz (which has priority?)
   - Full precedence chain from CLI to dimension

### Phase 4: Edge Cases and Coverage

10. **Add comprehensive edge case tests**
    - convert_tz=True with all supported time granularities
    - convert_tz=False with all supported time granularities
    - Empty view with time dimension + convert_tz
    - Large number of time dimensions with mixed convert_tz

11. **Verify test coverage**
    - Run: `make test-coverage`
    - Ensure 95%+ branch coverage for:
      - Dimension._to_dimension_group_dict() with convert_tz parameter
      - LookMLGenerator.__init__() with convert_tz parameter
      - SemanticModel.to_lookml_dict() propagation
      - CLI flag parsing and validation
    - Identify and add tests for any uncovered branches

12. **Validate test execution**
    - Run: `make test-fast` (unit tests only)
    - Run: `make test` (unit + integration)
    - Ensure all tests pass
    - Verify no performance degradation

## Test Fixture Strategy

### Reusable Fixtures

Create helper fixtures for common test scenarios:

```python
# Fixture: Time dimension with convert_tz in meta
@pytest.fixture
def time_dimension_with_convert_tz_true():
    return Dimension(
        name="created_at",
        type=DimensionType.TIME,
        config=Config(
            meta=ConfigMeta(convert_tz=True)
        ),
        type_params={"time_granularity": "day"}
    )

# Fixture: Time dimension with convert_tz=False in meta
@pytest.fixture
def time_dimension_with_convert_tz_false():
    return Dimension(
        name="created_at",
        type=DimensionType.TIME,
        config=Config(
            meta=ConfigMeta(convert_tz=False)
        ),
        type_params={"time_granularity": "day"}
    )

# Fixture: Semantic model with mixed convert_tz dimensions
@pytest.fixture
def model_with_mixed_convert_tz():
    return SemanticModel(
        name="events",
        model="ref('fct_events')",
        dimensions=[
            Dimension(
                name="created_at",
                type=DimensionType.TIME,
                config=Config(meta=ConfigMeta(convert_tz=True))
            ),
            Dimension(
                name="updated_at",
                type=DimensionType.TIME,
                config=Config(meta=ConfigMeta(convert_tz=False))
            ),
            Dimension(
                name="recorded_at",
                type=DimensionType.TIME,
                # No meta, will use generator/default
            ),
        ]
    )

# Fixture: CLI runner
@pytest.fixture
def cli_runner():
    return CliRunner()

# Fixture: Semantic models directory
@pytest.fixture
def semantic_models_dir():
    return Path(__file__).parent.parent / "semantic_models"
```

### Expected Output Patterns

Use parametrized tests for common assertion patterns:

```python
@pytest.mark.parametrize(
    "convert_tz,expected_lookml_value",
    [
        (True, "yes"),
        (False, "no"),
        (None, "no"),  # Default is False
    ]
)
def test_dimension_group_convert_tz_output(convert_tz, expected_lookml_value):
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        config=Config(meta=ConfigMeta(convert_tz=convert_tz))
        if convert_tz is not None else None
    )
    result = dim._to_dimension_group_dict()
    assert result.get("convert_tz") == expected_lookml_value
```

## Open Questions

### 1. Default Behavior Confirmation
**Question**: Should default convert_tz be False or True?
**Answer**: Default is False (explicit in epic DTL-007: "convert_tz: no - disable by default")
**Test Coverage**: `test_dimension_group_convert_tz_default_false()`

### 2. CLI Flag Validation
**Question**: What if both --convert-tz and --no-convert-tz are passed?
**Recommendation**: Implement mutual exclusivity check in DTL-010, test that error is raised
**Test Coverage**: `test_cli_convert_tz_mutual_exclusivity()` (if applicable)

### 3. LookML Output Format
**Question**: Should convert_tz be "yes"/"no" strings or boolean values in output dict?
**Answer**: "yes"/"no" strings (LookML convention - see existing patterns in codebase)
**Test Coverage**: Verify through `_to_dimension_group_dict()` tests

### 4. Categorical Dimension Behavior
**Question**: Should convert_tz in meta for categorical dimensions be silently ignored?
**Answer**: Yes, only applies to time dimensions, others ignore it
**Test Coverage**: `test_dimension_convert_tz_ignored_for_non_time_dimensions()`

### 5. Serialization Order
**Question**: Where does convert_tz appear in dimension_group dict relative to other fields?
**Recommendation**: Add test to verify position (after type/timeframes, before/after sql)
**Test Coverage**: Add assertion for dict key ordering if important

## Coverage Target Breakdown

### New Code Coverage (Target: 95%+)

**Dimension._to_dimension_group_dict() method**:
- Branch: convert_tz=True → Covered by `test_dimension_group_convert_tz_explicit_true()`
- Branch: convert_tz=False → Covered by `test_dimension_group_convert_tz_explicit_false()`
- Branch: convert_tz=None (use default) → Covered by `test_dimension_group_convert_tz_none()`
- Branch: Default applied → Covered by `test_dimension_group_convert_tz_default_false()`
- Branch: Meta overrides default → Covered by `test_dimension_group_convert_tz_precedence_meta_overrides_default()`

**LookMLGenerator.__init__() method**:
- Branch: convert_tz=True stored → Covered by `test_generator_initialization_with_convert_tz_true()`
- Branch: convert_tz=False stored → Covered by `test_generator_initialization_with_convert_tz_false()`
- Branch: convert_tz=None stored → Covered by `test_generator_initialization_with_convert_tz_none()`

**LookMLGenerator propagation**:
- Branch: Propagate to dimension_groups → Covered by `test_generator_propagates_convert_tz_to_dimensions()`
- Branch: Dimension meta overrides → Covered by `test_dimension_meta_overrides_generator_convert_tz_true()`
- Branch: All dimensions get setting → Covered by `test_generator_convert_tz_affects_all_dimension_groups()`

**SemanticModel.to_lookml_dict() propagation**:
- Branch: Apply generator convert_tz to each dimension → Covered by generator tests above
- Branch: Dimension meta overrides generator → Covered by precedence tests

**CLI flag handling**:
- Branch: --convert-tz parsed → Covered by `test_cli_generate_with_convert_tz_flag()`
- Branch: --no-convert-tz parsed → Covered by `test_cli_generate_with_no_convert_tz_flag()`
- Branch: No flag provided → Covered by `test_cli_generate_without_convert_tz_flag()`
- Branch: Flag value propagated to generator → Covered by `test_cli_convert_tz_flag_generates_convert_tz_yes()`

**Precedence chain**:
- All combinations covered by parametrized test: `test_precedence_chain()`

### Existing Test Updates

Update existing tests to verify convert_tz doesn't break them:
- ~3 tests in `TestDimensionType` → Add convert_tz assertions
- ~2 tests in `TestLookMLGenerator` initialization → Verify convert_tz parameter accepted
- ~2 tests in `TestCLI` generate command → Verify new flags appear in help

## Validation Checklist

Before marking DTL-011 complete:

- [ ] TestDimensionConvertTz class created with ~12 test methods
- [ ] TestLookMLGeneratorConvertTz class created with ~12 test methods
- [ ] TestCLIConvertTzFlags class created with ~11 test methods
- [ ] Parametrized precedence tests added (~8 test combinations)
- [ ] All new test classes implemented (~35+ new test methods)
- [ ] All fixtures created for reusable test scenarios
- [ ] `make test-fast` passes (unit tests)
- [ ] `make test` passes (unit + integration)
- [ ] Coverage report shows 95%+ for new code paths
- [ ] No existing tests broken by changes
- [ ] Test execution time remains reasonable (<10 seconds for new unit tests)
- [ ] All edge cases documented and tested
- [ ] Mock usage is appropriate (only for external dependencies like CLI)
- [ ] Test names are clear and descriptive
- [ ] Arrange-act-assert pattern followed consistently
- [ ] Precedence chain fully validated
- [ ] LookML output validation included in tests

## Estimated Complexity

**Complexity**: High
**Estimated Time**: 6-8 hours

**Breakdown**:
- Phase 1 (Schema-Level Tests): 1.5 hours
  - TestDimensionConvertTz class creation: 45 mins
  - LookML output validation: 30 mins
  - Edge case tests: 15 mins
- Phase 2 (Generator Tests): 2 hours
  - TestLookMLGeneratorConvertTz class creation: 50 mins
  - Propagation and precedence tests: 45 mins
  - Integration validation: 25 mins
- Phase 3 (CLI Tests): 2 hours
  - TestCLIConvertTzFlags class creation: 50 mins
  - File validation and parsing: 45 mins
  - Precedence chain with CLI: 25 mins
- Phase 4 (Edge Cases and Coverage): 1.5-2.5 hours
  - Edge case test development: 45 mins
  - Coverage validation and gap identification: 30 mins
  - Final validation and fixes: 30-45 mins

---

## Key Strategic Decisions

### 1. Three-Layer Testing Approach
**Decision**: Create separate test classes for each configuration layer (Schema, Generator, CLI).
**Rationale**: Mirrors the actual system architecture, makes it clear where configuration is validated, simplifies debugging when tests fail.

### 2. Parametrized Precedence Testing
**Decision**: Use parametrized tests with truth table for precedence chain validation.
**Rationale**: Ensures all combinations are tested systematically, easy to add new combinations if precedence changes, prevents accidental regressions.

### 3. LookML Output Validation
**Decision**: Include assertions for actual LookML output format (strings "yes"/"no") not just internal state.
**Rationale**: Validates the actual artifact users depend on, catches serialization bugs early.

### 4. Fixture Strategy
**Decision**: Create reusable fixtures for common dimension/model configurations rather than inline creation.
**Rationale**: Reduces test code duplication, improves readability, makes it easier to maintain consistent test data.

### 5. Integration Points
**Decision**: Include CLI file generation tests that verify final .lkml files contain correct values.
**Rationale**: Tests the complete end-to-end flow, catches integration issues between layers.

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-011.md`
3. Change status from `refinement` to `awaiting-strategy-review`
4. After review approval, change to `strategy-approved`
5. Run: `/implement:1-spec DTL-011`
