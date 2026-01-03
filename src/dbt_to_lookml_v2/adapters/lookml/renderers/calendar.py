"""Calendar view rendering for explore-level date selection.

Generates a unified calendar view per explore that aggregates date selector
dimensions from all participating models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dbt_to_lookml_v2.domain import ProcessedModel


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


def _smart_title(name: str) -> str:
    """Convert snake_case to Title Case."""
    return " ".join(word.capitalize() for word in name.replace("_", " ").split())


class CalendarRenderer:
    """Render explore-level calendar views for unified date selection."""

    def render(
        self,
        explore_name: str,
        date_options: list[DateOption],
    ) -> dict[str, Any] | None:
        """
        Render calendar view dict for lkml serialization.

        Returns None if no date options provided.
        """
        if not date_options:
            return None

        view_name = f"{explore_name}_explore_calendar"

        # Build parameter with allowed values
        allowed_values = []
        for opt in date_options:
            allowed_values.append({
                "label": opt.label,
                "value": opt.parameter_value,
            })

        # Use first option as default
        default_value = date_options[0].parameter_value

        parameter: dict[str, Any] = {
            "name": "date_field",
            "type": "unquoted",
            "label": "Analysis Date",
            "description": "Select which date field to use for calendar analysis",
            "view_label": " Calendar",  # Space prefix sorts to top
            "default_value": default_value,
            "allowed_values": allowed_values,
        }

        # Build CASE statement for calendar dimension_group
        case_branches = []
        for opt in date_options:
            case_branches.append(
                f"WHEN '{opt.parameter_value}' THEN {opt.raw_ref}"
            )
        case_statement = (
            "CASE {% parameter date_field %}\n        "
            + "\n        ".join(case_branches)
            + "\n      END"
        )

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

        return {
            "name": view_name,
            "parameters": [parameter],
            "dimension_groups": [dimension_group],
        }

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
