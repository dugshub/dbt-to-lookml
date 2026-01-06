"""
Tests for v2 domain primitives.

Phase 1 Gate: These tests verify that domain types compile and instantiate correctly.
"""

import pytest

from semantic_patterns.domain import (
    # Measure
    AggregationType,
    # Data Model
    ConnectionType,
    DataModel,
    # Model
    DateSelectorConfig,
    # Dimension
    Dimension,
    DimensionType,
    Entity,
    # Filter
    Filter,
    FilterOperator,
    Measure,
    # Metric
    Metric,
    MetricType,
    MetricVariant,
    PopComparison,
    PopConfig,
    PopOutput,
    ProcessedModel,
    TimeGranularity,
    VariantKind,
)


class TestDataModel:
    """Tests for DataModel."""

    def test_create_data_model(self):
        dm = DataModel(
            name="rentals",
            schema_name="gold_production",
            table="rentals",
            connection=ConnectionType.REDSHIFT,
        )
        assert dm.name == "rentals"
        assert dm.fully_qualified == "gold_production.rentals"

    def test_data_model_with_catalog(self):
        dm = DataModel(
            name="rentals",
            catalog="analytics",
            schema_name="gold_production",
            table="rentals",
            connection=ConnectionType.STARBURST,
        )
        assert dm.fully_qualified == "analytics.gold_production.rentals"


class TestMeasure:
    """Tests for Measure primitive."""

    def test_create_simple_measure(self):
        measure = Measure(
            name="total_revenue",
            agg=AggregationType.SUM,
            expr="checkout_amount",
            description="Sum of checkout amounts",
        )
        assert measure.name == "total_revenue"
        assert measure.agg == AggregationType.SUM
        assert measure.expr == "checkout_amount"

    def test_measure_with_meta(self):
        measure = Measure(
            name="rental_count",
            agg=AggregationType.COUNT_DISTINCT,
            expr="rental_id",
            meta={"category": "Transaction Metrics"},
        )
        assert measure.meta["category"] == "Transaction Metrics"

    def test_measure_with_group_and_format(self):
        measure = Measure(
            name="checkout_amount",
            agg=AggregationType.SUM,
            expr="rental_checkout_amount_local",
            format="usd",
            group="Revenue.Core",
            hidden=True,
        )
        assert measure.format == "usd"
        assert measure.group_parts == ["Revenue", "Core"]
        assert measure.hidden is True


class TestDimension:
    """Tests for Dimension primitive."""

    def test_create_categorical_dimension(self):
        dim = Dimension(
            name="rental_status",
            type=DimensionType.CATEGORICAL,
            expr="rental_status",
        )
        assert dim.name == "rental_status"
        assert dim.type == DimensionType.CATEGORICAL

    def test_create_time_dimension(self):
        dim = Dimension(
            name="created_date",
            type=DimensionType.TIME,
            expr="rental_created_at",
            granularity=TimeGranularity.DAY,
        )
        assert dim.type == DimensionType.TIME
        assert dim.granularity == TimeGranularity.DAY

    def test_time_dimension_with_variants(self):
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            granularity=TimeGranularity.DAY,
            primary_variant="utc",
            variants={
                "utc": "rental_created_at_utc",
                "local": "rental_created_at_local",
            },
        )
        assert dim.has_variants is True
        assert dim.effective_expr == "rental_created_at_utc"

    def test_dimension_requires_expr_or_variants(self):
        with pytest.raises(
            ValueError, match="Either 'expr' or 'variants' must be specified"
        ):
            Dimension(
                name="bad_dim",
                type=DimensionType.CATEGORICAL,
            )

    def test_dimension_group_parsing(self):
        dim = Dimension(
            name="status",
            type=DimensionType.CATEGORICAL,
            expr="status",
            group="Reservation.Status",
        )
        assert dim.group_parts == ["Reservation", "Status"]


class TestFilter:
    """Tests for Filter types."""

    def test_filter_from_dict_equals(self):
        f = Filter.from_dict({"transaction_type": "completed"})
        assert len(f.conditions) == 1
        assert f.conditions[0].field == "transaction_type"
        assert f.conditions[0].operator == FilterOperator.EQUALS
        assert f.conditions[0].value == "completed"

    def test_filter_from_dict_in(self):
        f = Filter.from_dict({"segment": ["Monthly", "Event"]})
        assert f.conditions[0].operator == FilterOperator.IN
        assert f.conditions[0].value == ["Monthly", "Event"]

    def test_filter_from_dict_comparison(self):
        f = Filter.from_dict({"amount": ">10"})
        assert f.conditions[0].operator == FilterOperator.GREATER_THAN
        assert f.conditions[0].value == 10

    def test_filter_from_dict_gte(self):
        f = Filter.from_dict({"count": ">=5"})
        assert f.conditions[0].operator == FilterOperator.GREATER_THAN_OR_EQUALS
        assert f.conditions[0].value == 5

    def test_filter_multiple_conditions(self):
        f = Filter.from_dict(
            {
                "transaction_type": "completed",
                "amount": ">100",
            }
        )
        assert len(f.conditions) == 2


