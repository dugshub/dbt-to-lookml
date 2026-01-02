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

## Session 3: TBD

_Continue from Phase 3..._
