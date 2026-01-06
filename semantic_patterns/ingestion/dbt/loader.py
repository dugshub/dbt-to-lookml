"""DbtLoader - loads dbt semantic model YAML files from directory."""

from pathlib import Path
from typing import Any

import yaml


class DbtLoader:
    """
    Load dbt semantic model files.

    Handles:
    - Finding all YAML files recursively
    - Separating `semantic_models:` from `metrics:` entries
    - Returning raw parsed dicts
    """

    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)

    def load_all(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Load all semantic models and metrics.

        Returns:
            Tuple of (semantic_models, metrics)
        """
        files = self._find_yaml_files()
        semantic_models: list[dict[str, Any]] = []
        metrics: list[dict[str, Any]] = []

        for file_path in files:
            doc = self._load_file(file_path)
            if doc:
                # Collect semantic_models
                for sm in doc.get("semantic_models", []):
                    sm["_source_file"] = str(file_path)
                    semantic_models.append(sm)

                # Collect metrics
                for m in doc.get("metrics", []):
                    m["_source_file"] = str(file_path)
                    metrics.append(m)

        return semantic_models, metrics

    def _find_yaml_files(self) -> list[Path]:
        """Find all .yml and .yaml files recursively."""
        files: list[Path] = []
        for pattern in ["**/*.yml", "**/*.yaml"]:
            files.extend(self.base_path.glob(pattern))
        # Sort for deterministic ordering
        return sorted(set(files))

    def _load_file(self, file_path: Path) -> dict[str, Any]:
        """Load and parse a single YAML file."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        if content is None:
            return {}

        if not isinstance(content, dict):
            raise ValueError(
                f"Expected dict at root of {file_path}, got {type(content)}"
            )

        return content

    @classmethod
    def from_directory(cls, path: str | Path) -> "DbtLoader":
        """Create loader from directory path."""
        return cls(path)
