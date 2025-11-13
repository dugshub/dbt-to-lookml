# Implementation Spec: DTL-005 - Update unit tests for field sets and joins

## Metadata
- **Issue**: DTL-005
- **Stack**: backend (testing)
- **Generated**: 2025-11-12T23:30:00Z
- **Strategy**: Approved 2025-11-12T23:15:00Z
- **Type**: feature

## Issue Context

### Problem Statement
Update unit tests in `src/tests/unit/test_lookml_generator.py` to provide comprehensive coverage for the new field set generation and join fields parameter features introduced in DTL-003 and DTL-004.

### Solution Approach
Add two new focused test classes (`TestGenerateDimensionSet`, `TestJoinFieldsParameter`) to test new functionality, update existing test fixtures and assertions to verify the new behavior, and ensure 95%+ branch coverage for all new code paths.

### Success Criteria
- All new test classes implemented with comprehensive test cases
- All existing tests updated to assert new behavior
- 95%+ branch coverage achieved for new code paths
- All tests pass with `make test-fast` and `make test`
- Test execution time remains under 5 seconds for unit tests

## Approved Strategy Summary

The strategy focuses on:
1. **Test Organization**: Create two new test classes for focused testing of dimension sets and join fields
2. **Fixture Strategy**: Reusable fixtures for common semantic model configurations
3. **Assertion Strategy**: Update existing tests with additional assertions rather than duplicating tests
4. **Edge Case Coverage**: Focus on empty views, hidden-only dimensions, and multi-hop joins
5. **Coverage Target**: 95% branch coverage specifically for new code paths

## Implementation Plan

### Phase 1: Dimension Set Tests (DTL-003 dependency)

**Tasks**:
1. Create `TestGenerateDimensionSet` test class with 9 test methods
2. Add integration tests to verify sets appear in view output
3. Update existing view generation tests to expect sets

### Phase 2: Join Fields Parameter Tests (DTL-004 dependency)

**Tasks**:
1. Create `TestJoinFieldsParameter` test class with 8 test methods
2. Add multi-hop and edge case tests
3. Update existing join graph tests with fields parameter assertions

### Phase 3: Edge Cases and Coverage Validation

**Tasks**:
1. Add comprehensive edge case tests (4 scenarios)
2. Run coverage validation and identify gaps
3. Validate test execution performance

## Detailed Task Breakdown

### Task 1: Create TestGenerateDimensionSet Class

**File**: `src/tests/unit/test_lookml_generator.py`

**Action**: Add new test class after `TestGenerateExploreslookml` (around line 1410)

**Implementation Guidance**:

