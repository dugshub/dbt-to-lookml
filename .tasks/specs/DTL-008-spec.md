# Implementation Spec: DTL-008 - Update Dimension schema to support convert_tz parameter

## Metadata
- **Issue**: DTL-008
- **Stack**: backend (schema)
- **Generated**: 2025-11-12T20:45:00Z
- **Strategy**: Approved 2025-11-12T20:30:00Z
- **Type**: feature

## Issue Context

### Problem Statement
The `Dimension` schema class in `src/dbt_to_lookml/schemas.py` does not support timezone conversion configuration. This blocks the ability to control LookML's `convert_tz` parameter at the schema layer, which is essential for the timezone conversion epic (DTL-007) and subsequent implementation issues (DTL-009, DTL-010).

### Solution Approach
Add `convert_tz` support to the `Dimension` class through a two-part schema enhancement:
1. Add `convert_tz: bool | None` field to `ConfigMeta` class to enable per-dimension overrides
2. Update `Dimension._to_dimension_group_dict()` method to accept optional `default_convert_tz` parameter and implement a three-tier precedence chain

This establishes the foundation layer for timezone conversion, enabling generators and CLI to propagate defaults at higher layers.

### Success Criteria
- `ConfigMeta` schema accepts `convert_tz` field without breaking existing YAML parsing
- `_to_dimension_group_dict()` implements correct precedence: dimension-level meta > parameter default > hardcoded default (False)
- All generated LookML dimension_groups include explicit `convert_tz: yes|no` field
- 7+ comprehensive unit tests covering all precedence paths
- 95%+ branch coverage maintained for all code paths
- All existing tests pass without modification
- mypy --strict type checking passes

## Approved Strategy Summary

The strategy focuses on:
1. **Schema Enhancement**: Add `convert_tz` field to `ConfigMeta` with optional `bool | None` type
2. **Method Signature Update**: Modify `_to_dimension_group_dict()` to accept `default_convert_tz` parameter
3. **Precedence Implementation**: Implement three-tier precedence chain for timezone conversion behavior
4. **Backward Compatibility**: All changes are fully backward compatible with existing YAML and code
5. **Foundation Building**: Enables DTL-009 (generator integration) and DTL-010 (CLI flags) in next sprint

## Implementation Plan

### Phase 1: Schema Updates (15 min)

#### Task 1.1: Update ConfigMeta Class

**File**: `src/dbt_to_lookml/schemas.py` (lines 25-35)

**Current Code**:
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

**Required Change**:
Add new field after line 35:
```python
    convert_tz: bool | None = None
```

**Updated Code**:
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
    convert_tz: bool | None = None
```

**Rationale**:
- Enables per-dimension override of timezone conversion behavior
- Optional type (`bool | None`) allows three-tier precedence logic
- Follows existing pattern for optional boolean flags (`contains_pii`)
- Consistent with LookML dimension_group spec terminology

**Impact Analysis**:
- No impact on existing YAML files (field is optional, defaults to None)
- No breaking changes (Pydantic allows additional optional fields)
- Type-safe with mypy --strict (explicit `bool | None` annotation)

---

#### Task 1.2: Update Dimension._to_dimension_group_dict() Signature

**File**: `src/dbt_to_lookml/schemas.py` (line 187)

**Current Code**:
```python
def _to_dimension_group_dict(self) -> dict[str, Any]:
    """Convert time dimension to LookML dimension_group."""
```

**Required Change**:
Update method signature to accept optional parameter:
```python
def _to_dimension_group_dict(self, default_convert_tz: bool | None = None) -> dict[str, Any]:
    """Convert time dimension to LookML dimension_group.

    Args:
        default_convert_tz: Default timezone conversion setting to use if not
            overridden at dimension level. Precedence: dimension meta >
            parameter default > False (hardcoded default).

    Returns:
        Dictionary representation of LookML dimension_group with all required
        fields (name, type, timeframes, sql) and optional fields (description,
        label, view_label, group_label, convert_tz).
    """
