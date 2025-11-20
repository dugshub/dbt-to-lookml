---
id: DTL-031-spec
issue: DTL-031
title: "Implementation Spec: Add time_dimension_group_label configuration to schemas and CLI"
type: feature
stack: backend
created: 2025-11-19
strategy: .tasks/strategies/DTL-031-strategy.md
status: ready
---

# DTL-031: Add time_dimension_group_label Configuration - Implementation Spec

## Metadata

- **Issue**: DTL-031
- **Type**: Feature
- **Stack**: Backend (Python)
- **Generated**: 2025-11-19
- **Strategy**: Approved (see `.tasks/strategies/DTL-031-strategy.md`)
- **Estimated Effort**: ~8 hours

## Issue Context

### Problem Statement

Add support for configuring the top-level `group_label` for time dimension_groups through a multi-level configuration system (dimension metadata → generator parameter → CLI flag → default value). This feature enables better organization of time dimensions in Looker's field picker by grouping all time dimension_groups under a common label (default: "Time Dimensions").

### Solution Approach

Implement a four-tier configuration precedence chain following the exact pattern established by the `convert_tz` feature:

1. **Dimension-level metadata override** (highest priority) - via `config.meta.time_dimension_group_label`
2. **Generator parameter** - via `LookMLGenerator(time_dimension_group_label=...)`
3. **CLI flag** - via `--time-dimension-group-label` or `--no-time-dimension-group-label`
4. **Default value** - "Time Dimensions" (provides better organization out-of-box)

### Success Criteria

1. ✅ `ConfigMeta` has `time_dimension_group_label: str | None` field
2. ✅ `LookMLGenerator` accepts `time_dimension_group_label` parameter with default "Time Dimensions"
3. ✅ CLI has mutually exclusive `--time-dimension-group-label` and `--no-time-dimension-group-label` flags
4. ✅ Precedence chain works correctly: metadata → generator → CLI → default
5. ✅ Time dimension_groups have correct `group_label` in output LookML
6. ✅ Feature can be disabled at any configuration level
7. ✅ 95%+ branch coverage maintained
8. ✅ Documentation updated in CLAUDE.md
9. ✅ All tests pass

## Approved Strategy Summary

The implementation follows the established `convert_tz` pattern:

- **Schema layer**: Add optional `time_dimension_group_label` field to `ConfigMeta`
- **Generator layer**: Add parameter to `LookMLGenerator.__init__()` with default "Time Dimensions"
- **Dimension layer**: Implement precedence logic in `Dimension._to_dimension_group_dict()`
- **CLI layer**: Add mutually exclusive flags with value resolution
- **Important behavior**: Time dimension group label **overrides** hierarchy labels for time dimensions

## Implementation Plan

### Phase 1: Schema Changes (ConfigMeta)

**File**: `src/dbt_to_lookml/schemas/config.py`

**Current State** (lines 23-97):
- `ConfigMeta` has existing fields: `domain`, `owner`, `contains_pii`, `update_frequency`, `subject`, `category`, `hierarchy`, `convert_tz`, `hidden`, `bi_field`
- All fields are optional with `| None` type annotation
- Uses Pydantic `BaseModel` for validation

**Changes Required**:

1. Add new field after `bi_field` (line 97):
```python
class ConfigMeta(BaseModel):
    # ... existing fields ...
    convert_tz: bool | None = None
    hidden: bool | None = None
    bi_field: bool | None = None
    time_dimension_group_label: str | None = None  # NEW FIELD
```

2. Update docstring (lines 23-85) to include new field:
```python
    """Represents metadata in a config section.

    # ... existing docstring content ...

    time_dimension_group_label: Control top-level group label for time dimension_groups.
        - String value: Set custom group_label (e.g., "Time Periods")
        - None: Disable time dimension grouping (preserves hierarchy labels)
        - Default in generator: "Time Dimensions" (better organization)
        This provides highest-priority override in configuration precedence chain.
        When set, overrides any group_label from hierarchy metadata for time dimensions.

    # ... rest of docstring ...
    """
```

**Pattern Reference**: Exactly matches `convert_tz` field pattern (line 95)

**Estimated Lines**: +1 line code, +10 lines docstring

**Testing Requirements**:
- Unit test: Verify field accepts string values
- Unit test: Verify field accepts None
- Unit test: Verify field defaults to None
- Unit test: Verify Pydantic validation works

---

### Phase 2: Generator Parameter (LookMLGenerator)

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Current State**:
- Constructor at lines 27-39
- Instance variables stored at lines 136-143
- Docstring at lines 40-128
- Generator passes `convert_tz` to model at lines 1127-1133 (need to find this in file)

**Changes Required**:

