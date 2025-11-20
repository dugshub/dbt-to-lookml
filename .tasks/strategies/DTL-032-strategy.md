# DTL-032: Implementation Strategy
## Implement group_label in dimension_group generation

**Issue**: [DTL-032](../issues/DTL-032.md)
**Epic**: [DTL-029](../epics/DTL-029.md)
**Type**: Feature
**Stack**: Backend
**Created**: 2025-11-19

---

## Overview

This strategy outlines the implementation approach for adding `group_label` support to time dimension_group generation in LookML output. The feature will organize time dimensions hierarchically in the Looker field picker by grouping all time dimension_groups under a common label (default: "Time Dimensions").

### Dependencies

- **Prerequisite**: DTL-031 must be completed first to add the necessary schema fields and generator parameters
- **Related**: DTL-030 (research), DTL-033 (group_item_label), DTL-034 (tests), DTL-035 (docs)

---

## Current State Analysis

### Existing Precedence Pattern

The codebase already implements a three-tier precedence pattern for `convert_tz` in `Dimension._to_dimension_group_dict()` (lines 306-316 in `schemas/semantic_layer.py`):

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
```

**Key observations:**
- Default value is set first (most defensive approach)
- Generator/CLI parameter overrides default if provided
- Dimension metadata has highest priority and can override everything
- Uses explicit `is not None` checks to differentiate between "not set" and "False/empty"
- Final conversion to LookML string format ("yes"/"no")

### Current dimension_group Output

From `golden/expected_rental_orders.view.lkml` (lines 40-52):

```lookml
dimension_group: rental_date {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: booking_date ;;
  description: "Date of rental booking"
  convert_tz: no
}
```

**Missing**: `group_label` parameter to organize time dimensions hierarchically.

### Parameter Flow Architecture

Current flow for `convert_tz` (serves as template for `group_label`):

1. **CLI** (`__main__.py`): Flags `--convert-tz` / `--no-convert-tz` → `convert_tz` boolean
2. **Generator** (`lookml.py` line 35): Stores as `self.convert_tz`
3. **SemanticModel** (`semantic_layer.py` line 427): Receives via `to_lookml_dict(convert_tz=...)`
4. **Dimension** (`semantic_layer.py` line 474): Receives via `to_lookml_dict(default_convert_tz=convert_tz)`
5. **Output** (`semantic_layer.py` line 316): Applied in `_to_dimension_group_dict()`

---

## Implementation Design

### 1. Method Signature Update

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`
**Location**: Line 220 (Dimension._to_dimension_group_dict)

```python
def _to_dimension_group_dict(
    self,
    default_convert_tz: bool | None = None,
    default_time_dimension_group_label: str | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
    """Convert time dimension to LookML dimension_group.

    Args:
        default_convert_tz: Default timezone conversion setting from generator or CLI.
        default_time_dimension_group_label: Default group label for time dimensions.
            - String value: Use as group_label for organization
            - None: Use hardcoded default ("Time Dimensions")
            - Empty string: Disable group labeling (no group_label parameter)

    Returns:
        Dictionary with dimension_group configuration including optional group_label.
    """
```

**Rationale**: Follows established pattern from `default_convert_tz` parameter. The `default_` prefix clearly indicates this is a fallback value that can be overridden.

### 2. Precedence Logic Implementation

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`
**Location**: After line 304 (before convert_tz logic or after it)

```python
# Determine group_label with three-tier precedence:
# 1. Dimension-level meta.time_dimension_group_label (highest priority)
# 2. default_time_dimension_group_label parameter (from generator/CLI)
# 3. Hardcoded default: "Time Dimensions" (lowest priority)
group_label = "Time Dimensions"  # Default
if default_time_dimension_group_label is not None:
    group_label = default_time_dimension_group_label
if self.config and self.config.meta and self.config.meta.time_dimension_group_label is not None:
    group_label = self.config.meta.time_dimension_group_label

# Apply group_label if not explicitly disabled (empty string)
if group_label:  # Falsy check: empty string means "disabled"
    result["group_label"] = group_label
