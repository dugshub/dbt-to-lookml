---
id: DTL-033-spec
issue: DTL-033
title: "Implementation Specification: Add group_item_label support for cleaner timeframe labels"
created: 2025-11-19
status: ready
---

# DTL-033: Implementation Specification

## Executive Summary

This specification details the implementation of optional `group_item_label` support for LookML dimension_groups, enabling cleaner timeframe labels using Liquid templating. The feature transforms repetitive labels like "Rental Created Date", "Rental Created Month" into concise "Date", "Month" labels while preserving hierarchical organization.

**Key Points:**
- **Scope:** Schema updates, generator changes, CLI integration, comprehensive testing
- **Effort:** 14 hours (1.75 days) across 6 phases
- **Complexity:** Medium - follows established patterns (convert_tz, hidden)
- **Risk:** Low - opt-in feature with backward compatibility guaranteed

## Technical Design

### Architecture Overview

The implementation follows the existing multi-level configuration pattern established for `convert_tz` and `hidden` parameters, ensuring consistency across the codebase.

```
Configuration Flow:
┌─────────────────────────────────────────────────────────┐
│ Dimension YAML (config.meta.use_group_item_label)      │ ← Highest Priority
├─────────────────────────────────────────────────────────┤
│ LookMLGenerator Parameter (use_group_item_label)       │
├─────────────────────────────────────────────────────────┤
│ CLI Flag (--use-group-item-label / --no-...)           │
├─────────────────────────────────────────────────────────┤
│ Default (False - backward compatible)                   │ ← Lowest Priority
└─────────────────────────────────────────────────────────┘

Data Flow:
CLI/API
  ↓ (--use-group-item-label flag)
LookMLGenerator.__init__(use_group_item_label=True)
  ↓ (stored as instance variable)
LookMLGenerator._generate_view_lookml()
  ↓ (passed to to_lookml_dict)
SemanticModel.to_lookml_dict(use_group_item_label=True)
  ↓ (passed to each time dimension)
Dimension.to_lookml_dict(default_use_group_item_label=True)
  ↓ (passed to dimension group conversion)
Dimension._to_dimension_group_dict(default_use_group_item_label=True)
  ↓ (checks metadata override, applies precedence logic)
Generated LookML with group_item_label Liquid template
```

### Liquid Template Design

**Core Template:**
```lookml
group_item_label: "{% assign tf = _field._name | remove: '{dimension_name}_' | replace: '_', ' ' | capitalize %}{{ tf }}"
```

**Template Mechanics:**

1. **Input:** `_field._name` (LookML special variable containing full field name)
   - Example: `rental_date_month`

2. **Processing Steps:**
   - `remove: 'rental_date_'` → Strips dimension group prefix → `month`
   - `replace: '_', ' '` → Replaces underscores with spaces → `month` (no change)
   - `capitalize` → Capitalizes first letter → `Month`

3. **Output:** Clean timeframe label → "Month"

**Multi-word Timeframe Handling:**

| Field Name | After Remove | After Replace | After Capitalize | Final Label |
|------------|--------------|---------------|------------------|-------------|
| `created_at_date` | `date` | `date` | `Date` | Date |
| `created_at_month` | `month` | `month` | `Month` | Month |
| `created_at_fiscal_quarter` | `fiscal_quarter` | `fiscal quarter` | `Fiscal quarter` | Fiscal quarter |
| `booking_time_hour` | `hour` | `hour` | `Hour` | Hour |
| `booking_time_raw` | `raw` | `raw` | `Raw` | Raw |

**Note:** For multi-word timeframes (e.g., `fiscal_quarter`), the template capitalizes only the first word. This is acceptable for v1 and can be enhanced in the future if needed.

### Precedence Logic

Following the exact pattern from `convert_tz` implementation:

```python
# Three-tier precedence (lowest to highest):
# 1. Hardcoded default: False
# 2. Generator/CLI parameter: default_use_group_item_label
# 3. Dimension-level metadata: config.meta.use_group_item_label

use_group_item_label = False  # Start with hardcoded default
if default_use_group_item_label is not None:
    use_group_item_label = default_use_group_item_label  # Override with generator setting
if (self.config and self.config.meta and
    self.config.meta.use_group_item_label is not None):
    use_group_item_label = self.config.meta.use_group_item_label  # Final override
```

## Implementation Details

### Phase 1: Schema Foundation (Est. 2 hours)

#### File: `src/dbt_to_lookml/schemas/config.py`

**Change 1.1: Add `use_group_item_label` field to `ConfigMeta`**

Location: Line 97 (after `bi_field` field)

```python
class ConfigMeta(BaseModel):
    """Metadata configuration for semantic model elements.

    Supports flexible metadata configuration for dimensions and measures, including
    optional hierarchy labels, data governance tags, and feature-specific overrides
    like timezone conversion.

    Attributes:
        # ... existing docstring content ...
        use_group_item_label: Control group_item_label generation for dimension_groups.
            - True: Generate group_item_label with Liquid template for clean labels
            - False/None: No group_item_label parameter (default behavior)
            When enabled, timeframe fields display as "Date", "Month", "Quarter"
            instead of repeating the full dimension group name.
            This provides the highest-priority override in the configuration
            precedence chain (dimension > generator > CLI > default).

    Example:
        Dimension with group_item_label override:

        ```yaml
        config:
          meta:
            domain: "events"
            owner: "analytics"
            use_group_item_label: yes  # Enable clean labels for this dimension
            hierarchy:
              entity: "event"
              category: "timing"
        ```

    See Also:
        CLAUDE.md: "Field Label Customization (group_item_label)" section for
            detailed precedence rules and usage examples.
    """

    domain: str | None = None
    owner: str | None = None
    contains_pii: bool | None = None
    update_frequency: str | None = None
    # Support both flat structure (subject, category) and nested (hierarchy)
    subject: str | None = None
    category: str | None = None
    hierarchy: Hierarchy | None = None
    convert_tz: bool | None = None
    hidden: bool | None = None
    bi_field: bool | None = None
    use_group_item_label: bool | None = None  # NEW FIELD
```

**Validation:**
- Run: `pytest src/tests/unit/test_schemas.py::TestConfig -xvs`
- Verify: Pydantic accepts new field without breaking existing schemas
- Test: Create dimension with `use_group_item_label: true` in YAML and parse successfully

### Phase 2: Core Logic Implementation (Est. 3 hours)

#### File: `src/dbt_to_lookml/schemas/semantic_layer.py`

