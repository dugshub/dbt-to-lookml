# Implementation Spec: Add Metric Schema Models to schemas.py

## Metadata
- **Issue**: `DTL-023`
- **Stack**: `backend`
- **Generated**: 2025-11-18
- **Strategy**: Approved 2025-11-18

## Issue Context

### Problem Statement

The dbt-to-lookml codebase currently supports parsing and generating LookML from semantic models (entities, dimensions, measures). To enable the cross-entity metrics epic (DTL-022), we need foundation schema models that can represent dbt metric definitions with all their type variants.

Without these schema models:
- We cannot parse dbt metric YAML files
- We cannot represent cross-entity relationships in metrics
- We cannot generate LookML measures from metric definitions
- We cannot validate metric structure and dependencies

### Solution Approach

Add comprehensive Pydantic schema models to `src/dbt_to_lookml/schemas.py` that:
1. Support all four dbt metric types (simple, ratio, derived, conversion)
2. Use discriminated union pattern for type-specific parameters
3. Extract primary entity from meta block (determines ownership)
4. Follow existing codebase patterns (BaseModel, Optional fields, helper methods)
5. Achieve 100% test coverage with strict type checking

### Success Criteria

- All metric types can be represented and validated via Pydantic models
- Type-specific parameters are validated based on metric type
- Primary entity extraction works correctly from meta blocks
- All models pass mypy --strict type checking
- 100% test coverage for new models (30-35 unit tests)
- No regression in existing schema tests

## Approved Strategy Summary

The approved strategy uses a **discriminated union architecture** for metric type parameters:

**Key Decisions**:
1. **Single Metric class** with `type_params` field that varies by metric type (matches dbt structure)
2. **Four parameter models**: `SimpleMetricParams`, `RatioMetricParams`, `DerivedMetricParams`, `ConversionMetricParams`
3. **MetricReference helper model** for derived metric dependencies
4. **Meta block flexibility** using `dict[str, Any]` with property method for primary_entity extraction
5. **No custom validators** - rely on Pydantic's built-in validation (matches codebase patterns)
6. **Parser-level semantic validation** deferred to DTL-024 (measure existence, entity references)

**Implementation Timeline**: 1.5 hours implementation + 2 hours testing = 3.5 hours total

## Implementation Plan

### Phase 1: Add Type Enum and Helper Models (15 min)

**Objective**: Add MetricType enum to types.py and MetricReference model to schemas.py

**Tasks**:
1. Add MetricType enum to types.py
2. Add MetricReference model to schemas.py
3. Update imports in schemas.py

### Phase 2: Add Type-Specific Params Models (20 min)

**Objective**: Create four parameter models with comprehensive docstrings

**Tasks**:
1. Add SimpleMetricParams model
2. Add RatioMetricParams model
3. Add DerivedMetricParams model
4. Add ConversionMetricParams model

### Phase 3: Add Discriminated Union Type (10 min)

**Objective**: Create type alias with Pydantic discriminator

**Tasks**:
1. Add MetricTypeParams union type with Field discriminator
2. Verify discriminator syntax matches Pydantic v2 patterns

### Phase 4: Add Main Metric Model (25 min)

**Objective**: Create comprehensive Metric model with all fields and primary_entity property

**Tasks**:
1. Add Metric class with all required fields
2. Add primary_entity property method
3. Add comprehensive docstrings with YAML examples

### Phase 5: Update Type Imports (5 min)

**Objective**: Ensure all type imports are correct

**Tasks**:
1. Verify MetricType import in schemas.py (if needed)
2. Verify all necessary Pydantic imports (Annotated, Literal, Field)

### Phase 6: Update __all__ Export (5 min)

**Objective**: Export new models if __all__ exists

**Tasks**:
1. Check if schemas.py uses __all__
2. Add new classes to __all__ if present

### Phase 7: Testing (2 hours)

**Objective**: Achieve 100% coverage with comprehensive unit tests

**Tasks**:
1. Create TestMetricReference class (4-5 tests)
2. Create TestSimpleMetricParams class (2-3 tests)
3. Create TestRatioMetricParams class (2-3 tests)
4. Create TestDerivedMetricParams class (3-4 tests)
5. Create TestConversionMetricParams class (2-3 tests)
6. Create TestMetric class (15-20 tests including parametrized tests)
7. Run coverage report and verify 100% for new code

## Detailed Task Breakdown