```

**Key design decisions:**

1. **Default value**: "Time Dimensions" - Clear, descriptive, follows LookML conventions
2. **Disabling mechanism**: Empty string (`""`) explicitly disables grouping
   - This is consistent with LookML behavior where omitting a field is different from setting it to empty
   - Allows users to opt-out at any precedence level
3. **None handling**: `None` means "use next level in precedence chain"
   - Dimension metadata `None` → check generator parameter
   - Generator parameter `None` → use hardcoded default
4. **Explicit checks**: Use `is not None` to differentiate between unset (`None`) and disabled (`""`)

### 3. Parameter Propagation

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`
**Location**: Line 474 (SemanticModel.to_lookml_dict, where dimensions are converted)

**Current code**:
```python
if dim.type == DimensionType.TIME:
    dim_dict = dim.to_lookml_dict(default_convert_tz=convert_tz)
```

**Updated code**:
```python
if dim.type == DimensionType.TIME:
    dim_dict = dim.to_lookml_dict(
        default_convert_tz=convert_tz,
        default_time_dimension_group_label=time_dimension_group_label,
    )
```

**Prerequisite**: `SemanticModel.to_lookml_dict()` must accept `time_dimension_group_label` parameter (updated in DTL-031).

**Current signature** (line 426):
```python
def to_lookml_dict(
    self, schema: str = "", convert_tz: bool | None = None
) -> dict[str, Any]:
```

**Expected after DTL-031**:
```python
def to_lookml_dict(
    self,
    schema: str = "",
    convert_tz: bool | None = None,
    time_dimension_group_label: str | None = None,
) -> dict[str, Any]:
```

### 4. Dimension.to_lookml_dict() Signature Update

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`
**Location**: Line 128 (Dimension.to_lookml_dict)

**Current code**:
```python
def to_lookml_dict(self, default_convert_tz: bool | None = None) -> dict[str, Any]:
    """Convert dimension to LookML format."""
    if self.type == DimensionType.TIME:
        return self._to_dimension_group_dict(default_convert_tz=default_convert_tz)
    else:
        return self._to_dimension_dict()
```

**Updated code**:
```python
def to_lookml_dict(
    self,
    default_convert_tz: bool | None = None,
    default_time_dimension_group_label: str | None = None,
) -> dict[str, Any]:
    """Convert dimension to LookML format.

    Args:
        default_convert_tz: Optional default timezone conversion setting for time dimensions.
        default_time_dimension_group_label: Optional default group label for time dimensions.
    """
    if self.type == DimensionType.TIME:
        return self._to_dimension_group_dict(
            default_convert_tz=default_convert_tz,
            default_time_dimension_group_label=default_time_dimension_group_label,
        )
    else:
        return self._to_dimension_dict()
```

**Rationale**: This maintains the parameter interface at the public method level and passes through to the private implementation method.

---

## Label Parameter Strategy

### Issue Context

The issue mentions: "Ensure dimension_group's `label` parameter is set for sub-grouping"

### Current Behavior

In `_to_dimension_group_dict()` (lines 296-297):

```python
if self.label:
    result["label"] = self.label
```

The `label` parameter is already applied if provided in the semantic model dimension definition.

### LookML Field Picker Hierarchy

With `group_label` and `label` both present:

```lookml
dimension_group: rental_date {
  type: time
  label: "Rental Created"           # Sub-category name in field picker
  group_label: "Time Dimensions"    # Top-level category
  timeframes: [date, week, month, quarter, year]
  sql: booking_date ;;
  convert_tz: no
}
```

**Result in Looker field picker**:
```
Time Dimensions          ← group_label
  Rental Created         ← label (dimension_group name becomes parent)
    Date                 ← timeframe
    Week
    Month
    Quarter
    Year
```

### Recommendation

**No additional implementation needed** for the `label` parameter. The existing code already handles it correctly. The issue statement is highlighting that:

1. `group_label` organizes all time dimensions under one top-level category
2. `label` (if provided) creates the sub-category for each dimension_group
3. Timeframes nest under the label/dimension_group name

**Documentation note**: In the spec/documentation, clarify that:
- `group_label` is the new feature (organizes all time dimensions)
- `label` is existing behavior (optionally customizes dimension_group display name)
- Both work together to create the hierarchy

---

## Edge Cases and Error Handling

### 1. Empty String vs. None

**Scenario**: User wants to disable group labeling

```yaml
# Dimension level - disable for this dimension only
dimensions:
  - name: created_at
    type: time
    config:
      meta:
        time_dimension_group_label: ""  # Empty string = disabled
