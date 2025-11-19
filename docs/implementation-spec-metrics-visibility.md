# Implementation Specification: Metrics Support and Field Visibility Control

## Metadata
- **Issues**: DTL-022 through DTL-028
- **Stack**: Backend (Python)
- **Generated**: 2025-11-19
- **Strategy**: Enhance existing implementation with field visibility controls
- **Current State**: Metrics support already exists (needs enhancement)

## Issue Context

### Problem Statement
The dbt-to-lookml tool has existing metrics support but lacks field visibility controls. This creates two critical gaps:

1. **Limited visibility control**: All dimensions and measures are exposed in LookML with no way to hide internal/technical fields beyond the existing `hidden` parameter
2. **No opt-in mechanism**: No way to selectively expose fields for BI tools while automatically including dependencies

### Solution Approach
Enhance the existing metrics implementation by:

1. **Visibility Controls**: Add `config.meta.hidden` and `config.meta.bi_field` parameters to ConfigMeta
2. **Smart Dependencies**: When using bi_field filtering, automatically include required measures (marked as hidden) even if not tagged as bi_field
3. **Maintain Compatibility**: Ensure all new features are optional and backward compatible

### Success Criteria
- ✅ Respect `hidden: true` in field metadata to exclude from LookML display
- ✅ Support `bi_field: true` opt-in mechanism for selective field exposure
- ✅ Automatically include metric dependencies (measures) even if not marked as bi_field, with hidden: yes
- ✅ Maintain backward compatibility (existing behavior unchanged when new fields not used)
- ✅ 95%+ test coverage across all new features
- ✅ Full type safety with mypy strict mode

## Approved Strategy Summary

The existing metrics implementation (already in `schemas.py` and `parsers/dbt_metrics.py`) provides a solid foundation. We need to:
1. Add visibility control fields to ConfigMeta
2. Update dimension/measure/metric LookML generation to respect hidden parameter
3. Add bi_field filtering logic to LookMLGenerator
4. Implement dependency resolution for metrics to auto-include required measures

## Implementation Plan

### Phase 1: Foundation - Schema Models Enhancement (DTL-022)

Since metrics schemas already exist, this phase focuses on understanding and documenting the current implementation.

**Tasks**:
1. **Review Existing Metric Schemas**
   - File: `src/dbt_to_lookml/schemas.py:589-965`
   - Action: Document existing classes: MetricReference, SimpleMetricParams, RatioMetricParams, DerivedMetricParams, ConversionMetricParams, Metric
   - Reference: Already implemented with to_lookml_dict methods

2. **Review Existing Parser**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Document DbtMetricParser class and its methods
   - Reference: Already handles all metric types

### Phase 2: Parser Extension Review (DTL-023)

The parser already supports metrics files. This phase is documentation only.

**Tasks**:
1. **Document Parser Capabilities**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Document that parser already supports:
     - Standard format: `metrics: [list]`
     - Direct format: Single metric object
     - Top-level format: List at root
     - Entity connectivity validation

### Phase 3: Implement Hidden Parameter Support (DTL-024)

**Tasks**:
1. **Add hidden field to ConfigMeta**
   - File: `src/dbt_to_lookml/schemas.py:25-86`
   - Action: Add `hidden: bool | None = None` after line 85
   - Pattern: Follow existing optional field pattern like `convert_tz`

2. **Update Dimension LookML Generation**
   - File: `src/dbt_to_lookml/schemas.py:222-242`
   - Action: In `_to_dimension_dict()`, check `self.config.meta.hidden` and add `hidden: "yes"` if True
   - Reference: Similar to how `view_label` and `group_label` are conditionally added

3. **Update Dimension Group LookML Generation**
   - File: `src/dbt_to_lookml/schemas.py:267-365`
   - Action: In `_to_dimension_group_dict()`, check hidden parameter before `convert_tz`
   - Add after line 362: Check config.meta.hidden and set result["hidden"] = "yes"

