---
id: DTL-026
title: "Implementation Strategy: Update explore generation for metric requirements"
created: 2025-11-18
status: approved
---

# DTL-026 Implementation Strategy: Update Explore Generation for Metric Requirements

## Executive Summary

This implementation enhances the explore join generation logic in `LookMLGenerator._build_join_graph()` to selectively expose measures from joined views when they are required by cross-entity metrics. The core architectural decision is to analyze metric dependencies at explore generation time and augment the `fields` parameter of join definitions to include both `dimensions_only*` (existing behavior) and explicitly listed required measures.

## Current State Analysis

### Existing Join Generation Logic

Location: `src/dbt_to_lookml/generators/lookml.py::_build_join_graph()` (lines 201-318)

**Current Behavior**:
- Traverses foreign key relationships using BFS to build complete join graphs
- Supports multi-hop joins (fact → dim1 → dim2) with 2-hop maximum depth
- Infers relationship cardinality based on entity types
- **Always sets**: `join["fields"] = [f"{target_view_name}.dimensions_only*"]`
- Does not consider metric requirements

**Key Methods**:
- `_build_join_graph(fact_model, all_models)` - Main join graph builder
- `_find_model_by_primary_entity(entity_name, models)` - Entity resolution
- `_identify_fact_models(models)` - Identifies models with measures
- `_infer_relationship(from_type, to_type, name_match)` - Cardinality inference
- `_generate_sql_on_clause(from_view, from_entity, to_view, to_entity)` - SQL generation

**Current Join Dictionary Structure**:
```python
join = {
    "view_name": "v_rental_orders",
    "sql_on": "${searches.search_sk} = ${rental_orders.search_sk}",
    "relationship": "many_to_one",
    "type": "left_outer",
    "fields": ["rental_orders.dimensions_only*"]  # ← Only dimensions exposed
}
```

### Dependencies

**Incoming** (Required from previous issues):
- DTL-023: `Metric` schema models with `primary_entity` property
- DTL-024: `extract_measure_dependencies(metric) -> set[str]` utility function
- DTL-025: `_extract_required_fields(metric, primary_model, all_models) -> list[str]` method

**Usage Pattern Expected**:
```python
# From DTL-024
from dbt_to_lookml.parsers.dbt_metrics import extract_measure_dependencies

# From DTL-025
required_fields = self._extract_required_fields(metric, base_model, all_models)
# Returns: ["rental_orders.rental_count", "users.user_count"]
```

## Architectural Decisions

### Decision 1: Metric Analysis Location

**Decision**: Perform metric requirements analysis within `_build_join_graph()` at explore generation time.

**Rationale**:
- Join graph construction already has full context (base model, all models)
- Avoids separate pre-processing pass
- Enables tight coupling between metric needs and join field exposure
- Maintains encapsulation within generator class

**Alternative Considered**: Pre-compute metric requirements in `_generate_explores_lookml()` and pass as parameter
- **Rejected**: Would require passing additional state through multiple method calls; increases coupling

### Decision 2: Metric Input Method

**Decision**: Add optional `metrics` parameter to `LookMLGenerator.generate()` and pass through to explore generation.

**Signature**:
```python
def generate(
    self,
    models: list[SemanticModel],
    metrics: list[Metric] | None = None
) -> dict[str, str]:
    """Generate LookML files from semantic models and optional metrics."""
```

**Rationale**:
- Maintains backward compatibility (metrics=None preserves existing behavior)
- Clear dependency injection pattern
- Follows existing generator interface patterns

**Alternative Considered**: Require metrics in constructor
- **Rejected**: Breaks backward compatibility; generator should remain stateless for models/metrics

### Decision 3: Requirement Identification Algorithm

**Method Signature**:
```python
def _identify_metric_requirements(
    self,
    base_model: SemanticModel,
    metrics: list[Metric],
    all_models: list[SemanticModel]
) -> dict[str, set[str]]:
    """
    Identify which measures from which models are required for metrics owned by base_model.

    Args:
        base_model: The semantic model serving as the explore base
        metrics: All metrics in the project
        all_models: All semantic models for measure lookup

    Returns:
        Dictionary mapping model name to set of required measure names:
        {
            "rental_orders": {"rental_count", "total_revenue"},
            "users": {"user_count"}
        }
    """
```

**Algorithm**:
1. Filter metrics to those owned by this explore: `metric.primary_entity == base_model.primary_entity.name`
2. For each owned metric:
   - Extract all measure dependencies (via `extract_measure_dependencies()` from DTL-024)
   - For each measure dependency:
     - Find which semantic model owns that measure
     - If model != base_model, add to requirements dictionary
