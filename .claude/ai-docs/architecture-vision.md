# Architecture Vision: Layered Semantic Processing

> **Status**: Working Document
> **Last Updated**: 2025-12-19
> **Purpose**: Capture architectural direction for separating domain logic from destination generators

## The Problem

Currently, domain concepts (PoP, Metrics, Join Graphs, Date Selector) are embedded inside `LookMLGenerator`. This creates:

1. **Tight coupling** - Can't add new destinations (Cube.js, Lightdash) without reimplementing domain logic
2. **Testing complexity** - Must test through LookML serialization even for pure domain logic
3. **Monolithic generator** - `lookml.py` is 2,684 lines with 56 methods
4. **Mixed concerns** - Business logic (PoP expansion) interleaved with output formatting

## Core Insight

**PoP, Metrics, Join Graphs are OUR domain concepts** - they exist independent of the destination BI system.

| Concept | Our Definition | LookML Output | Cube.js Output (future) |
|---------|---------------|---------------|------------------------|
| PoP | `PopConfig(comparisons=[py], windows=[month])` | `type: period_over_period` measures | `timeDimension` with `granularity` |
| Metric | `Metric(type=simple, measure=revenue)` | `measure: { type: sum }` | `measures: [{ name, sql, type }]` |
| Join | `Entity(type=foreign, expr=user_sk)` | `join: { sql_on }` | `joins: [{ sql }]` |
| Date Selector | `DateSelectorConfig(dimensions=[...])` | `parameter` + `dimension_group` | `dateRange` filter |

---

## Target Architecture

### Layer 1: Domain Models (`schemas/`)

Pydantic models defining our semantic layer concepts. These are **our definitions** layered on top of dbt's semantic models.

```
schemas/
├── semantic_layer.py       # SemanticModel, Measure, Dimension, Entity
├── metrics.py              # Metric, SimpleMetricParams, DerivedMetricParams
├── pop.py                  # PopConfig, PopComparison, PopWindow
├── date_selector.py        # DateSelectorConfig
└── config.py               # GeneratorConfig, FeatureFlags
```

**Key principle**: These models are destination-agnostic. They describe WHAT we want, not HOW to output it.

### Layer 2: Semantic Processors (`processors/`)

Pure functions/classes that transform domain models. No I/O, no destination-specific logic.

```
processors/
├── __init__.py
├── pop_expander.py         # Expand PopConfig → list of measure definitions
├── date_selector_resolver.py # Resolve time dims → DateSelectorConfig
├── metric_resolver.py      # Resolve metric expressions and dependencies
├── join_graph_builder.py   # Build join relationships from entities
├── measure_usage_analyzer.py # Determine which measures are needed
└── model_processor.py      # Orchestrate all processors
```

**Output**: `ProcessedModel` - a fully-resolved, destination-agnostic representation.

### Layer 3: Destination Generators (`generators/`)

Translators that convert `ProcessedModel` to destination-specific output.

```
generators/
├── __init__.py
├── base.py                 # Abstract Generator interface
├── lookml/
│   ├── __init__.py
│   ├── generator.py        # LookMLGenerator - orchestration
│   ├── view_writer.py      # ProcessedModel → view dict
│   ├── explore_writer.py   # JoinGraph → explore dict
│   ├── model_writer.py     # Model file generation
│   └── formatters.py       # LookML-specific formatting
├── cube/                   # Future
│   └── generator.py
└── lightdash/              # Future
    └── generator.py
```

---

## Data Flow

### Current (Problematic)

```
YAML → DbtParser → SemanticModel → LookMLGenerator → .lkml
                                         ↑
                              PoP expansion here
                              Metric resolution here
                              Join graph here
                              Date selector here
                              Measure filtering here
```

### Target

```
YAML → DbtParser → SemanticModel
                        ↓
              ModelProcessor.process()
                        ↓
                  ProcessedModel ←── destination-agnostic
                        ↓
              LookMLGenerator.generate()
                        ↓
                   .lkml files
```

