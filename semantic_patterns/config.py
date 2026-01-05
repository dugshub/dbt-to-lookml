"""Configuration schema for semantic-patterns.

Defines the sp.yml configuration file format using Pydantic models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from semantic_patterns.adapters.dialect import Dialect


class ExploreJoinConfig(BaseModel):
    """Configuration for a join override in an explore."""

    model: str
    expose: str | None = None  # "all" or "dimensions"

    model_config = {"frozen": True}


class ExploreConfig(BaseModel):
    """Configuration for a single explore."""

    fact: str
    name: str | None = None  # Defaults to fact model name
    label: str | None = None
    description: str | None = None
    joins: list[ExploreJoinConfig] = Field(default_factory=list)

    model_config = {"frozen": True}

    @property
    def effective_name(self) -> str:
        """Get the explore name (defaults to fact model name)."""
        return self.name or self.fact


class ModelConfig(BaseModel):
    """Looker model file configuration."""

    name: str = "semantic_model"  # Model file name (without .lkml)
    connection: str = "database"  # Looker connection name
    label: str | None = None  # Optional model label

    model_config = {"frozen": True}


class OptionsConfig(BaseModel):
    """Generator options configuration."""

    dialect: Dialect = Dialect.REDSHIFT
    pop_strategy: str = "dynamic"  # "dynamic" or "native"
    date_selector: bool = True
    convert_tz: bool = False  # Convert time dimensions to UTC
    view_prefix: str = ""  # Prefix for view names
    explore_prefix: str = ""  # Prefix for explore names (defaults to view_prefix)

    model_config = {"frozen": True}

    @property
    def effective_explore_prefix(self) -> str:
        """Get explore prefix, defaulting to view_prefix if not set."""
        return self.explore_prefix or self.view_prefix

    @field_validator("dialect", mode="before")
    @classmethod
    def parse_dialect(cls, v: Any) -> Dialect:
        """Parse dialect from string."""
        if isinstance(v, Dialect):
            return v
        if isinstance(v, str):
            try:
                return Dialect(v.lower())
            except ValueError:
                valid = [d.value for d in Dialect]
                raise ValueError(f"Invalid dialect '{v}'. Valid: {valid}")
        # If not Dialect or str, try to convert - will fail if invalid
        return Dialect(v)


class SPConfig(BaseModel):
    """
    Root configuration for semantic-patterns.

    This is the schema for sp.yml files.

    Example:
        input: ./semantic_models
        output: ./lookml
        schema: gold

        model:
          name: analytics
          connection: redshift_prod

        explores:
          - fact: rentals
          - fact: orders
            label: Order Analysis

        options:
          dialect: redshift
          view_prefix: sm_
    """

    input: str
    output: str
    schema_name: str = Field(alias="schema")

    model: ModelConfig = Field(default_factory=ModelConfig)
    explores: list[ExploreConfig] = Field(default_factory=list)
    options: OptionsConfig = Field(default_factory=OptionsConfig)

    model_config = {"frozen": True, "populate_by_name": True}

    @property
    def input_path(self) -> Path:
        """Get input as Path."""
        return Path(self.input)

    @property
    def output_path(self) -> Path:
        """Get output as Path."""
        return Path(self.output)

    @classmethod
    def from_yaml(cls, content: str) -> SPConfig:
        """Parse config from YAML string."""
        data = yaml.safe_load(content)
        return cls.model_validate(data)

    @classmethod
    def from_file(cls, path: Path | str) -> SPConfig:
        """Load config from a YAML file."""
        path = Path(path)
        content = path.read_text(encoding="utf-8")
        return cls.from_yaml(content)


# Config file discovery
CONFIG_FILENAMES = ["sp.yml", "sp.yaml", ".sp.yml", ".sp.yaml"]


def find_config(start_dir: Path | str | None = None) -> Path | None:
    """
    Find sp.yml config file.

    Searches in:
    1. start_dir (if provided)
    2. Current working directory
    3. Parent directories up to root

    Args:
        start_dir: Directory to start search from

    Returns:
        Path to config file, or None if not found
    """
    if start_dir is None:
        start_dir = Path.cwd()
    else:
        start_dir = Path(start_dir)

    current = start_dir.resolve()

    while True:
        for filename in CONFIG_FILENAMES:
            config_path = current / filename
            if config_path.is_file():
                return config_path

        # Move to parent
        parent = current.parent
        if parent == current:
            # Reached root
            break
        current = parent

    return None


def load_config(path: Path | str | None = None) -> SPConfig:
    """
    Load configuration from file.

    If path is not provided, searches for sp.yml in current
    and parent directories.

    Args:
        path: Explicit path to config file

    Returns:
        Parsed SPConfig

    Raises:
        FileNotFoundError: If no config file found
        ValueError: If config is invalid
    """
    if path is None:
        path = find_config()
        if path is None:
            raise FileNotFoundError(
                "No sp.yml found. Create one or specify path with --config"
            )
    else:
        path = Path(path)

    return SPConfig.from_file(path)
