---
id: DTL-055-spec
issue: DTL-055
title: "Implementation Spec: Add same-model detection utility for derived metrics"
type: spec
status: Complete
created: 2025-12-22
stack: backend
---

# Implementation Spec: Add same-model detection utility for derived metrics

## Metadata
- **Issue**: `DTL-055`
- **Stack**: `backend`
- **Type**: `feature`
- **Generated**: 2025-12-22
- **Epic**: DTL-054 (PoP Support for Same-Model Derived Metrics)

## Issue Context

### Problem Statement

To enable PoP (Period-over-Period) support for derived metrics, we need a utility function that can detect whether a derived metric qualifies for PoP generation. A derived metric qualifies when all of its parent metrics recursively resolve to simple metrics on the same semantic model.

### Solution Approach

Create a function `is_same_model_derived_metric()` that:
1. Takes a metric and list of all metrics
2. Recursively traverses `type_params.metrics` for derived metrics
3. Checks that ALL leaf metrics are `type: simple`
4. Verifies all parent metrics share the same `primary_entity`
5. Returns a tuple: `(qualifies: bool, primary_entity: str | None)`

### Success Criteria

- [ ] Function correctly identifies qualifying derived metrics
- [ ] Recursive resolution for nested derived metrics works correctly
- [ ] Cross-model metrics correctly return False
- [ ] Circular references are handled gracefully
- [ ] Missing parent metrics are handled gracefully
- [ ] Unit tests cover all edge cases

## Implementation Plan

### Phase 1: Create the Utility Function

**Location**: `src/dbt_to_lookml/generators/lookml.py` (add as a module-level function or method on LookMLGenerator)

**Function Signature**:

```python
def is_same_model_derived_metric(
    metric: Metric,
    all_metrics: list[Metric],
    visited: set[str] | None = None,
) -> tuple[bool, str | None]:
    """Detect if a derived metric qualifies for PoP generation.

    A derived metric qualifies when:
    1. It is a derived metric (type == "derived")
    2. All parent metrics recursively resolve to simple metrics
    3. All simple metrics share the same primary_entity

    Args:
        metric: The metric to check.
        all_metrics: All metrics for recursive lookup.
        visited: Set of visited metric names (for circular reference detection).

    Returns:
        Tuple of (qualifies, primary_entity).
        - (True, "entity_name") if all parents resolve to simple metrics on same model
        - (False, None) if metric doesn't qualify

    Examples:
        >>> # Simple metric - not derived, doesn't qualify
        >>> is_same_model_derived_metric(simple_metric, all_metrics)
        (False, None)

        >>> # Derived with all simple parents on same model
        >>> is_same_model_derived_metric(net_change_metric, all_metrics)
        (True, "facility")

        >>> # Derived with cross-model parents
        >>> is_same_model_derived_metric(cross_model_metric, all_metrics)
        (False, None)
    """
```

### Phase 2: Implementation Logic

**Algorithm**:

```python
from dbt_to_lookml.schemas import DerivedMetricParams, SimpleMetricParams, Metric

def is_same_model_derived_metric(
    metric: Metric,
    all_metrics: list[Metric],
    visited: set[str] | None = None,
) -> tuple[bool, str | None]:
    """See docstring above."""

    # Initialize visited set for circular reference detection
    if visited is None:
        visited = set()

    # Check for circular reference
    if metric.name in visited:
        return (False, None)  # Circular reference detected

    # Only process derived metrics
    if metric.type != "derived" or not isinstance(metric.type_params, DerivedMetricParams):
        return (False, None)  # Not a derived metric

    visited = visited | {metric.name}  # Add current to visited (immutable update)

    # Build metrics lookup
    metrics_by_name = {m.name: m for m in all_metrics}

    # Collect all primary entities from leaf metrics
    primary_entities: set[str] = set()

    for ref in metric.type_params.metrics:
        parent_metric = metrics_by_name.get(ref.name)

        if parent_metric is None:
            return (False, None)  # Parent metric not found

        if parent_metric.type == "simple" and isinstance(parent_metric.type_params, SimpleMetricParams):
            # Leaf node - simple metric
            entity = parent_metric.primary_entity
            if not entity:
                return (False, None)  # Simple metric without primary_entity
            primary_entities.add(entity)

        elif parent_metric.type == "derived" and isinstance(parent_metric.type_params, DerivedMetricParams):
            # Recursive case - nested derived metric
            qualifies, entity = is_same_model_derived_metric(
                parent_metric, all_metrics, visited
            )
            if not qualifies or not entity:
                return (False, None)  # Nested derived doesn't qualify
            primary_entities.add(entity)

        else:
            # Ratio, conversion, or unknown type - doesn't qualify
            return (False, None)

    # Check if all primary entities are the same
    if len(primary_entities) == 1:
        return (True, primary_entities.pop())
    else:
        return (False, None)  # Multiple entities = cross-model
```

