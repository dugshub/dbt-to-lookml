# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**dbt-to-lookml** converts dbt semantic models (YAML) into LookML views and explores. It features strict typing (mypy), comprehensive testing (pytest with 95%+ branch coverage target), and a rich CLI for validation, generation, and formatting.

## Core Architecture

### Package Structure

```
src/dbt_to_lookml/
├── interfaces/          # Abstract base classes
│   ├── parser.py       # Parser interface (strict_mode, YAML reading, error handling)
│   └── generator.py    # Generator interface (validation, file writing, formatting)
├── parsers/            # Input format parsers
│   └── dbt.py          # DbtParser - parses semantic model YAML files
├── generators/         # Output format generators
│   └── lookml.py       # LookMLGenerator - generates .view.lkml and explores.lkml
├── schemas.py          # Pydantic models for semantic models and LookML structures
├── types.py            # Enums (DimensionType, AggregationType) and type mappings
└── __main__.py         # CLI entry point (Click-based with rich output)
```

### Key Design Patterns

1. **Interface-based extensibility**: `Parser` and `Generator` base classes allow pluggable parsers/generators
2. **Strict validation**: Pydantic schemas validate all input; optional strict_mode for parsers
3. **Hierarchical labeling**: 3-tier hierarchy (entity → category → subcategory) for view_label/group_label in dimensions/measures
4. **Separation of concerns**: Parsing → Schema validation → Generation → File writing are distinct phases

### Data Flow

```
YAML files → DbtParser.parse_directory() → List[SemanticModel] →
LookMLGenerator.generate() → Dict[filename, content] →
Generator.write_files() → Physical .lkml files
```

## Development Commands

### Essential Commands

```bash
# Testing
make test              # Run unit + integration tests
make test-fast         # Run unit tests only (fastest feedback)
make test-full         # Run all test suites (unit, integration, golden, CLI, error handling)
python scripts/run-tests.py all -v  # Full test orchestration with detailed output

# Single test file
python -m pytest src/tests/unit/test_dbt_parser.py -v

# Single test method
python -m pytest src/tests/unit/test_lookml_generator.py::TestLookMLGenerator::test_generate_view_lookml -xvs

# Quick validation without writing files
uv run python -m dbt_to_lookml validate -i semantic_models/ -v

# Code Quality
make lint              # Run ruff linting
make format            # Auto-format with ruff
make type-check        # Run mypy type checking
make quality-gate      # Run lint + types + tests (pre-commit check)

# LookML Generation
make lookml-preview    # Dry-run with summary (no files written)
make lookml-generate INPUT_DIR=semantic_models OUTPUT_DIR=build/lookml
```

### Preview and Confirmation

```bash
# Show preview before generation (interactive confirmation)
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public

# Show preview only (no generation)
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public --preview

# Auto-confirm without prompt (useful for CI/automation)
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public --yes
```

### Explicit Fact Model Selection

Specify which models should generate explores using the `--fact-models` flag:

```bash
# Generate explores only for specified fact models
dbt-to-lookml generate \
  -i semantic_models/ \
  -o build/lookml/ \
  -s public \
  --fact-models rentals,orders

# Joins are discovered automatically via foreign key relationships
```

**Important:** The `--fact-models` flag is required to generate explores. If not specified, no explores will be generated (only view files).

**When to use:**
- When you want to create explores for fact tables
- When you have dimension models without measures that should be explores
- For explicit control over which models become explores

**Behavior:**

| Scenario | Behavior |
|----------|----------|
| No `--fact-models` flag | No explores generated (views only) |
| `--fact-models rentals` | Only `rentals` gets explore |
| `--fact-models rentals,orders` | Both `rentals` and `orders` get explores |
| Model not found | Warning + continue with found models |

### Test Organization

