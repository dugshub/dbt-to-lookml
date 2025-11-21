# DTL-025: Update test expectations for measure generation - Implementation Strategy

## Overview

This strategy outlines the comprehensive test updates required to validate the new measure suffix (`_measure`) and hiding behavior (`hidden: yes`) across all test suites. The changes impact unit tests, integration tests, and golden files.

## Problem Context

**Parent Issue**: [DTL-022: Epic: Universal Measure Suffix and Hiding Strategy](../epics/DTL-022.md)

**Scope**: Update test expectations across all test layers to reflect:
1. Measure names now have `_measure` suffix in generated LookML
2. All measures have `hidden: yes` property in generated LookML
3. Metric measure references now include `_measure` suffix in SQL expressions

**Dependencies**:
- [DTL-023: Modify Measure.to_lookml_dict()](../issues/DTL-023.md) - Must be completed first
- [DTL-024: Update _resolve_measure_reference()](../issues/DTL-024.md) - Must be completed first

## Current Architecture Analysis

### Test Organization

```
src/tests/
├── unit/                           # Fast, isolated unit tests
│   ├── test_schemas.py            # Schema model tests (Entity, Dimension, Measure)
│   ├── test_lookml_generator.py   # Generator main functionality tests
│   ├── test_lookml_generator_metrics.py  # Metric SQL generation tests
│   └── test_*.py                  # Other unit tests
├── integration/                    # End-to-end integration tests
│   ├── test_end_to_end.py         # Full pipeline tests
│   ├── test_cross_entity_metrics.py  # Cross-entity metric tests
│   └── test_*.py                  # Other integration tests
├── golden/                         # Expected output files
│   ├── expected_users.view.lkml
│   ├── expected_searches.view.lkml
│   ├── expected_rental_orders.view.lkml
│   └── expected_explores.lkml
└── test_golden.py                 # Golden file comparison tests
```

### Affected Test Files by Layer

#### Unit Tests (7 files)
1. **test_schemas.py** - Tests for Measure model and to_lookml_dict()
2. **test_lookml_generator.py** - Tests for view/measure generation
3. **test_lookml_generator_metrics.py** - Tests for _resolve_measure_reference()
4. **test_metric_dependencies.py** - Tests for metric dependency resolution
5. **test_bi_field_filter.py** - Tests for field filtering (if measures included)
6. **test_hidden_parameter.py** - Tests for hidden parameter handling
7. **test_flat_meta.py** - Tests for flat metadata structure (if measures included)

#### Integration Tests (3 files)
1. **test_end_to_end.py** - End-to-end pipeline tests
2. **test_cross_entity_metrics.py** - Cross-entity metric generation
3. **test_metric_validation.py** - Metric validation integration tests

#### Golden Tests (1 file + 4 golden files)
1. **test_golden.py** - Golden file comparison tests
2. **expected_users.view.lkml** - User measures (3 measures)
3. **expected_searches.view.lkml** - Search measures (1+ measures)
4. **expected_rental_orders.view.lkml** - Rental order measures (multiple)
5. **expected_explores.lkml** - May contain metric references

### Current Test Patterns

#### Measure Generation Pattern (from test_schemas.py)
```python
class TestMeasure:
    def test_measure_to_lookml_dict(self) -> None:
        measure = Measure(name="revenue", agg=AggregationType.SUM)
        result = measure.to_lookml_dict()

        assert result["name"] == "revenue"  # ← WILL CHANGE
        assert result["type"] == "sum"
        assert "hidden" not in result  # ← WILL CHANGE
```

#### Measure Reference Pattern (from test_lookml_generator_metrics.py)
```python
class TestHelperMethods:
    def test_resolve_measure_reference_same_view(self, generator, models_dict):
        result = generator._resolve_measure_reference(
            "order_count", "order", models_dict
        )
        assert result == "${order_count}"  # ← WILL CHANGE
```

#### Golden File Pattern (from expected_users.view.lkml)
```lookml
measure: user_count {  # ← WILL CHANGE to user_count_measure
  type: count
  sql: ${TABLE}.user_count ;;
  description: "Total number of users"
  view_label: " Metrics"
  group_label: "Users Performance"
  # ← MISSING hidden: yes
}
```

## Implementation Strategy

### Phase 1: Unit Tests - Measure Schema Tests

**File**: `src/tests/unit/test_schemas.py`

**Test Classes to Update**:
- `TestMeasure` - Direct Measure model tests

