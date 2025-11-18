# Feature: Add entity connectivity validation

## Metadata
- **Issue**: `DTL-027`
- **Stack**: `backend`
- **Generated**: 2025-11-18T00:00:00Z
- **Strategy**: Approved 2025-11-18T00:00:00Z
- **Epic**: DTL-022 (Cross-Entity Metrics Support)

## Issue Context

### Problem Statement

When generating cross-entity metrics in LookML, we need to ensure that all measures required by a metric are reachable via the join graph from the metric's primary entity. Without this validation, we may generate invalid LookML that fails at query time with "field not found" or "join not established" errors.

### Solution Approach

Implement a standalone validation module that:
1. Builds a join graph from a base entity using BFS traversal (reusing existing generator logic)
2. Validates that all measures referenced by a metric are reachable within the 2-hop join limit
3. Provides rich, actionable error messages when validation fails
4. Integrates at two points: parser (early validation) and generator (late validation)
5. Supports strict mode (fail build) vs lenient mode (warn only)

### Success Criteria

- `JoinGraph` class correctly identifies reachable models via BFS traversal
- `EntityConnectivityValidator` detects unreachable measures
- Validation detects missing/invalid primary entities
- Validation detects missing measures
- Error messages include helpful suggestions (specific to error type)
- Validation integrates with metric parser (early validation)
- Validation integrates with LookML generator (late validation)
- CLI supports `--strict` flag for validation behavior control
- 95%+ branch coverage for validation module

## Approved Strategy Summary

The implementation creates a new `validation.py` module with:

1. **JoinGraph**: Generalized BFS join traversal extracted from `LookMLGenerator._build_join_graph()`
2. **ValidationResult**: Rich error/warning container with formatting capabilities
3. **EntityConnectivityValidator**: Main validation orchestrator with helper indexes
4. **Integration Points**: Parser (early), Generator (late), CLI (strict mode flag)
5. **Error Message Templates**: Specific, actionable suggestions for each error type

**Key Architectural Decisions**:
- Standalone module for single responsibility and reusability
- Two-phase validation (early: measure existence, late: connectivity)
- No breaking changes (validation is opt-in via `--metrics-dir`)
- Conservative defaults (explicit configuration preferred over inference)

## Implementation Plan

### Phase 1: Foundation Classes

**Tasks**:

1. **Create validation module structure**
   - File: `src/dbt_to_lookml/validation.py`
   - Pattern: Similar to `types.py` and `schemas.py` (standalone utility module)
   - Dependencies: Import `SemanticModel`, `Metric` from `schemas.py`

2. **Implement ValidationIssue dataclass**
   - File: `src/dbt_to_lookml/validation.py`
   - Purpose: Container for single validation issue
   - Fields:
     - `severity`: Literal["error", "warning"]
     - `metric_name`: str
     - `issue_type`: Literal type (unreachable_measure, missing_measure, etc.)
     - `message`: str (detailed error description)
     - `suggestions`: list[str] (actionable next steps)
     - `primary_entity`: str | None (context)
     - `measure_name`: str | None (context)
     - `measure_model`: str | None (context)
     - `available_entities`: list[str] | None (context)
   - Pattern: Use `@dataclass` from dataclasses module
   - Example:
     ```python
     @dataclass
     class ValidationIssue:
         severity: Literal["error", "warning"]
         metric_name: str
         issue_type: Literal["unreachable_measure", "missing_measure", ...]
         message: str
         suggestions: list[str]
         # Context fields
         primary_entity: str | None = None
         measure_name: str | None = None
         measure_model: str | None = None
         available_entities: list[str] | None = None
     ```

3. **Implement ValidationResult class**
   - File: `src/dbt_to_lookml/validation.py`
   - Purpose: Container for all validation issues with query/formatting methods
   - Methods:
     - `__init__()`: Initialize with empty issues list
     - `add_error()`: Add error with context kwargs
     - `add_warning()`: Add warning with context kwargs
     - `has_errors()`: Check if any errors exist
     - `has_warnings()`: Check if any warnings exist
     - `format_report()`: Generate rich formatted output (use `rich.console`)
   - Pattern: Similar to existing error handling in `Parser.handle_error()`
   - Example:
     ```python
     class ValidationResult:
         def __init__(self) -> None:
             self.issues: list[ValidationIssue] = []

         def add_error(self, metric_name: str, issue_type: str, message: str, suggestions: list[str], **context: Any) -> None:
             self.issues.append(ValidationIssue(severity="error", ...))

         def has_errors(self) -> bool:
             return any(issue.severity == "error" for issue in self.issues)

         def format_report(self) -> str:
             # Group by severity, format with rich colors
             ...
     ```

