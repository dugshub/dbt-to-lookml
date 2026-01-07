"""View rendering for LookML.

Composes dimensions, measures, and metrics into complete view structures.
"""

from typing import Any

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
    ) -> None:
        self.dialect = dialect
        self.dimension_renderer = DimensionRenderer(dialect)
        self.measure_renderer = MeasureRenderer(dialect)
        self.pop_renderer = PopRenderer(pop_strategy)
        self.model_to_explore = model_to_explore or {}

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

        # Render dimensions - separate regular dimensions from dimension_groups
        dimensions = []
        dimension_groups = []
        for dim in model.dimensions:
            dim_results = self.dimension_renderer.render(dim)
            if dim.type == DimensionType.TIME:
                dimension_groups.extend(dim_results)
            else:
                dimensions.extend(dim_results)

        # Render entities as hidden dimensions with primary key
        entity_dims = self._render_entities(model.entities)
        if entity_dims:
            dimensions.extend(entity_dims)

        if dimensions:
            view["dimensions"] = dimensions

        if dimension_groups:
            view["dimension_groups"] = dimension_groups

        # Render measures (hidden raw measures)
        measures = []
        for measure in model.measures:
            if measure.hidden:  # Only include hidden measures in base
                measures.append(self.measure_renderer.render_measure(measure))

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

        # Build measure lookup for simple metrics
        measure_lookup = {m.name: m for m in model.measures}

        # Render base metric measures (not PoP variants)
        measures = []
        for metric in model.metrics:
            # Render base metric
            base_measure = self.measure_renderer.render_metric(metric, measure_lookup)
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

        # Create PoP renderer with calendar view context
        # Use model-to-explore mapping to find the correct explore's calendar
        from semantic_patterns.adapters.lookml.renderers.explore import (
            get_calendar_view_name,
        )
        from semantic_patterns.adapters.lookml.renderers.pop import LookerNativePopStrategy

        # Find which explore this model belongs to
        explore_name = self.model_to_explore.get(model.name)
        if not explore_name:
            # Model not in any explore - skip PoP generation
            # (These are dimension-only models that get joined but don't have their own explore)
            return None

        calendar_view_name = get_calendar_view_name(explore_name)
        pop_strategy = LookerNativePopStrategy(calendar_view_name=calendar_view_name)
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

    def _render_entities(self, entities: list[Entity]) -> list[dict[str, Any]]:
        """Render entities as hidden dimensions."""
        results = []

        for entity in entities:
            dim: dict[str, Any] = {
                "name": entity.name,
                "type": "string",
                "sql": f"${{TABLE}}.{entity.expr}",
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