**Changes Required**:

1. **test_measure_to_lookml_dict()** - Basic measure generation
   ```python
   # BEFORE
   assert result["name"] == "revenue"
   assert "hidden" not in result

   # AFTER
   assert result["name"] == "revenue_measure"
   assert result["hidden"] == "yes"
   ```

2. **test_measure_with_all_fields()** - Comprehensive measure test
   ```python
   # Update name assertion
   assert result["name"] == "total_revenue_measure"
   # Add hidden assertion
   assert result["hidden"] == "yes"
   ```

3. **test_measure_labels()** - Label handling tests
   ```python
   # Name should have suffix
   assert result["name"] == "user_count_measure"
   # Labels should remain unchanged
   assert result["view_label"] == " Metrics"
   # Hidden should be present
   assert result["hidden"] == "yes"
   ```

4. **Add new test**: `test_measure_suffix_and_hidden_always_applied()`
   ```python
   def test_measure_suffix_and_hidden_always_applied(self) -> None:
       """Test that _measure suffix and hidden: yes are always applied."""
       # Test with minimal measure
       minimal = Measure(name="count", agg=AggregationType.COUNT)
       result = minimal.to_lookml_dict()
       assert result["name"] == "count_measure"
       assert result["hidden"] == "yes"

       # Test with complex measure with labels
       complex_measure = Measure(
           name="revenue",
           agg=AggregationType.SUM,
           config=Config(meta=ConfigMeta(category="sales"))
       )
       result = complex_measure.to_lookml_dict()
       assert result["name"] == "revenue_measure"
       assert result["hidden"] == "yes"
       assert result["view_label"] == " Metrics"  # Labels preserved
   ```

**Estimated Changes**: ~8-10 test methods updated, 1-2 new tests added

### Phase 2: Unit Tests - Generator Measure Reference Tests

**File**: `src/tests/unit/test_lookml_generator_metrics.py`

**Test Classes to Update**:
- `TestHelperMethods` - _resolve_measure_reference() tests
- `TestSQLGenerationSimple` - Simple metric SQL generation
- `TestSQLGenerationRatio` - Ratio metric SQL generation
- `TestSQLGenerationDerived` - Derived metric SQL generation

**Changes Required**:

1. **TestHelperMethods** - All reference resolution tests (7 tests)
   ```python
   # test_resolve_measure_reference_same_view
   # BEFORE: assert result == "${order_count}"
   # AFTER:
   assert result == "${order_count_measure}"

   # test_resolve_measure_reference_cross_view
   # BEFORE: assert result == "${searches.search_count}"
   # AFTER:
   assert result == "${searches.search_count_measure}"

   # test_resolve_measure_reference_with_prefix
   # BEFORE: assert result == "${v_searches.search_count}"
   # AFTER:
   assert result == "${v_searches.search_count_measure}"
   ```

2. **TestSQLGenerationSimple** - Simple metric tests (4 tests)
   ```python
   # test_generate_simple_sql_same_view
   # BEFORE: assert sql == "${order_count}"
   # AFTER:
   assert sql == "${order_count_measure}"

   # test_generate_simple_sql_cross_view
   # BEFORE: assert sql == "${searches.search_count}"
   # AFTER:
   assert sql == "${searches.search_count_measure}"
   ```

3. **TestSQLGenerationRatio** - Ratio metric tests (5 tests)
   ```python
   # test_generate_ratio_sql_same_view
   # BEFORE: assert sql == "1.0 * ${numerator} / NULLIF(${denominator}, 0)"
   # AFTER:
   assert sql == "1.0 * ${numerator_measure} / NULLIF(${denominator_measure}, 0)"

   # test_generate_ratio_sql_cross_view
   # BEFORE: expected = "1.0 * ${orders.revenue} / NULLIF(${searches.search_count}, 0)"
   # AFTER:
   expected = "1.0 * ${orders.revenue_measure} / NULLIF(${searches.search_count_measure}, 0)"
   ```

4. **TestSQLGenerationDerived** - Derived metric tests (3 tests)
   ```python
   # Derived metrics reference other metrics which reference measures
   # The final SQL should have _measure suffix on all measure references
   # BEFORE: "${revenue} - ${cost}"
   # AFTER: "${revenue_measure} - ${cost_measure}"
   ```

**Estimated Changes**: ~19 test methods updated

### Phase 3: Unit Tests - View Generation Tests

**File**: `src/tests/unit/test_lookml_generator.py`

