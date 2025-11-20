---
id: DTL-034-strategy
issue_id: DTL-034
title: "Strategy: Update test suite for time dimension organization features"
created: 2025-11-19
status: approved
---

# Strategy: Update test suite for time dimension organization features

## Overview

This strategy defines a comprehensive testing approach for the time dimension organization features (group_label and group_item_label) introduced in DTL-032 and DTL-033. The goal is to maintain the project's 95%+ branch coverage target while ensuring all new code paths, edge cases, and integration scenarios are properly tested.

## Testing Philosophy

Following the project's established testing patterns:
- **Unit tests**: Fast, isolated tests for individual components
- **Integration tests**: End-to-end tests for complete workflows
- **Golden tests**: Regression protection via expected output comparison
- **CLI tests**: Command-line interface testing with various flags
- **Coverage target**: 95%+ branch coverage for all modified modules

## Test Organization

### 1. Unit Tests (src/tests/unit/)

#### 1.1 Schema Tests (test_schemas.py)

**Location**: Extend `TestConfigMeta` and `TestDimension` classes

**Test Cases**:
```python
class TestConfigMetaTimeDimensionGroupLabel:
    """Test time_dimension_group_label configuration in ConfigMeta."""

    def test_configmeta_time_dimension_group_label_field_exists()
        # Test that ConfigMeta accepts time_dimension_group_label field
        # Verify: str | None type
        # Verify: None default

    def test_configmeta_time_dimension_group_label_with_custom_value()
        # Test setting custom group label
        # Verify: "Time Fields" value

    def test_configmeta_time_dimension_group_label_empty_string()
        # Test disabling grouping with empty string
        # Verify: "" value disables grouping
```

**Test Cases - Dimension._to_dimension_group_dict()**:
```python
class TestDimensionGroupLabel:
    """Test group_label generation logic in dimension_groups."""

    def test_dimension_group_label_from_meta_override()
        # Dimension with config.meta.time_dimension_group_label
        # Verify: meta value takes precedence

    def test_dimension_group_label_from_generator_default()
        # No meta, pass default_time_dimension_group_label parameter
        # Verify: parameter value used

    def test_dimension_group_label_hardcoded_default()
        # No meta, no parameter
        # Verify: "Time Dimensions" default

    def test_dimension_group_label_disabled_empty_string()
        # Meta with empty string ""
        # Verify: no group_label in output

    def test_dimension_group_label_disabled_none()
        # Meta with None value
        # Verify: uses parameter/default fallback

    def test_dimension_group_label_precedence_chain()
        # Comprehensive test of: meta > param > default
        # Verify: correct precedence in all scenarios
```

**Test Cases - group_item_label**:
```python
class TestGroupItemLabel:
    """Test group_item_label generation for timeframes."""

    def test_group_item_label_enabled()
        # use_group_item_label=True
        # Verify: group_item_label field in dimension_group

    def test_group_item_label_disabled()
        # use_group_item_label=False
        # Verify: no group_item_label field

    def test_group_item_label_with_custom_dimension_label()
        # Dimension has custom label + group_item_label enabled
        # Verify: correct label format

    def test_group_item_label_template_format()
        # Verify: "{{ _field._name | capitalize }}" format
```

**Coverage Target**: All new ConfigMeta and Dimension methods must have 95%+ branch coverage

---

#### 1.2 Generator Tests (test_lookml_generator.py)

**Location**: Extend `TestLookMLGenerator` class

**Test Cases - Generator Initialization**:
```python
class TestLookMLGeneratorTimeDimensionParams:
    """Test LookMLGenerator initialization with time dimension params."""

    def test_generator_with_time_dimension_group_label()
        # Initialize with time_dimension_group_label="Custom Label"
        # Verify: parameter stored correctly

    def test_generator_with_use_group_item_label_true()
        # Initialize with use_group_item_label=True
        # Verify: parameter stored correctly

    def test_generator_with_use_group_item_label_false()
        # Initialize with use_group_item_label=False (default)
        # Verify: default behavior

    def test_generator_with_both_params()
        # Both time_dimension_group_label and use_group_item_label
        # Verify: both parameters work together
```

