"""Dimension domain - categorical and time-based attributes."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class DimensionType(str, Enum):
    """Dimension types."""

    CATEGORICAL = "categorical"
    TIME = "time"


class TimeGranularity(str, Enum):
    """Time granularity for time dimensions."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class TimezoneVariant(BaseModel):
    """A timezone variant for a time dimension."""

    name: str  # e.g., "utc", "local"
    expr: str  # SQL expression

    model_config = {"frozen": True}


class Dimension(BaseModel):
    """
    A dimension represents a categorical or time-based attribute for grouping/filtering.

    Time dimensions can have timezone variants (UTC/local pairs).
    """

    name: str = Field(..., description="Unique identifier")
    type: DimensionType = Field(..., description="Dimension type")
    label: str | None = Field(None, description="Display label")
    short_label: str | None = Field(None, description="Short label for compact displays")
    description: str | None = Field(None, description="Human-readable description")

    # SQL expression (required unless variants specified)
    expr: str | None = Field(None, description="SQL expression")

    # Time-specific
    granularity: TimeGranularity | None = Field(
        None, description="Time granularity (day, hour, etc.)"
    )

    # Timezone variants for time dimensions
    primary_variant: str | None = Field(
        None, description="Which variant is default (e.g., 'utc')"
    )
    variants: dict[str, str] | None = Field(
        None, description="Timezone variants: {name: expr}"
    )

    # Display/organization
    group: str | None = Field(None, description="Grouping (supports dot notation)")
    hidden: bool = Field(False, description="Hide from BI users")

    # Metadata
    meta: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_expr_or_variants(self) -> "Dimension":
        """Ensure either expr or variants is specified."""
        if self.expr is None and not self.variants:
            raise ValueError("Either 'expr' or 'variants' must be specified")
        return self

    @model_validator(mode="after")
    def validate_primary_variant(self) -> "Dimension":
        """Ensure primary_variant is valid if variants specified."""
        if self.variants and self.primary_variant:
            if self.primary_variant not in self.variants:
                raise ValueError(
                    f"primary_variant '{self.primary_variant}' not in variants"
                )
        return self

    @property
    def has_variants(self) -> bool:
        """Check if dimension has timezone variants."""
        return bool(self.variants)

    @property
    def effective_expr(self) -> str:
        """Get the effective SQL expression (primary variant or expr)."""
        if self.variants and self.primary_variant:
            return self.variants[self.primary_variant]
        if self.variants:
            # Return first variant if no primary specified
            return next(iter(self.variants.values()))
        return self.expr or ""

    @property
    def group_parts(self) -> list[str]:
        """Parse group into parts (handles dot notation and lists)."""
        if not self.group:
            return []
        if isinstance(self.group, list):
            return self.group
        return self.group.split(".")

    model_config = {"frozen": False, "extra": "forbid"}
