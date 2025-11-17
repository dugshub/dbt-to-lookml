# Implementation Strategy: DTL-013

**Issue**: DTL-013 - Update documentation for timezone conversion feature
**Analyzed**: 2025-11-12T20:30:00Z
**Stack**: backend (documentation)
**Type**: chore

## Approach

Update comprehensive documentation across the project to explain the new timezone conversion configuration feature introduced in the DTL-007 epic. This is a multi-level documentation update that includes:

1. **CLAUDE.md** - Add a comprehensive section documenting the timezone conversion feature, precedence chain, and usage examples at each configuration level
2. **Docstrings** - Enhance docstrings in `Dimension` and `LookMLGenerator` classes with examples and type hints
3. **README.md** - Add a brief reference note about timezone conversion capabilities
4. **CLI Help Text** - Verify that CLI help text clearly documents the `--convert-tz` and `--no-convert-tz` flags (already implemented in DTL-010)

The documentation strategy follows the project's existing style conventions (Google-style docstrings, clear examples, emphasis on precedence and configuration levels) and maintains consistency with the CLAUDE.md project guidelines.

## Architecture Impact

**Layer**: documentation (developer guidance)

**New Files**: None

**Modified Files**:
- `CLAUDE.md` - Add "Timezone Conversion Configuration" section to "Important Implementation Details"
- `src/dbt_to_lookml/schemas.py` - Enhance docstrings in:
  - `Dimension._to_dimension_group_dict()` - Add examples showing convert_tz parameter usage
  - `ConfigMeta` class - Document convert_tz field if added to schema
- `src/dbt_to_lookml/generators/lookml.py` - Enhance docstring in:
  - `LookMLGenerator.__init__()` - Document convert_tz parameter, precedence, and defaults
- `README.md` - Add brief reference to timezone conversion in CLI Usage or Features section

## Dependencies

**Depends on**:
- DTL-007 (Epic - completed)
- DTL-008 (Dimension schema updates - completed)
- DTL-009 (Generator layer updates - completed)
- DTL-010 (CLI flags - completed)
- DTL-011 (Unit tests - completed)
- DTL-012 (Integration/golden tests - completed)

**Documentation References**:
- Existing CLAUDE.md sections on "Semantic Model → LookML Conversion" and "Hierarchy Labels"
- Project conventions for Google-style docstrings
- README.md structure for CLI documentation

## Implementation Plan

### Phase 1: CLAUDE.md Documentation (Primary Update)

**File**: `/Users/dug/Work/repos/dbt-to-lookml/CLAUDE.md`

**Section Location**: Insert after "Hierarchy Labels" section in "Important Implementation Details"

**Content to Add**:

```markdown
### Timezone Conversion Configuration

LookML dimension_groups support timezone conversion through the `convert_tz` parameter, which controls whether timestamp values are converted from database timezone to the user's viewing timezone. This feature supports multi-level configuration with a sensible precedence chain.

#### Default Behavior

- **Default**: `convert_tz: no` (timezone conversion explicitly disabled)
- This prevents unexpected timezone shifts and provides predictable behavior
- Users must explicitly enable timezone conversion if needed

#### Configuration Levels (Precedence: Highest to Lowest)

1. **Dimension Metadata Override** (Highest priority)
   ```yaml
   dimensions:
     - name: created_at
       type: time
       config:
         meta:
           convert_tz: yes  # Enable for this dimension only
   ```

2. **Generator Parameter**
   ```python
   generator = LookMLGenerator(
       view_prefix="my_",
       convert_tz=True  # Apply to all dimensions (unless overridden)
   )
   ```

3. **CLI Flag**
   ```bash
   # Enable timezone conversion for all dimensions
   dbt-to-lookml generate -i semantic_models -o build/lookml --convert-tz

   # Explicitly disable (useful for override)
   dbt-to-lookml generate -i semantic_models -o build/lookml --no-convert-tz
   ```

4. **Default** (Lowest priority)
   - `convert_tz: no` - Applied when no explicit configuration provided

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
          convert_tz: yes  # This dimension enables timezone conversion

    - name: shipped_at
      type: time
      type_params:
        time_granularity: day
      # No convert_tz specified, uses generator/CLI/default
```

**Generated LookML**:
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: yes
}

dimension_group: shipped_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.shipped_at ;;
  convert_tz: no
}
```

##### Example 2: Generator-Level Configuration
```python
from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser

parser = DbtParser()
models = parser.parse_directory("semantic_models/")

