"""LookML-specific types for explore generation.

These types represent LookML concepts (joins, explores, field exposure)
and belong in the adapter layer, not the domain.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JoinRelationship(str, Enum):
    """LookML join relationship types."""

    MANY_TO_ONE = "many_to_one"
    ONE_TO_MANY = "one_to_many"
    ONE_TO_ONE = "one_to_one"


class JoinType(str, Enum):
    """LookML join types."""

    LEFT_OUTER = "left_outer"
    INNER = "inner"
    FULL_OUTER = "full_outer"


class ExposeLevel(str, Enum):
    """What fields to expose from a joined view."""

    ALL = "all"  # dimensions + metrics
    DIMENSIONS = "dimensions"  # dimensions only (safe default for incomplete FKs)


class JoinOverride(BaseModel):
    """Optional overrides for inferred joins."""

    model: str
    expose: ExposeLevel | None = None
    relationship: JoinRelationship | None = None

    model_config = {"frozen": True}


class ExploreConfig(BaseModel):
    """Explore configuration - LookML-specific authoring config."""

    name: str
    fact_model: str
    label: str | None = None
    description: str | None = None
    join_overrides: list[JoinOverride] = Field(default_factory=list)
    # Models to exclude from auto-join
    join_exclusions: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}

    def get_override(self, model_name: str) -> JoinOverride | None:
        """Get override for a specific model if it exists."""
        for override in self.join_overrides:
            if override.model == model_name:
                return override
        return None

    def is_excluded(self, model_name: str) -> bool:
        """Check if a model is excluded from auto-join."""
        return model_name in self.join_exclusions


class InferredJoin(BaseModel):
    """Join inferred from entity relationships."""

    model: str  # Model name to join
    entity: str  # Entity name used for join
    relationship: JoinRelationship
    expose: ExposeLevel
    fact_entity_name: str  # Dimension name on fact side (e.g., "facility")
    joined_entity_name: str  # Dimension name on joined side (e.g., "facility")

    model_config = {"frozen": True}

    @property
    def sql_on(self) -> str:
        """Generate sql_on clause (requires view names at render time)."""
        # This is a template - actual LookML refs are added during rendering
        fact_ref = f"${{FACT}}.{self.fact_entity_name}"
        join_ref = f"${{{self.model}}}.{self.joined_entity_name}"
        return f"{fact_ref} = {join_ref}"


def build_explore_config(data: dict[str, Any]) -> ExploreConfig:
    """Build ExploreConfig from dict (YAML parsing helper)."""
    join_overrides = []
    for jo in data.get("joins", []):
        override = _build_join_override(jo)
        join_overrides.append(override)

    return ExploreConfig(
        name=data["name"],
        fact_model=data["fact_model"],
        label=data.get("label"),
        description=data.get("description"),
        join_overrides=join_overrides,
        join_exclusions=data.get("join_exclusions", []),
    )


def _build_join_override(data: dict[str, Any]) -> JoinOverride:
    """Build JoinOverride from dict."""
    expose = None
    expose_str = data.get("expose")
    if expose_str:
        try:
            expose = ExposeLevel(expose_str)
        except ValueError:
            pass

    relationship = None
    rel_str = data.get("relationship")
    if rel_str:
        try:
            relationship = JoinRelationship(rel_str)
        except ValueError:
            pass

    return JoinOverride(
        model=data["model"],
        expose=expose,
        relationship=relationship,
    )
