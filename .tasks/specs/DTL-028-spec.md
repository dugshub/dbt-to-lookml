# Implementation Spec: DTL-028 - Add comprehensive tests for cross-entity metrics

**Issue ID**: DTL-028
**Type**: Testing
**Priority**: Medium
**Status**: Ready
**Created**: 2025-11-18
**Spec Version**: 1.0

## Overview

This spec provides detailed implementation guidance for comprehensive testing of the cross-entity metrics feature. The testing framework will cover unit tests for all components (schemas, parser, generator, validation), integration tests for end-to-end workflows, and golden tests for regression protection. The goal is to achieve 95%+ overall coverage and 100% coverage for all new metric-related code.

## Goals

1. **Comprehensive Coverage**: Test all metric types (simple, ratio, derived, conversion) and all validation scenarios
2. **Quality Assurance**: Achieve 95%+ overall coverage, 100% coverage for new metric code
3. **Regression Protection**: Golden tests ensure output stability across changes
4. **Developer Experience**: Clear test organization with helpful error messages
5. **Maintainability**: Follow existing test patterns and conventions

## Architecture Context

### Current Test Structure

The project follows a well-organized test structure:

```
src/tests/
├── unit/                          # Fast, isolated component tests
│   ├── test_dbt_parser.py        # Parser validation patterns
│   ├── test_lookml_generator.py  # Generator patterns
│   └── test_schemas.py           # Pydantic model validation
├── integration/                   # End-to-end workflows
│   ├── test_end_to_end.py        # Full generation pipeline
│   ├── test_hierarchy_integration.py
│   └── test_join_field_exposure.py
├── test_golden.py                 # Golden file comparisons
├── golden/                        # Expected output files
│   ├── expected_users.view.lkml
│   └── expected_explores.lkml
└── fixtures/                      # Test data
    └── sample_semantic_model.yml
```

### Testing Patterns to Follow

1. **Unit Tests**: Use pytest fixtures, arrange-act-assert pattern, comprehensive edge case coverage
2. **Integration Tests**: Use TemporaryDirectory, test full workflows, validate output structure
3. **Golden Tests**: Byte-for-byte comparison with helper method `_assert_content_matches`
4. **Fixtures**: Shared YAML files in `fixtures/` directory, reusable across tests
5. **Test Organization**: Group by functionality with descriptive class and method names

## Detailed Implementation Tasks

### Phase 1: Test Fixtures Setup (Priority: Critical)

#### Task 1.1: Create Fixture Directory Structure

**What**: Set up directory structure for metric test fixtures

**Location**:
- `src/tests/fixtures/semantic_models/` (for semantic model YAML files)
- `src/tests/fixtures/metrics/` (for metric YAML files)

**Action**:
```bash
mkdir -p src/tests/fixtures/semantic_models
mkdir -p src/tests/fixtures/metrics
```

**Acceptance Criteria**:
- [ ] Directories created and committed to git
- [ ] README.md in each directory explaining fixture purpose

#### Task 1.2: Create Semantic Model Fixtures

**What**: Create reusable semantic model YAML files for metric testing

**Files to Create**:

**File 1**: `src/tests/fixtures/semantic_models/sem_rental_orders.yml`
```yaml
semantic_models:
  - name: rental_orders
    model: ref('fct_rental_orders')
    description: "Rental order fact table"

    entities:
      - name: rental_sk
        type: primary
        expr: rental_id
        description: "Primary key for rentals"

      - name: user_sk
        type: foreign
        expr: user_id
        description: "Foreign key to users"

    dimensions:
      - name: rental_date
        type: time
        expr: rental_date
        type_params:
          time_granularity: day
        description: "Date when rental was created"

      - name: rental_status
        type: categorical
        expr: status
        description: "Current status of rental"

    measures:
      - name: rental_count
        agg: count
        description: "Total number of rentals"

      - name: total_revenue
        agg: sum
        expr: revenue_amount
        description: "Total rental revenue"

      - name: avg_rental_value
        agg: average
        expr: revenue_amount
        description: "Average revenue per rental"
```

**File 2**: `src/tests/fixtures/semantic_models/sem_searches.yml`
```yaml
semantic_models:
  - name: searches
    model: ref('fct_searches')
    description: "Search fact table"

    entities:
      - name: search_sk
        type: primary
        expr: search_id
        description: "Primary key for searches"

      - name: user_sk
        type: foreign
        expr: user_id
        description: "Foreign key to users"

    dimensions:
      - name: search_date
        type: time
        expr: search_date
        type_params:
          time_granularity: day
        description: "Date when search was performed"

      - name: search_term
        type: categorical
        expr: search_term
        description: "Search query text"

    measures:
      - name: search_count
        agg: count
        description: "Total number of searches"

      - name: unique_searchers
        agg: count_distinct
        expr: user_id
        description: "Number of unique users who searched"
```

**File 3**: `src/tests/fixtures/semantic_models/sem_users.yml`
```yaml
semantic_models:
  - name: users
    model: ref('dim_users')
    description: "User dimension table"

    entities:
      - name: user_sk
        type: primary
        expr: user_id
        description: "Primary key for users"

    dimensions:
      - name: user_status
        type: categorical
        expr: status
        description: "Current user status"

      - name: signup_date
        type: time
        expr: created_at
        type_params:
          time_granularity: day
        description: "Date when user signed up"

    measures:
      - name: user_count
        agg: count
        description: "Total number of users"
```

**Acceptance Criteria**:
- [ ] All three semantic model files created with valid YAML structure
- [ ] Files parse successfully with DbtParser
- [ ] Each model has at least one entity, dimension, and measure
- [ ] Foreign key relationships properly defined (user_sk in searches/rentals)

#### Task 1.3: Create Metric Fixtures

**What**: Create metric YAML files covering all metric types

**Files to Create**:

**File 1**: `src/tests/fixtures/metrics/search_conversion.yml`
```yaml
metrics:
  - name: search_conversion_rate
    type: ratio
    description: "Percentage of searches that convert to rentals"
    label: "Search Conversion Rate"
    type_params:
      numerator: rental_count
      denominator: search_count
    config:
      meta:
        primary_entity: search
        category: "Conversion Metrics"
```

**File 2**: `src/tests/fixtures/metrics/revenue_per_user.yml`
```yaml
metrics:
  - name: revenue_per_user
    type: ratio
    description: "Average revenue per user"
    label: "Revenue Per User"
    type_params:
      numerator: total_revenue
      denominator: user_count
    config:
      meta:
        primary_entity: user
        category: "Financial Metrics"
```

**File 3**: `src/tests/fixtures/metrics/engagement_score.yml`
```yaml
metrics:
  - name: engagement_score
    type: derived
    description: "Combined engagement metric across searches and rentals"
    label: "User Engagement Score"
    type_params:
      expr: "(search_count + rental_count) / user_count"
      metrics:
        - name: search_count
        - name: rental_count
        - name: user_count
    config:
      meta:
        primary_entity: user
        category: "Engagement Metrics"
```

