"""DomainBuilder - transforms YAML into domain model with expanded variants."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from semantic_patterns.domain import (
    AggregationType,
    ConnectionType,
    DataModel,
    DateSelectorConfig,
    Dimension,
    DimensionType,
    Entity,
    Filter,
    Measure,
    Metric,
    MetricType,
    PopComparison,
    PopConfig,
    PopOutput,
    ProcessedModel,
    TimeGranularity,
)
from semantic_patterns.ingestion.loader import YamlLoader


class DomainBuilder:
    """
    Build domain model from YAML files.

    Transforms our native schema YAML into fully-expanded ProcessedModel objects.
    """

    def __init__(self) -> None:
        self._data_models: dict[str, DataModel] = {}
        self._semantic_models: list[dict[str, Any]] = []
        self._metrics: list[dict[str, Any]] = []

    @classmethod
    def from_directory(cls, path: str | Path) -> list[ProcessedModel]:
        """
        Load YAML files from directory and build domain models.

        Returns list of ProcessedModel (semantic layer domain objects).
        Explore configuration is LookML-specific and handled by the adapter.
        """
        builder = cls()
        loader = YamlLoader(path)
        documents = loader.load_all()

        for doc in documents:
            builder._collect_from_document(doc)

        return builder.build()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> list[ProcessedModel]:
        """Build domain models from a single dict (for testing)."""
        builder = cls()
        builder._collect_from_document(data)
        return builder.build()

    def add_document(self, doc: dict[str, Any]) -> None:
        """
        Add a parsed document to the builder.

        Public method for adding documents from external sources (e.g., dbt mapper).
        Collects data models, semantic models, and metrics from the document.

        Args:
            doc: Parsed YAML document with data_models, semantic_models, and/or metrics
        """
        self._collect_from_document(doc)

    def _collect_from_document(self, doc: dict[str, Any]) -> None:
        """Collect data models, semantic models, and metrics from YAML."""
        # Collect data models
        for dm in doc.get("data_models", []):
            data_model = self._build_data_model(dm)
            self._data_models[data_model.name] = data_model

        # Collect semantic models
        self._semantic_models.extend(doc.get("semantic_models", []))

        # Collect metrics
        self._metrics.extend(doc.get("metrics", []))
        # Note: 'explores' in YAML is LookML-specific config, parsed by adapter

    def build(self) -> list[ProcessedModel]:
        """Build all ProcessedModel objects."""
        models = []
        for sm in self._semantic_models:
            model = self._build_processed_model(sm)
            models.append(model)
        return models

    def _build_data_model(self, data: dict[str, Any]) -> DataModel:
        """Build DataModel from dict."""
        connection_str = data.get("connection", "redshift")
        try:
            connection = ConnectionType(connection_str)
        except ValueError:
            connection = ConnectionType.REDSHIFT

        return DataModel(
            name=data["name"],
            catalog=data.get("catalog"),
            schema_name=data.get("schema", data.get("schema_name", "")),
            table=data["table"],
            connection=connection,
        )

    def _build_processed_model(self, data: dict[str, Any]) -> ProcessedModel:
        """Build ProcessedModel from semantic model dict."""
        name = data["name"]

        # Resolve data model reference
        data_model = None
        model_ref = data.get("model")
        if model_ref and model_ref in self._data_models:
            data_model = self._data_models[model_ref]

        # Build entities
        entities = [self._build_entity(e) for e in data.get("entities", [])]

        # Build dimensions
        dimensions = [self._build_dimension(d) for d in data.get("dimensions", [])]

        # Build measures
        measures = [self._build_measure(m) for m in data.get("measures", [])]

        # Resolve COUNT measures without expr - use primary entity for count_distinct
        measures = self._resolve_count_measures(measures, entities)

        # Build metrics (filter to those belonging to this model by entity)
        model_metrics = self._get_metrics_for_model(name, entities)
        metrics = [self._build_metric(m) for m in model_metrics]

        # Expand variants for all metrics
        for metric in metrics:
            metric.expand_variants()

        # Build date selector config
        date_selector = None
        if "date_selector" in data:
            ds = data["date_selector"]
            date_selector = DateSelectorConfig(dimensions=ds.get("dimensions", []))

        return ProcessedModel(
            name=name,
            label=data.get("label"),
            description=data.get("description"),
            data_model=data_model,
            measures=measures,
            dimensions=dimensions,
            metrics=metrics,
            entities=entities,
            time_dimension=data.get("time_dimension"),
            date_selector=date_selector,
            meta=data.get("meta", {}),
        )

    def _get_metrics_for_model(
        self, model_name: str, entities: list[Entity]
    ) -> list[dict[str, Any]]:
        """Get metrics that belong to a model (by primary entity reference)."""
        # Get PRIMARY entity names only - metrics belong to their primary model
        primary_entity_names = {e.name for e in entities if e.type == "primary"}

        # Filter metrics by entity field matching the model's primary entity
        matching_metrics = []
        for metric in self._metrics:
            metric_entity = metric.get("entity")
            if metric_entity and metric_entity in primary_entity_names:
                matching_metrics.append(metric)

        return matching_metrics

    def _build_entity(self, data: dict[str, Any]) -> Entity:
        """Build Entity from dict."""
        return Entity(
            name=data["name"],
            type=data["type"],
            expr=data["expr"],
            label=data.get("label"),
            complete=data.get("complete", False),
        )

    def _resolve_count_measures(
        self, measures: list[Measure], entities: list[Entity]
    ) -> list[Measure]:
        """
        Resolve COUNT measures without expressions.

        For measures with agg=COUNT and no expr, use the primary entity's
        expression and convert to COUNT_DISTINCT. This is safer than raw
        row counts which can be inflated by joins.

        Args:
            measures: List of measures to resolve
            entities: List of entities (to find primary)

        Returns:
            Updated list of measures with resolved expressions
        """
        # Find primary entity
        primary_entity = next(
            (e for e in entities if e.type == "primary"), None
        )

        if not primary_entity:
            return measures

        resolved = []
        for measure in measures:
            if measure.agg == AggregationType.COUNT and not measure.expr:
                # Use primary entity expr and convert to count_distinct
                resolved.append(
                    Measure(
                        name=measure.name,
                        agg=AggregationType.COUNT_DISTINCT,
                        expr=primary_entity.expr,
                        label=measure.label,
                        short_label=measure.short_label,
                        description=measure.description,
                        format=measure.format,
                        group=measure.group,
                        hidden=measure.hidden,
                        meta=measure.meta,
                    )
                )
            else:
                resolved.append(measure)

        return resolved

    def _build_dimension(self, data: dict[str, Any]) -> Dimension:
        """Build Dimension from dict."""
        # Parse dimension type
        dim_type_str = data.get("type", "categorical")
        if dim_type_str == "time":
            dim_type = DimensionType.TIME
        else:
            dim_type = DimensionType.CATEGORICAL

        # Parse granularity
        granularity = None
        gran_str = data.get("granularity")
        if gran_str:
            try:
                granularity = TimeGranularity(gran_str)
            except ValueError:
                pass

        # Parse variants
        variants = None
        if "variants" in data:
            variants = {k: v for k, v in data["variants"].items()}

        return Dimension(
            name=data["name"],
            type=dim_type,
            label=data.get("label"),
            short_label=data.get("short_label"),
            description=data.get("description"),
            expr=data.get("expr"),
            granularity=granularity,
            primary_variant=data.get("primary_variant"),
            variants=variants,
            group=data.get("group"),
            hidden=data.get("hidden", False),
            meta=data.get("meta", {}),
        )

    def _build_measure(self, data: dict[str, Any]) -> Measure:
        """Build Measure from dict."""
        # Parse aggregation type
        agg_str = data.get("agg", "sum")
        try:
            agg = AggregationType(agg_str)
        except ValueError:
            agg = AggregationType.SUM

        # expr can be None for COUNT - will be resolved later using primary entity
        # For other aggregation types, expr is required
        expr = data.get("expr")
        if not expr and agg != AggregationType.COUNT:
            raise KeyError(
                f"Measure '{data.get('name', 'unknown')}' with agg '{agg_str}' "
                "requires 'expr'. Only 'count' can omit expr (uses primary entity)."
            )

        return Measure(
            name=data["name"],
            agg=agg,
            expr=expr,
            label=data.get("label"),
            short_label=data.get("short_label"),
            description=data.get("description"),
            format=data.get("format"),
            group=data.get("group"),
            hidden=data.get("hidden", False),
            meta=data.get("meta", {}),
        )

    def _build_metric(self, data: dict[str, Any]) -> Metric:
        """Build Metric from dict."""
        # Parse metric type
        type_str = data.get("type", "simple")
        try:
            metric_type = MetricType(type_str)
        except ValueError:
            metric_type = MetricType.SIMPLE

        # Parse filter
        filter_obj = None
        if "filter" in data:
            filter_data = data["filter"]
            if isinstance(filter_data, dict):
                filter_obj = Filter.from_dict(filter_data)

        # Parse PoP config
        pop_config = None
        if "pop" in data:
            pop_config = self._build_pop_config(data["pop"])

        return Metric(
            name=data["name"],
            type=metric_type,
            label=data.get("label"),
            description=data.get("description"),
            measure=data.get("measure"),
            expr=data.get("expr"),
            metrics=data.get("metrics"),
            numerator=data.get("numerator"),
            denominator=data.get("denominator"),
            filter=filter_obj,
            pop=pop_config,
            format=data.get("format"),
            group=data.get("group"),
            entity=data.get("entity"),
            meta=data.get("meta", {}),
        )

    def _build_pop_config(self, data: dict[str, Any]) -> PopConfig:
        """Build PopConfig from dict."""
        # Parse comparisons
        comparisons = []
        for comp_str in data.get("comparisons", []):
            try:
                comparisons.append(PopComparison(comp_str))
            except ValueError:
                pass

        # Parse outputs
        outputs = []
        for out_str in data.get("outputs", []):
            try:
                outputs.append(PopOutput(out_str))
            except ValueError:
                pass

        return PopConfig(comparisons=comparisons, outputs=outputs)
