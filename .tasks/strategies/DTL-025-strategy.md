---
id: DTL-025-strategy
issue: DTL-025
title: "Implementation Strategy: Cross-Entity Measure Generation in LookMLGenerator"
created: 2025-11-18
status: draft
---

# Implementation Strategy: DTL-025 - Cross-Entity Measure Generation

## Executive Summary

This strategy outlines the implementation approach for adding cross-entity metric support to `LookMLGenerator`. The core challenge is converting dbt metrics (which reference measures across multiple semantic models) into LookML measures that use `${view.measure}` syntax and `required_fields` parameters.

**Key Architectural Decisions**:
1. **Primary Entity Ownership**: Metrics are generated in the view corresponding to their `primary_entity`
2. **Progressive Enhancement**: Metrics are optional input to `generate()` method (backward compatible)
3. **SQL Generation by Type**: Type-specific methods handle simple, ratio, and derived metric SQL generation
4. **Required Fields Extraction**: Automatic detection of cross-view dependencies for `required_fields` parameter
5. **View Prefix Handling**: Consistent application of view prefix to cross-view references

## Architecture Overview

### Data Flow

```
Metrics (from DTL-024) + SemanticModels
         ↓
LookMLGenerator.generate(models, metrics)
         ↓
Filter metrics by primary_entity → semantic model mapping
         ↓
For each metric:
  1. _generate_metric_measure() → measure dict
  2. _generate_[type]_sql() → SQL expression
  3. _extract_required_fields() → dependency list
  4. _infer_value_format() → format name
         ↓
Append metric measures to view's measures list
         ↓
Standard view generation continues
```

### Key Components

#### 1. Metric-to-Measure Conversion (`_generate_metric_measure`)

**Purpose**: Convert a `Metric` object to a LookML measure dictionary.

**Inputs**:
- `metric: Metric` - The metric to convert
- `primary_model: SemanticModel` - The semantic model that owns this metric
- `all_models: list[SemanticModel]` - All models (for resolving cross-view references)

**Outputs**:
- `dict[str, Any]` - LookML measure dictionary

**Logic**:
```python
def _generate_metric_measure(
    self,
    metric: Metric,
    primary_model: SemanticModel,
    all_models: list[SemanticModel]
) -> dict[str, Any]:
    """
    Generate LookML measure dict from metric definition.

    Algorithm:
    1. Generate SQL based on metric type (dispatch to type-specific method)
    2. Extract required_fields (cross-view dependencies)
    3. Infer value_format_name from metric type/name
    4. Build metadata (label, description, view_label, group_label)
    5. Return complete measure dict
    """
    # Build models lookup dict for SQL generation
    models_dict = {model.name: model for model in all_models}

    # Generate SQL based on metric type
    if isinstance(metric.type_params, SimpleMetricParams):
        sql = self._generate_simple_sql(metric, models_dict)
    elif isinstance(metric.type_params, RatioMetricParams):
        sql = self._generate_ratio_sql(metric, models_dict)
    elif isinstance(metric.type_params, DerivedMetricParams):
        sql = self._generate_derived_sql(metric, models_dict)
    else:
        raise ValueError(f"Unsupported metric type: {type(metric.type_params)}")

    # Extract required fields
    required_fields = self._extract_required_fields(metric, primary_model, all_models)

    # Build measure dict
    measure_dict = {
        "name": metric.name,
        "type": "number",  # Always number for cross-entity metrics
        "sql": sql,
        "value_format_name": self._infer_value_format(metric),
        "view_label": " Metrics",  # Leading space for sort order
    }

    # Add optional fields
    if metric.label:
        measure_dict["label"] = metric.label
    if metric.description:
        measure_dict["description"] = metric.description
    if required_fields:
        measure_dict["required_fields"] = required_fields

    # Add group_label (infer from meta or model name)
    group_label = self._infer_group_label(metric, primary_model)
    if group_label:
        measure_dict["group_label"] = group_label

    return measure_dict
```

