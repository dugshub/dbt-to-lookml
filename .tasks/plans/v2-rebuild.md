# dbt-to-lookml v2: Rebuild Plan

## Status: Phase 1 ✅ COMPLETE | Phase 2 Next
Last Updated: 2025-01-02

---

## Why This Rebuild

### The Problem
The current architecture mixes concerns in a 2,684-line monolithic generator:
- Parser outputs dbt's structure directly (not our domain)
- All logic (PoP eligibility, date selector, joins) lives in LookMLGenerator
- No intermediate domain model - we go straight from "dbt's shape" to "LookML syntax"

### The Pain We're Experiencing
1. **Derived metric PoP doesn't work** - generator silently skips them
2. **Manual drift** - GoldLayer LookML has evolved beyond what d2l can generate
3. **Can't reason about what exists** - no clear answer to "what metrics do we have?"
4. **Adding features is painful** - every new capability requires threading through the monolith

### The Architectural Insight
**The domain model should know what it IS. Adapters should know how to RENDER it.**

```
YAML → PyYAML → DomainBuilder → ProcessedModel → LookMLAdapter → .lkml
                     │
                     └── Metrics own their variants (PoP, benchmarks)
                         Domain is fully expanded before rendering
                         Adapter is pure mapping, no conditionals
```

### What Success Looks Like
- **10 metrics with 70 variants**, not 70 metrics
- Regenerate GoldLayer LookML from semantic models
- Add PoP/benchmarks by defining in YAML, not writing LookML
- Clear separation: YAML loads, DomainBuilder expands, Adapter renders

---

## Locked Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Build Location | `src/dbt_to_lookml_v2/` | Keep old code as reference, same tooling |
| Ingestion | PyYAML + our Pydantic models | DSI too opinionated (see spike results below) |
| Core Primitives | Measure, Dimension, Metric | Match dbt concepts, with types within |
| Variants | Owned by Metric, not separate entities | "10 metrics" not "70 measures" |
| Expansion | Domain layer expands configs → concrete variants | Adapter is pure mapping |
| Architecture | Ingestion → Domain → Adapters | Clean separation |

---

## DSI Spike Results (2025-01-02)

**Goal**: Evaluate dbt-semantic-interfaces for YAML parsing.

### What We Tested
1. `parse_yaml_files_to_semantic_manifest()` - DSI's built-in parser
2. `PydanticMetric` direct instantiation from YAML
3. Simple PyYAML loading

### Results

| Approach | Result | Notes |
|----------|--------|-------|
| DSI parser | ❌ FAILED | Expects project config, complains about `version` key |
| DSI PydanticMetric | ✅ Works | Can instantiate from YAML dict, preserves `config.meta` |
| PyYAML | ✅ Works | Simple, no dependencies, full control |

**DSI Parser Error:**
```
ParsingException: Did not find exactly one project configuration
ValidationError: Document should have one type of key, but has dict_keys(['version', 'metrics'])
```

**DSI PydanticMetric Success:**
```python
metric = PydanticMetric(**yaml_dict)
# Config: meta={'pop': {'enabled': True, 'comparisons': ['pp', 'py'], ...}}
```

### Decision: Use PyYAML + Our Own Models

**Reasons:**
1. DSI parser is too opinionated (needs full dbt project context)
2. Simple YAML loading works perfectly
3. Our Pydantic models give us full control
4. Fewer dependencies
5. `config.meta.pop` structure preserved either way

**Removed dependency:** `dbt-semantic-interfaces`

---

## Project Structure

```
src/dbt_to_lookml_v2/
├── __init__.py
├── domain/
│   ├── __init__.py          # Re-exports all
│   ├── README.md            # Future growth path
│   ├── measure.py           # Measure + AggregationType
│   ├── dimension.py         # Dimension + DimensionType
│   ├── metric.py            # Metric + MetricVariant + types
│   └── model.py             # ProcessedModel, Entity
├── ingestion/
│   └── __init__.py          # Phase 2: YAML loader + DomainBuilder
└── adapters/
    └── lookml/
        └── __init__.py      # Phase 3: LookML adapter

tests/
├── fixtures/v2_semantic_models/
│   └── rentals_with_metrics.yml
└── v2/
    └── test_domain.py       # 19 tests passing
```

---

## Phases

### Phase 1: Foundation ✅ COMPLETE
**Goal**: Define domain primitives, validate approach
**Gate**: Domain types compile and instantiate correctly

