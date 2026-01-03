"""Explore rendering for LookML.

Generates explore definitions with inferred joins from entity relationships.
"""

from __future__ import annotations

from typing import Any

from dbt_to_lookml_v2.adapters.lookml.renderers.calendar import (
    CalendarRenderer,
)
from dbt_to_lookml_v2.domain import (
    ExploreConfig,
    ExposeLevel,
    InferredJoin,
    JoinRelationship,
    ProcessedModel,
)


def _smart_title(name: str) -> str:
    """Convert snake_case to Title Case."""
    return " ".join(word.capitalize() for word in name.replace("_", " ").split())


class ExploreRenderer:
    """Render explore definitions to LookML."""

    def __init__(self, calendar_renderer: CalendarRenderer | None = None) -> None:
        self.calendar_renderer = calendar_renderer or CalendarRenderer()

    def render(
        self,
        explore_config: ExploreConfig,
        fact_model: ProcessedModel,
        all_models: dict[str, ProcessedModel],
    ) -> dict[str, Any]:
        """
        Render explore dict for lkml serialization.

        Args:
            explore_config: Configuration for this explore
            fact_model: The fact model for this explore
            all_models: Dict of all models by name (for join inference)

        Returns:
            Dict ready for lkml.dump() in explores format
        """
        explore: dict[str, Any] = {
            "name": explore_config.name,
        }

        # Add 'from' if explore name differs from fact model name
        if explore_config.name != explore_config.fact_model:
            explore["from"] = explore_config.fact_model

        # Optional label and description
        if explore_config.label:
            explore["label"] = explore_config.label
        else:
            explore["label"] = _smart_title(explore_config.name)

        if explore_config.description:
            explore["description"] = explore_config.description

        # Infer joins from entity relationships
        inferred_joins = self.infer_joins(
            fact_model, all_models, explore_config
        )

        # Collect joined models for calendar generation
        joined_models: list[ProcessedModel] = []

        # Render joins
        joins = []
        for join in inferred_joins:
            join_dict = self._render_join(join, fact_model.name)
            joins.append(join_dict)

            # Track joined model for calendar
            if join.model in all_models:
                joined_models.append(all_models[join.model])

        # Add calendar join if we have date options
        date_options = self.calendar_renderer.collect_date_options(
            fact_model, joined_models
        )
        if date_options:
            calendar_view_name = f"{explore_config.name}_explore_calendar"
            calendar_join = self._render_calendar_join(calendar_view_name)
            joins.append(calendar_join)

        if joins:
            explore["joins"] = joins

        return explore

    def infer_joins(
        self,
        fact_model: ProcessedModel,
        all_models: dict[str, ProcessedModel],
        explore_config: ExploreConfig,
    ) -> list[InferredJoin]:
        """
        Infer joins from entity relationships.

        Walks fact model's foreign entities and finds matching primary entities
        in other models.

        Args:
            fact_model: The fact model for this explore
            all_models: Dict of all models by name
            explore_config: Config for potential join overrides

        Returns:
            List of InferredJoin objects
        """
        joins: list[InferredJoin] = []

        # Build lookup: entity_name -> (model, entity) for primary entities
        primary_entity_lookup: dict[str, tuple[ProcessedModel, Any]] = {}
        for model in all_models.values():
            if model.name == fact_model.name:
                continue
            for entity in model.entities:
                if entity.type == "primary":
                    primary_entity_lookup[entity.name] = (model, entity)

        # Check each foreign entity on fact model
        for foreign_entity in fact_model.foreign_entities:
            if foreign_entity.name not in primary_entity_lookup:
                continue

            target_model, target_entity = primary_entity_lookup[foreign_entity.name]

            # Determine expose level
            expose = self._determine_expose_level(
                foreign_entity, target_model, explore_config
            )

            joins.append(
                InferredJoin(
                    model=target_model.name,
                    entity=foreign_entity.name,
                    relationship=JoinRelationship.MANY_TO_ONE,
                    expose=expose,
                    fact_entity_expr=foreign_entity.expr,
                    joined_entity_expr=target_entity.expr,
                )
            )

        # Check for child facts (models with complete foreign entity pointing to fact)
        if fact_model.primary_entity:
            fact_entity_name = fact_model.primary_entity.name
            for model in all_models.values():
                if model.name == fact_model.name:
                    continue
                for entity in model.foreign_entities:
                    if entity.name == fact_entity_name:
                        # This model has a FK to our fact model
                        expose = self._determine_expose_level(
                            entity, model, explore_config
                        )
                        # Find the matching entity expr on the joined model's primary
                        joined_expr = entity.expr
                        joins.append(
                            InferredJoin(
                                model=model.name,
                                entity=fact_entity_name,
                                relationship=JoinRelationship.ONE_TO_MANY,
                                expose=expose,
                                fact_entity_expr=fact_model.primary_entity.expr,
                                joined_entity_expr=joined_expr,
                            )
                        )

        return joins

    def _determine_expose_level(
        self,
        foreign_entity: Any,
        target_model: ProcessedModel,
        explore_config: ExploreConfig,
    ) -> ExposeLevel:
        """
        Determine what fields to expose from a joined model.

        Priority:
        1. Explicit override in explore config
        2. `complete: true` on foreign entity → expose all
        3. Default → expose dimensions only (safe)
        """
        # Check for override
        override = explore_config.get_override(target_model.name)
        if override and override.expose:
            return override.expose

        # Check complete flag on foreign entity
        if getattr(foreign_entity, "complete", False):
            return ExposeLevel.ALL

        # Safe default: dimensions only
        return ExposeLevel.DIMENSIONS

    def _render_join(
        self,
        join: InferredJoin,
        fact_view_name: str,
    ) -> dict[str, Any]:
        """Render a single join to LookML dict."""
        join_dict: dict[str, Any] = {
            "name": join.model,
            "type": "left_outer",
            "relationship": join.relationship.value,
            "sql_on": (
                f"${{{fact_view_name}.{join.fact_entity_expr}}} = "
                f"${{{join.model}.{join.joined_entity_expr}}}"
            ),
        }

        # Add field restriction if not exposing all
        if join.expose == ExposeLevel.DIMENSIONS:
            join_dict["fields"] = [f"{join.model}.dimensions_only*"]

        return join_dict

    def _render_calendar_join(self, calendar_view_name: str) -> dict[str, Any]:
        """Render the calendar view join."""
        return {
            "name": calendar_view_name,
            "relationship": "one_to_one",
            "sql": "",  # Empty SQL for virtual view
        }

    def get_calendar_view(
        self,
        explore_config: ExploreConfig,
        fact_model: ProcessedModel,
        joined_models: list[ProcessedModel],
    ) -> dict[str, Any] | None:
        """
        Generate the calendar view for this explore.

        Returns None if no date selector dimensions exist.
        """
        date_options = self.calendar_renderer.collect_date_options(
            fact_model, joined_models
        )
        if not date_options:
            return None

        return self.calendar_renderer.render(explore_config.name, date_options)
