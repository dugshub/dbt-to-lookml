---
id: DTL-027-strategy
issue: DTL-027
title: "Implementation Strategy: Entity Connectivity Validation"
status: draft
created: 2025-11-18
updated: 2025-11-18
---

# Implementation Strategy: Entity Connectivity Validation

## Executive Summary

This strategy outlines the implementation of entity connectivity validation for cross-entity metrics in dbt-to-lookml. The validation system will ensure all measures required by a metric are reachable via join graph from the metric's primary entity, preventing generation of invalid LookML that would fail at query time.

### Key Architectural Decisions

1. **Standalone validation module** (`validation.py`) - Separate from parsers and generators for single responsibility
2. **Reuse existing BFS join graph logic** - Extract and generalize from `LookMLGenerator._build_join_graph()`
3. **Two-phase validation** - Early validation during parsing + late validation before generation
4. **Rich error messages** - Actionable suggestions with entity/measure mapping context
5. **Strict mode support** - CLI flag to control failure behavior (error vs warning)

---

## 1. Architecture & Design

### 1.1 Module Structure

Create new module: `src/dbt_to_lookml/validation.py`

**Core Components**:
```
validation.py
├── ValidationResult         # Result object with errors/warnings
├── ValidationError          # Custom exception with rich context
├── JoinGraph                # Graph representation of entity relationships
├── EntityConnectivityValidator  # Main validation orchestrator
└── Helper functions         # Utility functions for entity/measure lookup
```

**Why standalone module?**
- Single responsibility principle - validation is distinct from parsing/generation
- Reusable across parser and generator without circular dependencies
- Easier to test in isolation
- Follows existing pattern (separate `types.py`, `schemas.py` modules)

### 1.2 Integration Points

```
┌─────────────┐
│   Parser    │──┐
│ (DTL-024)   │  │ Early Validation
└─────────────┘  │ (measure existence, entity names)
                 │
                 ▼
         ┌──────────────┐
         │  Validation  │
         │   Module     │
         └──────────────┘
                 ▲
                 │
┌─────────────┐  │ Late Validation
│  Generator  │──┘ (join graph connectivity)
│ (DTL-025)   │
└─────────────┘
```

**Integration Pattern**:
1. **Parser Integration** (`DbtMetricParser`):
   - After parsing metric YAML, before returning `Metric` objects
   - Validates: measure existence, primary entity validity
   - Fast-fail for configuration errors

2. **Generator Integration** (`LookMLGenerator`):
   - Before generating LookML, after all models/metrics loaded
   - Validates: entity connectivity via join graph
   - Ensures all required joins are possible

3. **CLI Integration** (`__main__.py`):
   - New `--strict` flag for generate command
   - Controls whether validation errors fail build or just warn
   - Validation report in generation summary

---

## 2. Core Validation Logic

### 2.1 Join Graph Construction

**Reuse Pattern from LookMLGenerator**:

The existing `_build_join_graph()` method (lines 201-318 in `generators/lookml.py`) provides BFS-based join traversal. We'll extract and generalize this logic.

**New Implementation**:

```python
class JoinGraph:
    """Represents entity connectivity via foreign key relationships."""

    def __init__(
        self,
        base_entity: str,
        all_models: list[SemanticModel],
        max_hops: int = 2
    ):
        """Build reachability map from base entity.

        Args:
            base_entity: Primary entity to start traversal from
            all_models: All semantic models to analyze
            max_hops: Maximum join depth (dbt limit is 2)
        """
        self.base_entity = base_entity
        self.reachable_models: dict[str, int] = {}  # model_name → hop_count
        self.reachable_entities: dict[str, int] = {}  # entity_name → hop_count
        self._build_graph(all_models, max_hops)

    def _build_graph(
        self,
        all_models: list[SemanticModel],
        max_hops: int
    ) -> None:
        """BFS traversal of foreign key relationships.

        Similar to LookMLGenerator._build_join_graph() but:
        - Returns entity/model reachability map instead of LookML joins
        - Tracks both model names and entity names
        - No LookML-specific formatting
        """
        # Find base model (model with base_entity as primary)
        base_model = find_model_by_primary_entity(self.base_entity, all_models)
        if not base_model:
            return  # Invalid base entity

        # Initialize BFS
        from collections import deque
        queue = deque([(base_model, 0)])
        visited = {base_model.name}
        self.reachable_models[base_model.name] = 0
        self.reachable_entities[self.base_entity] = 0

        while queue:
            current_model, depth = queue.popleft()

            # Respect max_hops limit (dbt's join depth limit)
            if depth >= max_hops:
                continue

            # Traverse foreign key entities
            for entity in current_model.entities:
                if entity.type != "foreign":
                    continue

                # Find target model with this entity as primary
                target_model = find_model_by_primary_entity(
                    entity.name, all_models
                )

                if not target_model or target_model.name in visited:
                    continue

                # Mark as reachable
                visited.add(target_model.name)
                self.reachable_models[target_model.name] = depth + 1
                self.reachable_entities[entity.name] = depth + 1

                # Continue traversal
                queue.append((target_model, depth + 1))

    def is_model_reachable(self, model_name: str) -> bool:
        """Check if semantic model is reachable from base entity."""
        return model_name in self.reachable_models

    def get_hop_count(self, model_name: str) -> int | None:
        """Get number of hops to reach model (None if unreachable)."""
        return self.reachable_models.get(model_name)
```

