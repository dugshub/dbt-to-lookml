"""Parser for dbt semantic model YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from dbt_to_lookml.interfaces.parser import Parser
from dbt_to_lookml.schemas.config import (
    Config,
    ConfigMeta,
    Hierarchy,
    PopConfig,
    PopGrain,
    PopComparison,
    PopWindow,
)
from dbt_to_lookml.schemas.semantic_layer import (
    Dimension,
    Entity,
    Measure,
    SemanticModel,
)
from dbt_to_lookml.types import (
    AggregationType,
    DimensionType,
)


class DbtParser(Parser):
    """Parser for dbt semantic model YAML files."""

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

        content = self.read_yaml(file_path)

        if not content:
            return []

        semantic_models = []

        # Handle both single model and list of models
        if isinstance(content, dict):
            if "semantic_models" in content:
                models_data = content["semantic_models"]
            elif "metrics" in content and "name" not in content:
                # This is a metrics-only file, not a semantic model file
                return []
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

    def parse_directory(self, directory: Path) -> list[SemanticModel]:
        """Parse all YAML files recursively in a directory.

        Args:
            directory: Directory containing YAML files (searched recursively).

        Returns:
            List of all parsed semantic models.
        """
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        semantic_models = []

        for yaml_file in directory.rglob("*.yml"):
            try:
                models = self.parse_file(yaml_file)
                semantic_models.extend(models)
            except Exception as e:
                self.handle_error(e, f"Failed to parse {yaml_file}")

        for yaml_file in directory.rglob("*.yaml"):
            try:
                models = self.parse_file(yaml_file)
                semantic_models.extend(models)
            except Exception as e:
                self.handle_error(e, f"Failed to parse {yaml_file}")

        return semantic_models

    def validate(self, content: dict[str, Any]) -> bool:
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
            if "semantic_models" in content:
                models = content["semantic_models"]
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

    def _validate_model_structure(self, model: dict[str, Any]) -> bool:
        """Validate a single model structure has required fields.

        Args:
            model: Model dictionary to validate.

        Returns:
            True if valid structure, False otherwise.
        """
        # Required fields for a semantic model
        return "name" in model and "model" in model

    def _parse_pop_config(
        self,
        pop_data: dict[str, Any],
        model_data: dict[str, Any],
    ) -> PopConfig | None:
        """Parse PoP configuration from measure meta with resolution.

        Resolves date_dimension and date_filter through hierarchy:
        1. Measure-level pop config
        2. Model-level pop config
        3. Model defaults.agg_time_dimension

        Args:
            pop_data: The pop config dict from measure meta.
            model_data: The full model data for fallback resolution.

        Returns:
            Parsed PopConfig or None if not enabled.
        """
        if not pop_data.get("enabled", False):
            return None

        # Parse enum values
        grains = [
            PopGrain(g) for g in pop_data.get("grains", ["mtd", "ytd"])
        ]
        comparisons = [
            PopComparison(c) for c in pop_data.get("comparisons", ["pp", "py"])
        ]
        windows = [
            PopWindow(w) for w in pop_data.get("windows", ["month"])
        ]

        # Get explicit values from measure config
        date_dimension = pop_data.get("date_dimension")
        date_filter = pop_data.get("date_filter")

        # Resolve date_dimension if not specified
        if not date_dimension:
            # Try model-level pop config
            model_meta = model_data.get("config", {}).get("meta", {})
            model_pop = model_meta.get("pop", {})
            date_dimension = model_pop.get("date_dimension")

            # Fall back to defaults.agg_time_dimension
            if not date_dimension:
                defaults = model_data.get("defaults", {})
                date_dimension = defaults.get("agg_time_dimension")

        # Derive date_filter if not specified
        if not date_filter and date_dimension:
            date_filter = f"{date_dimension}_date"

        return PopConfig(
            enabled=True,
            grains=grains,
            comparisons=comparisons,
            windows=windows,
            format=pop_data.get("format"),
            date_dimension=date_dimension,
            date_filter=date_filter,
        )

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
            if "name" not in model_data:
                raise ValueError("Missing required field 'name' in semantic model")
            if "model" not in model_data:
                raise ValueError("Missing required field 'model' in semantic model")

            # Parse config section
            config = None
            if "config" in model_data:
                config_data = model_data["config"]
                config_meta = None
                if "meta" in config_data:
                    meta_data = config_data["meta"]
                    config_meta = ConfigMeta(
                        domain=meta_data.get("domain"),
                        owner=meta_data.get("owner"),
                        contains_pii=meta_data.get("contains_pii"),
                        update_frequency=meta_data.get("update_frequency"),
                        convert_tz=meta_data.get("convert_tz"),
                        hidden=meta_data.get("hidden"),
                        bi_field=meta_data.get("bi_field"),
                        time_dimension_group_label=meta_data.get(
                            "time_dimension_group_label"
                        ),
                    )
                config = Config(meta=config_meta)

            # Parse entities
            entities = []
            for entity_data in model_data.get("entities", []):
                try:
                    # Parse entity config if present
                    entity_config = None
                    if "config" in entity_data:
                        config_data = entity_data["config"]
                        if "meta" in config_data:
                            meta_data = config_data["meta"]
                            entity_config_meta = ConfigMeta(
                                join_cardinality=meta_data.get("join_cardinality"),
                            )
                            entity_config = Config(meta=entity_config_meta)

                    entity = Entity(
                        name=entity_data["name"],
                        type=entity_data["type"],
                        expr=entity_data.get("expr"),
                        description=entity_data.get("description"),
                        config=entity_config,
                    )
                    entities.append(entity)
                except Exception as e:
                    entity_name = entity_data.get("name", "unknown")
                    raise ValueError(
                        f"Error parsing entity '{entity_name}': {e}"
                    ) from e

            # Parse dimensions
            dimensions = []
            for dim_data in model_data.get("dimensions", []):
                try:
                    # Handle complex expressions (multiline)
                    expr = dim_data.get("expr")
                    if expr and isinstance(expr, str):
                        # Clean up multiline expressions
                        expr = expr.strip()

                    # Parse config with hierarchy if present
                    dim_config = None
                    if "config" in dim_data:
                        config_data = dim_data["config"]
                        config_meta = None
                        if "meta" in config_data:
                            meta_data = config_data["meta"]
                            hierarchy = None
                            # Support both nested hierarchy and flat
                            # subject/entity/category
                            if "hierarchy" in meta_data:
                                hierarchy_data = meta_data["hierarchy"]
                                hierarchy = Hierarchy(
                                    entity=hierarchy_data.get("entity"),
                                    category=hierarchy_data.get("category"),
                                    subcategory=hierarchy_data.get("subcategory"),
                                )
                            elif (
                                "entity" in meta_data
                                or "subject" in meta_data
                                or "category" in meta_data
                            ):
                                # Flat structure: meta.subject/entity and
                                # meta.category. Use 'subject' if present,
                                # otherwise fall back to 'entity'
                                entity_value = meta_data.get(
                                    "subject"
                                ) or meta_data.get("entity")
                                hierarchy = Hierarchy(
                                    entity=entity_value,
                                    category=meta_data.get("category"),
                                    subcategory=meta_data.get("subcategory"),
                                )
                            elif (
                                "entity" in meta_data
                                or "subject" in meta_data
                                or "category" in meta_data
                            ):
                                # Flat structure: meta.subject/entity and
                                # meta.category. Use 'subject' if present,
                                # otherwise fall back to 'entity'
                                entity_value = meta_data.get(
                                    "subject"
                                ) or meta_data.get("entity")
                                hierarchy = Hierarchy(
                                    entity=entity_value,
                                    category=meta_data.get("category"),
                                    subcategory=meta_data.get("subcategory"),
                                )

                            # Parse timezone_variant if present
                            timezone_variant = None
                            if "timezone_variant" in meta_data:
                                from dbt_to_lookml.schemas.config import TimezoneVariant
                                tz_var_data = meta_data["timezone_variant"]

                                # Validate required fields exist
                                required_fields = ["canonical_name", "variant", "is_primary"]
                                missing_fields = [f for f in required_fields if f not in tz_var_data]

                                if missing_fields:
                                    dim_name = dim_data.get("name", "unknown")
                                    error_msg = (
                                        f"Dimension '{dim_name}' has malformed timezone_variant config. "
                                        f"Missing required fields: {', '.join(missing_fields)}. "
                                        f"Required fields are: {', '.join(required_fields)}"
                                    )
                                    if self.strict_mode:
                                        raise ValueError(error_msg)
                                    else:
                                        import warnings
                                        warnings.warn(error_msg)
                                    # Skip this timezone_variant config and continue
                                    timezone_variant = None
                                else:
                                    try:
                                        timezone_variant = TimezoneVariant(
                                            canonical_name=tz_var_data["canonical_name"],
                                            variant=tz_var_data["variant"],
                                            is_primary=tz_var_data["is_primary"],
                                        )
                                    except Exception as e:
                                        dim_name = dim_data.get("name", "unknown")
                                        error_msg = f"Dimension '{dim_name}' has invalid timezone_variant config: {e}"
                                        if self.strict_mode:
                                            raise ValueError(error_msg) from e
                                        else:
                                            import warnings
                                            warnings.warn(error_msg)
                                        timezone_variant = None

                            config_meta = ConfigMeta(
                                domain=meta_data.get("domain"),
                                owner=meta_data.get("owner"),
                                contains_pii=meta_data.get("contains_pii"),
                                update_frequency=meta_data.get("update_frequency"),
                                # Set both flat fields and hierarchy for
                                # backward compatibility
                                subject=meta_data.get("subject"),
                                category=meta_data.get("category"),
                                hierarchy=hierarchy,
                                convert_tz=meta_data.get("convert_tz"),
                                hidden=meta_data.get("hidden"),
                                bi_field=meta_data.get("bi_field"),
                                time_dimension_group_label=meta_data.get(
                                    "time_dimension_group_label"
                                ),
                                timezone_variant=timezone_variant,
                            )
                        dim_config = Config(meta=config_meta)

                    dimension = Dimension(
                        name=dim_data["name"],
                        type=DimensionType(dim_data["type"]),
                        expr=expr,
                        description=dim_data.get("description"),
                        label=dim_data.get("label"),
                        type_params=dim_data.get("type_params"),
                        config=dim_config,
                    )
                    dimensions.append(dimension)
                except Exception as e:
                    dim_name = dim_data.get("name", "unknown")
                    raise ValueError(
                        f"Error parsing dimension '{dim_name}': {e}"
                    ) from e

            # Parse measures
            measures = []
            for measure_data in model_data.get("measures", []):
                try:
                    # Handle complex expressions (multiline)
                    expr = measure_data.get("expr")
                    if expr and isinstance(expr, str):
                        # Clean up multiline expressions
                        expr = expr.strip()

                    # Parse config with hierarchy if present
                    measure_config = None
                    if "config" in measure_data:
                        config_data = measure_data["config"]
                        config_meta = None
                        if "meta" in config_data:
                            meta_data = config_data["meta"]
                            hierarchy = None
                            # Support both nested hierarchy and flat
                            # subject/entity/category
                            if "hierarchy" in meta_data:
                                hierarchy_data = meta_data["hierarchy"]
                                hierarchy = Hierarchy(
                                    entity=hierarchy_data.get("entity"),
                                    category=hierarchy_data.get("category"),
                                    subcategory=hierarchy_data.get("subcategory"),
                                )
                            elif (
                                "entity" in meta_data
                                or "subject" in meta_data
                                or "category" in meta_data
                            ):
                                # Flat structure: meta.subject/entity and
                                # meta.category. Use 'subject' if present,
                                # otherwise fall back to 'entity'
                                entity_value = meta_data.get(
                                    "subject"
                                ) or meta_data.get("entity")
                                hierarchy = Hierarchy(
                                    entity=entity_value,
                                    category=meta_data.get("category"),
                                    subcategory=meta_data.get("subcategory"),
                                )
                            elif (
                                "entity" in meta_data
                                or "subject" in meta_data
                                or "category" in meta_data
                            ):
                                # Flat structure: meta.subject/entity and
                                # meta.category. Use 'subject' if present,
                                # otherwise fall back to 'entity'
                                entity_value = meta_data.get(
                                    "subject"
                                ) or meta_data.get("entity")
                                hierarchy = Hierarchy(
                                    entity=entity_value,
                                    category=meta_data.get("category"),
                                    subcategory=meta_data.get("subcategory"),
                                )

                            # Parse pop config if present
                            pop_config = None
                            if "pop" in meta_data:
                                pop_config = self._parse_pop_config(
                                    meta_data["pop"], model_data
                                )

                            config_meta = ConfigMeta(
                                domain=meta_data.get("domain"),
                                owner=meta_data.get("owner"),
                                contains_pii=meta_data.get("contains_pii"),
                                update_frequency=meta_data.get("update_frequency"),
                                # Set both flat fields and hierarchy for
                                # backward compatibility
                                subject=meta_data.get("subject"),
                                category=meta_data.get("category"),
                                hierarchy=hierarchy,
                                convert_tz=meta_data.get("convert_tz"),
                                hidden=meta_data.get("hidden"),
                                bi_field=meta_data.get("bi_field"),
                                time_dimension_group_label=meta_data.get(
                                    "time_dimension_group_label"
                                ),
                                pop=pop_config,
                            )
                        measure_config = Config(meta=config_meta)

                    measure = Measure(
                        name=measure_data["name"],
                        agg=AggregationType(measure_data["agg"]),
                        expr=expr,
                        description=measure_data.get("description"),
                        label=measure_data.get("label"),
                        create_metric=measure_data.get("create_metric"),
                        config=measure_config,
                    )
                    measures.append(measure)
                except Exception as e:
                    measure_name = measure_data.get("name", "unknown")
                    raise ValueError(
                        f"Error parsing measure '{measure_name}': {e}"
                    ) from e

            return SemanticModel(
                name=model_data["name"],
                model=model_data["model"],
                description=model_data.get("description"),
                config=config,
                defaults=model_data.get("defaults"),
                entities=entities,
                dimensions=dimensions,
                measures=measures,
            )

        except Exception as e:
            model_name = model_data.get("name", "unknown")
            raise ValueError(f"Error parsing semantic model '{model_name}': {e}") from e
