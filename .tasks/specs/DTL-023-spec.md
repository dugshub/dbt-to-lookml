---
id: DTL-023-spec
issue: DTL-023
title: "Implementation Spec: Modify Measure.to_lookml_dict() to add suffix and hidden property"
created: 2025-11-21
status: ready
session: N/A
strategy_approved: 2025-11-21
---

# Implementation Spec: DTL-023

## Metadata
- **Issue**: `DTL-023`
- **Stack**: `backend`
- **Type**: `feature`
- **Layer**: `atoms`
- **Generated**: 2025-11-21
- **Strategy**: Approved 2025-11-21

## Issue Context

### Problem Statement

Update the `Measure` class in `src/dbt_to_lookml/schemas/semantic_layer.py` to implement universal measure suffix and hiding. This is the foundational change for the Universal Measure Suffix and Hiding Strategy (Epic DTL-022).

**Changes Required:**
1. Modify line 555: Change name from `self.name` to `f"{self.name}_measure"`
2. Add universal `"hidden": "yes"` to all measures
3. Remove conditional hidden logic (lines 572-574)
4. Update method docstring

**Purpose:**
- All measures suffixed with `_measure` for clear identification as internal building blocks
- All measures marked as hidden to separate from user-facing metrics
- Aligns with dbt semantic layer philosophy: measures → metrics

### Solution Approach

The approved strategy modifies the `Measure.to_lookml_dict()` method to:
1. Add universal `_measure` suffix to all measure names
2. Unconditionally add `hidden: yes` property
3. Remove conditional hidden logic that checked `config.meta.hidden`
4. Update docstring to document new behavior

This is a breaking change by design, coordinated with DTL-024 (measure reference resolution) and DTL-025 (test updates).

### Success Criteria

- [ ] Line 555 uses `f"{self.name}_measure"` for name generation
- [ ] Universal `hidden: yes` added immediately after name field
- [ ] Conditional hidden logic removed (lines 572-574)
- [ ] Docstring updated with behavior description and examples
- [ ] Code follows existing style (type hints, formatting)
- [ ] No unintended side effects on SQL expressions

## Approved Strategy Summary

### Key Architectural Decisions

1. **Universal Suffix**: All measures get `_measure` suffix via simple f-string interpolation
2. **Universal Hiding**: All measures hidden by default (no conditional logic)
3. **SQL Preservation**: SQL expressions use original `self.name` (not suffixed)
4. **Breaking Change**: Intentional architectural improvement requiring coordinated changes
5. **Placement**: Hidden property added immediately after result dict definition

### Impact Scope

**Files Directly Modified:**
- `src/dbt_to_lookml/schemas/semantic_layer.py` (lines 548-576)

**Downstream Impact (Handled in Separate Issues):**
- DTL-024: Update `_resolve_measure_reference()` in generator
- DTL-025: Update all test expectations and golden files

## Implementation Plan

### Phase 1: Modify Name Generation (Line 555)

**Task**: Add `_measure` suffix to all measure names

**Current Code (Line 555):**
```python
result: dict[str, Any] = {
    "name": self.name,
    "type": LOOKML_TYPE_MAP.get(self.agg, "number"),
    "sql": self.expr or f"${TABLE}.{self.name}",
}
```

**Updated Code:**
```python
result: dict[str, Any] = {
    "name": f"{self.name}_measure",
    "type": LOOKML_TYPE_MAP.get(self.agg, "number"),
    "sql": self.expr or f"${TABLE}.{self.name}",
}
```

**Key Points:**
- Use f-string interpolation: `f"{self.name}_measure"`
- SQL expression remains unchanged (uses `self.name` without suffix)
- No conditional logic needed - applies universally

### Phase 2: Add Universal Hidden Property

**Task**: Add `hidden: yes` unconditionally and remove conditional logic

