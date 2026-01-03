---
id: DTL-056-spec
issue: DTL-056
title: "Implementation Spec: Update PoP generation to include qualifying derived metrics"
type: spec
status: Ready
created: 2025-12-22
updated: 2025-12-23
stack: backend
---

# Implementation Spec: Update PoP generation to include qualifying derived metrics

## Metadata
- **Issue**: `DTL-056`
- **Stack**: `backend`
- **Type**: `feature`
- **Generated**: 2025-12-22
- **Updated**: 2025-12-23 (added parser fix)
- **Epic**: DTL-054 (PoP Support for Same-Model Derived Metrics)
- **Depends on**: DTL-055 (COMPLETE), DTL-059 (calendar dimension_group)

## Issue Context

### Problem Statement

There are **TWO blockers** preventing derived/ratio metrics from getting PoP support:

#### Blocker 1: Parser Strips PoP Config

The parser in `dbt_metrics.py` discards PoP config for non-simple metrics:

```python
# dbt_metrics.py lines 329-332
def _parse_metric_pop_config(self, pop_data, metric_type):
    ...
    # Only support PoP on simple metrics for now
    if metric_type != "simple":
        return None  # <-- PoP config discarded!
```

By the time metrics reach the generator, `m.config.meta.pop` is already `None` for derived/ratio metrics.

#### Blocker 2: Generator Doesn't Check Eligibility

Even after fixing the parser, the generator needs to filter using `is_pop_eligible_metric` to skip cross-model metrics:

```python
# generators/lookml.py lines 2231-2235 - No eligibility check
pop_metrics = [
    m for m in owned_metrics
    if m.config and m.config.meta and m.config.meta.pop
    and m.config.meta.pop.enabled
]
```

### Solution Approach

**Two changes required:**

1. **Parser fix**: Remove the `metric_type != "simple"` filter in `_parse_metric_pop_config`
2. **Generator fix**: Add eligibility filtering using `is_pop_eligible_metric`

### Success Criteria

- [ ] Parser preserves PoP config for derived/ratio metrics
- [ ] Generator filters using `is_pop_eligible_metric`
- [ ] Same-model derived metrics generate PoP measures
- [ ] Same-model ratio metrics generate PoP measures
- [ ] Cross-model metrics are silently skipped
- [ ] Simple metrics continue working as before
- [ ] Integration tests verify end-to-end behavior

## Implementation Plan

### Phase 1: Parser Fix

**File**: `src/dbt_to_lookml/parsers/dbt_metrics.py`

**Location**: Lines 329-332

**Current code**:
```python
def _parse_metric_pop_config(
    self,
    pop_data: dict[str, Any],
    metric_type: str,
) -> PopConfig | None:
    """Parse PoP configuration from metric meta.

    For metrics, PoP is only supported on simple metrics since they
    generate direct aggregate measures. Ratio and derived metrics
    generate type: number measures which have PoP limitations.
    ...
    """
    if not pop_data.get("enabled", False):
        return None

    # Only support PoP on simple metrics for now
    if metric_type != "simple":
        # Log warning but don't fail - user may be experimenting
        return None
    ...
```

**Updated code**:
```python
def _parse_metric_pop_config(
    self,
    pop_data: dict[str, Any],
    metric_type: str,
) -> PopConfig | None:
    """Parse PoP configuration from metric meta.

    PoP is supported for:
    - Simple metrics: Always supported (direct aggregates)
    - Ratio metrics: Supported if numerator/denominator from same model
    - Derived metrics: Supported if all parents resolve to same-model metrics

    Eligibility is checked at generation time by is_pop_eligible_metric().
    Cross-model metrics are silently skipped during generation.
    ...
    """
    if not pop_data.get("enabled", False):
        return None

    # REMOVED: metric_type != "simple" filter
    # Eligibility is now checked at generation time by is_pop_eligible_metric()
    # This allows the generator to make the decision with full context

    # Parse enum values with defaults
    grains = [PopGrain(g) for g in pop_data.get("grains", ["mtd", "ytd"])]
    ...
```