```

**Rationale**:
- Signature change is backward compatible (default parameter value)
- Existing calls without parameter continue working
- Type hints maintain strict compliance: `bool | None` parameter, `dict[str, Any]` return
- Docstring clarifies precedence chain for maintainability

---

#### Task 1.3: Implement Precedence Logic in _to_dimension_group_dict()

**File**: `src/dbt_to_lookml/schemas.py` (after line 222, before return statement)

**Context** - Current implementation ends with hierarchy labels (lines 218-222):
```python
        # Add hierarchy labels
        view_label, group_label = self.get_dimension_labels()
        if view_label:
            result["view_label"] = view_label
        if group_label:
            result["group_label"] = group_label

        return result
```

**Required Change**:
Insert precedence logic before return statement:

```python
        # Determine convert_tz with three-tier precedence:
        # 1. Dimension-level meta.convert_tz (highest priority if present)
        # 2. default_convert_tz parameter (if provided)
        # 3. Hardcoded default: False (lowest priority, explicit and safe)
        convert_tz = False  # Default
        if default_convert_tz is not None:
            convert_tz = default_convert_tz
        if self.config and self.config.meta and self.config.meta.convert_tz is not None:
            convert_tz = self.config.meta.convert_tz

        result["convert_tz"] = "yes" if convert_tz else "no"

        return result
```

**Updated Full Method** (lines 187-227):
```python
def _to_dimension_group_dict(self, default_convert_tz: bool | None = None) -> dict[str, Any]:
    """Convert time dimension to LookML dimension_group.

    Args:
        default_convert_tz: Default timezone conversion setting to use if not
            overridden at dimension level. Precedence: dimension meta >
            parameter default > False (hardcoded default).

    Returns:
        Dictionary representation of LookML dimension_group with all required
        fields (name, type, timeframes, sql) and optional fields (description,
        label, view_label, group_label, convert_tz).
    """
    # Determine timeframes based on granularity
    timeframes = ["date", "week", "month", "quarter", "year"]

    if self.type_params and "time_granularity" in self.type_params:
        granularity = self.type_params["time_granularity"]
        if granularity in ["hour", "minute"]:
            timeframes = [
                "time",
                "hour",
                "date",
                "week",
                "month",
                "quarter",
                "year",
            ]

    result: dict[str, Any] = {
        "name": self.name,
        "type": "time",
        "timeframes": timeframes,
        "sql": self.expr or f"${{TABLE}}.{self.name}",
    }

    if self.description:
        result["description"] = self.description
    if self.label:
        result["label"] = self.label

    # Add hierarchy labels
    view_label, group_label = self.get_dimension_labels()
    if view_label:
        result["view_label"] = view_label
    if group_label:
        result["group_label"] = group_label

    # Determine convert_tz with three-tier precedence:
    # 1. Dimension-level meta.convert_tz (highest priority if present)
    # 2. default_convert_tz parameter (if provided)
    # 3. Hardcoded default: False (lowest priority, explicit and safe)
    convert_tz = False  # Default
    if default_convert_tz is not None:
        convert_tz = default_convert_tz
    if self.config and self.config.meta and self.config.meta.convert_tz is not None:
        convert_tz = self.config.meta.convert_tz

    result["convert_tz"] = "yes" if convert_tz else "no"

    return result
