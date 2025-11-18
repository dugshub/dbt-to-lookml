---
id: DTL-023
title: "Implementation Strategy: Add Metric Schema Models to schemas.py"
issue: DTL-023
created: 2025-11-18
status: approved
---

# Implementation Strategy: Add Metric Schema Models to schemas.py

## Overview

This strategy outlines the implementation approach for adding Pydantic schema models to support dbt metrics in `src/dbt_to_lookml/schemas.py`. This is the foundation layer for the cross-entity metrics epic (DTL-022), enabling the codebase to represent and validate dbt metric definitions.

## Goals

1. **Extend schema models** to support all dbt metric types (simple, ratio, derived, conversion)
2. **Maintain strict typing** with full mypy --strict compliance
3. **Follow existing patterns** established by SemanticModel, Measure, Dimension
4. **Enable validation** of metric structure and metadata
5. **Support primary entity extraction** from meta blocks
6. **Achieve 100% test coverage** for new models

## Context Analysis

### Existing Schema Patterns

The codebase follows consistent Pydantic patterns in `schemas.py`:

**Key Patterns Identified**:
1. **BaseModel inheritance**: All schema classes extend `pydantic.BaseModel`
2. **Optional fields**: Use `| None = None` for optional fields (PEP 604 union syntax)
3. **Type safety**: Full type hints on all fields and methods
4. **Helper methods**: Properties and methods for label extraction, conversion logic
5. **Field defaults**: Use `Field(default_factory=list)` for mutable defaults
6. **Nested models**: ConfigMeta, Config, Hierarchy for structured metadata
7. **No validators**: Codebase does not currently use `@model_validator` or `@field_validator`

**Relevant Examples**:
```python
class Measure(BaseModel):
    name: str
    agg: AggregationType
    expr: str | None = None
    description: str | None = None
    label: str | None = None
    create_metric: bool | None = None
    config: Config | None = None

    def get_measure_labels(self, model_name: str | None = None) -> tuple[str, str | None]:
        """Extract labels with business logic."""
```

### Type System

The codebase uses `types.py` for enums and type mappings:
- `AggregationType(str, Enum)`: Measure aggregation types
- `DimensionType(str, Enum)`: Dimension types (categorical, time)
- `TimeGranularity(str, Enum)`: Time granularities
- `LOOKML_TYPE_MAP`: Dict mapping types to LookML equivalents

**Decision**: Create new `MetricType(str, Enum)` for metric type validation.

### Testing Patterns

From `test_schemas.py`:
- **Class-based organization**: `class TestEntity`, `class TestDimension`, etc.
- **Comprehensive validation**: Test required fields, optional fields, edge cases
- **Method testing**: Test helper methods and properties
- **Pydantic validation**: Use `pytest.raises(ValidationError)` for invalid cases
- **Parametrization**: Use `@pytest.mark.parametrize` for multiple scenarios
- **Clear naming**: `test_<feature>_<scenario>` pattern

## Architecture Decisions

### 1. Discriminated Union for Type-Specific Parameters

**Decision**: Use Pydantic discriminated union with a single `Metric` class and a `type_params` field that varies by metric type.

**Rationale**:
- Matches dbt metric structure (single `type` field with type-specific `type_params`)
- Enables Pydantic automatic validation of params based on `type` discriminator
- Simplifies parsing (one model vs. multiple subclasses)
- Aligns with existing pattern (Dimension has type_params dict)

**Implementation**:
```python
from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field, Discriminator

class SimpleMetricParams(BaseModel):
    """Type params for simple metrics (reference single measure)."""
    measure: str

class RatioMetricParams(BaseModel):
    """Type params for ratio metrics (numerator / denominator)."""
    numerator: str
    denominator: str

class DerivedMetricParams(BaseModel):
    """Type params for derived metrics (expression with metric refs)."""
    expr: str
    metrics: list["MetricReference"]

class ConversionMetricParams(BaseModel):
    """Type params for conversion metrics (funnel analysis)."""
    conversion_type_params: dict[str, Any]

# Discriminated union based on parent's 'type' field
MetricTypeParams = Annotated[
    SimpleMetricParams | RatioMetricParams | DerivedMetricParams | ConversionMetricParams,
    Field(discriminator="type")
]

class Metric(BaseModel):
    """Represents a dbt metric definition."""
    name: str
    type: Literal["simple", "ratio", "derived", "conversion"]
    type_params: MetricTypeParams
    label: str | None = None
    description: str | None = None
    meta: dict[str, Any] | None = None

    @property
    def primary_entity(self) -> str | None:
        """Extract primary_entity from meta block."""
        if self.meta:
            return self.meta.get("primary_entity")
        return None
```

