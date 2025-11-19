"""Integration tests for metric validation.

Tests end-to-end validation workflows including:
- Parser integration with validation
- Generator integration with validation
- Multi-model join graph scenarios
- Error message content verification
"""

from pathlib import Path

import pytest

from dbt_to_lookml.generators.lookml import LookMLGenerator, LookMLValidationError
from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.parsers.dbt_metrics import DbtMetricParser
from dbt_to_lookml.validation import (
    EntityConnectivityValidator,
    ValidationError,
)


@pytest.fixture
def fixtures_dir():
    """Path to validation test fixtures."""
    return Path(__file__).parent.parent / "fixtures" / "metrics_validation"


@pytest.fixture
def semantic_models(fixtures_dir):
    """Parse semantic models from fixtures."""
    parser = DbtParser()
    models_dir = fixtures_dir / "semantic_models"
    return parser.parse_directory(models_dir)


@pytest.fixture
def metrics_dir(fixtures_dir):
    """Path to metrics fixtures directory."""
    return fixtures_dir / "metrics"


def test_valid_metric_with_real_files(semantic_models, metrics_dir):
    """Test validation with valid metric from real YAML files."""
    # Parse valid metric
    parser = DbtMetricParser()
    metrics = parser.parse_file(metrics_dir / "valid_metric.yml")

    assert len(metrics) == 1
    metric = metrics[0]

    # Validate
    validator = EntityConnectivityValidator(semantic_models)
    result = validator.validate_metric(metric)

    # Should have no errors
    assert not result.has_errors()
    assert not result.has_warnings()


def test_unreachable_measure_end_to_end(semantic_models, metrics_dir):
    """Test unreachable measure scenario from parsing to validation."""
    # Parse unreachable metric (user -> session with no FK path)
    parser = DbtMetricParser()
    metrics = parser.parse_file(metrics_dir / "unreachable_metric.yml")

    assert len(metrics) == 1
    metric = metrics[0]

    # Validate
    validator = EntityConnectivityValidator(semantic_models)
    result = validator.validate_metric(metric)

    # Should have error for unreachable measure
    assert result.has_errors()
    assert any(
        issue.issue_type == "unreachable_measure"
        and issue.measure_name == "session_count"
        for issue in result.issues
    )

    # Error message should be informative
    report = result.format_report()
    assert "session_count" in report
    assert "sessions" in report.lower()
    assert "not reachable" in report.lower()


def test_missing_entity_validation(semantic_models, metrics_dir):
    """Test validation with invalid primary_entity."""
    parser = DbtMetricParser()
    metrics = parser.parse_file(metrics_dir / "missing_entity_metric.yml")

    assert len(metrics) == 1

    validator = EntityConnectivityValidator(semantic_models)
    result = validator.validate_metrics(metrics)

    assert result.has_errors()
    assert any(issue.issue_type == "invalid_primary_entity" for issue in result.issues)


def test_missing_measure_validation(semantic_models, metrics_dir):
    """Test validation with nonexistent measure."""
    parser = DbtMetricParser()
    metrics = parser.parse_file(metrics_dir / "missing_measure_metric.yml")

    assert len(metrics) == 1

    validator = EntityConnectivityValidator(semantic_models)
    result = validator.validate_metrics(metrics)

    assert result.has_errors()
    assert any(issue.issue_type == "missing_measure" for issue in result.issues)


def test_multi_model_join_graph(semantic_models, metrics_dir):
    """Test validation with multi-model join graph (3+ models)."""
    # Parse metric requiring multi-hop join (rental -> search -> ...)
    parser = DbtMetricParser()
    metrics = parser.parse_file(metrics_dir / "multi_hop_metric.yml")

    assert len(metrics) == 1

    validator = EntityConnectivityValidator(semantic_models)
    result = validator.validate_metrics(metrics)

    # Should be valid - rental reachable from search (1 hop)
    assert not result.has_errors()


