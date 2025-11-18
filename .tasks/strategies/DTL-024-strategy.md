# DTL-024 Implementation Strategy: Implement dbt metrics YAML parser

**Issue ID:** DTL-024
**Type:** Feature
**Priority:** High
**Created:** 2025-11-18
**Dependencies:** DTL-023 (Metric schema models)

---

## Executive Summary

Implement a robust parser for dbt metric YAML files that converts metric definitions into Metric schema objects. The parser will follow established patterns from `DbtParser`, supporting multiple metric types, primary entity resolution, dependency extraction, and comprehensive error handling.

### Key Architectural Decisions

1. **Extend base Parser interface**: `DbtMetricParser` inherits from `Parser` to maintain consistency with `DbtParser`
2. **Separate concern from semantic models**: Metrics and semantic models are parsed independently and linked during validation
3. **Smart primary entity inference**: For ratio metrics, infer primary entity from denominator measure's parent semantic model
4. **Fail-fast validation**: Validate metric structure and dependencies immediately during parsing
5. **Reuse YAML utilities**: Leverage `Parser.read_yaml()` and `Parser.handle_error()` for consistent behavior

---

## 1. Technical Architecture

### 1.1 Module Structure

**New file:** `src/dbt_to_lookml/parsers/dbt_metrics.py`

```
src/dbt_to_lookml/parsers/
├── __init__.py           # Add DbtMetricParser export
├── dbt.py               # Existing DbtParser (reference implementation)
└── dbt_metrics.py       # NEW: DbtMetricParser
```

### 1.2 Class Design

```python
class DbtMetricParser(Parser):
    """Parser for dbt metric YAML files.

    Parses metric definitions from YAML files and converts them to Metric
    schema objects. Supports all metric types: simple, ratio, derived, conversion.
    Validates metric structure and resolves primary entities.
    """

    def parse_file(self, file_path: Path) -> list[Metric]:
        """Parse a single metric YAML file.

        Args:
            file_path: Path to YAML file containing metrics

        Returns:
            List of parsed Metric objects

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is malformed
            ValidationError: If metric structure is invalid
        """

    def parse_directory(self, directory: Path) -> list[Metric]:
        """Recursively parse all metric files in directory.

        Scans for *.yml and *.yaml files, handling nested directories.
        Uses handle_error() for lenient vs strict error handling.

        Args:
            directory: Directory containing metric YAML files

        Returns:
            List of all parsed Metric objects
        """

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

    def _parse_type_params(
        self,
        metric_type: str,
        params_data: dict[str, Any]
    ) -> MetricTypeParams:
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

    def _validate_metric_structure(self, metric: dict[str, Any]) -> bool:
        """Validate single metric dictionary has required fields.

        Args:
            metric: Metric dictionary to validate

        Returns:
            True if has required fields, False otherwise
        """
```

### 1.3 Utility Functions

**Module-level functions in `dbt_metrics.py`:**

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
    """

def extract_measure_dependencies(metric: Metric) -> set[str]:
    """Extract all measure names referenced by metric.

    Handles each metric type:
    - simple: {type_params.measure}
    - ratio: {numerator, denominator}
    - derived: Extract from metrics list
    - conversion: Extract from conversion_type_params

    Args:
        metric: Metric to extract dependencies from

    Returns:
        Set of measure names (strings)
    """

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
    """
```

---

## 2. Implementation Details

### 2.1 File Discovery Pattern

**Following `DbtParser.parse_directory()` pattern:**

```python
def parse_directory(self, directory: Path) -> list[Metric]:
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    metrics = []

    # Handle both .yml and .yaml extensions
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

    # Handle nested directories (recursive)
    for subdir in directory.iterdir():
        if subdir.is_dir() and not subdir.name.startswith('.'):
            try:
                metrics.extend(self.parse_directory(subdir))
            except Exception as e:
                self.handle_error(e, f"Failed to parse directory {subdir}")

    return metrics
```

### 2.2 YAML Structure Support

**Support multiple YAML formats:**

```yaml
# Format 1: Direct metrics list
metrics:
  - name: total_revenue
    type: simple
    type_params:
      measure: revenue
    meta:
      primary_entity: rental

# Format 2: Single metric (auto-wrapped in list)
name: total_revenue
type: simple
type_params:
  measure: revenue

# Format 3: Top-level list
- name: metric_one
  type: simple
  type_params:
    measure: count_one
