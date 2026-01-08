"""View rendering for LookML.

Composes dimensions, measures, and metrics into complete view structures.
"""

from typing import Any

import sqlglot
import sqlglot.expressions as exp

from semantic_patterns.adapters.dialect import Dialect
from semantic_patterns.adapters.lookml.renderers.dimension import DimensionRenderer
from semantic_patterns.adapters.lookml.renderers.measure import MeasureRenderer
from semantic_patterns.adapters.lookml.renderers.pop import PopRenderer, PopStrategy
from semantic_patterns.domain import (
    Dimension,
    DimensionType,
    Entity,
    ProcessedModel,
    TimeGranularity,
)


class ViewRenderer:
    """
    Render ProcessedModel to LookML view structures.

    Generates:
    - Base view: dimensions, entities, sql_table_name
    - Metrics refinement: metric measures
    - PoP refinement: period_over_period measures
    """

    def __init__(
        self,
        dialect: Dialect | None = None,
        pop_strategy: PopStrategy | None = None,
        model_to_explore: dict[str, str] | None = None,
        model_to_fact: dict[str, str] | None = None,
    ) -> None:
        self.dialect = dialect
        self.dimension_renderer = DimensionRenderer(dialect)
        # MeasureRenderer will be created per-view with defined_fields
        self.pop_renderer = PopRenderer(pop_strategy)
        self.model_to_explore = model_to_explore or {}
        self.model_to_fact = model_to_fact or {}

    @staticmethod
    def _build_defined_fields(model: ProcessedModel) -> dict[str, str]:
        """
        Build map of column_name -> field_name for dimensions and entities.

        This allows measures to reference existing dimensions rather than
        re-declaring SQL column references.

        Returns:
            Dict mapping column names AND dimension names to LookML field names

        Example:
            Categorical dimension: name="transaction_type", expr="rental_event_type"
            Mapping: {
                "rental_event_type": "transaction_type",  # column -> field
                "transaction_type": "transaction_type",   # field -> field (identity)
            }

            Time dimension: name="created_at", expr="rental_created_at_utc"
            Mapping: {
                "rental_created_at_utc": "created_at_raw",  # column -> _raw field
                "created_at": "created_at_raw",             # name -> _raw field
            }

            Time dimension with variants: name="created_at", variants={utc: col_utc, local: col_local}
            Mapping: {
                "col_utc": "created_at_utc_raw",      # variant column -> variant _raw field
                "col_local": "created_at_local_raw", # variant column -> variant _raw field
                "created_at_utc": "created_at_utc_raw",    # variant name -> variant _raw field
                "created_at_local": "created_at_local_raw", # variant name -> variant _raw field
            }
        """
        mapping: dict[str, str] = {}

        # Add dimensions
        for dim in model.dimensions:
            if dim.type == DimensionType.TIME:
                # Time dimensions become dimension_groups with timeframe suffixes
                # The _raw timeframe gives the actual timestamp value
                if dim.has_variants and dim.variants:
                    # Map each variant's column and name to its _raw field
                    for variant_name, variant_expr in dim.variants.items():
                        field_name = f"{dim.name}_{variant_name}_raw"
                        # Map variant dimension name (e.g., "created_at_utc")
                        mapping[f"{dim.name}_{variant_name}"] = field_name
                        # Map variant SQL column (e.g., "rental_created_at_utc")
                        col_name = ViewRenderer._extract_simple_column(variant_expr)
                        if col_name:
                            mapping[col_name] = field_name
                else:
                    # Non-variant time dimension
                    field_name = f"{dim.name}_raw"
                    # Map dimension name to _raw field
                    mapping[dim.name] = field_name
                    # Map SQL column to _raw field
                    if dim.expr:
                        col_name = ViewRenderer._extract_simple_column(dim.expr)
                        if col_name and col_name != dim.name:
                            mapping[col_name] = field_name
            else:
                # Categorical dimensions map directly
                mapping[dim.name] = dim.name
                if dim.expr:
                    col_name = ViewRenderer._extract_simple_column(dim.expr)
                    if col_name and col_name != dim.name:
                        mapping[col_name] = dim.name

        # Add entities
        for entity in model.entities:
            # Map entity name to itself
            mapping[entity.name] = entity.name

            # Also map column name to entity name
            if entity.expr:
                col_name = ViewRenderer._extract_simple_column(entity.expr)
                if col_name and col_name != entity.name:
                    mapping[col_name] = entity.name

        return mapping

    @staticmethod
    def _extract_simple_column(expr: str) -> str | None:
        """
        Extract bare column name from simple SQL expressions.

        Examples:
            "transaction_type" -> "transaction_type"
            "unique_rental_sk" -> "unique_rental_sk"
            "UPPER(status)" -> None (not a simple column)
        """
        if not expr:
            return None

        try:
            parsed = sqlglot.parse_one(expr)
            # Check if it's just a bare column (no functions, operators, etc.)
            if isinstance(parsed, exp.Column) and not parsed.table:
                return parsed.name
        except Exception:
            pass

        return None

    def render_base_view(self, model: ProcessedModel) -> dict[str, Any]:
        """
        Render the base view with dimensions and entities.

        This is the main view file: {model}.view.lkml
        """
        view: dict[str, Any] = {
            "name": model.name,
        }

        # SQL table name
        if model.sql_table_name:
            view["sql_table_name"] = model.sql_table_name

        # Build field mapping progressively as we render dimensions
        # This allows later dimensions to reference earlier ones
        defined_fields: dict[str, str] = {}

        # Render dimensions - separate regular dimensions from dimension_groups
        dimensions = []
        dimension_groups = []
        for dim in model.dimensions:
            # Render this dimension with access to previously-defined dimensions
            dim_results = self.dimension_renderer.render(dim, defined_fields)

            if dim.type == DimensionType.TIME:
                dimension_groups.extend(dim_results)
            else:
                dimensions.extend(dim_results)

            # Add this dimension to the mapping for subsequent dimensions
            # Time dimensions map to _raw field, categorical dimensions map directly
            if dim.type == DimensionType.TIME:
                if dim.has_variants and dim.variants:
                    # Map each variant's column and name to its _raw field
                    for variant_name, variant_expr in dim.variants.items():
                        field_name = f"{dim.name}_{variant_name}_raw"
                        defined_fields[f"{dim.name}_{variant_name}"] = field_name
                        col_name = self._extract_simple_column(variant_expr)
                        if col_name:
                            defined_fields[col_name] = field_name
                else:
                    # Non-variant time dimension
                    field_name = f"{dim.name}_raw"
                    defined_fields[dim.name] = field_name
                    if dim.expr:
                        col_name = self._extract_simple_column(dim.expr)
                        if col_name and col_name != dim.name:
                            defined_fields[col_name] = field_name
            else:
                # Categorical dimensions map directly
                defined_fields[dim.name] = dim.name
                if dim.expr:
                    col_name = self._extract_simple_column(dim.expr)
                    if col_name and col_name != dim.name:
                        defined_fields[col_name] = dim.name

        # Render entities as hidden dimensions with primary key
        entity_dims = self._render_entities(model.entities, defined_fields)
        if entity_dims:
            dimensions.extend(entity_dims)

        # Add entities to the field mapping
        for entity in model.entities:
            defined_fields[entity.name] = entity.name
            if entity.expr:
                col_name = self._extract_simple_column(entity.expr)
                if col_name and col_name != entity.name:
                    defined_fields[col_name] = entity.name

        if dimensions:
            view["dimensions"] = dimensions

        if dimension_groups:
            view["dimension_groups"] = dimension_groups

        # Create measure renderer with complete field mapping
        measure_renderer = MeasureRenderer(self.dialect, defined_fields)

        # Render measures (hidden raw measures)
        measures = []
        for measure in model.measures:
            if measure.hidden:  # Only include hidden measures in base
                measures.append(measure_renderer.render_measure(measure, defined_fields))

        if measures:
            view["measures"] = measures

        # Generate dimensions_only set for join field restriction
        dim_set = self._render_dimensions_only_set(model)
        if dim_set:
            view["sets"] = [dim_set]

        return view

    def render_metrics_refinement(self, model: ProcessedModel) -> tuple[dict[str, Any], list[str]] | None:
        """
        Render metrics as a refinement view with includes.

        This is the metrics file: {model}.metrics.view.lkml
        Returns tuple of (view dict, includes list) or None if no metrics.
        """
        if not model.metrics:
            return None

        # Build field mapping for measure rendering
        defined_fields = self._build_defined_fields(model)
        measure_renderer = MeasureRenderer(self.dialect, defined_fields)

        # Build measure lookup for simple metrics
        measure_lookup = {m.name: m for m in model.measures}

        # Render base metric measures (not PoP variants)
        measures = []
        for metric in model.metrics:
            # Render base metric (using field refs for existing dimensions)
            base_measure = measure_renderer.render_metric(metric, measure_lookup, defined_fields)
            measures.append(base_measure)

        if not measures:
            return None

        # Refinement needs to include base view
        includes = [f"{model.name}.view.lkml"]

        return (
            {
                "name": f"+{model.name}",  # Refinement syntax
                "measures": measures,
            },
            includes,
        )

    def render_pop_refinement(self, model: ProcessedModel) -> tuple[dict[str, Any], list[str]] | None:
        """
        Render PoP variants as a refinement view with includes.

        This is the PoP file: {model}.pop.view.lkml
        Returns tuple of (view dict, includes list) or None if no PoP variants.
        """
        # Check if any metrics have PoP variants
        has_pop = any(m.has_pop for m in model.metrics)
        if not has_pop:
            return None

        # Create PoP renderer with fact view context
        # Calendar dimension is defined on the fact view via +{fact_view} extension
        from semantic_patterns.adapters.lookml.renderers.pop import LookerNativePopStrategy

        # Find the fact view for this model's explore
        # PoP measures need to reference {fact_view}.calendar_date
        fact_view_name = self.model_to_fact.get(model.name)
        if not fact_view_name:
            # Model not in any explore - skip PoP generation
            # (These are dimension-only models that get joined but don't have their own explore)
            return None

        pop_strategy = LookerNativePopStrategy(fact_view_name=fact_view_name)
        pop_renderer = PopRenderer(pop_strategy)

        measures = []
        for metric in model.metrics:
            pop_measures = pop_renderer.render_variants(metric)
            measures.extend(pop_measures)

        if not measures:
            return None

        # PoP refinement needs to include base view AND metrics file
        # (PoP measures reference metrics like "gmv" which are in metrics file)
        includes = [f"{model.name}.view.lkml", f"{model.name}.metrics.view.lkml"]

        return (
            {
                "name": f"+{model.name}",  # Refinement syntax
                "measures": measures,
            },
            includes,
        )

    def _render_entities(self, entities: list[Entity], defined_fields: dict[str, str]) -> list[dict[str, Any]]:
        """Render entities as hidden dimensions."""
        from semantic_patterns.adapters.lookml.sql_qualifier import LookMLSqlQualifier

        results = []

        for entity in entities:
            # Qualify entity expression (may reference dimensions)
            if defined_fields:
                qualifier = LookMLSqlQualifier(self.dialect, defined_fields)
                sql_expr = qualifier.qualify(entity.expr, defined_fields)
            else:
                sql_expr = qualify_table_columns(entity.expr)

            dim: dict[str, Any] = {
                "name": entity.name,
                "type": "string",
                "sql": sql_expr,
                "hidden": "yes",
            }

            if entity.type == "primary":
                dim["primary_key"] = "yes"

            if entity.label:
                dim["label"] = entity.label

            results.append(dim)

        return results

    def _render_dimensions_only_set(
        self, model: ProcessedModel
    ) -> dict[str, Any] | None:
        """
        Generate dimensions_only set for join field restriction.

        Includes all dimensions and entity dimensions.
        Used in explores: fields: [view.dimensions_only*]
        """
        fields: list[str] = []

        # Add entity names
        for entity in model.entities:
            fields.append(entity.name)

        # Add dimension names (accounting for time dimension_groups and variants)
        for dim in model.dimensions:
            if dim.type == DimensionType.TIME:
                # Time dimension_groups generate multiple timeframe fields
                # Explicitly list each timeframe (wildcards don't work in sets)
                timeframes = self._get_timeframes_for_dimension(dim)

                if dim.has_variants and dim.variants:
                    # With variants: created_utc_date, created_utc_week, created_local_date, etc.
                    for variant_name in dim.variants.keys():
                        for timeframe in timeframes:
                            fields.append(f"{dim.name}_{variant_name}_{timeframe}")
                else:
                    # Without variants: created_date, created_week, starts_at_date, etc.
                    for timeframe in timeframes:
                        fields.append(f"{dim.name}_{timeframe}")
            else:
                # Categorical dimensions have a single field
                fields.append(dim.name)

        if not fields:
            return None

        return {
            "name": "dimensions_only",
            "fields": fields,
        }

    def _get_timeframes_for_dimension(self, dim: Dimension) -> list[str]:
        """Get timeframes that will be generated for a time dimension."""
        # Map granularity to timeframes (matches dimension renderer logic)
        GRANULARITY_TIMEFRAMES = {
            TimeGranularity.HOUR: ["raw", "time", "hour", "date", "week", "month", "quarter", "year"],
            TimeGranularity.DAY: ["raw", "date", "week", "month", "quarter", "year"],
            TimeGranularity.WEEK: ["raw", "week", "month", "quarter", "year"],
            TimeGranularity.MONTH: ["raw", "month", "quarter", "year"],
            TimeGranularity.QUARTER: ["raw", "quarter", "year"],
            TimeGranularity.YEAR: ["raw", "year"],
        }
        DEFAULT_TIMEFRAMES = ["raw", "date", "week", "month", "quarter", "year"]

        if dim.granularity and dim.granularity in GRANULARITY_TIMEFRAMES:
            return GRANULARITY_TIMEFRAMES[dim.granularity]
        return DEFAULT_TIMEFRAMES
