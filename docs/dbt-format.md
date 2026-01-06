# dbt Semantic Layer Format

This guide explains how to use dbt Semantic Layer format files with semantic-patterns.

## Overview

semantic-patterns can ingest dbt Semantic Layer YAML files directly, allowing you to leverage your existing dbt semantic models and metrics definitions to generate LookML. This provides a bridge between dbt's semantic layer and Looker, without requiring you to rewrite your semantic definitions.

The dbt format support handles:
- `semantic_models` with entities, dimensions, and measures
- `metrics` with types: simple, derived, and ratio
- Period-over-period (PoP) comparisons via the `pop` config extension

## Configuration

To use dbt format files, set `format: dbt` in your `sp.yml` configuration file:

```yaml
input: ./models/semantic
output: ./lookml
schema: gold
format: dbt

model:
  name: my_analytics
  connection: snowflake_prod

explores:
  - fact: rentals

options:
  dialect: snowflake
  pop_strategy: dynamic
```

When `format: dbt` is set, the loader will recursively find all `.yml` and `.yaml` files in the input directory and parse them for `semantic_models` and `metrics` keys.

## File Structure

dbt semantic layer files can be organized flexibly. The loader finds all YAML files recursively and collects `semantic_models` and `metrics` from each file.

### Single File Approach

All definitions in one file:

```yaml
# models/semantic/orders.yml
version: 2

semantic_models:
  - name: orders
    model: ref('orders')
    # ... dimensions, measures, entities

metrics:
  - name: revenue
    type: simple
    # ... metric definition
```

### Multi-File Approach

Semantic models and metrics in separate files:

```
models/semantic/
  orders.yml           # semantic_models for orders
  order_metrics.yml    # metrics for orders
  customers.yml        # semantic_models for customers
```

Both approaches work. Files are processed in sorted order for deterministic results.

## Supported Features

### Semantic Models

The following semantic model components are fully supported:

#### Entities

```yaml
semantic_models:
  - name: rentals
    model: ref('rentals')

    entities:
      - name: rental
        type: primary
        expr: unique_rental_sk
        label: "Reservation"

      - name: facility
        type: foreign
        expr: facility_sk
```

Entity types: `primary`, `foreign`, `unique`, `natural`

#### Dimensions

```yaml
    dimensions:
      # Time dimension
      - name: created_at
        label: "Rental Created"
        type: time
        type_params:
          time_granularity: day
        expr: rental_created_at_utc
        config:
          meta:
            semantic_patterns:
              group: "Dates"
              date_selector: true

      # Categorical dimension
      - name: transaction_type
        label: "Order Status"
        type: categorical
        expr: rental_event_type
        config:
          meta:
            semantic_patterns:
              group: "Status"
```

Dimension types:
- `time` - Maps to time dimension in LookML (dimension_group)
- `categorical` - Maps to string/number dimension in LookML

Time granularities: `hour`, `day`, `week`, `month`, `quarter`, `year`

#### Measures

```yaml
    measures:
      - name: checkout_amount
        label: "Checkout Amount"
        agg: sum
        expr: rental_checkout_amount_local
        config:
          meta:
            semantic_patterns:
              group: "Revenue"
              format: usd
              hidden: true

      - name: rental_count
        label: "Rental Count"
        agg: count_distinct
        expr: unique_rental_sk
```

Supported aggregations: `sum`, `count`, `count_distinct`, `avg`, `min`, `max`

#### Defaults

```yaml
    defaults:
      agg_time_dimension: created_at  # Maps to time_dimension
```

### Metrics

#### Simple Metrics

Reference a single measure with optional filter:

```yaml
metrics:
  - name: gov
    label: "Gross Order Value (GOV)"
    type: simple
    type_params:
      measure: checkout_amount
    filter:
      - "{{ Dimension('rental__transaction_type') }} = 'completed'"
    config:
      meta:
        semantic_patterns:
          format: usd
          group: "Revenue"
          entity: rental
```

#### Derived Metrics

Compute from multiple metrics using a SQL expression:

```yaml
  - name: aov
    label: "Average Order Value"
    type: derived
    type_params:
      expr: gov / NULLIF(rental_count, 0)
      metrics:
        - gov
        - rental_count
    config:
      meta:
        semantic_patterns:
          format: usd
          group: "Revenue"
          entity: rental
```

#### Ratio Metrics

Compute a ratio between two metrics:

```yaml
  - name: conversion_rate
    label: "Conversion Rate"
    type: ratio
    type_params:
      numerator: purchases
      denominator: visits
    config:
      meta:
        semantic_patterns:
          format: percent_2
          group: "Funnel"
```

### Period-over-Period (PoP)

Add PoP comparisons via the `semantic_patterns` meta config:

```yaml
metrics:
  - name: gov
    label: "Gross Order Value"
    type: simple
    type_params:
      measure: checkout_amount
    config:
      meta:
        semantic_patterns:
          format: usd
          entity: rental
          pop:
            comparisons: [py, pm]
            outputs: [previous, pct_change]
```

Comparisons:
- `py` - Prior Year
- `pm` - Prior Month
- `pq` - Prior Quarter
- `pw` - Prior Week

Outputs:
- `previous` - The prior period value
- `change` - Absolute difference
- `pct_change` - Percentage change

This generates additional LookML measures like `gov_py`, `gov_pm`, `gov_py_pct_change`, etc.