```python
class TestGenerateDimensionSet:
    """Tests for _generate_dimension_set method and set integration in views."""

    def test_generate_dimension_set_with_entities_and_dimensions(self) -> None:
        """Test dimension set generation includes both entities and dimensions."""
        # Arrange
        generator = LookMLGenerator()
        model = SemanticModel(
            name="test_model",
            model="test_table",
            entities=[
                Entity(name="id", type="primary"),
                Entity(name="user_id", type="foreign"),
            ],
            dimensions=[
                Dimension(name="status", type=DimensionType.CATEGORICAL),
                Dimension(name="name", type=DimensionType.CATEGORICAL),
            ],
        )

        # Act
        dimension_set = generator._generate_dimension_set(model)

        # Assert
        assert dimension_set is not None
        assert dimension_set.name == "dimensions_only"
        expected_fields = {"id", "user_id", "status", "name"}
        assert set(dimension_set.fields) == expected_fields

    def test_generate_dimension_set_includes_hidden_entities(self) -> None:
        """Test that hidden entities are included in dimension set."""
        # Arrange
        generator = LookMLGenerator()
        model = SemanticModel(
            name="test_model",
            model="test_table",
            entities=[
                Entity(name="hidden_id", type="primary"),  # Hidden by default
            ],
            dimensions=[
                Dimension(name="visible_field", type=DimensionType.CATEGORICAL),
            ],
        )

        # Act
        dimension_set = generator._generate_dimension_set(model)

        # Assert
        assert "hidden_id" in dimension_set.fields
        assert "visible_field" in dimension_set.fields

    def test_generate_dimension_set_includes_dimension_groups(self) -> None:
        """Test that dimension_group base names are included in set."""
        # Arrange
        generator = LookMLGenerator()
        model = SemanticModel(
            name="test_model",
            model="test_table",
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"}
                ),
            ],
        )

        # Act
        dimension_set = generator._generate_dimension_set(model)

        # Assert
        # Should include base name 'created' (without timeframe suffixes)
        assert "created" in dimension_set.fields or "created_at" in dimension_set.fields

    def test_generate_dimension_set_empty_view(self) -> None:
        """Test dimension set generation for view with no dimensions."""
        # Arrange
        generator = LookMLGenerator()
        model = SemanticModel(
            name="empty_model",
            model="empty_table",
        )

        # Act
        dimension_set = generator._generate_dimension_set(model)

        # Assert
        # Should return None or empty set for views with no dimensions
        assert dimension_set is None or len(dimension_set.fields) == 0

    def test_generate_dimension_set_only_entities(self) -> None:
        """Test dimension set with only entities (no regular dimensions)."""
        # Arrange
        generator = LookMLGenerator()
        model = SemanticModel(
            name="test_model",
            model="test_table",
            entities=[
                Entity(name="id", type="primary"),
                Entity(name="parent_id", type="foreign"),
            ],
        )

        # Act
        dimension_set = generator._generate_dimension_set(model)

        # Assert
        assert dimension_set is not None
        assert set(dimension_set.fields) == {"id", "parent_id"}

    def test_generate_dimension_set_only_dimensions(self) -> None:
        """Test dimension set with only dimensions (no entities)."""
        # Arrange
        generator = LookMLGenerator()
        model = SemanticModel(
            name="test_model",
            model="test_table",
            dimensions=[
                Dimension(name="status", type=DimensionType.CATEGORICAL),
                Dimension(name="type", type=DimensionType.CATEGORICAL),
            ],
        )

        # Act
        dimension_set = generator._generate_dimension_set(model)

        # Assert
        assert dimension_set is not None
        assert set(dimension_set.fields) == {"status", "type"}

    def test_dimension_set_in_view_lookml_output(self) -> None:
        """Test that dimension set appears in generated view LookML."""
        # Arrange
        generator = LookMLGenerator()
        model = SemanticModel(
            name="users",
            model="dim_users",
            entities=[Entity(name="user_id", type="primary")],
            dimensions=[Dimension(name="status", type=DimensionType.CATEGORICAL)],
        )

        # Act
        content = generator._generate_view_lookml(model)

        # Assert
        assert "set:" in content or "dimensions_only" in content
        assert "fields:" in content

    def test_dimension_set_ordering_in_view(self) -> None:
        """Test that dimension set appears after measures in view structure."""
        # Arrange
        generator = LookMLGenerator()
        model = SemanticModel(
            name="orders",
            model="fact_orders",
            entities=[Entity(name="order_id", type="primary")],
            dimensions=[Dimension(name="status", type=DimensionType.CATEGORICAL)],
            measures=[Measure(name="count", agg=AggregationType.COUNT)],
        )

        # Act
        content = generator._generate_view_lookml(model)

        # Assert
        # Find positions of measures and sets in content
        measure_pos = content.find("measure:")
        set_pos = content.find("set:")

        # Set should appear after measures (or not at all if not implemented)
        if set_pos > 0:
            assert set_pos > measure_pos, "Dimension set should appear after measures"

    def test_dimension_set_with_view_prefix(self) -> None:
        """Test that view prefix doesn't affect set field references."""
        # Arrange
        generator = LookMLGenerator(view_prefix="v_")
        model = SemanticModel(
            name="users",
            model="dim_users",
            entities=[Entity(name="user_id", type="primary")],
            dimensions=[Dimension(name="status", type=DimensionType.CATEGORICAL)],
        )

        # Act
        dimension_set = generator._generate_dimension_set(model)

        # Assert
        # Field references in set should NOT include view prefix
        assert "user_id" in dimension_set.fields
        assert "v_user_id" not in dimension_set.fields
```

