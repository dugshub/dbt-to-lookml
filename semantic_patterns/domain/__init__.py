"""Domain layer - semantic primitives and types.

This layer contains output-agnostic semantic concepts:
- Models, entities, dimensions, measures, metrics
- Filters, time granularity, aggregation types

LookML-specific concepts (explores, joins, field exposure) belong in
adapters/lookml/types.py, not here.
"""

from semantic_patterns.domain.data_model import ConnectionType, DataModel
from semantic_patterns.domain.dimension import (
    Dimension,
    DimensionType,
    TimeGranularity,
    TimezoneVariant,
)
from semantic_patterns.domain.filter import Filter, FilterCondition, FilterOperator
from semantic_patterns.domain.measure import AggregationType, Measure
from semantic_patterns.domain.metric import (
    BenchmarkParams,
    Metric,
    MetricType,
    MetricVariant,
    PopComparison,
    PopConfig,
    PopOutput,
    PopParams,
    VariantKind,
)
from semantic_patterns.domain.model import DateSelectorConfig, Entity, ProcessedModel

__all__ = [
    # Data Model
    "ConnectionType",
    "DataModel",
    # Dimension
    "Dimension",
    "DimensionType",
    "TimeGranularity",
    "TimezoneVariant",
    # Filter
    "Filter",
    "FilterCondition",
    "FilterOperator",
    # Measure
    "AggregationType",
    "Measure",
    # Metric
    "BenchmarkParams",
    "Metric",
    "MetricType",
    "MetricVariant",
    "PopComparison",
    "PopConfig",
    "PopOutput",
    "PopParams",
    "VariantKind",
    # Model
    "DateSelectorConfig",
    "Entity",
    "ProcessedModel",
]