```

```python
# Generator level - disable for all dimensions
generator = LookMLGenerator(
    time_dimension_group_label=""  # Empty string = disabled
)
```

**Implementation**:
```python
if group_label:  # Falsy check handles empty string
    result["group_label"] = group_label
# If group_label is "", this block doesn't execute
```

**Result**: No `group_label` parameter in LookML output (backward compatible behavior).

### 2. Null/None Handling

**Scenario**: Parameter not provided (use next level in chain)

```python
# Dimension metadata doesn't specify (or is None)
# Falls back to generator parameter
if self.config and self.config.meta and self.config.meta.time_dimension_group_label is not None:
    group_label = self.config.meta.time_dimension_group_label
```

**Test case needed**: Verify `None` correctly falls through precedence chain.

### 3. Special Characters in Labels

**Scenario**: User provides label with special characters

```yaml
config:
  meta:
    time_dimension_group_label: "Time/Dimensions & Dates"
```

**Handling**: LookML accepts any string in quotes. The `lkml` library will handle escaping during serialization. No special validation needed.

**Test case**: Verify special characters are properly escaped in output.

### 4. Very Long Labels

**Scenario**: User provides very long label text

```yaml
config:
  meta:
    time_dimension_group_label: "This is an extremely long label that might cause issues in the Looker UI"
```

**Handling**: No length validation. LookML doesn't enforce limits; Looker UI will truncate/wrap as needed. This is a UX concern, not a validation concern.

**Decision**: Don't validate length; trust user judgment and Looker UI handling.

---

## Testing Strategy

### Unit Tests

**File**: `src/tests/unit/test_schemas.py`

#### Test 1: Default Group Label
```python
def test_dimension_group_default_group_label(self) -> None:
    """Test that time dimensions get default group_label."""
    # Arrange
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
    )

    # Act - no parameters provided
    result = dim.to_lookml_dict()

    # Assert
    assert result.get("group_label") == "Time Dimensions"
```

#### Test 2: Generator Parameter Override
```python
def test_dimension_group_generator_parameter_group_label(self) -> None:
    """Test that generator parameter overrides default group_label."""
    # Arrange
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
    )

    # Act - generator provides custom label
    result = dim.to_lookml_dict(default_time_dimension_group_label="Custom Time Dims")

    # Assert
    assert result.get("group_label") == "Custom Time Dims"
```

#### Test 3: Dimension Metadata Override
```python
def test_dimension_group_metadata_overrides_generator(self) -> None:
    """Test that dimension metadata overrides generator parameter."""
    # Arrange
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(meta=ConfigMeta(time_dimension_group_label="Event Times")),
    )

    # Act - generator provides different label
    result = dim.to_lookml_dict(default_time_dimension_group_label="Custom Time Dims")

    # Assert - metadata should win
    assert result.get("group_label") == "Event Times"
```

#### Test 4: Explicit Disable with Empty String (Metadata)
```python
def test_dimension_group_disable_with_empty_string_metadata(self) -> None:
    """Test that empty string in metadata disables group_label."""
    # Arrange
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(meta=ConfigMeta(time_dimension_group_label="")),
    )

    # Act - even with generator default
    result = dim.to_lookml_dict(default_time_dimension_group_label="Time Dimensions")

    # Assert - should have no group_label key
    assert "group_label" not in result
```

#### Test 5: Explicit Disable with Empty String (Generator)
```python
def test_dimension_group_disable_with_empty_string_generator(self) -> None:
    """Test that empty string in generator parameter disables group_label."""
    # Arrange
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
    )

    # Act
    result = dim.to_lookml_dict(default_time_dimension_group_label="")

    # Assert
    assert "group_label" not in result
```

#### Test 6: None Falls Through to Default
```python
def test_dimension_group_none_uses_default(self) -> None:
    """Test that None in metadata falls through to default."""
    # Arrange
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(meta=ConfigMeta(time_dimension_group_label=None)),
    )

    # Act - no generator parameter
    result = dim.to_lookml_dict()

    # Assert - should use hardcoded default
    assert result.get("group_label") == "Time Dimensions"
