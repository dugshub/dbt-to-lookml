"""Configuration schema for semantic-patterns.

Defines the sp.yml configuration file format using Pydantic models.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, ClassVar

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self

from semantic_patterns.adapters.dialect import Dialect


class OutputOptionsConfig(BaseModel):
    """Output options configuration."""

    clean: str | None = None  # "clean", "warn", or "ignore" - None prompts on first run
    manifest: bool = True  # Generate .sp-manifest.json

    model_config = {"frozen": True}


class ExploreJoinConfig(BaseModel):
    """Configuration for a join override in an explore."""

    model: str
    expose: str | None = None  # "all" or "dimensions"
    relationship: str | None = None  # "one_to_one", "many_to_one", "one_to_many"

    model_config = {"frozen": True}


class ExploreConfig(BaseModel):
    """Configuration for a single explore."""

    fact: str
    name: str | None = None  # Defaults to fact model name
    label: str | None = None
    description: str | None = None
    joins: list[ExploreJoinConfig] = Field(default_factory=list)
    # Models to exclude from auto-join
    join_exclusions: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}

    @property
    def effective_name(self) -> str:
        """Get the explore name (defaults to fact model name)."""
        return self.name or self.fact

    def get_join_config(self, model_name: str) -> ExploreJoinConfig | None:
        """Get join config for a specific model if it exists."""
        for join in self.joins:
            if join.model == model_name:
                return join
        return None


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


class GitHubConfig(BaseModel):
    """GitHub destination configuration.

    Example:
        github:
          enabled: true
          repo: myorg/looker-models
          branch: semantic-patterns/dev
          path: lookml/
          protected_branches:
            - production
            - release
          commit_message: "Update LookML from dbt models"
    """

    enabled: bool = False
    repo: str = ""  # owner/repo format (required if enabled)
    branch: str = ""  # Target branch (required if enabled)
    path: str = ""  # Path within repo (default: repo root)
    protected_branches: list[str] = Field(default_factory=list)
    commit_message: str = "semantic-patterns: Update LookML"

    model_config = {"frozen": True}

    # Hard-coded protection - NEVER push to these branches
    # ClassVar excludes this from model serialization
    ALWAYS_PROTECTED: ClassVar[frozenset[str]] = frozenset({"main", "master"})

    @field_validator("repo")
    @classmethod
    def validate_repo_format(cls, v: str) -> str:
        """Validate repo is in owner/repo format."""
        if not v:
            return v  # Empty is ok when not enabled
        if not re.match(r"^[\w.-]+/[\w.-]+$", v):
            raise ValueError(
                f"Invalid repo format '{v}'. Expected 'owner/repo' format."
            )
        return v

    @field_validator("branch")
    @classmethod
    def validate_branch_not_protected(cls, v: str) -> str:
        """Validate branch is not in always-protected list."""
        if not v:
            return v  # Empty is ok when not enabled
        if v.lower() in cls.ALWAYS_PROTECTED:
            raise ValueError(
                f"Cannot push to '{v}' - this is a protected branch. "
                f"Use a feature branch like 'semantic-patterns/dev' instead."
            )
        return v

    @model_validator(mode="after")
    def validate_enabled_requires_fields(self) -> Self:
        """Validate required fields when enabled."""
        if self.enabled:
            if not self.repo:
                raise ValueError("github.repo is required when github.enabled is true")
            if not self.branch:
                raise ValueError(
                    "github.branch is required when github.enabled is true"
                )
            if self.branch in self.protected_branches:
                raise ValueError(
                    f"Branch '{self.branch}' is in protected_branches list"
                )
        return self

    @property
    def all_protected_branches(self) -> frozenset[str]:
        """Get all protected branches (built-in + custom)."""
        return self.ALWAYS_PROTECTED | frozenset(self.protected_branches)

    @property
    def repo_url(self) -> str:
        """Get the full GitHub repo URL."""
        return f"https://github.com/{self.repo}" if self.repo else ""


class SPConfig(BaseModel):
    """
    Root configuration for semantic-patterns.

    This is the schema for sp.yml files.

    Example:
        project: my_project  # Names output folder (default: semantic-patterns)
        input: ./semantic_models
        output: ./lookml
        schema: gold
        format: semantic-patterns  # or 'dbt'

        model:
          name: analytics
          connection: redshift_prod

        explores:
          - fact: rentals
          - fact: orders
            label: Order Analysis
            join_exclusions:
              - some_model_to_skip

        options:
          dialect: redshift
          view_prefix: sm_

        output_options:
          clean: clean  # or 'warn' or 'ignore'
          manifest: true

        # Optional: Push to GitHub
        github:
          enabled: true
          repo: myorg/looker-models
          branch: semantic-patterns/dev
    """

    input: str
    output: str
    schema_name: str = Field(alias="schema")
    format: str = "semantic-patterns"  # 'dbt' or 'semantic-patterns'
    project: str = "semantic-patterns"  # Project name (names output folder)

    model: ModelConfig = Field(default_factory=ModelConfig)
    explores: list[ExploreConfig] = Field(default_factory=list)
    options: OptionsConfig = Field(default_factory=OptionsConfig)
    output_options: OutputOptionsConfig = Field(default_factory=OutputOptionsConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)

    @field_validator("format", mode="before")
    @classmethod
    def validate_format(cls, v: Any) -> str:
        """Validate format is one of the allowed values."""
        if v is None:
            return "semantic-patterns"
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ("dbt", "semantic-patterns"):
                return v_lower
            raise ValueError(f"Invalid format '{v}'. Valid: 'dbt', 'semantic-patterns'")
        raise ValueError(f"format must be a string, got {type(v)}")

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
