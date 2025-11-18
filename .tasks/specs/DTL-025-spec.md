---
id: DTL-025-spec
issue: DTL-025
title: "Implementation Spec: Cross-Entity Measure Generation in LookMLGenerator"
created: 2025-11-18
status: ready
session: implement-spec-dtl-025
strategy: .tasks/strategies/DTL-025-strategy.md
---

# Implementation Spec: DTL-025 - Cross-Entity Measure Generation

## Metadata
- **Issue**: `DTL-025`
- **Stack**: `backend`
- **Generated**: 2025-11-18
- **Session**: `implement-spec-dtl-025`
- **Strategy**: Approved 2025-11-18

## Issue Context

### Problem Statement

Currently, `LookMLGenerator` can only generate measures that reference fields within their own view. However, dbt metrics often reference measures from multiple semantic models, requiring LookML measures that use `${view.measure}` syntax and the `required_fields` parameter to declare cross-view dependencies.

### Solution Approach

Extend `LookMLGenerator` to accept an optional `metrics` parameter and generate measures for those metrics in the appropriate views (based on `primary_entity`). The generated measures will use LookML's cross-view reference syntax and declare their dependencies via `required_fields`.

### Success Criteria

- Generate LookML measures from dbt Metric objects
- Support all metric types: simple, ratio, derived
- Correctly apply `${view.measure}` syntax for cross-view references
- Extract and populate `required_fields` with cross-view dependencies
- Apply view prefix consistently to all view references
- Maintain backward compatibility (metrics parameter is optional)
- Achieve 95%+ branch coverage on all new code

## Approved Strategy Summary

The approved strategy (DTL-025-strategy.md) defines:

1. **Primary Entity Ownership**: Metrics are generated in the view corresponding to their `primary_entity`
2. **Progressive Enhancement**: The `generate()` method accepts an optional `metrics` parameter (default: None)
3. **Type-Specific SQL Generation**: Separate methods handle simple, ratio, and derived metric SQL
4. **Required Fields Extraction**: Automatic detection of cross-view dependencies
5. **View Prefix Handling**: Consistent application of `view_prefix` to cross-view references

## Implementation Plan

### Phase 1: Helper Methods for Model/Measure Lookup

Add private helper methods to navigate the semantic model graph.

**Tasks**:
1. **Implement `_find_model_with_measure()`**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Add method after `_find_model_by_primary_entity()`
   - Pattern: Similar to existing `_find_model_by_primary_entity()`
   - Tests: Unit tests for found/not found cases

2. **Implement `_resolve_measure_reference()`**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Add method to convert measure name to LookML syntax
   - Pattern: Uses `_find_model_with_measure()` and `_find_model_by_primary_entity()`
   - Tests: Same view vs. cross-view cases

### Phase 2: SQL Generation for Simple Metrics

Implement SQL generation for the simplest metric type first.

**Tasks**:
1. **Implement `_generate_simple_sql()`**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Generate `${measure}` or `${view.measure}` syntax
   - Pattern: Uses `_resolve_measure_reference()`
   - Tests: Same view and cross-view references

### Phase 3: SQL Generation for Ratio Metrics

Implement SQL generation for ratio metrics with null safety.

**Tasks**:
1. **Implement `_generate_ratio_sql()`**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Generate `1.0 * num / NULLIF(denom, 0)` syntax
   - Pattern: Resolves both numerator and denominator references
   - Tests: Both same view, both cross-view, mixed cases

### Phase 4: SQL Generation for Derived Metrics

Implement SQL generation for derived metrics with expression substitution.

**Tasks**:
1. **Implement `_generate_derived_sql()`**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Parse expression and replace metric references
   - Pattern: String replacement for MVP (document limitations)
   - Tests: Simple expressions like "metric_a + metric_b"

### Phase 5: Required Fields Extraction

Implement dependency detection for cross-view measures.

**Tasks**:
1. **Implement `_extract_required_fields()`**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Extract measure dependencies, filter to cross-view only
   - Pattern: Type-specific extraction logic
   - Tests: Empty list (same view), single dependency, multiple dependencies

### Phase 6: Measure Metadata Inference

Implement helpers for value format and group label inference.

**Tasks**:
1. **Implement `_infer_value_format()`**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Infer format from metric type and name
   - Pattern: Heuristics (ratio → percent_2, revenue → usd, count → decimal_0)
   - Tests: All format types and None case

2. **Implement `_infer_group_label()`**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Infer group label from meta or model name
   - Pattern: Priority: meta.category → "{Model} Performance"
   - Tests: With and without meta.category

### Phase 7: Metric-to-Measure Conversion

Implement the main conversion method that orchestrates all helpers.

