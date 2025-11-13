# Implementation Spec: Add LookML set support to schemas

## Metadata
- **Issue**: DTL-002
- **Stack**: backend
- **Generated**: 2025-11-12T23:00:00Z
- **Strategy**: Approved 2025-11-12T22:30:00Z
- **Type**: feature

## Issue Context

### Problem Statement
Extend the Pydantic schema models to support LookML field sets, which are used to group fields for reuse in explores and joins. Sets are the foundation for field exposure control in explores, enabling the generator to create and reference dimension-only sets in join definitions.

### Solution Approach
Add LookML `set:` support to the schema layer by creating a new `LookMLSet` Pydantic model and integrating it into `LookMLView`. This is a pure schema extension with no parser or generator changes required at this stage. The implementation follows existing schema patterns and maintains backward compatibility.

### Success Criteria
- [ ] `LookMLSet` Pydantic model created with required fields
- [ ] `LookMLView` extended with optional `sets` field
- [ ] `LookMLView.to_lookml_dict()` serializes sets correctly
- [ ] Sets appear in correct order (after `sql_table_name`, before `dimensions`)
- [ ] All tests passing with 95%+ branch coverage
- [ ] Type checking passes (mypy --strict)
- [ ] Backward compatibility maintained (views without sets still work)

## Approved Strategy Summary

**Architecture Impact**: Pure schema extension in `src/dbt_to_lookml/schemas.py`

**Key Design Decisions**:
1. Add `LookMLSet(BaseModel)` class after `LookMLMeasure` (around line 427)
2. Add `sets: List[LookMLSet]` field to `LookMLView` with default empty list
3. Update `LookMLView.to_lookml_dict()` to include sets in output
4. Maintain dict ordering: `name` → `sql_table_name` → `sets` → `dimensions` → `dimension_groups` → `measures`
5. Use existing patterns: `convert_bools()` helper, Optional fields, mypy --strict compliance

**Dependencies**: None (foundational work, uses existing Pydantic)

**Testing**: Unit tests only at this stage (no integration tests needed)

## Implementation Plan

### Phase 1: Add LookMLSet Model (15 min)

Create new Pydantic model following existing patterns in `schemas.py`.

**Tasks**:
1. **Add LookMLSet class after LookMLMeasure**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`
   - Location: After line 427 (after `LookMLMeasure` class)
   - Pattern: Follow `LookMLDimension`, `LookMLMeasure` structure
   - Reference: `schemas.py:388-427` (existing LookML models)

### Phase 2: Integrate sets into LookMLView (10 min)

Add optional sets field to `LookMLView` with backward compatibility.

**Tasks**:
1. **Add sets field to LookMLView**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`
   - Location: Line 437 (after `measures` field)
   - Pattern: Use `Field(default_factory=list)` for backward compatibility
   - Reference: `schemas.py:435-437` (existing list fields)

### Phase 3: Update to_lookml_dict() (20 min)

Extend serialization logic to include sets with proper ordering.

**Tasks**:
1. **Add sets serialization in to_lookml_dict()**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`
   - Location: Lines 439-478 (`LookMLView.to_lookml_dict()` method)
   - Pattern: Use `convert_bools()` helper like dimensions/measures
   - Reference: `schemas.py:463-476` (existing field serialization)

### Phase 4: Write Unit Tests (45 min)

Comprehensive test coverage for new functionality.

**Tasks**:
1. **Test LookMLSet model validation**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`
   - Location: Add new test class after `TestLookMLModels` (after line 623)
   - Tests: Creation, validation, required fields, optional fields

2. **Test LookMLView with sets**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`
   - Location: Add tests to `TestLookMLModels` class
   - Tests: View with sets, empty sets, multiple sets

3. **Test to_lookml_dict() serialization**
   - File: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`
   - Location: Add tests to `TestLookMLModels` class
   - Tests: Sets in output, correct ordering, backward compatibility

### Phase 5: Verify Quality Gates (10 min)

Run all quality checks to ensure compliance.

**Tasks**:
1. **Run type checking** - `make type-check`
2. **Run tests** - `make test-fast`
3. **Run coverage** - `make test-coverage` (verify 95%+)
4. **Run full quality gate** - `make quality-gate`

## Detailed Task Breakdown

### Task 1: Add LookMLSet Model

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Add new class after `LookMLMeasure` (line 427)

**Implementation Guidance**:
```python
class LookMLSet(BaseModel):
    """Represents a LookML set for grouping fields."""

    name: str
    fields: list[str]
```