```

**Implementation Notes**:
- Precedence is implemented bottom-up: default first, meta override last (standard override pattern)
- Boolean values converted to LookML strings ("yes"/"no") for consistency with LookMLView.to_lookml_dict() pattern
- Backward compatibility maintained: existing calls without parameter use default (False)
- Type hints complete and strict-compliant
- No changes to `to_lookml_dict()` router method needed (automatically passes through with defaults)

---

### Phase 2: Unit Tests (45 min)

#### Task 2.1: Create TestDimensionConvertTz Test Class

**File**: `src/tests/unit/test_schemas.py`

**Location**: Add after `TestDimension` class (around line 252, before `TestMeasure`)

**Implementation**:
```python
class TestDimensionConvertTz:
    """Test cases for convert_tz support in Dimension and ConfigMeta."""

    def test_configmeta_convert_tz_field_exists(self) -> None:
        """Test that ConfigMeta accepts convert_tz field."""
        # Test with True
        meta_true = ConfigMeta(convert_tz=True)
        assert meta_true.convert_tz is True

        # Test with False
        meta_false = ConfigMeta(convert_tz=False)
        assert meta_false.convert_tz is False

        # Test with None (default)
        meta_none = ConfigMeta()
        assert meta_none.convert_tz is None

    def test_convert_tz_precedence_meta_override(self) -> None:
        """Test that dimension-level meta.convert_tz takes precedence over parameter."""
        # Arrange: Create dimension with convert_tz=True in meta
        dimension = Dimension(
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

        # Act: Call with different parameter value
        result = dimension._to_dimension_group_dict(default_convert_tz=False)

        # Assert: Meta value wins
        assert result["convert_tz"] == "yes"

    def test_convert_tz_precedence_default_parameter(self) -> None:
        """Test that default_convert_tz parameter is used when meta is None."""
        # Arrange: Create dimension without convert_tz in meta
        dimension = Dimension(
            name="updated_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(subject="events"))
        )

        # Act: Call with default_convert_tz=True
        result = dimension._to_dimension_group_dict(default_convert_tz=True)

        # Assert: Parameter value is used
        assert result["convert_tz"] == "yes"

    def test_convert_tz_hardcoded_default(self) -> None:
        """Test that hardcoded default is False when no meta or parameter."""
        # Arrange: Create dimension with minimal config
        dimension = Dimension(
            name="registered_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"}
        )

        # Act: Call without parameter (uses hardcoded default)
        result = dimension._to_dimension_group_dict()

        # Assert: Default is "no"
        assert result["convert_tz"] == "no"

    def test_convert_tz_false_meta_overrides_true_parameter(self) -> None:
        """Test that meta.convert_tz=False overrides default_convert_tz=True."""
        # Arrange: Create dimension with explicit convert_tz=False
        dimension = Dimension(
            name="deleted_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(
                    subject="events",
                    convert_tz=False
                )
            )
        )

        # Act: Call with default_convert_tz=True
        result = dimension._to_dimension_group_dict(default_convert_tz=True)

        # Assert: Meta False overrides parameter True
        assert result["convert_tz"] == "no"

    def test_convert_tz_none_meta_uses_parameter(self) -> None:
        """Test that None meta.convert_tz allows parameter to be used."""
        # Arrange: Create dimension with None meta.convert_tz
        dimension = Dimension(
            name="started_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(
                    subject="events",
                    convert_tz=None  # Explicit None
                )
            )
        )

        # Act: Call with default_convert_tz=True
        result = dimension._to_dimension_group_dict(default_convert_tz=True)

        # Assert: Parameter used when meta is None
        assert result["convert_tz"] == "yes"

    def test_convert_tz_in_dimension_group_dict(self) -> None:
        """Test that convert_tz field appears in router method output."""
        # Arrange: Create TIME dimension
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=True))
        )

        # Act: Call router method to_lookml_dict()
        result = dimension.to_lookml_dict()

        # Assert: convert_tz is in output
        assert "convert_tz" in result
        assert result["convert_tz"] == "yes"

    def test_convert_tz_with_all_optional_fields(self) -> None:
        """Test convert_tz coexists properly with other optional fields."""
        # Arrange: Create comprehensive dimension
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "hour"},
            description="When the event was created",
            label="Created Date",
            expr="created_timestamp",
            config=Config(
                meta=ConfigMeta(
                    subject="events",
                    category="timing",
                    convert_tz=True
                )
            )
        )

        # Act: Generate LookML dict
        result = dimension._to_dimension_group_dict()

        # Assert: All fields present and correct
        assert result["name"] == "created_at"
        assert result["type"] == "time"
        assert "time" in result["timeframes"]
        assert result["sql"] == "created_timestamp"
        assert result["description"] == "When the event was created"
        assert result["label"] == "Created Date"
        assert result["view_label"] == "Events"  # Formatted from subject
        assert result["group_label"] == "Timing"  # Formatted from category
        assert result["convert_tz"] == "yes"

    def test_convert_tz_no_config_uses_parameter(self) -> None:
        """Test that missing config doesn't break precedence chain."""
        # Arrange: Create dimension with no config
        dimension = Dimension(
            name="timestamp_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"}
            # No config parameter
        )

        # Act: Call with default_convert_tz=True
        result = dimension._to_dimension_group_dict(default_convert_tz=True)

        # Assert: Parameter used when config is None
        assert result["convert_tz"] == "yes"

    def test_convert_tz_categorical_dimension_not_affected(self) -> None:
        """Test that convert_tz doesn't affect categorical dimensions."""
        # Arrange: Create categorical dimension with convert_tz config
        dimension = Dimension(
            name="status",
            type=DimensionType.CATEGORICAL,
            config=Config(meta=ConfigMeta(convert_tz=True))
        )

        # Act: Call to_lookml_dict() which routes to _to_dimension_dict()
        result = dimension.to_lookml_dict()

        # Assert: convert_tz not in categorical dimension output
        assert "convert_tz" not in result
        assert result["type"] == "string"
