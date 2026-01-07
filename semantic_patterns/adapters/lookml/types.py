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


class ExploreJoinConfig(BaseModel):
    """Configuration for a join override in an explore."""

    model: str
    expose: str | None = None  # "all" or "dimensions"
    relationship: str | None = None  # "one_to_one", "many_to_one", "one_to_many"

    model_config = {"frozen": True}


class ExploreConfig(BaseModel):
    """Looker explore configuration."""

    fact: str  # Fact model name
    name: str | None = None  # Explore name (defaults to fact model name)
    label: str | None = None
    description: str | None = None
    joins: list[ExploreJoinConfig] = Field(default_factory=list)
    join_exclusions: list[str] = Field(default_factory=list)
    joined_facts: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}

    @property
    def effective_name(self) -> str:
        """Get the explore name (defaults to fact model name)."""
        return self.name or self.fact

    @property
    def fact_model(self) -> str:
        """Alias for fact (backwards compatibility)."""
        return self.fact

    def get_join_config(self, model_name: str) -> ExploreJoinConfig | None:
        """Get join config for a specific model if it exists."""
        for join in self.joins:
            if join.model == model_name:
                return join
        return None

    def get_override(self, model_name: str) -> ExploreJoinConfig | None:
        """Alias for get_join_config (backwards compatibility)."""
        return self.get_join_config(model_name)

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