```

#### Test 7: Precedence Chain (All Levels)
```python
def test_dimension_group_label_precedence_chain(self) -> None:
    """Test full precedence chain: metadata > generator > default."""
    # Case 1: Metadata wins
    dim1 = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(meta=ConfigMeta(time_dimension_group_label="Meta")),
    )
    assert dim1.to_lookml_dict(default_time_dimension_group_label="Gen")["group_label"] == "Meta"

    # Case 2: Generator wins (no metadata)
    dim2 = Dimension(
        name="updated_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
    )
    assert dim2.to_lookml_dict(default_time_dimension_group_label="Gen")["group_label"] == "Gen"

    # Case 3: Default wins (neither metadata nor generator)
    dim3 = Dimension(
        name="deleted_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
    )
    assert dim3.to_lookml_dict()["group_label"] == "Time Dimensions"
```

#### Test 8: Works with Existing Parameters
```python
def test_dimension_group_label_with_convert_tz(self) -> None:
    """Test that group_label works alongside other parameters like convert_tz."""
    # Arrange
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(meta=ConfigMeta(convert_tz=True)),
    )

    # Act
    result = dim.to_lookml_dict(
        default_convert_tz=False,
        default_time_dimension_group_label="Events"
    )

    # Assert - both parameters applied
    assert result.get("group_label") == "Events"
    assert result.get("convert_tz") == "yes"  # Metadata overrides
```

#### Test 9: Label and Group Label Together
```python
def test_dimension_group_label_and_group_label(self) -> None:
    """Test that label and group_label can coexist."""
    # Arrange
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        label="Order Created",  # Sub-category
        config=Config(meta=ConfigMeta(time_dimension_group_label="Time Dimensions")),
    )

    # Act
    result = dim.to_lookml_dict()

    # Assert
    assert result.get("label") == "Order Created"
    assert result.get("group_label") == "Time Dimensions"
```

#### Test 10: Special Characters
```python
def test_dimension_group_label_special_characters(self) -> None:
    """Test that special characters in group_label are preserved."""
    # Arrange
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(meta=ConfigMeta(time_dimension_group_label="Time/Dates & Events")),
    )

    # Act
    result = dim.to_lookml_dict()

    # Assert
    assert result.get("group_label") == "Time/Dates & Events"
```

### Integration Tests

**File**: `src/tests/integration/test_time_dimension_organization.py` (new file)

#### Integration Test 1: Full Flow with Multiple Time Dimensions
```python
def test_multiple_time_dimensions_with_group_label(tmp_path: Path) -> None:
    """Test that multiple time dimensions all get same group_label."""
    # Arrange - semantic model with multiple time dimensions
    yaml_content = """
semantic_model:
  name: orders
  model: ref('orders')
  entities:
    - name: order_id
      type: primary
  dimensions:
    - name: created_at
      type: time
      type_params:
        time_granularity: day
      config:
        meta:
          time_dimension_group_label: "Event Times"
    - name: updated_at
      type: time
      type_params:
        time_granularity: day
      # No metadata - should use generator default
    - name: shipped_at
      type: time
      type_params:
        time_granularity: day
      config:
        meta:
          time_dimension_group_label: ""  # Explicitly disabled
  measures:
    - name: order_count
      agg: count
"""

    # Create temporary YAML file
    yaml_file = tmp_path / "orders.yaml"
    yaml_file.write_text(yaml_content)

    # Parse and generate
    parser = DbtParser()
    models = parser.parse_directory(str(tmp_path))

    generator = LookMLGenerator(
        schema="public",
        time_dimension_group_label="Order Times"  # Generator default
    )
    output = generator.generate(models)

    # Assert
    view_content = output["orders.view.lkml"]

    # created_at should use metadata override
    assert 'group_label: "Event Times"' in view_content

    # updated_at should use generator default
    assert 'group_label: "Order Times"' in view_content

    # shipped_at should have NO group_label (explicitly disabled)
    # This is harder to assert; check that shipped_at section doesn't have group_label
    assert view_content.count('group_label:') == 2  # Only created_at and updated_at
