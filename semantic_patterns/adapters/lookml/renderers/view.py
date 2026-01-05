"""View rendering for LookML.

Composes dimensions, measures, and metrics into complete view structures.
"""

from typing import Any

from semantic_patterns.adapters.dialect import Dialect
from semantic_patterns.adapters.lookml.renderers.dimension import DimensionRenderer
from semantic_patterns.adapters.lookml.renderers.measure import MeasureRenderer
from semantic_patterns.adapters.lookml.renderers.pop import PopRenderer, PopStrategy
from semantic_patterns.domain import (
    Entity,
    ProcessedModel,
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
    ) -> None:
        self.dialect = dialect
        self.dimension_renderer = DimensionRenderer(dialect)
        self.measure_renderer = MeasureRenderer(dialect)
        self.pop_renderer = PopRenderer(pop_strategy)

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

        # Render dimensions
        dimensions = []
        for dim in model.dimensions:
            dim_results = self.dimension_renderer.render(dim)
            dimensions.extend(dim_results)

        if dimensions:
            view["dimensions"] = dimensions

        # Render entities as hidden dimensions with primary key
        entity_dims = self._render_entities(model.entities)
        if entity_dims:
            if "dimensions" in view:
                view["dimensions"].extend(entity_dims)
            else:
                view["dimensions"] = entity_dims

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

    def render_metrics_refinement(self, model: ProcessedModel) -> dict[str, Any] | None:
        """
        Render metrics as a refinement view.

        This is the metrics file: {model}.metrics.view.lkml
        Returns None if no metrics to render.
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

        return {
            "name": f"+{model.name}",  # Refinement syntax
            "measures": measures,
        }

    def render_pop_refinement(self, model: ProcessedModel) -> dict[str, Any] | None:
        """
        Render PoP variants as a refinement view.

        This is the PoP file: {model}.pop.view.lkml
        Returns None if no PoP variants.
        """
        # Check if any metrics have PoP variants
        has_pop = any(m.has_pop for m in model.metrics)
        if not has_pop:
            return None

        measures = []
        for metric in model.metrics:
            pop_measures = self.pop_renderer.render_variants(metric)
            measures.extend(pop_measures)

        if not measures:
            return None

        return {
            "name": f"+{model.name}",  # Refinement syntax
            "measures": measures,
        }

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

        # Add dimension names (accounting for variants)
        for dim in model.dimensions:
            if dim.has_variants and dim.variants:
                # Time dims with variants generate multiple fields
                for variant_name in dim.variants.keys():
                    fields.append(f"{dim.name}_{variant_name}")
            else:
                fields.append(dim.name)

        if not fields:
            return None

        return {
            "name": "dimensions_only",
            "fields": fields,
        }
