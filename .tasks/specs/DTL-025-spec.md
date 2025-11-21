# Chore: Update test expectations for measure generation

## Metadata
- **Issue**: `DTL-025`
- **Stack**: `backend`
- **Generated**: 2025-01-21
- **Strategy**: Approved (DTL-025-strategy.md)
- **Type**: Test updates (chore)

## Issue Context

### Problem Statement
Update test files across all test suites to reflect the new measure suffix (`_measure`) and hiding behavior (`hidden: yes`) introduced by DTL-023 and DTL-024. This is a comprehensive test update to validate that measures are now generated with:
1. `_measure` suffix appended to measure names in LookML
2. `hidden: yes` property in all measure definitions
3. Metric measure references include the `_measure` suffix in SQL expressions

### Solution Approach
Systematically update test expectations across 7 phases:
1. Unit tests for Measure schema (test_schemas.py)
2. Unit tests for measure reference resolution (test_lookml_generator_metrics.py)
3. Unit tests for view generation (test_lookml_generator.py)
4. Integration tests for end-to-end pipeline (test_end_to_end.py)
5. Integration tests for cross-entity metrics (test_cross_entity_metrics.py)
6. Golden files with expected LookML output
7. Golden test comparison logic (test_golden.py)

### Success Criteria
- All 34 test files pass with updated expectations
- 95%+ branch coverage maintained across all modules
- All measure names have `_measure` suffix in generated LookML
- All measures have `hidden: yes` property
- All metric measure references include suffix
- Golden files accurately reflect new output format

## Approved Strategy Summary

The strategy divides test updates into 7 sequential phases, updating ~50-60 test methods across 11 test files plus 4 golden output files. The approach follows the implementation order:

1. **Phase 1-3**: Unit tests (foundation)
2. **Phase 6-7**: Golden files and tests (expected outputs)
3. **Phase 4-5**: Integration tests (end-to-end validation)

Key architectural decisions:
- Incremental testing per phase for quick validation
- Golden files can be regenerated using helper method
- Atomic git commits per phase for easier review
- Test-only changes (no production code modifications)

## Implementation Plan

### Phase 1: Unit Tests - Measure Schema Tests

**File**: `src/tests/unit/test_schemas.py`
**Class**: `TestMeasure` (lines 929-1013)
**Estimated effort**: 1-2 hours

**Tasks**:
1. **Update test_measure_creation() method**
   - Currently validates basic measure creation
   - NO CHANGES NEEDED (only tests Pydantic model creation, not LookML generation)

2. **Update test_count_measure() method**
   - Currently validates count measure with create_metric flag
   - NO CHANGES NEEDED (only tests model attributes, not LookML generation)

3. **Update test_measure_with_all_fields() method**
   - Currently validates measure with all optional fields
   - NO CHANGES NEEDED (only tests model attributes, not LookML generation)

4. **Update test_all_aggregation_types() method**
   - Currently validates all aggregation type constants
   - NO CHANGES NEEDED (only tests enum values, not LookML generation)

5. **Update test_measure_validation() method**
   - Currently validates Pydantic field validation
   - NO CHANGES NEEDED (validates required fields, not LookML generation)

6. **Update test_measure_with_filter_expression() method**
   - Currently validates CASE statement in expr field
   - NO CHANGES NEEDED (only tests model attributes, not LookML generation)

**NOTE**: After reviewing test_schemas.py TestMeasure class, most tests validate Pydantic model creation, NOT LookML generation. Need to find tests that actually call `to_lookml_dict()`.

**Search for actual to_lookml_dict() tests**:
- Look for tests calling `measure.to_lookml_dict()`
- These are the tests that need updates

### Phase 2: Unit Tests - Generator Measure Reference Tests

**File**: `src/tests/unit/test_lookml_generator_metrics.py`
**Classes**: `TestHelperMethods`, `TestSQLGenerationSimple`, `TestSQLGenerationRatio`, `TestSQLGenerationDerived`, `TestRequiredFieldsExtraction`, `TestMetricMeasureGeneration`
**Lines**: 1-1225
**Estimated effort**: 2-3 hours

**Task 2.1: Update TestHelperMethods (lines 19-114)**

7 test methods to update with `_measure` suffix in assertions:

1. **test_resolve_measure_reference_same_view (lines 71-78)**
   ```python
   # BEFORE line 78:
   assert result == "${order_count}"

   # AFTER:
   assert result == "${order_count_measure}"
   ```

2. **test_resolve_measure_reference_cross_view (lines 80-87)**
   ```python
   # BEFORE line 87:
   assert result == "${searches.search_count}"

   # AFTER:
   assert result == "${searches.search_count_measure}"
   ```

3. **test_resolve_measure_reference_with_prefix (lines 89-97)**
   ```python
   # BEFORE line 97:
   assert result == "${v_searches.search_count}"

   # AFTER:
   assert result == "${v_searches.search_count_measure}"
   ```

4. **test_resolve_measure_reference_missing_measure (lines 99-104)**
   - NO CHANGES NEEDED (tests error handling for nonexistent measure)

5. **test_resolve_measure_reference_missing_primary_entity (lines 106-114)**
   - NO CHANGES NEEDED (tests error handling for nonexistent entity)

**Task 2.2: Update TestSQLGenerationSimple (lines 116-208)**

4 test methods to update:

1. **test_generate_simple_sql_same_view (lines 142-153)**
   ```python
   # BEFORE line 153:
   assert sql == "${order_count}"

   # AFTER:
   assert sql == "${order_count_measure}"
   ```

2. **test_generate_simple_sql_cross_view (lines 155-166)**
   ```python
   # BEFORE line 166:
   assert sql == "${searches.search_count}"

   # AFTER:
   assert sql == "${searches.search_count_measure}"
   ```

3. **test_generate_simple_sql_with_prefix (lines 168-180)**
   ```python
   # BEFORE line 180:
   assert sql == "${v_searches.search_count}"

   # AFTER:
   assert sql == "${v_searches.search_count_measure}"
   ```

4. **test_generate_simple_sql_missing_primary_entity (lines 182-192)**
   - NO CHANGES NEEDED (tests error case)

5. **test_generate_simple_sql_wrong_type_params (lines 194-207)**
   - NO CHANGES NEEDED (tests error case)

**Task 2.3: Update TestSQLGenerationRatio (lines 210-353)**

5 test methods to update:

1. **test_generate_ratio_sql_both_same_view (lines 239-252)**
   ```python
   # BEFORE line 252:
   assert sql == "1.0 * ${revenue} / NULLIF(${order_count}, 0)"

   # AFTER:
   assert sql == "1.0 * ${revenue_measure} / NULLIF(${order_count_measure}, 0)"
   ```

2. **test_generate_ratio_sql_both_cross_view (lines 254-276)**
   ```python
   # BEFORE lines 274-275:
   assert (
       sql == "1.0 * ${orders.order_count} / NULLIF(${searches.search_count}, 0)"
   )

   # AFTER:
   assert (
       sql == "1.0 * ${orders.order_count_measure} / NULLIF(${searches.search_count_measure}, 0)"
   )
   ```

3. **test_generate_ratio_sql_num_same_denom_cross (lines 278-291)**
   ```python
   # BEFORE line 291:
   assert sql == "1.0 * ${order_count} / NULLIF(${searches.search_count}, 0)"

   # AFTER:
   assert sql == "1.0 * ${order_count_measure} / NULLIF(${searches.search_count_measure}, 0)"
   ```

4. **test_generate_ratio_sql_num_cross_denom_same (lines 293-306)**
   ```python
   # BEFORE line 306:
   assert sql == "1.0 * ${orders.order_count} / NULLIF(${search_count}, 0)"

   # AFTER:
   assert sql == "1.0 * ${orders.order_count_measure} / NULLIF(${search_count_measure}, 0)"
   ```

5. **test_generate_ratio_sql_with_prefix (lines 308-322)**
   ```python
   # BEFORE line 322:
   assert sql == "1.0 * ${order_count} / NULLIF(${v_searches.search_count}, 0)"

   # AFTER:
   assert sql == "1.0 * ${order_count_measure} / NULLIF(${v_searches.search_count_measure}, 0)"
   ```

6. **test_generate_ratio_sql_nullif_safety (lines 324-338)**
   - NO CHANGES NEEDED (tests NULLIF presence, not specific names)

7. **test_generate_ratio_sql_missing_primary_entity (lines 340-352)**
   - NO CHANGES NEEDED (tests error case)

