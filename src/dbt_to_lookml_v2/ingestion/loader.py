"""YAML loader - loads semantic model files from directory."""

from pathlib import Path
from typing import Any

import yaml


class YamlLoader:
    """
    Load YAML files from a directory structure.

    Expected structure:
        semantic_layer/
        ├── rentals.yml           # data_model + semantic_model + metrics
        ├── facilities.yml
        └── ...

    Or split structure:
        semantic_layer/
        ├── models/
        │   └── rentals.yml
        └── metrics/
            └── rental_metrics.yml
    """

    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)

    def load_all(self) -> list[dict[str, Any]]:
        """
        Load all YAML files from the directory.

        Returns list of parsed YAML documents.
        """
        files = self._find_yaml_files()
        documents = []
        for file_path in files:
            doc = self._load_file(file_path)
            if doc:
                # Add source file for debugging
                doc["_source_file"] = str(file_path)
                documents.append(doc)
        return documents

    def load_file(self, file_path: str | Path) -> dict[str, Any]:
        """Load a single YAML file."""
        return self._load_file(Path(file_path))

    def _find_yaml_files(self) -> list[Path]:
        """Find all .yml and .yaml files recursively."""
        files = []
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
            raise ValueError(f"Expected dict at root of {file_path}, got {type(content)}")

        return content

    @classmethod
    def from_directory(cls, path: str | Path) -> "YamlLoader":
        """Create loader from directory path."""
        return cls(path)
