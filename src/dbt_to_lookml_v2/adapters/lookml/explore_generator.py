"""Explore Generator - orchestrates explore and calendar file generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import lkml

from dbt_to_lookml_v2.adapters.dialect import Dialect, get_default_dialect
from dbt_to_lookml_v2.adapters.lookml.renderers.calendar import CalendarRenderer
from dbt_to_lookml_v2.adapters.lookml.renderers.explore import ExploreRenderer
from dbt_to_lookml_v2.domain import ExploreConfig, ProcessedModel


class ExploreGenerator:
    """
    Generate explore files from configuration.

    Produces:
    - {explore}.explore.lkml - Explore definition with joins
    - {explore}_explore_calendar.view.lkml - Unified date selector (if has dates)
    """

    def __init__(self, dialect: Dialect | None = None) -> None:
        self.dialect = dialect or get_default_dialect()
        self.calendar_renderer = CalendarRenderer()
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
        explore_dict = self.explore_renderer.render(
            explore_config, fact_model, models
        )
        explore_content = self._serialize_explore(explore_dict)
        files[f"{explore_config.name}.explore.lkml"] = explore_content

        # Collect joined models for calendar
        joined_models = self._get_joined_models(fact_model, models)

        # Generate calendar view if has date options
        date_options = self.calendar_renderer.collect_date_options(
            fact_model, joined_models
        )
        if date_options:
            calendar_dict = self.calendar_renderer.render(
                explore_config.name, date_options
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
        return lkml.dump(lookml_dict)

    def _serialize_view(self, view: dict[str, Any]) -> str:
        """Serialize view dict to LookML string."""
        lookml_dict = {"views": [view]}
        return lkml.dump(lookml_dict)