**Tasks**:
1. **Implement `_generate_metric_measure()`**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Convert Metric to complete LookML measure dict
   - Pattern: Dispatches to type-specific SQL generators, calls helper methods
   - Tests: Complete measure dict for each metric type

### Phase 8: Integration with View Generation

Update the main `generate()` method to accept and process metrics.

**Tasks**:
1. **Update `generate()` method signature**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Add `metrics: list[Metric] | None = None` parameter
   - Pattern: Backward compatible with default None
   - Tests: With and without metrics parameter

2. **Implement metric ownership mapping**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Build `dict[model_name, list[Metric]]` based on primary_entity
   - Pattern: Filter metrics to their owner models
   - Tests: Multiple metrics, multiple models, warnings for orphaned metrics

3. **Integrate metric measures into view generation**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Append metric measures to view_dict["views"][0]["measures"]
   - Pattern: After existing measure generation, before lkml.dump()
   - Tests: Metrics appended after original measures

### Phase 9: Error Handling and Validation

Add comprehensive error handling with clear messages.

**Tasks**:
1. **Add validation for missing measures**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Raise error if measure not found in any model
   - Pattern: In `_find_model_with_measure()` and `_resolve_measure_reference()`
   - Tests: Error messages with measure name

2. **Add warnings for orphaned metrics**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Log warning if metric's primary_entity doesn't match any model
   - Pattern: In `generate()` during ownership mapping
   - Tests: Console output verification

3. **Add validation for unsupported metric types**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Raise error for unknown type_params classes
   - Pattern: In `_generate_metric_measure()`
   - Tests: Error message with type name

### Phase 10: Testing and Documentation

Complete comprehensive test coverage and update documentation.

**Tasks**:
1. **Write unit tests for all new methods**
   - File: `src/tests/unit/test_lookml_generator.py`
   - Action: Add `TestMetricMeasureGeneration` and `TestMetricIntegration` classes
   - Pattern: Follow existing test patterns in the file
   - Tests: See detailed test breakdown below

2. **Update CLAUDE.md documentation**
   - File: `CLAUDE.md`
   - Action: Add section on cross-entity measure generation
   - Pattern: Include examples and usage notes
   - Tests: N/A (documentation)

## Detailed Task Breakdown

### Task 1: Implement `_find_model_with_measure()`

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Add method to find which semantic model contains a given measure

**Implementation Guidance**:
```python
def _find_model_with_measure(
    self,
    measure_name: str,
    models: dict[str, SemanticModel]
) -> SemanticModel | None:
    """Find which semantic model contains the given measure.

    Args:
        measure_name: Name of the measure to search for.
        models: Dictionary mapping model names to SemanticModel objects.

    Returns:
        The semantic model containing the measure, or None if not found.
    """
    for model in models.values():
        for measure in model.measures:
            if measure.name == measure_name:
                return model
    return None
```

**Reference**: Similar pattern to `_find_model_by_primary_entity()` at line 133-149

**Tests**:
- Test measure found in first model
- Test measure found in second model
- Test measure not found returns None
- Test empty models dict returns None

**Estimated lines**: ~10

---

### Task 2: Implement `_resolve_measure_reference()`

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Convert measure name to LookML reference syntax

**Implementation Guidance**:
```python
def _resolve_measure_reference(
    self,
    measure_name: str,
    primary_entity: str,
    models: dict[str, SemanticModel]
) -> str:
    """Resolve measure name to LookML reference syntax.

    Args:
        measure_name: Name of the measure to reference.
        primary_entity: Primary entity of the metric (determines "same view").
        models: Dictionary mapping model names to SemanticModel objects.

    Returns:
        LookML reference: "${measure}" or "${view_prefix}{model}.{measure}"

    Raises:
        ValueError: If measure not found in any model.
    """
    source_model = self._find_model_with_measure(measure_name, models)
    if not source_model:
        raise ValueError(f"Measure '{measure_name}' not found in any semantic model")

    primary_model = self._find_model_by_primary_entity(
        primary_entity, list(models.values())
    )

    # Same view reference (no prefix needed)
    if source_model.name == primary_model.name:
        return f"${{{measure_name}}}"

    # Cross-view reference (apply view prefix)
    view_name = f"{self.view_prefix}{source_model.name}"
    return f"${{{view_name}.{measure_name}}}"
```

**Reference**: Uses both helper methods defined earlier

**Tests**:
- Test same view returns `${measure}`
- Test cross-view returns `${view.measure}`
- Test view prefix applied to cross-view
- Test raises ValueError for missing measure
- Test error message includes measure name

**Estimated lines**: ~20

---

### Task 3: Implement `_generate_simple_sql()`

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Generate SQL for simple metrics

