"""ProcessedModel - the fully-expanded domain model ready for adapters."""

from typing import Any

from pydantic import BaseModel, Field, computed_field

from semantic_patterns.domain.data_model import DataModel
from semantic_patterns.domain.dimension import Dimension, DimensionType
from semantic_patterns.domain.measure import Measure
from semantic_patterns.domain.metric import Metric


class Entity(BaseModel):
    """An entity (join key) from the semantic model."""

    name: str
    type: str  # primary, foreign, unique
    expr: str
    label: str | None = None
    # For foreign keys: True = all rows have valid FK, safe for metrics
    complete: bool = False

    model_config = {"frozen": True}


class DateSelectorConfig(BaseModel):
    """Configuration for date selector feature."""

    dimensions: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}


class ProcessedModel(BaseModel):
    """
    A fully-processed semantic model ready for adapter rendering.

    Key properties:
    - Metrics have their variants already expanded
    - All typing decisions are made
    - Adapter just maps types to syntax
    """

    name: str
    description: str | None = None

    # Data source
    data_model: DataModel | None = None  # Reference to physical table

    # Core primitives
    measures: list[Measure] = Field(default_factory=list)
    dimensions: list[Dimension] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)

    # Join keys
    entities: list[Entity] = Field(default_factory=list)

    # Time dimension config
    time_dimension: str | None = None  # Default aggregation time dimension

    # Date selector config
    date_selector: DateSelectorConfig | None = None

    # Metadata
    meta: dict[str, Any] = Field(default_factory=dict)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def primary_entity(self) -> Entity | None:
        for entity in self.entities:
            if entity.type == "primary":
                return entity
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def foreign_entities(self) -> list[Entity]:
        return [e for e in self.entities if e.type == "foreign"]

    @property
    def sql_table_name(self) -> str | None:
        """Get fully qualified table name from data model."""
        if self.data_model:
            return self.data_model.fully_qualified
        return None

    @property
    def time_dimensions(self) -> list[Dimension]:
        return [d for d in self.dimensions if d.type == DimensionType.TIME]

    @property
    def categorical_dimensions(self) -> list[Dimension]:
        return [d for d in self.dimensions if d.type == DimensionType.CATEGORICAL]

    @property
    def date_selector_dimensions(self) -> list[Dimension]:
        """Get dimensions that are part of date selector."""
        if not self.date_selector:
            return []
        return [
            d for d in self.time_dimensions if d.name in self.date_selector.dimensions
        ]

    @property
    def default_time_dimension(self) -> Dimension | None:
        """Get the default time dimension for aggregations."""
        if not self.time_dimension:
            return None
        for dim in self.time_dimensions:
            if dim.name == self.time_dimension:
                return dim
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_variant_count(self) -> int:
        return sum(m.variant_count for m in self.metrics)

    def get_metric(self, name: str) -> Metric | None:
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None

    def get_measure(self, name: str) -> Measure | None:
        for measure in self.measures:
            if measure.name == name:
                return measure
        return None

    def get_dimension(self, name: str) -> Dimension | None:
        for dim in self.dimensions:
            if dim.name == name:
                return dim
        return None

    def summary(self) -> str:
        return (
            f"ProcessedModel({self.name}): "
            f"{len(self.measures)} measures, "
            f"{len(self.dimensions)} dimensions, "
            f"{len(self.metrics)} metrics ({self.total_variant_count} variants)"
        )

    model_config = {"frozen": False}
