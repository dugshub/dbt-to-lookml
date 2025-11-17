---
id: DTL-009
title: "Update LookMLGenerator to accept and propagate convert_tz settings"
type: strategy
status: ready
created: 2025-11-12
updated: 2025-11-12
---

# DTL-009 Implementation Strategy

## Overview

This strategy addresses the update of `LookMLGenerator` to accept and propagate timezone conversion (`convert_tz`) settings through the dimension generation pipeline. This is part of the broader timezone conversion feature (DTL-007) and depends on DTL-008 (Dimension schema updates).

## Current State Analysis

### LookMLGenerator Class (src/dbt_to_lookml/generators/lookml.py)

**Current signature:**
```python
class LookMLGenerator(Generator):
    def __init__(
        self,
        view_prefix: str = "",
        explore_prefix: str = "",
        validate_syntax: bool = True,
        format_output: bool = True,
        schema: str = "",
        connection: str = "redshift_test",
        model_name: str = "semantic_model",
    ) -> None:
```

**Current flow:**
1. `generate()` calls `_generate_view_lookml()` for each semantic model
2. `_generate_view_lookml()` converts prefixed `SemanticModel` to LookML via `semantic_model.to_lookml_dict(schema=self.schema)`
3. `SemanticModel.to_lookml_dict()` converts dimensions via `dim.to_lookml_dict()` (line 350)
4. `Dimension.to_lookml_dict()` delegates to `_to_dimension_group_dict()` for time dimensions

### SemanticModel.to_lookml_dict() (src/dbt_to_lookml/schemas.py:309-399)

**Current signature:**
```python
def to_lookml_dict(self, schema: str = "") -> dict[str, Any]:
```

**Current behavior:**
- Accepts only `schema` parameter
- Converts all dimensions via `dim.to_lookml_dict()` without additional context
- No mechanism to pass generator-level defaults to dimensions

### Design Dependencies

- **DTL-008** (prerequisite): Dimension._to_dimension_group_dict() must be updated to accept `default_convert_tz` parameter
- **DTL-010** (downstream): CLI will pass convert_tz to LookMLGenerator
- **DTL-011** (testing): Unit tests will validate propagation chain

## Implementation Plan

### Phase 1: LookMLGenerator Updates (files: lookml.py)

#### 1.1 Add convert_tz Parameter to __init__()

```python
def __init__(
    self,
    view_prefix: str = "",
    explore_prefix: str = "",
    validate_syntax: bool = True,
    format_output: bool = True,
    schema: str = "",
    connection: str = "redshift_test",
    model_name: str = "semantic_model",
    convert_tz: bool | None = None,  # NEW
) -> None:
```

**Details:**
- Accept `convert_tz: bool | None` with default None
- Store as instance variable: `self.convert_tz = convert_tz`
- Update docstring to document the new parameter
- No changes to parent Generator class needed (backward compatible)

#### 1.2 Update _generate_view_lookml() Method

**Current code (line 354-393):**
```python
def _generate_view_lookml(self, semantic_model: SemanticModel) -> str:
    # ... existing code ...
    if self.view_prefix:
        # ... create prefixed_model ...
        view_dict = prefixed_model.to_lookml_dict(schema=self.schema)
    else:
        view_dict = semantic_model.to_lookml_dict(schema=self.schema)
```

**Updated code:**
```python
def _generate_view_lookml(self, semantic_model: SemanticModel) -> str:
    # ... existing code ...
    if self.view_prefix:
        # ... create prefixed_model ...
        view_dict = prefixed_model.to_lookml_dict(
            schema=self.schema,
            convert_tz=self.convert_tz  # NEW
        )
    else:
        view_dict = semantic_model.to_lookml_dict(
            schema=self.schema,
            convert_tz=self.convert_tz  # NEW
        )
```

**Changes:**
- Pass `convert_tz=self.convert_tz` to both `to_lookml_dict()` calls
- Maintains backward compatibility (None is valid value)

### Phase 2: SemanticModel Updates (files: schemas.py)

#### 2.1 Update to_lookml_dict() Signature

**Current signature (line 309):**
```python
def to_lookml_dict(self, schema: str = "") -> dict[str, Any]:
```

**Updated signature:**
```python
def to_lookml_dict(self, schema: str = "", convert_tz: bool | None = None) -> dict[str, Any]:
```

**Details:**
- Add `convert_tz: bool | None = None` parameter
- Update docstring to document propagation behavior
- Default None maintains backward compatibility

#### 2.2 Update Dimension Conversion Loop

**Current code (line 348-354):**
```python
# Convert dimensions (separate regular dims from time dims)
for dim in self.dimensions:
    dim_dict = dim.to_lookml_dict()
    if dim.type == DimensionType.TIME:
        dimension_groups.append(dim_dict)
    else:
        dimensions.append(dim_dict)
```

**Updated code:**
```python
# Convert dimensions (separate regular dims from time dims)
for dim in self.dimensions:
    # For time dimensions, pass convert_tz to propagate generator default
    if dim.type == DimensionType.TIME:
        dim_dict = dim.to_lookml_dict(default_convert_tz=convert_tz)
    else:
        dim_dict = dim.to_lookml_dict()

    if dim.type == DimensionType.TIME:
        dimension_groups.append(dim_dict)
    else:
        dimensions.append(dim_dict)
```

**Details:**
- Only pass `convert_tz` to time dimensions (dimension_groups)
- Non-time dimensions don't support convert_tz in LookML
- Conditional passing maintains clean separation of concerns

### Phase 3: Type Hints and Imports

**No new imports needed** (typing is already imported)

**Type consistency check:**
- All type hints use `bool | None` (PEP 604 syntax, consistent with codebase)
- Return types remain unchanged (`dict[str, str]`, `dict[str, Any]`)