**Change 2.1: Update `Dimension.to_lookml_dict()` signature**

Location: Lines 125-138 (existing method)

```python
def to_lookml_dict(
    self,
    default_convert_tz: bool | None = None,
    default_use_group_item_label: bool | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
    """Convert dimension to LookML format.

    Converts semantic model dimension to LookML dictionary representation,
    handling both categorical dimensions and time dimension_groups with
    appropriate configuration.

    Args:
        default_convert_tz: Optional default timezone conversion setting
            from generator. Only applies to time dimensions. Overridden by
            dimension-level config.meta.convert_tz if present.
        default_use_group_item_label: Optional default group_item_label
            setting from generator. Only applies to time dimensions. When
            True, generates Liquid template for clean timeframe labels.
            Overridden by dimension-level config.meta.use_group_item_label.

    Returns:
        Dictionary with dimension or dimension_group configuration for
        LookML generation.

    Example:
        Time dimension with group_item_label enabled:

        ```python
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"}
        )
        result = dimension.to_lookml_dict(
            default_use_group_item_label=True
        )
        # Returns dimension_group dict with group_item_label Liquid template
        ```
    """
    if self.type == DimensionType.TIME:
        return self._to_dimension_group_dict(
            default_convert_tz=default_convert_tz,
            default_use_group_item_label=default_use_group_item_label  # NEW PARAMETER
        )
    else:
        return self._to_dimension_dict()
```

**Change 2.2: Update `Dimension._to_dimension_group_dict()` signature and logic**

Location: Lines 220-322 (existing method)

```python
def _to_dimension_group_dict(
    self,
    default_convert_tz: bool | None = None,
    default_use_group_item_label: bool | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
    """Convert time dimension to LookML dimension_group.

    Generates a LookML dimension_group block with appropriate timeframes
    based on the dimension's time_granularity setting. Supports timezone
    conversion and group_item_label configuration through multi-level
    precedence:

    Timezone Conversion Precedence:
    1. Dimension-level override via config.meta.convert_tz (highest priority)
    2. Generator default via default_convert_tz parameter
    3. Hardcoded default of False (lowest priority)

    Group Item Label Precedence:
    1. Dimension-level override via config.meta.use_group_item_label (highest)
    2. Generator default via default_use_group_item_label parameter
    3. Hardcoded default of False (lowest priority, backward compatible)

    Args:
        default_convert_tz: Default timezone conversion setting from
            generator or CLI.
            - True: Enable timezone conversion for all dimensions
              (unless overridden)
            - False: Disable timezone conversion (default behavior)
            - None: Use generator default (False)
        default_use_group_item_label: Default group_item_label setting from
            generator or CLI.
            - True: Generate group_item_label with Liquid template
            - False: No group_item_label parameter (default, backward compatible)
            - None: Use generator default (False)

    Returns:
        Dictionary with dimension_group configuration including:
        - name: Dimension name
        - type: "time"
        - timeframes: List of appropriate timeframes based on granularity
        - sql: SQL expression for the timestamp column
        - convert_tz: "yes" or "no" based on precedence rules
        - group_item_label: Liquid template (if enabled)
        - description: Optional description
        - label: Optional label
        - view_label/group_label: Optional hierarchy labels

    Example:
        Dimension with metadata override (enables group_item_label):

        ```python
        dimension = Dimension(
            name="rental_date",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(
                use_group_item_label=True  # Override any generator default
            ))
        )
        result = dimension._to_dimension_group_dict(
            default_use_group_item_label=False
        )
        # Result includes:
        # "group_item_label": "{% assign tf = _field._name | remove: 'rental_date_' | replace: '_', ' ' | capitalize %}{{ tf }}"
        ```

        Dimension without override (uses generator default):

        ```python
        dimension = Dimension(
            name="booking_timestamp",
            type=DimensionType.TIME,
            type_params={"time_granularity": "hour"}
        )
        result = dimension._to_dimension_group_dict(
            default_use_group_item_label=True
        )
        # Result includes group_item_label (from default parameter)
        ```

    See Also:
        CLAUDE.md: "Field Label Customization (group_item_label)" section
            for detailed precedence rules and usage examples.
    """
    # Determine timeframes based on granularity
    timeframes = self._get_timeframes()

    result: dict[str, Any] = {
        "name": self.name,
        "type": "time",
        "timeframes": timeframes,
        "sql": self.expr or f"${{TABLE}}.{self.name}",
    }

    if self.description:
        result["description"] = self.description
    if self.label:
        result["label"] = self.label

    # Add hierarchy labels
    view_label, group_label = self.get_dimension_labels()
    if view_label:
        result["view_label"] = view_label
    if group_label:
        result["group_label"] = group_label

    # Determine convert_tz with three-tier precedence:
    # 1. Dimension-level meta.convert_tz (highest priority if present)
    # 2. default_convert_tz parameter (if provided)
    # 3. Hardcoded default: False (lowest priority, explicit and safe)
    convert_tz = False  # Default
    if default_convert_tz is not None:
        convert_tz = default_convert_tz
    if self.config and self.config.meta and self.config.meta.convert_tz is not None:
        convert_tz = self.config.meta.convert_tz

    result["convert_tz"] = "yes" if convert_tz else "no"

    # NEW LOGIC: Determine use_group_item_label with three-tier precedence
    # 1. Dimension-level meta.use_group_item_label (highest priority if present)
    # 2. default_use_group_item_label parameter (if provided)
    # 3. Hardcoded default: False (lowest priority, backward compatible)
    use_group_item_label = False  # Default
    if default_use_group_item_label is not None:
        use_group_item_label = default_use_group_item_label
    if (self.config and self.config.meta and
        self.config.meta.use_group_item_label is not None):
        use_group_item_label = self.config.meta.use_group_item_label

    # Generate Liquid template for group_item_label if enabled
    if use_group_item_label:
        # Template extracts timeframe name from field name:
        # Field: {dimension_name}_{timeframe} → Label: {Timeframe}
        # Example: rental_date_month → Month
        result["group_item_label"] = (
            "{% assign tf = _field._name | remove: '" + self.name + "_' | "
            "replace: '_', ' ' | capitalize %}{{ tf }}"
        )

    # Add hidden parameter if specified
    if self.config and self.config.meta and self.config.meta.hidden is True:
        result["hidden"] = "yes"

    return result
```

**Change 2.3: Update `SemanticModel.to_lookml_dict()` signature and propagation**

Location: Find the method in semantic_layer.py (around line 450+)

