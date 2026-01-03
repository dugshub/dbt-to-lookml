# dbt-to-lookml v2 Build Log

## Session 1: 2025-01-02 - Foundation & DSI Spike

### What We Built

**Domain Layer** (`domain/`):
- `measure.py` - Measure + AggregationType enum
- `dimension.py` - Dimension + DimensionType enum
- `metric.py` - Metric + MetricVariant + PoP/Benchmark types
- `model.py` - ProcessedModel + Entity
- `README.md` - Future growth path documentation

**Test Suite** (`tests/v2/`):
- `test_domain.py` - 19 passing tests

**Package Structure**:
```
src/dbt_to_lookml_v2/
├── __init__.py
├── BUILD_LOG.md          ← You are here
├── domain/
│   ├── __init__.py
│   ├── README.md
│   ├── measure.py
│   ├── dimension.py
│   ├── metric.py
│   └── model.py
├── ingestion/
│   └── __init__.py       # Phase 2
└── adapters/
    └── lookml/
        └── __init__.py   # Phase 3
```

### Key Decisions Made

1. **Metrics own their variants** - A metric with 7 PoP variants is still ONE metric
2. **Variant names derived from parent** - `gmv_py` = `gmv.name` + `_py` suffix
3. **Simple file structure** - One file per primitive, not nested folders
4. **Pydantic for all schemas** - Ready for future storage layer

### DSI Spike Results

Evaluated `dbt-semantic-interfaces` for YAML parsing:

| Approach | Result |
|----------|--------|
| `parse_yaml_files_to_semantic_manifest()` | ❌ Failed - needs project context |
| `PydanticMetric` instantiation | ✅ Works - preserves config.meta |
| Simple PyYAML | ✅ Works - full control |

**Decision**: Use PyYAML + our own Pydantic models. DSI removed from dependencies.

### Real Semantic Models Discovered

Location: `/Users/doug/Work/data-modelling/official-models/redshift_gold/models/3_semantic/`

- 7 semantic models (rentals, facilities, reviews, etc.)
- 27 metrics total, 18 with PoP enabled
- PoP config in `config.meta.pop`:
  ```yaml
  pop:
    enabled: true
    comparisons: [pp, py]
    windows: [month]
    grains: [mtd, ytd]
  ```

### Phase 1 Complete ✅

**Gate passed**: Domain types compile and instantiate correctly (19 tests)

### Next: Phase 2 - Domain Builder

Build `ingestion/` layer to:
1. Load YAML files from directory
2. Parse into our domain models
3. Expand PoP config → MetricVariants

---

## Session 2: 2026-01-02 - Native Schema & Ingestion Layer

### What We Built

**Native Schema Specification** (`SCHEMA.md`):
- Defined our own schema format - dbt-inspired but first-class concepts
- DataModel: physical table with connection type (redshift, starburst, postgres, duckdb)
- Dimension variants: UTC/local timezone pairs
- Filter syntax: typed conditions with implicit operators
- PoP: first-class config (no more `config.meta.pop` hacks)
- Group: dot-notation hierarchy support

**Enhanced Domain Types**:
- `data_model.py` - DataModel + ConnectionType enum (NEW)
- `filter.py` - Filter + FilterCondition + FilterOperator (NEW)
- `dimension.py` - Added TimeGranularity enum, variants support, primary_variant
- `measure.py` - Added format, group, hidden as first-class fields
- `metric.py` - Simplified structure (measure, expr, metrics vs type_params), PopConfig for expansion
- `model.py` - Added DateSelectorConfig, data_model reference

**Ingestion Layer** (`ingestion/`):
- `loader.py` - YamlLoader: load .yml/.yaml files from directory
- `builder.py` - DomainBuilder: transform YAML → domain objects with variant expansion

**Test Suite**:
- `test_domain.py` - Expanded from 19 to 37 tests covering all new types

### Key Decisions Made