### Task 1: Add MetricType Enum to types.py

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/types.py`

**Action**: Add new enum after TimeGranularity (around line 37)

**Implementation Guidance**:
```python
class MetricType(str, Enum):
    """Supported metric types."""

    SIMPLE = "simple"
    RATIO = "ratio"
    DERIVED = "derived"
    CONVERSION = "conversion"
```

**Reference**: Follow pattern from `AggregationType` (lines 6-18) and `DimensionType` (lines 20-24)

**Tests**: Type enum will be tested indirectly through Metric model validation tests

**Estimated lines**: 8 lines

---

### Task 2: Add MetricReference Model to schemas.py

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Add new section "Metric Schemas (Input)" after SemanticModel class (after line 571)

**Implementation Guidance**:
```python
# ============================================================================
# Metric Schemas (Input)
# ============================================================================


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

**Reference**: Follow pattern from `Entity` (lines 94-101) for simple model with optional fields

**Tests**: TestMetricReference class with 4-5 test methods

**Estimated lines**: 35 lines

---

### Task 3: Add SimpleMetricParams Model

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Add after MetricReference model

**Implementation Guidance**:
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
```

**Reference**: Follow pattern from `Hierarchy` (lines 17-22) for simple model

**Tests**: TestSimpleMetricParams class with 2-3 test methods

**Estimated lines**: 20 lines

---

### Task 4: Add RatioMetricParams Model

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Add after SimpleMetricParams model

**Implementation Guidance**:
```python
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
```

**Reference**: Same pattern as SimpleMetricParams

**Tests**: TestRatioMetricParams class with 2-3 test methods

**Estimated lines**: 24 lines

---

### Task 5: Add DerivedMetricParams Model

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Add after RatioMetricParams model

**Implementation Guidance**:
```python
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
```

**Reference**: Follow pattern from `SemanticModel` (lines 427-437) for list field with Field(default_factory=list)

**Note**: Use bare `list[MetricReference]` without default_factory since it's a required field

**Tests**: TestDerivedMetricParams class with 3-4 test methods

**Estimated lines**: 28 lines

---

### Task 6: Add ConversionMetricParams Model

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Add after DerivedMetricParams model

**Implementation Guidance**:
```python
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

**Reference**: Follow pattern from `ConfigMeta` (lines 25-86) for flexible dict field

**Tests**: TestConversionMetricParams class with 2-3 test methods

**Estimated lines**: 26 lines

---

### Task 7: Add MetricTypeParams Discriminated Union

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Add after ConversionMetricParams model

**Implementation Guidance**:
```python
# Discriminated union for metric type params
# Pydantic will automatically validate params based on parent Metric.type field
MetricTypeParams = Annotated[
    SimpleMetricParams | RatioMetricParams | DerivedMetricParams | ConversionMetricParams,
    Field(discriminator="type"),
]
```

**Reference**: New pattern for this codebase - using Pydantic v2 discriminated unions

**Important**: The discriminator will use the `type` field from the parent `Metric` class

**Tests**: Tested indirectly through Metric validation tests (type mismatch scenarios)

**Estimated lines**: 6 lines

---

### Task 8: Add Main Metric Model

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Add after MetricTypeParams union

**Implementation Guidance**:
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

**Reference**: Follow pattern from `Measure` (lines 357-424) for comprehensive model with property method

**Tests**: TestMetric class with 15-20 test methods including parametrized tests

**Estimated lines**: 105 lines

---

### Task 9: Update Imports in schemas.py

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Update imports at top of file (lines 3-10)

**Implementation Guidance**:

Add to typing imports (line 6):
```python
from typing import Any, Annotated, Literal
```

Pydantic Field is already imported (line 8)

**Reference**: Existing import structure (lines 1-10)

**Tests**: Import validation via mypy type checking

**Estimated lines**: Modify 1 line

---

