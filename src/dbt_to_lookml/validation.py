"""Entity connectivity validation for cross-entity metrics.

This module provides validation infrastructure to ensure that metrics can be
successfully generated in LookML by verifying that all required measures are
reachable via the join graph from the metric's primary entity.

Key components:
- JoinGraph: BFS-based join traversal to determine model reachability
- EntityConnectivityValidator: Main validation orchestrator
- ValidationResult: Rich error/warning container with formatting
- ValidationError: Exception for validation failures

Usage:
    from dbt_to_lookml.validation import EntityConnectivityValidator
    from dbt_to_lookml.parsers.dbt import DbtParser

    # Parse semantic models
    parser = DbtParser()
    models = parser.parse_directory("semantic_models/")

    # Validate metrics
    validator = EntityConnectivityValidator(models)
    result = validator.validate_metrics(metrics)

    if result.has_errors():
        print(result.format_report())
        raise ValidationError("Metric validation failed")
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Literal

from dbt_to_lookml.schemas.semantic_layer import (
    ConversionMetricParams,
    Metric,
    RatioMetricParams,
    SemanticModel,
    SimpleMetricParams,
)

# ============================================================================
# Exceptions
# ============================================================================


class ValidationError(Exception):
    """Exception raised when metric validation fails in strict mode."""

    pass


# ============================================================================
# Helper Functions
# ============================================================================


def find_model_by_primary_entity(
    entity_name: str, models: list[SemanticModel]
) -> SemanticModel | None:
    """Find a semantic model that has a primary entity with the given name.

    Args:
        entity_name: Name of the entity to search for.
        models: List of semantic models to search within.

    Returns:
        The semantic model with the matching primary entity, or None if not found.

    Example:
        >>> models = [
        ...     SemanticModel(
        ...         name="users", entities=[Entity(name="user", type="primary")]
        ...     ),
        ...     SemanticModel(
        ...         name="rentals", entities=[Entity(name="rental", type="primary")]
        ...     )
        ... ]
        >>> model = find_model_by_primary_entity("user", models)
        >>> model.name
        'users'
    """
    for model in models:
        for entity in model.entities:
            if entity.name == entity_name and entity.type == "primary":
                return model
    return None


def extract_measure_dependencies(metric: Metric) -> set[str]:
    """Extract all measure names referenced by a metric.

    This function handles different metric types:
    - simple: Returns single measure from type_params.measure
    - ratio: Returns both numerator and denominator measures
    - conversion: Returns base_measure and conversion_measure
    - derived: Returns empty set (references metrics, not measures)

    Args:
        metric: The metric to extract dependencies from.

    Returns:
        Set of measure names referenced by this metric.

    Example:
        >>> metric = Metric(
        ...     name="conversion_rate",
        ...     type="ratio",
        ...     type_params=RatioMetricParams(
        ...         numerator="rental_count", denominator="search_count"
        ...     )
        ... )
        >>> extract_measure_dependencies(metric)
        {'rental_count', 'search_count'}
    """
    measure_names: set[str] = set()

    if isinstance(metric.type_params, SimpleMetricParams):
        measure_names.add(metric.type_params.measure)
    elif isinstance(metric.type_params, RatioMetricParams):
        measure_names.add(metric.type_params.numerator)
        measure_names.add(metric.type_params.denominator)
    elif isinstance(metric.type_params, ConversionMetricParams):
        # Extract measures from conversion_type_params dict
        conversion_params = metric.type_params.conversion_type_params
        if "base_measure" in conversion_params:
            measure_names.add(str(conversion_params["base_measure"]))
        if "conversion_measure" in conversion_params:
            measure_names.add(str(conversion_params["conversion_measure"]))
    # Derived metrics reference other metrics, not measures directly

    return measure_names


# ============================================================================
# Validation Data Structures
# ============================================================================


@dataclass
class ValidationIssue:
    """Container for a single validation issue (error or warning).

    Attributes:
        severity: Whether this is an error or warning.
        metric_name: Name of the metric with the issue.
        issue_type: Type of validation issue.
        message: Detailed error description.
        suggestions: List of actionable next steps.
        primary_entity: Optional context - primary entity for the metric.
        measure_name: Optional context - specific measure with issue.
        measure_model: Optional context - model containing the measure.
        available_entities: Optional context - list of valid entities.
    """

    severity: Literal["error", "warning"]
    metric_name: str
    issue_type: Literal[
        "unreachable_measure",
        "missing_measure",
        "missing_primary_entity",
        "invalid_primary_entity",
        "exceeds_hop_limit",
    ]
    message: str
    suggestions: list[str]
    # Context fields
    primary_entity: str | None = None
    measure_name: str | None = None
    measure_model: str | None = None
    available_entities: list[str] | None = None


@dataclass
class ValidationResult:
    """Container for all validation issues with query/formatting methods.

    This class accumulates validation issues and provides methods to query
    and format them for display.

    Example:
        >>> result = ValidationResult()
        >>> result.add_error(
        ...     metric_name="conversion_rate",
        ...     issue_type="unreachable_measure",
        ...     message="Measure not reachable",
        ...     suggestions=["Add foreign key relationship"]
        ... )
        >>> result.has_errors()
        True
        >>> print(result.format_report())
    """

    issues: list[ValidationIssue] = field(default_factory=list)

    def add_error(
        self,
        metric_name: str,
        issue_type: Literal[
            "unreachable_measure",
            "missing_measure",
            "missing_primary_entity",
            "invalid_primary_entity",
            "exceeds_hop_limit",
        ],
        message: str,
        suggestions: list[str],
        **context: Any,
    ) -> None:
        """Add an error to the validation result.

        Args:
            metric_name: Name of the metric with the error.
            issue_type: Type of validation error.
            message: Detailed error description.
            suggestions: List of actionable suggestions.
            **context: Additional context fields (primary_entity, measure_name, etc.).
        """
        self.issues.append(
            ValidationIssue(
                severity="error",
                metric_name=metric_name,
                issue_type=issue_type,
                message=message,
                suggestions=suggestions,
                primary_entity=context.get("primary_entity"),
                measure_name=context.get("measure_name"),
                measure_model=context.get("measure_model"),
                available_entities=context.get("available_entities"),
            )
        )

    def add_warning(
        self,
        metric_name: str,
        issue_type: Literal[
            "unreachable_measure",
            "missing_measure",
            "missing_primary_entity",
            "invalid_primary_entity",
            "exceeds_hop_limit",
        ],
        message: str,
        suggestions: list[str],
        **context: Any,
    ) -> None:
        """Add a warning to the validation result.

        Args:
            metric_name: Name of the metric with the warning.
            issue_type: Type of validation warning.
            message: Detailed warning description.
            suggestions: List of actionable suggestions.
            **context: Additional context fields (primary_entity, measure_name, etc.).
        """
        self.issues.append(
            ValidationIssue(
                severity="warning",
                metric_name=metric_name,
                issue_type=issue_type,
                message=message,
                suggestions=suggestions,
                primary_entity=context.get("primary_entity"),
                measure_name=context.get("measure_name"),
                measure_model=context.get("measure_model"),
                available_entities=context.get("available_entities"),
            )
        )

    def has_errors(self) -> bool:
        """Check if any errors exist.

        Returns:
            True if at least one error is present.
        """
        return any(issue.severity == "error" for issue in self.issues)

    def has_warnings(self) -> bool:
        """Check if any warnings exist.

        Returns:
            True if at least one warning is present.
        """
        return any(issue.severity == "warning" for issue in self.issues)

    def format_report(self) -> str:
        """Generate rich formatted output for validation issues.

        Returns:
            Formatted string with errors and warnings grouped by severity.

        Example:
            >>> result = ValidationResult()
            >>> result.add_error(...)
            >>> report = result.format_report()
            >>> print(report)
            [bold red]Validation Errors:[/bold red]
            ...
        """
        # Group issues by severity
        errors = [issue for issue in self.issues if issue.severity == "error"]
        warnings = [issue for issue in self.issues if issue.severity == "warning"]

        parts = []

        if errors:
            parts.append("\n[bold red]Validation Errors:[/bold red]\n")
            for issue in errors:
                parts.append(f"[red]✗[/red] {issue.message}")
                if issue.suggestions:
                    parts.append("\n[yellow]Suggestions:[/yellow]")
                    for suggestion in issue.suggestions:
                        parts.append(f"  • {suggestion}")
                parts.append("")  # Blank line

        if warnings:
            parts.append("\n[bold yellow]Validation Warnings:[/bold yellow]\n")
            for issue in warnings:
                parts.append(f"[yellow]⚠[/yellow] {issue.message}")
                if issue.suggestions:
                    parts.append("\n[dim]Suggestions:[/dim]")
                    for suggestion in issue.suggestions:
                        parts.append(f"  • {suggestion}")
                parts.append("")  # Blank line

        return "\n".join(parts)


# ============================================================================
# Join Graph
# ============================================================================


class JoinGraph:
    """BFS-based join graph builder for entity reachability analysis.

    This class builds a join graph from a base entity using breadth-first search
    traversal through foreign key relationships. It tracks which models and entities
    are reachable and the hop count (join depth) to reach them.

    The join graph respects a maximum hop limit (default 2) to prevent excessive
    join depth, which can cause performance issues in LookML.

    Attributes:
        base_entity: The starting entity for join traversal.
        all_models: List of all available semantic models.
        max_hops: Maximum join depth to traverse (default 2).
        reachable_models: Dictionary mapping model names to hop counts.
        reachable_entities: Dictionary mapping entity names to hop counts.

    Example:
        >>> graph = JoinGraph(base_entity="rental", all_models=models, max_hops=2)
        >>> graph.is_model_reachable("users")
        True
        >>> graph.get_hop_count("users")
        1
    """

    def __init__(
        self, base_entity: str, all_models: list[SemanticModel], max_hops: int = 2
    ):
        """Initialize and build the join graph.

        Args:
            base_entity: The starting entity for join traversal.
            all_models: List of all available semantic models.
            max_hops: Maximum join depth to traverse (default 2).
        """
        self.base_entity = base_entity
        self.all_models = all_models
        self.max_hops = max_hops
        self.reachable_models: dict[str, int] = {}
        self.reachable_entities: dict[str, int] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        """Build the join graph using BFS traversal.

        This method performs a breadth-first search starting from the base entity,
        following foreign key relationships to discover reachable models. It tracks
        the hop count for each discovered model/entity and respects the max_hops limit.

        The algorithm:
        1. Find the base model with the primary entity
        2. Initialize BFS queue with base model at depth 0
        3. For each model, explore foreign key entities
        4. Find target models where foreign key is primary
        5. Track reachability and hop count
        6. Continue until queue empty or max hops reached
        """
        # Find base model with primary entity
        base_model = find_model_by_primary_entity(self.base_entity, self.all_models)
        if not base_model:
            return  # Invalid base entity, reachable sets remain empty

        # BFS initialization
        queue: deque[tuple[SemanticModel, int]] = deque([(base_model, 0)])
        visited = {base_model.name}
        self.reachable_models[base_model.name] = 0
        self.reachable_entities[self.base_entity] = 0

        while queue:
            current_model, depth = queue.popleft()

            # Respect max hop limit (dbt recommends 2)
            if depth >= self.max_hops:
                continue

            # Process all foreign key entities in current model
            for entity in current_model.entities:
                if entity.type != "foreign":
                    continue

                # Find target model with this entity as primary
                target_model = find_model_by_primary_entity(
                    entity.name, self.all_models
                )

                if not target_model or target_model.name in visited:
                    continue

                # Mark as visited and reachable
                visited.add(target_model.name)
                hop_count = depth + 1
                self.reachable_models[target_model.name] = hop_count
                self.reachable_entities[entity.name] = hop_count

                # Continue traversal
                queue.append((target_model, hop_count))

    def is_model_reachable(self, model_name: str) -> bool:
        """Check if a model is reachable via the join graph.

        Args:
            model_name: Name of the model to check.

        Returns:
            True if the model is reachable from the base entity.
        """
        return model_name in self.reachable_models

    def is_entity_reachable(self, entity_name: str) -> bool:
        """Check if an entity is reachable via the join graph.

        Args:
            entity_name: Name of the entity to check.

        Returns:
            True if the entity is reachable from the base entity.
        """
        return entity_name in self.reachable_entities

    def get_hop_count(self, model_name: str) -> int | None:
        """Get the hop count for a reachable model.

        Args:
            model_name: Name of the model to query.

        Returns:
            Hop count (0 for base model, 1 for direct join, 2 for multi-hop),
            or None if not reachable.
        """
        return self.reachable_models.get(model_name)

    def get_reachable_models(self) -> dict[str, int]:
        """Get a copy of the reachable models map.

        Returns:
            Dictionary mapping model names to hop counts.
        """
        return self.reachable_models.copy()


# ============================================================================
# Entity Connectivity Validator
# ============================================================================


class EntityConnectivityValidator:
    """Main validation orchestrator for entity connectivity in metrics.

    This class validates that all measures required by a metric are reachable
    via the join graph from the metric's primary entity. It builds indexes
    of entities and measures for efficient lookup and provides detailed error
    messages with actionable suggestions.

    The validator performs the following checks:
    1. Primary entity exists and is valid
    2. All referenced measures exist
    3. All measure models are reachable via join graph
    4. Warn if measures require > 2 hops (may cause performance issues)

    Attributes:
        semantic_models: List of all semantic models.
        entity_to_model: Mapping of primary entity names to models.
        measure_to_model: Mapping of measure names to models.

    Example:
        >>> validator = EntityConnectivityValidator(models)
        >>> result = validator.validate_metric(metric)
        >>> if result.has_errors():
        ...     print(result.format_report())
    """

    def __init__(self, semantic_models: list[SemanticModel]):
        """Initialize validator and build entity/measure indexes.

        Args:
            semantic_models: List of all semantic models to validate against.
        """
        self.semantic_models = semantic_models
        self.entity_to_model: dict[str, SemanticModel] = {}
        self.measure_to_model: dict[str, SemanticModel] = {}
        self._build_entity_index()
        self._build_measure_index()

    def _build_entity_index(self) -> None:
        """Build index mapping primary entity names to their models.

        This creates a dictionary where keys are primary entity names and
        values are the semantic models that define those entities as primary.
        Only primary entities are indexed (not foreign entities).
        """
        for model in self.semantic_models:
            for entity in model.entities:
                if entity.type == "primary":
                    self.entity_to_model[entity.name] = model

    def _build_measure_index(self) -> None:
        """Build index mapping measure names to their models.

        This creates a dictionary where keys are measure names and values
        are the semantic models that define those measures.
        """
        for model in self.semantic_models:
            for measure in model.measures:
                self.measure_to_model[measure.name] = model

    def validate_metric(self, metric: Metric) -> ValidationResult:
        """Validate a single metric for entity connectivity.

        This method performs comprehensive validation:
        1. Extracts/infers primary entity
        2. Extracts measure dependencies
        3. Validates all measures exist
        4. Builds join graph from primary entity
        5. Checks each measure's model is reachable
        6. Warns if measures require > 2 hops

        Args:
            metric: The metric to validate.

        Returns:
            ValidationResult containing any errors or warnings found.
        """
        result = ValidationResult()

        # Step 1: Get/infer primary entity
        primary_entity = self._get_primary_entity(metric, result)
        if not primary_entity:
            return result  # Error already added

        # Step 2: Extract measure dependencies
        measure_names = extract_measure_dependencies(metric)

        # Derived metrics don't reference measures directly
        if not measure_names:
            return result

        # Step 3: Validate measures exist
        missing_measures = []
        measure_models: dict[str, SemanticModel] = {}
        for measure_name in measure_names:
            if measure_name not in self.measure_to_model:
                missing_measures.append(measure_name)
            else:
                measure_models[measure_name] = self.measure_to_model[measure_name]

        if missing_measures:
            self._add_missing_measure_error(metric, missing_measures, result)
            return result

        # Step 4: Build join graph
        join_graph = JoinGraph(
            base_entity=primary_entity, all_models=self.semantic_models, max_hops=2
        )

        # Step 5: Check reachability
        for measure_name, measure_model in measure_models.items():
            if not join_graph.is_model_reachable(measure_model.name):
                self._add_unreachable_measure_error(
                    metric, measure_name, measure_model, primary_entity, result
                )
            else:
                hop_count = join_graph.get_hop_count(measure_model.name)
                if hop_count and hop_count > 2:
                    self._add_hop_limit_warning(metric, measure_name, hop_count, result)

        return result

    def validate_metrics(self, metrics: list[Metric]) -> ValidationResult:
        """Validate multiple metrics for entity connectivity.

        Args:
            metrics: List of metrics to validate.

        Returns:
            ValidationResult containing all errors and warnings across all metrics.
        """
        combined_result = ValidationResult()

        for metric in metrics:
            result = self.validate_metric(metric)
            combined_result.issues.extend(result.issues)

        return combined_result

    def _get_primary_entity(
        self, metric: Metric, result: ValidationResult
    ) -> str | None:
        """Get or infer the primary entity for a metric.

        This method first checks for an explicit primary_entity in the metric's
        meta block. If not found, it attempts to infer the primary entity for
        ratio metrics by using the denominator's model's primary entity.

        Args:
            metric: The metric to get the primary entity for.
            result: ValidationResult to add errors to if needed.

        Returns:
            Primary entity name if found/inferred, None if not available.
        """
        # Try explicit primary_entity from meta
        if metric.primary_entity:
            if metric.primary_entity not in self.entity_to_model:
                self._add_invalid_primary_entity_error(metric, result)
                return None
            return metric.primary_entity

        # Try inference for ratio metrics
        if isinstance(metric.type_params, RatioMetricParams):
            denominator = metric.type_params.denominator
            if denominator in self.measure_to_model:
                denominator_model = self.measure_to_model[denominator]
                # Find primary entity of denominator's model
                for entity in denominator_model.entities:
                    if entity.type == "primary":
                        return entity.name

        # Could not determine primary entity
        self._add_missing_primary_entity_error(metric, result)
        return None

    def _add_unreachable_measure_error(
        self,
        metric: Metric,
        measure_name: str,
        measure_model: SemanticModel,
        primary_entity: str,
        result: ValidationResult,
    ) -> None:
        """Add error for measure model not reachable via join graph.

        Args:
            metric: The metric with the unreachable measure.
            measure_name: Name of the unreachable measure.
            measure_model: Model containing the measure.
            primary_entity: Primary entity of the metric.
            result: ValidationResult to add error to.
        """
        base_model = self.entity_to_model.get(primary_entity)
        base_model_name = base_model.name if base_model else "unknown"

        message = (
            f"Metric '{metric.name}' cannot be generated.\n\n"
            f"Primary Entity: {primary_entity}\n"
            f"Base Model: {base_model_name}\n"
            f"Unreachable Measure: {measure_name} "
            f"(from {measure_model.name} model)\n\n"
            f"The '{measure_model.name}' model is not reachable "
            f"from '{base_model_name}' via foreign key relationships."
        )

        suggestions = [
            "Change primary_entity to an entity that connects both models",
            f"Add a foreign key relationship between {base_model_name} "
            f"and {measure_model.name}",
            "Consider using a derived table approach for this metric",
        ]

        result.add_error(
            metric_name=metric.name,
            issue_type="unreachable_measure",
            message=message,
            suggestions=suggestions,
            primary_entity=primary_entity,
            measure_name=measure_name,
            measure_model=measure_model.name,
        )

    def _add_missing_primary_entity_error(
        self, metric: Metric, result: ValidationResult
    ) -> None:
        """Add error for missing primary_entity specification.

        Args:
            metric: The metric missing a primary entity.
            result: ValidationResult to add error to.
        """
        available = sorted(self.entity_to_model.keys())

        message = (
            f"Metric '{metric.name}' has no primary_entity specified.\n\n"
            f"Cross-entity metrics require an explicit primary_entity "
            f"in the meta block to determine which semantic model owns "
            f"the metric.\n\n"
            f"Available entities: {', '.join(available)}"
        )

        suggestions = [
            "Add 'primary_entity' to the metric's meta block",
            "For ratio metrics, the primary_entity should typically be "
            "the denominator's entity",
            f"Example: meta: {{primary_entity: '{available[0]}'}}",
        ]

        result.add_error(
            metric_name=metric.name,
            issue_type="missing_primary_entity",
            message=message,
            suggestions=suggestions,
            available_entities=available,
        )

    def _add_invalid_primary_entity_error(
        self, metric: Metric, result: ValidationResult
    ) -> None:
        """Add error for invalid primary_entity name.

        Args:
            metric: The metric with invalid primary entity.
            result: ValidationResult to add error to.
        """
        available = sorted(self.entity_to_model.keys())
        invalid_entity = metric.primary_entity or "unknown"

        message = (
            f"Metric '{metric.name}' has invalid primary_entity: "
            f"'{invalid_entity}'.\n\n"
            f"No semantic model has '{invalid_entity}' as a primary entity.\n\n"
            f"Available entities: {', '.join(available)}"
        )

        suggestions = [
            "Fix the primary_entity name in the metric's meta block",
            f"Use one of the available entities: {', '.join(available[:3])}",
            "Verify the entity name matches exactly (case-sensitive)",
        ]

        result.add_error(
            metric_name=metric.name,
            issue_type="invalid_primary_entity",
            message=message,
            suggestions=suggestions,
            primary_entity=invalid_entity,
            available_entities=available,
        )

    def _add_missing_measure_error(
        self, metric: Metric, missing_measures: list[str], result: ValidationResult
    ) -> None:
        """Add error for measures not found in any model.

        Args:
            metric: The metric referencing missing measures.
            missing_measures: List of measure names that don't exist.
            result: ValidationResult to add error to.
        """
        available = sorted(self.measure_to_model.keys())
        measures_str = ", ".join(missing_measures)

        message = (
            f"Metric '{metric.name}' references non-existent measures.\n\n"
            f"Missing measures: {measures_str}\n\n"
            f"Available measures: {', '.join(available[:10])}"
            + ("..." if len(available) > 10 else "")
        )

        suggestions = [
            "Verify the measure names are spelled correctly",
            "Check that the semantic models defining these measures are included",
            "Ensure measure definitions exist in the semantic model YAML files",
        ]

        result.add_error(
            metric_name=metric.name,
            issue_type="missing_measure",
            message=message,
            suggestions=suggestions,
        )

    def _add_hop_limit_warning(
        self,
        metric: Metric,
        measure_name: str,
        hop_count: int,
        result: ValidationResult,
    ) -> None:
        """Add warning for measures requiring > 2 hops.

        Args:
            metric: The metric with the measure.
            measure_name: Name of the measure requiring multiple hops.
            hop_count: Number of hops required to reach the measure.
            result: ValidationResult to add warning to.
        """
        message = (
            f"Metric '{metric.name}' requires {hop_count} join hops to reach "
            f"measure '{measure_name}'.\n\n"
            f"This exceeds the recommended 2-hop limit and may cause "
            f"performance issues."
        )

        suggestions = [
            "Consider changing the primary_entity to reduce join depth",
            "Consider creating a derived table to pre-join the required data",
            "Review the join graph to optimize the relationship structure",
        ]

        result.add_warning(
            metric_name=metric.name,
            issue_type="exceeds_hop_limit",
            message=message,
            suggestions=suggestions,
            measure_name=measure_name,
        )
