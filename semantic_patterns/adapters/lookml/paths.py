"""Path generation for LookML output structure.

Generates domain-based folder structure:
    {output}/{project}/
    ├── .sp-manifest.json
    ├── views/
    │   ├── {model_name}/
    │   │   ├── {model}.view.lkml
    │   │   ├── {model}.metrics.view.lkml
    │   │   └── {model}.pop.view.lkml
    │   └── ...
    └── models/
        ├── {explore}.explore.lkml
        └── {project}.model.lkml
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class OutputPaths:
    """Container for output path structure."""

    project: str
    base_path: Path

    @property
    def project_path(self) -> Path:
        """Root project folder: {output}/{project}/"""
        return self.base_path / self.project

    @property
    def views_path(self) -> Path:
        """Views folder: {output}/{project}/views/"""
        return self.project_path / "views"

    @property
    def models_path(self) -> Path:
        """Models folder: {output}/{project}/models/"""
        return self.project_path / "models"

    @property
    def manifest_path(self) -> Path:
        """Manifest file: {output}/{project}/.sp-manifest.json"""
        return self.project_path / ".sp-manifest.json"

    def view_domain_path(self, model_name: str) -> Path:
        """Domain folder for views: {output}/{project}/views/{model_name}/"""
        return self.views_path / model_name

    def view_file_path(self, model_name: str, suffix: str = "") -> Path:
        """
        Full path for a view file.

        Args:
            model_name: Name of the model
            suffix: Optional suffix like ".metrics" or ".pop"

        Returns:
            Path like views/{model_name}/{model_name}{suffix}.view.lkml
        """
        filename = f"{model_name}{suffix}.view.lkml"
        return self.view_domain_path(model_name) / filename

    def calendar_file_path(self, explore_name: str) -> Path:
        """Path for calendar view in views/{explore}_calendar/ folder."""
        calendar_name = f"{explore_name}_calendar"
        return self.view_domain_path(calendar_name) / f"{calendar_name}.view.lkml"

    def explore_file_path(self, explore_name: str) -> Path:
        """Path for explore file: {output}/{project}/models/{explore}.explore.lkml"""
        return self.models_path / f"{explore_name}.explore.lkml"

    def model_file_path(self) -> Path:
        """Path for model file: {output}/{project}/models/{project}.model.lkml"""
        return self.models_path / f"{self.project}.model.lkml"

    def relative_path(self, full_path: Path) -> str:
        """
        Get path relative to project root for include statements.

        Returns: "/{relative_path}" format for LookML includes
        """
        rel = full_path.relative_to(self.project_path)
        return f"/{rel}"

    def relative_view_include(self, model_name: str, suffix: str = "") -> str:
        """
        Generate include path relative to project root for model file.

        Returns: "/views/{model_name}/{model_name}{suffix}.view.lkml"
        """
        filename = f"{model_name}{suffix}.view.lkml"
        return f"/views/{model_name}/{filename}"

    def relative_explore_include(self, explore_name: str) -> str:
        """
        Generate include path relative to project root for model file.

        Returns: "/models/{explore}.explore.lkml"
        """
        return f"/models/{explore_name}.explore.lkml"

    def relative_calendar_include(self, explore_name: str) -> str:
        """
        Generate include path for calendar view.

        Returns: "/views/{explore}_calendar/{explore}_calendar.view.lkml"
        """
        calendar_name = f"{explore_name}_calendar"
        return f"/views/{calendar_name}/{calendar_name}.view.lkml"

    def ensure_directories(self) -> None:
        """Create all required directories."""
        self.project_path.mkdir(parents=True, exist_ok=True)
        self.views_path.mkdir(exist_ok=True)
        self.models_path.mkdir(exist_ok=True)

    def ensure_view_domain(self, model_name: str) -> None:
        """Ensure domain folder exists for a model."""
        self.view_domain_path(model_name).mkdir(parents=True, exist_ok=True)