# Enable timezone conversion for all dimension_groups
generator = LookMLGenerator(
    view_prefix="stg_",
    convert_tz=True  # All dimensions use convert_tz: yes unless overridden
)

output = generator.generate(models)
generator.write_files("build/lookml", output)
```

##### Example 3: CLI Usage
```bash
# Generate with timezone conversion enabled globally
dbt-to-lookml generate -i semantic_models/ -o build/lookml --convert-tz

# Generate with timezone conversion disabled (explicit, useful to override scripts)
dbt-to-lookml generate -i semantic_models/ -o build/lookml --no-convert-tz

# Generate with default behavior (convert_tz: no)
dbt-to-lookml generate -i semantic_models/ -o build/lookml
```

#### Implementation Details

- **Dimension._to_dimension_group_dict()**: Accepts `default_convert_tz` parameter from generator
  - Checks `config.meta.convert_tz` first (dimension-level override)
  - Falls back to `default_convert_tz` parameter
  - Falls back to `False` if neither specified

- **LookMLGenerator.__init__()**: Accepts optional `convert_tz: bool | None` parameter
  - Stores the setting as instance variable
  - Propagates to `SemanticModel.to_lookml_dict()` during generation

- **SemanticModel.to_lookml_dict()**: Accepts `convert_tz` parameter
  - Passes to each `Dimension._to_dimension_group_dict()` call

- **CLI Flags**: Mutually exclusive `--convert-tz` / `--no-convert-tz` options
  - `--convert-tz`: Sets `convert_tz=True`
  - `--no-convert-tz`: Sets `convert_tz=False`
  - Neither: Uses `convert_tz=None` (default behavior)

#### LookML Output Examples

With `convert_tz: no` (default):
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: no
}
```

With `convert_tz: yes`:
```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  convert_tz: yes
}
```
```

### Phase 2: Docstring Updates

**File**: `src/dbt_to_lookml/schemas.py`

**Update**: `Dimension._to_dimension_group_dict()` docstring

**Current**:
```python
def _to_dimension_group_dict(self) -> dict[str, Any]:
    """Convert time dimension to LookML dimension_group."""
```

**Updated**:
```python
def _to_dimension_group_dict(
    self, default_convert_tz: bool | None = None
) -> dict[str, Any]:
    """Convert time dimension to LookML dimension_group.

    Generates a LookML dimension_group block with appropriate timeframes based on
    the dimension's time_granularity setting. Supports timezone conversion configuration
    through multi-level precedence:

    1. Dimension-level override via config.meta.convert_tz (highest priority)
    2. Generator default via default_convert_tz parameter
    3. Hardcoded default of False (lowest priority)

    Args:
        default_convert_tz: Default timezone conversion setting from generator or CLI.
            - True: Enable timezone conversion for all dimensions (unless overridden)
            - False: Disable timezone conversion (default behavior)
            - None: Use generator default (False)

    Returns:
        Dictionary with dimension_group configuration including:
        - name: Dimension name
        - type: "time"
        - timeframes: List of appropriate timeframes based on granularity
        - sql: SQL expression for the timestamp column
        - convert_tz: "yes" or "no" based on precedence rules
        - description: Optional description
        - label: Optional label
        - view_label/group_label: Optional hierarchy labels

    Example:
        # Dimension with metadata override (enables timezone conversion)
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(
                convert_tz=True  # Override any generator default
            ))
        )
        result = dimension._to_dimension_group_dict(default_convert_tz=False)
        # Result includes: "convert_tz": "yes" (meta override takes precedence)

        # Dimension without override (uses generator default)
        dimension = Dimension(
            name="shipped_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "hour"}
        )
        result = dimension._to_dimension_group_dict(default_convert_tz=True)
        # Result includes: "convert_tz": "yes" (from default_convert_tz parameter)
    """
```

**File**: `src/dbt_to_lookml/generators/lookml.py`

**Update**: `LookMLGenerator.__init__()` docstring

**Current**:
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
) -> None:
    """Initialize the generator.

    Args:
        view_prefix: Prefix to add to view names.
        explore_prefix: Prefix to add to explore names.
        validate_syntax: Whether to validate generated LookML syntax.
        format_output: Whether to format LookML output for readability.
        schema: Database schema name for sql_table_name.
        connection: Looker connection name for the model file.
        model_name: Name for the generated model file (without .model.lkml extension).
    """
```