**File 4**: `src/tests/fixtures/metrics/total_revenue.yml`
```yaml
metrics:
  - name: total_revenue_metric
    type: simple
    description: "Total revenue as a metric"
    label: "Total Revenue"
    type_params:
      measure: total_revenue
    config:
      meta:
        primary_entity: rental
        category: "Financial Metrics"
```

**File 5**: `src/tests/fixtures/metrics/invalid_unreachable.yml` (for error testing)
```yaml
metrics:
  - name: invalid_metric
    type: ratio
    description: "Metric with unreachable measure"
    type_params:
      numerator: nonexistent_measure
      denominator: search_count
    config:
      meta:
        primary_entity: search
```

**File 6**: `src/tests/fixtures/metrics/missing_primary_entity.yml` (for error testing)
```yaml
metrics:
  - name: ambiguous_metric
    type: ratio
    description: "Metric without primary entity"
    type_params:
      numerator: rental_count
      denominator: search_count
    # No config.meta.primary_entity - should error
```

**Acceptance Criteria**:
- [ ] All metric files created with valid YAML structure
- [ ] Files parse successfully with DbtMetricParser
- [ ] All metric types represented (simple, ratio, derived)
- [ ] Error fixtures cause expected validation failures

### Phase 2: Unit Tests (Priority: Critical)

#### Task 2.1: Metric Schema Tests

**What**: Test Pydantic models for metrics

**File**: `src/tests/unit/test_metric_schemas.py`

**Implementation Details**:

```python
"""Unit tests for Metric schema models."""

import pytest
from pydantic import ValidationError

from dbt_to_lookml.schemas import (
    Metric,
    SimpleMetricParams,
    RatioMetricParams,
    DerivedMetricParams,
    ConversionMetricParams,
    MetricReference,
)


class TestMetricBase:
    """Test base Metric model."""

    def test_simple_metric_creation(self) -> None:
        """Test creating a simple metric with valid params."""
        metric = Metric(
            name="total_revenue",
            type="simple",
            description="Total revenue",
            type_params=SimpleMetricParams(measure="revenue_amount"),
        )

        assert metric.name == "total_revenue"
        assert metric.type == "simple"
        assert isinstance(metric.type_params, SimpleMetricParams)
        assert metric.type_params.measure == "revenue_amount"

    def test_ratio_metric_creation(self) -> None:
        """Test creating a ratio metric with valid params."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            description="Conversion rate",
            type_params=RatioMetricParams(
                numerator="rental_count",
                denominator="search_count",
            ),
        )

        assert metric.name == "conversion_rate"
        assert metric.type == "ratio"
        assert metric.type_params.numerator == "rental_count"
        assert metric.type_params.denominator == "search_count"

    def test_derived_metric_creation(self) -> None:
        """Test creating a derived metric with valid params."""
        metric = Metric(
            name="engagement_score",
            type="derived",
            description="Engagement score",
            type_params=DerivedMetricParams(
                expr="(a + b) / c",
                metrics=[
                    MetricReference(name="search_count"),
                    MetricReference(name="rental_count"),
                    MetricReference(name="user_count"),
                ],
            ),
        )

        assert metric.name == "engagement_score"
        assert metric.type == "derived"
        assert metric.type_params.expr == "(a + b) / c"
        assert len(metric.type_params.metrics) == 3

    def test_conversion_metric_creation(self) -> None:
        """Test creating a conversion metric with valid params."""
        metric = Metric(
            name="search_to_rental",
            type="conversion",
            description="Search to rental conversion",
            type_params=ConversionMetricParams(
                conversion_type_params={
                    "entity": "user",
                    "base_event": "search",
                    "conversion_event": "rental",
                }
            ),
        )

        assert metric.name == "search_to_rental"
        assert metric.type == "conversion"

    def test_primary_entity_extraction_from_meta(self) -> None:
        """Test primary_entity property extracts from config.meta block."""
        metric = Metric(
            name="test_metric",
            type="simple",
            type_params=SimpleMetricParams(measure="test"),
            config={"meta": {"primary_entity": "user"}},
        )

        assert metric.primary_entity == "user"

    def test_primary_entity_none_when_missing(self) -> None:
        """Test primary_entity returns None when not in config.meta."""
        metric = Metric(
            name="test_metric",
            type="simple",
            type_params=SimpleMetricParams(measure="test"),
        )

        assert metric.primary_entity is None

    def test_metric_validation_missing_name(self) -> None:
        """Test validation error when name is missing."""
        with pytest.raises(ValidationError) as exc_info:
            Metric(
                type="simple",
                type_params=SimpleMetricParams(measure="test"),
            )

        assert "name" in str(exc_info.value)

    def test_metric_validation_invalid_type(self) -> None:
        """Test validation error for invalid metric type."""
        with pytest.raises(ValidationError) as exc_info:
            Metric(
                name="test",
                type="invalid_type",
                type_params=SimpleMetricParams(measure="test"),
            )

        assert "type" in str(exc_info.value)


class TestSimpleMetricParams:
    """Test SimpleMetricParams model."""

    def test_valid_simple_params(self) -> None:
        """Test valid simple metric params."""
        params = SimpleMetricParams(measure="revenue_amount")
        assert params.measure == "revenue_amount"

    def test_missing_measure_field(self) -> None:
        """Test validation error when measure is missing."""
        with pytest.raises(ValidationError) as exc_info:
            SimpleMetricParams()

        assert "measure" in str(exc_info.value)


class TestRatioMetricParams:
    """Test RatioMetricParams model."""

    def test_valid_ratio_params(self) -> None:
        """Test valid ratio metric params."""
        params = RatioMetricParams(
            numerator="rental_count",
            denominator="search_count",
        )
        assert params.numerator == "rental_count"
        assert params.denominator == "search_count"

    def test_missing_numerator(self) -> None:
        """Test validation error when numerator is missing."""
        with pytest.raises(ValidationError) as exc_info:
            RatioMetricParams(denominator="search_count")

        assert "numerator" in str(exc_info.value)

    def test_missing_denominator(self) -> None:
        """Test validation error when denominator is missing."""
        with pytest.raises(ValidationError) as exc_info:
            RatioMetricParams(numerator="rental_count")

        assert "denominator" in str(exc_info.value)


class TestDerivedMetricParams:
    """Test DerivedMetricParams model."""

    def test_valid_derived_params(self) -> None:
        """Test valid derived metric params."""
        params = DerivedMetricParams(
            expr="a + b",
            metrics=[
                MetricReference(name="metric_a"),
                MetricReference(name="metric_b"),
            ],
        )
        assert params.expr == "a + b"
        assert len(params.metrics) == 2

    def test_missing_expr(self) -> None:
        """Test validation error when expr is missing."""
        with pytest.raises(ValidationError) as exc_info:
            DerivedMetricParams(
                metrics=[MetricReference(name="test")]
            )

        assert "expr" in str(exc_info.value)

    def test_missing_metrics(self) -> None:
        """Test validation error when metrics list is missing."""
        with pytest.raises(ValidationError) as exc_info:
            DerivedMetricParams(expr="a + b")

        assert "metrics" in str(exc_info.value)

    def test_empty_metrics_list(self) -> None:
        """Test validation error for empty metrics list."""
        with pytest.raises(ValidationError) as exc_info:
            DerivedMetricParams(expr="a + b", metrics=[])

        assert "metrics" in str(exc_info.value)


class TestMetricReference:
    """Test MetricReference model."""

    def test_basic_metric_reference(self) -> None:
        """Test creating basic metric reference with name only."""
        ref = MetricReference(name="search_count")
        assert ref.name == "search_count"
        assert ref.alias is None
        assert ref.offset_window is None

    def test_metric_reference_with_alias(self) -> None:
        """Test metric reference with alias."""
        ref = MetricReference(name="search_count", alias="searches")
        assert ref.name == "search_count"
        assert ref.alias == "searches"

    def test_metric_reference_with_offset_window(self) -> None:
        """Test metric reference with offset window."""
        ref = MetricReference(
            name="search_count",
            offset_window="7 days",
        )
        assert ref.name == "search_count"
        assert ref.offset_window == "7 days"
```

