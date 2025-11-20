---
id: DTL-030-strategy
issue: DTL-030
title: "Research and document LookML field organization patterns - Strategy"
created: 2025-11-19
status: approved
---

# DTL-030: Research and document LookML field organization patterns - Strategy

## Executive Summary

This document provides comprehensive research on LookML's field organization parameters (`group_label`, `label`, `group_item_label`) and their interaction with `dimension_group` for time dimensions. The research will inform the implementation of hierarchical time dimension organization to replace flat field lists in the Looker field picker.

## Problem Analysis

### Current Behavior

The dbt-to-lookml tool currently generates time dimension_groups with minimal labeling:

```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
}

dimension_group: updated_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.updated_at ;;
  convert_tz: no
}
```

This creates a flat field picker structure:
```
Time Dimensions
  Rental Created Date
  Rental Created Week
  Rental Created Month
  Rental Created Quarter
  Rental Created Year
  Rental Updated Date
  Rental Updated Week
  Rental Updated Month
  Rental Updated Quarter
  Rental Updated Year
```

### Desired Behavior

Implement hierarchical organization using LookML parameters:

```
Time Dimensions
  Rental Created
    Date
    Week
    Month
    Quarter
    Year
  Rental Updated
    Date
    Week
    Month
    Quarter
    Year
```

## LookML Field Organization Research

### 1. `group_label` Parameter

**Purpose**: Combines fields into custom groups within a view in the field picker.

**Syntax**:
```lookml
dimension: field_name {
  group_label: "desired label name"
  # ...
}
```

**Key Characteristics**:
- Cannot group dimensions and measures together (they always appear in separate sections)
- Works with both regular dimensions and dimension_groups
- Multiple fields with the same `group_label` are grouped together
- Creates an expandable section in the field picker

**Interaction with `dimension_group`**:
- dimension_group automatically creates a field grouping based on the dimension name
- You can add `group_label` to a dimension_group to place it within a larger category
- Additional fields can be added to the auto-generated group by matching the group_label

**Example**:
```lookml
view: accounts {
  dimension_group: created {
    type: time
    timeframes: [date, week, month]
    sql: ${TABLE}.created_date ;;
    group_label: "Important Dates"
  }

  dimension: special_date_calculation {
    sql: QUARTER(${TABLE}.created_date) ;;
    group_label: "Important Dates"
  }
}
```

This creates:
```
Important Dates
  Created Date
  Created Week
  Created Month
  Special Date Calculation
```

### 2. `label` Parameter

**Purpose**: Provides a human-readable name for the field or dimension_group.

**Syntax**:
```lookml
dimension_group: field_name {
  label: "Human Readable Label"
  # ...
}
```

**Key Characteristics**:
- For dimension_groups, the label becomes the base name for all timeframe fields
- Automatically suffixed with timeframe names (Date, Week, Month, etc.)
- Overrides the default label derived from the field name

**Automatic Label Generation**:
- dimension_group: `created_at` → "Created At Date", "Created At Week", etc.
- With label: "Created" → "Created Date", "Created Week", etc.

**Example**:
```lookml
dimension_group: DateTimeCanceled_ntz {
  label: "Date Canceled (UTC)"
  type: time
  convert_tz: no
  timeframes: [raw, date]
  sql: ${TABLE}."DATETIME_CANCELED" ;;
}
```

Generates:
- "Date Canceled (UTC) Raw"
- "Date Canceled (UTC) Date"

### 3. `group_item_label` Parameter

**Purpose**: Customizes how individual fields appear within a group_label section.

**Syntax**:
```lookml
dimension: field_name {
  group_label: "Group Name"
  group_item_label: "Item Name"
  # ...
}
```

**Key Characteristics**:
- Only displays in the field picker (not in Data section or visualizations)
- Allows removing redundant information from field names within groups
- Useful for simplifying labels when group context is clear

**Important Distinction**:
- `label`: Used everywhere (field picker, Data section, visualizations)
- `group_item_label`: Used only in field picker