### Phase 3: Unit Tests

**File**: `src/tests/unit/test_derived_metric_pop.py` (new file)

**Test Cases**:

```python
"""Unit tests for same-model derived metric detection."""

import pytest

from dbt_to_lookml.generators.lookml import is_same_model_derived_metric
from dbt_to_lookml.schemas import (
    Config,
    ConfigMeta,
    DerivedMetricParams,
    Metric,
    MetricReference,
    PopConfig,
    RatioMetricParams,
    SimpleMetricParams,
)


class TestSameModelDerivedMetricDetection:
    """Tests for is_same_model_derived_metric function."""

    def test_simple_metric_returns_false(self) -> None:
        """Simple metrics are not derived, should return (False, None)."""
        metric = Metric(
            name="revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="total_revenue"),
            meta={"primary_entity": "order"},
        )
        qualifies, entity = is_same_model_derived_metric(metric, [metric])
        assert qualifies is False
        assert entity is None

    def test_derived_with_simple_parents_same_model(self) -> None:
        """Derived metric with all simple parents on same model qualifies."""
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
        )

        all_metrics = [gained, lost, net_change]
        qualifies, entity = is_same_model_derived_metric(net_change, all_metrics)

        assert qualifies is True
        assert entity == "facility"

    def test_derived_with_cross_model_parents(self) -> None:
        """Derived metric with parents on different models doesn't qualify."""
        orders = Metric(
            name="order_count",
            type="simple",
            type_params=SimpleMetricParams(measure="orders"),
            meta={"primary_entity": "order"},
        )
        searches = Metric(
            name="search_count",
            type="simple",
            type_params=SimpleMetricParams(measure="searches"),
            meta={"primary_entity": "search"},
        )
        conversion = Metric(
            name="conversion_derived",
            type="derived",
            type_params=DerivedMetricParams(
                expr="orders / searches",
                metrics=[
                    MetricReference(name="order_count", alias="orders"),
                    MetricReference(name="search_count", alias="searches"),
                ],
            ),
            meta={"primary_entity": "search"},
        )

        all_metrics = [orders, searches, conversion]
        qualifies, entity = is_same_model_derived_metric(conversion, all_metrics)

        assert qualifies is False
        assert entity is None

    def test_nested_derived_metric_qualifies(self) -> None:
        """Nested derived (derived -> derived -> simple) qualifies if all same model."""
        # Level 0: Simple metrics
        a = Metric(
            name="metric_a",
            type="simple",
            type_params=SimpleMetricParams(measure="measure_a"),
            meta={"primary_entity": "entity"},
        )
        b = Metric(
            name="metric_b",
            type="simple",
            type_params=SimpleMetricParams(measure="measure_b"),
            meta={"primary_entity": "entity"},
        )
        c = Metric(
            name="metric_c",
            type="simple",
            type_params=SimpleMetricParams(measure="measure_c"),
            meta={"primary_entity": "entity"},
        )

        # Level 1: Derived from simple
        ab = Metric(
            name="metric_ab",
            type="derived",
            type_params=DerivedMetricParams(
                expr="a + b",
                metrics=[
                    MetricReference(name="metric_a", alias="a"),
                    MetricReference(name="metric_b", alias="b"),
                ],
            ),
            meta={"primary_entity": "entity"},
        )

        # Level 2: Derived from derived
        abc = Metric(
            name="metric_abc",
            type="derived",
            type_params=DerivedMetricParams(
                expr="ab + c",
                metrics=[
                    MetricReference(name="metric_ab", alias="ab"),
                    MetricReference(name="metric_c", alias="c"),
                ],
            ),
            meta={"primary_entity": "entity"},
        )

        all_metrics = [a, b, c, ab, abc]
        qualifies, entity = is_same_model_derived_metric(abc, all_metrics)

        assert qualifies is True
        assert entity == "entity"

    def test_nested_derived_with_cross_model_leaf(self) -> None:
        """Nested derived doesn't qualify if any leaf is on different model."""
        a = Metric(
            name="metric_a",
            type="simple",
            type_params=SimpleMetricParams(measure="measure_a"),
            meta={"primary_entity": "entity_1"},
        )
        b = Metric(
            name="metric_b",
            type="simple",
            type_params=SimpleMetricParams(measure="measure_b"),
            meta={"primary_entity": "entity_2"},  # Different entity!
        )

        derived = Metric(
            name="derived_ab",
            type="derived",
            type_params=DerivedMetricParams(
                expr="a - b",
                metrics=[
                    MetricReference(name="metric_a", alias="a"),
                    MetricReference(name="metric_b", alias="b"),
                ],
            ),
            meta={"primary_entity": "entity_1"},
        )

        all_metrics = [a, b, derived]
        qualifies, entity = is_same_model_derived_metric(derived, all_metrics)

        assert qualifies is False
        assert entity is None

    def test_circular_reference_returns_false(self) -> None:
        """Circular reference in metric graph returns False gracefully."""
        # A references B, B references A
        a = Metric(
            name="metric_a",
            type="derived",
            type_params=DerivedMetricParams(
                expr="b * 2",
                metrics=[MetricReference(name="metric_b", alias="b")],
            ),
            meta={"primary_entity": "entity"},
        )
        b = Metric(
            name="metric_b",
            type="derived",
            type_params=DerivedMetricParams(
                expr="a * 2",
                metrics=[MetricReference(name="metric_a", alias="a")],
            ),
            meta={"primary_entity": "entity"},
        )

        all_metrics = [a, b]
        qualifies, entity = is_same_model_derived_metric(a, all_metrics)

        assert qualifies is False
        assert entity is None

    def test_missing_parent_metric_returns_false(self) -> None:
        """Missing parent metric returns False gracefully."""
        derived = Metric(
            name="derived",
            type="derived",
            type_params=DerivedMetricParams(
                expr="missing + 1",
                metrics=[MetricReference(name="nonexistent", alias="missing")],
            ),
            meta={"primary_entity": "entity"},
        )

        qualifies, entity = is_same_model_derived_metric(derived, [derived])

        assert qualifies is False
        assert entity is None

    def test_ratio_parent_returns_false(self) -> None:
        """Derived referencing ratio metric doesn't qualify."""
        ratio = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="orders",
                denominator="searches",
            ),
            meta={"primary_entity": "search"},
        )
        derived = Metric(
            name="derived_from_ratio",
            type="derived",
            type_params=DerivedMetricParams(
                expr="ratio * 100",
                metrics=[MetricReference(name="conversion_rate", alias="ratio")],
            ),
            meta={"primary_entity": "search"},
        )

        all_metrics = [ratio, derived]
        qualifies, entity = is_same_model_derived_metric(derived, all_metrics)

        assert qualifies is False
        assert entity is None

    def test_simple_without_primary_entity_returns_false(self) -> None:
        """Simple metric without primary_entity causes False."""
        simple = Metric(
            name="orphan",
            type="simple",
            type_params=SimpleMetricParams(measure="some_measure"),
            # No meta/primary_entity
        )
        derived = Metric(
            name="derived_from_orphan",
            type="derived",
            type_params=DerivedMetricParams(
                expr="orphan + 1",
                metrics=[MetricReference(name="orphan")],
            ),
            meta={"primary_entity": "entity"},
        )

        all_metrics = [simple, derived]
        qualifies, entity = is_same_model_derived_metric(derived, all_metrics)

        assert qualifies is False
        assert entity is None
```

