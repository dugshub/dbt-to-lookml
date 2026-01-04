# Domain Layer

Pure semantic types - output-agnostic business concepts.

## Structure

```
domain/
├── data_model.py   # DataModel, ConnectionType (physical table reference)
├── dimension.py    # Dimension, DimensionType, TimeGranularity, TimezoneVariant
├── measure.py      # Measure, AggregationType
├── metric.py       # Metric, MetricType, MetricVariant, PopConfig, PopParams
├── filter.py       # Filter, FilterCondition, FilterOperator
└── model.py        # ProcessedModel, Entity, DateSelectorConfig
```

## Design Principles

### 1. Output-Agnostic

These types represent semantic concepts, not rendering concerns:

| Domain Concept | NOT Here (Adapter Concern) |
|----------------|---------------------------|
| `Metric` with `PopConfig` | `period_over_period` LookML type |
| `Entity` with `type: foreign` | `join` with `relationship: many_to_one` |
| `Dimension` with `group` | `view_label` + `group_label` |
| `Filter` conditions | `CASE WHEN ... END` SQL |

### 2. Metrics Own Their Variants

A metric with 7 PoP variants is ONE metric object with expanded `variants: list[MetricVariant]`.

```python
metric = Metric(name="revenue", pop=PopConfig(comparisons=[py, pm], outputs=[previous, change]))
metric.expand_variants()
# metric.variants = [base, py, py_change, pm, pm_change]
```

### 3. Entity-Based Relationships

Join inference comes from entity matching, not explicit join definitions:

```python
# Rentals model
Entity(name="facility", type="foreign", expr="facility_sk")

# Facilities model
Entity(name="facility", type="primary", expr="facility_sk")

# Adapter infers: rentals → facilities (many_to_one)
```

## What Does NOT Belong Here

LookML-specific concepts live in `adapters/lookml/types.py`:

- `ExploreConfig`, `JoinOverride`
- `JoinRelationship` (many_to_one, one_to_many)
- `ExposeLevel` (all, dimensions)
- `InferredJoin`

## Future Growth

When adding storage/UI management, expand to feature-folder pattern:

```
domain/
├── measure/
│   ├── schema.py       # Pydantic models
│   ├── models.py       # SQLAlchemy ORM
│   ├── service.py      # Business logic
│   └── repository.py   # Data access
├── dimension/
│   └── ...
└── metric/
    └── ...
```
