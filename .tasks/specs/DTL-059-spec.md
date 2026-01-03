---
id: DTL-059-spec
issue: DTL-059
title: "Implementation Spec: Always generate calendar dimension_group"
type: spec
status: Ready
created: 2025-12-23
stack: backend
---

# Implementation Spec: Always generate calendar dimension_group

## Metadata
- **Issue**: `DTL-059`
- **Stack**: `backend`
- **Type**: `feature`
- **Generated**: 2025-12-23
- **Related**: DTL-056 (PoP will use `calendar_date` for `based_on_time`)

## Issue Context

### Problem Statement

The `calendar` dimension_group is only generated when `--date-selector` is enabled. This creates inconsistency and forces conditional logic in features that want to reference a standard date dimension.

### Solution Approach

Always generate `calendar` dimension_group for models with `agg_time_dimension`:
- **Dynamic mode** (date_selector enabled): Parameter-based, user selects field
- **Static mode** (date_selector not enabled): Alias to `agg_time_dimension`

### Success Criteria

- [ ] `calendar` dimension_group generated for all models with `agg_time_dimension`
- [ ] Static mode references `${agg_time_dim_date}`
- [ ] Static mode description shows underlying field name
- [ ] Dynamic mode unchanged
- [ ] Unit tests for both modes

## Implementation Plan

### Phase 1: Add Static Calendar Method

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Add after `_generate_calendar_dimension_group`** (around line 732):

```python
def _generate_static_calendar_dimension_group(
    self, agg_time_dim: str
) -> dict[str, Any]:
    """Generate static calendar dimension_group as alias to agg_time_dimension.

    Used when date_selector is not enabled to provide a consistent
    calendar_date reference across all models.

    Args:
        agg_time_dim: Name of the model's default agg_time_dimension

    Returns:
        LookML dimension_group dict
    """
    return {
        "name": "calendar",
        "type": "time",
        "timeframes": ["date", "week", "month", "quarter", "year"],
        "sql": f"${{{agg_time_dim}_date}}",
        "label": "Calendar",
        "description": f"Calendar date dimension (based on {agg_time_dim})",
        "view_label": VIEW_LABEL_DATE_DIMENSIONS,
        "convert_tz": "no",
    }
```

### Phase 2: Update View Generation

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Location**: In `_generate_view_lookml` or `generate` method, where dimension_groups are assembled

**Logic**:
```python
# Determine calendar dimension_group mode
if self.date_selector and model_is_fact:
    # Dynamic mode - parameter-based (existing behavior)
    calendar_dim_group = self._generate_calendar_dimension_group()
elif model.defaults and model.defaults.get("agg_time_dimension"):
    # Static mode - alias to agg_time_dimension
    calendar_dim_group = self._generate_static_calendar_dimension_group(
        model.defaults["agg_time_dimension"]
    )
else:
    calendar_dim_group = None

if calendar_dim_group:
    dimension_groups.append(calendar_dim_group)
```

### Phase 3: Avoid Duplicate Calendar

Ensure we don't generate duplicate `calendar` dimension_groups:
- Check if `calendar` already exists before adding
- Or refactor to single location for calendar generation

```python
# Check if calendar already exists
existing_names = {dg.get("name") for dg in dimension_groups}
if "calendar" not in existing_names and calendar_dim_group:
    dimension_groups.append(calendar_dim_group)
```

## File Changes

### Files to Modify

#### `src/dbt_to_lookml/generators/lookml.py`

**Changes**:
1. Add `_generate_static_calendar_dimension_group` method
2. Update dimension_group generation to include static calendar when appropriate
3. Add deduplication logic to prevent duplicate calendar

**Estimated lines**: +30 new, ~10 modified

## Testing Strategy

### Unit Tests

**File**: `src/tests/unit/test_calendar_dimension.py` (new)

