# Implementation Spec: Implement dbt metrics YAML parser

## Metadata
- **Issue**: `DTL-024`
- **Stack**: `backend`
- **Generated**: 2025-11-18
- **Strategy**: Approved 2025-11-18

## Issue Context

### Problem Statement
Create a parser to read dbt metric YAML files and convert them to Metric schema models. This parser needs to support all four metric types (simple, ratio, derived, conversion), handle multiple YAML formats, provide smart primary entity resolution, and integrate seamlessly with the existing DbtParser infrastructure.

### Solution Approach
Implement `DbtMetricParser` class extending the base `Parser` interface, following the same architectural patterns as `DbtParser`. The parser will:
- Support all four metric types with type-specific parameter parsing
- Intelligently infer primary entities from ratio metric denominators
- Extract measure dependencies for validation
- Provide comprehensive error handling with clear, actionable messages
- Achieve 95%+ test coverage with extensive unit and integration tests

### Success Criteria
- Successfully parse all metric types (simple, ratio, derived, conversion)
- Smart primary entity resolution (explicit → inferred → error with guidance)
- Comprehensive dependency extraction for all metric types
- Clear error messages for all failure scenarios
- 95%+ branch coverage
- Full mypy --strict compliance

## Approved Strategy Summary

The approved strategy defines a robust architecture based on:

1. **Extending base Parser interface**: Maintains consistency with `DbtParser`, reusing YAML utilities and error handling
2. **Separate concern from semantic models**: Metrics parsed independently, linked during validation
3. **Smart primary entity inference**: For ratio metrics, infer from denominator measure's parent semantic model
4. **Fail-fast validation**: Validate structure immediately during parsing
5. **Type-specific parameter parsing**: Dedicated logic for each metric type's parameters

Key architectural decisions:
- Follow `DbtParser` file discovery patterns (recursive glob for .yml/.yaml)
- Support multiple YAML formats (metrics list, single metric, top-level list)
- Use Pydantic validation through Metric schema models (DTL-023)
- Provide module-level utility functions for entity resolution and dependency extraction

## Implementation Plan

### Phase 1: Core Parser Implementation
Create the main `DbtMetricParser` class with basic parsing infrastructure.

**Tasks**:
1. **Create `src/dbt_to_lookml/parsers/dbt_metrics.py`**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Create new module with class definition
   - Pattern: Follow `DbtParser` structure from `parsers/dbt.py`
   - Reference: `src/dbt_to_lookml/parsers/dbt.py:26-102`

2. **Implement `DbtMetricParser` class skeleton**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Define class extending `Parser` with `__init__`, abstract method stubs
   - Pattern: Same inheritance and initialization as `DbtParser`
   - Reference: `src/dbt_to_lookml/parsers/dbt.py:26-27`, `src/dbt_to_lookml/interfaces/parser.py:12-22`

3. **Implement `parse_file()` method**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Parse single metric YAML file, handle multiple formats
   - Pattern: Similar to `DbtParser.parse_file()` - use `self.read_yaml()`, handle dict/list
   - Reference: `src/dbt_to_lookml/parsers/dbt.py:29-72`

4. **Implement `parse_directory()` method**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Recursively scan for .yml/.yaml files
   - Pattern: Exact pattern from `DbtParser.parse_directory()` with glob and recursion
   - Reference: `src/dbt_to_lookml/parsers/dbt.py:74-102`

5. **Implement `validate()` method**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Validate metric structure (has 'metrics' key or direct metric structure)
   - Pattern: Similar to `DbtParser.validate()` - check for required keys
   - Reference: `src/dbt_to_lookml/parsers/dbt.py:104-133`

### Phase 2: Metric Parsing Logic
Implement type-specific metric parsing and validation.

**Tasks**:
1. **Implement `_parse_metric()` internal method**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Parse single metric dictionary into Metric object
   - Pattern: Similar to `DbtParser._parse_semantic_model()` - validate required fields, delegate to Pydantic
   - Reference: `src/dbt_to_lookml/parsers/dbt.py:147-379`

