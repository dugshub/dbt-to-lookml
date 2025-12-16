"""Unit tests for native PoP generation methods."""

import pytest

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.schemas.config import PopConfig, PopGrain, PopComparison, PopWindow
from dbt_to_lookml.schemas.semantic_layer import Measure
from dbt_to_lookml.types import AggregationType


class TestPopDimensions:
    """Tests for PoP dimension generation - returns empty with native PoP."""

    def test_dimensions_empty_with_native_pop(self) -> None:
        """Test _generate_pop_dimensions returns empty list (native PoP handles dates)."""
        generator = LookMLGenerator()
        config = PopConfig(enabled=True, grains=[PopGrain.MTD, PopGrain.YTD])

        dims = generator._generate_pop_dimensions(
            config, "selected_date", "selected_date_date"
        )

        # Native PoP doesn't require filter dimensions
        assert dims == []

    def test_dimensions_empty_with_comparisons(self) -> None:
        """Test dimensions empty even with comparisons configured."""
        generator = LookMLGenerator()
        config = PopConfig(
            enabled=True,
            comparisons=[PopComparison.PP, PopComparison.PY],
        )

        dims = generator._generate_pop_dimensions(
            config, "selected_date", "selected_date_date"
        )

        assert dims == []


class TestPopParameters:
    """Tests for PoP parameter generation - returns empty with direct native PoP."""

    def test_no_parameters_with_direct_native_pop(self) -> None:
        """Test no parameters generated with direct native PoP."""
        generator = LookMLGenerator()
        config = PopConfig(
            enabled=True,
            comparisons=[PopComparison.PP, PopComparison.PY],
            windows=[PopWindow.MONTH],
        )

        params = generator._generate_pop_parameters(config)

        # Direct native PoP doesn't need parameters
        assert params == []


class TestPopHiddenMeasures:
    """Tests for native PoP measure generation (now visible)."""

    def test_native_pop_measure_structure(self) -> None:
        """Test native PoP measures have correct structure."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM, expr="amount")
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])

        measures = generator._generate_pop_hidden_measures(
            measure, config, "created_at"
        )

        py_prev = next(m for m in measures if m["name"] == "revenue_py")
        assert py_prev["type"] == "period_over_period"
        assert py_prev["based_on"] == "revenue_measure"
        assert py_prev["based_on_time"] == "created_at_date"
        assert py_prev["period"] == "year"
        assert py_prev["kind"] == "previous"
        # Visible (not hidden)
        assert "hidden" not in py_prev

    def test_generates_three_kinds_per_period(self) -> None:
        """Test previous, difference, relative_change generated for each period."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM, expr="amount")
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])

        measures = generator._generate_pop_hidden_measures(
            measure, config, "created_at"
        )

        measure_names = {m["name"] for m in measures}
        assert "revenue_py" in measure_names  # previous
        assert "revenue_py_change" in measure_names  # difference
        assert "revenue_py_pct_change" in measure_names  # relative_change

    def test_base_measure_hidden(self) -> None:
        """Test base measure is hidden."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM, expr="amount")
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])

        measures = generator._generate_pop_hidden_measures(
            measure, config, "created_at"
        )

        base_measure = next(m for m in measures if m["name"] == "revenue_measure")
        assert base_measure["hidden"] == "yes"
        assert base_measure["type"] == "sum"
        assert "${TABLE}.amount" in base_measure["sql"]

    def test_measure_count_with_pp_and_py(self) -> None:
        """Test correct number of measures with both PP and PY."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM, expr="amount")
        config = PopConfig(
            enabled=True,
            comparisons=[PopComparison.PP, PopComparison.PY],
            windows=[PopWindow.MONTH],
        )

        measures = generator._generate_pop_hidden_measures(
            measure, config, "created_at"
        )

        # 1 base + 3 py measures + 3 pm measures = 7
        assert len(measures) == 7

    def test_period_mapping_py_to_year(self) -> None:
        """Test PY comparison maps to period: year."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM, expr="amount")
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])

        measures = generator._generate_pop_hidden_measures(
            measure, config, "created_at"
        )

        py_measure = next(m for m in measures if m["name"] == "revenue_py")
        assert py_measure["period"] == "year"

    def test_period_mapping_pp_month_to_month(self) -> None:
        """Test PP with month window maps to period: month."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM, expr="amount")
        config = PopConfig(
            enabled=True,
            comparisons=[PopComparison.PP],
            windows=[PopWindow.MONTH],
        )

        measures = generator._generate_pop_hidden_measures(
            measure, config, "created_at"
        )

        pm_measure = next(m for m in measures if m["name"] == "revenue_pm")
        assert pm_measure["period"] == "month"

    def test_period_mapping_pp_quarter_to_quarter(self) -> None:
        """Test PP with quarter window maps to period: quarter."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM, expr="amount")
        config = PopConfig(
            enabled=True,
            comparisons=[PopComparison.PP],
            windows=[PopWindow.QUARTER],
        )

        measures = generator._generate_pop_hidden_measures(
            measure, config, "created_at"
        )

        pq_measure = next(m for m in measures if m["name"] == "revenue_pq")
        assert pq_measure["period"] == "quarter"

    def test_count_measures_no_sql(self) -> None:
        """Test COUNT measures don't have sql parameter in base."""
        generator = LookMLGenerator()
        measure = Measure(name="order_count", agg=AggregationType.COUNT)
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])

        measures = generator._generate_pop_hidden_measures(
            measure, config, "created_at"
        )

        base = next(m for m in measures if m["name"] == "order_count_measure")
        assert "sql" not in base

    def test_avg_measures_have_float_cast(self) -> None:
        """Test AVG measures have float cast applied."""
        generator = LookMLGenerator()
        measure = Measure(name="avg_price", agg=AggregationType.AVERAGE, expr="price")
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])

        measures = generator._generate_pop_hidden_measures(
            measure, config, "created_at"
        )

        base_measure = next(m for m in measures if m["name"] == "avg_price_measure")
        assert "::FLOAT" in base_measure["sql"]

    def test_pop_measures_have_labels(self) -> None:
        """Test PoP measures have descriptive labels."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM, label="Revenue")
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])

        measures = generator._generate_pop_hidden_measures(
            measure, config, "created_at"
        )

        py_measure = next(m for m in measures if m["name"] == "revenue_py")
        assert py_measure["label"] == "Revenue (Prior Year)"
        assert py_measure["group_label"] == "Revenue PoP"
        assert py_measure["view_label"] == " Metrics (PoP)"

    def test_pop_measures_have_format(self) -> None:
        """Test PoP measures have format applied."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM)
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY], format="usd")

        measures = generator._generate_pop_hidden_measures(
            measure, config, "created_at"
        )

        py_measure = next(m for m in measures if m["name"] == "revenue_py")
        assert py_measure["value_format_name"] == "usd"

        pct_measure = next(m for m in measures if m["name"] == "revenue_py_pct_change")
        assert pct_measure["value_format_name"] == "percent_1"


