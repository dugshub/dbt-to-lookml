# Phase 4: Explore Generation Specification

> **Status**: Ready for Implementation
> **Depends on**: Phase 3 (LookML Adapter) - complete
> **Estimated Scope**: ~400 lines of new code + tests

## Overview

Generate LookML explores from ProcessedModels, including:
- Explore definitions with inferred joins from entity relationships
- Per-explore calendar views for unified date selection
- PoP integration with dynamic calendar references

---

## Quick Reference

### Model Type Decision Tree

```
Does model have an `explores:` config with `fact_model: {this_model}`?
  YES → Fact Model (own explore, own calendar, own PoP)
  NO  → Does model have `complete: true` on a foreign entity?
          YES → Child Fact (joins into parent, uses parent's calendar)
          NO  → Dimension Model (joins anywhere, no PoP)
```

### Output Files

```
output/
├── views/                              # From Phase 3
│   ├── rentals.view.lkml
│   ├── rentals.metrics.view.lkml
│   ├── rentals.pop.view.lkml
│   └── facilities.view.lkml
│
├── explores/                           # NEW in Phase 4
│   ├── rentals.explore.lkml            # Explore definition
│   └── rentals_explore_calendar.view.lkml  # Unified date selector
```

---

## 1. Join Inference from Entities

Joins are **inferred from entity relationships**, not explicitly defined.

### Entity Definitions

```yaml
# rentals.yml - fact model
semantic_models:
  - name: rentals
    entities:
      - name: rental
        type: primary         # this model IS a rental
        expr: unique_rental_sk
      - name: facility
        type: foreign         # this model HAS a facility
        expr: facility_sk

# facilities.yml - dimension model
semantic_models:
  - name: facilities
    entities:
      - name: facility
        type: primary         # this model IS a facility
        expr: facility_sk

# reviews.yml - child fact (complete relationship)
semantic_models:
  - name: reviews
    entities:
      - name: review
        type: primary
        expr: review_id
      - name: rental
        type: foreign
        expr: rental_sk
        complete: true        # every review has a rental, metrics safe

# searches.yml - child (partial relationship)
semantic_models:
  - name: searches
    entities:
      - name: search
        type: primary
        expr: search_id
      - name: rental
        type: foreign
        expr: rental_sk
        # no complete → defaults to false → dims only
```

### Join Inference Rules

1. **Match by entity name**: `rentals.facility` (foreign) → `facilities.facility` (primary)
2. **Relationship type**:
   - Foreign → Primary = `many_to_one`
   - Primary → Foreign = `one_to_many`
3. **Exposure rules** (the `complete` flag):
   - `complete: true` → expose **dimensions + metrics**
   - `complete: false` or absent → expose **dimensions only** (safe default)

### Why `complete` Matters

| Join | complete | Dimensions | Metrics | Why |
|------|----------|------------|---------|-----|
| rentals → reviews | true | Safe | Safe | Every review has exactly one rental |
| rentals → searches | false | Safe | **Unsafe** | Not every search becomes a rental |
| rentals → facilities | (n/a) | Safe | Safe | many_to_one, no fan-out risk |

**Safe by default**: Without `complete: true`, child model metrics are hidden to prevent accidental fan-out.

---

## 2. Model Hierarchy & PoP Calendar Resolution

### Model Types

| Model Type | How to Identify | Has Own Explore? | Calendar | PoP Generation |
|------------|-----------------|------------------|----------|----------------|
| **Fact** | Has `explore` config | Yes | Own: `{fact}_explore_calendar` | Yes, uses own calendar |
| **Child Fact** | Has `complete: true` foreign entity | No (joins into parent) | Uses parent's | Yes, uses parent's calendar |
| **Dimension** | Primary entity, no explore, no `complete: true` | No | N/A | No PoP generated |

### PoP Calendar Resolution Algorithm

```python
def resolve_pop_calendar(model: ProcessedModel, explores: list[ExploreConfig]) -> str | None:
    """Determine which calendar a model's PoP should reference."""

    # 1. Is this model a fact? (has its own explore)
    for explore in explores:
        if explore.fact_model == model.name:
            return f"{explore.name}_explore_calendar.calendar_date"

    # 2. Is this a child fact? (has complete: true entity)
    for entity in model.entities:
        if entity.type == "foreign" and entity.complete:
            # Find parent model (where this entity is primary)
            parent_model = find_model_with_primary_entity(entity.name)
            # Find parent's explore
            parent_explore = find_explore_for_model(parent_model)
            if parent_explore:
                return f"{parent_explore.name}_explore_calendar.calendar_date"

    # 3. Dimension model - no PoP
    return None
```

### Constraint