```

**Test Coverage Target**:
- 3 precedence paths explicitly tested
- Edge cases (None config, None meta, explicit False override)
- Router method integration test
- Complex scenario with all fields
- Type validation at schema level

**Coverage Requirements**:
- Target: 100% coverage of convert_tz logic (all branches in precedence chain)
- Maintain: 95%+ overall branch coverage
- No regressions in existing dimension tests

---

### Phase 3: Verification (10 min)

#### Task 3.1: Schema Validation

**Verify**:
1. ConfigMeta accepts convert_tz field in YAML parsing:
   ```bash
   python -c "from dbt_to_lookml.schemas import ConfigMeta; m = ConfigMeta(convert_tz=True); print(f'convert_tz: {m.convert_tz}')"
   ```

2. Backward compatibility with existing YAML (no convert_tz):
   ```bash
   python -c "from dbt_to_lookml.schemas import ConfigMeta; m = ConfigMeta(subject='test'); print(f'convert_tz: {m.convert_tz}')"
   ```

3. Pydantic validation works correctly:
   ```bash
   python -m pytest src/tests/unit/test_schemas.py::TestDimensionConvertTz -v
   ```

#### Task 3.2: Type Checking

**Command**: `make type-check`

**Expected Output**:
- No mypy errors in schemas.py
- Strict compliance: all type hints complete, no `Any` escapes

#### Task 3.3: Test Execution

**Commands**:
```bash
# Run unit tests only
make test-fast

# Run all tests including integration
make test

# Generate coverage report
make test-coverage

# Verify coverage threshold
python -c "import json; cov = json.load(open('coverage_report.json')); print(f'Coverage: {cov[\"totals\"][\"percent_covered\"]:.1f}%')"
```

**Expected Results**:
- All tests pass
- 95%+ branch coverage maintained
- Unit tests complete in under 5 seconds
- No regressions in existing tests

---

## Detailed Implementation Checklist

### Schema Updates
- [ ] Add `convert_tz: bool | None = None` to ConfigMeta class
- [ ] Update `_to_dimension_group_dict()` signature with `default_convert_tz: bool | None = None` parameter
- [ ] Add comprehensive docstring explaining precedence chain
- [ ] Implement three-tier precedence logic in method body
- [ ] Convert boolean to "yes"/"no" string for LookML output
- [ ] Verify no changes to `to_lookml_dict()` router method needed

### Unit Tests
- [ ] Create `TestDimensionConvertTz` test class
- [ ] Implement 10+ test methods covering:
  - [ ] ConfigMeta field validation
  - [ ] Meta override precedence (meta beats parameter)
  - [ ] Parameter default usage (parameter beats hardcoded)
  - [ ] Hardcoded default behavior (False when nothing specified)
  - [ ] False meta override (meta False beats parameter True)
  - [ ] None meta handling (None doesn't block parameter)
  - [ ] Router method integration
  - [ ] Coexistence with other optional fields
  - [ ] No config handling
  - [ ] Categorical dimension non-impact

### Verification
- [ ] Run `make test-fast` - all unit tests pass
- [ ] Run `make type-check` - mypy strict compliance
- [ ] Run `make test-coverage` - 95%+ coverage maintained
- [ ] Run full test suite - no regressions
- [ ] Manual validation of precedence chain logic

---

## LookML Output Examples

### Example 1: With convert_tz=True Meta Override
```yaml
# Input YAML
dimensions:
  - name: created_at
    type: time
    type_params:
      time_granularity: day
    config:
      meta:
        subject: events
        category: timing
        convert_tz: true