**Test Cases - LookML Generation**:
```python
class TestTimeDimensionGroupGeneration:
    """Test time dimension group_label in generated LookML."""

    def test_generate_with_custom_group_label()
        # Generator with custom time_dimension_group_label
        # Create semantic model with time dimension
        # Verify: group_label appears in generated dict

    def test_generate_with_disabled_group_label()
        # Generator with time_dimension_group_label=""
        # Verify: no group_label in output

    def test_generate_respects_dimension_meta_override()
        # Dimension has meta.time_dimension_group_label
        # Generator has different default
        # Verify: dimension meta wins

    def test_generate_multiple_time_dimensions_same_group()
        # Multiple time dimensions, same group_label
        # Verify: all share same group_label

    def test_generate_multiple_time_dimensions_different_groups()
        # Time dimensions with different meta overrides
        # Verify: different group_labels correctly applied
```

**Coverage Target**: All new generator code paths must have 95%+ branch coverage

---

### 2. Integration Tests (src/tests/integration/)

#### 2.1 End-to-End Integration (test_end_to_end.py)

**Location**: Create new test class or extend existing

**Test Cases**:
```python
class TestTimeDimensionOrganizationIntegration:
    """Integration tests for time dimension organization features."""

    def test_parse_and_generate_with_time_dimension_grouping()
        # Parse semantic models with time dimensions
        # Generate with default grouping
        # Verify: group_label in all dimension_groups

    def test_parse_and_generate_with_custom_group_label()
        # Generate with custom time_dimension_group_label
        # Verify: custom label applied to all time dimension_groups

    def test_parse_and_generate_with_group_item_label()
        # Generate with use_group_item_label=True
        # Verify: group_item_label in dimension_groups

    def test_hierarchical_organization_in_full_pipeline()
        # Complete pipeline: parse -> generate -> validate
        # Multiple time dimensions per model
        # Verify: hierarchical structure in output
        # Verify: LookML syntax validation passes

    def test_precedence_dimension_meta_overrides_generator()
        # Fixture with dimension meta time_dimension_group_label
        # Generator with different default
        # Verify: dimension meta takes precedence

    def test_mixed_configuration_multiple_models()
        # Some dimensions with meta, some without
        # Multiple semantic models
        # Verify: each dimension respects its config
```

**Coverage Target**: End-to-end workflows with all configuration combinations

---

### 3. Golden Tests (test_golden.py)

#### 3.1 Golden File Updates

**Files to Update**:
- `tests/golden/expected_users.view.lkml`
- `tests/golden/expected_searches.view.lkml`
- `tests/golden/expected_rental_orders.view.lkml`
- `tests/golden/expected_explores.lkml` (if needed)

**Required Changes**:
```lookml
# BEFORE (current golden files)
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
}

# AFTER (updated golden files)
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
  group_label: "Time Dimensions"
}
```

**Test Cases**:
```python
class TestTimeDimensionGoldenFiles:
    """Test golden files include time dimension organization."""

    def test_golden_files_have_group_label()
        # Parse expected_*.view.lkml golden files
        # Verify: all dimension_groups have group_label: "Time Dimensions"

    def test_generate_matches_updated_golden()
        # Generate from semantic models
        # Compare with updated golden files
        # Verify: exact match including group_label

    def test_golden_with_custom_group_label()
        # New golden file with custom group_label
        # Verify: custom label preserved

    def test_golden_with_group_item_label()
        # Optional: golden file demonstrating group_item_label
        # Verify: format matches expected template
```

**Action Items**:
1. Update existing golden files to include `group_label: "Time Dimensions"`
2. Optionally create new golden file demonstrating custom group_label
3. Update `update_golden_files_if_requested()` helper method

---

### 4. CLI Tests (test_cli.py)

#### 4.1 CLI Flag Tests

**Location**: Create new test class `TestCLITimeDimensionFlags`

**Test Cases**:
```python
class TestCLITimeDimensionFlags:
    """Test CLI flags for time dimension organization."""

    def test_cli_generate_with_time_dimension_group_label_flag()
        # --time-dimension-group-label "Custom Label"
        # Verify: CLI accepts flag
        # Verify: generated files contain custom label

    def test_cli_generate_with_no_time_dimension_group_label_flag()
        # --no-time-dimension-group-label
        # Verify: disables grouping (empty string)
        # Verify: no group_label in generated files

    def test_cli_generate_with_use_group_item_label_flag()
        # --use-group-item-label
        # Verify: CLI accepts flag
        # Verify: group_item_label in generated dimension_groups

    def test_cli_generate_without_time_dimension_flags()
        # No flags (default behavior)
        # Verify: group_label: "Time Dimensions" in output

    def test_cli_flags_mutually_exclusive()
        # --time-dimension-group-label and --no-time-dimension-group-label
        # Verify: CLI rejects mutually exclusive flags

    def test_cli_help_shows_time_dimension_flags()
        # generate --help
        # Verify: help text documents new flags

    def test_cli_time_dimension_flags_with_other_flags()
        # Combine with --convert-tz, --view-prefix, etc.
        # Verify: all flags work together

    def test_cli_time_dimension_flag_with_dry_run()
        # --time-dimension-group-label with --dry-run
        # Verify: preview shows correct configuration
```

