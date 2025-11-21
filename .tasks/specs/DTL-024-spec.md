# Implementation Spec: Update LookMLGenerator._resolve_measure_reference() to append suffix

## Metadata
- **Issue**: `DTL-024`
- **Stack**: `backend`
- **Generated**: 2025-11-21
- **Strategy**: Approved 2025-11-21

## Issue Context

### Problem Statement

After DTL-023 modifies `Measure.to_lookml_dict()` to append a `_measure` suffix to all measure names (and mark them hidden), this issue updates `LookMLGenerator._resolve_measure_reference()` to ensure all references to measures in metric SQL expressions use the suffixed names.

The `_resolve_measure_reference()` method converts measure names into LookML reference syntax (`${measure_name}` for same-view or `${view.measure_name}` for cross-view). This method is critical because it's called by all metric SQL generation methods:
- `_generate_simple_sql()` - simple metrics
- `_generate_ratio_sql()` - ratio metrics (numerator and denominator)
- `_generate_derived_sql()` - derived metrics (multiple measure references)

Without this change, metrics would reference non-existent measure names (missing the `_measure` suffix), breaking the generated LookML.

### Solution Approach

Apply a simple, surgical change to append `_measure` suffix to measure names in both return statements of `_resolve_measure_reference()`:
1. Line 273: Same-view reference `${measure_name}` → `${measure_name_measure}`
2. Line 277: Cross-view reference `${view.measure_name}` → `${view.measure_name_measure}`

This maintains the existing logic while ensuring measure references match the new naming convention established in DTL-023.

### Success Criteria

- Same-view measure references include `_measure` suffix
- Cross-view measure references include `_measure` suffix
- All metric types (simple, ratio, derived) generate correct SQL
- Unit tests pass with updated expectations
- Branch coverage maintained at 95%+
- No regression in existing functionality

## Approved Strategy Summary

The approved strategy establishes a **universal suffix approach** for all measures:

**Key Decisions**:
1. **Simple string concatenation**: Append `_measure` suffix directly in return statements
2. **No collision detection**: All measures get suffix consistently (simpler than conditional logic)
3. **Two-line change**: Minimal, surgical modification to existing method
4. **Comprehensive test updates**: Update all test expectations across metric types

**Implementation Timeline**: 5 min implementation + 50 min test updates = ~90 min total

## Detailed Implementation Changes

### Change 1: Update Same-View Reference (Line 273)

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py`

**Current Code** (line 273):
```python
return f"${{{measure_name}}}"
```

**New Code**:
```python
return f"${{{measure_name}_measure}}"
```

**Rationale**: Append `_measure` suffix to match measure names from DTL-023.

---

### Change 2: Update Cross-View Reference (Line 277)

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py`

**Current Code** (line 277):
```python
return f"${{{view_name}.{measure_name}}}"
```

**New Code**:
```python
return f"${{{view_name}.{measure_name}_measure}}"
```

**Rationale**: Append `_measure` suffix to cross-view measure references.

---

### Change 3: Update Docstring (Optional)

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py`

**Current Returns Documentation** (line 253):
```python
Returns:
    LookML reference: "${measure}" or "${view_prefix}{model}.{measure}"
```

**New Returns Documentation**:
```python
Returns:
    LookML reference: "${measure_measure}" or "${view_prefix}{model}.{measure_measure}"
```

**Note**: This is optional but improves clarity.

## Test Updates

### Unit Tests File

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_lookml_generator_metrics.py`

### TestHelperMethods Updates

**Test 1: test_resolve_measure_reference_same_view** (line 78)
```python
# Change
assert result == "${order_count}"
# To
assert result == "${order_count_measure}"
```

**Test 2: test_resolve_measure_reference_cross_view** (line 87)
```python
# Change
assert result == "${searches.search_count}"
# To
assert result == "${searches.search_count_measure}"
```

**Test 3: test_resolve_measure_reference_with_prefix** (line 97)
```python
# Change
assert result == "${v_searches.search_count}"
# To
assert result == "${v_searches.search_count_measure}"
```

### TestSQLGenerationSimple Updates

Update all assertions checking generated SQL to include `_measure` suffix:
- `test_generate_simple_sql`: `${searches.search_count}` → `${searches.search_count_measure}`
- `test_generate_simple_sql_same_view`: `${order_count}` → `${order_count_measure}`
- `test_generate_simple_sql_with_prefix`: `${v_searches.search_count}` → `${v_searches.search_count_measure}`

### TestSQLGenerationRatio Updates

Update numerator and denominator references in all ratio metric tests:

**Example Pattern**:
```python
# Before
"1.0 * ${orders.order_count} / NULLIF(${searches.search_count}, 0)"

# After
"1.0 * ${orders.order_count_measure} / NULLIF(${searches.search_count_measure}, 0)"
```

### TestSQLGenerationDerived Updates

Update all measure references in derived metric expressions:

**Example Pattern**:
```python
# Before
"${order_count} + ${searches.search_count}"

# After
"${order_count_measure} + ${searches.search_count_measure}"
```

### TestMetricMeasureGeneration Updates

Update SQL field assertions in generated measure dictionaries:

**Example Pattern**:
```python
# Before
assert "${searches.search_count}" in measure_dict["sql"]

# After
assert "${searches.search_count_measure}" in measure_dict["sql"]
```

## Validation Commands

**Run unit tests**:
```bash
pytest src/tests/unit/test_lookml_generator_metrics.py -xvs
```

**Run quality gate**:
```bash
make quality-gate
```

**Check coverage**:
```bash
make test-coverage
```

## Implementation Checklist

- [ ] Line 273: Append `_measure` to same-view reference
- [ ] Line 277: Append `_measure` to cross-view reference
- [ ] Line 253: Update docstring (optional)
- [ ] Update TestHelperMethods tests (3 tests)
- [ ] Update TestSQLGenerationSimple tests (~3 tests)
- [ ] Update TestSQLGenerationRatio tests (~4 tests)
- [ ] Update TestSQLGenerationDerived tests (~4 tests)
- [ ] Update TestMetricMeasureGeneration tests (multiple)
- [ ] Run unit tests: `pytest src/tests/unit/test_lookml_generator_metrics.py -xvs`
- [ ] Run type checking: `make type-check`
- [ ] Run linting: `make lint`
- [ ] Run full tests: `make test`

**Estimated Time**: 90 minutes
