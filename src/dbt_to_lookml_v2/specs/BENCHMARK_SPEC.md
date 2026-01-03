# Benchmark Measures Specification

> **Status:** Phase 5 Planning
> **Last Updated:** 2026-01-02

## Overview

Benchmark measures provide "total" or "rolled-up" comparisons that ignore certain filters while optionally correlating on selected dimensions. This spec outlines three implementation options.

---

## Core Concepts

### Dimension Groups

Reusable groupings of related dimensions:

```yaml
dimension_groups:
  geography:
    - reporting_market
    - reporting_region
    - reporting_neighborhood

  segment:
    - rental_segment_rollup
    - rental_segment
    - temporal_segment

  time:
    - created_at
    - starts_at
```

### Correlation Behavior

| Type | Behavior |
|------|----------|
| No correlation | Grand total - ignores all filters/selections |
| Explicit dim | Always correlate on this specific dimension |
| Dynamic group | Correlate on whichever dim from group is `_is_selected` |

---

## Option A: Pre-defined Benchmark Levels

User selects from a dropdown of pre-defined aggregation levels.

### 1. How It's Defined (Developer)

```yaml
# semantic_models/rentals.yml

dimension_groups:
  geography:
    - reporting_market
    - reporting_region
    - reporting_neighborhood
  segment:
    - rental_segment_rollup
    - rental_segment

semantic_models:
  - name: rentals

    # Define benchmark levels for this model
    benchmark_levels:
      - name: total
        label: "SpotHero Total"
        correlate_on: []

      - name: geo
        label: "Geography Total"
        correlate_on: [geography]  # Dynamic within group

      - name: segment
        label: "Segment Total"
        correlate_on: [segment]

      - name: market_only
        label: "Market Total"
        correlate_on: [reporting_market]  # Explicit single dim

      - name: geo_segment
        label: "Geo & Segment"
        correlate_on: [geography, segment]

metrics:
  - name: gmv
    type: simple
    measure: total_gmv
    benchmarks: [total, geo, segment]  # Which levels to generate

  - name: rental_count
    type: simple
    measure: rental_count
    benchmarks: [total, market_only]  # Different levels

  - name: aov
    type: derived
    benchmarks: false  # No benchmarks for this metric
```

### 2. How It's Used (End User in Looker)

**Generated LookML:**

```lookml
# Parameter for level selection
parameter: benchmark_level {
  label: "Benchmark Comparison"
  type: unquoted
  default_value: "total"
  allowed_value: { value: "total" label: "SpotHero Total" }
  allowed_value: { value: "geo" label: "Geography Total" }
  allowed_value: { value: "segment" label: "Segment Total" }
}

# Single measure that switches based on parameter
measure: gmv_benchmark {
  label: "GMV (Benchmark)"
  type: number
  sql:
    CASE {% parameter benchmark_level %}
      WHEN 'total' THEN ${gmv_total}
      WHEN 'geo' THEN ${gmv_geo}
      WHEN 'segment' THEN ${gmv_segment}
    END ;;
}

# Hidden measures for each level
measure: gmv_total {
  hidden: yes
  type: number
  sql: (
    SELECT SUM(rental_checkout_amount_local)
    FROM ${rentals.SQL_TABLE_NAME} subq
    WHERE subq.rental_event_type = 'completed'
      AND {% condition benchmark_date_filter %} subq.rental_created_at_utc {% endcondition %}
  ) ;;
}

measure: gmv_geo {
  hidden: yes
  type: number
  sql: (
    SELECT SUM(rental_checkout_amount_local)
    FROM ${rentals.SQL_TABLE_NAME} subq
    WHERE subq.rental_event_type = 'completed'
      AND {% condition benchmark_date_filter %} subq.rental_created_at_utc {% endcondition %}
      {% if reporting_market._is_selected %}
        AND subq.reporting_market = ${TABLE}.reporting_market
      {% endif %}
      {% if reporting_region._is_selected %}
        AND subq.reporting_region = ${TABLE}.reporting_region
      {% endif %}
      {% if reporting_neighborhood._is_selected %}
        AND subq.reporting_neighborhood = ${TABLE}.reporting_neighborhood
      {% endif %}
  ) ;;
}
```

**User Experience:**
1. User sees "Benchmark Comparison" dropdown in Looker
2. Selects "Geography Total"
3. Adds `gmv_benchmark` to their report
4. Gets market/region/neighborhood total based on what's in their GROUP BY

### 3. How to Add/Change (Maintenance)

