# Implementation Spec: Update explore generation for metric requirements

## Metadata
- **Issue**: `DTL-026`
- **Stack**: `backend`
- **Generated**: 2025-11-18
- **Strategy**: Approved 2025-11-18
- **Type**: Feature

## Issue Context

### Problem Statement

Currently, the LookML generator creates explore joins that only expose dimensions from joined views using `fields: [view.dimensions_only*]`. This prevents cross-entity metrics from accessing measures in joined views, causing query failures when metrics reference measures across entity boundaries.

For example, a `search_conversion_rate` metric owned by the `searches` explore needs to access `rental_count` from the `rental_orders` view, but the join configuration doesn't expose measures.

### Solution Approach

Enhance the explore join generation logic in `LookMLGenerator._build_join_graph()` to analyze metric requirements at explore generation time and selectively expose required measures from joined views by augmenting the `fields` parameter.

The core architectural decision is to maintain backward compatibility (metrics parameter is optional) while adding intelligence to the join field selection process based on which metrics each explore owns.

### Success Criteria

1. Join fields lists include both `dimensions_only*` and explicitly listed required measures
2. Only measures actually required by cross-entity metrics are exposed
3. Measures from the base view are not included in required_fields
4. Multi-hop joins correctly expose required measures
5. No duplicate measures in fields lists
6. Empty case handled (no metrics → dimensions_only only)
7. View prefix applied correctly to all field names
8. Fields list output is deterministic (sorted) for reliable testing

## Approved Strategy Summary

The approved implementation strategy establishes the following key architectural decisions:

### Metric Analysis Location
Perform metric requirements analysis within `_build_join_graph()` at explore generation time. This provides full context (base model, all models, metrics) without requiring separate pre-processing passes.

### Metric Input Method
Add optional `metrics: list[Metric] | None = None` parameter to `LookMLGenerator.generate()` method, propagating through to explore generation. This maintains backward compatibility while enabling metric-aware join generation.

### Requirement Identification Algorithm
New method `_identify_metric_requirements()` will:
1. Filter metrics to those owned by the base explore (via `primary_entity` match)
2. Extract all measure dependencies using `extract_measure_dependencies()` from DTL-024
3. Map each measure to its source model
4. Return dictionary: `{model_name: set[measure_names]}`
5. Exclude measures from the base model itself

### Fields List Construction
After creating each join dictionary, check if the target model has required measures. If so, append them to the fields list in sorted order for deterministic output.

### View Prefix Handling
Consistently use prefixed view names throughout. The internal requirements dictionary uses unprefixed model names, but the generated fields list uses prefixed view names.

## Implementation Plan

### Phase 1: Method Signature Updates

Update all method signatures in the generation pipeline to accept and propagate the optional `metrics` parameter.

**Tasks**:
1. Update `generate()` method signature
2. Update `_generate_explores_lookml()` method signature
3. Update `_build_join_graph()` method signature
4. Add import statements for Metric type

### Phase 2: Implement Metric Requirements Identification

Create new method to analyze which measures from which models are required for metrics owned by a given explore.

**Tasks**:
1. Implement `_identify_metric_requirements()` method
2. Add logic to find primary entity for base model
3. Filter metrics by primary_entity ownership
4. Build model-to-measures mapping for efficient lookup
5. Extract and map measure dependencies

### Phase 3: Enhance Join Graph Building

Integrate metric requirements into the join generation process.

**Tasks**:
1. Call `_identify_metric_requirements()` at start of `_build_join_graph()`
2. After creating each join dictionary, check for required measures
3. Append required measures to fields list in sorted order
4. Ensure view prefix is applied correctly

### Phase 4: Add Type Imports

Set up proper type imports with TYPE_CHECKING guard to avoid circular dependencies.

**Tasks**:
1. Add TYPE_CHECKING import
2. Add conditional Metric import
3. Add Any import if not already present

### Phase 5: Unit Testing