**Task 2.4: Update TestSQLGenerationDerived (lines 355-516)**

3 test methods to update:

1. **test_generate_derived_sql_simple_addition (lines 408-428)**
   ```python
   # BEFORE line 428:
   assert sql == "${order_count} + ${searches.search_count}"

   # AFTER:
   assert sql == "${order_count_measure} + ${searches.search_count_measure}"
   ```

2. **test_generate_derived_sql_simple_subtraction (lines 430-450)**
   ```python
   # BEFORE line 450:
   assert sql == "${order_count} - ${searches.search_count}"

   # AFTER:
   assert sql == "${order_count_measure} - ${searches.search_count_measure}"
   ```

3. **test_generate_derived_sql_with_parentheses (lines 452-472)**
   ```python
   # BEFORE line 472:
   assert sql == "(${order_count} + ${searches.search_count}) / 2"

   # AFTER:
   assert sql == "(${order_count_measure} + ${searches.search_count_measure}) / 2"
   ```

4. **test_generate_derived_sql_cross_view_refs (lines 474-494)**
   ```python
   # BEFORE line 494:
   assert sql == "${revenue} + ${searches.search_count}"

   # AFTER:
   assert sql == "${revenue_measure} + ${searches.search_count_measure}"
   ```

5. **test_generate_derived_sql_missing_primary_entity (lines 496-515)**
   - NO CHANGES NEEDED (tests error case)

**Task 2.5: Update TestRequiredFieldsExtraction (lines 518-682)**

Update `required_fields` list expectations (6 test methods):

1. **test_extract_required_fields_simple_cross_view (lines 561-574)**
   ```python
   # BEFORE line 573:
   assert required == ["searches.search_count"]

   # AFTER:
   assert required == ["searches.search_count_measure"]
   ```

2. **test_extract_required_fields_ratio_both_cross (lines 575-598)**
   ```python
   # BEFORE line 598:
   assert sorted(required) == ["orders.order_count", "searches.search_count"]

   # AFTER:
   assert sorted(required) == ["orders.order_count_measure", "searches.search_count_measure"]
   ```

3. **test_extract_required_fields_ratio_mixed (lines 600-614)**
   ```python
   # BEFORE line 614:
   assert required == ["searches.search_count"]

   # AFTER:
   assert required == ["searches.search_count_measure"]
   ```

4. **test_extract_required_fields_derived_multiple (lines 616-634)**
   ```python
   # BEFORE line 634:
   assert required == ["searches.search_count"]

   # AFTER:
   assert required == ["searches.search_count_measure"]
   ```

5. **test_extract_required_fields_with_prefix (lines 636-651)**
   ```python
   # BEFORE line 651:
   assert required == ["v_searches.search_count"]

   # AFTER:
   assert required == ["v_searches.search_count_measure"]
   ```

6. **test_extract_required_fields_sorted (lines 653-681)**
   ```python
   # BEFORE line 681:
   assert required == ["orders.order_count", "searches.search_count"]

   # AFTER:
   assert required == ["orders.order_count_measure", "searches.search_count_measure"]
   ```

**Task 2.6: Update TestMetricMeasureGeneration (lines 818-1070)**

Update measure dict validation (5 test methods):

1. **test_generate_metric_measure_simple (lines 847-872)**
   ```python
   # BEFORE line 866:
   assert measure_dict["sql"] == "${order_count}"

   # AFTER:
   assert measure_dict["sql"] == "${order_count_measure}"
   ```

2. **test_generate_metric_measure_derived (lines 901-941)**
   ```python
   # BEFORE lines 939-940:
   assert "${order_count}" in measure_dict["sql"]
   assert "${searches.search_count}" in measure_dict["sql"]

   # AFTER:
   assert "${order_count_measure}" in measure_dict["sql"]
   assert "${searches.search_count_measure}" in measure_dict["sql"]

   # BEFORE line 941:
   assert measure_dict["required_fields"] == ["searches.search_count"]

   # AFTER:
   assert measure_dict["required_fields"] == ["searches.search_count_measure"]
   ```

3. **test_generate_metric_measure_required_fields (lines 943-959)**
   ```python
   # BEFORE line 959:
   assert measure_dict["required_fields"] == ["searches.search_count"]

   # AFTER:
   assert measure_dict["required_fields"] == ["searches.search_count_measure"]
   ```

