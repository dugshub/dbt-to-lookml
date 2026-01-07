"""Tests for LookML adapter."""


from semantic_patterns.adapters import Dialect, SqlRenderer
from semantic_patterns.adapters.lookml import (
    DimensionRenderer,
    LookMLGenerator,
    MeasureRenderer,
    PopRenderer,
    ViewRenderer,
)
from semantic_patterns.adapters.lookml.renderers.calendar import (
    CalendarRenderer,
    DateOption,
    PopCalendarConfig,
)
from semantic_patterns.adapters.lookml.renderers.pop import DynamicFilteredPopStrategy
from semantic_patterns.domain import (
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


class TestDialect:
    """Tests for dialect handling."""

    def test_default_dialect_is_redshift(self):
        renderer = SqlRenderer()
        assert renderer.dialect == Dialect.REDSHIFT

    def test_qualify_expression_simple(self):
        """Test basic column qualification - SQL-pure (no LookML)."""
        renderer = SqlRenderer(Dialect.REDSHIFT)
        result = renderer.qualify_expression("rental_status")
        # Should add SQL table qualifier (not LookML ${TABLE})
        assert result == "t.rental_status"

    def test_qualify_expression_complex(self):
        """Test complex expression qualification - SQL-pure (no LookML)."""
        renderer = SqlRenderer(Dialect.REDSHIFT)
        expr = "CASE WHEN status = 'active' THEN 1 ELSE 0 END"
        result = renderer.qualify_expression(expr)
        # Should add SQL table qualifier to bare columns
        assert "t.status" in result
        assert "'active'" in result

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
        assert results[0]["period"] == "year"
        assert results[0]["kind"] == "previous"
        # based_on_time is only added when calendar_view_name is provided
        assert "based_on_time" not in results[0]

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
        view, includes = result
        assert view["name"] == "+rentals"  # Refinement syntax
        assert len(view["measures"]) == 1
        assert "rentals.view.lkml" in includes

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

        # Provide model-to-explore mapping for PoP calendar reference
        model_to_explore = {"rentals": "rentals"}
        renderer = ViewRenderer(model_to_explore=model_to_explore)
        result = renderer.render_pop_refinement(model)

        assert result is not None
        view, includes = result
        assert view["name"] == "+rentals"
        assert len(view["measures"]) == 1
        assert view["measures"][0]["type"] == "period_over_period"
        assert "rentals.view.lkml" in includes
        assert "rentals.metrics.view.lkml" in includes


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
                Measure(
                    name="amount", agg=AggregationType.SUM, expr="amount", hidden=True
                ),
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

        # Provide model-to-explore mapping for PoP generation
        model_to_explore = {"rentals": "rentals"}
        generator = LookMLGenerator(model_to_explore=model_to_explore)
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


class TestDynamicFilteredPopStrategy:
    """Tests for DynamicFilteredPopStrategy."""

    def test_render_prior_measure(self):
        """Test rendering the _prior filtered measure."""
        strategy = DynamicFilteredPopStrategy("rentals_explore_calendar")

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="GMV",
            format="usd",
            group="Metrics.Revenue",  # Two-level group for view_label + group_label
            pop=PopConfig(
                comparisons=[PopComparison.PRIOR_YEAR],
                outputs=[PopOutput.PREVIOUS],
            ),
        )

        result = strategy._render_prior(metric)

        assert result["name"] == "gmv_prior"
        assert result["type"] == "sum"
        assert result["label"] == "GMV (PoP)"
        assert result["value_format_name"] == "usd"
        assert (
            result["filters"][0]["field"]
            == "rentals_explore_calendar.is_comparison_period"
        )
        assert result["filters"][0]["value"] == "yes"
        assert result["view_label"] == "  Metrics (PoP)"  # PoP always goes to Metrics (PoP)
        assert result["group_label"] == "Revenue · GMV"  # Category · Metric Label

    def test_render_change_measure(self):
        """Test rendering the _change measure."""
        strategy = DynamicFilteredPopStrategy("rentals_explore_calendar")

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="GMV",
            format="usd",
        )

        result = strategy._render_change(metric)

        assert result["name"] == "gmv_change"
        assert result["type"] == "number"
        assert result["label"] == "GMV Change"
        assert "${gmv}" in result["sql"]
        assert "${gmv_prior}" in result["sql"]

    def test_render_pct_change_measure(self):
        """Test rendering the _pct_change measure."""
        strategy = DynamicFilteredPopStrategy("rentals_explore_calendar")

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
        )

        result = strategy._render_pct_change(metric)

        assert result["name"] == "gmv_pct_change"
        assert result["type"] == "number"
        assert result["value_format_name"] == "percent_1"
        assert "NULLIF" in result["sql"]

    def test_render_all_outputs(self):
        """Test render_all generates all configured outputs."""
        strategy = DynamicFilteredPopStrategy("rentals_explore_calendar")

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
        )

        results = strategy.render_all(metric)

        # Should generate exactly 3 measures (one per output), not 6 (comparisons × outputs)
        assert len(results) == 3
        names = {r["name"] for r in results}
        assert names == {"gmv_prior", "gmv_change", "gmv_pct_change"}

    def test_deduplication_via_render(self):
        """Test that render() deduplicates by output type."""
        strategy = DynamicFilteredPopStrategy("rentals_explore_calendar")

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            pop=PopConfig(
                comparisons=[PopComparison.PRIOR_YEAR, PopComparison.PRIOR_MONTH],
                outputs=[PopOutput.PREVIOUS],
            ),
        )
        metric.expand_variants()

        # Should have 2 variants (py-previous, pm-previous)
        pop_variants = [v for v in metric.variants if v.kind.value == "pop"]
        assert len(pop_variants) == 2

        # But render() should deduplicate, returning only one measure
        results = [strategy.render(metric, v) for v in pop_variants]
        # First call returns the measure, second returns None
        assert results[0] is not None
        assert results[1] is None