**Alternative Considered**: Subclass-based approach with `SimpleMetric(Metric)`, `RatioMetric(Metric)`, etc.
- **Rejected**: More complex parsing logic, harder to serialize/deserialize, doesn't match dbt structure

### 2. Helper Models for Nested Structures

**Decision**: Create `MetricReference` model for referencing other metrics in derived metrics.

**Rationale**:
- Derived metrics can reference other metrics with optional aliases and offset windows
- Structured model enables validation of references
- Provides clear API for extracting dependencies

**Implementation**:
```python
class MetricReference(BaseModel):
    """Reference to another metric in derived metric expressions."""
    name: str
    alias: str | None = None
    offset_window: str | None = None
```

### 3. Validation Strategy

**Decision**: Use Pydantic's built-in validation without custom validators for initial implementation.

**Rationale**:
- Codebase does not currently use `@model_validator` or `@field_validator`
- Required field validation is automatic with Pydantic
- Type validation (Literal for metric type) is automatic
- Cross-model validation (measure references, entity existence) should be handled by parser, not schema layer

**Deferred to DTL-024 (Parser)**:
- Validating that referenced measures exist in semantic models
- Validating that primary_entity references a valid entity
- Validating that metric names are globally unique

**Rationale for deferral**:
- Schema models are data structures, not business logic validators
- Parser has access to full context (all semantic models, all metrics)
- Separation of concerns: schemas validate structure, parser validates semantics

### 4. Meta Block Structure

**Decision**: Use `dict[str, Any]` for meta block, matching existing ConfigMeta pattern.

**Rationale**:
- Flexible structure for custom metadata
- Matches existing pattern in Measure, Dimension (config.meta)
- Allows future extension without schema changes
- Primary entity extraction via property method

**Alternative Considered**: Structured `MetricMeta(BaseModel)` with typed fields
- **Rejected**: Over-engineering for single field (primary_entity), reduces flexibility

### 5. Placement in schemas.py

**Decision**: Add metric models in a new section between SemanticModel and LookML schemas.

**Structure**:
```python
# ============================================================================
# Semantic Model Schemas (Input)
# ============================================================================
# ... existing Entity, Dimension, Measure, SemanticModel ...

# ============================================================================
# Metric Schemas (Input)
# ============================================================================
class MetricReference(BaseModel):
    """..."""

class SimpleMetricParams(BaseModel):
    """..."""

class RatioMetricParams(BaseModel):
    """..."""

class DerivedMetricParams(BaseModel):
    """..."""

class ConversionMetricParams(BaseModel):
    """..."""

MetricTypeParams = Annotated[...]

class Metric(BaseModel):
    """..."""

# ============================================================================
# LookML Schemas (Output)
# ============================================================================
# ... existing LookML* classes ...
```

**Rationale**:
- Clear separation of input schemas (semantic models, metrics) from output schemas (LookML)
- Logical ordering: metrics reference measures from semantic models
- Follows existing comment-based section organization

## Implementation Plan

### Phase 1: Add Type Enum and Helper Models (15 min)

**File**: `src/dbt_to_lookml/types.py`

Add `MetricType` enum:
```python
class MetricType(str, Enum):
    """Supported metric types."""

    SIMPLE = "simple"
    RATIO = "ratio"
    DERIVED = "derived"
    CONVERSION = "conversion"
```

**File**: `src/dbt_to_lookml/schemas.py`

Add imports:
```python
from typing import Annotated, Any, Literal
from pydantic import Field
```

