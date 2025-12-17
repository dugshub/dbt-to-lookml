"""Parser for dbt metric YAML files.

This module provides parsing functionality for dbt metric definitions,
supporting all metric types (simple, ratio, derived, conversion) and
handling multiple YAML file formats.

Example:
    Basic usage:

    >>> from pathlib import Path
    >>> from dbt_to_lookml.parsers.dbt_metrics import DbtMetricParser
    >>>
    >>> parser = DbtMetricParser(strict_mode=True)
    >>> metrics = parser.parse_directory(Path("metrics/"))
    >>> print(f"Found {len(metrics)} metrics")

    Parsing with semantic models for entity resolution:

    >>> from dbt_to_lookml.parsers.dbt import DbtParser
    >>> from dbt_to_lookml.parsers.dbt_metrics import (
    ...     DbtMetricParser,
    ...     resolve_primary_entity,
    ... )
    >>>
    >>> # Parse semantic models and metrics
    >>> model_parser = DbtParser()
    >>> models = model_parser.parse_directory(Path("semantic_models/"))
    >>>
    >>> metric_parser = DbtMetricParser()
    >>> metrics = metric_parser.parse_directory(Path("metrics/"))
    >>>
    >>> # Resolve primary entities
    >>> for metric in metrics:
    ...     entity = resolve_primary_entity(metric, models)
    ...     print(f"{metric.name} -> {entity}")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from dbt_to_lookml.interfaces.parser import Parser
from dbt_to_lookml.schemas.config import (
    Config,
    ConfigMeta,
    PopComparison,
    PopConfig,
    PopGrain,
    PopWindow,
)
from dbt_to_lookml.schemas.semantic_layer import (
    ConversionMetricParams,
    DerivedMetricParams,
    Metric,
    MetricReference,
    RatioMetricParams,
    SemanticModel,
    SimpleMetricParams,
)


class DbtMetricParser(Parser):
    """Parser for dbt metric YAML files.

    Parses metric definitions from YAML files and converts them to Metric
    schema objects. Supports all metric types: simple, ratio, derived, conversion.
    Validates metric structure and resolves primary entities.

    The parser supports three YAML formats:
    - Standard: `metrics: [list of metrics]`
    - Direct: Single metric object (auto-wrapped in list)
    - Top-level: List of metrics at root level

    When semantic_models are provided, the parser can perform early validation
    of entity connectivity to ensure metrics can be successfully generated.

    Attributes:
        strict_mode: If True, validation errors raise exceptions.
            If False, warnings logged.
        semantic_models: Optional list of semantic models for entity
            connectivity validation.

    Example:
        >>> parser = DbtMetricParser(strict_mode=True)
        >>> metrics = parser.parse_file(Path("metrics/revenue.yml"))
        >>> assert len(metrics) > 0
        >>> assert metrics[0].type in ["simple", "ratio", "derived", "conversion"]

        With validation:
        >>> from dbt_to_lookml.parsers.dbt import DbtParser
        >>> model_parser = DbtParser()
        >>> models = model_parser.parse_directory(Path("semantic_models/"))
        >>> metric_parser = DbtMetricParser(strict_mode=True, semantic_models=models)
        >>> metrics = metric_parser.parse_directory(Path("metrics/"))
    """

    def __init__(
        self,
        strict_mode: bool = False,
        semantic_models: list[SemanticModel] | None = None,
    ):
        """Initialize parser with optional semantic models for validation.

        Args:
            strict_mode: If True, validation errors raise exceptions.
                If False, warnings logged.
            semantic_models: Optional list of semantic models for entity
                connectivity validation.
        """
        super().__init__(strict_mode=strict_mode)
        self.semantic_models = semantic_models or []

    def parse_file(self, file_path: Path) -> list[Metric]:
        """Parse a single metric YAML file.

        Supports multiple YAML formats:
        - metrics: [list of metrics]
        - Direct metric object (single)
        - Top-level list of metrics

        Args:
            file_path: Path to YAML file containing metrics

        Returns:
            List of parsed Metric objects

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is malformed
            ValidationError: If metric structure is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = self.read_yaml(file_path)

        if not content:
            return []

        metrics = []

        # Handle both dict (metrics key or single metric) and list formats
        if isinstance(content, dict):
            if "metrics" in content:
                metrics_data = content["metrics"]
            elif "semantic_models" in content and "name" not in content:
                # This is a semantic models file, not a metrics file
                return []
            else:
                # Assume the entire content is a single metric
                metrics_data = [content]
        elif isinstance(content, list):
            metrics_data = content
        else:
            raise ValueError(f"Invalid YAML structure in {file_path}")

        for metric_data in metrics_data:
            try:
                metric = self._parse_metric(metric_data)
                metrics.append(metric)
            except (ValidationError, ValueError) as e:
                self.handle_error(e, f"Skipping invalid metric in {file_path}")

        return metrics

    def parse_directory(self, directory: Path, validate: bool = True) -> list[Metric]:
        """Recursively parse all metric files in directory.

        Scans for *.yml and *.yaml files, handling nested directories.
        Uses handle_error() for lenient vs strict error handling.

        When semantic_models are provided and validate=True, performs
        entity connectivity validation after parsing all metrics.

        Args:
            directory: Directory containing metric YAML files
            validate: If True and semantic_models provided, run connectivity validation

        Returns:
            List of all parsed Metric objects

        Raises:
            ValidationError: If validation fails in strict_mode
        """
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        metrics = []

        for yaml_file in directory.rglob("*.yml"):
            try:
                file_metrics = self.parse_file(yaml_file)
                metrics.extend(file_metrics)
            except Exception as e:
                self.handle_error(e, f"Failed to parse {yaml_file}")

        for yaml_file in directory.rglob("*.yaml"):
            try:
                file_metrics = self.parse_file(yaml_file)
                metrics.extend(file_metrics)
            except Exception as e:
                self.handle_error(e, f"Failed to parse {yaml_file}")

        # Early validation if semantic models provided
        if validate and self.semantic_models:
            self._validate_metrics(metrics)

        return metrics

    def _validate_metrics(self, metrics: list[Metric]) -> None:
        """Validate metrics for entity connectivity.

        Performs entity connectivity validation using the
        EntityConnectivityValidator. In strict mode, raises ValidationError on
        errors. In lenient mode, logs warnings.

        Args:
            metrics: List of metrics to validate

        Raises:
            ValidationError: If validation fails in strict_mode
        """
        from rich.console import Console

        from dbt_to_lookml.validation import (
            EntityConnectivityValidator,
            ValidationError,
        )

        console = Console()
        validator = EntityConnectivityValidator(self.semantic_models)
        result = validator.validate_metrics(metrics)

        if result.has_errors():
            if self.strict_mode:
                console.print(result.format_report())
                error_count = len([i for i in result.issues if i.severity == "error"])
                raise ValidationError(
                    f"Metric validation failed with {error_count} errors"
                )
            else:
                console.print("[yellow]Validation warnings:[/yellow]")
                console.print(result.format_report())

        if result.has_warnings() and not result.has_errors():
            console.print("[yellow]Validation warnings:[/yellow]")
            console.print(result.format_report())

    def validate(self, content: dict[str, Any]) -> bool:
        """Validate that content contains valid metric structure.

        Checks for:
        - 'metrics' key or direct metric structure
        - Required fields: name, type, type_params
        - Valid metric type value

        Args:
            content: Parsed YAML content

        Returns:
            True if valid metric structure, False otherwise
        """
        if not content:
            return False

        # Check for metrics key or direct metric structure
        if isinstance(content, dict):
            if "metrics" in content:
                metrics = content["metrics"]
                if not isinstance(metrics, list):
                    return False
                # Check first metric has required fields
                if metrics and len(metrics) > 0:
                    return self._validate_metric_structure(metrics[0])
            else:
                # Direct metric structure
                return self._validate_metric_structure(content)
        elif isinstance(content, list):
            # List of metrics
            if content and len(content) > 0:
                return self._validate_metric_structure(content[0])

        return False

    def _validate_metric_structure(self, metric: dict[str, Any]) -> bool:
        """Validate single metric dictionary has required fields.

        Args:
            metric: Metric dictionary to validate

        Returns:
            True if has required fields, False otherwise
        """
        # Required fields for a metric
        required_fields = ["name", "type", "type_params"]
        has_required = all(field in metric for field in required_fields)

        if not has_required:
            return False

        # Validate metric type is one of the supported types
        valid_types = ["simple", "ratio", "derived", "conversion"]
        return metric.get("type") in valid_types

    def _parse_metric_pop_config(
        self,
        pop_data: dict[str, Any],
        metric_type: str,
    ) -> PopConfig | None:
        """Parse PoP configuration from metric meta.

        For metrics, PoP is only supported on simple metrics since they
        generate direct aggregate measures. Ratio and derived metrics
        generate type: number measures which have PoP limitations.

        Args:
            pop_data: The pop config dict from metric meta.
            metric_type: The type of metric (simple, ratio, derived, conversion).

        Returns:
            Parsed PopConfig or None if not enabled or not supported.
        """
        if not pop_data.get("enabled", False):
            return None

        # Only support PoP on simple metrics for now
        if metric_type != "simple":
            # Log warning but don't fail - user may be experimenting
            return None

        # Parse enum values with defaults
        grains = [PopGrain(g) for g in pop_data.get("grains", ["mtd", "ytd"])]
        comparisons = [
            PopComparison(c) for c in pop_data.get("comparisons", ["pp", "py"])
        ]
        windows = [PopWindow(w) for w in pop_data.get("windows", ["month"])]

        return PopConfig(
            enabled=True,
            grains=grains,
            comparisons=comparisons,
            windows=windows,
            format=pop_data.get("format"),
            date_dimension=pop_data.get("date_dimension"),
            date_filter=pop_data.get("date_filter"),
        )

    def _parse_metric(self, metric_data: dict[str, Any]) -> Metric:
        """Parse single metric from dictionary data.

        Internal method that handles type-specific params construction
        and delegates to Pydantic validation.

        Args:
            metric_data: Dictionary with metric fields

        Returns:
            Validated Metric object

        Raises:
            ValidationError: If metric structure invalid
            ValueError: If metric type unsupported or required fields missing
        """
        try:
            # Validate required fields
            if "name" not in metric_data:
                raise ValueError("Missing required field 'name' in metric")
            if "type" not in metric_data:
                raise ValueError("Missing required field 'type' in metric")
            if "type_params" not in metric_data:
                raise ValueError("Missing required field 'type_params' in metric")

            # Parse type-specific parameters
            metric_type = metric_data["type"]
            params_data = metric_data["type_params"]
            type_params = self._parse_type_params(metric_type, params_data)

            # Extract meta from config.meta (dbt convention) or top-level meta
            meta = None
            if "config" in metric_data and isinstance(metric_data["config"], dict):
                meta = metric_data["config"].get("meta")
            elif "meta" in metric_data:
                meta = metric_data.get("meta")

            # Extract filter (list of filter expressions)
            metric_filter = metric_data.get("filter")

            # Parse PoP config from meta if present
            metric_config = None
            if meta and isinstance(meta, dict) and "pop" in meta:
                pop_config = self._parse_metric_pop_config(meta["pop"], metric_type)
                if pop_config:
                    metric_config = Config(meta=ConfigMeta(pop=pop_config))

            # Construct metric object
            return Metric(
                name=metric_data["name"],
                type=metric_type,
                type_params=type_params,
                label=metric_data.get("label"),
                description=metric_data.get("description"),
                filter=metric_filter,
                meta=meta,
                config=metric_config,
            )

        except Exception as e:
            metric_name = metric_data.get("name", "unknown")
            raise ValueError(f"Error parsing metric '{metric_name}': {e}") from e

    def _parse_type_params(
        self,
        metric_type: str,
        params_data: dict[str, Any],
    ) -> (
        SimpleMetricParams
        | RatioMetricParams
        | DerivedMetricParams
        | ConversionMetricParams
    ):
        """Parse type-specific parameters based on metric type.

        Constructs appropriate TypeParams subclass:
        - simple -> SimpleMetricParams
        - ratio -> RatioMetricParams
        - derived -> DerivedMetricParams
        - conversion -> ConversionMetricParams

        Args:
            metric_type: One of 'simple', 'ratio', 'derived', 'conversion'
            params_data: Dictionary with type-specific params

        Returns:
            Appropriate MetricTypeParams subclass instance

        Raises:
            ValueError: If metric_type is unknown
            ValidationError: If params don't match expected structure
        """
        if metric_type == "simple":
            return SimpleMetricParams(**params_data)
        elif metric_type == "ratio":
            return RatioMetricParams(**params_data)
        elif metric_type == "derived":
            # Handle metrics list which needs to be converted to MetricReference objects
            if "metrics" in params_data:
                metric_refs = [MetricReference(**ref) for ref in params_data["metrics"]]
                params_data = {**params_data, "metrics": metric_refs}
            return DerivedMetricParams(**params_data)
        elif metric_type == "conversion":
            return ConversionMetricParams(**params_data)
        else:
            valid_types = ["simple", "ratio", "derived", "conversion"]
            raise ValueError(
                f"Unknown metric type '{metric_type}'. "
                f"Supported types: {', '.join(valid_types)}"
            )