- name: metric_two
  type: ratio
  type_params:
    numerator: num
    denominator: denom
```

### 2.3 Type Parameter Parsing Logic

```python
def _parse_type_params(
    self,
    metric_type: str,
    params_data: dict[str, Any]
) -> MetricTypeParams:
    """Parse type-specific parameters."""

    if metric_type == "simple":
        return SimpleMetricParams(
            measure=params_data["measure"]
        )

    elif metric_type == "ratio":
        return RatioMetricParams(
            numerator=params_data["numerator"],
            denominator=params_data["denominator"]
        )

    elif metric_type == "derived":
        # Parse metric references
        metrics_list = []
        for metric_ref_data in params_data.get("metrics", []):
            metrics_list.append(MetricReference(
                name=metric_ref_data["name"],
                alias=metric_ref_data.get("alias"),
                offset_window=metric_ref_data.get("offset_window")
            ))

        return DerivedMetricParams(
            expr=params_data["expr"],
            metrics=metrics_list
        )

    elif metric_type == "conversion":
        return ConversionMetricParams(
            conversion_type_params=params_data.get("conversion_type_params", {})
        )

    else:
        raise ValueError(
            f"Unknown metric type: {metric_type}. "
            f"Supported types: simple, ratio, derived, conversion"
        )
```

### 2.4 Primary Entity Resolution Algorithm

```python
def resolve_primary_entity(
    metric: Metric,
    semantic_models: list[SemanticModel]
) -> str:
    """Resolve primary entity with fallback logic."""

    # Priority 1: Explicit meta.primary_entity
    if metric.meta and "primary_entity" in metric.meta:
        return metric.meta["primary_entity"]

    # Priority 2: Infer from denominator (ratio metrics only)
    if metric.type == "ratio":
        assert isinstance(metric.type_params, RatioMetricParams)
        denominator_measure = metric.type_params.denominator

        # Find semantic model containing denominator measure
        model = find_measure_model(denominator_measure, semantic_models)

        if model:
            # Extract primary entity from model
            primary_entity = None
            for entity in model.entities:
                if entity.type == "primary":
                    primary_entity = entity.name
                    break

            if primary_entity:
                return primary_entity

    # Priority 3: Error - require explicit specification
    raise ValueError(
        f"Metric '{metric.name}' requires explicit primary_entity. "
        f"Add to meta block:\n"
        f"meta:\n"
        f"  primary_entity: <entity_name>"
    )
```

### 2.5 Dependency Extraction

```python
def extract_measure_dependencies(metric: Metric) -> set[str]:
    """Extract measure dependencies by type."""

    if metric.type == "simple":
        assert isinstance(metric.type_params, SimpleMetricParams)
        return {metric.type_params.measure}

    elif metric.type == "ratio":
        assert isinstance(metric.type_params, RatioMetricParams)
        return {
            metric.type_params.numerator,
            metric.type_params.denominator
        }

    elif metric.type == "derived":
        assert isinstance(metric.type_params, DerivedMetricParams)
        # For derived metrics, dependencies are other metrics (not measures)
        # Return empty set for measure dependencies
        return set()

    elif metric.type == "conversion":
        # Conversion metrics have complex params
        # Extract measures from conversion_type_params if present
        assert isinstance(metric.type_params, ConversionMetricParams)
        params = metric.type_params.conversion_type_params
        dependencies = set()

        if "base_measure" in params:
            dependencies.add(params["base_measure"])
        if "conversion_measure" in params:
            dependencies.add(params["conversion_measure"])

        return dependencies

    return set()