4. **Update Measure LookML Generation**
   - File: `src/dbt_to_lookml/schemas.py:426-450`
   - Action: In `to_lookml_dict()`, check config.meta.hidden and add hidden parameter
   - Add after line 448: Check hidden and set result["hidden"] = "yes"

5. **Update Metric LookML Generation**
   - File: `src/dbt_to_lookml/schemas.py:820-965`
   - Action: In Metric.to_lookml_dict(), check meta.hidden and add to result
   - Pattern: Follow existing meta field extraction pattern

### Phase 4: Implement bi_field Opt-in Mechanism (DTL-025)

**Tasks**:
1. **Add bi_field to ConfigMeta**
   - File: `src/dbt_to_lookml/schemas.py:25-86`
   - Action: Add `bi_field: bool | None = None` after hidden field
   - Pattern: Optional boolean field like hidden

2. **Add bi_field Filtering to LookMLGenerator**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Add `use_bi_field_filter: bool = False` parameter to `__init__`
   - Store as instance variable for use in generation

3. **Implement Field Filtering Logic**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: In `generate()` method, filter fields when use_bi_field_filter=True
   - Pattern: Check each field's config.meta.bi_field, include if True
   - Note: Primary keys (entities) always included regardless

4. **Add CLI Flag**
   - File: `src/dbt_to_lookml/__main__.py`
   - Action: Add `--bi-field-only` flag to generate command
   - Pattern: Follow existing boolean flag patterns like `--convert-tz`
   - Pass to LookMLGenerator constructor

### Phase 5: Smart Dependencies Implementation (DTL-026)

**Tasks**:
1. **Add Dependency Tracking to Metric**
   - File: `src/dbt_to_lookml/schemas.py:792-965`
   - Action: Add `get_required_measures()` method to Metric class
   - Implementation:
     ```python
     def get_required_measures(self) -> list[str]:
         """Get list of measure names this metric depends on."""
         if self.type == "simple" and isinstance(self.type_params, SimpleMetricParams):
             return [self.type_params.measure]
         elif self.type == "ratio" and isinstance(self.type_params, RatioMetricParams):
             return [self.type_params.numerator, self.type_params.denominator]
         elif self.type == "derived" and isinstance(self.type_params, DerivedMetricParams):
             # For derived, need to recursively resolve metric references
             return []  # Handled by generator's recursive resolution
         return []
     ```

2. **Add Recursive Dependency Resolution**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: Add `_resolve_metric_dependencies()` method
   - Pattern: Build dependency graph, detect cycles, collect all required measures
   - Reference: Similar to how wizard/detection.py handles directory traversal

3. **Auto-include Dependencies**
   - File: `src/dbt_to_lookml/generators/lookml.py`
   - Action: In field filtering logic, auto-include dependent measures
   - Mark auto-included measures as hidden unless already bi_field=true
   - Pattern: Two-pass approach: first collect bi_field metrics, then add dependencies

### Phase 6: Comprehensive Testing (DTL-027)

**Tasks**:
1. **Unit Tests for Hidden Parameter**
   - File: Create `src/tests/unit/test_hidden_parameter.py`
   - Test cases:
     - Dimension with hidden=true → hidden: yes in LookML
     - Dimension_group with hidden=true → hidden: yes
     - Measure with hidden=true → hidden: yes
     - Metric with hidden=true → hidden: yes
     - No hidden field → no hidden in output (backward compat)

2. **Unit Tests for bi_field Filter**
   - File: Create `src/tests/unit/test_bi_field_filter.py`
   - Test cases:
     - Generator with use_bi_field_filter=false → all fields included
     - Generator with use_bi_field_filter=true → only bi_field=true included
     - Primary keys always included regardless
     - CLI flag parsing and propagation

3. **Unit Tests for Dependencies**
   - File: Create `src/tests/unit/test_metric_dependencies.py`
   - Test cases:
     - Simple metric dependency extraction
     - Ratio metric dependency extraction
     - Derived metric recursive resolution
     - Circular dependency detection
     - Auto-included measures get hidden: yes