```python
def to_lookml_dict(
    self,
    schema: str = "",
    convert_tz: bool | None = None,
    use_group_item_label: bool | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
    """Convert entire semantic model to lkml views format.

    Transforms semantic model with entities, dimensions, and measures into
    LookML view dictionary structure suitable for file generation.

    Args:
        schema: Optional database schema name to prepend to table name
            in sql_table_name parameter.
        convert_tz: Optional timezone conversion setting passed to time
            dimensions as default. Individual dimensions can override via
            config.meta.convert_tz.
        use_group_item_label: Optional group_item_label setting passed to
            time dimensions as default. Individual dimensions can override
            via config.meta.use_group_item_label. When enabled, generates
            Liquid templates for cleaner timeframe labels.

    Returns:
        Dictionary with LookML view configuration including dimensions,
        dimension_groups, measures, and sets.

    Example:
        Generate view with group_item_label enabled:

        ```python
        model = SemanticModel(name="orders", ...)
        view_dict = model.to_lookml_dict(
            schema="analytics",
            use_group_item_label=True
        )
        # All time dimensions get group_item_label templates
        ```
    """
    dimensions = []
    dimension_groups = []
    measures = []

    # ... existing entity conversion logic ...

    # Convert dimensions (time vs categorical)
    for dim in self.dimensions:
        if dim.type == DimensionType.TIME:
            dim_dict = dim.to_lookml_dict(
                default_convert_tz=convert_tz,
                default_use_group_item_label=use_group_item_label  # NEW PARAMETER
            )
            dimension_groups.append(dim_dict)
        else:
            dim_dict = dim.to_lookml_dict()
            dimensions.append(dim_dict)

    # ... rest of existing logic for measures, sets, etc. ...
```

**Testing for Phase 2:**
- Unit tests for `_to_dimension_group_dict()` with all precedence scenarios
- Unit tests for `to_lookml_dict()` parameter propagation
- Unit tests for Liquid template generation correctness
- Target: 100% branch coverage for new logic paths

### Phase 3: Generator Integration (Est. 2 hours)

#### File: `src/dbt_to_lookml/generators/lookml.py`

**Change 3.1: Add `use_group_item_label` parameter to `__init__()`**

Location: Lines 26-38 (existing __init__ signature)

```python
def __init__(
    self,
    view_prefix: str = "",
    explore_prefix: str = "",
    validate_syntax: bool = True,
    format_output: bool = True,
    schema: str = "",
    connection: str = "redshift_test",
    model_name: str = "semantic_model",
    convert_tz: bool | None = None,
    use_bi_field_filter: bool = False,
    use_group_item_label: bool = False,  # NEW PARAMETER
    fact_models: list[str] | None = None,
) -> None:
    """Initialize the generator.

    Configures LookML generation with support for timezone conversion,
    field visibility control, view/explore naming, syntax validation, and
    output formatting.

    Args:
        view_prefix: Prefix to add to all generated view names. Useful
            for namespacing views by environment or project.
        explore_prefix: Prefix to add to all generated explore names.
            Works alongside view_prefix for consistent naming conventions.
        validate_syntax: Whether to validate generated LookML syntax
            using the lkml library. Validation runs automatically unless
            explicitly disabled.
        format_output: Whether to format LookML output for human
            readability. Applies consistent indentation and spacing to
            generated files.
        schema: Database schema name for sql_table_name in generated
            views. Used to qualify table references (e.g., "public.orders").
        connection: Looker connection name for the generated .model.lkml
            file. This tells Looker which database connection to use for
            the model.
        model_name: Name for the generated model file (without
            .model.lkml extension). Allows multiple models to be generated
            from different semantic model sets.
        convert_tz: Default timezone conversion setting for all
            dimension_groups. Controls the convert_tz parameter in generated
            LookML dimension_groups.
            - True: Enable timezone conversion globally (convert_tz: yes)
            - False: Disable timezone conversion globally (convert_tz: no)
            - None: Use hardcoded default (False, disabled by default)
            This setting is overridden by per-dimension config.meta.convert_tz
            in semantic models, allowing fine-grained control at the
            dimension level.
        use_bi_field_filter: Whether to filter explore fields based on
            config.meta.bi_field settings.
            - False (default): All fields included in explores (backward compatible)
            - True: Only fields with bi_field: true included (selective exposure)
            Primary keys (entities) are always included regardless of setting.
        use_group_item_label: Whether to add group_item_label to dimension_groups
            for cleaner timeframe labels. When enabled, timeframes display as
            "Date", "Month", "Quarter" instead of repeating the dimension group name.
            Uses Liquid templating to extract timeframe name from field name.
            - False (default): No group_item_label (backward compatible)
            - True: Generate group_item_label with Liquid template
            This setting is overridden by per-dimension
            config.meta.use_group_item_label in semantic models.
        fact_models: Optional list of model names to generate explores for.
            If provided, only these models will have explores generated.
            If None, no explores will be generated.
            Join relationships are discovered automatically via foreign keys.

    Example:
        Enable group_item_label globally:

        ```python
        generator = LookMLGenerator(
            view_prefix="fact_",
            use_group_item_label=True
        )
        ```

        Combine with other features:

        ```python
        generator = LookMLGenerator(
            view_prefix="dim_",
            convert_tz=True,
            use_group_item_label=True,
            use_bi_field_filter=True
        )
        ```

    See Also:
        CLAUDE.md: "Field Label Customization (group_item_label)" section.
    """
    self.view_prefix = view_prefix
    self.explore_prefix = explore_prefix
    self.validate_syntax = validate_syntax
    self.format_output = format_output
    self.schema = schema
    self.connection = connection
    self.model_name = model_name
    self.convert_tz = convert_tz
    self.use_bi_field_filter = use_bi_field_filter
    self.use_group_item_label = use_group_item_label  # NEW INSTANCE VARIABLE
    self.fact_models = fact_models or []
```

**Change 3.2: Propagate to view generation**

Location: Find `_generate_view_lookml()` method (around line 150-200)

```python
def _generate_view_lookml(self, model: SemanticModel) -> str:
    """Generate LookML for a single view.

    Args:
        model: Semantic model to convert to LookML view.

    Returns:
        LookML string for the view file.
    """
    # Apply prefix to model name if configured
    prefixed_model = self._apply_prefix_to_model(model)

    # Convert to LookML dict with all configuration options
    view_dict = prefixed_model.to_lookml_dict(
        schema=self.schema,
        convert_tz=self.convert_tz,
        use_group_item_label=self.use_group_item_label  # NEW PARAMETER
    )

    # ... rest of method ...
```