**Updated**:
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
) -> None:
    """Initialize the generator.

    Configures LookML generation with support for timezone conversion, view/explore
    naming, syntax validation, and output formatting. The convert_tz parameter establishes
    the default timezone behavior for all generated dimension_groups, which can be
    overridden at the dimension level through semantic model metadata.

    Args:
        view_prefix: Prefix to add to all generated view names. Useful for namespacing
            views by environment or project.
        explore_prefix: Prefix to add to all generated explore names. Works alongside
            view_prefix for consistent naming conventions.
        validate_syntax: Whether to validate generated LookML syntax using the lkml
            library. Validation runs automatically unless explicitly disabled.
        format_output: Whether to format LookML output for human readability. Applies
            consistent indentation and spacing to generated files.
        schema: Database schema name for sql_table_name in generated views. Used to
            qualify table references (e.g., "public.orders").
        connection: Looker connection name for the generated .model.lkml file.
            This tells Looker which database connection to use for the model.
        model_name: Name for the generated model file (without .model.lkml extension).
            Allows multiple models to be generated from different semantic model sets.
        convert_tz: Default timezone conversion setting for all dimension_groups.
            Controls the convert_tz parameter in generated LookML dimension_groups.
            - True: Enable timezone conversion globally (convert_tz: yes in LookML)
            - False: Disable timezone conversion globally (convert_tz: no in LookML)
            - None: Use hardcoded default (False, disabled by default)
            This setting is overridden by per-dimension config.meta.convert_tz in
            semantic models, allowing fine-grained control at the dimension level.

    Example:
        # Enable timezone conversion globally
        generator = LookMLGenerator(
            view_prefix="fact_",
            convert_tz=True
        )

        # Disable timezone conversion (explicit default)
        generator = LookMLGenerator(
            view_prefix="dim_",
            convert_tz=False
        )

        # Use hardcoded default (False, but dimension metadata can still override)
        generator = LookMLGenerator(view_prefix="stg_")

    See Also:
        - CLAUDE.md: "Timezone Conversion Configuration" section for multi-level
          precedence rules and detailed examples
        - Dimension._to_dimension_group_dict(): Implements timezone conversion logic
          with precedence handling
        - CLI: Use --convert-tz / --no-convert-tz flags for command-line control
    """
```

### Phase 3: ConfigMeta Documentation Update

**File**: `src/dbt_to_lookml/schemas.py`

**Update**: `ConfigMeta` class docstring to document convert_tz field

**Current**:
```python
class ConfigMeta(BaseModel):
    """Represents metadata in a config section."""

    domain: str | None = None
    owner: str | None = None
    contains_pii: bool | None = None
    update_frequency: str | None = None
    subject: str | None = None
    category: str | None = None
    hierarchy: Hierarchy | None = None
```

**Updated**:
```python
class ConfigMeta(BaseModel):
    """Represents metadata in a config section.

    Supports flexible metadata configuration for dimensions and measures, including
    optional hierarchy labels, data governance tags, and feature-specific overrides
    like timezone conversion.

    Attributes:
        domain: Data domain classification (e.g., "customer", "product").
        owner: Owner or team responsible for this data element.
        contains_pii: Whether the dimension contains personally identifiable information.
        update_frequency: How frequently the underlying data is updated
            (e.g., "daily", "real-time").
        subject: Flat structure view label for dimensions (preferred over hierarchy).
        category: Flat structure group label for dimensions/measures (preferred over hierarchy).
        hierarchy: Nested hierarchy structure for 3-tier labeling:
            - entity: Maps to view_label for dimensions
            - category: Maps to group_label for dimensions, view_label for measures
            - subcategory: Maps to group_label for measures
        convert_tz: Override timezone conversion behavior for this specific dimension.
            Controls whether the dimension_group's convert_tz parameter is set to yes/no.
            - True/yes: Enable timezone conversion (convert_tz: yes in LookML)
            - False/no: Disable timezone conversion (convert_tz: no in LookML)
            - Omitted: Use generator or CLI default setting
            This provides the highest-priority override in the configuration precedence chain.

    Example:
        # Dimension with timezone override and hierarchy labels
        config:
          meta:
            domain: "events"
            owner: "analytics"
            contains_pii: false
            convert_tz: yes  # Override generator default for this dimension
            hierarchy:
              entity: "event"
              category: "timing"
              subcategory: "creation"
    """
```

### Phase 4: README.md Update (Optional)

**File**: `README.md`

**Location**: In "CLI Usage" section or add brief note to "Features"

**Content to Add** (if not already documented):

In the CLI Usage section, add:

```markdown
## Timezone Conversion