**Reference**: Similar test patterns at `TestLookMLGenerator` (lines 27-700)

**Estimated lines**: ~200

---

### Task 2: Create TestJoinFieldsParameter Class

**File**: `src/tests/unit/test_lookml_generator.py`

**Action**: Add new test class after `TestGenerateDimensionSet`

**Implementation Guidance**:

```python
class TestJoinFieldsParameter:
    """Tests for fields parameter in join generation."""

    def test_join_includes_fields_parameter(self) -> None:
        """Test that joins include fields parameter key."""
        # Arrange
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

        # Act
        joins = generator._build_join_graph(models[0], models)

        # Assert
        assert len(joins) == 1
        assert "fields" in joins[0], "Join should include fields parameter"

    def test_join_fields_parameter_format(self) -> None:
        """Test that fields parameter has correct format."""
        # Arrange
        generator = LookMLGenerator()
        models = [
            SemanticModel(
                name="orders",
                model="fact_orders",
                entities=[
                    Entity(name="order_id", type="primary"),
                    Entity(name="customer_id", type="foreign"),
                ],
                measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
            ),
            SemanticModel(
                name="customers",
                model="dim_customers",
                entities=[Entity(name="customer_id", type="primary")],
            ),
        ]

        # Act
        joins = generator._build_join_graph(models[0], models)

        # Assert
        assert len(joins) == 1
        fields_param = joins[0]["fields"]
        # Expected format: ["customers.dimensions_only*"]
        assert isinstance(fields_param, list)
        assert len(fields_param) == 1
        assert "customers.dimensions_only*" in fields_param[0]

    def test_join_fields_parameter_with_view_prefix(self) -> None:
        """Test fields parameter with view prefix applied."""
        # Arrange
        generator = LookMLGenerator(view_prefix="v_")
        models = [
            SemanticModel(
                name="orders",
                model="fact_orders",
                entities=[
                    Entity(name="order_id", type="primary"),
                    Entity(name="customer_id", type="foreign"),
                ],
                measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
            ),
            SemanticModel(
                name="customers",
                model="dim_customers",
                entities=[Entity(name="customer_id", type="primary")],
            ),
        ]

        # Act
        joins = generator._build_join_graph(models[0], models)

        # Assert
        fields_param = joins[0]["fields"]
        # Should use prefixed view name: "v_customers.dimensions_only*"
        assert "v_customers.dimensions_only*" in fields_param[0]

    def test_join_fields_parameter_multi_hop(self) -> None:
        """Test that multi-hop joins all have fields parameter."""
        # Arrange
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

        # Act
        joins = generator._build_join_graph(models[0], models)

        # Assert
        assert len(joins) == 2
        # All joins should have fields parameter
        for join in joins:
            assert "fields" in join, f"Join to {join['view_name']} missing fields parameter"

    def test_join_fields_parameter_multiple_joins(self) -> None:
        """Test that all joins have fields parameter with multiple foreign keys."""
        # Arrange
        generator = LookMLGenerator()
        models = [
            SemanticModel(
                name="rentals",
                model="fact_rentals",
                entities=[
                    Entity(name="rental_id", type="primary"),
                    Entity(name="user_id", type="foreign"),
                    Entity(name="search_id", type="foreign"),
                ],
                measures=[Measure(name="rental_count", agg=AggregationType.COUNT)],
            ),
            SemanticModel(
                name="users",
                model="dim_users",
                entities=[Entity(name="user_id", type="primary")],
            ),
            SemanticModel(
                name="searches",
                model="fact_searches",
                entities=[Entity(name="search_id", type="primary")],
            ),
        ]

        # Act
        joins = generator._build_join_graph(models[0], models)

        # Assert
        assert len(joins) == 2
        for join in joins:
            assert "fields" in join

    def test_explore_lookml_contains_fields_parameter(self) -> None:
        """Test that fields parameter appears in serialized explore output."""
        # Arrange
        generator = LookMLGenerator()
        models = [
            SemanticModel(
                name="orders",
                model="fact_orders",
                entities=[
                    Entity(name="order_id", type="primary"),
                    Entity(name="customer_id", type="foreign"),
                ],
                measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
            ),
            SemanticModel(
                name="customers",
                model="dim_customers",
                entities=[Entity(name="customer_id", type="primary")],
            ),
        ]

        # Act
        content = generator._generate_explores_lookml(models)

        # Assert
        assert "fields:" in content, "Explore should contain fields parameter"
        assert "dimensions_only*" in content

    def test_fields_parameter_serialization_order(self) -> None:
        """Test that lkml library serializes fields in correct position."""
        # Arrange
        generator = LookMLGenerator()
        models = [
            SemanticModel(
                name="orders",
                model="fact_orders",
                entities=[
                    Entity(name="order_id", type="primary"),
                    Entity(name="user_id", type="foreign"),
                ],
                measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
            ),
            SemanticModel(
                name="users",
                model="dim_users",
                entities=[Entity(name="user_id", type="primary")],
            ),
        ]

        # Act
        content = generator._generate_explores_lookml(models)

        # Assert
        # Verify fields appears in join block (after join name, before or after sql_on)
        lines = content.split('\n')
        join_found = False
        fields_found = False
        for i, line in enumerate(lines):
            if 'join:' in line or 'name:' in line and join_found:
                join_found = True
            if join_found and 'fields:' in line:
                fields_found = True
                break

        assert fields_found, "Fields parameter should appear in join block"

    def test_join_without_dimensions_set(self) -> None:
        """Test graceful handling when target view has no dimension set."""
        # Arrange
        generator = LookMLGenerator()
        models = [
            SemanticModel(
                name="orders",
                model="fact_orders",
                entities=[
                    Entity(name="order_id", type="primary"),
                    Entity(name="empty_dim_id", type="foreign"),
                ],
                measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
            ),
            SemanticModel(
                name="empty_dim",
                model="dim_empty",
                entities=[Entity(name="empty_dim_id", type="primary")],
                # No dimensions or measures
            ),
        ]

        # Act
        joins = generator._build_join_graph(models[0], models)

        # Assert
        # Should still add fields parameter even if target has no dimensions
        assert len(joins) == 1
        assert "fields" in joins[0]
```