```

### Golden Test Updates

**File**: Update existing golden test expected output files

The golden tests compare generated LookML against expected output. We need to update expected files to include `group_label` where appropriate.

**Strategy**:
1. Run golden tests after implementation
2. Review generated output for correctness
3. Update expected files if changes are intentional
4. Commit updated golden files with implementation

**Example update** (`src/tests/golden/expected_rental_orders.view.lkml`):

**Before**:
```lookml
dimension_group: rental_date {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: booking_date ;;
  description: "Date of rental booking"
  convert_tz: no
}
```

**After**:
```lookml
dimension_group: rental_date {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: booking_date ;;
  description: "Date of rental booking"
  group_label: "Time Dimensions"
  convert_tz: no
}
```

**Decision point**: Do we update all existing golden tests, or add a new test fixture with group_label?
- **Recommendation**: Update existing tests to include the default behavior, and add new test fixtures for edge cases (disabled, custom labels)

---

## LookML Output Examples

### Example 1: Default Behavior (Hardcoded Default)

**Input** (no configuration):
```yaml
dimensions:
  - name: created_at
    type: time
    type_params:
      time_granularity: day
```

**Output**:
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  group_label: "Time Dimensions"
  convert_tz: no
}
```

### Example 2: Generator Parameter Override

**Generator**:
```python
generator = LookMLGenerator(
    time_dimension_group_label="Event Timestamps"
)
```

**Output**:
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  group_label: "Event Timestamps"
  convert_tz: no
}
```

### Example 3: Dimension Metadata Override

**Input**:
```yaml
dimensions:
  - name: created_at
    type: time
    type_params:
      time_granularity: day
    config:
      meta:
        time_dimension_group_label: "Order Lifecycle"
```

**Output**:
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  group_label: "Order Lifecycle"
  convert_tz: no
}
```

### Example 4: Disabled (Empty String)

**Input**:
```yaml
dimensions:
  - name: created_at
    type: time
    type_params:
      time_granularity: day
    config:
      meta:
        time_dimension_group_label: ""
```

**Output** (no group_label parameter):
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
}
```

### Example 5: With Label for Sub-Category

**Input**:
```yaml
dimensions:
  - name: created_at
    type: time
    label: "Order Created"
    type_params:
      time_granularity: day
    config:
      meta:
        time_dimension_group_label: "Time Dimensions"
```

**Output**:
```lookml
dimension_group: created_at {
  type: time
  label: "Order Created"
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  group_label: "Time Dimensions"
  convert_tz: no
}
```

**Looker Field Picker** (hierarchical display):
```
Time Dimensions
  Order Created
    Date
    Week
    Month
    Quarter
    Year