1. **Update constructor signature** (after line 38, before closing paren):
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
    fact_models: list[str] | None = None,
    time_dimension_group_label: str | None = "Time Dimensions",  # NEW PARAMETER
) -> None:
```

2. **Store instance variable** (after line 143):
```python
    self.convert_tz = convert_tz
    self.use_bi_field_filter = use_bi_field_filter
    self.fact_models = fact_models
    self.time_dimension_group_label = time_dimension_group_label  # NEW
```

3. **Update docstring** (add after line 84, in Args section):
```python
        time_dimension_group_label: Top-level group label for time dimension_groups.
            Controls the group_label parameter for organizing time dimensions in
            Looker's field picker.
            - String value: Set as group_label for all time dimension_groups
            - None: Disable group labeling (no group_label set)
            - Default: "Time Dimensions" (provides better organization)
            This setting is overridden by per-dimension config.meta.time_dimension_group_label
            in semantic models, allowing fine-grained control at the dimension level.

    Example:
        Set custom group label:

        ```python
        generator = LookMLGenerator(
            view_prefix="stg_",
            time_dimension_group_label="Time Periods"
        )
        ```

        Disable group labeling:

        ```python
        generator = LookMLGenerator(
            view_prefix="stg_",
            time_dimension_group_label=None
        )
        ```

        Use default:

        ```python
        generator = LookMLGenerator(view_prefix="stg_")
        # time_dimension_group_label defaults to "Time Dimensions"
        ```
```

4. **Pass parameter to model conversion** (find where `convert_tz` is passed, likely around line 1127):
```python
view_dict = semantic_model.to_lookml_dict(
    schema=self.schema,
    convert_tz=self.convert_tz,
    time_dimension_group_label=self.time_dimension_group_label,  # NEW
)
```

**Pattern Reference**: Exactly matches `convert_tz` parameter pattern

**Estimated Lines**: +1 constructor param, +1 instance var, +20 docstring, +1 pass-through

**Testing Requirements**:
- Unit test: Verify default value is "Time Dimensions"
- Unit test: Verify custom string value is stored
- Unit test: Verify None value is stored
- Unit test: Verify parameter is passed to generation

---

### Phase 3: Dimension Generation Logic (SemanticModel & Dimension)

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`

#### Part A: SemanticModel.to_lookml_dict() Method

**Current State**: Method signature accepts `schema` and `convert_tz` parameters

**Changes Required**:

1. **Find method signature** (search for `def to_lookml_dict` in SemanticModel class):
```python
def to_lookml_dict(
    self,
    schema: str = "",
    convert_tz: bool | None = None,
    time_dimension_group_label: str | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
```

2. **Pass parameter to dimensions** (find dimensions loop, pass new param):
```python
for dimension in self.dimensions:
    dim_dict = dimension.to_lookml_dict(
        default_convert_tz=convert_tz,
        default_time_dimension_group_label=time_dimension_group_label,  # NEW
    )
    dimensions_list.append(dim_dict)
```

**Pattern Reference**: Exactly matches `convert_tz` parameter flow

#### Part B: Dimension.to_lookml_dict() Method

**Current State**: Method at lines 128-138 accepts `default_convert_tz` parameter

**Changes Required**:

1. **Update method signature** (line 128):
```python
def to_lookml_dict(
    self,
    default_convert_tz: bool | None = None,
    default_time_dimension_group_label: str | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
```

2. **Pass to dimension_group method** (line 136):
```python
if self.type == DimensionType.TIME:
    return self._to_dimension_group_dict(
        default_convert_tz=default_convert_tz,
        default_time_dimension_group_label=default_time_dimension_group_label,  # NEW
    )
```

#### Part C: Dimension._to_dimension_group_dict() Method

**Current State**:
- Method signature at lines 220-221 accepts `default_convert_tz`
- Hierarchy labels set at lines 300-304
- `convert_tz` precedence logic at lines 306-316

**Changes Required**:

1. **Update method signature** (line 220):
```python
def _to_dimension_group_dict(
    self,
    default_convert_tz: bool | None = None,
    default_time_dimension_group_label: str | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
```

2. **Implement precedence logic** (after line 304, BEFORE convert_tz logic at 306):
```python
# Add hierarchy labels
view_label, group_label = self.get_dimension_labels()
if view_label:
    result["view_label"] = view_label
if group_label:
    result["group_label"] = group_label

# Determine time_dimension_group_label with three-tier precedence:
# 1. Dimension-level meta.time_dimension_group_label (highest priority if present)
# 2. default_time_dimension_group_label parameter (if provided)
# 3. No group label (lowest priority, None means no grouping)
time_dim_group_label = None  # Default: no grouping
if default_time_dimension_group_label is not None:
    time_dim_group_label = default_time_dimension_group_label
if (self.config and self.config.meta and
    self.config.meta.time_dimension_group_label is not None):
    time_dim_group_label = self.config.meta.time_dimension_group_label

# Apply time dimension group label if present
# This overrides group_label from hierarchy for time dimensions
if time_dim_group_label:
    # IMPORTANT: This overrides group_label set above
    # Time dimension group label takes precedence for consistent organization
    result["group_label"] = time_dim_group_label

# (convert_tz logic continues below at line 306)
```