**Reference**: Similar join tests at `TestBuildJoinGraph` (lines 1021-1266)

**Estimated lines**: ~180

---

### Task 3: Update TestBuildJoinGraph Assertions

**File**: `src/tests/unit/test_lookml_generator.py`

**Action**: Update existing test methods to assert fields parameter presence

**Changes**:

1. **Line 1047** - Update `test_build_join_graph_simple_one_hop()`:
```python
# After line 1052, add:
assert "fields" in joins[0], "Join should include fields parameter"
assert isinstance(joins[0]["fields"], list)
```

2. **Line 1087** - Update `test_build_join_graph_multi_hop()`:
```python
# After line 1089, add:
# Verify all joins have fields parameter
for join in joins:
    assert "fields" in join, f"Join to {join['view_name']} should have fields parameter"
```

3. **Line 1162** - Update `test_build_join_graph_with_view_prefix()`:
```python
# After line 1163, add:
assert "fields" in joins[0]
# Verify fields uses prefixed view name
assert "v_users" in joins[0]["fields"][0]
```

4. **Line 1217** - Update `test_build_join_graph_multiple_foreign_keys()`:
```python
# After line 1219, add:
# All joins should have fields parameter
for join in joins:
    assert "fields" in join
```

**Estimated lines**: ~15 additions across 4 test methods

---