Comprehensive unit tests covering all aspects of the new functionality.

**Tasks**:
1. Test `_identify_metric_requirements()` with various scenarios
2. Test `_build_join_graph()` with and without metrics
3. Test view prefix handling
4. Test deterministic output
5. Test multi-hop join scenarios

### Phase 6: Integration Testing

End-to-end tests with realistic fixtures.

**Tasks**:
1. Create semantic model fixtures
2. Create metric fixtures
3. Test full generation pipeline
4. Verify LookML syntax validity

## Detailed Task Breakdown

### Task 1: Update `generate()` Method Signature

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Location**: Line ~320

**Action**: Add optional `metrics` parameter and pass to explores generation

**Implementation Guidance**:
```python
def generate(
    self,
    models: list[SemanticModel],
    metrics: list[Metric] | None = None
) -> dict[str, str]:
    """Generate LookML files from semantic models.

    Args:
        models: List of semantic models to generate from.
        metrics: Optional list of metrics for cross-entity measure generation.
            When provided, explore joins will be enhanced to expose required
            measures from joined views based on metric dependencies.

    Returns:
        Dictionary mapping filename to file content.
    """
    files = {}

    # ... existing code ...

    # Update line ~355 to pass metrics
    if models:
        console.print("[bold blue]Generating explores file...[/bold blue]")
        explores_content = self._generate_explores_lookml(models, metrics)
        files["explores.lkml"] = explores_content
        console.print("  [green]✓[/green] Generated explores.lkml")
```

**Reference**: Existing pattern at line 320-367

**Tests**: Test that metrics parameter is accepted and passed through

---

### Task 2: Update `_generate_explores_lookml()` Method Signature

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Location**: Line ~481

**Action**: Add optional `metrics` parameter and pass to join graph building

**Implementation Guidance**:
```python
def _generate_explores_lookml(
    self,
    semantic_models: list[SemanticModel],
    metrics: list[Metric] | None = None
) -> str:
    """Generate LookML content for explores from semantic models.

    Only generates explores for fact tables (models with measures) and includes
    automatic join graph generation based on entity relationships.

    Args:
        semantic_models: List of semantic models to create explores for.
        metrics: Optional list of metrics for metric-aware join generation.

    Returns:
        The LookML content as a string with include statements and explores.
    """
    # ... existing code ...

    # Update line ~518 to pass metrics
    for fact_model in fact_models:
        # ... existing code ...

        # Build join graph for this fact model
        joins = self._build_join_graph(fact_model, semantic_models, metrics)
```

**Reference**: Existing pattern at line 481-559

**Tests**: Test that metrics are propagated to join graph building

---

### Task 3: Update `_build_join_graph()` Method Signature

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Location**: Line ~201

**Action**: Add optional `metrics` parameter and call requirements identification

**Implementation Guidance**:
```python
def _build_join_graph(
    self,
    fact_model: SemanticModel,
    all_models: list[SemanticModel],
    metrics: list[Metric] | None = None
) -> list[dict[str, Any]]:
    """Build a complete join graph for a fact table including multi-hop joins.

    This method traverses foreign key relationships to build a complete join graph.
    It handles both direct joins (fact → dimension) and multi-hop joins
    (fact → dim1 → dim2), as in rentals → searches → sessions.

    When metrics are provided, join field lists are enhanced to include measures
    required by cross-entity metrics owned by the fact model.

    Args:
        fact_model: The fact table semantic model to build joins for.
        all_models: All available semantic models.
        metrics: Optional list of metrics to analyze for required measure exposure.

    Returns:
        List of join dictionaries with keys: view_name, sql_on, relationship,
        type, fields.
    """
    joins = []
    visited = set()

    # Identify metric requirements if metrics provided
    metric_requirements: dict[str, set[str]] = {}
    if metrics:
        metric_requirements = self._identify_metric_requirements(
            fact_model, metrics, all_models
        )

    # ... existing BFS traversal code ...
```