**Example**:
```lookml
dimension: GroupField1 {
  group_label: "Group"
  group_item_label: "Field 1"
  label: "Group - Field 1"
  type: string
  sql: ${TABLE}."COLUMN1" ;;
}

dimension: GroupField2 {
  group_label: "Group"
  group_item_label: "Field 2"
  label: "Group - Field 2"
  type: string
  sql: ${TABLE}."COLUMN2" ;;
}
```

Field Picker shows:
```
Group
  Field 1
  Field 2
```

Elsewhere shows: "Group - Field 1", "Group - Field 2"

### 4. Interaction Between Parameters for Time Dimensions

**Current Understanding**: dimension_group creates an automatic field grouping, but this grouping is NOT hierarchical in the field picker by default.

**Key Insight**: The "hierarchical" organization shown in the epic's desired output requires:
1. A common `group_label` across multiple dimension_groups (e.g., "Time Dimensions")
2. Each dimension_group's `label` creates a sub-section
3. Timeframes appear nested under their parent dimension_group's label

**Example Pattern**:
```lookml
dimension_group: created_at {
  label: "Rental Created"
  group_label: "Time Dimensions"
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
}

dimension_group: updated_at {
  label: "Rental Updated"
  group_label: "Time Dimensions"
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.updated_at ;;
  convert_tz: no
}
```

**Expected Field Picker Structure**:
```
Time Dimensions
  Rental Created Date
  Rental Created Week
  Rental Created Month
  Rental Created Quarter
  Rental Created Year
  Rental Updated Date
  Rental Updated Week
  Rental Updated Month
  Rental Updated Quarter
  Rental Updated Year
```

**Note**: This is still a flat list within "Time Dimensions". True hierarchical nesting (dimension_group name as a parent with timeframes as children) may NOT be achievable with standard LookML parameters alone.

**Alternative Investigation Needed**:
- Check if Looker's field picker automatically creates visual hierarchy based on label prefixes
- Investigate if there are undocumented or newer LookML parameters for deeper nesting
- Consider if `view_label` parameter interactions could achieve the desired effect

## Configuration Precedence Design

Following the existing pattern from timezone conversion (convert_tz), the time dimension group_label should support multi-level configuration:

### Precedence Chain (Highest to Lowest)

1. **Dimension Metadata Override** (Highest Priority)
   ```yaml
   dimensions:
     - name: created_at
       type: time
       config:
         meta:
           time_dimension_group_label: "Important Dates"
   ```

2. **Generator Parameter**
   ```python
   generator = LookMLGenerator(
       time_dimension_group_label="Time Dimensions"
   )
   ```

3. **CLI Flag**
   ```bash
   dbt-to-lookml generate -i semantic_models -o build/lookml \
     --time-dimension-group-label "Time Dimensions"
   ```

4. **Default Behavior** (Lowest Priority)
   - No group_label applied to dimension_groups
   - Preserves backward compatibility
   - Users must explicitly enable grouping

### Design Rationale

**Why Default to No Grouping?**
- Backward compatibility: Existing users expect current behavior
- Opt-in philosophy: Advanced organization is an enhancement, not a requirement
- Flexibility: Some users may want different grouping strategies

**Why Support Dimension-Level Override?**
- Fine-grained control for specific time dimensions
- Some time dimensions may belong to different conceptual groups
- Matches existing pattern (convert_tz, hidden, bi_field)

## Current Codebase Patterns

### Existing Configuration Structure

The tool already supports hierarchical labeling through `config.meta.hierarchy`:

```python
class Hierarchy(BaseModel):
    entity: str | None = None
    category: str | None = None
    subcategory: str | None = None

class ConfigMeta(BaseModel):
    hierarchy: Hierarchy | None = None
    convert_tz: bool | None = None
    hidden: bool | None = None
    bi_field: bool | None = None
    # ... other fields
```

### Label Extraction Pattern

Dimensions use `get_dimension_labels()` method:

```python
def get_dimension_labels(self) -> tuple[str | None, str | None]:
    """Get view_label and group_label for dimension based on meta."""
    if self.config and self.config.meta:
        meta = self.config.meta

        # Try flat structure first (meta.subject, meta.category)
        view_label = meta.subject
        group_label = meta.category

        # Fall back to hierarchical structure
        if not view_label and meta.hierarchy:
            view_label = meta.hierarchy.entity
        if not group_label and meta.hierarchy:
            group_label = meta.hierarchy.category

        # Format with proper capitalization
        if view_label:
            view_label = view_label.replace("_", " ").title()
        if group_label:
            group_label = group_label.replace("_", " ").title()

        return view_label, group_label
    return None, None
```

### Current dimension_group Generation

In `semantic_layer.py`, `Dimension._to_dimension_group_dict()`:

```python
def _to_dimension_group_dict(
    self, default_convert_tz: bool | None = None
) -> dict[str, Any]:
    """Convert time dimension to LookML dimension_group."""
    timeframes = self._get_timeframes()

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

    # ... convert_tz logic ...

    return result
```

**Current Issue**: The `group_label` from hierarchy is designed for categorical grouping (e.g., "Booking", "Revenue"), not for time dimension organization.

## Implementation Approach

### Option 1: Extend ConfigMeta with time_dimension_group_label

**Pros**:
- Follows existing pattern (convert_tz, hidden, bi_field)
- Supports dimension-level override
- Clear separation from hierarchy.category

**Cons**:
- Adds another field to ConfigMeta
- Slightly more complex for users

**Schema Change**:
```python
class ConfigMeta(BaseModel):
    # ... existing fields ...
    time_dimension_group_label: str | None = None
```

**Usage**:
```yaml
dimensions:
  - name: created_at
    type: time
    config:
      meta:
        time_dimension_group_label: "Important Dates"
```

### Option 2: Reuse hierarchy.category for time dimensions

**Pros**:
- No schema changes needed
- Leverages existing structure

**Cons**:
- Conflates different concepts (hierarchy vs. time grouping)
- Less intuitive for users
- May cause confusion with measure hierarchy

### Option 3: Add separate time_dimension configuration block

**Pros**:
- Clean separation of concerns
- Could support future time-specific features

**Cons**:
- More verbose
- Breaking change to config structure

### Recommended Approach: Option 1

Extend ConfigMeta with `time_dimension_group_label` for clarity and consistency with existing patterns.

## group_item_label Implementation Strategy

### When to Use group_item_label

**Primary Use Case**: Simplifying timeframe labels when grouped under a common category.

**Example Scenario**:
```lookml
dimension_group: created_at {
  label: "Created"
  group_label: "Time Dimensions"
  group_item_label: "Created"  # Optional
  type: time
  timeframes: [date, week, month]
  sql: ${TABLE}.created_at ;;
}
```

**Field Picker Shows**:
- Without group_item_label: "Created Date", "Created Week", "Created Month"
- With group_item_label: Same as without (dimension_group handles this automatically)

**Note**: group_item_label is typically NOT needed for dimension_groups because the label parameter already controls the timeframe prefix.

### Potential Use Case: Additional Fields in Time Groups

If we want to add custom time-based fields to auto-generated dimension_group sections:

```lookml
dimension_group: created_at {
  label: "Created"
  group_label: "Time Dimensions"
  type: time
  timeframes: [date, week, month]
  sql: ${TABLE}.created_at ;;
}

dimension: created_fiscal_year {
  group_label: "Time Dimensions"
  group_item_label: "Created Fiscal Year"  # Simplifies from full context
  label: "Created - Fiscal Year"  # Full label for visualizations
  type: string
  sql: ... fiscal year calculation ... ;;
}
```

**Recommendation**: Implement group_item_label support as **optional** (DTL-033) after core group_label functionality is stable.

## Test Coverage Requirements

### Unit Tests

1. **Schema Tests** (`test_schemas.py`)
   - ConfigMeta with time_dimension_group_label field
   - Dimension._to_dimension_group_dict() with group_label parameter
   - Label precedence (dimension > generator > CLI > default)