**Testing for Phase 3:**
- Unit test: Verify `use_group_item_label` parameter stored correctly
- Unit test: Verify default value is False
- Integration test: Verify propagation to view generation
- Integration test: Generated LookML contains group_item_label when enabled

### Phase 4: CLI Integration (Est. 2 hours)

#### File: `src/dbt_to_lookml/__main__.py`

**Change 4.1: Add CLI flags**

Location: Add after existing `--no-convert-tz` flag in `generate` command (around line 100-150)

```python
@cli.command(cls=RichCommand)
@click.option(
    "-i", "--input-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Directory containing semantic model YAML files",
)
# ... other existing options ...
@click.option(
    "--convert-tz",
    is_flag=True,
    default=False,
    help="Enable timezone conversion for all dimension_groups (convert_tz: yes)",
)
@click.option(
    "--no-convert-tz",
    is_flag=True,
    default=False,
    help="Explicitly disable timezone conversion (convert_tz: no)",
)
@click.option(
    "--use-group-item-label",
    is_flag=True,
    default=False,
    help="Add group_item_label to dimension_groups for cleaner timeframe labels "
         "(e.g., 'Date', 'Month' instead of 'Rental Created Date', 'Rental Created Month')",
)
@click.option(
    "--no-group-item-label",
    is_flag=True,
    default=False,
    help="Explicitly disable group_item_label (useful to override defaults)",
)
# ... rest of options ...
def generate(
    input_dir: Path,
    output_dir: Path,
    schema: str,
    view_prefix: str,
    explore_prefix: str,
    connection: str,
    model_name: str,
    preview: bool,
    yes: bool,
    dry_run: bool,
    no_validation: bool,
    show_summary: bool,
    convert_tz: bool,
    no_convert_tz: bool,
    use_group_item_label: bool,  # NEW PARAMETER
    no_group_item_label: bool,  # NEW PARAMETER
    fact_models: str,
    use_bi_field_filter: bool,
) -> None:
    """Generate LookML files from semantic models.

    Parses semantic model YAML files from INPUT_DIR and generates
    corresponding LookML view and explore files in OUTPUT_DIR. Supports
    extensive configuration options for customizing output, including
    prefixes, schema qualification, timezone handling, field visibility,
    and label customization.

    Examples:

        Basic generation with schema:

            dbt-to-lookml generate -i semantic_models/ -o build/lookml -s public

        With cleaner timeframe labels:

            dbt-to-lookml generate -i models/ -o lookml/ -s analytics --use-group-item-label

        Full configuration:

            dbt-to-lookml generate \\
                -i semantic_models/ \\
                -o build/lookml/ \\
                -s analytics \\
                --view-prefix fact_ \\
                --convert-tz \\
                --use-group-item-label \\
                --fact-models rentals,orders
    """
    # Validate mutually exclusive flags for convert_tz
    if convert_tz and no_convert_tz:
        raise click.UsageError(
            "Cannot use both --convert-tz and --no-convert-tz"
        )

    # NEW: Validate mutually exclusive flags for group_item_label
    if use_group_item_label and no_group_item_label:
        raise click.UsageError(
            "Cannot use both --use-group-item-label and --no-group-item-label"
        )

    # Determine convert_tz setting
    convert_tz_setting: bool | None = None
    if convert_tz:
        convert_tz_setting = True
    elif no_convert_tz:
        convert_tz_setting = False
    # else: None (use default/dimension-level settings)

    # NEW: Determine group_item_label setting
    group_item_label_setting: bool | None = None
    if use_group_item_label:
        group_item_label_setting = True
    elif no_group_item_label:
        group_item_label_setting = False
    # else: None (use default/dimension-level settings)

    # ... existing parsing logic ...

    # Parse semantic models
    parser = DbtParser()
    models = parser.parse_directory(str(input_dir))

    # ... existing model filtering/validation ...

    # Process fact_models
    fact_models_list: list[str] | None = None
    if fact_models:
        fact_models_list = [m.strip() for m in fact_models.split(",")]

    # Create generator with all configuration
    generator = LookMLGenerator(
        view_prefix=view_prefix,
        explore_prefix=explore_prefix,
        validate_syntax=not no_validation,
        format_output=True,
        schema=schema,
        connection=connection,
        model_name=model_name,
        convert_tz=convert_tz_setting,
        use_bi_field_filter=use_bi_field_filter,
        use_group_item_label=group_item_label_setting,  # NEW PARAMETER
        fact_models=fact_models_list,
    )

    # ... rest of generation logic ...
```

**Testing for Phase 4:**
- CLI test: Verify `--use-group-item-label` flag enables feature
- CLI test: Verify default behavior (no flag) doesn't add group_item_label
- CLI test: Verify mutual exclusion of `--use-group-item-label` and `--no-group-item-label`
- CLI test: Verify generated files contain group_item_label when flag used

### Phase 5: Comprehensive Testing (Est. 4 hours)

#### 5.1 Unit Tests

**File:** `src/tests/unit/test_schemas.py`

Add to `TestDimension` class:

```python
class TestDimension:
    """Tests for Dimension model."""

    # ... existing tests ...

    def test_dimension_group_with_group_item_label_enabled(self) -> None:
        """Test group_item_label is added when enabled via parameter."""
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        result = dimension._to_dimension_group_dict(
            default_use_group_item_label=True
        )

        assert "group_item_label" in result
        expected_template = (
            "{% assign tf = _field._name | remove: 'created_at_' | "
            "replace: '_', ' ' | capitalize %}{{ tf }}"
        )
        assert result["group_item_label"] == expected_template

    def test_dimension_group_with_group_item_label_disabled(self) -> None:
        """Test group_item_label is not added when disabled (default)."""
        dimension = Dimension(
            name="updated_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        result = dimension._to_dimension_group_dict(
            default_use_group_item_label=False
        )

        assert "group_item_label" not in result

    def test_dimension_group_item_label_metadata_override_enable(self) -> None:
        """Test dimension-level metadata overrides generator default to enable."""
        dimension = Dimension(
            name="shipped_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(use_group_item_label=True)  # Override
            ),
        )

        # Even with False default, metadata override should enable it
        result = dimension._to_dimension_group_dict(
            default_use_group_item_label=False
        )

        assert "group_item_label" in result
        assert "{% assign tf = _field._name" in result["group_item_label"]
        assert "remove: 'shipped_at_'" in result["group_item_label"]

    def test_dimension_group_item_label_metadata_override_disable(self) -> None:
        """Test dimension-level metadata can disable when generator enables."""
        dimension = Dimension(
            name="deleted_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(use_group_item_label=False)  # Override
            ),
        )

        # Even with True default, metadata override should disable it
        result = dimension._to_dimension_group_dict(
            default_use_group_item_label=True
        )

        assert "group_item_label" not in result

    def test_dimension_group_item_label_default_none(self) -> None:
        """Test no group_item_label when parameter is None (default)."""
        dimension = Dimension(
            name="processed_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        result = dimension._to_dimension_group_dict()

        assert "group_item_label" not in result

    def test_group_item_label_template_structure(self) -> None:
        """Test Liquid template generates correct structure for various names."""
        test_cases = [
            ("rental_date", "rental_date_"),
            ("booking_timestamp", "booking_timestamp_"),
            ("user_signup_time", "user_signup_time_"),
            ("created_at", "created_at_"),
        ]

        for dim_name, expected_remove in test_cases:
            dimension = Dimension(
                name=dim_name,
                type=DimensionType.TIME,
            )

            result = dimension._to_dimension_group_dict(
                default_use_group_item_label=True
            )

            template = result["group_item_label"]

            # Verify template structure
            assert "{% assign tf = _field._name" in template
            assert f"remove: '{expected_remove}'" in template
            assert "replace: '_', ' '" in template
            assert "capitalize" in template
            assert "{{ tf }}" in template

    def test_group_item_label_with_other_parameters(self) -> None:
        """Test group_item_label works alongside other dimension parameters."""
        dimension = Dimension(
            name="event_time",
            type=DimensionType.TIME,
            type_params={"time_granularity": "hour"},
            description="Event occurrence timestamp",
            label="Event Time",
            config=Config(
                meta=ConfigMeta(
                    use_group_item_label=True,
                    convert_tz=True,
                    hierarchy={"entity": "event", "category": "timing"}
                )
            ),
        )

        result = dimension._to_dimension_group_dict(
            default_convert_tz=False,
            default_use_group_item_label=False
        )

        # Verify all parameters coexist correctly
        assert result["name"] == "event_time"
        assert result["type"] == "time"
        assert result["description"] == "Event occurrence timestamp"
        assert result["label"] == "Event Time"
        assert result["view_label"] == "Event"
        assert result["group_label"] == "Timing"
        assert result["convert_tz"] == "yes"
        assert "group_item_label" in result
        assert "remove: 'event_time_'" in result["group_item_label"]
```

**File:** `src/tests/unit/test_lookml_generator.py`

Add to `TestLookMLGenerator` class:

```python
class TestLookMLGenerator:
    """Tests for LookMLGenerator."""

    # ... existing tests ...

    def test_generator_use_group_item_label_parameter(self) -> None:
        """Test use_group_item_label parameter is stored."""
        generator = LookMLGenerator(use_group_item_label=True)

        assert generator.use_group_item_label is True

    def test_generator_use_group_item_label_default(self) -> None:
        """Test use_group_item_label defaults to False."""
        generator = LookMLGenerator()

        assert generator.use_group_item_label is False

    def test_generator_propagates_group_item_label_to_views(self) -> None:
        """Test generator propagates use_group_item_label to view generation."""
        from dbt_to_lookml.schemas import (
            Dimension,
            DimensionType,
            Entity,
            SemanticModel,
        )

        model = SemanticModel(
            name="test_model",
            model="ref('test_table')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                )
            ],
        )

        generator = LookMLGenerator(use_group_item_label=True)
        files = generator.generate([model])

        # Get the generated view content
        view_content = files["test_model.view.lkml"]

        # Verify group_item_label is present
        assert "group_item_label:" in view_content
        assert "_field._name" in view_content
        assert "remove: 'created_at_'" in view_content
```

#### 5.2 Integration Tests

**File:** `src/tests/integration/test_group_item_label.py` (NEW FILE)