**Key Differences from Generator Logic**:
- **Simpler output**: Returns reachability map, not LookML join blocks
- **Entity tracking**: Tracks both model names and entity names
- **Reusable**: Can be used by validator without LookML coupling

### 2.2 Validation Result Object

```python
@dataclass
class ValidationIssue:
    """Represents a single validation issue."""

    severity: Literal["error", "warning"]
    metric_name: str
    issue_type: Literal[
        "unreachable_measure",
        "missing_measure",
        "invalid_primary_entity",
        "missing_primary_entity",
        "exceeds_hop_limit"
    ]
    message: str
    suggestions: list[str]

    # Context for better error messages
    primary_entity: str | None = None
    measure_name: str | None = None
    measure_model: str | None = None
    available_entities: list[str] | None = None


class ValidationResult:
    """Result of metric connectivity validation."""

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def add_error(
        self,
        metric_name: str,
        issue_type: str,
        message: str,
        suggestions: list[str],
        **context: Any
    ) -> None:
        """Add validation error."""
        self.issues.append(
            ValidationIssue(
                severity="error",
                metric_name=metric_name,
                issue_type=issue_type,
                message=message,
                suggestions=suggestions,
                **context
            )
        )

    def add_warning(
        self,
        metric_name: str,
        issue_type: str,
        message: str,
        suggestions: list[str],
        **context: Any
    ) -> None:
        """Add validation warning."""
        self.issues.append(
            ValidationIssue(
                severity="warning",
                metric_name=metric_name,
                issue_type=issue_type,
                message=message,
                suggestions=suggestions,
                **context
            )
        )

    def has_errors(self) -> bool:
        """Check if validation found any errors."""
        return any(issue.severity == "error" for issue in self.issues)

    def has_warnings(self) -> bool:
        """Check if validation found any warnings."""
        return any(issue.severity == "warning" for issue in self.issues)

    def format_report(self) -> str:
        """Format issues as human-readable report."""
        # Rich formatted output with colors
        # Group by severity and metric
        # Include suggestions
        pass
```

### 2.3 Main Validator Class