4. **Integration Tests**
   - File: Create `src/tests/integration/test_visibility_end_to_end.py`
   - Test full pipeline with hidden/bi_field parameters
   - File: Update `src/tests/integration/test_metric_parsing_integration.py`
   - Add tests for bi_field filtering with metrics

5. **Golden Tests**
   - File: Update `src/tests/test_golden.py`
   - Add fixtures for hidden fields
   - Add fixtures for bi_field filtering
   - Add fixtures for dependency resolution

### Phase 7: Documentation Updates (DTL-028)

**Tasks**:
1. **Update CLAUDE.md**
   - File: `CLAUDE.md`
   - Action: Add sections:
     - "Field Visibility Control" after "Timezone Conversion Configuration"
     - Document hidden and bi_field parameters
     - Add examples showing usage
     - Document precedence and defaults

2. **Add Example Files**
   - Files: Create in `examples/visibility/`
     - `hidden_fields.yml`: Example with hidden dimensions/measures
     - `bi_field_selection.yml`: Example with bi_field opt-in
     - `metric_dependencies.yml`: Example showing auto-inclusion

## Detailed Task Breakdown

### Task 1: Add Visibility Fields to ConfigMeta

**File**: `src/dbt_to_lookml/schemas.py:25-86`

**Action**: Add hidden and bi_field fields

**Implementation Guidance**:
```python
class ConfigMeta(BaseModel):
    """Represents metadata in a config section.

    ...existing docstring...
    """

    domain: str | None = None
    owner: str | None = None
    contains_pii: bool | None = None
    update_frequency: str | None = None
    subject: str | None = None
    category: str | None = None
    hierarchy: Hierarchy | None = None
    convert_tz: bool | None = None
    hidden: bool | None = None  # NEW: Control field visibility in LookML
    bi_field: bool | None = None  # NEW: Mark field for BI exposure
```

**Reference**: Lines 77-85 show existing optional bool fields pattern

### Task 2: Update Dimension Hidden Support

**File**: `src/dbt_to_lookml/schemas.py:222-242`

**Implementation Guidance**:
```python
def _to_dimension_dict(self) -> dict[str, Any]:
    """Convert categorical dimension to LookML dimension."""
    result: dict[str, Any] = {
        "name": self.name,
        "type": "string",
        "sql": self.expr or f"${TABLE}.{self.name}",
    }

    # ...existing code for description, label, hierarchy labels...

    # Add hidden parameter if specified
    if self.config and self.config.meta and self.config.meta.hidden is True:
        result["hidden"] = "yes"

    return result
```

**Reference**: Similar pattern at lines 236-240 for hierarchy labels

### Task 3: Update Measure Hidden Support

**File**: `src/dbt_to_lookml/schemas.py:426-450`

**Implementation Guidance**:
```python
def to_lookml_dict(self, model_name: str | None = None) -> dict[str, Any]:
    """Convert measure to LookML format."""
    result: dict[str, Any] = {
        "name": self.name,
        "type": LOOKML_TYPE_MAP.get(self.agg, "number"),
        "sql": self.expr or f"${TABLE}.{self.name}",
    }

    # ...existing code for description, label, hierarchy labels...

    # Add hidden parameter if specified
    if self.config and self.config.meta and self.config.meta.hidden is True:
        result["hidden"] = "yes"

    return result
```

### Task 4: LookMLGenerator bi_field Support

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Implementation Guidance**:
```python
class LookMLGenerator(Generator):
    """Generator for LookML files from semantic models."""

    def __init__(
        self,
        view_prefix: str = "",
        explore_prefix: str = "",
        connection_name: str = "redshift_test",
        convert_tz: bool | None = None,
        use_bi_field_filter: bool = False,  # NEW parameter
    ):
        """Initialize generator with options."""
        super().__init__()
        self.view_prefix = view_prefix
        self.explore_prefix = explore_prefix
        self.connection_name = connection_name
        self.convert_tz = convert_tz
        self.use_bi_field_filter = use_bi_field_filter  # Store for filtering
```