3. **Update docstring** (lines 223-282):
```python
"""Convert time dimension to LookML dimension_group.

Generates a LookML dimension_group block with appropriate timeframes
based on the dimension's time_granularity setting. Supports timezone
conversion and group labeling through multi-level precedence.

Args:
    default_convert_tz: Default timezone conversion setting from
        generator or CLI.
        - True: Enable timezone conversion for all dimensions
          (unless overridden)
        - False: Disable timezone conversion (default behavior)
        - None: Use generator default (False)

    default_time_dimension_group_label: Default group label for time
        dimension_groups from generator or CLI.
        - String value: Set as group_label for time dimensions
        - None: No group labeling (preserves hierarchy labels)
        This is overridden by dimension-level meta.time_dimension_group_label

Returns:
    Dictionary with dimension_group configuration including:
    - name: Dimension name
    - type: "time"
    - timeframes: List of appropriate timeframes based on granularity
    - sql: SQL expression for the timestamp column
    - convert_tz: "yes" or "no" based on precedence rules
    - group_label: Time dimension group label (if configured)
    - description: Optional description
    - label: Optional label
    - view_label: Optional hierarchy view label (if no group label override)

Example:
    Dimension with group label override:

    ```python
    dimension = Dimension(
        name="created_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "day"},
        config=Config(meta=ConfigMeta(
            time_dimension_group_label="Event Timestamps"  # Override
        ))
    )
    result = dimension._to_dimension_group_dict(
        default_time_dimension_group_label="Time Dimensions"
    )
    # Result includes: "group_label": "Event Timestamps"
    ```

    Dimension with generator default:

    ```python
    dimension = Dimension(
        name="shipped_at",
        type=DimensionType.TIME,
        type_params={"time_granularity": "hour"}
    )
    result = dimension._to_dimension_group_dict(
        default_time_dimension_group_label="Time Dimensions"
    )
    # Result includes: "group_label": "Time Dimensions"
    ```

See Also:
    CLAUDE.md: "Timezone Conversion Configuration" section for similar
        multi-level precedence pattern.
"""
```

**Important Design Note**: The time dimension group label **overrides** `group_label` from hierarchy metadata. This ensures all time dimensions are grouped consistently under one label when the feature is enabled.

**Pattern Reference**: Exactly matches `convert_tz` precedence logic (lines 306-316)

**Estimated Lines**: +2 signature, +15 logic, +40 docstring

**Testing Requirements**:
- Unit test: Metadata override works (highest priority)
- Unit test: Generator default is used when no metadata
- Unit test: None value disables feature
- Unit test: Group label overrides hierarchy group_label
- Integration test: Full parameter flow from CLI to output

---

### Phase 4: CLI Integration (__main__.py)

**File**: `src/dbt_to_lookml/__main__.py`

**Current State**:
- `convert_tz` flags at lines 305-314
- Mutual exclusivity check at lines 392-401
- Value resolution at lines 566-574
- Generator instantiation at lines 586-597

**Changes Required**:

1. **Add CLI options** (after line 314, before `--bi-field-only` at line 316):
```python
@click.option(
    "--no-convert-tz",
    is_flag=True,
    help="Don't convert time dimensions to UTC (mutually exclusive with --convert-tz)",
)
@click.option(
    "--time-dimension-group-label",
    type=str,
    default=None,
    help="Group label for time dimension_groups (default: 'Time Dimensions'). "
         "Groups all time dimensions under a common label in Looker's field picker.",
)
@click.option(
    "--no-time-dimension-group-label",
    is_flag=True,
    help="Disable time dimension group labeling (preserves hierarchy labels)",
)
@click.option(
    "--bi-field-only",
    is_flag=True,
    help="Only include fields marked with bi_field: true in explores",
)
```

2. **Update generate function signature** (after line 353, before `bi_field_only`):
```python
def generate(
    input_dir: Path,
    output_dir: Path,
    schema: str,
    view_prefix: str,
    explore_prefix: str,
    dry_run: bool,
    no_validation: bool,
    no_formatting: bool,
    show_summary: bool,
    connection: str,
    model_name: str,
    convert_tz: bool,
    no_convert_tz: bool,
    time_dimension_group_label: str | None,  # NEW PARAMETER
    no_time_dimension_group_label: bool,     # NEW PARAMETER
    bi_field_only: bool,
    fact_models: str | None,
    yes: bool,
    preview: bool,
) -> None:
```

