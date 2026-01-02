"""Measure domain - aggregatable numeric values."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AggregationType(str, Enum):
    """Supported aggregation types for measures."""

    SUM = "sum"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    PERCENTILE = "percentile"


class Measure(BaseModel):
    """
    A measure represents an aggregatable numeric value.

    This is the raw aggregation - sum, count, average, etc.
    Measures are typically not exposed directly; metrics use them.
    """

    name: str = Field(..., description="Unique identifier for the measure")
    agg: AggregationType = Field(..., description="Aggregation type")
    expr: str = Field(..., description="SQL expression for the measure")
    label: str | None = Field(None, description="Display label")
    description: str | None = Field(None, description="Human-readable description")

    # Display/organization
    format: str | None = Field(None, description="Value format (usd, decimal_0, etc.)")
    group: str | None = Field(None, description="Grouping (supports dot notation)")
    hidden: bool = Field(False, description="Hide from BI users")

    # Metadata
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @property
    def group_parts(self) -> list[str]:
        """Parse group into parts (handles dot notation)."""
        if not self.group:
            return []
        return self.group.split(".")

    model_config = {"frozen": False, "extra": "forbid"}