def test_parser_integration_strict_mode(semantic_models, tmp_path):
    """Test parser integration with validation in strict mode."""
    # Create temp directory with just the failing metric
    temp_metrics = tmp_path / "metrics"
    temp_metrics.mkdir()

    # Copy the unreachable metric file
    import shutil
    from pathlib import Path

    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "metrics_validation"
    shutil.copy(
        fixtures_dir / "metrics" / "unreachable_metric.yml",
        temp_metrics / "unreachable_metric.yml",
    )

    # Parser with strict mode should raise ValidationError
    parser = DbtMetricParser(strict_mode=True, semantic_models=semantic_models)

    with pytest.raises(ValidationError):
        # This will fail validation during parse_directory
        parser.parse_directory(temp_metrics)


def test_parser_integration_lenient_mode(semantic_models, tmp_path, capsys):
    """Test parser integration with validation in lenient mode."""
    # Create temp directory with just the failing metric
    temp_metrics = tmp_path / "metrics"
    temp_metrics.mkdir()

    # Copy the unreachable metric file
    import shutil
    from pathlib import Path

    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "metrics_validation"
    shutil.copy(
        fixtures_dir / "metrics" / "unreachable_metric.yml",
        temp_metrics / "unreachable_metric.yml",
    )

    # Parser without strict mode should log warnings but not fail
    parser = DbtMetricParser(strict_mode=False, semantic_models=semantic_models)

    # Should parse successfully despite validation errors
    metrics = parser.parse_directory(temp_metrics)
    assert len(metrics) == 1

    # Check that warnings were printed (captured output)
    captured = capsys.readouterr()
    assert "Validation" in captured.out or "warning" in captured.out.lower()


def test_parser_integration_validation_disabled(semantic_models, metrics_dir):
    """Test parser with validation explicitly disabled."""
    parser = DbtMetricParser(semantic_models=semantic_models)

    # Parse with validate=False should skip validation
    metrics = parser.parse_directory(metrics_dir, validate=False)

    # Should parse all metrics without validation errors
    assert len(metrics) >= 3


def test_generator_integration_validation(semantic_models):
    """Test generator integration with validation before generation."""
    from dbt_to_lookml.schemas.semantic_layer import (
    Metric,
    RatioMetricParams,
)

    # Create metric with unreachable measure
    bad_metric = Metric(
        name="bad_conversion",
        type="ratio",
        type_params=RatioMetricParams(
            numerator="user_count",
            denominator="session_count",
        ),
        meta={"primary_entity": "user"},
    )

    generator = LookMLGenerator()

    # Should raise LookMLValidationError
    with pytest.raises(LookMLValidationError):
        generator.generate(semantic_models, metrics=[bad_metric], validate=True)


def test_generator_integration_validation_disabled(semantic_models):
    """Test generator with validation disabled."""
    from dbt_to_lookml.schemas.semantic_layer import (
    Metric,
    RatioMetricParams,
)

    # Create metric with unreachable measure
    bad_metric = Metric(
        name="bad_conversion",
        type="ratio",
        type_params=RatioMetricParams(
            numerator="user_count",
            denominator="session_count",
        ),
        meta={"primary_entity": "user"},
    )

    generator = LookMLGenerator()

    # With validate=False, should not raise error
    # (though generation may fail later during metric processing)
    try:
        files = generator.generate(
            semantic_models, metrics=[bad_metric], validate=False
        )
        # If it gets here, validation was skipped
        assert isinstance(files, dict)
    except Exception as e:
        # If it fails, it should not be a ValidationError
        assert not isinstance(e, LookMLValidationError)


def test_error_message_content(semantic_models, metrics_dir):
    """Test that error messages contain helpful information."""
    parser = DbtMetricParser()
    metrics = parser.parse_file(metrics_dir / "unreachable_metric.yml")

    validator = EntityConnectivityValidator(semantic_models)
    result = validator.validate_metrics(metrics)

    assert result.has_errors()

    # Get the error
    error_issue = [i for i in result.issues if i.severity == "error"][0]

    # Verify error contains helpful context
    assert error_issue.metric_name == "user_to_session_ratio"
    assert error_issue.primary_entity == "user"
    assert error_issue.measure_name == "session_count"
    assert error_issue.measure_model == "sessions"

    # Verify suggestions are provided
    assert len(error_issue.suggestions) > 0
    assert any("foreign key" in s.lower() for s in error_issue.suggestions)