**In generate method**: Add filtering logic when creating explore fields

### Task 5: CLI Flag Addition

**File**: `src/dbt_to_lookml/__main__.py`

**Implementation Guidance**:
```python
@click.option(
    "--bi-field-only",
    is_flag=True,
    help="Only include fields marked with bi_field: true in explores",
)
def generate(
    # ...existing parameters...
    bi_field_only: bool,
):
    """Generate LookML from dbt semantic models."""
    # Pass to generator
    generator = LookMLGenerator(
        # ...existing parameters...
        use_bi_field_filter=bi_field_only,
    )
```

**Reference**: Follow pattern of --convert-tz/--no-convert-tz flags

## File Changes

### Files to Modify

#### `src/dbt_to_lookml/schemas.py`
**Why**: Add visibility control fields and update LookML generation

**Changes**:
- Add `hidden` and `bi_field` fields to ConfigMeta (lines 86-87)
- Update `Dimension._to_dimension_dict()` to check hidden (line ~240)
- Update `Dimension._to_dimension_group_dict()` to check hidden (line ~363)
- Update `Measure.to_lookml_dict()` to check hidden (line ~449)
- Update `Metric.to_lookml_dict()` to check hidden (line ~900)
- Add `Metric.get_required_measures()` method (line ~920)

**Estimated lines**: ~30 additions

#### `src/dbt_to_lookml/generators/lookml.py`
**Why**: Add bi_field filtering and dependency resolution

**Changes**:
- Add `use_bi_field_filter` parameter to `__init__`
- Add `_filter_fields_by_bi_field()` method
- Add `_resolve_metric_dependencies()` method
- Update `generate()` to apply filtering when enabled
- Auto-include dependencies with hidden: yes

**Estimated lines**: ~150 additions

#### `src/dbt_to_lookml/__main__.py`
**Why**: Add CLI flag for bi_field filtering

**Changes**:
- Add `--bi-field-only` click option
- Pass flag to LookMLGenerator constructor

**Estimated lines**: ~10 additions

### Files to Create

#### `src/tests/unit/test_hidden_parameter.py`
**Why**: Unit tests for hidden parameter support

**Structure**: Based on `test_flat_meta.py`

```python
"""Unit tests for hidden parameter support."""

import pytest
from dbt_to_lookml.schemas import (
    ConfigMeta, Config, Dimension, Measure, Metric,
    DimensionType, AggregationType, SimpleMetricParams
)

class TestHiddenParameter:
    """Test cases for hidden parameter in fields."""

    def test_dimension_with_hidden_true(self):
        """Test dimension with hidden=true generates hidden: yes."""
        # Test implementation

    def test_measure_with_hidden_true(self):
        """Test measure with hidden=true generates hidden: yes."""
        # Test implementation

    # More test cases...
```

#### `src/tests/unit/test_bi_field_filter.py`
**Why**: Unit tests for bi_field filtering

**Structure**: Test LookMLGenerator filtering logic

#### `src/tests/unit/test_metric_dependencies.py`
**Why**: Unit tests for dependency resolution

**Structure**: Test get_required_measures and recursive resolution

#### `src/tests/integration/test_visibility_end_to_end.py`
**Why**: Integration tests for complete visibility workflow

**Structure**: Parse YAML → Generate LookML with filtering → Validate output

## Testing Strategy

### Unit Tests

**File**: `src/tests/unit/test_hidden_parameter.py`

**Test Cases**:
1. **test_dimension_hidden_true**: Verify hidden: yes in output
2. **test_dimension_hidden_false**: Verify no hidden parameter
3. **test_dimension_hidden_none**: Verify backward compatibility
4. **test_measure_hidden_true**: Verify hidden: yes for measures
5. **test_metric_hidden_true**: Verify hidden: yes for metrics
6. **test_dimension_group_hidden**: Verify time dimensions support hidden

### Integration Tests

**File**: `src/tests/integration/test_visibility_end_to_end.py`