```

---

## 3. Error Handling Strategy

### 3.1 Error Categories

| Error Category | Example | Handling | User Message |
|---------------|---------|----------|--------------|
| Missing file | `metrics/foo.yml` doesn't exist | FileNotFoundError | "File not found: {path}" |
| Invalid YAML | Malformed YAML syntax | yaml.YAMLError | "Invalid YAML in {file}: {error}" |
| Missing required field | No `name` field | ValidationError | "Missing required field 'name' in metric" |
| Unknown metric type | `type: custom` | ValueError | "Unknown metric type 'custom'. Supported: simple, ratio, derived, conversion" |
| Invalid type params | Missing `measure` in simple metric | ValidationError | "SimpleMetricParams missing required field 'measure'" |
| Missing primary entity | Can't infer for simple metric | ValueError | "Metric requires explicit primary_entity in meta block" |

### 3.2 Error Context Propagation

**Follow DbtParser pattern for contextual errors:**

```python
def _parse_metric(self, metric_data: dict[str, Any]) -> Metric:
    """Parse with error context."""
    try:
        # Validate required fields
        if "name" not in metric_data:
            raise ValueError("Missing required field 'name' in metric")
        if "type" not in metric_data:
            raise ValueError("Missing required field 'type' in metric")
        if "type_params" not in metric_data:
            raise ValueError("Missing required field 'type_params' in metric")

        # Parse type params
        type_params = self._parse_type_params(
            metric_data["type"],
            metric_data["type_params"]
        )

        # Construct Metric object (Pydantic validation)
        return Metric(
            name=metric_data["name"],
            type=metric_data["type"],
            type_params=type_params,
            label=metric_data.get("label"),
            description=metric_data.get("description"),
            meta=metric_data.get("meta")
        )

    except Exception as e:
        metric_name = metric_data.get("name", "unknown")
        raise ValueError(
            f"Error parsing metric '{metric_name}': {e}"
        ) from e
```

### 3.3 Strict vs Lenient Mode

**Inherited from `Parser` base class:**

- **Strict mode** (`strict_mode=True`): Raise exceptions immediately
- **Lenient mode** (`strict_mode=False`): Log warnings and continue parsing
- Use `self.handle_error()` for consistent behavior

---

## 4. Testing Strategy

### 4.1 Unit Tests

**File:** `src/tests/unit/test_dbt_metric_parser.py`

**Test Coverage:**

```python
class TestDbtMetricParser:
    """Unit tests for DbtMetricParser."""

    # File parsing tests
    def test_parse_empty_file() -> None
    def test_parse_file_not_found() -> None
    def test_parse_invalid_yaml() -> None

    # Single metric type tests
    def test_parse_simple_metric() -> None
    def test_parse_ratio_metric() -> None
    def test_parse_derived_metric() -> None
    def test_parse_conversion_metric() -> None

    # Multiple metrics
    def test_parse_multiple_metrics_in_list() -> None
    def test_parse_metrics_key_structure() -> None

    # Directory parsing
    def test_parse_directory_single_file() -> None
    def test_parse_directory_multiple_files() -> None
    def test_parse_directory_nested() -> None
    def test_parse_directory_mixed_extensions() -> None

    # Validation
    def test_validate_valid_metric_structure() -> None
    def test_validate_missing_name() -> None
    def test_validate_missing_type() -> None
    def test_validate_unknown_type() -> None

    # Error handling
    def test_strict_mode_raises_on_invalid() -> None
    def test_lenient_mode_continues_on_invalid() -> None

    # Edge cases
    def test_parse_metric_with_all_fields() -> None
    def test_parse_metric_minimal_fields() -> None


class TestPrimaryEntityResolution:
    """Tests for resolve_primary_entity function."""

    def test_explicit_primary_entity() -> None
    def test_infer_from_denominator_ratio_metric() -> None
    def test_error_when_cannot_infer() -> None
    def test_error_simple_metric_no_primary() -> None
    def test_error_derived_metric_no_primary() -> None
    def test_denominator_measure_not_found() -> None
    def test_denominator_model_no_primary_entity() -> None


class TestDependencyExtraction:
    """Tests for extract_measure_dependencies function."""

    def test_simple_metric_dependencies() -> None
    def test_ratio_metric_dependencies() -> None
    def test_derived_metric_dependencies() -> None
    def test_conversion_metric_dependencies() -> None
    def test_empty_dependencies() -> None


class TestFindMeasureModel:
    """Tests for find_measure_model function."""

    def test_find_measure_in_first_model() -> None
    def test_find_measure_in_second_model() -> None
    def test_measure_not_found() -> None
    def test_empty_semantic_models() -> None
```

### 4.2 Integration Tests

**File:** `src/tests/integration/test_metric_parsing_integration.py`

**Test Scenarios:**

```python
class TestMetricParsingIntegration:
    """End-to-end metric parsing tests."""

    def test_parse_real_metric_files() -> None:
        """Parse actual metric YAML fixtures."""

    def test_parse_with_semantic_models() -> None:
        """Parse metrics and validate against semantic models."""

    def test_primary_entity_resolution_end_to_end() -> None:
        """Test full resolution flow with real data."""

    def test_nested_directory_structure() -> None:
        """Test parsing metrics from nested subdirectories."""