- **Unit tests** (`src/tests/unit/`): Fast, isolated tests for parsers, generators, schemas
- **Integration tests** (`src/tests/integration/`): End-to-end file parsing → LookML generation
- **Golden tests** (`src/tests/test_golden.py`): Compare generated LookML against expected output
- **CLI tests** (`src/tests/test_cli.py`): Test command-line interface
- **Error handling tests** (`src/tests/test_error_handling.py`): Test error scenarios and recovery
- **Performance tests** (`src/tests/test_performance.py`): Benchmarking (use `--include-slow` for stress tests)

Test markers: `unit`, `integration`, `golden`, `cli`, `performance`, `error_handling`, `slow`, `smoke`

### Coverage Requirements

- Target: 95% branch coverage (enforced in CI at 60% minimum, 95% for `make test-coverage`)
- Generate HTML report: `make test-coverage` → `htmlcov/index.html`

## Important Implementation Details

### Semantic Model → LookML Conversion

1. **Entities** → dimensions with `hidden: yes` (all entity types are hidden by default since they typically represent surrogate keys)
   - **Primary entities**: Get `primary_key: yes` + `hidden: yes`
   - **Foreign entities**: Get `hidden: yes` (used for join relationships)
   - **Unique entities**: Get `hidden: yes`
   - Natural keys should be exposed as regular dimensions instead
2. **Dimensions** → dimensions or dimension_groups (for time dimensions)
3. **Measures** → measures with aggregation type mapping (see `types.py:LOOKML_TYPE_MAP`)
4. **Time dimensions**: Automatically generate appropriate timeframes based on `type_params.time_granularity`

### Hierarchy Labels

Dimensions and measures support hierarchical labeling via `config.meta.hierarchy`:

```yaml
config:
  meta:
    hierarchy:
      entity: "user"           # → view_label for dimensions
      category: "demographics" # → group_label for dimensions, view_label for measures
      subcategory: "location"  # → group_label for measures
```

Implementation: `schemas.py:Dimension.get_dimension_labels()` and `schemas.py:Measure.get_measure_labels()`

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

### Field Visibility Control

The field visibility control system provides flexible mechanisms to manage which fields appear in generated LookML explores and whether fields are marked as hidden. This supports both internal/technical field hiding and selective BI field exposure.

#### Hidden Parameter

Hide fields from LookML output using the `hidden` parameter:

```yaml
dimensions:
  - name: internal_id
    type: categorical
    config:
      meta:
        hidden: true  # Field won't appear in LookML output

  - name: customer_name
    type: categorical
    # No hidden parameter - field visible (default)
```

**LookML Output** (hidden field):
```lookml
dimension: internal_id {
  hidden: yes
  type: string
  sql: ${TABLE}.internal_id ;;
}
```

#### BI Field Filtering

Selectively expose fields in explores using the `bi_field` parameter combined with CLI flag:

```yaml
dimensions:
  - name: customer_id
    type: categorical
    config:
      meta:
        bi_field: true  # Include in --bi-field-only explores

  - name: internal_notes
    type: categorical
    config:
      meta:
        bi_field: false  # Exclude from --bi-field-only explores
```

##### CLI Usage:

```bash
# Generate with all fields (default)
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public

# Generate with only bi_field: true fields exposed
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public --bi-field-only
```

#### Configuration Precedence

1. **Dimension/Measure level** (via `config.meta`)
   - `hidden: true` - Always hides the field
   - `bi_field: true` - Always includes in filtered explores
   - `bi_field: false` - Always excludes from filtered explores

2. **Generator default** (via `LookMLGenerator` parameter)
   - `use_bi_field_filter=True` - Enable filtering, include only bi_field fields
   - `use_bi_field_filter=False` (default) - All fields included, backward compatible

#### Implementation Details

- **Hidden Parameter**:
  - Applied to dimensions (both categorical and time)
  - Applied to measures
  - Generates `hidden: yes` in LookML output
  - Respected in both views and explores

- **BI Field Filtering**:
  - `LookMLGenerator._filter_fields_by_bi_field()` filters explore join fields
  - Primary keys (entities) always included for join relationships
  - Only applied when `use_bi_field_filter=True`
  - Backward compatible (disabled by default)

