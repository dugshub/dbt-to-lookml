"""Dimension rendering for LookML."""

from typing import Any

from dbt_to_lookml_v2.adapters.dialect import Dialect, SqlRenderer
from dbt_to_lookml_v2.adapters.lookml.renderers.labels import apply_group_labels
from dbt_to_lookml_v2.domain import Dimension, DimensionType, TimeGranularity

# Map TimeGranularity to LookML timeframes
GRANULARITY_TIMEFRAMES: dict[TimeGranularity, list[str]] = {
    TimeGranularity.HOUR: [
        "raw", "time", "hour", "date", "week", "month", "quarter", "year"
    ],
    TimeGranularity.DAY: ["raw", "date", "week", "month", "quarter", "year"],
    TimeGranularity.WEEK: ["raw", "week", "month", "quarter", "year"],
    TimeGranularity.MONTH: ["raw", "month", "quarter", "year"],
    TimeGranularity.QUARTER: ["raw", "quarter", "year"],
    TimeGranularity.YEAR: ["raw", "year"],
}

DEFAULT_TIMEFRAMES = ["raw", "date", "week", "month", "quarter", "year"]


class DimensionRenderer:
    """Render dimensions to LookML format."""

    def __init__(self, dialect: Dialect | None = None) -> None:
        self.sql_renderer = SqlRenderer(dialect)

    def render(self, dimension: Dimension) -> list[dict[str, Any]]:
        """
        Render a dimension to LookML dict(s).

        Returns a list because time dimensions with variants
        generate multiple dimension_groups.
        """
        if dimension.type == DimensionType.TIME:
            return self._render_time_dimension(dimension)
        else:
            return [self._render_categorical_dimension(dimension)]

    def _render_categorical_dimension(self, dim: Dimension) -> dict[str, Any]:
        """Render a categorical dimension."""
        result: dict[str, Any] = {
            "name": dim.name,
            "type": "string",
            "sql": self._qualify_expr(dim.effective_expr),
        }

        if dim.label:
            result["label"] = dim.label

        if dim.description:
            result["description"] = dim.description

        if dim.hidden:
            result["hidden"] = "yes"

        if dim.group:
            apply_group_labels(result, dim.group_parts)

        return result

    def _render_time_dimension(self, dim: Dimension) -> list[dict[str, Any]]:
        """
        Render a time dimension as dimension_group(s).

        If dimension has variants (UTC/local), generates one per variant.
        """
        if dim.has_variants and dim.variants:
            return self._render_time_with_variants(dim)
        else:
            return [self._render_single_time_dimension(dim)]

    def _render_single_time_dimension(self, dim: Dimension) -> dict[str, Any]:
        """Render a single time dimension_group."""
        result: dict[str, Any] = {
            "name": dim.name,
            "type": "time",
            "sql": self._qualify_expr(dim.effective_expr),
            "timeframes": self._get_timeframes(dim.granularity),
            "convert_tz": "no",  # Data is UTC, don't convert
        }

        if dim.label:
            result["label"] = dim.label

        if dim.description:
            result["description"] = dim.description

        if dim.hidden:
            result["hidden"] = "yes"

        if dim.group:
            apply_group_labels(result, dim.group_parts)

        return result

    def _render_time_with_variants(self, dim: Dimension) -> list[dict[str, Any]]:
        """Render time dimension with timezone variants."""
        results = []

        for variant_name, expr in (dim.variants or {}).items():
            is_primary = variant_name == dim.primary_variant

            # Name: created_at_utc, created_at_local
            name = f"{dim.name}_{variant_name}"

            result: dict[str, Any] = {
                "name": name,
                "type": "time",
                "sql": self._qualify_expr(expr),
                "timeframes": self._get_timeframes(dim.granularity),
                "convert_tz": "no",  # Data is UTC, don't convert
            }

            # Label includes variant
            if dim.label:
                if variant_name == "utc":
                    variant_label = variant_name.upper()
                else:
                    variant_label = variant_name.title()
                result["label"] = f"{dim.label} ({variant_label})"
            else:
                name_title = dim.name.replace("_", " ").title()
                result["label"] = f"{name_title} ({variant_name.upper()})"

            if dim.description:
                result["description"] = dim.description

            # Non-primary variants can be hidden by default
            if dim.hidden or (not is_primary and not dim.hidden):
                # Only hide non-primary if not explicitly shown
                pass  # For now, show all variants

            if dim.group:
                apply_group_labels(result, dim.group_parts)

            results.append(result)

        return results

    def _get_timeframes(self, granularity: TimeGranularity | None) -> list[str]:
        """Get appropriate timeframes for granularity."""
        if granularity and granularity in GRANULARITY_TIMEFRAMES:
            return GRANULARITY_TIMEFRAMES[granularity]
        return DEFAULT_TIMEFRAMES

    def _qualify_expr(self, expr: str) -> str:
        """Qualify column references in expression."""
        return self.sql_renderer.qualify_expression(expr)