class TestPopConfig:
    """Tests for PopConfig."""

    def test_pop_config_expand(self):
        config = PopConfig(
            comparisons=[PopComparison.PRIOR_YEAR, PopComparison.PRIOR_MONTH],
            outputs=[PopOutput.PREVIOUS, PopOutput.CHANGE],
        )
        variants = config.expand_variants()
        assert len(variants) == 4  # 2 comparisons * 2 outputs

    def test_pop_config_expand_with_format(self):
        config = PopConfig(
            comparisons=[PopComparison.PRIOR_YEAR],
            outputs=[PopOutput.PREVIOUS],
        )
        variants = config.expand_variants(value_format="usd")
        assert variants[0].value_format == "usd"


class TestMetricVariant:
    """Tests for MetricVariant."""

    def test_base_variant(self):
        variant = MetricVariant.base()
        assert variant.kind == VariantKind.BASE
        assert variant.suffix == ""

    def test_pop_variant_previous(self):
        variant = MetricVariant.pop(
            comparison=PopComparison.PRIOR_YEAR,
            output=PopOutput.PREVIOUS,
        )
        assert variant.kind == VariantKind.POP
        assert variant.suffix == "_py"

    def test_pop_variant_change(self):
        variant = MetricVariant.pop(
            comparison=PopComparison.PRIOR_YEAR,
            output=PopOutput.CHANGE,
        )
        assert variant.suffix == "_py_change"

    def test_pop_variant_pct_change(self):
        variant = MetricVariant.pop(
            comparison=PopComparison.PRIOR_MONTH,
            output=PopOutput.PERCENT_CHANGE,
        )
        assert variant.suffix == "_pm_pct_change"

    def test_benchmark_variant(self):
        variant = MetricVariant.benchmark(slice="market")
        assert variant.kind == VariantKind.BENCHMARK
        assert variant.suffix == "_vs_market"

    def test_resolve_name(self):
        """Variant names are derived from parent metric."""
        metric = Metric(name="gmv", type=MetricType.SIMPLE, measure="total_gmv")
        variant = MetricVariant.pop(
            comparison=PopComparison.PRIOR_YEAR,
            output=PopOutput.PREVIOUS,
        )
        assert variant.resolve_name(metric) == "gmv_py"


class TestMetric:
    """Tests for Metric primitive."""

    def test_create_simple_metric(self):
        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
        )
        assert metric.name == "gmv"
        assert metric.type == MetricType.SIMPLE
        assert metric.measure == "total_gmv"
        assert metric.variant_count == 0  # No variants yet

    def test_metric_with_variants(self):
        """Metric owns its variants - not separate entities."""
        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            variants=[
                MetricVariant.base(),
                MetricVariant.pop(PopComparison.PRIOR_YEAR, PopOutput.PREVIOUS),
                MetricVariant.pop(PopComparison.PRIOR_YEAR, PopOutput.CHANGE),
                MetricVariant.pop(PopComparison.PRIOR_YEAR, PopOutput.PERCENT_CHANGE),
                MetricVariant.pop(PopComparison.PRIOR_MONTH, PopOutput.PREVIOUS),
                MetricVariant.pop(PopComparison.PRIOR_MONTH, PopOutput.CHANGE),
                MetricVariant.pop(PopComparison.PRIOR_MONTH, PopOutput.PERCENT_CHANGE),
            ],
        )
        # Still ONE metric, with 7 variants
        assert metric.name == "gmv"
        assert metric.variant_count == 7
        assert metric.has_pop is True
        assert metric.has_benchmark is False

    def test_derived_metric(self):
        metric = Metric(
            name="gmv_per_facility",
            type=MetricType.DERIVED,
            expr="gmv / NULLIF(facility_count, 0)",
            metrics=["gmv", "facility_count"],
        )
        assert metric.type == MetricType.DERIVED
        assert metric.expr == "gmv / NULLIF(facility_count, 0)"
        assert metric.metrics == ["gmv", "facility_count"]

    def test_ratio_metric(self):
        metric = Metric(
            name="conversion_rate",
            type=MetricType.RATIO,
            numerator="rental_count",
            denominator="search_count",
            format="percent_2",
        )
        assert metric.type == MetricType.RATIO
        assert metric.numerator == "rental_count"
        assert metric.denominator == "search_count"

    def test_metric_with_pop_config(self):
        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            pop=PopConfig(
                comparisons=[PopComparison.PRIOR_YEAR, PopComparison.PRIOR_MONTH],
                outputs=[
                    PopOutput.PREVIOUS,
                    PopOutput.CHANGE,
                    PopOutput.PERCENT_CHANGE,
                ],
            ),
            format="usd",
        )
        metric.expand_variants()
        # 1 base + 6 PoP (2 comparisons * 3 outputs)
        assert metric.variant_count == 7
        assert metric.has_pop is True

    def test_metric_group_parsing(self):
        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            group="Metrics.Revenue",
        )
        assert metric.group_parts == ["Metrics", "Revenue"]


