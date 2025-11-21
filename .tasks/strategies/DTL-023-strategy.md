---
id: DTL-023-strategy
issue: DTL-023
title: "Implementation Strategy: Modify Measure.to_lookml_dict() to add suffix and hidden property"
created: 2025-11-21
status: approved
---

# Implementation Strategy: DTL-023

## Overview

This strategy outlines the implementation approach for modifying the `Measure.to_lookml_dict()` method in `src/dbt_to_lookml/schemas/semantic_layer.py` to add a universal `_measure` suffix to all measure names and mark them as `hidden: yes`. This is the foundational change for the Universal Measure Suffix and Hiding Strategy (Epic DTL-022).

## Context Analysis

### Current Implementation

The `Measure.to_lookml_dict()` method (lines 548-576) currently generates LookML measure dictionaries with the following structure:

```python
def to_lookml_dict(self, model_name: str | None = None) -> dict[str, Any]:
    """Convert measure to LookML format."""
    result: dict[str, Any] = {
        "name": self.name,  # Line 555: Uses original name
        "type": LOOKML_TYPE_MAP.get(self.agg, "number"),
        "sql": self.expr or f"${TABLE}.{self.name}",
    }

    # ... adds description, label, view_label, group_label

    # Add hidden parameter if specified (line 573)
    if self.config and self.config.meta and self.config.meta.hidden is True:
        result["hidden"] = "yes"

    return result
```

### Current Behavior

1. **Name generation**: Uses `self.name` directly (line 555)
2. **Hidden parameter**: Only added when explicitly configured via `config.meta.hidden=True` (lines 573-574)
3. **Impact**: Measures appear in LookML with original names and are visible by default

### Desired Behavior

1. **Name generation**: Use `f"{self.name}_measure"` to add universal suffix
2. **Hidden parameter**: Always add `"hidden": "yes"` immediately after name field
3. **Impact**: All semantic model measures are suffixed and hidden, creating clear separation from user-facing metrics

## Implementation Plan

### Step 1: Modify Name Generation (Line 555)

**Current:**
```python
result: dict[str, Any] = {
    "name": self.name,
    "type": LOOKML_TYPE_MAP.get(self.agg, "number"),
    "sql": self.expr or f"${TABLE}.{self.name}",
}
```

**Updated:**
```python
result: dict[str, Any] = {
    "name": f"{self.name}_measure",
    "type": LOOKML_TYPE_MAP.get(self.agg, "number"),
    "sql": self.expr or f"${TABLE}.{self.name}",
}
```

**Rationale:**
- Simple string interpolation adds `_measure` suffix to all measure names
- SQL expression remains unchanged (uses original column/expression name)
- No conditional logic needed - applies universally

### Step 2: Add Universal Hidden Property

**Current:**
```python
# Add hidden parameter if specified
if self.config and self.config.meta and self.config.meta.hidden is True:
    result["hidden"] = "yes"
```

**Updated:**
```python
# All measures are hidden (internal building blocks for metrics)
result["hidden"] = "yes"

# Remove the conditional hidden logic (lines 572-574)
```

**Placement:**
Insert immediately after the initial `result` dictionary definition, before description/label logic:

```python
result: dict[str, Any] = {
    "name": f"{self.name}_measure",
    "type": LOOKML_TYPE_MAP.get(self.agg, "number"),
    "sql": self.expr or f"${TABLE}.{self.name}",
}

# All measures are hidden (internal building blocks for metrics)
result["hidden"] = "yes"

if self.description:
    result["description"] = self.description
# ... rest of method
```

**Rationale:**
- Universal hiding aligns with dbt semantic layer philosophy (measures → metrics)
- Eliminates need for conditional logic and per-measure configuration
- Creates consistent behavior across all measures
- Removes the conditional block at lines 572-574 as it becomes redundant

### Step 3: Update Method Docstring

**No changes to signature** - method accepts `model_name: str | None = None` and returns `dict[str, Any]`

**Update docstring** to reflect new behavior:

```python
def to_lookml_dict(self, model_name: str | None = None) -> dict[str, Any]:
    """Convert measure to LookML format with universal suffix and hiding.

    All measures are generated with:
    - Name suffix: '_measure' appended to distinguish from metrics
    - Hidden property: 'yes' to hide from end users (building blocks for metrics)

    Args:
        model_name: Optional semantic model name for inferring group_label.

    Returns:
        Dictionary with LookML measure configuration including:
        - name: Measure name with '_measure' suffix
        - type: LookML aggregation type
        - sql: SQL expression for the measure
        - hidden: Always 'yes'
        - Optional: description, label, view_label, group_label

    Example:
        ```python
        measure = Measure(name="revenue", agg=AggregationType.SUM)
        result = measure.to_lookml_dict()
        # Returns: {"name": "revenue_measure", "type": "sum",
        #           "sql": "${TABLE}.revenue", "hidden": "yes", ...}
        ```
    """
```