- **Metric Dependencies**:
  - `Metric.get_required_measures()` extracts measure dependencies
  - Supports simple, ratio, and derived metric types
  - Used for intelligent field inclusion in cross-entity metrics

#### Combined Example

```yaml
semantic_model:
  name: orders
  config:
    meta:
      hierarchy:
        entity: "order"
        category: "transactions"

  entities:
    - name: order_id
      type: primary

  dimensions:
    - name: internal_hash
      type: categorical
      config:
        meta:
          hidden: true  # Hide internal field

    - name: customer_name
      type: categorical
      config:
        meta:
          bi_field: true  # Include in BI filtering

    - name: warehouse_id
      type: categorical
      config:
        meta:
          bi_field: false  # Exclude from BI filtering

  measures:
    - name: revenue
      agg: sum
      config:
        meta:
          bi_field: true  # Include in BI filtering

    - name: internal_cost
      agg: sum
      config:
        meta:
          hidden: true  # Hide from BI
          bi_field: false
```

**Generated LookML behavior**:
- `internal_hash` dimension: Not in LookML (hidden)
- `customer_name` dimension: In explores with `--bi-field-only`
- `warehouse_id` dimension: In explores without `--bi-field-only`, excluded with flag
- `revenue` measure: In explores with `--bi-field-only`
- `internal_cost` measure: Not in LookML (hidden)

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
   dbt-to-lookml generate -i semantic_models -o build/lookml \
       --time-dimension-group-label "Time Periods"

   # Disable grouping (preserves hierarchy labels)
   dbt-to-lookml generate -i semantic_models -o build/lookml \
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
dbt-to-lookml generate -i semantic_models/ -o build/lookml \
    --time-dimension-group-label "Time Fields"

# Generate with grouping disabled (preserves hierarchy labels)
dbt-to-lookml generate -i semantic_models/ -o build/lookml \
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

#### Enhanced Organization with group_item_label

The `group_item_label` feature provides cleaner field labels in Looker's field picker by using a Liquid template
to extract just the timeframe name (e.g., "Date", "Week") instead of repeating the dimension name for each timeframe.

##### Example 4: Using group_item_label for Cleaner Labels
```yaml
# semantic_models/rentals.yaml
semantic_model:
  name: rentals
  dimensions:
    - name: created_at
      type: time
      type_params:
        time_granularity: day
      config:
        meta:
          group_item_label: true  # Enable cleaner timeframe labels
```

**CLI Command**:
```bash
# Enable group_item_label for all time dimensions
dbt-to-lookml generate -i semantic_models/ -o build/lookml \
    --use-group-item-label
```

**Generated LookML**:
```lookml
dimension_group: rental_created {
  label: "Rental Created"
  group_label: "Time Dimensions"
  group_item_label: "{% assign tf = _field._name | remove: 'rental_created_' | replace: '_', ' ' | capitalize %}{{ tf }}"
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.rental_created_at ;;
  convert_tz: no
}
```

**Field Picker Result** (with `group_item_label`):
```
Time Dimensions
  Rental Created
    Date         ← Cleaner: "Date" instead of "Rental Created Date"
    Week         ← Cleaner: "Week" instead of "Rental Created Week"
    Month
    Quarter
    Year
```

#### Field Picker Organization: Before and After

**Before** (Without time dimension organization):
```
DIMENSIONS
  Rental Created Date
  Rental Created Week
  Rental Created Month
  Rental Created Quarter
  Rental Created Year
  Rental Updated Date
  Rental Updated Week
  Rental Updated Month
  Rental Updated Quarter
  Rental Updated Year
  Customer Name
  Location
```
Problem: All timeframes are in a flat list, mixed with other dimensions.

**After** (With default time dimension organization):
```
DIMENSIONS
  Time Dimensions
    Rental Created
      Rental Created Date
      Rental Created Week
      Rental Created Month
      Rental Created Quarter
      Rental Created Year
    Rental Updated
      Rental Updated Date
      Rental Updated Week
      Rental Updated Month
      Rental Updated Quarter
      Rental Updated Year
  Customer Name
  Location
```
Solution: Time dimensions are grouped hierarchically under "Time Dimensions".

