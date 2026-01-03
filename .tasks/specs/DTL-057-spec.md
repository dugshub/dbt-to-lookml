---
id: DTL-057-spec
issue: DTL-057
title: "Implementation Spec: Add comprehensive test coverage for derived metric PoP"
type: spec
status: Ready
created: 2025-12-22
stack: backend
---

# Implementation Spec: Add comprehensive test coverage for derived metric PoP

## Metadata
- **Issue**: `DTL-057`
- **Stack**: `backend`
- **Type**: `feature`
- **Generated**: 2025-12-22
- **Epic**: DTL-054 (PoP Support for Same-Model Derived Metrics)
- **Depends on**: DTL-055 (COMPLETE), DTL-056

## Issue Context

### Problem Statement

Comprehensive test coverage is needed to ensure the derived metric PoP feature works correctly across all scenarios. Tests should cover:
1. Unit tests for `is_pop_eligible_metric` function (ALREADY COMPLETE - 20 tests)
2. Integration tests for end-to-end PoP generation
3. Edge cases and error handling

### Current Test Coverage

**Already Implemented** (`src/tests/unit/test_derived_metric_pop.py`):
- `TestSimpleMetricPopEligibility` (2 tests)
- `TestRatioMetricPopEligibility` (6 tests)
- `TestDerivedMetricPopEligibility` (8 tests)
- `TestConversionMetricPopEligibility` (1 test)
- `TestBackwardsCompatibility` (3 tests)

**Related Tests**:
- `test_pop_generator.py` - PoP measure generation tests
- `test_pop_integration.py` - Overall PoP integration tests
- `test_pop_parser.py` - PoP config parsing tests

### Remaining Work

The remaining tests should focus on **end-to-end integration** - verifying that when a semantic model with derived metrics is processed, the correct PoP measures are generated in the output LookML.

### Success Criteria

- [ ] All existing tests continue to pass
- [ ] Integration tests verify derived metric PoP end-to-end
- [ ] Edge cases covered (date selector, custom formats, etc.)
- [ ] Test coverage meets project requirements (95%+)

## Implementation Plan

### Phase 1: Review Existing Coverage

**Already Complete** (20 tests in `test_derived_metric_pop.py`):

| Test Class | Count | Purpose |
|------------|-------|---------|
| TestSimpleMetricPopEligibility | 2 | Simple metric eligibility |
| TestRatioMetricPopEligibility | 6 | Ratio metric same-model detection |
| TestDerivedMetricPopEligibility | 8 | Derived metric recursive resolution |
| TestConversionMetricPopEligibility | 1 | Conversion metrics (not supported) |
| TestBackwardsCompatibility | 3 | Old function name compatibility |

### Phase 2: Integration Tests (Covered in DTL-056)

The following integration tests are specified in DTL-056:
1. `test_same_model_derived_generates_pop` - Derived with same-model parents generates PoP
2. `test_cross_model_derived_skips_pop` - Cross-model derived is skipped
3. `test_simple_metric_pop_still_works` - Simple metrics unaffected

### Phase 3: Additional Edge Case Tests

**New tests to add** (extend `test_derived_metric_pop.py` or new file):

```python
class TestDerivedMetricPopEdgeCases:
    """Edge case tests for derived metric PoP."""

    def test_derived_pop_with_date_selector_enabled(self) -> None:
        """Derived metric PoP works with date_selector feature."""
        # Verify PoP uses calendar_date when date_selector is enabled
        pass

    def test_derived_pop_inherits_format_from_config(self) -> None:
        """Derived metric PoP measures inherit value_format from pop config."""
        # Verify format like "usd" is applied to PoP measures
        pass

    def test_derived_pop_labels_match_pattern(self) -> None:
        """Derived metric PoP measure labels follow standard pattern."""
        # Pattern: "{metric_label} (Prior Year)", "{metric_label} Δ (Prior Year)"
        pass

    def test_deeply_nested_derived_qualifies(self) -> None:
        """3+ levels of nesting still qualifies if all same-model."""
        # derived -> derived -> derived -> simple (all same entity)
        pass

    def test_mixed_simple_and_derived_pop(self) -> None:
        """Model with both simple and derived metrics with PoP works."""
        # Both should get PoP measures generated
        pass

    def test_derived_with_single_parent_qualifies(self) -> None:
        """Derived metric with only one parent metric qualifies."""
        # expr: "revenue * 1.1" with one parent
        pass

    def test_derived_pop_group_label(self) -> None:
        """Derived PoP measures have correct group_label."""
        # Should be grouped under "Metrics (Period-over-Period)"
        pass

    def test_derived_pop_view_label(self) -> None:
        """Derived PoP measures have correct view_label."""
        # Should use VIEW_LABEL_METRICS_POP constant
        pass
```