**Test Count**: 22 test methods

**Acceptance Criteria**:
- [ ] All test methods implemented
- [ ] Tests pass with valid data
- [ ] Validation errors properly tested
- [ ] 100% coverage of Metric schema classes

#### Task 2.2: Metric Parser Tests

**What**: Test DbtMetricParser for parsing metric YAML files

**File**: `src/tests/unit/test_dbt_metric_parser.py`

**Implementation Pattern**: Follow pattern from `test_dbt_parser.py`

**Key Test Cases**:

```python
"""Unit tests for DbtMetricParser."""

import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
import yaml

from dbt_to_lookml.parsers.dbt_metrics import DbtMetricParser
from dbt_to_lookml.schemas import Metric


class TestDbtMetricParser:
    """Test cases for DbtMetricParser."""

    @pytest.fixture
    def parser(self) -> DbtMetricParser:
        """Create a DbtMetricParser instance."""
        return DbtMetricParser()

    def test_parse_empty_file(self, parser: DbtMetricParser) -> None:
        """Test parsing an empty YAML file."""
        with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("")
            f.flush()

            result = parser.parse_file(Path(f.name))
            assert result == []

    def test_parse_single_simple_metric(self, parser: DbtMetricParser) -> None:
        """Test parsing a file with a single simple metric."""
        metric_yaml = """
metrics:
  - name: total_revenue
    type: simple
    description: "Total revenue"
    type_params:
      measure: revenue_amount
"""
        with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(metric_yaml)
            f.flush()

            result = parser.parse_file(Path(f.name))
            assert len(result) == 1
            assert result[0].name == "total_revenue"
            assert result[0].type == "simple"

    def test_parse_single_ratio_metric(self, parser: DbtMetricParser) -> None:
        """Test parsing a file with a single ratio metric."""
        metric_yaml = """
metrics:
  - name: conversion_rate
    type: ratio
    type_params:
      numerator: rental_count
      denominator: search_count
    config:
      meta:
        primary_entity: search
"""
        with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(metric_yaml)
            f.flush()

            result = parser.parse_file(Path(f.name))
            assert len(result) == 1
            assert result[0].name == "conversion_rate"
            assert result[0].type == "ratio"
            assert result[0].primary_entity == "search"

    def test_parse_directory(self, parser: DbtMetricParser) -> None:
        """Test parsing multiple files from a directory."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create multiple metric files
            (tmpdir_path / "metric1.yml").write_text("""
metrics:
  - name: metric1
    type: simple
    type_params:
      measure: measure1
""")
            (tmpdir_path / "metric2.yml").write_text("""
metrics:
  - name: metric2
    type: ratio
    type_params:
      numerator: num
      denominator: denom
""")

            result = parser.parse_directory(tmpdir_path)
            assert len(result) >= 2
            metric_names = [m.name for m in result]
            assert "metric1" in metric_names
            assert "metric2" in metric_names

    def test_parse_nonexistent_file(self, parser: DbtMetricParser) -> None:
        """Test parsing a file that doesn't exist raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parser.parse_file(Path("/nonexistent/file.yml"))

    def test_strict_mode_validation_error(self) -> None:
        """Test that strict mode raises validation errors."""
        parser = DbtMetricParser(strict_mode=True)

        invalid_yaml = """
metrics:
  - name: invalid
    type: invalid_type
"""
        with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(invalid_yaml)
            f.flush()

            with pytest.raises(Exception):  # ValidationError or similar
                parser.parse_file(Path(f.name))

    def test_parse_invalid_yaml(self, parser: DbtMetricParser) -> None:
        """Test parsing invalid YAML files."""
        invalid_yaml = "metrics:\n  - invalid: yaml: syntax:"

        with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(invalid_yaml)
            f.flush()

            with pytest.raises(Exception):  # YAML parsing error
                parser.parse_file(Path(f.name))

    def test_primary_entity_extraction_explicit(self, parser: DbtMetricParser) -> None:
        """Test primary entity extraction when explicitly defined."""
        metric_yaml = """
metrics:
  - name: test_metric
    type: ratio
    type_params:
      numerator: a
      denominator: b
    config:
      meta:
        primary_entity: user
"""
        with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(metric_yaml)
            f.flush()

            result = parser.parse_file(Path(f.name))
            assert result[0].primary_entity == "user"

    def test_dependency_extraction_simple_metric(self, parser: DbtMetricParser) -> None:
        """Test measure dependency extraction for simple metric."""
        metric_yaml = """
metrics:
  - name: simple_metric
    type: simple
    type_params:
      measure: revenue_amount
"""
        with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(metric_yaml)
            f.flush()

            result = parser.parse_file(Path(f.name))
            # Verify that parser correctly identifies dependencies
            assert result[0].type_params.measure == "revenue_amount"

    def test_dependency_extraction_ratio_metric(self, parser: DbtMetricParser) -> None:
        """Test measure dependency extraction for ratio metric."""
        metric_yaml = """
metrics:
  - name: ratio_metric
    type: ratio
    type_params:
      numerator: measure_a
      denominator: measure_b
"""
        with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(metric_yaml)
            f.flush()

            result = parser.parse_file(Path(f.name))
            assert result[0].type_params.numerator == "measure_a"
            assert result[0].type_params.denominator == "measure_b"
```