**Add a new benchmark level:**
```yaml
benchmark_levels:
  # ... existing levels ...

  - name: channel          # ← Add new level
    label: "Channel Total"
    correlate_on: [booking_channel]
```

**Add to a metric:**
```yaml
metrics:
  - name: gmv
    benchmarks: [total, geo, segment, channel]  # ← Add 'channel'
```

**Regenerate:** Run d2l to regenerate LookML.

### Pros/Cons

| Pros | Cons |
|------|------|
| Clean dropdown UI | Must pre-define all combinations |
| Predictable behavior | N levels × M metrics = many hidden measures |
| Easy to understand | Adding new level requires regeneration |

---

## Option B: Toggle Parameters (Full Runtime Flexibility)

User toggles individual dimensions on/off for correlation.

### 1. How It's Defined (Developer)

```yaml
semantic_models:
  - name: rentals

    # Define which dimensions can be correlated
    benchmark_config:
      enabled: true
      correlatable_dimensions:
        - name: reporting_market
          label: "Market"
          default: false

        - name: reporting_region
          label: "Region"
          default: false

        - name: rental_segment_rollup
          label: "Segment"
          default: false

metrics:
  - name: gmv
    benchmarks: true  # Just a flag - uses model's correlatable_dimensions

  - name: rental_count
    benchmarks: true

  - name: aov
    benchmarks: false
```

### 2. How It's Used (End User in Looker)

**Generated LookML:**

```lookml
# One toggle per correlatable dimension
parameter: correlate_on_market {
  label: "Pin to Market"
  type: yesno
  default_value: "no"
}

parameter: correlate_on_region {
  label: "Pin to Region"
  type: yesno
  default_value: "no"
}

parameter: correlate_on_segment {
  label: "Pin to Segment"
  type: yesno
  default_value: "no"
}

# Single benchmark measure per metric
measure: gmv_benchmark {
  label: "GMV (Benchmark)"
  type: number
  sql: (
    SELECT SUM(rental_checkout_amount_local)
    FROM ${rentals.SQL_TABLE_NAME} subq
    WHERE subq.rental_event_type = 'completed'
      AND {% condition benchmark_date_filter %} subq.rental_created_at_utc {% endcondition %}

      {% if correlate_on_market._parameter_value == 'yes' %}
        AND subq.reporting_market = ${TABLE}.reporting_market
      {% endif %}

      {% if correlate_on_region._parameter_value == 'yes' %}
        AND subq.reporting_region = ${TABLE}.reporting_region
      {% endif %}

      {% if correlate_on_segment._parameter_value == 'yes' %}
        AND subq.rental_segment_rollup = ${TABLE}.rental_segment_rollup
      {% endif %}
  ) ;;
}

measure: rental_count_benchmark {
  label: "Rental Count (Benchmark)"
  type: number
  sql: (
    SELECT COUNT(DISTINCT unique_rental_sk)
    FROM ${rentals.SQL_TABLE_NAME} subq
    WHERE subq.rental_event_type = 'completed'
      AND {% condition benchmark_date_filter %} subq.rental_created_at_utc {% endcondition %}

      {% if correlate_on_market._parameter_value == 'yes' %}
        AND subq.reporting_market = ${TABLE}.reporting_market
      {% endif %}

      {% if correlate_on_region._parameter_value == 'yes' %}
        AND subq.reporting_region = ${TABLE}.reporting_region
      {% endif %}

      {% if correlate_on_segment._parameter_value == 'yes' %}
        AND subq.rental_segment_rollup = ${TABLE}.rental_segment_rollup
      {% endif %}
  ) ;;
}
```

**User Experience:**
1. User sees toggle switches: "Pin to Market", "Pin to Region", "Pin to Segment"
2. Toggles on "Pin to Market" and "Pin to Segment"
3. `gmv_benchmark` now shows total for their specific market + segment combination
4. Can change toggles without regenerating anything

### 3. How to Add/Change (Maintenance)

**Add a new correlatable dimension:**
```yaml
benchmark_config:
  correlatable_dimensions:
    # ... existing dims ...

    - name: booking_channel    # ← Add new dim
      label: "Channel"
      default: false
```

**Regenerate:** Run d2l - adds new toggle parameter, updates all benchmark measures.

**Change defaults:**
```yaml
- name: reporting_market
  label: "Market"
  default: true  # ← Now on by default
```

### Pros/Cons

| Pros | Cons |
|------|------|
| Full runtime flexibility | UI clutter (many toggles) |
| One measure per metric | Can create confusing combinations |
| Any combination possible | User must understand what toggles do |