2. **Implement `_parse_type_params()` method**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Parse type-specific parameters based on metric type
   - Pattern: Switch statement on metric type, construct appropriate TypeParams subclass
   - Implementation: See strategy section 2.3 for detailed logic

3. **Implement `_validate_metric_structure()` helper**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Check single metric has required fields (name, type, type_params)
   - Pattern: Similar to `DbtParser._validate_model_structure()`
   - Reference: `src/dbt_to_lookml/parsers/dbt.py:135-145`

### Phase 3: Utility Functions
Implement module-level utility functions for entity resolution and dependency extraction.

**Tasks**:
1. **Implement `resolve_primary_entity()` function**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Three-tier priority: explicit meta → infer from denominator → error
   - Pattern: Standalone function accepting metric and semantic models list
   - Implementation: See strategy section 2.4 for complete algorithm

2. **Implement `extract_measure_dependencies()` function**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Extract measure names by metric type
   - Pattern: Type-specific extraction returning set of measure names
   - Implementation: See strategy section 2.5 for complete logic

3. **Implement `find_measure_model()` helper**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Find semantic model containing specific measure
   - Pattern: Iterate semantic models, check measures list
   - Implementation: Simple iteration with measure name matching

### Phase 4: Error Handling
Add comprehensive error handling with clear, actionable messages.

**Tasks**:
1. **Add file not found handling**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Raise FileNotFoundError with path in `parse_file()`
   - Pattern: Same as `DbtParser.parse_file()`
   - Reference: `src/dbt_to_lookml/parsers/dbt.py:43-44`

2. **Add invalid YAML handling**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Let yaml.YAMLError propagate with context via `handle_error()`
   - Pattern: Use try/except in parse methods, delegate to `self.handle_error()`
   - Reference: `src/dbt_to_lookml/parsers/dbt.py:69-70`

3. **Add missing field validation**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Check required fields (name, type, type_params) in `_parse_metric()`
   - Pattern: Explicit checks with clear ValueError messages
   - Reference: `src/dbt_to_lookml/parsers/dbt.py:161-164`

4. **Add unknown metric type handling**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Raise ValueError with supported types list in `_parse_type_params()`
   - Pattern: Final else clause with descriptive message
   - Implementation: See strategy section 2.3, line 320-324

5. **Add primary entity resolution errors**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Raise ValueError with guidance when can't resolve
   - Pattern: Clear message with YAML snippet showing how to fix
   - Implementation: See strategy section 2.4, line 359-365

### Phase 5: Module Integration
Export the parser and integrate with existing codebase.

**Tasks**:
1. **Export `DbtMetricParser` from `parsers/__init__.py`**
   - File: `src/dbt_to_lookml/parsers/__init__.py`
   - Action: Add import and export to `__all__`
   - Pattern: Same as existing `DbtParser` export
   - Reference: Strategy section 5.3 for export pattern

2. **Add comprehensive module docstring**
   - File: `src/dbt_to_lookml/parsers/dbt_metrics.py`
   - Action: Add module-level docstring with examples
   - Pattern: Google-style docstring with usage examples
   - Reference: Strategy Appendix A for usage example

### Phase 6: Testing
Create comprehensive test suite with 95%+ coverage.

**Tasks**:
1. **Create unit test file**
   - File: `src/tests/unit/test_dbt_metric_parser.py`
   - Action: Create test file with test classes
   - Pattern: Follow structure from `test_dbt_parser.py`
   - Reference: `src/tests/unit/test_dbt_parser.py:1-100`

2. **Create metric fixtures directory**
   - File: `src/tests/fixtures/metrics/`
   - Action: Create directory and fixture files for all metric types
   - Pattern: Similar to `sample_semantic_model.yml`
   - Implementation: See strategy section 4.3 for fixture structure