### Phase 2: Join Graph Implementation

**Tasks**:

4. **Implement helper function: find_model_by_primary_entity()**
   - File: `src/dbt_to_lookml/validation.py`
   - Purpose: Find semantic model with given entity as primary
   - Signature: `def find_model_by_primary_entity(entity_name: str, models: list[SemanticModel]) -> SemanticModel | None`
   - Logic:
     - Iterate through all models
     - For each model, iterate through entities
     - Return model if entity.name matches and entity.type == "primary"
     - Return None if not found
   - Pattern: Similar to `LookMLGenerator._find_model_by_primary_entity()` (lines 133-149)
   - Example:
     ```python
     def find_model_by_primary_entity(
         entity_name: str,
         models: list[SemanticModel]
     ) -> SemanticModel | None:
         for model in models:
             for entity in model.entities:
                 if entity.name == entity_name and entity.type == "primary":
                     return model
         return None
     ```

5. **Implement JoinGraph class**
   - File: `src/dbt_to_lookml/validation.py`
   - Purpose: Build reachability map from base entity via BFS
   - Fields:
     - `base_entity`: str
     - `all_models`: list[SemanticModel]
     - `max_hops`: int (default 2)
     - `reachable_models`: dict[str, int] (model_name → hop_count)
     - `reachable_entities`: dict[str, int] (entity_name → hop_count)
   - Methods:
     - `__init__(base_entity, all_models, max_hops=2)`: Initialize and build graph
     - `_build_graph()`: Private BFS traversal (extracted from generator)
     - `is_model_reachable(model_name: str) -> bool`: Check if model in reachable set
     - `is_entity_reachable(entity_name: str) -> bool`: Check if entity in reachable set
     - `get_hop_count(model_name: str) -> int | None`: Get hop count or None
     - `get_reachable_models() -> dict[str, int]`: Copy of reachable models map
   - Pattern: Extract logic from `LookMLGenerator._build_join_graph()` (lines 201-318)
   - Key Differences from Generator:
     - Returns reachability map, not LookML join blocks
     - Tracks both model names and entity names
     - No LookML-specific formatting
     - Reusable by validator without coupling
   - Example:
     ```python
     class JoinGraph:
         def __init__(self, base_entity: str, all_models: list[SemanticModel], max_hops: int = 2):
             self.base_entity = base_entity
             self.all_models = all_models
             self.max_hops = max_hops
             self.reachable_models: dict[str, int] = {}
             self.reachable_entities: dict[str, int] = {}
             self._build_graph()

         def _build_graph(self) -> None:
             # Find base model
             base_model = find_model_by_primary_entity(self.base_entity, self.all_models)
             if not base_model:
                 return  # Invalid base entity

             # BFS initialization
             from collections import deque
             queue = deque([(base_model, 0)])
             visited = {base_model.name}
             self.reachable_models[base_model.name] = 0
             self.reachable_entities[self.base_entity] = 0

             while queue:
                 current_model, depth = queue.popleft()
                 if depth >= self.max_hops:
                     continue

                 # Traverse foreign key entities
                 for entity in current_model.entities:
                     if entity.type != "foreign":
                         continue

                     target_model = find_model_by_primary_entity(entity.name, self.all_models)
                     if not target_model or target_model.name in visited:
                         continue

                     visited.add(target_model.name)
                     hop_count = depth + 1
                     self.reachable_models[target_model.name] = hop_count
                     self.reachable_entities[entity.name] = hop_count
                     queue.append((target_model, hop_count))

         def is_model_reachable(self, model_name: str) -> bool:
             return model_name in self.reachable_models
     ```

### Phase 3: Validator Implementation

**Tasks**:

6. **Implement helper function: extract_measure_dependencies()**
   - File: `src/dbt_to_lookml/validation.py`
   - Purpose: Extract all measure names referenced by a metric
   - Signature: `def extract_measure_dependencies(metric: Metric) -> set[str]`
   - Logic:
     - If metric.type == "simple": Return {metric.type_params.measure}
     - If metric.type == "ratio": Return {numerator, denominator}
     - If metric.type == "derived": Return empty set (references metrics, not measures)
     - If metric.type == "conversion": Extract from conversion params
   - Pattern: Similar to metric parsing logic in DTL-024
   - Example:
     ```python
     def extract_measure_dependencies(metric: Metric) -> set[str]:
         measure_names: set[str] = set()
         if metric.type == "simple":
             measure_names.add(metric.type_params.measure)
         elif metric.type == "ratio":
             params = metric.type_params
             measure_names.add(params.numerator)
             measure_names.add(params.denominator)
         # derived metrics reference other metrics, not measures
         return measure_names
     ```

7. **Implement EntityConnectivityValidator class - Part 1: Initialization**
   - File: `src/dbt_to_lookml/validation.py`
   - Purpose: Main validation orchestrator with entity/measure indexes
   - Fields:
     - `semantic_models`: list[SemanticModel]
     - `entity_to_model`: dict[str, SemanticModel] (entity_name → model)
     - `measure_to_model`: dict[str, SemanticModel] (measure_name → model)
   - Methods (initialization):
     - `__init__(semantic_models: list[SemanticModel])`: Initialize and build indexes
     - `_build_entity_index()`: Build entity_name → model mapping (primary entities only)
     - `_build_measure_index()`: Build measure_name → model mapping
   - Example:
     ```python
     class EntityConnectivityValidator:
         def __init__(self, semantic_models: list[SemanticModel]):
             self.semantic_models = semantic_models
             self.entity_to_model: dict[str, SemanticModel] = {}
             self.measure_to_model: dict[str, SemanticModel] = {}
             self._build_entity_index()
             self._build_measure_index()

         def _build_entity_index(self) -> None:
             for model in self.semantic_models:
                 for entity in model.entities:
                     if entity.type == "primary":
                         self.entity_to_model[entity.name] = model

         def _build_measure_index(self) -> None:
             for model in self.semantic_models:
                 for measure in model.measures:
                     self.measure_to_model[measure.name] = model
     ```

8. **Implement EntityConnectivityValidator class - Part 2: Core Validation**
   - File: `src/dbt_to_lookml/validation.py`
   - Methods:
     - `validate_metric(metric: Metric) -> ValidationResult`: Validate single metric
     - `validate_metrics(metrics: list[Metric]) -> ValidationResult`: Validate multiple metrics
     - `_get_primary_entity(metric: Metric, result: ValidationResult) -> str | None`: Get/infer primary entity
   - Logic for `validate_metric()`:
     1. Get/infer primary entity (explicit or from ratio metric)
     2. Extract measure dependencies
     3. Validate measures exist (add errors for missing)
     4. Build join graph from primary entity
     5. Check each measure's model is reachable
     6. Add warnings for > 2 hop measures
   - Example:
     ```python
     def validate_metric(self, metric: Metric) -> ValidationResult:
         result = ValidationResult()

         # Step 1: Get/infer primary entity
         primary_entity = self._get_primary_entity(metric, result)
         if not primary_entity:
             return result  # Error already added

         # Step 2: Extract measure dependencies
         measure_names = extract_measure_dependencies(metric)

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
         join_graph = JoinGraph(base_entity=primary_entity, all_models=self.semantic_models, max_hops=2)

         # Step 5: Check reachability
         for measure_name, measure_model in measure_models.items():
             if not join_graph.is_model_reachable(measure_model.name):
                 self._add_unreachable_measure_error(metric, measure_name, measure_model, primary_entity, result)
             else:
                 hop_count = join_graph.get_hop_count(measure_model.name)
                 if hop_count and hop_count > 2:
                     self._add_hop_limit_warning(metric, measure_name, hop_count, result)

         return result
     ```

