"""Unit tests for validation module.

Tests cover:
- JoinGraph BFS traversal and reachability
- EntityConnectivityValidator validation logic
- ValidationResult error/warning categorization
- Helper functions (find_model_by_primary_entity, extract_measure_dependencies)
"""

from dbt_to_lookml.schemas import (
    ConversionMetricParams,
    DerivedMetricParams,
    Entity,
    Measure,
    Metric,
    MetricReference,
    RatioMetricParams,
    SemanticModel,
    SimpleMetricParams,
)
from dbt_to_lookml.types import AggregationType
from dbt_to_lookml.validation import (
    EntityConnectivityValidator,
    JoinGraph,
    ValidationError,
    ValidationResult,
    extract_measure_dependencies,
    find_model_by_primary_entity,
)

# ============================================================================
# Helper Function Tests
# ============================================================================


def test_find_model_by_primary_entity_found():
    """Test finding a model by its primary entity."""
    users = SemanticModel(
        name="users",
        model="users",
        entities=[Entity(name="user", type="primary")],
        measures=[],
    )
    rentals = SemanticModel(
        name="rentals",
        model="rentals",
        entities=[
            Entity(name="rental", type="primary"),
            Entity(name="user", type="foreign"),
        ],
        measures=[],
    )

    result = find_model_by_primary_entity("user", [users, rentals])
    assert result == users


def test_find_model_by_primary_entity_not_found():
    """Test finding a model when entity doesn't exist."""
    users = SemanticModel(
        name="users",
        model="users",
        entities=[Entity(name="user", type="primary")],
        measures=[],
    )

    result = find_model_by_primary_entity("nonexistent", [users])
    assert result is None


def test_find_model_by_primary_entity_foreign_only():
    """Test that foreign entities are not matched."""
    rentals = SemanticModel(
        name="rentals",
        model="rentals",
        entities=[
            Entity(name="rental", type="primary"),
            Entity(name="user", type="foreign"),
        ],
        measures=[],
    )

    # Should not find model with only foreign entity
    result = find_model_by_primary_entity("user", [rentals])
    assert result is None


def test_extract_measure_dependencies_simple():
    """Test extracting dependencies from simple metric."""
    metric = Metric(
        name="total_revenue",
        type="simple",
        type_params=SimpleMetricParams(measure="revenue"),
    )

    deps = extract_measure_dependencies(metric)
    assert deps == {"revenue"}


def test_extract_measure_dependencies_ratio():
    """Test extracting dependencies from ratio metric."""
    metric = Metric(
        name="conversion_rate",
        type="ratio",
        type_params=RatioMetricParams(
            numerator="rental_count", denominator="search_count"
        ),
    )

    deps = extract_measure_dependencies(metric)
    assert deps == {"rental_count", "search_count"}


def test_extract_measure_dependencies_derived():
    """Test extracting dependencies from derived metric (empty set)."""
    metric = Metric(
        name="revenue_growth",
        type="derived",
        type_params=DerivedMetricParams(
            expr="current - prior",
            metrics=[
                MetricReference(name="revenue", alias="current"),
                MetricReference(name="revenue", alias="prior", offset_window="1 month"),
            ],
        ),
    )

    deps = extract_measure_dependencies(metric)
    assert deps == set()  # Derived metrics reference metrics, not measures


def test_extract_measure_dependencies_conversion():
    """Test extracting dependencies from conversion metric."""
    metric = Metric(
        name="signup_conversion",
        type="conversion",
        type_params=ConversionMetricParams(
            conversion_type_params={
                "base_measure": "session_count",
                "conversion_measure": "signup_count",
            }
        ),
    )

    deps = extract_measure_dependencies(metric)
    assert deps == {"session_count", "signup_count"}


# ============================================================================
# ValidationResult Tests
# ============================================================================


def test_validation_result_categorization():
    """Test error/warning categorization in ValidationResult."""
    result = ValidationResult()

    result.add_error(
        metric_name="m1",
        issue_type="unreachable_measure",
        message="Error message",
        suggestions=["Fix it"],
    )
    result.add_warning(
        metric_name="m2",
        issue_type="exceeds_hop_limit",
        message="Warning message",
        suggestions=["Optimize it"],
    )

    assert result.has_errors()
    assert result.has_warnings()
    assert len(result.issues) == 2
    assert result.issues[0].severity == "error"
    assert result.issues[1].severity == "warning"