3. **Write parser unit tests**
   - File: `src/tests/unit/test_dbt_metric_parser.py`
   - Action: Implement `TestDbtMetricParser` class with all test methods
   - Pattern: Use TemporaryDirectory, yaml.dump, pytest assertions
   - Reference: `src/tests/unit/test_dbt_parser.py:18-100`
   - Tests: See strategy section 4.1 for complete test list

4. **Write utility function tests**
   - File: `src/tests/unit/test_dbt_metric_parser.py`
   - Action: Implement `TestPrimaryEntityResolution`, `TestDependencyExtraction`, `TestFindMeasureModel`
   - Pattern: Direct function calls with test data
   - Tests: See strategy section 4.1 for complete test list

5. **Create integration tests**
   - File: `src/tests/integration/test_metric_parsing_integration.py`
   - Action: Create end-to-end tests with real fixtures
   - Pattern: Parse actual files, validate against semantic models
   - Tests: See strategy section 4.2 for test scenarios

## Detailed Task Breakdown

### Task 1: Create DbtMetricParser Class

**File**: `src/dbt_to_lookml/parsers/dbt_metrics.py`

**Action**: Create new parser module with complete implementation

**Implementation Guidance**:
```python
"""Parser for dbt metric YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from dbt_to_lookml.interfaces.parser import Parser
from dbt_to_lookml.schemas import (
    Metric,
    SimpleMetricParams,
    RatioMetricParams,
    DerivedMetricParams,
    ConversionMetricParams,
    MetricReference,
    SemanticModel,
)


class DbtMetricParser(Parser):
    """Parser for dbt metric YAML files.

    Parses metric definitions from YAML files and converts them to Metric
    schema objects. Supports all metric types: simple, ratio, derived, conversion.
    Validates metric structure and resolves primary entities.

    Example:
        >>> parser = DbtMetricParser(strict_mode=True)
        >>> metrics = parser.parse_directory(Path("metrics/"))
        >>> print(f"Found {len(metrics)} metrics")
    """

    def parse_file(self, file_path: Path) -> list[Metric]:
        """Parse a single metric YAML file.

        Supports multiple YAML formats:
        - metrics: [list of metrics]
        - Direct metric object (single)
        - Top-level list of metrics

        Args:
            file_path: Path to YAML file containing metrics

        Returns:
            List of parsed Metric objects

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is malformed
            ValidationError: If metric structure is invalid
        """
        # Implementation: Follow DbtParser.parse_file() pattern
        # 1. Check file exists
        # 2. Read YAML with self.read_yaml()
        # 3. Handle dict/list formats
        # 4. Extract metrics list
        # 5. Parse each metric with _parse_metric()
        # 6. Use self.handle_error() for exception handling

    def parse_directory(self, directory: Path) -> list[Metric]:
        """Recursively parse all metric files in directory.

        Scans for *.yml and *.yaml files, handling nested directories.
        Uses handle_error() for lenient vs strict error handling.

        Args:
            directory: Directory containing metric YAML files

        Returns:
            List of all parsed Metric objects
        """
        # Implementation: Exact pattern from DbtParser.parse_directory()
        # 1. Validate directory exists
        # 2. Glob *.yml files
        # 3. Glob *.yaml files
        # 4. Recursively handle subdirectories
        # 5. Collect all metrics

    def validate(self, content: dict[str, Any]) -> bool:
        """Validate that content contains valid metric structure.

        Checks for:
        - 'metrics' key or direct metric structure
        - Required fields: name, type, type_params
        - Valid metric type value

        Args:
            content: Parsed YAML content

        Returns:
            True if valid metric structure, False otherwise
        """
        # Implementation: Similar to DbtParser.validate()
        # 1. Check for metrics key
        # 2. Check for direct metric structure
        # 3. Validate first metric has required fields

    def _parse_metric(self, metric_data: dict[str, Any]) -> Metric:
        """Parse single metric from dictionary data.

        Internal method that handles type-specific params construction
        and delegates to Pydantic validation.

        Args:
            metric_data: Dictionary with metric fields

        Returns:
            Validated Metric object

        Raises:
            ValidationError: If metric structure invalid
            ValueError: If metric type unsupported
        """
        # Implementation:
        # 1. Validate required fields (name, type, type_params)
        # 2. Parse type_params with _parse_type_params()
        # 3. Construct Metric object
        # 4. Wrap errors with context (metric name)

    def _parse_type_params(
        self,
        metric_type: str,
        params_data: dict[str, Any]
    ) -> SimpleMetricParams | RatioMetricParams | DerivedMetricParams | ConversionMetricParams:
        """Parse type-specific parameters based on metric type.

        Constructs appropriate TypeParams subclass:
        - simple -> SimpleMetricParams
        - ratio -> RatioMetricParams
        - derived -> DerivedMetricParams
        - conversion -> ConversionMetricParams

        Args:
            metric_type: One of 'simple', 'ratio', 'derived', 'conversion'
            params_data: Dictionary with type-specific params

        Returns:
            Appropriate MetricTypeParams subclass instance

        Raises:
            ValueError: If metric_type is unknown
            ValidationError: If params don't match expected structure
        """
        # Implementation: See strategy section 2.3 for complete logic
        # Switch on metric_type, construct appropriate params object

    def _validate_metric_structure(self, metric: dict[str, Any]) -> bool:
        """Validate single metric dictionary has required fields.

        Args:
            metric: Metric dictionary to validate

        Returns:
            True if has required fields, False otherwise
        """
        # Implementation: Check for name, type, type_params keys
```