### Filter Expressions

dbt Jinja filter expressions are parsed and converted:

```yaml
# dbt format
filter:
  - "{{ Dimension('rental__transaction_type') }} = 'completed'"
  - "{{ Dimension('rental__amount') }} > 100"
  - "{{ Dimension('rental__segment') }} IN ('Monthly', 'Event')"

# Converted internally to
filter:
  transaction_type: completed
  amount: ">100"
  segment: ['Monthly', 'Event']
```

## Limitations

The following dbt Semantic Layer features are not yet supported:

1. **Cumulative metrics** - The `type: cumulative` metric type is not supported
2. **Conversion metrics** - The `type: conversion` metric type is not supported
3. **Saved queries** - dbt's saved_queries are not processed
4. **Exports** - dbt's exports configuration is not processed
5. **Complex join paths** - Multi-hop joins must be configured explicitly in explores
6. **Metric offset** - Window function offsets in derived metrics

## Complete Example

Here is a complete example with semantic model and metrics:

**rentals.yml**
```yaml
version: 2

semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: created_at

    entities:
      - name: rental
        type: primary
        expr: unique_rental_sk
        label: "Reservation"

      - name: facility
        type: foreign
        expr: facility_sk

    dimensions:
      - name: created_at
        label: "Rental Created"
        type: time
        type_params:
          time_granularity: day
        expr: rental_created_at_utc
        config:
          meta:
            semantic_patterns:
              group: "Dates"
              date_selector: true

      - name: starts_at
        label: "Rental Start"
        type: time
        type_params:
          time_granularity: hour
        expr: rental_starts_at_utc
        config:
          meta:
            semantic_patterns:
              group: "Dates"
              date_selector: true

      - name: transaction_type
        label: "Order Status"
        type: categorical
        expr: rental_event_type
        config:
          meta:
            semantic_patterns:
              group: "Status"

      - name: rental_segment
        label: "Primary Segment"
        type: categorical
        expr: rental_segment_rollup
        config:
          meta:
            semantic_patterns:
              group: "Segment"

    measures:
      - name: checkout_amount
        label: "Checkout Amount"
        agg: sum
        expr: rental_checkout_amount_local
        config:
          meta:
            semantic_patterns:
              group: "Revenue"
              format: usd
              hidden: true

      - name: rental_count
        label: "Rental Count"
        agg: count_distinct
        expr: unique_rental_sk
        config:
          meta:
            semantic_patterns:
              group: "Counts"
              format: decimal_0
              hidden: true
```

**rental_metrics.yml**
```yaml
version: 2

metrics:
  - name: gov
    label: "Gross Order Value (GOV)"
    type: simple
    type_params:
      measure: checkout_amount
    filter:
      - "{{ Dimension('rental__transaction_type') }} = 'completed'"
    config:
      meta:
        semantic_patterns:
          format: usd
          group: "Revenue"
          entity: rental
          pop:
            comparisons: [py, pm]
            outputs: [previous, pct_change]

  - name: rental_count
    label: "Rental Count"
    type: simple
    type_params:
      measure: rental_count
    filter:
      - "{{ Dimension('rental__transaction_type') }} = 'completed'"
    config:
      meta:
        semantic_patterns:
          format: decimal_0
          group: "Counts"
          entity: rental
          pop:
            comparisons: [py, pm]
            outputs: [previous, pct_change]

  - name: aov
    label: "Average Order Value"
    type: derived
    type_params:
      expr: gov / NULLIF(rental_count, 0)
      metrics:
        - gov
        - rental_count
    config:
      meta:
        semantic_patterns:
          format: usd
          group: "Revenue"
          entity: rental
```

## Mapping Details

### Dimension Type Mapping

| dbt Type | semantic-patterns Type | LookML Output |
|----------|------------------------|---------------|
| `time` | `time` | `dimension_group` with timeframes |
| `categorical` | `categorical` | `dimension` (string/number) |

### Measure Aggregation Mapping

| dbt `agg` | LookML `type` |
|-----------|---------------|
| `sum` | `sum` |
| `count` | `count` |
| `count_distinct` | `count_distinct` |
| `avg` | `average` |
| `min` | `min` |
| `max` | `max` |

### Metric Type Mapping

| dbt Metric Type | Description |
|-----------------|-------------|
| `simple` | Maps to a LookML measure referencing the underlying measure with optional SQL filters |
| `derived` | Maps to a LookML measure with `type: number` and SQL expression |
| `ratio` | Maps to a LookML measure computing numerator/denominator |

### semantic_patterns Meta Fields

Fields under `config.meta.semantic_patterns` control LookML generation:

| Field | Description |
|-------|-------------|
| `group` | LookML `group_label` for organizing fields |
| `format` | Value format (e.g., `usd`, `decimal_0`, `percent_1`) |
| `hidden` | Set to `true` to hide from Looker UI |
| `entity` | Associate metric with an entity for explore generation |
| `date_selector` | Mark time dimension for date selector filter |
| `complete` | Mark entity as complete (all records present) |
| `pop` | Period-over-period configuration |

### Legacy Meta Field Mapping

For backward compatibility, these legacy field names are also supported:

| Legacy Field | Maps To |
|--------------|---------|
| `subject` | `group` |
| `primary_entity` | `entity` |
| `bi_field: false` | `hidden: true` |