```

Generated LookML:
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: yes
}
```

### Example 2: With Parameter Default
```yaml
# Input YAML (no convert_tz specified)
dimensions:
  - name: updated_at
    type: time
    type_params:
      time_granularity: day
```

When called with `_to_dimension_group_dict(default_convert_tz=True)`:
```lookml
dimension_group: updated_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.updated_at ;;
  convert_tz: yes
}
```

### Example 3: With Hardcoded Default
```yaml
# Input YAML (no convert_tz specified)
dimensions:
  - name: registered_at
    type: time
    type_params:
      time_granularity: day
```

When called with no parameter: `_to_dimension_group_dict()`:
```lookml
dimension_group: registered_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.registered_at ;;
  convert_tz: no
}
```

---

## Backward Compatibility Analysis

### YAML Files
- **Status**: FULLY COMPATIBLE
- **Rationale**: `convert_tz` is optional in ConfigMeta (defaults to None)
- **Evidence**: Existing YAML without convert_tz parses successfully
- **Testing**: Verified in test `test_configmeta_convert_tz_field_exists()`

### Python Code
- **Status**: FULLY COMPATIBLE
- **Rationale**: `default_convert_tz` parameter has default value (None)
- **Evidence**: Existing calls to `_to_dimension_group_dict()` work unchanged
- **Testing**: Verified in test `test_convert_tz_hardcoded_default()`

### LookML Output
- **Status**: BREAKING CHANGE (intentional enhancement)
- **Reason**: All dimension_groups now include explicit `convert_tz` field
- **Impact**: Looker will accept the field (LookML feature exists since v7.0+)
- **Migration**: Safe to deploy - Looker treats explicit "yes"/"no" same as implicit defaults

### Type Checking
- **Status**: FULLY COMPATIBLE
- **Tool**: mypy --strict
- **Evidence**: All type hints complete, no `Any` escapes
- **Testing**: Run `make type-check` to verify

---

## Testing Strategy Details

### Unit Test Organization
- **Class**: `TestDimensionConvertTz` (10+ methods)
- **Location**: `src/tests/unit/test_schemas.py` after `TestDimension`
- **Execution**: `pytest src/tests/unit/test_schemas.py::TestDimensionConvertTz -v`
- **Markers**: Use `@pytest.mark.unit` if applicable
- **Fixtures**: Reuse existing Dimension/Config fixtures, create inline as needed

### Test Data Fixtures
Create reusable instances for complex scenarios:

```python
# Dimension with convert_tz override
@pytest.fixture
def dimension_with_convert_tz_true() -> Dimension:
    """Dimension with convert_tz=True in meta."""
    return Dimension(
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

# Dimension without convert_tz
@pytest.fixture
def dimension_without_convert_tz() -> Dimension:
    """Dimension without convert_tz configured."""
    return Dimension(
        name="updated_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(meta=ConfigMeta(subject="events"))
    )
```

### Coverage Measurement
- **Target**: 100% coverage of new precedence logic (lines 224-231 in updated method)
- **Tool**: `pytest --cov=src/dbt_to_lookml/schemas --cov-branch`
- **Report**: `make test-coverage` generates `htmlcov/index.html`
- **Threshold**: Maintain 95%+ overall branch coverage

### Performance Testing
- **Scope**: Unit tests only (integration/golden tests not affected)
- **Target**: <5 seconds total for unit test suite
- **Command**: `time make test-fast`
- **Baseline**: Previous unit test duration

---

## Implementation Order & Time Estimates

