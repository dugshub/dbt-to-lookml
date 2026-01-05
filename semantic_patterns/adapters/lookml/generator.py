"""LookML Generator - orchestrates file generation from ProcessedModels."""

from pathlib import Path
from typing import Any

import lkml

from semantic_patterns.adapters.dialect import Dialect, get_default_dialect
from semantic_patterns.adapters.lookml.renderers.pop import PopStrategy
from semantic_patterns.adapters.lookml.renderers.view import ViewRenderer
from semantic_patterns.domain import ProcessedModel


class LookMLGenerator:
    """
    Generate LookML files from ProcessedModels.

    Produces split files with refinements:
    - {model}.view.lkml - Base view with dimensions and entities
    - {model}.metrics.view.lkml - Refinement with metric measures
    - {model}.pop.view.lkml - Refinement with PoP measures

    Files are only generated if they have content.
    """

    def __init__(
        self,
        dialect: Dialect | None = None,
        pop_strategy: PopStrategy | None = None,
    ) -> None:
        self.dialect = dialect or get_default_dialect()
        self.view_renderer = ViewRenderer(self.dialect, pop_strategy)

    def generate(self, models: list[ProcessedModel]) -> dict[str, str]:
        """
        Generate LookML files for all models.

        Returns dict of {filename: content}.
        """
        files: dict[str, str] = {}

        for model in models:
            model_files = self.generate_model(model)
            files.update(model_files)

        return files

    def generate_model(self, model: ProcessedModel) -> dict[str, str]:
        """Generate LookML files for a single model."""
        files: dict[str, str] = {}

        # Base view (always generated)
        base_view = self.view_renderer.render_base_view(model)
        base_content = self._serialize_view(base_view)
        files[f"{model.name}.view.lkml"] = base_content

        # Metrics refinement (if has metrics)
        metrics_view = self.view_renderer.render_metrics_refinement(model)
        if metrics_view:
            metrics_content = self._serialize_view(metrics_view)
            files[f"{model.name}.metrics.view.lkml"] = metrics_content

        # PoP refinement (if has PoP variants)
        pop_view = self.view_renderer.render_pop_refinement(model)
        if pop_view:
            pop_content = self._serialize_view(pop_view)
            files[f"{model.name}.pop.view.lkml"] = pop_content

        return files

    def generate_and_write(
        self,
        models: list[ProcessedModel],
        output_dir: str | Path,
    ) -> list[Path]:
        """
        Generate and write LookML files to disk.

        Returns list of written file paths.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files = self.generate(models)
        written: list[Path] = []

        for filename, content in files.items():
            file_path = output_path / filename
            file_path.write_text(content, encoding="utf-8")
            written.append(file_path)

        return written

    def _serialize_view(self, view: dict[str, Any]) -> str:
        """Serialize view dict to LookML string."""
        # Wrap in views array for lkml
        lookml_dict = {"views": [view]}
        result = lkml.dump(lookml_dict)
        assert result is not None
        return result
