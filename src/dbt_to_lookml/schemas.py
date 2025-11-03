"""Schema definitions for dbt semantic models and LookML structures."""

from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel, Field

from dbt_to_lookml.types import AggregationType, DimensionType, LOOKML_TYPE_MAP


# ============================================================================
# Semantic Model Schemas (Input)
# ============================================================================

class Hierarchy(BaseModel):
    """Represents the 3-tier hierarchy for labeling."""

    entity: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None


class ConfigMeta(BaseModel):
    """Represents metadata in a config section."""

    domain: Optional[str] = None
    owner: Optional[str] = None
    contains_pii: Optional[bool] = None
    update_frequency: Optional[str] = None
    hierarchy: Optional[Hierarchy] = None


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
            'sql': self.expr or f"${{TABLE}}.{self.name}",
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
    config: Optional[Config] = None

    def to_lookml_dict(self) -> dict[str, Any]:
        """Convert dimension to LookML format."""
        if self.type == DimensionType.TIME:
            return self._to_dimension_group_dict()
        else:
            return self._to_dimension_dict()

    def get_dimension_labels(self) -> tuple[Optional[str], Optional[str]]:
        """Get view_label and group_label for dimension based on hierarchy.

        Returns:
            Tuple of (view_label, group_label) where:
            - view_label is the entity name
            - group_label is the category name
        """
        if self.config and self.config.meta and self.config.meta.hierarchy:
            hierarchy = self.config.meta.hierarchy
            # Format entity and category with proper capitalization
            view_label = hierarchy.entity.replace('_', ' ').title() if hierarchy.entity else None
            group_label = hierarchy.category.replace('_', ' ').title() if hierarchy.category else None
            return view_label, group_label
        return None, None

    def _to_dimension_dict(self) -> dict[str, Any]:
        """Convert categorical dimension to LookML dimension."""
        result: dict[str, Any] = {
            'name': self.name,
            'type': 'string',  # Most categorical dims are strings
            'sql': self.expr or f"${{TABLE}}.{self.name}",
        }

        if self.description:
            result['description'] = self.description
        if self.label:
            result['label'] = self.label

        # Add hierarchy labels
        view_label, group_label = self.get_dimension_labels()
        if view_label:
            result['view_label'] = view_label
        if group_label:
            result['group_label'] = group_label

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
            'sql': self.expr or f"${{TABLE}}.{self.name}",
        }

        if self.description:
            result['description'] = self.description
        if self.label:
            result['label'] = self.label

        # Add hierarchy labels
        view_label, group_label = self.get_dimension_labels()
        if view_label:
            result['view_label'] = view_label
        if group_label:
            result['group_label'] = group_label

        return result


class Measure(BaseModel):
    """Represents a measure in a semantic model."""

    name: str
    agg: AggregationType
    expr: Optional[str] = None
    description: Optional[str] = None
    label: Optional[str] = None
    create_metric: Optional[bool] = None
    config: Optional[Config] = None
    non_additive_dimension: Optional[dict[str, Any]] = None  # For backward compatibility

    def get_measure_labels(self) -> tuple[Optional[str], Optional[str]]:
        """Get view_label and group_label for measure based on hierarchy.

        Returns:
            Tuple of (view_label, group_label) where:
            - view_label is the category name
            - group_label is the subcategory name
        """
        if self.config and self.config.meta and self.config.meta.hierarchy:
            hierarchy = self.config.meta.hierarchy
            # Format category and subcategory with proper capitalization
            view_label = hierarchy.category.replace('_', ' ').title() if hierarchy.category else None
            group_label = hierarchy.subcategory.replace('_', ' ').title() if hierarchy.subcategory else None
            return view_label, group_label
        return None, None

    def to_lookml_dict(self) -> dict[str, Any]:
        """Convert measure to LookML format."""
        result: dict[str, Any] = {
            'name': self.name,
            'type': LOOKML_TYPE_MAP.get(self.agg, 'number'),
            'sql': self.expr or f"${{TABLE}}.{self.name}",
        }

        if self.description:
            result['description'] = self.description
        if self.label:
            result['label'] = self.label

        # Add hierarchy labels
        view_label, group_label = self.get_measure_labels()
        if view_label:
            result['view_label'] = view_label
        if group_label:
            result['group_label'] = group_label

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

    def to_lookml_dict(self, schema: str = "") -> dict[str, Any]:
        """Convert entire semantic model to lkml views format.

        Args:
            schema: Optional database schema name to prepend to table name.

        Returns:
            Dictionary in LookML views format.
        """
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
            'sql_table_name': self._extract_table_name(schema),
        }

        if dimensions:
            view_dict['dimensions'] = dimensions

        if dimension_groups:
            view_dict['dimension_groups'] = dimension_groups

        if measures:
            view_dict['measures'] = measures

        return {'views': [view_dict]}

    def _extract_table_name(self, schema: str = "") -> str:
        """Extract table name from dbt ref() syntax.

        Args:
            schema: Optional database schema name to prepend.

        Returns:
            Fully qualified table name (schema.table or just table).
        """
        # Handle ref('table_name') syntax
        match = re.search(r"ref\(['\"]([^'\"]+)['\"]\)", self.model)
        table_name = match.group(1) if match else self.model

        # Prepend schema if provided
        if schema:
            return f"{schema}.{table_name}"
        return table_name