class TestPopVisibleMeasures:
    """Tests for visible current period measure generation."""

    def test_single_current_measure_created(self) -> None:
        """Test only the current period measure is created."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM, label="Revenue")
        config = PopConfig(
            enabled=True,
            comparisons=[PopComparison.PY],
            format="usd",
        )

        measures = generator._generate_pop_visible_measures(measure, config)

        assert len(measures) == 1
        assert measures[0]["name"] == "revenue"

    def test_current_measure_references_base(self) -> None:
        """Test current measure references base measure."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM)
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])

        measures = generator._generate_pop_visible_measures(measure, config)

        current = measures[0]
        assert current["sql"] == "${revenue_measure}"
        assert current["type"] == "number"

    def test_format_applied_to_current(self) -> None:
        """Test value_format_name applied to current measure."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM)
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY], format="usd")

        measures = generator._generate_pop_visible_measures(measure, config)

        current = measures[0]
        assert current["value_format_name"] == "usd"

    def test_view_label_and_group_label(self) -> None:
        """Test view_label is  Metrics (PoP) and group_label uses measure label."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM, label="Revenue")
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])

        measures = generator._generate_pop_visible_measures(measure, config)

        current = measures[0]
        assert current["view_label"] == " Metrics (PoP)"
        assert current["group_label"] == "Revenue PoP"

    def test_label_generation_from_measure_name(self) -> None:
        """Test labels generated from measure name when no label provided."""
        generator = LookMLGenerator()
        measure = Measure(name="total_revenue", agg=AggregationType.SUM)
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])

        measures = generator._generate_pop_visible_measures(measure, config)

        current = measures[0]
        # Should use _smart_title
        assert current["label"] == "Total Revenue"
        assert current["group_label"] == "Total Revenue PoP"
        assert current["view_label"] == " Metrics (PoP)"