**Reference**: Similar implementation at `src/dbt_to_lookml/parsers/dbt.py:26-379`

**Tests**:
- `test_parse_simple_metric()`
- `test_parse_ratio_metric()`
- `test_parse_derived_metric()`
- `test_parse_conversion_metric()`
- `test_parse_file_not_found()`
- `test_parse_invalid_yaml()`
- `test_parse_directory_recursive()`

### Task 2: Implement Utility Functions

**File**: `src/dbt_to_lookml/parsers/dbt_metrics.py`

**Action**: Add module-level utility functions after class definition

**Implementation Guidance**:
```python
def resolve_primary_entity(
    metric: Metric,
    semantic_models: list[SemanticModel]
) -> str:
    """Determine primary entity for metric.

    Resolution priority:
    1. Explicit meta.primary_entity (highest priority)
    2. Infer from denominator for ratio metrics
    3. Raise error requiring explicit specification

    Inference algorithm for ratio metrics:
    - Extract denominator measure name
    - Find semantic model containing that measure
    - Return that model's primary entity name

    Args:
        metric: Metric object to resolve
        semantic_models: All semantic models for lookup

    Returns:
        Primary entity name (e.g., 'search', 'user', 'rental')

    Raises:
        ValueError: If can't resolve (missing meta, can't infer)

    Example:
        >>> metric = Metric(name="conversion_rate", type="ratio", ...)
        >>> entity = resolve_primary_entity(metric, semantic_models)
        >>> print(entity)  # "search"
    """
    # Implementation: See strategy section 2.4 for complete algorithm
    # 1. Check metric.meta["primary_entity"]
    # 2. If ratio, find denominator's model and extract primary entity
    # 3. Raise helpful error with YAML snippet


def extract_measure_dependencies(metric: Metric) -> set[str]:
    """Extract all measure names referenced by metric.

    Handles each metric type:
    - simple: {type_params.measure}
    - ratio: {numerator, denominator}
    - derived: Extract from metrics list (not measures)
    - conversion: Extract from conversion_type_params

    Args:
        metric: Metric to extract dependencies from

    Returns:
        Set of measure names (strings)

    Example:
        >>> metric = Metric(name="revenue_per_user", type="ratio", ...)
        >>> deps = extract_measure_dependencies(metric)
        >>> print(deps)  # {"total_revenue", "user_count"}
    """
    # Implementation: See strategy section 2.5 for complete logic
    # Switch on metric.type, extract appropriate measure names


def find_measure_model(
    measure_name: str,
    semantic_models: list[SemanticModel]
) -> SemanticModel | None:
    """Find which semantic model contains a measure.

    Args:
        measure_name: Name of measure to find
        semantic_models: List of semantic models to search

    Returns:
        SemanticModel containing the measure, or None if not found

    Example:
        >>> model = find_measure_model("revenue", semantic_models)
        >>> print(model.name)  # "rentals"
    """
    # Implementation: Simple iteration
    # for model in semantic_models:
    #     for measure in model.measures:
    #         if measure.name == measure_name:
    #             return model
    # return None
```

