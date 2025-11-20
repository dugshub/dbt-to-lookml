# DTL-032: Implementation Specification
## Implement group_label in dimension_group generation

**Issue**: [DTL-032](../issues/DTL-032.md)
**Strategy**: [DTL-032-strategy.md](../strategies/DTL-032-strategy.md)
**Epic**: [DTL-029](../epics/DTL-029.md)
**Type**: Feature
**Stack**: Backend
**Created**: 2025-11-19

---

## Overview

This specification provides detailed implementation instructions for adding `group_label` support to time dimension_group generation in LookML output. The feature organizes time dimensions hierarchically in the Looker field picker by grouping all time dimension_groups under a common label (default: "Time Dimensions").

### Dependencies

- **Prerequisite**: DTL-031 must be completed first to add the necessary schema fields (`ConfigMeta.time_dimension_group_label`) and generator parameters (`LookMLGenerator.time_dimension_group_label`)
- **Related**: DTL-030 (research), DTL-033 (group_item_label), DTL-034 (tests), DTL-035 (docs)

---

## Acceptance Criteria

### Functional Requirements

- [ ] Time dimensions generate `group_label` in LookML output (default: "Time Dimensions")
- [ ] Three-tier precedence system works correctly:
  - Dimension metadata (`config.meta.time_dimension_group_label`) has highest priority
  - Generator parameter (`LookMLGenerator(time_dimension_group_label=...)`) overrides default
  - Hardcoded default ("Time Dimensions") is lowest priority
- [ ] Empty string explicitly disables `group_label` at any precedence level
- [ ] `None` values correctly fall through to next precedence level
- [ ] Works alongside existing parameters (convert_tz, label, description, view_label, group_label from hierarchy)
- [ ] No regression in existing dimension_group functionality

### Quality Requirements

- [ ] 95%+ branch coverage maintained (10+ unit tests + integration tests)
- [ ] All type hints correct (mypy --strict passes)
- [ ] No linting errors (ruff passes)
- [ ] Golden tests updated and passing
- [ ] Code follows existing patterns and conventions

### Documentation Requirements

- [ ] Comprehensive docstrings with examples
- [ ] Inline comments for precedence logic
- [ ] CLAUDE.md updated if needed (defer extensive docs to DTL-035)

---

## Implementation Steps

### Step 1: Update Dimension._to_dimension_group_dict() Signature

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`
**Location**: Line 220-222 (method signature)

**Current Code**:
```python
def _to_dimension_group_dict(
    self, default_convert_tz: bool | None = None
) -> dict[str, Any]:
```

**Updated Code**:
```python
def _to_dimension_group_dict(
    self,
    default_convert_tz: bool | None = None,
    default_time_dimension_group_label: str | None = None,
) -> dict[str, Any]:
```

**Rationale**: Follows established pattern from `default_convert_tz` parameter. The `default_` prefix clearly indicates this is a fallback value that can be overridden.

---

### Step 2: Update Dimension._to_dimension_group_dict() Docstring

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`
**Location**: Line 223-283 (docstring)

**Add to Args section** (after default_convert_tz documentation):
```python
        default_time_dimension_group_label: Default group label for time dimensions.
            Controls the group_label parameter in generated dimension_groups through
            multi-level precedence:

            1. Dimension-level override via config.meta.time_dimension_group_label
               (highest priority)
            2. Generator default via default_time_dimension_group_label parameter
            3. Hardcoded default of "Time Dimensions" (lowest priority)

            Values:
            - String value: Use as group_label for organization in field picker
            - None: Use next level in precedence chain (or hardcoded default)
            - Empty string (""): Explicitly disable group_label (backward compatible)
```

**Add to Returns section** (update to include group_label):
```python
        Returns:
            Dictionary with dimension_group configuration including:
            - name: Dimension name
            - type: "time"
            - timeframes: List of appropriate timeframes based on granularity
            - sql: SQL expression for the timestamp column
            - convert_tz: "yes" or "no" based on precedence rules
            - group_label: Optional organizational label (if not disabled)
            - description: Optional description
            - label: Optional label
            - view_label/group_label: Optional hierarchy labels
```

