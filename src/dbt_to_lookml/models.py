"""Data models for dbt semantic models and LookML structures."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AggregationType(str, Enum):
    """Supported aggregation types for measures."""

    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"


class DimensionType(str, Enum):
    """Supported dimension types."""

    CATEGORICAL = "categorical"
    TIME = "time"


class TimeGranularity(str, Enum):
    """Supported time granularities."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    HOUR = "hour"
    MINUTE = "minute"


class ConfigMeta(BaseModel):
    """Represents metadata in a config section."""

    domain: Optional[str] = None
    owner: Optional[str] = None
    contains_pii: Optional[bool] = None
    update_frequency: Optional[str] = None


class Config(BaseModel):
    """Represents a config section in a semantic model."""

    meta: Optional[ConfigMeta] = None


class Entity(BaseModel):
    """Represents an entity in a semantic model."""

    name: str
    type: str
    expr: Optional[str] = None
    description: Optional[str] = None


class Dimension(BaseModel):
    """Represents a dimension in a semantic model."""

    name: str
    type: DimensionType
    expr: Optional[str] = None
    description: Optional[str] = None
    label: Optional[str] = None
    type_params: Optional[dict[str, Any]] = None


class Measure(BaseModel):
    """Represents a measure in a semantic model."""

    name: str
    agg: AggregationType
    expr: Optional[str] = None
    description: Optional[str] = None
    label: Optional[str] = None
    create_metric: Optional[bool] = None


class SemanticModel(BaseModel):
    """Represents a complete semantic model."""

    name: str
    model: str
    description: Optional[str] = None
    config: Optional[Config] = None
    defaults: Optional[dict[str, Any]] = None
    entities: list[Entity] = Field(default_factory=list)
    dimensions: list[Dimension] = Field(default_factory=list)
    measures: list[Measure] = Field(default_factory=list)


class LookMLDimension(BaseModel):
    """Represents a LookML dimension."""

    name: str
    type: str
    sql: str
    description: Optional[str] = None
    label: Optional[str] = None
    hidden: Optional[bool] = None
    primary_key: Optional[bool] = None


class LookMLDimensionGroup(BaseModel):
    """Represents a LookML dimension_group for time dimensions."""

    name: str
    type: str = "time"
    timeframes: list[str] = Field(default_factory=lambda: ["date", "week", "month", "quarter", "year"])
    sql: str
    description: Optional[str] = None
    label: Optional[str] = None
    hidden: Optional[bool] = None


class LookMLMeasure(BaseModel):
    """Represents a LookML measure."""

    name: str
    type: str
    sql: str
    description: Optional[str] = None
    label: Optional[str] = None
    hidden: Optional[bool] = None


class LookMLView(BaseModel):
    """Represents a LookML view."""

    name: str
    sql_table_name: str
    description: Optional[str] = None
    dimensions: list[LookMLDimension] = Field(default_factory=list)
    dimension_groups: list[LookMLDimensionGroup] = Field(default_factory=list)
    measures: list[LookMLMeasure] = Field(default_factory=list)


class LookMLExplore(BaseModel):
    """Represents a LookML explore."""

    name: str
    view_name: str
    description: Optional[str] = None
    hidden: Optional[bool] = None