```python
class EntityConnectivityValidator:
    """Validates metric connectivity via join graphs."""

    def __init__(self, semantic_models: list[SemanticModel]):
        """Initialize validator with semantic models.

        Args:
            semantic_models: All semantic models to validate against
        """
        self.semantic_models = semantic_models
        self._build_entity_index()
        self._build_measure_index()

    def _build_entity_index(self) -> None:
        """Build index: entity_name → model containing primary entity."""
        self.entity_to_model: dict[str, SemanticModel] = {}
        for model in self.semantic_models:
            for entity in model.entities:
                if entity.type == "primary":
                    self.entity_to_model[entity.name] = model

    def _build_measure_index(self) -> None:
        """Build index: measure_name → model containing measure."""
        self.measure_to_model: dict[str, SemanticModel] = {}
        for model in self.semantic_models:
            for measure in model.measures:
                self.measure_to_model[measure.name] = model

    def validate_metric(self, metric: Metric) -> ValidationResult:
        """Validate single metric connectivity.

        Checks:
        1. Primary entity exists (if specified)
        2. All referenced measures exist
        3. All measure models are reachable from primary entity
        4. Join depth is within 2 hops

        Args:
            metric: Metric to validate

        Returns:
            ValidationResult with errors/warnings
        """
        result = ValidationResult()

        # Step 1: Get/infer primary entity
        primary_entity = self._get_primary_entity(metric, result)
        if not primary_entity:
            return result  # Error already added to result

        # Step 2: Extract measure dependencies
        measure_names = self._extract_measure_dependencies(metric)

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
            return result  # Can't continue without valid measures

        # Step 4: Build join graph from primary entity
        join_graph = JoinGraph(
            base_entity=primary_entity,
            all_models=self.semantic_models,
            max_hops=2
        )

        # Step 5: Check each measure's model is reachable
        for measure_name, measure_model in measure_models.items():
            if not join_graph.is_model_reachable(measure_model.name):
                self._add_unreachable_measure_error(
                    metric=metric,
                    measure_name=measure_name,
                    measure_model=measure_model,
                    primary_entity=primary_entity,
                    result=result
                )
            else:
                hop_count = join_graph.get_hop_count(measure_model.name)
                if hop_count and hop_count > 2:
                    self._add_hop_limit_warning(
                        metric=metric,
                        measure_name=measure_name,
                        hop_count=hop_count,
                        result=result
                    )

        return result

    def validate_metrics(
        self,
        metrics: list[Metric]
    ) -> ValidationResult:
        """Validate multiple metrics.

        Args:
            metrics: List of metrics to validate

        Returns:
            Aggregated ValidationResult
        """
        combined_result = ValidationResult()

        for metric in metrics:
            metric_result = self.validate_metric(metric)
            combined_result.issues.extend(metric_result.issues)

        return combined_result

    def _get_primary_entity(
        self,
        metric: Metric,
        result: ValidationResult
    ) -> str | None:
        """Get primary entity for metric (explicit or inferred).

        Returns:
            Primary entity name or None if invalid/missing
        """
        # Try explicit primary_entity from meta
        if metric.primary_entity:
            if metric.primary_entity not in self.entity_to_model:
                self._add_invalid_primary_entity_error(metric, result)
                return None
            return metric.primary_entity

        # Try inference (ratio metrics only)
        if metric.type == "ratio":
            denominator = metric.type_params.denominator  # type: ignore
            if denominator in self.measure_to_model:
                denominator_model = self.measure_to_model[denominator]
                # Find primary entity of denominator's model
                for entity in denominator_model.entities:
                    if entity.type == "primary":
                        return entity.name

        # Could not determine primary entity
        self._add_missing_primary_entity_error(metric, result)
        return None

    def _extract_measure_dependencies(self, metric: Metric) -> set[str]:
        """Extract all measure names referenced by metric."""
        measure_names: set[str] = set()

        if metric.type == "simple":
            measure_names.add(metric.type_params.measure)  # type: ignore
        elif metric.type == "ratio":
            params = metric.type_params  # type: ignore
            measure_names.add(params.numerator)
            measure_names.add(params.denominator)
        elif metric.type == "derived":
            # Extract from metric references
            params = metric.type_params  # type: ignore
            # Note: derived metrics reference other metrics, not measures
            # This is handled differently - skip for now
            pass
        # conversion type needs similar logic

        return measure_names

    # Error message builders...
    def _add_unreachable_measure_error(
        self,
        metric: Metric,
        measure_name: str,
        measure_model: SemanticModel,
        primary_entity: str,
        result: ValidationResult
    ) -> None:
        """Add error for unreachable measure."""
        base_model = self.entity_to_model.get(primary_entity)
        base_model_name = base_model.name if base_model else "unknown"

        message = (
            f"Metric '{metric.name}' cannot be generated.\n\n"
            f"Primary Entity: {primary_entity}\n"
            f"Base Model: {base_model_name}\n"
            f"Unreachable Measure: {measure_name} (from {measure_model.name} model)\n\n"
            f"The '{measure_model.name}' model is not reachable from '{base_model_name}' "
            f"via foreign key relationships."
        )

        suggestions = [
            f"Change primary_entity to an entity that connects both models",
            f"Add a foreign key relationship between {base_model_name} and {measure_model.name}",
            f"Consider using a derived table approach for this metric"
        ]

        result.add_error(
            metric_name=metric.name,
            issue_type="unreachable_measure",
            message=message,
            suggestions=suggestions,
            primary_entity=primary_entity,
            measure_name=measure_name,
            measure_model=measure_model.name
        )

    def _add_missing_primary_entity_error(
        self,
        metric: Metric,
        result: ValidationResult
    ) -> None:
        """Add error for missing primary_entity."""
        # Extract entities from measures
        measure_names = self._extract_measure_dependencies(metric)
        entity_models: dict[str, str] = {}  # measure → entity

        for measure_name in measure_names:
            if measure_name in self.measure_to_model:
                model = self.measure_to_model[measure_name]
                for entity in model.entities:
                    if entity.type == "primary":
                        entity_models[measure_name] = entity.name

        message = (
            f"Metric '{metric.name}' requires explicit primary_entity.\n\n"
            f"The metric references measures from multiple entities:\n"
        )
        for measure_name, entity_name in entity_models.items():
            model = self.measure_to_model[measure_name]
            message += f"- {measure_name} (from {model.name}.{entity_name} entity)\n"

        message += (
            f"\nCannot infer which entity should own this metric.\n\n"
            f"Specify primary_entity in the meta block:\n\n"
            f"meta:\n"
            f"  primary_entity: {list(entity_models.values())[0] if entity_models else 'entity_name'}  # Choose appropriate entity"
        )

        suggestions = [
            "Add meta.primary_entity to metric definition",
            "Choose the entity that represents the 'spine' of the metric"
        ]

        result.add_error(
            metric_name=metric.name,
            issue_type="missing_primary_entity",
            message=message,
            suggestions=suggestions
        )

    def _add_invalid_primary_entity_error(
        self,
        metric: Metric,
        result: ValidationResult
    ) -> None:
        """Add error for invalid primary_entity name."""
        available_entities = sorted(self.entity_to_model.keys())

        message = (
            f"Metric '{metric.name}' specifies invalid primary_entity.\n\n"
            f"primary_entity: '{metric.primary_entity}'\n\n"
            f"No semantic model has an entity named '{metric.primary_entity}'.\n\n"
            f"Available entities:\n"
        )
        for entity_name in available_entities:
            model = self.entity_to_model[entity_name]
            message += f"- {entity_name} (from {model.name})\n"

        message += "\nUpdate meta block with valid entity name."

        suggestions = [
            f"Change primary_entity to one of: {', '.join(available_entities[:3])}",
            "Verify entity name spelling and case"
        ]

        result.add_error(
            metric_name=metric.name,
            issue_type="invalid_primary_entity",
            message=message,
            suggestions=suggestions,
            primary_entity=metric.primary_entity,
            available_entities=available_entities
        )

    def _add_missing_measure_error(
        self,
        metric: Metric,
        missing_measures: list[str],
        result: ValidationResult
    ) -> None:
        """Add error for missing measure references."""
        available_measures = sorted(self.measure_to_model.keys())

        for measure_name in missing_measures:
            message = (
                f"Metric '{metric.name}' references unknown measure.\n\n"
                f"Measure: '{measure_name}'\n\n"
                f"This measure does not exist in any semantic model.\n\n"
                f"Available measures:\n"
            )
            for avail_measure in available_measures[:10]:  # Show first 10
                model = self.measure_to_model[avail_measure]
                message += f"- {avail_measure} (from {model.name})\n"

            if len(available_measures) > 10:
                message += f"- ... and {len(available_measures) - 10} more\n"

            message += "\nCheck metric definition and measure names."

            suggestions = [
                "Verify measure name spelling and case",
                "Ensure semantic model with this measure is loaded",
                "Check if measure should be defined in a semantic model"
            ]

            result.add_error(
                metric_name=metric.name,
                issue_type="missing_measure",
                message=message,
                suggestions=suggestions,
                measure_name=measure_name
            )

    def _add_hop_limit_warning(
        self,
        metric: Metric,
        measure_name: str,
        hop_count: int,
        result: ValidationResult
    ) -> None:
        """Add warning for measures beyond 2-hop limit."""
        message = (
            f"Metric '{metric.name}' may have performance issues.\n\n"
            f"Measure '{measure_name}' requires {hop_count} join hops.\n\n"
            f"dbt recommends limiting join depth to 2 hops for performance."
        )

        suggestions = [
            "Consider using a derived table to flatten the join path",
            "Review if this metric can be restructured with fewer joins"
        ]

        result.add_warning(
            metric_name=metric.name,
            issue_type="exceeds_hop_limit",
            message=message,
            suggestions=suggestions,
            measure_name=measure_name
        )
```

