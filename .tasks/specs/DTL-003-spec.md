# Implementation Specification: DTL-003

## Metadata
- **Issue**: `DTL-003`
- **Title**: Generate dimension-only field sets in views
- **Stack**: backend
- **Type**: feature
- **Generated**: 2025-11-12T22:55:00Z
- **Strategy**: Approved 2025-11-12T19:30:00Z

## Issue Context

### Problem Statement

Implement automatic generation of `set: dimensions_only` in all LookML view files, containing references to all dimension fields (including hidden entities). This set will enable selective field exposure when dimensional views are joined to fact explores, preventing dimensional measures from appearing in fact-based analysis.

### Solution Approach

Add a new `_generate_dimension_set()` private method to `LookMLGenerator` class that collects all dimension field names (entities + dimensions + dimension_groups) and creates a LookML set structure. Integrate this method into the existing `_generate_view_lookml()` pipeline to emit the set alongside dimensions and measures in the view structure.

### Success Criteria

- ✅ All generated view files include a `set: dimensions_only` field set
- ✅ Set includes all dimensions (regular dimensions, hidden entities, and dimension_groups)
- ✅ Views with no dimensions gracefully skip set generation
- ✅ Maintains existing view structure ordering
- ✅ 95%+ branch coverage for new code
- ✅ All tests passing (unit + integration + golden)

## Approved Strategy Summary

The implementation adds automatic generation of dimension-only field sets to LookML views through:

1. **New Schema**: Add `LookMLSet` Pydantic model in `schemas.py` for type-safe set representation
2. **Generator Method**: Implement `_generate_dimension_set()` in `LookMLGenerator` to collect dimension names
3. **Integration**: Call the new method from `_generate_view_lookml()` and include sets in view output
4. **Edge Cases**: Handle views with no dimensions (skip set generation)

**Key Architectural Decision**: Sets appear after measures in the view structure, maintaining clean separation of concerns: entities → dimensions → dimension_groups → measures → sets.

## Implementation Plan

### Phase 1: Add LookMLSet Schema (15-20 min)

Add type-safe schema for LookML field sets with serialization support.

**Tasks**:
1. **Add LookMLSet Pydantic Model**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`
   - Action: Add new class after `LookMLMeasure` (around line 428)
   - Pattern: Follow existing LookML* class patterns (LookMLDimension, LookMLMeasure, etc.)
   - Reference: `LookMLMeasure` class (lines 416-427)

### Phase 2: Implement _generate_dimension_set() Method (30-40 min)

Create the core method that collects dimension names and generates the set structure.

**Tasks**:
1. **Add _generate_dimension_set() Private Method**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py`
   - Action: Add new private method after `_generate_sql_on_clause()` (around line 137)
   - Pattern: Private method taking `SemanticModel` as parameter, returning optional dict
   - Reference: Other `_generate_*` methods like `_generate_sql_on_clause()` (lines 119-137)

### Phase 3: Integrate into View Generation (20-30 min)

Update the view generation pipeline to include the dimension set in output.

**Tasks**:
1. **Modify SemanticModel.to_lookml_dict()**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`
   - Action: Add sets collection to view_dict after measures (around line 361)
   - Pattern: Conditional inclusion based on whether dimensions exist
   - Reference: Existing measures handling (lines 345-361)

2. **Update _generate_view_lookml() to Support Sets**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py`
   - Action: Ensure sets are properly serialized by lkml.dump() (no code changes needed if SemanticModel handles it)
   - Pattern: Existing view_dict serialization flow
   - Reference: `_generate_view_lookml()` method (lines 344-377)

### Phase 4: Testing (45-60 min)

Comprehensive test coverage for all new functionality and edge cases.

