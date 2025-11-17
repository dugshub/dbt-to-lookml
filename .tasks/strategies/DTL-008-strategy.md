# Implementation Strategy: DTL-008

**Issue**: DTL-008 - Update Dimension schema to support convert_tz parameter
**Analyzed**: 2025-11-12T20:30:00Z
**Stack**: backend
**Type**: feature

## Approach

Add timezone conversion configuration support to the `Dimension` class by introducing a `convert_tz` field and updating the `_to_dimension_group_dict()` method to accept an optional `default_convert_tz` parameter. This enables a three-level precedence chain for timezone conversion behavior:

1. Per-dimension metadata override (`config.meta.convert_tz`)
2. Generator/method default parameter (`default_convert_tz`)
3. Hardcoded default (False)

The implementation is the foundation for the timezone conversion epic (DTL-007), enabling explicit control at the schema layer before propagation to generators and CLI.

## Architecture Impact

**Layer**: Core Schema Layer (foundational for DTL-009, DTL-010)

**Modified Files**:
- `src/dbt_to_lookml/schemas.py`:
  - Update `ConfigMeta` class to add `convert_tz: bool | None` field
  - Update `Dimension` class to modify `_to_dimension_group_dict()` signature
  - No changes needed to `Config` class (reuses existing meta structure)

**No new files** - This is a schema enhancement that fits within existing architecture.

## Dependencies

- **Depends on**: None (this is the foundation layer)

- **Blocking**:
  - DTL-009: Update LookMLGenerator to accept and propagate convert_tz settings
  - DTL-010: Add CLI flags for timezone conversion control
  - DTL-011: Add comprehensive unit tests for timezone conversion

- **Related to**: DTL-007 (parent epic defining overall strategy)

## Detailed Implementation Plan

### 1. Update ConfigMeta Schema

**Current state** (lines 25-35 in schemas.py):
```python
class ConfigMeta(BaseModel):
    """Represents metadata in a config section."""

    domain: str | None = None
    owner: str | None = None
    contains_pii: bool | None = None
    update_frequency: str | None = None
    subject: str | None = None
    category: str | None = None
    hierarchy: Hierarchy | None = None
```

**Change**: Add new field after line 35:
```python
    convert_tz: bool | None = None
```

**Rationale**:
- Supports per-dimension override of timezone conversion behavior
- Optional (`bool | None`) to allow three-tier precedence logic
- Follows existing pattern for optional boolean flags (`contains_pii`)
- Consistent with naming from LookML dimension_group spec

### 2. Update Dimension._to_dimension_group_dict() Method

**Current state** (lines 187-224):
- Takes no parameters
- Returns dict with name, type, timeframes, sql, and optional description/label
- Does not handle convert_tz at all

**Changes required**:

a) **Update method signature** (line 187):
```python
def _to_dimension_group_dict(self, default_convert_tz: bool | None = None) -> dict[str, Any]:
```

b) **Add convert_tz resolution logic** (after line 222, before return):
```python
        # Determine convert_tz with precedence:
        # 1. Dimension-level meta.convert_tz (if present)
        # 2. default_convert_tz parameter (if provided)
        # 3. Hardcoded default: False
        convert_tz = False  # Default
        if default_convert_tz is not None:
            convert_tz = default_convert_tz
        if self.config and self.config.meta and self.config.meta.convert_tz is not None:
            convert_tz = self.config.meta.convert_tz

        result["convert_tz"] = "yes" if convert_tz else "no"
```

**Implementation notes**:
- Precedence chain is implemented bottom-up (default first, meta override last)
- Boolean values are converted to LookML strings ("yes"/"no") for consistency with LookMLView.to_lookml_dict() pattern (lines 491-506)
- The method remains backward compatible: existing calls without the parameter will work with the default
- Type hints remain strict: `bool | None` for parameters, returns `dict[str, Any]`

### 3. Update to_lookml_dict() Router Method

**Current state** (lines 128-133):
```python
def to_lookml_dict(self) -> dict[str, Any]:
    """Convert dimension to LookML format."""
    if self.type == DimensionType.TIME:
        return self._to_dimension_group_dict()
    else:
        return self._to_dimension_dict()
```

**No changes needed** - The router method will automatically pass through to the updated `_to_dimension_group_dict()` with default parameters, maintaining backward compatibility.

### 4. Update SemanticModel.to_lookml_dict()

**Current state** (lines 349-352):
```python
        # Convert dimensions (separate regular dims from time dims)
        for dim in self.dimensions:
            dim_dict = dim.to_lookml_dict()
            if dim.type == DimensionType.TIME:
                dimension_groups.append(dim_dict)
```

**Decision**: Do NOT change SemanticModel in this issue. The generator-level default (`default_convert_tz`) will be passed at the next layer (DTL-009). This keeps schema changes focused and allows DTL-009 to introduce generator-level configuration.

## Testing Strategy

### Unit Test Coverage (src/tests/unit/test_schemas.py)

Add a new test class `TestDimensionConvertTz` with the following cases:

1. **test_convert_tz_precedence_meta_override**
   - Create Dimension with `config.meta.convert_tz=True`
   - Call `_to_dimension_group_dict(default_convert_tz=False)`
   - Verify: `result["convert_tz"] == "yes"` (meta wins)