**Coverage Target**: All CLI flag combinations and error cases

---

### 5. Edge Case Tests

#### 5.1 Edge Cases to Cover

**Location**: Distributed across unit and integration tests

**Test Cases**:
```python
class TestTimeDimensionEdgeCases:
    """Edge cases for time dimension organization."""

    def test_no_time_dimensions_in_model()
        # Semantic model with only categorical dimensions
        # Verify: no errors, no group_label added

    def test_single_time_dimension()
        # Model with exactly one time dimension
        # Verify: group_label still applied (consistency)

    def test_time_dimension_with_no_label()
        # Dimension with no label field
        # Verify: group_item_label uses dimension name

    def test_empty_string_disables_both_labels()
        # time_dimension_group_label=""
        # Verify: neither group_label nor group_item_label

    def test_none_vs_empty_string_behavior()
        # None: use default
        # "": disable grouping
        # Verify: distinct behaviors

    def test_unicode_in_group_label()
        # Custom label with unicode characters
        # Verify: correct encoding in LookML

    def test_special_characters_in_group_label()
        # Label with quotes, brackets, etc.
        # Verify: proper escaping/handling

    def test_very_long_group_label()
        # Edge case: very long label string
        # Verify: no truncation, valid LookML
```

---

## Implementation Order

### Phase 1: Unit Tests (Priority: High)
1. Add ConfigMeta tests for `time_dimension_group_label` field
2. Add Dimension tests for `_to_dimension_group_dict()` with group_label logic
3. Add Dimension tests for group_item_label generation
4. Add LookMLGenerator initialization tests
5. Add LookMLGenerator generation tests with new parameters

**Deliverable**: 95%+ coverage of schemas and generator

### Phase 2: Integration & Golden Tests (Priority: High)
1. Update golden files with `group_label: "Time Dimensions"`
2. Add golden file validation tests
3. Add end-to-end integration tests
4. Add precedence/configuration tests across full pipeline

**Deliverable**: Regression protection and integration validation

### Phase 3: CLI Tests (Priority: Medium)
1. Add CLI flag tests for `--time-dimension-group-label`
2. Add CLI flag tests for `--no-time-dimension-group-label`
3. Add CLI flag tests for `--use-group-item-label`
4. Add flag combination tests
5. Add help text validation tests

**Deliverable**: Complete CLI interface coverage

### Phase 4: Edge Cases & Polish (Priority: Low)
1. Add edge case tests
2. Add error handling tests
3. Verify all test markers are correct
4. Run full test suite and verify coverage

**Deliverable**: 95%+ branch coverage across all modules

---

## Test Patterns & Best Practices

### 1. Pytest Patterns (from existing tests)

```python
# Use parametrize for multiple scenarios
@pytest.mark.parametrize(
    "group_label_value,expected_output",
    [
        ("Custom Label", "Custom Label"),
        ("", None),  # Empty string disables
        (None, "Time Dimensions"),  # None uses default
    ],
)
def test_group_label_variations(group_label_value, expected_output):
    ...

# Use fixtures for common setup
@pytest.fixture
def time_dimension() -> Dimension:
    return Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
    )

# Use temporary directories for file tests
with TemporaryDirectory() as temp_dir:
    output_dir = Path(temp_dir)
    ...
```

### 2. Assertion Patterns

```python
# Schema validation
assert meta.time_dimension_group_label == "Custom Label"
assert meta.time_dimension_group_label is None

# LookML dict validation
result = dimension._to_dimension_group_dict()
assert result["group_label"] == "Time Dimensions"
assert "group_item_label" in result

# File content validation
content = view_file.read_text()
assert "group_label: Time Dimensions" in content
assert 'group_item_label: "{{ _field._name | capitalize }}"' in content

# Precedence validation
# Meta override should win over parameter
result = dimension._to_dimension_group_dict(
    default_time_dimension_group_label="Generator Default"
)
assert result["group_label"] == "Dimension Meta Override"
```

### 3. Test Documentation

Each test should include:
- Descriptive docstring explaining what is being tested
- Arrange-Act-Assert structure clearly marked
- Edge cases documented in comments

