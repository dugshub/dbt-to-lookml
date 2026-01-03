"""Explore domain types for LookML explore generation."""

from __future__ import annotations

from enum import Enum

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

    model_config = {"frozen": True}


class ExploreConfig(BaseModel):
    """Explore configuration from YAML."""

    name: str
    fact_model: str
    label: str | None = None
    description: str | None = None
    join_overrides: list[JoinOverride] = Field(default_factory=list)

    model_config = {"frozen": True}

    def get_override(self, model_name: str) -> JoinOverride | None:
        """Get override for a specific model if it exists."""
        for override in self.join_overrides:
            if override.model == model_name:
                return override
        return None


class InferredJoin(BaseModel):
    """Join inferred from entity relationships."""

    model: str  # Model name to join
    entity: str  # Entity name used for join
    relationship: JoinRelationship
    expose: ExposeLevel
    fact_entity_expr: str  # Expression on fact side (e.g., "facility_sk")
    joined_entity_expr: str  # Expression on joined side (e.g., "facility_sk")

    model_config = {"frozen": True}

    @property
    def sql_on(self) -> str:
        """Generate sql_on clause (requires view names at render time)."""
        # This is a template - actual LookML refs are added during rendering
        return f"${{FACT}}.{self.fact_entity_expr} = ${{{self.model}}}.{self.joined_entity_expr}"