**Reference**: Strategy sections 2.4 and 2.5 for detailed algorithms

**Tests**:
- `test_resolve_primary_entity_explicit()`
- `test_resolve_primary_entity_infer_from_denominator()`
- `test_resolve_primary_entity_error_no_meta()`
- `test_extract_measure_dependencies_simple()`
- `test_extract_measure_dependencies_ratio()`
- `test_find_measure_model_found()`
- `test_find_measure_model_not_found()`

### Task 3: Create Test Fixtures

**File**: Create directory and fixture files

**Action**: Set up test fixtures for all metric types

**Structure**:
```
src/tests/fixtures/metrics/
├── simple_metric.yml
├── ratio_metric.yml
├── derived_metric.yml
├── conversion_metric.yml
└── nested/
    └── additional_metrics.yml
```

**Fixture Content Examples**:

`simple_metric.yml`:
```yaml
metrics:
  - name: total_revenue
    type: simple
    type_params:
      measure: revenue
    label: Total Revenue
    description: Sum of all revenue
    meta:
      primary_entity: rental
```

`ratio_metric.yml`:
```yaml
metrics:
  - name: search_conversion_rate
    type: ratio
    type_params:
      numerator: rental_count
      denominator: search_count
    label: Search Conversion Rate
    description: Percentage of searches that convert to rentals
    # No primary_entity - will be inferred from denominator

  - name: revenue_per_user
    type: ratio
    type_params:
      numerator: total_revenue
      denominator: user_count
    meta:
      primary_entity: user  # Explicit
```

`derived_metric.yml`:
```yaml
metrics:
  - name: revenue_growth
    type: derived
    type_params:
      expr: "current_revenue - previous_revenue"
      metrics:
        - name: total_revenue
          alias: current_revenue
        - name: total_revenue
          alias: previous_revenue
          offset_window: "1 month"
    meta:
      primary_entity: rental
```

`conversion_metric.yml`:
```yaml
metrics:
  - name: user_conversion
    type: conversion
    type_params:
      conversion_type_params:
        base_measure: search_count
        conversion_measure: rental_count
        entity: user_id
    meta:
      primary_entity: user
```

## File Changes

### Files to Create

#### `src/dbt_to_lookml/parsers/dbt_metrics.py`
**Why**: Main implementation file for metric parser

**Structure**: Based on `src/dbt_to_lookml/parsers/dbt.py`

**Estimated lines**: ~450 lines (class: ~300, utilities: ~150)

**Contents**:
- Module docstring
- Imports (Parser, Metric schemas, ValidationError)
- `DbtMetricParser` class (~300 lines)
  - `parse_file()` method (~40 lines)
  - `parse_directory()` method (~30 lines)
  - `validate()` method (~25 lines)
  - `_parse_metric()` method (~50 lines)
  - `_parse_type_params()` method (~80 lines)
  - `_validate_metric_structure()` method (~10 lines)