4. **test_generate_metric_measure_ratio (lines 874-900)**
   ```python
   # BEFORE line 898:
   assert measure_dict["required_fields"] == ["searches.search_count"]

   # AFTER:
   assert measure_dict["required_fields"] == ["searches.search_count_measure"]
   ```

5. Other tests in this class are validation-focused and don't need updates

### Phase 3: Unit Tests - View Generation Tests

**File**: `src/tests/unit/test_lookml_generator.py`
**Size**: 3860 lines (very large file)
**Estimated effort**: 1 hour

**Strategy**: Search for specific test patterns that validate measure content

**Tasks**:
1. Search for tests calling `_generate_view_lookml()` and asserting on measure content
2. Search for tests validating measure names or hidden properties
3. Update assertions to include `_measure` suffix and `hidden: yes`

**Search patterns**:
```bash
grep -n "measure:" src/tests/unit/test_lookml_generator.py
grep -n "hidden" src/tests/unit/test_lookml_generator.py
grep -n "_generate_view" src/tests/unit/test_lookml_generator.py
```

### Phase 4: Integration Tests - End-to-End Tests

**File**: `src/tests/integration/test_end_to_end.py`
**Lines**: 500+ lines
**Estimated effort**: 1 hour

**Task 4.1: Review test methods that validate measure content**

From the file analysis (lines 1-500), these tests validate generated content:

1. **test_parse_and_generate_sample_model (lines 21-60)**
   - Validates that view files contain "view:" and "sql_table_name:"
   - NO SPECIFIC MEASURE VALIDATION - no changes needed

2. **test_real_semantic_models_end_to_end (lines 93-150)**
   - Line 143: `assert ("dimension:" in content or "measure:" in content)`
   - NO SPECIFIC MEASURE NAME VALIDATION - no changes needed

3. **test_all_aggregation_types_in_real_models (lines 184-217)**
   - Lines 216-217: Generic checks for "type: sum" or "type: count"
   - NO SPECIFIC MEASURE NAME VALIDATION - no changes needed

4. **Add validation for hidden property (optional enhancement)**
   - In tests that check for measures, could add: `assert "hidden: yes" in content`
   - But this is optional since golden tests will validate this

### Phase 5: Integration Tests - Cross-Entity Metrics

**File**: `src/tests/integration/test_cross_entity_metrics.py`
**Estimated effort**: 1-2 hours

**Strategy**: Need to read this file to identify specific tests

**Tasks**:
1. Find tests that validate metric SQL with measure references
2. Update assertions to include `_measure` suffix
3. Search for patterns like `"${model.measure}"` and update to `"${model.measure_measure}"`

### Phase 6: Golden Files - Update Expected Output

**Files**:
- `src/tests/golden/expected_users.view.lkml` (89 lines, 3 measures)
- `src/tests/golden/expected_searches.view.lkml` (82 lines, 2 measures)
- `src/tests/golden/expected_rental_orders.view.lkml` (91 lines, 3 measures)
- `src/tests/golden/expected_explores.lkml` (38 lines)

**Estimated effort**: 1-2 hours

**Task 6.1: Update expected_users.view.lkml**

3 measures to update (lines 52-74):

1. **user_count (lines 52-58)**
   ```lookml
   # BEFORE:
   measure: user_count {
     type: count
     sql: ${TABLE}.user_count ;;
     description: "Total number of users"
     view_label: " Metrics"
     group_label: "Users Performance"
   }

   # AFTER:
   measure: user_count_measure {
     hidden: yes
     type: count
     sql: ${TABLE}.user_count ;;
     description: "Total number of users"
     view_label: " Metrics"
     group_label: "Users Performance"
   }
   ```

2. **active_users (lines 60-66)**
   ```lookml
   # BEFORE:
   measure: active_users {
     type: count_distinct
     sql: CASE WHEN status = 'active' THEN user_id END ;;
     description: "Count of active users"
     view_label: " Metrics"
     group_label: "Users Performance"
   }

   # AFTER:
   measure: active_users_measure {
     hidden: yes
     type: count_distinct
     sql: CASE WHEN status = 'active' THEN user_id END ;;
     description: "Count of active users"
     view_label: " Metrics"
     group_label: "Users Performance"
   }
   ```

