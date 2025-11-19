# Implementation Strategy: DTL-028 - Add comprehensive tests for cross-entity metrics

**Issue ID**: DTL-028
**Type**: Testing
**Priority**: Medium
**Status**: Has Strategy
**Created**: 2025-11-18

## Executive Summary

This strategy provides a comprehensive testing framework for cross-entity metrics support, covering unit tests for all new components (schemas, parser, generator, validation), integration tests for end-to-end workflows, and golden tests with expected output files. The testing approach follows existing patterns while achieving 95%+ branch coverage target.

## Goals

1. **Comprehensive Coverage**: Test all metric types (simple, ratio, derived, conversion) and validation scenarios
2. **Quality Assurance**: Achieve 95%+ overall coverage, 100% coverage for new metric code
3. **Regression Protection**: Golden tests ensure output stability across changes
4. **Developer Experience**: Clear test organization and helpful error messages

## Architecture Analysis

### Current Test Structure

The project follows a well-organized test structure:

```
src/tests/
├── unit/                          # Fast, isolated tests
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
│   ├── expected_searches.view.lkml
│   ├── expected_rental_orders.view.lkml
│   └── expected_explores.lkml
└── fixtures/                      # Test data
    └── sample_semantic_model.yml
```

### Testing Patterns Observed

1. **Unit Tests**: Use pytest fixtures, arrange-act-assert pattern, comprehensive edge case coverage
2. **Integration Tests**: Use TemporaryDirectory, test full workflows, validate output structure
3. **Golden Tests**: Byte-for-byte comparison with helper method `_assert_content_matches`
4. **Fixtures**: Shared semantic model YAML files, reusable across tests

## Implementation Plan

### Phase 1: Test Fixtures Setup

**Objective**: Create reusable test data for all testing layers

#### 1.1 Semantic Model Fixtures

Create `src/tests/fixtures/semantic_models/` with comprehensive models:

**File: `sem_rental_orders.yml`**
```yaml
name: rental_orders
model: ref('fct_rental_orders')
description: "Rental order fact table"
entities:
  - name: rental_sk
    type: primary
    expr: rental_id
  - name: user_sk
    type: foreign
    expr: user_id
dimensions:
  - name: rental_date
    type: time
    type_params:
      time_granularity: day
  - name: rental_status
    type: categorical
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
```

**File: `sem_searches.yml`**
```yaml
name: searches
model: ref('fct_searches')
description: "Search fact table"
entities:
  - name: search_sk
    type: primary
    expr: search_id
  - name: user_sk
    type: foreign
    expr: user_id
dimensions:
  - name: search_date
    type: time
    type_params:
      time_granularity: day
  - name: search_term
    type: categorical
measures:
  - name: search_count
    agg: count
    description: "Total number of searches"
  - name: unique_searchers
    agg: count_distinct
    expr: user_id
```

**File: `sem_users.yml`**
```yaml
name: users
model: ref('dim_users')
description: "User dimension table"
entities:
  - name: user_sk
    type: primary
    expr: user_id
dimensions:
  - name: user_status
    type: categorical
  - name: signup_date
    type: time
    type_params:
      time_granularity: day
measures:
  - name: user_count
    agg: count
    description: "Total number of users"
```

#### 1.2 Metric Fixtures

Create `src/tests/fixtures/metrics/` with all metric types:

**File: `search_conversion.yml`**
```yaml
metrics:
  - name: search_conversion_rate
    type: ratio
    description: "Percentage of searches that convert to rentals"
    label: "Search Conversion Rate"
    type_params:
      numerator: rental_count
      denominator: search_count
    meta:
      primary_entity: search
      category: "Conversion Metrics"
```

**File: `revenue_per_user.yml`**
```yaml
metrics:
  - name: revenue_per_user
    type: ratio
    description: "Average revenue per user"
    label: "Revenue Per User"
    type_params:
      numerator: total_revenue
      denominator: user_count
    meta:
      primary_entity: user
      category: "Financial Metrics"
```