1. **Our own schema, not dbt's** - Building toward a semantic layer authoring system
2. **SQL generation in adapters** - Domain types are pure data, adapters handle dialect differences
3. **Skip `pp` (prior period)** - Only explicit periods (py, pm, pq, pw) for v1
4. **Support multiple group formats** - Dot notation, list, single level all valid
5. **Filters use implicit operators** - Plain value = equals, list = IN, quoted string = parse operator

### Package Structure

```
src/dbt_to_lookml_v2/
├── SCHEMA.md             # Native schema specification
├── BUILD_LOG.md          ← You are here
├── domain/
│   ├── data_model.py     # NEW: DataModel + ConnectionType
│   ├── filter.py         # NEW: Filter + FilterCondition
│   ├── dimension.py      # Updated: variants, granularity
│   ├── measure.py        # Updated: format, group, hidden
│   ├── metric.py         # Updated: PopConfig, simplified params
│   └── model.py          # Updated: DateSelectorConfig
├── ingestion/
│   ├── loader.py         # NEW: YamlLoader
│   └── builder.py        # NEW: DomainBuilder
└── adapters/
    └── lookml/           # Phase 3
```

### Commits (v2-rebuild branch)

```
d5514f9 chore(v2): add DSI spike script and test fixture
89fbf4a feat(v2): add package structure and build log
92547a3 test(v2): add comprehensive domain type tests
bfc2041 feat(v2): add ingestion layer (YAML loader + DomainBuilder)
3f300ba feat(v2): add domain primitives with first-class schema support
8c4a7b2 docs: add native semantic schema specification
fbdf48d docs: add v2 rebuild plan and architecture vision
```

### Phase 2 Complete ✅

**Gate passed**: YAML files → DomainBuilder → ProcessedModel with variants expanded

### Next: Phase 3 - LookML Adapter

Build `adapters/lookml/` to:
1. Render ProcessedModel → .lkml view files
2. Handle PoP variant generation (period_over_period measures)
3. Handle dimension rendering (categorical + dimension_groups)
4. Generate date selector (parameter + dynamic calendar)

---

## Session 3: 2026-01-02 - LookML Adapter (Phase 3)

### What We Built

**Shared Adapter Components** (`adapters/`):
- `dialect.py` - Dialect enum + SqlRenderer with sqlglot integration
  - Supports: redshift, postgres, snowflake, bigquery, duckdb, starburst
  - `D2L_DIALECT` env var for default (redshift)

**LookML Adapter** (`adapters/lookml/`):
- `dimension_renderer.py` - Categorical + time dimension_groups with timezone variants
- `measure_renderer.py` - Measures + metrics (simple, derived, ratio)
- `pop_renderer.py` - PoP with swappable strategy pattern (LookerNativePopStrategy)
- `view_renderer.py` - Compose full views using child renderers
- `generator.py` - Orchestrate file generation

**Output Structure** (split files with refinements):
```
{model}.view.lkml           # Base: dims, entities, sql_table_name
{model}.metrics.view.lkml   # Refinement: +{model} { metric measures }
{model}.pop.view.lkml       # Refinement: +{model} { PoP measures }
```

### Key Decisions Made

1. **Dialect at adapters level** - Shared across LookML, future Cube.js, etc.
2. **Hierarchical renderers** - Generator → ViewRenderer → Dimension/Measure/Pop Renderers
3. **Swappable PoP strategy** - Protocol pattern for future alternative implementations
4. **Split files with refinements** - Clean organization, only generate what's needed

### Package Structure

```
src/dbt_to_lookml_v2/
├── adapters/
│   ├── dialect.py              # Shared dialect + SqlRenderer
│   └── lookml/
│       ├── generator.py        # LookMLGenerator - orchestrator
│       ├── view_renderer.py    # ViewRenderer - composes views
│       ├── dimension_renderer.py
│       ├── measure_renderer.py
│       └── pop_renderer.py     # PopStrategy pattern
```

### Tests

- `test_lookml_adapter.py` - 18 tests for adapter components
- Total v2 tests: 55 passing

