"""Explore Generator - orchestrates explore and calendar file generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import lkml

from semantic_patterns.adapters.dialect import Dialect, get_default_dialect
from semantic_patterns.adapters.lookml.renderers.calendar import (
    CalendarRenderer,
    PopCalendarConfig,
)
from semantic_patterns.adapters.lookml.renderers.explore import ExploreRenderer
from semantic_patterns.adapters.lookml.types import ExploreConfig, build_explore_config
from semantic_patterns.domain import ProcessedModel


class ExploreGenerator:
    """
    Generate explore files from configuration.

    Produces:
    - {explore}.explore.lkml - Explore definition with joins
    - {explore}_explore_calendar.view.lkml - Unified date selector (if has dates)
    """

    def __init__(self, dialect: Dialect | None = None) -> None:
        self.dialect = dialect or get_default_dialect()
        self.calendar_renderer = CalendarRenderer(self.dialect)
        self.explore_renderer = ExploreRenderer(self.calendar_renderer)

    def generate(
        self,
        explores: list[ExploreConfig],
        models: dict[str, ProcessedModel],
    ) -> dict[str, str]:
        """
        Generate all explore files.

        Args:
            explores: List of explore configurations
            models: Dict of all models by name

        Returns:
            Dict of {filename: content}
        """
        files: dict[str, str] = {}

        for explore_config in explores:
            explore_files = self.generate_explore(explore_config, models)
            files.update(explore_files)

        return files

    def generate_explore(
        self,
        explore_config: ExploreConfig,
        models: dict[str, ProcessedModel],
    ) -> dict[str, str]:
        """Generate files for a single explore."""
        files: dict[str, str] = {}

        # Get fact model
        fact_model = models.get(explore_config.fact_model)
        if not fact_model:
            # Skip if fact model not found
            return files

        # Render explore
        explore_dict = self.explore_renderer.render(explore_config, fact_model, models)
        explore_content = self._serialize_explore(explore_dict)
        files[f"{explore_config.name}.explore.lkml"] = explore_content

        # Collect joined models for calendar
        joined_models = self._get_joined_models(fact_model, models)

        # Generate calendar view if has date options
        date_options = self.calendar_renderer.collect_date_options(
            fact_model, joined_models
        )
        if date_options:
            # Detect PoP metrics to enable calendar PoP infrastructure
            all_explore_models = [fact_model] + joined_models
            pop_config = PopCalendarConfig.from_models(all_explore_models)

            calendar_dict = self.calendar_renderer.render(
                explore_config.name, date_options, pop_config
            )
            if calendar_dict:
                calendar_content = self._serialize_view(calendar_dict)
                calendar_filename = f"{explore_config.name}_explore_calendar.view.lkml"
                files[calendar_filename] = calendar_content

        return files

    def generate_and_write(
        self,
        explores: list[ExploreConfig],
        models: dict[str, ProcessedModel],
        output_dir: str | Path,
    ) -> list[Path]:
        """
        Generate and write explore files to disk.

        Args:
            explores: List of explore configurations
            models: Dict of all models by name
            output_dir: Directory to write files to

        Returns:
            List of written file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files = self.generate(explores, models)
        written: list[Path] = []

        for filename, content in files.items():
            file_path = output_path / filename
            file_path.write_text(content, encoding="utf-8")
            written.append(file_path)

        return written

    def _get_joined_models(
        self,
        fact_model: ProcessedModel,
        all_models: dict[str, ProcessedModel],
    ) -> list[ProcessedModel]:
        """Get list of models that would be joined to the fact model."""
        joined: list[ProcessedModel] = []

        # Build lookup: entity_name -> model for primary entities
        primary_entity_lookup: dict[str, ProcessedModel] = {}
        for model in all_models.values():
            if model.name == fact_model.name:
                continue
            for entity in model.entities:
                if entity.type == "primary":
                    primary_entity_lookup[entity.name] = model

        # Find models for each foreign entity on fact
        for foreign_entity in fact_model.foreign_entities:
            if foreign_entity.name in primary_entity_lookup:
                joined.append(primary_entity_lookup[foreign_entity.name])

        # Find child facts (models with FK to this fact)
        if fact_model.primary_entity:
            fact_entity_name = fact_model.primary_entity.name
            for model in all_models.values():
                if model.name == fact_model.name:
                    continue
                for entity in model.foreign_entities:
                    if entity.name == fact_entity_name:
                        joined.append(model)

        return joined

    def _serialize_explore(self, explore: dict[str, Any]) -> str:
        """Serialize explore dict to LookML string."""
        lookml_dict = {"explores": [explore]}
        result = lkml.dump(lookml_dict)
        assert result is not None
        return result

    def _serialize_view(self, view: dict[str, Any]) -> str:
        """Serialize view dict to LookML string."""
        lookml_dict = {"views": [view]}
        result = lkml.dump(lookml_dict)
        assert result is not None
        return result

    @staticmethod
    def configs_from_fact_models(fact_models: list[str]) -> list[ExploreConfig]:
        """
        Create simple ExploreConfigs from a list of fact model names.

        This is the simplest way to generate explores - just specify which
        models are facts and the system infers joins from entity relationships.

        Args:
            fact_models: List of model names to use as explore facts

        Returns:
            List of ExploreConfig with name=fact_model, no overrides
        """
        return [ExploreConfig(name=name, fact_model=name) for name in fact_models]

    @staticmethod
    def configs_from_yaml(explore_dicts: list[dict[str, Any]]) -> list[ExploreConfig]:
        """
        Parse ExploreConfigs from YAML data.

        Use this when you have explore configuration in YAML format
        with labels, descriptions, or join overrides.

        Args:
            explore_dicts: List of explore config dicts from YAML

        Returns:
            List of ExploreConfig
        """
        return [build_explore_config(e) for e in explore_dicts]