def test_validation_result_has_errors():
    """Test has_errors() method."""
    result = ValidationResult()
    assert not result.has_errors()

    result.add_error(
        metric_name="test",
        issue_type="missing_measure",
        message="Test error",
        suggestions=[],
    )
    assert result.has_errors()


def test_validation_result_has_warnings():
    """Test has_warnings() method."""
    result = ValidationResult()
    assert not result.has_warnings()

    result.add_warning(
        metric_name="test",
        issue_type="exceeds_hop_limit",
        message="Test warning",
        suggestions=[],
    )
    assert result.has_warnings()


def test_validation_result_format_report():
    """Test format_report() generates readable output."""
    result = ValidationResult()

    result.add_error(
        metric_name="bad_metric",
        issue_type="missing_measure",
        message="Missing measure 'revenue'",
        suggestions=["Check spelling", "Verify model exists"],
    )

    report = result.format_report()
    assert "Validation Errors" in report
    assert "Missing measure 'revenue'" in report
    assert "Check spelling" in report
    assert "Verify model exists" in report


# ============================================================================
# JoinGraph Tests
# ============================================================================


def test_join_graph_single_hop():
    """Test single-hop reachability (fact → dimension)."""
    # Setup: rentals -> users (1 hop)
    rentals = SemanticModel(
        name="rental_orders",
        model="rental_orders",
        entities=[
            Entity(name="rental", type="primary"),
            Entity(name="user", type="foreign"),
        ],
        measures=[Measure(name="rental_count", agg=AggregationType.COUNT, expr=None)],
    )
    users = SemanticModel(
        name="users",
        model="users",
        entities=[Entity(name="user", type="primary")],
        measures=[Measure(name="user_count", agg=AggregationType.COUNT, expr=None)],
    )

    # Build graph from rental entity
    graph = JoinGraph(base_entity="rental", all_models=[rentals, users], max_hops=2)

    # Assert both models reachable
    assert graph.is_model_reachable("rental_orders")
    assert graph.is_model_reachable("users")
    assert graph.get_hop_count("rental_orders") == 0
    assert graph.get_hop_count("users") == 1
    assert graph.is_entity_reachable("rental")
    assert graph.is_entity_reachable("user")


def test_join_graph_multi_hop():
    """Test multi-hop reachability (fact → dim1 → dim2)."""
    # Setup: rentals -> searches -> sessions (2 hops)
    rentals = SemanticModel(
        name="rentals",
        model="rentals",
        entities=[
            Entity(name="rental", type="primary"),
            Entity(name="search", type="foreign"),
        ],
        measures=[],
    )
    searches = SemanticModel(
        name="searches",
        model="searches",
        entities=[
            Entity(name="search", type="primary"),
            Entity(name="session", type="foreign"),
        ],
        measures=[],
    )
    sessions = SemanticModel(
        name="sessions",
        model="sessions",
        entities=[Entity(name="session", type="primary")],
        measures=[],
    )

    graph = JoinGraph(
        base_entity="rental", all_models=[rentals, searches, sessions], max_hops=2
    )

    # All should be reachable within 2 hops
    assert graph.is_model_reachable("rentals")
    assert graph.is_model_reachable("searches")
    assert graph.is_model_reachable("sessions")
    assert graph.get_hop_count("rentals") == 0
    assert graph.get_hop_count("searches") == 1
    assert graph.get_hop_count("sessions") == 2


def test_join_graph_unreachable():
    """Test unreachable models (no foreign key path)."""
    users = SemanticModel(
        name="users",
        model="users",
        entities=[Entity(name="user", type="primary")],
        measures=[],
    )
    sessions = SemanticModel(
        name="sessions",
        model="sessions",
        entities=[Entity(name="session", type="primary")],
        measures=[],
    )

    # No foreign key relationship between users and sessions
    graph = JoinGraph(base_entity="user", all_models=[users, sessions], max_hops=2)

    assert graph.is_model_reachable("users")
    assert not graph.is_model_reachable("sessions")
    assert graph.get_hop_count("sessions") is None