**After** (With group_item_label enabled):
```
DIMENSIONS
  Time Dimensions
    Rental Created
      Date         ← Cleaner labels
      Week
      Month
      Quarter
      Year
    Rental Updated
      Date
      Week
      Month
      Quarter
      Year
  Customer Name
  Location
```
Enhancement: `group_item_label` removes redundant dimension name repetition.

#### Combined Example: All Features Together

This example demonstrates combining `group_label`, `group_item_label`, and `convert_tz`:

```yaml
semantic_model:
  name: transactions
  dimensions:
    - name: transaction_date
      type: time
      type_params:
        time_granularity: day
      config:
        meta:
          time_dimension_group_label: "Transaction Timeline"  # Custom group
          group_item_label: true                              # Clean labels
          convert_tz: yes                                     # Timezone conversion
```

**Generated LookML**:
```lookml
dimension_group: transaction_date {
  label: "Transaction Date"
  group_label: "Transaction Timeline"
  group_item_label: "{% assign tf = _field._name | remove: 'transaction_date_' | replace: '_', ' ' | capitalize %}{{ tf }}"
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.transaction_date ;;
  convert_tz: yes
}
```

#### Extended Implementation Details

- **group_item_label Parameter** (`LookMLGenerator`):
  - `use_group_item_label: bool = False`
  - Enables `group_item_label` in all time dimension_groups
  - Uses Liquid templating to extract timeframe names
  - Disabled by default (backward compatible)

- **Dimension._to_dimension_group_dict()**: Extended logic
  - Checks `config.meta.group_item_label` for dimension-level override
  - Falls back to `use_group_item_label` parameter from generator
  - Generates Liquid template when enabled:
    - Extracts field name suffix (the timeframe part)
    - Removes dimension name prefix
    - Capitalizes for display (Date, Week, etc.)

- **CLI Flag**: `--use-group-item-label`
  - Enables group_item_label feature for all time dimensions
  - Works in combination with `--time-dimension-group-label`
  - Optional flag (disabled by default)

#### Configuration Precedence Summary

For time dimension organization, the complete precedence chain is:

1. **Dimension Metadata** (Highest priority)
   - `time_dimension_group_label` - Custom group label for this dimension
   - `group_item_label` - Enable clean timeframe labels for this dimension

2. **Generator Parameters**
   - `time_dimension_group_label` - Apply group label to all dimensions
   - `use_group_item_label` - Enable clean labels for all dimensions

3. **CLI Flags**
   - `--time-dimension-group-label TEXT` - Custom group label
   - `--no-time-dimension-group-label` - Disable grouping
   - `--use-group-item-label` - Enable clean labels

4. **Defaults** (Lowest priority)
   - `group_label: "Time Dimensions"` - Default grouping
   - `group_item_label` disabled - Default is full field names

### Parser Error Handling

- `DbtParser` supports `strict_mode` (fail fast) vs. lenient mode (log warnings, continue)
- Base `Parser.handle_error()` provides consistent error handling
- CLI commands parse files individually to provide granular error reporting per file

### Generator Validation

- `LookMLGenerator.validate_output()` uses the `lkml` library to parse and validate syntax
- Validation runs automatically during file writing unless `--no-validation` is passed
- Validation errors are collected and reported at the end without stopping generation

## Code Style

- **Type hints**: All functions must have type hints (enforced by mypy --strict)
- **Line length**: 88 characters (Black-compatible)
- **Imports**: Sorted with ruff (isort rules)
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Docstrings**: Google-style docstrings for all public functions/classes

## Wizard System Architecture

The wizard system provides interactive command building through a structured architecture with project detection, prompt sequencing, and validation.

### Module Structure

