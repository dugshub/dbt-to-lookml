"""Period-over-Period (PoP) rendering for LookML.

Uses a strategy pattern to allow swapping PoP implementations:
- LookerNativePopStrategy: Uses Looker's native period_over_period type
- DynamicFilteredPopStrategy: Uses filtered measures with user-selectable period

The dynamic strategy generates fewer measures (3 per metric vs N*M with native)
and gives users runtime control over the comparison period.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from semantic_patterns.adapters.lookml.labels import LabelResolver
from semantic_patterns.domain import (
    Metric,
    MetricVariant,
    PopComparison,
    PopOutput,
    PopParams,
    VariantKind,
)

if TYPE_CHECKING:
    from semantic_patterns.domain import Measure

    # For filter rendering (import at runtime to avoid circular imports)
    from semantic_patterns.adapters.lookml.renderers.filter import FilterRenderer

# Map PopComparison to Looker's period_over_period comparison_period
COMPARISON_TO_LOOKML: dict[PopComparison, str] = {
    PopComparison.PRIOR_YEAR: "year",
    PopComparison.PRIOR_MONTH: "month",
    PopComparison.PRIOR_QUARTER: "quarter",
    PopComparison.PRIOR_WEEK: "week",
}


def _extract_category(metric: Metric) -> str | None:
    """Extract category from metric's group_parts for PoP group_label."""
    if len(metric.group_parts) >= 2:
        return metric.group_parts[1]
    elif metric.group_parts:
        return metric.group_parts[0]
    return None

# Map PopOutput to Looker's period_over_period kind
OUTPUT_TO_LOOKML: dict[PopOutput, str] = {
    PopOutput.PREVIOUS: "previous",
    PopOutput.CHANGE: "difference",
    PopOutput.PERCENT_CHANGE: "relative_change",
}


class PopStrategy(Protocol):
    """Protocol for PoP rendering strategies."""

    def render(
        self,
        metric: Metric,
        variant: MetricVariant,
    ) -> dict[str, Any]:
        """Render a PoP variant to LookML measure dict."""
        ...


class LookerNativePopStrategy:
    """
    Use Looker's native period_over_period measure type.

    Generates:
        measure: gmv_py {
            type: period_over_period
            based_on: gmv
            based_on_time: {fact_view}.calendar_date
            period: year
            kind: previous
        }

    Requires:
    - Calendar dimension_group on fact view (provides calendar_date)
    - Calendar is added via view extension (+fact_view) in explore file
    """

    def __init__(
        self,
        fact_view_name: str | None = None,
        label_resolver: LabelResolver | None = None,
    ) -> None:
        """
        Initialize with fact view name for qualified based_on_time references.

        Args:
            fact_view_name: Name of the fact view (e.g., "sp_rentals")
                           Calendar dimension is defined on this view.
            label_resolver: Optional LabelResolver for label generation.
                           If not provided, a default one is created.
        """
        self.fact_view_name = fact_view_name
        if label_resolver is None:
            from semantic_patterns.config import LabelConfig
            label_resolver = LabelResolver(LabelConfig())
        self.label_resolver = label_resolver

    def render(
        self,
        metric: Metric,
        variant: MetricVariant,
    ) -> dict[str, Any]:
        """Render PoP variant using Looker's native type."""
        if variant.kind != VariantKind.POP or not isinstance(variant.params, PopParams):
            raise ValueError(f"Expected PoP variant, got {variant.kind}")

        params = variant.params
        name = variant.resolve_name(metric)

        result: dict[str, Any] = {
            "name": name,
            "type": "period_over_period",
            "based_on": metric.name,
            "period": COMPARISON_TO_LOOKML.get(params.comparison, "year"),
            "kind": OUTPUT_TO_LOOKML.get(params.output, "previous"),
        }

        # Add qualified based_on_time reference to calendar dimension on fact view
        # Calendar is defined via +{fact_view} extension, so we need full qualification
        if self.fact_view_name:
            result["based_on_time"] = f"{self.fact_view_name}.calendar_date"

        # Generate label using LabelResolver
        # Convert enum names to lowercase strings for LabelResolver lookup
        comparison_str = params.comparison.name.lower()  # e.g., "prior_year"
        output_str = params.output.value  # e.g., "previous", "change", "pct_change"

        result["label"] = self.label_resolver.pop_label(
            metric, comparison_str, output_str
        )

        # Inherit format from variant or metric
        if variant.value_format:
            result["value_format_name"] = variant.value_format
        elif metric.format:
            # For percent change, use percent format
            if params.output == PopOutput.PERCENT_CHANGE:
                result["value_format_name"] = "percent_1"
            else:
                result["value_format_name"] = metric.format

        # PoP measures go to "Metrics (PoP)" view_label
        # group_label groups all variants of a metric, group_item_label distinguishes them
        category = _extract_category(metric)
        result["view_label"] = "  Metrics (PoP)"
        result["group_label"] = self.label_resolver.pop_group_label(metric, category)
        result["group_item_label"] = self.label_resolver.pop_group_item_label(
            metric, comparison_str, output_str
        )

        return result


