"""Parser for dbt semantic model YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from dbt_to_lookml.models import (
    AggregationType,
    Config,
    ConfigMeta,
    Dimension,
    DimensionType,
    Entity,
    Measure,
    SemanticModel,
)


class SemanticModelParser:
    """Parser for dbt semantic model YAML files."""

    def __init__(self, strict_mode: bool = False) -> None:
        """Initialize the parser.

        Args:
            strict_mode: If True, raise errors on validation issues.
                        If False, log warnings and continue.
        """
        self.strict_mode = strict_mode

    def parse_file(self, file_path: Path) -> list[SemanticModel]:
        """Parse a single YAML file containing semantic models.

        Args:
            file_path: Path to the YAML file to parse.

        Returns:
            List of parsed semantic models.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            yaml.YAMLError: If the YAML is invalid.
            ValidationError: If the semantic model structure is invalid.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, encoding='utf-8') as f:
            content = yaml.safe_load(f)

        if not content:
            return []

        semantic_models = []

        # Handle both single model and list of models
        if isinstance(content, dict):
            if 'semantic_models' in content:
                models_data = content['semantic_models']
            else:
                # Assume the entire content is a single model
                models_data = [content]
        elif isinstance(content, list):
            models_data = content
        else:
            raise ValueError(f"Invalid YAML structure in {file_path}")

        for model_data in models_data:
            try:
                semantic_model = self._parse_semantic_model(model_data)
                semantic_models.append(semantic_model)
            except (ValidationError, ValueError) as e:
                if self.strict_mode:
                    raise
                print(f"Warning: Skipping invalid model in {file_path}: {e}")

        return semantic_models

    def parse_directory(self, directory: Path) -> list[SemanticModel]:
        """Parse all YAML files in a directory.

        Args:
            directory: Directory containing YAML files.

        Returns:
            List of all parsed semantic models.
        """
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        semantic_models = []

        for yaml_file in directory.glob("*.yml"):
            try:
                models = self.parse_file(yaml_file)
                semantic_models.extend(models)
            except Exception as e:
                if self.strict_mode:
                    raise
                print(f"Warning: Failed to parse {yaml_file}: {e}")

        for yaml_file in directory.glob("*.yaml"):
            try:
                models = self.parse_file(yaml_file)
                semantic_models.extend(models)
            except Exception as e:
                if self.strict_mode:
                    raise
                print(f"Warning: Failed to parse {yaml_file}: {e}")

        return semantic_models

    def _parse_semantic_model(self, model_data: dict[str, Any]) -> SemanticModel:
        """Parse a single semantic model from dictionary data.

        Args:
            model_data: Dictionary containing semantic model data.

        Returns:
            Parsed semantic model.

        Raises:
            ValidationError: If the model structure is invalid.
        """
        try:
            # Validate required fields
            if 'name' not in model_data:
                raise ValueError("Missing required field 'name' in semantic model")
            if 'model' not in model_data:
                raise ValueError("Missing required field 'model' in semantic model")

            # Parse config section
            config = None
            if 'config' in model_data:
                config_data = model_data['config']
                config_meta = None
                if 'meta' in config_data:
                    meta_data = config_data['meta']
                    config_meta = ConfigMeta(
                        domain=meta_data.get('domain'),
                        owner=meta_data.get('owner'),
                        contains_pii=meta_data.get('contains_pii'),
                        update_frequency=meta_data.get('update_frequency'),
                    )
                config = Config(meta=config_meta)

            # Parse entities
            entities = []
            for entity_data in model_data.get('entities', []):
                try:
                    entity = Entity(
                        name=entity_data['name'],
                        type=entity_data['type'],
                        expr=entity_data.get('expr'),
                        description=entity_data.get('description'),
                    )
                    entities.append(entity)
                except Exception as e:
                    raise ValueError(f"Error parsing entity '{entity_data.get('name', 'unknown')}': {e}") from e

            # Parse dimensions
            dimensions = []
            for dim_data in model_data.get('dimensions', []):
                try:
                    # Handle complex expressions (multiline)
                    expr = dim_data.get('expr')
                    if expr and isinstance(expr, str):
                        # Clean up multiline expressions
                        expr = expr.strip()
                    
                    dimension = Dimension(
                        name=dim_data['name'],
                        type=DimensionType(dim_data['type']),
                        expr=expr,
                        description=dim_data.get('description'),
                        label=dim_data.get('label'),
                        type_params=dim_data.get('type_params'),
                    )
                    dimensions.append(dimension)
                except Exception as e:
                    raise ValueError(f"Error parsing dimension '{dim_data.get('name', 'unknown')}': {e}") from e

            # Parse measures
            measures = []
            for measure_data in model_data.get('measures', []):
                try:
                    # Handle complex expressions (multiline)
                    expr = measure_data.get('expr')
                    if expr and isinstance(expr, str):
                        # Clean up multiline expressions
                        expr = expr.strip()
                    
                    measure = Measure(
                        name=measure_data['name'],
                        agg=AggregationType(measure_data['agg']),
                        expr=expr,
                        description=measure_data.get('description'),
                        label=measure_data.get('label'),
                        create_metric=measure_data.get('create_metric'),
                    )
                    measures.append(measure)
                except Exception as e:
                    raise ValueError(f"Error parsing measure '{measure_data.get('name', 'unknown')}': {e}") from e

            return SemanticModel(
                name=model_data['name'],
                model=model_data['model'],
                description=model_data.get('description'),
                config=config,
                defaults=model_data.get('defaults'),
                entities=entities,
                dimensions=dimensions,
                measures=measures,
            )
            
        except Exception as e:
            model_name = model_data.get('name', 'unknown')
            raise ValueError(f"Error parsing semantic model '{model_name}': {e}") from e