**Test Count**: 25+ test methods

**Acceptance Criteria**:
- [ ] All parsing scenarios tested (empty file, single metric, multiple metrics)
- [ ] All metric types covered (simple, ratio, derived, conversion)
- [ ] Error handling tested (invalid YAML, missing fields, validation errors)
- [ ] Directory parsing tested (nested directories, multiple files)
- [ ] 100% coverage of DbtMetricParser code

#### Task 2.3: Measure Generation Tests

**What**: Test cross-entity measure generation in LookMLGenerator

**File**: Additions to `src/tests/unit/test_lookml_generator.py`

**New Test Classes**:

```python
class TestCrossEntityMeasureGeneration:
    """Test _generate_metric_measure method."""

    @pytest.fixture
    def generator(self) -> LookMLGenerator:
        """Create a LookMLGenerator instance."""
        return LookMLGenerator()

    @pytest.fixture
    def semantic_models(self) -> list:
        """Create sample semantic models for testing."""
        # Return list of SemanticModel instances
        # Include: searches, rental_orders, users
        pass

    def test_generate_simple_metric_measure(
        self, generator: LookMLGenerator, semantic_models: list
    ) -> None:
        """Test generating measure from simple metric."""
        metric = Metric(
            name="total_revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="revenue_amount"),
            config={"meta": {"primary_entity": "rental"}},
        )

        measure_dict = generator._generate_metric_measure(
            metric, semantic_models[0], semantic_models
        )

        assert measure_dict["name"] == "total_revenue"
        assert measure_dict["type"] == "number"
        assert "sql" in measure_dict

    def test_generate_ratio_metric_measure(
        self, generator: LookMLGenerator, semantic_models: list
    ) -> None:
        """Test generating measure from ratio metric."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="rental_count",
                denominator="search_count",
            ),
            config={"meta": {"primary_entity": "search"}},
        )

        measure_dict = generator._generate_metric_measure(
            metric, semantic_models[0], semantic_models
        )

        assert "1.0 *" in measure_dict["sql"]
        assert "NULLIF" in measure_dict["sql"]
        assert measure_dict["value_format_name"] == "percent_2"

    def test_measure_metadata_labels(
        self, generator: LookMLGenerator, semantic_models: list
    ) -> None:
        """Test that generated measures have correct labels."""
        metric = Metric(
            name="test_metric",
            type="simple",
            label="Test Metric Label",
            type_params=SimpleMetricParams(measure="test"),
            config={"meta": {"primary_entity": "test"}},
        )

        measure_dict = generator._generate_metric_measure(
            metric, semantic_models[0], semantic_models
        )

        assert measure_dict.get("label") == "Test Metric Label"

    def test_measure_value_format_ratio(
        self, generator: LookMLGenerator, semantic_models: list
    ) -> None:
        """Test value_format_name for ratio metrics (percent)."""
        metric = Metric(
            name="rate_metric",
            type="ratio",
            type_params=RatioMetricParams(numerator="a", denominator="b"),
            config={"meta": {"primary_entity": "test"}},
        )

        measure_dict = generator._generate_metric_measure(
            metric, semantic_models[0], semantic_models
        )

        assert measure_dict["value_format_name"] == "percent_2"


class TestSQLGeneration:
    """Test SQL generation for different metric types."""

    @pytest.fixture
    def generator(self) -> LookMLGenerator:
        """Create a LookMLGenerator instance."""
        return LookMLGenerator()

    def test_ratio_sql_generation_basic(self, generator: LookMLGenerator) -> None:
        """Test basic ratio SQL: numerator / denominator."""
        metric = Metric(
            name="ratio",
            type="ratio",
            type_params=RatioMetricParams(numerator="a", denominator="b"),
        )

        sql = generator._generate_ratio_sql(metric, models)

        assert "1.0 *" in sql
        assert "/" in sql
        assert "NULLIF" in sql

    def test_ratio_sql_generation_cross_view(self, generator: LookMLGenerator) -> None:
        """Test ratio SQL with ${view.measure} syntax."""
        # Test that cross-view references use proper LookML syntax
        pass

    def test_derived_sql_generation(self, generator: LookMLGenerator) -> None:
        """Test derived metric SQL expression evaluation."""
        metric = Metric(
            name="derived",
            type="derived",
            type_params=DerivedMetricParams(
                expr="(a + b) / c",
                metrics=[
                    MetricReference(name="metric_a"),
                    MetricReference(name="metric_b"),
                    MetricReference(name="metric_c"),
                ],
            ),
        )

        sql = generator._generate_derived_sql(metric, models)

        assert "+" in sql
        assert "/" in sql


class TestRequiredFieldsExtraction:
    """Test _extract_required_fields method."""

    @pytest.fixture
    def generator(self) -> LookMLGenerator:
        """Create a LookMLGenerator instance."""
        return LookMLGenerator()

    def test_required_fields_same_view_excluded(
        self, generator: LookMLGenerator
    ) -> None:
        """Test that measures from same view are not in required_fields."""
        # Ratio metric where numerator is from same view as metric owner
        metric = Metric(
            name="test_ratio",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="same_view_measure",
                denominator="other_view_measure",
            ),
        )

        required = generator._extract_required_fields(metric, owner_model, all_models)

        assert "same_view_measure" not in str(required)
        assert "other_view" in str(required)

    def test_required_fields_cross_view_included(
        self, generator: LookMLGenerator
    ) -> None:
        """Test that cross-view measures are in required_fields."""
        metric = Metric(
            name="cross_view_metric",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="other_model_measure",
                denominator="same_view_measure",
            ),
        )

        required = generator._extract_required_fields(metric, owner_model, all_models)

        assert len(required) == 1
        assert "other_model.other_model_measure" in required

    def test_required_fields_deterministic_ordering(
        self, generator: LookMLGenerator
    ) -> None:
        """Test that required_fields list is sorted deterministically."""
        metric = Metric(
            name="multi_dep",
            type="derived",
            type_params=DerivedMetricParams(
                expr="a + b + c",
                metrics=[
                    MetricReference(name="measure_c"),
                    MetricReference(name="measure_a"),
                    MetricReference(name="measure_b"),
                ],
            ),
        )

        required = generator._extract_required_fields(metric, owner_model, all_models)

        # Verify list is sorted
        assert required == sorted(required)

    def test_required_fields_no_duplicates(
        self, generator: LookMLGenerator
    ) -> None:
        """Test that required_fields contains no duplicates."""
        metric = Metric(
            name="dup_metric",
            type="derived",
            type_params=DerivedMetricParams(
                expr="a + a + a",
                metrics=[
                    MetricReference(name="measure_a"),
                    MetricReference(name="measure_a"),
                    MetricReference(name="measure_a"),
                ],
            ),
        )

        required = generator._extract_required_fields(metric, owner_model, all_models)

        # Verify no duplicates
        assert len(required) == len(set(required))


class TestMetricOwnershipFiltering:
    """Test that only metrics owned by a view are generated."""

    def test_metric_filtered_by_primary_entity(self) -> None:
        """Test that only metrics with matching primary_entity are included."""
        # Create metrics with different primary entities
        # Verify only matching metrics are included in view
        pass

    def test_multiple_metrics_same_primary_entity(self) -> None:
        """Test multiple metrics owned by same entity."""
        # Verify all metrics with same primary_entity appear in view
        pass

    def test_no_metrics_for_view_without_primary_entity(self) -> None:
        """Test views with no owned metrics don't generate metric measures."""
        # Verify no metric measures when no metrics match
        pass
```