**Add Example section** (after convert_tz examples):
```python
        Example (group_label precedence):
            Dimension with metadata override:

            ```python
            dimension = Dimension(
                name="created_at",
                type=DimensionType.TIME,
                type_params={"time_granularity": "day"},
                config=Config(meta=ConfigMeta(
                    time_dimension_group_label="Event Times"
                ))
            )
            result = dimension._to_dimension_group_dict(
                default_time_dimension_group_label="System Times"
            )
            # Result includes: "group_label": "Event Times" (meta wins)
            ```

            Dimension without override (uses generator default):

            ```python
            dimension = Dimension(
                name="shipped_at",
                type=DimensionType.TIME,
                type_params={"time_granularity": "day"}
            )
            result = dimension._to_dimension_group_dict(
                default_time_dimension_group_label="Shipping Timestamps"
            )
            # Result includes: "group_label": "Shipping Timestamps"
            ```

            Dimension with explicit disable:

            ```python
            dimension = Dimension(
                name="legacy_date",
                type=DimensionType.TIME,
                type_params={"time_granularity": "day"},
                config=Config(meta=ConfigMeta(
                    time_dimension_group_label=""  # Empty string disables
                ))
            )
            result = dimension._to_dimension_group_dict()
            # Result does NOT include "group_label" key
            ```
```

---

### Step 3: Implement Precedence Logic in _to_dimension_group_dict()

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`
**Location**: After line 304 (after group_label from hierarchy, before convert_tz logic)

**Insert Code** (after existing hierarchy group_label logic):
```python
        # Determine time dimension group_label with three-tier precedence:
        # 1. Dimension-level meta.time_dimension_group_label (highest priority)
        # 2. default_time_dimension_group_label parameter (from generator/CLI)
        # 3. Hardcoded default: "Time Dimensions" (lowest priority)
        #
        # Empty string explicitly disables group labeling (backward compatible).
        # None means "use next level in precedence chain".
        time_group_label = "Time Dimensions"  # Default
        if default_time_dimension_group_label is not None:
            time_group_label = default_time_dimension_group_label
        if (
            self.config
            and self.config.meta
            and self.config.meta.time_dimension_group_label is not None
        ):
            time_group_label = self.config.meta.time_dimension_group_label

        # Apply time dimension group_label if not explicitly disabled
        # Note: This is separate from hierarchy-based group_label (if present)
        # If hierarchy group_label exists, it takes precedence over time_group_label
        if time_group_label and "group_label" not in result:
            result["group_label"] = time_group_label
```

**Rationale**:
- Follows exact pattern from `convert_tz` precedence logic (lines 306-316)
- Default value set first (defensive approach)
- Generator/CLI parameter overrides default if provided
- Dimension metadata has highest priority and can override everything
- Explicit `is not None` checks differentiate between "not set" and "False/empty"
- Falsy check (`if time_group_label`) handles empty string disable case
- Checks `"group_label" not in result` to avoid overwriting hierarchy-based group_label

**Important**: The hierarchy-based `group_label` (from `get_dimension_labels()`) is already set at lines 300-304. This time dimension group_label should only apply if no hierarchy group_label exists, giving hierarchy labels priority.

---

### Step 4: Update Dimension.to_lookml_dict() Signature

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`
**Location**: Line 128-138

**Current Code**:
```python
def to_lookml_dict(self, default_convert_tz: bool | None = None) -> dict[str, Any]:
    """Convert dimension to LookML format.

    Args:
        default_convert_tz: Optional default timezone conversion setting
            for time dimensions.
    """
    if self.type == DimensionType.TIME:
        return self._to_dimension_group_dict(default_convert_tz=default_convert_tz)
    else:
        return self._to_dimension_dict()
```

**Updated Code**:
```python
def to_lookml_dict(
    self,
    default_convert_tz: bool | None = None,
    default_time_dimension_group_label: str | None = None,
) -> dict[str, Any]:
    """Convert dimension to LookML format.

    Args:
        default_convert_tz: Optional default timezone conversion setting
            for time dimensions.
        default_time_dimension_group_label: Optional default group label
            for time dimensions. Passed through to dimension_group generation.
    """
    if self.type == DimensionType.TIME:
        return self._to_dimension_group_dict(
            default_convert_tz=default_convert_tz,
            default_time_dimension_group_label=default_time_dimension_group_label,
        )
    else:
        return self._to_dimension_dict()
```

**Rationale**: This maintains the parameter interface at the public method level and passes through to the private implementation method. Only time dimensions use the parameter; categorical dimensions ignore it.

---

