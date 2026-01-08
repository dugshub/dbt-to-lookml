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
from semantic_patterns.adapters.lookml.types import ExploreConfig


class OutputOptionsConfig(BaseModel):
    """Output options configuration."""

    clean: str | None = None  # "clean", "warn", or "ignore" - None prompts on first run
    manifest: bool = True  # Generate .sp-manifest.json

    model_config = {"frozen": True}


class ModelConfig(BaseModel):
    """Looker model file configuration."""

    name: str = "semantic_model"  # Model file name (without .lkml)
    connection: str = "database"  # Looker connection name
    label: str | None = None  # Optional model label

    model_config = {"frozen": True}


class LabelConfig(BaseModel):
    """Configuration for label rendering behavior."""

    max_length: int = 27  # Looker filter clips at ~27-29 chars
    group_conformity: bool = True  # If one field in group uses short_label, all do
    pop_style: str = "compact"  # "compact", "standard", or "verbose"

    model_config = {"frozen": True}


class OptionsConfig(BaseModel):
    """Generator options configuration."""

    dialect: Dialect = Dialect.REDSHIFT
    pop_strategy: str = "dynamic"  # "dynamic" or "native"
    date_selector: bool = True
    convert_tz: bool = False  # Convert time dimensions to UTC
    view_prefix: str = ""  # Prefix for view names
    explore_prefix: str = ""  # Prefix for explore names (defaults to view_prefix)
    labels: LabelConfig = Field(default_factory=LabelConfig)

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


class LookerConfig(BaseModel):
    """Looker destination configuration.

    Unified config for LookML generation, Git repository push, and dev environment sync.

    Example:
        looker:
          enabled: true

          # LookML model configuration
          model:
            name: analytics
            connection: redshift_prod

          # Explores (optional - omit for views-only)
          explores:
            - fact: rentals
            - fact: orders
              label: Order Analysis

          # Git repository (backing Looker project)
          repo: myorg/looker-models
          branch: sp-generated
          path: lookml/
          commit_message: "semantic-patterns: Update LookML"

          # Looker instance (optional - for dev sync)
          base_url: https://mycompany.looker.com
          project_id: my_lookml_project
          sync_dev: true
    """

    enabled: bool = False

    # LookML generation config
    model: ModelConfig = Field(default_factory=ModelConfig)
    explores: list[ExploreConfig] = Field(default_factory=list)

    # Git repository settings (backing the Looker project)
    repo: str = ""  # owner/repo format (required if enabled)
    branch: str = ""  # Target branch (required if enabled)
    path: str = ""  # Path within repo (default: repo root)
    protected_branches: list[str] = Field(default_factory=list)
    commit_message: str = "semantic-patterns: Update LookML"

    # Looker instance settings (optional - for dev environment sync)
    base_url: str = ""  # e.g., https://mycompany.looker.com
    project_id: str = ""  # Looker project name
    sync_dev: bool = True  # Sync user's dev environment after push

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
                f"Use a feature branch like 'sp-generated' instead."
            )
        return v

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate and normalize Looker base URL."""
        if not v:
            return v
        # Remove trailing slash
        v = v.rstrip("/")
        # Ensure https
        if not v.startswith("https://"):
            if v.startswith("http://"):
                v = v.replace("http://", "https://", 1)
            else:
                v = f"https://{v}"
        return v

    @model_validator(mode="after")
    def validate_enabled_requires_fields(self) -> Self:
        """Validate required fields when enabled."""
        if self.enabled:
            if not self.repo:
                raise ValueError("looker.repo is required when looker.enabled is true")
            if not self.branch:
                raise ValueError(
                    "looker.branch is required when looker.enabled is true"
                )
            if self.branch in self.protected_branches:
                raise ValueError(
                    f"Branch '{self.branch}' is in protected_branches list"
                )
            # If sync_dev is true, require Looker instance settings
            if self.sync_dev and self.base_url and not self.project_id:
                raise ValueError(
                    "looker.project_id is required when looker.base_url is set"
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

    @property
    def looker_sync_enabled(self) -> bool:
        """Check if Looker dev sync is configured and enabled."""
        return self.sync_dev and bool(self.base_url) and bool(self.project_id)


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

        options:
          dialect: redshift
          view_prefix: sm_

        output_options:
          clean: clean  # or 'warn' or 'ignore'
          manifest: true

        # Looker-specific configuration
        looker:
          enabled: true

          model:
            name: analytics
            connection: redshift_prod

          explores:
            - fact: rentals
            - fact: facility_monthly_status
              label: Facility Monthly Status
              joined_facts:
                - facility_lifecycle
              join_exclusions:
                - some_model_to_skip

          repo: myorg/looker-models
          branch: sp-generated
          base_url: https://mycompany.looker.com
          project_id: my_lookml_project
    """

    input: str
    output: str
    schema_name: str = Field(alias="schema")
    format: str = "semantic-patterns"  # 'dbt' or 'semantic-patterns'
    project: str = "semantic-patterns"  # Project name (names output folder)

    options: OptionsConfig = Field(default_factory=OptionsConfig)
    output_options: OutputOptionsConfig = Field(default_factory=OutputOptionsConfig)
    looker: LookerConfig = Field(default_factory=LookerConfig)

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

    # Backwards compatibility: delegate to looker config
    @property
    def model(self) -> ModelConfig:
        """Get model config (delegates to looker.model)."""
        return self.looker.model

    @property
    def explores(self) -> list[ExploreConfig]:
        """Get explores config (delegates to looker.explores)."""
        return self.looker.explores

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