**One `complete: true` per model**: A child fact can only belong to one parent explore. Multiple `complete: true` entities pointing to different facts is a modeling error.

---

## 3. Explore Configuration

Minimal config - just specify the fact model:

```yaml
explores:
  - name: rentals
    fact_model: rentals
    # joins inferred from foreign entities!
```

Optional: explicit overrides for edge cases:

```yaml
explores:
  - name: rentals
    fact_model: rentals
    label: "Rental Analytics"
    joins:
      - model: reviews
        expose: dimensions    # override: dims only even though complete=true
```

### Generated Explore LookML

```lookml
# rentals.explore.lkml
explore: rentals {
  label: "Rentals"
  description: "Core rental fact model"

  join: facilities {
    type: left_outer
    relationship: many_to_one
    sql_on: ${rentals.facility_sk} = ${facilities.facility_sk} ;;
  }

  join: reviews {
    type: left_outer
    relationship: one_to_many
    sql_on: ${rentals.rental_id} = ${reviews.rental_id} ;;
    # complete: true → all fields exposed
  }

  join: searches {
    type: left_outer
    relationship: one_to_many
    sql_on: ${rentals.rental_id} = ${searches.rental_id} ;;
    fields: [searches.dimensions*]  # complete: false → dims only
  }

  join: rentals_explore_calendar {
    relationship: one_to_one
    sql:  ;;
  }
}
```

---