3. Return aggregated requirements

**Key Design Choice**: Use `set[str]` for measure names to automatically deduplicate if multiple metrics require the same measure.

### Decision 4: Fields List Construction

**Enhancement Location**: Within `_build_join_graph()` after join dictionary creation.

**Logic**:
```python
# After current line 307 (join creation)
join = {
    "view_name": target_view_name,
    "sql_on": sql_on,
    "relationship": relationship,
    "type": "left_outer",
    "fields": [f"{target_view_name}.dimensions_only*"],  # Base case
}

# NEW: Enhance fields list if measures are required
if target_model.name in metric_requirements:
    required_measures = metric_requirements[target_model.name]
    for measure_name in sorted(required_measures):  # Sort for determinism
        join["fields"].append(f"{target_view_name}.{measure_name}")

joins.append(join)
```

**Rationale for `sorted()`**: Ensures deterministic output for testing; measure order doesn't affect functionality.

### Decision 5: View Prefix Handling

**Implementation**: Apply view prefix consistently throughout.

**Key Locations**:
```python
# Model name → View name mapping (already exists, line 221-223)
model_view_names = {
    model.name: f"{self.view_prefix}{model.name}" for model in all_models
}

# When adding measures to fields list
target_view_name = model_view_names[target_model.name]  # Already prefixed
join["fields"].append(f"{target_view_name}.{measure_name}")  # Prefix preserved
```

**Edge Case Handling**: Ensure metric requirements dictionary uses unprefixed model names (internal representation) while fields list uses prefixed view names (LookML output).

## Implementation Plan

### Phase 1: Method Signature Updates

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Changes**:
1. Update `generate()` method signature (line ~320):
   ```python
   def generate(
       self,
       models: list[SemanticModel],
       metrics: list[Metric] | None = None
   ) -> dict[str, str]:
   ```

2. Pass metrics to `_generate_explores_lookml()` (line ~355):
   ```python
   explores_content = self._generate_explores_lookml(models, metrics)
   ```

3. Update `_generate_explores_lookml()` signature (line ~481):
   ```python
   def _generate_explores_lookml(
       self,
       semantic_models: list[SemanticModel],
       metrics: list[Metric] | None = None
   ) -> str:
   ```

4. Pass metrics to `_build_join_graph()` (line ~518):
   ```python
   joins = self._build_join_graph(fact_model, semantic_models, metrics)
   ```

5. Update `_build_join_graph()` signature (line ~201):
   ```python
   def _build_join_graph(
       self,
       fact_model: SemanticModel,
       all_models: list[SemanticModel],
       metrics: list[Metric] | None = None
   ) -> list[dict[str, Any]]:
   ```

### Phase 2: Implement `_identify_metric_requirements()`

**Location**: New method in `LookMLGenerator`, before `_build_join_graph()`

**Implementation**:
```python
def _identify_metric_requirements(
    self,
    base_model: SemanticModel,
    metrics: list[Metric],
    all_models: list[SemanticModel]
) -> dict[str, set[str]]:
    """Identify which measures from joined views are required by cross-entity metrics.

    This method determines which measures from other semantic models need to be
    exposed in the explore's join definitions to support cross-entity metrics
    owned by the base model.

    Args:
        base_model: The semantic model serving as the explore base/spine.
        metrics: All metrics in the project.
        all_models: All semantic models for measure-to-model lookup.

    Returns:
        Dictionary mapping model name to set of required measure names.
        Example: {"rental_orders": {"rental_count"}, "users": {"user_count"}}

    Example:
        >>> # Given search_conversion_rate metric owned by searches model
        >>> # that requires rental_count from rental_orders model
        >>> requirements = generator._identify_metric_requirements(
        ...     searches_model, [conversion_metric], all_models
        ... )
        >>> requirements
        {"rental_orders": {"rental_count"}}
    """
    from dbt_to_lookml.parsers.dbt_metrics import extract_measure_dependencies

    requirements: dict[str, set[str]] = {}

    # Find the primary entity name for this base model
    base_entity_name = None
    for entity in base_model.entities:
        if entity.type == "primary":
            base_entity_name = entity.name
            break

    if not base_entity_name:
        # No primary entity, can't own metrics
        return requirements

    # Filter to metrics owned by this explore
    owned_metrics = [
        m for m in metrics
        if m.primary_entity == base_entity_name
    ]

    # Build model name → measures mapping for efficient lookup
    model_measures: dict[str, set[str]] = {}
    for model in all_models:
        model_measures[model.name] = {m.name for m in model.measures}

    # For each owned metric, extract measure dependencies
    for metric in owned_metrics:
        measure_deps = extract_measure_dependencies(metric)

        for measure_name in measure_deps:
            # Find which model owns this measure
            owner_model_name = None
            for model_name, measures in model_measures.items():
                if measure_name in measures:
                    owner_model_name = model_name
                    break

            if not owner_model_name:
                # Measure not found in any model - validation issue
                # Log warning but don't fail (validation should catch this)
                continue

            # Skip if measure is from the base model itself
            if owner_model_name == base_model.name:
                continue

            # Add to requirements
            if owner_model_name not in requirements:
                requirements[owner_model_name] = set()
            requirements[owner_model_name].add(measure_name)

    return requirements
```