#### 2. SQL Generation by Metric Type

##### Simple Metrics (`_generate_simple_sql`)

**Purpose**: Generate SQL for simple metrics (direct measure reference).

**Logic**:
```python
def _generate_simple_sql(
    self,
    metric: Metric,
    models: dict[str, SemanticModel]
) -> str:
    """
    Generate SQL for simple metric.

    Algorithm:
    1. Extract measure name from type_params.measure
    2. Find which semantic model contains this measure
    3. If same model as primary_entity: ${measure}
    4. If different model: ${view_prefix}{model_name}.{measure}
    """
    params = metric.type_params  # SimpleMetricParams
    measure_name = params.measure

    # Find model containing this measure
    source_model = self._find_model_with_measure(measure_name, models)
    if not source_model:
        raise ValueError(f"Measure '{measure_name}' not found in any semantic model")

    # Determine primary model from metric.meta.primary_entity
    primary_entity = metric.primary_entity
    primary_model = self._find_model_by_primary_entity(primary_entity, list(models.values()))

    # Same view reference (no prefix needed)
    if source_model.name == primary_model.name:
        return f"${{{measure_name}}}"

    # Cross-view reference (apply view prefix)
    view_name = f"{self.view_prefix}{source_model.name}"
    return f"${{{view_name}.{measure_name}}}"
```

##### Ratio Metrics (`_generate_ratio_sql`)

**Purpose**: Generate SQL for ratio metrics (numerator / denominator).

**Logic**:
```python
def _generate_ratio_sql(
    self,
    metric: Metric,
    models: dict[str, SemanticModel]
) -> str:
    """
    Generate SQL for ratio metric.

    Algorithm:
    1. Extract numerator and denominator measure names
    2. Resolve each to ${view.measure} syntax
    3. Apply ratio formula: 1.0 * num / NULLIF(denom, 0)
    """
    params = metric.type_params  # RatioMetricParams
    numerator = params.numerator
    denominator = params.denominator

    # Resolve numerator reference
    num_ref = self._resolve_measure_reference(
        numerator, metric.primary_entity, models
    )

    # Resolve denominator reference
    denom_ref = self._resolve_measure_reference(
        denominator, metric.primary_entity, models
    )

    # Build ratio SQL with null safety
    return f"1.0 * {num_ref} / NULLIF({denom_ref}, 0)"
```

##### Derived Metrics (`_generate_derived_sql`)

**Purpose**: Generate SQL for derived metrics (expression with metric references).

**Logic**:
```python
def _generate_derived_sql(
    self,
    metric: Metric,
    models: dict[str, SemanticModel]
) -> str:
    """
    Generate SQL for derived metric.

    Algorithm:
    1. Parse expr from type_params
    2. Identify all metric references in expr
    3. Replace each metric reference with ${view.measure} syntax
    4. Return transformed expression

    Note: This is complex - may need expression parser.
    For MVP, can support simple cases like "metric_a + metric_b"
    """
    params = metric.type_params  # DerivedMetricParams
    expr = params.expr
    metric_refs = params.metrics

    # Build replacement map: metric_name → ${view.measure}
    replacements = {}
    for ref in metric_refs:
        # Find the metric definition
        source_metric = self._find_metric_by_name(ref.name, all_metrics)
        if not source_metric:
            raise ValueError(f"Metric '{ref.name}' not found")

        # Convert metric to measure reference
        # (Metrics map to measures via same name convention)
        measure_ref = self._resolve_measure_reference(
            ref.name, metric.primary_entity, models
        )
        replacements[ref.name] = measure_ref

    # Replace all metric references in expression
    result_expr = expr
    for metric_name, measure_ref in replacements.items():
        result_expr = result_expr.replace(metric_name, measure_ref)

    return result_expr
```