Add `MetricReference` model:
```python
class MetricReference(BaseModel):
    """Reference to another metric in derived metric expressions.

    Used in derived metrics to reference other metrics with optional
    aliases and offset windows for time-based calculations.

    Attributes:
        name: Name of the referenced metric.
        alias: Optional alias for the metric in the expression.
        offset_window: Optional time window offset (e.g., "1 month", "7 days").

    Example:
        ```yaml
        metrics:
          - name: revenue_growth
            type: derived
            type_params:
              expr: "revenue - revenue_last_month"
              metrics:
                - name: revenue
                - name: revenue
                  alias: revenue_last_month
                  offset_window: "1 month"
        ```
    """

    name: str
    alias: str | None = None
    offset_window: str | None = None
```

### Phase 2: Add Type-Specific Params Models (20 min)

Add param models with comprehensive docstrings:

```python
class SimpleMetricParams(BaseModel):
    """Type parameters for simple metrics.

    Simple metrics reference a single measure from a semantic model.

    Attributes:
        measure: Name of the measure to use (e.g., "revenue", "order_count").

    Example:
        ```yaml
        metrics:
          - name: total_revenue
            type: simple
            type_params:
              measure: revenue
        ```
    """

    measure: str


class RatioMetricParams(BaseModel):
    """Type parameters for ratio metrics.

    Ratio metrics calculate numerator / denominator, typically for rates,
    percentages, or per-unit calculations.

    Attributes:
        numerator: Name of the measure to use as numerator.
        denominator: Name of the measure to use as denominator.

    Example:
        ```yaml
        metrics:
          - name: conversion_rate
            type: ratio
            type_params:
              numerator: completed_orders
              denominator: total_searches
        ```
    """

    numerator: str
    denominator: str


class DerivedMetricParams(BaseModel):
    """Type parameters for derived metrics.

    Derived metrics combine other metrics using a SQL expression.

    Attributes:
        expr: SQL expression combining referenced metrics.
        metrics: List of metric references used in the expression.

    Example:
        ```yaml
        metrics:
          - name: revenue_growth
            type: derived
            type_params:
              expr: "(current_revenue - prior_revenue) / prior_revenue"
              metrics:
                - name: monthly_revenue
                  alias: current_revenue
                - name: monthly_revenue
                  alias: prior_revenue
                  offset_window: "1 month"
        ```
    """

    expr: str
    metrics: list[MetricReference]


class ConversionMetricParams(BaseModel):
    """Type parameters for conversion metrics.

    Conversion metrics track funnel conversions between entity states.
    The structure is flexible to support various conversion patterns.

    Attributes:
        conversion_type_params: Dictionary containing conversion-specific
            configuration. Structure depends on conversion type.

    Example:
        ```yaml
        metrics:
          - name: checkout_conversion
            type: conversion
            type_params:
              conversion_type_params:
                entity: order
                calculation: conversion_rate
                base_event: page_view
                conversion_event: purchase
        ```
    """

    conversion_type_params: dict[str, Any]
```

### Phase 3: Add Discriminated Union Type (10 min)

Add type alias with discriminator:

```python
# Discriminated union for metric type params
# Pydantic will automatically validate params based on parent Metric.type field
MetricTypeParams = Annotated[
    SimpleMetricParams | RatioMetricParams | DerivedMetricParams | ConversionMetricParams,
    Field(discriminator="type")
]
```

**Note**: This requires the parent `Metric` class to have a `type` field that Pydantic uses as the discriminator.

### Phase 4: Add Main Metric Model (25 min)

Add comprehensive `Metric` model:

```python
class Metric(BaseModel):
    """Represents a dbt metric definition.

    Metrics define calculations that can be simple aggregations, ratios,
    derived calculations, or conversion funnels. They can reference measures
    from one or more semantic models and are owned by a primary entity.

    Attributes:
        name: Unique metric identifier (snake_case).
        type: Type of metric calculation.
        type_params: Type-specific parameters (validated based on type).
        label: Optional human-readable label for the metric.
        description: Optional detailed description of what the metric represents.
        meta: Optional metadata dictionary for custom configuration.
            Common fields:
            - primary_entity: Entity that owns this metric (determines which
              view file contains the generated measure).
            - category: Category for grouping related metrics.

    Examples:
        Simple metric:
        ```yaml
        metrics:
          - name: total_revenue
            type: simple
            type_params:
              measure: revenue
            label: Total Revenue
            description: Sum of all revenue
            meta:
              primary_entity: order
              category: financial_performance
        ```

        Ratio metric (cross-entity):
        ```yaml
        metrics:
          - name: search_conversion_rate
            type: ratio
            type_params:
              numerator: rental_count    # From rental_orders
              denominator: search_count  # From searches
            label: Search Conversion Rate
            description: Percentage of searches that result in rentals
            meta:
              primary_entity: search  # Searches is the spine/denominator
              category: conversion_metrics
        ```

        Derived metric:
        ```yaml
        metrics:
          - name: revenue_growth
            type: derived
            type_params:
              expr: "(current - prior) / prior"
              metrics:
                - name: monthly_revenue
                  alias: current
                - name: monthly_revenue
                  alias: prior
                  offset_window: "1 month"
            meta:
              primary_entity: order
        ```

    See Also:
        - Epic DTL-022 for primary entity ownership pattern
        - MetricReference for derived metric dependencies
    """

    name: str
    type: Literal["simple", "ratio", "derived", "conversion"]
    type_params: MetricTypeParams
    label: str | None = None
    description: str | None = None
    meta: dict[str, Any] | None = None

    @property
    def primary_entity(self) -> str | None:
        """Extract primary_entity from meta block.

        The primary entity determines which semantic model/view owns this
        metric and serves as the base for the calculation.

        Returns:
            Primary entity name if specified in meta, None otherwise.

        Example:
            ```python
            metric = Metric(
                name="conversion_rate",
                type="ratio",
                type_params=RatioMetricParams(
                    numerator="orders",
                    denominator="searches"
                ),
                meta={"primary_entity": "search"}
            )
            assert metric.primary_entity == "search"
            ```
        """
        if self.meta:
            return self.meta.get("primary_entity")
        return None
```

### Phase 5: Update Type Imports (5 min)

**File**: `src/dbt_to_lookml/schemas.py`

Update imports to include MetricType if needed:
```python
from dbt_to_lookml.types import (
    LOOKML_TYPE_MAP,
    AggregationType,
    DimensionType,
    MetricType,  # Add this
)
```

**Note**: MetricType may not be needed if we use Literal directly in the Metric class.

### Phase 6: Update __all__ Export (5 min)

If `schemas.py` has an `__all__` list, add new classes:
```python
__all__ = [
    # ... existing exports ...
    "Metric",
    "MetricReference",
    "SimpleMetricParams",
    "RatioMetricParams",
    "DerivedMetricParams",
    "ConversionMetricParams",
]
```

**Check**: Verify if `schemas.py` uses `__all__` for explicit exports.

## Testing Strategy

### Test File: `src/tests/unit/test_schemas.py`

Add new test class at the end of the file (before LookML model tests).

### Test Class Structure