**Implementation Guidance**:
```python
def _generate_simple_sql(
    self,
    metric: Metric,
    models: dict[str, SemanticModel]
) -> str:
    """Generate SQL for simple metric.

    Args:
        metric: The metric with SimpleMetricParams.
        models: Dictionary of all semantic models.

    Returns:
        LookML SQL expression referencing the measure.
    """
    from dbt_to_lookml.schemas import SimpleMetricParams

    if not isinstance(metric.type_params, SimpleMetricParams):
        raise TypeError(f"Expected SimpleMetricParams, got {type(metric.type_params)}")

    measure_name = metric.type_params.measure
    primary_entity = metric.primary_entity

    if not primary_entity:
        raise ValueError(f"Metric '{metric.name}' has no primary_entity")

    return self._resolve_measure_reference(measure_name, primary_entity, models)
```

**Reference**: Strategy lines 120-158

**Tests**:
- Test simple metric same view
- Test simple metric cross-view
- Test view prefix applied
- Test raises error for missing primary_entity
- Test raises TypeError for wrong type_params

**Estimated lines**: ~15

---

### Task 4: Implement `_generate_ratio_sql()`

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Generate SQL for ratio metrics with null safety

**Implementation Guidance**:
```python
def _generate_ratio_sql(
    self,
    metric: Metric,
    models: dict[str, SemanticModel]
) -> str:
    """Generate SQL for ratio metric.

    Args:
        metric: The metric with RatioMetricParams.
        models: Dictionary of all semantic models.

    Returns:
        LookML SQL expression: "1.0 * num / NULLIF(denom, 0)"
    """
    from dbt_to_lookml.schemas import RatioMetricParams

    if not isinstance(metric.type_params, RatioMetricParams):
        raise TypeError(f"Expected RatioMetricParams, got {type(metric.type_params)}")

    numerator = metric.type_params.numerator
    denominator = metric.type_params.denominator
    primary_entity = metric.primary_entity

    if not primary_entity:
        raise ValueError(f"Metric '{metric.name}' has no primary_entity")

    # Resolve numerator reference
    num_ref = self._resolve_measure_reference(numerator, primary_entity, models)

    # Resolve denominator reference
    denom_ref = self._resolve_measure_reference(denominator, primary_entity, models)

    # Build ratio SQL with null safety
    return f"1.0 * {num_ref} / NULLIF({denom_ref}, 0)"
```

**Reference**: Strategy lines 160-195

**Tests**:
- Test both measures same view
- Test both measures cross-view
- Test numerator same view, denominator cross-view
- Test numerator cross-view, denominator same view
- Test view prefix applied
- Test NULLIF prevents division by zero
- Test raises error for missing primary_entity

**Estimated lines**: ~25

---

### Task 5: Implement `_generate_derived_sql()`

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Generate SQL for derived metrics (MVP: simple string replacement)

**Implementation Guidance**:
```python
def _generate_derived_sql(
    self,
    metric: Metric,
    models: dict[str, SemanticModel],
    all_metrics: list[Metric]
) -> str:
    """Generate SQL for derived metric.

    NOTE: MVP implementation uses simple string replacement.
    Limitations: Does not handle complex expressions with operators/functions
    that might conflict with metric names.

    Args:
        metric: The metric with DerivedMetricParams.
        models: Dictionary of all semantic models.
        all_metrics: List of all metrics (to resolve metric references).

    Returns:
        LookML SQL expression with metric references replaced.
    """
    from dbt_to_lookml.schemas import DerivedMetricParams

    if not isinstance(metric.type_params, DerivedMetricParams):
        raise TypeError(f"Expected DerivedMetricParams, got {type(metric.type_params)}")

    expr = metric.type_params.expr
    metric_refs = metric.type_params.metrics
    primary_entity = metric.primary_entity

    if not primary_entity:
        raise ValueError(f"Metric '{metric.name}' has no primary_entity")

    # Build replacement map: metric_name → ${view.measure}
    replacements = {}
    for ref in metric_refs:
        # Find the metric definition (metrics map to measures via same name)
        # This is a simplification - assumes metric name = measure name
        measure_name = ref.name
        measure_ref = self._resolve_measure_reference(
            measure_name, primary_entity, models
        )
        replacements[ref.name] = measure_ref

    # Replace all metric references in expression
    result_expr = expr
    for metric_name, measure_ref in replacements.items():
        result_expr = result_expr.replace(metric_name, measure_ref)

    return result_expr
```

**Reference**: Strategy lines 197-250

**Tests**:
- Test simple addition: "metric_a + metric_b"
- Test simple subtraction: "metric_a - metric_b"
- Test parentheses: "(metric_a + metric_b) / 2"
- Test multiple references to same metric
- Test cross-view metric references
- Test raises error for missing primary_entity

**Estimated lines**: ~40

---

### Task 6: Implement `_extract_required_fields()`

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Extract cross-view measure dependencies