**Tasks**:
1. **Unit Tests for LookMLSet Schema**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`
   - Action: Add test class `TestLookMLSet` after `TestLookMLMeasure`
   - Tests:
     - `test_lookml_set_creation()` - Basic set creation
     - `test_lookml_set_with_fields()` - Set with multiple fields
     - `test_lookml_set_to_dict()` - Serialization to dict format

2. **Unit Tests for Dimension Set Generation**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_lookml_generator.py`
   - Action: Add tests in `TestLookMLGenerator` class
   - Tests:
     - `test_generate_dimension_set()` - Verify all dimensions collected
     - `test_generate_dimension_set_includes_entities()` - Verify hidden entities included
     - `test_generate_dimension_set_includes_dimension_groups()` - Verify time dimensions included
     - `test_generate_dimension_set_empty_view()` - Verify graceful handling of no dimensions
     - `test_dimension_set_in_view_output()` - Verify set appears in generated LookML

3. **Integration Tests**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/integration/test_end_to_end.py`
   - Action: Add test method `test_dimension_sets_in_generated_views()`
   - Verify: Generated view files contain `set:` blocks with correct field lists

4. **Update Golden Files**
   - Action: Regenerate golden files to include dimension sets
   - Files: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/golden/expected_*.lkml`
   - Verify: Golden tests pass with new set structure

### Phase 5: Validation & Documentation (10-15 min)

Ensure code quality and update relevant documentation.

**Tasks**:
1. **Run Quality Checks**
   - Run: `make lint`, `make type-check`, `make test-coverage`
   - Fix any issues identified

2. **Update Type Hints**
   - Ensure all new methods have complete type hints
   - Run: `make type-check` to verify

## Detailed Task Breakdown

### Task 1: Add LookMLSet Schema

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Add new Pydantic model for LookML field sets

**Implementation Guidance**:
```python
class LookMLSet(BaseModel):
    """Represents a LookML field set."""

    name: str
    fields: list[str] = Field(default_factory=list)

    def to_lookml_dict(self) -> dict[str, Any]:
        """Convert LookML set to dictionary format for lkml library.

        Returns:
            Dictionary with 'name' and 'fields' keys.
        """
        return {
            'name': self.name,
            'fields': self.fields
        }
```

**Location**: Insert after `LookMLMeasure` class (around line 428)

**Reference**: Similar pattern to `LookMLDimension.to_lookml_dict()` but simpler structure

**Tests**: Must have type hints for mypy --strict compliance

---

### Task 2: Implement _generate_dimension_set() Method

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py`

**Action**: Add private method to collect dimension names and create set

**Implementation Guidance**:
```python
def _generate_dimension_set(self, semantic_model: SemanticModel) -> dict[str, Any] | None:
    """Generate a dimension-only field set for selective field exposure.

    Collects all dimension field names (entities, dimensions, dimension_groups)
    to create a set that can be referenced in explore joins to limit field exposure.

    Args:
        semantic_model: The semantic model to generate dimension set for.

    Returns:
        Dictionary with set structure, or None if no dimensions exist.
    """
    dimension_fields: list[str] = []

    # Collect entity names (all entities are dimensions, even if hidden)
    for entity in semantic_model.entities:
        dimension_fields.append(entity.name)

    # Collect regular dimension names
    for dimension in semantic_model.dimensions:
        dimension_fields.append(dimension.name)

    # Return None if no dimensions (empty views)
    if not dimension_fields:
        return None

    # Create set structure
    return {
        'name': 'dimensions_only',
        'fields': dimension_fields
    }
```

**Location**: Insert after `_generate_sql_on_clause()` method (around line 137)

**Reference**: Follow pattern of other `_generate_*` methods:
- Private method (starts with `_`)
- Takes `SemanticModel` as parameter
- Returns optional dict
- Has comprehensive docstring
- Includes type hints

**Important Considerations**:
- **Include all entities**: Even hidden entities must be in the set (needed for join keys)
- **Include dimension_groups**: Time dimensions are still dimensions for join purposes
- **Handle empty case**: Return None if no dimensions exist (view has only measures)
- **Field order**: Entities first, then dimensions (matches view structure)

---

### Task 3: Update SemanticModel.to_lookml_dict()

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Add sets to view_dict structure after measures

**Implementation Guidance**:
```python
# In SemanticModel.to_lookml_dict() method, after measures handling (around line 361):