Control timezone conversion in generated dimension_groups with CLI flags:
- `--convert-tz`: Enable timezone conversion for all dimensions
- `--no-convert-tz`: Disable timezone conversion for all dimensions
- (No flag): Use default behavior (convert_tz: no, disabled by default)

Per-dimension overrides are supported via `config.meta.convert_tz` in semantic models.
See CLAUDE.md "Timezone Conversion Configuration" for detailed precedence rules and examples.
```

Or, if README.md is already comprehensive, add a link in the CLI section:

```
See CLAUDE.md "Timezone Conversion Configuration" for timezone control details and examples.
```

## Acceptance Criteria

### Must-Have Criteria

- [ ] **CLAUDE.md** - Comprehensive "Timezone Conversion Configuration" section added with:
  - [ ] Default behavior clearly explained (convert_tz: no)
  - [ ] All 4 configuration levels documented
  - [ ] Precedence chain clearly illustrated
  - [ ] 3+ examples (dimension metadata, generator, CLI)
  - [ ] Generated LookML examples showing convert_tz output
  - [ ] Implementation details section explaining code flow

- [ ] **Docstrings** - Enhanced with examples and comprehensive documentation:
  - [ ] `Dimension._to_dimension_group_dict()` docstring updated with parameter docs and examples
  - [ ] `LookMLGenerator.__init__()` docstring includes convert_tz parameter with examples
  - [ ] `ConfigMeta` class docstring documents convert_tz field
  - [ ] All docstrings follow Google-style format
  - [ ] Type hints are correct (bool | None, etc.)

- [ ] **README.md** - Timezone conversion feature briefly documented:
  - [ ] CLI flags explained
  - [ ] Reference to CLAUDE.md for detailed documentation
  - [ ] Precedence rules summarized or linked

### Should-Have Criteria

- [ ] Code examples are copy-paste ready and syntactically correct
- [ ] Examples cover common use cases (global setting, per-dimension override, CLI usage)
- [ ] Documentation reflects actual implementation behavior
- [ ] Links between sections are consistent (e.g., See Also sections)

### Nice-to-Have Criteria

- [ ] Documentation includes troubleshooting section (common mistakes)
- [ ] Links to related GitHub issues or discussions
- [ ] Consistency check with other features' documentation style

## Testing Strategy

Documentation validation is primarily manual/review-based:

1. **Syntax Check**: Verify all code examples are syntactically valid
   - YAML examples are valid YAML
   - Python examples are valid Python
   - LookML examples are valid LookML (can be checked with lkml library)

2. **Accuracy Check**: Verify documentation matches implementation
   - Run through examples mentally to ensure they produce expected output
   - Check that precedence examples work as documented
   - Verify default behavior matches code (convert_tz: no)

3. **Consistency Check**: Verify documentation style and completeness
   - All docstrings follow Google-style format
   - Cross-references are accurate
   - No broken links between documents

4. **Completeness Check**: Verify all required topics are covered
   - Default behavior explained
   - All configuration levels documented
   - Precedence chain clear
   - Examples provided for each level

## Success Metrics

1. **Clarity**: Documentation is clear enough for new developers to understand
   - Timezone conversion concepts
   - How to configure at each level
   - Precedence rules and when to use each approach

2. **Completeness**: All required sections are documented
   - CLAUDE.md section added with full detail
   - Docstrings enhanced with examples
   - README.md references timezone feature

3. **Accuracy**: Documentation matches implementation
   - Code examples produce expected output
   - Default behavior correctly documented
   - Precedence rules correctly explained

4. **Style Consistency**: Documentation follows project conventions
   - Google-style docstrings
   - Consistent formatting
   - Similar structure to other feature documentation

## Potential Risks

1. **Documentation Drift**: If timezone conversion implementation changes, this documentation could become outdated
   - **Mitigation**: Update documentation in the same PR as implementation changes

2. **Incomplete Coverage**: Important use cases might be missed
   - **Mitigation**: Include troubleshooting section with common mistakes

3. **Examples Not Tested**: Code examples might have subtle errors
   - **Mitigation**: Run examples through lkml library for validation

## Time Estimate

- CLAUDE.md comprehensive section: 1-2 hours
- Docstring updates: 30-45 minutes
- README.md update: 15-30 minutes
- Review and refinement: 30-45 minutes
- **Total**: 2.5-4 hours

## Next Steps

1. Create CLAUDE.md section with timezone conversion details
2. Update Dimension and LookMLGenerator docstrings
3. Update ConfigMeta docstring
4. Add optional README.md reference
5. Review for accuracy against implementation
6. Get team review and approval
7. Merge to main branch
