# Implementation Strategy: DTL-006

**Issue**: DTL-006 - Update integration and golden tests
**Analyzed**: 2025-11-12T18:40:00Z
**Stack**: backend
**Type**: feature

## Approach

Update end-to-end integration and golden file tests to validate field exposure control works correctly. This involves creating comprehensive test fixtures with join scenarios, updating expected LookML output files to include field sets and join constraints, and adding new integration test cases for multi-hop joins and field exposure verification.

This is the validation layer for the field exposure control epic (DTL-001), ensuring that:
1. Field sets are generated correctly in views
2. Joins properly constrain exposed fields using `fields:` parameters
3. Multi-hop joins maintain field constraints through the chain
4. Golden files accurately reflect the new LookML structure

## Architecture Impact

**Layer**: Testing (validation layer for schemas + generators)

**New Files**:
- `src/semantic_models/sem_users.yml` - User dimension semantic model fixture
- `src/semantic_models/sem_searches.yml` - Search dimension semantic model fixture
- `src/semantic_models/sem_rental_orders.yml` - Rental fact semantic model fixture (with joins)
- `src/tests/golden/expected_users.view.lkml` - Expected LookML for users view with sets
- `src/tests/golden/expected_searches.view.lkml` - Expected LookML for searches view with sets
- `src/tests/golden/expected_rental_orders.view.lkml` - Expected LookML for rental orders view with sets

**Modified Files**:
- `src/tests/test_golden.py` - Add tests for field sets and join field constraints
- `src/tests/integration/test_end_to_end.py` - Add field exposure integration tests
- `src/tests/golden/expected_explores.lkml` - Update to include `fields:` parameters in joins
- `src/tests/integration/test_join_field_exposure.py` (NEW) - Dedicated tests for join field exposure

## Dependencies

- **Depends on**:
  - DTL-002: LookML set support in schemas (MUST be complete)
  - DTL-003: Field set generation in views (MUST be complete)
  - DTL-004: Join generation with fields parameter (MUST be complete)
  - DTL-005: Unit tests updated (SHOULD be complete for confidence)

- **Blocking**: None (final validation step in epic)

- **Test Data Requirements**:
  - Need semantic model fixtures that represent real-world scenarios:
    - Fact table with foreign keys (rental_orders)
    - Dimension tables with both dimensions and measures (users, searches)
    - Multi-hop join scenario (rentals → searches → sessions)

## Testing Strategy

### Golden Test Updates

**Current State Analysis**:
- Fixture location: `src/tests/fixtures/sample_semantic_model.yml` (minimal single model)
- Golden output location: `src/tests/golden/expected_explores.lkml`
- Test fixture reference: `Path(__file__).parent.parent / "semantic_models"`
- Missing: `src/semantic_models/` directory with comprehensive fixtures

**Strategy**:
1. **Create semantic_models fixture directory** with representative models:
   - `sem_users.yml` - Dimension table with primary entity, dimensions, measures
   - `sem_searches.yml` - Dimension table with foreign keys (multi-hop scenario)
   - `sem_rental_orders.yml` - Fact table with foreign keys to users and searches
   - Use realistic field counts (5-10 dimensions, 3-5 measures per model)

2. **Generate expected output files** using helper method pattern:
   - Extend `update_golden_files_if_requested()` method in `test_golden.py`
   - Run generator with completed DTL-002/003/004 code to create baseline
   - Manually verify generated LookML contains:
     - `set: dimensions_only` in all views
     - All dimensions listed in the set (including hidden entities)
     - `fields: [view.dimensions_only*]` in all explore joins
   - Save as `expected_*.view.lkml` and `expected_explores.lkml`

3. **Add golden test verification cases**:
   - Test that views contain `set: dimensions_only`
   - Test that sets include all dimension fields (parse and count)
   - Test that explore joins include `fields:` parameter
   - Test that `fields:` references the correct view's `dimensions_only` set
   - Test multi-hop joins maintain field constraints at each level

### Integration Test Updates

**New Test File**: `src/tests/integration/test_join_field_exposure.py`

Test scenarios:
1. **Single join field exposure**:
   - Fact table joins dimension table
   - Verify generated explore has `fields: [dimension.dimensions_only*]`
   - Parse generated LookML and verify structure

2. **Multi-hop join field exposure**:
   - Fact → Dim1 → Dim2 chain (rentals → searches → sessions)
   - Verify each join has correct `fields:` parameter
   - Verify field constraints propagate correctly

3. **Dimension-only exposure verification**:
   - Generate LookML from fact + dimension models
   - Parse explores and extract join field constraints
   - Verify measures are NOT in the field list (dimensions only)

4. **Hidden entity inclusion in sets**:
   - Verify hidden entities (primary/foreign keys) are in `dimensions_only` set
   - Verify they're marked `hidden: yes` but still in the set
   - Important: Hidden fields needed for join relationships

**Updates to existing tests**:
- `test_end_to_end.py`:
  - Add assertion for `set:` existence in generated views
  - Add assertion for `fields:` in explore joins
  - Update smoke tests to verify field exposure control