# Generate dimension set if dimensions exist
sets = []
dimension_field_names = []

# Collect all dimension field names
for entity in self.entities:
    dimension_field_names.append(entity.name)
for dim in self.dimensions:
    dimension_field_names.append(dim.name)

# Create set if we have dimensions
if dimension_field_names:
    sets.append({
        'name': 'dimensions_only',
        'fields': dimension_field_names
    })

# Add to view_dict (after measures)
if sets:
    view_dict['sets'] = sets

return {'views': [view_dict]}
```

**Location**: Around line 361, after the measures block

**Reference**: Follow pattern of dimensions/measures conditional inclusion (lines 354-361)

**Tests**: Verify set appears after measures in output

---

### Task 4: Unit Tests - Schema Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`

**Action**: Add test class for LookMLSet

**Implementation Guidance**:
```python
class TestLookMLSet:
    """Test cases for LookMLSet model."""

    def test_lookml_set_creation(self) -> None:
        """Test basic LookML set creation."""
        field_set = LookMLSet(name="dimensions_only", fields=["user_id", "status"])
        assert field_set.name == "dimensions_only"
        assert len(field_set.fields) == 2
        assert "user_id" in field_set.fields
        assert "status" in field_set.fields

    def test_lookml_set_empty_fields(self) -> None:
        """Test LookML set with empty fields list."""
        field_set = LookMLSet(name="empty_set")
        assert field_set.name == "empty_set"
        assert field_set.fields == []

    def test_lookml_set_to_dict(self) -> None:
        """Test LookML set serialization to dict."""
        field_set = LookMLSet(
            name="dimensions_only",
            fields=["user_id", "created_date", "status"]
        )
        result = field_set.to_lookml_dict()

        assert result['name'] == "dimensions_only"
        assert len(result['fields']) == 3
        assert result['fields'] == ["user_id", "created_date", "status"]
```

**Location**: Add after `TestLookMLMeasure` class

**Reference**: Follow pattern from `TestEntity` and `TestDimension` (lines 26-100)

---

### Task 5: Unit Tests - Generator Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_lookml_generator.py`

**Action**: Add test methods to `TestLookMLGenerator` class