```

### 4.3 Test Fixtures

**Create fixture files in `src/tests/fixtures/metrics/`:**

```
src/tests/fixtures/
├── sample_semantic_model.yml  # Existing
└── metrics/                    # NEW
    ├── simple_metric.yml
    ├── ratio_metric.yml
    ├── derived_metric.yml
    ├── conversion_metric.yml
    └── nested/
        └── additional_metrics.yml
```

**Example fixture content:**

```yaml
# simple_metric.yml
metrics:
  - name: total_revenue
    type: simple
    type_params:
      measure: revenue
    label: Total Revenue
    description: Sum of all revenue
    meta:
      primary_entity: rental

# ratio_metric.yml
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

### 4.4 Coverage Target

- **Overall module coverage:** 95%+
- **Branch coverage:** 95%+
- **All error paths tested:** 100%

---

## 5. Integration Points

### 5.1 With DTL-023 (Metric Schema)

**Dependencies:**

- `Metric` base model
- `SimpleMetricParams`, `RatioMetricParams`, `DerivedMetricParams`, `ConversionMetricParams`
- `MetricReference` helper model

**Import pattern:**

```python
from dbt_to_lookml.schemas import (
    Metric,
    SimpleMetricParams,
    RatioMetricParams,
    DerivedMetricParams,
    ConversionMetricParams,
    MetricReference,
)
```

### 5.2 With Existing Parser Infrastructure

**Inherit from base Parser:**

```python
from dbt_to_lookml.interfaces.parser import Parser

class DbtMetricParser(Parser):
    """Extends Parser base class."""
```

**Reuse utilities:**

- `self.read_yaml(path)` - YAML file reading
- `self.handle_error(error, context)` - Error handling
- `self.strict_mode` - Validation mode flag

### 5.3 With Future Components

**Blocks:**

- **DTL-025** (Cross-entity measure generation): Needs parsed Metric objects
- **DTL-027** (Entity connectivity validation): Needs parsed metrics and dependency extraction

**Export pattern:**

```python
# src/dbt_to_lookml/parsers/__init__.py
from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.parsers.dbt_metrics import DbtMetricParser

__all__ = ["DbtParser", "DbtMetricParser"]
```

---

## 6. Implementation Checklist

### Phase 1: Core Parser (Must Have)

- [ ] Create `src/dbt_to_lookml/parsers/dbt_metrics.py`
- [ ] Implement `DbtMetricParser` class extending `Parser`
- [ ] Implement `parse_file()` method
- [ ] Implement `parse_directory()` with recursion
- [ ] Implement `validate()` method
- [ ] Implement `_parse_metric()` internal method
- [ ] Implement `_parse_type_params()` for all metric types
- [ ] Implement `_validate_metric_structure()` helper
- [ ] Export `DbtMetricParser` from `parsers/__init__.py`

### Phase 2: Utility Functions (Must Have)

- [ ] Implement `resolve_primary_entity()` function
- [ ] Implement `extract_measure_dependencies()` function
- [ ] Implement `find_measure_model()` helper
- [ ] Add comprehensive docstrings with examples

### Phase 3: Error Handling (Must Have)

- [ ] Add error handling for file not found
- [ ] Add error handling for invalid YAML
- [ ] Add error handling for missing required fields
- [ ] Add error handling for unknown metric type
- [ ] Add error handling for invalid type params
- [ ] Add clear error messages with context

### Phase 4: Testing (Must Have)

- [ ] Create `src/tests/unit/test_dbt_metric_parser.py`
- [ ] Write unit tests for all public methods
- [ ] Write unit tests for primary entity resolution
- [ ] Write unit tests for dependency extraction
- [ ] Write unit tests for error cases
- [ ] Create metric YAML fixtures
- [ ] Write integration tests
- [ ] Achieve 95%+ branch coverage

### Phase 5: Documentation (Should Have)

- [ ] Add module-level docstring
- [ ] Add class docstring with examples
- [ ] Add method docstrings with Args/Returns/Raises
- [ ] Add inline comments for complex logic
- [ ] Update CLAUDE.md if needed

---

## 7. Acceptance Criteria Validation

