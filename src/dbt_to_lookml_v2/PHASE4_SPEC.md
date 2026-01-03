# Phase 4: Explore Generation Specification

> **Status**: Draft
> **Depends on**: Phase 3 (LookML Adapter) complete

## Overview

Generate LookML explores from ProcessedModels, including:
- Explore definitions with joins
- Per-explore calendar views for unified date selection
- Relationship handling (many_to_one, one_to_many)

---

## Output Structure

```
output/
├── views/
│   ├── rentals.view.lkml
│   ├── rentals.metrics.view.lkml
│   ├── rentals.pop.view.lkml
│   ├── facilities.view.lkml
│   └── reviews.view.lkml
│
├── explores/
│   ├── rentals.explore.lkml
│   ├── rentals_explore_calendar.view.lkml    ← unified date selector
│   └── ...
```

---

## Explore Configuration

### Input: Explore Definition

Explores can be defined explicitly or inferred from entity relationships:

```yaml
# Option A: Explicit explore definition
explores:
  - name: rentals
    fact_model: rentals
    joins:
      - model: facilities
        relationship: many_to_one
        on: facility  # entity name
      - model: reviews
        relationship: one_to_many
        on: rental

# Option B: Inferred from entities (future)
# - Primary entity in fact model
# - Foreign entities auto-join to their primary models
```

### Output: Explore LookML

```lookml
# rentals.explore.lkml
explore: rentals {
  label: "Rentals"
  description: "Core rental fact model"

  join: facilities {
    type: left_outer
    relationship: many_to_one
    sql_on: ${rentals.facility_id} = ${facilities.facility_id} ;;
  }

  join: reviews {
    type: left_outer
    relationship: one_to_many
    sql_on: ${rentals.rental_id} = ${reviews.rental_id} ;;
  }

  join: rentals_explore_calendar {
    relationship: one_to_one
    sql:  ;;
  }
}
```

---

## Date Selector: Explore Calendar View

### Problem

When date selectors exist per-view, joined explores show duplicate parameters.

### Solution

Generate ONE `{explore_name}_explore_calendar.view.lkml` per explore containing:
1. Single `date_field` parameter with all date options from all joined views
2. CASE-based `calendar` dimension_group routing to the correct view

### Collection Algorithm

```python
def collect_date_options(
    fact_model: ProcessedModel,
    joined_models: list[ProcessedModel],
) -> list[DateOption]:
    """Collect date selector dimensions from all explore participants."""
    options = []

    for model in [fact_model] + joined_models:
        if not model.date_selector:
            continue

        for dim_name in model.date_selector.dimensions:
            dim = model.get_dimension(dim_name)
            if dim:
                options.append(DateOption(
                    view=model.name,
                    dimension=dim_name,
                    label=dim.label or _smart_title(dim_name),
                    raw_ref=f"${{{model.name}.{dim_name}_raw}}",
                ))

    return options
```

### Generated Calendar View

```lookml
# rentals_explore_calendar.view.lkml
view: rentals_explore_calendar {
  # No sql_table_name - virtual view

  parameter: date_field {
    type: unquoted
    label: "Analysis Date"
    description: "Select which date field to use for calendar analysis"
    view_label: "Calendar"

    allowed_value: { label: "Rental Created" value: "rentals__created_at" }
    allowed_value: { label: "Rental Starts" value: "rentals__starts_at" }
    allowed_value: { label: "Facility Opened" value: "facilities__opened_at" }

    default_value: "rentals__created_at"
  }

  dimension_group: calendar {
    type: time
    label: "Calendar"
    description: "Dynamic date based on Analysis Date selection"
    view_label: "Calendar"
    timeframes: [date, week, month, quarter, year]
    convert_tz: no
    sql:
      CASE {% parameter date_field %}
        WHEN 'rentals__created_at' THEN ${rentals.created_at_raw}
        WHEN 'rentals__starts_at' THEN ${rentals.starts_at_raw}
        WHEN 'facilities__opened_at' THEN ${facilities.opened_at_raw}
      END
    ;;
  }
}
```

### User Experience

```
Explore: Rentals
├── Rentals
│   ├── Rental Created Date/Week/Month...    ← individual dimensions
│   └── Rental Starts Date/Week/Month...
├── Facilities
│   └── Facility Opened Date/Week/Month...
└── Calendar                                   ← unified selector
    ├── Analysis Date [dropdown]               ← ONE parameter
    │     • Rental Created
    │     • Rental Starts
    │     • Facility Opened
    └── Calendar Date/Week/Month/Quarter/Year  ← dynamic dimension
```

---