- Utility functions (~150 lines)
  - `resolve_primary_entity()` (~60 lines)
  - `extract_measure_dependencies()` (~50 lines)
  - `find_measure_model()` (~15 lines)

#### `src/tests/unit/test_dbt_metric_parser.py`
**Why**: Comprehensive unit tests for parser

**Structure**: Based on `src/tests/unit/test_dbt_parser.py`

**Estimated lines**: ~800 lines (35-40 test methods)

**Contents**:
- `TestDbtMetricParser` class (~400 lines, 20 tests)
- `TestPrimaryEntityResolution` class (~200 lines, 7 tests)
- `TestDependencyExtraction` class (~120 lines, 5 tests)
- `TestFindMeasureModel` class (~80 lines, 4 tests)

#### `src/tests/integration/test_metric_parsing_integration.py`
**Why**: End-to-end integration tests

**Estimated lines**: ~200 lines (4 integration tests)

**Contents**:
- `TestMetricParsingIntegration` class
- Tests using real fixtures from `src/tests/fixtures/metrics/`

#### `src/tests/fixtures/metrics/simple_metric.yml`
**Why**: Test fixture for simple metrics

**Lines**: ~12 lines

#### `src/tests/fixtures/metrics/ratio_metric.yml`
**Why**: Test fixture for ratio metrics

**Lines**: ~22 lines

#### `src/tests/fixtures/metrics/derived_metric.yml`
**Why**: Test fixture for derived metrics

**Lines**: ~16 lines

#### `src/tests/fixtures/metrics/conversion_metric.yml`
**Why**: Test fixture for conversion metrics

**Lines**: ~14 lines

#### `src/tests/fixtures/metrics/nested/additional_metrics.yml`
**Why**: Test fixture for directory recursion

**Lines**: ~12 lines

### Files to Modify

#### `src/dbt_to_lookml/parsers/__init__.py`
**Why**: Export new parser

**Changes**:
- Add import: `from dbt_to_lookml.parsers.dbt_metrics import DbtMetricParser`
- Update `__all__`: Add `"DbtMetricParser"`

**Estimated lines**: +2 lines

## Testing Strategy

### Unit Tests

**File**: `src/tests/unit/test_dbt_metric_parser.py`

**Test Classes and Cases**:

**TestDbtMetricParser** (20 tests):
1. `test_parse_empty_file()` - Empty YAML returns empty list
2. `test_parse_file_not_found()` - FileNotFoundError raised
3. `test_parse_invalid_yaml()` - yaml.YAMLError raised
4. `test_parse_simple_metric()` - Simple metric parsed correctly
5. `test_parse_ratio_metric()` - Ratio metric parsed correctly
6. `test_parse_derived_metric()` - Derived metric with MetricReference list
7. `test_parse_conversion_metric()` - Conversion metric parsed correctly
8. `test_parse_multiple_metrics_in_list()` - Multiple metrics in one file
9. `test_parse_metrics_key_structure()` - YAML with 'metrics:' key
10. `test_parse_direct_metric_structure()` - Single metric (auto-wrapped)
11. `test_parse_top_level_list()` - Top-level list of metrics
12. `test_parse_directory_single_file()` - Directory with one file
13. `test_parse_directory_multiple_files()` - Directory with multiple files
14. `test_parse_directory_nested()` - Recursive directory parsing
15. `test_parse_directory_mixed_extensions()` - Both .yml and .yaml
16. `test_validate_valid_metric_structure()` - Valid structure returns True
17. `test_validate_missing_name()` - Missing name returns False
18. `test_validate_missing_type()` - Missing type returns False
19. `test_strict_mode_raises_on_invalid()` - Strict mode raises
20. `test_lenient_mode_continues_on_invalid()` - Lenient mode logs warning

