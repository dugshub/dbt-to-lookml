"""
Tests for LabelResolver class.

Tests label resolution, group conformity, and PoP styling.
"""

import pytest

from semantic_patterns.adapters.lookml.labels import LabelResolver
from semantic_patterns.config import LabelConfig
from semantic_patterns.domain.dimension import Dimension, DimensionType
from semantic_patterns.domain.metric import Metric, MetricType


class TestEffectiveLabel:
    """Tests for effective_label method."""

    def test_returns_label_when_under_max_length(self):
        """Label should be returned when it's under max_length."""
        config = LabelConfig(max_length=30)
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",  # 24 chars, under 30
            short_label="GMV",
        )

        result = resolver.effective_label(metric)
        assert result == "Gross Merchandise Value"

    def test_returns_short_label_when_label_exceeds_max_length(self):
        """Short label should be used when label exceeds max_length."""
        config = LabelConfig(max_length=20)
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",  # 24 chars, over 20
            short_label="GMV",
        )

        result = resolver.effective_label(metric)
        assert result == "GMV"

    def test_returns_label_when_exceeds_max_length_but_no_short_label(self):
        """Label is returned if it exceeds max_length but no short_label exists."""
        config = LabelConfig(max_length=20)
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",  # 24 chars, over 20
            # No short_label
        )

        result = resolver.effective_label(metric)
        assert result == "Gross Merchandise Value"

    def test_falls_back_to_title_cased_name_when_no_label(self):
        """Title-cased name should be used when no label is provided."""
        config = LabelConfig(max_length=30)
        resolver = LabelResolver(config)

        metric = Metric(
            name="total_revenue",
            type=MetricType.SIMPLE,
            measure="revenue_sum",
            # No label or short_label
        )

        result = resolver.effective_label(metric)
        assert result == "Total Revenue"

    def test_works_with_dimension(self):
        """Should work with Dimension objects as well."""
        config = LabelConfig(max_length=15)
        resolver = LabelResolver(config)

        dimension = Dimension(
            name="rental_status",
            type=DimensionType.CATEGORICAL,
            expr="rental_status",
            label="Rental Reservation Status",  # 26 chars, over 15
            short_label="Status",
        )

        result = resolver.effective_label(dimension)
        assert result == "Status"