```python
class TestMetricReference:
    """Test cases for MetricReference model."""

    def test_metric_reference_creation(self) -> None:
        """Test basic metric reference creation."""

    def test_metric_reference_with_alias(self) -> None:
        """Test metric reference with alias."""

    def test_metric_reference_with_offset_window(self) -> None:
        """Test metric reference with offset window."""

    def test_metric_reference_with_all_fields(self) -> None:
        """Test metric reference with all optional fields."""

    def test_metric_reference_validation(self) -> None:
        """Test metric reference field validation."""


class TestSimpleMetricParams:
    """Test cases for SimpleMetricParams model."""

    def test_simple_metric_params_creation(self) -> None:
        """Test basic simple metric params creation."""

    def test_simple_metric_params_validation(self) -> None:
        """Test that measure is required."""


class TestRatioMetricParams:
    """Test cases for RatioMetricParams model."""

    def test_ratio_metric_params_creation(self) -> None:
        """Test basic ratio metric params creation."""

    def test_ratio_metric_params_validation(self) -> None:
        """Test that numerator and denominator are required."""


class TestDerivedMetricParams:
    """Test cases for DerivedMetricParams model."""

    def test_derived_metric_params_creation(self) -> None:
        """Test basic derived metric params creation."""

    def test_derived_metric_params_with_multiple_metrics(self) -> None:
        """Test derived params with multiple metric references."""

    def test_derived_metric_params_validation(self) -> None:
        """Test that expr and metrics are required."""


class TestConversionMetricParams:
    """Test cases for ConversionMetricParams model."""

    def test_conversion_metric_params_creation(self) -> None:
        """Test basic conversion metric params creation."""

    def test_conversion_metric_params_flexible_structure(self) -> None:
        """Test that conversion_type_params accepts various structures."""


class TestMetric:
    """Test cases for Metric model."""

    def test_metric_simple_creation(self) -> None:
        """Test simple metric creation."""

    def test_metric_ratio_creation(self) -> None:
        """Test ratio metric creation."""

    def test_metric_derived_creation(self) -> None:
        """Test derived metric creation."""

    def test_metric_conversion_creation(self) -> None:
        """Test conversion metric creation."""

    def test_metric_with_all_optional_fields(self) -> None:
        """Test metric with label, description, meta."""

    def test_metric_validation_missing_name(self) -> None:
        """Test that name is required."""

    def test_metric_validation_missing_type(self) -> None:
        """Test that type is required."""

    def test_metric_validation_missing_type_params(self) -> None:
        """Test that type_params is required."""

    def test_metric_validation_invalid_type(self) -> None:
        """Test that type must be one of the allowed values."""

    def test_metric_type_params_mismatch(self) -> None:
        """Test that type_params must match metric type."""
        # This tests the discriminated union validation

    def test_metric_primary_entity_present(self) -> None:
        """Test primary_entity property when meta.primary_entity exists."""

    def test_metric_primary_entity_missing(self) -> None:
        """Test primary_entity property when meta is None."""

    def test_metric_primary_entity_meta_without_field(self) -> None:
        """Test primary_entity property when meta exists but no primary_entity."""

    def test_metric_primary_entity_nested_meta(self) -> None:
        """Test primary_entity extraction from complex meta block."""

    @pytest.mark.parametrize(
        "metric_type,params_class,params_dict",
        [
            ("simple", SimpleMetricParams, {"measure": "revenue"}),
            ("ratio", RatioMetricParams, {"numerator": "orders", "denominator": "searches"}),
            ("derived", DerivedMetricParams, {"expr": "a + b", "metrics": []}),
            ("conversion", ConversionMetricParams, {"conversion_type_params": {}}),
        ],
    )
    def test_metric_all_types_valid(
        self, metric_type: str, params_class: type, params_dict: dict
    ) -> None:
        """Test that all metric types can be created with valid params."""
```

### Test Coverage Targets

- **MetricReference**: 100% (simple model, 4-5 tests)
- **SimpleMetricParams**: 100% (simple model, 2-3 tests)
- **RatioMetricParams**: 100% (simple model, 2-3 tests)
- **DerivedMetricParams**: 100% (simple model, 3-4 tests)
- **ConversionMetricParams**: 100% (simple model, 2-3 tests)
- **Metric**: 100% (main model, 15-20 tests)

**Total new tests**: ~30-35 test methods

### Test Execution

```bash
# Run new metric tests only
pytest src/tests/unit/test_schemas.py::TestMetric -xvs
pytest src/tests/unit/test_schemas.py::TestMetricReference -xvs
pytest src/tests/unit/test_schemas.py::TestSimpleMetricParams -xvs
pytest src/tests/unit/test_schemas.py::TestRatioMetricParams -xvs
pytest src/tests/unit/test_schemas.py::TestDerivedMetricParams -xvs
pytest src/tests/unit/test_schemas.py::TestConversionMetricParams -xvs

# Run all schema tests
pytest src/tests/unit/test_schemas.py -v

# Check coverage for schemas.py
pytest src/tests/unit/test_schemas.py --cov=src/dbt_to_lookml/schemas --cov-report=term-missing
```