**Implementation Guidance**:
```python
def _extract_required_fields(
    self,
    metric: Metric,
    primary_model: SemanticModel,
    all_models: list[SemanticModel]
) -> list[str]:
    """Extract required_fields list for metric.

    Only includes cross-view dependencies (measures from other views).

    Args:
        metric: The metric to extract dependencies from.
        primary_model: The semantic model that owns this metric.
        all_models: All available semantic models.

    Returns:
        Sorted list of required field references (e.g., ["view.measure"]).
    """
    from dbt_to_lookml.schemas import (
        SimpleMetricParams,
        RatioMetricParams,
        DerivedMetricParams
    )

    required = set()

    # Extract measure references based on type
    measures = []
    if isinstance(metric.type_params, SimpleMetricParams):
        measures = [metric.type_params.measure]
    elif isinstance(metric.type_params, RatioMetricParams):
        measures = [
            metric.type_params.numerator,
            metric.type_params.denominator
        ]
    elif isinstance(metric.type_params, DerivedMetricParams):
        # Extract from metric references (assume metric name = measure name)
        measures = [ref.name for ref in metric.type_params.metrics]

    # Build models lookup
    models_dict = {model.name: model for model in all_models}

    # Filter to cross-view references only
    for measure_name in measures:
        source_model = self._find_model_with_measure(measure_name, models_dict)
        if source_model and source_model.name != primary_model.name:
            view_name = f"{self.view_prefix}{source_model.name}"
            required.add(f"{view_name}.{measure_name}")

    return sorted(list(required))
```

**Reference**: Strategy lines 252-301

**Tests**:
- Test simple metric same view returns empty list
- Test simple metric cross-view returns one dependency
- Test ratio metric both cross-view returns two dependencies
- Test ratio metric mixed returns one dependency
- Test derived metric multiple dependencies
- Test view prefix applied to dependencies
- Test sorted output

**Estimated lines**: ~40

---

### Task 7: Implement `_infer_value_format()`

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Infer value format from metric type and name

**Implementation Guidance**:
```python
def _infer_value_format(self, metric: Metric) -> str | None:
    """Infer LookML value_format_name from metric type and name.

    Heuristics:
    - Ratio metrics → "percent_2"
    - Names with "revenue" or "price" → "usd"
    - Names with "count" → "decimal_0"
    - Default → None (Looker default)

    Args:
        metric: The metric to infer format for.

    Returns:
        Format name or None.
    """
    from dbt_to_lookml.schemas import RatioMetricParams

    if isinstance(metric.type_params, RatioMetricParams):
        return "percent_2"

    name_lower = metric.name.lower()
    if "revenue" in name_lower or "price" in name_lower:
        return "usd"
    if "count" in name_lower:
        return "decimal_0"

    return None
```

**Reference**: Strategy lines 352-375

**Tests**:
- Test ratio metric returns "percent_2"
- Test name with "revenue" returns "usd"
- Test name with "price" returns "usd"
- Test name with "count" returns "decimal_0"
- Test other name returns None
- Test case insensitive matching

**Estimated lines**: ~15

---

### Task 8: Implement `_infer_group_label()`

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Infer group label from meta or model name

**Implementation Guidance**:
```python
def _infer_group_label(
    self,
    metric: Metric,
    primary_model: SemanticModel
) -> str | None:
    """Infer group_label for metric.

    Priority:
    1. metric.meta.category (if present)
    2. "{Model Name} Performance" (from primary model)

    Args:
        metric: The metric to infer label for.
        primary_model: The model that owns this metric.

    Returns:
        Group label string or None.
    """
    if metric.meta and "category" in metric.meta:
        return metric.meta["category"].replace("_", " ").title()

    # Default: "{Model} Performance"
    model_name = primary_model.name.replace("_", " ").title()
    return f"{model_name} Performance"
```

**Reference**: Strategy lines 377-398

**Tests**:
- Test with meta.category returns category
- Test without meta returns "{Model} Performance"
- Test titlecase formatting
- Test underscore to space conversion

**Estimated lines**: ~15

---

### Task 9: Implement `_generate_metric_measure()`

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Main orchestration method to convert Metric to LookML measure dict