- [x] Create `src/dbt_to_lookml_v2/` package structure
- [x] Define: `domain/measure.py` - Measure + AggregationType
- [x] Define: `domain/dimension.py` - Dimension + DimensionType
- [x] Define: `domain/metric.py` - Metric + MetricVariant + types
- [x] Define: `domain/model.py` - ProcessedModel, Entity
- [x] Test: 19 tests passing
- [x] Spike: DSI vs PyYAML → **Decision: PyYAML**

### Phase 2: Domain Builder ← NEXT
**Goal**: Transform YAML → Our domain model with expanded variants
**Gate**: Given YAML files, output ProcessedModel with PoP variants expanded

- [ ] `ingestion/loader.py` - Load YAML files from directory
- [ ] `ingestion/builder.py` - DomainBuilder class
- [ ] Parse semantic models → Measure, Dimension, Entity
- [ ] Parse metrics → Metric with type resolution
- [ ] PoP config parsing from `config.meta.pop`
- [ ] PoP expansion: config → concrete MetricVariants
- [ ] Test: Load real semantic models, verify variant expansion

**Validation**:
```python
from dbt_to_lookml_v2.ingestion import DomainBuilder

model = DomainBuilder.from_directory("/path/to/semantic_models/")
gmv = model.get_metric("gmv")
assert gmv.type == MetricType.SIMPLE
assert len(gmv.variants) == 7  # base + 6 PoP variants
```

### Phase 3: LookML Adapter
**Goal**: Render domain model to .lkml matching GoldLayer patterns
**Gate**: Generated LookML matches gold_rentals.view.lkml structure

- [ ] Base measure rendering (by metric type)
- [ ] Variant rendering (PoP → period_over_period measures)
- [ ] Dimension rendering (categorical + dimension_groups)
- [ ] Date selector (parameter + dynamic calendar)
- [ ] dimensions_only set generation
- [ ] Test: Output matches expected LookML patterns

### Phase 4: Explores & Integration
**Goal**: End-to-end working CLI
**Gate**: `d2l generate` produces valid LookML from semantic models

- [ ] Explore generation with joins
- [ ] CLI wiring
- [ ] File output structure
- [ ] Integration test

---

## Real Semantic Models (Discovered)

Location: `/Users/doug/Work/data-modelling/official-models/redshift_gold/models/3_semantic/`

**Semantic Models:**
- `rentals`: 14 measures, 37 dims, 5 entities
- `facility_dimension`: 1 measure, 42 dims, 2 entities
- `facility_lifecycle`: 17 measures, 20 dims, 3 entities
- `facility_monthly_status`: 4 measures, 5 dims, 3 entities
- `reviews`: 4 measures, 13 dims, 3 entities
- `sfdc_cases`: 4 measures, 15 dims, 3 entities
- `time_spine`: 1 measure, 1 dim, 1 entity

**Metrics (27 total, 18 with PoP):**
- Revenue: gov, gmv, aov, amv (all PoP)
- Counts: rental_count, renter_count, transacting_facility_count (all PoP)
- Facility: live_canonical_facility_count, active_canonical_facility_count (PoP)
- Reviews: review_count, average_star_rating (PoP)
- And more...

**PoP Config Structure:**
```yaml
config:
  meta:
    pop:
      enabled: true
      grains: [mtd, ytd]
      comparisons: [pp, py]
      windows: [month]
      format: usd
```

---

## Key Domain Types (Phase 1 Complete)

```python
# Metric with variants (the core insight)
class Metric(BaseModel):
    name: str
    type: MetricType  # SIMPLE, DERIVED, RATIO
    variants: list[MetricVariant]  # OWNED by metric

# Variant - no independent identity
class MetricVariant(BaseModel):
    kind: VariantKind  # BASE, POP, BENCHMARK
    params: PopParams | BenchmarkParams | None

    def resolve_name(self, parent: Metric) -> str:
        return f"{parent.name}{self.suffix}"  # Always derived

# PoP params
class PopParams(BaseModel):
    comparison: PopComparison  # py, pm, pq, pw
    output: PopOutput  # previous, change, pct_change
```

---

## Quick Reference

```
YAML files
    │
    ▼
PyYAML.safe_load()
    │
    ▼
DomainBuilder.build()           ← Phase 2
    │
    ├── Parse semantic models → Measures, Dimensions, Entities
    ├── Parse metrics → Metric with type
    └── Expand PoP config → MetricVariants
    │
    ▼
ProcessedModel
    ├── measures: list[Measure]
    ├── dimensions: list[Dimension]
    ├── metrics: list[Metric]  ← Each owns its variants
    └── entities: list[Entity]
    │
    ▼
LookMLAdapter.render()          ← Phase 3
    │
    ▼
.lkml files
```
