"""Data models for dbt semantic models and LookML structures."""

from __future__ import annotations

import re
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

    def to_lookml_dict(self) -> dict[str, Any]:
        """Convert entity to LookML dimension format."""
        result: dict[str, Any] = {
            'name': self.name,
            'type': 'string',
            'sql': self.expr or self.name,
        }
        
        if self.type == 'primary':
            result['primary_key'] = 'yes'
            
        if self.description:
            result['description'] = self.description
            
        return result


class Dimension(BaseModel):
    """Represents a dimension in a semantic model."""

    name: str
    type: DimensionType
    expr: Optional[str] = None
    description: Optional[str] = None
    label: Optional[str] = None
    type_params: Optional[dict[str, Any]] = None

    def to_lookml_dict(self) -> dict[str, Any]:
        """Convert dimension to LookML format."""
        if self.type == DimensionType.TIME:
            return self._to_dimension_group_dict()
        else:
            return self._to_dimension_dict()

    def _to_dimension_dict(self) -> dict[str, Any]:
        """Convert categorical dimension to LookML dimension."""
        result: dict[str, Any] = {
            'name': self.name,
            'type': 'string',  # Most categorical dims are strings
            'sql': self.expr or self.name,
        }
        
        if self.description:
            result['description'] = self.description
        if self.label:
            result['label'] = self.label
            
        return result

    def _to_dimension_group_dict(self) -> dict[str, Any]:
        """Convert time dimension to LookML dimension_group."""
        # Determine timeframes based on granularity
        timeframes = ['date', 'week', 'month', 'quarter', 'year']
        
        if self.type_params and 'time_granularity' in self.type_params:
            granularity = self.type_params['time_granularity']
            if granularity in ['hour', 'minute']:
                timeframes = ['time', 'hour', 'date', 'week', 'month', 'quarter', 'year']
        
        result: dict[str, Any] = {
            'name': self.name,
            'type': 'time',
            'timeframes': timeframes,
            'sql': self.expr or self.name,
        }
        
        if self.description:
            result['description'] = self.description
        if self.label:
            result['label'] = self.label
            
        return result


class Measure(BaseModel):
    """Represents a measure in a semantic model."""

    name: str
    agg: AggregationType
    expr: Optional[str] = None
    description: Optional[str] = None
    label: Optional[str] = None
    create_metric: Optional[bool] = None

    def to_lookml_dict(self) -> dict[str, Any]:
        """Convert measure to LookML format."""
        # Map dbt aggregation types to LookML measure types
        lookml_type_map = {
            AggregationType.COUNT: 'count',
            AggregationType.COUNT_DISTINCT: 'count_distinct', 
            AggregationType.SUM: 'sum',
            AggregationType.AVERAGE: 'average',
            AggregationType.MIN: 'min',
            AggregationType.MAX: 'max',
            AggregationType.MEDIAN: 'median',
        }
        
        result: dict[str, Any] = {
            'name': self.name,
            'type': lookml_type_map[self.agg],
            'sql': self.expr or self.name,
        }
        
        if self.description:
            result['description'] = self.description
        if self.label:
            result['label'] = self.label
            
        return result


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

    def to_lookml_dict(self) -> dict[str, Any]:
        """Convert entire semantic model to lkml views format."""
        dimensions = []
        dimension_groups = []
        
        # Convert entities to dimensions
        for entity in self.entities:
            dimensions.append(entity.to_lookml_dict())
        
        # Convert dimensions (separate regular dims from time dims)
        for dim in self.dimensions:
            dim_dict = dim.to_lookml_dict()
            if dim.type == DimensionType.TIME:
                dimension_groups.append(dim_dict)
            else:
                dimensions.append(dim_dict)
        
        # Convert measures
        measures = [measure.to_lookml_dict() for measure in self.measures]
        
        # Build the view dict
        view_dict: dict[str, Any] = {
            'name': self.name,
            'sql_table_name': self._extract_table_name(),
        }
                    
        if dimensions:
            view_dict['dimensions'] = dimensions
            
        if dimension_groups:
            view_dict['dimension_groups'] = dimension_groups
            
        if measures:
            view_dict['measures'] = measures
            
        return {'views': [view_dict]}
    
    def _extract_table_name(self) -> str:
        """Extract table name from dbt ref() syntax."""
        # Handle ref('table_name') syntax
        match = re.search(r"ref\(['\"]([^'\"]+)['\"]\)", self.model)
        return match.group(1) if match else self.model


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