**Implementation Guidance**:
```python
def _generate_metric_measure(
    self,
    metric: Metric,
    primary_model: SemanticModel,
    all_models: list[SemanticModel],
    all_metrics: list[Metric] | None = None
) -> dict[str, Any]:
    """Generate LookML measure dict from metric definition.

    Args:
        metric: The metric to convert.
        primary_model: The semantic model that owns this metric.
        all_models: All available semantic models.
        all_metrics: All metrics (needed for derived metric resolution).

    Returns:
        Complete LookML measure dictionary.

    Raises:
        ValueError: If metric type is unsupported or validation fails.
    """
    from dbt_to_lookml.schemas import (
        SimpleMetricParams,
        RatioMetricParams,
        DerivedMetricParams
    )

    # Build models lookup dict for SQL generation
    models_dict = {model.name: model for model in all_models}

    # Generate SQL based on metric type
    if isinstance(metric.type_params, SimpleMetricParams):
        sql = self._generate_simple_sql(metric, models_dict)
    elif isinstance(metric.type_params, RatioMetricParams):
        sql = self._generate_ratio_sql(metric, models_dict)
    elif isinstance(metric.type_params, DerivedMetricParams):
        if all_metrics is None:
            raise ValueError("all_metrics required for derived metric generation")
        sql = self._generate_derived_sql(metric, models_dict, all_metrics)
    else:
        raise ValueError(f"Unsupported metric type: {type(metric.type_params)}")

    # Extract required fields
    required_fields = self._extract_required_fields(metric, primary_model, all_models)

    # Build measure dict
    measure_dict: dict[str, Any] = {
        "name": metric.name,
        "type": "number",  # Always number for cross-entity metrics
        "sql": sql,
        "view_label": " Metrics",  # Leading space for sort order
    }

    # Add value format
    value_format = self._infer_value_format(metric)
    if value_format:
        measure_dict["value_format_name"] = value_format

    # Add optional fields
    if metric.label:
        measure_dict["label"] = metric.label
    if metric.description:
        measure_dict["description"] = metric.description
    if required_fields:
        measure_dict["required_fields"] = required_fields

    # Add group_label
    group_label = self._infer_group_label(metric, primary_model)
    if group_label:
        measure_dict["group_label"] = group_label

    return measure_dict
```

**Reference**: Strategy lines 46-114

**Tests**:
- Test simple metric generates correct dict
- Test ratio metric generates correct dict
- Test derived metric generates correct dict
- Test required_fields populated for cross-view
- Test required_fields empty for same-view
- Test label and description included
- Test view_label is " Metrics"
- Test group_label inferred
- Test value_format_name inferred
- Test raises ValueError for unsupported type

**Estimated lines**: ~60

---

### Task 10: Update `generate()` method

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Add metrics parameter and integrate metric measure generation

**Implementation Guidance**:
```python
def generate(
    self,
    models: list[SemanticModel],
    metrics: list[Metric] | None = None
) -> dict[str, str]:
    """Generate LookML files from semantic models and metrics.

    Args:
        models: List of semantic models to generate from.
        metrics: Optional list of metrics to generate measures for.

    Returns:
        Dictionary mapping filename to file content.
    """
    files = {}

    console.print(
        f"[bold blue]Processing {len(models)} semantic models...[/bold blue]"
    )
    if metrics:
        console.print(f"[bold blue]Processing {len(metrics)} metrics...[/bold blue]")

    # Build metric ownership mapping: model_name → [metrics]
    metric_map: dict[str, list[Metric]] = {}
    if metrics:
        for metric in metrics:
            primary_entity = metric.primary_entity
            if not primary_entity:
                console.print(
                    f"[yellow]Warning: Metric '{metric.name}' has no primary_entity, skipping[/yellow]"
                )
                continue

            # Find model with this primary entity
            owner_model = self._find_model_by_primary_entity(primary_entity, models)
            if not owner_model:
                console.print(
                    f"[yellow]Warning: No model found for primary_entity '{primary_entity}', "
                    f"skipping metric '{metric.name}'[/yellow]"
                )
                continue

            if owner_model.name not in metric_map:
                metric_map[owner_model.name] = []
            metric_map[owner_model.name].append(metric)

    # Generate individual view files
    for i, model in enumerate(models, 1):
        console.print(
            f"  [{i}/{len(models)}] Processing [cyan]{model.name}[/cyan]..."
        )

        # Generate view content (existing logic, needs refactor)
        view_content = self._generate_view_lookml(model)

        # Check if we need to add metrics to this view
        owned_metrics = metric_map.get(model.name, [])
        if owned_metrics:
            console.print(f"    Adding {len(owned_metrics)} metric(s) to {model.name}")

            # Parse the existing view content back to dict to append measures
            view_dict = lkml.load(view_content)

            # Generate metric measures
            metric_measures = []
            for metric in owned_metrics:
                try:
                    measure_dict = self._generate_metric_measure(
                        metric, model, models, metrics
                    )
                    metric_measures.append(measure_dict)
                except Exception as e:
                    console.print(f"[red]Error generating metric '{metric.name}': {e}[/red]")

            # Append to existing measures in view_dict
            if metric_measures:
                if "measures" not in view_dict["views"][0]:
                    view_dict["views"][0]["measures"] = []
                view_dict["views"][0]["measures"].extend(metric_measures)

                # Re-dump to LookML
                view_content = lkml.dump(view_dict)
                if self.format_output:
                    view_content = self._format_lookml_content(view_content)

        # Add to files dict with sanitized filename
        view_name = f"{self.view_prefix}{model.name}"
        clean_view_name = self._sanitize_filename(view_name)
        filename = f"{clean_view_name}.view.lkml"

        files[filename] = view_content
        console.print(f"    [green]✓[/green] Generated {filename}")

    # Generate explores and model files (existing logic, unchanged)
    if models:
        console.print("[bold blue]Generating explores file...[/bold blue]")
        explores_content = self._generate_explores_lookml(models)
        files["explores.lkml"] = explores_content
        console.print("  [green]✓[/green] Generated explores.lkml")

    if models:
        console.print("[bold blue]Generating model file...[/bold blue]")
        model_content = self._generate_model_lookml()
        model_filename = f"{self._sanitize_filename(self.model_name)}.model.lkml"
        files[model_filename] = model_content
        console.print(f"  [green]✓[/green] Generated {model_filename}")

    return files
```