class PopRenderer:
    """
    Render PoP variants for metrics.

    Uses pluggable strategy pattern for different PoP implementations.
    """

    def __init__(self, strategy: PopStrategy | None = None) -> None:
        self.strategy = strategy or LookerNativePopStrategy()

    def render_variants(self, metric: Metric) -> list[dict[str, Any]]:
        """Render all PoP variants for a metric."""
        results = []

        for variant in metric.variants:
            if variant.kind == VariantKind.POP:
                result = self.strategy.render(metric, variant)
                results.append(result)

        return results

    def render_single(
        self,
        metric: Metric,
        variant: MetricVariant,
    ) -> dict[str, Any]:
        """Render a single PoP variant."""
        return self.strategy.render(metric, variant)


class DynamicFilteredPopStrategy:
    """
    Generate PoP measures using filtered measures with a dynamic comparison period.

    Instead of generating separate measures for each comparison period (py, pm, etc.),
    this strategy generates a single set of measures that use the calendar view's
    `is_comparison_period` dimension, which is controlled by the user via parameter.

    Generates per metric (when PoP enabled):
    - {metric}_prior: Filtered measure for comparison period
    - {metric}_change: Absolute difference (current - prior)
    - {metric}_pct_change: Percent change

    Requires:
    - calendar_view_name: The explore calendar view name
    - The calendar view must have `is_comparison_period` dimension
    """

    def __init__(
        self,
        calendar_view_name: str,
        label_resolver: LabelResolver | None = None,
    ) -> None:
        """
        Initialize with the calendar view name for filter references.

        Args:
            calendar_view_name: Name of the calendar view
            label_resolver: Optional LabelResolver for label generation.
                           If not provided, a default one is created.
        """
        self.calendar_view_name = calendar_view_name
        if label_resolver is None:
            from semantic_patterns.config import LabelConfig
            label_resolver = LabelResolver(LabelConfig())
        self.label_resolver = label_resolver
        self._rendered_outputs: dict[str, set[PopOutput]] = {}

    def reset(self) -> None:
        """Reset rendered tracking for a new render pass."""
        self._rendered_outputs.clear()

    def render(
        self,
        metric: Metric,
        variant: MetricVariant,
    ) -> dict[str, Any] | None:
        """
        Render a single PoP measure for the given output type.

        For dynamic PoP, we only render one measure per output type per metric,
        regardless of how many comparison periods are configured.
        """
        if variant.kind != VariantKind.POP or not isinstance(variant.params, PopParams):
            return None

        output = variant.params.output

        # Track what we've rendered to avoid duplicates
        if metric.name not in self._rendered_outputs:
            self._rendered_outputs[metric.name] = set()

        if output in self._rendered_outputs[metric.name]:
            # Already rendered this output type for this metric
            return None

        self._rendered_outputs[metric.name].add(output)

        if output == PopOutput.PREVIOUS:
            return self._render_prior(metric)
        elif output == PopOutput.CHANGE:
            return self._render_change(metric)
        elif output == PopOutput.PERCENT_CHANGE:
            return self._render_pct_change(metric)

        return None

    def render_all(
        self,
        metric: Metric,
        measures: dict[str, "Measure"] | None = None,
        defined_fields: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Render all PoP measures for a metric based on its pop.outputs config.

        This is the preferred method for dynamic PoP - generates exactly
        the measures specified in outputs, ignoring comparisons (which are
        handled by the calendar parameter).

        Args:
            metric: The metric to render PoP measures for
            measures: Dict of measure name -> Measure for looking up expressions
            defined_fields: Map of column_name -> field_name for filter rendering
        """
        if not metric.pop or not metric.pop.outputs:
            return []

        results = []
        for output in metric.pop.outputs:
            if output == PopOutput.PREVIOUS:
                results.append(self._render_prior(metric, measures, defined_fields))
            elif output == PopOutput.CHANGE:
                results.append(self._render_change(metric))
            elif output == PopOutput.PERCENT_CHANGE:
                results.append(self._render_pct_change(metric))

        return results

    def _render_prior(
        self,
        metric: Metric,
        measures: dict[str, "Measure"] | None = None,
        defined_fields: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Render the _prior filtered measure."""
        from semantic_patterns.adapters.lookml.renderers.filter import FilterRenderer
        from semantic_patterns.adapters.lookml.renderers.measure import get_lookml_type

        base_label = metric.label or metric.name.replace("_", " ").title()

        # Use LabelResolver for label generation (previous output type)
        label = self.label_resolver.pop_label(metric, "prior_year", "previous")

        # Look up the underlying measure for expression and aggregation type
        measure = measures.get(metric.measure or "") if measures and metric.measure else None

        # Determine aggregation type from measure, default to sum
        lookml_type = "sum"
        if measure:
            lookml_type = get_lookml_type(measure.agg, bool(measure.expr))

        result: dict[str, Any] = {
            "name": f"{metric.name}_prior",
            "type": lookml_type,
            "label": label,
            "description": f"{base_label} for the selected comparison period",
            "filters": [
                {
                    "field": f"{self.calendar_view_name}.is_comparison_period",
                    "value": "yes",
                }
            ],
        }

        # Build SQL from the measure's expression
        # IMPORTANT: Apply metric's filter (e.g., rental_event_type = 'completed')
        # to match the base metric's behavior
        fields = defined_fields or {}
        if measure:
            base_sql = f"${{TABLE}}.{measure.expr}"
        elif metric.measure:
            base_sql = f"${{TABLE}}.{metric.measure}"
        else:
            base_sql = "NULL"

        # Apply metric's filter as CASE WHEN (matching base metric pattern)
        if metric.filter and metric.filter.conditions:
            filter_renderer = FilterRenderer(defined_fields=fields)
            result["sql"] = filter_renderer.render_case_when(base_sql, metric.filter, fields)
        else:
            result["sql"] = base_sql

        if metric.format:
            result["value_format_name"] = metric.format

        # PoP measures go to "Metrics (PoP)" view_label
        # group_label groups all variants of a metric, group_item_label distinguishes them
        category = _extract_category(metric)
        result["view_label"] = "  Metrics (PoP)"
        result["group_label"] = self.label_resolver.pop_group_label(metric, category)
        result["group_item_label"] = self.label_resolver.pop_group_item_label(
            metric, "prior_year", "previous"
        )

        return result

    def _render_change(self, metric: Metric) -> dict[str, Any]:
        """Render the _change measure (current - prior)."""
        base_label = metric.label or metric.name.replace("_", " ").title()

        # Use LabelResolver for label generation (change output type)
        label = self.label_resolver.pop_label(metric, "prior_year", "change")

        result: dict[str, Any] = {
            "name": f"{metric.name}_change",
            "type": "number",
            "label": label,
            "description": f"Difference between current and prior period {base_label}",
            "sql": f"${{{metric.name}}} - ${{{metric.name}_prior}}",
        }

        if metric.format:
            result["value_format_name"] = metric.format

        # PoP measures go to "Metrics (PoP)" view_label
        # group_label groups all variants of a metric, group_item_label distinguishes them
        category = _extract_category(metric)
        result["view_label"] = "  Metrics (PoP)"
        result["group_label"] = self.label_resolver.pop_group_label(metric, category)
        result["group_item_label"] = self.label_resolver.pop_group_item_label(
            metric, "prior_year", "change"
        )

        return result

    def _render_pct_change(self, metric: Metric) -> dict[str, Any]:
        """Render the _pct_change measure."""
        # Use LabelResolver for label generation (pct_change output type)
        label = self.label_resolver.pop_label(metric, "prior_year", "pct_change")

        prior = f"${{{metric.name}_prior}}"
        current = f"${{{metric.name}}}"
        result: dict[str, Any] = {
            "name": f"{metric.name}_pct_change",
            "type": "number",
            "label": label,
            "description": "Percent change from prior period",
            "sql": f"({current} - {prior}) / NULLIF({prior}, 0)",
            "value_format_name": "percent_1",
        }

        # PoP measures go to "Metrics (PoP)" view_label
        # group_label groups all variants of a metric, group_item_label distinguishes them
        category = _extract_category(metric)
        result["view_label"] = "  Metrics (PoP)"
        result["group_label"] = self.label_resolver.pop_group_label(metric, category)
        result["group_item_label"] = self.label_resolver.pop_group_item_label(
            metric, "prior_year", "pct_change"
        )

        return result