---

## Option C: Group Toggle Parameters (Recommended)

User toggles dimension groups on/off. Within each group, correlation is dynamic based on `_is_selected`.

### 1. How It's Defined (Developer)

```yaml
# Define dimension groups
dimension_groups:
  geography:
    label: "Geography"
    dimensions:
      - reporting_market
      - reporting_region
      - reporting_neighborhood

  segment:
    label: "Segment"
    dimensions:
      - rental_segment_rollup
      - rental_segment
      - temporal_segment

  time:
    label: "Time Period"
    dimensions:
      - created_at
      - starts_at

semantic_models:
  - name: rentals

    benchmark_config:
      enabled: true

      # Which groups can be toggled
      correlatable_groups: [geography, segment]

      # Optional: explicit dims always correlated (not toggleable)
      always_correlate: []

      # Optional: default state
      defaults:
        geography: false
        segment: false

metrics:
  - name: gmv
    benchmarks: true

  - name: rental_count
    benchmarks: true

  - name: aov
    benchmarks:
      enabled: true
      # Override: only allow segment correlation for this metric
      correlatable_groups: [segment]
```

### 2. How It's Used (End User in Looker)

**Generated LookML:**

```lookml
# One toggle per GROUP (not per dimension)
parameter: correlate_geography {
  label: "Correlate on Geography"
  description: "When enabled, benchmark will match your selected geography (market, region, or neighborhood)"
  type: yesno
  default_value: "no"
}

parameter: correlate_segment {
  label: "Correlate on Segment"
  description: "When enabled, benchmark will match your selected segment"
  type: yesno
  default_value: "no"
}

# Single benchmark measure per metric
measure: gmv_benchmark {
  label: "GMV (Benchmark)"
  group_label: "Benchmarks"
  description: "Company-wide GMV. Use correlation toggles to pin to geography/segment."
  type: number
  value_format_name: usd
  sql: (
    SELECT SUM(rental_checkout_amount_local)
    FROM ${rentals.SQL_TABLE_NAME} subq
    WHERE subq.rental_event_type = 'completed'
      AND {% condition benchmark_date_filter %} subq.rental_created_at_utc {% endcondition %}

      -- Geography group: dynamic correlation when toggle is ON
      {% if correlate_geography._parameter_value == 'yes' %}
        {% if reporting_market._is_selected %}
          AND subq.reporting_market = ${TABLE}.reporting_market
        {% endif %}
        {% if reporting_region._is_selected %}
          AND subq.reporting_region = ${TABLE}.reporting_region
        {% endif %}
        {% if reporting_neighborhood._is_selected %}
          AND subq.reporting_neighborhood = ${TABLE}.reporting_neighborhood
        {% endif %}
      {% endif %}

      -- Segment group: dynamic correlation when toggle is ON
      {% if correlate_segment._parameter_value == 'yes' %}
        {% if rental_segment_rollup._is_selected %}
          AND subq.rental_segment_rollup = ${TABLE}.rental_segment_rollup
        {% endif %}
        {% if rental_segment._is_selected %}
          AND subq.rental_segment = ${TABLE}.rental_segment
        {% endif %}
        {% if temporal_segment._is_selected %}
          AND subq.temporal_segment = ${TABLE}.temporal_segment
        {% endif %}
      {% endif %}
  ) ;;
}
```

**User Experience:**

**Scenario 1: Grand Total**
- Both toggles OFF
- Query: `GROUP BY reporting_market, rental_segment_rollup`
- `gmv_benchmark` = SpotHero total (ignores market and segment)

**Scenario 2: Market Total**
- Geography toggle ON, Segment toggle OFF
- Query: `GROUP BY reporting_market, rental_segment_rollup`
- `gmv_benchmark` = Total for each market (correlates on market, ignores segment)

**Scenario 3: Market + Segment Total**
- Both toggles ON
- Query: `GROUP BY reporting_market, rental_segment_rollup`
- `gmv_benchmark` = Total for each market+segment combination

**Scenario 4: Dynamic Geography**
- Geography toggle ON
- Query 1: `GROUP BY reporting_market` → correlates on market
- Query 2: `GROUP BY reporting_neighborhood` → correlates on neighborhood
- Same toggle, different dimension - automatically uses what's selected

### 3. How to Add/Change (Maintenance)

**Add a dimension to existing group:**
```yaml
dimension_groups:
  geography:
    dimensions:
      - reporting_market
      - reporting_region
      - reporting_neighborhood
      - reporting_dma           # ← Add new dim to group
```
Regenerate. The toggle now includes the new dimension automatically.