## 4. Date Selector: Explore Calendar View

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
    view_label: " Calendar"  # space prefix sorts to top

    allowed_value: { label: "Rental Created" value: "rentals__created_at" }
    allowed_value: { label: "Rental Starts" value: "rentals__starts_at" }
    allowed_value: { label: "Facility Opened" value: "facilities__opened_at" }

    default_value: "rentals__created_at"
  }

  dimension_group: calendar {
    type: time
    label: "Calendar"
    description: "Dynamic date based on Analysis Date selection"
    view_label: " Calendar"  # space prefix sorts to top
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

### User Experience in Looker

```
Explore: Rentals
├── Rentals
│   ├── Rental Created Date/Week/Month...
│   └── Rental Starts Date/Week/Month...
├── Facilities
│   └── Facility Opened Date/Week/Month...
└──  Calendar                              ← sorted to top
    ├── Analysis Date [dropdown]           ← ONE parameter
    │     • Rental Created
    │     • Rental Starts
    │     • Facility Opened
    └── Calendar Date/Week/Month/Quarter/Year
```

---

## 5. Domain Types

### Entity Update (modify existing)

```python
# domain/model.py - UPDATE Entity class

@dataclass
class Entity:
    name: str
    type: str                     # "primary", "foreign", "unique"
    expr: str
    label: str | None = None
    complete: bool = False        # NEW: for foreign keys, True = metrics safe
```

### New Explore Types

```python
# domain/explore.py - NEW FILE

from dataclasses import dataclass, field
from enum import Enum

class JoinRelationship(str, Enum):
    MANY_TO_ONE = "many_to_one"
    ONE_TO_MANY = "one_to_many"
    ONE_TO_ONE = "one_to_one"

class JoinType(str, Enum):
    LEFT_OUTER = "left_outer"
    INNER = "inner"
    FULL_OUTER = "full_outer"

class ExposeLevel(str, Enum):
    ALL = "all"                   # dimensions + metrics
    DIMENSIONS = "dimensions"     # dimensions only

@dataclass
class JoinOverride:
    """Optional overrides for inferred joins."""
    model: str
    expose: ExposeLevel | None = None

@dataclass
class ExploreConfig:
    """Explore configuration from YAML."""
    name: str
    fact_model: str
    label: str | None = None
    description: str | None = None
    join_overrides: list[JoinOverride] = field(default_factory=list)

@dataclass
class InferredJoin:
    """Join inferred from entity relationships."""
    model: str
    entity: str                   # entity name used for join
    relationship: JoinRelationship
    expose: ExposeLevel
    sql_on: str                   # generated sql_on clause
```

---

## 6. Implementation Components

### New Files

```
src/dbt_to_lookml_v2/
├── domain/
│   └── explore.py              # NEW: ExploreConfig, InferredJoin, enums
├── adapters/
│   └── lookml/
│       ├── explore_renderer.py     # NEW: Explore LookML generation
│       ├── calendar_renderer.py    # NEW: Calendar view generation
│       └── explore_generator.py    # NEW: Orchestrator
└── ingestion/
    └── builder.py              # UPDATE: parse explores from YAML
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

    def render(self, explore_name: str, date_options: list[DateOption]) -> dict[str, Any]:
        """Render calendar view dict for lkml serialization."""
        ...

    def collect_date_options(
        self,
        fact_model: ProcessedModel,
        joined_models: list[ProcessedModel],
    ) -> list[DateOption]:
        """Collect date options from all models in explore."""
        ...
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

    def infer_joins(
        self,
        fact_model: ProcessedModel,
        all_models: dict[str, ProcessedModel],
    ) -> list[InferredJoin]:
        """Infer joins from entity relationships."""
        ...
```

### ExploreGenerator (orchestrator)

```python
class ExploreGenerator:
    """Generate explore files from configuration."""

    def __init__(self, dialect: Dialect | None = None):
        self.calendar_renderer = CalendarRenderer()
        self.explore_renderer = ExploreRenderer(self.calendar_renderer)

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

## 7. Edge Cases

| Case | Behavior |
|------|----------|
| No date_selector on any model | Skip calendar view generation |
| Fact-only explore (no joins) | Generate calendar with just fact's dates |
| Duplicate dimension names | Qualify with view: `rentals__created_at` |
| Circular entity references | Not supported, error |
| Multi-hop joins (A→B→C) | Deferred to future version |

---

## 8. Test Cases

```python
# tests/v2/test_explore_adapter.py

class TestExploreRenderer:
    def test_single_model_explore(self): ...
    def test_multi_join_explore(self): ...
    def test_many_to_one_relationship(self): ...
    def test_one_to_many_relationship(self): ...
    def test_complete_true_exposes_metrics(self): ...
    def test_complete_false_dims_only(self): ...
    def test_join_override(self): ...

class TestCalendarRenderer:
    def test_collect_date_options(self): ...
    def test_render_calendar_view(self): ...
    def test_no_date_selector_returns_none(self): ...
    def test_duplicate_dim_names_qualified(self): ...
    def test_case_statement_generation(self): ...

class TestExploreGenerator:
    def test_generate_explore_and_calendar(self): ...
    def test_skip_calendar_when_no_dates(self): ...
```

---

## 9. Deliverables Checklist

- [ ] `domain/explore.py` - ExploreConfig, InferredJoin, enums
- [ ] `domain/model.py` - Add `complete` to Entity
- [ ] `ingestion/builder.py` - Parse `explores:` from YAML
- [ ] `adapters/lookml/calendar_renderer.py` - Calendar view generation
- [ ] `adapters/lookml/explore_renderer.py` - Explore LookML rendering
- [ ] `adapters/lookml/explore_generator.py` - Orchestrator
- [ ] `tests/v2/test_explore_adapter.py` - Test coverage
- [ ] Update `BUILD_LOG.md` with session notes

---

## 10. Implementation Notes for Next Agent

### Start Here

1. **Read existing code first**:
   - `domain/model.py` - understand Entity, ProcessedModel structure
   - `adapters/lookml/view_renderer.py` - pattern for renderers
   - `adapters/lookml/generator.py` - pattern for generator orchestration
   - `ingestion/builder.py` - how YAML is parsed into domain objects

2. **Implementation order**:
   1. Add `complete: bool = False` to Entity in `domain/model.py`
   2. Create `domain/explore.py` with new types
   3. Update `ingestion/builder.py` to parse `explores:` config
   4. Build `CalendarRenderer` first (simpler, standalone)
   5. Build `ExploreRenderer` (uses CalendarRenderer)
   6. Build `ExploreGenerator` orchestrator
   7. Add tests throughout

3. **Key patterns to follow**:
   - Renderers return `dict[str, Any]` for lkml serialization
   - Generators return `dict[str, str]` (filename → content)
   - Use `lkml.dump()` for serialization (see `generator.py`)

### Gotchas

- **`view_label: " Calendar"`** - the space prefix is intentional (sorts to top)
- **`sql:  ;;`** in calendar join - empty SQL is valid for virtual views
- **`fields: [view.dimensions*]`** - Looker syntax for field restriction
- **Parameter values use `__`** not `.` - e.g., `rentals__created_at` (LookML-safe)

### Testing Tips

- Use existing fixtures in `tests/v2/` as examples
- Test renderers return correct dict structure
- Test generator produces valid LookML (can parse with `lkml.load()`)
- Test edge cases: no dates, no joins, duplicate names

---

## Resolved Questions

1. ~~**Explore definition source**~~ → Inferred from entities, minimal explicit config
2. ~~**PoP integration**~~ → Uses `{explore}_explore_calendar.calendar_date`. Liquid is processed.
3. ~~**View labels**~~ → `" Calendar"` (space prefix for sort)
4. ~~**Join depth**~~ → Single-hop only for v1

---

## Future: Sets & Drill Fields

**Not in Phase 4 scope.** See end of this file for design notes on:
- Group-based sets (infer from `group` field)
- Explicit set membership (`sets: [detail, drill_core]`)
- Cross-view drill fields