**File: `engagement_score.yml`**
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
    meta:
      primary_entity: user
      category: "Engagement Metrics"
```

**File: `total_revenue.yml`**
```yaml
metrics:
  - name: total_revenue_metric
    type: simple
    description: "Total revenue as a metric"
    label: "Total Revenue"
    type_params:
      measure: total_revenue
    meta:
      primary_entity: rental
      category: "Financial Metrics"
```

**File: `invalid_unreachable.yml`** (for error testing)
```yaml
metrics:
  - name: invalid_metric
    type: ratio
    description: "Metric with unreachable measure"
    type_params:
      numerator: nonexistent_measure
      denominator: search_count
    meta:
      primary_entity: search
```

**File: `missing_primary_entity.yml`** (for error testing)
```yaml
metrics:
  - name: ambiguous_metric
    type: ratio
    description: "Metric without primary entity"
    type_params:
      numerator: rental_count
      denominator: search_count
    # No meta.primary_entity - should error
```

### Phase 2: Unit Tests

**Objective**: Test individual components in isolation with 100% coverage of new code

#### 2.1 Metric Schema Tests

**File: `src/tests/unit/test_metric_schemas.py`**

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

    def test_simple_metric_creation(self):
        """Test creating a simple metric."""

    def test_ratio_metric_creation(self):
        """Test creating a ratio metric."""

    def test_derived_metric_creation(self):
        """Test creating a derived metric."""

    def test_conversion_metric_creation(self):
        """Test creating a conversion metric."""

    def test_primary_entity_extraction_from_meta(self):
        """Test primary_entity property extracts from meta block."""

    def test_primary_entity_none_when_missing(self):
        """Test primary_entity returns None when not in meta."""

    def test_metric_validation_missing_name(self):
        """Test validation error when name is missing."""

    def test_metric_validation_invalid_type(self):
        """Test validation error for invalid metric type."""

    def test_metric_type_params_mismatch(self):
        """Test error when type_params doesn't match metric type."""


class TestSimpleMetricParams:
    """Test SimpleMetricParams model."""

    def test_valid_simple_params(self):
        """Test valid simple metric params."""

    def test_missing_measure_field(self):
        """Test validation error when measure is missing."""


class TestRatioMetricParams:
    """Test RatioMetricParams model."""

    def test_valid_ratio_params(self):
        """Test valid ratio metric params."""

    def test_missing_numerator(self):
        """Test validation error when numerator is missing."""

    def test_missing_denominator(self):
        """Test validation error when denominator is missing."""


class TestDerivedMetricParams:
    """Test DerivedMetricParams model."""

    def test_valid_derived_params(self):
        """Test valid derived metric params."""

    def test_missing_expr(self):
        """Test validation error when expr is missing."""

    def test_missing_metrics(self):
        """Test validation error when metrics list is missing."""

    def test_empty_metrics_list(self):
        """Test validation error for empty metrics list."""


class TestMetricReference:
    """Test MetricReference model."""

    def test_basic_metric_reference(self):
        """Test creating basic metric reference with name only."""

    def test_metric_reference_with_alias(self):
        """Test metric reference with alias."""

    def test_metric_reference_with_offset_window(self):
        """Test metric reference with offset window."""
```

**Coverage Target**: 100% of new Metric schema code

#### 2.2 Metric Parser Tests

**File: `src/tests/unit/test_dbt_metric_parser.py`**

Following the pattern from `test_dbt_parser.py`:

```python
"""Unit tests for DbtMetricParser."""

import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
import yaml

from dbt_to_lookml.parsers.dbt_metrics import DbtMetricParser


class TestDbtMetricParser:
    """Test cases for DbtMetricParser."""

    def test_parse_empty_file(self):
        """Test parsing an empty YAML file."""

    def test_parse_single_simple_metric(self):
        """Test parsing a file with a single simple metric."""

    def test_parse_single_ratio_metric(self):
        """Test parsing a file with a single ratio metric."""

    def test_parse_single_derived_metric(self):
        """Test parsing a file with a single derived metric."""

    def test_parse_multiple_metrics_in_list(self):
        """Test parsing a file with multiple metrics."""

    def test_parse_nonexistent_file(self):
        """Test parsing a file that doesn't exist raises FileNotFoundError."""

    def test_strict_mode_validation_error(self):
        """Test that strict mode raises validation errors."""

    def test_non_strict_mode_validation_error(self):
        """Test that non-strict mode handles validation errors gracefully."""

    def test_parse_directory(self):
        """Test parsing multiple files from a directory."""

    def test_parse_nested_directories(self):
        """Test parsing metrics from nested directory structure."""

    def test_parse_empty_directory(self):
        """Test parsing an empty directory."""

    def test_parse_invalid_yaml(self):
        """Test parsing invalid YAML files."""

    def test_parse_unknown_metric_type(self):
        """Test error handling for unknown metric type."""

    def test_primary_entity_extraction_explicit(self):
        """Test primary entity extraction when explicitly defined."""

    def test_primary_entity_inference_from_denominator(self):
        """Test primary entity inference from ratio denominator."""

    def test_primary_entity_missing_error(self):
        """Test error when primary entity cannot be inferred."""

    def test_dependency_extraction_simple_metric(self):
        """Test measure dependency extraction for simple metric."""

    def test_dependency_extraction_ratio_metric(self):
        """Test measure dependency extraction for ratio metric."""

    def test_dependency_extraction_derived_metric(self):
        """Test measure dependency extraction for derived metric."""

    def test_validation_integration_with_semantic_models(self):
        """Test metric validation against semantic models."""

    def test_error_handling_missing_required_fields(self):
        """Test error handling for missing required metric fields."""
```

**Coverage Target**: 100% of DbtMetricParser code

#### 2.3 Measure Generation Tests

**File: `src/tests/unit/test_cross_entity_measure_generation.py`**

```python
"""Unit tests for cross-entity measure generation in LookMLGenerator."""

import pytest
from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.schemas import Metric, SemanticModel


class TestCrossEntityMeasureGeneration:
    """Test _generate_metric_measure method."""

    def test_generate_simple_metric_measure(self):
        """Test generating measure from simple metric."""

    def test_generate_ratio_metric_measure(self):
        """Test generating measure from ratio metric."""

    def test_generate_derived_metric_measure(self):
        """Test generating measure from derived metric."""

    def test_measure_metadata_labels(self):
        """Test that generated measures have correct labels."""

    def test_measure_metadata_descriptions(self):
        """Test that descriptions are preserved."""

    def test_measure_metadata_view_label(self):
        """Test view_label is set correctly for metrics."""

    def test_measure_metadata_group_label(self):
        """Test group_label is set from metric category."""

    def test_measure_value_format_ratio(self):
        """Test value_format_name for ratio metrics (percent)."""

    def test_measure_value_format_derived(self):
        """Test value_format_name for derived metrics."""


class TestSQLGeneration:
    """Test SQL generation for different metric types."""

    def test_ratio_sql_generation_basic(self):
        """Test basic ratio SQL: numerator / denominator."""

    def test_ratio_sql_generation_with_nullif(self):
        """Test ratio SQL includes NULLIF for zero division."""

    def test_ratio_sql_generation_cross_view(self):
        """Test ratio SQL with ${view.measure} syntax."""

    def test_derived_sql_generation(self):
        """Test derived metric SQL expression evaluation."""

    def test_derived_sql_with_multiple_metrics(self):
        """Test derived SQL with multiple metric references."""

    def test_simple_metric_sql_cross_view(self):
        """Test simple metric referencing measure from other view."""

    def test_view_prefix_handling_in_sql(self):
        """Test that view prefixes are applied correctly in SQL."""


class TestRequiredFieldsExtraction:
    """Test _extract_required_fields method."""

    def test_required_fields_same_view_excluded(self):
        """Test that measures from same view are not in required_fields."""

    def test_required_fields_cross_view_included(self):
        """Test that cross-view measures are in required_fields."""

    def test_required_fields_ratio_metric(self):
        """Test required_fields for ratio metric."""

    def test_required_fields_derived_metric(self):
        """Test required_fields for derived metric with multiple measures."""

    def test_required_fields_view_prefix_handling(self):
        """Test that view prefixes are applied in required_fields."""

    def test_required_fields_deterministic_ordering(self):
        """Test that required_fields list is sorted deterministically."""

    def test_required_fields_no_duplicates(self):
        """Test that required_fields contains no duplicates."""


class TestMetricOwnershipFiltering:
    """Test that only metrics owned by a view are generated."""

    def test_metric_filtered_by_primary_entity(self):
        """Test that only metrics with matching primary_entity are included."""

    def test_multiple_metrics_same_primary_entity(self):
        """Test multiple metrics owned by same entity."""

    def test_no_metrics_for_view_without_primary_entity(self):
        """Test views with no owned metrics don't generate metric measures."""
```