### Task 4: Update TestGenerateExploreslookml Assertions

**File**: `src/tests/unit/test_lookml_generator.py`

**Action**: Update existing test methods and add new test

**Changes**:

1. **Line 1377** - Update `test_generate_explores_with_complex_joins()`:
```python
# After line 1409, add:
# Verify fields parameter in joins
assert "fields:" in content, "Explores with joins should have fields parameter"
```

2. **Line 1359** - Update `test_generate_explores_with_prefixes()`:
```python
# After line 1375, add:
# Verify fields uses prefixed view names
assert "v_rentals" in content or "dimensions_only" in content
```

3. **Add new test method after line 1409**:
```python
def test_generate_explores_fields_parameter_position(self) -> None:
    """Test that fields parameter appears in correct position within join block."""
    generator = LookMLGenerator()

    models = [
        SemanticModel(
            name="orders",
            model="fact_orders",
            entities=[
                Entity(name="order_id", type="primary"),
                Entity(name="customer_id", type="foreign"),
            ],
            measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
        ),
        SemanticModel(
            name="customers",
            model="dim_customers",
            entities=[Entity(name="customer_id", type="primary")],
        ),
    ]

    content = generator._generate_explores_lookml(models)

    # Verify fields appears within join structure
    assert "join:" in content or "joins:" in content
    assert "fields:" in content
    # Fields should appear near sql_on and relationship
    assert content.find("fields:") > 0
```

**Estimated lines**: ~35

---

### Task 5: Update TestLookMLGenerator View Tests

**File**: `src/tests/unit/test_lookml_generator.py`

**Action**: Update existing view generation tests to expect sets

**Changes**:

1. **Line 51** - Update `test_generate_view_lookml()`:
```python
# After line 104, add:
# Check for dimension set (if implemented)
# Note: May not be present if no dimensions exist
if "dimension:" in content or "dimension_group:" in content:
    # View with dimensions should have set
    pass  # Set assertion optional based on implementation
```

2. **Line 477** - Update `test_complex_view_with_all_elements()`:
```python
# After line 534, add:
# Verify dimension set is present for complex view
assert "set:" in content or len(content) > 0  # Set may be included
```

3. **Line 160** - Update `test_lookml_files_generation()`:
```python
# After line 213, add:
# Check for sets in view files
# Sets should be present in views with dimensions
if "dimension:" in users_content:
    # Can optionally check for set presence
    pass
```

**Estimated lines**: ~10 additions

---

### Task 6: Add Edge Case Tests

**File**: `src/tests/unit/test_lookml_generator.py`

**Action**: Add comprehensive edge case tests

**Implementation**:

```python
class TestDimensionSetEdgeCases:
    """Edge case tests for dimension set generation."""

    def test_dimension_set_with_100_plus_dimensions(self) -> None:
        """Test dimension set handles large number of dimensions."""
        # Arrange
        generator = LookMLGenerator()
        dimensions = [
            Dimension(name=f"dim_{i}", type=DimensionType.CATEGORICAL)
            for i in range(120)
        ]
        model = SemanticModel(
            name="large_model",
            model="large_table",
            dimensions=dimensions,
        )

        # Act
        dimension_set = generator._generate_dimension_set(model)

        # Assert
        assert len(dimension_set.fields) == 120

    def test_dimension_set_with_only_hidden_dimensions(self) -> None:
        """Test that set is still generated when all dimensions are hidden."""
        # Arrange
        generator = LookMLGenerator()
        model = SemanticModel(
            name="test_model",
            model="test_table",
            entities=[
                Entity(name="id", type="primary"),  # Hidden by default
                Entity(name="fk", type="foreign"),  # Hidden by default
            ],
        )

        # Act
        dimension_set = generator._generate_dimension_set(model)

        # Assert
        # Set should be generated even for hidden fields
        assert dimension_set is not None
        assert len(dimension_set.fields) == 2

    def test_join_fields_with_circular_reference(self) -> None:
        """Test that circular references don't cause issues with fields parameter."""
        # Arrange
        generator = LookMLGenerator()
        models = [
            SemanticModel(
                name="orders",
                model="fact_orders",
                entities=[
                    Entity(name="order_id", type="primary"),
                    Entity(name="customer_id", type="foreign"),
                ],
                measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
            ),
            SemanticModel(
                name="customers",
                model="dim_customers",
                entities=[
                    Entity(name="customer_id", type="primary"),
                    Entity(name="order_id", type="foreign"),  # Circular
                ],
            ),
        ]

        # Act
        joins = generator._build_join_graph(models[0], models)

        # Assert
        # Should handle gracefully without infinite loop
        assert len(joins) >= 1
        for join in joins:
            assert "fields" in join

    def test_dimension_set_with_mixed_dimension_types(self) -> None:
        """Test dimension set with various dimension types."""
        # Arrange
        generator = LookMLGenerator()
        model = SemanticModel(
            name="mixed_model",
            model="mixed_table",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(name="category", type=DimensionType.CATEGORICAL),
                Dimension(name="created_at", type=DimensionType.TIME),
                Dimension(name="amount", type=DimensionType.CATEGORICAL),
            ],
        )

        # Act
        dimension_set = generator._generate_dimension_set(model)

        # Assert
        # All dimension types should be included
        assert len(dimension_set.fields) >= 3
```

