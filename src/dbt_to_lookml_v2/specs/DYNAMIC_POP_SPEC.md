# Dynamic Period-over-Period (PoP) Specification

## Overview

This spec defines a new `DynamicFilteredPopStrategy` that generates PoP measures using SQL filtered measures with a user-selectable comparison period parameter, as an alternative to Looker's native `period_over_period` measure type.

### Motivation

Looker's native `period_over_period` has limitations:
- Only works with Redshift 2.1+, BigQuery, MySQL 8.0.12+, Snowflake
- Doesn't support custom calendars, cohort analysis, Looker Studio
- Can't use Liquid parameters in PoP definitions

The dynamic filtered approach:
- Works universally across all SQL dialects
- Integrates with our existing calendar/date selector infrastructure
- Reduces measure count (3 per metric vs 12+ with static variants)
- Gives users dynamic control over comparison period

---

## Architecture

### Strategy Selection

```
LookMLGenerator(pop_strategy=...)
    ├── LookerNativePopStrategy     # Existing: type: period_over_period
    └── DynamicFilteredPopStrategy  # New: filtered measures + parameter
```

Users select strategy at generation time:

```python
# Native PoP (current default)
generator = LookMLGenerator(pop_strategy=LookerNativePopStrategy())

# Dynamic filtered PoP (new)
generator = LookMLGenerator(pop_strategy=DynamicFilteredPopStrategy())
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `CalendarRenderer` | Enhanced to emit `date_range` filter, `comparison_period` parameter, period classification dimensions |
| `DynamicFilteredPopStrategy` | Generates filtered measures referencing calendar dimensions |
| `ExploreGenerator` | Coordinates calendar + PoP generation |
| `Dialect` (sqlglot) | Converts `DATEADD` to dialect-specific syntax |

---

## Calendar View Enhancements

### Current Output

```lookml
view: {explore}_explore_calendar {
  parameter: date_field { ... }
  dimension_group: calendar { ... }
}
```

### Enhanced Output (when PoP metrics exist)

```lookml
view: {explore}_explore_calendar {
  # ─────────────────────────────────────────────────────────────
  # DATE SELECTION (existing)
  # ─────────────────────────────────────────────────────────────
  parameter: date_field {
    view_label: " Calendar"
    label: "Analysis Date Field"
    type: unquoted
    default_value: "{default_date_option}"
    allowed_values: [ ... ]  # From date selector config
  }

  # ─────────────────────────────────────────────────────────────
  # DATE RANGE FILTER (new)
  # Unified filter for both display and PoP offset
  # ─────────────────────────────────────────────────────────────
  filter: date_range {
    view_label: " Calendar"
    label: "Date Range"
    type: date
    description: "Select date range for analysis. PoP comparisons offset from this range."
  }

  # ─────────────────────────────────────────────────────────────
  # COMPARISON PERIOD (new, only when PoP metrics exist)
  # ─────────────────────────────────────────────────────────────
  parameter: comparison_period {
    view_label: " Calendar"
    label: "Compare To"
    type: unquoted
    default_value: "none"
    allowed_values: [
      { label: "No Comparison" value: "none" }
      { label: "Prior Year" value: "year" }
      { label: "Prior Month" value: "month" }
      { label: "Prior Quarter" value: "quarter" }
      { label: "Prior Week" value: "week" }
    ]
  }

  # ─────────────────────────────────────────────────────────────
  # CALENDAR DIMENSION GROUP (existing, updated SQL)
  # ─────────────────────────────────────────────────────────────
  dimension_group: calendar {
    view_label: " Calendar"
    type: time
    timeframes: [date, week, month, quarter, year]
    convert_tz: no
    sql: {dynamic_date_case_statement} ;;
  }

  # ─────────────────────────────────────────────────────────────
  # PERIOD CLASSIFICATION DIMENSIONS (new)
  # Hidden - used by PoP filtered measures
  # ─────────────────────────────────────────────────────────────
  dimension: is_selected_period {
    hidden: yes
    type: yesno
    sql: {% condition date_range %} {dynamic_date_expr} {% endcondition %} ;;
  }

  dimension: is_comparison_period {
    hidden: yes
    type: yesno
    sql:
      {% if comparison_period._parameter_value != "'none'" %}
        {% condition date_range %}
          {dialect_dateadd}({% parameter comparison_period %}, 1, {dynamic_date_expr})
        {% endcondition %}
      {% else %}
        FALSE
      {% endif %}
    ;;
  }
}
```

### Dynamic Date Expression

The `{dynamic_date_expr}` is a CASE statement built from date options:

```sql
CASE {% parameter date_field %}
  WHEN 'rentals__created_at' THEN ${rentals.created_at_raw}
  WHEN 'rentals__starts_at' THEN ${rentals.starts_at_raw}
  WHEN 'facilities__opened_at' THEN ${facilities.opened_at_raw}
