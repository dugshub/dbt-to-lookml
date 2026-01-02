# Native Semantic Schema Specification

> **Version**: 2.0
> **Status**: Draft
> **Purpose**: Define our semantic layer schema - dbt-inspired but with first-class concepts

## Design Principles

1. **dbt-familiar structure** - semantic_models, entities, dimensions, measures, metrics
2. **First-class concepts** - PoP, benchmarks, date selectors are top-level, not buried in meta
3. **Good defaults** - less verbose, sensible defaults
4. **Flat > nested** - avoid deep nesting where possible
5. **Query-engine agnostic** - generates to LookML, dbt, Cube.js, etc.

---

## File Structure

Single unified file per domain:

```
semantic_layer/
├── rentals.yml           # data_model + semantic_model + metrics
├── facilities.yml
└── reviews.yml
```

---

## Schema Reference

### Top-Level Structure

```yaml
version: 2

data_models:
  - name: rentals
    # ...

semantic_models:
  - name: rentals
    # ...

metrics:
  - name: gmv
    # ...
```

---

### DataModel

Represents the physical table/source.

```yaml
data_models:
  - name: rentals
    catalog: analytics          # optional (database in Snowflake, catalog in Starburst)
    schema: gold_production
    table: rentals
    connection: redshift        # redshift | starburst | postgres | duckdb
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique identifier for reference |
| `catalog` | string | no | Database/catalog (3-part naming) |
| `schema` | string | yes | Schema name |
| `table` | string | yes | Table name |
| `connection` | enum | yes | Connection type |

**Connection Types**: `redshift`, `starburst`, `postgres`, `duckdb`

---

### SemanticModel

The logical model with entities, dimensions, and measures.

```yaml
semantic_models:
  - name: rentals
    description: Core rental fact model
    model: rentals                    # references data_model by name
    time_dimension: created_at        # default aggregation time dimension

    date_selector:
      dimensions: [created_at, starts_at]

    entities:
      # ...

    dimensions:
      # ...

    measures:
      # ...
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique identifier |
| `description` | string | no | Human-readable description |
| `model` | string | yes | Reference to data_model name |
| `time_dimension` | string | no | Default time dimension for aggregations |
| `date_selector` | object | no | Date selector configuration |
| `entities` | list | yes | Join keys |
| `dimensions` | list | yes | Categorical and time attributes |
| `measures` | list | yes | Aggregatable values |

#### DateSelector

```yaml
date_selector:
  dimensions: [created_at, starts_at, ends_at]
```

---

### Entity

Join keys for relationships between models.

```yaml
entities:
  - name: rental
    type: primary
    expr: unique_rental_sk
    label: Reservation            # optional display label

  - name: facility
    type: foreign
    expr: facility_sk
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Entity name |
| `type` | enum | yes | `primary`, `foreign`, `unique` |
| `expr` | string | yes | SQL expression (usually column name) |
| `label` | string | no | Display label |

---

### Dimension

Categorical or time-based attributes for grouping/filtering.

#### Categorical Dimension

```yaml
dimensions:
  - name: transaction_type
    label: Rental Order Status
    description: Order fulfillment status
    type: categorical
    expr: rental_event_type
    group: Status
    hidden: false                 # default
```

#### Time Dimension (simple)

```yaml
  - name: updated_at
    type: time
    expr: rental_updated_at_utc
    granularity: day
    hidden: true
```

#### Time Dimension (with timezone variants)

```yaml
  - name: created_at
    label: Rental Created
    type: time
    granularity: day
    group: Dates
    primary_variant: utc
    variants:
      utc: rental_created_at_utc
      local: rental_created_at_local
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique identifier |
| `label` | string | no | Display label |
| `description` | string | no | Human-readable description |
| `type` | enum | yes | `categorical`, `time` |
| `expr` | string | yes* | SQL expression (*not required if variants specified) |
| `granularity` | string | no | For time: `day`, `hour`, `week`, `month`, `quarter`, `year` |
| `group` | string | no | Grouping (supports dot notation: `Dates.UTC`) |
| `hidden` | bool | no | Hide from BI users (default: false) |
| `primary_variant` | string | no | Which variant is default (for time dims with variants) |
| `variants` | object | no | Timezone variants: `{utc: expr, local: expr}` |

---

### Measure

Aggregatable numeric values. Typically hidden - exposed via metrics.

```yaml
measures:
  - name: checkout_amount
    label: Checkout Amount
    description: Sum of rental checkout amounts
    agg: sum
    expr: rental_checkout_amount_local
    format: usd
    hidden: true
    group: Revenue

  - name: rental_count
    agg: count_distinct
    expr: unique_rental_sk
    format: decimal_0
    hidden: true
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique identifier |
| `label` | string | no | Display label |
| `description` | string | no | Human-readable description |
| `agg` | enum | yes | Aggregation type |
| `expr` | string | yes | SQL expression |
| `format` | string | no | Value format |
| `hidden` | bool | no | Hide from BI users (default: false) |
| `group` | string | no | Grouping |

**Aggregation Types**: `sum`, `count`, `count_distinct`, `average`, `min`, `max`, `median`

**Format Values**: `usd`, `decimal_0`, `decimal_1`, `decimal_2`, `percent_1`, `percent_2`

---

### Metric

Business-level measures with semantic meaning.

#### Simple Metric

```yaml
metrics:
  - name: gmv
    label: Gross Merchandise Value
    description: Total revenue excluding fees
    type: simple
    measure: display_amount

    filter:
      transaction_type: completed

    pop:
      comparisons: [py, pm]
      outputs: [previous, change, pct_change]

    format: usd
    group: Metrics.Revenue