### Step 5: Update SemanticModel.to_lookml_dict() Call Site

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`
**Location**: Line 426-427 (method signature), Line 473-476 (dimension conversion)

**Current Signature** (line 426):
```python
def to_lookml_dict(
    self, schema: str = "", convert_tz: bool | None = None
) -> dict[str, Any]:
```

**Expected After DTL-031**:
```python
def to_lookml_dict(
    self,
    schema: str = "",
    convert_tz: bool | None = None,
    time_dimension_group_label: str | None = None,
) -> dict[str, Any]:
```

**Current Call Site** (lines 473-476):
```python
        # Convert dimensions (separate regular dims from time dims)
        for dim in self.dimensions:
            # Pass convert_tz to time dimensions to propagate generator default
            if dim.type == DimensionType.TIME:
                dim_dict = dim.to_lookml_dict(default_convert_tz=convert_tz)
```

**Updated Call Site**:
```python
        # Convert dimensions (separate regular dims from time dims)
        for dim in self.dimensions:
            # Pass convert_tz and time_dimension_group_label to time dimensions
            if dim.type == DimensionType.TIME:
                dim_dict = dim.to_lookml_dict(
                    default_convert_tz=convert_tz,
                    default_time_dimension_group_label=time_dimension_group_label,
                )
```

**Note**: This step depends on DTL-031 being completed first to add the `time_dimension_group_label` parameter to `SemanticModel.to_lookml_dict()`.

---

### Step 6: Update SemanticModel.to_lookml_dict() Docstring

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`
**Location**: Line 428-438 (docstring)

**Current Docstring**:
```python
    """Convert entire semantic model to lkml views format.

    Args:
        schema: Optional database schema name to prepend to table name.
        convert_tz: Optional timezone conversion setting. Passed to time
            dimensions as default_convert_tz. None means use
            dimension-level defaults.

    Returns:
        Dictionary in LookML views format.
    """
```

**Updated Docstring** (add after convert_tz):
```python
    """Convert entire semantic model to lkml views format.

    Args:
        schema: Optional database schema name to prepend to table name.
        convert_tz: Optional timezone conversion setting. Passed to time
            dimensions as default_convert_tz. None means use
            dimension-level defaults.
        time_dimension_group_label: Optional default group label for time
            dimensions. Passed to time dimensions as
            default_time_dimension_group_label. None means use hardcoded
            default ("Time Dimensions").

    Returns:
        Dictionary in LookML views format.
    """
```

---

## Testing Implementation

### Unit Tests

**File**: `src/tests/unit/test_schemas.py`
**Location**: Add after existing convert_tz tests (after line 1449)

#### Test 1: Default Group Label

```python
def test_dimension_group_default_time_group_label(self) -> None:
    """Test that time dimensions get default time dimension group_label."""
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
def test_dimension_group_generator_parameter_time_group_label(self) -> None:
    """Test that generator parameter overrides default time group_label."""
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
def test_dimension_group_metadata_overrides_generator_time_group_label(self) -> None:
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
def test_dimension_group_disable_time_group_label_with_empty_string_metadata(
    self,
) -> None:
    """Test that empty string in metadata disables time group_label."""
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
def test_dimension_group_disable_time_group_label_with_empty_string_generator(
    self,
) -> None:
    """Test that empty string in generator parameter disables time group_label."""
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
def test_dimension_group_none_uses_default_time_group_label(self) -> None:
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
def test_dimension_group_time_label_precedence_chain(self) -> None:
    """Test full precedence chain: metadata > generator > default."""
    # Case 1: Metadata wins
    dim1 = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(meta=ConfigMeta(time_dimension_group_label="Meta")),
    )
    assert (
        dim1.to_lookml_dict(default_time_dimension_group_label="Gen")["group_label"]
        == "Meta"
    )

    # Case 2: Generator wins (no metadata)
    dim2 = Dimension(
        name="updated_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
    )
    assert (
        dim2.to_lookml_dict(default_time_dimension_group_label="Gen")["group_label"]
        == "Gen"
    )

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
def test_dimension_group_time_label_with_convert_tz(self) -> None:
    """Test that time group_label works alongside convert_tz."""
    # Arrange
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(meta=ConfigMeta(convert_tz=True)),
    )

    # Act
    result = dim.to_lookml_dict(
        default_convert_tz=False, default_time_dimension_group_label="Events"
    )

    # Assert - both parameters applied
    assert result.get("group_label") == "Events"
    assert result.get("convert_tz") == "yes"  # Metadata overrides
```

#### Test 9: Label and Time Group Label Together

```python
def test_dimension_group_label_and_time_group_label(self) -> None:
    """Test that label and time group_label can coexist."""
    # Arrange
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        label="Order Created",  # Sub-category
        config=Config(
            meta=ConfigMeta(time_dimension_group_label="Time Dimensions")
        ),
    )

    # Act
    result = dim.to_lookml_dict()

    # Assert
    assert result.get("label") == "Order Created"
    assert result.get("group_label") == "Time Dimensions"
```

