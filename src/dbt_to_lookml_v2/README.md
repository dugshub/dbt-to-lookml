# dbt-to-lookml v2

Domain-driven semantic layer to LookML generation.

## Architecture

```
YAML → Ingestion (DomainBuilder) → Domain (ProcessedModel) → Adapter → .lkml
```

| Layer | Purpose | Key Types |
|-------|---------|-----------|
| `ingestion/` | Load YAML, build domain objects | `DomainBuilder`, `YamlLoader` |
| `domain/` | Pure semantic types (output-agnostic) | `ProcessedModel`, `Metric`, `Dimension`, `Measure`, `Entity` |
| `adapters/lookml/` | LookML-specific rendering | `LookMLGenerator`, `ExploreGenerator`, `ExploreConfig` |

## Usage

### Basic: Generate Views

```python
from dbt_to_lookml_v2.ingestion import DomainBuilder
from dbt_to_lookml_v2.adapters.lookml import LookMLGenerator

# Load semantic models from YAML directory
models = DomainBuilder.from_directory("path/to/semantic_models/")

# Generate LookML view files
generator = LookMLGenerator()
files = generator.generate(models)

# files = {
#   "rentals.view.lkml": "...",
#   "rentals.metrics.view.lkml": "...",
#   "rentals.pop.view.lkml": "...",
#   ...
# }

# Write to disk
from pathlib import Path
output_dir = Path("output/views")
output_dir.mkdir(parents=True, exist_ok=True)
for filename, content in files.items():
    (output_dir / filename).write_text(content)
```

### With Explores

```python
from dbt_to_lookml_v2.ingestion import DomainBuilder
from dbt_to_lookml_v2.adapters.lookml import LookMLGenerator, ExploreGenerator

# Load models
models = DomainBuilder.from_directory("semantic_models/")
model_lookup = {m.name: m for m in models}

# Generate views
view_gen = LookMLGenerator()
view_files = view_gen.generate(models)

# Generate explores - specify which models are facts
explores = ExploreGenerator.configs_from_fact_models(["rentals", "orders"])
explore_gen = ExploreGenerator()
explore_files = explore_gen.generate(explores, model_lookup)

# Combine and write
all_files = {**view_files, **explore_files}
```

### With Explore Configuration (Labels, Join Overrides)

```python
from dbt_to_lookml_v2.adapters.lookml import ExploreGenerator

# From YAML-style config dicts
explore_configs = ExploreGenerator.configs_from_yaml([
    {
        "name": "rental_analytics",
        "fact_model": "rentals",
        "label": "Rental Analytics",
        "joins": [
            {"model": "facilities", "expose": "dimensions"},
            {"model": "reviews", "expose": "all"},
        ]
    }
])

explore_files = explore_gen.generate(explore_configs, model_lookup)
```

### From a Single Dict (Testing)

```python
from dbt_to_lookml_v2.ingestion import DomainBuilder

# For unit tests or simple cases
models = DomainBuilder.from_dict({
    "semantic_models": [
        {
            "name": "orders",
            "entities": [{"name": "order", "type": "primary", "expr": "order_id"}],
            "dimensions": [{"name": "status", "type": "categorical", "expr": "status"}],
            "measures": [{"name": "amount", "agg": "sum", "expr": "amount"}],
        }
    ],
    "metrics": [
        {"name": "total_amount", "type": "simple", "measure": "amount"}
    ]
})
```

## Output Structure

For a model named `rentals` with metrics and PoP variants:

```
output/
├── rentals.view.lkml              # Base view: dims, entities, sql_table_name
├── rentals.metrics.view.lkml      # Refinement: +rentals { measures }
├── rentals.pop.view.lkml          # Refinement: +rentals { PoP measures }
├── rentals.explore.lkml           # Explore with inferred joins
└── rentals_explore_calendar.view.lkml  # Date selector parameter + calendar dim
```

## Key Concepts

### Metrics Own Their Variants

A metric with PoP (period-over-period) config expands into multiple variants:

```yaml
metrics:
  - name: revenue
    type: simple
    measure: amount
    pop:
      comparisons: [py, pm]      # prior year, prior month
      outputs: [previous, change, pct_change]
```

Generates: `revenue`, `revenue_py`, `revenue_py_change`, `revenue_py_pct_change`, `revenue_pm`, ...

### Entity-Based Join Inference

Explores infer joins from entity relationships:

```yaml
# rentals.yml
entities:
  - name: rental
    type: primary
    expr: rental_sk
  - name: facility
    type: foreign
    expr: facility_sk

# facilities.yml
entities:
  - name: facility
    type: primary
    expr: facility_sk
```

The explore generator automatically creates a `many_to_one` join from rentals → facilities.

### Domain vs Adapter Separation

- **Domain types** (`domain/`): Semantic concepts that apply to any BI tool
- **Adapter types** (`adapters/lookml/types.py`): LookML-specific concepts (explores, joins, field exposure)

This separation allows future adapters (Cube.js, Tableau, etc.) to reuse the domain layer.

## YAML Schema

See [SCHEMA.md](./SCHEMA.md) for the full native schema specification.

## Development

```bash
# Run v2 tests
uv run pytest tests/v2 -v

# Type check
uv run mypy src/dbt_to_lookml_v2 --ignore-missing-imports
```