3. **avg_lifetime_rentals (lines 68-74)**
   ```lookml
   # BEFORE:
   measure: avg_lifetime_rentals {
     type: average
     sql: total_rentals ;;
     description: "Average number of rentals per user"
     view_label: " Metrics"
     group_label: "Users Performance"
   }

   # AFTER:
   measure: avg_lifetime_rentals_measure {
     hidden: yes
     type: average
     sql: total_rentals ;;
     description: "Average number of rentals per user"
     view_label: " Metrics"
     group_label: "Users Performance"
   }
   ```

**Task 6.2: Update expected_searches.view.lkml**

Search for measure blocks and apply same pattern:
1. Add `_measure` suffix to measure name
2. Add `hidden: yes` as first property after name
3. Keep all other properties unchanged

**Task 6.3: Update expected_rental_orders.view.lkml**

Search for measure blocks (3 measures based on grep output) and apply same pattern.

**Task 6.4: Update expected_explores.lkml (if needed)**

Check if this file contains metric definitions with measure references. If yes, update measure references to include `_measure` suffix.

### Phase 7: Golden Tests - Update Comparison Tests

**File**: `src/tests/test_golden.py`
**Estimated effort**: 1-2 hours

**Tasks**:

1. **Search for tests that validate measure content**
   ```bash
   grep -n "measure" src/tests/test_golden.py
   grep -n "hidden" src/tests/test_golden.py
   ```

2. **Add validation for hidden property** (if tests exist that check measures)
   - Add assertions like: `assert "hidden: yes" in content`

3. **Add new comprehensive test** (recommended):
   ```python
   def test_measures_always_hidden_with_suffix(
       self, semantic_models_dir: Path
   ) -> None:
       """Test that all generated measures have _measure suffix and hidden: yes."""
       import re
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
               measures = re.findall(r'measure:\s+(\w+)\s+\{', content)

               for measure_name in measures:
                   # All measure names should end with _measure
                   assert measure_name.endswith("_measure"), (
                       f"Measure {measure_name} missing _measure suffix in {view_file.name}"
                   )

                   # Extract the measure block and verify hidden: yes
                   measure_pattern = f'measure: {measure_name} {{[^}}]+}}'
                   measure_block = re.search(measure_pattern, content, re.DOTALL)

                   if measure_block:
                       block_content = measure_block.group(0)
                       assert "hidden: yes" in block_content, (
                           f"Measure {measure_name} missing hidden: yes in {view_file.name}"
                       )
   ```

## Detailed Task Breakdown

### Summary of Changes by File

| File | Test Methods | Assertions | New Tests | Estimated Lines |
|------|--------------|------------|-----------|-----------------|
| test_schemas.py | 0-2 | 0-6 | 0-1 | ~10-20 |
| test_lookml_generator_metrics.py | 19 | ~38 | 0 | ~38 |
| test_lookml_generator.py | 3-5 | ~6-10 | 0 | ~10-15 |
| test_end_to_end.py | 0-2 | 0-4 | 0 | ~0-5 |
| test_cross_entity_metrics.py | 5-8 | ~10-16 | 0 | ~10-20 |
| test_golden.py | 3-5 | ~6-10 | 1 | ~40-50 |
| expected_users.view.lkml | 3 measures | N/A | 0 | ~9 |
| expected_searches.view.lkml | 2 measures | N/A | 0 | ~6 |
| expected_rental_orders.view.lkml | 3 measures | N/A | 0 | ~9 |
| expected_explores.lkml | TBD | N/A | 0 | ~0-10 |
| **TOTAL** | **33-44** | **~60-84** | **1-2** | **~132-187** |

## Testing Strategy

### Incremental Testing Approach

Test each phase independently before moving to the next:

```bash
# Phase 1: Measure Schema Tests
pytest src/tests/unit/test_schemas.py::TestMeasure -xvs

# Phase 2: Measure Reference Tests
pytest src/tests/unit/test_lookml_generator_metrics.py -xvs

# Phase 3: View Generation Tests
pytest src/tests/unit/test_lookml_generator.py -xvs

# Phase 6-7: Golden Tests (after updating golden files)
pytest src/tests/test_golden.py -xvs

# Phase 4: End-to-End Tests
pytest src/tests/integration/test_end_to_end.py -xvs

# Phase 5: Cross-Entity Metrics
pytest src/tests/integration/test_cross_entity_metrics.py -xvs

# Final: Full test suite
make test-full
```