**Diff**:
```diff
     if not pop_data.get("enabled", False):
         return None

-    # Only support PoP on simple metrics for now
-    if metric_type != "simple":
-        # Log warning but don't fail - user may be experimenting
-        return None
+    # Eligibility is checked at generation time by is_pop_eligible_metric()
+    # This allows same-model derived/ratio metrics to get PoP support

     # Parse enum values with defaults
```

### Phase 2: Generator Fix

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Location**: Around line 2230

**Current code**:
```python
# Generate PoP measures for metrics with pop.enabled
pop_metrics = [
    m for m in owned_metrics
    if m.config and m.config.meta and m.config.meta.pop
    and m.config.meta.pop.enabled
]
```

**Updated code**:
```python
# Generate PoP measures for eligible metrics with pop.enabled
# Eligibility: simple always qualifies, ratio/derived only if same-model
all_metrics = metrics if metrics else []
pop_metrics = [
    m for m in owned_metrics
    if m.config and m.config.meta and m.config.meta.pop
    and m.config.meta.pop.enabled
    and is_pop_eligible_metric(m, all_metrics, models)[0]
]
```

### Phase 3: Use `calendar_date` for PoP `based_on_time`

**Depends on**: DTL-059 (Always generate calendar dimension_group)

Once DTL-059 provides a consistent `calendar` dimension_group (static or dynamic), PoP generation can simply use `calendar_date` for all `based_on_time` values.

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Update PoP generation** (around line 2250):

**Current code**:
```python
# Determine date dimension for PoP based_on_time
# Priority: date_selector enabled → calendar_date (dynamic)
#           Otherwise → agg_time_dimension (static)
date_dim = None

if is_date_selector_model:
    date_dim = "calendar"
elif model.defaults:
    date_dim = model.defaults.get("agg_time_dimension")
```

**Updated code**:
```python
# Always use calendar_date for PoP based_on_time
# DTL-059 ensures calendar dimension_group exists (static or dynamic)
date_dim = "calendar"
```

This simplifies the PoP generation since DTL-059 guarantees `calendar_date` exists.

### Phase 4: Update Docstrings

Update the docstring in `_parse_metric_pop_config` to reflect the new behavior (done in Phase 1).

### Phase 5: Integration Tests

Add tests that verify end-to-end behavior through the parser AND generator.

## Detailed Implementation

### Step 1: Remove parser filter

**File**: `src/dbt_to_lookml/parsers/dbt_metrics.py`
**Lines**: 329-332

Remove:
```python
# Only support PoP on simple metrics for now
if metric_type != "simple":
    # Log warning but don't fail - user may be experimenting
    return None
```

Add comment:
```python
# Eligibility is checked at generation time by is_pop_eligible_metric()
# This allows same-model derived/ratio metrics to get PoP support
```

### Step 2: Add eligibility check in generator

**File**: `src/dbt_to_lookml/generators/lookml.py`
**Lines**: Around 2230

Replace the `pop_metrics` filter with eligibility check:
```python
# Generate PoP measures for eligible metrics with pop.enabled
# Eligibility: simple always qualifies, ratio/derived only if same-model
all_metrics = metrics if metrics else []
pop_metrics = [
    m for m in owned_metrics
    if m.config and m.config.meta and m.config.meta.pop
    and m.config.meta.pop.enabled
    and is_pop_eligible_metric(m, all_metrics, models)[0]
]
```

### Step 3: Verify tests pass

Run existing tests to ensure no regressions:
```bash
python -m pytest src/tests/unit/test_pop_generator.py src/tests/unit/test_pop_integration.py src/tests/unit/test_derived_metric_pop.py -v
```

## File Changes

### Files to Modify

#### `src/dbt_to_lookml/parsers/dbt_metrics.py`

**Why**: Remove filter that blocks PoP config for non-simple metrics

**Changes**:
1. Remove lines 329-332 (the `metric_type != "simple"` filter)
2. Update docstring to explain eligibility is checked at generation time