**Note**: Derived metrics are complex. For MVP (DTL-025), we can:
- Implement simple string replacement
- Document limitations (no complex expressions)
- Plan enhancement in future iteration

#### 3. Required Fields Extraction (`_extract_required_fields`)

**Purpose**: Identify which fields from other views this metric requires.

**Logic**:
```python
def _extract_required_fields(
    self,
    metric: Metric,
    primary_model: SemanticModel,
    all_models: list[SemanticModel]
) -> list[str]:
    """
    Extract required_fields list for metric.

    Algorithm:
    1. Extract all measure references from metric (type-specific)
    2. Resolve each measure to source model
    3. If source model != primary model: add to required_fields
    4. Format as "{view_prefix}{model_name}.{measure_name}"
    5. Return sorted list
    """
    required = set()

    # Extract measure references based on type
    if isinstance(metric.type_params, SimpleMetricParams):
        measures = [metric.type_params.measure]
    elif isinstance(metric.type_params, RatioMetricParams):
        measures = [
            metric.type_params.numerator,
            metric.type_params.denominator
        ]
    elif isinstance(metric.type_params, DerivedMetricParams):
        # Extract from metric references
        measures = [ref.name for ref in metric.type_params.metrics]
    else:
        measures = []

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

#### 4. Helper Methods

##### Find Model with Measure (`_find_model_with_measure`)

```python
def _find_model_with_measure(
    self,
    measure_name: str,
    models: dict[str, SemanticModel]
) -> SemanticModel | None:
    """Find which semantic model contains the given measure."""
    for model in models.values():
        for measure in model.measures:
            if measure.name == measure_name:
                return model
    return None
```

##### Resolve Measure Reference (`_resolve_measure_reference`)

```python
def _resolve_measure_reference(
    self,
    measure_name: str,
    primary_entity: str,
    models: dict[str, SemanticModel]
) -> str:
    """
    Resolve measure name to LookML reference syntax.

    Returns:
    - Same view: "${measure_name}"
    - Cross view: "${view_prefix}{model_name}.{measure_name}"
    """
    source_model = self._find_model_with_measure(measure_name, models)
    if not source_model:
        raise ValueError(f"Measure '{measure_name}' not found")

    primary_model = self._find_model_by_primary_entity(
        primary_entity, list(models.values())
    )

    if source_model.name == primary_model.name:
        return f"${{{measure_name}}}"

    view_name = f"{self.view_prefix}{source_model.name}"
    return f"${{{view_name}.{measure_name}}}"
```

##### Infer Value Format (`_infer_value_format`)

```python
def _infer_value_format(self, metric: Metric) -> str | None:
    """
    Infer LookML value_format_name from metric type and name.

    Heuristics:
    - Ratio metrics → "percent_2"
    - Names with "revenue" or "price" → "usd"
    - Names with "count" → "decimal_0"
    - Default → None (Looker default)
    """
    if isinstance(metric.type_params, RatioMetricParams):
        return "percent_2"

    name_lower = metric.name.lower()
    if "revenue" in name_lower or "price" in name_lower:
        return "usd"
    if "count" in name_lower:
        return "decimal_0"

    return None
```

##### Infer Group Label (`_infer_group_label`)

```python
def _infer_group_label(
    self,
    metric: Metric,
    primary_model: SemanticModel
) -> str | None:
    """
    Infer group_label for metric.

    Priority:
    1. metric.meta.category (if present)
    2. "{Model Name} Performance" (from primary model)
    """
    if metric.meta and "category" in metric.meta:
        return metric.meta["category"].replace("_", " ").title()

    # Default: "{Model} Performance"
    model_name = primary_model.name.replace("_", " ").title()
    return f"{model_name} Performance"