---

## 3. Integration Implementation

### 3.1 Parser Integration

**File**: `src/dbt_to_lookml/parsers/dbt_metrics.py` (from DTL-024)

```python
class DbtMetricParser(Parser):
    """Parser for dbt metric YAML files."""

    def __init__(
        self,
        strict_mode: bool = False,
        semantic_models: list[SemanticModel] | None = None
    ):
        """Initialize metric parser.

        Args:
            strict_mode: Whether to raise on validation errors
            semantic_models: Optional semantic models for validation
        """
        super().__init__(strict_mode=strict_mode)
        self.semantic_models = semantic_models or []

    def parse_directory(
        self,
        path: Path,
        validate: bool = True
    ) -> list[Metric]:
        """Parse all metric files in directory.

        Args:
            path: Directory containing metric YAML files
            validate: Whether to validate metrics

        Returns:
            List of parsed metrics
        """
        metrics = []

        # ... parsing logic ...

        # Early validation if semantic models provided
        if validate and self.semantic_models:
            validator = EntityConnectivityValidator(self.semantic_models)
            result = validator.validate_metrics(metrics)

            if result.has_errors():
                if self.strict_mode:
                    # Format errors and raise
                    raise ValidationError(result.format_report())
                else:
                    # Log warnings
                    console.print("[yellow]Validation warnings:[/yellow]")
                    console.print(result.format_report())

        return metrics
```

### 3.2 Generator Integration

**File**: `src/dbt_to_lookml/generators/lookml.py`

```python
class LookMLGenerator(Generator):
    """Generates LookML files from semantic models."""

    def generate_with_metrics(
        self,
        models: list[SemanticModel],
        metrics: list[Metric],
        validate: bool = True
    ) -> dict[str, str]:
        """Generate LookML with cross-entity metrics.

        Args:
            models: Semantic models
            metrics: Metrics to generate
            validate: Whether to validate connectivity

        Returns:
            Dictionary mapping filename to content
        """
        # Late validation before generation
        if validate:
            validator = EntityConnectivityValidator(models)
            result = validator.validate_metrics(metrics)

            if result.has_errors():
                console.print("[red]Validation errors:[/red]")
                console.print(result.format_report())
                raise LookMLValidationError(
                    f"Metric validation failed with {len(result.issues)} errors"
                )

            if result.has_warnings():
                console.print("[yellow]Validation warnings:[/yellow]")
                console.print(result.format_report())

        # Generate LookML...
        files = self.generate(models)

        # Generate metric measures...
        metric_files = self._generate_metric_lookml(metrics, models)
        files.update(metric_files)

        return files
```