**Add a new group:**
```yaml
dimension_groups:
  # ... existing groups ...

  channel:                      # ← New group
    label: "Channel"
    dimensions:
      - booking_channel
      - device_type
      - traffic_source

semantic_models:
  - name: rentals
    benchmark_config:
      correlatable_groups: [geography, segment, channel]  # ← Add group
```
Regenerate. New toggle appears: "Correlate on Channel".

**Change defaults:**
```yaml
benchmark_config:
  defaults:
    geography: true   # ← Now on by default
    segment: false
```

**Metric-level override:**
```yaml
metrics:
  - name: conversion_rate
    benchmarks:
      enabled: true
      correlatable_groups: [segment]  # ← Only segment, no geography
```

### Pros/Cons

| Pros | Cons |
|------|------|
| Clean UI (few toggles) | Groups must be pre-defined |
| Dynamic within groups | Slightly more complex to understand |
| One measure per metric | - |
| Best of both worlds | - |
| Easy to add dims to groups | - |

---

## Comparison Matrix

| Aspect | Option A (Levels) | Option B (Dim Toggles) | Option C (Group Toggles) |
|--------|-------------------|------------------------|--------------------------|
| **UI Elements** | 1 dropdown | N toggles (one per dim) | N toggles (one per group) |
| **Measures Generated** | N levels × M metrics | 1 per metric | 1 per metric |
| **Runtime Flexibility** | Pick from list | Any combination | Group-level |
| **Maintenance** | Add level, regenerate | Add dim, regenerate | Add dim to group, regenerate |
| **User Understanding** | Simple | Complex | Medium |
| **Generated LookML Size** | Large | Small | Small |
| **Query Complexity** | Multiple subqueries | Single subquery | Single subquery |

---

## Recommended Approach: Option C

**Why:**
1. **Clean UX** - 2-3 toggles vs 6-10 dimension toggles
2. **Efficient generation** - One measure per metric
3. **Dynamic behavior** - `_is_selected` handles which dim within group
4. **Maintainable** - Add dims to groups without changing metrics
5. **Intuitive** - "Pin to Geography" is clearer than "Pin to Market + Pin to Region + Pin to Neighborhood"

---

## Implementation Notes

### Required Components

1. **Schema additions:**
   - `dimension_groups` in model YAML
   - `benchmark_config` in semantic model
   - `benchmarks` flag/config in metrics

2. **Domain types:**
   - `DimensionGroup`
   - `BenchmarkConfig`
   - `CorrelatableGroup`

3. **Renderer:**
   - `BenchmarkRenderer` - generates toggle parameters + benchmark measures
   - Integrates with `ViewRenderer`

4. **Generator updates:**
   - New file: `{model}.benchmarks.view.lkml` (refinement)

---

## Materialization Strategies

The subquery approach (shown above) runs a correlated subquery for every benchmark measure. This works but can be slow at scale. For better performance, we support pre-computed materialization.

### Strategy Comparison

| Strategy | Refresh | Speed | Infrastructure | Best For |
|----------|---------|-------|----------------|----------|
| `subquery` | Real-time | Slow (correlated query per row) | None | Small datasets, prototyping |
| `view` | Real-time | Slow (CUBE runs every query) | None | When real-time is critical |
| `dbt_table` | dbt run | Fast | dbt job | Most production use cases |
| `dbt_incremental` | dbt run (append) | Fast | dbt job | Large tables, frequent refresh |
| `materialized_view` | DB-managed | Fast | DB feature | When dbt isn't available |
| `looker_pdt` | Looker-managed | Fast | Looker persistence | Looker-only shops |

### Recommended: dbt Table/Incremental

For Option C, the recommended approach is:

```yaml
benchmark_config:
  enabled: true
  strategy: dbt_table          # or 'dbt_incremental'
  refresh: hourly              # for scheduling (dbt Cloud / Airflow)
  model_name: rental_benchmarks
  correlatable_groups: [geography, segment]
```

### What Gets Generated

**1. dbt CUBE Model (one per semantic model with benchmarks)**