## Impact Analysis

### Files Directly Modified

1. **src/dbt_to_lookml/schemas/semantic_layer.py**
   - Lines 548-576: `Measure.to_lookml_dict()` method
   - Estimated LOC change: +3 lines, -3 lines (net: 0)

### Downstream Impact

1. **src/dbt_to_lookml/generators/lookml.py**
   - Method `_resolve_measure_reference()` (lines 242-277) must be updated to append suffix
   - This is handled in DTL-024 (separate issue)
   - Metrics generation will initially break until DTL-024 is implemented

2. **Test Files Requiring Updates**
   - Unit tests: `test_schemas.py`, `test_hidden_parameter.py`, `test_hierarchy.py`, `test_flat_meta.py`
   - Integration tests: `test_join_field_exposure.py`, `test_metric_validation.py`
   - Golden tests: All `.view.lkml` files in `src/tests/golden/`
   - This is handled in DTL-025 (separate issue)

### Breaking Changes

**Severity: High (within development, not user-facing)**

1. **Measure names in generated LookML**: All measures will have `_measure` suffix
   - Before: `measure: revenue { ... }`
   - After: `measure: revenue_measure { ... }`

2. **Hidden by default**: All measures marked as hidden
   - Before: Visible unless explicitly hidden via config
   - After: Always hidden (no conditional logic)

3. **Metric references**: Metrics must reference suffixed measure names
   - Before: `${revenue}`
   - After: `${revenue_measure}`
   - Handled automatically by DTL-024

### Backward Compatibility

**NOT backward compatible** - This is a breaking change by design:

1. **Intentional break**: Part of architectural improvement for measure/metric separation
2. **Coordinated changes**: Requires DTL-024 and DTL-025 to complete the transition
3. **Test-first approach**: All tests updated to expect new behavior (DTL-025)

## Testing Strategy

### Unit Tests to Update (DTL-025)

1. **test_schemas.py::TestMeasure**
   - `test_measure_creation`: Verify name includes `_measure` suffix
   - `test_count_measure`: Verify suffix and hidden property
   - `test_measure_with_all_fields`: Verify suffix + hidden + all optional fields
   - `test_lookml_measure_creation`: Update expectations for name format

2. **test_hidden_parameter.py::TestHiddenParameterMeasure**
   - All tests expect `hidden: yes` by default
   - Remove tests for conditional hiding (no longer applicable)
   - Add test verifying universal hiding regardless of config

3. **test_hierarchy.py**
   - `test_measure_hierarchy_labels`: Verify suffix + hidden + labels
   - `test_measure_lookml_with_hierarchy`: Update expected output

4. **test_flat_meta.py**
   - `test_measure_with_category`: Verify suffix + hidden + labels
   - `test_measure_without_meta_uses_model_name`: Update expectations
   - `test_measure_lookml_with_flat_meta`: Update expected output

### Integration Tests to Update (DTL-025)

1. **test_join_field_exposure.py**
   - `test_join_fields_exclude_measures`: Update to expect suffixed names

2. **test_metric_validation.py**
   - Tests may fail until DTL-024 completes (measure reference resolution)
   - Update expected measure names in validation logic

### Golden Tests to Update (DTL-025)

**All expected view files** in `src/tests/golden/` require updates:

Example transformation for `expected_searches.view.lkml`:

**Before:**
```lookml
measure: search_count {
  type: count
  sql: ${TABLE}.search_count ;;
  description: "Total number of searches"
  view_label: " Metrics"
  group_label: "Searches Performance"
}
```

**After:**
```lookml
measure: search_count_measure {
  hidden: yes
  type: count
  sql: ${TABLE}.search_count ;;
  description: "Total number of searches"
  view_label: " Metrics"
  group_label: "Searches Performance"
}
```

### New Test Cases to Add (DTL-025)

1. **Test universal suffix behavior**
   ```python
   def test_measure_universal_suffix():
       """Verify all measures get _measure suffix."""
       measure = Measure(name="revenue", agg=AggregationType.SUM)
       result = measure.to_lookml_dict()
       assert result["name"] == "revenue_measure"
       assert result["name"].endswith("_measure")
   ```

2. **Test universal hiding behavior**
   ```python
   def test_measure_universal_hidden():
       """Verify all measures are hidden regardless of config."""
       # Without config
       measure1 = Measure(name="count", agg=AggregationType.COUNT)
       result1 = measure1.to_lookml_dict()
       assert result1["hidden"] == "yes"

       # With config but no hidden field
       measure2 = Measure(
           name="sum",
           agg=AggregationType.SUM,
           config=Config(meta=ConfigMeta(category="metrics"))
       )
       result2 = measure2.to_lookml_dict()
       assert result2["hidden"] == "yes"

       # With explicit hidden=False in config (still hidden)
       measure3 = Measure(
           name="avg",
           agg=AggregationType.AVERAGE,
           config=Config(meta=ConfigMeta(hidden=False))
       )
       result3 = measure3.to_lookml_dict()
       assert result3["hidden"] == "yes"
   ```