#### Test 10: Special Characters

```python
def test_dimension_group_time_label_special_characters(self) -> None:
    """Test that special characters in time group_label are preserved."""
    # Arrange
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(
            meta=ConfigMeta(time_dimension_group_label="Time/Dates & Events")
        ),
    )

    # Act
    result = dim.to_lookml_dict()

    # Assert
    assert result.get("group_label") == "Time/Dates & Events"
```

#### Test 11: Hierarchy Group Label Takes Precedence

```python
def test_dimension_group_hierarchy_group_label_overrides_time_group_label(
    self,
) -> None:
    """Test that hierarchy-based group_label takes precedence over time group_label."""
    # Arrange - dimension has hierarchy with category
    dim = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(
            meta=ConfigMeta(
                hierarchy={"category": "event_tracking"},
                time_dimension_group_label="Time Dimensions",  # Should be ignored
            )
        ),
    )

    # Act
    result = dim.to_lookml_dict()

    # Assert - hierarchy group_label wins
    assert result.get("group_label") == "Event Tracking"  # From hierarchy
```

---

### Integration Tests

**File**: `src/tests/integration/test_time_dimension_organization.py` (new file)

#### Integration Test 1: Full Flow with Multiple Time Dimensions

```python
"""Integration tests for time dimension organization with group_label."""

from pathlib import Path

import pytest

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser


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
        time_dimension_group_label="Order Times",  # Generator default
    )
    output = generator.generate(models)

    # Assert
    view_content = output["orders.view.lkml"]

    # created_at should use metadata override
    assert 'group_label: "Event Times"' in view_content

    # updated_at should use generator default
    assert 'group_label: "Order Times"' in view_content

    # shipped_at should have NO group_label (explicitly disabled)
    # Verify count: only created_at and updated_at have group_label
    assert view_content.count('group_label:') == 2


def test_time_dimension_group_label_with_hierarchy(tmp_path: Path) -> None:
    """Test that hierarchy group_label takes precedence over time group_label."""
    # Arrange
    yaml_content = """
semantic_model:
  name: events
  model: ref('events')
  entities:
    - name: event_id
      type: primary
  dimensions:
    - name: event_timestamp
      type: time
      type_params:
        time_granularity: hour
      config:
        meta:
          hierarchy:
            category: "event_tracking"
          time_dimension_group_label: "Time Dimensions"  # Should be ignored
  measures:
    - name: event_count
      agg: count
"""

    yaml_file = tmp_path / "events.yaml"
    yaml_file.write_text(yaml_content)

    parser = DbtParser()
    models = parser.parse_directory(str(tmp_path))

    generator = LookMLGenerator(schema="public")
    output = generator.generate(models)

    view_content = output["events.view.lkml"]

    # Hierarchy should win
    assert 'group_label: "Event Tracking"' in view_content
    # Time dimension group label should NOT appear
    assert 'group_label: "Time Dimensions"' not in view_content
```

---

### Golden Test Updates

**Files**:
- `src/tests/golden/expected_rental_orders.view.lkml`
- Other golden test expected files as needed

**Strategy**:
1. Run golden tests after implementation
2. Review generated output for correctness
3. Update expected files if changes are correct and intentional
4. Commit updated golden files with implementation

**Example Update** for `expected_rental_orders.view.lkml`:

**Before** (lines 40-52):
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

**Note**: The exact line order may vary based on how the lkml library serializes dictionaries. The important verification is that `group_label: "Time Dimensions"` appears in the dimension_group block.

---

## Code Quality Validation

### Pre-Commit Checklist

Before committing changes:

- [ ] Run `make test-fast` - unit tests pass
- [ ] Run `make test` - unit + integration tests pass
- [ ] Run `make type-check` - no mypy errors
- [ ] Run `make lint` - no linting issues
- [ ] Run `make format` - code formatted
- [ ] Run `make test-coverage` - maintain 95%+ branch coverage
- [ ] Run `make test-full` - all test suites pass
- [ ] Manual smoke test: Generate LookML with various configurations

### Type Checking Validation

Ensure all type hints are correct:

```bash
uv run mypy src/dbt_to_lookml/schemas/semantic_layer.py --strict
```

Expected output: No errors

### Coverage Target

Branch coverage must remain at 95%+ for:
- `src/dbt_to_lookml/schemas/semantic_layer.py`
- Overall project coverage