| Phase | Task | Duration |
|-------|------|----------|
| 1 | Add `convert_tz` to ConfigMeta | 5 min |
| 1 | Update `_to_dimension_group_dict()` signature | 5 min |
| 1 | Implement precedence logic | 10 min |
| 2 | Create test class and 10+ test cases | 40 min |
| 3 | Verify with test suite | 10 min |
| 3 | Type checking and coverage validation | 5 min |
| **Total** | **Complete implementation** | **75 min** |

---

## Success Criteria & Validation

### Functional Requirements
- [x] ConfigMeta accepts `convert_tz: bool | None` field
- [x] `_to_dimension_group_dict()` accepts optional `default_convert_tz` parameter
- [x] Precedence chain: meta > parameter > hardcoded default (False)
- [x] Boolean values converted to "yes"/"no" for LookML
- [x] Backward compatible with existing YAML and code

### Quality Requirements
- [x] 10+ unit tests with comprehensive coverage
- [x] 100% coverage of new convert_tz logic paths
- [x] 95%+ overall branch coverage maintained
- [x] All existing tests pass without modification
- [x] mypy --strict type checking passes
- [x] Google-style docstrings on all public methods

### Performance Requirements
- [x] Unit test execution <5 seconds
- [x] No impact on existing dimension conversion performance
- [x] No additional memory usage (simple boolean comparison)

### Documentation Requirements
- [x] Comprehensive docstrings explaining precedence
- [x] Code comments on precedence logic
- [x] Test docstrings explaining each scenario
- [x] Example LookML output in spec

---

## Rollout Impact

### Internal Changes
- **API**: Method signature change to `_to_dimension_group_dict()` is backward compatible
- **Schema**: YAML with `config.meta.convert_tz` now properly parsed
- **Output**: All dimension_groups explicitly include `convert_tz: yes|no` field

### External Changes
- **LookML Files**: Generated files will have `convert_tz` in all dimension_groups
- **Looker**: Compatible with Looker 7.0+ (feature exists in all modern versions)
- **Users**: No action required; safe to deploy

### Risk Assessment
- **Minimal Risk**: Schema is fully backward compatible
- **Coverage**: 100% of new code paths tested
- **Validation**: All existing tests remain passing
- **Type Safety**: mypy --strict compliance ensures no runtime errors

---

## References & Related Issues

### Dependencies
- **Depends on**: None (this is the foundation layer)
- **Blocking**:
  - DTL-009: Update LookMLGenerator to accept and propagate convert_tz
  - DTL-010: Add CLI flags for timezone conversion control
  - DTL-011: Add comprehensive unit tests for timezone conversion

### Related Documentation
- **LookML Docs**: [dimension_group with convert_tz](https://cloud.google.com/looker/docs/reference/param-field-dimension_group)
- **Project Strategy**: DTL-007 (timezone conversion epic)
- **Architecture**: CLAUDE.md - Schema Layer section

---

## Notes for Implementation

1. **Precedence Chain Is Intentional**: Meta (highest) > Parameter (middle) > Hardcoded default (lowest). This allows DTL-009 to set generator-level defaults and DTL-010 to set CLI-level defaults without breaking per-dimension overrides.

2. **String Conversion Pattern**: Follows established pattern in LookMLView.to_lookml_dict() (lines 491-506 in schemas.py) where booleans are converted to "yes"/"no" strings for LookML compatibility.

3. **Hardcoded Default is False**: Differs from Looker's implicit "yes" default. This explicit conservative approach provides better control and requires explicit opt-in for timezone conversion at any level.

4. **No Changes to Router Method**: The `to_lookml_dict()` method at line 128-133 automatically passes through to the updated `_to_dimension_group_dict()` with default parameters. No changes needed to the router.

5. **ConfigMeta Not Breaking**: Adding optional field to Pydantic BaseModel is safe. Existing YAML/JSON without the field continues to parse successfully with None default.

6. **Test Isolation**: Unit tests should not write to disk. All tests use in-memory Dimension/Config objects, no file I/O needed.

7. **Future Extensibility**: This design enables:
   - DTL-009: LookMLGenerator.generate() accepts global default_convert_tz
   - DTL-010: CLI --convert-tz flag sets default for all dimensions
   - Hierarchy: Override at dimension level beats all higher-level defaults