```sql
-- models/benchmarks/rental_benchmarks.sql
{{ config(
    materialized='incremental',
    unique_key=['date_day', 'reporting_market', 'reporting_region',
                'reporting_neighborhood', 'rental_segment_rollup',
                'rental_segment', 'temporal_segment'],
    incremental_strategy='merge'
) }}

SELECT
    date_day,

    -- Geography group: COALESCE with sentinel for rollups
    COALESCE(reporting_market, '__ALL__') as reporting_market,
    COALESCE(reporting_region, '__ALL__') as reporting_region,
    COALESCE(reporting_neighborhood, '__ALL__') as reporting_neighborhood,

    -- Segment group
    COALESCE(rental_segment_rollup, '__ALL__') as rental_segment_rollup,
    COALESCE(rental_segment, '__ALL__') as rental_segment,
    COALESCE(temporal_segment, '__ALL__') as temporal_segment,

    -- Pre-aggregated measures
    SUM(rental_checkout_amount_local) as benchmark_gmv,
    SUM(driver_payout) as benchmark_gov,
    COUNT(DISTINCT unique_rental_sk) as benchmark_rental_count

FROM {{ ref('rentals') }}
WHERE rental_event_type = 'completed'

{% if is_incremental() %}
    AND date_day >= (SELECT MAX(date_day) - INTERVAL '3 days' FROM {{ this }})
{% endif %}

GROUP BY CUBE(
    reporting_market, reporting_region, reporting_neighborhood,
    rental_segment_rollup, rental_segment, temporal_segment
), date_day
```

**Row Count Estimation:**
- 2^6 = 64 combinations per date
- 730 days (2 years) = ~47K rows
- Fast to build, fast to query

**2. LookML View for Benchmark Table (trivial)**

```lookml
# rental_benchmarks.view.lkml
view: rental_benchmarks {
  sql_table_name: ${ref('rental_benchmarks')} ;;

  dimension: date_day { type: date }
  dimension: reporting_market { type: string }
  dimension: reporting_region { type: string }
  # ... all dims ...

  # Pre-aggregated measures - just SUM the pre-computed values
  measure: benchmark_gmv {
    type: sum
    sql: ${TABLE}.benchmark_gmv ;;
  }

  measure: benchmark_rental_count {
    type: sum
    sql: ${TABLE}.benchmark_rental_count ;;
  }
}
```

**3. Dynamic Join (correlation logic defined ONCE)**

```lookml
# rentals.explore.lkml
explore: rentals {
  extends: [_benchmark_utils]  # Inherits toggle parameters

  join: rental_benchmarks {
    type: left_outer
    relationship: many_to_one

    sql_on:
      ${rentals.date_day} = ${rental_benchmarks.date_day}

      -- Geography group: correlate when toggle is ON + dim is selected
      AND ${rental_benchmarks.reporting_market} =
        {% if correlate_geography._parameter_value == 'yes' %}
          {% if rentals.reporting_market._is_selected %}
            ${rentals.reporting_market}
          {% else %}
            '__ALL__'
          {% endif %}
        {% else %}
          '__ALL__'
        {% endif %}

      AND ${rental_benchmarks.reporting_region} =
        {% if correlate_geography._parameter_value == 'yes' %}
          {% if rentals.reporting_region._is_selected %}
            ${rentals.reporting_region}
          {% else %}
            '__ALL__'
          {% endif %}
        {% else %}
          '__ALL__'
        {% endif %}

      AND ${rental_benchmarks.reporting_neighborhood} =
        {% if correlate_geography._parameter_value == 'yes' %}
          {% if rentals.reporting_neighborhood._is_selected %}
            ${rentals.reporting_neighborhood}
          {% else %}
            '__ALL__'
          {% endif %}
        {% else %}
          '__ALL__'
        {% endif %}

      -- Segment group
      AND ${rental_benchmarks.rental_segment_rollup} =
        {% if correlate_segment._parameter_value == 'yes' %}
          {% if rentals.rental_segment_rollup._is_selected %}
            ${rentals.rental_segment_rollup}
          {% else %}
            '__ALL__'
          {% endif %}
        {% else %}
          '__ALL__'
        {% endif %}

      -- ... remaining segment dims ...
    ;;
  }
}
```

**4. Benchmark Measures in View (dead simple)**

```lookml
# rentals.benchmarks.view.lkml (refinement)
view: +rentals {
  extends: [_benchmark_utils]  # Inherit toggle parameters

  measure: gmv_benchmark {
    label: "GMV (Benchmark)"
    group_label: "Benchmarks"
    description: "Company GMV total. Use correlation toggles to pin to geography/segment."
    type: sum
    sql: ${rental_benchmarks.benchmark_gmv} ;;
    value_format_name: usd
  }

  measure: rental_count_benchmark {
    label: "Rental Count (Benchmark)"
    group_label: "Benchmarks"
    type: sum
    sql: ${rental_benchmarks.benchmark_rental_count} ;;
  }

  measure: gov_benchmark {
    label: "GOV (Benchmark)"
    group_label: "Benchmarks"
    type: sum
    sql: ${rental_benchmarks.benchmark_gov} ;;
    value_format_name: usd
  }
}
```

