# Semantic Model to LookML Conversion Rules

This document describes how dbt semantic layer concepts are translated to LookML.

## Entity Conversion

All entities become dimensions with `hidden: yes` since they typically represent surrogate keys.

| Entity Type | LookML Output |
|-------------|---------------|
| Primary | `dimension` with `primary_key: yes` + `hidden: yes` |
| Foreign | `dimension` with `hidden: yes` (used for joins) |
| Unique | `dimension` with `hidden: yes` |

**Note**: Natural keys should be exposed as regular dimensions instead of entities.

## Dimension Conversion

| dbt Type | LookML Type |
|----------|-------------|
| `categorical` | `dimension` (type: string) |
| `time` | `dimension_group` (type: time) |

### Time Dimensions

Automatically generate appropriate timeframes based on `type_params.time_granularity`:

| Granularity | Timeframes |
|-------------|------------|
| `day` | `[date, week, month, quarter, year]` |
| `week` | `[week, month, quarter, year]` |
| `month` | `[month, quarter, year]` |

## Smart Measure Optimization (DTL-036)

The generator uses smart optimization to minimize redundant LookML measures:

### Simple Metrics → Direct Aggregates

Simple metrics generate **directly as aggregate measures** (not `type: number` wrappers):

```yaml
# dbt input
measures:
  - name: total_revenue
    agg: sum
metrics:
  - name: rental_revenue
    type: simple
    type_params:
      measure: total_revenue
```

```lookml
# LookML output (single measure, no hidden wrapper)
measure: rental_revenue {
  type: sum  # Direct aggregation
  sql: ${TABLE}.amount ;;
}
```

### Hidden Measures

Hidden `_measure` versions are **only created** when:
- A measure is used by a **complex metric** (ratio/derived), AND
- That measure does **not** have a simple metric exposing it

Measures are **excluded** from LookML if:
- They have a simple metric (the simple metric provides the visible aggregate)
- They're not used by any metric at all (orphaned)

### Aggregation Type Mapping

| dbt Aggregation | LookML Type |
|-----------------|-------------|
| `sum` | `sum` |
| `count` | `count` |
| `count_distinct` | `count_distinct` |
| `average` | `average` |
| `min` | `min` |
| `max` | `max` |
| `median` | `median` |

See `types.py:LOOKML_TYPE_MAP` for full mapping.

## Metric Conversion

### Simple Metrics

- Generate as **direct aggregate measures** (type: sum, count, etc.)
- Use the source measure's SQL and aggregation type
- **Visible** (no `hidden: yes`)
- `view_label: "  Metrics"` for organization

### Complex Metrics (Ratio/Derived)

- Generate as `type: number` measures
- Reference other measures in SQL expressions
- **Visible** (no `hidden: yes`)

| Type | SQL Generation |
|------|----------------|
| Simple | Direct aggregation (no reference needed) |
| Ratio | `${visible_metric} / NULLIF(${other_metric}, 0)` |
| Derived | Expression referencing visible metrics |

### Reference Resolution

Complex metrics reference **visible simple metrics** when available:
```lookml
# gross_merchandise_value references the visible total_revenue metric
measure: gross_merchandise_value {
  type: number
  sql: ${total_revenue} - ${total_spothero_fees} ;;
}
```

## Hierarchy Labels

3-tier hierarchy for organizing fields in Looker's field picker:

```yaml
config:
  meta:
    hierarchy:
      entity: "user"           # → view_label for dimensions
      category: "demographics" # → group_label for dimensions, view_label for measures
      subcategory: "location"  # → group_label for measures
```

**Implementation**:
- `Dimension.get_dimension_labels()` in `schemas/semantic_layer.py`
- `Measure.get_measure_labels()` in `schemas/semantic_layer.py`

## Translation Architecture

```
schemas/semantic_layer.py          # dbt data model (format-agnostic)
        ↓
generators/lookml.py               # LookML-specific naming:
                                   # - view_prefix
                                   # - explore_prefix
                                   # - measure_suffix (_measure)
        ↓
.view.lkml / explores.lkml         # Output files
```

**Key Principle**: Semantic layer models remain format-agnostic. All LookML-specific naming conventions are owned by `LookMLGenerator`.