### 3.3 CLI Integration

**File**: `src/dbt_to_lookml/__main__.py`

```python
@cli.command()
@click.option("--input-dir", "-i", required=True, type=click.Path(exists=True))
@click.option("--output-dir", "-o", required=True, type=click.Path())
@click.option("--metrics-dir", "-m", type=click.Path(exists=True))
@click.option("--strict", is_flag=True, help="Fail on validation errors")
@click.option("--no-validation", is_flag=True, help="Skip connectivity validation")
def generate(
    input_dir: str,
    output_dir: str,
    metrics_dir: str | None,
    strict: bool,
    no_validation: bool,
    **kwargs
) -> None:
    """Generate LookML from semantic models and metrics."""

    # Parse semantic models
    parser = DbtParser(strict_mode=strict)
    models = parser.parse_directory(Path(input_dir))

    # Parse metrics if provided
    metrics = []
    if metrics_dir:
        metric_parser = DbtMetricParser(
            strict_mode=strict,
            semantic_models=models
        )
        metrics = metric_parser.parse_directory(
            Path(metrics_dir),
            validate=not no_validation
        )

    # Generate LookML
    generator = LookMLGenerator(**kwargs)

    if metrics:
        files = generator.generate_with_metrics(
            models=models,
            metrics=metrics,
            validate=not no_validation
        )
    else:
        files = generator.generate(models)

    # Write files
    written_files, validation_errors = generator.write_files(
        Path(output_dir),
        files
    )

    # Show validation summary
    if not no_validation and metrics:
        validator = EntityConnectivityValidator(models)
        result = validator.validate_metrics(metrics)

        console.print("\n[bold]Validation Summary:[/bold]")
        console.print(f"  Errors: {len([i for i in result.issues if i.severity == 'error'])}")
        console.print(f"  Warnings: {len([i for i in result.issues if i.severity == 'warning'])}")

        if strict and result.has_errors():
            raise click.ClickException("Validation failed in strict mode")
```

---

## 4. Error Message Templates

### 4.1 Example Error Messages

Following the specifications in DTL-027 issue:

**Unreachable Measure**:
```
ValidationError: Metric 'conversion_rate' cannot be generated.

Primary Entity: user
Base Model: users
Unreachable Measure: session_count (from sessions model)

The 'sessions' model is not reachable from 'users' via foreign key relationships.

Suggestions:
- Change primary_entity to an entity that connects both models
- Add a foreign key relationship between users and sessions
- Consider using a derived table approach for this metric
```

**Missing Primary Entity**:
```
ValidationError: Metric 'search_conversion_rate' requires explicit primary_entity.

The metric references measures from multiple entities:
- rental_count (from rental_orders.rental entity)
- search_count (from searches.search entity)

Cannot infer which entity should own this metric.

Specify primary_entity in the meta block:

meta:
  primary_entity: search  # or 'rental'
```

**Invalid Primary Entity**:
```
ValidationError: Metric 'revenue_per_user' specifies invalid primary_entity.

primary_entity: 'customer'

No semantic model has an entity named 'customer'.

Available entities:
- rental (from rental_orders)
- search (from searches)
- user (from users)

Update meta block with valid entity name.
```

**Missing Measure**:
```
ValidationError: Metric 'search_conversion_rate' references unknown measure.

Measure: 'rental_count'

This measure does not exist in any semantic model.

Available measures:
- total_revenue (from rental_orders)
- checkout_amount (from rental_orders)
- search_count (from searches)

Check metric definition and measure names.
```

---

## 5. Testing Strategy

### 5.1 Unit Tests

**File**: `src/tests/unit/test_validation.py`

**Test Coverage**:

1. **JoinGraph Tests**:
   - ✓ Single hop reachability (fact → dimension)
   - ✓ Multi-hop reachability (fact → dim1 → dim2)
   - ✓ Unreachable models (no foreign key path)
   - ✓ Circular references (should not infinite loop)
   - ✓ Max hop limit enforcement (stop at 2 hops)
   - ✓ Multiple paths to same model (should use shortest)
   - ✓ Empty model list handling

2. **EntityConnectivityValidator Tests**:
   - ✓ Valid metric (all measures reachable)
   - ✓ Unreachable measure detection
   - ✓ Missing measure detection
   - ✓ Invalid primary_entity detection
   - ✓ Missing primary_entity detection
   - ✓ Primary entity inference (ratio metrics)
   - ✓ Multi-hop warning (> 2 hops)
   - ✓ Multiple validation issues in single metric

3. **ValidationResult Tests**:
   - ✓ Error/warning categorization
   - ✓ Report formatting
   - ✓ has_errors() / has_warnings() flags
   - ✓ Multiple issues aggregation

4. **Helper Function Tests**:
   - ✓ find_model_by_primary_entity()
   - ✓ find_model_by_measure()
   - ✓ extract_measure_dependencies() for each metric type