```

### 5. Integration with View Generation

Update the `generate()` method to accept optional metrics:

```python
def generate(
    self,
    models: list[SemanticModel],
    metrics: list[Metric] | None = None
) -> dict[str, str]:
    """
    Generate LookML files from semantic models and metrics.

    Args:
        models: List of semantic models to generate from.
        metrics: Optional list of metrics to generate measures for.

    Returns:
        Dictionary mapping filename to file content.
    """
    files = {}

    console.print(f"[bold blue]Processing {len(models)} semantic models...[/bold blue]")
    if metrics:
        console.print(f"[bold blue]Processing {len(metrics)} metrics...[/bold blue]")

    # Build metric ownership mapping: model_name → [metrics]
    metric_map: dict[str, list[Metric]] = {}
    if metrics:
        for metric in metrics:
            primary_entity = metric.primary_entity
            if not primary_entity:
                console.print(f"[yellow]Warning: Metric '{metric.name}' has no primary_entity, skipping[/yellow]")
                continue

            # Find model with this primary entity
            owner_model = self._find_model_by_primary_entity(primary_entity, models)
            if not owner_model:
                console.print(f"[yellow]Warning: No model found for primary_entity '{primary_entity}', skipping metric '{metric.name}'[/yellow]")
                continue

            if owner_model.name not in metric_map:
                metric_map[owner_model.name] = []
            metric_map[owner_model.name].append(metric)

    # Generate individual view files
    for i, model in enumerate(models, 1):
        console.print(f"  [{i}/{len(models)}] Processing [cyan]{model.name}[/cyan]...")

        # Generate base view content
        view_dict = self._generate_view_dict(model)

        # Add metrics owned by this model
        owned_metrics = metric_map.get(model.name, [])
        if owned_metrics:
            console.print(f"    Adding {len(owned_metrics)} metric(s) to {model.name}")
            metric_measures = []
            for metric in owned_metrics:
                try:
                    measure_dict = self._generate_metric_measure(metric, model, models)
                    metric_measures.append(measure_dict)
                except Exception as e:
                    console.print(f"[red]Error generating metric '{metric.name}': {e}[/red]")

            # Append to existing measures in view_dict
            if "measures" not in view_dict["views"][0]:
                view_dict["views"][0]["measures"] = []
            view_dict["views"][0]["measures"].extend(metric_measures)

        # Convert to LookML string
        view_content = lkml.dump(view_dict)
        if self.format_output:
            view_content = self._format_lookml_content(view_content)

        # Add to files dict
        view_name = f"{self.view_prefix}{model.name}"
        filename = f"{self._sanitize_filename(view_name)}.view.lkml"
        files[filename] = view_content
        console.print(f"    [green]✓[/green] Generated {filename}")

    # Generate explores and model files (unchanged)
    # ...

    return files
```

**Note**: Need to extract view dict generation into `_generate_view_dict()` helper to avoid duplication.

## Testing Strategy

### Unit Tests (src/tests/unit/test_lookml_generator.py)

#### Test Class: `TestMetricMeasureGeneration`

```python
class TestMetricMeasureGeneration:
    """Test metric-to-measure conversion."""

    def test_generate_simple_metric_same_view(self):
        """Test simple metric where measure is in same view."""
        # Setup: metric with primary_entity matching measure's model
        # Assert: SQL is "${measure}" (no view prefix)
        # Assert: required_fields is empty

    def test_generate_simple_metric_cross_view(self):
        """Test simple metric where measure is in different view."""
        # Setup: metric referencing measure from other model
        # Assert: SQL is "${other_view.measure}"
        # Assert: required_fields contains "other_view.measure"

    def test_generate_ratio_metric_both_cross_view(self):
        """Test ratio metric with num and denom from other views."""
        # Setup: ratio metric with both measures from different models
        # Assert: SQL is "1.0 * ${view1.num} / NULLIF(${view2.denom}, 0)"
        # Assert: required_fields contains both references

    def test_generate_ratio_metric_mixed(self):
        """Test ratio metric with num from same view, denom from other."""
        # Assert: Num uses "${measure}" syntax
        # Assert: Denom uses "${view.measure}" syntax
        # Assert: required_fields only contains cross-view reference

    def test_generate_derived_metric_simple(self):
        """Test derived metric with simple expression."""
        # Setup: expr = "metric_a + metric_b"
        # Assert: Expression correctly substitutes metric refs

    def test_metric_value_format_inference(self):
        """Test value_format_name inference."""
        # Test ratio → "percent_2"
        # Test revenue → "usd"
        # Test count → "decimal_0"
        # Test other → None

    def test_metric_group_label_inference(self):
        """Test group_label inference."""
        # Test with meta.category → uses meta value
        # Test without meta → uses "{Model} Performance"

    def test_view_prefix_in_cross_references(self):
        """Test view prefix applied to cross-view references."""
        # Setup: generator with view_prefix="v_"
        # Assert: SQL contains "${v_other_view.measure}"
        # Assert: required_fields contains "v_other_view.measure"