**5. Shared Utils (generated once per project)**

```lookml
# _benchmark_utils.view.lkml
view: _benchmark_utils {
  extension: required

  # Shared correlation toggles
  parameter: correlate_geography {
    label: "Correlate on Geography"
    description: "When enabled, benchmark will match your selected geography"
    type: yesno
    default_value: "no"
  }

  parameter: correlate_segment {
    label: "Correlate on Segment"
    description: "When enabled, benchmark will match your selected segment"
    type: yesno
    default_value: "no"
  }

  # Shared date filter
  filter: benchmark_date_filter {
    type: date
    label: "Benchmark Date Range"
  }
}
```

### Why PDT is Better

| Subquery Approach | PDT + JOIN Approach |
|-------------------|---------------------|
| SQL in every measure | SQL defined once in join |
| Repetitive Liquid blocks | Liquid only in sql_on |
| Correlated subquery per row | Pre-computed join lookup |
| Slow queries | Sub-second queries |
| Real-time (but slow) | Refresh lag (but fast) |

### DRYing Up the sql_on with LookML Macros

The sql_on Liquid is still repetitive per dimension. We can DRY this up with a project-level macro:

```lookml
# _benchmark_macros.lkml (included in project manifest)

# Macro: correlation_condition
# Usage: {% include '_benchmark_macros' correlation_condition dim='reporting_market' group='geography' %}

# Unfortunately LookML doesn't support true macros, but we can use a pattern:
```

**Alternative: Generator-side templating**

Since LookML doesn't have real macros, we DRY up in the generator code itself:

```python
# In explore_generator.py

def render_correlation_condition(dim: str, group: str, base_view: str, benchmark_view: str) -> str:
    """Generate a single correlation condition for sql_on."""
    return f"""
      AND ${{{benchmark_view}.{dim}}} =
        {{% if correlate_{group}._parameter_value == 'yes' %}}
          {{% if {base_view}.{dim}._is_selected %}}
            ${{{base_view}.{dim}}}
          {{% else %}}
            '__ALL__'
          {{% endif %}}
        {{% else %}}
          '__ALL__'
        {{% endif %}}"""

def render_benchmark_join(config: BenchmarkConfig, base_view: str, benchmark_view: str) -> str:
    """Generate complete sql_on clause."""
    conditions = [f"${{{base_view}.date_day}} = ${{{benchmark_view}.date_day}}"]

    for group_name, group_dims in config.dimension_groups.items():
        if group_name in config.correlatable_groups:
            for dim in group_dims:
                conditions.append(
                    render_correlation_condition(dim, group_name, base_view, benchmark_view)
                )

    return "\n".join(conditions)
```

**Generated output is verbose, generator code is DRY.**

This is the right trade-off:
- Users see explicit, readable LookML
- Developers maintain simple generator code
- No runtime macro overhead

### Output File Structure

```
views/
├── _benchmark_utils.view.lkml     # Shared toggles (once per project)
├── rentals.view.lkml              # Base view (unchanged)
├── rentals.metrics.view.lkml      # Metric measures (unchanged)
├── rentals.benchmarks.view.lkml   # Benchmark measures (refinement)
├── rental_benchmarks.view.lkml    # PDT view for pre-computed data
├── facilities.view.lkml
├── facilities.metrics.view.lkml
└── facilities.benchmarks.view.lkml

explores/
├── rentals.explore.lkml           # Contains dynamic sql_on join

dbt/
├── models/
│   └── benchmarks/
│       ├── rental_benchmarks.sql  # CUBE model
│       └── facilities_benchmarks.sql
```

---

## Open Questions

1. **Cross-entity correlation:** How to handle dims from joined entities (e.g., `facility.reporting_market`)?
2. **Filter handling:** Should benchmarks respect non-GROUP BY filters? (Current: No - only `_is_selected`)
3. **Date filter:** Always required? Infer from model's `time_dimension`?
4. **Explore placement:** Benchmark toggles at explore level or view level?

---

## Next Steps

1. [ ] Finalize Option C schema
2. [ ] Add domain types for dimension groups and benchmark config
3. [ ] Implement BenchmarkRenderer
4. [ ] Add tests
5. [ ] Document for users