def test_join_graph_max_hops():
    """Test max hop limit enforcement."""
    # Chain: model1 -> model2 -> model3 -> model4
    model1 = SemanticModel(
        name="model1",
        model="model1",
        entities=[
            Entity(name="entity1", type="primary"),
            Entity(name="entity2", type="foreign"),
        ],
        measures=[],
    )
    model2 = SemanticModel(
        name="model2",
        model="model2",
        entities=[
            Entity(name="entity2", type="primary"),
            Entity(name="entity3", type="foreign"),
        ],
        measures=[],
    )
    model3 = SemanticModel(
        name="model3",
        model="model3",
        entities=[
            Entity(name="entity3", type="primary"),
            Entity(name="entity4", type="foreign"),
        ],
        measures=[],
    )
    model4 = SemanticModel(
        name="model4",
        model="model4",
        entities=[Entity(name="entity4", type="primary")],
        measures=[],
    )

    # With max_hops=2, model4 should not be reachable (would be 3 hops)
    graph = JoinGraph(
        base_entity="entity1", all_models=[model1, model2, model3, model4], max_hops=2
    )

    assert graph.is_model_reachable("model1")
    assert graph.is_model_reachable("model2")
    assert graph.is_model_reachable("model3")
    assert not graph.is_model_reachable("model4")


def test_join_graph_invalid_base_entity():
    """Test join graph with invalid base entity."""
    users = SemanticModel(
        name="users",
        model="users",
        entities=[Entity(name="user", type="primary")],
        measures=[],
    )

    graph = JoinGraph(base_entity="nonexistent", all_models=[users], max_hops=2)

    # Should have empty reachable sets
    assert not graph.is_model_reachable("users")
    assert len(graph.reachable_models) == 0


def test_join_graph_circular_references():
    """Test that circular references don't cause infinite loop."""
    # model1 -> model2 -> model1 (circular)
    model1 = SemanticModel(
        name="model1",
        model="model1",
        entities=[
            Entity(name="entity1", type="primary"),
            Entity(name="entity2", type="foreign"),
        ],
        measures=[],
    )
    model2 = SemanticModel(
        name="model2",
        model="model2",
        entities=[
            Entity(name="entity2", type="primary"),
            Entity(name="entity1", type="foreign"),
        ],
        measures=[],
    )

    # Should complete without infinite loop
    graph = JoinGraph(base_entity="entity1", all_models=[model1, model2], max_hops=2)

    assert graph.is_model_reachable("model1")
    assert graph.is_model_reachable("model2")


# ============================================================================
# EntityConnectivityValidator Tests
# ============================================================================


def test_validator_valid_metric():
    """Test validation of a valid metric with reachable measures."""
    users = SemanticModel(
        name="users",
        model="users",
        entities=[Entity(name="user", type="primary")],
        measures=[Measure(name="user_count", agg=AggregationType.COUNT, expr=None)],
    )

    metric = Metric(
        name="total_users",
        type="simple",
        type_params=SimpleMetricParams(measure="user_count"),
        meta={"primary_entity": "user"},
    )

    validator = EntityConnectivityValidator([users])
    result = validator.validate_metric(metric)

    assert not result.has_errors()
    assert not result.has_warnings()


def test_validator_unreachable_measure():
    """Test detection of unreachable measure."""
    users = SemanticModel(
        name="users",
        model="users",
        entities=[Entity(name="user", type="primary")],
        measures=[Measure(name="user_count", agg=AggregationType.COUNT, expr=None)],
    )
    sessions = SemanticModel(
        name="sessions",
        model="sessions",
        entities=[Entity(name="session", type="primary")],
        measures=[Measure(name="session_count", agg=AggregationType.COUNT, expr=None)],
    )

    # Metric requiring both user_count and session_count from primary_entity=user
    metric = Metric(
        name="conversion_rate",
        type="ratio",
        type_params=RatioMetricParams(
            numerator="user_count", denominator="session_count"
        ),
        meta={"primary_entity": "user"},
    )

    validator = EntityConnectivityValidator([users, sessions])
    result = validator.validate_metric(metric)

    assert result.has_errors()
    assert any(
        issue.issue_type == "unreachable_measure"
        and issue.measure_name == "session_count"
        for issue in result.issues
    )


def test_validator_missing_measure():
    """Test detection of missing measure."""
    users = SemanticModel(
        name="users",
        model="users",
        entities=[Entity(name="user", type="primary")],
        measures=[Measure(name="user_count", agg=AggregationType.COUNT, expr=None)],
    )

    metric = Metric(
        name="total_revenue",
        type="simple",
        type_params=SimpleMetricParams(measure="revenue"),  # Doesn't exist
        meta={"primary_entity": "user"},
    )

    validator = EntityConnectivityValidator([users])
    result = validator.validate_metric(metric)

    assert result.has_errors()
    assert any(issue.issue_type == "missing_measure" for issue in result.issues)