**Pattern Notes**:
- Follow same structure as `LookMLDimension`, `LookMLMeasure`
- Use `list[str]` (not `List[str]`) for Python 3.9+ compatibility
- No Optional fields needed - both name and fields are required
- No `to_lookml_dict()` method needed - serialization handled by parent
- Google-style docstring required

**Reference**: Similar implementation at `schemas.py:388-427`

**Tests**:
- Test required field validation (name, fields)
- Test creation with valid data
- Test fields can be empty list

### Task 2: Add sets Field to LookMLView

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Add field after `measures` (line 437)

**Implementation Guidance**:
```python
class LookMLView(BaseModel):
    """Represents a LookML view."""

    name: str
    sql_table_name: str
    description: Optional[str] = None
    dimensions: list[LookMLDimension] = Field(default_factory=list)
    dimension_groups: list[LookMLDimensionGroup] = Field(default_factory=list)
    measures: list[LookMLMeasure] = Field(default_factory=list)
    sets: list[LookMLSet] = Field(default_factory=list)  # NEW
```

**Pattern Notes**:
- Use `Field(default_factory=list)` for backward compatibility
- Maintains existing pattern from dimensions/measures fields
- No Optional wrapper needed - empty list is default

**Reference**: Existing list fields at `schemas.py:435-437`

**Tests**:
- Test view creation without sets (backward compatibility)
- Test view creation with sets
- Test sets default to empty list

### Task 3: Update LookMLView.to_lookml_dict()

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Add sets serialization in `to_lookml_dict()` method (lines 439-478)

**Implementation Guidance**:
```python
def to_lookml_dict(self) -> dict[str, Any]:
    """Convert LookML view to dictionary format."""
    def convert_bools(d: dict) -> dict:
        # ... existing implementation ...
        pass

    view_dict: dict[str, Any] = {
        'name': self.name,
        'sql_table_name': self.sql_table_name,
    }

    if self.description:
        view_dict['description'] = self.description

    # NEW: Add sets serialization AFTER description, BEFORE dimensions
    if self.sets:
        view_dict['sets'] = [
            convert_bools(set_item.model_dump(exclude_none=True))
            for set_item in self.sets
        ]

    if self.dimensions:
        view_dict['dimensions'] = [
            convert_bools(dim.model_dump(exclude_none=True)) for dim in self.dimensions
        ]

    # ... rest of existing implementation ...
```

**Critical Requirements**:
1. **Ordering**: Sets must appear AFTER `sql_table_name` and BEFORE `dimensions`
2. **Conditional**: Only add `sets` key if list is non-empty (like dimensions/measures)
3. **Serialization**: Use `convert_bools()` helper and `model_dump(exclude_none=True)`
4. **Dict Structure**: Match existing pattern for dimensions/measures

**Expected Output Structure**:
```python
{
    'views': [
        {
            'name': 'view_name',
            'sql_table_name': 'schema.table',
            'sets': [
                {'name': 'dimension_set', 'fields': ['dim1', 'dim2']},
                {'name': 'another_set', 'fields': ['dim3']}
            ],
            'dimensions': [...],
            'dimension_groups': [...],
            'measures': [...]
        }
    ]
}
```

**Reference**: Existing serialization at `schemas.py:463-476`

**Tests**:
- Test sets appear in output when present
- Test sets omitted when empty
- Test correct ordering in dict
- Test multiple sets serialize correctly
- Test convert_bools applied to set dicts

### Task 4: Write Unit Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`

**Test Class 1: TestLookMLSet** (new class after line 623)

**Test Methods**:

1. **test_lookml_set_creation**
   - Setup: Create LookMLSet with name and fields
   - Action: Verify all attributes
   - Assert: name matches, fields list correct

2. **test_lookml_set_with_multiple_fields**
   - Setup: Create set with 5+ dimension names
   - Action: Verify fields list
   - Assert: All fields present in order

3. **test_lookml_set_with_empty_fields**
   - Setup: Create set with empty fields list
   - Action: Verify set creation succeeds
   - Assert: fields is empty list

4. **test_lookml_set_validation_missing_name**
   - Setup: Attempt to create set without name
   - Action: pytest.raises(ValidationError)
   - Assert: ValidationError raised

5. **test_lookml_set_validation_missing_fields**
   - Setup: Attempt to create set without fields
   - Action: pytest.raises(ValidationError)
   - Assert: ValidationError raised

**Test Methods for TestLookMLModels** (add to existing class)

