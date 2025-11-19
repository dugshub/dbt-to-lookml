"""dbt Semantic Layer schemas for semantic models and metrics.

This module contains all input schema definitions from dbt's semantic layer
specification, including semantic models (entities, dimensions, measures) and
metrics (simple, ratio, derived, conversion).

The semantic layer is dbt's framework for defining business logic and metrics
on top of data models, providing a consistent interface for analytics and
reporting tools.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from dbt_to_lookml.schemas.config import Config
from dbt_to_lookml.types import LOOKML_TYPE_MAP, AggregationType, DimensionType

__all__ = [
    # Semantic Model schemas
    "Entity",
    "Dimension",
    "Measure",
    "SemanticModel",
    # Metric schemas
    "MetricReference",
    "SimpleMetricParams",
    "RatioMetricParams",
    "DerivedMetricParams",
    "ConversionMetricParams",
    "Metric",
]


# ============================================================================
# Semantic Model Schemas
# ============================================================================


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

        # Hide all entities (typically surrogate keys)
        # Natural keys should be defined as dimensions
        result["hidden"] = "yes"

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

    def to_lookml_dict(self, default_convert_tz: bool | None = None) -> dict[str, Any]:
        """Convert dimension to LookML format.

        Args:
            default_convert_tz: Optional default timezone conversion setting
                for time dimensions.
        """
        if self.type == DimensionType.TIME:
            return self._to_dimension_group_dict(default_convert_tz=default_convert_tz)
        else:
            return self._to_dimension_dict()

    def get_dimension_labels(self) -> tuple[str | None, str | None]:
        """Get view_label and group_label for dimension based on meta.

        Returns:
            Tuple of (view_label, group_label) where:
            - view_label comes from meta.subject (or meta.hierarchy.entity as fallback)
            - group_label comes from meta.category (or
              meta.hierarchy.category as fallback)
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

    def _get_timeframes(self) -> list[str]:
        """Get the list of timeframes for this time dimension.

        Returns:
            List of timeframe strings
            (e.g., ['date', 'week', 'month', 'quarter', 'year'])
        """
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
        return timeframes

    def _to_dimension_group_dict(
        self, default_convert_tz: bool | None = None
    ) -> dict[str, Any]:
        """Convert time dimension to LookML dimension_group.

        Generates a LookML dimension_group block with appropriate timeframes
        based on the dimension's time_granularity setting. Supports timezone
        conversion configuration through multi-level precedence:

        1. Dimension-level override via config.meta.convert_tz (highest priority)
        2. Generator default via default_convert_tz parameter
        3. Hardcoded default of False (lowest priority)

        Args:
            default_convert_tz: Default timezone conversion setting from
                generator or CLI.
                - True: Enable timezone conversion for all dimensions
                  (unless overridden)
                - False: Disable timezone conversion (default behavior)
                - None: Use generator default (False)

        Returns:
            Dictionary with dimension_group configuration including:
            - name: Dimension name
            - type: "time"
            - timeframes: List of appropriate timeframes based on granularity
            - sql: SQL expression for the timestamp column
            - convert_tz: "yes" or "no" based on precedence rules
            - description: Optional description
            - label: Optional label
            - view_label/group_label: Optional hierarchy labels

        Example:
            Dimension with metadata override (enables timezone conversion):

            ```python
            dimension = Dimension(
                name="created_at",
                type=DimensionType.TIME,
                type_params={"time_granularity": "day"},
                config=Config(meta=ConfigMeta(
                    convert_tz=True  # Override any generator default
                ))
            )
            result = dimension._to_dimension_group_dict(default_convert_tz=False)
            # Result includes: "convert_tz": "yes" (meta override takes precedence)
            ```

            Dimension without override (uses generator default):

            ```python
            dimension = Dimension(
                name="shipped_at",
                type=DimensionType.TIME,
                type_params={"time_granularity": "hour"}
            )
            result = dimension._to_dimension_group_dict(default_convert_tz=True)
            # Result includes: "convert_tz": "yes" (from default_convert_tz parameter)
            ```

        See Also:
            CLAUDE.md: "Timezone Conversion Configuration" section for detailed
                precedence rules and usage examples.
        """
        # Determine timeframes based on granularity
        timeframes = self._get_timeframes()

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

        # Determine convert_tz with three-tier precedence:
        # 1. Dimension-level meta.convert_tz (highest priority if present)
        # 2. default_convert_tz parameter (if provided)
        # 3. Hardcoded default: False (lowest priority, explicit and safe)
        convert_tz = False  # Default
        if default_convert_tz is not None:
            convert_tz = default_convert_tz
        if self.config and self.config.meta and self.config.meta.convert_tz is not None:
            convert_tz = self.config.meta.convert_tz

        result["convert_tz"] = "yes" if convert_tz else "no"

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
    ) -> tuple[str | None, str | None]:
        """Get view_label and group_label for measure.

        Labeling rules:
        1. Hierarchy: category → view_label, subcategory → group_label
        2. Flat category: " Metrics" → view_label, category → group_label
        3. Model name fallback: " Metrics" → view_label, model_name-based → group_label
        4. No config and no model_name: no labels

        Returns:
            Tuple of (view_label, group_label) where:
            - view_label is from hierarchy.category, or " Metrics" if using
              flat/model fallback
            - group_label is from hierarchy.subcategory, flat category, or
              model name
        """
        view_label = None
        group_label = None

        if self.config and self.config.meta:
            meta = self.config.meta
            # Check hierarchical structure first
            if meta.hierarchy:
                # category → view_label
                if meta.hierarchy.category:
                    view_label = meta.hierarchy.category.replace("_", " ").title()
                # subcategory → group_label
                if meta.hierarchy.subcategory:
                    group_label = meta.hierarchy.subcategory.replace("_", " ").title()
            # Fall back to flat structure for backward compatibility
            elif meta.category:
                # For flat structure: " Metrics" → view_label, category → group_label
                view_label = " Metrics"
                group_label = meta.category.replace("_", " ").title()

        # If no labels from meta and model_name provided, use model_name fallback
        if not view_label and not group_label and model_name:
            # Convert model name to title case and add "Performance"
            formatted_name = model_name.replace("_", " ").title()
            group_label = f"{formatted_name} Performance"
            view_label = " Metrics"  # Default with leading space for sort order

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
        if view_label:
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

    def to_lookml_dict(
        self, schema: str = "", convert_tz: bool | None = None
    ) -> dict[str, Any]:
        """Convert entire semantic model to lkml views format.

        Args:
            schema: Optional database schema name to prepend to table name.
            convert_tz: Optional timezone conversion setting. Passed to time
                dimensions as default_convert_tz. None means use
                dimension-level defaults.

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
            # Pass convert_tz to time dimensions to propagate generator default
            if dim.type == DimensionType.TIME:
                dim_dict = dim.to_lookml_dict(default_convert_tz=convert_tz)
            else:
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
            # For time dimensions, add each individual timeframe field
            # (e.g., created_at_date, created_at_week, created_at_month)
            # For regular dimensions, use the base name
            if dim.type == DimensionType.TIME:
                timeframes = dim._get_timeframes()
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
# Metric Schemas
# ============================================================================


class MetricReference(BaseModel):
    """Reference to another metric in derived metric expressions.

    Used in derived metrics to reference other metrics with optional
    aliases and offset windows for time-based calculations.

    Attributes:
        name: Name of the referenced metric.
        alias: Optional alias for the metric in the expression.
        offset_window: Optional time window offset (e.g., "1 month", "7 days").

    Example:
        ```yaml
        metrics:
          - name: revenue_growth
            type: derived
            type_params:
              expr: "revenue - revenue_last_month"
              metrics:
                - name: revenue
                - name: revenue
                  alias: revenue_last_month
                  offset_window: "1 month"
        ```
    """

    name: str
    alias: str | None = None
    offset_window: str | None = None


class SimpleMetricParams(BaseModel):
    """Type parameters for simple metrics.

    Simple metrics reference a single measure from a semantic model.

    Attributes:
        measure: Name of the measure to use (e.g., "revenue", "order_count").

    Example:
        ```yaml
        metrics:
          - name: total_revenue
            type: simple
            type_params:
              measure: revenue
        ```
    """

    measure: str


class RatioMetricParams(BaseModel):
    """Type parameters for ratio metrics.

    Ratio metrics calculate numerator / denominator, typically for rates,
    percentages, or per-unit calculations.

    Attributes:
        numerator: Name of the measure to use as numerator.
        denominator: Name of the measure to use as denominator.

    Example:
        ```yaml
        metrics:
          - name: conversion_rate
            type: ratio
            type_params:
              numerator: completed_orders
              denominator: total_searches
        ```
    """

    numerator: str
    denominator: str


class DerivedMetricParams(BaseModel):
    """Type parameters for derived metrics.

    Derived metrics combine other metrics using a SQL expression.

    Attributes:
        expr: SQL expression combining referenced metrics.
        metrics: List of metric references used in the expression.

    Example:
        ```yaml
        metrics:
          - name: revenue_growth
            type: derived
            type_params:
              expr: "(current_revenue - prior_revenue) / prior_revenue"
              metrics:
                - name: monthly_revenue
                  alias: current_revenue
                - name: monthly_revenue
                  alias: prior_revenue
                  offset_window: "1 month"
        ```
    """

    expr: str
    metrics: list[MetricReference]


class ConversionMetricParams(BaseModel):
    """Type parameters for conversion metrics.

    Conversion metrics track funnel conversions between entity states.
    The structure is flexible to support various conversion patterns.

    Attributes:
        conversion_type_params: Dictionary containing conversion-specific
            configuration. Structure depends on conversion type.

    Example:
        ```yaml
        metrics:
          - name: checkout_conversion
            type: conversion
            type_params:
              conversion_type_params:
                entity: order
                calculation: conversion_rate
                base_event: page_view
                conversion_event: purchase
        ```
    """

    conversion_type_params: dict[str, Any]


class Metric(BaseModel):
    """Represents a dbt metric definition.

    Metrics define calculations that can be simple aggregations, ratios,
    derived calculations, or conversion funnels. They can reference measures
    from one or more semantic models and are owned by a primary entity.

    Attributes:
        name: Unique metric identifier (snake_case).
        type: Type of metric calculation.
        type_params: Type-specific parameters (validated based on type).
        label: Optional human-readable label for the metric.
        description: Optional detailed description of what the metric represents.
        meta: Optional metadata dictionary for custom configuration.
            Common fields:
            - primary_entity: Entity that owns this metric (determines which
              view file contains the generated measure).
            - category: Category for grouping related metrics.

    Examples:
        Simple metric:
        ```yaml
        metrics:
          - name: total_revenue
            type: simple
            type_params:
              measure: revenue
            label: Total Revenue
            description: Sum of all revenue
            meta:
              primary_entity: order
              category: financial_performance
        ```

        Ratio metric (cross-entity):
        ```yaml
        metrics:
          - name: search_conversion_rate
            type: ratio
            type_params:
              numerator: rental_count    # From rental_orders
              denominator: search_count  # From searches
            label: Search Conversion Rate
            description: Percentage of searches that result in rentals
            meta:
              primary_entity: search  # Searches is the spine/denominator
              category: conversion_metrics
        ```

        Derived metric:
        ```yaml
        metrics:
          - name: revenue_growth
            type: derived
            type_params:
              expr: "(current - prior) / prior"
              metrics:
                - name: monthly_revenue
                  alias: current
                - name: monthly_revenue
                  alias: prior
                  offset_window: "1 month"
            meta:
              primary_entity: order
        ```

    See Also:
        - Epic DTL-022 for primary entity ownership pattern
        - MetricReference for derived metric dependencies
    """

    name: str
    type: Literal["simple", "ratio", "derived", "conversion"]
    type_params: (
        SimpleMetricParams
        | RatioMetricParams
        | DerivedMetricParams
        | ConversionMetricParams
    )
    label: str | None = None
    description: str | None = None
    meta: dict[str, Any] | None = None

    @property
    def primary_entity(self) -> str | None:
        """Extract primary_entity from meta block.

        The primary entity determines which semantic model/view owns this
        metric and serves as the base for the calculation.

        Returns:
            Primary entity name if specified in meta, None otherwise.

        Example:
            ```python
            metric = Metric(
                name="conversion_rate",
                type="ratio",
                type_params=RatioMetricParams(
                    numerator="orders",
                    denominator="searches"
                ),
                meta={"primary_entity": "search"}
            )
            assert metric.primary_entity == "search"
            ```
        """
        if self.meta:
            return self.meta.get("primary_entity")
        return None