```
src/dbt_to_lookml/wizard/
├── __init__.py              # Public API exports
├── base.py                  # BaseWizard abstract class (mode, config storage)
├── types.py                 # TypedDict definitions (WizardConfig, WizardMode)
├── detection.py             # ProjectDetector (structure analysis, smart defaults)
├── generate_wizard.py       # GenerateWizard (prompts, validation, command building)
├── tui.py                   # GenerateWizardTUI (Textual-based UI, optional)
└── tui_widgets.py          # Custom Textual widgets (input, preview panels)
```

### Design Patterns

1. **Detection-First**: Analyze project structure before prompting
   - `ProjectDetector` scans for semantic_models directories
   - Extracts schema hints from YAML files
   - Suggests output directories based on conventions
   - Results cached for performance (500ms target detection time)

2. **Progressive Enhancement**: Graceful degradation when dependencies missing
   - Core wizard uses `questionary` (required in `pyproject.toml`)
   - TUI mode uses `textual` (optional, skipped if unavailable)
   - Falls back to prompt mode automatically

3. **Validation Pipeline**: Multi-stage input validation
   - Real-time validation during prompts using `questionary.Validator`
   - Path existence and type checks via `PathValidator`
   - Schema name format validation via `SchemaValidator`
   - Final config validation before command building

### Key Components

#### Detection Module (`wizard/detection.py`)

**Purpose**: Analyze project structure and provide smart defaults

**Main Classes**:
- `ProjectDetector`: Scans filesystem, caches results with TTL
- `DetectionResult`: NamedTuple with input_dir, output_dir, schema_name, file counts
- `DetectionCache`: Simple TTL cache for detection results

**Usage**:
```python
from dbt_to_lookml.wizard.detection import ProjectDetector

detector = ProjectDetector(working_dir=Path.cwd())
result = detector.detect()

if result.has_semantic_models():
    print(f"Found: {result.input_dir}")
```

#### Generate Wizard (`wizard/generate_wizard.py`)

**Purpose**: Interactive prompts for building generate commands

**Main Classes**:
- `GenerateWizardConfig`: Dataclass with all command options
- `PathValidator`: Custom questionary validator for filesystem paths
- `SchemaValidator`: Custom questionary validator for schema names
- `GenerateWizard`: Main wizard orchestrating prompts and config

**Prompt Sequence**:
1. Input directory (with detection default)
2. Output directory (with suggested default)
3. Schema name (with detected default from YAML)
4. View prefix (optional, empty default)
5. Explore prefix (optional, empty default)
6. Connection name (default: "redshift_test")
7. Model name (default: "semantic_model")
8. Timezone conversion (three-choice select: No/Yes/Explicitly disable)
9. Additional options (checkboxes: dry-run, no-validation, show-summary)

**Command Building**:
```python
config = GenerateWizardConfig(
    input_dir=Path("semantic_models"),
    output_dir=Path("build/lookml"),
    schema="analytics",
)
command = config.to_command_string(multiline=True)
# Returns: "dbt-to-lookml generate \\\n  -i semantic_models \\\n  -o build/lookml \\\n  -s analytics"
```

### Testing Strategy

#### Unit Tests (95%+ coverage target)

**Detection Tests** (`src/tests/unit/test_wizard_detection.py`):
- Directory detection scenarios (semantic_models, models/semantic, etc.)
- Multiple candidate priority handling
- Missing/empty directory handling
- Permission and symlink error handling
- Cache functionality and TTL expiration

**Generate Wizard Tests** (`src/tests/unit/test_generate_wizard.py`):
- Config dataclass command building (all option combinations)
- Validator classes (PathValidator, SchemaValidator)
- Wizard prompt methods with mocked questionary
- Full wizard flow with sequential mocks
- Error handling and cancellation scenarios
- Detection integration with mocked ProjectDetector