```python
"""Integration tests for group_item_label feature.

Tests end-to-end generation of group_item_label in LookML dimension_groups,
including CLI flag behavior, metadata overrides, and Liquid template correctness.
"""

from pathlib import Path

import lkml
import pytest

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.schemas.config import Config, ConfigMeta
from dbt_to_lookml.schemas.semantic_layer import (
    Dimension,
    DimensionType,
    Entity,
    SemanticModel,
)


class TestGroupItemLabelIntegration:
    """Integration tests for group_item_label in dimension_groups."""

    def test_group_item_label_enabled_globally(self, tmp_path: Path) -> None:
        """Test group_item_label generation when enabled globally."""
        # Create sample semantic model with multiple time dimensions
        model = SemanticModel(
            name="test_events",
            model="ref('events')",
            entities=[Entity(name="event_id", type="primary")],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                ),
                Dimension(
                    name="updated_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "hour"},
                ),
            ],
        )

        # Generate with group_item_label enabled
        generator = LookMLGenerator(
            use_group_item_label=True,
            schema="public",
        )
        files = generator.generate([model])

        # Parse generated LookML
        content = files["test_events.view.lkml"]
        parsed = lkml.load(content)
        dimension_groups = parsed["views"][0]["dimension_groups"]

        # Verify all dimension_groups have group_item_label
        assert len(dimension_groups) == 2

        for dg in dimension_groups:
            assert "group_item_label" in dg, (
                f"dimension_group {dg['name']} missing group_item_label"
            )

            # Verify template structure
            template = dg["group_item_label"]
            assert "_field._name" in template
            assert "remove:" in template
            assert f"remove: '{dg['name']}_'" in template
            assert "capitalize" in template

    def test_group_item_label_disabled_globally(self, tmp_path: Path) -> None:
        """Test no group_item_label when disabled globally (default)."""
        model = SemanticModel(
            name="test_events",
            model="ref('events')",
            entities=[Entity(name="event_id", type="primary")],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                ),
            ],
        )

        # Generate with default settings (group_item_label disabled)
        generator = LookMLGenerator(
            use_group_item_label=False,
            schema="public",
        )
        files = generator.generate([model])

        # Parse generated LookML
        content = files["test_events.view.lkml"]
        parsed = lkml.load(content)
        dimension_groups = parsed["views"][0]["dimension_groups"]

        # Verify no dimension_groups have group_item_label
        for dg in dimension_groups:
            assert "group_item_label" not in dg, (
                f"dimension_group {dg['name']} unexpectedly has group_item_label"
            )

    def test_group_item_label_dimension_level_override(self, tmp_path: Path) -> None:
        """Test dimension-level metadata overrides generator setting."""
        # Create model with mixed group_item_label settings
        model = SemanticModel(
            name="test_model",
            model="ref('test_table')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                # This one enables group_item_label via metadata
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                    config=Config(meta=ConfigMeta(use_group_item_label=True)),
                ),
                # This one uses generator default (False)
                Dimension(
                    name="updated_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "hour"},
                ),
                # This one explicitly disables via metadata
                Dimension(
                    name="deleted_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                    config=Config(meta=ConfigMeta(use_group_item_label=False)),
                ),
            ],
        )

        # Generator has use_group_item_label=False (default)
        generator = LookMLGenerator(use_group_item_label=False)

        files = generator.generate([model])
        content = files["test_model.view.lkml"]
        parsed = lkml.load(content)

        dimension_groups = parsed["views"][0]["dimension_groups"]
        dg_dict = {dg["name"]: dg for dg in dimension_groups}

        # created_at should have group_item_label (metadata override)
        assert "group_item_label" in dg_dict["created_at"]
        assert "remove: 'created_at_'" in dg_dict["created_at"]["group_item_label"]

        # updated_at should NOT have group_item_label (uses generator default)
        assert "group_item_label" not in dg_dict["updated_at"]

        # deleted_at should NOT have group_item_label (metadata override)
        assert "group_item_label" not in dg_dict["deleted_at"]

    def test_group_item_label_liquid_template_validation(self, tmp_path: Path) -> None:
        """Test that generated Liquid templates are syntactically valid LookML."""
        test_cases = [
            "created_at",
            "booking_date",
            "rental_timestamp",
            "user_signup_datetime",
        ]

        for dim_name in test_cases:
            model = SemanticModel(
                name="test_model",
                model="ref('test_table')",
                entities=[Entity(name="id", type="primary")],
                dimensions=[
                    Dimension(
                        name=dim_name,
                        type=DimensionType.TIME,
                        type_params={"time_granularity": "day"},
                    )
                ],
            )

            generator = LookMLGenerator(use_group_item_label=True)
            files = generator.generate([model])

            content = files["test_model.view.lkml"]

            # Verify template contains dimension name
            assert f"remove: '{dim_name}_'" in content

            # Verify LookML is valid
            parsed = lkml.load(content)
            assert parsed is not None

    def test_group_item_label_with_hierarchy_labels(self, tmp_path: Path) -> None:
        """Test group_item_label works alongside hierarchy labels."""
        model = SemanticModel(
            name="test_model",
            model="ref('test_table')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                    config=Config(
                        meta=ConfigMeta(
                            use_group_item_label=True,
                            hierarchy={"entity": "event", "category": "timing"},
                        )
                    ),
                )
            ],
        )

        generator = LookMLGenerator(use_group_item_label=True)
        files = generator.generate([model])

        content = files["test_model.view.lkml"]
        parsed = lkml.load(content)

        dg = parsed["views"][0]["dimension_groups"][0]

        # Verify all labels coexist
        assert dg["view_label"] == "Event"
        assert dg["group_label"] == "Timing"
        assert "group_item_label" in dg
        assert "remove: 'created_at_'" in dg["group_item_label"]

    @pytest.mark.parametrize(
        "granularity,expected_timeframes",
        [
            ("day", ["date", "week", "month", "quarter", "year"]),
            ("hour", ["time", "hour", "date", "week", "month", "quarter", "year"]),
            ("month", ["month", "quarter", "year"]),
        ],
    )
    def test_group_item_label_with_various_granularities(
        self, tmp_path: Path, granularity: str, expected_timeframes: list[str]
    ) -> None:
        """Test group_item_label works with all time granularities."""
        model = SemanticModel(
            name="test_model",
            model="ref('test_table')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(
                    name="event_time",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": granularity},
                )
            ],
        )

        generator = LookMLGenerator(use_group_item_label=True)
        files = generator.generate([model])

        content = files["test_model.view.lkml"]
        parsed = lkml.load(content)

        dg = parsed["views"][0]["dimension_groups"][0]

        # Verify timeframes match granularity
        assert dg["timeframes"] == expected_timeframes

        # Verify group_item_label present regardless of granularity
        assert "group_item_label" in dg
        assert "remove: 'event_time_'" in dg["group_item_label"]
```

#### 5.3 Golden Tests

**File:** `src/tests/test_golden.py`

Add test to verify backward compatibility:

```python
class TestGoldenFiles:
    """Tests that verify golden file outputs."""

    # ... existing tests ...

    def test_golden_group_item_label_disabled_by_default(self) -> None:
        """Test that golden files don't have group_item_label (backward compat).

        Since use_group_item_label defaults to False, golden files should
        not contain group_item_label unless explicitly enabled in test data.
        This ensures backward compatibility and opt-in behavior.
        """
        # Find all golden view files
        golden_dir = Path(__file__).parent / "golden"
        golden_files = list(golden_dir.glob("expected_*.view.lkml"))

        assert len(golden_files) > 0, "No golden view files found"

        for golden_file in golden_files:
            content = golden_file.read_text()

            # Golden files should not have group_item_label (feature disabled by default)
            assert "group_item_label:" not in content, (
                f"Golden file {golden_file.name} unexpectedly has "
                f"group_item_label (feature should be opt-in)"
            )
```

#### 5.4 CLI Tests

**File:** `src/tests/test_cli.py`

Add to CLI test class:

```python
class TestCLIGenerate:
    """Tests for generate command."""

    # ... existing tests ...

    def test_generate_with_use_group_item_label_flag(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test --use-group-item-label flag enables feature."""
        # Create sample semantic model directory
        input_dir = tmp_path / "semantic_models"
        input_dir.mkdir()

        model_yaml = """
semantic_model:
  name: test_events
  model: ref('events')
  entities:
    - name: event_id
      type: primary
  dimensions:
    - name: created_at
      type: time
      type_params:
        time_granularity: day
"""
        (input_dir / "events.yml").write_text(model_yaml)

        output_dir = tmp_path / "output"

        result = runner.invoke(
            cli,
            [
                "generate",
                "-i", str(input_dir),
                "-o", str(output_dir),
                "-s", "public",
                "--use-group-item-label",
            ],
        )

        assert result.exit_code == 0

        # Check generated files contain group_item_label
        view_files = list(output_dir.glob("*.view.lkml"))
        assert len(view_files) > 0

        for view_file in view_files:
            content = view_file.read_text()
            if "dimension_group:" in content:
                assert "group_item_label:" in content
                assert "_field._name" in content

    def test_generate_without_group_item_label_flag(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test default behavior does not add group_item_label."""
        # Create sample semantic model directory
        input_dir = tmp_path / "semantic_models"
        input_dir.mkdir()

        model_yaml = """
semantic_model:
  name: test_events
  model: ref('events')
  entities:
    - name: event_id
      type: primary
  dimensions:
    - name: created_at
      type: time
      type_params:
        time_granularity: day
"""
        (input_dir / "events.yml").write_text(model_yaml)

        output_dir = tmp_path / "output"

        result = runner.invoke(
            cli,
            [
                "generate",
                "-i", str(input_dir),
                "-o", str(output_dir),
                "-s", "public",
            ],
        )

        assert result.exit_code == 0

        # Check generated files do not contain group_item_label
        view_files = list(output_dir.glob("*.view.lkml"))

        for view_file in view_files:
            content = view_file.read_text()
            assert "group_item_label:" not in content

    def test_generate_mutually_exclusive_group_item_label_flags(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that --use-group-item-label and --no-group-item-label are exclusive."""
        input_dir = tmp_path / "semantic_models"
        input_dir.mkdir()

        output_dir = tmp_path / "output"

        result = runner.invoke(
            cli,
            [
                "generate",
                "-i", str(input_dir),
                "-o", str(output_dir),
                "-s", "public",
                "--use-group-item-label",
                "--no-group-item-label",
            ],
        )

        assert result.exit_code != 0
        assert "Cannot use both" in result.output

    def test_generate_with_no_group_item_label_flag(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test --no-group-item-label explicitly disables feature."""
        input_dir = tmp_path / "semantic_models"
        input_dir.mkdir()

        model_yaml = """
semantic_model:
  name: test_events
  model: ref('events')
  entities:
    - name: event_id
      type: primary
  dimensions:
    - name: created_at
      type: time
      type_params:
        time_granularity: day
"""
        (input_dir / "events.yml").write_text(model_yaml)

        output_dir = tmp_path / "output"

        result = runner.invoke(
            cli,
            [
                "generate",
                "-i", str(input_dir),
                "-o", str(output_dir),
                "-s", "public",
                "--no-group-item-label",
            ],
        )

        assert result.exit_code == 0

        # Verify no group_item_label in output
        view_files = list(output_dir.glob("*.view.lkml"))
        for view_file in view_files:
            content = view_file.read_text()
            assert "group_item_label:" not in content
```

**Coverage Target:**
- Overall: 95%+ branch coverage
- New code paths: 100% coverage
- All precedence scenarios tested

### Phase 6: Validation and Documentation (Est. 1 hour)

#### 6.1 Test Execution

```bash
# Run all tests
make test-full

# Check coverage
make test-coverage

# Verify specific test modules
pytest src/tests/unit/test_schemas.py::TestDimension::test_dimension_group_with_group_item_label_enabled -xvs
pytest src/tests/integration/test_group_item_label.py -xvs
pytest src/tests/test_cli.py::TestCLIGenerate::test_generate_with_use_group_item_label_flag -xvs
```

#### 6.2 Manual Testing

```bash
# Test with sample semantic models
mkdir -p test_data/semantic_models

# Create sample YAML
cat > test_data/semantic_models/events.yml <<EOF
semantic_model:
  name: user_events
  model: ref('events')
  entities:
    - name: event_id
      type: primary
  dimensions:
    - name: created_at
      type: time
      type_params:
        time_granularity: day
    - name: rental_date
      type: time
      type_params:
        time_granularity: hour
      config:
        meta:
          use_group_item_label: false  # Test override
EOF

# Generate with flag
dbt-to-lookml generate \
  -i test_data/semantic_models/ \
  -o test_data/output/ \
  -s public \
  --use-group-item-label

# Inspect output
cat test_data/output/user_events.view.lkml | grep -A 5 "dimension_group:"
```

Expected output snippet:
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
  group_item_label: "{% assign tf = _field._name | remove: 'created_at_' | replace: '_', ' ' | capitalize %}{{ tf }}"
}

dimension_group: rental_date {
  type: time
  timeframes: [time, hour, date, week, month, quarter, year]
  sql: ${TABLE}.rental_date ;;
  convert_tz: no
  # No group_item_label (overridden by metadata)
}
```

## Edge Cases and Special Scenarios

### 1. Dimension Names with Multiple Underscores

**Scenario:** Dimension name contains multiple underscores (e.g., `created_at_utc`)

**Template Generated:**
```lookml
group_item_label: "{% assign tf = _field._name | remove: 'created_at_utc_' | replace: '_', ' ' | capitalize %}{{ tf }}"
```

**Field Examples:**
- `created_at_utc_date` → "Date"
- `created_at_utc_month` → "Month"
- `created_at_utc_fiscal_quarter` → "Fiscal quarter"

**Result:** Works correctly because we remove the entire dimension name prefix including all underscores.

### 2. Interaction with convert_tz

**Scenario:** Both `convert_tz` and `use_group_item_label` enabled

**Generated LookML:**
```lookml
dimension_group: booking_time {
  type: time
  timeframes: [time, hour, date, week, month, quarter, year]
  sql: ${TABLE}.booking_timestamp ;;
  convert_tz: yes
  group_item_label: "{% assign tf = _field._name | remove: 'booking_time_' | replace: '_', ' ' | capitalize %}{{ tf }}"
}
```

**Result:** Both parameters coexist without conflict.

### 3. Interaction with hidden Parameter

**Scenario:** Time dimension with `hidden: true` and `use_group_item_label: true`

**Generated LookML:**
```lookml
dimension_group: internal_timestamp {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.internal_ts ;;
  convert_tz: no
  group_item_label: "{% assign tf = _field._name | remove: 'internal_timestamp_' | replace: '_', ' ' | capitalize %}{{ tf }}"
  hidden: yes
}
```

**Result:** All parameters coexist. Hidden dimension still gets group_item_label (useful for derived fields referencing it).

### 4. Interaction with Hierarchy Labels (DTL-032)

**Scenario:** Time dimension with both `group_label` and `group_item_label`

**YAML:**
```yaml
dimensions:
  - name: created_at
    type: time
    type_params:
      time_granularity: day
    config:
      meta:
        use_group_item_label: true
        hierarchy:
          entity: "event"
          category: "timing"