2. **test_convert_tz_precedence_default_parameter**
   - Create Dimension without config meta
   - Call `_to_dimension_group_dict(default_convert_tz=True)`
   - Verify: `result["convert_tz"] == "yes"`

3. **test_convert_tz_hardcoded_default**
   - Create Dimension without config meta
   - Call `_to_dimension_group_dict()` (no parameter)
   - Verify: `result["convert_tz"] == "no"` (hardcoded default)

4. **test_convert_tz_false_default_override**
   - Create Dimension with `config.meta.convert_tz=False`
   - Call `_to_dimension_group_dict(default_convert_tz=True)`
   - Verify: `result["convert_tz"] == "no"` (meta False overrides default True)

5. **test_convert_tz_none_meta_uses_parameter**
   - Create Dimension with `config.meta.convert_tz=None`
   - Call `_to_dimension_group_dict(default_convert_tz=True)`
   - Verify: `result["convert_tz"] == "yes"` (parameter used when meta is None)

6. **test_convert_tz_in_dimension_group_dict**
   - Create Dimension with TIME type
   - Call `to_lookml_dict()` (router method)
   - Verify: returned dict includes `convert_tz` field

7. **test_convert_tz_with_all_optional_fields**
   - Create Dimension with description, label, and config.meta
   - Verify convert_tz coexists with other optional fields in output

### Test Data Fixtures

Create test Dimension instances:
```python
# Dimension with convert_tz override
dim_with_tz = Dimension(
    name="created_at",
    type=DimensionType.TIME,
    type_params={"time_granularity": "day"},
    config=Config(
        meta=ConfigMeta(
            subject="events",
            category="timing",
            convert_tz=True
        )
    )
)

# Dimension without convert_tz (should use defaults)
dim_without_tz = Dimension(
    name="updated_at",
    type=DimensionType.TIME,
    config=Config(meta=ConfigMeta(subject="events"))
)
```

### Coverage Requirements

- Target: 100% coverage of convert_tz logic paths
- Minimum: 95% overall branch coverage maintained
- Test all three precedence branches explicitly
- Verify no regression in existing dimension conversion tests

## Schema Validation

**Backward Compatibility**: FULLY COMPATIBLE
- `ConfigMeta.convert_tz` is optional (`None` allowed)
- Existing YAML without convert_tz will parse successfully
- Existing code calling `_to_dimension_group_dict()` without parameters continues to work
- Default behavior (convert_tz: no) is explicit and predictable

**Type Checking (mypy --strict)**:
- Parameter type: `bool | None` (matches existing nullable booleans)
- Return type: `dict[str, Any]` (unchanged)
- String conversion follows established pattern in LookMLView.to_lookml_dict()
- All type hints complete, no `Any` escapes

## LookML Output Format

Generated dimension_groups will include convert_tz field:

```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: yes
}
```

or with default:

```lookml
dimension_group: updated_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.updated_at ;;
  convert_tz: no
}
```

## Implementation Checklist

- [ ] Update `ConfigMeta` to add `convert_tz: bool | None = None` field
- [ ] Update `Dimension._to_dimension_group_dict()` signature to accept `default_convert_tz: bool | None = None`
- [ ] Implement precedence logic in `_to_dimension_group_dict()` method
- [ ] Add 7+ unit test cases to `test_schemas.py::TestDimensionConvertTz`
- [ ] Run `make test-fast` to verify unit tests pass
- [ ] Run `make type-check` to verify mypy strict compliance
- [ ] Run `make test-coverage` to verify no coverage regression
- [ ] Verify no breaking changes to existing tests
- [ ] Document changes in docstrings (ConfigMeta, _to_dimension_group_dict)

## Implementation Order

1. **Add ConfigMeta.convert_tz field** - 5 min
2. **Update _to_dimension_group_dict() signature** - 5 min
3. **Implement precedence logic** - 10 min
4. **Write unit tests** - 30 min
5. **Verify tests and coverage** - 10 min
6. **Final validation** - 5 min

**Estimated total**: 60 minutes

## Rollout Impact

- **Internal API**: Method signature change to `_to_dimension_group_dict()` adds optional parameter (backward compatible)
- **Schema**: YAML files with `config.meta.convert_tz` will now be properly parsed
- **LookML Output**: All generated dimension_groups will include explicit `convert_tz: yes|no` field
- **Test Impact**: No existing tests need modification; new tests validate convert_tz logic
- **Performance**: No impact (simple boolean precedence check)

## Notes for Implementation

1. **Preserve existing behavior in transition**: The hardcoded default is `False` (convert_tz: no), which is explicit and safe. This differs from Looker's implicit `yes` default, providing better control.

2. **String conversion pattern**: Follow the established pattern in LookMLView.to_lookml_dict() (lines 491-506) which converts booleans to "yes"/"no" strings for LookML compatibility.

3. **Three-tier precedence is intentional**:
   - Meta (dimension level) wins for explicit overrides
   - Parameter (generator/method level) allows batch configuration
   - Hardcoded default (False) is safe and explicit

4. **Future extensibility**: This design allows DTL-009 to propagate a default_convert_tz from the generator, and DTL-010 to set it from CLI flags.

5. **Optional config requirement**: If `config` is None, precedence falls through to default_convert_tz parameter (lines 2-3 of logic).