## Implementation Components

### New Files

```
src/dbt_to_lookml_v2/
├── adapters/
│   └── lookml/
│       ├── explore_renderer.py      # NEW: Explore LookML generation
│       └── calendar_renderer.py     # NEW: Explore calendar view generation
```

### ExploreRenderer

```python
class ExploreRenderer:
    """Render explore definitions to LookML."""

    def __init__(self, calendar_renderer: CalendarRenderer):
        self.calendar_renderer = calendar_renderer

    def render(
        self,
        explore_config: ExploreConfig,
        fact_model: ProcessedModel,
        joined_models: dict[str, ProcessedModel],
    ) -> dict[str, Any]:
        """Render explore dict for lkml serialization."""
        ...

    def render_joins(
        self,
        joins: list[JoinConfig],
        models: dict[str, ProcessedModel],
    ) -> list[dict[str, Any]]:
        """Render join clauses."""
        ...
```

### CalendarRenderer

```python
@dataclass
class DateOption:
    view: str           # "rentals"
    dimension: str      # "created_at"
    label: str          # "Rental Created"
    raw_ref: str        # "${rentals.created_at_raw}"

class CalendarRenderer:
    """Render explore-level calendar views."""

    def render(
        self,
        explore_name: str,
        date_options: list[DateOption],
    ) -> dict[str, Any]:
        """Render calendar view dict."""
        ...

    def collect_date_options(
        self,
        fact_model: ProcessedModel,
        joined_models: list[ProcessedModel],
    ) -> list[DateOption]:
        """Collect date options from all models."""
        ...
```

### ExploreGenerator (orchestrator)

```python
class ExploreGenerator:
    """Generate explore files from configuration."""

    def generate(
        self,
        explores: list[ExploreConfig],
        models: dict[str, ProcessedModel],
    ) -> dict[str, str]:
        """
        Generate all explore files.

        Returns:
            Dict of {filename: content}
            - {explore}.explore.lkml
            - {explore}_explore_calendar.view.lkml (if has date options)
        """
        ...
```

---

## Domain Types (additions)

```python
# domain/explore.py (NEW)

@dataclass
class JoinConfig:
    model: str                    # "facilities"
    relationship: JoinRelationship  # many_to_one, one_to_many, one_to_one
    on_entity: str                # "facility" - entity name for join condition
    type: JoinType = JoinType.LEFT_OUTER

@dataclass
class ExploreConfig:
    name: str
    fact_model: str
    label: str | None = None
    description: str | None = None
    joins: list[JoinConfig] = field(default_factory=list)

class JoinRelationship(str, Enum):
    MANY_TO_ONE = "many_to_one"
    ONE_TO_MANY = "one_to_many"
    ONE_TO_ONE = "one_to_one"

class JoinType(str, Enum):
    LEFT_OUTER = "left_outer"
    INNER = "inner"
    FULL_OUTER = "full_outer"
```

---

## Edge Cases

### No Date Selector Dimensions

If no models in the explore have `date_selector` config, skip calendar view generation entirely.

### Empty Joins

Explore with just a fact model (no joins):
- Still generates calendar view if fact model has date_selector
- Calendar view only contains fact model's date options

### Duplicate Dimension Names

If `rentals.created_at` and `facilities.created_at` both exist:
- Parameter values use qualified names: `rentals__created_at`, `facilities__created_at`
- Labels should differentiate: "Rental Created", "Facility Created"

### Circular References

Not supported in v1. Explores are hierarchical (fact → dimensions).

---

## Test Cases

1. **Single model explore** - fact only, no joins
2. **Multi-join explore** - fact + 2-3 dimension models
3. **Calendar generation** - correct parameter options and CASE statement
4. **No date selector** - calendar view not generated
5. **Duplicate dimension names** - properly qualified
6. **Join relationship types** - many_to_one, one_to_many rendered correctly

---

## Phase 4 Deliverables

1. `domain/explore.py` - ExploreConfig, JoinConfig types
2. `adapters/lookml/explore_renderer.py` - Explore LookML rendering
3. `adapters/lookml/calendar_renderer.py` - Calendar view rendering
4. `adapters/lookml/explore_generator.py` - Orchestrator
5. `tests/v2/test_explore_adapter.py` - Test coverage
6. Update `BUILD_LOG.md` with session notes

---

## Open Questions

1. **Explore definition source**: Explicit YAML config vs. inferred from entities?
2. **PoP integration**: Does `based_on_time` use `calendar` dimension when date selector enabled?
3. **View labels**: Should calendar dimensions have `view_label: "Calendar"` or explore name?