## File Changes

### Files to Create

#### `src/tests/unit/test_derived_metric_pop.py`

**Why**: Dedicated test file for derived metric PoP functionality

**Content**: Test cases as specified in Phase 3

### Files to Modify

#### `src/dbt_to_lookml/generators/lookml.py`

**Why**: Add the `is_same_model_derived_metric` function

**Changes**:
1. Add imports if needed (should already have access to Metric, DerivedMetricParams, SimpleMetricParams)
2. Add the function (approximately lines 1400-1450, after existing utility functions)

**Approximate Location**: After `_find_model_by_primary_entity` method or as a standalone function

**Implementation Guidance**:

```python
# Add near other utility functions in generators/lookml.py

def is_same_model_derived_metric(
    metric: Metric,
    all_metrics: list[Metric],
    visited: set[str] | None = None,
) -> tuple[bool, str | None]:
    """Detect if a derived metric qualifies for PoP generation.

    [Full docstring as shown in Phase 1]
    """
    from dbt_to_lookml.schemas import DerivedMetricParams, SimpleMetricParams

    # [Implementation as shown in Phase 2]
```

## Testing Strategy

### Unit Tests

Run the new test file:
```bash
python -m pytest tests/unit/test_derived_metric_pop.py -v
```

### Integration Tests

