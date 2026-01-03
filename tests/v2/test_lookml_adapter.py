"""Tests for LookML adapter."""

import pytest

from dbt_to_lookml_v2.domain import (
    AggregationType,
    ConnectionType,
    DataModel,
    Dimension,
    DimensionType,
    Entity,
    Measure,
    Metric,
    MetricType,
    MetricVariant,
    PopComparison,
    PopConfig,
    PopOutput,
    ProcessedModel,
    TimeGranularity,
)
from dbt_to_lookml_v2.adapters import Dialect, SqlRenderer
from dbt_to_lookml_v2.adapters.lookml import (
    DimensionRenderer,
    LookMLGenerator,
    MeasureRenderer,
    PopRenderer,
    ViewRenderer,
)


class TestDialect:
    """Tests for dialect handling."""

    def test_default_dialect_is_redshift(self):
        renderer = SqlRenderer()
        assert renderer.dialect == Dialect.REDSHIFT

    def test_qualify_expression_simple(self):
        renderer = SqlRenderer(Dialect.REDSHIFT)
        result = renderer.qualify_expression("rental_status")
        # sqlglot quotes identifiers
        assert "rental_status" in result
        assert "${TABLE}" in result

    def test_qualify_expression_complex(self):
        renderer = SqlRenderer(Dialect.REDSHIFT)
        expr = "CASE WHEN status = 'active' THEN 1 ELSE 0 END"
        result = renderer.qualify_expression(expr)
        # sqlglot quotes identifiers
        assert "status" in result
        assert "${TABLE}" in result

    def test_extract_columns(self):
        renderer = SqlRenderer(Dialect.REDSHIFT)
        cols = renderer.extract_columns("a + b - c")
        assert set(cols) == {"a", "b", "c"}


class TestDimensionRenderer:
    """Tests for dimension rendering."""

    def test_render_categorical_dimension(self):
        dim = Dimension(
            name="status",
            type=DimensionType.CATEGORICAL,
            expr="rental_status",
            label="Status",
        )
        renderer = DimensionRenderer()
        result = renderer.render(dim)

        assert len(result) == 1
        assert result[0]["name"] == "status"
        assert result[0]["type"] == "string"
        assert result[0]["label"] == "Status"

    def test_render_time_dimension(self):
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            expr="created_at_utc",
            granularity=TimeGranularity.DAY,
        )
        renderer = DimensionRenderer()
        result = renderer.render(dim)

        assert len(result) == 1
        assert result[0]["name"] == "created_at"
        assert result[0]["type"] == "time"
        assert "date" in result[0]["timeframes"]

    def test_render_time_dimension_with_variants(self):
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            granularity=TimeGranularity.DAY,
            primary_variant="utc",
            variants={
                "utc": "created_at_utc",
                "local": "created_at_local",
            },
        )
        renderer = DimensionRenderer()
        result = renderer.render(dim)

        # Should generate 2 dimension_groups
        assert len(result) == 2
        names = {r["name"] for r in result}
        assert names == {"created_at_utc", "created_at_local"}


class TestMeasureRenderer:
    """Tests for measure rendering."""

    def test_render_sum_measure(self):
        measure = Measure(
            name="total_revenue",
            agg=AggregationType.SUM,
            expr="amount",
            format="usd",
        )
        renderer = MeasureRenderer()
        result = renderer.render_measure(measure)

        assert result["name"] == "total_revenue"
        assert result["type"] == "sum"
        assert result["value_format_name"] == "usd"

    def test_render_simple_metric(self):
        measure = Measure(
            name="amount",
            agg=AggregationType.SUM,
            expr="checkout_amount",
        )
        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="amount",
            label="Gross Merchandise Value",
            format="usd",
        )
        renderer = MeasureRenderer()
        result = renderer.render_metric(metric, {"amount": measure})

        assert result["name"] == "gmv"
        assert result["type"] == "sum"
        assert result["label"] == "Gross Merchandise Value"

    def test_render_derived_metric(self):
        metric = Metric(
            name="aov",
            type=MetricType.DERIVED,
            expr="gmv / NULLIF(rental_count, 0)",
            metrics=["gmv", "rental_count"],
        )
        renderer = MeasureRenderer()
        result = renderer.render_metric(metric, {})

        assert result["name"] == "aov"
        assert result["type"] == "number"
        assert "${gmv}" in result["sql"]
        assert "${rental_count}" in result["sql"]