6. **test_lookml_view_with_sets**
   - Setup: Create view with dimensions and sets
   - Action: Verify sets field populated
   - Assert: len(view.sets) correct, set names match

7. **test_lookml_view_without_sets_backward_compatibility**
   - Setup: Create view without sets parameter
   - Action: Verify sets defaults to empty list
   - Assert: len(view.sets) == 0, view creates successfully

8. **test_lookml_view_to_lookml_dict_with_sets**
   - Setup: Create view with sets
   - Action: Call to_lookml_dict()
   - Assert: 'sets' key in view dict, sets contain correct data

9. **test_lookml_view_to_lookml_dict_without_sets**
   - Setup: Create view without sets
   - Action: Call to_lookml_dict()
   - Assert: 'sets' key NOT in view dict (empty list omitted)

10. **test_lookml_view_to_lookml_dict_sets_ordering**
    - Setup: Create view with sets, dimensions, measures
    - Action: Call to_lookml_dict(), get dict keys
    - Assert: keys order is ['name', 'sql_table_name', 'sets', 'dimensions', 'measures']

11. **test_lookml_view_to_lookml_dict_multiple_sets**
    - Setup: Create view with 3 sets
    - Action: Call to_lookml_dict()
    - Assert: All 3 sets in output, correct structure

**Pattern Notes**:
- Follow existing test structure in `test_schemas.py`
- Use descriptive docstrings
- Test one concept per test method
- Use pytest.raises for validation errors
- Follow naming: `test_{class}_{method}_{scenario}`

**Reference**: Existing tests at `test_schemas.py:506-623`

## File Changes

### Files to Modify

#### `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`
**Why**: Add LookMLSet model and integrate into LookMLView

**Changes**:
1. Add `LookMLSet` class (4 lines) after line 427
2. Add `sets` field to `LookMLView` (1 line) after line 437
3. Update `to_lookml_dict()` method (5 lines) in lines 439-478
   - Add sets serialization after description, before dimensions
   - Use existing `convert_bools()` helper pattern

**Estimated lines**: ~10 new lines total

**Code Sections**:
```
Line 427: After LookMLMeasure → Add LookMLSet class
Line 437: After measures field → Add sets field
Line 455: In to_lookml_dict() → Add sets serialization logic
```

#### `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`
**Why**: Add comprehensive test coverage for new functionality

**Changes**:
1. Add `TestLookMLSet` test class with 5 test methods (after line 623)
2. Add 6 test methods to existing `TestLookMLModels` class
   - Tests for sets field, serialization, ordering, backward compatibility

**Estimated lines**: ~150 new test lines

**Test Coverage**:
- LookMLSet model validation: 5 tests
- LookMLView integration: 6 tests
- Total: 11 new test methods

### Files to Create

None - all changes are modifications to existing files.

## Testing Strategy

### Unit Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`

**Test Organization**:
- New class: `TestLookMLSet` (5 methods)
- Extended class: `TestLookMLModels` (6 additional methods)

**Coverage Areas**:
1. **Model Validation** (5 tests)
   - Required field enforcement (name, fields)
   - Valid creation scenarios
   - Edge cases (empty fields list)

2. **Integration with LookMLView** (3 tests)
   - View creation with sets
   - Backward compatibility (no sets)
   - Multiple sets handling

3. **Serialization** (3 tests)
   - to_lookml_dict() with sets
   - to_lookml_dict() without sets (omitted)
   - Correct ordering in output dict

### Edge Cases

1. **Empty sets list**: View with `sets=[]` should omit 'sets' key from output
2. **Set with empty fields**: `LookMLSet(name="test", fields=[])` should validate successfully
3. **Multiple sets**: View should handle list of multiple sets correctly
4. **Ordering**: Sets must appear after sql_table_name, before dimensions

### Integration Tests

**Not required at this stage** - No parser or generator changes. Integration testing will be added in subsequent issues when generator uses sets.

### Manual Testing

```bash
# Create test view
python -c "
from dbt_to_lookml.schemas import LookMLView, LookMLSet, LookMLDimension

view = LookMLView(
    name='test_view',
    sql_table_name='schema.table',
    sets=[
        LookMLSet(name='dimension_set', fields=['dim1', 'dim2']),
        LookMLSet(name='another_set', fields=['dim3'])
    ],
    dimensions=[
        LookMLDimension(name='dim1', type='string', sql='\${TABLE}.dim1')
    ]
)

import json
print(json.dumps(view.to_lookml_dict(), indent=2))
"
```