**Test Cases**:
1. **test_hidden_fields_excluded**: Full pipeline with hidden fields
2. **test_bi_field_filtering**: Only bi_field=true fields in explores
3. **test_dependency_auto_inclusion**: Required measures auto-included
4. **test_circular_dependency_handling**: Detect and handle cycles

### Golden Tests

Update existing golden test fixtures to include:
- Fields with hidden: true
- Fields with bi_field: true
- Metrics with dependencies requiring auto-inclusion

### Edge Cases
1. **Field with both hidden and bi_field**: bi_field takes precedence
2. **Metric referencing non-existent measure**: Log warning, skip
3. **Circular metric dependencies**: Detect, log, break cycle
4. **Empty bi_field filter result**: Include at least primary keys

## Validation Commands

**Backend**:
```bash
cd /Users/dug/Work/repos/dbt-to-lookml

# Format and lint
make format
make lint

# Type checking
make type-check

# Run specific test files
python -m pytest src/tests/unit/test_hidden_parameter.py -xvs
python -m pytest src/tests/unit/test_bi_field_filter.py -xvs
python -m pytest src/tests/unit/test_metric_dependencies.py -xvs

# Integration tests
python -m pytest src/tests/integration/test_visibility_end_to_end.py -xvs

# Full test suite with coverage
make test-coverage

# All quality gates
make quality-gate
```

**Manual Testing**:
```bash
# Test hidden parameter
echo 'semantic_models:
  - name: test_model
    model: "ref(test)"
    dimensions:
      - name: hidden_dim
        type: categorical
        config:
          meta:
            hidden: true
' | python -m dbt_to_lookml validate -

# Test bi_field filtering
python -m dbt_to_lookml generate \
  -i semantic_models/ \
  -o build/lookml/ \
  -s public \
  --bi-field-only
```

## Dependencies

### Existing Dependencies
- `pydantic`: Schema validation (already used)
- `pyyaml`: YAML parsing (already used)
- `lkml`: LookML validation (already used)
- `click`: CLI framework (already used)

### New Dependencies Needed
None - all functionality uses existing libraries

## Implementation Notes

### Important Considerations

1. **Backward Compatibility**: All new fields are optional with None defaults
2. **Entity Handling**: Entities remain hidden by default (existing behavior)
3. **Primary Keys**: Always included in explores regardless of bi_field setting
4. **Dependency Order**: Metrics must be processed after measures for dependency resolution
5. **Performance**: Dependency resolution uses caching to avoid repeated traversals

### Code Patterns to Follow

1. **Optional Field Pattern**: Follow ConfigMeta.convert_tz pattern for new fields
2. **LookML Generation**: Add fields conditionally like existing view_label/group_label
3. **Error Handling**: Use Parser.handle_error() for lenient mode support
4. **Testing**: Follow existing test structure in unit/integration/golden tests

### References
- `src/dbt_to_lookml/schemas.py:85`: Example of optional bool field (convert_tz)
- `src/dbt_to_lookml/schemas.py:236-240`: Pattern for conditional LookML fields
- `src/dbt_to_lookml/parsers/dbt_metrics.py`: Existing metrics parser
- `src/tests/unit/test_flat_meta.py`: Test pattern for metadata fields

## Implementation Order

1. **Phase 3**: Add hidden parameter support (simplest change)
2. **Phase 4**: Add bi_field parameter and basic filtering
3. **Phase 5**: Implement smart dependency resolution
4. **Phase 6**: Add comprehensive tests
5. **Phase 7**: Update documentation

## Success Metrics

- ✅ All existing tests continue to pass (backward compatibility)
- ✅ New unit tests achieve 95%+ branch coverage
- ✅ Integration tests validate end-to-end workflows
- ✅ Golden tests show correct LookML output
- ✅ mypy type checking passes with --strict
- ✅ make quality-gate passes all checks

## Ready for Implementation

This specification is complete and ready for implementation. The existing metrics support provides a solid foundation, requiring only targeted enhancements for visibility control and smart dependencies.