Run coverage report:
```bash
make test-coverage
open htmlcov/index.html
```

---

## Edge Cases and Error Handling

### Edge Case 1: Empty String vs. None

**Scenario**: User wants to disable group labeling

**Dimension Level**:
```yaml
dimensions:
  - name: created_at
    type: time
    config:
      meta:
        time_dimension_group_label: ""  # Empty string = disabled
```

**Generator Level**:
```python
generator = LookMLGenerator(
    time_dimension_group_label=""  # Empty string = disabled
)
```

**Expected Behavior**: No `group_label` key in LookML output (backward compatible).

**Implementation**: Falsy check `if time_group_label:` handles empty string.

### Edge Case 2: Null/None Handling

**Scenario**: Parameter not provided (use next level in chain)

**Implementation**: Explicit `is not None` checks ensure `None` falls through to next precedence level.

**Test Coverage**: Test 6 validates this behavior.

### Edge Case 3: Special Characters in Labels

**Scenario**: User provides label with special characters

```yaml
config:
  meta:
    time_dimension_group_label: "Time/Dimensions & Dates"
```

**Handling**: LookML accepts any string in quotes. The `lkml` library handles escaping during serialization.

**Validation**: Test 10 validates special characters are preserved.

### Edge Case 4: Hierarchy Group Label Precedence

**Scenario**: Dimension has both hierarchy-based group_label and time_dimension_group_label

**Expected Behavior**: Hierarchy group_label takes precedence (more specific than time grouping).

**Implementation**: Check `"group_label" not in result` before applying time group_label.

**Test Coverage**: Test 11 validates this behavior.

---

## LookML Output Examples

### Example 1: Default Behavior (Hardcoded Default)

**Input**:
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

**Output** (no group_label):
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

**Looker Field Picker**:
```
Time Dimensions          ← group_label
  Order Created          ← label
    Date                 ← timeframe
    Week
    Month
    Quarter
    Year
```

### Example 6: Hierarchy Group Label Takes Precedence

**Input**:
```yaml
dimensions:
  - name: event_time
    type: time
    type_params:
      time_granularity: hour
    config:
      meta:
        hierarchy:
          category: "event_tracking"
        time_dimension_group_label: "Time Dimensions"
```

**Output** (hierarchy wins):
```lookml
dimension_group: event_time {
  type: time
  timeframes: [time, hour, date, week, month, quarter, year]
  sql: ${TABLE}.event_time ;;
  group_label: "Event Tracking"
  convert_tz: no
}
```

---

## Risk Assessment

### Low Risk

1. **Pattern replication**: Following exact pattern of `convert_tz` implementation reduces risk
2. **Backward compatible**: Default behavior adds new parameter without breaking existing functionality
3. **Well-tested precedence**: Using same precedence pattern that's already proven in production

### Medium Risk

1. **Golden test updates**: Must update expected output files correctly
   - **Mitigation**: Review diffs carefully; run tests multiple times; commit golden files separately
2. **Parameter threading**: Must update multiple function signatures consistently
   - **Mitigation**: Follow type checking; mypy will catch signature mismatches
3. **Hierarchy interaction**: Must ensure hierarchy group_label has precedence
   - **Mitigation**: Explicit test coverage (Test 11); check `"group_label" not in result`

### Edge Cases to Watch

1. **Empty string vs. None**: Ensure explicit `is not None` checks
2. **Falsy values**: Empty string should disable, not error
3. **Interaction with hierarchy**: Hierarchy group_label should take precedence
4. **Parameter order**: Maintain consistent parameter order across signatures

---

## Success Criteria Validation

### Functional Validation

Verify the following manually after implementation:

```bash
# Test 1: Generate with default behavior
uv run python -m dbt_to_lookml generate -i semantic_models/ -o /tmp/test1
# Verify: dimension_groups have group_label: "Time Dimensions"

# Test 2: Generate with custom time_dimension_group_label
uv run python -m dbt_to_lookml generate \
  -i semantic_models/ \
  -o /tmp/test2 \
  --time-dimension-group-label "Event Times"
# Verify: dimension_groups have group_label: "Event Times"

# Test 3: Verify metadata override works
# Create test YAML with metadata override, generate, verify output
```

### Quality Validation

```bash
# Run full quality gate
make quality-gate

# Check coverage specifically
make test-coverage
# Verify: 95%+ branch coverage maintained

# Type check specific file
uv run mypy src/dbt_to_lookml/schemas/semantic_layer.py --strict
# Verify: No errors

# Lint specific file
uv run ruff check src/dbt_to_lookml/schemas/semantic_layer.py
# Verify: No errors
```