END
```

---

## PoP Measure Generation

### Trigger Condition

PoP measures are ONLY generated when:
1. The metric has `pop:` config in YAML
2. `DynamicFilteredPopStrategy` is selected

### Generated Measures per Metric

For a metric `gov` with PoP enabled, generate:

| Measure | Type | Purpose |
|---------|------|---------|
| `gov` | (existing) | Base metric, no change |
| `gov_prior` | sum (filtered) | Same aggregation, filtered to comparison period |
| `gov_change` | number | `${gov} - ${gov_prior}` |
| `gov_pct_change` | number | `(${gov} - ${gov_prior}) / NULLIF(${gov_prior}, 0)` |

### Measure Properties

All PoP measures inherit from base metric:
- `view_label` - Same grouping as base
- `group_label` - Same sub-grouping as base
- `value_format_name` - Same format (except pct_change uses percent)
- `description` - Auto-generated explaining the comparison

### Measure Visibility

PoP measures should be hidden when `comparison_period = 'none'`:

```lookml
measure: gov_prior {
  ...
  hidden: "{% if {calendar_view}.comparison_period._parameter_value == \"'none'\" %}yes{% else %}no{% endif %}"
}
```

Or alternatively, always show but return NULL when no comparison selected.

**Decision needed:** Hide vs show-with-null.

---

## Dialect Handling

### DATEADD Syntax by Dialect

| Dialect | Syntax |
|---------|--------|
| Redshift | `DATEADD({period}, 1, {date})` |
| Snowflake | `DATEADD({period}, 1, {date})` |
| BigQuery | `DATE_ADD({date}, INTERVAL 1 {period})` |
| Postgres | `{date} + INTERVAL '1 {period}'` |
| DuckDB | `{date} + INTERVAL '1 {period}'` |
| Starburst | `date_add('{period}', 1, {date})` |

### Implementation

Use existing `adapters/dialect.py` with sqlglot:

```python
class SqlRenderer:
    def dateadd(self, period: str, amount: int, date_expr: str) -> str:
        """Generate dialect-specific DATEADD expression."""
        # Use sqlglot to transpile
        ...
```

The calendar renderer calls this when building the `is_comparison_period` SQL.

---

## Domain Model

### No Changes Required

The domain `PopConfig` and `PopComparison` remain as-is. The strategy interprets them:

```yaml
# YAML config (unchanged)
metrics:
  - name: gov
    pop:
      comparisons: [py, pm, pq, pw]  # Informs allowed_values in parameter
      outputs: [previous, change, pct_change]  # Which measures to generate
```

### Interpretation by Strategy

| YAML | Native Strategy | Dynamic Strategy |
|------|-----------------|------------------|
| `comparisons: [py, pm]` | Generates `gov_py`, `gov_pm` | Populates `allowed_values` in parameter |
| `outputs: [previous, change]` | Generates `_py`, `_py_change` | Generates `_prior`, `_change` |

---

## File Output Structure

### With Native PoP (current)

```
rentals.view.lkml           # Base view
rentals.metrics.view.lkml   # Metrics
rentals.pop.view.lkml       # Static PoP: gov_py, gov_pm, gov_py_change...
rentals.explore.lkml        # Explore
rentals_explore_calendar.view.lkml  # Date selector only
```

### With Dynamic PoP (new)

```
rentals.view.lkml           # Base view
rentals.metrics.view.lkml   # Metrics
rentals.pop.view.lkml       # Dynamic PoP: gov_prior, gov_change, gov_pct_change
rentals.explore.lkml        # Explore
rentals_explore_calendar.view.lkml  # Date selector + comparison_period + period dims
```

---

## Configuration

### Generator-Level

```python
from dbt_to_lookml_v2.adapters.lookml import LookMLGenerator
from dbt_to_lookml_v2.adapters.lookml.renderers.pop import DynamicFilteredPopStrategy

generator = LookMLGenerator(
    pop_strategy=DynamicFilteredPopStrategy(
        default_comparison="none",  # or "year"
        include_no_comparison=True,  # Add "None" option
    )
)
```

### Future: YAML-Level Override

```yaml
# Potential future enhancement
metrics:
  - name: gov
    pop:
      strategy: dynamic  # or "native"
      comparisons: [py, pm, pq, pw]
      outputs: [previous, change, pct_change]