**Reference**: Existing pattern at line 201-318

**Tests**: Test both with and without metrics parameter

---

### Task 4: Implement `_identify_metric_requirements()` Method

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Location**: New method, insert before `_build_join_graph()` (around line 200)

**Action**: Create new method to identify required measures by model

**Implementation Guidance**:
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

    A metric is "owned" by an explore if its primary_entity matches the explore's
    primary entity. Only owned metrics are considered when building requirements.

    Args:
        base_model: The semantic model serving as the explore base/spine.
        metrics: All metrics in the project.
        all_models: All semantic models for measure-to-model lookup.

    Returns:
        Dictionary mapping model name to set of required measure names.
        Example: {"rental_orders": {"rental_count"}, "users": {"user_count"}}

        Note: Model names in keys are unprefixed (internal representation).
        Measures from the base model itself are excluded.

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

**Reference**: Similar pattern to `_identify_fact_models()` at line 151-160

**Tests**: See comprehensive test cases in Testing Strategy section

---

### Task 5: Enhance Join Creation with Required Measures

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Location**: Line ~307 (after join dictionary creation)

**Action**: Add required measures to fields list if present

**Implementation Guidance**:
```python
# Existing code creates join dictionary (around line 302-308)
join = {
    "view_name": target_view_name,
    "sql_on": sql_on,
    "relationship": relationship,
    "type": "left_outer",
    "fields": [f"{target_view_name}.dimensions_only*"],
}

# NEW: Enhance fields list with required measures for cross-entity metrics
if target_model.name in metric_requirements:
    required_measures = sorted(metric_requirements[target_model.name])
    for measure_name in required_measures:
        join["fields"].append(f"{target_view_name}.{measure_name}")

joins.append(join)
```

**Important**:
- Use `target_model.name` (unprefixed) to look up in requirements
- Use `target_view_name` (prefixed) in the fields list
- Sort measures for deterministic output

**Reference**: Join creation at line 302-310

**Tests**: Test that fields list is correctly enhanced

---

### Task 6: Add Type Imports

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Location**: Top of file (around line 1-12)

**Action**: Add TYPE_CHECKING guard and Metric import

**Implementation Guidance**:
```python
"""Generator for creating LookML files from semantic models."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING

import lkml
from rich.console import Console

from dbt_to_lookml.interfaces.generator import Generator
from dbt_to_lookml.schemas import SemanticModel

# Conditional import to avoid circular dependencies
if TYPE_CHECKING:
    from dbt_to_lookml.schemas import Metric

console = Console()
```

**Note**: Use TYPE_CHECKING guard to prevent runtime circular import issues

**Reference**: Existing imports at line 1-12

**Tests**: Verify mypy --strict passes

---

## File Changes

### Files to Modify

#### `src/dbt_to_lookml/generators/lookml.py`

**Why**: Core implementation of metric-aware join generation

**Changes**:
- Add TYPE_CHECKING import and conditional Metric import (line ~1-12)
- Add new `_identify_metric_requirements()` method (before line 201)
- Update `_build_join_graph()` signature and add requirements identification (line 201-318)
- Update `_generate_explores_lookml()` signature to accept metrics (line 481)
- Update `generate()` signature to accept metrics (line 320)
- Enhance join field list construction with required measures (line ~307)

**Estimated lines**: ~120 new lines, ~15 modified lines

---

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
   - Action: Call `_identify_metric_requirements()`
   - Assert: Returns `{"rental_orders": {"rental_count"}}`

2. **`test_identify_metric_requirements_multiple_measures`**
   - Setup: Base model, metric requiring multiple measures from same joined model
   - Action: Call `_identify_metric_requirements()`
   - Assert: All measures included in set for that model

3. **`test_identify_metric_requirements_multiple_models`**
   - Setup: Base model, metric requiring measures from multiple different models
   - Action: Call `_identify_metric_requirements()`
   - Assert: Multiple entries in returned dictionary