---

## Implementation Estimate

### Time Breakdown

- **Code changes**: 1-2 hours
  - Method signature updates: 30 min
  - Precedence logic implementation: 30 min
  - Parameter threading: 30 min
  - Docstring updates: 30 min

- **Testing**: 2-3 hours
  - Unit tests (11 tests): 1.5 hours
  - Integration tests (2 tests): 30 min
  - Golden test updates: 1 hour

- **Validation**: 30 min
  - Run full test suite
  - Manual verification of output
  - Coverage check

**Total Estimated Effort**: 3.5-5.5 hours

---

## Implementation Checklist

### Pre-Implementation

- [ ] Verify DTL-031 is completed (prerequisite)
- [ ] Review strategy document
- [ ] Review existing convert_tz implementation
- [ ] Set up test branch

### Code Changes

- [ ] Update `Dimension._to_dimension_group_dict()` signature
- [ ] Update `Dimension._to_dimension_group_dict()` docstring
- [ ] Implement three-tier precedence logic
- [ ] Add `group_label` to result dictionary (if not disabled)
- [ ] Update `Dimension.to_lookml_dict()` signature
- [ ] Update `Dimension.to_lookml_dict()` docstring
- [ ] Update `Dimension.to_lookml_dict()` implementation
- [ ] Update `SemanticModel.to_lookml_dict()` call site
- [ ] Update `SemanticModel.to_lookml_dict()` docstring

### Testing

- [ ] Implement Test 1: Default group label
- [ ] Implement Test 2: Generator parameter override
- [ ] Implement Test 3: Dimension metadata override
- [ ] Implement Test 4: Empty string disables (metadata)
- [ ] Implement Test 5: Empty string disables (generator)
- [ ] Implement Test 6: None falls through to default
- [ ] Implement Test 7: Precedence chain (all levels)
- [ ] Implement Test 8: Works with convert_tz
- [ ] Implement Test 9: Label and group_label together
- [ ] Implement Test 10: Special characters
- [ ] Implement Test 11: Hierarchy precedence
- [ ] Implement Integration Test 1: Multiple dimensions
- [ ] Implement Integration Test 2: Hierarchy interaction
- [ ] Update golden test expectations
- [ ] Verify all tests pass

### Validation

- [ ] Run `make test-fast` - unit tests pass
- [ ] Run `make test` - integration tests pass
- [ ] Run `make type-check` - no mypy errors
- [ ] Run `make lint` - no ruff errors
- [ ] Run `make format` - code formatted
- [ ] Run `make test-coverage` - 95%+ coverage
- [ ] Run `make test-full` - all suites pass
- [ ] Manual smoke tests with various configs

### Documentation

- [ ] Comprehensive docstrings added
- [ ] Inline comments for precedence logic
- [ ] CLAUDE.md updated (if needed)
- [ ] Spec marked as completed

### Completion

- [ ] All tests passing
- [ ] All quality gates passing
- [ ] Code reviewed (self-review)
- [ ] Commit with descriptive message
- [ ] Issue status updated to Ready
- [ ] Add `state:has-spec` label to issue

---

## Follow-Up Items

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
- **LookMLGenerator.__init__**: `src/dbt_to_lookml/generators/lookml.py:27-155`
- **LookMLGenerator._generate_view_lookml**: `src/dbt_to_lookml/generators/lookml.py:1102-1145`

### Test Locations

- **Unit tests**: `src/tests/unit/test_schemas.py`
- **convert_tz tests**: `src/tests/unit/test_schemas.py:1202-1449`
- **Golden tests**: `src/tests/golden/`
- **Expected output**: `src/tests/golden/expected_rental_orders.view.lkml`

### Documentation

- **CLAUDE.md**: `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md`
- **Epic DTL-029**: `.tasks/epics/DTL-029.md`
- **Issue DTL-032**: `.tasks/issues/DTL-032.md`
- **Strategy DTL-032**: `.tasks/strategies/DTL-032-strategy.md`
- **Prerequisite DTL-031**: `.tasks/issues/DTL-031.md`

---

## Approval

**Status**: Ready for Implementation
**Prerequisite**: DTL-031 completion required
**Next Step**: Begin implementation following this specification

---

**Spec Version**: 1.0
**Last Updated**: 2025-11-19
**Author**: Claude (via /implement:1-spec)