### Task 10: Check and Update __all__ Export

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`

**Action**: Check if __all__ exists at end of file, add new classes if present

**Implementation Guidance**:

If __all__ exists:
```python
__all__ = [
    # ... existing exports ...
    "Metric",
    "MetricReference",
    "SimpleMetricParams",
    "RatioMetricParams",
    "DerivedMetricParams",
    "ConversionMetricParams",
    "MetricTypeParams",
]
```

**Note**: After reading the file, schemas.py does NOT have an __all__ export, so this task is **SKIP**

**Tests**: None needed (task skipped)

**Estimated lines**: 0 lines

## File Changes

### Files to Modify

#### `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/types.py`
**Why**: Add MetricType enum for type validation

**Changes**:
- Add MetricType enum after TimeGranularity (line 37)

**Estimated lines**: ~8 new lines

#### `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py`
**Why**: Add all metric schema models

**Changes**:
- Update typing imports to include Annotated, Literal (line 6)
- Add new "Metric Schemas (Input)" section after SemanticModel (line 572)
- Add MetricReference model (~35 lines)
- Add SimpleMetricParams model (~20 lines)
- Add RatioMetricParams model (~24 lines)
- Add DerivedMetricParams model (~28 lines)
- Add ConversionMetricParams model (~26 lines)
- Add MetricTypeParams union (~6 lines)
- Add Metric model (~105 lines)

**Estimated lines**: ~245 new lines total

### Files to Create

#### `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_metric_schemas.py`

**Alternative**: Add tests to existing `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`

**Decision**: Add to existing test_schemas.py (matches codebase pattern - all schema tests in one file)

**Structure**: Based on existing test classes in test_schemas.py (lines 25-550)

**Test Classes**:
```python
class TestMetricReference:
    """Test cases for MetricReference model."""
    # 4-5 test methods

class TestSimpleMetricParams:
    """Test cases for SimpleMetricParams model."""
    # 2-3 test methods

class TestRatioMetricParams:
    """Test cases for RatioMetricParams model."""
    # 2-3 test methods

class TestDerivedMetricParams:
    """Test cases for DerivedMetricParams model."""
    # 3-4 test methods

class TestConversionMetricParams:
    """Test cases for ConversionMetricParams model."""
    # 2-3 test methods

class TestMetric:
    """Test cases for Metric model."""
    # 15-20 test methods including parametrized tests
```

**Estimated lines**: ~400-500 new test lines

## Testing Strategy

### Unit Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`

**Location**: Add after TestSemanticModel class (around line 700), before LookML model tests

**Test Cases**:

#### TestMetricReference

1. **test_metric_reference_creation**
   - Setup: Create MetricReference with only name
   - Action: Instantiate model
   - Assert: name is set, alias and offset_window are None

2. **test_metric_reference_with_alias**
   - Setup: Create MetricReference with name and alias
   - Action: Instantiate model
   - Assert: Both fields set correctly

3. **test_metric_reference_with_offset_window**
   - Setup: Create MetricReference with name and offset_window
   - Action: Instantiate model
   - Assert: Both fields set correctly

4. **test_metric_reference_with_all_fields**
   - Setup: Create MetricReference with all fields
   - Action: Instantiate model
   - Assert: All fields set correctly

5. **test_metric_reference_validation**
   - Setup: Attempt to create without name
   - Action: Use pytest.raises(ValidationError)
   - Assert: Validation error raised

#### TestSimpleMetricParams

1. **test_simple_metric_params_creation**
   - Setup: Create with measure field
   - Action: Instantiate model
   - Assert: measure field set

2. **test_simple_metric_params_validation**
   - Setup: Attempt to create without measure
   - Action: Use pytest.raises(ValidationError)
   - Assert: Validation error raised for missing required field

#### TestRatioMetricParams

1. **test_ratio_metric_params_creation**
   - Setup: Create with numerator and denominator
   - Action: Instantiate model
   - Assert: Both fields set correctly

2. **test_ratio_metric_params_validation**
   - Setup: Attempt to create with only numerator (missing denominator)
   - Action: Use pytest.raises(ValidationError)
   - Assert: Validation error raised

#### TestDerivedMetricParams

1. **test_derived_metric_params_creation**
   - Setup: Create with expr and empty metrics list
   - Action: Instantiate model
   - Assert: expr set, metrics is empty list

2. **test_derived_metric_params_with_multiple_metrics**
   - Setup: Create with expr and list of MetricReference objects
   - Action: Instantiate model
   - Assert: All metric references present in list

3. **test_derived_metric_params_validation**
   - Setup: Attempt to create without expr
   - Action: Use pytest.raises(ValidationError)
   - Assert: Validation error raised

#### TestConversionMetricParams

1. **test_conversion_metric_params_creation**
   - Setup: Create with conversion_type_params dict
   - Action: Instantiate model
   - Assert: Dict field set

2. **test_conversion_metric_params_flexible_structure**
   - Setup: Create with various dict structures
   - Action: Instantiate multiple models with different structures
   - Assert: All structures accepted

#### TestMetric

1. **test_metric_simple_creation**
   - Setup: Create simple metric with SimpleMetricParams
   - Action: Instantiate Metric
   - Assert: All fields set correctly, type_params is SimpleMetricParams instance