### Phase 3: Enhance `_build_join_graph()`

**Location**: `src/dbt_to_lookml/generators/lookml.py` lines 201-318

**Changes**:

1. **At method start** (after line 218):
   ```python
   # Identify metric requirements if metrics provided
   metric_requirements: dict[str, set[str]] = {}
   if metrics:
       metric_requirements = self._identify_metric_requirements(
           fact_model, metrics, all_models
       )
   ```

2. **After join creation** (after line 307, before `joins.append(join)`):
   ```python
   # Enhance fields list with required measures for cross-entity metrics
   if target_model.name in metric_requirements:
       required_measures = sorted(metric_requirements[target_model.name])
       for measure_name in required_measures:
           join["fields"].append(f"{target_view_name}.{measure_name}")

   joins.append(join)
   ```

### Phase 4: Import Statement

**Location**: Top of `src/dbt_to_lookml/generators/lookml.py`

**Add**:
```python
from typing import Any

# Conditional import based on TYPE_CHECKING for circular dependency prevention
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dbt_to_lookml.schemas import Metric
```

**Note**: Use `TYPE_CHECKING` guard to avoid runtime circular imports if Metric references generator types.

## Testing Strategy

### Unit Tests

**File**: `src/tests/unit/test_lookml_generator.py`

**New Test Class**:
```python
class TestMetricRequirementsForExplores:
    """Tests for explore join enhancement based on metric requirements."""
```

**Test Cases**:

1. **`test_identify_metric_requirements_basic`**
   - Setup: Base model (searches), one metric requiring one measure from different model
   - Verify: Returns `{"rental_orders": {"rental_count"}}`

2. **`test_identify_metric_requirements_multiple_measures`**
   - Setup: Base model, metric requiring multiple measures from same joined model
   - Verify: All measures included in set for that model

3. **`test_identify_metric_requirements_multiple_models`**
   - Setup: Base model, metric requiring measures from multiple different models
   - Verify: Multiple entries in returned dictionary

4. **`test_identify_metric_requirements_excludes_base_model_measures`**
   - Setup: Metric requiring measure from base model and different model
   - Verify: Base model's measure NOT in requirements

5. **`test_identify_metric_requirements_deduplicates`**
   - Setup: Two metrics requiring same measure from same model
   - Verify: Measure appears once in set (set deduplication)

6. **`test_identify_metric_requirements_no_primary_entity`**
   - Setup: Base model without primary entity
   - Verify: Returns empty dict

7. **`test_identify_metric_requirements_no_metrics`**
   - Setup: Empty metrics list
   - Verify: Returns empty dict

8. **`test_identify_metric_requirements_no_owned_metrics`**
   - Setup: Metrics exist but none owned by this base model
   - Verify: Returns empty dict

9. **`test_build_join_graph_no_metrics`**
   - Setup: Call `_build_join_graph()` with `metrics=None`
   - Verify: Fields list contains only `dimensions_only*`

10. **`test_build_join_graph_with_metric_requirements`**
    - Setup: Base model, joined model, metric requiring measure from joined model
    - Verify: Fields list contains `dimensions_only*` plus required measure

11. **`test_build_join_graph_multiple_required_measures`**
    - Setup: Multiple metrics requiring different measures from same joined model
    - Verify: Fields list includes all required measures

12. **`test_build_join_graph_fields_deterministic`**
    - Setup: Multiple required measures
    - Verify: Fields list is sorted (deterministic order)

13. **`test_build_join_graph_with_view_prefix`**
    - Setup: Generator with view_prefix, metric requirements
    - Verify: Fields list uses prefixed view names