```

---

## Implementation Checklist

### Code Changes

- [ ] Update `Dimension._to_dimension_group_dict()` signature to accept `default_time_dimension_group_label`
- [ ] Implement three-tier precedence logic for `group_label` determination
- [ ] Add `group_label` to result dictionary (if not disabled)
- [ ] Update `Dimension.to_lookml_dict()` signature to accept and pass through the parameter
- [ ] Update `SemanticModel.to_lookml_dict()` to pass `time_dimension_group_label` to dimension conversion
- [ ] Add comprehensive docstring updates explaining precedence and usage

### Testing

**Unit Tests** (`test_schemas.py`):
- [ ] Test default group_label behavior
- [ ] Test generator parameter override
- [ ] Test dimension metadata override (highest priority)
- [ ] Test empty string disables group_label (metadata level)
- [ ] Test empty string disables group_label (generator level)
- [ ] Test None falls through to next precedence level
- [ ] Test full precedence chain (all three levels)
- [ ] Test interaction with other parameters (convert_tz, label, etc.)
- [ ] Test special characters in group_label
- [ ] Test label and group_label together

**Integration Tests** (`test_time_dimension_organization.py`):
- [ ] Test multiple time dimensions with different configurations
- [ ] Test full flow: YAML → Parser → Generator → LookML output
- [ ] Test precedence in realistic scenario with mixed configurations

**Golden Tests**:
- [ ] Update existing golden test expected files to include `group_label`
- [ ] Add new golden test fixture for edge cases (disabled, custom labels)
- [ ] Verify golden tests pass with updated expectations

### Documentation

- [ ] Update `_to_dimension_group_dict()` docstring with group_label precedence explanation
- [ ] Update CLAUDE.md if needed (likely minimal; DTL-035 handles main docs)
- [ ] Add inline comments explaining precedence logic

### Validation

- [ ] Run `make test` - all tests pass
- [ ] Run `make test-coverage` - maintain 95%+ branch coverage
- [ ] Run `make type-check` - no mypy errors
- [ ] Run `make lint` - no linting issues
- [ ] Run `make test-full` - all test suites pass
- [ ] Manual testing: Generate LookML with various configurations and verify output

---

## Risk Assessment

### Low Risk

1. **Pattern replication**: Following exact pattern of `convert_tz` implementation reduces risk
2. **Backward compatible**: Default behavior adds new parameter without breaking existing functionality
3. **Well-tested precedence**: Using same precedence pattern that's already proven in production

### Medium Risk

1. **Golden test updates**: Must update expected output files correctly
   - **Mitigation**: Review diffs carefully; commit separately for clarity
2. **Parameter threading**: Must update multiple function signatures consistently
   - **Mitigation**: Follow type checking; mypy will catch signature mismatches

### Edge Cases to Watch

1. **Empty string vs. None**: Ensure explicit `is not None` checks
2. **Falsy values**: Empty string should disable, not error
3. **Interaction with label**: Verify both parameters work together correctly

---

## Success Criteria

### Functional

- [ ] Time dimensions have `group_label` in generated LookML (default: "Time Dimensions")
- [ ] Three-tier precedence works correctly (metadata > generator > default)
- [ ] Empty string explicitly disables group labeling at any level
- [ ] Works alongside existing parameters (convert_tz, label, description, etc.)
- [ ] No regression in existing dimension_group functionality

### Quality

- [ ] 95%+ branch coverage maintained (10 unit tests + integration tests)
- [ ] All type hints correct (mypy --strict passes)
- [ ] No linting errors (ruff passes)
- [ ] Golden tests updated and passing
- [ ] Code follows existing patterns and conventions

### Documentation

- [ ] Comprehensive docstrings with examples
- [ ] Inline comments for precedence logic
- [ ] CLAUDE.md updated if needed (defer to DTL-035 for main updates)

---

## Follow-up Items

### Immediate (This Issue)

- Implement group_label generation logic
- Update tests
- Update golden test expectations

### Later Issues (Out of Scope)

- **DTL-033**: Add `group_item_label` support for cleaner timeframe display
- **DTL-034**: Comprehensive test suite updates (if more extensive testing needed)
- **DTL-035**: Full documentation with user-facing examples and best practices

---

## References

### Code Locations

- **Dimension class**: `src/dbt_to_lookml/schemas/semantic_layer.py:117-323`
- **_to_dimension_group_dict**: `src/dbt_to_lookml/schemas/semantic_layer.py:220-322`
- **convert_tz precedence**: `src/dbt_to_lookml/schemas/semantic_layer.py:306-316`
- **SemanticModel.to_lookml_dict**: `src/dbt_to_lookml/schemas/semantic_layer.py:426-524`
- **LookMLGenerator**: `src/dbt_to_lookml/generators/lookml.py:22-155`
- **ConfigMeta schema**: `src/dbt_to_lookml/schemas/config.py:23-98`

### Test Locations

- **Unit tests**: `src/tests/unit/test_schemas.py`
- **convert_tz tests**: `src/tests/unit/test_schemas.py:1202-1426`
- **Golden tests**: `src/tests/golden/`
- **Expected output**: `src/tests/golden/expected_rental_orders.view.lkml`

### Documentation

- **CLAUDE.md**: `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md`
- **Epic DTL-029**: `.tasks/epics/DTL-029.md`
- **Issue DTL-032**: `.tasks/issues/DTL-032.md`
- **Prerequisite DTL-031**: `.tasks/issues/DTL-031.md`

---

## Estimated Effort

- **Code changes**: 1-2 hours
  - Method signature updates: 30 min
  - Precedence logic implementation: 30 min
  - Parameter threading: 30 min
  - Docstring updates: 30 min

- **Testing**: 2-3 hours
  - Unit tests (10 tests): 1.5 hours
  - Integration test: 30 min
  - Golden test updates: 1 hour

- **Validation**: 30 min
  - Run full test suite
  - Manual verification of output

**Total**: 3.5-5.5 hours

---

## Approval Checklist

Before moving to implementation (spec phase):

- [x] Strategy reviewed and approved
- [ ] Dependencies confirmed (DTL-031 completed)
- [ ] Test approach validated
- [ ] Risk assessment acceptable
- [ ] Effort estimate reasonable

---

**Status**: Ready for spec phase
**Next Step**: Create detailed implementation spec (DTL-032-spec.md) based on this strategy
**Blocking**: Waiting for DTL-031 completion
