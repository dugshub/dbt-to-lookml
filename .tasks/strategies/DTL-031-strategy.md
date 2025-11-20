---
id: DTL-031-strategy
issue: DTL-031
title: "Implementation Strategy: Add time_dimension_group_label configuration to schemas and CLI"
created: 2025-11-19
status: approved
---

# DTL-031 Implementation Strategy

## Overview

Add support for configuring the top-level `group_label` for time dimension_groups through a multi-level configuration system (dimension metadata → generator parameter → CLI flag → default value).

This feature follows the established pattern used by `convert_tz` and enables better organization of time dimensions in Looker's field picker by grouping all time dimension_groups under a common label (default: "Time Dimensions").

## Architecture Analysis

### Current State

**Schema Structure** (`schemas/config.py`):
- `ConfigMeta` class already supports multiple field-level metadata overrides
- Existing pattern: `convert_tz`, `hidden`, `bi_field` fields
- Uses Pydantic `BaseModel` with optional fields (type: `str | None` or `bool | None`)

**Generator Flow** (`generators/lookml.py`):
- `LookMLGenerator.__init__()` accepts configuration parameters
- Parameters are stored as instance variables
- Generator passes parameters through to model conversion methods
- Current relevant parameters: `convert_tz: bool | None`, `use_bi_field_filter: bool`

**Dimension Generation** (`schemas/semantic_layer.py`):
- `Dimension._to_dimension_group_dict()` generates time dimension_groups
- Currently sets `view_label` and `group_label` from hierarchy metadata
- Accepts `default_convert_tz` parameter showing precedence pattern
- Lines 300-304: Existing label logic for `view_label` and `group_label`

**CLI Configuration** (`__main__.py`):
- Click-based CLI with option decorators
- Existing timezone flags show mutual exclusivity pattern:
  - Lines 305-314: `--convert-tz` and `--no-convert-tz` flags
  - Lines 392-401: Mutual exclusivity validation
  - Lines 566-574: Value resolution for generator
- Parameters passed to `LookMLGenerator` constructor at line 586

### Target State

Add `time_dimension_group_label` configuration that:

1. **Schema level**: Optional field in `ConfigMeta` for per-dimension override
2. **Generator level**: Optional parameter in `LookMLGenerator.__init__()`
3. **CLI level**: Mutually exclusive flags `--time-dimension-group-label` and `--no-time-dimension-group-label`
4. **Default value**: "Time Dimensions" (provides better organization out-of-box)

## Implementation Plan

### Phase 1: Schema Changes

**File**: `src/dbt_to_lookml/schemas/config.py`

**Changes**:
```python
class ConfigMeta(BaseModel):
    # ... existing fields ...
    convert_tz: bool | None = None
    hidden: bool | None = None
    bi_field: bool | None = None
    time_dimension_group_label: str | None = None  # NEW FIELD
```

**Rationale**:
- Follows existing pattern for optional metadata overrides
- Type `str | None` matches the parameter type (string label or None to disable)
- Placed after existing field-level overrides for logical grouping
- Provides highest-priority override in precedence chain

**Testing**:
- Unit test: `test_config_meta_time_dimension_group_label_field()` in `test_schemas.py`
- Verify field is optional and accepts string values or None
- Test Pydantic validation (no constraints on string content)

### Phase 2: Generator Parameter

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Changes**:

1. **Constructor signature** (line 27-39):
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

2. **Store as instance variable** (after line 143):
```python
self.convert_tz = convert_tz
self.use_bi_field_filter = use_bi_field_filter
self.fact_models = fact_models
self.time_dimension_group_label = time_dimension_group_label  # NEW
```

3. **Update docstring** (lines 40-127):
Add parameter documentation:
```python
"""
Args:
    # ... existing params ...
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
"""
```

4. **Pass to model conversion** (line 1127-1133):
```python
view_dict = semantic_model.to_lookml_dict(
    schema=self.schema,
    convert_tz=self.convert_tz,
    time_dimension_group_label=self.time_dimension_group_label,  # NEW
)
```