| Criterion | Implementation Approach | Validation Method |
|-----------|------------------------|-------------------|
| `DbtMetricParser` extends `Parser` | Class definition with `(Parser)` inheritance | Mypy type checking |
| `parse_file()` successfully parses single metric YAML | Implementation with YAML reading and Pydantic validation | Unit tests with fixtures |
| `parse_directory()` recursively scans and parses all metric files | Glob pattern matching with recursion | Integration tests with nested dirs |
| `resolve_primary_entity()` handles explicit and inferred cases | Three-tier priority logic | Unit tests covering all branches |
| `extract_measure_dependencies()` finds all measure references | Type-specific extraction logic | Unit tests for each metric type |
| Error handling provides clear, actionable messages | Custom error messages with context | Error handling unit tests |
| Validation integrates with semantic models | `resolve_primary_entity()` and `find_measure_model()` | Integration tests with both parsers |
| Parser handles all metric types | `_parse_type_params()` switch statement | Unit test per type |

---

## 8. Risk Analysis

### High Risk Items

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **DTL-023 schema changes** | Parser code breaks if Metric schema changes | Use strict type hints, comprehensive tests |
| **Complex nested YAML structures** | Parser fails on edge cases | Test multiple YAML formats, validate early |
| **Primary entity inference errors** | Incorrect entity assignment | Extensive unit tests, clear error messages |

### Medium Risk Items

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Performance on large directories** | Slow parsing for 100+ files | Profile if needed, consider lazy loading |
| **Circular metric dependencies** | Derived metrics referencing each other | Document as future enhancement, validate in DTL-027 |

### Low Risk Items

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Unknown metric types in future** | Parser rejects new types | Clear error message, easy to extend |
| **Missing semantic model during validation** | Can't resolve primary entity | Validation is optional, can defer to generation phase |

---

## 9. Success Metrics

### Functional Metrics

- [ ] Parser successfully reads all 4 metric types (simple, ratio, derived, conversion)
- [ ] Primary entity resolution works for explicit, inferred, and error cases
- [ ] Dependency extraction returns correct measures for all types
- [ ] Directory scanning handles nested directories and both `.yml` and `.yaml`
- [ ] Error messages are clear and actionable for all error categories

### Quality Metrics

- [ ] 95%+ branch coverage on all new code
- [ ] 100% mypy strict type checking compliance
- [ ] All tests pass in CI/CD pipeline
- [ ] No performance regression (parsing should be fast)

### Integration Metrics

- [ ] Parsed metrics integrate cleanly with DTL-025 (generator)
- [ ] Utility functions work with semantic models from DbtParser
- [ ] API follows same patterns as DbtParser

---

## 10. Follow-up Tasks

### Immediate (This Issue)

1. Implement `DbtMetricParser` class
2. Implement utility functions
3. Write comprehensive tests
4. Achieve 95%+ coverage

### Future (Other Issues)

1. **DTL-025**: Use parsed Metric objects in LookML generator
2. **DTL-027**: Validate metric connectivity using dependency extraction
3. **CLI Integration**: Add `--metrics-dir` flag to CLI
4. **Documentation**: Add examples to CLAUDE.md

---

## 11. Implementation Notes

### Code Style

- Follow existing patterns from `DbtParser`
- Use Google-style docstrings
- Type hints on all functions (mypy --strict)
- 88 character line length (Black-compatible)

### Testing Best Practices

- Use `TemporaryDirectory` for file I/O tests
- Mock external dependencies where appropriate
- Follow arrange-act-assert pattern
- Clear test names describing what is tested

### Performance Considerations

- YAML parsing is fast enough for typical metric counts (< 100 files)
- No caching needed at this stage
- Profile if performance issues arise

---

## Appendix A: Example Usage

```python
from pathlib import Path
from dbt_to_lookml.parsers.dbt_metrics import DbtMetricParser, resolve_primary_entity
from dbt_to_lookml.parsers.dbt import DbtParser

# Parse semantic models
sem_parser = DbtParser()
semantic_models = sem_parser.parse_directory(Path("semantic_models/"))

# Parse metrics
metric_parser = DbtMetricParser(strict_mode=True)
metrics = metric_parser.parse_directory(Path("metrics/"))

# Resolve primary entities
for metric in metrics:
    try:
        primary_entity = resolve_primary_entity(metric, semantic_models)
        print(f"Metric {metric.name} → Primary Entity: {primary_entity}")
    except ValueError as e:
        print(f"Error: {e}")
```

---

## Appendix B: YAML Format Examples

**See DTL-024 issue notes for detailed examples.**

---

**Strategy Status:** Ready for Implementation
**Next Step:** Begin Phase 1 - Core Parser Implementation
**Estimated Effort:** 3-5 days for implementation + testing