# ============================================================================
# LookML Schemas (Output)
# ============================================================================

class LookMLDimension(BaseModel):
    """Represents a LookML dimension."""

    name: str
    type: str
    sql: str
    description: Optional[str] = None
    label: Optional[str] = None
    hidden: Optional[bool] = None
    primary_key: Optional[bool] = None
    view_label: Optional[str] = None
    group_label: Optional[str] = None


class LookMLDimensionGroup(BaseModel):
    """Represents a LookML dimension_group for time dimensions."""

    name: str
    type: str = "time"
    timeframes: list[str] = Field(default_factory=lambda: ["date", "week", "month", "quarter", "year"])
    sql: str
    description: Optional[str] = None
    label: Optional[str] = None
    hidden: Optional[bool] = None
    view_label: Optional[str] = None
    group_label: Optional[str] = None


class LookMLMeasure(BaseModel):
    """Represents a LookML measure."""

    name: str
    type: str
    sql: str
    description: Optional[str] = None
    label: Optional[str] = None
    hidden: Optional[bool] = None
    view_label: Optional[str] = None
    group_label: Optional[str] = None


class LookMLView(BaseModel):
    """Represents a LookML view."""

    name: str
    sql_table_name: str
    description: Optional[str] = None
    dimensions: list[LookMLDimension] = Field(default_factory=list)
    dimension_groups: list[LookMLDimensionGroup] = Field(default_factory=list)
    measures: list[LookMLMeasure] = Field(default_factory=list)

    def to_lookml_dict(self) -> dict[str, Any]:
        """Convert LookML view to dictionary format."""
        def convert_bools(d: dict) -> dict:
            """Convert boolean values to LookML-compatible strings."""
            result = {}
            for k, v in d.items():
                if isinstance(v, bool):
                    result[k] = "yes" if v else "no"
                elif isinstance(v, dict):
                    result[k] = convert_bools(v)
                elif isinstance(v, list):
                    result[k] = [convert_bools(item) if isinstance(item, dict) else item for item in v]
                else:
                    result[k] = v
            return result

        view_dict: dict[str, Any] = {
            'name': self.name,
            'sql_table_name': self.sql_table_name,
        }

        if self.description:
            view_dict['description'] = self.description

        if self.dimensions:
            view_dict['dimensions'] = [
                convert_bools(dim.model_dump(exclude_none=True)) for dim in self.dimensions
            ]

        if self.dimension_groups:
            view_dict['dimension_groups'] = [
                convert_bools(dg.model_dump(exclude_none=True)) for dg in self.dimension_groups
            ]

        if self.measures:
            view_dict['measures'] = [
                convert_bools(measure.model_dump(exclude_none=True)) for measure in self.measures
            ]

        return {'views': [view_dict]}


class LookMLExplore(BaseModel):
    """Represents a LookML explore."""

    name: str
    view_name: str
    type: Optional[str] = "table"  # Default type
    description: Optional[str] = None
    hidden: Optional[bool] = None
    joins: list[dict[str, Any]] = Field(default_factory=list)  # For backward compatibility