**Test Count**: 20+ test methods

**Acceptance Criteria**:
- [ ] All measure generation scenarios tested
- [ ] SQL generation tested for all metric types
- [ ] Required fields extraction tested with edge cases
- [ ] Metric ownership filtering tested
- [ ] 100% coverage of new measure generation code

#### Task 2.4: Explore Enhancement Tests

**What**: Test explore enhancement with metric requirements

**File**: Additions to `src/tests/unit/test_lookml_generator.py`

**New Test Class**:

```python
class TestMetricRequirementIdentification:
    """Test _identify_metric_requirements method."""

    @pytest.fixture
    def generator(self) -> LookMLGenerator:
        """Create a LookMLGenerator instance."""
        return LookMLGenerator()

    def test_no_metrics_returns_empty_dict(self, generator: LookMLGenerator) -> None:
        """Test that no metrics results in empty requirements."""
        base_model = create_semantic_model("base")
        join_models = [create_semantic_model("join1"), create_semantic_model("join2")]
        metrics = []

        requirements = generator._identify_metric_requirements(
            base_model, join_models, metrics
        )

        assert requirements == {}

    def test_single_metric_single_measure(self, generator: LookMLGenerator) -> None:
        """Test metric requiring one measure from one view."""
        # Create metric requiring one measure from join view
        requirements = generator._identify_metric_requirements(
            base_model, join_models, metrics
        )

        assert "join_view" in requirements
        assert "measure_name" in requirements["join_view"]

    def test_multiple_metrics_same_view(self, generator: LookMLGenerator) -> None:
        """Test multiple metrics requiring measures from same view."""
        # Create multiple metrics requiring different measures from same join view
        requirements = generator._identify_metric_requirements(
            base_model, join_models, metrics
        )

        assert len(requirements["join_view"]) == 2

    def test_base_view_measures_excluded(self, generator: LookMLGenerator) -> None:
        """Test that measures from base explore are not in requirements."""
        # Create metric that uses base view measure
        requirements = generator._identify_metric_requirements(
            base_model, join_models, metrics
        )

        assert base_model.name not in requirements


class TestJoinFieldsGeneration:
    """Test join fields parameter with metric requirements."""

    def test_join_fields_no_metrics_dimensions_only(self) -> None:
        """Test join has only dimensions_only* when no metrics."""
        # Generate explore without metrics
        # Verify fields: [view.dimensions_only*]
        pass

    def test_join_fields_with_one_required_measure(self) -> None:
        """Test join fields includes one required measure."""
        # Generate explore with one metric requiring one measure
        # Verify fields includes the measure
        pass

    def test_join_fields_with_multiple_required_measures(self) -> None:
        """Test join fields includes multiple required measures."""
        # Generate explore with metrics requiring multiple measures
        # Verify all measures in fields list
        pass

    def test_join_fields_no_duplicates(self) -> None:
        """Test that fields list contains no duplicates."""
        pass

    def test_join_fields_deterministic_ordering(self) -> None:
        """Test that fields are sorted deterministically."""
        pass
```

**Test Count**: 15+ test methods

**Acceptance Criteria**:
- [ ] Metric requirement identification tested
- [ ] Join fields generation tested with and without metrics
- [ ] Edge cases tested (no metrics, multiple metrics, duplicates)
- [ ] 100% coverage of explore enhancement code

#### Task 2.5: Validation Tests

**What**: Test metric connectivity validation

**File**: `src/tests/unit/test_metric_validation.py`

**Implementation**:

```python
"""Unit tests for metric connectivity validation."""

import pytest

from dbt_to_lookml.validation import (
    build_join_graph,
    validate_metric_connectivity,
    ValidationError,
)
from dbt_to_lookml.schemas import Metric, SemanticModel


class TestJoinGraphBuilding:
    """Test build_join_graph function."""

    def test_build_graph_single_model(self) -> None:
        """Test join graph for isolated model."""
        model = create_semantic_model("isolated")

        graph = build_join_graph([model])

        assert "isolated" in graph
        assert len(graph["isolated"]) == 0  # No connections

    def test_build_graph_direct_relationships(self) -> None:
        """Test join graph with direct foreign key relationships."""
        # Create models with foreign key relationships
        users = create_model_with_entities("users", primary="user_sk")
        orders = create_model_with_entities(
            "orders", primary="order_sk", foreign=["user_sk"]
        )

        graph = build_join_graph([users, orders])

        assert "users" in graph["orders"]
        assert graph["orders"]["users"]["hops"] == 1

    def test_build_graph_multi_hop_relationships(self) -> None:
        """Test join graph with 2-hop joins."""
        # Create 3 models: A -> B -> C
        graph = build_join_graph([model_a, model_b, model_c])

        assert graph["model_c"]["model_a"]["hops"] == 2

    def test_build_graph_max_hops_limit(self) -> None:
        """Test that graph respects max_hops parameter."""
        # Create 4-hop chain
        graph = build_join_graph(models, max_hops=2)

        # Verify only 1-hop and 2-hop connections included
        pass


class TestMetricConnectivityValidation:
    """Test validate_metric_connectivity function."""

    def test_valid_metric_all_measures_reachable(self) -> None:
        """Test validation passes for valid metric."""
        metric = create_ratio_metric(
            numerator_model="orders",
            denominator_model="searches",
            primary_entity="search",
        )

        # Should not raise
        validate_metric_connectivity(metric, search_model, all_models)

    def test_unreachable_measure_raises_error(self) -> None:
        """Test validation error when measure not reachable."""
        metric = create_ratio_metric(
            numerator_model="isolated_model",  # Not connected
            denominator_model="searches",
            primary_entity="search",
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_metric_connectivity(metric, search_model, all_models)

        error_msg = str(exc_info.value)
        assert "not reachable" in error_msg
        assert "isolated_model" in error_msg

    def test_missing_primary_entity_raises_error(self) -> None:
        """Test error when primary_entity doesn't exist."""
        metric = Metric(
            name="test",
            type="ratio",
            type_params=RatioMetricParams(numerator="a", denominator="b"),
            config={"meta": {"primary_entity": "nonexistent"}},
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_metric_connectivity(metric, None, all_models)

        assert "primary_entity" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_error_message_helpful_for_unreachable(self) -> None:
        """Test that error messages include helpful suggestions."""
        with pytest.raises(ValidationError) as exc_info:
            validate_metric_connectivity(metric, primary_model, all_models)

        error_msg = str(exc_info.value)
        assert "Change primary_entity" in error_msg or "add join path" in error_msg
```

