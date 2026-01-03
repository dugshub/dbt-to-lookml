"""Unit tests for PoP eligibility metric detection."""

from dbt_to_lookml.generators.lookml import (
    is_pop_eligible_metric,
    is_same_model_derived_metric,
)
from dbt_to_lookml.schemas.semantic_layer import (
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


class TestSimpleMetricPopEligibility:
    """Tests for simple metric PoP eligibility."""

    def test_simple_metric_with_primary_entity_qualifies(self) -> None:
        """Simple metric with primary_entity qualifies for PoP."""
        metric = Metric(
            name="revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="total_revenue"),
            meta={"primary_entity": "order"},
        )
        qualifies, entity = is_pop_eligible_metric(metric)
        assert qualifies is True
        assert entity == "order"

    def test_simple_metric_without_primary_entity_fails(self) -> None:
        """Simple metric without primary_entity doesn't qualify."""
        metric = Metric(
            name="revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="total_revenue"),
            # No meta/primary_entity
        )
        qualifies, entity = is_pop_eligible_metric(metric)
        assert qualifies is False
        assert entity is None


class TestRatioMetricPopEligibility:
    """Tests for ratio metric PoP eligibility."""

    def test_ratio_metric_same_model_qualifies(self) -> None:
        """Ratio metric with numerator and denominator from same model qualifies."""
        # Create a model with both measures
        rentals_model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            entities=[Entity(name="rental", type="primary")],
            measures=[
                Measure(name="gov", agg=AggregationType.SUM),
                Measure(name="rental_count", agg=AggregationType.COUNT),
            ],
        )

        # AOV = GOV / Rental Count (both from rentals)
        aov_metric = Metric(
            name="average_order_value",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="gov",
                denominator="rental_count",
            ),
            meta={"primary_entity": "rental"},
        )

        qualifies, entity = is_pop_eligible_metric(
            aov_metric, all_models=[rentals_model]
        )
        assert qualifies is True
        assert entity == "rental"

    def test_ratio_metric_cross_model_fails(self) -> None:
        """Ratio metric with measures from different models doesn't qualify."""
        orders_model = SemanticModel(
            name="orders",
            model="ref('orders')",
            entities=[Entity(name="order", type="primary")],
            measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
        )
        searches_model = SemanticModel(
            name="searches",
            model="ref('searches')",
            entities=[Entity(name="search", type="primary")],
            measures=[Measure(name="search_count", agg=AggregationType.COUNT)],
        )

        # Conversion rate = orders / searches (cross-model)
        conversion_metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count",
                denominator="search_count",
            ),
            meta={"primary_entity": "search"},
        )

        qualifies, entity = is_pop_eligible_metric(
            conversion_metric, all_models=[orders_model, searches_model]
        )
        assert qualifies is False
        assert entity is None

    def test_ratio_metric_missing_measure_fails(self) -> None:
        """Ratio metric with missing measure doesn't qualify."""
        rentals_model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            entities=[Entity(name="rental", type="primary")],
            measures=[Measure(name="gov", agg=AggregationType.SUM)],
            # Missing rental_count measure
        )

        aov_metric = Metric(
            name="average_order_value",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="gov",
                denominator="rental_count",  # Doesn't exist
            ),
            meta={"primary_entity": "rental"},
        )

        qualifies, entity = is_pop_eligible_metric(
            aov_metric, all_models=[rentals_model]
        )
        assert qualifies is False
        assert entity is None

    def test_ratio_metric_without_models_falls_back_to_primary_entity(self) -> None:
        """Ratio metric without all_models falls back to primary_entity."""
        aov_metric = Metric(
            name="average_order_value",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="gov",
                denominator="rental_count",
            ),
            meta={"primary_entity": "rental"},
        )

        # Without all_models, falls back to primary_entity
        qualifies, entity = is_pop_eligible_metric(aov_metric)
        assert qualifies is True
        assert entity == "rental"

    def test_ratio_metric_without_models_or_entity_fails(self) -> None:
        """Ratio metric without models or primary_entity fails."""
        aov_metric = Metric(
            name="average_order_value",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="gov",
                denominator="rental_count",
            ),
            # No meta/primary_entity
        )

        qualifies, entity = is_pop_eligible_metric(aov_metric)
        assert qualifies is False
        assert entity is None

    def test_ratio_metric_model_without_primary_entity_fails(self) -> None:
        """Ratio metric from model without primary entity fails."""
        rentals_model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            entities=[Entity(name="rental", type="foreign")],  # Not primary!
            measures=[
                Measure(name="gov", agg=AggregationType.SUM),
                Measure(name="rental_count", agg=AggregationType.COUNT),
            ],
        )

        aov_metric = Metric(
            name="average_order_value",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="gov",
                denominator="rental_count",
            ),
        )

        qualifies, entity = is_pop_eligible_metric(
            aov_metric, all_models=[rentals_model]
        )
        assert qualifies is False
        assert entity is None