2. **Generator Tests** (`test_lookml_generator.py`)
   - LookMLGenerator initialization with time_dimension_group_label parameter
   - group_label propagation to dimension_groups
   - Multiple dimension_groups with same group_label
   - Mixed time dimensions (some with group_label, some without)

3. **Hierarchy Tests** (`test_hierarchy.py`)
   - Ensure time_dimension_group_label doesn't conflict with hierarchy.category
   - Both can coexist on the same dimension

### Integration Tests

1. **End-to-End Tests** (`test_end_to_end.py`)
   - Parse semantic models with time_dimension_group_label metadata
   - Generate LookML with correct group_label output
   - Verify lkml library correctly parses generated output

2. **Golden Tests** (`test_golden.py`)
   - Update golden files with group_label examples
   - Verify backward compatibility (no group_label when not configured)

### Coverage Targets

- **Per-Module**: 95%+ branch coverage
- **Overall**: Maintain project-wide 95%+ coverage

## Documentation Requirements

### Code Examples

**Before** (Current):
```yaml
dimensions:
  - name: created_at
    type: time
    type_params:
      time_granularity: day
```

```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
}
```

**After** (With group_label):
```yaml
dimensions:
  - name: created_at
    type: time
    type_params:
      time_granularity: day
    config:
      meta:
        time_dimension_group_label: "Time Dimensions"
```

```lookml
dimension_group: created_at {
  label: "Created At"
  group_label: "Time Dimensions"
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
}
```

### Precedence Rules Documentation

Similar to timezone conversion section in CLAUDE.md:

```markdown
### Time Dimension Organization Configuration

LookML dimension_groups support field organization through the `group_label` parameter,
which controls whether time dimensions are grouped together in the field picker.
This feature supports multi-level configuration with a sensible precedence chain.

#### Default Behavior

- **Default**: No group_label applied (backward compatible)
- Time dimensions appear in the standard field picker locations
- Users must explicitly enable grouping if needed

#### Configuration Levels (Precedence: Highest to Lowest)

1. **Dimension Metadata Override** (Highest priority)
2. **Generator Parameter**
3. **CLI Flag**
4. **Default** (Lowest priority)

[... detailed examples ...]
```

## Interaction with Existing Features

### 1. Hierarchy Labels (view_label, group_label)

**Current Behavior**: Dimensions use hierarchy.category → group_label for categorical grouping

**Interaction**: time_dimension_group_label is SEPARATE from hierarchy.category
- hierarchy.category: Used for grouping categorical dimensions (e.g., "Booking Info")
- time_dimension_group_label: Used for grouping time dimension_groups (e.g., "Time Dimensions")

**Example**:
```yaml
dimensions:
  - name: created_at
    type: time
    config:
      meta:
        hierarchy:
          entity: "rental"
          category: "temporal"  # → view_label
        time_dimension_group_label: "Time Dimensions"  # → group_label
```

**LookML Output**:
```lookml
dimension_group: created_at {
  view_label: "Rental"              # from hierarchy.entity
  group_label: "Time Dimensions"     # from time_dimension_group_label
  type: time
  # ...
}
```

### 2. Timezone Conversion (convert_tz)

**No Conflict**: Both parameters can coexist on dimension_groups

**Example**:
```lookml
dimension_group: created_at {
  group_label: "Time Dimensions"
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: yes
}
```

### 3. Field Visibility (hidden, bi_field)

**Interaction**: group_label should be applied BEFORE hidden filtering
- If dimension has `hidden: true`, it won't appear in LookML
- group_label is irrelevant for hidden fields
- bi_field filtering happens at explore join level (not view level)

### 4. Dimension Sets (dimensions_only)

**No Impact**: Sets reference individual timeframe fields, not group_label

## Open Questions & Research Gaps

### 1. True Hierarchical Nesting in Field Picker

**Question**: Can we achieve this structure in Looker's field picker?
```
Time Dimensions
  Created  <-- This level
    Date
    Week
    Month
```

**Current Evidence**:
- LookML group_label creates one level of grouping
- dimension_group's label becomes a prefix, not a nested section
- May require Looker version-specific features or UI behavior