---

## Key Data Structures

### ProcessedModel

The contract between processors and generators:

```python
@dataclass
class ProcessedModel:
    """Fully resolved semantic model ready for any generator."""
    name: str
    sql_table_name: str
    primary_entity: ProcessedEntity | None

    # All dimensions (original + generated like calendar)
    dimensions: list[ProcessedDimension]

    # All measures (original + PoP variants)
    measures: list[ProcessedMeasure]

    # Resolved metrics with SQL expressions
    metrics: list[ProcessedMetric]

    # Join relationships to other models
    joins: list[JoinRelationship]

    # Feature-specific configs (resolved)
    date_selector: DateSelectorConfig | None

    # Metadata
    description: str | None
    meta: dict[str, Any]
```

### ProcessedMeasure

```python
@dataclass
class ProcessedMeasure:
    """A measure ready for generation."""
    name: str
    type: MeasureType  # sum, count_distinct, average, etc.
    sql: str

    # Display
    label: str | None
    description: str | None
    group_label: str | None
    view_label: str | None

    # Behavior
    hidden: bool
    value_format: str | None

    # Origin tracking
    source: MeasureSource  # original, pop_variant, metric_derived
    source_measure: str | None  # For PoP: which measure this derives from
    pop_config: PopMeasureConfig | None  # For PoP: period, kind, etc.
```

### JoinRelationship

```python
@dataclass
class JoinRelationship:
    """A resolved join between two models."""
    from_model: str
    to_model: str

    # Join details
    from_field: str
    to_field: str
    relationship: JoinCardinality  # many_to_one, one_to_many, etc.

    # SQL
    sql_on: str  # Generated SQL ON clause

    # Metadata
    required: bool
```

---

## Migration Strategy

### Phase 1: Extract Processors (No Breaking Changes)

Create processors alongside existing code. Each processor extracts logic from `LookMLGenerator`:

| Processor | Extract From | Lines Affected |
|-----------|--------------|----------------|
| `PopExpander` | `_generate_pop_*` methods | ~300 lines |
| `DateSelectorResolver` | `_generate_date_selector_*` | ~120 lines |
| `MetricResolver` | `_generate_metric_measure` | ~200 lines |
| `JoinGraphBuilder` | `_build_join_graph` | ~380 lines |
| `MeasureUsageAnalyzer` | `_analyze_measure_usage` | ~100 lines |

**Approach**: New code calls processors, old code gradually deprecated.

### Phase 2: Introduce ProcessedModel

Create `ProcessedModel` and `ModelProcessor` that orchestrates all processors:

```python
class ModelProcessor:
    def process(
        self,
        model: SemanticModel,
        metrics: list[Metric],
        config: ProcessorConfig
    ) -> ProcessedModel:
        # 1. Resolve metrics
        resolved_metrics = self.metric_resolver.resolve(model, metrics)

        # 2. Analyze measure usage
        usage = self.usage_analyzer.analyze(model, resolved_metrics)

        # 3. Expand PoP
        pop_measures = self.pop_expander.expand(model, usage)

        # 4. Resolve date selector
        date_selector = self.date_selector_resolver.resolve(model, config)

        # 5. Build joins
        joins = self.join_builder.build(model)

        return ProcessedModel(...)
```

### Phase 3: Simplify LookMLGenerator

`LookMLGenerator` becomes a thin translator:

```python
class LookMLGenerator:
    def generate(self, processed_models: list[ProcessedModel]) -> dict[str, str]:
        files = {}
        for model in processed_models:
            view_content = self.view_writer.write(model)
            files[f"{model.name}.view.lkml"] = view_content

        explores = self.explore_writer.write(processed_models)
        files["explores.lkml"] = explores

        return files
```

### Phase 4: Split Views Feature

With clean architecture, split views becomes straightforward:

```python
class ViewSplitter:
    def split(self, model: ProcessedModel) -> list[ViewFile]:
        """Split a ProcessedModel into multiple view files."""
        base = ViewFile(
            name=f"{model.name}.view.lkml",
            components=[model.dimensions, model.base_measures]
        )
        metrics = ViewFile(
            name=f"{model.name}.metrics.view.lkml",
            components=[model.metric_measures],
            refinement_of=model.name
        )
        pop = ViewFile(
            name=f"{model.name}.pop.view.lkml",
            components=[model.pop_measures],
            refinement_of=model.name
        )
        return [base, metrics, pop]
```

---

## Checklist: Things to Extract

### From `LookMLGenerator` (2,684 lines)

- [ ] **PoP Generation** (~300 lines)
  - `_generate_pop_hidden_measures()` (line 458)
  - `_generate_pop_visible_measures()` (line 585)
  - `_generate_metric_pop_measures()` (line 619)
  - `_generate_calendar_dimension_group()` (line 726)

- [ ] **Date Selector** (~120 lines)
  - `_generate_date_selector_parameter()` (line 270)
  - `_generate_date_selector_fields()` (line 747)
  - `_should_include_in_date_selector()` (line 392)
  - `_get_date_selector_dimensions()` (line 417)

- [ ] **Metric Resolution** (~200 lines)
  - `_generate_metric_measure()` (line 1516)
  - `_resolve_metric_reference()`
  - `_extract_required_fields()`
  - `_infer_value_format()`

- [ ] **Join Graph** (~380 lines)
  - `_build_join_graph()` (line 1857)
  - `_identify_metric_requirements()` (line 1707)
  - `_infer_relationship()`
  - `_generate_sql_on_clause()`

- [ ] **Measure Analysis** (~100 lines)
  - `_analyze_measure_usage()` (line 963)

### From `SemanticModel.to_lookml_dict()`

Consider whether base view generation should also be a processor or stay in the schema.

---

## Open Questions

1. **Where does `to_lookml_dict()` live?**
   - Currently on `SemanticModel` (schema knows about LookML)
   - Could move to `ViewWriter` (cleaner separation)
   - Trade-off: convenience vs purity

2. **ProcessedModel granularity**
   - One `ProcessedModel` per semantic model?
   - Or one per output view (for split views)?

3. **Configuration handling**
   - Currently 14 constructor params on `LookMLGenerator`
   - Should config be on processors or passed through?

4. **Backward compatibility**
   - Keep `LookMLGenerator.generate()` signature stable
   - Internal refactoring only

---

## Related Issues

- **DTL-037**: PoP Epic (currently implements PoP in generator)
- **DTL-046**: Date Selector Epic (currently implements in generator)
- **Future**: Split Views feature (blocked by this refactor)
- **Future**: Cube.js generator (enabled by this refactor)

---

## SQL Processing with sqlglot

We've integrated [sqlglot](https://github.com/tobymao/sqlglot) (zero-dependency SQL parser) for SQL expression handling. This enables several architectural capabilities:

### Current Usage

`qualify_sql_expression()` in `types.py` uses sqlglot to:
- Parse SQL expressions into AST
- Find all `Column` nodes without table qualifiers
- Add `${TABLE}.` prefix to prevent ambiguous column errors in joins

```python
# Before: bare column refs cause Looker join errors
CASE WHEN rental_status = 'active' THEN facility_id END

# After: sqlglot identifies and qualifies columns
CASE WHEN ${TABLE}.rental_status = 'active' THEN ${TABLE}.facility_id END
```

### Future Capabilities

#### 1. SQL Expression Processor

A dedicated processor for all SQL transformation:

```python
processors/
├── sql_expression_processor.py  # sqlglot-based SQL handling
```

```python
class SqlExpressionProcessor:
    """Process SQL expressions with sqlglot."""

    def qualify_columns(self, expr: str, table_alias: str = "${TABLE}") -> str:
        """Add table qualifiers to bare column references."""

    def extract_column_references(self, expr: str) -> list[str]:
        """Find all columns referenced in an expression."""

    def validate(self, expr: str) -> list[SqlError]:
        """Validate SQL syntax before generation."""

    def transpile(self, expr: str, from_dialect: str, to_dialect: str) -> str:
        """Convert SQL between dialects (Redshift → BigQuery)."""
```

