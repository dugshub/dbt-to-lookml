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


def _smart_title(text: str) -> str:
    """Convert text to title case while preserving common acronyms.

    Replaces underscores with spaces and title-cases each word, but preserves
    common acronyms like UTC, API, ID, URL, etc. in uppercase.

    Args:
        text: Input text with underscores (e.g., "rental_end_utc")

    Returns:
        Title-cased text with preserved acronyms (e.g., "Rental End UTC")

    Examples:
        >>> _smart_title("rental_end_utc")
        "Rental End UTC"
        >>> _smart_title("api_key_id")
        "API Key ID"
        >>> _smart_title("user_name")
        "User Name"
    """
    # List of acronyms to preserve in uppercase
    acronyms = {
        "UTC",
        "API",
        "ID",
        "URL",
        "HTTP",
        "HTTPS",
        "SQL",
        "JSON",
        "XML",
        "CSV",
        "HTML",
        "PDF",
        "UUID",
        "URI",
        "ISO",
    }

    # Preserve leading whitespace for sort order control
    leading_spaces = len(text) - len(text.lstrip())
    prefix = text[:leading_spaces]

    # Replace underscores and title case
    words = text.replace("_", " ").title().split()

    # Preserve acronyms
    result_words = []
    for word in words:
        if word.upper() in acronyms:
            result_words.append(word.upper())
        else:
            result_words.append(word)

    return prefix + " ".join(result_words)


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

    def to_lookml_dict(
        self,
        default_convert_tz: bool | None = None,
        default_time_dimension_group_label: str | None = None,
        default_use_group_item_label: bool | None = None,
    ) -> dict[str, Any]:
        """Convert dimension to LookML format.

        Converts semantic model dimension to LookML dictionary representation,
        handling both categorical dimensions and time dimension_groups with
        appropriate configuration.

        Args:
            default_convert_tz: Optional default timezone conversion setting
                from generator. Only applies to time dimensions. Overridden by
                dimension-level config.meta.convert_tz if present.
            default_time_dimension_group_label: Optional default group label
                for time dimension_groups.
            default_use_group_item_label: Optional default group_item_label
                setting from generator. Only applies to time dimensions. When
                True, generates Liquid template for clean timeframe labels.
                Overridden by dimension-level config.meta.use_group_item_label.

        Returns:
            Dictionary with dimension or dimension_group configuration for
            LookML generation.

        Example:
            Time dimension with group_item_label enabled:

            ```python
            dimension = Dimension(
                name="created_at",
                type=DimensionType.TIME,
                type_params={"time_granularity": "day"}
            )
            result = dimension.to_lookml_dict(
                default_use_group_item_label=True
            )
            # Returns dimension_group dict with group_item_label Liquid template
            ```
        """
        if self.type == DimensionType.TIME:
            return self._to_dimension_group_dict(
                default_convert_tz=default_convert_tz,
                default_time_dimension_group_label=default_time_dimension_group_label,
                default_use_group_item_label=default_use_group_item_label,
            )
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
                view_label = _smart_title(view_label)
            if group_label:
                group_label = _smart_title(group_label)

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

        # Add hidden parameter if specified
        if self.config and self.config.meta and self.config.meta.hidden is True:
            result["hidden"] = "yes"

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
        self,
        default_convert_tz: bool | None = None,
        default_time_dimension_group_label: str | None = None,
        default_use_group_item_label: bool | None = None,
    ) -> dict[str, Any]:
        """Convert time dimension to LookML dimension_group.

        Generates a LookML dimension_group block with appropriate timeframes
        based on the dimension's time_granularity setting. Supports timezone
        conversion, group labeling, and group_item_label through multi-level
        precedence.

        Args:
            default_convert_tz: Default timezone conversion setting from
                generator or CLI.
                - True: Enable timezone conversion for all dimensions
                  (unless overridden)
                - False: Disable timezone conversion (default behavior)
                - None: Use generator default (False)

            default_time_dimension_group_label: Default group label for time
                dimensions. Controls the group_label parameter in generated
                dimension_groups through multi-level precedence:

                1. Dimension-level override via
                   config.meta.time_dimension_group_label (highest priority)
                2. Generator default via default_time_dimension_group_label
                   parameter
                3. Hardcoded default of "Time Dimensions" (lowest priority)

                Values:
                - String value: Use as group_label for time dimension
                  organization
                - None: Use next level in precedence chain (or hardcoded
                  default)
                - Empty string (""): Explicitly disable group_label
                  (backward compatible)

                Note: Hierarchy-based group_label (from category/subcategory)
                takes precedence over time_dimension_group_label for
                organizational specificity.

            default_use_group_item_label: Default group_item_label setting from
                generator or CLI.
                - True: Generate group_item_label with Liquid template
                - False: No group_item_label parameter (default, backward compatible)
                - None: Use generator default (False)

        Returns:
            Dictionary with dimension_group configuration including:
            - name: Dimension name
            - type: "time"
            - timeframes: List of appropriate timeframes based on granularity
            - sql: SQL expression for the timestamp column
            - convert_tz: "yes" or "no" based on precedence rules
            - group_item_label: Liquid template (if enabled)
            - group_label: Time dimension group label (if configured)
            - description: Optional description
            - label: Optional label
            - view_label: Optional hierarchy view label (if no group label
              override)

        Example:
            Dimension with metadata override (enables group_item_label):

            ```python
            dimension = Dimension(
                name="rental_date",
                type=DimensionType.TIME,
                type_params={"time_granularity": "day"},
                config=Config(meta=ConfigMeta(
                    use_group_item_label=True  # Override any generator default
                ))
            )
            result = dimension._to_dimension_group_dict(
                default_use_group_item_label=False
            )
            # Result includes group_item_label with Liquid template
            ```

            Dimension without override (uses generator default):

            ```python
            dimension = Dimension(
                name="booking_timestamp",
                type=DimensionType.TIME,
                type_params={"time_granularity": "hour"}
            )
            result = dimension._to_dimension_group_dict(
                default_use_group_item_label=True
            )
            # Result includes group_item_label (from default parameter)
            ```

        See Also:
            CLAUDE.md: "Field Label Customization (group_item_label)" section
                for detailed precedence rules and usage examples.
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

        # Determine time_dimension_group_label with three-tier precedence:
        # 1. Dimension-level meta.time_dimension_group_label (highest priority)
        # 2. default_time_dimension_group_label parameter (from generator/CLI)
        # 3. Hardcoded default: " Time Dimensions" (lowest priority)
        #
        # IMPORTANT: time_dimension_group_label OVERRIDES hierarchy group_label
        # for time dimensions. This ensures consistent organization of all time
        # dimensions under a common grouping, even when hierarchy metadata exists
        # (which may be used for other semantic layer purposes).
        # Empty string explicitly disables group_label (backward compatible).
        # None means "use next level in precedence chain".
        # Leading space in default ensures time dimensions sort to top of field picker.
        # Default time dimension group label (space prefix added when applied)
        time_group_label = "Date Dimensions - Local Time"
        if default_time_dimension_group_label is not None:
            time_group_label = default_time_dimension_group_label
        if (
            self.config
            and self.config.meta
            and self.config.meta.time_dimension_group_label is not None
        ):
            time_group_label = self.config.meta.time_dimension_group_label

        # Apply time dimension group_label if not explicitly disabled
        # and no hierarchy group_label exists (hierarchy takes precedence)
        # Prefix with 1 space for sort order (after Metrics with 2 spaces)
        if time_group_label and "group_label" not in result:
            result["group_label"] = f" {time_group_label.lstrip()}"  # 1 space prefix

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

        # Determine use_group_item_label with three-tier precedence:
        # 1. Dimension-level meta.use_group_item_label (highest priority if present)
        # 2. default_use_group_item_label parameter (if provided)
        # 3. Hardcoded default: False (lowest priority, backward compatible)
        use_group_item_label = False  # Default
        if default_use_group_item_label is not None:
            use_group_item_label = default_use_group_item_label
        if (
            self.config
            and self.config.meta
            and self.config.meta.use_group_item_label is not None
        ):
            use_group_item_label = self.config.meta.use_group_item_label

        # Generate Liquid template for group_item_label if enabled
        if use_group_item_label:
            # Template extracts timeframe from last underscore-separated segment
            # Works universally regardless of dimension name complexity
            # Example: gold_rental_segmentation_month → "Month"
            result["group_item_label"] = (
                "{% assign parts = _field._name | split: '_' %}"
                "{% assign tf = parts | last %}"
                "{{ tf | capitalize }}"
            )

        # Add hidden parameter if specified
        if self.config and self.config.meta and self.config.meta.hidden is True:
            result["hidden"] = "yes"

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
                    view_label = _smart_title(meta.hierarchy.category)
                # subcategory → group_label
                if meta.hierarchy.subcategory:
                    group_label = _smart_title(meta.hierarchy.subcategory)
            # Fall back to flat structure for backward compatibility
            elif meta.category:
                # For flat structure: "Metrics" → view_label, category → group_label
                view_label = "Metrics"  # Space prefix added when applied
                group_label = _smart_title(meta.category)

        # If no labels from meta and model_name provided, use model_name fallback
        if not view_label and not group_label and model_name:
            # Convert model name to title case and add "Performance"
            formatted_name = _smart_title(model_name)
            group_label = f"{formatted_name} Performance"
            view_label = "Metrics"  # Space prefix added when applied

        return view_label, group_label

    def to_lookml_dict(self, model_name: str | None = None) -> dict[str, Any]:
        """Convert measure to LookML format with universal suffix and hiding.

        All measures are generated with:
        - Name suffix: '_measure' appended to distinguish from metrics
        - Hidden property: 'yes' to hide from end users (building blocks for metrics)

        Args:
            model_name: Optional semantic model name for inferring group_label.

        Returns:
            Dictionary with LookML measure configuration including:
            - name: Measure name with '_measure' suffix
            - type: LookML aggregation type
            - sql: SQL expression for the measure
            - hidden: Always 'yes'
            - Optional: description, label, view_label, group_label

        Example:
            ```python
            measure = Measure(name="revenue", agg=AggregationType.SUM)
            result = measure.to_lookml_dict()
            # Returns: {"name": "revenue_measure", "type": "sum",
            #           "sql": "${TABLE}.revenue", "hidden": "yes", ...}
            ```
        """
        result: dict[str, Any] = {
            "name": f"{self.name}_measure",
            "type": LOOKML_TYPE_MAP.get(self.agg, "number"),
        }

        # Only add sql for non-count types
        # type: count in LookML doesn't take a sql parameter - it counts all rows
        if self.agg != AggregationType.COUNT:
            result["sql"] = self.expr or f"${{TABLE}}.{self.name}"

        # All measures are hidden (internal building blocks for metrics)
        result["hidden"] = "yes"

        if self.description:
            result["description"] = self.description
        if self.label:
            result["label"] = self.label

        # Add measure labels (prefix view_label with 2 spaces for sort order)
        view_label, group_label = self.get_measure_labels(model_name)
        if view_label:
            result["view_label"] = f"  {view_label.lstrip()}"  # 2 spaces prefix
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
        self,
        schema: str = "",
        convert_tz: bool | None = None,
        time_dimension_group_label: str | None = None,
        use_group_item_label: bool | None = None,
        use_bi_field_filter: bool = False,
        required_measures: set[str] | None = None,
    ) -> dict[str, Any]:
        """Convert entire semantic model to lkml views format.

        Transforms semantic model with entities, dimensions, and measures into
        LookML view dictionary structure suitable for file generation.

        Args:
            schema: Optional database schema name to prepend to table name
                in sql_table_name parameter.
            convert_tz: Optional timezone conversion setting passed to time
                dimensions as default. Individual dimensions can override via
                config.meta.convert_tz.
            time_dimension_group_label: Optional default group label for time
                dimension_groups. Passed to time dimensions. None means no
                group label applied at generator level.
            use_group_item_label: Optional group_item_label setting passed to
                time dimensions as default. Individual dimensions can override
                via config.meta.use_group_item_label. When enabled, generates
                Liquid templates for cleaner timeframe labels.
            use_bi_field_filter: Whether to filter fields based on bi_field
                metadata. When True, only dimensions and measures with
                config.meta.bi_field=True are included in the generated view.
                Entities are always included (needed for joins). Default: False.
            required_measures: Optional set of measure names that should be
                included regardless of bi_field status (e.g., measures needed
                by metrics with bi_field=True).

        Returns:
            Dictionary with LookML view configuration including dimensions,
            dimension_groups, measures, and sets.

        Example:
            Generate view with group_item_label enabled:

            ```python
            model = SemanticModel(name="orders", ...)
            view_dict = model.to_lookml_dict(
                schema="analytics",
                use_group_item_label=True
            )
            # All time dimensions get group_item_label templates
            ```
        """
        dimensions = []
        dimension_groups = []

        # Determine if this is a fact table (has measures)
        is_fact_table = len(self.measures) > 0

        # Extract view_label for entities from config.meta.subject
        entity_view_label = None
        if self.config and self.config.meta and self.config.meta.subject:
            entity_view_label = _smart_title(self.config.meta.subject)
        # If not in model config, try to get from first dimension's subject
        elif self.dimensions:
            for dim in self.dimensions:
                if dim.config and dim.config.meta and dim.config.meta.subject:
                    entity_view_label = _smart_title(dim.config.meta.subject)
                    break
        # Fall back to model name if no subject found
        if not entity_view_label:
            entity_view_label = _smart_title(self.name)

        # Convert entities to dimensions
        for entity in self.entities:
            dimensions.append(
                entity.to_lookml_dict(
                    view_label=entity_view_label, is_fact_table=is_fact_table
                )
            )

        # Convert dimensions (separate regular dims from time dims)
        # Track which dimensions were included for the dimensions_only set
        included_dimensions: list[Dimension] = []
        for dim in self.dimensions:
            # Apply bi_field filtering if enabled
            if use_bi_field_filter:
                has_bi_field = (
                    dim.config
                    and dim.config.meta
                    and dim.config.meta.bi_field is True
                )
                if not has_bi_field:
                    continue  # Skip dimensions without bi_field: true

            # Track this dimension as included
            included_dimensions.append(dim)

            # Pass convert_tz, time_dimension_group_label, and use_group_item_label
            # to time dimensions to propagate generator defaults
            if dim.type == DimensionType.TIME:
                dim_dict = dim.to_lookml_dict(
                    default_convert_tz=convert_tz,
                    default_time_dimension_group_label=time_dimension_group_label,
                    default_use_group_item_label=use_group_item_label,
                )
            else:
                dim_dict = dim.to_lookml_dict()

            if dim.type == DimensionType.TIME:
                dimension_groups.append(dim_dict)
            else:
                dimensions.append(dim_dict)

        # Convert measures (pass model name for group_label inference)
        # Apply bi_field filtering if enabled
        measures = []
        required_measure_names = required_measures or set()
        for measure in self.measures:
            force_hidden = False
            if use_bi_field_filter:
                has_bi_field = (
                    measure.config
                    and measure.config.meta
                    and measure.config.meta.bi_field is True
                )
                is_required = measure.name in required_measure_names
                if not has_bi_field and not is_required:
                    continue  # Skip unless bi_field or required by metrics
                # Force hidden if only included as metric dependency
                if is_required and not has_bi_field:
                    force_hidden = True
            measure_dict = measure.to_lookml_dict(model_name=self.name)
            if force_hidden:
                measure_dict["hidden"] = "yes"
            measures.append(measure_dict)

        # Collect all dimension field names for the dimensions_only set
        # Only include entities and dimensions that passed filtering
        dimension_field_names: list[str] = []
        for entity in self.entities:
            dimension_field_names.append(entity.name)
        for dim in included_dimensions:
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

    def get_required_measures(self) -> list[str]:
        """Get list of measure names this metric depends on.

        Extracts measure dependencies based on metric type:
        - Simple: Single measure reference
        - Ratio: Numerator and denominator measures
        - Derived: Extracted from metric references
        - Conversion: Empty (no simple measure dependencies)

        Returns:
            List of measure names required by this metric.
        """
        if self.type == "simple" and isinstance(self.type_params, SimpleMetricParams):
            return [self.type_params.measure]
        elif self.type == "ratio" and isinstance(self.type_params, RatioMetricParams):
            return [self.type_params.numerator, self.type_params.denominator]
        elif self.type == "derived" and isinstance(
            self.type_params, DerivedMetricParams
        ):
            # For derived metrics, extract unique metric names
            unique_measures = set()
            for ref in self.type_params.metrics:
                unique_measures.add(ref.name)
            return sorted(list(unique_measures))
        # Conversion metrics don't have direct measure dependencies
        return []