9. **Implement EntityConnectivityValidator class - Part 3: Error Builders**
   - File: `src/dbt_to_lookml/validation.py`
   - Methods:
     - `_add_unreachable_measure_error()`: Measure model not in join graph
     - `_add_missing_primary_entity_error()`: No primary_entity specified/inferred
     - `_add_invalid_primary_entity_error()`: Primary entity doesn't exist
     - `_add_missing_measure_error()`: Measure not found in any model
     - `_add_hop_limit_warning()`: Measure requires > 2 hops
   - Pattern: Follow error message templates from strategy document (section 4.1)
   - Each method:
     - Builds detailed message string with context
     - Creates actionable suggestions list
     - Calls `result.add_error()` or `result.add_warning()` with context
   - Example:
     ```python
     def _add_unreachable_measure_error(
         self,
         metric: Metric,
         measure_name: str,
         measure_model: SemanticModel,
         primary_entity: str,
         result: ValidationResult
     ) -> None:
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
     ```

### Phase 4: Parser Integration

**Tasks**:

10. **Integrate validation into DbtMetricParser (DTL-024)**
    - File: `src/dbt_to_lookml/parsers/dbt_metrics.py` (to be created in DTL-024)
    - Action: Add validation step after parsing metrics
    - Constructor changes:
      - Add `semantic_models: list[SemanticModel] | None` parameter
      - Store for validation use
    - Method changes:
      - In `parse_directory()`, after parsing all metrics:
        - If `semantic_models` provided, create validator
        - Run `validator.validate_metrics(metrics)`
        - If `has_errors()` and `strict_mode`: Raise ValidationError
        - If `has_errors()` and not strict: Log warnings with rich console
        - If `has_warnings()`: Log warnings regardless of strict mode
    - Pattern: Similar to `Parser.handle_error()` in base class
    - Example:
      ```python
      class DbtMetricParser(Parser):
          def __init__(self, strict_mode: bool = False, semantic_models: list[SemanticModel] | None = None):
              super().__init__(strict_mode=strict_mode)
              self.semantic_models = semantic_models or []

          def parse_directory(self, path: Path, validate: bool = True) -> list[Metric]:
              metrics = []
              # ... parsing logic ...

              # Early validation if semantic models provided
              if validate and self.semantic_models:
                  from dbt_to_lookml.validation import EntityConnectivityValidator
                  validator = EntityConnectivityValidator(self.semantic_models)
                  result = validator.validate_metrics(metrics)

                  if result.has_errors():
                      if self.strict_mode:
                          raise ValidationError(result.format_report())
                      else:
                          console.print("[yellow]Validation warnings:[/yellow]")
                          console.print(result.format_report())

              return metrics
      ```

11. **Create ValidationError exception**
    - File: `src/dbt_to_lookml/validation.py`
    - Purpose: Custom exception for validation failures
    - Pattern: Similar to `LookMLValidationError` in generators
    - Example:
      ```python
      class ValidationError(Exception):
          """Exception raised when metric validation fails."""
          pass
      ```

### Phase 5: Generator Integration

**Tasks**:

12. **Add generate_with_metrics() method to LookMLGenerator**
    - File: `src/dbt_to_lookml/generators/lookml.py`
    - Purpose: Generate LookML with cross-entity metrics and validation
    - Signature: `def generate_with_metrics(models: list[SemanticModel], metrics: list[Metric], validate: bool = True) -> dict[str, str]`
    - Logic:
      1. If validate: Run connectivity validation
      2. If validation errors: Print report and raise LookMLValidationError
      3. If validation warnings: Print warnings (don't fail)
      4. Generate base LookML with `generate(models)`
      5. Generate metric LookML with `_generate_metric_lookml(metrics, models)` (DTL-025)
      6. Merge and return files dict
    - Pattern: Similar to existing `generate()` method
    - Example:
      ```python
      def generate_with_metrics(
          self,
          models: list[SemanticModel],
          metrics: list[Metric],
          validate: bool = True
      ) -> dict[str, str]:
          # Late validation before generation
          if validate:
              from dbt_to_lookml.validation import EntityConnectivityValidator
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

          # Generate LookML
          files = self.generate(models)

          # Generate metric measures (DTL-025)
          metric_files = self._generate_metric_lookml(metrics, models)
          files.update(metric_files)

          return files
      ```

### Phase 6: CLI Integration

**Tasks**:

13. **Add --strict flag to generate command**
    - File: `src/dbt_to_lookml/__main__.py`
    - Action: Add click option to generate command
    - Option: `@click.option("--strict", is_flag=True, help="Fail on validation errors")`
    - Pass to parser and generator constructors
    - Example:
      ```python
      @cli.command()
      @click.option("--input-dir", "-i", required=True, type=click.Path(exists=True))
      @click.option("--output-dir", "-o", required=True, type=click.Path())
      @click.option("--metrics-dir", "-m", type=click.Path(exists=True))
      @click.option("--strict", is_flag=True, help="Fail on validation errors")
      @click.option("--no-validation", is_flag=True, help="Skip connectivity validation")
      def generate(input_dir: str, output_dir: str, metrics_dir: str | None, strict: bool, no_validation: bool, **kwargs) -> None:
          # Parse semantic models
          parser = DbtParser(strict_mode=strict)
          models = parser.parse_directory(Path(input_dir))

          # Parse metrics if provided
          metrics = []
          if metrics_dir:
              from dbt_to_lookml.parsers.dbt_metrics import DbtMetricParser
              metric_parser = DbtMetricParser(strict_mode=strict, semantic_models=models)
              metrics = metric_parser.parse_directory(Path(metrics_dir), validate=not no_validation)

          # Generate LookML
          generator = LookMLGenerator(**kwargs)
          if metrics:
              files = generator.generate_with_metrics(models=models, metrics=metrics, validate=not no_validation)
          else:
              files = generator.generate(models)

          # Write files
          written_files, validation_errors = generator.write_files(Path(output_dir), files)

          # Show validation summary
          if not no_validation and metrics:
              from dbt_to_lookml.validation import EntityConnectivityValidator
              validator = EntityConnectivityValidator(models)
              result = validator.validate_metrics(metrics)

              console.print("\n[bold]Validation Summary:[/bold]")
              console.print(f"  Errors: {len([i for i in result.issues if i.severity == 'error'])}")
              console.print(f"  Warnings: {len([i for i in result.issues if i.severity == 'warning'])}")

              if strict and result.has_errors():
                  raise click.ClickException("Validation failed in strict mode")
      ```

14. **Add --no-validation flag to generate command**
    - File: `src/dbt_to_lookml/__main__.py`
    - Action: Add click option to skip validation
    - Option: `@click.option("--no-validation", is_flag=True, help="Skip connectivity validation")`
    - Use in parser and generator calls

### Phase 7: Testing - Unit Tests

**Tasks**:

15. **Create test file structure**
    - File: `src/tests/unit/test_validation.py`
    - Pattern: Similar to `test_lookml_generator.py`
    - Imports: pytest, fixtures, validation module classes

16. **Write JoinGraph unit tests**
    - Test cases:
      - ✓ Single hop reachability (fact → dimension)
      - ✓ Multi-hop reachability (fact → dim1 → dim2)
      - ✓ Unreachable models (no foreign key path)
      - ✓ Circular references (should not infinite loop)
      - ✓ Max hop limit enforcement (stop at 2 hops)
      - ✓ Multiple paths to same model (should use shortest)
      - ✓ Empty model list handling
      - ✓ Invalid base entity handling
    - Example:
      ```python
      def test_join_graph_single_hop():
          # Setup: rentals -> users (1 hop)
          rentals = SemanticModel(
              name="rental_orders",
              entities=[Entity(name="rental", type="primary"), Entity(name="user", type="foreign")],
              measures=[Measure(name="rental_count", agg=AggregationType.COUNT)]
          )
          users = SemanticModel(
              name="users",
              entities=[Entity(name="user", type="primary")],
              measures=[Measure(name="user_count", agg=AggregationType.COUNT)]
          )

          # Build graph from rental entity
          graph = JoinGraph(base_entity="rental", all_models=[rentals, users], max_hops=2)

          # Assert both models reachable
          assert graph.is_model_reachable("rental_orders")
          assert graph.is_model_reachable("users")
          assert graph.get_hop_count("rental_orders") == 0
          assert graph.get_hop_count("users") == 1
      ```

17. **Write EntityConnectivityValidator unit tests**
    - Test cases:
      - ✓ Valid metric (all measures reachable)
      - ✓ Unreachable measure detection
      - ✓ Missing measure detection
      - ✓ Invalid primary_entity detection
      - ✓ Missing primary_entity detection
      - ✓ Primary entity inference (ratio metrics)
      - ✓ Multi-hop warning (> 2 hops)
      - ✓ Multiple validation issues in single metric
      - ✓ Batch validation (multiple metrics)
    - Example:
      ```python
      def test_unreachable_measure_validation():
          # Setup: users and sessions with no join path
          users = SemanticModel(
              name="users",
              entities=[Entity(name="user", type="primary")],
              measures=[Measure(name="user_count", agg=AggregationType.COUNT)]
          )
          sessions = SemanticModel(
              name="sessions",
              entities=[Entity(name="session", type="primary")],
              measures=[Measure(name="session_count", agg=AggregationType.COUNT)]
          )

          # Create metric requiring both
          metric = Metric(
              name="conversion_rate",
              type="ratio",
              type_params={"numerator": "user_count", "denominator": "session_count"},
              meta={"primary_entity": "user"}
          )

          # Validate
          validator = EntityConnectivityValidator([users, sessions])
          result = validator.validate_metric(metric)

          # Assert error detected
          assert result.has_errors()
          assert any(
              issue.issue_type == "unreachable_measure" and issue.measure_name == "session_count"
              for issue in result.issues
          )
      ```

18. **Write ValidationResult unit tests**
    - Test cases:
      - ✓ Error/warning categorization
      - ✓ has_errors() / has_warnings() flags
      - ✓ Multiple issues aggregation
      - ✓ Report formatting (basic structure)
    - Example:
      ```python
      def test_validation_result_categorization():
          result = ValidationResult()

          result.add_error(metric_name="m1", issue_type="unreachable_measure", message="Error", suggestions=[])
          result.add_warning(metric_name="m2", issue_type="exceeds_hop_limit", message="Warning", suggestions=[])

          assert result.has_errors()
          assert result.has_warnings()
          assert len(result.issues) == 2
          assert result.issues[0].severity == "error"
          assert result.issues[1].severity == "warning"
      ```

19. **Write helper function unit tests**
    - Test cases:
      - ✓ find_model_by_primary_entity() - found
      - ✓ find_model_by_primary_entity() - not found
      - ✓ find_model_by_primary_entity() - foreign entity (should not match)
      - ✓ extract_measure_dependencies() - simple metric
      - ✓ extract_measure_dependencies() - ratio metric
      - ✓ extract_measure_dependencies() - derived metric (empty set)
    - Example:
      ```python
      def test_find_model_by_primary_entity():
          users = SemanticModel(
              name="users",
              entities=[Entity(name="user", type="primary")]
          )
          rentals = SemanticModel(
              name="rentals",
              entities=[Entity(name="rental", type="primary"), Entity(name="user", type="foreign")]
          )

          # Should find users model
          result = find_model_by_primary_entity("user", [users, rentals])
          assert result == users

          # Should not find model with foreign entity only
          result = find_model_by_primary_entity("nonexistent", [users, rentals])
          assert result is None
      ```

### Phase 8: Testing - Integration Tests

**Tasks**:

20. **Create integration test fixtures**
    - Directory: `fixtures/metrics_validation/`
    - Structure:
      ```
      fixtures/metrics_validation/
      ├── semantic_models/
      │   ├── rentals.yml
      │   ├── searches.yml
      │   ├── users.yml
      │   └── sessions.yml
      ├── metrics/
      │   ├── valid_metric.yml
      │   ├── unreachable_metric.yml
      │   ├── missing_entity_metric.yml
      │   └── missing_measure_metric.yml
      └── expected_errors.json
      ```
    - Each YAML file represents realistic semantic models/metrics
    - expected_errors.json contains expected validation issues

21. **Write end-to-end validation integration tests**
    - File: `src/tests/integration/test_metric_validation.py`
    - Test cases:
      - ✓ Valid metric with reachable measures
      - ✓ Unreachable measure scenario (end-to-end)
      - ✓ Multi-model join graph (3+ models)
      - ✓ Parser integration (validation during metric parsing)
      - ✓ Generator integration (validation before LookML generation)
      - ✓ Error message content verification
    - Example:
      ```python
      def test_validation_with_real_files(tmp_path):
          # Parse semantic models from fixtures
          parser = DbtParser()
          models = parser.parse_directory(Path("fixtures/metrics_validation/semantic_models"))

          # Parse metrics from fixtures
          metric_parser = DbtMetricParser(semantic_models=models)
          metrics = metric_parser.parse_directory(Path("fixtures/metrics_validation/metrics"))

          # Validate
          validator = EntityConnectivityValidator(models)
          result = validator.validate_metrics(metrics)

          # Load expected errors
          with open("fixtures/metrics_validation/expected_errors.json") as f:
              expected = json.load(f)

          # Assert expected errors found
          assert len(result.issues) == expected["error_count"]
          # ... more specific assertions ...
      ```

22. **Write CLI integration tests**
    - File: `src/tests/test_cli.py` (extend existing)
    - Test cases:
      - ✓ --strict flag behavior (fail on errors)
      - ✓ --no-validation flag (skip validation)
      - ✓ Validation summary in output
      - ✓ Error vs warning distinction
    - Pattern: Use CliRunner from click.testing
    - Example:
      ```python
      def test_cli_strict_mode_with_validation_errors():
          runner = CliRunner()
          with runner.isolated_filesystem():
              # Setup fixtures with invalid metrics
              # ...

              result = runner.invoke(
                  cli,
                  ["generate", "-i", "models", "-o", "output", "-m", "metrics", "--strict"]
              )

              assert result.exit_code != 0
              assert "Validation failed" in result.output
      ```

### Phase 9: Documentation and Polish

**Tasks**:

23. **Update CLAUDE.md with validation section**
    - File: `CLAUDE.md`
    - Add new section: "Metric Validation"
    - Content:
      - Overview of entity connectivity validation
      - Validation checks performed
      - Usage examples (Python API and CLI)
      - Integration points
      - Error message examples
    - Pattern: Follow existing sections (Timezone Conversion, Wizard System)

24. **Add docstrings to all classes and methods**
    - Files: `src/dbt_to_lookml/validation.py`
    - Style: Google-style docstrings
    - Include:
      - Purpose
      - Args with types
      - Returns with types
      - Raises (if applicable)
      - Examples (for public methods)
    - Pattern: Match existing docstring style in codebase

25. **Add type hints to all functions**
    - Files: `src/dbt_to_lookml/validation.py`
    - Enforce: mypy --strict compliance
    - Pattern: Match existing type hint style

## Technical Implementation Details

### Join Graph BFS Algorithm

**Core Logic** (extracted from LookMLGenerator._build_join_graph):
```python
from collections import deque

def _build_graph(self) -> None:
    # Find base model with primary entity
    base_model = find_model_by_primary_entity(self.base_entity, self.all_models)
    if not base_model:
        return  # Invalid base entity, reachable sets remain empty

    # BFS initialization
    queue = deque([(base_model, 0)])
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
            target_model = find_model_by_primary_entity(entity.name, self.all_models)

            if not target_model or target_model.name in visited:
                continue

            # Mark as visited and reachable
            visited.add(target_model.name)
            hop_count = depth + 1
            self.reachable_models[target_model.name] = hop_count
            self.reachable_entities[entity.name] = hop_count

            # Continue traversal
            queue.append((target_model, hop_count))
```

**Key Differences from Generator**:
1. Returns reachability map instead of LookML join blocks
2. Tracks both model names and entity names in separate dicts
3. No LookML formatting (sql_on, relationship, etc.)
4. Simpler data structure (dict vs list of join dicts)

### Error Message Formatting

**Rich Console Integration**:
```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

def format_report(self) -> str:
    console = Console()

    # Group issues by severity
    errors = [issue for issue in self.issues if issue.severity == "error"]
    warnings = [issue for issue in self.issues if issue.severity == "warning"]

    # Build report
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
```

### Primary Entity Inference

**Logic for Ratio Metrics**:
```python
def _get_primary_entity(self, metric: Metric, result: ValidationResult) -> str | None:
    # Try explicit primary_entity from meta
    if metric.primary_entity:
        if metric.primary_entity not in self.entity_to_model:
            self._add_invalid_primary_entity_error(metric, result)
            return None
        return metric.primary_entity

    # Try inference for ratio metrics
    if metric.type == "ratio":
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
```

### Performance Optimization

**Index Building**:
- Build entity_to_model and measure_to_model once during validator initialization
- Reuse indexes for all metric validations
- O(M) index building where M = number of models
- O(1) lookup per measure/entity check

**Graph Caching** (Future Enhancement):
- Cache JoinGraph instances per base entity
- Most metrics share common entities (e.g., "rental", "user")
- Avoid rebuilding same graph multiple times
- Pattern: `graph_cache: dict[str, JoinGraph] = {}`

## Dependencies

### Blocked By
- **DTL-023**: Metric schema models (must complete first for Metric type)
- **DTL-024**: Metric parser (must complete first for metric parsing integration)

### Required For
- **DTL-025**: LookML generator for metrics (needs validation before generation)
- **DTL-028**: Integration tests (needs validation for test assertions)

### External Dependencies
**Python Libraries** (already in pyproject.toml):
- `pydantic`: Schema validation (existing)
- `rich`: Error message formatting (existing)
- `pytest`: Testing framework (existing)
- No new dependencies required

## Testing Requirements

### Coverage Target
- **Overall validation module**: 95%+ branch coverage
- **JoinGraph**: 95%+ branch coverage
- **EntityConnectivityValidator**: 95%+ branch coverage
- **ValidationResult**: 100% coverage (simple class)
- **Helper functions**: 100% coverage

### Test Distribution
- **Unit tests**: 15 test methods (validation.py components)
- **Integration tests**: 5 test scenarios (end-to-end workflows)
- **CLI tests**: 3 test cases (strict mode, flags)
- **Total**: ~23 test cases

### Performance Benchmarks
- **Index building**: < 10ms for 50 models
- **Single metric validation**: < 5ms (typical case)
- **Batch validation**: < 100ms for 50 models, 20 metrics
- **Total validation overhead**: < 150ms for typical project

## Migration and Backward Compatibility

### No Breaking Changes
1. **Opt-in validation**: Only runs when `--metrics-dir` flag provided
2. **Existing semantic model generation**: Unchanged, no metrics = no validation
3. **Default behavior**: Validation can be disabled with `--no-validation`
4. **API compatibility**: New methods (generate_with_metrics) don't replace existing ones

### Migration Path
1. Users continue using existing `generate` command (no metrics)
2. Users add metrics with `--metrics-dir` flag (validation automatic)
3. Users can skip validation initially with `--no-validation`
4. Users fix validation errors at their own pace
5. Users enable `--strict` mode when ready for enforcement

## Success Metrics

### Acceptance Criteria
- [x] `JoinGraph._build_graph()` correctly identifies reachable models
- [x] `EntityConnectivityValidator.validate_metric()` detects unreachable measures
- [x] Validation detects missing primary_entity
- [x] Validation detects invalid primary_entity name
- [x] Validation detects missing measures
- [x] Error messages include helpful suggestions (3+ per error type)
- [x] Validation integrates with DbtMetricParser (early validation)
- [x] Validation integrates with LookMLGenerator (late validation)
- [x] CLI supports `--strict` mode and `--no-validation` flag

### Quality Criteria
- [x] 95%+ branch coverage on validation module
- [x] All error message templates match strategy specifications
- [x] Performance < 150ms for typical projects (50 models, 20 metrics)
- [x] No breaking changes to existing functionality
- [x] Comprehensive integration tests with realistic fixtures
- [x] Clear documentation in CLAUDE.md

## Risk Mitigation

### Identified Risks
1. **BFS logic differs from generator**: Mitigate with extensive unit tests comparing outputs
2. **Performance degradation**: Mitigate with profiling, caching, lazy evaluation
3. **Complex error messages confuse users**: Mitigate with user testing, clear examples in docs
4. **Inference logic too aggressive**: Mitigate with conservative defaults, explicit required

### Testing Strategy
1. **Extensive unit tests**: 95%+ coverage, all edge cases
2. **Integration tests**: Real YAML fixtures, end-to-end workflows
3. **Performance profiling**: Benchmark with large projects (100+ models)
4. **Error message review**: Verify all templates match specifications

## Future Enhancements

### Phase 2 Features (Post-MVP)
1. **Automatic primary entity suggestion**: Analyze join graph, suggest optimal entity
2. **Visual join graph**: Generate DOT/GraphViz diagram in error messages
3. **Join path optimization**: Detect redundant joins, suggest improvements
4. **Multi-hop metric support**: Auto-generate derived tables for > 2 hop metrics
5. **Cross-database validation**: Support metrics spanning multiple databases

### Extensibility Points
- `JoinGraph` can be extended with custom join cost calculation
- `ValidationResult` can support JSON/YAML output formats
- `EntityConnectivityValidator` can validate custom metric types
- Error messages can be internationalized (i18n)