class TestCalendarRendererWithPoP:
    """Tests for CalendarRenderer with PoP infrastructure."""

    def test_pop_calendar_config_from_models(self):
        """Test PopCalendarConfig detects PoP metrics."""
        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            pop=PopConfig(
                comparisons=[PopComparison.PRIOR_YEAR, PopComparison.PRIOR_MONTH],
                outputs=[PopOutput.PREVIOUS],
            ),
        )

        model = ProcessedModel(name="rentals", metrics=[metric])
        config = PopCalendarConfig.from_models([model])

        assert config.enabled is True
        assert PopComparison.PRIOR_YEAR in config.comparisons
        assert PopComparison.PRIOR_MONTH in config.comparisons

    def test_pop_calendar_config_no_pop_metrics(self):
        """Test PopCalendarConfig with no PoP metrics."""
        metric = Metric(name="gmv", type=MetricType.SIMPLE, measure="total_gmv")
        model = ProcessedModel(name="rentals", metrics=[metric])
        config = PopCalendarConfig.from_models([model])

        assert config.enabled is False

    def test_calendar_render_with_pop(self):
        """Test calendar view includes PoP infrastructure when enabled."""
        renderer = CalendarRenderer(Dialect.REDSHIFT)

        date_options = [
            DateOption(
                view="rentals",
                dimension="created_at",
                label="Rental Created",
                raw_ref="${rentals.created_at_raw}",
            ),
        ]

        pop_config = PopCalendarConfig(
            enabled=True,
            comparisons=[PopComparison.PRIOR_YEAR, PopComparison.PRIOR_MONTH],
            default_comparison="year",
        )

        result = renderer.render("rentals", date_options, pop_config)

        # Should have 2 parameters: date_field and comparison_period
        assert len(result["parameters"]) == 2
        param_names = {p["name"] for p in result["parameters"]}
        assert "date_field" in param_names
        assert "comparison_period" in param_names

        # Should have date_range filter
        assert "filters" in result
        assert result["filters"][0]["name"] == "date_range"

        # Should have period dimensions
        assert "dimensions" in result
        dim_names = {d["name"] for d in result["dimensions"]}
        assert "is_selected_period" in dim_names
        assert "is_comparison_period" in dim_names

    def test_calendar_render_without_pop(self):
        """Test calendar view without PoP has no extra infrastructure."""
        renderer = CalendarRenderer(Dialect.REDSHIFT)

        date_options = [
            DateOption(
                view="rentals",
                dimension="created_at",
                label="Rental Created",
                raw_ref="${rentals.created_at_raw}",
            ),
        ]

        result = renderer.render("rentals", date_options)

        # Should only have date_field parameter
        assert len(result["parameters"]) == 1
        assert result["parameters"][0]["name"] == "date_field"

        # Should not have filters or extra dimensions
        assert "filters" not in result
        assert "dimensions" not in result


class TestDialectDateadd:
    """Tests for SqlRenderer.dateadd() method."""

    def test_redshift_dateadd(self):
        renderer = SqlRenderer(Dialect.REDSHIFT)
        result = renderer.dateadd("year", 1, "my_date")
        assert result == "DATEADD(year, 1, my_date)"

    def test_snowflake_dateadd(self):
        renderer = SqlRenderer(Dialect.SNOWFLAKE)
        result = renderer.dateadd("month", -1, "created_at")
        assert result == "DATEADD(month, -1, created_at)"

    def test_bigquery_dateadd(self):
        renderer = SqlRenderer(Dialect.BIGQUERY)
        result = renderer.dateadd("year", 1, "my_date")
        assert result == "DATE_ADD(my_date, INTERVAL 1 YEAR)"

    def test_postgres_dateadd_positive(self):
        renderer = SqlRenderer(Dialect.POSTGRES)
        result = renderer.dateadd("month", 3, "created_at")
        assert result == "created_at + INTERVAL '3 month'"

    def test_postgres_dateadd_negative(self):
        renderer = SqlRenderer(Dialect.POSTGRES)
        result = renderer.dateadd("year", -1, "created_at")
        assert result == "created_at - INTERVAL '1 year'"

    def test_duckdb_dateadd(self):
        renderer = SqlRenderer(Dialect.DUCKDB)
        result = renderer.dateadd("week", 2, "start_date")
        assert result == "start_date + INTERVAL '2 week'"

    def test_starburst_dateadd(self):
        renderer = SqlRenderer(Dialect.STARBURST)
        result = renderer.dateadd("quarter", 1, "order_date")
        assert result == "date_add('quarter', 1, order_date)"