**Test Count**: 15+ test methods

**Acceptance Criteria**:
- [ ] Join graph building tested (single model, direct relationships, multi-hop)
- [ ] Validation tested (valid metrics, unreachable measures, missing entities)
- [ ] Error messages tested for helpfulness
- [ ] 100% coverage of validation code

### Phase 3: Integration Tests (Priority: High)

#### Task 3.1: Cross-Entity Metrics Integration Tests

**What**: End-to-end tests from parsing to LookML generation

**File**: `src/tests/integration/test_cross_entity_metrics.py`

**Implementation**:

```python
"""Integration tests for cross-entity metrics end-to-end."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.parsers.dbt_metrics import DbtMetricParser
from dbt_to_lookml.generators.lookml import LookMLGenerator


class TestBasicRatioMetric:
    """Test basic ratio metric generation."""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Return path to test fixtures."""
        return Path(__file__).parent.parent / "fixtures"

    def test_search_conversion_rate_generation(self, fixtures_dir: Path) -> None:
        """Test generating search conversion rate metric.

        Workflow:
        1. Parse semantic models (searches, rental_orders)
        2. Parse metric (search_conversion_rate)
        3. Generate LookML
        4. Verify measure in searches.view.lkml
        5. Verify required_fields present
        6. Verify join fields expose rental_count
        """
        # Arrange
        parser = DbtParser()
        metric_parser = DbtMetricParser()

        models = parser.parse_directory(fixtures_dir / "semantic_models")
        metrics = metric_parser.parse_directory(fixtures_dir / "metrics")

        generator = LookMLGenerator()

        # Act
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generated_files, errors = generator.generate_lookml_files(
                models, output_dir, metrics=metrics
            )

            # Assert
            assert len(errors) == 0

            searches_view = (output_dir / "searches.view.lkml").read_text()

            # Verify measure exists
            assert "measure: search_conversion_rate" in searches_view

            # Verify required_fields
            assert "required_fields:" in searches_view
            assert "rental_orders.rental_count" in searches_view

            # Verify SQL
            assert "${rental_orders.rental_count}" in searches_view
            assert "NULLIF(${search_count}, 0)" in searches_view

            # Verify explore
            explores = (output_dir / "explores.lkml").read_text()
            assert "rental_orders.rental_count" in explores

    def test_generated_measure_has_correct_sql(self, fixtures_dir: Path) -> None:
        """Test that generated SQL uses cross-view references."""
        # Similar test verifying SQL structure
        pass

    def test_generated_measure_has_required_fields(self, fixtures_dir: Path) -> None:
        """Test that required_fields parameter is present."""
        pass

    def test_explore_join_exposes_required_measure(self, fixtures_dir: Path) -> None:
        """Test that rental_orders join includes rental_count in fields."""
        pass


class TestMultiEntityDerivedMetric:
    """Test derived metric across multiple entities."""

    def test_engagement_score_generation(self, fixtures_dir: Path) -> None:
        """Test generating engagement score metric.

        Workflow:
        1. Parse semantic models (users, searches, rental_orders)
        2. Parse metric (engagement_score)
        3. Generate LookML
        4. Verify measure in users.view.lkml
        5. Verify required_fields includes both searches and rental_orders
        6. Verify both joins expose required measures
        """
        parser = DbtParser()
        metric_parser = DbtMetricParser()

        models = parser.parse_directory(fixtures_dir / "semantic_models")
        metrics = metric_parser.parse_file(fixtures_dir / "metrics" / "engagement_score.yml")

        generator = LookMLGenerator()

        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generated_files, errors = generator.generate_lookml_files(
                models, output_dir, metrics=metrics
            )

            assert len(errors) == 0

            users_view = (output_dir / "users.view.lkml").read_text()

            # Verify measure exists
            assert "measure: engagement_score" in users_view

            # Verify required_fields includes both models
            assert "searches.search_count" in users_view
            assert "rental_orders.rental_count" in users_view

            # Verify explore has both joins with measures
            explores = (output_dir / "explores.lkml").read_text()
            assert "searches.search_count" in explores
            assert "rental_orders.rental_count" in explores


class TestSimpleMetricCrossView:
    """Test simple metric with cross-view reference."""

    def test_total_revenue_metric_cross_view(self, fixtures_dir: Path) -> None:
        """Test simple metric referencing measure from different view."""
        pass


class TestValidationErrorScenarios:
    """Test validation error handling during generation."""

    def test_unreachable_measure_error(self, fixtures_dir: Path) -> None:
        """Test error when measure not reachable from primary entity."""
        parser = DbtParser()
        metric_parser = DbtMetricParser()

        models = parser.parse_directory(fixtures_dir / "semantic_models")
        metrics = metric_parser.parse_file(
            fixtures_dir / "metrics" / "invalid_unreachable.yml"
        )

        generator = LookMLGenerator()

        with pytest.raises(ValidationError) as exc_info:
            with TemporaryDirectory() as tmpdir:
                generator.generate_lookml_files(models, Path(tmpdir), metrics=metrics)

        assert "not reachable" in str(exc_info.value)

    def test_missing_primary_entity_error(self, fixtures_dir: Path) -> None:
        """Test error when metric missing primary_entity declaration."""
        metrics = metric_parser.parse_file(
            fixtures_dir / "metrics" / "missing_primary_entity.yml"
        )

        with pytest.raises(ValidationError) as exc_info:
            generator.generate_lookml_files(models, Path(tmpdir), metrics=metrics)

        assert "primary_entity" in str(exc_info.value)
```

**Test Count**: 10+ test methods

**Acceptance Criteria**:
- [ ] All integration test scenarios implemented
- [ ] Tests use real fixtures from fixtures/ directory
- [ ] End-to-end workflow tested (parse → generate → validate)
- [ ] Error scenarios tested with expected error messages
- [ ] 95%+ workflow coverage

### Phase 4: Golden Tests (Priority: High)

#### Task 4.1: Create Golden Files

**What**: Create expected output LookML files

**Location**: `src/tests/golden/`

**Files to Create**:

**File 1**: `src/tests/golden/expected_searches_with_metrics.view.lkml`
```lookml
view: searches {
  sql_table_name: fct_searches ;;
  description: "Search fact table"

  dimension: search_sk {
    type: string
    primary_key: yes
    hidden: yes
    sql: ${TABLE}.search_id ;;
    description: "Primary key for searches"
  }

  dimension: user_sk {
    type: string
    hidden: yes
    sql: ${TABLE}.user_id ;;
    description: "Foreign key to users"
  }

  dimension_group: search_date {
    type: time
    timeframes: [date, week, month, quarter, year]
    sql: ${TABLE}.search_date ;;
    convert_tz: no
    description: "Date when search was performed"
  }

  dimension: search_term {
    type: string
    sql: ${TABLE}.search_term ;;
    description: "Search query text"
  }

  measure: search_count {
    type: count
    description: "Total number of searches"
  }

  measure: unique_searchers {
    type: count_distinct
    sql: ${TABLE}.user_id ;;
    description: "Number of unique users who searched"
  }

  # Cross-entity metric
  measure: search_conversion_rate {
    type: number
    label: "Search Conversion Rate"
    description: "Percentage of searches that convert to rentals"
    sql: 1.0 * ${rental_orders.rental_count} / NULLIF(${search_count}, 0) ;;
    required_fields: [rental_orders.rental_count]
    value_format_name: percent_2
    view_label: " Metrics"
    group_label: "Conversion Metrics"
  }

  set: dimensions_only {
    fields: [search_sk, user_sk, search_date_date, search_term]
  }
}
```

**File 2**: `src/tests/golden/expected_users_with_metrics.view.lkml`
```lookml
view: users {
  sql_table_name: dim_users ;;
  description: "User dimension table"

  dimension: user_sk {
    type: string
    primary_key: yes
    hidden: yes
    sql: ${TABLE}.user_id ;;
    description: "Primary key for users"
  }

  dimension: user_status {
    type: string
    sql: ${TABLE}.status ;;
    description: "Current user status"
  }

  dimension_group: signup_date {
    type: time
    timeframes: [date, week, month, quarter, year]
    sql: ${TABLE}.created_at ;;
    convert_tz: no
    description: "Date when user signed up"
  }

  measure: user_count {
    type: count
    description: "Total number of users"
  }

  # Cross-entity metrics
  measure: revenue_per_user {
    type: number
    label: "Revenue Per User"
    description: "Average revenue per user"
    sql: 1.0 * ${rental_orders.total_revenue} / NULLIF(${user_count}, 0) ;;
    required_fields: [rental_orders.total_revenue]
    value_format_name: usd
    view_label: " Metrics"
    group_label: "Financial Metrics"
  }

  measure: engagement_score {
    type: number
    label: "User Engagement Score"
    description: "Combined engagement metric across searches and rentals"
    sql: (${searches.search_count} + ${rental_orders.rental_count}) / NULLIF(${user_count}, 0) ;;
    required_fields: [rental_orders.rental_count, searches.search_count]
    value_format_name: decimal_2
    view_label: " Metrics"
    group_label: "Engagement Metrics"
  }

  set: dimensions_only {
    fields: [user_sk, user_status, signup_date_date]
  }
}
```

**File 3**: `src/tests/golden/expected_explores_with_metrics.lkml`
```lookml
explore: searches {
  join: rental_orders {
    sql_on: ${searches.user_sk} = ${rental_orders.user_sk} ;;
    relationship: one_to_many
    fields: [
      rental_orders.dimensions_only*,
      rental_orders.rental_count
    ]
  }

  join: users {
    sql_on: ${searches.user_sk} = ${users.user_sk} ;;
    relationship: many_to_one
    fields: [users.dimensions_only*]
  }
}

explore: users {
  join: rental_orders {
    sql_on: ${users.user_sk} = ${rental_orders.user_sk} ;;
    relationship: one_to_many
    fields: [
      rental_orders.dimensions_only*,
      rental_orders.rental_count,
      rental_orders.total_revenue
    ]
  }

  join: searches {
    sql_on: ${users.user_sk} = ${searches.user_sk} ;;
    relationship: one_to_many
    fields: [
      searches.dimensions_only*,
      searches.search_count
    ]
  }
}

explore: rental_orders {
  join: users {
    sql_on: ${rental_orders.user_sk} = ${users.user_sk} ;;
    relationship: many_to_one
    fields: [users.dimensions_only*]
  }

  join: searches {
    sql_on: ${rental_orders.user_sk} = ${searches.user_sk} ;;
    relationship: one_to_many
    fields: [searches.dimensions_only*]
  }
}
```

**Acceptance Criteria**:
- [ ] All golden files created with valid LookML syntax
- [ ] Files represent expected output for metric test cases
- [ ] Files include comments indicating cross-entity metrics

#### Task 4.2: Implement Golden Tests

**What**: Add test methods to compare generated output with golden files

**File**: Additions to `src/tests/test_golden.py`

**Implementation**:

```python
class TestGoldenFilesMetrics:
    """Golden file tests for metrics."""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Return path to test fixtures."""
        return Path(__file__).parent / "fixtures"

    def test_searches_with_metrics_matches_golden(
        self, golden_dir: Path, fixtures_dir: Path
    ) -> None:
        """Test searches view with metrics matches golden file."""
        parser = DbtParser()
        metric_parser = DbtMetricParser()

        models = parser.parse_directory(fixtures_dir / "semantic_models")
        metrics = metric_parser.parse_directory(fixtures_dir / "metrics")

        generator = LookMLGenerator()

        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generated_files, errors = generator.generate_lookml_files(
                models, output_dir, metrics=metrics
            )

            assert len(errors) == 0

            expected_content = (
                golden_dir / "expected_searches_with_metrics.view.lkml"
            ).read_text()
            actual_content = (output_dir / "searches.view.lkml").read_text()

            self._assert_content_matches(
                expected_content, actual_content, "searches.view.lkml"
            )

    def test_users_with_metrics_matches_golden(
        self, golden_dir: Path, fixtures_dir: Path
    ) -> None:
        """Test users view with metrics matches golden file."""
        # Similar implementation
        pass

    def test_explores_with_metrics_matches_golden(
        self, golden_dir: Path, fixtures_dir: Path
    ) -> None:
        """Test explores with metric requirements match golden file."""
        # Similar implementation
        pass

    def test_metric_measure_sql_formatting(self) -> None:
        """Test that metric SQL is properly formatted."""
        # Verify SQL formatting consistency
        pass

    def test_metric_required_fields_ordering(self) -> None:
        """Test that required_fields are sorted consistently."""
        # Verify deterministic ordering
        pass
```

**Test Count**: 5+ test methods

**Acceptance Criteria**:
- [ ] Golden tests implemented for all metric scenarios
- [ ] Tests use `_assert_content_matches` helper
- [ ] Tests verify byte-for-byte match with golden files
- [ ] Tests provide clear diff output on failure

