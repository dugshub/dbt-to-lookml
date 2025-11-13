# Implementation Spec: Update join generation with fields parameter

## Metadata
- **Issue**: DTL-004
- **Stack**: backend
- **Generated**: 2025-11-12T23:05:00Z
- **Strategy**: Approved 2025-11-12T23:00:00Z
- **Dependencies**: DTL-002 (LookML set schema), DTL-003 (dimension-only sets)

## Issue Context

### Problem Statement
Modify explore join generation to include `fields: [view.dimensions_only*]` parameter, constraining exposed fields to dimensions only in joined views.

### Solution Approach
Update the join dictionary structure in `_build_join_graph()` to include a `fields` parameter, and ensure `_generate_explores_lookml()` correctly serializes this parameter using the lkml library. This completes the field exposure control mechanism by referencing the dimension-only sets created by DTL-003.

### Success Criteria
- All join dictionaries include `fields` parameter with correct view name and wildcard syntax
- Fields parameter serializes correctly in explores.lkml output
- Multi-hop joins include fields parameter at all levels
- lkml library validates generated output without errors
- 95%+ branch coverage maintained

## Approved Strategy Summary

The implementation modifies two key methods in `LookMLGenerator`:

1. **`_build_join_graph()`** (lines 139-251): Add `fields` key to join dictionaries with value `["{view_name}.dimensions_only*"]`
2. **`_generate_explores_lookml()`** (lines 403-480): Ensure lkml library serializes the fields parameter correctly in join blocks

**Architecture Impact**: Isolated to generators layer, no schema changes needed (DTL-002 already added set support)

**Dependencies**: Assumes DTL-003 ensures all views have `dimensions_only` sets

## Implementation Plan

### Phase 1: Update Join Dictionary Structure

**Task**: Add `fields` parameter to join dictionaries in `_build_join_graph()`

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Location**: Lines 236-241 (join dictionary creation)

**Current Code**:
```python
# Create join block
join = {
    'view_name': target_view_name,
    'sql_on': sql_on,
    'relationship': relationship,
    'type': 'left_outer'
}
```

**Modified Code**:
```python
# Create join block
join = {
    'view_name': target_view_name,
    'sql_on': sql_on,
    'relationship': relationship,
    'type': 'left_outer',
    'fields': [f'{target_view_name}.dimensions_only*']
}
```