4. **`test_identify_metric_requirements_excludes_base_model_measures`**
   - Setup: Metric requiring measure from base model and different model
   - Action: Call `_identify_metric_requirements()`
   - Assert: Base model's measure NOT in requirements (only cross-view measures)

5. **`test_identify_metric_requirements_deduplicates`**
   - Setup: Two metrics requiring same measure from same model
   - Action: Call `_identify_metric_requirements()`
   - Assert: Measure appears once in set (automatic deduplication via set)

6. **`test_identify_metric_requirements_no_primary_entity`**
   - Setup: Base model without primary entity
   - Action: Call `_identify_metric_requirements()`
   - Assert: Returns empty dict immediately

7. **`test_identify_metric_requirements_no_metrics`**
   - Setup: Empty metrics list
   - Action: Call `_identify_metric_requirements()`
   - Assert: Returns empty dict

8. **`test_identify_metric_requirements_no_owned_metrics`**
   - Setup: Metrics exist but none owned by this base model
   - Action: Call `_identify_metric_requirements()`
   - Assert: Returns empty dict

9. **`test_build_join_graph_no_metrics`**
   - Setup: Call `_build_join_graph()` with `metrics=None`
   - Action: Generate join graph
   - Assert: Fields list contains only `dimensions_only*` (backward compatibility)

10. **`test_build_join_graph_with_metric_requirements`**
    - Setup: Base model, joined model, metric requiring measure from joined model
    - Action: Call `_build_join_graph()` with metrics
    - Assert: Fields list contains `dimensions_only*` plus required measure

11. **`test_build_join_graph_multiple_required_measures`**
    - Setup: Multiple metrics requiring different measures from same joined model
    - Action: Call `_build_join_graph()` with metrics
    - Assert: Fields list includes all required measures (deduplicated)

12. **`test_build_join_graph_fields_deterministic`**
    - Setup: Multiple required measures in non-alphabetical order
    - Action: Call `_build_join_graph()` twice
    - Assert: Fields list is identical and sorted (deterministic)

13. **`test_build_join_graph_with_view_prefix`**
    - Setup: Generator with `view_prefix="v_"`, metric requirements
    - Action: Call `_build_join_graph()`
    - Assert: Fields list uses prefixed view names (e.g., `v_rental_orders.rental_count`)

14. **`test_build_join_graph_multi_hop_with_metrics`**
    - Setup: Multi-hop join (A → B → C), metric in A requiring measure from C
    - Action: Call `_build_join_graph()`
    - Assert: C's join includes required measure in fields list

### Mock Patterns

For unit tests that need Metric objects:

```python
from unittest.mock import MagicMock, patch

def create_mock_metric(
    name: str,
    primary_entity: str,
    measure_deps: set[str]
) -> MagicMock:
    """Create a mock Metric for testing."""
    metric = MagicMock()
    metric.name = name
    metric.primary_entity = primary_entity
    return metric

# Mock extract_measure_dependencies to return expected measures
@patch('dbt_to_lookml.parsers.dbt_metrics.extract_measure_dependencies')
def test_identify_metric_requirements_basic(mock_extract):
    mock_extract.return_value = {"rental_count"}

    generator = LookMLGenerator()
    metric = create_mock_metric("conversion", "search", {"rental_count"})

    # ... rest of test
```

### Integration Tests

**File**: `src/tests/integration/test_cross_entity_metrics.py` (new)

**Test Cases**:

1. **`test_end_to_end_explore_with_metric_requirements`**
   - Setup: Create real semantic model YAML files + metric YAML files
   - Action: Parse models + metrics, generate explores
   - Assert: Generated LookML contains enhanced fields lists
   - Assert: LookML syntax is valid via lkml.load()