**TestPrimaryEntityResolution** (7 tests):
1. `test_explicit_primary_entity()` - meta.primary_entity used
2. `test_infer_from_denominator_ratio_metric()` - Infers from denominator
3. `test_error_when_cannot_infer()` - Raises helpful error
4. `test_error_simple_metric_no_primary()` - Simple metric requires explicit
5. `test_error_derived_metric_no_primary()` - Derived metric requires explicit
6. `test_denominator_measure_not_found()` - Can't find denominator's model
7. `test_denominator_model_no_primary_entity()` - Model has no primary entity

**TestDependencyExtraction** (5 tests):
1. `test_simple_metric_dependencies()` - Returns {measure}
2. `test_ratio_metric_dependencies()` - Returns {numerator, denominator}
3. `test_derived_metric_dependencies()` - Returns empty set (metrics, not measures)
4. `test_conversion_metric_dependencies()` - Extracts from conversion_type_params
5. `test_empty_dependencies()` - Handles edge cases

**TestFindMeasureModel** (4 tests):
1. `test_find_measure_in_first_model()` - Found in first model
2. `test_find_measure_in_second_model()` - Found in second model
3. `test_measure_not_found()` - Returns None
4. `test_empty_semantic_models()` - Returns None for empty list

### Integration Tests

**File**: `src/tests/integration/test_metric_parsing_integration.py`

**Test Scenarios**:

1. **test_parse_real_metric_files()**
   - Setup: Create temp directory with all fixture files
   - Action: Parse directory with `DbtMetricParser`
   - Assert: All metrics parsed, correct types, correct field values

2. **test_parse_with_semantic_models()**
   - Setup: Parse semantic models and metrics
   - Action: Validate metrics against semantic models
   - Assert: All measure dependencies found, entities valid

3. **test_primary_entity_resolution_end_to_end()**
   - Setup: Parse semantic models and ratio metrics
   - Action: Resolve primary entities for all metrics
   - Assert: Explicit and inferred entities correct

4. **test_nested_directory_structure()**
   - Setup: Create nested directory structure with metrics
   - Action: Parse root directory recursively
   - Assert: Metrics from all levels found

### Edge Cases

1. **Metric with all optional fields**: Label, description, meta all populated
2. **Metric with minimal fields**: Only required fields
3. **Empty metrics list**: File with `metrics: []`
4. **Mixed valid/invalid metrics in file**: Some parse, some fail
5. **Circular metric dependencies**: Derived metric referencing itself
6. **Unknown measure reference**: Measure not in semantic models
7. **Malformed type_params**: Missing required fields
8. **Unknown metric type**: Type not in [simple, ratio, derived, conversion]

## Validation Commands

**Type checking**:
```bash
cd /Users/dug/Work/repos/dbt-to-lookml
make type-check
```

**Linting**:
```bash
make lint
```

**Unit tests only (fast feedback)**:
```bash
make test-fast
```

**Full test suite**:
```bash
make test
```

**Coverage report**:
```bash
make test-coverage
open htmlcov/index.html
```

**Quality gate (pre-commit)**:
```bash
make quality-gate
```

## Dependencies

### Existing Dependencies
- `pydantic`: For Metric model validation
- `pyyaml`: For YAML parsing (via Parser.read_yaml())
- `pytest`: For testing framework

### New Dependencies Needed
None - all required dependencies already in project

### Blocked By
- **DTL-023**: Requires `Metric`, `SimpleMetricParams`, `RatioMetricParams`, `DerivedMetricParams`, `ConversionMetricParams`, `MetricReference` models

**Status**: DTL-023 is in refinement with approved strategy but not yet implemented. This spec assumes DTL-023 will be completed first.

## Implementation Notes

### Important Considerations

1. **DTL-023 Dependency**: This parser requires the Metric schema models from DTL-023. Implementation should wait until DTL-023 is completed and merged.

2. **YAML Format Flexibility**: Support three YAML formats to maximize compatibility:
   - `metrics: [list]` - Standard dbt format
   - Direct metric object - Convenience for single metrics
   - Top-level list - Alternative format

