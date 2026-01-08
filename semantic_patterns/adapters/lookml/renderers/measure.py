"""Measure and metric rendering for LookML."""

from typing import Any

from semantic_patterns.adapters.dialect import Dialect
from semantic_patterns.adapters.lookml.renderers.filter import FilterRenderer
from semantic_patterns.adapters.lookml.renderers.labels import apply_group_labels
from semantic_patterns.adapters.lookml.sql_qualifier import LookMLSqlQualifier
from semantic_patterns.domain import (
    AggregationType,
    Measure,
    Metric,
    MetricType,
)

# Map AggregationType to LookML measure type
AGG_TO_LOOKML: dict[AggregationType, str] = {
    AggregationType.SUM: "sum",
    AggregationType.COUNT: "count",
    AggregationType.COUNT_DISTINCT: "count_distinct",
    AggregationType.AVERAGE: "average",
    AggregationType.MIN: "min",
    AggregationType.MAX: "max",
    AggregationType.MEDIAN: "median",
    AggregationType.PERCENTILE: "percentile",
}

# Map format strings to LookML value_format_name
FORMAT_TO_LOOKML: dict[str, str] = {
    "usd": "usd",
    "decimal_0": "decimal_0",
    "decimal_1": "decimal_1",
    "decimal_2": "decimal_2",
    "percent_1": "percent_1",
    "percent_2": "percent_2",
}


class MeasureRenderer:
    """Render measures and metrics to LookML format."""

    def __init__(self, dialect: Dialect | None = None, defined_fields: dict[str, str] | None = None) -> None:
        self.sql_qualifier = LookMLSqlQualifier(dialect, defined_fields)
        self.defined_fields = defined_fields or {}
        self.filter_renderer = FilterRenderer(dialect, defined_fields)

    def render_measure(self, measure: Measure, defined_fields: dict[str, str] | None = None) -> dict[str, Any]:
        """Render a raw measure to LookML."""
        fields = defined_fields if defined_fields is not None else self.defined_fields

        # Determine LookML measure type
        # Special case: COUNT with an expr should be count_distinct in LookML
        # because LookML's "count" type just counts rows (no sql parameter)
        lookml_type = AGG_TO_LOOKML.get(measure.agg, "sum")
        if measure.agg == AggregationType.COUNT and measure.expr:
            lookml_type = "count_distinct"

        result: dict[str, Any] = {
            "name": measure.name,
            "type": lookml_type,
            "sql": self._qualify_expr(measure.expr, fields),
        }

        if measure.label:
            result["label"] = measure.label

        if measure.description:
            result["description"] = measure.description

        if measure.hidden:
            result["hidden"] = "yes"

        if measure.format and measure.format in FORMAT_TO_LOOKML:
            result["value_format_name"] = FORMAT_TO_LOOKML[measure.format]

        if measure.group:
            apply_group_labels(result, measure.group_parts)

        return result

    def render_metric(
        self,
        metric: Metric,
        measures: dict[str, Measure],
        defined_fields: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Render a metric (base variant) to LookML measure.

        For simple metrics: direct aggregation from the underlying measure
        For derived/ratio: type: number with SQL expression
        """
        fields = defined_fields if defined_fields is not None else self.defined_fields

        if metric.type == MetricType.SIMPLE:
            return self._render_simple_metric(metric, measures, fields)
        elif metric.type == MetricType.DERIVED:
            return self._render_derived_metric(metric)
        elif metric.type == MetricType.RATIO:
            return self._render_ratio_metric(metric)
        else:
            return self._render_simple_metric(metric, measures, fields)

    def _render_simple_metric(
        self,
        metric: Metric,
        measures: dict[str, Measure],
        defined_fields: dict[str, str],
    ) -> dict[str, Any]:
        """Render simple metric as direct aggregation."""
        # Get the underlying measure
        measure = measures.get(metric.measure or "") if metric.measure else None

        if measure:
            # Qualify the expression (use field references for defined dimensions)
            qualified_expr = self._qualify_expr(measure.expr, defined_fields)

            # Wrap with filter if metric has one
            if metric.filter and metric.filter.conditions:
                sql_expr = self.filter_renderer.render_case_when(
                    qualified_expr, metric.filter, defined_fields
                )
            else:
                sql_expr = qualified_expr

            # Determine LookML measure type
            # Special case: COUNT with an expr should be count_distinct in LookML
            lookml_type = AGG_TO_LOOKML.get(measure.agg, "sum")
            if measure.agg == AggregationType.COUNT and measure.expr:
                lookml_type = "count_distinct"

            result: dict[str, Any] = {
                "name": metric.name,
                "type": lookml_type,
                "sql": sql_expr,
            }
        else:
            # Fallback: reference measure by name
            result = {
                "name": metric.name,
                "type": "number",
                "sql": f"${{TABLE}}.{metric.measure}",
            }

        self._add_common_fields(result, metric)
        return result

    def _render_derived_metric(self, metric: Metric) -> dict[str, Any]:
        """Render derived metric as type: number with expression."""
        # Replace metric references with ${metric_name}
        sql_expr = metric.expr or ""
        for dep in metric.metrics or []:
            sql_expr = sql_expr.replace(dep, f"${{{dep}}}")

        result: dict[str, Any] = {
            "name": metric.name,
            "type": "number",
            "sql": sql_expr,
        }

        self._add_common_fields(result, metric)
        return result

    def _render_ratio_metric(self, metric: Metric) -> dict[str, Any]:
        """Render ratio metric as type: number."""
        numerator = metric.numerator or "0"
        denominator = metric.denominator or "1"

        result: dict[str, Any] = {
            "name": metric.name,
            "type": "number",
            "sql": f"${{{numerator}}} / NULLIF(${{{denominator}}}, 0)",
        }

        self._add_common_fields(result, metric)
        return result

    def _add_common_fields(self, result: dict[str, Any], metric: Metric) -> None:
        """Add common fields to metric result."""
        if metric.label:
            result["label"] = metric.label

        if metric.description:
            result["description"] = metric.description

        if metric.format and metric.format in FORMAT_TO_LOOKML:
            result["value_format_name"] = FORMAT_TO_LOOKML[metric.format]

        if metric.group:
            apply_group_labels(result, metric.group_parts)

    def _qualify_expr(self, expr: str, defined_fields: dict[str, str]) -> str:
        """Qualify column references in expression (use field refs for defined dimensions)."""
        return self.sql_qualifier.qualify(expr, defined_fields)
