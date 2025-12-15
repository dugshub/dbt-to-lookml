# Implementation Strategy: DTL-036

**Issue**: DTL-036 - Optimize Measure Generation: Eliminate Redundant Hidden Measures
**Analyzed**: 2024-12-14T20:00:00Z
**Stack**: backend
**Type**: feature

## Approach

Refactor the LookML generator to perform a two-pass generation: first analyze all metrics to build a "measure usage map", then generate measures intelligently based on whether each measure is exposed via a simple metric or only used internally by complex metrics. Simple metrics will directly inherit their source measure's aggregation type instead of wrapping it with `type: number`.

## Current vs. Proposed Flow

### Current Flow
```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ dbt Measures    │───▶│ ALL → Hidden Measures│───▶│ Metrics reference   │
│ (total_revenue) │    │ (total_revenue_meas) │    │ hidden measures     │
└─────────────────┘    └──────────────────────┘    └─────────────────────┘
```

### Proposed Flow
```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ dbt Measures    │───▶│ Analyze: Who uses    │───▶│ Smart Generation    │
│ + Metrics       │    │ each measure?        │    │                     │
└─────────────────┘    └──────────────────────┘    └─────────────────────┘
                                                            │
                       ┌────────────────────────────────────┼────────────────────┐
                       ▼                                    ▼                    ▼
              ┌─────────────────┐              ┌─────────────────┐    ┌──────────────────┐
              │ Simple Metric   │              │ Complex Metric  │    │ Hidden Measure   │
              │ type: sum/count │              │ type: number    │    │ (only if needed) │
              │ (visible)       │              │ refs other meas │    │                  │
              └─────────────────┘              └─────────────────┘    └──────────────────┘
```

## Architecture Impact

**Layer**: generators

**New Files**:
- `src/dbt_to_lookml/generators/measure_analyzer.py` - Measure usage analysis logic (optional, could be methods in lookml.py)

**Modified Files**:
- `src/dbt_to_lookml/generators/lookml.py` - Core changes to measure generation
  - Add `_analyze_measure_usage()` method
  - Modify `_generate_metric_measure()` to handle simple metrics differently
  - Modify measure reference resolution to use visible simple metrics when available
- `src/dbt_to_lookml/schemas/semantic_layer.py` - May need to expose measure's aggregation type to metrics
- `src/tests/unit/test_lookml_generator.py` - New tests for smart measure generation
- `src/tests/integration/test_metric_generation.py` - Integration tests with real fixtures

## Key Data Structures

### Measure Usage Map
```python
@dataclass
class MeasureUsage:
    """Tracks how a measure is used across metrics."""
    measure_name: str
    source_model: str
    simple_metric_name: str | None  # If exposed via simple metric
    complex_metric_refs: list[str]  # Metrics that reference this measure

    @property
    def needs_hidden_measure(self) -> bool:
        """True if measure needs a hidden _measure version."""
        # Only need hidden if:
        # 1. Used by complex metrics, AND
        # 2. NOT exposed via simple metric
        return bool(self.complex_metric_refs) and not self.simple_metric_name
```

### Metric Type Classification
```python
def is_simple_metric(metric: Metric) -> bool:
    """Simple metrics directly expose a single measure."""
    return isinstance(metric.type_params, SimpleMetricParams)

def is_complex_metric(metric: Metric) -> bool:
    """Complex metrics combine multiple measures."""
    return isinstance(metric.type_params, (RatioMetricParams, DerivedMetricParams))
```

## Algorithm

### Phase 1: Analyze Measure Usage
```python
def _analyze_measure_usage(
    self,
    models: list[SemanticModel],
    metrics: list[Metric]
) -> dict[str, MeasureUsage]:
    """Build map of measure name → usage info."""
    usage_map = {}

    # Initialize with all measures
    for model in models:
        for measure in model.measures:
            usage_map[measure.name] = MeasureUsage(
                measure_name=measure.name,
                source_model=model.name,
                simple_metric_name=None,
                complex_metric_refs=[]
            )

    # Track simple metric exposures
    for metric in metrics:
        if is_simple_metric(metric):
            measure_name = metric.type_params.measure
            if measure_name in usage_map:
                usage_map[measure_name].simple_metric_name = metric.name

    # Track complex metric references
    for metric in metrics:
        if is_complex_metric(metric):
            referenced_measures = extract_measure_dependencies(metric)
            for measure_name in referenced_measures:
                if measure_name in usage_map:
                    usage_map[measure_name].complex_metric_refs.append(metric.name)

    return usage_map
```

