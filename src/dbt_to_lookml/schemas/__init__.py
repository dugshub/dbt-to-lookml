"""Schema definitions for dbt semantic models and LookML structures.

This module provides backward compatibility for existing imports while the schemas
are organized into domain-specific modules:

- schemas.config: Shared configuration schemas (Hierarchy, ConfigMeta, Config)
- schemas.semantic_layer: dbt semantic layer schemas (Entity, Dimension, Measure,
  SemanticModel, Metric, MetricReference, *MetricParams)
- schemas.lookml: LookML output schemas (LookML*)

Migration Guide:
    Old import style (deprecated):
        >>> from dbt_to_lookml.schemas import SemanticModel, Dimension

    New import style (recommended):
        >>> from dbt_to_lookml.schemas.semantic_layer import SemanticModel, Dimension
        >>> from dbt_to_lookml.schemas.config import Config, ConfigMeta
        >>> from dbt_to_lookml.schemas.lookml import LookMLView, LookMLExplore

Note:
    Importing from this module directly will trigger a DeprecationWarning.
    Please migrate to the new module-specific imports.
"""

from __future__ import annotations

import warnings

# Import all schemas for re-export
from dbt_to_lookml.schemas.config import Config, ConfigMeta, Hierarchy
from dbt_to_lookml.schemas.lookml import (
    LookMLDimension,
    LookMLDimensionGroup,
    LookMLExplore,
    LookMLMeasure,
    LookMLSet,
    LookMLView,
)
from dbt_to_lookml.schemas.semantic_layer import (
    ConversionMetricParams,
    DerivedMetricParams,
    Dimension,
    Entity,
    Measure,
    Metric,
    MetricReference,
    RatioMetricParams,
    SemanticModel,
    SimpleMetricParams,
)

# Issue deprecation warning
warnings.warn(
    "Importing from dbt_to_lookml.schemas is deprecated. "
    "Use specific modules instead:\n"
    "  - dbt_to_lookml.schemas.config for Config, ConfigMeta, Hierarchy\n"
    "  - dbt_to_lookml.schemas.semantic_layer for SemanticModel, "
    "Dimension, Measure, Entity, Metric, etc.\n"
    "  - dbt_to_lookml.schemas.lookml for LookML* classes",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    # Config schemas
    "Hierarchy",
    "ConfigMeta",
    "Config",
    # Semantic layer schemas
    "Entity",
    "Dimension",
    "Measure",
    "SemanticModel",
    "MetricReference",
    "SimpleMetricParams",
    "RatioMetricParams",
    "DerivedMetricParams",
    "ConversionMetricParams",
    "Metric",
    # LookML schemas
    "LookMLDimension",
    "LookMLDimensionGroup",
    "LookMLMeasure",
    "LookMLSet",
    "LookMLView",
    "LookMLExplore",
]