# ============================================================================
# Utility Functions
# ============================================================================


def resolve_primary_entity(metric: Metric, semantic_models: list[SemanticModel]) -> str:
    """Determine primary entity for metric.

    Resolution priority:
    1. Explicit meta.primary_entity (highest priority)
    2. Infer from denominator for ratio metrics
    3. Raise error requiring explicit specification

    Inference algorithm for ratio metrics:
    - Extract denominator measure name
    - Find semantic model containing that measure
    - Return that model's primary entity name

    Args:
        metric: Metric object to resolve
        semantic_models: All semantic models for lookup

    Returns:
        Primary entity name (e.g., 'search', 'user', 'rental')

    Raises:
        ValueError: If can't resolve (missing meta, can't infer)

    Example:
        >>> from dbt_to_lookml.schemas import Metric, RatioMetricParams
        >>> metric = Metric(
        ...     name="conversion_rate",
        ...     type="ratio",
        ...     type_params=RatioMetricParams(
        ...         numerator="rental_count",
        ...         denominator="search_count"
        ...     )
        ... )
        >>> entity = resolve_primary_entity(metric, semantic_models)
        >>> # Returns the primary entity from the model containing search_count
    """
    # Priority 1: Explicit primary_entity in meta
    if metric.primary_entity:
        return metric.primary_entity

    # Priority 2: Infer from denominator for ratio metrics
    if metric.type == "ratio" and isinstance(metric.type_params, RatioMetricParams):
        denominator = metric.type_params.denominator
        denominator_model = find_measure_model(denominator, semantic_models)

        if denominator_model is None:
            raise ValueError(
                f"Cannot infer primary entity for metric '{metric.name}': "
                f"denominator measure '{denominator}' not found in any semantic model. "
                f"Please specify explicitly in meta:\n"
                f"  meta:\n"
                f"    primary_entity: <entity_name>"
            )

        # Extract primary entity from the model
        primary_entities = [
            e for e in denominator_model.entities if e.type == "primary"
        ]
        if not primary_entities:
            raise ValueError(
                f"Cannot infer primary entity for metric '{metric.name}': "
                f"denominator measure '{denominator}' is in model "
                f"'{denominator_model.name}' which has no primary entity. "
                f"Please specify explicitly in meta:\n"
                f"  meta:\n"
                f"    primary_entity: <entity_name>"
            )

        return primary_entities[0].name

    # Priority 3: Cannot infer - require explicit specification
    raise ValueError(
        f"Cannot determine primary entity for metric '{metric.name}'. "
        f"For {metric.type} metrics, primary entity must be specified "
        f"explicitly in meta:\n"
        f"  meta:\n"
        f"    primary_entity: <entity_name>"
    )