3. **Add mutual exclusivity validation** (after line 401, before preview check at 404):
```python
    # Validate mutual exclusivity of timezone flags
    if convert_tz and no_convert_tz:
        error_panel = format_error(
            "Conflicting timezone options provided",
            context="Use either --convert-tz OR --no-convert-tz, not both",
        )
        console.print(error_panel)
        raise click.ClickException(
            "--convert-tz and --no-convert-tz cannot be used together"
        )

    # Validate mutual exclusivity of time dimension group label flags
    if time_dimension_group_label is not None and no_time_dimension_group_label:
        error_panel = format_error(
            "Conflicting time dimension group label options provided",
            context="Use either --time-dimension-group-label OR "
                    "--no-time-dimension-group-label, not both",
        )
        console.print(error_panel)
        raise click.ClickException(
            "--time-dimension-group-label and --no-time-dimension-group-label "
            "cannot be used together"
        )

    # Preview mode implies dry run
    if preview:
        dry_run = True
```

4. **Add value resolution** (after line 574, before fact models parsing at 576):
```python
    # Determine convert_tz value for generator
    convert_tz_value: bool | None = None
    if convert_tz:
        convert_tz_value = True
    elif no_convert_tz:
        convert_tz_value = False

    # Determine time_dimension_group_label value for generator
    # If --no-time-dimension-group-label specified: None (explicit disable)
    # If --time-dimension-group-label specified: custom value
    # If neither specified: "Time Dimensions" (default via generator)
    time_dim_group_label_value: str | None = "Time Dimensions"  # Default
    if no_time_dimension_group_label:
        time_dim_group_label_value = None
    elif time_dimension_group_label is not None:
        time_dim_group_label_value = time_dimension_group_label

    # Parse fact models if provided
    fact_model_names: list[str] | None = None
    if fact_models:
        fact_model_names = [name.strip() for name in fact_models.split(",")]
```

5. **Pass to generator** (update line 586):
```python
    # Configure generator
    generator = LookMLGenerator(
        view_prefix=view_prefix,
        explore_prefix=explore_prefix,
        validate_syntax=not no_validation,
        format_output=not no_formatting,
        schema=schema,
        connection=connection,
        model_name=model_name,
        convert_tz=convert_tz_value,
        use_bi_field_filter=bi_field_only,
        fact_models=fact_model_names,
        time_dimension_group_label=time_dim_group_label_value,  # NEW
    )
```

6. **Update command docstring** (add examples to docstring at lines 359-383):
```python
"""Generate LookML views and explores from semantic models.

This command parses dbt semantic model YAML files and generates
corresponding LookML view files (.view.lkml) and a consolidated
explores file (explores.lkml).

Examples:

  Basic generation (uses default "Time Dimensions" grouping):
  $ dbt-to-lookml generate -i semantic_models/ -o build/lookml -s prod_schema

  With custom time dimension group label:
  $ dbt-to-lookml generate -i models/ -o lookml/ -s analytics \\
      --time-dimension-group-label "Time Periods"

  Disable time dimension grouping:
  $ dbt-to-lookml generate -i models/ -o lookml/ -s dwh \\
      --no-time-dimension-group-label

  With prefixes and timezone conversion:
  $ dbt-to-lookml generate -i models/ -o lookml/ -s analytics \\
      --view-prefix "sm_" --explore-prefix "exp_" --convert-tz

For interactive mode, use:
  $ dbt-to-lookml wizard generate
"""
```

**Pattern Reference**: Exactly matches `convert_tz` CLI flag pattern (lines 305-314, 392-401, 566-574)

**Estimated Lines**: +14 options, +2 signature, +12 validation, +8 resolution, +1 pass-through, +12 docstring

**Testing Requirements**:
- CLI test: `--time-dimension-group-label` flag sets custom value
- CLI test: `--no-time-dimension-group-label` flag disables feature
- CLI test: Mutual exclusivity validation works
- CLI test: Default value applied when no flags
- CLI test: Help text displays correctly

---

## Detailed Task Breakdown

### Task 1: Add time_dimension_group_label to ConfigMeta Schema

**File**: `src/dbt_to_lookml/schemas/config.py`

**Action**: Add optional field to Pydantic model

**Implementation Guidance**:
```python
# Line 97 - add new field after bi_field
class ConfigMeta(BaseModel):
    # ... existing fields ...
    bi_field: bool | None = None
    time_dimension_group_label: str | None = None  # NEW
```

**Reference**: Similar to `convert_tz` field at line 95

**Tests**:
- `test_config_meta_time_dimension_group_label_field()` in `test_schemas.py`
- Verify field accepts string, None, and defaults to None

**Estimated Time**: 15 minutes

---

### Task 2: Add Generator Parameter

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Action**: Add parameter to constructor, store as instance variable, update docstring