class TestDerivedMetricPopEligibility:
    """Tests for derived metric PoP eligibility."""

    def test_derived_with_simple_parents_same_model(self) -> None:
        """Derived metric with all simple parents on same model qualifies."""
        gained = Metric(
            name="gained_eom",
            type="simple",
            type_params=SimpleMetricParams(measure="gained_count"),
            meta={"primary_entity": "facility"},
        )
        lost = Metric(
            name="lost_eom",
            type="simple",
            type_params=SimpleMetricParams(measure="lost_count"),
            meta={"primary_entity": "facility"},
        )
        net_change = Metric(
            name="net_change_eom",
            type="derived",
            type_params=DerivedMetricParams(
                expr="gained - lost",
                metrics=[
                    MetricReference(name="gained_eom", alias="gained"),
                    MetricReference(name="lost_eom", alias="lost"),
                ],
            ),
            meta={"primary_entity": "facility"},
        )

        all_metrics = [gained, lost, net_change]
        qualifies, entity = is_pop_eligible_metric(net_change, all_metrics)

        assert qualifies is True
        assert entity == "facility"

    def test_derived_with_cross_model_parents(self) -> None:
        """Derived metric with parents on different models doesn't qualify."""
        orders = Metric(
            name="order_count",
            type="simple",
            type_params=SimpleMetricParams(measure="orders"),
            meta={"primary_entity": "order"},
        )
        searches = Metric(
            name="search_count",
            type="simple",
            type_params=SimpleMetricParams(measure="searches"),
            meta={"primary_entity": "search"},
        )
        conversion = Metric(
            name="conversion_derived",
            type="derived",
            type_params=DerivedMetricParams(
                expr="orders / searches",
                metrics=[
                    MetricReference(name="order_count", alias="orders"),
                    MetricReference(name="search_count", alias="searches"),
                ],
            ),
            meta={"primary_entity": "search"},
        )

        all_metrics = [orders, searches, conversion]
        qualifies, entity = is_pop_eligible_metric(conversion, all_metrics)

        assert qualifies is False
        assert entity is None

    def test_nested_derived_metric_qualifies(self) -> None:
        """Nested derived (derived -> derived -> simple) qualifies if all same model."""
        a = Metric(
            name="metric_a",
            type="simple",
            type_params=SimpleMetricParams(measure="measure_a"),
            meta={"primary_entity": "entity"},
        )
        b = Metric(
            name="metric_b",
            type="simple",
            type_params=SimpleMetricParams(measure="measure_b"),
            meta={"primary_entity": "entity"},
        )
        c = Metric(
            name="metric_c",
            type="simple",
            type_params=SimpleMetricParams(measure="measure_c"),
            meta={"primary_entity": "entity"},
        )

        ab = Metric(
            name="metric_ab",
            type="derived",
            type_params=DerivedMetricParams(
                expr="a + b",
                metrics=[
                    MetricReference(name="metric_a", alias="a"),
                    MetricReference(name="metric_b", alias="b"),
                ],
            ),
            meta={"primary_entity": "entity"},
        )

        abc = Metric(
            name="metric_abc",
            type="derived",
            type_params=DerivedMetricParams(
                expr="ab + c",
                metrics=[
                    MetricReference(name="metric_ab", alias="ab"),
                    MetricReference(name="metric_c", alias="c"),
                ],
            ),
            meta={"primary_entity": "entity"},
        )

        all_metrics = [a, b, c, ab, abc]
        qualifies, entity = is_pop_eligible_metric(abc, all_metrics)

        assert qualifies is True
        assert entity == "entity"

    def test_derived_with_ratio_parent_same_model_qualifies(self) -> None:
        """Derived metric with ratio parent on same model qualifies."""
        rentals_model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            entities=[Entity(name="rental", type="primary")],
            measures=[
                Measure(name="gov", agg=AggregationType.SUM),
                Measure(name="rental_count", agg=AggregationType.COUNT),
            ],
        )

        # AOV ratio metric
        aov = Metric(
            name="aov",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="gov",
                denominator="rental_count",
            ),
            meta={"primary_entity": "rental"},
        )

        # Derived that adjusts AOV
        aov_adjusted = Metric(
            name="aov_adjusted",
            type="derived",
            type_params=DerivedMetricParams(
                expr="aov * 1.1",
                metrics=[MetricReference(name="aov")],
            ),
            meta={"primary_entity": "rental"},
        )

        all_metrics = [aov, aov_adjusted]
        qualifies, entity = is_pop_eligible_metric(
            aov_adjusted, all_metrics, [rentals_model]
        )

        assert qualifies is True
        assert entity == "rental"

    def test_derived_with_cross_model_ratio_parent_fails(self) -> None:
        """Derived metric with cross-model ratio parent doesn't qualify."""
        orders_model = SemanticModel(
            name="orders",
            model="ref('orders')",
            entities=[Entity(name="order", type="primary")],
            measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
        )
        searches_model = SemanticModel(
            name="searches",
            model="ref('searches')",
            entities=[Entity(name="search", type="primary")],
            measures=[Measure(name="search_count", agg=AggregationType.COUNT)],
        )

        # Cross-model ratio
        conversion = Metric(
            name="conversion",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count",
                denominator="search_count",
            ),
            meta={"primary_entity": "search"},
        )

        # Derived from cross-model ratio
        conversion_pct = Metric(
            name="conversion_pct",
            type="derived",
            type_params=DerivedMetricParams(
                expr="conversion * 100",
                metrics=[MetricReference(name="conversion")],
            ),
            meta={"primary_entity": "search"},
        )

        all_metrics = [conversion, conversion_pct]
        qualifies, entity = is_pop_eligible_metric(
            conversion_pct, all_metrics, [orders_model, searches_model]
        )

        assert qualifies is False
        assert entity is None

    def test_circular_reference_returns_false(self) -> None:
        """Circular reference in metric graph returns False gracefully."""
        a = Metric(
            name="metric_a",
            type="derived",
            type_params=DerivedMetricParams(
                expr="b * 2",
                metrics=[MetricReference(name="metric_b", alias="b")],
            ),
            meta={"primary_entity": "entity"},
        )
        b = Metric(
            name="metric_b",
            type="derived",
            type_params=DerivedMetricParams(
                expr="a * 2",
                metrics=[MetricReference(name="metric_a", alias="a")],
            ),
            meta={"primary_entity": "entity"},
        )

        all_metrics = [a, b]
        qualifies, entity = is_pop_eligible_metric(a, all_metrics)

        assert qualifies is False
        assert entity is None

    def test_missing_parent_metric_returns_false(self) -> None:
        """Missing parent metric returns False gracefully."""
        derived = Metric(
            name="derived",
            type="derived",
            type_params=DerivedMetricParams(
                expr="missing + 1",
                metrics=[MetricReference(name="nonexistent", alias="missing")],
            ),
            meta={"primary_entity": "entity"},
        )

        qualifies, entity = is_pop_eligible_metric(derived, [derived])

        assert qualifies is False
        assert entity is None

    def test_derived_without_all_metrics_fails(self) -> None:
        """Derived metric without all_metrics parameter fails."""
        derived = Metric(
            name="derived",
            type="derived",
            type_params=DerivedMetricParams(
                expr="a + b",
                metrics=[MetricReference(name="a"), MetricReference(name="b")],
            ),
        )

        qualifies, entity = is_pop_eligible_metric(derived)  # No all_metrics
        assert qualifies is False
        assert entity is None


