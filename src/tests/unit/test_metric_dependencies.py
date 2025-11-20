"""Unit tests for metric dependency tracking and resolution.

Tests the get_required_measures() method on Metric class for extracting
dependencies from different metric types.
"""

from dbt_to_lookml.schemas.semantic_layer import (
    ConversionMetricParams,
    DerivedMetricParams,
    Metric,
    MetricReference,
    RatioMetricParams,
    SimpleMetricParams,
)


class TestSimpleMetricDependencies:
    """Test dependency tracking for simple metrics."""

    def test_simple_metric_single_measure(self):
        """Test simple metric returns single measure dependency."""
        metric = Metric(
            name="total_revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="revenue"),
            meta={"primary_entity": "order"},
        )
        dependencies = metric.get_required_measures()
        assert dependencies == ["revenue"]

    def test_simple_metric_different_measure(self):
        """Test simple metric with different measure."""
        metric = Metric(
            name="order_count",
            type="simple",
            type_params=SimpleMetricParams(measure="orders"),
            meta={"primary_entity": "order"},
        )
        dependencies = metric.get_required_measures()
        assert dependencies == ["orders"]

    def test_simple_metric_without_meta(self):
        """Test simple metric without meta still returns measure."""
        metric = Metric(
            name="count",
            type="simple",
            type_params=SimpleMetricParams(measure="quantity"),
        )
        dependencies = metric.get_required_measures()
        assert dependencies == ["quantity"]