After DTL-056 is implemented, integration tests will verify end-to-end PoP generation:
```bash
python -m pytest tests/unit/test_derived_metric_pop.py tests/unit/test_lookml_generator_metrics.py -v
```

### Manual Verification

1. Create a test semantic model with derived metric
2. Run the generator and verify the function returns correct results

## Dependencies

### Existing Dependencies

- `Metric`, `DerivedMetricParams`, `SimpleMetricParams`, `MetricReference` from `schemas/semantic_layer.py`

### Related Issues

- **Parent**: DTL-054 (Epic)
- **Required by**: DTL-056 (Update PoP generation to use this utility)

## Implementation Notes

### Key Considerations

1. **Immutable visited set**: Use `visited | {metric.name}` to avoid mutating the set, enabling safe recursive calls without side effects.

2. **Early returns**: Return `(False, None)` as soon as any disqualifying condition is found for efficiency.

3. **Entity collection**: Use a set to collect primary entities, then check if `len(entities) == 1` for same-model validation.

4. **Type narrowing**: Use `isinstance()` checks to narrow types and satisfy mypy.

5. **Function location**: Could be a standalone function or a method on `LookMLGenerator`. Standalone is simpler and more testable.

### Edge Cases Handled

| Case | Behavior |
|------|----------|
| Simple metric (not derived) | Returns `(False, None)` |
| Derived with all simple, same model | Returns `(True, entity_name)` |
| Derived with cross-model parents | Returns `(False, None)` |
| Nested derived, all same model | Returns `(True, entity_name)` (recursive) |
| Circular reference | Returns `(False, None)` (via visited set) |
| Missing parent metric | Returns `(False, None)` |
| Ratio/conversion parent | Returns `(False, None)` |
| Simple without primary_entity | Returns `(False, None)` |

## Implementation Status: COMPLETE

**This issue has already been implemented.**

The following functions exist in `src/dbt_to_lookml/generators/lookml.py`:
- `is_pop_eligible_metric()` (lines 2673-2811) - Unified function for all metric types
- `is_same_model_derived_metric()` (lines 2815-2829) - Backwards compatibility wrapper

Tests exist in `src/tests/unit/test_derived_metric_pop.py` with 20 passing tests covering:
- Simple metrics (2 tests)
- Ratio metrics (6 tests)
- Derived metrics (8 tests)
- Conversion metrics (1 test)
- Backwards compatibility (3 tests)

**No further implementation needed for DTL-055.**

**Next Issue**: DTL-056 (Integrate `is_pop_eligible_metric` into PoP generation flow)