**Implementation Guidance**:
```python
def test_dimension_set_in_view_output(self) -> None:
    """Test that dimension sets appear in generated view LookML."""
    generator = LookMLGenerator()

    semantic_model = SemanticModel(
        name="users",
        model="dim_users",
        entities=[
            Entity(name="user_id", type="primary"),
            Entity(name="tenant_id", type="foreign")
        ],
        dimensions=[
            Dimension(name="status", type=DimensionType.CATEGORICAL),
            Dimension(name="created_at", type=DimensionType.TIME)
        ],
        measures=[
            Measure(name="user_count", agg=AggregationType.COUNT)
        ]
    )

    content = generator._generate_view_lookml(semantic_model)

    # Verify set block exists
    assert "set:" in content or "sets:" in content
    assert "dimensions_only" in content

    # Verify set includes all dimensions
    assert "user_id" in content  # entity
    assert "tenant_id" in content  # entity
    assert "status" in content  # dimension
    assert "created_at" in content  # dimension

def test_dimension_set_empty_view(self) -> None:
    """Test that views with no dimensions don't generate sets."""
    generator = LookMLGenerator()

    # Measures-only view (shouldn't happen in practice, but handle gracefully)
    semantic_model = SemanticModel(
        name="metrics_only",
        model="fct_metrics",
        measures=[
            Measure(name="total", agg=AggregationType.SUM)
        ]
    )

    content = generator._generate_view_lookml(semantic_model)

    # Verify no set block when no dimensions
    assert "set:" not in content and "sets:" not in content

def test_dimension_set_includes_hidden_entities(self) -> None:
    """Test that hidden entities are included in dimension sets."""
    generator = LookMLGenerator()

    semantic_model = SemanticModel(
        name="orders",
        model="fct_orders",
        entities=[
            Entity(name="order_id", type="primary", description="Hidden primary key")
        ],
        dimensions=[
            Dimension(name="status", type=DimensionType.CATEGORICAL)
        ]
    )

    content = generator._generate_view_lookml(semantic_model)

    # Verify hidden entity is in the set
    assert "dimensions_only" in content
    # Parse to verify structure
    import lkml
    parsed = lkml.load(content)
    views = parsed.get('views', [])
    assert len(views) == 1

    sets = views[0].get('sets', [])
    if sets:  # If implementation uses sets list
        dimension_set = next((s for s in sets if s['name'] == 'dimensions_only'), None)
        assert dimension_set is not None
        assert 'order_id' in dimension_set['fields']
        assert 'status' in dimension_set['fields']

def test_dimension_set_includes_dimension_groups(self) -> None:
    """Test that dimension_groups (time dimensions) are included in sets."""
    generator = LookMLGenerator()

    semantic_model = SemanticModel(
        name="events",
        model="fct_events",
        entities=[
            Entity(name="event_id", type="primary")
        ],
        dimensions=[
            Dimension(
                name="event_timestamp",
                type=DimensionType.TIME,
                type_params={'time_granularity': 'day'}
            ),
            Dimension(name="event_type", type=DimensionType.CATEGORICAL)
        ]
    )

    content = generator._generate_view_lookml(semantic_model)

    # Verify dimension_group is in the set
    assert "dimensions_only" in content
    assert "event_timestamp" in content  # Should be in set even as dimension_group
    assert "event_type" in content
```

**Location**: Add to `TestLookMLGenerator` class (after existing tests)

**Reference**: Follow pattern from existing tests like `test_generate_view_lookml()` (lines 51-104)

**Estimated lines**: ~100-120 lines total

---

### Task 6: Integration Test

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/integration/test_end_to_end.py`

**Action**: Add integration test for dimension sets in generated files

**Implementation Guidance**:
```python
def test_dimension_sets_in_generated_views(self) -> None:
    """Test that all generated view files include dimension sets."""
    fixture_path = Path(__file__).parent.parent / "fixtures"

    parser = DbtParser()
    semantic_models = parser.parse_directory(fixture_path)

    generator = LookMLGenerator()

    with TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        generated_files, validation_errors = generator.generate_lookml_files(
            semantic_models, output_dir
        )

        assert len(validation_errors) == 0

        # Check each view file for dimension sets
        view_files = [f for f in generated_files if f.name.endswith('.view.lkml')]

        for view_file in view_files:
            content = view_file.read_text()

            # Parse LookML to check structure
            parsed = lkml.load(content)
            views = parsed.get('views', [])

            for view in views:
                # If view has dimensions, should have set
                has_dimensions = (
                    len(view.get('dimensions', [])) > 0 or
                    len(view.get('dimension_groups', [])) > 0
                )

                if has_dimensions:
                    sets = view.get('sets', [])
                    assert len(sets) > 0, f"View {view['name']} has dimensions but no sets"

                    # Find dimensions_only set
                    dim_set = next((s for s in sets if s['name'] == 'dimensions_only'), None)
                    assert dim_set is not None, f"View {view['name']} missing dimensions_only set"

                    # Verify fields list is not empty
                    assert len(dim_set.get('fields', [])) > 0