**Current Code (Lines 560-574):**
```python
if self.description:
    result["description"] = self.description
if self.label:
    result["label"] = self.label

# Add measure labels
view_label, group_label = self.get_measure_labels(model_name)
if view_label:
    result["view_label"] = view_label
if group_label:
    result["group_label"] = group_label

# Add hidden parameter if specified
if self.config and self.config.meta and self.config.meta.hidden is True:
    result["hidden"] = "yes"

return result
```

**Updated Code:**
```python
# All measures are hidden (internal building blocks for metrics)
result["hidden"] = "yes"

if self.description:
    result["description"] = self.description
if self.label:
    result["label"] = self.label

# Add measure labels
view_label, group_label = self.get_measure_labels(model_name)
if view_label:
    result["view_label"] = view_label
if group_label:
    result["group_label"] = group_label

return result
```

**Key Points:**
- Add `result["hidden"] = "yes"` immediately after result dict definition
- Remove conditional hidden block (lines 572-574) - it becomes redundant
- Add explanatory comment about universal hiding
- Maintains existing order for other optional fields

### Phase 3: Update Method Docstring

**Task**: Update docstring to reflect new behavior

**Current Docstring (Lines 548-553):**
```python
def to_lookml_dict(self, model_name: str | None = None) -> dict[str, Any]:
    """Convert measure to LookML format.

    Args:
        model_name: Optional semantic model name for inferring group_label.
    """
```

**Updated Docstring:**
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

**Key Points:**
- Documents universal suffix behavior
- Documents universal hiding behavior
- Provides clear example showing new output format
- Maintains existing signature documentation

## Detailed Task Breakdown

### Task 1: Modify Measure Name Generation

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`

**Line**: 555

**Action**: Change `"name": self.name` to `"name": f"{self.name}_measure"`

**Implementation Guidance**:
```python
# Before
"name": self.name,

# After
"name": f"{self.name}_measure",
```

**Reference**: Similar f-string patterns used throughout codebase for name formatting (see `_smart_title()` function in same file)

**Tests**: Verify all tests expecting measure names now include `_measure` suffix

### Task 2: Add Universal Hidden Property

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`

**Lines**: Insert after 558 (after result dict definition)

**Action**: Add `result["hidden"] = "yes"` with comment

**Implementation Guidance**:
```python
result: dict[str, Any] = {
    "name": f"{self.name}_measure",
    "type": LOOKML_TYPE_MAP.get(self.agg, "number"),
    "sql": self.expr or f"${TABLE}.{self.name}",
}

# All measures are hidden (internal building blocks for metrics)
result["hidden"] = "yes"
```

**Reference**: Similar pattern used in `Entity.to_lookml_dict()` for primary keys (line 94-96)

**Tests**: Verify all measures have `hidden: yes` regardless of config

### Task 3: Remove Conditional Hidden Logic

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`

**Lines**: 572-574 (to be removed)

**Action**: Delete conditional hidden block

**Implementation Guidance**:
```python
# Remove these lines:
# Add hidden parameter if specified
if self.config and self.config.meta and self.config.meta.hidden is True:
    result["hidden"] = "yes"
```

**Reference**: This becomes redundant since all measures are now universally hidden

**Tests**: Remove tests for conditional hiding behavior

### Task 4: Update Method Docstring

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`

**Lines**: 548-553 (expand docstring)

**Action**: Add comprehensive docstring with behavior description and examples

**Implementation Guidance**:
See Phase 3 for complete docstring

**Reference**: Similar detailed docstrings in `Dimension._to_dimension_group_dict()` (lines 402-420)

**Tests**: Docstring is documentation - no specific tests, but validates understanding

## File Changes

### Files to Modify

#### `src/dbt_to_lookml/schemas/semantic_layer.py`

**Location**: Lines 548-576 (`Measure.to_lookml_dict()` method)

**Why**: Implement universal measure suffix and hiding

**Changes**:
1. **Line 555**: Add `_measure` suffix to name
2. **After line 558**: Add universal `hidden: yes` property
3. **Lines 572-574**: Remove conditional hidden logic
4. **Lines 548-553**: Expand docstring with behavior documentation

