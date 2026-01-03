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

### PDT Alternative

For large dimension groups or performance-critical scenarios, can combine with PDT approach:

1. Generate dbt CUBE model from dimension groups
2. Generate join with dynamic `sql_on` instead of subqueries
3. Benchmark measures become simple references to PDT columns

```yaml
benchmark_config:
  strategy: pdt  # or 'subquery' (default)
  pdt_model: rental_benchmarks
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
