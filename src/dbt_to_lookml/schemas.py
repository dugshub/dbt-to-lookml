"""Schema definitions for dbt semantic models and LookML structures."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from dbt_to_lookml.types import LOOKML_TYPE_MAP, AggregationType, DimensionType

# ============================================================================
# Semantic Model Schemas (Input)
# ============================================================================


class Hierarchy(BaseModel):
    """Represents the 3-tier hierarchy for labeling."""

    entity: str | None = None
    category: str | None = None
    subcategory: str | None = None


class ConfigMeta(BaseModel):
    """Represents metadata in a config section."""

    domain: str | None = None
    owner: str | None = None
    contains_pii: bool | None = None
    update_frequency: str | None = None
    # Support both flat structure (subject, category) and nested (hierarchy)
    subject: str | None = None
    category: str | None = None
    hierarchy: Hierarchy | None = None


class Config(BaseModel):
    """Represents a config section in a semantic model."""

    meta: ConfigMeta | None = None


class Entity(BaseModel):
    """Represents an entity in a semantic model."""

    name: str
    type: str
    expr: str | None = None
    description: str | None = None

    def _qualify_sql_expression(self, expr: str | None, field_name: str) -> str:
        """Ensure SQL expressions use ${TABLE} to avoid ambiguous column references.

        This prevents ambiguous column errors in joins by ensuring all column references
        are qualified with ${TABLE}.

        Args:
            expr: Custom SQL expression or None
            field_name: Name of the field (used as default)

        Returns:
            Qualified SQL expression
        """
        if expr is None:
            # Default case: use ${TABLE}.field_name
            return f"${{TABLE}}.{field_name}"

        # Check if expression already contains table qualifiers
        if "${TABLE}" in expr or "${" in expr:
            # Already contains LookML references, use as-is
            return expr

        # Check if it's a simple column reference (alphanumeric + underscore only)
        # This handles cases like "id" or "facility_sk"
        if expr.replace("_", "").replace(" ", "").isalnum() and " " not in expr.strip():
            # Simple column name - qualify it with ${TABLE}
            return f"${{TABLE}}.{expr}"

        # Complex expression (functions, operators, etc.)
        # Use as-is but user should ensure proper qualification
        return expr

    def to_lookml_dict(
        self, view_label: str | None = None, is_fact_table: bool = False
    ) -> dict[str, Any]:
        """Convert entity to LookML dimension format.

        Args:
            view_label: Optional view_label for the entity (from model subject).
            is_fact_table: Whether this entity is in a fact table (has measures).
        """
        result: dict[str, Any] = {
            "name": self.name,
            "type": "string",
            "sql": self._qualify_sql_expression(self.expr, self.name),
        }

        if self.type == "primary":
            result["primary_key"] = "yes"

            # Add view_label and group_label for primary entities in fact tables
            if is_fact_table:
                if view_label:
                    result["view_label"] = view_label
                result["group_label"] = "Join Keys"

        # Hide all entities (typically surrogate keys) - natural keys should be defined as dimensions
        result['hidden'] = 'yes'

        if self.description:
            result["description"] = self.description

        return result


class Dimension(BaseModel):
    """Represents a dimension in a semantic model."""

    name: str
    type: DimensionType
    expr: str | None = None
    description: str | None = None
    label: str | None = None
    type_params: dict[str, Any] | None = None
    config: Config | None = None

    def to_lookml_dict(self) -> dict[str, Any]:
        """Convert dimension to LookML format."""
        if self.type == DimensionType.TIME:
            return self._to_dimension_group_dict()
        else:
            return self._to_dimension_dict()

    def get_dimension_labels(self) -> tuple[str | None, str | None]:
        """Get view_label and group_label for dimension based on meta.

        Returns:
            Tuple of (view_label, group_label) where:
            - view_label comes from meta.subject (or meta.hierarchy.entity as fallback)
            - group_label comes from meta.category (or meta.hierarchy.category as fallback)
        """
        if self.config and self.config.meta:
            meta = self.config.meta

            # Try flat structure first (meta.subject, meta.category)
            view_label = meta.subject
            group_label = meta.category

            # Fall back to hierarchical structure if flat structure not present
            if not view_label and meta.hierarchy:
                view_label = meta.hierarchy.entity
            if not group_label and meta.hierarchy:
                group_label = meta.hierarchy.category

            # Format with proper capitalization if present
            if view_label:
                view_label = view_label.replace("_", " ").title()
            if group_label:
                group_label = group_label.replace("_", " ").title()

            return view_label, group_label
        return None, None

    def _to_dimension_dict(self) -> dict[str, Any]:
        """Convert categorical dimension to LookML dimension."""
        result: dict[str, Any] = {
            "name": self.name,
            "type": "string",  # Most categorical dims are strings
            "sql": self.expr or f"${{TABLE}}.{self.name}",
        }

        if self.description:
            result["description"] = self.description
        if self.label:
            result["label"] = self.label

        # Add hierarchy labels
        view_label, group_label = self.get_dimension_labels()
        if view_label:
            result["view_label"] = view_label
        if group_label:
            result["group_label"] = group_label

        return result

    def _to_dimension_group_dict(self) -> dict[str, Any]:
        """Convert time dimension to LookML dimension_group."""
        # Determine timeframes based on granularity
        timeframes = ["date", "week", "month", "quarter", "year"]

        if self.type_params and "time_granularity" in self.type_params:
            granularity = self.type_params["time_granularity"]
            if granularity in ["hour", "minute"]:
                timeframes = [
                    "time",
                    "hour",
                    "date",
                    "week",
                    "month",
                    "quarter",
                    "year",
                ]

        result: dict[str, Any] = {
            "name": self.name,
            "type": "time",
            "timeframes": timeframes,
            "sql": self.expr or f"${{TABLE}}.{self.name}",
        }

        if self.description:
            result["description"] = self.description
        if self.label:
            result["label"] = self.label

        # Add hierarchy labels
        view_label, group_label = self.get_dimension_labels()
        if view_label:
            result["view_label"] = view_label
        if group_label:
            result["group_label"] = group_label

        return result


class Measure(BaseModel):
    """Represents a measure in a semantic model."""

    name: str
    agg: AggregationType
    expr: str | None = None
    description: str | None = None
    label: str | None = None
    create_metric: bool | None = None
    config: Config | None = None
    non_additive_dimension: dict[str, Any] | None = None  # For backward compatibility

    def get_measure_labels(
        self, model_name: str | None = None
    ) -> tuple[str, str | None]:
        """Get view_label and group_label for measure.

        Returns:
            Tuple of (view_label, group_label) where:
            - view_label is always " Metrics" (with leading space for sort order)
            - group_label is inferred from model name or meta.category
        """
        # Always use " Metrics" as view_label (leading space for sort order)
        view_label = " Metrics"

        # Try to get group_label from meta first
        group_label = None
        if self.config and self.config.meta:
            meta = self.config.meta
            # Try flat structure first
            if meta.category:
                group_label = meta.category.replace("_", " ").title()
            # Fall back to hierarchical structure
            elif meta.hierarchy and meta.hierarchy.category:
                group_label = meta.hierarchy.category.replace("_", " ").title()

        # If no group_label from meta, infer from model name
        if not group_label and model_name:
            # Convert model name to title case and add "Performance"
            formatted_name = model_name.replace("_", " ").title()
            group_label = f"{formatted_name} Performance"

        return view_label, group_label

    def to_lookml_dict(self, model_name: str | None = None) -> dict[str, Any]:
        """Convert measure to LookML format.

        Args:
            model_name: Optional semantic model name for inferring group_label.
        """
        result: dict[str, Any] = {
            "name": self.name,
            "type": LOOKML_TYPE_MAP.get(self.agg, "number"),
            "sql": self.expr or f"${{TABLE}}.{self.name}",
        }

        if self.description:
            result["description"] = self.description
        if self.label:
            result["label"] = self.label

        # Add measure labels
        view_label, group_label = self.get_measure_labels(model_name)
        result["view_label"] = view_label
        if group_label:
            result["group_label"] = group_label

        return result


class SemanticModel(BaseModel):
    """Represents a complete semantic model."""

    name: str
    model: str
    description: str | None = None
    config: Config | None = None
    defaults: dict[str, Any] | None = None
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

        # Determine if this is a fact table (has measures)
        is_fact_table = len(self.measures) > 0

        # Extract view_label for entities from config.meta.subject
        entity_view_label = None
        if self.config and self.config.meta and self.config.meta.subject:
            entity_view_label = self.config.meta.subject.replace("_", " ").title()
        # If not in model config, try to get from first dimension's subject
        elif self.dimensions:
            for dim in self.dimensions:
                if dim.config and dim.config.meta and dim.config.meta.subject:
                    entity_view_label = dim.config.meta.subject.replace(
                        "_", " "
                    ).title()
                    break
        # Fall back to model name if no subject found
        if not entity_view_label:
            entity_view_label = self.name.replace("_", " ").title()

        # Convert entities to dimensions
        for entity in self.entities:
            dimensions.append(
                entity.to_lookml_dict(
                    view_label=entity_view_label, is_fact_table=is_fact_table
                )
            )

        # Convert dimensions (separate regular dims from time dims)
        for dim in self.dimensions:
            dim_dict = dim.to_lookml_dict()
            if dim.type == DimensionType.TIME:
                dimension_groups.append(dim_dict)
            else:
                dimensions.append(dim_dict)

        # Convert measures (pass model name for group_label inference)
        measures = [
            measure.to_lookml_dict(model_name=self.name) for measure in self.measures
        ]

        # Collect all dimension field names for the dimensions_only set
        dimension_field_names: list[str] = []
        for entity in self.entities:
            dimension_field_names.append(entity.name)
        for dim in self.dimensions:
            # Time dimensions become dimension_groups with multiple timeframe fields
            # We must explicitly list each timeframe field in the set
            if dim.type == DimensionType.TIME:
                # Determine timeframes (same logic as to_dimension_group_dict)
                timeframes = ["date", "week", "month", "quarter", "year"]
                if dim.type_params and dim.type_params.get("time_granularity") in ["hour", "minute"]:
                    timeframes = ["time", "hour", "date", "week", "month", "quarter", "year"]

                # Add each expanded timeframe field
                for timeframe in timeframes:
                    dimension_field_names.append(f"{dim.name}_{timeframe}")
            else:
                dimension_field_names.append(dim.name)

        # Build the view dict
        view_dict: dict[str, Any] = {
            "name": self.name,
            "sql_table_name": self._extract_table_name(schema),
        }

        if dimensions:
            view_dict["dimensions"] = dimensions

        if dimension_groups:
            view_dict["dimension_groups"] = dimension_groups

        if measures:
            view_dict["measures"] = measures

        # Add dimensions_only set if we have any dimensions
        if dimension_field_names:
            view_dict["sets"] = [
                {"name": "dimensions_only", "fields": dimension_field_names}
            ]

        return {"views": [view_dict]}

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