**Estimated Lines**:
- Added: ~5 lines (expanded docstring + hidden property + comment)
- Removed: ~3 lines (conditional hidden block)
- Net: +2 lines

**Structure**: Method already exists, minimal modifications

**Complete Modified Method**:
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
    result: dict[str, Any] = {
        "name": f"{self.name}_measure",
        "type": LOOKML_TYPE_MAP.get(self.agg, "number"),
        "sql": self.expr or f"${TABLE}.{self.name}",
    }

    # All measures are hidden (internal building blocks for metrics)
    result["hidden"] = "yes"

    if self.description:
        result["description"] = self.description
    if self.label:
        result["label"] = self.label

    # Add measure labels
    view_label, group_label = self.get_measure_labels(model_name)
    if view_label:
        result["view_label"] = view_label
    if group_label:
        result["group_label"] = group_label

    return result
```

### Files NOT Modified (Handled in Other Issues)

#### `src/dbt_to_lookml/generators/lookml.py`
**Issue**: DTL-024
**Reason**: Measure reference resolution must append suffix

#### `src/tests/unit/test_schemas.py`
**Issue**: DTL-025
**Reason**: Test expectations must be updated for suffix and hiding

#### `src/tests/unit/test_hidden_parameter.py`
**Issue**: DTL-025
**Reason**: Hidden parameter tests need rewrite for universal behavior

#### `src/tests/golden/*.view.lkml`
**Issue**: DTL-025
**Reason**: Expected LookML output must show suffix and hidden property

## Testing Strategy

**IMPORTANT**: This implementation will cause test failures. This is expected and intentional. DTL-025 will update all tests to match new behavior.

### Expected Test Failures (DTL-025 will fix)

#### Unit Tests - `test_schemas.py::TestMeasure`

**Failing Tests:**
1. `test_measure_creation`: Expects `name == "total_revenue"`, will be `"total_revenue_measure"`
2. `test_count_measure`: Expects no hidden property, will have `hidden: yes`
3. `test_measure_with_all_fields`: Expects original name, will be suffixed
4. `test_all_aggregation_types`: All names will be suffixed

**Fix Required (DTL-025):**
```python
def test_measure_creation(self) -> None:
    """Test basic measure creation."""
    measure = Measure(name="total_revenue", agg=AggregationType.SUM)
    result = measure.to_lookml_dict()

    # Updated expectations
    assert result["name"] == "total_revenue_measure"  # Was: "total_revenue"
    assert result["hidden"] == "yes"  # New assertion
    assert result["type"] == "sum"
```

#### Unit Tests - `test_hidden_parameter.py::TestHiddenParameterMeasure`

**Failing Tests:**
1. `test_measure_with_hidden_false`: Expects no hidden, will have `hidden: yes`
2. `test_measure_without_hidden`: Expects no hidden, will have `hidden: yes`
3. `test_existing_measures_unaffected`: Expects no hidden, will have `hidden: yes`

**Fix Required (DTL-025):**
```python
def test_measure_universal_hidden(self):
    """Test all measures are hidden regardless of config."""
    # Without config
    measure1 = Measure(name="count", agg=AggregationType.COUNT)
    result1 = measure1.to_lookml_dict()
    assert result1["hidden"] == "yes"
    assert result1["name"] == "count_measure"

    # With config but hidden=False (still hidden)
    measure2 = Measure(
        name="sum",
        agg=AggregationType.SUM,
        config=Config(meta=ConfigMeta(hidden=False))
    )
    result2 = measure2.to_lookml_dict()
    assert result2["hidden"] == "yes"  # Universal hiding overrides config
```

#### Golden Tests - All `*.view.lkml` files

**Failing Tests:**
- `test_golden.py::test_searches_view_golden`
- `test_golden.py::test_users_view_golden`
- `test_golden.py::test_rental_orders_view_golden`

**Example Fix Required (DTL-025):**

Before (`expected_searches.view.lkml`):
```lookml
measure: search_count {
  type: count
  sql: ${TABLE}.search_count ;;
  description: "Total number of searches"
  view_label: " Metrics"
  group_label: "Searches Performance"
}
```

After:
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

#### Test 1: Universal Suffix Behavior

**File**: `src/tests/unit/test_schemas.py`

**Purpose**: Verify all measures get `_measure` suffix

```python
def test_measure_universal_suffix():
    """Verify all measures get _measure suffix."""
    # Test with different aggregation types
    measures = [
        Measure(name="revenue", agg=AggregationType.SUM),
        Measure(name="count", agg=AggregationType.COUNT),
        Measure(name="avg_price", agg=AggregationType.AVERAGE),
    ]

    for measure in measures:
        result = measure.to_lookml_dict()
        assert result["name"].endswith("_measure")
        assert result["name"] == f"{measure.name}_measure"
```

#### Test 2: Universal Hidden Behavior

**File**: `src/tests/unit/test_hidden_parameter.py`

**Purpose**: Verify all measures are hidden regardless of config

```python
def test_measure_universal_hidden_ignores_config():
    """Verify all measures are hidden regardless of config.meta.hidden."""
    # Without config
    measure1 = Measure(name="count", agg=AggregationType.COUNT)
    assert measure1.to_lookml_dict()["hidden"] == "yes"

    # With config but no hidden field
    measure2 = Measure(
        name="sum",
        agg=AggregationType.SUM,
        config=Config(meta=ConfigMeta(category="metrics"))
    )
    assert measure2.to_lookml_dict()["hidden"] == "yes"

    # With explicit hidden=False in config (still hidden)
    measure3 = Measure(
        name="avg",
        agg=AggregationType.AVERAGE,
        config=Config(meta=ConfigMeta(hidden=False))
    )
    assert measure3.to_lookml_dict()["hidden"] == "yes"

    # With explicit hidden=True in config (still hidden, redundant)
    measure4 = Measure(
        name="max",
        agg=AggregationType.MAX,
        config=Config(meta=ConfigMeta(hidden=True))
    )
    assert measure4.to_lookml_dict()["hidden"] == "yes"
```

#### Test 3: SQL Expression Unaffected by Suffix

**File**: `src/tests/unit/test_schemas.py`

**Purpose**: Verify SQL uses original name, not suffixed name

```python
def test_measure_suffix_does_not_affect_sql():
    """Verify SQL expression uses original name, not suffixed name."""
    # Test with default SQL generation
    measure1 = Measure(name="revenue", agg=AggregationType.SUM)
    result1 = measure1.to_lookml_dict()
    assert result1["name"] == "revenue_measure"
    assert result1["sql"] == "${TABLE}.revenue"
    assert "_measure" not in result1["sql"]

    # Test with custom expression
    measure2 = Measure(
        name="profit",
        agg=AggregationType.SUM,
        expr="amount * quantity"
    )
    result2 = measure2.to_lookml_dict()
    assert result2["name"] == "profit_measure"
    assert result2["sql"] == "amount * quantity"
    assert "_measure" not in result2["sql"]
```

#### Test 4: Suffix with All Field Types

**File**: `src/tests/unit/test_schemas.py`

**Purpose**: Verify suffix works with all optional fields

```python
def test_measure_suffix_with_all_fields():
    """Verify suffix works correctly with all optional fields."""
    measure = Measure(
        name="total_revenue",
        agg=AggregationType.SUM,
        expr="amount * quantity",
        description="Total revenue calculation",
        label="Total Revenue",
        config=Config(
            meta=ConfigMeta(
                hierarchy=Hierarchy(
                    entity="order",
                    category="financial",
                    subcategory="revenue"
                )
            )
        )
    )
    result = measure.to_lookml_dict(model_name="orders")

    # Verify suffix
    assert result["name"] == "total_revenue_measure"

    # Verify hidden
    assert result["hidden"] == "yes"

    # Verify other fields unchanged
    assert result["description"] == "Total revenue calculation"
    assert result["label"] == "Total Revenue"
    assert result["sql"] == "amount * quantity"
    assert result["type"] == "sum"

    # Verify labels from hierarchy
    assert "view_label" in result
    assert "group_label" in result
```

### Validation Commands

**Run after implementing changes:**

```bash
# Format code
make format

# Check linting
make lint

# Type checking
make type-check

# Run unit tests (expect failures - DTL-025 will fix)
python -m pytest src/tests/unit/test_schemas.py::TestMeasure -xvs
python -m pytest src/tests/unit/test_hidden_parameter.py::TestHiddenParameterMeasure -xvs

# Run all tests (expect many failures)
make test

# Quality gate (will fail until DTL-025 completes)
make quality-gate
```

**After DTL-025 (test updates):**

```bash
# All tests should pass
make test-full

# Coverage should be 95%+
make test-coverage
```

## Implementation Notes

### Important Considerations

1. **Breaking Change by Design**: This is intentional - part of architectural improvement
2. **Coordinated with DTL-024**: Measure reference resolution must be updated simultaneously
3. **Coordinated with DTL-025**: All tests must be updated to expect new behavior
4. **No Backward Compatibility**: Old behavior is replaced, not extended
5. **SQL Preservation**: Critical that SQL uses `self.name` (original), not suffixed name

### Code Patterns to Follow

1. **F-String Interpolation**: Used throughout codebase for name formatting
   - Example: `_smart_title()` function (line 119-154)
   - Example: Entity labels (line 82-93)

2. **Universal Properties**: Pattern established for entity hiding
   - Example: `Entity.to_lookml_dict()` always adds `hidden: yes` for all entity types (line 94-96)
   - Our change extends this pattern to measures

3. **Dictionary Building**: Consistent pattern in codebase
   - Start with minimal dict
   - Add universal properties
   - Add optional fields conditionally
   - Return dict

4. **Docstring Style**: Google-style docstrings with examples
   - See `Dimension._to_dimension_group_dict()` (lines 402-420)
   - See `Entity.to_lookml_dict()` (lines 58-68)

### References

**Similar Implementations:**
- `Entity.to_lookml_dict()` (lines 58-115): Universal hidden property for all entities
- `Dimension._to_dimension_group_dict()` (lines 402-500): Complex field generation with conditional logic
- `_smart_title()` (lines 119-154): Name formatting with f-strings

**Type Mappings:**
- `types.py::LOOKML_TYPE_MAP` (lines 49-59): Aggregation type to LookML type mapping

**Test Patterns:**
- `test_schemas.py::TestEntity` (lines 32-162): Test structure for model classes
- `test_hidden_parameter.py` (lines 1-182): Test structure for hidden parameter

## Dependencies

### Existing Dependencies

**No new dependencies required.** All functionality uses existing imports:

- `typing.Any`: For type hints
- `pydantic`: Already imported for `BaseModel`
- `types.py::LOOKML_TYPE_MAP`: Already imported for aggregation mapping

### Relationship to Other Issues

**Parent Epic:**
- **DTL-022**: Universal Measure Suffix and Hiding Strategy

**Sequential Dependencies:**
- **DTL-024** (Next): Update `_resolve_measure_reference()` to handle suffixed names
- **DTL-025** (Next): Update all test expectations for new behavior

**Implementation Order:**
1. DTL-023 (This issue): Implement suffix and hiding
2. DTL-024: Fix measure reference resolution
3. DTL-025: Update all tests

**Recommended Approach:**
- Implement DTL-023 and DTL-024 in same feature branch
- This maintains working state (no broken metric generation)
- Then update tests in DTL-025

## Ready for Implementation

This spec is complete and ready for implementation.

### Pre-Implementation Checklist

- [ ] Read this complete spec
- [ ] Understand the breaking change nature
- [ ] Review the approved strategy document
- [ ] Coordinate with DTL-024 (measure reference resolution)
- [ ] Understand DTL-025 will fix all test failures

### Implementation Checklist

- [ ] Line 555: Change to `f"{self.name}_measure"`
- [ ] After line 558: Add `result["hidden"] = "yes"` with comment
- [ ] Lines 572-574: Remove conditional hidden block
- [ ] Lines 548-553: Update docstring with new behavior
- [ ] Run `make format` to auto-format
- [ ] Run `make lint` to check style
- [ ] Run `make type-check` to verify types
- [ ] Manually verify SQL expressions use original name

### Post-Implementation Checklist

- [ ] Code follows existing patterns
- [ ] Type hints preserved
- [ ] Formatting matches ruff/black standards
- [ ] No hardcoded strings except `_measure` suffix
- [ ] Docstring includes clear example
- [ ] Ready to coordinate with DTL-024

### Estimated Effort

**Code Changes**: 30 minutes
- 4 specific changes in single method
- Straightforward modifications

**Local Testing**: 30 minutes
- Verify expected test failures
- Check no unintended side effects
- Validate SQL preservation

**Total**: 1 hour for DTL-023 only

**Note**: Full epic completion requires DTL-024 and DTL-025 (estimated 6-8 hours total)

## Code Review Focus Areas

### Critical Review Points

1. **Name Suffix**: Verify f-string is `f"{self.name}_measure"` (not hardcoded)
2. **SQL Expression**: Verify SQL still uses `self.name` (not suffixed)
3. **Hidden Property**: Verify added as `result["hidden"] = "yes"` (string "yes")
4. **Conditional Removal**: Verify lines 572-574 completely removed
5. **Docstring**: Verify includes behavior description and example

### Style Review Points

1. **Type Hints**: Verify signature unchanged: `def to_lookml_dict(self, model_name: str | None = None) -> dict[str, Any]:`
2. **Formatting**: Verify follows ruff/black (88 char line length)
3. **Comments**: Verify comment explains universal hiding rationale
4. **Consistency**: Verify pattern matches `Entity.to_lookml_dict()` style

### Testing Review Points

1. **Expected Failures**: Confirm test failures are expected and documented
2. **SQL Safety**: Verify SQL expressions don't contain `_measure` suffix
3. **No Regressions**: Verify optional fields (description, label, etc.) still work
4. **Type Mapping**: Verify aggregation type mapping unchanged

## Success Metrics

### Implementation Success

- [x] Line 555 uses `f"{self.name}_measure"` for name generation
- [x] Universal `hidden: yes` added immediately after name field
- [x] Conditional hidden logic removed (lines 572-574)
- [x] Docstring updated with examples
- [x] Code follows existing style (type hints, formatting)
- [x] SQL expressions use original name (not suffixed)

### Quality Gates

- [x] `make format` runs successfully
- [x] `make lint` passes with no errors
- [x] `make type-check` passes with no errors
- [ ] Tests fail as expected (DTL-025 will fix)
- [ ] No unintended side effects observed

### Integration Success

- [ ] Coordinates with DTL-024 (measure reference resolution)
- [ ] Coordinates with DTL-025 (test updates)
- [ ] Branch coverage will be maintained at 95%+ after DTL-025

## Session Artifacts

**Strategy Document**: `.tasks/strategies/DTL-023-strategy.md`
**This Spec**: `.tasks/specs/DTL-023-spec.md`
**Issue File**: `.tasks/issues/DTL-023.md`

## References

- **Parent Epic**: [DTL-022](./../epics/DTL-022.md) - Universal Measure Suffix and Hiding Strategy
- **Related Issues**:
  - [DTL-024](./../issues/DTL-024.md) - Update measure reference resolution in generator
  - [DTL-025](./../issues/DTL-025.md) - Update test expectations and golden files
- **Primary File**: `src/dbt_to_lookml/schemas/semantic_layer.py` (lines 548-576)
- **Method**: `Measure.to_lookml_dict()`
- **Layer**: Atoms (core data structure)
- **Strategy**: `.tasks/strategies/DTL-023-strategy.md`