class TestEntity:
    """Tests for Entity."""

    def test_create_entity(self):
        entity = Entity(name="rental", type="primary", expr="unique_rental_sk")
        assert entity.name == "rental"
        assert entity.type == "primary"
        assert entity.expr == "unique_rental_sk"

    def test_entity_with_label(self):
        entity = Entity(
            name="rental",
            type="primary",
            expr="unique_rental_sk",
            label="Reservation",
        )
        assert entity.label == "Reservation"


class TestProcessedModel:
    """Tests for ProcessedModel container."""

    def test_create_processed_model(self):
        dm = DataModel(
            name="rentals",
            schema_name="gold_production",
            table="rentals",
            connection=ConnectionType.REDSHIFT,
        )
        model = ProcessedModel(
            name="rentals",
            description="Rental fact model",
            data_model=dm,
        )
        assert model.name == "rentals"
        assert model.sql_table_name == "gold_production.rentals"

    def test_model_with_primitives(self):
        model = ProcessedModel(
            name="rentals",
            measures=[
                Measure(name="total_revenue", agg=AggregationType.SUM, expr="amount"),
            ],
            dimensions=[
                Dimension(name="status", type=DimensionType.CATEGORICAL, expr="status"),
                Dimension(
                    name="created_at", type=DimensionType.TIME, expr="created_at"
                ),
            ],
            metrics=[
                Metric(
                    name="revenue",
                    type=MetricType.SIMPLE,
                    measure="total_revenue",
                    variants=[MetricVariant.base()],
                ),
            ],
        )
        assert len(model.measures) == 1
        assert len(model.dimensions) == 2
        assert len(model.metrics) == 1
        assert len(model.time_dimensions) == 1
        assert len(model.categorical_dimensions) == 1

    def test_model_with_entities(self):
        model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
                Entity(name="facility", type="foreign", expr="facility_sk"),
                Entity(name="user", type="foreign", expr="user_sk"),
            ],
        )
        assert model.primary_entity is not None
        assert model.primary_entity.name == "rental"
        assert len(model.foreign_entities) == 2

    def test_model_with_date_selector(self):
        model = ProcessedModel(
            name="rentals",
            time_dimension="created_at",
            date_selector=DateSelectorConfig(dimensions=["created_at", "starts_at"]),
            dimensions=[
                Dimension(
                    name="created_at", type=DimensionType.TIME, expr="created_at"
                ),
                Dimension(name="starts_at", type=DimensionType.TIME, expr="starts_at"),
                Dimension(name="ends_at", type=DimensionType.TIME, expr="ends_at"),
            ],
        )
        assert len(model.date_selector_dimensions) == 2
        assert model.default_time_dimension is not None
        assert model.default_time_dimension.name == "created_at"

    def test_model_summary(self):
        """Summary provides quick overview."""
        model = ProcessedModel(
            name="rentals",
            measures=[Measure(name="m1", agg=AggregationType.SUM, expr="x")],
            dimensions=[Dimension(name="d1", type=DimensionType.CATEGORICAL, expr="y")],
            metrics=[
                Metric(
                    name="metric1",
                    type=MetricType.SIMPLE,
                    measure="m1",
                    variants=[
                        MetricVariant.base(),
                        MetricVariant.pop(PopComparison.PRIOR_YEAR, PopOutput.PREVIOUS),
                    ],
                ),
            ],
        )
        summary = model.summary()
        assert "rentals" in summary
        assert "1 measures" in summary
        assert "1 dimensions" in summary
        assert "1 metrics" in summary
        assert "2 variants" in summary

    def test_total_variant_count(self):
        """10 metrics with 7 variants each = 70 variants total."""
        metrics = [
            Metric(
                name=f"metric_{i}",
                type=MetricType.SIMPLE,
                measure="m1",
                variants=[MetricVariant.base()]
                + [
                    MetricVariant.pop(comp, out)
                    for comp in [PopComparison.PRIOR_YEAR, PopComparison.PRIOR_MONTH]
                    for out in [
                        PopOutput.PREVIOUS,
                        PopOutput.CHANGE,
                        PopOutput.PERCENT_CHANGE,
                    ]
                ],
            )
            for i in range(10)
        ]
        model = ProcessedModel(name="test", metrics=metrics)

        # 10 metrics, each with 7 variants (1 base + 6 PoP)
        assert len(model.metrics) == 10
        assert model.total_variant_count == 70