**Implementation Guidance**:
1. Add to `__init__()` signature with default "Time Dimensions"
2. Store as `self.time_dimension_group_label`
3. Add comprehensive docstring with examples

**Reference**: Exactly matches `convert_tz` parameter pattern (lines 36, 141, 68-75)

**Tests**:
- `test_generator_time_dimension_group_label_parameter()` in `test_lookml_generator.py`
- Verify default, custom, and None values

**Estimated Time**: 30 minutes

---

### Task 3: Implement Dimension Generation Logic

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`

**Action**: Add parameter flow and precedence logic

**Implementation Guidance**:
1. Update `SemanticModel.to_lookml_dict()` to accept and pass parameter
2. Update `Dimension.to_lookml_dict()` to accept and pass parameter
3. Update `Dimension._to_dimension_group_dict()` signature and implement precedence
4. Place logic AFTER hierarchy labels, BEFORE convert_tz logic
5. Override `group_label` when time_dim_group_label is set

**Reference**: `convert_tz` precedence logic at lines 306-316

**Tests**:
- `test_dimension_time_dimension_group_label_metadata_override()` in `test_schemas.py`
- `test_dimension_time_dimension_group_label_default()` in `test_schemas.py`
- `test_dimension_time_dimension_group_label_disabled()` in `test_schemas.py`
- `test_dimension_time_dimension_group_label_overrides_hierarchy()` in `test_schemas.py`

**Estimated Time**: 1.5 hours

---

### Task 4: Add CLI Flags and Integration

**File**: `src/dbt_to_lookml/__main__.py`

**Action**: Add CLI options, validation, resolution, and parameter passing

**Implementation Guidance**:
1. Add two mutually exclusive flags (lines 315-324)
2. Add parameters to `generate()` signature
3. Add mutual exclusivity check (after line 401)
4. Add value resolution logic (after line 574)
5. Pass to generator (line 596)
6. Update docstring examples

**Reference**: `convert_tz` flags and validation (lines 305-314, 392-401, 566-574)

**Tests**:
- `test_generate_time_dimension_group_label_flag()` in `test_cli.py`
- `test_generate_no_time_dimension_group_label_flag()` in `test_cli.py`
- `test_generate_mutual_exclusivity_time_dimension_labels()` in `test_cli.py`
- `test_generate_default_time_dimension_group_label()` in `test_cli.py`

**Estimated Time**: 1 hour

---

### Task 5: Write Unit Tests

**Files**:
- `src/tests/unit/test_schemas.py`
- `src/tests/unit/test_lookml_generator.py`
- `src/tests/test_cli.py`

**Tests to Add**:

#### test_schemas.py
1. `test_config_meta_time_dimension_group_label_field()`:
   - Verify field accepts string values
   - Verify field accepts None
   - Verify field defaults to None

2. `test_dimension_time_dimension_group_label_metadata_override()`:
   - Create dimension with `meta.time_dimension_group_label="Event Times"`
   - Call `_to_dimension_group_dict(default_time_dimension_group_label="Time Dimensions")`
   - Assert `group_label == "Event Times"` (metadata wins)

3. `test_dimension_time_dimension_group_label_default()`:
   - Create dimension without metadata override
   - Call `_to_dimension_group_dict(default_time_dimension_group_label="Time Dimensions")`
   - Assert `group_label == "Time Dimensions"` (default used)

4. `test_dimension_time_dimension_group_label_disabled()`:
   - Create dimension without metadata
   - Call `_to_dimension_group_dict(default_time_dimension_group_label=None)`
   - Assert `group_label` not in result or matches hierarchy

5. `test_dimension_time_dimension_group_label_overrides_hierarchy()`:
   - Create dimension with hierarchy `category="Events"`
   - Call `_to_dimension_group_dict(default_time_dimension_group_label="Time Dimensions")`
   - Assert `group_label == "Time Dimensions"` (time label overrides hierarchy)

#### test_lookml_generator.py
1. `test_generator_time_dimension_group_label_parameter()`:
   - Create generator with default (no param specified)
   - Assert `generator.time_dimension_group_label == "Time Dimensions"`

2. `test_generator_time_dimension_group_label_custom_value()`:
   - Create generator with `time_dimension_group_label="Time Periods"`
   - Assert value stored correctly

3. `test_generator_time_dimension_group_label_none_disables()`:
   - Create generator with `time_dimension_group_label=None`
   - Assert None stored correctly

#### test_cli.py
1. `test_generate_time_dimension_group_label_flag()`:
   - Invoke CLI with `--time-dimension-group-label "Custom Label"`
   - Assert command succeeds
   - Verify flag is processed

2. `test_generate_no_time_dimension_group_label_flag()`:
   - Invoke CLI with `--no-time-dimension-group-label`
   - Assert command succeeds
   - Verify feature disabled

3. `test_generate_mutual_exclusivity_time_dimension_labels()`:
   - Invoke CLI with both flags
   - Assert command fails with clear error message

4. `test_generate_default_time_dimension_group_label()`:
   - Invoke CLI with neither flag
   - Assert default value "Time Dimensions" is used

**Pattern Reference**: Follow existing `convert_tz` test patterns in each file

**Estimated Time**: 2 hours

---

### Task 6: Write Integration Test

**File**: `src/tests/integration/test_end_to_end.py` (or create new file if needed)

**Test**: `test_time_dimension_group_label_integration()`

**Implementation Guidance**:
```python
def test_time_dimension_group_label_integration(tmp_path):
    """Test full flow from CLI flag to LookML output."""
    # 1. Create semantic model YAML with time dimension
    input_dir = tmp_path / "semantic_models"
    input_dir.mkdir()

    semantic_model_yaml = """
    semantic_model:
      name: events
      model: ref('fct_events')
      entities:
        - name: event_id
          type: primary
      dimensions:
        - name: event_timestamp
          type: time
          type_params:
            time_granularity: day
        - name: processed_at
          type: time
          type_params:
            time_granularity: hour
          config:
            meta:
              time_dimension_group_label: "Processing Times"  # Override
    """
    (input_dir / "events.yml").write_text(semantic_model_yaml)

    # 2. Run generator with time_dimension_group_label
    output_dir = tmp_path / "lookml"
    generator = LookMLGenerator(
        schema="analytics",
        time_dimension_group_label="Event Times"
    )

    # Parse and generate
    parser = DbtParser()
    models = parser.parse_directory(input_dir)
    generated = generator.generate(models)
    generator.write_files(output_dir, generated)

    # 3. Verify output LookML
    view_file = output_dir / "events.view.lkml"
    assert view_file.exists()

    content = view_file.read_text()

    # event_timestamp should have "Event Times" (generator default)
    assert 'dimension_group: event_timestamp' in content
    assert 'group_label: "Event Times"' in content

    # processed_at should have "Processing Times" (metadata override)
    assert 'dimension_group: processed_at' in content
    assert 'group_label: "Processing Times"' in content