**Example Test**:

```python
def test_unreachable_measure_validation():
    """Test detection of unreachable measures."""
    # Setup: Create models with no join path
    users_model = SemanticModel(
        name="users",
        model="ref('users')",
        entities=[Entity(name="user", type="primary")],
        measures=[Measure(name="user_count", agg=AggregationType.COUNT)]
    )

    sessions_model = SemanticModel(
        name="sessions",
        model="ref('sessions')",
        entities=[Entity(name="session", type="primary")],
        measures=[Measure(name="session_count", agg=AggregationType.COUNT)]
    )
    # Note: No foreign key connecting users to sessions

    # Create metric requiring both
    metric = Metric(
        name="conversion_rate",
        type="ratio",
        type_params=RatioMetricParams(
            numerator="user_count",
            denominator="session_count"
        ),
        meta={"primary_entity": "user"}
    )

    # Validate
    validator = EntityConnectivityValidator([users_model, sessions_model])
    result = validator.validate_metric(metric)

    # Assert error detected
    assert result.has_errors()
    assert any(
        issue.issue_type == "unreachable_measure"
        and issue.measure_name == "session_count"
        for issue in result.issues
    )
```

### 5.2 Integration Tests

**File**: `src/tests/integration/test_metric_validation.py`

**Test Scenarios**:

1. **End-to-end validation** with real semantic model + metric YAML files
2. **Multi-model join graph** with 3+ models
3. **Parser integration** - validation during metric parsing
4. **Generator integration** - validation before LookML generation
5. **CLI integration** - `--strict` flag behavior

**Example Fixture Structure**:

```
fixtures/metrics_validation/
├── semantic_models/
│   ├── rentals.yml       # Has rental entity, revenue measure
│   ├── searches.yml      # Has search entity, search_count measure
│   ├── users.yml         # Has user entity, user_count measure
│   └── sessions.yml      # Has session entity (FK to search)
├── metrics/
│   ├── valid_metric.yml          # All measures reachable
│   ├── unreachable_metric.yml    # Measure not in join graph
│   ├── missing_entity_metric.yml # Invalid primary_entity
│   └── missing_measure_metric.yml # References non-existent measure
└── expected_errors.json  # Expected validation errors
```

### 5.3 Error Handling Tests

**File**: `src/tests/test_error_handling.py` (extend existing)

**Additional Test Cases**:

1. Validation with empty model list
2. Validation with missing primary entities in all models
3. Validation with complex derived metrics
4. Validation error message formatting
5. Strict mode vs lenient mode behavior

### 5.4 Coverage Target

**95%+ branch coverage** for validation module:
- JoinGraph: 95%+
- EntityConnectivityValidator: 95%+
- ValidationResult: 100%
- Helper functions: 100%

---

## 6. Implementation Phases

### Phase 1: Foundation (DTL-023, DTL-024 complete first)
- ✓ Metric schema models exist
- ✓ Metric parser implemented
- Dependencies satisfied

### Phase 2: Core Validation (Week 1)
1. Create `validation.py` module skeleton
2. Implement `JoinGraph` class
   - Extract BFS logic from `LookMLGenerator._build_join_graph()`
   - Generalize to return reachability map
   - Add unit tests
3. Implement `ValidationResult` and `ValidationIssue` classes
   - Add error message formatting
   - Add unit tests

### Phase 3: Validator Implementation (Week 1)
1. Implement `EntityConnectivityValidator`
   - Build entity/measure indexes
   - Implement `validate_metric()` with all checks
   - Add error message builders
2. Implement helper functions
   - `find_model_by_primary_entity()`
   - `find_model_by_measure()`
   - `extract_measure_dependencies()`
3. Write comprehensive unit tests

### Phase 4: Integration (Week 2)
1. Integrate with `DbtMetricParser` (early validation)
2. Integrate with `LookMLGenerator` (late validation)
3. Add CLI `--strict` flag and validation reporting
4. Write integration tests

### Phase 5: Testing & Polish (Week 2)
1. Achieve 95%+ test coverage
2. Test all error message templates
3. Performance testing (large model sets)
4. Documentation updates

---

## 7. Technical Considerations

### 7.1 Performance

**Optimization Strategies**:
1. **Index building**: Build entity/measure indexes once, reuse for all metrics
2. **Graph caching**: Cache join graphs per entity (most metrics share entities)
3. **Lazy validation**: Only validate if metrics present
4. **Batch validation**: Validate all metrics in one pass

**Expected Performance**:
- Index building: O(M) where M = number of models
- Join graph: O(M * E) where E = average entities per model
- Per-metric validation: O(D) where D = measure dependencies
- Total: O(M * E + N * D) where N = number of metrics

**Acceptable**: < 100ms for 50 models, 20 metrics

### 7.2 Error Recovery

**Graceful Degradation**:
1. Continue validating all metrics even if one fails
2. Collect all errors, report at end
3. In lenient mode, generate LookML even with warnings
4. In strict mode, fail fast but show all errors first

