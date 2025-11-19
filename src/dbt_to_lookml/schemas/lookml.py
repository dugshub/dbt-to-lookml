"""LookML output schemas for Looker views and explores.

This module contains schema definitions for LookML structures that are generated
as output from the conversion process. These schemas represent Looker's view and
explore definitions.

LookML is Looker's modeling language for defining dimensions, measures, and explores
that power analytics and visualization in the Looker platform.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "LookMLDimension",
    "LookMLDimensionGroup",
    "LookMLMeasure",
    "LookMLSet",
    "LookMLView",
    "LookMLExplore",
]


class LookMLDimension(BaseModel):
    """Represents a LookML dimension."""

    name: str
    type: str
    sql: str
    description: str | None = None
    label: str | None = None
    hidden: bool | None = None
    primary_key: bool | None = None
    view_label: str | None = None
    group_label: str | None = None


class LookMLDimensionGroup(BaseModel):
    """Represents a LookML dimension_group for time dimensions."""

    name: str
    type: str = "time"
    timeframes: list[str] = Field(
        default_factory=lambda: ["date", "week", "month", "quarter", "year"]
    )
    sql: str
    description: str | None = None
    label: str | None = None
    hidden: bool | None = None
    view_label: str | None = None
    group_label: str | None = None


class LookMLMeasure(BaseModel):
    """Represents a LookML measure."""

    name: str
    type: str
    sql: str
    description: str | None = None
    label: str | None = None
    hidden: bool | None = None
    view_label: str | None = None
    group_label: str | None = None


class LookMLSet(BaseModel):
    """Represents a LookML set for grouping fields."""

    name: str
    fields: list[str]


class LookMLView(BaseModel):
    """Represents a LookML view."""

    name: str
    sql_table_name: str
    description: str | None = None
    dimensions: list[LookMLDimension] = Field(default_factory=list)
    dimension_groups: list[LookMLDimensionGroup] = Field(default_factory=list)
    measures: list[LookMLMeasure] = Field(default_factory=list)
    sets: list[LookMLSet] = Field(default_factory=list)

    def to_lookml_dict(self) -> dict[str, Any]:
        """Convert LookML view to dictionary format."""

        def convert_bools(d: dict[str, Any]) -> dict[str, Any]:
            """Convert boolean values to LookML-compatible strings."""
            result: dict[str, Any] = {}
            for k, v in d.items():
                if isinstance(v, bool):
                    result[k] = "yes" if v else "no"
                elif isinstance(v, dict):
                    result[k] = convert_bools(v)
                elif isinstance(v, list):
                    result[k] = [
                        convert_bools(item) if isinstance(item, dict) else item
                        for item in v
                    ]
                else:
                    result[k] = v
            return result

        view_dict: dict[str, Any] = {
            "name": self.name,
            "sql_table_name": self.sql_table_name,
        }

        if self.description:
            view_dict["description"] = self.description

        if self.sets:
            view_dict["sets"] = [
                convert_bools(set_item.model_dump(exclude_none=True))
                for set_item in self.sets
            ]

        if self.dimensions:
            view_dict["dimensions"] = [
                convert_bools(dim.model_dump(exclude_none=True))
                for dim in self.dimensions
            ]

        if self.dimension_groups:
            view_dict["dimension_groups"] = [
                convert_bools(dg.model_dump(exclude_none=True))
                for dg in self.dimension_groups
            ]

        if self.measures:
            view_dict["measures"] = [
                convert_bools(measure.model_dump(exclude_none=True))
                for measure in self.measures
            ]

        return {"views": [view_dict]}


class LookMLExplore(BaseModel):
    """Represents a LookML explore."""

    name: str
    view_name: str
    type: str | None = "table"  # Default type
    description: str | None = None
    hidden: bool | None = None
    joins: list[dict[str, Any]] = Field(
        default_factory=list
    )  # For backward compatibility