**Coverage Target**: 100% of new measure generation code

#### 2.4 Explore Enhancement Tests

**File: `src/tests/unit/test_explore_metric_requirements.py`**

```python
"""Unit tests for explore enhancement with metric requirements."""

import pytest
from dbt_to_lookml.generators.lookml import LookMLGenerator


class TestMetricRequirementIdentification:
    """Test _identify_metric_requirements method."""

    def test_no_metrics_returns_empty_dict(self):
        """Test that no metrics results in empty requirements."""

    def test_single_metric_single_measure(self):
        """Test metric requiring one measure from one view."""

    def test_single_metric_multiple_measures(self):
        """Test metric requiring multiple measures from one view."""

    def test_multiple_metrics_same_view(self):
        """Test multiple metrics requiring measures from same view."""

    def test_multiple_metrics_different_views(self):
        """Test multiple metrics requiring measures from different views."""

    def test_base_view_measures_excluded(self):
        """Test that measures from base explore are not in requirements."""


class TestJoinFieldsGeneration:
    """Test join fields parameter with metric requirements."""

    def test_join_fields_no_metrics_dimensions_only(self):
        """Test join has only dimensions_only* when no metrics."""

    def test_join_fields_with_one_required_measure(self):
        """Test join fields includes one required measure."""

    def test_join_fields_with_multiple_required_measures(self):
        """Test join fields includes multiple required measures."""

    def test_join_fields_no_duplicates(self):
        """Test that fields list contains no duplicates."""

    def test_join_fields_deterministic_ordering(self):
        """Test that fields are sorted deterministically."""

    def test_join_fields_view_prefix_applied(self):
        """Test that view prefix is applied to field references."""

    def test_multi_hop_join_fields(self):
        """Test join fields for multi-hop join scenarios."""
```

**Coverage Target**: 100% of explore enhancement code

#### 2.5 Validation Tests

**File: `src/tests/unit/test_metric_validation.py`**

```python
"""Unit tests for metric connectivity validation."""

import pytest
from dbt_to_lookml.validation import (
    build_join_graph,
    validate_metric_connectivity,
    ValidationError,
)


class TestJoinGraphBuilding:
    """Test build_join_graph function."""

    def test_build_graph_single_model(self):
        """Test join graph for isolated model."""

    def test_build_graph_direct_relationships(self):
        """Test join graph with direct foreign key relationships."""

    def test_build_graph_multi_hop_relationships(self):
        """Test join graph with 2-hop joins."""

    def test_build_graph_max_hops_limit(self):
        """Test that graph respects max_hops parameter."""

    def test_build_graph_circular_relationships(self):
        """Test handling of circular foreign key relationships."""


class TestMetricConnectivityValidation:
    """Test validate_metric_connectivity function."""

    def test_valid_metric_all_measures_reachable(self):
        """Test validation passes for valid metric."""

    def test_unreachable_measure_raises_error(self):
        """Test validation error when measure not reachable."""

    def test_missing_primary_entity_raises_error(self):
        """Test error when primary_entity doesn't exist."""

    def test_invalid_primary_entity_name_raises_error(self):
        """Test error for invalid primary_entity name."""

    def test_missing_measure_reference_raises_error(self):
        """Test error when referenced measure doesn't exist."""

    def test_multi_hop_reachability_within_limit(self):
        """Test validation passes for 2-hop joins."""

    def test_multi_hop_exceeds_limit_raises_error(self):
        """Test error when joins exceed max hop limit."""

    def test_error_message_helpful_for_unreachable(self):
        """Test that error messages include helpful suggestions."""

    def test_error_message_helpful_for_missing_primary_entity(self):
        """Test error message guidance for missing primary_entity."""
```