#### 2. Multi-Dialect Support

sqlglot supports 20+ SQL dialects. This enables:

| Source Dialect | Target Destinations |
|---------------|---------------------|
| Redshift | LookML (Redshift), Cube.js (BigQuery), Lightdash (Snowflake) |
| Snowflake | LookML (Snowflake), Cube.js (Postgres) |
| BigQuery | Any target dialect |

```python
# Example: transpile Redshift → BigQuery
sqlglot.transpile(
    "DATEADD(day, -7, GETDATE())",
    read="redshift",
    write="bigquery"
)
# → "DATE_ADD(CURRENT_DATE(), INTERVAL -7 DAY)"
```

#### 3. ProcessedModel with Normalized SQL

SQL expressions in `ProcessedModel` could be stored as sqlglot ASTs or normalized SQL:

```python
@dataclass
class ProcessedMeasure:
    name: str
    type: MeasureType
    sql_ast: sqlglot.Expression  # Parsed AST, transpile at generation time
    # OR
    sql_normalized: str  # Pre-qualified, dialect-neutral SQL
```

#### 4. Validation at Parse Time

Catch SQL errors early:

```python
class DbtParser:
    def parse_dimension(self, dim_yaml: dict) -> Dimension:
        expr = dim_yaml.get("expr")
        if expr:
            try:
                sqlglot.parse_one(expr)
            except ParseError as e:
                raise ValidationError(f"Invalid SQL in dimension {name}: {e}")
```

### Integration Points

| Component | sqlglot Usage |
|-----------|--------------|
| `types.py` | `qualify_sql_expression()` - column qualification |
| `parsers/metric_filter.py` | Dimension ref resolution + qualification |
| `generators/lookml.py` | `_qualify_measure_sql()` delegates to shared fn |
| **Future**: `processors/sql_processor.py` | Centralized SQL handling |
| **Future**: `generators/cube/` | Dialect transpilation |

---

## Notes / Observations

<!-- Add notes here as you work through the codebase -->

### 2025-12-19 - Initial Vision
- Created based on discussion about split views feature
- Identified that PoP, metrics, joins are domain concepts mixed into LookML generator
- Proposed 3-layer architecture: Domain Models → Processors → Generators

### 2025-12-19 - sqlglot Integration
- Added sqlglot for SQL expression parsing (zero dependencies, 561KB)
- Consolidated all SQL qualification to single `qualify_sql_expression()` function
- Opens path for multi-dialect support and SQL validation

### 2025-01-02 - v2 Rebuild Decision

**Key Architectural Insight**: The domain model should know what it IS. Adapters should know how to RENDER it.

Instead of processors that transform data, we now use **typed domain primitives with owned variants**:

```python
# OLD approach (processors)
pop_processor.expand(metric) → list[measures]

# NEW approach (domain owns variants)
metric.variants = [base, py, pm, ...]  # Already expanded
adapter.render(metric)  # Pure mapping
```

**Core Change**: Metrics OWN their variants (PoP, benchmarks) - they're not separate entities.
- 10 metrics with 70 variants ≠ 70 metrics
- Variant names derived from parent: `gmv_py` = `gmv` + `_py` suffix
- Domain model is the source of truth for WHAT exists

**New Structure** (`src/dbt_to_lookml_v2/`):
- `domain/` - Measure, Dimension, Metric (with variants)
- `ingestion/` - YAML → Domain (DomainBuilder)
- `adapters/lookml/` - Domain → .lkml (pure mapping)

**DSI Spike Result**: dbt-semantic-interfaces parser too opinionated (needs project context). Using simple PyYAML + our own Pydantic models instead.

See `.tasks/plans/v2-rebuild.md` for full implementation plan.