### Coverage Validation

After all updates:
```bash
# Check coverage maintained at 95%+
make test-coverage

# View HTML report
open htmlcov/index.html
```

### Edge Cases to Validate

1. **Measures with existing underscores**: `user_count` → `user_count_measure` (not `user_count__measure`)
2. **Metric reference chains**: Derived → simple → measures (all have suffix)
3. **Cross-view with prefix**: `${v_orders.revenue_measure}` (prefix + suffix)
4. **Empty measure lists**: Tests with no measures unaffected
5. **Complex SQL expressions**: Multiple measure references in one expression

## Validation Commands

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
pytest src/tests/unit/test_lookml_generator_metrics.py -xvs

# Run specific test method
pytest src/tests/unit/test_lookml_generator_metrics.py::TestHelperMethods::test_resolve_measure_reference_same_view -xvs

# Quality gate (lint + types + tests)
make quality-gate
```

## Dependencies

### Existing Dependencies
- `pytest`: Test framework
- `pytest-cov`: Coverage reporting
- `lkml`: LookML syntax validation
- All existing project dependencies

### No New Dependencies Needed
This is a test-only change with no new dependencies.

## Implementation Notes

### Important Considerations

1. **Test-only changes**: No production code modifications in this issue
2. **Dependency on DTL-023 and DTL-024**: Must be completed first
3. **Atomic commits**: One phase per commit for easier review
4. **Golden file regeneration**: Can use helper method if manual updates error-prone
5. **Backward compatibility**: Changes are additive (adding suffix and hidden property)

### Code Patterns to Follow

**Assertion Update Pattern**:
```python
# BEFORE
assert result == "${measure_name}"

# AFTER
assert result == "${measure_name_measure}"
```

**Golden File Update Pattern**:
```lookml
# BEFORE
measure: measure_name {
  type: count
  ...
}

# AFTER
measure: measure_name_measure {
  hidden: yes
  type: count
  ...
}
```

### References

- Strategy: `.tasks/strategies/DTL-025-strategy.md`
- Parent Epic: DTL-022 (Universal Measure Suffix and Hiding Strategy)
- Blocked by: DTL-023, DTL-024

## Ready for Implementation

This spec provides:
- ✅ Exact file locations and line numbers
- ✅ Specific assertion changes needed
- ✅ Golden file update patterns
- ✅ Incremental testing strategy
- ✅ Validation commands
- ✅ Estimated effort per phase (8-13 hours total)

**Next Steps**:
1. Ensure DTL-023 and DTL-024 are completed
2. Create feature branch: `feature/DTL-025-update-test-expectations`
3. Implement changes phase by phase
4. Test incrementally after each phase
5. Verify 95%+ coverage maintained
6. Create PR with phase-by-phase commits

## Appendix: Quick Reference

### Files to Modify

**Unit Tests**:
- `src/tests/unit/test_schemas.py` (TestMeasure class)
- `src/tests/unit/test_lookml_generator_metrics.py` (6 test classes)
- `src/tests/unit/test_lookml_generator.py` (search for measure validation)

**Integration Tests**:
- `src/tests/integration/test_end_to_end.py` (optional enhancements)
- `src/tests/integration/test_cross_entity_metrics.py` (measure reference assertions)

**Golden Files**:
- `src/tests/golden/expected_users.view.lkml` (3 measures)
- `src/tests/golden/expected_searches.view.lkml` (2 measures)
- `src/tests/golden/expected_rental_orders.view.lkml` (3 measures)
- `src/tests/golden/expected_explores.lkml` (check for metrics)

**Golden Tests**:
- `src/tests/test_golden.py` (add comprehensive validation test)

### Search Commands for Implementation

```bash
# Find all measure references in tests
grep -r "\${[a-z_]*}" src/tests/unit/test_lookml_generator_metrics.py

# Find all measure assertions
grep -n "assert.*measure" src/tests/unit/*.py

# Find measure blocks in golden files
grep -n "measure:" src/tests/golden/*.lkml
```