**Key Points**:
- Use `target_view_name` variable (already computed at line 197)
- Format: `["{view_name}.dimensions_only*"]` (list with single wildcard string)
- Position: After `type` in dictionary (order doesn't matter for dict, lkml library handles serialization order)

### Phase 2: Verify lkml Library Serialization

**Task**: Ensure lkml library correctly serializes `fields` as list parameter

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Location**: Lines 444-454 (join dict conversion in `_generate_explores_lookml()`)

**Current Code**:
```python
explore_dict['joins'] = []
for join in joins:
    join_dict = {
        'name': join['view_name'],
        'sql_on': join['sql_on'],
        'relationship': join['relationship'],
        'type': join['type']
    }
    explore_dict['joins'].append(join_dict)
```

**Modified Code**:
```python
explore_dict['joins'] = []
for join in joins:
    join_dict = {
        'name': join['view_name'],
        'sql_on': join['sql_on'],
        'relationship': join['relationship'],
        'type': join['type'],
        'fields': join['fields']
    }
    explore_dict['joins'].append(join_dict)
```

**Key Points**:
- Simply pass through the `fields` list from join dictionary
- lkml library (v5.0.2) handles list serialization correctly
- Expected output format: `fields: [view_name.dimensions_only*]`

### Phase 3: Add Unit Tests

**Task**: Add comprehensive unit tests for fields parameter

**File**: `src/tests/unit/test_lookml_generator.py`

**New Test Method 1**: `test_build_join_graph_includes_fields_parameter`
```python
def test_build_join_graph_includes_fields_parameter(self) -> None:
    """Test that join dictionaries include fields parameter."""
    generator = LookMLGenerator()

    models = [
        SemanticModel(
            name="rentals",
            model="fact_rentals",
            entities=[
                Entity(name="rental_id", type="primary"),
                Entity(name="user_id", type="foreign"),
            ],
            measures=[Measure(name="rental_count", agg=AggregationType.COUNT)],
        ),
        SemanticModel(
            name="users",
            model="dim_users",
            entities=[Entity(name="user_id", type="primary")],
        ),
    ]

    joins = generator._build_join_graph(models[0], models)

    assert len(joins) == 1
    assert 'fields' in joins[0]
    assert joins[0]['fields'] == ['users.dimensions_only*']
```

**New Test Method 2**: `test_build_join_graph_fields_with_view_prefix`
```python
def test_build_join_graph_fields_with_view_prefix(self) -> None:
    """Test that fields parameter uses correct view prefix."""
    generator = LookMLGenerator(view_prefix="v_")

    models = [
        SemanticModel(
            name="rentals",
            model="fact_rentals",
            entities=[
                Entity(name="rental_id", type="primary"),
                Entity(name="user_id", type="foreign"),
            ],
            measures=[Measure(name="rental_count", agg=AggregationType.COUNT)],
        ),
        SemanticModel(
            name="users",
            model="dim_users",
            entities=[Entity(name="user_id", type="primary")],
        ),
    ]

    joins = generator._build_join_graph(models[0], models)

    assert len(joins) == 1
    assert joins[0]['fields'] == ['v_users.dimensions_only*']
```

**New Test Method 3**: `test_build_join_graph_multi_hop_includes_fields`
```python
def test_build_join_graph_multi_hop_includes_fields(self) -> None:
    """Test that multi-hop joins include fields parameter at all levels."""
    generator = LookMLGenerator()

    models = [
        SemanticModel(
            name="rentals",
            model="fact_rentals",
            entities=[
                Entity(name="rental_id", type="primary"),
                Entity(name="search_id", type="foreign"),
            ],
            measures=[Measure(name="rental_count", agg=AggregationType.COUNT)],
        ),
        SemanticModel(
            name="searches",
            model="fact_searches",
            entities=[
                Entity(name="search_id", type="primary"),
                Entity(name="user_id", type="foreign"),
            ],
        ),
        SemanticModel(
            name="users",
            model="dim_users",
            entities=[Entity(name="user_id", type="primary")],
        ),
    ]

    joins = generator._build_join_graph(models[0], models)

    # Should have joins to searches and users
    assert len(joins) == 2

    # All joins should have fields parameter
    for join in joins:
        assert 'fields' in join
        assert join['fields'][0].endswith('.dimensions_only*')

    # Verify specific view names
    view_names = {j['view_name'] for j in joins}
    assert view_names == {'searches', 'users'}

    # Verify fields match view names
    for join in joins:
        expected_fields = f"{join['view_name']}.dimensions_only*"
        assert join['fields'] == [expected_fields]
```

**Updated Test Method**: `test_build_join_graph_simple_one_hop`
```python
# Update existing test at line 1024 to assert fields parameter exists
def test_build_join_graph_simple_one_hop(self) -> None:
    """Test building a join graph with a single join."""
    generator = LookMLGenerator()

    models = [
        SemanticModel(
            name="rentals",
            model="fact_rentals",
            entities=[
                Entity(name="rental_id", type="primary"),
                Entity(name="user_id", type="foreign"),
            ],
            measures=[Measure(name="rental_count", agg=AggregationType.COUNT)],
        ),
        SemanticModel(
            name="users",
            model="dim_users",
            entities=[Entity(name="user_id", type="primary")],
        ),
    ]

    joins = generator._build_join_graph(models[0], models)

    assert len(joins) == 1
    assert joins[0]["view_name"] == "users"
    assert "${rentals.user_id}" in joins[0]["sql_on"]
    assert "${users.user_id}" in joins[0]["sql_on"]
    assert joins[0]["relationship"] == "many_to_one"
    assert joins[0]["type"] == "left_outer"
    # ADD THIS ASSERTION:
    assert joins[0]["fields"] == ["users.dimensions_only*"]
```

### Phase 4: Add Integration Tests

**Task**: Verify fields parameter appears in generated explores.lkml

**File**: `src/tests/unit/test_lookml_generator.py`

**New Test Method**: `test_generate_explores_includes_fields_in_joins`
```python
def test_generate_explores_includes_fields_in_joins(self) -> None:
    """Test that generated explores include fields parameter in join blocks."""
    generator = LookMLGenerator()

    models = [
        SemanticModel(
            name="rentals",
            model="fact_rentals",
            entities=[
                Entity(name="rental_id", type="primary"),
                Entity(name="user_id", type="foreign"),
            ],
            measures=[Measure(name="rental_count", agg=AggregationType.COUNT)],
        ),
        SemanticModel(
            name="users",
            model="dim_users",
            entities=[Entity(name="user_id", type="primary")],
        ),
    ]

    content = generator._generate_explores_lookml(models)

    # Verify fields parameter appears in output
    assert "fields:" in content
    assert "users.dimensions_only*" in content

    # Verify it's within a join block context
    assert "join:" in content or "joins:" in content

    # Validate syntax by parsing with lkml library
    import lkml
    parsed = lkml.load(content)
    assert parsed is not None
```

### Phase 5: Update Golden Tests (Coordinate with DTL-006)

**Task**: Ensure golden test expectations include fields parameter

**File**: `src/tests/golden/expected_explores.lkml`

**Note**: This file will be updated as part of DTL-006 (golden test regeneration). For now, ensure new tests don't break existing golden tests.

**Action**: Run golden tests to ensure they still pass:
```bash
python -m pytest src/tests/test_golden.py -xvs
```

If golden tests fail due to new fields parameter, this is expected and should be addressed in DTL-006.

### Phase 6: Manual Validation

**Task**: Generate sample LookML and validate syntax

**Commands**:
```bash
# Generate LookML with real semantic models
make lookml-preview

# Or generate actual files
uv run python -m dbt_to_lookml generate \
  -i src/tests/fixtures/semantic_models \
  -o /tmp/lookml_test \
  -v

# Inspect explores.lkml
cat /tmp/lookml_test/explores.lkml
```

**Expected Output** (excerpt from explores.lkml):
```lookml
explore: {
  rentals: {
    from: rentals
    joins: {
      users: {
        sql_on: ${rentals.user_id} = ${users.user_id}
        relationship: many_to_one
        type: left_outer
        fields: [users.dimensions_only*]
      }
    }
  }
}
```

## Detailed Task Breakdown

### Task 1: Modify `_build_join_graph()` to add fields parameter

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Add `fields` key to join dictionary

**Implementation Guidance**:
```python
# Line 236-241: Update join dictionary creation
join = {
    'view_name': target_view_name,
    'sql_on': sql_on,
    'relationship': relationship,
    'type': 'left_outer',
    'fields': [f'{target_view_name}.dimensions_only*']  # ADD THIS LINE
}
```

**Reference**: Similar dictionary pattern at lines 448-453 (join_dict in explores generation)

**Estimated lines**: 1 line added

### Task 2: Update `_generate_explores_lookml()` to serialize fields

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Pass through `fields` parameter in join_dict

**Implementation Guidance**:
```python
# Line 448-453: Add fields to join_dict
join_dict = {
    'name': join['view_name'],
    'sql_on': join['sql_on'],
    'relationship': join['relationship'],
    'type': join['type'],
    'fields': join['fields']  # ADD THIS LINE
}
```

**Reference**: lkml library serialization at line 471 (`lkml.dump({'explores': explores})`)

**Tests**: Verify lkml library preserves list format

**Estimated lines**: 1 line added

### Task 3: Add unit tests for fields parameter

**File**: `src/tests/unit/test_lookml_generator.py`

**Action**: Add 3 new test methods and update 1 existing test

**Test Cases**:
1. **test_build_join_graph_includes_fields_parameter**: Basic fields parameter test
2. **test_build_join_graph_fields_with_view_prefix**: Verify prefix handling
3. **test_build_join_graph_multi_hop_includes_fields**: Multi-hop join coverage
4. **Update test_build_join_graph_simple_one_hop**: Add fields assertion

**Estimated lines**: ~80 lines total

### Task 4: Add integration test for explores generation

**File**: `src/tests/unit/test_lookml_generator.py`

**Action**: Add `test_generate_explores_includes_fields_in_joins` method

**Purpose**: Verify end-to-end serialization through lkml library

**Estimated lines**: ~30 lines

### Task 5: Manual validation and documentation

**Action**: Generate test LookML files and verify syntax

**Commands**:
```bash
make lookml-preview
uv run python -m dbt_to_lookml validate -i src/tests/fixtures/semantic_models -v
```

**Expected**: No validation errors, fields parameter present in explores.lkml

## File Changes

### Files to Modify

#### `src/dbt_to_lookml/generators/lookml.py`

**Why**: Core join generation logic

**Changes**:
- Line 241: Add `'fields': [f'{target_view_name}.dimensions_only*']` to join dictionary
- Line 453: Add `'fields': join['fields']` to join_dict for serialization

**Estimated lines**: 2 lines modified (total file: 609 lines)

**Pattern**: Dictionary-based configuration (existing pattern in file)

#### `src/tests/unit/test_lookml_generator.py`

**Why**: Comprehensive test coverage for new functionality

**Changes**:
- Add 3 new test methods (~80 lines)
- Update 1 existing test method (~2 lines)
- Add 1 integration test method (~30 lines)

**Estimated lines**: ~112 lines added (total file: ~1725 lines)

**Pattern**: Class-based test organization with descriptive docstrings

### Files NOT Modified

- `src/dbt_to_lookml/schemas.py`: No changes (DTL-002 already added set support)
- `src/dbt_to_lookml/types.py`: No changes (no new types needed)
- Golden test files: Will be updated in DTL-006

## Testing Strategy

### Unit Tests

**File**: `src/tests/unit/test_lookml_generator.py`

**Test Cases**:

1. **test_build_join_graph_includes_fields_parameter**
   - Setup: Create rentals → users join scenario
   - Action: Call `_build_join_graph()`
   - Assert: `fields` key exists with value `['users.dimensions_only*']`

2. **test_build_join_graph_fields_with_view_prefix**
   - Setup: Generator with `view_prefix="v_"`
   - Action: Build join graph
   - Assert: `fields` value is `['v_users.dimensions_only*']`

3. **test_build_join_graph_multi_hop_includes_fields**
   - Setup: 3-model chain (rentals → searches → users)
   - Action: Build join graph
   - Assert: All 2 joins have `fields` parameter with correct view names

4. **test_generate_explores_includes_fields_in_joins** (integration)
   - Setup: Create models with join relationships
   - Action: Generate explores LookML
   - Assert: Output contains `fields:` and `dimensions_only*`, validates with lkml library

### Integration Tests

Run full generation pipeline to verify:

```bash
# Generate from fixtures
uv run python -m dbt_to_lookml generate \
  -i src/tests/fixtures/semantic_models \
  -o /tmp/test_output \
  --validate

# Verify explores.lkml contains fields parameter
grep -A 5 "join:" /tmp/test_output/explores.lkml | grep "fields:"
```

### Edge Cases

1. **Empty join graph**: Model with no foreign entities
   - Expected: No joins generated, no fields parameter
   - Test: Existing test `test_build_join_graph_no_foreign_entities`

2. **Missing target model**: Foreign key without matching primary
   - Expected: No join created (existing behavior)
   - Test: Existing test `test_build_join_graph_missing_target_model`

3. **Circular dependencies**: Avoid infinite loops
   - Expected: Visited set prevents cycles (existing behavior)
   - Test: Existing test `test_build_join_graph_circular_dependency`

### Coverage Target

**Target**: 95%+ branch coverage

**Key branches to cover**:
- Join dictionary creation with fields parameter (line 241)
- Join dict serialization with fields (line 453)
- Multi-hop traversal includes fields at all levels

**Command**:
```bash
make test-coverage
open htmlcov/index.html
```

## Validation Commands

### Backend Quality Gates

```bash
# Full quality gate (recommended)
make quality-gate

# Individual checks
make lint           # Ruff linting
make type-check     # Mypy strict type checking
make test           # Run unit + integration tests
make test-coverage  # Check 95% coverage target
```

### Specific Test Commands

```bash
# Run only new tests
python -m pytest src/tests/unit/test_lookml_generator.py::TestBuildJoinGraph::test_build_join_graph_includes_fields_parameter -xvs

# Run all join graph tests
python -m pytest src/tests/unit/test_lookml_generator.py::TestBuildJoinGraph -xvs

# Run integration test
python -m pytest src/tests/unit/test_lookml_generator.py::TestGenerateExploreslookml::test_generate_explores_includes_fields_in_joins -xvs

# Run full test suite
make test-full
```

### Manual Validation

```bash
# Preview generation (dry-run)
make lookml-preview

# Generate to temp directory
uv run python -m dbt_to_lookml generate \
  -i src/tests/fixtures/semantic_models \
  -o /tmp/lookml_validation \
  --validate

# Inspect output
cat /tmp/lookml_validation/explores.lkml

# Validate with lkml library
python -c "import lkml; print(lkml.load(open('/tmp/lookml_validation/explores.lkml').read()))"
```

## Dependencies

### Existing Dependencies

- **lkml** (v5.0.2): LookML parsing and serialization
  - Used at: Line 471 (`lkml.dump({'explores': explores})`)
  - Purpose: Serialize join dictionaries to LookML format
  - Note: Library preserves list syntax correctly

### New Dependencies Needed

None. All required functionality exists.

## Implementation Notes

### Important Considerations

1. **lkml Library Serialization Order**:
   - The lkml library may serialize join parameters in any order
   - LookML syntax doesn't enforce parameter order
   - Tests should verify presence, not position, of `fields` parameter

2. **View Prefix Handling**:
   - `target_view_name` variable (line 197) already includes prefix
   - No additional prefix logic needed for fields parameter
   - Tests verify prefix propagation

3. **Dimension Set Availability**:
   - Implementation assumes DTL-003 ensures all views have `dimensions_only` sets
   - No fallback logic needed for missing sets
   - Looker will error at explore query time if set doesn't exist (acceptable behavior)

4. **Multi-hop Join Coverage**:
   - BFS traversal in `_build_join_graph()` processes all reachable models
   - Depth limit of 2 hops (existing behavior)
   - Fields parameter applies to all joins regardless of depth

### Code Patterns to Follow

1. **Dictionary Construction**:
```python
# Existing pattern (lines 236-241)
join = {
    'view_name': target_view_name,
    'sql_on': sql_on,
    'relationship': relationship,
    'type': 'left_outer'
}

# Follow this pattern for fields addition
join['fields'] = [f'{target_view_name}.dimensions_only*']
```

2. **Test Method Naming**:
```python
# Pattern: test_{method_under_test}_{specific_aspect}
def test_build_join_graph_includes_fields_parameter(self) -> None:
    """Test that join dictionaries include fields parameter."""
```

3. **Type Hints**:
```python
# All functions require full type hints (mypy --strict)
def _build_join_graph(
    self,
    fact_model: SemanticModel,
    all_models: List[SemanticModel]
) -> List[Dict[str, str]]:  # Note: Will need to update to Dict[str, Any] for fields list
```

### References

- **Join dictionary structure**: `src/dbt_to_lookml/generators/lookml.py:236-241`
- **Join serialization**: `src/dbt_to_lookml/generators/lookml.py:444-454`
- **lkml library usage**: `src/dbt_to_lookml/generators/lookml.py:471`
- **Existing join tests**: `src/tests/unit/test_lookml_generator.py:1021-1266`
- **Multi-hop example**: Test at line 1054 (`test_build_join_graph_multi_hop`)

## Open Questions & Resolutions

### Q1: Does lkml library preserve list syntax for fields parameter correctly?

**Status**: To be verified in implementation

**Resolution approach**: Add explicit validation in unit tests to parse generated LookML back through `lkml.load()`

**Test**:
```python
content = generator._generate_explores_lookml(models)
parsed = lkml.load(content)
assert parsed is not None
# Verify fields is present in parsed structure
```

### Q2: What is the correct order of join parameters in LookML?

**Status**: Not strictly required

**Resolution**: lkml library handles serialization order; LookML syntax doesn't enforce specific order. Tests verify presence, not position.

### Q3: Should joins fail or warn if a view doesn't have a dimensions_only set?

**Status**: Out of scope for DTL-004

**Resolution**: Assume DTL-003 ensures all views have sets. Looker will error at query time if set is missing (acceptable behavior for misconfigured views).

## Estimated Complexity

**Complexity**: Low

**Estimated Time**: 2-3 hours

**Breakdown**:
- Code changes: 30 minutes (2 lines modified)
- Unit test implementation: 60 minutes (4 tests, ~100 lines)
- Integration testing: 30 minutes (1 test, manual validation)
- Documentation and validation: 30 minutes

**Rationale**:
- Minimal code changes (2 lines)
- Well-established testing patterns
- No new dependencies
- No architectural changes
- Main effort is comprehensive test coverage

## Ready for Implementation

This spec is complete and ready for implementation. All prerequisites are documented, code patterns are identified, and testing strategy is comprehensive.

**Next Steps**:
1. Implement code changes in `lookml.py`
2. Add unit tests in `test_lookml_generator.py`
3. Run quality gate: `make quality-gate`
4. Manual validation with `make lookml-preview`
5. Update DTL-004 issue status to "in-progress"