### Commits

```
23f579c test(v2): add LookML adapter tests
a8c4fc5 feat(v2): add LookML adapter with split file generation
df01f7d feat(v2): add shared dialect module with sqlglot integration
```

### Phase 3 Complete ✅

**Gate passed**: ProcessedModel → LookML files with dimensions, measures, metrics, and PoP

### Deferred

- Date selector (complex liquid logic)
- Timezone variant toggle parameter
- Explore generation (Phase 4)

---

## Session 4: 2026-01-02 - Explore Generation (Phase 4)

### What We Built

**Domain Types** (`domain/`):
- `explore.py` - ExploreConfig, InferredJoin, JoinRelationship, ExposeLevel enums
- Updated `model.py` - Added `complete: bool` field to Entity for FK completeness

**Explore Adapter** (`adapters/lookml/`):
- `renderers/calendar.py` - CalendarRenderer + DateOption
  - Collects date selector dimensions from all explore participants
  - Generates unified parameter + CASE-based dimension_group
- `renderers/explore.py` - ExploreRenderer
  - Infers joins from entity relationships (foreign → primary matching)
  - Determines expose level (dimensions only vs all) based on `complete` flag
  - Supports join overrides from config
- `explore_generator.py` - ExploreGenerator orchestrator
  - Generates `{explore}.explore.lkml` files
  - Generates `{explore}_explore_calendar.view.lkml` if has date selectors

**Ingestion Updates** (`ingestion/`):
- `builder.py` - Updated to parse `explores:` config and `complete:` on entities
- Returns tuple: `(List[ProcessedModel], List[ExploreConfig])`

### Key Features

1. **Join Inference from Entities**
   - Matches foreign entities to primary entities across models
   - `many_to_one` for FK → PK joins
   - `one_to_many` for child fact detection

2. **Expose Level Safety**
   - `complete: true` on FK → expose dimensions + metrics
   - `complete: false` (default) → expose dimensions only (safe default)
   - Override via `join_overrides` in explore config

3. **Unified Calendar View**
   - One `{explore}_explore_calendar.view.lkml` per explore
   - Single `date_field` parameter with all date options
   - CASE-based `calendar` dimension_group for dynamic switching

### Package Structure

```
src/dbt_to_lookml_v2/
├── domain/
│   ├── explore.py             # NEW: ExploreConfig, InferredJoin, enums
│   └── model.py               # Updated: Entity.complete field
├── ingestion/
│   └── builder.py             # Updated: parse explores + complete
└── adapters/
    └── lookml/
        ├── explore_generator.py         # NEW: orchestrator
        └── renderers/
            ├── calendar.py              # NEW: CalendarRenderer
            └── explore.py               # NEW: ExploreRenderer
```

### Tests

- `test_explore_adapter.py` - 27 tests for explore components
- Total v2 tests: 82 passing

### Phase 4 Complete ✅

**Gate passed**: ExploreConfig → explore files with inferred joins and unified calendar

### Output Example

```lookml
# rentals.explore.lkml
explore: rentals {
  label: "Rentals"

  join: facilities {
    type: left_outer
    relationship: many_to_one
    sql_on: ${rentals.facility_sk} = ${facilities.facility_sk} ;;
  }

  join: reviews {
    type: left_outer
    relationship: one_to_many
    sql_on: ${rentals.rental_sk} = ${reviews.rental_sk} ;;
    # complete: true → all fields exposed
  }

  join: rentals_explore_calendar {
    relationship: one_to_one
    sql:  ;;
  }
}

# rentals_explore_calendar.view.lkml
view: rentals_explore_calendar {
  parameter: date_field {
    type: unquoted
    label: "Analysis Date"
    view_label: " Calendar"
    default_value: "rentals__created_at"
    allowed_values: [
      { label: "Rental Created" value: "rentals__created_at" }
      { label: "Facility Opened" value: "facilities__opened_at" }
    ]
  }

  dimension_group: calendar {
    type: time
    view_label: " Calendar"
    timeframes: [date, week, month, quarter, year]
    convert_tz: no
    sql:
      CASE {% parameter date_field %}
        WHEN 'rentals__created_at' THEN ${rentals.created_at_raw}
        WHEN 'facilities__opened_at' THEN ${facilities.opened_at_raw}
      END
    ;;
  }
}
```