3. **Test suffix doesn't affect SQL expression**
   ```python
   def test_measure_suffix_sql_unaffected():
       """Verify SQL expression uses original name, not suffixed name."""
       measure = Measure(
           name="revenue",
           agg=AggregationType.SUM,
           expr="amount * quantity"
       )
       result = measure.to_lookml_dict()
       assert result["name"] == "revenue_measure"
       assert result["sql"] == "amount * quantity"
       # SQL should not contain '_measure' suffix
       assert "_measure" not in result["sql"]
   ```

## Implementation Steps

### Phase 1: Code Changes (This Issue - DTL-023)

1. **Modify line 555**: Change `"name": self.name` to `"name": f"{self.name}_measure"`
2. **Add line 560**: Insert `result["hidden"] = "yes"` after result dict definition
3. **Remove lines 572-574**: Delete conditional hidden logic
4. **Update docstring**: Add documentation for universal suffix and hiding

### Phase 2: Generator Updates (DTL-024)

1. Update `_resolve_measure_reference()` to append suffix to references
2. Ensure metrics correctly reference suffixed measures
3. Update generator tests

### Phase 3: Test Updates (DTL-025)

1. Update all unit tests for `Measure.to_lookml_dict()`
2. Update integration tests
3. Regenerate golden test expected outputs
4. Add new test cases for universal behavior
5. Verify 95%+ branch coverage maintained

## Risk Mitigation

### Risk 1: Broken Metrics Generation

**Risk**: Metrics will fail to resolve measures until DTL-024 completes

**Mitigation**:
- Coordinate DTL-023 and DTL-024 implementation closely
- Consider implementing both in same PR to maintain working state
- Use feature branch for all three issues (DTL-023, DTL-024, DTL-025)

### Risk 2: Test Failures

**Risk**: Many tests will fail after this change

**Mitigation**:
- Expected behavior - tests document the change
- DTL-025 provides comprehensive test update plan
- Use TDD approach: Update tests alongside implementation

### Risk 3: Unintended Side Effects

**Risk**: SQL expressions or other fields might unexpectedly use suffixed name

**Mitigation**:
- Only modify the `"name"` field in result dictionary
- SQL expression uses `self.name` (original, unsuffixed)
- Add explicit test case to verify SQL unaffected (see Testing Strategy)

## Success Criteria

### Implementation Success

- [ ] Line 555 uses `f"{self.name}_measure"` for name generation
- [ ] Universal `hidden: yes` added immediately after name field
- [ ] Conditional hidden logic removed (lines 572-574)
- [ ] Docstring updated with examples
- [ ] Code follows existing style (type hints, formatting)

### Testing Success

- [ ] Unit tests updated for `Measure` class (DTL-025)
- [ ] All measure-related tests expect `_measure` suffix
- [ ] All measure-related tests expect `hidden: yes`
- [ ] Golden tests updated with new expected output
- [ ] Branch coverage maintained at 95%+

### Integration Success

- [ ] Coordinates with DTL-024 (measure reference resolution)
- [ ] Coordinates with DTL-025 (test updates)
- [ ] No unintended side effects on SQL expressions
- [ ] LookML syntax validation passes

## Implementation Timeline

**Estimated effort**: 1-2 hours for code changes (DTL-023 only)

1. **Code modification**: 30 minutes
   - Update 3 lines in `Measure.to_lookml_dict()`
   - Update docstring

2. **Initial testing**: 30 minutes
   - Run unit tests to identify failures
   - Verify expected behavior locally

3. **Coordination**: 30 minutes
   - Ensure DTL-024 is ready for implementation
   - Review test update plan in DTL-025

**Note**: Full epic completion requires DTL-024 and DTL-025, estimated 6-8 hours total.

## Code Review Checklist

- [ ] Name suffix uses f-string: `f"{self.name}_measure"`
- [ ] Hidden property added as `result["hidden"] = "yes"`
- [ ] Conditional hidden logic removed
- [ ] Docstring updated with behavior description
- [ ] SQL expression still uses `self.name` (not suffixed)
- [ ] Type hints preserved
- [ ] Formatting follows ruff/black standards
- [ ] No hardcoded strings outside of `_measure` suffix

## References

- **Parent Epic**: [DTL-022](./../epics/DTL-022.md) - Universal Measure Suffix and Hiding Strategy
- **Related Issues**:
  - [DTL-024](./../issues/DTL-024.md) - Update measure reference resolution
  - [DTL-025](./../issues/DTL-025.md) - Update test expectations
- **File**: `src/dbt_to_lookml/schemas/semantic_layer.py` (lines 548-576)
- **Method**: `Measure.to_lookml_dict()`
- **Layer**: Atoms (core data structure)