class TestPopRenderer:
    """Tests for PoP rendering."""

    def test_render_pop_variant(self):
        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="GMV",
            format="usd",
        )
        metric.variants = [
            MetricVariant.base(),
            MetricVariant.pop(PopComparison.PRIOR_YEAR, PopOutput.PREVIOUS),
        ]

        renderer = PopRenderer()
        results = renderer.render_variants(metric)

        assert len(results) == 1
        assert results[0]["name"] == "gmv_py"
        assert results[0]["type"] == "period_over_period"
        assert results[0]["based_on"] == "gmv"
        assert results[0]["comparison_period"] == "year"

    def test_render_multiple_pop_variants(self):
        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            pop=PopConfig(
                comparisons=[PopComparison.PRIOR_YEAR, PopComparison.PRIOR_MONTH],
                outputs=[PopOutput.PREVIOUS, PopOutput.PERCENT_CHANGE],
            ),
        )
        metric.expand_variants()

        renderer = PopRenderer()
        results = renderer.render_variants(metric)

        # 2 comparisons × 2 outputs = 4 PoP variants
        assert len(results) == 4
        names = {r["name"] for r in results}
        assert "gmv_py" in names
        assert "gmv_py_pct_change" in names
        assert "gmv_pm" in names
        assert "gmv_pm_pct_change" in names


class TestViewRenderer:
    """Tests for view rendering."""

    def test_render_base_view(self):
        model = ProcessedModel(
            name="rentals",
            data_model=DataModel(
                name="rentals",
                schema_name="gold",
                table="rentals",
                connection=ConnectionType.REDSHIFT,
            ),
            dimensions=[
                Dimension(name="status", type=DimensionType.CATEGORICAL, expr="status"),
            ],
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
            ],
        )

        renderer = ViewRenderer()
        result = renderer.render_base_view(model)

        assert result["name"] == "rentals"
        assert result["sql_table_name"] == "gold.rentals"
        assert len(result["dimensions"]) == 2  # 1 dim + 1 entity

    def test_render_metrics_refinement(self):
        model = ProcessedModel(
            name="rentals",
            measures=[
                Measure(name="amount", agg=AggregationType.SUM, expr="amount"),
            ],
            metrics=[
                Metric(name="gmv", type=MetricType.SIMPLE, measure="amount"),
            ],
        )

        renderer = ViewRenderer()
        result = renderer.render_metrics_refinement(model)

        assert result is not None
        assert result["name"] == "+rentals"  # Refinement syntax
        assert len(result["measures"]) == 1

    def test_render_pop_refinement(self):
        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="amount",
            pop=PopConfig(
                comparisons=[PopComparison.PRIOR_YEAR],
                outputs=[PopOutput.PREVIOUS],
            ),
        )
        metric.expand_variants()

        model = ProcessedModel(
            name="rentals",
            metrics=[metric],
        )

        renderer = ViewRenderer()
        result = renderer.render_pop_refinement(model)

        assert result is not None
        assert result["name"] == "+rentals"
        assert len(result["measures"]) == 1
        assert result["measures"][0]["type"] == "period_over_period"


class TestLookMLGenerator:
    """Tests for LookML generator."""

    def test_generate_single_model(self):
        model = ProcessedModel(
            name="rentals",
            data_model=DataModel(
                name="rentals",
                schema_name="gold",
                table="rentals",
                connection=ConnectionType.REDSHIFT,
            ),
            dimensions=[
                Dimension(name="status", type=DimensionType.CATEGORICAL, expr="status"),
            ],
            measures=[
                Measure(name="amount", agg=AggregationType.SUM, expr="amount", hidden=True),
            ],
            metrics=[
                Metric(name="gmv", type=MetricType.SIMPLE, measure="amount"),
            ],
        )

        generator = LookMLGenerator()
        files = generator.generate_model(model)

        assert "rentals.view.lkml" in files
        assert "rentals.metrics.view.lkml" in files
        assert "rentals.pop.view.lkml" not in files  # No PoP

    def test_generate_with_pop(self):
        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="amount",
            pop=PopConfig(
                comparisons=[PopComparison.PRIOR_YEAR],
                outputs=[PopOutput.PREVIOUS],
            ),
        )
        metric.expand_variants()

        model = ProcessedModel(
            name="rentals",
            metrics=[metric],
        )

        generator = LookMLGenerator()
        files = generator.generate_model(model)

        assert "rentals.view.lkml" in files
        assert "rentals.metrics.view.lkml" in files
        assert "rentals.pop.view.lkml" in files

    def test_generated_content_is_valid_lookml(self):
        model = ProcessedModel(
            name="rentals",
            dimensions=[
                Dimension(name="status", type=DimensionType.CATEGORICAL, expr="status"),
            ],
        )

        generator = LookMLGenerator()
        files = generator.generate_model(model)

        # Should be parseable LookML
        content = files["rentals.view.lkml"]
        assert "view: rentals" in content
        assert "dimension: status" in content