```

**Pattern Reference**: Follow existing integration test patterns

**Estimated Time**: 1 hour

---

### Task 7: Update CLAUDE.md Documentation

**File**: `CLAUDE.md`

**Action**: Add new section after "Timezone Conversion Configuration" (after line 312)

**Content to Add**:
```markdown
### Time Dimension Group Label Configuration

Time dimension_groups support hierarchical organization through the `group_label` parameter,
which controls how time dimensions are grouped in Looker's field picker. This feature uses
multi-level configuration with a sensible precedence chain, similar to timezone conversion.

#### Default Behavior

- **Default**: `group_label: "Time Dimensions"` (groups all time dimensions together)
- This provides better organization in Looker's field picker out-of-box
- Users can customize or disable this grouping as needed

#### Configuration Levels (Precedence: Highest to Lowest)

1. **Dimension Metadata Override** (Highest priority)
   ```yaml
   dimensions:
     - name: created_at
       type: time
       config:
         meta:
           time_dimension_group_label: "Event Timestamps"  # Custom group for this dimension
   ```

2. **Generator Parameter**
   ```python
   generator = LookMLGenerator(
       view_prefix="my_",
       time_dimension_group_label="Time Periods"  # Apply to all dimensions
   )
   ```

3. **CLI Flag**
   ```bash
   # Use custom group label
   dbt-to-lookml generate -i semantic_models -o build/lookml \\
       --time-dimension-group-label "Time Periods"

   # Disable grouping (preserves hierarchy labels)
   dbt-to-lookml generate -i semantic_models -o build/lookml \\
       --no-time-dimension-group-label
   ```

4. **Default** (Lowest priority)
   - `group_label: "Time Dimensions"` - Applied when no explicit configuration provided

#### Examples

##### Example 1: Override at Dimension Level
```yaml
# semantic_models/orders.yaml
semantic_model:
  name: orders
  dimensions:
    - name: created_at
      type: time
      type_params:
        time_granularity: day
      config:
        meta:
          time_dimension_group_label: "Order Timestamps"  # Override

    - name: shipped_at
      type: time
      type_params:
        time_granularity: day
      # No override, uses generator/CLI/default
```

**Generated LookML**:
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  group_label: "Order Timestamps"
}

dimension_group: shipped_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.shipped_at ;;
  group_label: "Time Dimensions"
}
```

##### Example 2: Generator-Level Configuration
```python
from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser

parser = DbtParser()
models = parser.parse_directory("semantic_models/")