2. **`test_explore_generation_backward_compatibility`**
   - Setup: Real semantic models, NO metrics
   - Action: Generate explores without metrics parameter
   - Assert: Fields lists unchanged (dimensions_only* only)
   - Assert: No errors or warnings

### Test Fixtures

**Required Fixtures** (in `src/tests/fixtures/` or test file):

1. **semantic_models/searches.yml**:
```yaml
semantic_models:
  - name: searches
    model: ref('fct_searches')
    entities:
      - name: search
        type: primary
        expr: search_sk
    measures:
      - name: search_count
        agg: count
        description: Count of searches
```

2. **semantic_models/rental_orders.yml**:
```yaml
semantic_models:
  - name: rental_orders
    model: ref('fct_rental_orders')
    entities:
      - name: rental
        type: primary
        expr: rental_sk
      - name: search
        type: foreign
        expr: search_sk
    measures:
      - name: rental_count
        agg: count
        description: Count of rentals
      - name: total_revenue
        agg: sum
        expr: revenue_amount
        description: Total revenue
```

3. **Mock metric for unit tests**:
```python
# In test file
mock_metric = MagicMock()
mock_metric.name = "search_conversion_rate"
mock_metric.primary_entity = "search"
# Mock extract_measure_dependencies to return {"rental_count", "search_count"}
```

---

## Validation Commands

**Run all checks**:
```bash
cd /Users/dug/Work/repos/dbt-to-lookml

# Format code
make format

# Run linting
make lint

# Run type checking
make type-check

# Run unit tests
make test-fast

# Run full test suite
make test-full

# Check coverage
make test-coverage

# Run all quality gates
make quality-gate
```

**Specific test commands**:
```bash
# Run only new test class
python -m pytest src/tests/unit/test_lookml_generator.py::TestMetricRequirementsForExplores -xvs

# Run specific test
python -m pytest src/tests/unit/test_lookml_generator.py::TestMetricRequirementsForExplores::test_identify_metric_requirements_basic -xvs

# Run with coverage for lookml.py
python -m pytest src/tests/unit/test_lookml_generator.py --cov=src/dbt_to_lookml/generators/lookml --cov-report=term-missing
```

---

## Dependencies

### Existing Dependencies

- `lkml`: LookML parsing and validation
- `pydantic`: Schema validation for SemanticModel
- `rich`: Console output formatting

### New Dependencies Needed

**From DTL-023** (must be implemented first):
- `Metric` base model in `schemas.py`
- `MetricTypeParams` union type
- `primary_entity` property on Metric

**From DTL-024** (must be implemented first):
- `extract_measure_dependencies(metric) -> set[str]` function in `parsers/dbt_metrics.py`
- Function must return all measure names referenced by a metric

**From DTL-025** (must be implemented first):
- `_extract_required_fields()` method pattern (similar logic needed)
- Understanding of measure-to-model mapping

---

## Implementation Notes

### Important Considerations

1. **Measure Not Found Handling**: If a metric references a measure that doesn't exist in any model, `_identify_metric_requirements()` skips it silently (logs warning in verbose mode). The validation layer (DTL-027) is responsible for catching semantic errors.

2. **Backward Compatibility**: All new parameters are optional with default `None`. Existing code calling `generate(models)` works unchanged with zero behavioral changes.

3. **View Prefix Consistency**: Internal requirements dictionary uses unprefixed model names (e.g., `"rental_orders"`), but generated fields lists use prefixed view names (e.g., `"v_rental_orders.rental_count"`).

4. **Deterministic Output**: Always use `sorted()` when iterating over required measures to ensure consistent, testable output.

5. **Primary Entity Ownership**: A metric is "owned" by an explore if `metric.primary_entity == base_model.primary_entity.name`. This determines which explore should generate measures for the metric.

### Code Patterns to Follow

**Pattern 1: Optional Parameter Propagation**
```python
def method(self, required_arg, optional_arg: Type | None = None):
    if optional_arg:
        # Use optional feature
    else:
        # Default behavior
```

