"""Unit tests for direct native PoP pipeline integration."""

import pytest

from dbt_to_lookml.constants import SUFFIX_POP, VIEW_LABEL_METRICS_POP
from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.schemas.config import (
    Config,
    ConfigMeta,
    PopComparison,
    PopConfig,
    PopGrain,
    PopWindow,
)
from dbt_to_lookml.schemas.semantic_layer import Measure, SemanticModel
from dbt_to_lookml.types import AggregationType


class TestPopPipelineIntegration:
    """Tests for direct native PoP pipeline integration."""

    def test_end_to_end_generation(self) -> None:
        """Test complete direct native PoP view generation."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    expr="amount",
                    config=Config(
                        meta=ConfigMeta(
                            pop=PopConfig(
                                enabled=True,
                                comparisons=[PopComparison.PY],
                            )
                        )
                    ),
                )
            ],
        )

        result = generator.generate_view(model)

        view = result["views"][0]

        # No filter dimensions with native PoP
        dim_names = {d["name"] for d in view.get("dimensions", [])}
        assert "is_mtd" not in dim_names
        assert "is_prior_year" not in dim_names

        # No parameters with direct native PoP
        param_names = {p["name"] for p in view.get("parameter", [])}
        assert "comparison_period" not in param_names

        # Check measures exist
        measure_names = {m["name"] for m in view.get("measures", [])}
        assert "revenue_measure" in measure_names
        assert "revenue_py" in measure_names
        assert "revenue_py_change" in measure_names
        assert "revenue_py_pct_change" in measure_names
        assert "revenue" in measure_names

    def test_backward_compatibility(self) -> None:
        """Test models without PoP are unchanged."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            measures=[
                Measure(name="revenue", agg=AggregationType.SUM, expr="amount")
            ],
        )

        result = generator.generate_view(model)

        view = result["views"][0]
        measure_names = {m["name"] for m in view.get("measures", [])}

        # No PoP measures should be present
        assert "revenue_py" not in measure_names
        assert "revenue_pm" not in measure_names

    def test_mixed_pop_non_pop_measures(self) -> None:
        """Test model with both PoP and non-PoP measures."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(name="count", agg=AggregationType.COUNT),  # No PoP
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    expr="amount",
                    config=Config(
                        meta=ConfigMeta(
                            pop=PopConfig(enabled=True, comparisons=[PopComparison.PY])
                        )
                    ),
                ),
            ],
        )

        result = generator.generate_view(model)

        view = result["views"][0]
        measure_names = {m["name"] for m in view.get("measures", [])}
        # count should appear
        assert "count" in measure_names or "count_measure" in measure_names
        # revenue has PoP variants
        assert "revenue_py" in measure_names
        assert "revenue_py_pct_change" in measure_names
        # count should NOT have PoP variants
        assert "count_py" not in measure_names

    def test_pop_with_multiple_periods(self) -> None:
        """Test native PoP generation with PY and PP comparisons."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    expr="amount",
                    config=Config(
                        meta=ConfigMeta(
                            pop=PopConfig(
                                enabled=True,
                                comparisons=[PopComparison.PP, PopComparison.PY],
                                windows=[PopWindow.MONTH],
                            )
                        )
                    ),
                )
            ],
        )

        result = generator.generate_view(model)
        view = result["views"][0]

        measure_names = {m["name"] for m in view.get("measures", [])}

        # Base measure (hidden)
        assert "revenue_measure" in measure_names

        # PY native PoP measures (visible)
        assert "revenue_py" in measure_names
        assert "revenue_py_change" in measure_names
        assert "revenue_py_pct_change" in measure_names

        # PM native PoP measures (visible)
        assert "revenue_pm" in measure_names
        assert "revenue_pm_change" in measure_names
        assert "revenue_pm_pct_change" in measure_names

        # Current measure (visible)
        assert "revenue" in measure_names

    def test_pop_no_filter_dimensions(self) -> None:
        """Test that native PoP doesn't create filter dimensions."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    config=Config(
                        meta=ConfigMeta(
                            pop=PopConfig(
                                enabled=True,
                                comparisons=[PopComparison.PP, PopComparison.PY],
                            )
                        )
                    ),
                )
            ],
        )

        result = generator.generate_view(model)
        view = result["views"][0]

        # No is_* dimensions should exist
        for dim in view.get("dimensions", []):
            assert not dim["name"].startswith("is_")

    def test_pop_base_measure_hidden(self) -> None:
        """Test that base measure is hidden."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    config=Config(
                        meta=ConfigMeta(
                            pop=PopConfig(enabled=True, comparisons=[PopComparison.PY])
                        )
                    ),
                )
            ],
        )

        result = generator.generate_view(model)
        view = result["views"][0]

        base_measure = next(m for m in view["measures"] if m["name"] == "revenue_measure")
        assert base_measure["hidden"] == "yes"

    def test_pop_measures_visible(self) -> None:
        """Test that PoP measures are visible (not hidden)."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    config=Config(
                        meta=ConfigMeta(
                            pop=PopConfig(enabled=True, comparisons=[PopComparison.PY])
                        )
                    ),
                )
            ],
        )

        result = generator.generate_view(model)
        view = result["views"][0]

        py_measure = next(m for m in view["measures"] if m["name"] == "revenue_py")
        assert "hidden" not in py_measure

    def test_pop_visible_measures_have_group_label(self) -> None:
        """Test that PoP visible measures share a group label."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    label="Revenue",
                    config=Config(
                        meta=ConfigMeta(
                            pop=PopConfig(enabled=True, comparisons=[PopComparison.PY])
                        )
                    ),
                )
            ],
        )

        result = generator.generate_view(model)
        view = result["views"][0]

        # Get visible PoP measures
        pop_measures = [
            m for m in view.get("measures", [])
            if m["name"] in ["revenue", "revenue_py", "revenue_py_change", "revenue_py_pct_change"]
        ]

        # All should have same view_label and group_label
        assert len(pop_measures) == 4
        for measure in pop_measures:
            assert measure.get("view_label") == VIEW_LABEL_METRICS_POP
            assert measure.get("group_label") == f"Revenue {SUFFIX_POP}"

    def test_pop_with_custom_format(self) -> None:
        """Test PoP measures respect custom format."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    config=Config(
                        meta=ConfigMeta(
                            pop=PopConfig(
                                enabled=True,
                                comparisons=[PopComparison.PY],
                                format="usd",
                            )
                        )
                    ),
                )
            ],
        )

        result = generator.generate_view(model)
        view = result["views"][0]

        # Find measures
        revenue = next(m for m in view["measures"] if m["name"] == "revenue")
        py = next(m for m in view["measures"] if m["name"] == "revenue_py")
        change = next(m for m in view["measures"] if m["name"] == "revenue_py_change")

        # Should have custom format
        assert revenue.get("value_format_name") == "usd"
        assert py.get("value_format_name") == "usd"
        assert change.get("value_format_name") == "usd"

    def test_pop_pct_change_has_percent_format(self) -> None:
        """Test PoP percent change always has percent format."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    config=Config(
                        meta=ConfigMeta(
                            pop=PopConfig(
                                enabled=True,
                                comparisons=[PopComparison.PY],
                                format="usd",
                            )
                        )
                    ),
                )
            ],
        )

        result = generator.generate_view(model)
        view = result["views"][0]

        pct_change = next(m for m in view["measures"] if m["name"] == "revenue_py_pct_change")
        # Should always use percent_1, not custom format
        assert pct_change.get("value_format_name") == "percent_1"

    def test_native_pop_measure_type(self) -> None:
        """Test that native PoP measures have type: period_over_period."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    expr="amount",
                    config=Config(
                        meta=ConfigMeta(
                            pop=PopConfig(enabled=True, comparisons=[PopComparison.PY])
                        )
                    ),
                )
            ],
        )

        result = generator.generate_view(model)
        view = result["views"][0]

        py = next(m for m in view["measures"] if m["name"] == "revenue_py")
        assert py["type"] == "period_over_period"
        assert py["based_on"] == "revenue_measure"
        assert py["period"] == "year"
        assert py["kind"] == "previous"

    def test_pop_measures_have_descriptive_labels(self) -> None:
        """Test PoP measures have descriptive labels."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    label="Revenue",
                    config=Config(
                        meta=ConfigMeta(
                            pop=PopConfig(
                                enabled=True,
                                comparisons=[PopComparison.PP, PopComparison.PY],
                                windows=[PopWindow.MONTH],
                            )
                        )
                    ),
                )
            ],
        )

        result = generator.generate_view(model)
        view = result["views"][0]

        py = next(m for m in view["measures"] if m["name"] == "revenue_py")
        pm = next(m for m in view["measures"] if m["name"] == "revenue_pm")

        assert py["label"] == "Revenue (Prior Year)"
        assert pm["label"] == "Revenue (Prior Month)"
