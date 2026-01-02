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

## Session 2: TBD

_Continue from Phase 2..._