**Diff**:
```diff
@@ -312,20 +312,16 @@ class DbtMetricParser:
     def _parse_metric_pop_config(
         self,
         pop_data: dict[str, Any],
         metric_type: str,
     ) -> PopConfig | None:
         """Parse PoP configuration from metric meta.

-        For metrics, PoP is only supported on simple metrics since they
-        generate direct aggregate measures. Ratio and derived metrics
-        generate type: number measures which have PoP limitations.
+        PoP is supported for simple, ratio, and derived metrics.
+        Eligibility (same-model requirement for ratio/derived) is checked
+        at generation time by is_pop_eligible_metric().
         ...
         """
         if not pop_data.get("enabled", False):
             return None

-        # Only support PoP on simple metrics for now
-        if metric_type != "simple":
-            # Log warning but don't fail - user may be experimenting
-            return None
+        # Eligibility is checked at generation time by is_pop_eligible_metric()

         # Parse enum values with defaults
```

#### `src/dbt_to_lookml/generators/lookml.py`

**Why**: Add eligibility check to filter out cross-model metrics

**Changes**:
1. Update `pop_metrics` filter around line 2230 to include eligibility check

**Diff**:
```diff
@@ -2230,11 +2230,13 @@ class LookMLGenerator(Generator):
-                # Generate PoP measures for metrics with pop.enabled
-                pop_metrics = [
-                    m for m in owned_metrics
-                    if m.config and m.config.meta and m.config.meta.pop
-                    and m.config.meta.pop.enabled
-                ]
+                # Generate PoP measures for eligible metrics with pop.enabled
+                # Eligibility: simple always qualifies, ratio/derived only if same-model
+                all_metrics = metrics if metrics else []
+                pop_metrics = [
+                    m for m in owned_metrics
+                    if m.config and m.config.meta and m.config.meta.pop
+                    and m.config.meta.pop.enabled
+                    and is_pop_eligible_metric(m, all_metrics, models)[0]
+                ]
```

### Files to Create

#### `src/tests/unit/test_derived_metric_pop_integration.py`

**Why**: Test end-to-end behavior through parser and generator

See test code in Testing Strategy section below.

## Testing Strategy

### Unit Tests (Existing)

The existing tests verify component behavior:
- `test_derived_metric_pop.py` - Tests `is_pop_eligible_metric` function (20 tests)
- `test_pop_generator.py` - Tests PoP measure generation
- `test_pop_integration.py` - Tests overall PoP integration

### Parser Test

Add test to verify parser preserves PoP for derived metrics:

```python
# In test_dbt_metric_parser.py or new file

def test_parser_preserves_pop_for_derived_metric(self) -> None:
    """Parser should preserve PoP config for derived metrics."""
    metric_yaml = """
    metrics:
      - name: net_change
        type: derived
        type_params:
          expr: gained - lost
          metrics:
            - name: gained
            - name: lost
        meta:
          primary_entity: facility
          pop:
            enabled: true
            comparisons: [py]
    """
    # Parse and verify pop config is preserved
    parser = DbtMetricParser()
    # ... parse metric ...
    assert metric.config.meta.pop is not None
    assert metric.config.meta.pop.enabled is True
```

### Integration Tests

**File**: `src/tests/unit/test_derived_metric_pop_integration.py`