```

#### Test Class: `TestMetricIntegration`

```python
class TestMetricIntegration:
    """Test integration of metrics with view generation."""

    def test_generate_with_metrics(self):
        """Test generate() method with metrics parameter."""
        # Setup: models + metrics
        # Call: generate(models, metrics)
        # Assert: Metric measures appear in correct view file

    def test_metric_ownership_filtering(self):
        """Test metrics only appear in primary entity's view."""
        # Setup: 2 models, 2 metrics (one for each)
        # Assert: Each view only contains its owned metric

    def test_metrics_appended_to_measures(self):
        """Test metrics appended to existing measures."""
        # Assert: Model's original measures present
        # Assert: Metric measures added at end

    def test_missing_primary_entity_warning(self):
        """Test warning when metric has no primary_entity."""
        # Setup: metric with primary_entity = None
        # Assert: Warning logged, metric skipped

    def test_unknown_primary_entity_warning(self):
        """Test warning when primary_entity doesn't match any model."""
        # Assert: Warning logged, metric skipped
```

### Coverage Target

- **New methods**: 95%+ branch coverage
- **Modified methods**: Maintain existing coverage
- **Overall generator module**: 95%+

## Error Handling

### Validation Errors

1. **Measure not found**: "Measure '{name}' not found in any semantic model"
   - Raised in: `_find_model_with_measure()`
   - Impact: Metric generation fails, error logged, continues to next metric

2. **Primary entity not found**: "No model found for primary_entity '{entity}'"
   - Raised in: `generate()` during metric ownership mapping
   - Impact: Metric skipped with warning

3. **Unsupported metric type**: "Unsupported metric type: {type}"
   - Raised in: `_generate_metric_measure()`
   - Impact: Metric generation fails, error logged

### Warning Scenarios

1. **Missing primary_entity**: Log warning, skip metric
2. **Circular metric dependencies** (derived metrics): Not handled in MVP, document limitation

## Backward Compatibility

### API Changes

- `generate()` method signature: **BACKWARD COMPATIBLE**
  - Old: `generate(models: list[SemanticModel])`
  - New: `generate(models: list[SemanticModel], metrics: list[Metric] | None = None)`
  - Default `metrics=None` maintains existing behavior

### File Output Changes

- **Without metrics**: Output identical to current
- **With metrics**: Additional measures in view files

## Dependencies

### DTL-023: Metric Schema Models

**Required classes/types**:
- `Metric` - Base metric model
- `SimpleMetricParams`, `RatioMetricParams`, `DerivedMetricParams` - Type params
- `MetricReference` - For derived metrics
- `metric.primary_entity` property

**Usage in DTL-025**:
```python
from dbt_to_lookml.schemas import (
    Metric,
    SimpleMetricParams,
    RatioMetricParams,
    DerivedMetricParams
)

# Type checking
if isinstance(metric.type_params, SimpleMetricParams):
    measure_name = metric.type_params.measure

