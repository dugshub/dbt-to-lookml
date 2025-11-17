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

## Common Pitfalls

1. **Don't bypass interfaces**: Use `Parser.parse_directory()` and `Generator.write_files()`, not direct file I/O
2. **Pydantic validation**: All schema changes must maintain backward compatibility; use `Optional` for new fields
3. **Test isolation**: Unit tests should not write to disk; use fixtures and temporary directories in integration tests
4. **CLI output**: Use `rich.console.Console` for all CLI output (never print() directly in generators/parsers)
5. **Multiline YAML expressions**: The parser strips multiline expressions; ensure proper SQL formatting in generated LookML

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
