"""Period-over-Period (PoP) rendering for LookML.

Uses a strategy pattern to allow swapping PoP implementations.
Current: Looker's native period_over_period measure type.
Future: Could add custom SQL-based PoP, offset-based PoP, etc.
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