---

## Session 5: 2026-01-03 - Integration Testing & LookML Parity

### What We Built

**Integration Test Fixtures** (`tests/v2/fixtures/integration/`):
- `rentals.yml` - Fact model with date selector, time variants, PoP metrics, filters
- `facilities.yml` - Dimension model with geography, operator hierarchy
- `reviews.yml` - Child fact with `complete: true` (1:1 with rental)

**Integration Tests** (`tests/v2/test_integration.py`):
- 14 end-to-end tests verifying full pipeline
- Loads real-world style YAML → domain models → LookML output
- Validates generated LookML is parseable

### Comparison with Existing LookML

Analyzed production LookML at `analytics_lookML/GoldLayer/` and fixed gaps:

| Issue | Solution | Files |
|-------|----------|-------|
| **Dot notation group** | `group: "Metrics.Revenue"` → `view_label` + `group_label` | `labels.py` (new) |
| **Filter in SQL** | `CASE WHEN filter THEN expr END` embedded in measure | `filter.py` (new), `measure.py` |
| **dimensions_only set** | Generate `set: dimensions_only { fields: [...] }` | `view.py` |
| **Explore from:** | Add `from:` when explore name differs from view | `explore.py` |
| **view_label sorting** | Space prefix `"  Metrics"` for Looker field picker | `labels.py` |

### New Renderers

```
adapters/lookml/renderers/
├── labels.py     # NEW: parse_group_labels(), apply_group_labels()
├── filter.py     # NEW: FilterRenderer.render_case_when()
├── calendar.py   # CalendarRenderer + DateOption
└── explore.py    # ExploreRenderer
```

### Generated Output Now Matches Production Pattern

```lookml
# rentals.view.lkml
view: rentals {
  sql_table_name: gold_production.rentals ;;

  set: dimensions_only {
    fields: [rental, facility, created_at_utc, created_at_local, ...]
  }

  dimension: transaction_type { ... }
}

# rentals.metrics.view.lkml
view: +rentals {
  measure: gov {
    type: sum
    sql: CASE WHEN "${TABLE}".transaction_type = 'completed'
         THEN "${TABLE}".rental_checkout_amount_local END ;;
    view_label: "  Metrics"
    group_label: "Revenue"
    value_format_name: usd
  }
}

# rentals.explore.lkml
explore: rentals {
  label: "Rental Analytics"

  join: facilities {
    relationship: many_to_one
    fields: [facilities.dimensions_only*]
    sql_on: ${rentals.facility_sk} = ${facilities.facility_sk} ;;
  }

  join: reviews {
    relationship: one_to_many
    # complete: true → no field restriction
    sql_on: ${rentals.unique_rental_sk} = ${reviews.unique_rental_sk} ;;
  }
}
```

### Tests

- `test_integration.py` - 14 integration tests
- `test_explore_adapter.py` - 27 explore tests
- **Total v2 tests: 96 passing**

### Key Insights from LookML Comparison

1. **Calendar architecture** - Single calendar view per explore is correct; avoids duplicate "Calendar" sections when multiple views extend a base
2. **Filter embedding** - Baking filters into measure SQL is safer than relying on query-time filters
3. **Set for field restriction** - Explicit `dimensions_only` set gives more control than `dimensions*`
4. **view_label hierarchy** - Two-level grouping (view_label + group_label) essential for Looker UX

### Phase 4+ Complete ✅

**Gate passed**: Integration tests verify parity with production LookML patterns

---

## Session 6: TBD

_Continue with CLI integration, benchmarks, or additional features..._