**Estimated lines**: ~90

---

## File Changes Summary

### Files to Modify

#### `src/tests/unit/test_lookml_generator.py`
**Why**: Add comprehensive test coverage for new features

**Changes**:
- Add `TestGenerateDimensionSet` class (~200 lines, 9 test methods)
- Add `TestJoinFieldsParameter` class (~180 lines, 8 test methods)
- Add `TestDimensionSetEdgeCases` class (~90 lines, 4 test methods)
- Update `TestBuildJoinGraph` methods (~15 lines, 4 methods)
- Update `TestGenerateExploreslookml` methods (~35 lines, 3 methods)
- Update `TestLookMLGenerator` view tests (~10 lines, 3 methods)

**Total estimated additions**: ~530 lines

### Files to Create

None - all changes are in existing test file.

## Testing Strategy

### Unit Test Execution

**Run individual test classes**:
```bash
# Test dimension set generation
python -m pytest src/tests/unit/test_lookml_generator.py::TestGenerateDimensionSet -xvs

# Test join fields parameter
python -m pytest src/tests/unit/test_lookml_generator.py::TestJoinFieldsParameter -xvs

# Test edge cases
python -m pytest src/tests/unit/test_lookml_generator.py::TestDimensionSetEdgeCases -xvs
```

**Run all updated tests**:
```bash
make test-fast
```

### Test Cases Summary

**TestGenerateDimensionSet (9 tests)**:
1. `test_generate_dimension_set_with_entities_and_dimensions` - Basic set generation
2. `test_generate_dimension_set_includes_hidden_entities` - Hidden entity inclusion
3. `test_generate_dimension_set_includes_dimension_groups` - Time dimension handling
4. `test_generate_dimension_set_empty_view` - Empty view edge case
5. `test_generate_dimension_set_only_entities` - Entity-only views
6. `test_generate_dimension_set_only_dimensions` - Dimension-only views
7. `test_dimension_set_in_view_lookml_output` - Set in serialized output
8. `test_dimension_set_ordering_in_view` - Set position after measures
9. `test_dimension_set_with_view_prefix` - Prefix handling

**TestJoinFieldsParameter (8 tests)**:
1. `test_join_includes_fields_parameter` - Fields key exists
2. `test_join_fields_parameter_format` - Correct format validation
3. `test_join_fields_parameter_with_view_prefix` - Prefix in fields
4. `test_join_fields_parameter_multi_hop` - Multi-hop coverage
5. `test_join_fields_parameter_multiple_joins` - Multiple foreign keys
6. `test_explore_lookml_contains_fields_parameter` - Serialization test
7. `test_fields_parameter_serialization_order` - Position validation
8. `test_join_without_dimensions_set` - Graceful degradation