def extract_measure_dependencies(metric: Metric) -> set[str]:
    """Extract all measure names referenced by metric.

    Handles each metric type:
    - simple: {type_params.measure}
    - ratio: {numerator, denominator}
    - derived: Empty set (references metrics, not measures)
    - conversion: Extracts from conversion_type_params

    Args:
        metric: Metric to extract dependencies from

    Returns:
        Set of measure names (strings)

    Example:
        >>> from dbt_to_lookml.schemas import Metric, RatioMetricParams
        >>> metric = Metric(
        ...     name="revenue_per_user",
        ...     type="ratio",
        ...     type_params=RatioMetricParams(
        ...         numerator="total_revenue",
        ...         denominator="user_count"
        ...     )
        ... )
        >>> deps = extract_measure_dependencies(metric)
        >>> assert deps == {"total_revenue", "user_count"}
    """
    if metric.type == "simple" and isinstance(metric.type_params, SimpleMetricParams):
        return {metric.type_params.measure}

    elif metric.type == "ratio" and isinstance(metric.type_params, RatioMetricParams):
        return {metric.type_params.numerator, metric.type_params.denominator}

    elif metric.type == "derived":
        # Derived metrics reference other metrics, not measures directly
        return set()

    elif metric.type == "conversion" and isinstance(
        metric.type_params, ConversionMetricParams
    ):
        # Extract measures from conversion_type_params
        conversion_params = metric.type_params.conversion_type_params
        measures = set()

        # Common conversion parameter patterns
        if "base_measure" in conversion_params:
            measures.add(conversion_params["base_measure"])
        if "conversion_measure" in conversion_params:
            measures.add(conversion_params["conversion_measure"])

        return measures

    return set()


def find_measure_model(
    measure_name: str, semantic_models: list[SemanticModel]
) -> SemanticModel | None:
    """Find which semantic model contains a measure.

    Args:
        measure_name: Name of measure to find
        semantic_models: List of semantic models to search

    Returns:
        SemanticModel containing the measure, or None if not found

    Example:
        >>> model = find_measure_model("revenue", semantic_models)
        >>> if model:
        ...     print(f"Found in model: {model.name}")
    """
    for model in semantic_models:
        for measure in model.measures:
            if measure.name == measure_name:
                return model
    return None
