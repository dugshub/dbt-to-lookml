"""Parser for dbt semantic model YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import ValidationError

from dbt_to_lookml.interfaces.parser import Parser
from dbt_to_lookml.types import (
    AggregationType,
    DimensionType,
)
from dbt_to_lookml.schemas import (
    Config,
    ConfigMeta,
    Dimension,
    Entity,
    Hierarchy,
    Measure,
    SemanticModel,
)


class DbtParser(Parser):
    """Parser for dbt semantic model YAML files."""

    def parse_file(self, file_path: Path) -> List[SemanticModel]:
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

        content = self.read_yaml(file_path)

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
                self.handle_error(e, f"Skipping invalid model in {file_path}")

        return semantic_models

    def parse_directory(self, directory: Path) -> List[SemanticModel]:
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
                self.handle_error(e, f"Failed to parse {yaml_file}")

        for yaml_file in directory.glob("*.yaml"):
            try:
                models = self.parse_file(yaml_file)
                semantic_models.extend(models)
            except Exception as e:
                self.handle_error(e, f"Failed to parse {yaml_file}")

        return semantic_models

    def validate(self, content: Dict[str, Any]) -> bool:
        """Validate that content contains valid dbt semantic model structure.

        Args:
            content: Parsed YAML content to validate.

        Returns:
            True if valid dbt semantic model structure, False otherwise.
        """
        if not content:
            return False

        # Check for semantic_models key or direct model structure
        if isinstance(content, dict):
            if 'semantic_models' in content:
                models = content['semantic_models']
                if not isinstance(models, list):
                    return False
                # Check first model has required fields
                if models and len(models) > 0:
                    return self._validate_model_structure(models[0])
            else:
                # Direct model structure
                return self._validate_model_structure(content)
        elif isinstance(content, list):
            # List of models
            if content and len(content) > 0:
                return self._validate_model_structure(content[0])

        return False

    def _validate_model_structure(self, model: Dict[str, Any]) -> bool:
        """Validate a single model structure has required fields.

        Args:
            model: Model dictionary to validate.

        Returns:
            True if valid structure, False otherwise.
        """
        # Required fields for a semantic model
        return 'name' in model and 'model' in model

    def _parse_semantic_model(self, model_data: Dict[str, Any]) -> SemanticModel:
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

                    # Parse config with hierarchy if present
                    dim_config = None
                    if 'config' in dim_data:
                        config_data = dim_data['config']
                        config_meta = None
                        if 'meta' in config_data:
                            meta_data = config_data['meta']
                            hierarchy = None
                            # Support both nested hierarchy and flat entity/category
                            if 'hierarchy' in meta_data:
                                hierarchy_data = meta_data['hierarchy']
                                hierarchy = Hierarchy(
                                    entity=hierarchy_data.get('entity'),
                                    category=hierarchy_data.get('category'),
                                    subcategory=hierarchy_data.get('subcategory'),
                                )
                            elif 'entity' in meta_data or 'category' in meta_data:
                                # Flat structure: meta.entity and meta.category
                                hierarchy = Hierarchy(
                                    entity=meta_data.get('entity'),
                                    category=meta_data.get('category'),
                                    subcategory=meta_data.get('subcategory'),
                                )
                            config_meta = ConfigMeta(
                                domain=meta_data.get('domain'),
                                owner=meta_data.get('owner'),
                                contains_pii=meta_data.get('contains_pii'),
                                update_frequency=meta_data.get('update_frequency'),
                                hierarchy=hierarchy,
                            )
                        dim_config = Config(meta=config_meta)

                    dimension = Dimension(
                        name=dim_data['name'],
                        type=DimensionType(dim_data['type']),
                        expr=expr,
                        description=dim_data.get('description'),
                        label=dim_data.get('label'),
                        type_params=dim_data.get('type_params'),
                        config=dim_config,
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

                    # Parse config with hierarchy if present
                    measure_config = None
                    if 'config' in measure_data:
                        config_data = measure_data['config']
                        config_meta = None
                        if 'meta' in config_data:
                            meta_data = config_data['meta']
                            hierarchy = None
                            # Support both nested hierarchy and flat entity/category
                            if 'hierarchy' in meta_data:
                                hierarchy_data = meta_data['hierarchy']
                                hierarchy = Hierarchy(
                                    entity=hierarchy_data.get('entity'),
                                    category=hierarchy_data.get('category'),
                                    subcategory=hierarchy_data.get('subcategory'),
                                )
                            elif 'entity' in meta_data or 'category' in meta_data:
                                # Flat structure: meta.entity and meta.category
                                hierarchy = Hierarchy(
                                    entity=meta_data.get('entity'),
                                    category=meta_data.get('category'),
                                    subcategory=meta_data.get('subcategory'),
                                )
                            config_meta = ConfigMeta(
                                domain=meta_data.get('domain'),
                                owner=meta_data.get('owner'),
                                contains_pii=meta_data.get('contains_pii'),
                                update_frequency=meta_data.get('update_frequency'),
                                hierarchy=hierarchy,
                            )
                        measure_config = Config(meta=config_meta)

                    measure = Measure(
                        name=measure_data['name'],
                        agg=AggregationType(measure_data['agg']),
                        expr=expr,
                        description=measure_data.get('description'),
                        label=measure_data.get('label'),
                        create_metric=measure_data.get('create_metric'),
                        config=measure_config,
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