**Mocking Patterns**:
```python
# Mock questionary prompts
@patch("dbt_to_lookml.wizard.generate_wizard.questionary.text")
def test_wizard(mock_text):
    mock_text.return_value.ask.return_value = "user_input"
    wizard = GenerateWizard()
    result = wizard._prompt_schema()
    assert result == "user_input"

# Mock filesystem detection
@patch("dbt_to_lookml.wizard.detection.ProjectDetector")
def test_detection(mock_detector_class):
    mock_detector = MagicMock()
    mock_detector_class.return_value = mock_detector
    mock_detector.detect.return_value = MagicMock(input_dir=Path(...))
```

#### Integration Tests (`src/tests/integration/test_wizard_integration.py`)

- Realistic project structure creation with semantic models
- Full wizard flow with mocked prompts and real file operations
- Detection + wizard + generator end-to-end workflows
- Error recovery and validation failure scenarios

#### CLI Tests (`src/tests/test_cli.py::TestCLIWizard`)

- Wizard command help text and availability
- Wizard generate subcommand testing
- TUI flag handling (with/without Textual)
- Non-interactive mode handling

### Coverage Requirements

**Per-Module Targets**:
- `wizard/detection.py`: 95%+ branch coverage
- `wizard/generate_wizard.py`: 95%+ branch coverage
- `wizard/base.py`: 95%+ branch coverage
- `wizard/tui.py`: 85%+ coverage (optional feature)
- `wizard/tui_widgets.py`: 85%+ coverage (optional feature)

**Overall Wizard Coverage**: 95%+

### Error Handling

**Error Categories**:
1. **User Input Errors**: Real-time validation prevents invalid input
   - Empty paths → "Path cannot be empty"
   - Nonexistent directories → "Path does not exist"
   - Invalid schema names → "Schema can only contain letters, numbers, _, -"
   - User can re-enter or cancel with Ctrl-C

2. **Filesystem Errors**: Graceful handling of permission/symlink issues
   - Detection skips restricted directories
   - PathValidator catches existence checks

3. **Detection Failures**: Graceful degradation
   - If detection fails, wizard continues with empty defaults
   - User still provides full config via prompts

4. **Execution Errors**: Command validation before execution
   - Config validation in `validate_config()`
   - LookML syntax validation during generation

### Performance Considerations

**Detection Performance**:
- Target: < 500ms for detection on typical project
- Caching with 5-minute TTL to reduce repeated scans
- Limits directory traversal depth (max 3 levels)
- Skips large directories (.git, node_modules, .venv)

**Prompt Performance**:
- < 100ms between prompts (questionary response time)
- Target total wizard flow: < 2 minutes (mostly user think time)

## Common Pitfalls

1. **Don't bypass interfaces**: Use `Parser.parse_directory()` and `Generator.write_files()`, not direct file I/O
2. **Pydantic validation**: All schema changes must maintain backward compatibility; use `Optional` for new fields
3. **Test isolation**: Unit tests should not write to disk; use fixtures and temporary directories in integration tests
4. **CLI output**: Use `rich.console.Console` for all CLI output (never print() directly in generators/parsers)
5. **Multiline YAML expressions**: The parser strips multiline expressions; ensure proper SQL formatting in generated LookML
6. **Wizard mocking**: Mock questionary at the module level where it's used (`dbt_to_lookml.wizard.generate_wizard.questionary`), not at import level
7. **Detection caching**: Be aware of 5-minute cache TTL when testing detection; use `cache_enabled=False` for tests

## Python Version

- **Minimum**: Python 3.9 (specified in `pyproject.toml`)
- **Development**: Tested on Python 3.9-3.13
- **Package manager**: `uv` is preferred for fast dependency management (`uv.lock` is committed)

## Installation for Development

```bash
# Clone and install in editable mode
git clone https://github.com/dugshub/dbt-to-lookml.git
cd dbt-to-lookml
pip install -e ".[dev]"  # or: uv pip install -e ".[dev]"

# Verify installation
dbt-to-lookml --version
make validate-setup
```

## CI/CD Notes

- GitHub Actions workflow: `.github/workflows/test.yml`
- Use `make ci-test` to generate JSON test report (`test_results.json`)
- Quality gate must pass before merge: lint + types + tests