**Pattern 2: Dictionary Comprehension for Model Mapping**
```python
model_view_names = {
    model.name: f"{self.view_prefix}{model.name}" for model in all_models
}
```

**Pattern 3: Set Operations for Deduplication**
```python
requirements: dict[str, set[str]] = {}
# Sets automatically deduplicate measure names
requirements[model_name].add(measure_name)
```

**Pattern 4: Sorted Iteration for Determinism**
```python
for measure_name in sorted(required_measures):
    join["fields"].append(f"{target_view_name}.{measure_name}")
```

### References

- `_build_join_graph()` existing implementation: Line 201-318
- `_identify_fact_models()` pattern: Line 151-160
- `generate()` existing implementation: Line 320-367
- `_generate_explores_lookml()` existing implementation: Line 481-559
- Existing test patterns: `src/tests/unit/test_lookml_generator.py` lines 1-150

---

## Edge Cases and Error Handling

### Edge Case 1: Measure Not Found in Any Model

**Scenario**: Metric references a measure name that doesn't exist in any semantic model.

**Handling**:
- `_identify_metric_requirements()` skips the measure (continues loop)
- Does not fail generation (assumes validation will catch this)
- Could log warning if verbose mode enabled
- Results in incomplete fields list (measure not exposed)

**Rationale**: Generator should be tolerant; validation layer (DTL-027) catches semantic errors.

### Edge Case 2: Base Model Has No Primary Entity

**Scenario**: Semantic model without primary entity.

**Handling**:
- `_identify_metric_requirements()` returns empty dict immediately
- No metrics can be owned by this model anyway (primary_entity required for ownership)

### Edge Case 3: Metric Requires Measure From Unavailable Join

**Scenario**: Metric requires measure from model that's not reachable via join graph.

**Handling**:
- `_build_join_graph()` only processes joins it discovers via entity relationships
- If model not in join graph, measure won't be exposed
- Validation layer (DTL-027) should detect unreachable measures
- This issue's scope: Only enhance joins that ARE in the graph; don't create new joins

### Edge Case 4: Multi-Hop Join Requirements

**Scenario**: Explore A → B → C, metric in A requires measure from C.

**Current Behavior**: `_build_join_graph()` already discovers C via BFS traversal.

**Enhancement**: When processing join to C, check if `target_model.name == "C"` is in metric_requirements.

**Expected Result**: C's join includes required measures in fields list.

### Edge Case 5: Circular Dependencies

**Scenario**: Models with circular foreign key relationships.

**Current Behavior**: `_build_join_graph()` uses `visited` set to prevent cycles (line 218).

**Enhancement Impact**: None; cycle prevention logic unchanged. Metric requirements don't affect traversal.

### Edge Case 6: Duplicate Measure Names Across Models

**Scenario**: Two different models both have a measure named "count".

**Current Behavior**: `extract_measure_dependencies()` returns measure names without model qualification.

**Handling**:
- `_identify_metric_requirements()` finds the FIRST model with matching measure name
- If multiple models have same measure name, first match wins
- Potential ambiguity issue

**Mitigation**: Document limitation; recommend unique measure names across models; validation layer should warn.

---

## Ready for Implementation

This spec is complete and ready for implementation. All architectural decisions have been approved, dependencies are documented, and comprehensive test coverage is planned.

**Next Steps**:
1. Ensure DTL-023, DTL-024, and DTL-025 are completed
2. Implement changes in order: imports → new method → signature updates → enhancement logic
3. Write unit tests alongside implementation (TDD approach recommended)
4. Run validation commands frequently
5. Create integration tests after unit tests pass
6. Update issue status to "Ready" when complete

**Estimated Implementation Time**: 4-6 hours implementation + 6-8 hours testing = 10-14 hours total

**Risk Level**: Low (well-isolated changes, backward compatible, extensive test coverage)