```

**Location**: Add to `TestEndToEndIntegration` class

**Reference**: Similar pattern to `test_generate_with_prefixes()` (lines 76-105)

## File Changes

### Files to Modify

#### `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`
**Why**: Add LookMLSet schema and update SemanticModel.to_lookml_dict()

**Changes**:
- Add `LookMLSet` class after `LookMLMeasure` (line ~428)
- Update `SemanticModel.to_lookml_dict()` to generate and include sets (line ~361)

**Estimated lines**: +40 lines

#### `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/generators/lookml.py`
**Why**: Add dimension set generation method (optional - only if not handled in schemas.py)

**Changes**:
- Potentially add `_generate_dimension_set()` method if needed for generator-level logic
- Update imports if LookMLSet is used

**Estimated lines**: +25 lines (if method added)

#### `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`
**Why**: Test LookMLSet schema

**Changes**:
- Add `TestLookMLSet` class with 3 test methods

**Estimated lines**: +40 lines

#### `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_lookml_generator.py`
**Why**: Test dimension set generation in views

**Changes**:
- Add 4 test methods to `TestLookMLGenerator` class

**Estimated lines**: +120 lines

#### `/Users/dug/Work/repos/dbt-to-lookml/src/tests/integration/test_end_to_end.py`
**Why**: Integration test for dimension sets

**Changes**:
- Add `test_dimension_sets_in_generated_views()` method

**Estimated lines**: +45 lines

### Files to Create

None - all changes are modifications to existing files.

### Files Potentially Affected (Golden Files)

#### `/Users/dug/Work/repos/dbt-to-lookml/src/tests/golden/expected_*.lkml`
**Why**: Golden files will need updating to include dimension sets

**Action**: Regenerate golden files after implementation using actual generated output

## Testing Strategy

### Unit Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`

**Test Cases**:
1. **test_lookml_set_creation**
   - Setup: Create LookMLSet with name and fields
   - Action: Instantiate class
   - Assert: Name and fields are correctly set

2. **test_lookml_set_empty_fields**
   - Setup: Create LookMLSet without fields
   - Action: Instantiate with default fields
   - Assert: Fields list is empty array

3. **test_lookml_set_to_dict**
   - Setup: Create LookMLSet with multiple fields
   - Action: Call to_lookml_dict()
   - Assert: Dict has correct structure and field order

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_lookml_generator.py`

**Test Cases**:
4. **test_dimension_set_in_view_output**
   - Setup: SemanticModel with entities, dimensions, measures
   - Action: Generate view LookML
   - Assert: Output contains set block with all dimension names

5. **test_dimension_set_empty_view**
   - Setup: SemanticModel with only measures (no dimensions)
   - Action: Generate view LookML
   - Assert: No set block in output

6. **test_dimension_set_includes_hidden_entities**
   - Setup: SemanticModel with hidden primary entity
   - Action: Generate view LookML
   - Assert: Set includes entity even though it's hidden

7. **test_dimension_set_includes_dimension_groups**
   - Setup: SemanticModel with time dimension (dimension_group)
   - Action: Generate view LookML
   - Assert: Set includes dimension_group name

### Integration Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/integration/test_end_to_end.py`

**Test Cases**:
8. **test_dimension_sets_in_generated_views**
   - Setup: Parse fixture semantic models, generate LookML files
   - Action: Read each generated view file
   - Assert: Views with dimensions have dimensions_only set with correct fields

### Edge Cases

1. **Empty view (no dimensions, no measures)**: Should not generate set (graceful handling)
2. **Measures-only view**: Should not generate set
3. **Single dimension**: Should generate set with one field
4. **Mixed dimension types**: Should include regular dims, entities, and dimension_groups
5. **Hidden entities**: Must be included in set (needed for joins)
6. **Dimension groups (time dims)**: Must be included in set

## Validation Commands

### Run Full Test Suite
```bash
cd /Users/dug/Work/repos/dbt-to-lookml
make test-full
```

### Run Unit Tests Only (Fast Feedback)
```bash
make test-fast
# OR
python -m pytest src/tests/unit/test_schemas.py::TestLookMLSet -xvs
python -m pytest src/tests/unit/test_lookml_generator.py::TestLookMLGenerator::test_dimension_set_in_view_output -xvs
```