**Reference**: Strategy lines 400-484, existing `generate()` at line 320-367

**Tests**:
- Test generate without metrics (backward compatible)
- Test generate with metrics
- Test metric ownership filtering
- Test metrics appended to existing measures
- Test warning for missing primary_entity
- Test warning for unknown primary_entity
- Test error handling during metric generation

**Estimated lines**: ~100 (modification of existing method)

---

## File Changes

### Files to Modify

#### `src/dbt_to_lookml/generators/lookml.py`

**Why**: Core implementation of cross-entity measure generation

**Changes**:
- Add helper methods: `_find_model_with_measure()`, `_resolve_measure_reference()`
- Add SQL generation methods: `_generate_simple_sql()`, `_generate_ratio_sql()`, `_generate_derived_sql()`
- Add extraction method: `_extract_required_fields()`
- Add inference methods: `_infer_value_format()`, `_infer_group_label()`
- Add orchestration method: `_generate_metric_measure()`
- Update `generate()` method to accept and process metrics
- Add imports for Metric schema classes

**Estimated lines**: ~300 new lines, ~50 modified lines

#### `src/dbt_to_lookml/schemas.py`

**Why**: Need to import Metric types (assuming DTL-023 is complete)

**Changes**:
- Verify Metric, SimpleMetricParams, RatioMetricParams, DerivedMetricParams exist
- No changes needed if DTL-023 complete

**Estimated lines**: 0 (read-only dependency)

### Files to Create

#### `src/tests/unit/test_lookml_generator_metrics.py`

**Why**: Comprehensive unit tests for metric measure generation

**Structure**: Based on existing test patterns

```python
"""Unit tests for metric measure generation in LookMLGenerator."""

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.schemas import (
    Metric,
    SimpleMetricParams,
    RatioMetricParams,
    DerivedMetricParams,
    MetricReference,
    SemanticModel,
    Entity,
    Measure,
)
from dbt_to_lookml.types import AggregationType
import pytest


class TestMetricMeasureGeneration:
    """Test metric-to-measure conversion."""

    # Fixtures for test data
    @pytest.fixture
    def generator(self):
        return LookMLGenerator()

    @pytest.fixture
    def models_dict(self):
        # Create test semantic models with measures
        pass

    # Test simple metrics
    def test_generate_simple_metric_same_view(self, generator, models_dict):
        """Test simple metric where measure is in same view."""
        pass

    def test_generate_simple_metric_cross_view(self, generator, models_dict):
        """Test simple metric where measure is in different view."""
        pass

    # Test ratio metrics
    def test_generate_ratio_metric_both_cross_view(self, generator, models_dict):
        """Test ratio metric with num and denom from other views."""
        pass

    def test_generate_ratio_metric_mixed(self, generator, models_dict):
        """Test ratio metric with num from same view, denom from other."""
        pass

    # Test derived metrics
    def test_generate_derived_metric_simple(self, generator, models_dict):
        """Test derived metric with simple expression."""
        pass

    # Test value format inference
    def test_metric_value_format_inference(self, generator):
        """Test value_format_name inference."""
        pass

    # Test group label inference
    def test_metric_group_label_inference(self, generator):
        """Test group_label inference."""
        pass

    # Test view prefix handling
    def test_view_prefix_in_cross_references(self):
        """Test view prefix applied to cross-view references."""
        pass


class TestMetricIntegration:
    """Test integration of metrics with view generation."""

    def test_generate_with_metrics(self):
        """Test generate() method with metrics parameter."""
        pass

    def test_metric_ownership_filtering(self):
        """Test metrics only appear in primary entity's view."""
        pass

    def test_metrics_appended_to_measures(self):
        """Test metrics appended to existing measures."""
        pass

    def test_missing_primary_entity_warning(self):
        """Test warning when metric has no primary_entity."""
        pass

    def test_unknown_primary_entity_warning(self):
        """Test warning when primary_entity doesn't match any model."""
        pass
```