**Coverage Target**: 100% of validation code

### Phase 3: Integration Tests

**Objective**: Test end-to-end workflows from parsing to LookML generation

#### 3.1 Cross-Entity Metrics Integration Tests

**File: `src/tests/integration/test_cross_entity_metrics.py`**

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
    def semantic_models_dir(self, tmp_path):
        """Create semantic models for testing."""
        # Create fixtures: searches, rental_orders

    @pytest.fixture
    def metrics_dir(self, tmp_path):
        """Create metrics for testing."""
        # Create search_conversion_rate metric

    def test_search_conversion_rate_generation(self):
        """Test generating search conversion rate metric.

        Workflow:
        1. Parse semantic models (searches, rental_orders)
        2. Parse metric (search_conversion_rate)
        3. Generate LookML
        4. Verify measure in searches.view.lkml
        5. Verify required_fields present
        6. Verify join fields expose rental_count
        """

    def test_generated_measure_has_correct_sql(self):
        """Test that generated SQL uses cross-view references."""

    def test_generated_measure_has_required_fields(self):
        """Test that required_fields parameter is present."""

    def test_explore_join_exposes_required_measure(self):
        """Test that rental_orders join includes rental_count in fields."""


class TestMultiEntityDerivedMetric:
    """Test derived metric across multiple entities."""

    def test_engagement_score_generation(self):
        """Test generating engagement score metric.

        Workflow:
        1. Parse semantic models (users, searches, rental_orders)
        2. Parse metric (engagement_score)
        3. Generate LookML
        4. Verify measure in users.view.lkml
        5. Verify required_fields includes both searches and rental_orders
        6. Verify both joins expose required measures
        """

    def test_derived_metric_sql_expression(self):
        """Test derived metric SQL expression is correctly formatted."""


class TestSimpleMetricCrossView:
    """Test simple metric with cross-view reference."""

    def test_total_revenue_metric_cross_view(self):
        """Test simple metric referencing measure from different view.

        Workflow:
        1. Parse semantic models (users, rental_orders)
        2. Parse metric (total_revenue owned by users)
        3. Generate LookML
        4. Verify measure in users.view.lkml
        5. Verify cross-view reference to rental_orders.total_revenue
        6. Verify required_fields
        """


class TestValidationErrorScenarios:
    """Test validation error handling during generation."""

    def test_unreachable_measure_error(self):
        """Test error when measure not reachable from primary entity."""

    def test_missing_primary_entity_error(self):
        """Test error when metric missing primary_entity declaration."""

    def test_invalid_primary_entity_name_error(self):
        """Test error when primary_entity references non-existent entity."""

    def test_missing_measure_reference_error(self):
        """Test error when metric references non-existent measure."""