**Test Methods to Update**:
- `test_generate_view_lookml()` - View with measures
- `test_lookml_files_generation()` - Complete file generation
- Any test that validates measure presence in views

**Changes Required**:

1. **test_generate_view_lookml()**
   ```python
   # View generation test
   view = LookMLView(
       name="users",
       measures=[
           LookMLMeasure(
               name="count_measure",  # ← Add suffix
               type="count",
               sql="1",
               hidden="yes"  # ← Add hidden
           )
       ]
   )

   content = generator._generate_view_lookml(view)
   assert "measure: count_measure" in content
   assert "hidden: yes" in content
   ```

2. **test_lookml_files_generation()**
   ```python
   # Check generated content for suffix and hidden
   users_content = users_view.read_text()
   assert "measure: user_count_measure" in users_content
   assert "hidden: yes" in users_content
   ```

**Estimated Changes**: ~3-5 test methods updated

### Phase 4: Integration Tests - End-to-End Tests

**File**: `src/tests/integration/test_end_to_end.py`

**Test Methods to Update**:
- `test_parse_and_generate_sample_model()` - Sample model generation
- `test_real_semantic_models_end_to_end()` - Real models test
- Any test that validates measure content

**Changes Required**:

1. **Update measure content validation**
   ```python
   # When checking for measures in generated content
   if model.measures:
       assert "measure:" in content
       # Add validation for hidden property
       assert "hidden: yes" in content
       # Measure names will have suffix but exact names vary
       # Don't validate specific measure names unless necessary
   ```

2. **Metric reference validation** (if present)
   ```python
   # If tests validate metric SQL, update to expect _measure suffix
   if "metric" in content:
       # Metric references should use suffixed measure names
       pass  # Specific validation depends on test content
   ```

**Estimated Changes**: ~2-3 test methods updated

### Phase 5: Integration Tests - Cross-Entity Metrics

**File**: `src/tests/integration/test_cross_entity_metrics.py`

**Purpose**: Tests metric generation across different entity relationships

**Changes Required**:

1. **Update all metric SQL validation**
   ```python
   # Any assertion on metric SQL needs suffix update
   # Example:
   # BEFORE: assert "${orders.revenue}" in metric_sql
   # AFTER: assert "${orders.revenue_measure}" in metric_sql
   ```

2. **Update measure reference expectations**
   ```python
   # Cross-view measure references
   # BEFORE: "${other_view.measure_name}"
   # AFTER: "${other_view.measure_name_measure}"
   ```

**Estimated Changes**: ~5-8 test methods updated (depends on file content)

### Phase 6: Golden Files - Update Expected Output

**Files**:
- `src/tests/golden/expected_users.view.lkml`
- `src/tests/golden/expected_searches.view.lkml`
- `src/tests/golden/expected_rental_orders.view.lkml`
- `src/tests/golden/expected_explores.lkml` (if contains metrics)

**Changes Required**:

#### expected_users.view.lkml (3 measures)

**Current Content**:
```lookml
measure: user_count {
  type: count
  sql: ${TABLE}.user_count ;;
  description: "Total number of users"
  view_label: " Metrics"
  group_label: "Users Performance"
}

measure: active_users {
  type: count_distinct
  sql: CASE WHEN status = 'active' THEN user_id END ;;
  description: "Count of active users"
  view_label: " Metrics"
  group_label: "Users Performance"
}

measure: avg_lifetime_rentals {
  type: average
  sql: total_rentals ;;
  description: "Average number of rentals per user"
  view_label: " Metrics"
  group_label: "Users Performance"
}
```

**Updated Content**:
```lookml
measure: user_count_measure {
  hidden: yes
  type: count
  sql: ${TABLE}.user_count ;;
  description: "Total number of users"
  view_label: " Metrics"
  group_label: "Users Performance"
}

measure: active_users_measure {
  hidden: yes
  type: count_distinct
  sql: CASE WHEN status = 'active' THEN user_id END ;;
  description: "Count of active users"
  view_label: " Metrics"
  group_label: "Users Performance"
}

measure: avg_lifetime_rentals_measure {
  hidden: yes
  type: average
  sql: total_rentals ;;
  description: "Average number of rentals per user"
  view_label: " Metrics"
  group_label: "Users Performance"
}
```

**Pattern**:
1. Add `_measure` suffix to measure name
2. Add `hidden: yes` as first property after name
3. Keep all other properties unchanged