**Rationale**:
- Default value "Time Dimensions" provides better organization out-of-box
- Follows `convert_tz` pattern for generator-level configuration
- Instance variable storage enables access during generation
- Docstring follows existing pattern with detailed examples

**Testing**:
- Unit test: `test_generator_time_dimension_group_label_parameter()` in `test_lookml_generator.py`
- Test default value is "Time Dimensions"
- Test custom string value is stored and passed through
- Test None value disables feature

### Phase 3: Dimension Generation Logic

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`

**Changes**:

1. **Update method signature** (line 128):
```python
def to_lookml_dict(
    self,
    default_convert_tz: bool | None = None,
    default_time_dimension_group_label: str | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
```

2. **Pass through to dimension_group method** (line 136):
```python
if self.type == DimensionType.TIME:
    return self._to_dimension_group_dict(
        default_convert_tz=default_convert_tz,
        default_time_dimension_group_label=default_time_dimension_group_label,  # NEW
    )
```

3. **Update _to_dimension_group_dict signature** (line 220-221):
```python
def _to_dimension_group_dict(
    self,
    default_convert_tz: bool | None = None,
    default_time_dimension_group_label: str | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
```

4. **Implement precedence logic** (after line 304, before convert_tz logic):
```python
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
# This sets the top-level grouping for time dimensions, separate from
# the view_label/group_label hierarchy set above
if time_dim_group_label:
    # IMPORTANT: This overrides group_label from hierarchy
    # Time dimension group label takes precedence for time dimensions
    result["group_label"] = time_dim_group_label
```

5. **Update docstring** (lines 223-282):
Add parameter documentation and update examples:
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
    - view_label: Optional hierarchy view label (if no group label)

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

**Important Design Decision**:

The time dimension group label **overrides** any `group_label` set by the hierarchy metadata when present. This ensures:

1. **Consistent organization**: All time dimensions grouped under one label
2. **Clear precedence**: Explicit time dimension grouping takes priority
3. **Backward compatible**: When not configured (None), hierarchy labels still work

**Testing**:
- Unit test: `test_dimension_time_dimension_group_label_metadata_override()` in `test_schemas.py`
- Unit test: `test_dimension_time_dimension_group_label_default()` in `test_schemas.py`
- Unit test: `test_dimension_time_dimension_group_label_disabled()` in `test_schemas.py`
- Integration test: End-to-end flow with all precedence levels

### Phase 4: SemanticModel Method Update

**File**: `src/dbt_to_lookml/schemas/semantic_layer.py`

**Changes**:

1. **Update SemanticModel.to_lookml_dict() signature** (find method, likely around line 450-500):
```python
def to_lookml_dict(
    self,
    schema: str = "",
    convert_tz: bool | None = None,
    time_dimension_group_label: str | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
```

2. **Pass to dimension conversion** (in dimensions loop):
```python
for dimension in self.dimensions:
    dim_dict = dimension.to_lookml_dict(
        default_convert_tz=convert_tz,
        default_time_dimension_group_label=time_dimension_group_label,  # NEW
    )
    dimensions_list.append(dim_dict)
```

**Rationale**:
- Completes the parameter flow from generator → model → dimension
- Maintains consistency with `convert_tz` parameter pattern
- Enables generator configuration to reach dimension generation

**Testing**:
- Covered by integration tests showing full parameter flow

### Phase 5: CLI Integration

**File**: `src/dbt_to_lookml/__main__.py`

**Changes**:

1. **Add CLI options** (after line 314, before `--bi-field-only`):
```python
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
```

2. **Update generate function signature** (line 340):
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

3. **Add mutual exclusivity validation** (after line 401, before preview check):
```python
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
```

4. **Add value resolution** (after line 574, before fact models parsing):
```python
# Determine time_dimension_group_label value for generator
# If --no-time-dimension-group-label specified: None (explicit disable)
# If --time-dimension-group-label specified: custom value
# If neither specified: "Time Dimensions" (default via generator)
time_dim_group_label_value: str | None = "Time Dimensions"  # Default
if no_time_dimension_group_label:
    time_dim_group_label_value = None
elif time_dimension_group_label is not None:
    time_dim_group_label_value = time_dimension_group_label
```

5. **Pass to generator** (line 586):
```python
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

6. **Update docstring** (lines 359-383):
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
```

**Rationale**:
- Follows established CLI flag patterns (`--convert-tz` / `--no-convert-tz`)
- Mutually exclusive flags prevent configuration conflicts
- Clear help text explains feature and usage
- Default value set in resolution logic (not in decorator) for clarity
- Updated examples show common use cases

**Testing**:
- CLI test: `test_generate_time_dimension_group_label_flag()` in `test_cli.py`
- CLI test: `test_generate_no_time_dimension_group_label_flag()` in `test_cli.py`
- CLI test: `test_generate_mutual_exclusivity_time_dimension_labels()` in `test_cli.py`
- CLI test: `test_generate_default_time_dimension_group_label()` in `test_cli.py`

## Testing Strategy

### Unit Tests

**File**: `src/tests/unit/test_schemas.py`

New tests:
1. `test_config_meta_time_dimension_group_label_field()`: Verify field exists and accepts string/None
2. `test_dimension_time_dimension_group_label_metadata_override()`: Metadata overrides generator default
3. `test_dimension_time_dimension_group_label_default()`: Uses generator default when no override
4. `test_dimension_time_dimension_group_label_disabled()`: None value disables feature
5. `test_dimension_time_dimension_group_label_overrides_hierarchy()`: Group label overrides hierarchy group_label

**File**: `src/tests/unit/test_lookml_generator.py`

New tests:
1. `test_generator_time_dimension_group_label_parameter()`: Parameter storage and default
2. `test_generator_time_dimension_group_label_custom_value()`: Custom value passed through
3. `test_generator_time_dimension_group_label_none_disables()`: None value disables feature

**File**: `src/tests/test_cli.py`

New tests:
1. `test_generate_time_dimension_group_label_flag()`: Flag sets custom value
2. `test_generate_no_time_dimension_group_label_flag()`: Flag disables feature
3. `test_generate_mutual_exclusivity_time_dimension_labels()`: Flags are mutually exclusive
4. `test_generate_default_time_dimension_group_label()`: Default value applied when no flags

### Integration Tests

**File**: `src/tests/integration/test_end_to_end.py` (or new file)

New test:
1. `test_time_dimension_group_label_integration()`: Full flow from CLI → generator → LookML output
   - Verify dimension metadata override works
   - Verify generator default applies
   - Verify CLI flag sets value
   - Verify output LookML contains correct group_label

### Coverage Target

- All new code paths: 100% branch coverage
- Schema changes: Full validation coverage
- Generator changes: All parameter combinations
- CLI changes: All flag combinations and validation

**Estimated Coverage Impact**: +0.1% (small, focused change)

## Migration & Backward Compatibility

### Backward Compatibility

**100% backward compatible**:
1. **No breaking changes**: All new fields are optional with sensible defaults
2. **Additive only**: No changes to existing behavior when feature not used
3. **Default behavior**: "Time Dimensions" provides better organization out-of-box but doesn't break existing LookML
4. **Opt-out available**: Use `--no-time-dimension-group-label` to disable if needed

### Default Value Rationale

Using "Time Dimensions" as default (instead of None) because:
1. **Better UX**: Provides organization improvement out-of-box
2. **Non-breaking**: Adding a group_label doesn't break existing LookML
3. **Expected behavior**: Users requesting this feature expect grouping by default
4. **Easy opt-out**: Single flag (`--no-time-dimension-group-label`) to disable

### Migration Path

**No migration needed** - feature is additive:
1. Existing semantic models work unchanged
2. Existing LookML regenerates with improved grouping
3. No schema version changes required
4. No data changes required

## Documentation Updates

### CLAUDE.md Updates

Add new section after "Timezone Conversion Configuration":

```markdown
### Time Dimension Group Label Configuration

Time dimension_groups support hierarchical organization through the `group_label` parameter,
which controls how time dimensions are grouped in Looker's field picker. This feature uses
multi-level configuration with a sensible precedence chain, similar to timezone conversion.

#### Default Behavior

- **Default**: `group_label: "Time Dimensions"` (groups all time dimensions together)
- This provides better organization in Looker's field picker
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

[Include examples showing different configuration scenarios]

#### Important: Group Label Overrides Hierarchy

When `time_dimension_group_label` is set (either by default or explicitly), it **overrides**
any `group_label` from the hierarchy metadata for time dimensions. This ensures consistent
organization of all time dimensions under a common grouping.

To preserve hierarchy-based group labels for time dimensions, use
`--no-time-dimension-group-label` to disable this feature.
```

### CLI Help Text

Already included in implementation plan (Phase 5, step 1)

## Risk Assessment

### Low Risk Areas
- **Schema changes**: Simple optional field addition
- **Generator parameter**: Follows established pattern
- **CLI flags**: Mirror existing convert_tz pattern
- **Testing**: Comprehensive coverage planned

### Medium Risk Areas
- **Group label override behavior**: Overriding hierarchy labels might surprise users
  - **Mitigation**: Clear documentation and opt-out flag
  - **Mitigation**: Default value provides better UX but can be disabled

### High Risk Areas
- **None** identified

## Dependencies

### Internal Dependencies
- No new dependencies
- Uses existing Pydantic, Click, Rich libraries

### External Dependencies
- No external API changes
- No LookML spec changes (using standard `group_label` parameter)

## Acceptance Criteria

1. ✅ `ConfigMeta` has `time_dimension_group_label: str | None` field
2. ✅ `LookMLGenerator` accepts `time_dimension_group_label` parameter with default "Time Dimensions"
3. ✅ CLI has `--time-dimension-group-label` and `--no-time-dimension-group-label` flags
4. ✅ Flags are mutually exclusive with clear error message
5. ✅ Precedence chain works correctly: metadata → generator → CLI → default
6. ✅ Time dimension_groups have correct `group_label` in output LookML
7. ✅ Feature can be disabled at any configuration level
8. ✅ 95%+ branch coverage maintained
9. ✅ Documentation updated with examples
10. ✅ All tests pass

## Implementation Checklist

- [ ] Phase 1: Add `time_dimension_group_label` field to `ConfigMeta`
- [ ] Phase 2: Add parameter to `LookMLGenerator.__init__()`
- [ ] Phase 3: Implement logic in `Dimension._to_dimension_group_dict()`
- [ ] Phase 4: Update `SemanticModel.to_lookml_dict()` to pass parameter
- [ ] Phase 5: Add CLI flags and integration
- [ ] Write unit tests for schema changes
- [ ] Write unit tests for generator changes
- [ ] Write unit tests for dimension generation
- [ ] Write CLI tests for flag handling
- [ ] Write integration test for end-to-end flow
- [ ] Update CLAUDE.md with new section
- [ ] Run full test suite and verify 95%+ coverage
- [ ] Manual testing of generated LookML

## Estimated Effort

- **Schema changes**: 0.5 hours
- **Generator changes**: 1 hour
- **Dimension logic**: 1.5 hours
- **CLI integration**: 1 hour
- **Unit tests**: 2 hours
- **Integration tests**: 1 hour
- **Documentation**: 1 hour

**Total**: ~8 hours

## Related Issues

- **Parent**: [DTL-029: Epic: Improve Time Dimension Organization in LookML Field Picker](../epics/DTL-029.md)
- **Depends on**: DTL-030 (research complete)
- **Blocks**: DTL-032 (implements group_label using this configuration)
- **Related**: DTL-033 (will use same configuration mechanism for group_item_label)