2. **test_metric_ratio_creation**
   - Setup: Create ratio metric with RatioMetricParams
   - Action: Instantiate Metric
   - Assert: type is "ratio", type_params has numerator/denominator

3. **test_metric_derived_creation**
   - Setup: Create derived metric with DerivedMetricParams
   - Action: Instantiate Metric
   - Assert: type is "derived", type_params has expr/metrics

4. **test_metric_conversion_creation**
   - Setup: Create conversion metric with ConversionMetricParams
   - Action: Instantiate Metric
   - Assert: type is "conversion", type_params has conversion_type_params

5. **test_metric_with_all_optional_fields**
   - Setup: Create metric with label, description, meta
   - Action: Instantiate Metric
   - Assert: All optional fields set

6. **test_metric_validation_missing_name**
   - Setup: Attempt to create without name
   - Action: Use pytest.raises(ValidationError)
   - Assert: Validation error raised

7. **test_metric_validation_missing_type**
   - Setup: Attempt to create without type
   - Action: Use pytest.raises(ValidationError)
   - Assert: Validation error raised

8. **test_metric_validation_missing_type_params**
   - Setup: Attempt to create without type_params
   - Action: Use pytest.raises(ValidationError)
   - Assert: Validation error raised

9. **test_metric_validation_invalid_type**
   - Setup: Attempt to create with type="invalid"
   - Action: Use pytest.raises(ValidationError)
   - Assert: Validation error for Literal type constraint

10. **test_metric_type_params_mismatch**
    - Setup: Attempt to create simple metric with RatioMetricParams
    - Action: Use pytest.raises(ValidationError)
    - Assert: Discriminated union validation catches mismatch

11. **test_metric_primary_entity_present**
    - Setup: Create metric with meta={"primary_entity": "order"}
    - Action: Access primary_entity property
    - Assert: Returns "order"

12. **test_metric_primary_entity_missing**
    - Setup: Create metric with meta=None
    - Action: Access primary_entity property
    - Assert: Returns None

13. **test_metric_primary_entity_meta_without_field**
    - Setup: Create metric with meta={"category": "performance"}
    - Action: Access primary_entity property
    - Assert: Returns None (field not in meta dict)

14. **test_metric_primary_entity_nested_meta**
    - Setup: Create metric with complex meta block
    - Action: Access primary_entity property
    - Assert: Correctly extracts from complex structure

15. **test_metric_all_types_valid (parametrized)**
    - Setup: Use @pytest.mark.parametrize with all four metric types
    - Parameters: metric_type, params_class, params_dict
    - Action: Create Metric for each type
    - Assert: All types can be instantiated successfully

### Edge Cases

1. **Empty metrics list in DerivedMetricParams**: Should be valid (expr might reference external values)
2. **Special characters in metric names**: Validated by parser layer, not schema
3. **Very long expressions**: Pydantic will accept any string length
4. **Unicode in labels/descriptions**: Pydantic handles UTF-8 correctly
5. **Null vs missing fields**: Pydantic distinguishes None (explicit null) from unset

## Validation Commands

**Type checking**:
```bash
cd /Users/dug/Work/repos/dbt-to-lookml
make type-check
# Or: mypy src/dbt_to_lookml/schemas.py src/dbt_to_lookml/types.py --strict
```

**Linting**:
```bash
make lint
# Or: ruff check src/dbt_to_lookml/schemas.py src/dbt_to_lookml/types.py
```

**Format**:
```bash
make format
# Or: ruff format src/dbt_to_lookml/schemas.py src/dbt_to_lookml/types.py
```

**Run new tests only**:
```bash
pytest src/tests/unit/test_schemas.py::TestMetric -xvs
pytest src/tests/unit/test_schemas.py::TestMetricReference -xvs
pytest src/tests/unit/test_schemas.py::TestSimpleMetricParams -xvs
pytest src/tests/unit/test_schemas.py::TestRatioMetricParams -xvs
pytest src/tests/unit/test_schemas.py::TestDerivedMetricParams -xvs
pytest src/tests/unit/test_schemas.py::TestConversionMetricParams -xvs
```

**Run all schema tests**:
```bash
pytest src/tests/unit/test_schemas.py -v
```

**Coverage check**:
```bash
pytest src/tests/unit/test_schemas.py --cov=src/dbt_to_lookml/schemas --cov-report=term-missing --cov-report=html
# Open: htmlcov/index.html
```