Example:
```python
def test_group_label_precedence_meta_overrides_parameter(self) -> None:
    """Test that dimension-level meta takes precedence over generator parameter.

    When a dimension has config.meta.time_dimension_group_label set, it should
    override the default_time_dimension_group_label parameter passed to
    _to_dimension_group_dict().
    """
    # Arrange: Create dimension with meta override
    dimension = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(
            meta=ConfigMeta(time_dimension_group_label="Custom Label")
        ),
    )

    # Act: Call with different parameter value
    result = dimension._to_dimension_group_dict(
        default_time_dimension_group_label="Generator Default"
    )

    # Assert: Meta value wins
    assert result["group_label"] == "Custom Label"
```

---

## Coverage Verification

### 1. Run Coverage Reports

```bash
# Unit tests only (fast)
make test-fast

# Full test suite with coverage
make test-coverage

# View HTML report
open htmlcov/index.html
```

### 2. Coverage Targets by Module

| Module | Current Coverage | Target Coverage | Priority |
|--------|------------------|-----------------|----------|
| `schemas/config.py` | TBD | 95%+ | High |
| `schemas/semantic_layer.py` (Dimension) | TBD | 95%+ | High |
| `generators/lookml.py` | TBD | 95%+ | High |
| `__main__.py` (CLI) | TBD | 95%+ | Medium |

### 3. Coverage Gaps to Address

After initial test implementation:
1. Run coverage report and identify untested branches
2. Add targeted tests for missing coverage
3. Document any intentionally untested code (if any)

---

## Test Data & Fixtures

### 1. Test Fixtures Needed

**Semantic Model with Time Dimensions**:
```yaml
# tests/fixtures/time_dimension_test.yml
semantic_model:
  name: events
  model: fact_events
  entities:
    - name: event_id
      type: primary
  dimensions:
    - name: created_at
      type: time
      type_params:
        time_granularity: day
      config:
        meta:
          time_dimension_group_label: "Event Timing"

    - name: updated_at
      type: time
      type_params:
        time_granularity: day
      # No meta - uses default

    - name: event_type
      type: categorical
```

### 2. Expected Golden Output

**New golden file** (optional):
```lookml
# tests/golden/expected_events_custom_group.view.lkml
view: events {
  sql_table_name: fact_events ;;

  dimension_group: created_at {
    type: time
    timeframes: [date, week, month, quarter, year]
    sql: ${TABLE}.created_at ;;
    convert_tz: no
    group_label: "Event Timing"
  }

  dimension_group: updated_at {
    type: time
    timeframes: [date, week, month, quarter, year]
    sql: ${TABLE}.updated_at ;;
    convert_tz: no
    group_label: "Time Dimensions"
  }

  dimension: event_type {
    type: string
    sql: ${TABLE}.event_type ;;
  }
}
```

---

## Success Criteria

- [ ] All unit tests pass with 95%+ branch coverage
- [ ] All integration tests pass
- [ ] Golden files updated and tests pass
- [ ] CLI tests cover all flag combinations
- [ ] Edge cases documented and tested
- [ ] No regression in existing tests
- [ ] Coverage report shows 95%+ for modified modules
- [ ] All test markers correctly applied
- [ ] Test documentation clear and comprehensive

---

## Risks & Mitigation

### Risk 1: Breaking Existing Tests
**Mitigation**:
- Run full test suite before and after changes
- Update golden files incrementally
- Maintain backward compatibility in schemas

### Risk 2: Coverage Gaps
**Mitigation**:
- Use coverage report to identify gaps
- Add parametrized tests for multiple scenarios
- Review untested branches explicitly

### Risk 3: Integration Test Flakiness
**Mitigation**:
- Use temporary directories for all file operations
- Clean up resources in fixtures
- Avoid timing-dependent assertions

---

## Next Steps

1. **Review & Approval**: Get strategy approved
2. **Spec Generation**: Create detailed implementation spec from this strategy
3. **Test Implementation**: Implement tests in phases (1-4)
4. **Coverage Verification**: Run coverage reports and fill gaps
5. **Documentation**: Update test documentation if needed

---

## References

- Project test patterns: `src/tests/unit/test_schemas.py`
- Integration test patterns: `src/tests/integration/test_end_to_end.py`
- CLI test patterns: `src/tests/test_cli.py`
- Golden test patterns: `src/tests/test_golden.py`
- Coverage requirements: `CLAUDE.md` (95%+ target)