#### expected_searches.view.lkml

Apply same pattern to all measures in this file.

#### expected_rental_orders.view.lkml

Apply same pattern to all measures in this file.

#### expected_explores.lkml

**If contains metric definitions with measure references**:
```lookml
# BEFORE
measure: conversion_rate {
  sql: ${conversions} / ${searches} ;;
}

# AFTER
measure: conversion_rate {
  sql: ${conversions_measure} / ${searches_measure} ;;
}
```

**Update Strategy**:
- Can regenerate golden files using the update helper method in test_golden.py
- Or manually update each measure following the pattern above

### Phase 7: Golden Tests - Update Comparison Tests

**File**: `src/tests/test_golden.py`

**Changes Required**:

1. **Update measure content assertions** in various test methods:
   ```python
   # test_complex_semantic_model_features_preserved
   # Add assertion for hidden measures
   assert "hidden: yes" in content
   # Update measure name expectations if checking specific names
   assert "measure:" in content  # Generic check still works
   ```

2. **test_golden_files_comprehensive_coverage()**
   ```python
   # When checking for measures
   if model.measures:
       assert "measure:" in content
       # Add check for hidden property
       assert "hidden: yes" in content
       # Check for suffix in measure names
       # Note: Specific measure names vary, so validate pattern not names
   ```

3. **Add new test**: `test_measures_always_hidden_with_suffix()`
   ```python
   def test_measures_always_hidden_with_suffix(
       self, semantic_models_dir: Path
   ) -> None:
       """Test that all generated measures have _measure suffix and hidden: yes."""
       parser = DbtParser()
       generator = LookMLGenerator()

       all_models = parser.parse_directory(semantic_models_dir)

       with TemporaryDirectory() as temp_dir:
           output_dir = Path(temp_dir)
           generated_files, _ = generator.generate_lookml_files(
               all_models, output_dir
           )

           for view_file in [f for f in generated_files if f.name.endswith(".view.lkml")]:
               content = view_file.read_text()

               # Find all measure blocks
               import re
               measures = re.findall(r'measure:\s+(\w+)\s+\{', content)

               for measure_name in measures:
                   # All measure names should end with _measure
                   assert measure_name.endswith("_measure"), (
                       f"Measure {measure_name} missing _measure suffix in {view_file.name}"
                   )

                   # Extract the measure block
                   measure_pattern = f'measure: {measure_name} {{[^}}]+}}'
                   measure_block = re.search(measure_pattern, content, re.DOTALL)

                   if measure_block:
                       block_content = measure_block.group(0)
                       assert "hidden: yes" in block_content, (
                           f"Measure {measure_name} missing hidden: yes in {view_file.name}"
                       )
   ```

**Estimated Changes**: ~3-5 test methods updated, 1 new test added

## Testing Approach

### Test Execution Strategy

1. **Incremental Testing**:
   ```bash
   # Test each phase independently
   pytest src/tests/unit/test_schemas.py::TestMeasure -xvs
   pytest src/tests/unit/test_lookml_generator_metrics.py -xvs
   pytest src/tests/unit/test_lookml_generator.py -xvs
   pytest src/tests/integration/test_end_to_end.py -xvs
   pytest src/tests/integration/test_cross_entity_metrics.py -xvs
   pytest src/tests/test_golden.py -xvs
   ```

2. **Coverage Validation**:
   ```bash
   # After all updates, verify coverage maintained
   make test-coverage
   # Target: 95%+ branch coverage
   ```

3. **Full Test Suite**:
   ```bash
   # Final validation
   make test-full
   ```

### Validation Checklist

For each updated test file:
- [ ] All measure name assertions updated with `_measure` suffix
- [ ] All measure reference assertions updated with `_measure` suffix
- [ ] Hidden property assertions added where appropriate
- [ ] Labels and descriptions remain unchanged
- [ ] Cross-view references include suffix: `${view.measure_measure}`
- [ ] Same-view references include suffix: `${measure_measure}`
- [ ] Tests pass individually
- [ ] Coverage maintained at 95%+

## Risk Assessment

### Low Risk Changes
- Golden file updates (mechanical, easily validated)
- Simple assertion updates (name suffix checks)
- Hidden property checks (additive, no logic change)

### Medium Risk Changes
- Measure reference resolution tests (logic depends on suffix handling)
- Cross-entity metric tests (multiple reference points)