**Expected Output**:
```json
{
  "views": [
    {
      "name": "test_view",
      "sql_table_name": "schema.table",
      "sets": [
        {"name": "dimension_set", "fields": ["dim1", "dim2"]},
        {"name": "another_set", "fields": ["dim3"]}
      ],
      "dimensions": [
        {"name": "dim1", "type": "string", "sql": "${TABLE}.dim1"}
      ]
    }
  ]
}
```

## Validation Commands

Run these commands to verify implementation:

```bash
# Format code (auto-fix)
make format

# Run linter
make lint

# Run type checker (mypy --strict)
make type-check

# Run unit tests only (fast)
make test-fast

# Run tests with coverage report
make test-coverage

# Verify 95%+ coverage
# Open htmlcov/index.html and verify src/dbt_to_lookml/schemas.py coverage

# Run full quality gate (lint + types + tests)
make quality-gate
```

**Expected Results**:
- ✅ Linting passes (no errors)
- ✅ Type checking passes (mypy --strict compliant)
- ✅ All tests pass
- ✅ Branch coverage ≥ 95% for schemas.py

## Dependencies

### Existing Dependencies
- **pydantic**: Core Pydantic models (BaseModel, Field)
  - Already in use throughout schemas.py
  - No version changes needed

### New Dependencies Needed
None - implementation uses only existing dependencies.

### Import Changes
No new imports needed. Uses existing:
```python
from pydantic import BaseModel, Field
from typing import Any, Optional
```

## Implementation Notes

### Important Considerations

1. **Python 3.9+ Type Hints**
   - Use `list[str]` not `List[str]` (lowercase list)
   - Use `dict[str, Any]` not `Dict[str, Any]`
   - Follow existing pattern in schemas.py (line 6-10)

2. **Pydantic Patterns**
   - Use `Field(default_factory=list)` for mutable defaults
   - Never use `sets: list[LookMLSet] = []` (mutable default antipattern)
   - Use `model_dump(exclude_none=True)` for serialization

3. **Backward Compatibility**
   - Empty sets list must NOT add 'sets' key to output dict
   - Existing code creating LookMLView without sets must continue working
   - Use `if self.sets:` check before adding to dict

4. **Dict Ordering**
   - Python 3.7+ guarantees dict insertion order
   - Critical to add sets in correct position (after sql_table_name)
   - Test ordering explicitly

5. **Type Safety**
   - All functions must have type hints (mypy --strict)
   - Use `-> None` for test methods
   - Use `-> dict[str, Any]` for to_lookml_dict

### Code Patterns to Follow

**Pattern 1: Pydantic Model Structure**
```python
# Reference: schemas.py:388-427
class LookMLSet(BaseModel):
    """Docstring describing the model."""

    name: str
    fields: list[str]
```

**Pattern 2: List Field with Default**
```python
# Reference: schemas.py:435-437
sets: list[LookMLSet] = Field(default_factory=list)
```

**Pattern 3: Conditional Dict Addition**
```python
# Reference: schemas.py:463-476
if self.sets:
    view_dict['sets'] = [...]
```

**Pattern 4: Model Serialization**
```python
# Reference: schemas.py:464-466
view_dict['sets'] = [
    convert_bools(set_item.model_dump(exclude_none=True))
    for set_item in self.sets
]
```

**Pattern 5: Test Structure**
```python
# Reference: test_schemas.py:509-524
def test_lookml_set_creation(self) -> None:
    """Test description."""
    set_obj = LookMLSet(name="test", fields=["a", "b"])
    assert set_obj.name == "test"
    assert set_obj.fields == ["a", "b"]
```

### References

**Schema Models**:
- `schemas.py:388-427` - LookML model definitions
- `schemas.py:429-478` - LookMLView and to_lookml_dict()

**Test Patterns**:
- `test_schemas.py:26-185` - Entity tests (validation patterns)
- `test_schemas.py:506-623` - LookML model tests

**Type Definitions**:
- `types.py:1-50` - Enum and type mapping patterns

## Ready for Implementation

This spec is complete and ready for implementation. All code changes are scoped, patterns are documented, and tests are specified.

**Implementation Time**: 1.5-2 hours

**Complexity**: Low (pure schema extension, no business logic)

**Risk**: Minimal (no existing functionality affected, backward compatible)

---

**Next Steps**:
1. Review this spec
2. Update issue status to "ready" in `.tasks/issues/DTL-002.md`
3. Add `state:has-spec` label
4. Proceed with implementation following this spec