### Phase 2: Generate Measures

```python
def _generate_metric_measure(self, metric, model, models, metrics, usage_map):
    if is_simple_metric(metric):
        # Direct generation - use measure's aggregation type
        measure = self._find_measure(metric.type_params.measure, models)
        return {
            "name": metric.name,
            "type": LOOKML_TYPE_MAP[measure.agg],  # sum, count, etc.
            "sql": measure.expr or f"${{TABLE}}.{measure.name}",
            "label": metric.label,
            "description": metric.description,
            # NOT hidden - this is the visible metric
        }
    else:
        # Complex metric - type: number, reference other measures
        sql = self._generate_complex_sql(metric, models, usage_map)
        return {
            "name": metric.name,
            "type": "number",
            "sql": sql,
            ...
        }

def _resolve_measure_reference(self, measure_name, usage_map):
    """Resolve measure to LookML reference, preferring visible simple metrics."""
    usage = usage_map.get(measure_name)

    if usage and usage.simple_metric_name:
        # Reference the visible simple metric instead of hidden measure
        return f"${{{usage.simple_metric_name}}}"
    else:
        # Fall back to hidden measure
        return f"${{{measure_name}_measure}}"
```

### Phase 3: Generate Hidden Measures (Only When Needed)

```python
def _generate_hidden_measures(self, model, usage_map):
    """Generate hidden measures only for those that need them."""
    hidden_measures = []

    for measure in model.measures:
        usage = usage_map.get(measure.name)
        if usage and usage.needs_hidden_measure:
            hidden_measures.append({
                "name": f"{measure.name}_measure",
                "type": LOOKML_TYPE_MAP[measure.agg],
                "sql": measure.expr,
                "hidden": "yes",
            })

    return hidden_measures
```

## Dependencies

- **Depends on**: None
- **Packages**: No new packages needed
- **Patterns**: Existing measure/metric generation patterns in `generators/lookml.py`

## Testing Strategy

### Unit Tests (`test_lookml_generator.py`)

1. **Simple metric direct generation**
   - Input: Simple metric referencing `sum` measure
   - Assert: Output measure has `type: sum`, no hidden measure created

2. **Complex metric with hidden measures**
   - Input: Ratio metric with two measures, neither has simple metric
   - Assert: Two hidden measures created, ratio uses `type: number`

3. **Mixed scenario - simple + complex sharing measure**
   - Input: `total_revenue` measure with simple metric `rental_revenue` AND ratio metric using `total_revenue`
   - Assert: `rental_revenue` is `type: sum`, ratio refs `${rental_revenue}`, NO hidden `total_revenue_measure`

4. **Cross-entity references**
   - Input: Metric in model A referencing measure in model B
   - Assert: Correct view-qualified references

### Integration Tests

Using `src/tests/fixtures/real_semantic_models/` and `src/tests/fixtures/metrics/real_metrics.yml`:

1. Generate LookML from real fixtures
2. Count total measures (should be reduced vs. current)
3. Verify no hidden measures for measures exposed via simple metrics
4. Verify LookML syntax validity

### Coverage Target: 95%+

## Implementation Sequence

1. **Add measure usage analyzer** - `_analyze_measure_usage()` method
2. **Modify simple metric generation** - Use measure's type directly
3. **Modify measure reference resolution** - Prefer visible simple metrics
4. **Modify hidden measure generation** - Only when `needs_hidden_measure`
5. **Update view generation flow** - Integrate usage map
6. **Add unit tests** - Cover all scenarios
7. **Add integration tests** - Test with real fixtures
8. **Verify backward compatibility** - Existing tests still pass

## Edge Cases

1. **Measure with no metrics** - Don't generate anything (measure-only models are rare)
2. **Circular references** - Derived metrics referencing other derived metrics → resolve transitively
3. **Cross-entity simple metrics** - Simple metric in model A for measure in model B → still works
4. **Same measure name in multiple models** - Scope usage map by `model.measure_name`

## Open Questions

- Should we add a CLI flag to opt-out of this optimization for backward compatibility?
- Should orphan measures (no metrics) still generate hidden measures for manual SQL use?

## Estimated Complexity

**Complexity**: Medium
**Estimated Time**: 4-6 hours

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-036.md`
3. Change status from `backlog` to `strategy-approved`
4. Run: `/implement:1-spec DTL-036`
