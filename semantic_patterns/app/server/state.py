"""Server state - holds loaded config and models."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from semantic_patterns.config import SPConfig, find_config, load_config
from semantic_patterns.domain import ProcessedModel
from semantic_patterns.ingestion.builder import DomainBuilder
from semantic_patterns.ingestion.dbt.loader import DbtLoader
from semantic_patterns.ingestion.dbt.mapper import DbtMapper


class ServerState(BaseModel):
    """Holds the current state of loaded config and models."""

    config_path: Path | None = None
    config: SPConfig | None = None
    models: list[ProcessedModel] = []

    model_config = {"arbitrary_types_allowed": True}

    def load(self, config_path: Path | None = None) -> None:
        """Load config and models from disk."""
        # Find and load config
        if config_path is None:
            found = find_config()
            if found is None:
                raise FileNotFoundError("No sp.yml found")
            config_path = found

        self.config_path = config_path
        self.config = load_config(config_path)

        # Resolve input path relative to config file
        input_path = self.config.input_path
        if not input_path.is_absolute():
            input_path = config_path.parent / input_path

        # Load models based on format
        if self.config.format == "dbt":
            self.models = self._load_dbt_models(input_path)
        else:
            self.models = self._load_native_models(input_path)

    def _load_native_models(self, input_path: Path) -> list[ProcessedModel]:
        """Load semantic-patterns native format."""
        return DomainBuilder.from_directory(input_path)

    def _load_dbt_models(self, input_path: Path) -> list[ProcessedModel]:
        """Load dbt semantic layer format."""
        loader = DbtLoader(input_path)
        semantic_models, metrics = loader.load_all()

        # Map dbt format to our format
        mapper = DbtMapper()
        mapper.add_semantic_models(semantic_models)
        mapper.add_metrics(metrics)
        documents = mapper.get_documents()

        # Build domain models from mapped documents
        builder = DomainBuilder()
        for doc in documents:
            builder.add_document(doc)

        return builder.build()

    def reload(self) -> None:
        """Reload from current config path."""
        if self.config_path:
            self.load(self.config_path)

    def get_model(self, name: str) -> ProcessedModel | None:
        """Get a model by name."""
        for model in self.models:
            if model.name == name:
                return model
        return None

    def get_stats(self) -> dict[str, Any]:
        """Get summary statistics."""
        total_dimensions = sum(len(m.dimensions) for m in self.models)
        total_measures = sum(len(m.measures) for m in self.models)
        total_metrics = sum(len(m.metrics) for m in self.models)
        total_variants = sum(m.total_variant_count for m in self.models)
        total_entities = sum(len(m.entities) for m in self.models)

        return {
            "models": len(self.models),
            "dimensions": total_dimensions,
            "measures": total_measures,
            "metrics": total_metrics,
            "metric_variants": total_variants,
            "entities": total_entities,
            "explores": len(self.config.explores) if self.config else 0,
        }


# Global state instance
state = ServerState()