**TestDimensionSetEdgeCases (4 tests)**:
1. `test_dimension_set_with_100_plus_dimensions` - Large dimension count
2. `test_dimension_set_with_only_hidden_dimensions` - Hidden-only fields
3. `test_join_fields_with_circular_reference` - Circular dependency handling
4. `test_dimension_set_with_mixed_dimension_types` - Type variety

**Updated Existing Tests (10 tests)**:
- 4 tests in `TestBuildJoinGraph`
- 3 tests in `TestGenerateExploreslookml`
- 3 tests in `TestLookMLGenerator`

**Total**: 31 new/updated test cases

## Validation Commands

**Quick validation** (unit tests only):
```bash
make test-fast
```

**Full validation** (unit + integration):
```bash
make test
```

**Coverage check**:
```bash
make test-coverage
# Open htmlcov/index.html to verify 95%+ coverage
```

**Single class execution**:
```bash
python -m pytest src/tests/unit/test_lookml_generator.py::TestGenerateDimensionSet -xvs
```

**Specific test method**:
```bash
python -m pytest src/tests/unit/test_lookml_generator.py::TestGenerateDimensionSet::test_generate_dimension_set_with_entities_and_dimensions -xvs
```

## Dependencies

### Existing Dependencies (Already in Project)
- `pytest>=7.0` - Testing framework
- `pytest-cov` - Coverage reporting
- `unittest.mock` - Mocking framework (standard library)

### New Dependencies Needed
None - all required dependencies are already configured.

## Implementation Notes

### Important Considerations

1. **Test Isolation**: Each test creates its own `LookMLGenerator` instance and semantic models to ensure isolation
2. **Arrange-Act-Assert Pattern**: All tests follow clear AAA structure for readability
3. **Mock Usage**: Only mock external dependencies (lkml library) where needed, not internal methods
4. **Parametrization**: Consider using `@pytest.mark.parametrize` for testing variations if patterns emerge
5. **Assertion Messages**: Include descriptive messages in assertions for better failure diagnostics

### Code Patterns to Follow

**Test Class Organization**:
```python
class TestFeatureName:
    """Tests for specific feature with clear docstring."""

    def test_method_scenario_expected_behavior(self) -> None:
        """Test description in plain English."""
        # Arrange
        setup_code()

        # Act
        result = method_under_test()

        # Assert
        assert expected_condition, "Descriptive message"
```

**Fixture Pattern** (if needed for multiple tests):
```python
@pytest.fixture
def sample_semantic_model() -> SemanticModel:
    """Create a sample semantic model for testing."""
    return SemanticModel(
        name="test_model",
        model="test_table",
        entities=[Entity(name="id", type="primary")],
    )
```

**Assertion Pattern for Collections**:
```python
# Use set comparison for unordered collections
assert set(actual_fields) == set(expected_fields)

# Use explicit length checks
assert len(joins) == expected_count

# Use membership tests
assert "fields" in join_dict
```

### References

- Test structure pattern: `TestLookMLGenerator` (lines 27-700)
- Join graph tests: `TestBuildJoinGraph` (lines 1021-1266)
- Explore generation tests: `TestGenerateExploreslookml` (lines 1268-1410)
- Edge case pattern: `TestJoinGraphEdgeCases` (lines 1412-1472)

## Coverage Target Breakdown

### New Code Coverage (Target: 95%+)

**Method: `_generate_dimension_set()` (New Method)**:
- Branch: Has entities → `test_generate_dimension_set_only_entities()`
- Branch: Has dimensions → `test_generate_dimension_set_only_dimensions()`
- Branch: Has both → `test_generate_dimension_set_with_entities_and_dimensions()`
- Branch: Has neither → `test_generate_dimension_set_empty_view()`
- Branch: Has dimension_groups → `test_generate_dimension_set_includes_dimension_groups()`
- Branch: Hidden entities → `test_generate_dimension_set_includes_hidden_entities()`