class TestConversionMetricPopEligibility:
    """Tests for conversion metric PoP eligibility (not supported)."""

    def test_conversion_metric_fails(self) -> None:
        """Conversion metrics are not supported for PoP."""
        from dbt_to_lookml.schemas.semantic_layer import ConversionMetricParams

        conversion = Metric(
            name="funnel_conversion",
            type="conversion",
            type_params=ConversionMetricParams(
                conversion_type_params={"entity": "user", "calculation": "rate"}
            ),
            meta={"primary_entity": "user"},
        )

        qualifies, entity = is_pop_eligible_metric(conversion)
        assert qualifies is False
        assert entity is None


class TestBackwardsCompatibility:
    """Tests for backwards compatibility with is_same_model_derived_metric."""

    def test_old_function_still_works_for_derived(self) -> None:
        """Old function name still works for derived metrics."""
        gained = Metric(
            name="gained_eom",
            type="simple",
            type_params=SimpleMetricParams(measure="gained_count"),
            meta={"primary_entity": "facility"},
        )
        lost = Metric(
            name="lost_eom",
            type="simple",
            type_params=SimpleMetricParams(measure="lost_count"),
            meta={"primary_entity": "facility"},
        )
        net_change = Metric(
            name="net_change_eom",
            type="derived",
            type_params=DerivedMetricParams(
                expr="gained - lost",
                metrics=[
                    MetricReference(name="gained_eom", alias="gained"),
                    MetricReference(name="lost_eom", alias="lost"),
                ],
            ),
        )

        all_metrics = [gained, lost, net_change]
        qualifies, entity = is_same_model_derived_metric(net_change, all_metrics)

        assert qualifies is True
        assert entity == "facility"

    def test_old_function_returns_false_for_simple(self) -> None:
        """Old function returns False for simple metrics (not derived)."""
        simple = Metric(
            name="revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="total_revenue"),
            meta={"primary_entity": "order"},
        )

        qualifies, entity = is_same_model_derived_metric(simple, [simple])
        assert qualifies is False
        assert entity is None

    def test_old_function_returns_false_for_ratio(self) -> None:
        """Old function returns False for ratio metrics (not derived)."""
        ratio = Metric(
            name="aov",
            type="ratio",
            type_params=RatioMetricParams(numerator="gov", denominator="count"),
            meta={"primary_entity": "rental"},
        )

        qualifies, entity = is_same_model_derived_metric(ratio, [ratio])
        assert qualifies is False
        assert entity is None
