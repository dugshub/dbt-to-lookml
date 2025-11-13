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
