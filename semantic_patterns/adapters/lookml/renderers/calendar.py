"""Calendar view rendering for explore-level date selection.

Generates a unified calendar view per explore that aggregates date selector
dimensions from all participating models.

When PoP (period-over-period) metrics exist, also generates:
- date_range filter for selecting analysis period
- comparison_period parameter for dynamic PoP selection
- is_selected_period / is_comparison_period dimensions for filtered measures
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from semantic_patterns.adapters.dialect import Dialect, SqlRenderer, get_default_dialect
from semantic_patterns.domain import PopComparison, ProcessedModel


@dataclass
class DateOption:
    """A date field option for the explore calendar."""

    view: str  # View name (e.g., "rentals")
    dimension: str  # Dimension name (e.g., "created_at")
    label: str  # Display label (e.g., "Rental Created")
    raw_ref: str  # LookML reference (e.g., "${rentals.created_at_raw}")

    @property
    def parameter_value(self) -> str:
        """Value for the parameter (uses __ instead of . for LookML safety)."""
        return f"{self.view}__{self.dimension}"


@dataclass
class PopCalendarConfig:
    """Configuration for PoP-enabled calendar generation."""

    enabled: bool = False
    comparisons: list[PopComparison] = field(default_factory=list)
    default_comparison: str = "year"  # Default to prior year

    @classmethod
    def from_models(cls, models: list[ProcessedModel]) -> "PopCalendarConfig":
        """Build PoP config by scanning models for PoP-enabled metrics."""
        all_comparisons: set[PopComparison] = set()

        for model in models:
            for metric in model.metrics:
                if metric.pop and metric.pop.comparisons:
                    all_comparisons.update(metric.pop.comparisons)

        if all_comparisons:
            return cls(enabled=True, comparisons=sorted(all_comparisons, key=lambda c: c.value))
        return cls(enabled=False)


# Map PopComparison to display labels for the parameter
COMPARISON_LABELS: dict[PopComparison, str] = {
    PopComparison.PRIOR_YEAR: "Prior Year",
    PopComparison.PRIOR_MONTH: "Prior Month",
    PopComparison.PRIOR_QUARTER: "Prior Quarter",
    PopComparison.PRIOR_WEEK: "Prior Week",
}

# Map PopComparison to Looker period values
COMPARISON_PERIODS: dict[PopComparison, str] = {
    PopComparison.PRIOR_YEAR: "year",
    PopComparison.PRIOR_MONTH: "month",
    PopComparison.PRIOR_QUARTER: "quarter",
    PopComparison.PRIOR_WEEK: "week",
}


def _smart_title(name: str) -> str:
    """Convert snake_case to Title Case."""
    return " ".join(word.capitalize() for word in name.replace("_", " ").split())


class CalendarRenderer:
    """Render explore-level calendar views for unified date selection."""

    def __init__(self, dialect: Dialect | None = None) -> None:
        self.dialect = dialect or get_default_dialect()
        self.sql_renderer = SqlRenderer(self.dialect)

    def render(
        self,
        explore_name: str,
        date_options: list[DateOption],
        pop_config: PopCalendarConfig | None = None,
    ) -> dict[str, Any] | None:
        """
        Render calendar view dict for lkml serialization.

        Returns None if no date options provided.
        """
        if not date_options:
            return None

        view_name = f"{explore_name}_explore_calendar"

        # Build date_field parameter with allowed values
        allowed_values = []
        for opt in date_options:
            allowed_values.append({
                "label": opt.label,
                "value": opt.parameter_value,
            })

        # Use first option as default
        default_value = date_options[0].parameter_value

        date_field_param: dict[str, Any] = {
            "name": "date_field",
            "type": "unquoted",
            "label": "Analysis Date",
            "description": "Select which date field to use for calendar analysis",
            "view_label": " Calendar",  # Space prefix sorts to top
            "default_value": default_value,
            "allowed_values": allowed_values,
        }

        # Build CASE statement for dynamic date expression
        case_statement = self._build_date_case_statement(date_options)

        dimension_group: dict[str, Any] = {
            "name": "calendar",
            "type": "time",
            "label": "Calendar",
            "description": "Dynamic date based on Analysis Date selection",
            "view_label": " Calendar",  # Space prefix sorts to top
            "timeframes": ["date", "week", "month", "quarter", "year"],
            "convert_tz": "no",
            "sql": case_statement,
        }

        parameters = [date_field_param]
        dimensions = []
        filters = []

        # Add PoP infrastructure if enabled
        if pop_config and pop_config.enabled:
            pop_elements = self._render_pop_infrastructure(
                date_options, pop_config, view_name
            )
            if pop_elements.get("filter"):
                filters.append(pop_elements["filter"])
            if pop_elements.get("parameter"):
                parameters.append(pop_elements["parameter"])
            if pop_elements.get("dimensions"):
                dimensions.extend(pop_elements["dimensions"])

        result: dict[str, Any] = {
            "name": view_name,
            "parameters": parameters,
            "dimension_groups": [dimension_group],
        }

        if filters:
            result["filters"] = filters
        if dimensions:
            result["dimensions"] = dimensions

        return result

    def _build_date_case_statement(self, date_options: list[DateOption]) -> str:
        """Build CASE statement for dynamic date selection."""
        case_branches = []
        for opt in date_options:
            case_branches.append(
                f"WHEN '{opt.parameter_value}' THEN {opt.raw_ref}"
            )
        return (
            "CASE {% parameter date_field %}\n        "
            + "\n        ".join(case_branches)
            + "\n      END"
        )

    def _render_pop_infrastructure(
        self,
        date_options: list[DateOption],
        pop_config: PopCalendarConfig,
        view_name: str,
    ) -> dict[str, Any]:
        """
        Render PoP infrastructure: date_range filter, comparison_period param,
        and period classification dimensions.
        """
        result: dict[str, Any] = {}

        # date_range filter - user selects the analysis period
        result["filter"] = {
            "name": "date_range",
            "type": "date",
            "label": "Date Range",
            "description": "Select date range for analysis. PoP comparisons offset from this range.",
            "view_label": " Calendar",
        }

        # comparison_period parameter - user selects which period to compare to
        comparison_allowed_values = []
        for comp in pop_config.comparisons:
            comparison_allowed_values.append({
                "label": COMPARISON_LABELS.get(comp, comp.value),
                "value": COMPARISON_PERIODS.get(comp, comp.value),
            })

        result["parameter"] = {
            "name": "comparison_period",
            "type": "unquoted",
            "label": "Compare To",
            "description": "Select comparison period for PoP analysis",
            "view_label": " Calendar",
            "default_value": pop_config.default_comparison,
            "allowed_values": comparison_allowed_values,
        }

        # Build the dynamic date expression for period classification
        date_case_expr = self._build_date_case_statement(date_options)

        # is_selected_period - TRUE if date falls within selected date_range
        is_selected_sql = f"{{% condition date_range %}} {date_case_expr} {{% endcondition %}}"

        # is_comparison_period - TRUE if date falls within the offset period
        # Uses dialect-specific DATEADD to shift the date forward by comparison period
        # Then checks if the shifted date falls within the selected range
        dateadd_expr = self._build_comparison_dateadd(date_case_expr)
        is_comparison_sql = f"""{{% condition date_range %}}
          {dateadd_expr}
        {{% endcondition %}}"""

        result["dimensions"] = [
            {
                "name": "is_selected_period",
                "type": "yesno",
                "hidden": "yes",
                "sql": is_selected_sql,
            },
            {
                "name": "is_comparison_period",
                "type": "yesno",
                "hidden": "yes",
                "sql": is_comparison_sql,
            },
        ]

        return result

    def _build_comparison_dateadd(self, date_expr: str) -> str:
        """
        Build dialect-specific DATEADD for comparison period offset.

        The comparison period is dynamic (from parameter), so we use
        Liquid to inject the period value into the SQL.
        """
        # For dynamic period, we need to use Liquid parameter in the SQL
        # The dateadd method expects static values, so we build a template
        # that will work with Looker's Liquid processing

        if self.dialect in (Dialect.REDSHIFT, Dialect.SNOWFLAKE):
            return f"DATEADD({{% parameter comparison_period %}}, 1, {date_expr})"

        elif self.dialect == Dialect.BIGQUERY:
            # BigQuery needs uppercase period and different syntax
            return f"DATE_ADD({date_expr}, INTERVAL 1 {{% parameter comparison_period %}})"

        elif self.dialect in (Dialect.POSTGRES, Dialect.DUCKDB):
            return f"{date_expr} + INTERVAL '1 ' || {{% parameter comparison_period %}}"

        elif self.dialect == Dialect.STARBURST:
            return f"date_add({{% parameter comparison_period %}}, 1, {date_expr})"

        else:
            # Fallback to Redshift syntax
            return f"DATEADD({{% parameter comparison_period %}}, 1, {date_expr})"

    def collect_date_options(
        self,
        fact_model: ProcessedModel,
        joined_models: list[ProcessedModel],
    ) -> list[DateOption]:
        """
        Collect date selector dimensions from all models in explore.

        Args:
            fact_model: The fact model for this explore
            joined_models: List of models joined to the fact

        Returns:
            List of DateOption objects for all eligible date dimensions
        """
        options: list[DateOption] = []

        all_models = [fact_model] + joined_models
        for model in all_models:
            if not model.date_selector:
                continue

            for dim_name in model.date_selector.dimensions:
                dim = model.get_dimension(dim_name)
                if dim:
                    # Generate label from view and dimension
                    view_title = _smart_title(model.name)
                    dim_title = dim.label or _smart_title(dim_name)
                    label = f"{view_title} {dim_title}"

                    options.append(
                        DateOption(
                            view=model.name,
                            dimension=dim_name,
                            label=label,
                            raw_ref=f"${{{model.name}.{dim_name}_raw}}",
                        )
                    )

        return options