## Testing Strategy

### Unit Tests to Add (test_lookml_generator.py)

#### Test 1: Generator accepts convert_tz parameter
```python
def test_generator_initialization_with_convert_tz(self) -> None:
    """Test that LookMLGenerator accepts convert_tz parameter."""
    # Test None (default)
    gen_none = LookMLGenerator(convert_tz=None)
    assert gen_none.convert_tz is None

    # Test True
    gen_true = LookMLGenerator(convert_tz=True)
    assert gen_true.convert_tz is True

    # Test False
    gen_false = LookMLGenerator(convert_tz=False)
    assert gen_false.convert_tz is False
```

#### Test 2: convert_tz is propagated to dimension generation
```python
def test_convert_tz_propagation_to_dimensions(self) -> None:
    """Test that convert_tz is passed to SemanticModel.to_lookml_dict()."""
    # Create a semantic model with a time dimension
    model = SemanticModel(
        name="events",
        model="events",
        dimensions=[
            Dimension(
                name="created_at",
                type=DimensionType.TIME,
                type_params={"time_granularity": "day"}
            )
        ]
    )

    # Generate with convert_tz=True
    generator = LookMLGenerator(convert_tz=True)
    content = generator._generate_view_lookml(model)

    # Verify content includes convert_tz setting
    # (exact verification depends on DTL-008 implementation)
    assert "convert_tz:" in content
```

#### Test 3: Backward compatibility (None default)
```python
def test_generator_backward_compatibility(self) -> None:
    """Test that existing code without convert_tz still works."""
    # Old-style initialization should work
    generator = LookMLGenerator(
        view_prefix="v_",
        schema="public"
    )
    assert generator.convert_tz is None

    # Should generate without errors
    model = SemanticModel(name="test", model="test")
    content = generator._generate_view_lookml(model)
    assert isinstance(content, str)
```

### Integration Tests (existing)

- Existing integration tests should continue to pass
- No changes to test expectations needed until DTL-008 is complete
- Golden tests updated in DTL-012

## Acceptance Criteria

- [x] LookMLGenerator.__init__() accepts `convert_tz: bool | None` parameter
- [x] convert_tz is stored as instance variable
- [x] _generate_view_lookml() passes convert_tz to to_lookml_dict()
- [x] SemanticModel.to_lookml_dict() accepts convert_tz parameter
- [x] SemanticModel passes convert_tz to time dimensions via to_lookml_dict()
- [x] Type hints correct (bool | None everywhere)
- [x] Backward compatibility maintained (None default)
- [x] No breaking changes to existing API
- [x] mypy strict typing compliance
- [x] Docstrings updated

## Precedence Chain (for reference)

After this change, the full precedence chain will be:
1. **Per-dimension metadata** (DTL-008): `config.meta.convert_tz` in dimension YAML
2. **Generator parameter** (DTL-009): `LookMLGenerator(convert_tz=...)`
3. **CLI flag** (DTL-010): `--convert-tz` / `--no-convert-tz`
4. **Default**: `convert_tz: no` (explicit in generated LookML)

This implementation provides level 2 of the chain.

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Breaking change to SemanticModel API | Low | High | Use default parameter None; existing calls still work |
| Mypy type errors | Low | Medium | Use consistent `bool \| None` type throughout |
| Missing dependency on DTL-008 | Medium | High | Clearly document that DTL-008 must be complete first; use if checks in to_lookml_dict() |
| Test coverage gaps | Medium | Medium | Add unit tests for all parameter combinations |

## Implementation Order

1. **Update LookMLGenerator.__init__()** - Add parameter and instance variable
2. **Update LookMLGenerator._generate_view_lookml()** - Pass convert_tz to to_lookml_dict()
3. **Update SemanticModel.to_lookml_dict()** - Accept and pass convert_tz parameter
4. **Add unit tests** - Test initialization, propagation, backward compatibility
5. **Run full test suite** - Ensure no regressions
6. **Type check with mypy** - Verify strict typing compliance

## Code Review Checklist

- [ ] All parameter names match DTL-008 expectations
- [ ] Type hints are consistent with codebase style
- [ ] Docstrings updated with examples
- [ ] No breaking changes to public API
- [ ] Tests cover all parameter combinations (None, True, False)
- [ ] mypy --strict passes without errors
- [ ] Backward compatibility verified with existing tests

## Deployment Notes

- This change is safe to deploy independently (backward compatible)
- DTL-009 can be merged before DTL-010 and DTL-011
- DTL-012 (test updates) should follow after this implementation
- No database or configuration changes needed
- No CLI changes (DTL-010 handles that)

## Related Issues

- **Predecessor**: DTL-008 (Dimension schema must accept convert_tz in _to_dimension_group_dict)
- **Successor**: DTL-010 (CLI adds --convert-tz flag)
- **Successor**: DTL-011 (Unit tests for timezone conversion)
- **Successor**: DTL-012 (Integration and golden tests)
- **Successor**: DTL-013 (Documentation updates)

## Questions for Team Review

1. Should we add default_convert_tz as a formal parameter to Dimension.to_lookml_dict(), or continue using the pattern where SemanticModel handles this?
   - **Recommendation**: Continue current pattern (SemanticModel calls dim.to_lookml_dict(default_convert_tz=...) for time dims only)

2. Should we document the three-level default hierarchy in a module-level constant?
   - **Recommendation**: Yes, but in DTL-010 when CLI is added; for now just comments in code

3. Do we need to add convert_tz to the LookMLView class or just SemanticModel?
   - **Recommendation**: Just SemanticModel; LookMLView is for direct LookML input