```

**Coverage Target**: 95%+ end-to-end workflow coverage

### Phase 4: Golden Tests

**Objective**: Ensure generated output matches expected LookML exactly

#### 4.1 Golden File Generation

Create expected output files in `src/tests/golden/`:

**File: `expected_searches_with_metrics.view.lkml`**
```lookml
view: searches {
  sql_table_name: fct_searches ;;

  dimension: search_sk {
    type: string
    primary_key: yes
    hidden: yes
    sql: ${TABLE}.search_id ;;
  }

  dimension: user_sk {
    type: string
    hidden: yes
    sql: ${TABLE}.user_id ;;
  }

  dimension_group: search_date {
    type: time
    timeframes: [date, week, month, quarter, year]
    sql: ${TABLE}.search_date ;;
    convert_tz: no
  }

  dimension: search_term {
    type: string
    sql: ${TABLE}.search_term ;;
  }

  measure: search_count {
    type: count
    description: "Total number of searches"
  }

  measure: unique_searchers {
    type: count_distinct
    sql: ${TABLE}.user_id ;;
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

**File: `expected_users_with_metrics.view.lkml`**
```lookml
view: users {
  sql_table_name: dim_users ;;

  dimension: user_sk {
    type: string
    primary_key: yes
    hidden: yes
    sql: ${TABLE}.user_id ;;
  }

  dimension: user_status {
    type: string
    sql: ${TABLE}.user_status ;;
  }

  dimension_group: signup_date {
    type: time
    timeframes: [date, week, month, quarter, year]
    sql: ${TABLE}.signup_date ;;
    convert_tz: no
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
    required_fields: [searches.search_count, rental_orders.rental_count]
    value_format_name: decimal_2
    view_label: " Metrics"
    group_label: "Engagement Metrics"
  }

  set: dimensions_only {
    fields: [user_sk, user_status, signup_date_date]
  }
}
```

**File: `expected_explores_with_metrics.lkml`**
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
      rental_orders.total_revenue,
      rental_orders.rental_count
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

#### 4.2 Golden Test Implementation

**File: `src/tests/test_golden.py`** (additions)

```python
class TestGoldenFilesMetrics:
    """Golden file tests for metrics."""

    def test_searches_with_metrics_matches_golden(self, golden_dir, fixtures_dir):
        """Test searches view with metrics matches golden file."""

    def test_users_with_metrics_matches_golden(self, golden_dir, fixtures_dir):
        """Test users view with metrics matches golden file."""

    def test_explores_with_metrics_matches_golden(self, golden_dir, fixtures_dir):
        """Test explores with metric requirements match golden file."""

    def test_metric_measure_sql_formatting(self):
        """Test that metric SQL is properly formatted."""

    def test_metric_required_fields_ordering(self):
        """Test that required_fields are sorted consistently."""

    def test_join_fields_deterministic_ordering(self):
        """Test that join fields are ordered consistently."""
```

**Coverage Target**: Golden tests provide regression protection

## Testing Strategy Details

### Test Organization Principles

1. **One Test, One Thing**: Each test method tests exactly one behavior
2. **Clear Names**: Test names describe what is being tested (e.g., `test_ratio_metric_sql_generation_with_nullif`)
3. **Arrange-Act-Assert**: Follow consistent pattern in all tests
4. **Fixtures Over Repetition**: Use pytest fixtures for shared setup
5. **Independence**: Tests don't share state, can run in any order

### Error Testing Approach

For each error scenario, test:
1. **Error is raised**: Verify exception type
2. **Error message is helpful**: Check message contains actionable guidance
3. **Error contains context**: Include metric name, entity names, suggestions

Example:
```python
def test_unreachable_measure_error_message():
    """Test that unreachable measure error provides helpful guidance."""
    with pytest.raises(ValidationError) as exc_info:
        validate_metric_connectivity(metric, primary_model, all_models)

    error_msg = str(exc_info.value)
    assert "not reachable from" in error_msg
    assert "rental_orders" in error_msg  # Model name
    assert "sessions" in error_msg  # Unreachable model
    assert "Change primary_entity" in error_msg  # Suggestion
```

### Performance Considerations

1. **Unit tests target**: < 1 second total execution
2. **Integration tests target**: < 5 seconds total execution
3. **Golden tests target**: < 3 seconds total execution
4. **Use TemporaryDirectory**: Clean up automatically, faster than disk I/O

### Coverage Measurement

Run coverage with:
```bash
make test-coverage  # HTML report in htmlcov/
python -m pytest src/tests/unit/test_metric_*.py --cov=src/dbt_to_lookml --cov-branch --cov-report=term-missing
```

Track coverage by module:
- `schemas.py` (Metric classes): 100%
- `parsers/dbt_metrics.py`: 100%
- `generators/lookml.py` (metric methods): 100%
- `validation.py`: 100%
- Overall project: 95%+

## Implementation Checklist

### Phase 1: Fixtures ✓
- [ ] Create `src/tests/fixtures/semantic_models/`
- [ ] Create `sem_rental_orders.yml`
- [ ] Create `sem_searches.yml`
- [ ] Create `sem_users.yml`
- [ ] Create `src/tests/fixtures/metrics/`
- [ ] Create `search_conversion.yml`
- [ ] Create `revenue_per_user.yml`
- [ ] Create `engagement_score.yml`
- [ ] Create `total_revenue.yml`
- [ ] Create error test fixtures

### Phase 2: Unit Tests ✓
- [ ] Create `test_metric_schemas.py` (20+ tests)
- [ ] Create `test_dbt_metric_parser.py` (25+ tests)
- [ ] Create `test_cross_entity_measure_generation.py` (20+ tests)
- [ ] Create `test_explore_metric_requirements.py` (15+ tests)
- [ ] Create `test_metric_validation.py` (15+ tests)
- [ ] Run coverage, verify 100% of new code

### Phase 3: Integration Tests ✓
- [ ] Create `test_cross_entity_metrics.py`
- [ ] Implement basic ratio metric test
- [ ] Implement multi-entity derived metric test
- [ ] Implement simple metric cross-view test
- [ ] Implement validation error scenarios
- [ ] Run integration suite, verify all pass

### Phase 4: Golden Tests ✓
- [ ] Create `expected_searches_with_metrics.view.lkml`
- [ ] Create `expected_users_with_metrics.view.lkml`
- [ ] Create `expected_explores_with_metrics.lkml`
- [ ] Add golden test methods to `test_golden.py`
- [ ] Generate actual output, compare with golden files
- [ ] Verify byte-for-byte match

### Phase 5: Validation ✓
- [ ] Run full test suite: `make test-full`
- [ ] Generate coverage report: `make test-coverage`
- [ ] Verify 95%+ overall coverage
- [ ] Verify 100% coverage for metric code
- [ ] Review coverage gaps, add tests if needed
- [ ] Update documentation with test patterns

## Risk Mitigation

### Risk 1: Coverage Target Not Met
**Mitigation**:
- Start with unit tests (highest ROI for coverage)
- Use coverage HTML report to identify untested branches
- Add edge case tests for each uncovered branch
- Prioritize new metric code for 100% coverage

### Risk 2: Golden Tests Fragile
**Mitigation**:
- Use `_assert_content_matches` helper with normalization
- Test structural elements, not exact whitespace
- Version golden files in git for tracking changes
- Document golden file update process

### Risk 3: Integration Tests Slow
**Mitigation**:
- Use TemporaryDirectory for fast cleanup
- Keep fixture files minimal
- Run unit tests in parallel (pytest-xdist)
- Use pytest markers to run subsets

### Risk 4: Tests Coupled to Implementation
**Mitigation**:
- Test behavior, not implementation details
- Use public API methods in tests
- Mock external dependencies, not internal methods
- Focus on input/output, not intermediate states

## Dependencies

### Blocked By
- DTL-023: Metric schema models (test_metric_schemas.py depends on Metric classes)
- DTL-024: Metric parser (test_dbt_metric_parser.py depends on DbtMetricParser)
- DTL-025: Measure generation (test_cross_entity_measure_generation.py depends on _generate_metric_measure)
- DTL-026: Explore enhancement (test_explore_metric_requirements.py depends on _identify_metric_requirements)
- DTL-027: Validation (test_metric_validation.py depends on validation functions)

### Blocks
- None (testing is final validation step)

## Success Criteria

1. ✓ All unit tests passing (95+ total tests)
2. ✓ All integration tests passing (10+ scenarios)
3. ✓ All golden tests passing (byte-for-byte match)
4. ✓ Coverage report shows 95%+ overall
5. ✓ Coverage report shows 100% for new metric code
6. ✓ All metric types covered in tests
7. ✓ All validation scenarios tested
8. ✓ All error paths tested with helpful messages
9. ✓ Tests follow existing patterns (arrange-act-assert)
10. ✓ Test names clearly describe what is tested

## Key Architectural Decisions

### Decision 1: Separate Test Files by Component
**Rationale**: Follows existing project structure, makes tests easy to find, allows parallel execution

**Alternatives Considered**:
- Single test file for all metrics → Too large, hard to navigate
- Organize by metric type → Doesn't align with code organization

**Trade-offs**: More files to manage, but better organization and discoverability

### Decision 2: Fixtures in `fixtures/` Subdirectory
**Rationale**: Consistent with existing project structure, reusable across test types

**Alternatives Considered**:
- Inline fixtures in test files → Less reusable, harder to maintain
- Pytest fixture functions → Better for dynamic data, but YAML files are static

**Trade-offs**: Requires file I/O, but more realistic testing

### Decision 3: Golden Files for Regression Protection
**Rationale**: Ensures output stability, catches unintended changes, provides documentation of expected output

**Alternatives Considered**:
- Structural assertions only → Misses formatting issues
- Generated comparison → Doesn't catch subtle changes

**Trade-offs**: Requires manual golden file updates, but provides strongest regression protection

### Decision 4: 100% Coverage for New Code
**Rationale**: Metrics are core feature, need highest quality, catches edge cases early

**Alternatives Considered**:
- 95% target for all code → Allows untested branches in new code
- 80% target → Too low for critical feature

**Trade-offs**: More tests to write, but better quality and maintainability

## Estimated Effort

- **Phase 1 (Fixtures)**: 4 hours
- **Phase 2 (Unit Tests)**: 16 hours
- **Phase 3 (Integration Tests)**: 8 hours
- **Phase 4 (Golden Tests)**: 6 hours
- **Phase 5 (Validation)**: 4 hours
- **Buffer (20%)**: 8 hours

**Total**: 46 hours (~6 days)

## Next Steps

1. **Immediate**: Create test fixtures directory structure and YAML files
2. **Day 1-2**: Implement unit tests for schemas and parser
3. **Day 3-4**: Implement unit tests for generator and validation
4. **Day 5**: Implement integration and golden tests
5. **Day 6**: Coverage validation, gap filling, documentation

## Appendix A: Test Naming Conventions

Follow these patterns for test names:

- **Schema validation**: `test_{model}_validation_{scenario}`
  - Example: `test_metric_validation_missing_name`

- **Parsing**: `test_parse_{what}_{scenario}`
  - Example: `test_parse_single_ratio_metric`

- **Generation**: `test_generate_{what}_{scenario}`
  - Example: `test_generate_ratio_metric_measure`

- **Validation**: `test_{what}_validation_{scenario}`
  - Example: `test_connectivity_validation_unreachable_measure`

- **Integration**: `test_{workflow}_{scenario}`
  - Example: `test_search_conversion_rate_generation`

## Appendix B: Coverage Gap Analysis Strategy

When coverage is below target:

1. **Generate HTML report**: `make test-coverage`
2. **Open `htmlcov/index.html`**: Find modules with low coverage
3. **Identify uncovered branches**: Look for red/yellow highlighted code
4. **Categorize gaps**:
   - Error handling paths
   - Edge cases (empty lists, None values)
   - Optional parameters
   - Conditional logic branches
5. **Add targeted tests**: One test per uncovered branch
6. **Re-run coverage**: Verify gap is filled

## Document History

- **2025-11-18**: Initial strategy document created
- **Status**: Ready for implementation