```

---

## Implementation Plan

### Phase 1: Calendar Enhancements

1. Add `has_pop_metrics()` check to determine if PoP infrastructure needed
2. Extend `CalendarRenderer` to emit:
   - `filter: date_range`
   - `parameter: comparison_period`
   - `dimension: is_selected_period`
   - `dimension: is_comparison_period`
3. Add `dateadd()` method to `SqlRenderer` in dialect.py

### Phase 2: DynamicFilteredPopStrategy

1. Create `DynamicFilteredPopStrategy` class implementing `PopStrategy` protocol
2. Implement `render()` to generate filtered measures:
   - `{metric}_prior` with filter on `is_comparison_period`
   - `{metric}_change` as type: number
   - `{metric}_pct_change` as type: number
3. Handle measure properties (label, format, group) inheritance

### Phase 3: Integration

1. Update `ViewRenderer` to pass calendar view name to pop strategy
2. Update `ExploreGenerator` to detect PoP metrics and enable calendar enhancements
3. Add tests for new strategy

### Phase 4: Documentation

1. Update README with dynamic PoP usage
2. Add examples to SCHEMA.md
3. Update BUILD_LOG.md

---

## Example Output

### Input YAML

```yaml
metrics:
  - name: gov
    label: Gross Order Value
    type: simple
    measure: checkout_amount
    filter:
      transaction_type: completed
    pop:
      comparisons: [py, pm, pq]
      outputs: [previous, change, pct_change]
    format: usd
    group: Revenue
```

### Generated Calendar View (partial)

```lookml
parameter: comparison_period {
  view_label: " Calendar"
  label: "Compare To"
  type: unquoted
  default_value: "none"
  allowed_values: [
    { label: "No Comparison" value: "none" }
    { label: "Prior Year" value: "year" }
    { label: "Prior Month" value: "month" }
    { label: "Prior Quarter" value: "quarter" }
  ]
}

dimension: is_comparison_period {
  hidden: yes
  type: yesno
  sql:
    {% if comparison_period._parameter_value != "'none'" %}
      {% condition date_range %}
        DATEADD({% parameter comparison_period %}, 1,
          CASE {% parameter date_field %}
            WHEN 'rentals__created_at' THEN ${rentals.created_at_raw}
          END
        )
      {% endcondition %}
    {% else %}
      FALSE
    {% endif %}
  ;;
}
```

### Generated PoP Measures

```lookml
view: +rentals {

  measure: gov_prior {
    type: sum
    sql: CASE WHEN ${TABLE}.rental_event_type = 'completed'
              THEN ${TABLE}.rental_checkout_amount_local END ;;
    filters: [rentals_explore_calendar.is_comparison_period: "yes"]
    label: "GOV (Prior Period)"
    description: "GOV for the comparison period selected in Calendar settings"
    view_label: "  Metrics"
    group_label: "Revenue"
    value_format_name: usd
  }

  measure: gov_change {
    type: number
    sql: ${gov} - ${gov_prior} ;;
    label: "GOV Change"
    description: "Difference between current and prior period GOV"
    view_label: "  Metrics"
    group_label: "Revenue"
    value_format_name: usd
  }

  measure: gov_pct_change {
    type: number
    sql: (${gov} - ${gov_prior}) / NULLIF(${gov_prior}, 0) ;;
    label: "GOV % Change"
    description: "Percent change from prior period"
    view_label: "  Metrics"
    group_label: "Revenue"
    value_format_name: percent_1
  }
}
```

---

## Open Questions

1. **Hide vs NULL:** When `comparison_period = 'none'`, should PoP measures be hidden or show NULL?

2. **Default comparison:** Should default be `'none'` (explicit opt-in) or `'year'` (common case)?

3. **Label templating:** Should labels include the dynamic period (e.g., "GOV (Prior Year)") or be static (e.g., "GOV Prior")?

4. **Filter inheritance:** The `gov_prior` measure needs the same filter as `gov` (transaction_type = completed). How do we ensure the SQL matches exactly?

5. **Both strategies?** Should we support generating BOTH static and dynamic PoP for the same metric (user chooses at query time)?

---

## Success Criteria

1. PoP measures work correctly with dynamic date field selection
2. Comparison period parameter limits to configured comparisons
3. All SQL dialects supported via sqlglot
4. Measure count reduced from 12+ to 3 per metric
5. Full test coverage for new strategy
6. No breaking changes to existing `LookerNativePopStrategy`
