"""Data models for dbt semantic models and LookML structures.

This module provides backward compatibility by re-exporting from the new structure.
The actual implementations are now in:
- types.py: Enums and type definitions
- schemas.py: Pydantic model schemas
"""

# Re-export everything for backward compatibility
from dbt_to_lookml.schemas import (
    Config,
    ConfigMeta,
    Dimension,
    Entity,
    Hierarchy,
    LookMLDimension,
    LookMLDimensionGroup,
    LookMLExplore,
    LookMLMeasure,
    LookMLView,
    Measure,
    SemanticModel,
)
from dbt_to_lookml.types import AggregationType, DimensionType, TimeGranularity

__all__ = [
    # Types
    "AggregationType",
    "DimensionType",
    "TimeGranularity",
    # Semantic Model Schemas
    "Hierarchy",
    "ConfigMeta",
    "Config",
    "Entity",
    "Dimension",
    "Measure",
    "SemanticModel",
    # LookML Schemas
    "LookMLDimension",
    "LookMLDimensionGroup",
    "LookMLMeasure",
    "LookMLView",
    "LookMLExplore",
]