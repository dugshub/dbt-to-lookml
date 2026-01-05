"""Period-over-Period (PoP) rendering for LookML.

Uses a strategy pattern to allow swapping PoP implementations:
- LookerNativePopStrategy: Uses Looker's native period_over_period type
- DynamicFilteredPopStrategy: Uses filtered measures with user-selectable comparison period

The dynamic strategy generates fewer measures (3 per metric vs N*M with native)
and gives users runtime control over the comparison period.
"""

from typing import Any, Protocol

from dbt_to_lookml_v2.adapters.lookml.renderers.labels import apply_group_labels
from dbt_to_lookml_v2.domain import (
    Metric,
    MetricVariant,
    PopComparison,
    PopOutput,
    PopParams,
    VariantKind,
)

# Map PopComparison to Looker's period_over_period comparison_period
COMPARISON_TO_LOOKML: dict[PopComparison, str] = {
    PopComparison.PRIOR_YEAR: "year",
    PopComparison.PRIOR_MONTH: "month",
    PopComparison.PRIOR_QUARTER: "quarter",
    PopComparison.PRIOR_WEEK: "week",
}

# Map PopOutput to Looker's period_over_period output
OUTPUT_TO_LOOKML: dict[PopOutput, str] = {
    PopOutput.PREVIOUS: "value",
    PopOutput.CHANGE: "difference",
    PopOutput.PERCENT_CHANGE: "percent_difference",
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
            comparison_period: year
            output: value
        }

    Limitations:
    - Only works with time-based data
    - Requires a proper date dimension
    - Some complex scenarios may not work
    """

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
            "comparison_period": COMPARISON_TO_LOOKML.get(params.comparison, "year"),
            "output": OUTPUT_TO_LOOKML.get(params.output, "value"),
        }

        # Generate label
        comparison_labels = {
            PopComparison.PRIOR_YEAR: "Prior Year",
            PopComparison.PRIOR_MONTH: "Prior Month",
            PopComparison.PRIOR_QUARTER: "Prior Quarter",
            PopComparison.PRIOR_WEEK: "Prior Week",
        }
        output_labels = {
            PopOutput.PREVIOUS: "",
            PopOutput.CHANGE: "Change",
            PopOutput.PERCENT_CHANGE: "% Change",
        }

        comp_label = comparison_labels.get(params.comparison, "Prior Period")
        out_label = output_labels.get(params.output, "")

        base_label = metric.label or metric.name.replace("_", " ").title()
        if out_label:
            result["label"] = f"{base_label} vs {comp_label} ({out_label})"
        else:
            result["label"] = f"{base_label} ({comp_label})"

        # Inherit format from variant or metric
        if variant.value_format:
            result["value_format_name"] = variant.value_format
        elif metric.format:
            # For percent change, use percent format
            if params.output == PopOutput.PERCENT_CHANGE:
                result["value_format_name"] = "percent_1"
            else:
                result["value_format_name"] = metric.format

        # Group with base metric
        if metric.group:
            apply_group_labels(result, metric.group_parts)

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
    - calendar_view_name: The explore calendar view name (e.g., "rentals_explore_calendar")
    - The calendar view must have `is_comparison_period` dimension
    """

    def __init__(self, calendar_view_name: str) -> None:
        """
        Initialize with the calendar view name for filter references.

        Args:
            calendar_view_name: Name of the calendar view (e.g., "rentals_explore_calendar")
        """
        self.calendar_view_name = calendar_view_name
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

    def render_all(self, metric: Metric) -> list[dict[str, Any]]:
        """
        Render all PoP measures for a metric based on its pop.outputs config.

        This is the preferred method for dynamic PoP - generates exactly
        the measures specified in outputs, ignoring comparisons (which are
        handled by the calendar parameter).
        """
        if not metric.pop or not metric.pop.outputs:
            return []

        results = []
        for output in metric.pop.outputs:
            if output == PopOutput.PREVIOUS:
                results.append(self._render_prior(metric))
            elif output == PopOutput.CHANGE:
                results.append(self._render_change(metric))
            elif output == PopOutput.PERCENT_CHANGE:
                results.append(self._render_pct_change(metric))

        return results

    def _render_prior(self, metric: Metric) -> dict[str, Any]:
        """Render the _prior filtered measure."""
        base_label = metric.label or metric.name.replace("_", " ").title()

        result: dict[str, Any] = {
            "name": f"{metric.name}_prior",
            "type": "sum",  # TODO: inherit from base metric's aggregation
            "label": f"{base_label} (PoP)",
            "description": f"{base_label} for the comparison period selected in Calendar",
            "filters": [{
                "field": f"{self.calendar_view_name}.is_comparison_period",
                "value": "yes",
            }],
        }

        # Build SQL - needs to match the base metric
        # For simple metrics, this is the measure's expression
        # TODO: Handle derived/ratio metrics and filters
        if metric.measure:
            result["sql"] = f"${{TABLE}}.{metric.measure}"

        if metric.format:
            result["value_format_name"] = metric.format

        if metric.group:
            apply_group_labels(result, metric.group_parts)

        return result

    def _render_change(self, metric: Metric) -> dict[str, Any]:
        """Render the _change measure (current - prior)."""
        base_label = metric.label or metric.name.replace("_", " ").title()

        result: dict[str, Any] = {
            "name": f"{metric.name}_change",
            "type": "number",
            "label": f"{base_label} Change",
            "description": f"Difference between current and prior period {base_label}",
            "sql": f"${{{metric.name}}} - ${{{metric.name}_prior}}",
        }

        if metric.format:
            result["value_format_name"] = metric.format

        if metric.group:
            apply_group_labels(result, metric.group_parts)

        return result

    def _render_pct_change(self, metric: Metric) -> dict[str, Any]:
        """Render the _pct_change measure."""
        base_label = metric.label or metric.name.replace("_", " ").title()

        result: dict[str, Any] = {
            "name": f"{metric.name}_pct_change",
            "type": "number",
            "label": f"{base_label} % Change",
            "description": f"Percent change from prior period",
            "sql": f"(${{{metric.name}}} - ${{{metric.name}_prior}}) / NULLIF(${{{metric.name}_prior}}, 0)",
            "value_format_name": "percent_1",
        }

        if metric.group:
            apply_group_labels(result, metric.group_parts)

        return result