### Phase 4: LookML Validation Tests

```python
class TestDerivedMetricPopLookmlOutput:
    """Tests for generated LookML structure."""

    def test_derived_pop_measure_type_is_period_over_period(self) -> None:
        """Generated PoP measures use type: period_over_period."""
        pass

    def test_derived_pop_based_on_references_metric(self) -> None:
        """PoP measures have based_on referencing the derived metric."""
        # based_on: net_change_eom (not a hidden base)
        pass

    def test_derived_pop_based_on_time_uses_date_dimension(self) -> None:
        """PoP measures have correct based_on_time."""
        # based_on_time: report_date_date or calendar_date
        pass

    def test_lookml_is_syntactically_valid(self) -> None:
        """Generated LookML can be parsed by lkml."""
        # lkml.load(output) should not raise
        pass
```

## File Changes

### Files to Modify

#### `src/tests/unit/test_derived_metric_pop.py`

**Why**: Add edge case and LookML output tests

**Changes**: Add new test classes as specified above

**Estimated additions**: ~150-200 lines

### Files to Create

None required - tests should be added to existing file.

## Testing Strategy

### Run All PoP-Related Tests

```bash
python -m pytest src/tests/unit/test_derived_metric_pop.py \
                 src/tests/unit/test_pop_generator.py \
                 src/tests/unit/test_pop_integration.py \
                 src/tests/unit/test_pop_parser.py -v
```

### Verify Coverage

```bash
python -m pytest src/tests/unit/test_derived_metric_pop.py --cov=src/dbt_to_lookml/generators/lookml --cov-report=term-missing
```

### Focus Areas

1. **is_pop_eligible_metric function**: 100% coverage (already achieved)
2. **_generate_metric_pop_measures**: High coverage for derived metric path
3. **generate method**: Coverage of pop_metrics filtering with eligibility check

## Dependencies

### Existing Dependencies

- `is_pop_eligible_metric` function (DTL-055 - COMPLETE)
- Integration of function (DTL-056)

### Related Issues

- **Parent**: DTL-054 (Epic)
- **Depends on**: DTL-055 (COMPLETE), DTL-056

## Implementation Notes

### Test Fixtures

Consider creating shared fixtures for common test scenarios:

```python
@pytest.fixture
def same_model_derived_metric():
    """Create a derived metric with all parents on same model."""
    # Returns (model, metrics_list, derived_metric)
    pass

@pytest.fixture
def cross_model_derived_metric():
    """Create a derived metric with cross-model parents."""
    # Returns (models_list, metrics_list, derived_metric)
    pass
```

### Key Assertions

For each test, verify:
1. **Eligibility**: `is_pop_eligible_metric` returns correct result
2. **Generation**: PoP measures are/aren't in output
3. **Structure**: Measure dict has correct fields
4. **LookML**: Output is valid and parseable

## Status Assessment

Given that DTL-055 is complete with 20 passing tests, and DTL-056 will include integration tests, the remaining work for DTL-057 is:

1. **Edge case tests** (~8 new tests)
2. **LookML output validation tests** (~4 new tests)
3. **Shared fixtures** for cleaner test code

**Estimated Total New Tests**: ~12

## Ready for Implementation

This spec is ready for implementation after DTL-056 is complete.

**Implementation Steps**:
1. Wait for DTL-056 integration to be complete
2. Add edge case tests to `test_derived_metric_pop.py`
3. Add LookML validation tests
4. Run full test suite and verify coverage

**Estimated Effort**: 1-2 hours
- Edge case tests: 45 minutes
- LookML validation tests: 30 minutes
- Fixtures and cleanup: 15 minutes

**Success Criteria**:
- [ ] All 20+ existing tests continue to pass
- [ ] 12+ new tests added and passing
- [ ] Coverage of `is_pop_eligible_metric` at 100%
- [ ] Integration tests verify end-to-end behavior