**Estimated lines**: ~600

## Testing Strategy

### Unit Tests

**File**: `src/tests/unit/test_lookml_generator_metrics.py` (new file)

**Test Cases**:

#### Helper Methods
1. **test_find_model_with_measure_found** - Measure exists in model
2. **test_find_model_with_measure_not_found** - Measure doesn't exist
3. **test_resolve_measure_reference_same_view** - Returns `${measure}`
4. **test_resolve_measure_reference_cross_view** - Returns `${view.measure}`
5. **test_resolve_measure_reference_with_prefix** - View prefix applied
6. **test_resolve_measure_reference_missing_measure** - Raises ValueError

#### SQL Generation - Simple
7. **test_generate_simple_sql_same_view** - SQL for same-view measure
8. **test_generate_simple_sql_cross_view** - SQL for cross-view measure
9. **test_generate_simple_sql_with_prefix** - View prefix in SQL
10. **test_generate_simple_sql_missing_primary_entity** - Raises ValueError

#### SQL Generation - Ratio
11. **test_generate_ratio_sql_both_same_view** - Both measures same view
12. **test_generate_ratio_sql_both_cross_view** - Both measures cross-view
13. **test_generate_ratio_sql_num_same_denom_cross** - Mixed references
14. **test_generate_ratio_sql_num_cross_denom_same** - Mixed references (inverse)
15. **test_generate_ratio_sql_nullif_safety** - NULLIF in SQL
16. **test_generate_ratio_sql_missing_primary_entity** - Raises ValueError

#### SQL Generation - Derived
17. **test_generate_derived_sql_simple_addition** - "metric_a + metric_b"
18. **test_generate_derived_sql_simple_subtraction** - "metric_a - metric_b"
19. **test_generate_derived_sql_with_parentheses** - "(metric_a + metric_b) / 2"
20. **test_generate_derived_sql_cross_view_refs** - Cross-view metric refs
21. **test_generate_derived_sql_missing_primary_entity** - Raises ValueError

#### Required Fields Extraction
22. **test_extract_required_fields_simple_same_view** - Empty list
23. **test_extract_required_fields_simple_cross_view** - One dependency
24. **test_extract_required_fields_ratio_both_cross** - Two dependencies
25. **test_extract_required_fields_ratio_mixed** - One dependency
26. **test_extract_required_fields_derived_multiple** - Multiple dependencies
27. **test_extract_required_fields_with_prefix** - View prefix in fields
28. **test_extract_required_fields_sorted** - Output sorted

#### Inference Methods
29. **test_infer_value_format_ratio** - Returns "percent_2"
30. **test_infer_value_format_revenue** - Returns "usd"
31. **test_infer_value_format_price** - Returns "usd"
32. **test_infer_value_format_count** - Returns "decimal_0"
33. **test_infer_value_format_other** - Returns None
34. **test_infer_value_format_case_insensitive** - Case doesn't matter
35. **test_infer_group_label_with_meta** - Uses meta.category
36. **test_infer_group_label_without_meta** - Uses "{Model} Performance"
37. **test_infer_group_label_formatting** - Titlecase and spaces

#### Metric Measure Generation
38. **test_generate_metric_measure_simple** - Complete dict for simple
39. **test_generate_metric_measure_ratio** - Complete dict for ratio
40. **test_generate_metric_measure_derived** - Complete dict for derived
41. **test_generate_metric_measure_required_fields** - Cross-view deps
42. **test_generate_metric_measure_no_required_fields** - Same-view only
43. **test_generate_metric_measure_labels** - Label and description
44. **test_generate_metric_measure_view_label** - " Metrics" with space
45. **test_generate_metric_measure_group_label** - Inferred label
46. **test_generate_metric_measure_value_format** - Inferred format
47. **test_generate_metric_measure_unsupported_type** - Raises ValueError

#### Integration Tests
48. **test_generate_without_metrics** - Backward compatible
49. **test_generate_with_metrics** - Metrics added to views
50. **test_generate_metric_ownership** - Correct view assignment
51. **test_generate_metrics_appended** - After original measures
52. **test_generate_missing_primary_entity_warning** - Console warning
53. **test_generate_unknown_primary_entity_warning** - Console warning
54. **test_generate_metric_error_handling** - Error during generation

### Coverage Target

- **New methods**: 95%+ branch coverage
- **Modified methods**: Maintain existing coverage
- **Overall generator module**: 95%+

## Validation Commands

**Type checking**:
```bash
cd /Users/dug/Work/repos/dbt-to-lookml
make type-check
# or
mypy src/dbt_to_lookml/generators/lookml.py --strict
```

**Linting**:
```bash
make lint
# or
ruff check src/dbt_to_lookml/generators/lookml.py
```