**Investigation Needed**:
- Test generated LookML in actual Looker instance
- Check Looker documentation for field picker rendering rules
- Explore view_label + group_label combinations

### 2. Interaction with view_label

**Question**: Does view_label affect time dimension grouping?

**Current Understanding**:
- view_label moves fields to a different view section in field picker
- Typically used for cross-view organization
- May conflict with group_label grouping

**Test Needed**: Generate LookML with both view_label and group_label on dimension_group

### 3. Looker Version Compatibility

**Question**: Are there version-specific differences in field picker behavior?

**Recommendation**: Document minimum Looker version if field organization has known issues

### 4. Performance with Many Time Dimensions

**Question**: Does heavy use of group_label impact Looker field picker performance?

**Not Critical**: Unlikely to be an issue, but worth noting in documentation

## Implementation Sequence

Following the epic's sub-issue structure:

1. **DTL-030** (This Document): Research and documentation ✓
2. **DTL-031**: Add time_dimension_group_label to schema and CLI
3. **DTL-032**: Implement group_label in dimension_group generation
4. **DTL-033**: Add optional group_item_label support
5. **DTL-034**: Update comprehensive test suite
6. **DTL-035**: Update documentation (CLAUDE.md, README)

## Success Criteria

- [ ] Comprehensive understanding of group_label, label, group_item_label parameters
- [ ] Documented interaction between parameters and dimension_group
- [ ] Clear precedence rules designed (dimension > generator > CLI > default)
- [ ] Examples showing before/after LookML output
- [ ] Integration points with existing features identified
- [ ] Test coverage plan defined (95%+ target)
- [ ] Open questions documented for future investigation

## References

### LookML Documentation
- [group_label (for fields)](https://cloud.google.com/looker/docs/reference/param-field-group-label)
- [group_item_label](https://cloud.google.com/looker/docs/reference/param-field-group-item-label)
- [dimension_group](https://cloud.google.com/looker/docs/reference/param-field-dimension-group)

### Codebase Files
- `/src/dbt_to_lookml/schemas/config.py` - ConfigMeta schema
- `/src/dbt_to_lookml/schemas/semantic_layer.py` - Dimension._to_dimension_group_dict()
- `/src/dbt_to_lookml/generators/lookml.py` - LookMLGenerator
- `/src/tests/unit/test_hierarchy.py` - Existing hierarchy tests

### Related Issues
- Epic DTL-029: Improve Time Dimension Organization in LookML Field Picker
- DTL-031: Add time_dimension_group_label configuration to schemas and CLI
- DTL-032: Implement group_label in dimension_group generation
- DTL-033: Add group_item_label support for cleaner timeframe labels

## Appendix: LookML Examples from Research

### Example 1: Basic dimension_group with group_label
```lookml
view: accounts {
  dimension_group: created {
    label: "Account Created"
    group_label: "Important Dates"
    type: time
    timeframes: [date, week, month]
    sql: ${TABLE}.created_date ;;
  }
}
```

### Example 2: Multiple dimension_groups with same group_label
```lookml
view: rentals {
  dimension_group: created_at {
    label: "Rental Created"
    group_label: "Time Dimensions"
    type: time
    timeframes: [date, week, month, quarter, year]
    sql: ${TABLE}.created_at ;;
    convert_tz: no
  }

  dimension_group: updated_at {
    label: "Rental Updated"
    group_label: "Time Dimensions"
    type: time
    timeframes: [date, week, month, quarter, year]
    sql: ${TABLE}.updated_at ;;
    convert_tz: no
  }
}
```

### Example 3: Adding custom fields to dimension_group section
```lookml
view: orders {
  dimension_group: created {
    label: "Created"
    type: time
    timeframes: [date, week, month]
    sql: ${TABLE}.created_date ;;
  }

  dimension: fiscal_quarter {
    group_label: "Created Date"  # Matches auto-generated group
    group_item_label: "Fiscal Quarter"
    sql: QUARTER(${TABLE}.created_date) ;;
  }
}
```