# Set custom group label for all time dimensions
generator = LookMLGenerator(
    view_prefix="stg_",
    time_dimension_group_label="Time Periods"
)

output = generator.generate(models)
generator.write_files("build/lookml", output)
```

##### Example 3: CLI Usage
```bash
# Generate with custom time dimension group label
dbt-to-lookml generate -i semantic_models/ -o build/lookml \\
    --time-dimension-group-label "Time Fields"

# Generate with grouping disabled (preserves hierarchy labels)
dbt-to-lookml generate -i semantic_models/ -o build/lookml \\
    --no-time-dimension-group-label

# Generate with default behavior
dbt-to-lookml generate -i semantic_models/ -o build/lookml
# Uses default "Time Dimensions" grouping
```

#### Important: Group Label Overrides Hierarchy

When `time_dimension_group_label` is set (either by default or explicitly), it **overrides**
any `group_label` from the hierarchy metadata for time dimensions. This ensures consistent
organization of all time dimensions under a common grouping.

**Example**: Hierarchy override behavior
```yaml
dimensions:
  - name: event_date
    type: time
    config:
      meta:
        hierarchy:
          category: "Event Details"  # Would normally set group_label
# With default time_dimension_group_label="Time Dimensions":
# group_label will be "Time Dimensions" (not "Event Details")
```

To preserve hierarchy-based group labels for time dimensions, use
`--no-time-dimension-group-label` to disable this feature.

#### Implementation Details

- **Dimension._to_dimension_group_dict()**: Accepts `default_time_dimension_group_label` parameter
  - Checks `config.meta.time_dimension_group_label` first (dimension-level override)
  - Falls back to `default_time_dimension_group_label` parameter
  - Falls back to no grouping if neither specified
  - Overrides hierarchy `group_label` when present

- **LookMLGenerator.__init__()**: Accepts optional `time_dimension_group_label: str | None` parameter
  - Defaults to "Time Dimensions" for better organization
  - Stores setting as instance variable
  - Propagates to `SemanticModel.to_lookml_dict()` during generation

- **SemanticModel.to_lookml_dict()**: Accepts `time_dimension_group_label` parameter
  - Passes to each `Dimension._to_dimension_group_dict()` call

- **CLI Flags**: Mutually exclusive `--time-dimension-group-label TEXT` / `--no-time-dimension-group-label` options
  - `--time-dimension-group-label TEXT`: Sets custom group label
  - `--no-time-dimension-group-label`: Disables grouping (None value)
  - Neither: Uses default "Time Dimensions"

#### LookML Output Examples

With `group_label: "Time Dimensions"` (default):
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  group_label: "Time Dimensions"
  convert_tz: no
}
```

With custom `group_label: "Time Periods"`:
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  group_label: "Time Periods"
  convert_tz: no
}
```

With grouping disabled (None):
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
}
```
```

**Estimated Time**: 1 hour

---

## File Changes Summary

### Files to Modify

#### `src/dbt_to_lookml/schemas/config.py`
**Why**: Add schema field for metadata override

**Changes**:
- Add `time_dimension_group_label: str | None = None` field to `ConfigMeta`
- Update class docstring

**Estimated lines**: ~10 lines

---

#### `src/dbt_to_lookml/generators/lookml.py`
**Why**: Add generator-level configuration parameter

**Changes**:
- Add `time_dimension_group_label` parameter to `__init__()` with default "Time Dimensions"
- Store as instance variable
- Pass to model conversion
- Update docstring

**Estimated lines**: ~25 lines

---

#### `src/dbt_to_lookml/schemas/semantic_layer.py`
**Why**: Implement precedence logic and parameter flow

**Changes**:
- Update `SemanticModel.to_lookml_dict()` signature and pass parameter
- Update `Dimension.to_lookml_dict()` signature and pass parameter
- Update `Dimension._to_dimension_group_dict()` signature and implement logic
- Update method docstring

**Estimated lines**: ~60 lines

---

#### `src/dbt_to_lookml/__main__.py`
**Why**: Add CLI flags and integration

**Changes**:
- Add two mutually exclusive CLI options
- Update `generate()` function signature
- Add mutual exclusivity validation
- Add value resolution logic
- Pass to generator
- Update command docstring

**Estimated lines**: ~50 lines

---

#### `CLAUDE.md`
**Why**: Document new feature

**Changes**:
- Add new section "Time Dimension Group Label Configuration"
- Include configuration levels, examples, and implementation details

**Estimated lines**: ~150 lines

---

### Files to Create (Tests)

#### `src/tests/unit/test_schemas.py` (additions)
**New tests**: 5 test methods

**Estimated lines**: ~100 lines

---

#### `src/tests/unit/test_lookml_generator.py` (additions)
**New tests**: 3 test methods

**Estimated lines**: ~60 lines

---

#### `src/tests/test_cli.py` (additions)
**New tests**: 4 test methods

**Estimated lines**: ~120 lines

---

#### `src/tests/integration/test_end_to_end.py` (additions)
**New tests**: 1 integration test

**Estimated lines**: ~80 lines

---

## Testing Strategy

### Unit Tests (95%+ coverage target)

**Schema Tests** (`test_schemas.py`):
- ✅ ConfigMeta field validation
- ✅ Dimension precedence logic (metadata > default > None)
- ✅ Group label override behavior
- ✅ All branches in precedence chain

**Generator Tests** (`test_lookml_generator.py`):
- ✅ Parameter storage and default value
- ✅ Custom value handling
- ✅ None value handling
- ✅ Parameter pass-through to generation

**CLI Tests** (`test_cli.py`):
- ✅ Flag parsing and validation
- ✅ Mutual exclusivity enforcement
- ✅ Default value application
- ✅ Help text display

### Integration Tests

**End-to-End Test** (`test_end_to_end.py`):
- ✅ Full parameter flow from CLI → Generator → Dimension → LookML output
- ✅ Metadata override verification
- ✅ Generator default verification
- ✅ Generated LookML correctness

### Edge Cases

1. **Empty string value**: Should be treated as valid (not None)
2. **Special characters in label**: Should pass through unchanged
3. **Very long label**: Should not be truncated
4. **Unicode characters**: Should be preserved
5. **Hierarchy + time label**: Time label should override hierarchy

### Coverage Requirements

- All new code paths: 100% branch coverage
- Overall project coverage: Maintain 95%+
- No coverage regression

---

## Validation Commands

### Development Workflow

```bash
# 1. Run unit tests
python -m pytest src/tests/unit/test_schemas.py::TestDimension::test_dimension_time_dimension_group_label -xvs
python -m pytest src/tests/unit/test_lookml_generator.py -k time_dimension_group_label -xvs
python -m pytest src/tests/test_cli.py -k time_dimension_group_label -xvs