class TestResolveGroupLabels:
    """Tests for resolve_group_labels method."""

    def test_without_group_conformity_each_field_gets_own_effective_label(self):
        """Without group_conformity, each field uses its own effective_label."""
        config = LabelConfig(max_length=20, group_conformity=False)
        resolver = LabelResolver(config)

        fields = [
            Metric(
                name="gmv",
                type=MetricType.SIMPLE,
                measure="total_gmv",
                label="Gross Merchandise Value",  # 24 chars, over 20
                short_label="GMV",
            ),
            Metric(
                name="revenue",
                type=MetricType.SIMPLE,
                measure="total_revenue",
                label="Total Revenue",  # 13 chars, under 20
                short_label="Rev",
            ),
        ]

        result = resolver.resolve_group_labels(fields)

        # gmv exceeds max_length, uses short_label
        assert result["gmv"] == "GMV"
        # revenue under max_length, uses full label
        assert result["revenue"] == "Total Revenue"

    def test_with_group_conformity_all_fields_use_short_label_if_any_needs_it(self):
        """With group_conformity, if ANY field needs short_label, ALL use it."""
        config = LabelConfig(max_length=20, group_conformity=True)
        resolver = LabelResolver(config)

        fields = [
            Metric(
                name="gmv",
                type=MetricType.SIMPLE,
                measure="total_gmv",
                label="Gross Merchandise Value",  # 24 chars, over 20 - needs short
                short_label="GMV",
            ),
            Metric(
                name="revenue",
                type=MetricType.SIMPLE,
                measure="total_revenue",
                label="Total Revenue",  # 13 chars, under 20 - but has short_label
                short_label="Rev",
            ),
        ]

        result = resolver.resolve_group_labels(fields)

        # gmv needs short_label due to length
        assert result["gmv"] == "GMV"
        # revenue also uses short_label due to group conformity
        assert result["revenue"] == "Rev"

    def test_group_conformity_mix_of_fields_with_and_without_short_labels(self):
        """Fields without short_label use effective_label even with conformity."""
        config = LabelConfig(max_length=20, group_conformity=True)
        resolver = LabelResolver(config)

        fields = [
            Metric(
                name="gmv",
                type=MetricType.SIMPLE,
                measure="total_gmv",
                label="Gross Merchandise Value",  # 24 chars, over 20 - triggers conformity
                short_label="GMV",
            ),
            Metric(
                name="revenue",
                type=MetricType.SIMPLE,
                measure="total_revenue",
                label="Total Revenue",  # 13 chars
                short_label="Rev",
            ),
            Metric(
                name="orders",
                type=MetricType.SIMPLE,
                measure="order_count",
                label="Order Count",  # No short_label
            ),
        ]

        result = resolver.resolve_group_labels(fields)

        # Both gmv and revenue use short_label due to conformity
        assert result["gmv"] == "GMV"
        assert result["revenue"] == "Rev"
        # orders has no short_label, uses effective_label (full label)
        assert result["orders"] == "Order Count"

    def test_no_conformity_triggered_when_all_under_max_length(self):
        """Group conformity doesn't force short_label if no field exceeds max_length."""
        config = LabelConfig(max_length=30, group_conformity=True)
        resolver = LabelResolver(config)

        fields = [
            Metric(
                name="gmv",
                type=MetricType.SIMPLE,
                measure="total_gmv",
                label="Gross Merchandise Value",  # 24 chars, under 30
                short_label="GMV",
            ),
            Metric(
                name="revenue",
                type=MetricType.SIMPLE,
                measure="total_revenue",
                label="Total Revenue",  # 13 chars, under 30
                short_label="Rev",
            ),
        ]

        result = resolver.resolve_group_labels(fields)

        # No field exceeds max_length, so full labels used
        assert result["gmv"] == "Gross Merchandise Value"
        assert result["revenue"] == "Total Revenue"

    def test_empty_fields_list(self):
        """Should handle empty list of fields."""
        config = LabelConfig(max_length=30, group_conformity=True)
        resolver = LabelResolver(config)

        result = resolver.resolve_group_labels([])
        assert result == {}