```python
"""Integration tests for derived metric PoP generation."""

import lkml
import pytest

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.schemas.config import Config, ConfigMeta, PopComparison, PopConfig, PopWindow
from dbt_to_lookml.schemas.semantic_layer import (
    DerivedMetricParams,
    Entity,
    Measure,
    Metric,
    MetricReference,
    RatioMetricParams,
    SemanticModel,
    SimpleMetricParams,
)
from dbt_to_lookml.types import AggregationType


class TestDerivedMetricPopGeneration:
    """Tests for PoP generation with derived metrics."""

    def test_same_model_derived_generates_pop(self) -> None:
        """Derived metric with same-model parents generates PoP measures."""
        model = SemanticModel(
            name="facility_status",
            model="ref('facility_status')",
            defaults={"agg_time_dimension": "report_date"},
            entities=[Entity(name="facility", type="primary")],
            measures=[
                Measure(name="gained_count", agg=AggregationType.SUM, expr="gained"),
                Measure(name="lost_count", agg=AggregationType.SUM, expr="lost"),
            ],
        )

        gained = Metric(
            name="gained_eom",
            type="simple",
            type_params=SimpleMetricParams(measure="gained_count"),
            meta={"primary_entity": "facility"},
        )
        lost = Metric(
            name="lost_eom",
            type="simple",
            type_params=SimpleMetricParams(measure="lost_count"),
            meta={"primary_entity": "facility"},
        )
        net_change = Metric(
            name="net_change_eom",
            type="derived",
            type_params=DerivedMetricParams(
                expr="gained - lost",
                metrics=[
                    MetricReference(name="gained_eom", alias="gained"),
                    MetricReference(name="lost_eom", alias="lost"),
                ],
            ),
            meta={"primary_entity": "facility"},
            config=Config(
                meta=ConfigMeta(
                    primary_entity="facility",
                    pop=PopConfig(
                        enabled=True,
                        comparisons=[PopComparison.PY, PopComparison.PP],
                        windows=[PopWindow.MONTH],
                    ),
                )
            ),
        )

        metrics = [gained, lost, net_change]
        generator = LookMLGenerator()
        files = generator.generate([model], metrics)

        view_file = files.get("facility_status.view.lkml", "")
        assert view_file, "View file should be generated"

        view_dict = lkml.load(view_file)
        measures = view_dict["views"][0].get("measures", [])
        measure_names = {m["name"] for m in measures}

        # Should have PoP measures for net_change_eom
        assert "net_change_eom_py" in measure_names, "Prior year measure missing"
        assert "net_change_eom_pm" in measure_names, "Prior month measure missing"

    def test_cross_model_derived_skips_pop(self) -> None:
        """Derived metric with cross-model parents skips PoP generation."""
        orders_model = SemanticModel(
            name="orders",
            model="ref('orders')",
            defaults={"agg_time_dimension": "order_date"},
            entities=[Entity(name="order", type="primary")],
            measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
        )
        searches_model = SemanticModel(
            name="searches",
            model="ref('searches')",
            defaults={"agg_time_dimension": "search_date"},
            entities=[Entity(name="search", type="primary")],
            measures=[Measure(name="search_count", agg=AggregationType.COUNT)],
        )

        orders = Metric(
            name="total_orders",
            type="simple",
            type_params=SimpleMetricParams(measure="order_count"),
            meta={"primary_entity": "order"},
        )
        searches = Metric(
            name="total_searches",
            type="simple",
            type_params=SimpleMetricParams(measure="search_count"),
            meta={"primary_entity": "search"},
        )
        conversion = Metric(
            name="conversion_rate",
            type="derived",
            type_params=DerivedMetricParams(
                expr="orders / searches",
                metrics=[
                    MetricReference(name="total_orders", alias="orders"),
                    MetricReference(name="total_searches", alias="searches"),
                ],
            ),
            meta={"primary_entity": "search"},
            config=Config(
                meta=ConfigMeta(
                    primary_entity="search",
                    pop=PopConfig(
                        enabled=True,
                        comparisons=[PopComparison.PY],
                    ),
                )
            ),
        )

        metrics = [orders, searches, conversion]
        generator = LookMLGenerator()
        files = generator.generate([orders_model, searches_model], metrics)

        # Parse searches view
        view_file = files.get("searches.view.lkml", "")
        if view_file:
            view_dict = lkml.load(view_file)
            measures = view_dict["views"][0].get("measures", [])
            measure_names = {m["name"] for m in measures}

            # Should NOT have PoP measures
            assert "conversion_rate_py" not in measure_names

    def test_same_model_ratio_generates_pop(self) -> None:
        """Ratio metric with same-model measures generates PoP measures."""
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "rental_date"},
            entities=[Entity(name="rental", type="primary")],
            measures=[
                Measure(name="gov", agg=AggregationType.SUM, expr="amount"),
                Measure(name="rental_count", agg=AggregationType.COUNT),
            ],
        )

        aov = Metric(
            name="average_order_value",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="gov",
                denominator="rental_count",
            ),
            meta={"primary_entity": "rental"},
            config=Config(
                meta=ConfigMeta(
                    primary_entity="rental",
                    pop=PopConfig(
                        enabled=True,
                        comparisons=[PopComparison.PY],
                    ),
                )
            ),
        )

        generator = LookMLGenerator()
        files = generator.generate([model], [aov])

        view_file = files.get("rentals.view.lkml", "")
        assert view_file

        view_dict = lkml.load(view_file)
        measures = view_dict["views"][0].get("measures", [])
        measure_names = {m["name"] for m in measures}

        # Should have PoP measures for AOV
        assert "average_order_value_py" in measure_names

    def test_simple_metric_pop_still_works(self) -> None:
        """Simple metrics with PoP continue to work."""
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "rental_date"},
            entities=[Entity(name="rental", type="primary")],
            measures=[Measure(name="revenue", agg=AggregationType.SUM, expr="amount")],
        )

        revenue = Metric(
            name="total_revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="revenue"),
            meta={"primary_entity": "rental"},
            config=Config(
                meta=ConfigMeta(
                    primary_entity="rental",
                    pop=PopConfig(
                        enabled=True,
                        comparisons=[PopComparison.PY],
                    ),
                )
            ),
        )

        generator = LookMLGenerator()
        files = generator.generate([model], [revenue])

        view_file = files.get("rentals.view.lkml", "")
        assert view_file

        view_dict = lkml.load(view_file)
        measures = view_dict["views"][0].get("measures", [])
        measure_names = {m["name"] for m in measures}

        assert "total_revenue_py" in measure_names
```