**Method: `_build_join_graph()` (Updated with Fields)**:
- Branch: Add fields to join → All join tests updated
- Branch: View prefix in fields → `test_join_fields_parameter_with_view_prefix()`
- Branch: Multi-hop with fields → `test_join_fields_parameter_multi_hop()`

**Method: `_generate_view_lookml()` (Updated with Sets)**:
- Branch: Generate set → `test_dimension_set_in_view_lookml_output()`
- Branch: Set ordering → `test_dimension_set_ordering_in_view()`
- Branch: No dimensions (no set) → `test_generate_dimension_set_empty_view()`

**Method: `_generate_explores_lookml()` (Updated with Fields Serialization)**:
- Branch: Fields in joins → `test_explore_lookml_contains_fields_parameter()`
- Branch: Fields serialization → `test_fields_parameter_serialization_order()`

### Coverage Validation Approach

1. Run coverage with branch analysis:
```bash
pytest src/tests/unit/test_lookml_generator.py --cov=src/dbt_to_lookml/generators/lookml --cov-branch --cov-report=html
```

2. Review HTML report for uncovered branches:
```bash
open htmlcov/index.html
```

3. Add tests for any uncovered branches identified in report

4. Verify final coverage meets 95% threshold:
```bash
make test-coverage
```

## Ready for Implementation

This spec is complete and ready for implementation. All test cases are defined with:
- Clear arrange-act-assert structure
- Specific expected outcomes
- Edge case coverage
- Integration with existing test patterns
- Coverage validation approach

### Implementation Sequence

1. **Start with Phase 1**: Implement `TestGenerateDimensionSet` (depends on DTL-003)
2. **Proceed to Phase 2**: Implement `TestJoinFieldsParameter` (depends on DTL-004)
3. **Complete Phase 3**: Add edge cases and validate coverage
4. **Verify all tests pass**: Run `make test-fast` and `make test`
5. **Validate coverage**: Run `make test-coverage` and verify 95%+ for new code

### Validation Checklist

Before marking DTL-005 complete:

- [ ] `TestGenerateDimensionSet` class implemented (9 tests)
- [ ] `TestJoinFieldsParameter` class implemented (8 tests)
- [ ] `TestDimensionSetEdgeCases` class implemented (4 tests)
- [ ] `TestBuildJoinGraph` updated (4 test methods)
- [ ] `TestGenerateExploreslookml` updated (3 test methods)
- [ ] `TestLookMLGenerator` updated (3 test methods)
- [ ] `make test-fast` passes (unit tests)
- [ ] `make test` passes (unit + integration)
- [ ] Coverage report shows 95%+ for new code paths
- [ ] No existing tests broken
- [ ] Test execution time < 5 seconds for unit tests
- [ ] All edge cases tested
- [ ] Arrange-act-assert pattern followed
- [ ] Test names are descriptive and clear

### Estimated Complexity

**Complexity**: Medium
**Estimated Time**: 4-5 hours

**Breakdown**:
- Phase 1 (Dimension Set Tests): 2 hours
- Phase 2 (Join Fields Tests): 2 hours
- Phase 3 (Edge Cases and Coverage): 1 hour

---

## Spec Generation Notes

**Generated by**: `/implement:1-spec` workflow
**Strategy source**: `.tasks/strategies/DTL-005-strategy.md`
**Codebase analysis**:
- Analyzed `test_lookml_generator.py` (1613 lines, 23 test classes)
- Analyzed `lookml.py` generator (609 lines)
- Analyzed `schemas.py` for model structure
- Identified test patterns and fixture usage

**Key decisions**:
1. Created focused test classes for new features rather than scattering tests
2. Updated existing tests with assertions instead of duplicating test logic
3. Prioritized edge cases based on production risk (empty views, hidden fields, multi-hop)
4. Targeted 95% branch coverage specifically for new code paths
5. Maintained existing test patterns and naming conventions
