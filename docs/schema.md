# Semantic Patterns YAML Schema Reference

This document provides a complete reference for the semantic-patterns native YAML schema. Use this guide when writing semantic models, dimensions, measures, and metrics.

## Table of Contents

- [Top-Level Structure](#top-level-structure)
- [Data Models](#data-models)
- [Semantic Models](#semantic-models)
- [Entities](#entities)
- [Dimensions](#dimensions)
- [Measures](#measures)
- [Metrics](#metrics)
- [Filters](#filters)
- [Explores](#explores)
- [Complete Example](#complete-example)

---

## Top-Level Structure

A semantic-patterns YAML file can contain four main sections:

```yaml
version: 2

data_models:
  - # Physical table definitions

semantic_models:
  - # Semantic model definitions (dimensions, measures, entities)

metrics:
  - # Business metrics with optional period-over-period variants

explores:
  - # LookML explore configurations (optional)
```

All sections are optional. You can define everything in a single file or split across multiple files. The loader recursively finds all `.yml` and `.yaml` files in the specified directory.

---

## Data Models

Data models define the physical tables/sources that semantic models reference.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the data model |
| `catalog` | string | No | Database/catalog name (for 3-part naming) |
| `schema` | string | Yes | Schema name |
| `table` | string | Yes | Table name |
| `connection` | string | No | Connection type: `redshift`, `starburst`, `postgres`, `duckdb`. Defaults to `redshift` |

### Example

```yaml
data_models:
  - name: rentals
    schema: gold_production
    table: rentals
    connection: redshift

  - name: events
    catalog: analytics
    schema: silver
    table: user_events
    connection: starburst
```

---

## Semantic Models

Semantic models are the core abstraction - they define dimensions, measures, and entities on top of a data model.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the semantic model |
| `description` | string | No | Human-readable description (supports multiline) |
| `model` | string | No | Reference to a data model name |
| `time_dimension` | string | No | Default time dimension for aggregations |
| `date_selector` | object | No | Date selector configuration |
| `entities` | list | No | List of entity definitions |
| `dimensions` | list | No | List of dimension definitions |
| `measures` | list | No | List of measure definitions |
| `meta` | object | No | Arbitrary metadata |

### Date Selector

The `date_selector` field enables date picker functionality for time dimensions.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dimensions` | list[string] | Yes | Time dimension names to include in date selector |

### Example

```yaml
semantic_models:
  - name: rentals
    description: |
      Core rental fact model - transaction-level data for rental analytics.
      Combines revenue, counts, segmentation, and timing data.
    model: rentals
    time_dimension: created_at

    date_selector:
      dimensions: [created_at, starts_at]

    entities:
      - # entity definitions

    dimensions:
      - # dimension definitions

    measures:
      - # measure definitions
```

---

## Entities

Entities define join keys (primary keys, foreign keys) that connect semantic models.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the entity |
| `type` | string | Yes | Entity type: `primary`, `foreign`, or `unique` |
| `expr` | string | Yes | SQL expression for the key column |
| `label` | string | No | Display label |
| `complete` | boolean | No | For foreign keys: `true` means all rows have valid FK values (enables metric exposure in joined explores). Defaults to `false` |

### Entity Types

- **primary**: The main identifier for the model (one per model)
- **foreign**: A reference to another model's primary key
- **unique**: An alternative unique identifier

### Example

```yaml
entities:
  # Primary entity
  - name: rental
    type: primary
    expr: unique_rental_sk
    label: Reservation

  # Foreign key (incomplete - not all rentals have facilities)
  - name: facility
    type: foreign
    expr: facility_sk

  # Foreign key (complete - every review has a rental)
  - name: rental
    type: foreign
    expr: unique_rental_sk
    complete: true
```

---

## Dimensions

Dimensions are categorical or time-based attributes used for grouping and filtering.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier |
| `type` | string | Yes | `categorical` or `time` |
| `label` | string | No | Display label |
| `description` | string | No | Human-readable description |
| `expr` | string | Conditional | SQL expression (required unless `variants` is specified) |
| `group` | string | No | Grouping for organization (supports dot notation: `Sales.Revenue`) |
| `hidden` | boolean | No | Hide from BI users. Defaults to `false` |
| `meta` | object | No | Arbitrary metadata |

### Time-Specific Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `granularity` | string | No | Time granularity: `hour`, `day`, `week`, `month`, `quarter`, `year` |
| `primary_variant` | string | No | Default variant name when using timezone variants |
| `variants` | object | No | Map of variant name to SQL expression (for UTC/local pairs) |

### Timezone Variants

For time dimensions that need multiple timezone representations:

```yaml
- name: created_at
  type: time
  granularity: day
  primary_variant: utc
  variants:
    utc: rental_created_at_utc
    local: rental_created_at_local
```

When `variants` is specified, `expr` is not required. The `primary_variant` determines which variant is used as the default.

### Examples

```yaml
dimensions:
  # Simple categorical dimension
  - name: rental_segment
    label: Primary Segment
    description: Hierarchical segment (Monthly > Event > Airport > Transient)
    type: categorical
    expr: rental_segment_rollup
    group: Segment

  # Time dimension with granularity
  - name: created_at
    label: Rental Created
    type: time
    granularity: day
    expr: rental_created_at
    group: Dates

  # Time dimension with timezone variants
  - name: starts_at
    label: Rental Start
    description: When the parking period begins
    type: time
    granularity: hour
    group: Dates
    primary_variant: utc
    variants:
      utc: rental_starts_at_utc
      local: rental_starts_at_local

  # Boolean/flag dimension
  - name: is_monthly_rental
    label: Is Monthly
    type: categorical
    expr: is_monthly_rental
    group: Segment

  # Hidden dimension (used internally)
  - name: facility_created_at
    type: time
    granularity: day
    expr: facility_created_at
    hidden: true
```

---

## Measures

Measures are aggregatable numeric values. They define the raw aggregations that metrics build upon.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier |
| `agg` | string | Yes | Aggregation type |
| `expr` | string | Yes | SQL expression |
| `label` | string | No | Display label |
| `description` | string | No | Human-readable description |
| `format` | string | No | Value format: `usd`, `decimal_0`, `decimal_1`, `decimal_2`, `percent_0`, `percent_1`, `percent_2` |
| `group` | string | No | Grouping for organization |
| `hidden` | boolean | No | Hide from BI users. Defaults to `false` |
| `meta` | object | No | Arbitrary metadata |

### Aggregation Types

| Value | Description |
|-------|-------------|
| `sum` | Sum of values |
| `count` | Count of rows |
| `count_distinct` | Count of distinct values |
| `average` | Average (mean) of values |
| `min` | Minimum value |
| `max` | Maximum value |
| `median` | Median value |
| `percentile` | Percentile calculation |

### Examples

```yaml
measures:
  # Sum aggregation
  - name: checkout_amount
    label: Checkout Amount
    description: Sum of checkout amounts (what customer pays)
    agg: sum
    expr: rental_checkout_amount_local
    format: usd
    hidden: true

  # Count distinct
  - name: rental_count
    label: Rental Count
    agg: count_distinct
    expr: unique_rental_sk
    format: decimal_0
    hidden: true

  # Complex expression
  - name: display_amount
    label: Display Amount
    description: Sum of display prices (excludes SpotHero fees)
    agg: sum
    expr: rental_checkout_amount_local - coalesce(total_spothero_fee_amount, 0)
    format: usd
    hidden: true

  # Average
  - name: avg_star_rating
    label: Average Star Rating
    agg: average
    expr: star_rating
    format: decimal_1
    hidden: true
```

---

## Metrics

Metrics are business-level measures with semantic meaning. They can have period-over-period (PoP) variants automatically generated.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier |
| `type` | string | Yes | Metric type: `simple`, `derived`, or `ratio` |
| `label` | string | No | Display label |
| `description` | string | No | Human-readable description |
| `format` | string | No | Value format (same options as measures) |
| `group` | string | No | Grouping for organization |
| `entity` | string | No | Associated entity (determines which model owns this metric) |
| `filter` | object | No | Filter conditions |
| `pop` | object | No | Period-over-period configuration |
| `meta` | object | No | Arbitrary metadata |

### Metric Types

#### Simple Metrics

Reference a single measure directly.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `measure` | string | Yes | Name of the measure to aggregate |

```yaml
- name: rental_count
  label: Rental Count
  type: simple
  measure: rental_count
  format: decimal_0
  entity: rental
```

#### Derived Metrics

Compute from other metrics using a SQL expression.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `expr` | string | Yes | SQL expression referencing other metrics |
| `metrics` | list[string] | Yes | List of metric dependencies |

```yaml
- name: aov
  label: Average Order Value
  description: Average checkout amount per completed rental
  type: derived
  expr: gov / NULLIF(rental_count, 0)
  metrics: [gov, rental_count]
  format: usd
  entity: rental
```

#### Ratio Metrics

Compute a ratio of two metrics.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `numerator` | string | Yes | Numerator metric name |
| `denominator` | string | Yes | Denominator metric name |

```yaml
- name: conversion_rate
  label: Conversion Rate
  type: ratio
  numerator: purchases
  denominator: visits
  format: percent_2
  entity: session
```

### Period-over-Period (PoP) Configuration

The `pop` field automatically generates time comparison variants.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `comparisons` | list[string] | Yes | Comparison periods |
| `outputs` | list[string] | Yes | Output types |

#### Comparison Periods

| Value | Description |
|-------|-------------|
| `py` | Prior Year |
| `pm` | Prior Month |
| `pq` | Prior Quarter |
| `pw` | Prior Week |

#### Output Types

| Value | Description | Suffix Generated |
|-------|-------------|------------------|
| `previous` | The prior period value | `_py`, `_pm`, `_pq`, `_pw` |
| `change` | Absolute difference | `_py_change`, `_pm_change`, etc. |
| `pct_change` | Relative percentage change | `_py_pct_change`, `_pm_pct_change`, etc. |

### Example with PoP

```yaml
- name: gov
  label: Gross Order Value
  description: Total checkout revenue from completed rentals
  type: simple
  measure: checkout_amount
  filter:
    transaction_type: completed
  pop:
    comparisons: [py, pm]
    outputs: [previous, pct_change]
  format: usd
  group: Revenue
  entity: rental
```

This generates the following variants:
- `gov` - Base metric
- `gov_py` - Prior year value
- `gov_py_pct_change` - Year-over-year percent change
- `gov_pm` - Prior month value
- `gov_pm_pct_change` - Month-over-month percent change

---

## Filters

Filters restrict metrics to specific conditions. Filters are specified as a dictionary.

### Filter Syntax

| Format | Interpretation | Example |
|--------|---------------|---------|
| `field: value` | Equals | `status: completed` |
| `field: [a, b, c]` | IN list | `type: [sale, refund]` |
| `field: '>10'` | Greater than | `amount: '>10'` |
| `field: '>=10'` | Greater than or equal | `amount: '>=10'` |
| `field: '<100'` | Less than | `quantity: '<100'` |
| `field: '<=100'` | Less than or equal | `quantity: '<=100'` |
| `field: '!=cancelled'` | Not equals | `status: '!=cancelled'` |

### Examples

```yaml
# Simple equality filter
filter:
  transaction_type: completed

# IN filter
filter:
  rental_segment: [monthly, transient]

# Comparison filter
filter:
  checkout_amount: '>0'

# Multiple conditions (AND)
filter:
  transaction_type: completed
  is_active: true
```

---

## Explores

Explores define how semantic models are joined for BI tool presentation. This is LookML-specific configuration.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier |
| `fact_model` | string | Yes | Primary semantic model name |
| `label` | string | No | Display label |

### Example

```yaml
explores:
  - name: rentals
    fact_model: rentals
    label: Rental Analytics
```

---

## Complete Example

Here is a complete example showing all components working together:

```yaml
version: 2

data_models:
  - name: rentals
    schema: gold_production
    table: rentals
    connection: redshift

semantic_models:
  - name: rentals
    description: |
      Core rental fact model - transaction-level data for rental analytics.
      Combines revenue, counts, segmentation, and timing data.
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
      # Time with UTC/local variants
      - name: created_at
        label: Rental Created
        description: When the rental was created
        type: time
        granularity: day
        group: Dates
        primary_variant: utc
        variants:
          utc: rental_created_at_utc
          local: rental_created_at_local

      - name: starts_at
        label: Rental Start
        type: time
        granularity: hour
        group: Dates
        primary_variant: utc
        variants:
          utc: rental_starts_at_utc
          local: rental_starts_at_local

      # Categorical dimensions
      - name: transaction_type
        label: Order Status
        description: Order fulfillment status
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
        label: Checkout Amount
        agg: sum
        expr: rental_checkout_amount_local
        format: usd
        hidden: true

      - name: rental_count
        label: Rental Count
        agg: count_distinct
        expr: unique_rental_sk
        format: decimal_0
        hidden: true

metrics:
  - name: gov
    label: Gross Order Value
    description: Total checkout revenue from completed rentals
    type: simple
    measure: checkout_amount
    filter:
      transaction_type: completed
    pop:
      comparisons: [py, pm]
      outputs: [previous, pct_change]
    format: usd
    group: Revenue
    entity: rental

  - name: rental_count
    label: Rental Count
    description: Count of completed rental transactions
    type: simple
    measure: rental_count
    filter:
      transaction_type: completed
    pop:
      comparisons: [py, pm]
      outputs: [previous, pct_change]
    format: decimal_0
    group: Counts
    entity: rental

  - name: aov
    label: Average Order Value
    description: Average checkout amount per completed rental
    type: derived
    expr: gov / NULLIF(rental_count, 0)
    metrics: [gov, rental_count]
    format: usd
    group: Revenue
    entity: rental

explores:
  - name: rentals
    fact_model: rentals
    label: Rental Analytics
```

---

## File Organization

You can organize your YAML files in several ways:

### Single File (Simple)

```
semantic_layer/
└── rentals.yml          # Everything in one file
```

### Split by Model

```
semantic_layer/
├── rentals.yml          # rentals data_model + semantic_model + metrics
├── facilities.yml       # facilities data_model + semantic_model
└── reviews.yml          # reviews data_model + semantic_model + metrics
```

### Split by Type

```
semantic_layer/
├── models/
│   ├── rentals.yml      # data_model + semantic_model
│   └── facilities.yml
└── metrics/
    └── rental_metrics.yml  # metrics only
```

The loader recursively finds all YAML files, so use whatever organization works best for your team.