14. **`test_build_join_graph_multi_hop_with_metrics`**
    - Setup: Multi-hop join (A → B → C), metric in A requiring measure from C
    - Verify: C's join includes required measure

### Integration Tests

**File**: `src/tests/integration/test_cross_entity_metrics.py` (new)

**Test Cases**:

1. **`test_end_to_end_explore_with_metric_requirements`**
   - Setup: Real semantic model files + metric files
   - Parse models + metrics
   - Generate explores
   - Verify: Generated LookML contains enhanced fields lists
   - Verify: LookML syntax is valid

2. **`test_explore_generation_backward_compatibility`**
   - Setup: Real semantic models, NO metrics
   - Generate explores
   - Verify: Fields lists unchanged (dimensions_only* only)

### Test Fixtures

**Required Fixtures** (in `src/tests/fixtures/`):

1. **semantic_models/searches.yml**:
   ```yaml
   semantic_models:
     - name: searches
       entities:
         - name: search
           type: primary
       measures:
         - name: search_count
           type: count
   ```

2. **semantic_models/rental_orders.yml**:
   ```yaml
   semantic_models:
     - name: rental_orders
       entities:
         - name: rental
           type: primary
         - name: search
           type: foreign
       measures:
         - name: rental_count
           type: count
         - name: total_revenue
           type: sum
   ```

3. **metrics/search_conversion.yml**:
   ```yaml
   metrics:
     - name: search_conversion_rate
       type: ratio
       type_params:
         numerator: rental_count
         denominator: search_count
       meta:
         primary_entity: search
   ```

### Mock Patterns

For unit tests that need Metric objects:
```python
from unittest.mock import MagicMock

def create_mock_metric(
    name: str,
    primary_entity: str,
    measure_deps: list[str]
) -> MagicMock:
    """Create a mock Metric for testing."""
    metric = MagicMock()
    metric.name = name
    metric.primary_entity = primary_entity

    # Mock extract_measure_dependencies to return expected measures
    with patch('dbt_to_lookml.parsers.dbt_metrics.extract_measure_dependencies') as mock_extract:
        mock_extract.return_value = set(measure_deps)

    return metric
```

## Edge Cases and Error Handling

### Edge Case 1: Measure Not Found in Any Model

**Scenario**: Metric references a measure name that doesn't exist in any semantic model.

**Handling**:
- `_identify_metric_requirements()` skips the measure (logs warning if verbose)
- Doesn't fail generation (assumes validation will catch this in DTL-027)
- Results in incomplete fields list

**Rationale**: Generator should be tolerant; validation layer (DTL-027) is responsible for catching semantic errors.

### Edge Case 2: Base Model Has No Primary Entity

**Scenario**: Semantic model without primary entity.

**Handling**:
- `_identify_metric_requirements()` returns empty dict immediately
- No metrics can be owned by this model anyway (primary_entity required for metric ownership)

### Edge Case 3: Metric Requires Measure From Unavailable Join

**Scenario**: Metric requires measure from model that's not reachable via join graph.

**Handling**:
- `_build_join_graph()` only processes joins it discovers via entity relationships
- If model not in join graph, measure won't be exposed
- Validation layer (DTL-027) should detect unreachable measures

**This Issue's Scope**: Only enhance joins that ARE in the graph; don't create new joins.

### Edge Case 4: Multi-Hop Join Requirements

**Scenario**: Explore A → B → C, metric in A requires measure from C.

**Current Behavior**: `_build_join_graph()` already discovers C via BFS traversal.

**Enhancement**: When processing join to C, check if `target_model.name == "C"` is in metric_requirements.

**Expected Result**: C's join includes required measures.

### Edge Case 5: Circular Dependencies

**Scenario**: Models with circular foreign key relationships.

**Current Behavior**: `_build_join_graph()` uses `visited` set to prevent cycles (line 218).

**Enhancement Impact**: None; cycle prevention logic unchanged.

### Edge Case 6: Duplicate Measure Names Across Models

**Scenario**: Two different models both have a measure named "count".

**Current Behavior**: `extract_measure_dependencies()` returns measure names without model qualification.

**Handling**:
- `_identify_metric_requirements()` finds the FIRST model with matching measure name
- If multiple models have same measure name, first match wins
- Potential ambiguity issue

**Mitigation**: Document limitation; recommend unique measure names across models; validation layer should warn.

## Backward Compatibility

### API Compatibility