def test_validator_invalid_primary_entity():
    """Test detection of invalid primary_entity."""
    users = SemanticModel(
        name="users",
        model="users",
        entities=[Entity(name="user", type="primary")],
        measures=[Measure(name="user_count", agg=AggregationType.COUNT, expr=None)],
    )

    metric = Metric(
        name="total_users",
        type="simple",
        type_params=SimpleMetricParams(measure="user_count"),
        meta={"primary_entity": "nonexistent"},  # Invalid
    )

    validator = EntityConnectivityValidator([users])
    result = validator.validate_metric(metric)

    assert result.has_errors()
    assert any(issue.issue_type == "invalid_primary_entity" for issue in result.issues)


def test_validator_missing_primary_entity():
    """Test detection of missing primary_entity for simple metric."""
    users = SemanticModel(
        name="users",
        model="users",
        entities=[Entity(name="user", type="primary")],
        measures=[Measure(name="user_count", agg=AggregationType.COUNT, expr=None)],
    )

    metric = Metric(
        name="total_users",
        type="simple",
        type_params=SimpleMetricParams(measure="user_count"),
        # No meta with primary_entity
    )

    validator = EntityConnectivityValidator([users])
    result = validator.validate_metric(metric)

    assert result.has_errors()
    assert any(issue.issue_type == "missing_primary_entity" for issue in result.issues)


def test_validator_primary_entity_inference_ratio():
    """Test primary entity inference for ratio metrics."""
    # Setup where user_count is in base (users) and search_count needs FK
    users = SemanticModel(
        name="users",
        model="users",
        entities=[
            Entity(name="user", type="primary"),
            Entity(name="search", type="foreign"),  # FK to searches
        ],
        measures=[Measure(name="user_count", agg=AggregationType.COUNT, expr=None)],
    )
    searches = SemanticModel(
        name="searches",
        model="searches",
        entities=[Entity(name="search", type="primary")],
        measures=[Measure(name="search_count", agg=AggregationType.COUNT, expr=None)],
    )

    # Ratio metric without explicit primary_entity (should infer from denominator)
    metric = Metric(
        name="searches_per_user",
        type="ratio",
        type_params=RatioMetricParams(
            numerator="search_count", denominator="user_count"
        ),
        # No explicit primary_entity - should infer "user" from user_count
    )

    validator = EntityConnectivityValidator([users, searches])
    result = validator.validate_metric(metric)

    # Should infer primary_entity="user" and validate successfully
    # (users has FK to searches, so search_count is reachable)
    assert not result.has_errors()


def test_validator_batch_validation():
    """Test validation of multiple metrics."""
    users = SemanticModel(
        name="users",
        model="users",
        entities=[Entity(name="user", type="primary")],
        measures=[Measure(name="user_count", agg=AggregationType.COUNT, expr=None)],
    )

    metric1 = Metric(
        name="total_users",
        type="simple",
        type_params=SimpleMetricParams(measure="user_count"),
        meta={"primary_entity": "user"},
    )
    metric2 = Metric(
        name="total_revenue",
        type="simple",
        type_params=SimpleMetricParams(measure="revenue"),  # Doesn't exist
        meta={"primary_entity": "user"},
    )

    validator = EntityConnectivityValidator([users])
    result = validator.validate_metrics([metric1, metric2])

    # Should have one error from metric2
    assert result.has_errors()
    assert len([i for i in result.issues if i.severity == "error"]) == 1


def test_validator_derived_metric_no_validation():
    """Test that derived metrics don't trigger measure validation."""
    users = SemanticModel(
        name="users",
        model="users",
        entities=[Entity(name="user", type="primary")],
        measures=[],
    )

    metric = Metric(
        name="revenue_growth",
        type="derived",
        type_params=DerivedMetricParams(
            expr="current - prior",
            metrics=[
                MetricReference(name="revenue", alias="current"),
                MetricReference(name="revenue", alias="prior", offset_window="1 month"),
            ],
        ),
        meta={"primary_entity": "user"},
    )

    validator = EntityConnectivityValidator([users])
    result = validator.validate_metric(metric)

    # Derived metrics reference other metrics, not measures, so no validation errors
    assert not result.has_errors()


def test_validation_error_exception():
    """Test that ValidationError can be raised."""
    error = ValidationError("Test error message")
    assert str(error) == "Test error message"
    assert isinstance(error, Exception)