### Mitigation Strategies
1. **Incremental Validation**: Test each phase independently
2. **Golden File Regeneration**: Use update helper if manual updates error-prone
3. **Comprehensive Regex**: Use regex to find all measure references in tests
4. **Diff Review**: Carefully review diffs to ensure no unintended changes

## Edge Cases to Validate

1. **Measures with existing underscores**: `user_count` → `user_count_measure` (not `user_count__measure`)
2. **Metric reference chains**: Derived metrics → simple metrics → measures (all should have suffix)
3. **Cross-view with prefix**: `${v_orders.revenue_measure}` (prefix + suffix)
4. **Empty measure lists**: Tests with no measures should be unaffected
5. **Metric SQL expressions**: Complex SQL with multiple measure references

## Success Criteria

### Quantitative
- [ ] All unit tests pass (100%)
- [ ] All integration tests pass (100%)
- [ ] All golden tests pass (100%)
- [ ] Coverage maintained at 95%+ branch coverage
- [ ] No new linting or type errors introduced

### Qualitative
- [ ] All measure names have `_measure` suffix in generated LookML
- [ ] All measures have `hidden: yes` property
- [ ] All metric measure references include suffix
- [ ] Golden files accurately reflect new output format
- [ ] Test assertions clearly validate suffix and hidden behavior

## Implementation Order

1. **Phase 1**: Unit Tests - Measure Schema Tests (test_schemas.py)
   - Establishes base validation for Measure.to_lookml_dict()
   - Required first as foundation

2. **Phase 2**: Unit Tests - Generator Measure Reference Tests (test_lookml_generator_metrics.py)
   - Validates _resolve_measure_reference() behavior
   - Depends on Phase 1 understanding

3. **Phase 3**: Unit Tests - View Generation Tests (test_lookml_generator.py)
   - Validates view-level measure generation
   - Can run parallel to Phase 2

4. **Phase 6**: Golden Files - Update Expected Output
   - Update expected LookML files
   - Should be done before Phase 7
   - Can regenerate using helper method

5. **Phase 7**: Golden Tests - Update Comparison Tests (test_golden.py)
   - Updates golden file comparison logic
   - Depends on Phase 6 (golden files updated)

6. **Phase 4**: Integration Tests - End-to-End Tests (test_end_to_end.py)
   - Validates full pipeline
   - Depends on all unit tests passing

7. **Phase 5**: Integration Tests - Cross-Entity Metrics (test_cross_entity_metrics.py)
   - Validates complex metric scenarios
   - Should be last as it depends on all other changes

## Estimated Effort

- **Phase 1**: 1-2 hours (8-10 test updates, 1-2 new tests)
- **Phase 2**: 2-3 hours (19 test updates across multiple classes)
- **Phase 3**: 1 hour (3-5 test updates)
- **Phase 4**: 1 hour (2-3 test updates)
- **Phase 5**: 1-2 hours (5-8 test updates, file review)
- **Phase 6**: 1-2 hours (golden file updates, can use regeneration)
- **Phase 7**: 1-2 hours (3-5 test updates, 1 new test)

**Total Estimated**: 8-13 hours

## Code Review Focus Areas

1. **Consistency**: All measure references have suffix (no missed instances)
2. **Completeness**: Hidden property checked in all measure validation tests
3. **Correctness**: Golden files match generated output exactly
4. **Coverage**: New tests added for suffix/hidden behavior
5. **Clarity**: Test names and assertions clearly indicate what's being tested

## Rollback Strategy

If issues discovered post-merge:
1. **Revert DTL-025**: Revert test updates
2. **Revert DTL-024**: Revert _resolve_measure_reference() changes
3. **Revert DTL-023**: Revert Measure.to_lookml_dict() changes

All three must be reverted together as they form a cohesive change.

## Documentation Updates

No user-facing documentation changes required (test-only changes).

Internal documentation:
- Update test file docstrings if measure validation patterns change
- Update test_golden.py helper method documentation for golden file regeneration

## Dependencies

- **Blocks**: None (this is final task in epic)
- **Blocked By**:
  - DTL-023 (Measure.to_lookml_dict() implementation)
  - DTL-024 (_resolve_measure_reference() implementation)

## Notes

- Consider using regex search to find all measure references in tests before starting
- Golden files can be regenerated using `test_golden.py::update_golden_files_if_requested()` helper
- Keep git commits atomic: one phase per commit for easier review and rollback
- Test changes should be straightforward assertion updates (no logic changes in tests)