```python
"""Tests for calendar dimension_group generation."""

import pytest
from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.schemas.semantic_layer import Entity, SemanticModel


class TestCalendarDimensionGroup:
    """Tests for calendar dimension_group generation."""

    def test_static_calendar_generated_without_date_selector(self) -> None:
        """Static calendar generated when date_selector not enabled."""
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "rental_date"},
            entities=[Entity(name="rental", type="primary")],
        )

        generator = LookMLGenerator(date_selector=False)
        files = generator.generate([model])

        view_content = files.get("rentals.view.lkml", "")
        assert "dimension_group: calendar" in view_content
        assert "${rental_date_date}" in view_content
        assert "based on rental_date" in view_content

    def test_dynamic_calendar_generated_with_date_selector(self) -> None:
        """Dynamic calendar generated when date_selector enabled."""
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "rental_date"},
            entities=[Entity(name="rental", type="primary")],
        )

        generator = LookMLGenerator(date_selector=True, fact_models=["rentals"])
        files = generator.generate([model])

        view_content = files.get("rentals.view.lkml", "")
        assert "dimension_group: calendar" in view_content
        assert "calendar_date_param" in view_content
        assert "Dynamic calendar" in view_content

    def test_no_calendar_without_agg_time_dimension(self) -> None:
        """No calendar generated if model lacks agg_time_dimension."""
        model = SemanticModel(
            name="users",
            model="ref('users')",
            # No defaults/agg_time_dimension
            entities=[Entity(name="user", type="primary")],
        )

        generator = LookMLGenerator(date_selector=False)
        files = generator.generate([model])

        view_content = files.get("users.view.lkml", "")
        assert "dimension_group: calendar" not in view_content

    def test_static_calendar_description_includes_field_name(self) -> None:
        """Static calendar description shows underlying field."""
        generator = LookMLGenerator()
        calendar = generator._generate_static_calendar_dimension_group("order_date")

        assert calendar["name"] == "calendar"
        assert "order_date" in calendar["description"]
        assert calendar["sql"] == "${order_date_date}"
```

### Run Tests

```bash
python -m pytest src/tests/unit/test_calendar_dimension.py -v
```

## Dependencies

### Related Issues

- **Used by**: DTL-056 (PoP `based_on_time: calendar_date`)

## Implementation Notes

### Key Points

1. **Backwards compatible**: Dynamic mode behavior unchanged for fact models
2. **Graceful fallback**: No calendar if no `agg_time_dimension`
3. **Self-documenting**: Static mode description explains what it references
4. **Joined models**: Get static calendar referencing their own `agg_time_dimension`

### Design Decision: Static vs Dynamic for Joined Models

Joined models (e.g., `reviews` joined to `rentals` fact) get **static calendar** referencing their own `agg_time_dimension`. This is simpler than trying to propagate the fact model's parameter.

**Rationale**:
- At generation time, we don't know which explores a model will be joined into
- Cross-view parameter references (`{% parameter other_view.param %}`) add complexity
- In practice, joined models' dates often align with the fact model's date anyway

**Future enhancement**: Could add cross-view parameter referencing where joined views reference the fact model's `calendar_date_param` for truly unified date selection across an explore.

### Generated LookML Examples

**Static mode**:
```lookml
dimension_group: calendar {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${rental_date_date} ;;
  label: "Calendar"
  description: "Calendar date dimension (based on rental_date)"
  view_label: " Date Dimensions"
  convert_tz: no
}
```

**Dynamic mode** (unchanged):
```lookml
dimension_group: calendar {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.{% parameter calendar_date_param %}::timestamp ;;
  label: "Calendar"
  description: "Dynamic calendar based on selected date field"
  view_label: " Date Dimensions"
  convert_tz: no
}
```

## Ready for Implementation

**Implementation Steps**:
1. Add `_generate_static_calendar_dimension_group` method
2. Update view generation to include static calendar when `agg_time_dimension` exists
3. Add deduplication check for calendar dimension_group
4. Add unit tests
5. Run full test suite

**Estimated Effort**: 45 minutes
- New method: 10 minutes
- Integration into view generation: 15 minutes
- Tests: 15 minutes
- Verification: 5 minutes

**Success Criteria**:
- [ ] Static calendar generated for models with `agg_time_dimension`
- [ ] Dynamic calendar still works when date_selector enabled
- [ ] No duplicate calendar dimension_groups
- [ ] Description shows underlying field name in static mode
- [ ] All tests pass