class TestPopLabel:
    """Tests for pop_label method."""

    def test_compact_style_previous(self):
        """Compact style generates short format for previous: 'GMV (PY)'."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
            short_label="GMV",
        )

        result = resolver.pop_label(metric, "prior_year", "previous")
        assert result == "GMV (PY)"

    def test_compact_style_change(self):
        """Compact style generates: 'GMV Δ PY'."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
            short_label="GMV",
        )

        result = resolver.pop_label(metric, "prior_year", "change")
        assert result == "GMV Δ PY"

    def test_compact_style_pct_change(self):
        """Compact style generates: 'GMV %Δ PY'."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
            short_label="GMV",
        )

        result = resolver.pop_label(metric, "prior_year", "pct_change")
        assert result == "GMV %Δ PY"

    def test_standard_style_previous(self):
        """Standard style generates verbose format for previous."""
        config = LabelConfig(max_length=50, pop_style="standard")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Order Value",
        )

        result = resolver.pop_label(metric, "prior_year", "previous")
        assert result == "Gross Order Value (Prior Year)"

    def test_standard_style_change(self):
        """Standard style generates verbose format for change."""
        config = LabelConfig(max_length=50, pop_style="standard")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Order Value",
        )

        result = resolver.pop_label(metric, "prior_year", "change")
        assert result == "Gross Order Value vs Prior Year Change"

    def test_standard_style_pct_change(self):
        """Standard style generates verbose format for pct_change."""
        config = LabelConfig(max_length=50, pop_style="standard")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Order Value",
        )

        result = resolver.pop_label(metric, "prior_year", "pct_change")
        assert result == "Gross Order Value vs Prior Year % Change"

    def test_verbose_style(self):
        """Verbose style generates extended format."""
        config = LabelConfig(max_length=50, pop_style="verbose")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Order Value",
        )

        result = resolver.pop_label(metric, "prior_month", "previous")
        assert result == "Gross Order Value - Prior Month"

    def test_falls_back_to_compact_for_unknown_style(self):
        """Unknown style falls back to compact."""
        config = LabelConfig(max_length=30, pop_style="unknown_style")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
            short_label="GMV",
        )

        result = resolver.pop_label(metric, "prior_year", "previous")
        assert result == "GMV (PY)"

    def test_truncates_with_ellipsis_if_short_label_too_long(self):
        """Short label is truncated with ellipsis if still too long."""
        config = LabelConfig(max_length=10, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
            short_label="VeryLongShortLabel",  # 18 chars, over 10
        )

        result = resolver.pop_label(metric, "prior_year", "previous")
        # Short label truncated to max_length-2 + ellipsis = 8 + "…" = "VeryLong…"
        assert "VeryLong…" in result
        assert result == "VeryLong… (PY)"

    def test_uses_label_as_short_when_no_short_label(self):
        """When no short_label, uses label for compact style."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="GMV",
            # No short_label
        )

        result = resolver.pop_label(metric, "prior_year", "previous")
        assert result == "GMV (PY)"

    def test_prior_month_abbreviation(self):
        """Prior month uses PM abbreviation."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            short_label="GMV",
        )

        result = resolver.pop_label(metric, "prior_month", "previous")
        assert result == "GMV (PM)"

    def test_prior_quarter_abbreviation(self):
        """Prior quarter uses PQ abbreviation."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            short_label="GMV",
        )

        result = resolver.pop_label(metric, "prior_quarter", "change")
        assert result == "GMV Δ PQ"

    def test_unknown_comparison_uses_title_case(self):
        """Unknown comparison period uses title-cased label."""
        config = LabelConfig(max_length=50, pop_style="standard")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="GMV",
        )

        result = resolver.pop_label(metric, "custom_period", "previous")
        assert result == "GMV (Custom Period)"

    def test_unknown_comparison_abbreviation(self):
        """Unknown comparison uses first 2 chars uppercase as abbreviation."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            short_label="GMV",
        )

        result = resolver.pop_label(metric, "custom_period", "previous")
        assert result == "GMV (CU)"


class TestPopGroupLabel:
    """Tests for pop_group_label method."""

    def test_returns_short_label_without_category(self):
        """Returns just short label when no category provided."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
            short_label="GMV",
        )

        result = resolver.pop_group_label(metric)
        assert result == "GMV"

    def test_includes_category_with_short_label(self):
        """Returns 'Category · Short Label' format when category provided."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
            short_label="GMV",
        )

        result = resolver.pop_group_label(metric, category="Revenue")
        assert result == "Revenue · GMV"

    def test_standard_style_includes_category_prefix(self):
        """Standard style includes category prefix when provided."""
        config = LabelConfig(max_length=50, pop_style="standard")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
            short_label="GMV",
        )

        result = resolver.pop_group_label(metric, category="Revenue Metrics")
        assert result == "Revenue Metrics · GMV"

    def test_verbose_style_includes_category_prefix(self):
        """Verbose style includes category prefix when provided."""
        config = LabelConfig(max_length=50, pop_style="verbose")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
            short_label="GMV",
        )

        result = resolver.pop_group_label(metric, category="Revenue")
        assert result == "Revenue · GMV"

    def test_without_category_returns_just_short_label(self):
        """Without category returns just short/effective label."""
        config = LabelConfig(max_length=50, pop_style="standard")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
            short_label="GMV",
        )

        result = resolver.pop_group_label(metric, category=None)
        assert result == "GMV"

    def test_uses_title_cased_name_when_no_labels(self):
        """Falls back to title-cased name when no label or short_label."""
        config = LabelConfig(max_length=50, pop_style="standard")
        resolver = LabelResolver(config)

        metric = Metric(
            name="total_revenue",
            type=MetricType.SIMPLE,
            measure="revenue_sum",
            # No label or short_label
        )

        result = resolver.pop_group_label(metric, category="Sales")
        assert result == "Sales · Total Revenue"

    def test_uses_label_when_no_short_label(self):
        """Uses full label when short_label not provided."""
        config = LabelConfig(max_length=50, pop_style="standard")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
            # No short_label
        )

        result = resolver.pop_group_label(metric, category="Revenue")
        assert result == "Revenue · Gross Merchandise Value"


class TestPopGroupItemLabel:
    """Tests for pop_group_item_label method."""

    def test_previous_output_format(self):
        """Previous output: 'GOV - PY'."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gov",
            type=MetricType.SIMPLE,
            measure="checkout_amount",
            label="Gross Order Value",
            short_label="GOV",
        )

        result = resolver.pop_group_item_label(metric, "prior_year", "previous")
        assert result == "GOV - PY"

    def test_pct_change_output_format(self):
        """Pct change output: 'GOV - PY%'."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gov",
            type=MetricType.SIMPLE,
            measure="checkout_amount",
            label="Gross Order Value",
            short_label="GOV",
        )

        result = resolver.pop_group_item_label(metric, "prior_year", "pct_change")
        assert result == "GOV - PY%"

    def test_change_output_format(self):
        """Change output: 'GOV - PYΔ'."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gov",
            type=MetricType.SIMPLE,
            measure="checkout_amount",
            label="Gross Order Value",
            short_label="GOV",
        )

        result = resolver.pop_group_item_label(metric, "prior_year", "change")
        assert result == "GOV - PYΔ"

    def test_prior_month_abbreviation(self):
        """Prior month uses PM abbreviation."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gov",
            type=MetricType.SIMPLE,
            measure="checkout_amount",
            short_label="GOV",
        )

        result = resolver.pop_group_item_label(metric, "prior_month", "previous")
        assert result == "GOV - PM"

    def test_prior_quarter_abbreviation(self):
        """Prior quarter uses PQ abbreviation."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gov",
            type=MetricType.SIMPLE,
            measure="checkout_amount",
            short_label="GOV",
        )

        result = resolver.pop_group_item_label(metric, "prior_quarter", "pct_change")
        assert result == "GOV - PQ%"

    def test_uses_short_label_when_available(self):
        """Uses short_label for the label portion."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="gmv",
            type=MetricType.SIMPLE,
            measure="total_gmv",
            label="Gross Merchandise Value",
            short_label="GMV",
        )

        result = resolver.pop_group_item_label(metric, "prior_year", "previous")
        assert result == "GMV - PY"

    def test_falls_back_to_label_when_no_short_label(self):
        """Falls back to label when short_label not provided."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="revenue",
            type=MetricType.SIMPLE,
            measure="total_revenue",
            label="Revenue",
            # No short_label
        )

        result = resolver.pop_group_item_label(metric, "prior_year", "previous")
        assert result == "Revenue - PY"

    def test_unknown_comparison_uses_first_two_chars(self):
        """Unknown comparison uses first 2 chars uppercase."""
        config = LabelConfig(max_length=30, pop_style="compact")
        resolver = LabelResolver(config)

        metric = Metric(
            name="revenue",
            type=MetricType.SIMPLE,
            measure="total_revenue",
            short_label="Rev",
        )

        result = resolver.pop_group_item_label(metric, "custom_period", "previous")
        assert result == "Rev - CU"