**Full quality gate**:
```bash
make quality-gate
# Runs: lint + type-check + test
```

## Dependencies

### Existing Dependencies
- `pydantic`: Already in use for all schema models (BaseModel, Field, ValidationError)
- `pytest`: Already in use for testing framework
- Python 3.9+: Union syntax with `|` operator (PEP 604)

### New Dependencies
None - all required packages already in project

### Pydantic Features Used
- `BaseModel`: Base class for all models
- `Field`: For discriminator and default_factory
- `Annotated`: For discriminated union type
- `Literal`: For type field validation
- Property methods: For primary_entity extraction
- Automatic validation: For required fields and types

## Implementation Notes

### Important Considerations

1. **Discriminated Union Limitation**: The discriminator Field uses the parent's `type` field, but the union members (SimpleMetricParams, etc.) don't have a `type` field themselves. This is correct for Pydantic v2 - the discriminator applies at the parent level.

2. **Type Import**: The `MetricType` enum is added to types.py but may not be imported in schemas.py since we use `Literal` directly. Keep the enum for consistency and potential future use.

3. **Validation Scope**: Schema models validate structure only. Semantic validation (measure existence, entity references, metric name uniqueness) is deferred to the parser layer (DTL-024).

4. **Meta Block Flexibility**: Using `dict[str, Any]` for meta allows future extension without schema changes. The `primary_entity` property provides typed access to the most critical field.

5. **Test Organization**: All schema tests live in `test_schemas.py`. Add new test classes before the LookML model tests to maintain logical grouping (Input schemas → LookML schemas).

6. **Backward Compatibility**: These are new models with no impact on existing schemas (SemanticModel, Measure, etc.). No migration needed.

### Code Patterns to Follow

**Pattern 1: Simple Model with Optional Fields** (from Entity, Hierarchy):
```python
class ExampleModel(BaseModel):
    """Docstring with example."""
    required_field: str
    optional_field: str | None = None
```

**Pattern 2: Model with List Field** (from SemanticModel):
```python
class ExampleModel(BaseModel):
    """Docstring."""
    items: list[SomeType] = Field(default_factory=list)  # For optional list
    required_items: list[SomeType]  # For required list (no default)
```

**Pattern 3: Property Method** (from Dimension.get_dimension_labels):
```python
@property
def some_property(self) -> str | None:
    """Extract value with business logic.

    Returns:
        Extracted value or None.
    """
    if self.some_field:
        return self.some_field.get("key")
    return None
```

**Pattern 4: Test Structure** (from TestEntity):
```python
class TestModelName:
    """Test cases for ModelName model."""

    def test_model_creation(self) -> None:
        """Test basic model creation."""
        instance = ModelName(required_field="value")
        assert instance.required_field == "value"

    def test_model_validation(self) -> None:
        """Test model field validation."""
        with pytest.raises(ValidationError):
            ModelName()  # Missing required field
```

### References
- `Entity` model (lines 94-164): Simple model with optional fields, to_lookml_dict method
- `Dimension` model (lines 167-354): Model with type_params dict, property methods
- `Measure.get_measure_labels()` (lines 369-399): Property method extracting from meta
- `SemanticModel` (lines 427-571): Model with list fields using Field(default_factory)
- `TestEntity` class (lines 25-177): Test structure with validation tests
- `TestDimension` class (lines 179-435): Tests for models with type variants

## Ready for Implementation

This spec is complete and ready for implementation.

**Key files to modify**:
- `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/types.py` (~8 lines)
- `/Users/dug/Work/repos/dbt-to-lookml/src/dbt_to_lookml/schemas.py` (~245 lines)
- `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py` (~400-500 test lines)

**Validation checklist**:
- [ ] MetricType enum added to types.py
- [ ] MetricReference model added to schemas.py
- [ ] All four params models added (Simple, Ratio, Derived, Conversion)
- [ ] MetricTypeParams union created with discriminator
- [ ] Metric model added with primary_entity property
- [ ] All imports updated (Annotated, Literal)
- [ ] 30-35 unit tests added to test_schemas.py
- [ ] All tests pass: `pytest src/tests/unit/test_schemas.py -v`
- [ ] Type checking passes: `make type-check`
- [ ] Linting passes: `make lint`
- [ ] Coverage 100% for new models: `make test-coverage`
- [ ] No regression in existing tests: `make test`

**Estimated effort**: 3.5 hours (1.5 implementation + 2 testing)