**Formatting**:
```bash
make format
# or
ruff format src/dbt_to_lookml/generators/lookml.py
```

**Unit tests (fast feedback)**:
```bash
make test-fast
# or
python -m pytest src/tests/unit/test_lookml_generator_metrics.py -v
```

**Single test method**:
```bash
python -m pytest src/tests/unit/test_lookml_generator_metrics.py::TestMetricMeasureGeneration::test_generate_simple_metric_same_view -xvs
```

**Coverage report**:
```bash
make test-coverage
# Then open: htmlcov/index.html
```

**Full quality gate**:
```bash
make quality-gate
# Runs: lint + types + tests
```

## Dependencies

### Existing Dependencies

**DTL-023: Metric Schema Models**
- `Metric` - Base metric model
- `SimpleMetricParams` - Simple metric type params
- `RatioMetricParams` - Ratio metric type params
- `DerivedMetricParams` - Derived metric type params
- `MetricReference` - For derived metric references
- `metric.primary_entity` property

**Required imports**:
```python
from dbt_to_lookml.schemas import (
    Metric,
    SimpleMetricParams,
    RatioMetricParams,
    DerivedMetricParams,
    MetricReference,
)
```

**DTL-024: Metric Parser**
- `DbtMetricParser.parse_directory()` - Returns `list[Metric]`
- Integration in CLI for reading metric files

### New Dependencies Needed

None - all dependencies are existing packages or blocked issues.

## Implementation Notes

### Important Considerations

1. **Metric Name = Measure Name Assumption**: The MVP assumes that derived metrics reference other metrics by the same name as their corresponding measures. This is a simplification that may need refinement.

2. **Derived Metric Limitations**: The MVP uses simple string replacement for derived metric expressions. This doesn't handle:
   - Complex expressions where operator precedence matters
   - Function calls that might contain metric names as substrings
   - Quoted strings containing metric names
   - **Document this limitation** in docstrings and CLAUDE.md

3. **Primary Entity Requirement**: All metrics must have a `primary_entity` (explicit or inferred). Metrics without this are skipped with warnings.

4. **View Dict Manipulation**: The current approach parses generated LookML back to dict to append measures. Consider refactoring `_generate_view_lookml()` to return a dict instead of a string for cleaner integration.

5. **Error Handling Philosophy**: Non-critical errors (missing primary_entity, unknown primary_entity) log warnings and skip the metric. Critical errors (measure not found, unsupported type) raise exceptions.

### Code Patterns to Follow

1. **Type Narrowing with isinstance()**: Use `isinstance()` checks to narrow Union types for mypy
   ```python
   if isinstance(metric.type_params, SimpleMetricParams):
       # mypy knows metric.type_params is SimpleMetricParams here
       measure_name = metric.type_params.measure
   ```

2. **Console Output**: Use `rich.console.Console` for all user-facing output
   ```python
   console.print(f"[yellow]Warning: {message}[/yellow]")
   console.print(f"[red]Error: {message}[/red]")
   console.print(f"[green]✓[/green] Success")
   ```

3. **Measure Dict Building**: Follow existing pattern from `Measure._to_lookml_dict()`
   ```python
   measure_dict: dict[str, Any] = {
       "name": metric.name,
       "type": "number",
       "sql": sql,
   }
   # Add optional fields only if present
   if metric.label:
       measure_dict["label"] = metric.label
   ```

4. **Test Fixtures**: Use pytest fixtures for reusable test data
   ```python
   @pytest.fixture
   def sample_models(self):
       return [
           SemanticModel(...),
           SemanticModel(...),
       ]
   ```

### References

- **Existing entity lookup**: `_find_model_by_primary_entity()` at line 133-149
- **Existing join building**: `_build_join_graph()` at line 201-318
- **Existing view generation**: `_generate_view_lookml()` at line 415-458
- **Existing test patterns**: `test_lookml_generator.py` lines 27-249
- **Existing measure conversion**: `schemas.py:Measure._to_lookml_dict()` (search for class Measure)

## Ready for Implementation

This spec is complete and ready for the `/implement` workflow.

**Estimated Implementation Time**: 2-3 weeks

**Confidence Level**: High - all architectural decisions made, dependencies clear, test plan comprehensive

**Risks**:
- Derived metric expression parsing (mitigated with MVP approach)
- Test coverage might require >54 tests to reach 95% (mitigated with detailed test plan)

**Next Steps**:
1. Verify DTL-023 and DTL-024 are complete
2. Create feature branch: `feature/DTL-025-cross-entity-measures`
3. Implement in order: helpers → simple → ratio → derived → integration
4. Write tests alongside implementation (TDD approach)
5. Run `make quality-gate` after each phase
6. Update CLAUDE.md when complete