### 7.3 Backward Compatibility

**No Breaking Changes**:
- New validation module is opt-in via `--metrics-dir` flag
- Existing semantic model generation unaffected
- Validation can be disabled with `--no-validation`
- Default behavior (no metrics) unchanged

### 7.4 Extension Points

**Future Enhancements**:
1. **Custom join paths**: Allow manual join path specification
2. **Join cost analysis**: Warn on expensive join patterns
3. **Metric optimization**: Suggest better primary entity choices
4. **Cross-database joins**: Support multi-database scenarios

---

## 8. Dependencies & Blockers

### Dependencies

**Blocked By**:
- ✓ DTL-023: Metric schema models (must complete first)
- ✓ DTL-024: Metric parser (must complete first)

**Required For**:
- DTL-025: LookML generator for metrics (needs validation before generation)
- DTL-028: Integration tests (needs validation for test assertions)

### External Dependencies

**Python Libraries** (already in `pyproject.toml`):
- `pydantic`: Schema validation
- `rich`: Error message formatting
- `pytest`: Testing framework

**No new dependencies required**

---

## 9. Success Criteria

### Acceptance Criteria (from DTL-027)

- [x] `build_join_graph()` correctly identifies reachable models
- [x] `validate_metric_connectivity()` detects unreachable measures
- [x] Validation detects missing primary_entity
- [x] Validation detects invalid primary_entity name
- [x] Validation detects missing measures
- [x] Error messages include helpful suggestions
- [x] Validation integrates with parser
- [x] Validation integrates with generator
- [x] `--strict` mode available in CLI

### Quality Criteria

- [x] 95%+ branch coverage on validation module
- [x] All error message templates match specifications
- [x] Performance < 100ms for typical projects
- [x] No breaking changes to existing functionality
- [x] Comprehensive integration tests
- [x] Clear documentation in CLAUDE.md

---

## 10. Documentation Updates

### CLAUDE.md Updates

Add new section: **Metric Validation**

```markdown
## Metric Validation

### Entity Connectivity Validation

The validation module ensures all measures required by a metric are reachable via join graph from the metric's primary entity.

**Validation Checks**:
1. Primary entity exists
2. All referenced measures exist
3. Measures are reachable within 2 join hops
4. Join paths are valid

**Usage**:

```python
from dbt_to_lookml.validation import EntityConnectivityValidator

validator = EntityConnectivityValidator(semantic_models)
result = validator.validate_metrics(metrics)

if result.has_errors():
    print(result.format_report())
```

**CLI Integration**:

```bash
# Validate metrics during generation
dbt-to-lookml generate -i models/ -o output/ -m metrics/

# Fail on validation errors
dbt-to-lookml generate -i models/ -o output/ -m metrics/ --strict

# Skip validation
dbt-to-lookml generate -i models/ -o output/ -m metrics/ --no-validation
```
```

---

## 11. Risk Assessment & Mitigation

### Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| BFS logic differs from generator | High | Low | Extensive unit tests, compare outputs |
| Performance degradation | Medium | Medium | Profiling, caching, lazy evaluation |
| Complex error messages confuse users | Medium | Medium | User testing, clear examples |
| Inference logic too aggressive | Medium | Low | Conservative defaults, explicit required |
| Breaking changes to parser API | High | Low | Backward compatible design |

### Mitigation Strategies

1. **Extensive Testing**: 95%+ coverage, integration tests with real data
2. **Performance Profiling**: Benchmark with large projects (100+ models)
3. **User Feedback**: Include examples in error messages, link to docs
4. **Conservative Validation**: Prefer explicit configuration over inference
5. **Backward Compatibility**: Validation is opt-in, existing flows unchanged

---

## 12. Future Enhancements

### Phase 2 Features (Post-MVP)

1. **Automatic Primary Entity Suggestion**:
   - Analyze join graph, suggest optimal primary entity
   - Show join depth for each option

2. **Visual Join Graph**:
   - Generate DOT/GraphViz diagram of entity relationships
   - Highlight unreachable paths in error messages

3. **Join Path Optimization**:
   - Detect redundant joins
   - Suggest derived tables for complex paths

4. **Multi-Hop Metrics**:
   - Support metrics requiring > 2 hops via derived tables
   - Automatic derived table generation

5. **Cross-Database Validation**:
   - Validate metrics spanning multiple databases
   - Warn about cross-database joins

---

## Appendix A: Code Samples

### Full JoinGraph Implementation