# Primary entity access
primary_entity = metric.primary_entity
```

### DTL-024: Metric Parser

**Required output**:
- `list[Metric]` - Parsed metrics from YAML files

**Integration point**:
```python
# In CLI (__main__.py)
from dbt_to_lookml.parsers.dbt_metrics import DbtMetricParser

metric_parser = DbtMetricParser()
metrics = metric_parser.parse_directory(metrics_dir)

generator = LookMLGenerator(...)
files = generator.generate(models, metrics)
```

## Implementation Order

### Phase 1: Core Infrastructure (Week 1)

1. **Add method signatures** (TDD approach)
   - `_generate_metric_measure()`
   - `_generate_simple_sql()`
   - `_generate_ratio_sql()`
   - `_extract_required_fields()`
   - Helper methods

2. **Implement simple metrics**
   - `_generate_simple_sql()` - same view case
   - `_generate_simple_sql()` - cross view case
   - Tests for simple metrics

3. **Implement ratio metrics**
   - `_generate_ratio_sql()` - all cases
   - Tests for ratio metrics

4. **Implement required_fields extraction**
   - `_extract_required_fields()`
   - Tests for dependency detection

### Phase 2: Integration (Week 2)

5. **Update generate() method**
   - Add `metrics` parameter
   - Implement ownership mapping
   - Integrate metric measure generation
   - Tests for integration

6. **Implement derived metrics** (if time permits)
   - `_generate_derived_sql()` - simple cases
   - Tests for derived metrics
   - Document limitations

7. **Add helper methods**
   - `_infer_value_format()`
   - `_infer_group_label()`
   - Tests for helpers

### Phase 3: Polish (Week 2-3)

8. **Error handling**
   - Validation errors
   - Warning messages
   - Tests for error cases

9. **Documentation**
   - Update CLAUDE.md
   - Add docstrings
   - Update examples

10. **Code review and refinement**
    - Address feedback
    - Refactor for clarity
    - Ensure 95%+ coverage

## Risk Mitigation

### Risk 1: Complex Derived Metric Expressions

**Mitigation**: Start with simple string replacement, document limitations, plan future enhancement.

### Risk 2: Circular Dependencies

**Mitigation**: Not handling in MVP. Document as limitation. Add validation in DTL-027.

### Risk 3: Type Checking Complexity

**Mitigation**: Use `isinstance()` checks with type narrowing. Mypy should handle correctly with proper Union types.

### Risk 4: Test Coverage

**Mitigation**: Write tests first (TDD). Target 95%+ branch coverage. Use parameterized tests for multiple scenarios.

## Success Criteria

- [ ] All methods implemented with full type hints
- [ ] mypy --strict passes
- [ ] 95%+ branch coverage on new code
- [ ] All acceptance criteria from DTL-025 met
- [ ] Integration tests pass
- [ ] Backward compatibility maintained
- [ ] Documentation complete

## Open Questions

### Q1: Should we validate measure existence during generation?

**Answer**: Yes, raise clear error if measure not found. This prevents generating invalid LookML.

### Q2: How to handle metrics with same name as existing measures?

**Answer**: Allow it. Metrics generate as separate measures. Up to user to avoid name conflicts.

### Q3: Should we sort measures (original vs. metric-generated)?

**Answer**: Keep original measures first, then append metric measures. Maintain stable order.

### Q4: How to handle metric metadata (description, label)?

**Answer**: Use metric.label and metric.description directly. If label missing, use titlecase(metric.name).

## Conclusion

This strategy provides a comprehensive roadmap for implementing cross-entity measure generation in `LookMLGenerator`. The approach is:

- **Incremental**: Build in phases (simple → ratio → derived)
- **Testable**: TDD approach with high coverage target
- **Backward Compatible**: Optional metrics parameter
- **Type-Safe**: Full mypy compliance
- **Maintainable**: Clear separation of concerns, helper methods

The implementation should take 2-3 weeks with thorough testing and documentation.