**Method Signature Changes**:
- All new parameters are optional with default `None`
- Existing code calling `generate(models)` works unchanged
- Existing code calling `_build_join_graph(fact, models)` works unchanged

**Behavior Changes**:
- When `metrics=None`, behavior identical to current implementation
- Zero breaking changes to existing consumers

### Generated LookML Compatibility

**Without Metrics**:
```lookml
fields: [rental_orders.dimensions_only*]
```
(No change from current output)

**With Metrics**:
```lookml
fields: [
  rental_orders.dimensions_only*,
  rental_orders.rental_count
]
```
(Enhanced but backward compatible - extra measures don't break existing queries)

## Performance Considerations

### Complexity Analysis

**`_identify_metric_requirements()`**:
- Time: O(M × D × N) where:
  - M = number of metrics owned by explore
  - D = average measure dependencies per metric
  - N = number of semantic models (for measure lookup)
- Space: O(R) where R = total unique required measures across all models
- **Optimization**: Build `model_measures` lookup dict once (O(N × A) where A = avg measures per model)

**`_build_join_graph()` Enhancement**:
- Added work: O(J × R) where:
  - J = number of joins in graph
  - R = average required measures per joined model
- Negligible compared to existing BFS traversal

**Expected Performance**:
- Typical project: 10-50 metrics, 20-100 models
- Requirements identification: < 10ms
- Join enhancement: < 1ms
- **Total overhead**: < 20ms per explore (acceptable)

### Caching Considerations

**Not Implemented in This Issue**:
- Metric requirements are recomputed per explore
- For large projects with many explores, could cache metric → model mapping

**Future Optimization** (if needed):
- Pre-compute global `measure_name → model_name` mapping once
- Pass as parameter to `_identify_metric_requirements()`

## Documentation Requirements

### Code Documentation

**Docstrings Required**:
1. `_identify_metric_requirements()` - Full docstring with examples
2. Updated docstring for `generate()` - Document metrics parameter
3. Updated docstring for `_build_join_graph()` - Document metrics parameter and behavior change

**Inline Comments**:
- Explain why measures from base model are excluded
- Clarify sorted() usage for determinism

### CLAUDE.md Updates

**Section to Add**: "Explore Generation with Metric Requirements"

**Content**:
```markdown
### Explore Generation with Metric Requirements

When metrics are provided to the generator, explore joins are automatically enhanced
to expose required measures from joined views.

**Without metrics** (default behavior):
```lookml
join: rental_orders {
  fields: [rental_orders.dimensions_only*]
}
```

**With metrics** (enhanced):
```lookml
join: rental_orders {
  fields: [
    rental_orders.dimensions_only*,
    rental_orders.rental_count,
    rental_orders.total_revenue
  ]
}
```

**Primary Entity Ownership**: Measures are exposed in joins only when the base
explore owns metrics that require them. A metric is owned by an explore if its
`primary_entity` matches the explore's primary entity.

**Algorithm**:
1. For each explore, identify owned metrics via primary_entity match
2. Extract measure dependencies from owned metrics
3. Map measures to their source models
4. Enhance join fields lists to include required measures
5. Maintain dimensions_only* for backward compatibility

See `LookMLGenerator._identify_metric_requirements()` for implementation details.
```

## Acceptance Criteria Verification

Mapping to issue acceptance criteria:

- [x] **`_identify_metric_requirements()` correctly finds required measures**
  - ✓ Implementation in Phase 2
  - ✓ Test cases 1-8 verify correctness

- [x] **Join fields include `dimensions_only*` plus required measures**
  - ✓ Implementation in Phase 3, step 2
  - ✓ Test cases 10-11 verify

- [x] **Base view measures not included in required_fields**
  - ✓ Implementation: Line excluding `owner_model_name == base_model.name`
  - ✓ Test case 4 verifies

- [x] **Multi-hop joins expose required measures**
  - ✓ Existing BFS traversal unchanged, enhancement applies to all joins
  - ✓ Test case 14 verifies

- [x] **No duplicate measures in fields list**
  - ✓ Using `set[str]` for requirements ensures uniqueness
  - ✓ Test case 5 verifies

- [x] **Empty case handled (no metrics → dimensions_only only)**
  - ✓ metrics=None preserves existing behavior
  - ✓ Test case 9 verifies

- [x] **View prefix applied correctly to field names**
  - ✓ Implementation uses `target_view_name` which is already prefixed
  - ✓ Test case 13 verifies

- [x] **Fields list is deterministic/sorted for testing**
  - ✓ Implementation uses `sorted(required_measures)`
  - ✓ Test case 12 verifies

## Risk Assessment

### Low Risk
- ✅ Backward compatible (all new params optional)
- ✅ Well-isolated changes (single file, clear boundaries)
- ✅ Extensive test coverage planned

### Medium Risk
- ⚠️ **Dependency on DTL-024**: Requires `extract_measure_dependencies()` to be correct
  - **Mitigation**: Unit tests mock this function; integration tests verify end-to-end
- ⚠️ **Measure name ambiguity**: Multiple models with same measure name
  - **Mitigation**: Document limitation; recommend unique names; validation layer warnings

### High Risk
- ❌ None identified

## Rollout Plan

### Phase 1: Implementation
1. Implement `_identify_metric_requirements()`
2. Update method signatures
3. Enhance `_build_join_graph()`
4. Add imports

### Phase 2: Unit Testing
1. Write tests for `_identify_metric_requirements()`
2. Write tests for enhanced `_build_join_graph()`
3. Achieve 95%+ branch coverage

### Phase 3: Integration Testing
1. Create test fixtures (semantic models + metrics)
2. Write end-to-end tests
3. Verify LookML syntax validity

### Phase 4: Documentation
1. Update CLAUDE.md
2. Add docstrings
3. Add inline comments

### Phase 5: Review
1. Code review focusing on edge cases
2. Performance testing with large projects
3. Final acceptance criteria verification

## Success Metrics

- ✅ All acceptance criteria verified
- ✅ 95%+ branch coverage on new code
- ✅ All unit tests passing
- ✅ All integration tests passing
- ✅ No performance regression (< 20ms overhead per explore)
- ✅ Zero breaking changes to existing API
- ✅ Documentation complete

## Open Questions

**Q1**: Should we warn when a measure is required but the model isn't in the join graph?
- **Decision**: No, defer to validation layer (DTL-027)

**Q2**: Should we auto-create joins for required models not in entity graph?
- **Decision**: No, out of scope; maintain principle that joins follow entity relationships

**Q3**: How to handle measure name collisions across models?
- **Decision**: First match wins; document limitation; recommend unique names

**Q4**: Should metric requirements be cached across explores?
- **Decision**: No, premature optimization; can add if performance issues arise

## Appendix: Example Scenarios

### Scenario A: Simple Cross-Entity Metric

**Input**:
- Searches model (primary: search, measures: search_count)
- Rental_orders model (primary: rental, foreign: search, measures: rental_count)
- Metric: search_conversion_rate (primary_entity: search, numerator: rental_count, denominator: search_count)

**Expected Output** (searches explore):
```lookml
join: rental_orders {
  sql_on: ${searches.search} = ${rental_orders.search} ;;
  relationship: many_to_one
  type: left_outer
  fields: [
    rental_orders.dimensions_only*,
    rental_orders.rental_count
  ]
}
```

### Scenario B: Multiple Required Measures

**Input**:
- Users model (primary: user, measures: user_count)
- Rental_orders model (foreign: user, measures: rental_count, total_revenue)
- Metric: engagement_score (primary_entity: user, requires: rental_count, total_revenue)

**Expected Output** (users explore):
```lookml
join: rental_orders {
  fields: [
    rental_orders.dimensions_only*,
    rental_orders.rental_count,
    rental_orders.total_revenue
  ]
}
```

### Scenario C: No Metrics

**Input**:
- Searches model
- Rental_orders model
- NO metrics

**Expected Output** (unchanged from current):
```lookml
join: rental_orders {
  fields: [rental_orders.dimensions_only*]
}
```

### Scenario D: Multi-Hop with Metrics

**Input**:
- Searches model (primary: search)
- Sessions model (primary: session, foreign: search, measures: session_count)
- Users model (primary: user, foreign: session, measures: user_count)
- Metric: search_to_user_ratio (primary_entity: search, requires: user_count)

**Expected Output** (searches explore):
```lookml
join: sessions {
  fields: [sessions.dimensions_only*]
}

join: users {
  fields: [
    users.dimensions_only*,
    users.user_count  # ← Required by cross-entity metric
  ]
}
```

---

## Approval

- **Strategy Status**: Approved
- **Ready for Implementation**: Yes
- **Blocked By**: DTL-023, DTL-024, DTL-025 (must be completed first)
- **Estimated Complexity**: Medium (4-6 hours implementation + 6-8 hours testing)
- **Risk Level**: Low