# 2. Run integration tests
python -m pytest src/tests/integration/test_end_to_end.py::test_time_dimension_group_label_integration -xvs

# 3. Run all tests
make test

# 4. Check coverage
make test-coverage

# 5. Code quality gates
make format          # Auto-fix formatting
make lint            # Check linting
make type-check      # Check type hints
make quality-gate    # All gates
```

### Pre-Commit Checklist

```bash
# Full validation before commit
make format
make quality-gate
make test-full

# Verify coverage hasn't regressed
python -m pytest --cov=src/dbt_to_lookml --cov-branch --cov-report=term
```

---

## Dependencies

### Existing Dependencies (No Changes)
- `pydantic`: Schema validation (already used)
- `click`: CLI framework (already used)
- `lkml`: LookML syntax validation (already used)
- `rich`: Console output (already used)

### New Dependencies
**None** - This feature uses only existing dependencies

---

## Implementation Notes

### Important Considerations

1. **Default Value Rationale**: "Time Dimensions" provides better UX out-of-box without breaking existing functionality
2. **Override Behavior**: Time dimension group label **overrides** hierarchy labels for consistency
3. **Backward Compatibility**: 100% compatible - all changes are additive with sensible defaults
4. **Pattern Consistency**: Exactly mirrors `convert_tz` implementation for developer familiarity

### Code Patterns to Follow

1. **Type Annotations**: Always use `str | None` (not `Optional[str]`)
2. **Default Values**: Set default in generator constructor, not CLI decorator
3. **Precedence Logic**: Check metadata first, then parameter, then hardcoded default
4. **Validation**: Use Click's error handling with rich formatting
5. **Docstrings**: Google-style with comprehensive examples

### References

**Similar Implementations**:
- `convert_tz` feature: `schemas/config.py` line 95, `generators/lookml.py` line 36, `__main__.py` lines 305-574
- `hidden` parameter: `schemas/config.py` line 96, `schemas/semantic_layer.py` lines 192-193
- `bi_field` parameter: `schemas/config.py` line 97, `generators/lookml.py` line 37

**Test Patterns**:
- Convert_tz tests: `tests/unit/test_schemas.py` lines 261-357
- CLI flag tests: `tests/test_cli.py` lines 1233-1283
- Generator tests: `tests/unit/test_lookml_generator.py` lines 2730-2750

---

## Ready for Implementation

This spec is complete and ready for the `/implement` workflow.

**Checklist**:
- ✅ Detailed implementation plan with 5 phases
- ✅ Task breakdown with time estimates
- ✅ File-level implementation guidance
- ✅ Code patterns and references
- ✅ Comprehensive testing strategy
- ✅ Validation commands
- ✅ Documentation updates
- ✅ Backward compatibility analysis

**Next Step**: Run `/implement DTL-031` to execute implementation