### Run Specific Test File
```bash
python -m pytest src/tests/unit/test_lookml_generator.py -v
```

### Code Quality Checks
```bash
make lint              # Run ruff linting
make format            # Auto-format with ruff
make type-check        # Run mypy type checking
make quality-gate      # Run all checks (lint + types + tests)
```

### Coverage Report
```bash
make test-coverage     # Generate HTML coverage report (95% target)
open htmlcov/index.html
```

### Manual Validation (Optional)
```bash
# Generate LookML and inspect output
uv run python -m dbt_to_lookml generate \
  -i semantic_models/ \
  -o build/lookml \
  --schema analytics \
  -v

# Check a generated view for set structure
cat build/lookml/users.view.lkml
```

## Dependencies

### Existing Dependencies
- `lkml` - Used for LookML serialization (already installed)
- `pydantic` - Used for schema validation (already installed)

### New Dependencies Needed
None - all required packages are already in use.

## Implementation Notes

### Important Considerations

1. **View Structure Ordering**: Sets must appear after measures in the view structure to maintain clean organization:
   - entities (as hidden dimensions)
   - dimensions (regular)
   - dimension_groups (time)
   - measures
   - **sets** ← new

2. **Hidden Entities**: All entities must be included in the dimension set, even though they're hidden. This is critical for join relationships where hidden entities serve as join keys.

3. **Dimension Groups**: Time dimensions that become `dimension_group:` in LookML must still be included in the set using their base name (e.g., `created_at` not `created_at_date`).

4. **Empty Views**: Views with no dimensions should gracefully skip set generation (return None or omit 'sets' key from view_dict).

5. **Type Safety**: All new code must have complete type hints for mypy --strict compliance.

6. **Set Name**: Hardcoded to `dimensions_only` per epic requirements (not configurable in this iteration).

### Code Patterns to Follow

1. **Pydantic Models**: All schema classes inherit from `BaseModel`, use Field() for defaults, include `to_lookml_dict()` method
   - Reference: `LookMLDimension` (lines 388-400), `LookMLMeasure` (lines 416-427)

2. **Private Generator Methods**: Start with `_`, take models/configs as params, return optional dicts
   - Reference: `_generate_sql_on_clause()` (lines 119-137)

3. **LookML Serialization**: Use `lkml.dump()` for all LookML output, ensure dicts have correct structure
   - Reference: `_generate_view_lookml()` (lines 344-377)

4. **Test Patterns**: Use pytest classes, descriptive test names, arrange-act-assert pattern
   - Reference: `TestEntity` (lines 26-116 in test_schemas.py)

5. **Type Hints**: Use modern Python type syntax (`list[str]`, `dict[str, Any]`, `Optional[T]`)
   - Reference: All method signatures in schemas.py

### References

- **LookML Set Syntax**: `set: name { fields: [field1, field2, ...] }`
- **Similar Implementation**: Join generation in `_build_join_graph()` (lines 139-251) for collecting and structuring data
- **Schema Patterns**: `LookMLView.to_lookml_dict()` (lines 439-478) for dict conversion
- **Test Patterns**: `test_generate_view_lookml()` (lines 51-104) for generator testing

## Ready for Implementation

This spec is complete and ready for implementation. All code changes, test requirements, and validation steps are clearly defined.

**Next Steps**:
1. Review this spec for completeness
2. Begin implementation with Phase 1 (Add LookMLSet Schema)
3. Follow TDD approach: write tests first, then implementation
4. Run `make quality-gate` before committing
5. Update issue status to "in-progress" when starting
6. Update issue status to "review" when complete

**Estimated Implementation Time**: 2-3 hours
- Schema additions: 20 mins
- Generator method/integration: 40 mins
- Unit tests: 60 mins
- Integration tests: 30 mins
- Validation and cleanup: 15 mins