## Acceptance Criteria Validation

| Criterion | Validation Method |
|-----------|-------------------|
| Metric base model with all required fields | Unit tests + mypy type checking |
| Type-specific params for simple, ratio, derived, conversion | Unit tests for each params class |
| primary_entity property extracts from meta block | Property tests with various meta structures |
| Validation ensures type_params match metric type | Pydantic discriminated union validation tests |
| All models pass mypy --strict type checking | `make type-check` passes |
| Unit tests for model validation (each metric type) | TestMetric class with parametrized tests |
| Unit tests for primary_entity extraction | TestMetric property tests |
| Unit tests for validation edge cases | TestMetric validation tests |

## Risk Assessment

### Low Risks
- **Pydantic API changes**: Using stable Pydantic v2 features (BaseModel, Field, Literal)
- **Type checking**: Following existing patterns that already pass mypy --strict
- **Test coverage**: Simple models, straightforward to test

### Medium Risks
- **Discriminated union complexity**: First use of discriminated unions in codebase
  - **Mitigation**: Add comprehensive validation tests, clear docstrings
  - **Fallback**: Use Union without discriminator if issues arise
- **Forward compatibility**: Meta block structure may evolve
  - **Mitigation**: Use flexible dict[str, Any], property method for extraction

### High Risks
- **None identified**: This is a foundational layer with no external dependencies

## Rollback Plan

If issues arise during implementation:

1. **Phase 1-2 issues**: Revert type enum and helper models, minimal impact
2. **Phase 3-4 issues (discriminated union)**: Fall back to simple Union without discriminator
3. **Phase 5-6 issues**: Remove from exports, fix imports

**Recovery**: All changes are in a single file (schemas.py) with isolated test suite. Easy to revert via git.

## Dependencies

### Blocked By
- None (foundation layer)

### Blocks
- DTL-024: Metric parser needs these models to parse YAML
- DTL-025: Generator needs these models to create LookML measures
- DTL-026: Explore generation needs Metric model for dependency analysis
- DTL-027: Validation needs Metric model for connectivity checks

## Success Metrics

- ✅ All unit tests pass (30-35 new tests)
- ✅ 100% coverage on new Metric models
- ✅ `make type-check` passes (mypy --strict)
- ✅ `make lint` passes (ruff)
- ✅ No regression in existing tests
- ✅ Documentation clear and comprehensive

## Timeline Estimate

- **Implementation**: 1.5 hours
  - Phase 1: 15 min
  - Phase 2: 20 min
  - Phase 3: 10 min
  - Phase 4: 25 min
  - Phase 5: 5 min
  - Phase 6: 5 min
  - Buffer: 10 min

- **Testing**: 2 hours
  - Write test cases: 1 hour
  - Debug and fix: 30 min
  - Coverage verification: 30 min

- **Total**: 3.5 hours

## References

- **Issue**: `.tasks/issues/DTL-023.md`
- **Epic**: `.tasks/epics/DTL-022.md`
- **Plan**: `.tasks/plans/cross-entity-metrics-plan.yaml`
- **Existing schemas**: `src/dbt_to_lookml/schemas.py` (lines 1-705)
- **Existing types**: `src/dbt_to_lookml/types.py` (lines 1-51)
- **Test patterns**: `src/tests/unit/test_schemas.py` (lines 1-1466)

## Architectural Principles

This implementation follows these key principles from CLAUDE.md:

1. **Strict typing**: All functions have type hints (mypy --strict)
2. **Pydantic validation**: Use BaseModel for automatic validation
3. **Separation of concerns**: Schema models validate structure, parser validates semantics
4. **Test-driven**: 95%+ coverage target, comprehensive unit tests
5. **Documentation**: Google-style docstrings for all public classes
6. **Consistency**: Follow existing patterns (BaseModel, Optional fields, helper methods)

## Approval

This strategy is ready for implementation once approved by the project maintainer.

**Estimated effort**: 3.5 hours
**Risk level**: Low
**Test coverage**: 100% (new code)
**Breaking changes**: None
