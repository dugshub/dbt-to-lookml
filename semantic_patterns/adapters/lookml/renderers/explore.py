"""Explore rendering for LookML.

Generates explore definitions with inferred joins from entity relationships.
"""

from __future__ import annotations

from typing import Any

from semantic_patterns.adapters.lookml.renderers.calendar import (
    CalendarRenderer,
)
from semantic_patterns.adapters.lookml.types import (
    ExploreConfig,
    ExposeLevel,
    InferredJoin,
    JoinRelationship,
)
from semantic_patterns.domain import ProcessedModel


def get_calendar_view_name(explore_name: str) -> str:
    """
    Get standardized calendar view name for an explore.

    Centralized naming convention - must match OutputPaths.calendar_view_name()
    """
    return f"{explore_name}_explore_calendar"


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
    ) -> tuple[dict[str, Any], list[str]]:
        """
        Render explore dict and required includes for lkml serialization.

        Args:
            explore_config: Configuration for this explore
            fact_model: The fact model for this explore
            all_models: Dict of all models by name (for join inference)

        Returns:
            Tuple of (explore dict, list of include paths)
        """
        # Track all views that need to be included
        includes: list[str] = []

        # Include fact model view (using wildcard for all refinements)
        includes.append(f"/**/{fact_model.name}.view.lkml")

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
        inferred_joins = self.infer_joins(fact_model, all_models, explore_config)

        # Collect joined models for calendar generation
        joined_models: list[ProcessedModel] = []

        # Render joins
        joins = []
        for join in inferred_joins:
            join_dict = self._render_join(join, fact_model.name)
            joins.append(join_dict)

            # Include joined view (using wildcard for all refinements)
            includes.append(f"/**/{join.model}.view.lkml")

            # Track joined model for calendar
            if join.model in all_models:
                joined_models.append(all_models[join.model])

        # Add calendar join if we have date options
        date_options = self.calendar_renderer.collect_date_options(
            fact_model, joined_models
        )
        if date_options:
            calendar_view_name = get_calendar_view_name(explore_config.name)
            calendar_join = self._render_calendar_join(calendar_view_name)
            joins.append(calendar_join)

            # Include calendar view
            includes.append(f"/**/{calendar_view_name}.view.lkml")

        if joins:
            explore["joins"] = joins

        return explore, includes

    def infer_joins(
        self,
        fact_model: ProcessedModel,
        all_models: dict[str, ProcessedModel],
        explore_config: ExploreConfig,
    ) -> list[InferredJoin]:
        """
        Infer joins from entity relationships (exclude-based).

        Auto-joins ALL entity-linked models by default. Use join_exclusions
        to exclude specific models from auto-join.

        Args:
            fact_model: The fact model for this explore
            all_models: Dict of all models by name
            explore_config: Config for join overrides and exclusions

        Returns:
            List of InferredJoin objects
        """
        joins: list[InferredJoin] = []

        # Build lookup: entity_name -> (model, entity) for primary entities
        # Exclude models in join_exclusions
        primary_entity_lookup: dict[str, tuple[ProcessedModel, Any]] = {}
        for model in all_models.values():
            if model.name == fact_model.name:
                continue
            if explore_config.is_excluded(model.name):
                continue
            for entity in model.entities:
                if entity.type == "primary":
                    primary_entity_lookup[entity.name] = (model, entity)

        # Check each foreign entity on fact model
        for foreign_entity in fact_model.foreign_entities:
            if foreign_entity.name not in primary_entity_lookup:
                continue

            target_model, target_entity = primary_entity_lookup[foreign_entity.name]

            # Determine relationship (explicit override takes priority)
            relationship = self._determine_relationship(
                target_model.name, explore_config, JoinRelationship.MANY_TO_ONE
            )

            # Determine expose level
            expose = self._determine_expose_level(
                foreign_entity, target_model, explore_config
            )

            joins.append(
                InferredJoin(
                    model=target_model.name,
                    entity=foreign_entity.name,
                    relationship=relationship,
                    expose=expose,
                    fact_entity_name=foreign_entity.name,
                    joined_entity_name=target_entity.name,
                )
            )

        # Check for child facts (models with foreign entity pointing to fact)
        if fact_model.primary_entity:
            fact_entity_name = fact_model.primary_entity.name
            for model in all_models.values():
                if model.name == fact_model.name:
                    continue
                if explore_config.is_excluded(model.name):
                    continue
                for entity in model.foreign_entities:
                    if entity.name == fact_entity_name:
                        # This model has a FK to our fact model
                        # Determine relationship (explicit override takes priority)
                        relationship = self._determine_relationship(
                            model.name, explore_config, JoinRelationship.ONE_TO_MANY
                        )

                        expose = self._determine_expose_level(
                            entity, model, explore_config
                        )
                        # Use entity names (not expressions) for dimension references
                        joins.append(
                            InferredJoin(
                                model=model.name,
                                entity=fact_entity_name,
                                relationship=relationship,
                                expose=expose,
                                fact_entity_name=fact_model.primary_entity.name,
                                joined_entity_name=entity.name,
                            )
                        )

        return joins

    def _determine_relationship(
        self,
        model_name: str,
        explore_config: ExploreConfig,
        default: JoinRelationship,
    ) -> JoinRelationship:
        """
        Determine join relationship from explicit config or default.

        Priority:
        1. Explicit relationship in join override
        2. Default based on entity direction
        """
        override = explore_config.get_override(model_name)
        if override and override.relationship:
            return override.relationship
        return default

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
                f"${{{fact_view_name}.{join.fact_entity_name}}} = "
                f"${{{join.model}.{join.joined_entity_name}}}"
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
            "type": "cross",
            "relationship": "one_to_one",
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