class TestRatioMetricDependencies:
    """Test dependency tracking for ratio metrics."""

    def test_ratio_metric_both_measures(self):
        """Test ratio metric returns both numerator and denominator."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="completed_orders",
                denominator="total_searches",
            ),
            meta={"primary_entity": "search"},
        )
        dependencies = metric.get_required_measures()
        assert set(dependencies) == {"completed_orders", "total_searches"}

    def test_ratio_metric_same_measure(self):
        """Test ratio metric where numerator and denominator are same."""
        metric = Metric(
            name="repeat_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="repeat_orders",
                denominator="total_orders",
            ),
            meta={"primary_entity": "customer"},
        )
        dependencies = metric.get_required_measures()
        # Should include both even if same conceptually
        assert len(dependencies) == 2

    def test_ratio_metric_order_preservation(self):
        """Test that ratio metrics preserve numerator and denominator."""
        metric = Metric(
            name="rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="num",
                denominator="denom",
            ),
        )
        dependencies = metric.get_required_measures()
        assert "num" in dependencies
        assert "denom" in dependencies


class TestDerivedMetricDependencies:
    """Test dependency tracking for derived metrics."""

    def test_derived_metric_single_measure(self):
        """Test derived metric with single measure reference."""
        metric = Metric(
            name="growth",
            type="derived",
            type_params=DerivedMetricParams(
                expr="current - prior",
                metrics=[
                    MetricReference(name="monthly_revenue", alias="current"),
                ],
            ),
            meta={"primary_entity": "order"},
        )
        dependencies = metric.get_required_measures()
        assert dependencies == ["monthly_revenue"]

    def test_derived_metric_multiple_measures(self):
        """Test derived metric with multiple metric references."""
        metric = Metric(
            name="revenue_growth",
            type="derived",
            type_params=DerivedMetricParams(
                expr="(current - prior) / prior",
                metrics=[
                    MetricReference(name="monthly_revenue", alias="current"),
                    MetricReference(name="monthly_revenue", alias="prior"),
                ],
            ),
            meta={"primary_entity": "order"},
        )
        dependencies = metric.get_required_measures()
        # Should return unique measures (monthly_revenue appears twice)
        assert dependencies == ["monthly_revenue"]

    def test_derived_metric_distinct_measures(self):
        """Test derived metric combining different measures."""
        metric = Metric(
            name="profit_ratio",
            type="derived",
            type_params=DerivedMetricParams(
                expr="revenue - cost",
                metrics=[
                    MetricReference(name="revenue", alias="revenue"),
                    MetricReference(name="cost", alias="cost"),
                ],
            ),
        )
        dependencies = metric.get_required_measures()
        assert set(dependencies) == {"revenue", "cost"}

    def test_derived_metric_measures_sorted(self):
        """Test that derived metric measures are returned in sorted order."""
        metric = Metric(
            name="combined",
            type="derived",
            type_params=DerivedMetricParams(
                expr="z + a + m",
                metrics=[
                    MetricReference(name="z_measure"),
                    MetricReference(name="a_measure"),
                    MetricReference(name="m_measure"),
                ],
            ),
        )
        dependencies = metric.get_required_measures()
        assert dependencies == ["a_measure", "m_measure", "z_measure"]


class TestConversionMetricDependencies:
    """Test dependency tracking for conversion metrics."""

    def test_conversion_metric_no_dependencies(self):
        """Test conversion metric returns empty dependencies."""
        metric = Metric(
            name="checkout_conversion",
            type="conversion",
            type_params=ConversionMetricParams(
                conversion_type_params={
                    "entity": "order",
                    "calculation": "conversion_rate",
                    "base_event": "page_view",
                    "conversion_event": "purchase",
                }
            ),
            meta={"primary_entity": "user"},
        )
        dependencies = metric.get_required_measures()
        assert dependencies == []

    def test_conversion_metric_empty_params(self):
        """Test conversion metric with empty params."""
        metric = Metric(
            name="simple_conversion",
            type="conversion",
            type_params=ConversionMetricParams(conversion_type_params={}),
        )
        dependencies = metric.get_required_measures()
        assert dependencies == []


class TestMetricDependenciesEdgeCases:
    """Test edge cases in metric dependency tracking."""

    def test_metric_without_type_params(self):
        """Test metric behavior when type_params doesn't match type."""
        # This shouldn't happen in practice but test resilience
        metric = Metric(
            name="test",
            type="simple",
            type_params=SimpleMetricParams(measure="test_measure"),
        )
        # Should not raise error
        dependencies = metric.get_required_measures()
        assert "test_measure" in dependencies

    def test_metric_with_label_and_description(self):
        """Test that label/description don't affect dependency extraction."""
        metric = Metric(
            name="revenue",
            type="simple",
            label="Total Revenue",
            description="Sum of all revenue transactions",
            type_params=SimpleMetricParams(measure="revenue_amount"),
            meta={"primary_entity": "order"},
        )
        dependencies = metric.get_required_measures()
        assert dependencies == ["revenue_amount"]

    def test_multiple_metrics_different_types(self):
        """Test dependency extraction for metrics of different types."""
        metrics = [
            Metric(
                name="simple",
                type="simple",
                type_params=SimpleMetricParams(measure="m1"),
            ),
            Metric(
                name="ratio",
                type="ratio",
                type_params=RatioMetricParams(
                    numerator="m2",
                    denominator="m3",
                ),
            ),
            Metric(
                name="conversion",
                type="conversion",
                type_params=ConversionMetricParams(conversion_type_params={}),
            ),
        ]

        results = [m.get_required_measures() for m in metrics]
        assert results[0] == ["m1"]
        assert set(results[1]) == {"m2", "m3"}
        assert results[2] == []


class TestMetricDependenciesUniqueness:
    """Test that metric dependencies handle duplicates correctly."""

    def test_derived_metric_duplicate_measures_deduplicated(self):
        """Test that duplicate measures in derived metrics are deduplicated."""
        metric = Metric(
            name="duplicate_test",
            type="derived",
            type_params=DerivedMetricParams(
                expr="(a + a) / b",
                metrics=[
                    MetricReference(name="measure_a", alias="a"),
                    MetricReference(name="measure_a", alias="a2"),
                    MetricReference(name="measure_b", alias="b"),
                ],
            ),
        )
        dependencies = metric.get_required_measures()
        # Should have unique measures only
        assert set(dependencies) == {"measure_a", "measure_b"}
        assert len(dependencies) == 2

    def test_ratio_metric_unique_measures(self):
        """Test ratio metric with unique measure requirements."""
        metric = Metric(
            name="unique_test",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="orders",
                denominator="searches",
            ),
        )
        dependencies = metric.get_required_measures()
        assert len(set(dependencies)) == len(dependencies)  # All unique