### Test Fixture Design

**Semantic Model Structure**:

```yaml
# sem_users.yml - Dimension table
semantic_models:
  - name: users
    model: ref('dim_users')
    entities:
      - name: user_sk
        type: primary
        expr: user_sk
    dimensions:
      - name: user_id
        type: categorical
      - name: email_domain
        type: categorical
      - name: created_date
        type: time
    measures:
      - name: user_count
        agg: count
      - name: active_users
        agg: count_distinct

# sem_searches.yml - Dimension table with FK
semantic_models:
  - name: searches
    model: ref('dim_searches')
    entities:
      - name: search_sk
        type: primary
      - name: user_sk
        type: foreign
    dimensions:
      - name: search_query
        type: categorical
      - name: results_count
        type: categorical
    measures:
      - name: search_count
        agg: count

# sem_rental_orders.yml - Fact table
semantic_models:
  - name: rental_orders
    model: ref('fct_rentals')
    entities:
      - name: rental_sk
        type: primary
      - name: user_sk
        type: foreign
      - name: search_sk
        type: foreign
    dimensions:
      - name: booking_status
        type: categorical
      - name: rental_date
        type: time
    measures:
      - name: rental_count
        agg: count
      - name: total_revenue
        agg: sum
        expr: checkout_amount
```

### Expected LookML Structure

**View with field set** (`expected_users.view.lkml`):
```lookml
view: users {
  sql_table_name: dim_users ;;

  set: dimensions_only {
    fields: [
      user_sk,
      user_id,
      email_domain,
      created_date_date,
      created_date_month,
      created_date_year
    ]
  }

  dimension: user_sk {
    primary_key: yes
    hidden: yes
    type: string
    sql: ${TABLE}.user_sk ;;
  }

  dimension: user_id { ... }
  dimension: email_domain { ... }
  dimension_group: created_date { ... }

  measure: user_count { ... }
  measure: active_users { ... }
}
```

**Explore with field constraints** (`expected_explores.lkml`):
```lookml
include: "*.view.lkml"

explore: rental_orders {
  from: rental_orders

  join: users {
    type: left_outer
    sql_on: ${rental_orders.user_sk} = ${users.user_sk} ;;
    relationship: many_to_one
    fields: [users.dimensions_only*]
  }

  join: searches {
    type: left_outer
    sql_on: ${rental_orders.search_sk} = ${searches.search_sk} ;;
    relationship: many_to_one
    fields: [searches.dimensions_only*]
  }
}
```

## Process for Regenerating Expected Output Files

**Step-by-step workflow**:

1. **Setup fixture directory**:
   ```bash
   mkdir -p src/semantic_models
   # Create sem_users.yml, sem_searches.yml, sem_rental_orders.yml
   ```

2. **Generate baseline output** (after DTL-002/003/004 complete):
   ```bash
   uv run python -m dbt_to_lookml generate \
     -i src/semantic_models \
     -o src/tests/golden/temp_output
   ```

3. **Review and validate generated LookML**:
   - Manually inspect each `.view.lkml` file
   - Verify `set: dimensions_only` present and complete
   - Verify all dimensions listed (including hidden entities)
   - Verify `explores.lkml` has `fields:` in all joins
   - Check LookML syntax with `lkml.load()`

4. **Copy to expected output location**:
   ```bash
   cp src/tests/golden/temp_output/*.view.lkml src/tests/golden/
   mv src/tests/golden/*.view.lkml src/tests/golden/expected_*.view.lkml
   cp src/tests/golden/temp_output/explores.lkml \
      src/tests/golden/expected_explores.lkml
   rm -rf src/tests/golden/temp_output
   ```

5. **Create helper method** in `test_golden.py`:
   ```python
   def regenerate_golden_files_with_field_sets(self, golden_dir: Path) -> None:
       """Helper to regenerate golden files with field set support.

       Usage: Call manually during development when schema changes.
       Not run as part of regular test suite.
       """
       semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
       parser = DbtParser()
       generator = LookMLGenerator()

       # Parse all fixture models
       all_models = parser.parse_directory(semantic_models_dir)

       with TemporaryDirectory() as temp_dir:
           output_dir = Path(temp_dir)
           generated_files, _ = generator.generate_lookml_files(
               all_models, output_dir
           )

           # Copy each view file to golden directory
           for generated_file in generated_files:
               if generated_file.name.endswith(".view.lkml"):
                   model_name = generated_file.stem.replace(".view", "")
                   golden_file = golden_dir / f"expected_{model_name}.view.lkml"
                   content = generated_file.read_text()
                   golden_file.write_text(content)
               elif generated_file.name == "explores.lkml":
                   golden_file = golden_dir / "expected_explores.lkml"
                   content = generated_file.read_text()
                   golden_file.write_text(content)
   ```

6. **Validate golden files pass tests**:
   ```bash
   make test-golden
   ```

## Validation Criteria

**Explores show only dimensions from joins, not measures**:

1. **Parse explore join definitions**:
   ```python
   # In test case
   explores_content = (output_dir / "explores.lkml").read_text()
   parsed = lkml.load(explores_content)

   for explore in parsed['explores']:
       if 'joins' in explore:
           for join in explore['joins']:
               # Verify fields parameter exists
               assert 'fields' in join
               # Verify it references dimensions_only
               assert join['fields'] == [f"{join['name']}.dimensions_only*"]
   ```

2. **Verify dimension-only sets**:
   ```python
   # In test case
   view_content = (output_dir / "users.view.lkml").read_text()
   parsed = lkml.load(view_content)

   view = parsed['views'][0]
   # Verify set exists
   assert 'sets' in view
   dimensions_only_set = next(s for s in view['sets'] if s['name'] == 'dimensions_only')

   # Verify contains dimensions
   set_fields = dimensions_only_set['fields']
   dimension_names = [d['name'] for d in view.get('dimensions', [])]
   dimension_group_names = [f"{dg['name']}_{tf}"
                            for dg in view.get('dimension_groups', [])
                            for tf in dg['timeframes']]

   all_dimension_fields = dimension_names + dimension_group_names
   for dim_field in all_dimension_fields:
       assert dim_field in set_fields

   # Verify does NOT contain measures
   measure_names = [m['name'] for m in view.get('measures', [])]
   for measure_field in measure_names:
       assert measure_field not in set_fields
   ```

3. **Multi-hop join verification**:
   ```python
   # Verify chain: rental_orders → searches → (sessions if present)
   rental_explore = next(e for e in parsed['explores']
                        if e['name'] == 'rental_orders')

   # Each join should have field constraints
   for join in rental_explore.get('joins', []):
       assert 'fields' in join
       assert '.dimensions_only*' in join['fields'][0]
   ```

## Implementation Sequence

1. **Create semantic model fixtures** (30 min)
   - Create `src/semantic_models/` directory
   - Write `sem_users.yml`, `sem_searches.yml`, `sem_rental_orders.yml`
   - Validate YAML syntax and structure

2. **Generate baseline expected output** (20 min)
   - Run generator with completed DTL-002/003/004 code
   - Review generated LookML files
   - Manually verify field sets and join constraints
   - Save as expected output files

3. **Update golden test cases** (45 min)
   - Add test for field set presence in views
   - Add test for field set completeness (all dimensions included)
   - Add test for join field constraints in explores
   - Add test for multi-hop join field exposure
   - Update `update_golden_files_if_requested()` helper

4. **Create integration test file** (60 min)
   - Create `test_join_field_exposure.py`
   - Add single join field exposure test
   - Add multi-hop join field exposure test
   - Add dimension-only verification test
   - Add hidden entity inclusion test

5. **Update existing integration tests** (30 min)
   - Add field set assertions to `test_end_to_end.py`
   - Update smoke tests to check for `fields:` in joins
   - Verify backward compatibility tests still pass

6. **Run full test suite and fix issues** (45 min)
   - `make test-golden` - verify golden tests pass
   - `make test-integration` - verify integration tests pass
   - `make test-full` - verify all tests pass
   - Fix any issues discovered during test execution

7. **Update test documentation** (15 min)
   - Document golden file regeneration process
   - Add comments explaining field exposure test strategy
   - Update test README if exists

## Open Questions

- **Q**: Should we test field exposure with real external semantic models or only fixtures?
  - **Decision**: Use fixtures for golden/integration tests (deterministic). Real models tested in smoke tests only.

- **Q**: How to handle backward compatibility if field sets are optional?
  - **Decision**: Add tests for both with and without field sets to ensure graceful degradation.

- **Q**: Should multi-hop joins test all possible depth levels (1, 2, 3+ hops)?
  - **Decision**: Test depth 1 (direct) and depth 2 (multi-hop) only. Max depth is 2 per current implementation.

- **Q**: How to validate that measures are truly excluded from field exposure?
  - **Decision**: Parse generated explores, extract join field lists, verify no measure names appear.

## Estimated Complexity

**Complexity**: Medium
**Estimated Time**: 3.5-4.5 hours

**Breakdown**:
- Fixture creation: 30 min
- Baseline generation: 20 min
- Golden test updates: 45 min
- Integration test creation: 60 min
- Existing test updates: 30 min
- Full test suite validation: 45 min
- Documentation: 15 min

**Risk factors**:
- Depends on DTL-002/003/004 being fully complete
- May need multiple iterations to get expected output correct
- LookML parsing edge cases might surface during testing

## Success Metrics

- [ ] All golden tests pass with new expected output files
- [ ] Integration tests verify field sets in all generated views
- [ ] Integration tests verify `fields:` parameter in all explore joins
- [ ] Multi-hop join tests validate field constraints at each level
- [ ] Test coverage maintained at 95%+ branch coverage
- [ ] `make test-full` passes completely
- [ ] No regressions in existing test suite

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-006.md`
3. Change status from `refinement` to `awaiting-strategy-review`, then to `strategy-approved`
4. Run: `/implement:1-spec DTL-006`