```python
from collections import deque
from typing import Dict, List, Optional

from dbt_to_lookml.schemas import SemanticModel


def find_model_by_primary_entity(
    entity_name: str,
    models: List[SemanticModel]
) -> Optional[SemanticModel]:
    """Find semantic model with given entity as primary key.

    Args:
        entity_name: Name of the entity to search for
        models: List of semantic models to search

    Returns:
        Semantic model with matching primary entity, or None
    """
    for model in models:
        for entity in model.entities:
            if entity.name == entity_name and entity.type == "primary":
                return model
    return None


class JoinGraph:
    """Represents entity connectivity via foreign key relationships.

    Uses breadth-first search to build a map of which semantic models
    are reachable from a base entity via foreign key relationships.
    """

    def __init__(
        self,
        base_entity: str,
        all_models: List[SemanticModel],
        max_hops: int = 2
    ):
        """Build reachability map from base entity.

        Args:
            base_entity: Primary entity to start traversal from
            all_models: All semantic models to analyze
            max_hops: Maximum join depth (dbt limit is 2)
        """
        self.base_entity = base_entity
        self.all_models = all_models
        self.max_hops = max_hops

        # Maps: model_name → hop_count
        self.reachable_models: Dict[str, int] = {}
        # Maps: entity_name → hop_count
        self.reachable_entities: Dict[str, int] = {}

        self._build_graph()

    def _build_graph(self) -> None:
        """Build reachability map using BFS traversal."""
        # Find base model
        base_model = find_model_by_primary_entity(
            self.base_entity,
            self.all_models
        )

        if not base_model:
            # Invalid base entity - reachable sets remain empty
            return

        # Initialize BFS
        queue: deque = deque([(base_model, 0)])
        visited: set = {base_model.name}

        # Mark base as reachable
        self.reachable_models[base_model.name] = 0
        self.reachable_entities[self.base_entity] = 0

        while queue:
            current_model, depth = queue.popleft()

            # Respect max hop limit
            if depth >= self.max_hops:
                continue

            # Traverse foreign key entities
            for entity in current_model.entities:
                if entity.type != "foreign":
                    continue

                # Find target model with this entity as primary
                target_model = find_model_by_primary_entity(
                    entity.name,
                    self.all_models
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
        """Check if semantic model is reachable from base entity.

        Args:
            model_name: Name of the semantic model

        Returns:
            True if model is reachable, False otherwise
        """
        return model_name in self.reachable_models

    def is_entity_reachable(self, entity_name: str) -> bool:
        """Check if entity is reachable from base entity.

        Args:
            entity_name: Name of the entity

        Returns:
            True if entity is reachable, False otherwise
        """
        return entity_name in self.reachable_entities

    def get_hop_count(self, model_name: str) -> Optional[int]:
        """Get number of hops to reach model.

        Args:
            model_name: Name of the semantic model

        Returns:
            Number of hops (0 for base model), or None if unreachable
        """
        return self.reachable_models.get(model_name)

    def get_reachable_models(self) -> Dict[str, int]:
        """Get all reachable models with their hop counts.

        Returns:
            Dictionary mapping model_name to hop_count
        """
        return self.reachable_models.copy()
```

---

## Appendix B: Test Fixtures

### Example Test Data

```python
# fixtures/validation_test_data.py

from dbt_to_lookml.schemas import (
    Entity, Dimension, Measure, SemanticModel
)
from dbt_to_lookml.types import AggregationType, DimensionType


# Simple 2-model setup: rentals -> users
RENTALS_MODEL = SemanticModel(
    name="rental_orders",
    model="ref('rental_orders')",
    entities=[
        Entity(name="rental", type="primary"),
        Entity(name="user", type="foreign")  # FK to users
    ],
    measures=[
        Measure(name="rental_count", agg=AggregationType.COUNT),
        Measure(name="total_revenue", agg=AggregationType.SUM, expr="amount")
    ]
)

USERS_MODEL = SemanticModel(
    name="users",
    model="ref('users')",
    entities=[
        Entity(name="user", type="primary")
    ],
    measures=[
        Measure(name="user_count", agg=AggregationType.COUNT)
    ]
)

# Isolated model (no foreign keys)
SESSIONS_MODEL = SemanticModel(
    name="sessions",
    model="ref('sessions')",
    entities=[
        Entity(name="session", type="primary")
    ],
    measures=[
        Measure(name="session_count", agg=AggregationType.COUNT)
    ]
)

# Multi-hop setup: rentals -> searches -> sessions
SEARCHES_MODEL = SemanticModel(
    name="searches",
    model="ref('searches')",
    entities=[
        Entity(name="search", type="primary"),
        Entity(name="session", type="foreign"),  # FK to sessions
        Entity(name="rental", type="foreign")    # FK to rentals
    ],
    measures=[
        Measure(name="search_count", agg=AggregationType.COUNT)
    ]
)
```

---

## Summary

This implementation strategy provides a comprehensive plan for adding entity connectivity validation to dbt-to-lookml. The design prioritizes:

1. **Separation of Concerns**: Standalone validation module
2. **Reusability**: Extract and generalize existing join graph logic
3. **User Experience**: Rich error messages with actionable suggestions
4. **Testing**: 95%+ coverage with unit and integration tests
5. **Performance**: < 100ms for typical projects
6. **Backward Compatibility**: No breaking changes

The phased implementation approach ensures DTL-023 and DTL-024 dependencies are satisfied before beginning, and delivers functionality incrementally with thorough testing at each phase.
