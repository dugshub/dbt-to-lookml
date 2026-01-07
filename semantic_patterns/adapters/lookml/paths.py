"""Path generation for LookML output structure.

Generates domain-based folder structure:
    {output}/{project}/
    ├── .sp-manifest.json
    ├── {project}.model.lkml
    ├── views/
    │   ├── {model_name}/
    │   │   ├── {model}.view.lkml
    │   │   ├── {model}.metrics.view.lkml
    │   │   └── {model}.pop.view.lkml
    │   └── ...
    └── explores/
        └── {explore}.explore.lkml
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
    def explores_path(self) -> Path:
        """Explores folder: {output}/{project}/explores/"""
        return self.project_path / "explores"

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

    def calendar_view_name(self, explore_name: str) -> str:
        """Get standardized calendar view name for an explore."""
        return f"{explore_name}_explore_calendar"

    def calendar_file_path(self, explore_name: str) -> Path:
        """Path for calendar view in views/{explore}_explore_calendar/ folder."""
        calendar_name = self.calendar_view_name(explore_name)
        return self.view_domain_path(calendar_name) / f"{calendar_name}.view.lkml"

    def explore_file_path(self, explore_name: str) -> Path:
        """Path for explore file: {output}/{project}/explores/{explore}.explore.lkml"""
        return self.explores_path / f"{explore_name}.explore.lkml"

    def model_file_path(self) -> Path:
        """Path for model file: {output}/{project}/{project}.model.lkml"""
        return self.project_path / f"{self.project}.model.lkml"

    def relative_path(self, full_path: Path) -> str:
        """
        Get path relative to project root for include statements.

        Returns: "{relative_path}" format for LookML includes (no leading slash)
        """
        rel = full_path.relative_to(self.project_path)
        return str(rel)

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

        Returns: "/explores/{explore}.explore.lkml"
        """
        return f"/explores/{explore_name}.explore.lkml"

    def relative_calendar_include(self, explore_name: str) -> str:
        """
        Generate include path for calendar view.

        Returns: "/views/{explore}_explore_calendar/{explore}_explore_calendar.view.lkml"
        """
        calendar_name = self.calendar_view_name(explore_name)
        return f"/views/{calendar_name}/{calendar_name}.view.lkml"

    def ensure_directories(self) -> None:
        """Create all required directories."""
        self.project_path.mkdir(parents=True, exist_ok=True)
        self.views_path.mkdir(exist_ok=True)
        self.explores_path.mkdir(exist_ok=True)

    def ensure_view_domain(self, model_name: str) -> None:
        """Ensure domain folder exists for a model."""
        self.view_domain_path(model_name).mkdir(parents=True, exist_ok=True)