### Run All Tests

```bash
# Run all PoP-related tests
python -m pytest src/tests/unit/test_pop*.py src/tests/unit/test_derived_metric_pop*.py -v

# Run full test suite
make test
```

## Dependencies

### Existing Dependencies

- `is_pop_eligible_metric` function (DTL-055 - COMPLETE)

### Related Issues

- **Parent**: DTL-054 (Epic)
- **Depends on**: DTL-055 (COMPLETE)
- **Related**: DTL-057 (Additional test coverage)

## Implementation Notes

### Key Points

1. **Two-step fix required**: Both parser AND generator need changes
2. **Parser now trusts generator**: Parser preserves PoP config, generator decides eligibility
3. **Backwards compatible**: Simple metrics work exactly as before
4. **Silent skipping**: Cross-model metrics don't error, they're just filtered out

### Looker Compatibility

Looker's `period_over_period` documentation confirms:
- `type: number` measures ARE supported for `based_on`
- The measure must be "aggregate in nature" (which ratio/derived metrics are)
- Cross-model PoP would fail in Looker, so we filter these out

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Simple metric | Always generates PoP |
| Same-model ratio | Generates PoP |
| Cross-model ratio | Skipped silently |
| Same-model derived | Generates PoP |
| Cross-model derived | Skipped silently |
| Nested derived (all same-model) | Generates PoP |
| Derived with ratio parent (all same-model) | Generates PoP |

## Ready for Implementation

This spec is complete and ready for implementation.

**Implementation Steps**:
1. Implement DTL-059 first (calendar dimension_group for all models)
2. Remove parser filter in `dbt_metrics.py` (lines 329-332)
3. Add eligibility check in `generators/lookml.py` (around line 2230)
4. Update PoP to always use `based_on_time: calendar_date`
5. Add integration tests
6. Run full test suite
7. Mark DTL-056 as complete

**Estimated Effort**: 1.5 hours
- Parser fix: 10 minutes
- Generator eligibility fix: 15 minutes
- Update PoP to use `calendar_date`: 10 minutes
- Integration tests: 40 minutes
- Verification & polish: 15 minutes

**Success Criteria**:
- [ ] Parser preserves PoP config for all metric types
- [ ] Generator filters using `is_pop_eligible_metric`
- [ ] Same-model derived/ratio metrics generate PoP measures
- [ ] Cross-model metrics are silently skipped
- [ ] Simple metrics continue to work unchanged
- [ ] All PoP measures use `based_on_time: calendar_date` (requires DTL-059)
- [ ] All tests pass including new integration tests