```

**Generated LookML:**
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  view_label: "Event"
  group_label: "Timing"
  convert_tz: no
  group_item_label: "{% assign tf = _field._name | remove: 'created_at_' | replace: '_', ' ' | capitalize %}{{ tf }}"
}
```

**Looker Field Explorer Hierarchy:**
```
Event (view_label)
└── Timing (group_label)
    └── Created At (dimension_group name)
        ├── Date (group_item_label)
        ├── Week (group_item_label)
        ├── Month (group_item_label)
        ├── Quarter (group_item_label)
        └── Year (group_item_label)
```

**Result:** Creates three-level hierarchy as intended by DTL-029 epic.

### 5. Empty or Missing Timeframes

**Scenario:** Custom timeframes configuration (future enhancement)

**Current Implementation:** Uses `_get_timeframes()` based on granularity. Template works regardless of which timeframes are included.

**Result:** Template is dynamic and adapts to any timeframe list.

## Risk Analysis and Mitigation

### Risk 1: Liquid Template Syntax Errors

**Severity:** Medium
**Probability:** Low

**Mitigation:**
- Comprehensive integration tests with lkml library parsing
- Manual testing in Looker instance (if available)
- Template follows established Looker documentation patterns
- Simple template structure minimizes error potential

### Risk 2: Breaking Changes to Existing Output

**Severity:** High
**Probability:** Very Low

**Mitigation:**
- Feature disabled by default (opt-in)
- Golden tests verify no changes to existing output
- Backward compatibility test explicitly checks this
- No changes to existing LookML without explicit flag

### Risk 3: Interaction with Other Features

**Severity:** Low
**Probability:** Low

**Mitigation:**
- Integration tests verify coexistence with:
  - `convert_tz`
  - `hidden`
  - `group_label` / hierarchy labels
  - `bi_field` filtering
- All parameter combinations tested
- Clear precedence documentation

### Risk 4: Multi-word Timeframe Capitalization

**Severity:** Low (cosmetic issue)
**Probability:** Medium (if Looker adds new multi-word timeframes)

**Current Behavior:** `fiscal_quarter` → "Fiscal quarter" (only first word capitalized)

**Mitigation:**
- Acceptable for v1 implementation
- Can be enhanced in future with more sophisticated template
- Documented as known limitation
- Simple fix if needed: Use Liquid `split` and `map: 'capitalize'`

### Risk 5: Performance Impact

**Severity:** Very Low
**Probability:** Very Low

**Mitigation:**
- Template is static string generation at build time
- No runtime performance impact
- Existing performance tests cover dimension generation
- Template adds ~100 characters per dimension_group

## Success Criteria Checklist

- [ ] `use_group_item_label` parameter added to `ConfigMeta` schema
- [ ] `use_group_item_label` parameter added to `LookMLGenerator.__init__()`
- [ ] `--use-group-item-label` CLI flag implemented
- [ ] `--no-group-item-label` CLI flag implemented (mutual exclusion)
- [ ] Three-tier precedence logic working (metadata > generator > CLI > default)
- [ ] Liquid template correctly generates for all dimension names
- [ ] All unit tests pass (95%+ coverage maintained)
- [ ] All integration tests pass
- [ ] Golden tests verify backward compatibility
- [ ] CLI tests verify flag behavior
- [ ] Manual testing completed with sample data
- [ ] No breaking changes to existing functionality
- [ ] All mypy type checks pass
- [ ] All linting checks pass (ruff)
- [ ] Test coverage report shows 95%+ for new code

## Implementation Sequence

### Day 1 (Morning - 4 hours)
1. **Phase 1:** Schema Foundation (2 hours)
   - Update `ConfigMeta` with `use_group_item_label` field
   - Update docstrings and examples
   - Run initial schema tests

2. **Phase 2:** Core Logic (2 hours start)
   - Update `_to_dimension_group_dict()` signature
   - Implement precedence logic
   - Generate Liquid template

### Day 1 (Afternoon - 4 hours)
3. **Phase 2 (continued):** Core Logic (1 hour)
   - Update `to_lookml_dict()` propagation
   - Update `SemanticModel.to_lookml_dict()`

4. **Phase 3:** Generator Integration (2 hours)
   - Add parameter to `LookMLGenerator.__init__()`
   - Propagate to view generation
   - Write generator unit tests

5. **Phase 5 (start):** Testing (1 hour)
   - Write core unit tests for schemas
   - Write unit tests for generator

### Day 2 (Morning - 4 hours)
6. **Phase 4:** CLI Integration (2 hours)
   - Add CLI flags
   - Implement mutual exclusion validation
   - Wire up to generator

7. **Phase 5 (continued):** Testing (2 hours)
   - Write integration tests
   - Write golden tests
   - Write CLI tests

### Day 2 (Afternoon - 2 hours)
8. **Phase 5 (completed):** Testing (1 hour)
   - Run full test suite
   - Fix any failing tests
   - Verify coverage targets

9. **Phase 6:** Validation (1 hour)
   - Manual testing with sample data
   - Verify generated LookML
   - Final quality checks
   - Update documentation (if needed)

## Next Steps After Implementation

1. **Update issue status** to "Done" in `.tasks/issues/DTL-033.md`
2. **Add `state:implemented` label** to issue
3. **Update epic** DTL-029 progress tracker
4. **Create PR** with comprehensive description
5. **Request code review** focusing on:
   - Precedence logic correctness
   - Test coverage completeness
   - Backward compatibility verification
6. **Prepare for DTL-034** (test suite updates) and DTL-035 (documentation)

## References

- **Issue:** `.tasks/issues/DTL-033.md`
- **Strategy:** `.tasks/strategies/DTL-033-strategy.md`
- **Epic:** `.tasks/epics/DTL-029.md`
- **Related Issues:**
  - DTL-032: group_label implementation (dependency)
  - DTL-034: Test suite updates (follow-up)
  - DTL-035: Documentation updates (follow-up)
- **Documentation:**
  - LookML dimension_group: https://cloud.google.com/looker/docs/reference/param-field-dimension-group
  - Liquid templating: https://shopify.github.io/liquid/
  - CLAUDE.md: Timezone Conversion Configuration pattern
  - CLAUDE.md: Field Visibility Control pattern

---

**Specification Status:** Ready for Implementation
**Estimated Effort:** 14 hours (1.75 days)
**Complexity:** Medium
**Risk Level:** Low