```

#### Derived Metric

```yaml
  - name: gmv_per_facility
    label: GMV per Facility
    type: derived
    expr: gmv / NULLIF(facility_count, 0)
    metrics: [gmv, facility_count]

    pop:
      comparisons: [py, pm]
      outputs: [previous, pct_change]

    format: usd
    group: Metrics.Revenue
```

#### Ratio Metric

```yaml
  - name: conversion_rate
    label: Conversion Rate
    type: ratio
    numerator: rental_count
    denominator: search_count

    format: percent_2
    group: Funnel
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique identifier |
| `label` | string | no | Display label |
| `description` | string | no | Human-readable description |
| `type` | enum | yes | `simple`, `derived`, `ratio` |
| `measure` | string | * | For simple: measure reference |
| `expr` | string | * | For derived: SQL expression |
| `metrics` | list | * | For derived: metric dependencies |
| `numerator` | string | * | For ratio: numerator metric |
| `denominator` | string | * | For ratio: denominator metric |
| `filter` | object | no | Filter conditions |
| `pop` | object | no | Period-over-period config |
| `benchmarks` | list | no | Benchmark comparisons |
| `format` | string | no | Value format |
| `group` | string | no | Grouping |
| `entity` | string | no | Associated entity |

---

### Filter Syntax

Filters use implicit operators based on value type:

```yaml
filter:
  # Equals (plain value)
  transaction_type: completed

  # IN (list)
  rental_segment: [Monthly, Event, Airport]

  # Comparison operators (quoted string)
  amount: '>10'
  count: '<=5'
  revenue: '>=1000'
```

**Parsing Rules**:
- Plain value → `= value`
- List → `IN (values)`
- Quoted string starting with `<`, `>`, `<=`, `>=` → parse operator

---

### PoP (Period-over-Period)

```yaml
pop:
  comparisons: [py, pm]                    # which periods to compare
  outputs: [previous, change, pct_change]  # what values to generate
```

**Comparison Values**:
- `py` - prior year (same dates, last year)
- `pm` - prior month (same dates, last month)
- `pq` - prior quarter (same dates, last quarter)
- `pw` - prior week (same dates, last week)

**Output Values**:
- `previous` - the value from the prior period
- `change` - absolute difference (current - previous)
- `pct_change` - percentage change ((current - previous) / previous)

**Generated Variants**:
A metric with `comparisons: [py, pm]` and `outputs: [previous, change, pct_change]` generates:
- `gmv` (base)
- `gmv_py` (prior year value)
- `gmv_py_change` (vs prior year change)
- `gmv_py_pct_change` (vs prior year % change)
- `gmv_pm` (prior month value)
- `gmv_pm_change` (vs prior month change)
- `gmv_pm_pct_change` (vs prior month % change)

---

### Benchmarks (Future)

```yaml
benchmarks:
  - slice: market
    label: vs Market Avg
  - slice: segment
    label: vs Segment
```

---

### Grouping

Supports multiple formats (all equivalent):

```yaml
# Dot notation
group: Metrics.Revenue

# List
group: [Metrics, Revenue]

# Single level
group: Revenue
```

---

## Complete Example

```yaml
version: 2

data_models:
  - name: rentals
    schema: gold_production
    table: rentals
    connection: redshift

semantic_models:
  - name: rentals
    description: Core rental fact model
    model: rentals
    time_dimension: created_at

    date_selector:
      dimensions: [created_at, starts_at]

    entities:
      - name: rental
        type: primary
        expr: unique_rental_sk
        label: Reservation

      - name: facility
        type: foreign
        expr: facility_sk

    dimensions:
      - name: created_at
        label: Rental Created
        type: time
        granularity: day
        group: Dates
        primary_variant: utc
        variants:
          utc: rental_created_at_utc
          local: rental_created_at_local

      - name: transaction_type
        label: Order Status
        type: categorical
        expr: rental_event_type
        group: Status

      - name: rental_segment
        label: Primary Segment
        type: categorical
        expr: rental_segment_rollup
        group: Segment

    measures:
      - name: checkout_amount
        agg: sum
        expr: rental_checkout_amount_local
        format: usd
        hidden: true

      - name: display_amount
        agg: sum
        expr: rental_checkout_amount_local - coalesce(total_spothero_fee_amount, 0)
        format: usd
        hidden: true

      - name: rental_count
        agg: count_distinct
        expr: unique_rental_sk
        format: decimal_0
        hidden: true

metrics:
  - name: gmv
    label: Gross Merchandise Value
    description: Total revenue excluding SpotHero fees
    type: simple
    measure: display_amount
    filter:
      transaction_type: completed
    pop:
      comparisons: [py, pm]
      outputs: [previous, change, pct_change]
    format: usd
    group: Metrics.Revenue

  - name: rental_count
    label: Rental Count
    type: simple
    measure: rental_count
    filter:
      transaction_type: completed
    pop:
      comparisons: [py, pm]
      outputs: [previous, change, pct_change]
    format: decimal_0
    group: Metrics.Counts

  - name: aov
    label: Average Order Value
    type: derived
    expr: gmv / NULLIF(rental_count, 0)
    metrics: [gmv, rental_count]
    pop:
      comparisons: [py]
      outputs: [previous, pct_change]
    format: usd
    group: Metrics.Revenue
```