3. **Error Context**: Always include metric name in error messages for easy debugging. Follow pattern from DbtParser of wrapping errors with context.

4. **Primary Entity Inference**: Only infer for ratio metrics from denominator. All other metric types require explicit `meta.primary_entity`.

5. **Dependency Extraction**: Derived metrics reference other metrics (not measures), so return empty set for measure dependencies.

6. **Strict vs Lenient Mode**: Inherit from Parser base class. Use `self.handle_error()` consistently for all error handling.

7. **Type Checking**: All type hints must pass `mypy --strict`. Use `list[Metric]` not `List[Metric]` (PEP 585).

### Code Patterns to Follow

**YAML Reading Pattern** (from `DbtParser.parse_file`):
```python
content = self.read_yaml(file_path)
if not content:
    return []

# Handle dict/list formats
if isinstance(content, dict):
    if "metrics" in content:
        metrics_data = content["metrics"]
    else:
        metrics_data = [content]
elif isinstance(content, list):
    metrics_data = content
else:
    raise ValueError(f"Invalid YAML structure in {file_path}")
```

**Error Handling Pattern** (from `DbtParser._parse_semantic_model`):
```python
try:
    # Parsing logic
    if "name" not in metric_data:
        raise ValueError("Missing required field 'name' in metric")
    # ...
except Exception as e:
    metric_name = metric_data.get("name", "unknown")
    raise ValueError(f"Error parsing metric '{metric_name}': {e}") from e
```

**Directory Recursion Pattern** (from `DbtParser.parse_directory`):
```python
if not directory.is_dir():
    raise ValueError(f"Not a directory: {directory}")

metrics = []

for yaml_file in directory.glob("*.yml"):
    try:
        metrics.extend(self.parse_file(yaml_file))
    except Exception as e:
        self.handle_error(e, f"Failed to parse {yaml_file}")

for yaml_file in directory.glob("*.yaml"):
    try:
        metrics.extend(self.parse_file(yaml_file))
    except Exception as e:
        self.handle_error(e, f"Failed to parse {yaml_file}")

return metrics
```

**Test Fixture Pattern** (from `test_dbt_parser.py`):
```python
def test_parse_simple_metric(self) -> None:
    """Test parsing a simple metric."""
    parser = DbtMetricParser()

    metric_data = {
        "name": "total_revenue",
        "type": "simple",
        "type_params": {"measure": "revenue"},
        "meta": {"primary_entity": "rental"}
    }

    with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump({"metrics": [metric_data]}, f)
        temp_path = Path(f.name)

    try:
        metrics = parser.parse_file(temp_path)
        assert len(metrics) == 1
        assert metrics[0].name == "total_revenue"
        assert metrics[0].type == "simple"
    finally:
        temp_path.unlink()
```

### References
- **Parser interface**: `src/dbt_to_lookml/interfaces/parser.py:12-90`
- **DbtParser implementation**: `src/dbt_to_lookml/parsers/dbt.py:26-379`
- **Parser tests**: `src/tests/unit/test_dbt_parser.py:18-100`
- **Test fixtures**: `src/tests/fixtures/sample_semantic_model.yml`
- **Strategy document**: `.tasks/strategies/DTL-024-strategy.md`

## Ready for Implementation

This spec is complete and ready for implementation. All architectural decisions have been made, code patterns identified, and test cases defined. Implementation can proceed phase by phase, with each phase independently testable.

**Recommended Implementation Order**:
1. Wait for DTL-023 completion (Metric schema models)
2. Phase 1: Core Parser Implementation
3. Phase 2: Metric Parsing Logic
4. Phase 6: Testing (create fixtures and basic tests)
5. Phase 3: Utility Functions
6. Phase 4: Error Handling
7. Phase 5: Module Integration
8. Final: Complete test coverage to 95%+

**Estimated Implementation Time**: 3-5 days (including comprehensive testing)