## Testing Strategy

### Coverage Targets

- **Overall Project**: 95%+ branch coverage
- **New Metric Code**: 100% coverage
  - `schemas.py` (Metric classes): 100%
  - `parsers/dbt_metrics.py`: 100%
  - `generators/lookml.py` (metric methods): 100%
  - `validation.py`: 100%

### Test Execution Order

1. **Unit Tests First**: Fast feedback loop, highest ROI for coverage
2. **Integration Tests Second**: Validate component integration
3. **Golden Tests Last**: Ensure output stability

### Performance Targets

- Unit tests: < 1 second total execution
- Integration tests: < 5 seconds total execution
- Golden tests: < 3 seconds total execution
- Full test suite: < 10 seconds

### Test Markers

Use pytest markers for selective test execution:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.golden` - Golden tests
- `@pytest.mark.metrics` - All metric-related tests

## Error Handling

### Error Testing Principles

For each error scenario:
1. **Verify exception type**: Ensure correct exception is raised
2. **Check error message**: Verify message is helpful and actionable
3. **Include context**: Error should include metric name, entity names, suggestions

### Key Error Scenarios

1. **Unreachable Measure**: Measure not accessible via join path
2. **Missing Primary Entity**: Metric lacks primary_entity in config.meta
3. **Invalid Primary Entity**: primary_entity references non-existent entity
4. **Missing Measure Reference**: Metric references non-existent measure
5. **Validation Failure**: Invalid metric type or params

## Implementation Checklist

### Phase 1: Fixtures
- [ ] Create `src/tests/fixtures/semantic_models/` directory
- [ ] Create `sem_rental_orders.yml`
- [ ] Create `sem_searches.yml`
- [ ] Create `sem_users.yml`
- [ ] Create `src/tests/fixtures/metrics/` directory
- [ ] Create `search_conversion.yml`
- [ ] Create `revenue_per_user.yml`
- [ ] Create `engagement_score.yml`
- [ ] Create `total_revenue.yml`
- [ ] Create `invalid_unreachable.yml`
- [ ] Create `missing_primary_entity.yml`

### Phase 2: Unit Tests
- [ ] Create `test_metric_schemas.py` (22 tests)
- [ ] Create `test_dbt_metric_parser.py` (25+ tests)
- [ ] Add measure generation tests to `test_lookml_generator.py` (20+ tests)
- [ ] Add explore enhancement tests to `test_lookml_generator.py` (15+ tests)
- [ ] Create `test_metric_validation.py` (15+ tests)
- [ ] Run unit tests: `pytest src/tests/unit/test_metric_*.py -v`
- [ ] Verify 100% coverage of new code

### Phase 3: Integration Tests
- [ ] Create `test_cross_entity_metrics.py`
- [ ] Implement `TestBasicRatioMetric` class (4 tests)
- [ ] Implement `TestMultiEntityDerivedMetric` class (2 tests)
- [ ] Implement `TestSimpleMetricCrossView` class (1 test)
- [ ] Implement `TestValidationErrorScenarios` class (4 tests)
- [ ] Run integration tests: `pytest src/tests/integration/test_cross_entity_metrics.py -v`

### Phase 4: Golden Tests
- [ ] Create `expected_searches_with_metrics.view.lkml`
- [ ] Create `expected_users_with_metrics.view.lkml`
- [ ] Create `expected_explores_with_metrics.lkml`
- [ ] Add `TestGoldenFilesMetrics` class to `test_golden.py` (5+ tests)
- [ ] Run golden tests: `pytest src/tests/test_golden.py::TestGoldenFilesMetrics -v`
- [ ] Verify byte-for-byte match

### Phase 5: Validation
- [ ] Run full test suite: `make test-full`
- [ ] Generate coverage report: `make test-coverage`
- [ ] Verify 95%+ overall coverage
- [ ] Verify 100% coverage for metric code
- [ ] Review HTML coverage report for gaps
- [ ] Add tests for any uncovered branches
- [ ] Update documentation

## Risk Mitigation

### Risk 1: Coverage Target Not Met

**Mitigation**:
- Start with unit tests (highest ROI)
- Use HTML coverage report to identify gaps
- Add edge case tests for uncovered branches
- Prioritize new metric code for 100% coverage

### Risk 2: Golden Tests Fragile

**Mitigation**:
- Use `_assert_content_matches` helper
- Test structural elements, not exact whitespace
- Version golden files in git
- Document update process

### Risk 3: Integration Tests Slow

**Mitigation**:
- Use TemporaryDirectory
- Keep fixtures minimal
- Run unit tests in parallel
- Use pytest markers

### Risk 4: Tests Coupled to Implementation

**Mitigation**:
- Test behavior, not implementation
- Use public API methods
- Mock external dependencies only
- Focus on input/output

## Dependencies

### Blocked By
- DTL-023: Metric schema models
- DTL-024: Metric parser
- DTL-025: Measure generation
- DTL-026: Explore enhancement
- DTL-027: Validation

### Blocks
- None (testing is final step)

## Success Criteria

1. All unit tests passing (95+ total tests)
2. All integration tests passing (10+ scenarios)
3. All golden tests passing (byte-for-byte match)
4. Coverage report shows 95%+ overall
5. Coverage report shows 100% for new metric code
6. All metric types covered in tests
7. All validation scenarios tested
8. All error paths tested with helpful messages
9. Tests follow existing patterns
10. Test names clearly describe what is tested

## Estimated Effort

- **Phase 1 (Fixtures)**: 4 hours
- **Phase 2 (Unit Tests)**: 16 hours
- **Phase 3 (Integration Tests)**: 8 hours
- **Phase 4 (Golden Tests)**: 6 hours
- **Phase 5 (Validation)**: 4 hours
- **Buffer (20%)**: 8 hours

**Total**: 46 hours (~6 days)

## Next Steps

1. Create fixture directory structure
2. Create semantic model fixtures
3. Create metric fixtures
4. Implement unit tests for schemas
5. Implement unit tests for parser
6. Implement unit tests for generator
7. Implement unit tests for validation
8. Implement integration tests
9. Create golden files
10. Implement golden tests
11. Run coverage analysis
12. Fill coverage gaps
13. Update documentation

## Appendix: Test Naming Conventions

**Schema validation**: `test_{model}_validation_{scenario}`
- Example: `test_metric_validation_missing_name`

**Parsing**: `test_parse_{what}_{scenario}`
- Example: `test_parse_single_ratio_metric`

**Generation**: `test_generate_{what}_{scenario}`
- Example: `test_generate_ratio_metric_measure`

**Validation**: `test_{what}_validation_{scenario}`
- Example: `test_connectivity_validation_unreachable_measure`

**Integration**: `test_{workflow}_{scenario}`
- Example: `test_search_conversion_rate_generation`
