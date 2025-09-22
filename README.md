# dbt-to-lookml

Convert dbt semantic models into LookML views and explores with validation, formatting, and a friendly CLI.

## Overview
- Parses dbt semantic model YAML, maps entities/dimensions/measures, and emits `.view.lkml` and `explores.lkml`.
- Includes strict typing (mypy), linting (ruff), and a comprehensive pytest suite with high coverage.

## Requirements
- Python >= 3.13
- Optional: `uv` for fast, locked dependency management (repo includes `uv.lock`).

## Installation

### From Source (Recommended for now)
```bash
git clone https://github.com/yourusername/dbt-to-lookml.git
cd dbt-to-lookml
pip install -e .
```

### Using Pre-built Package
```bash
# Build the package
python -m build

# Install from wheel
pip install dist/dbt_to_lookml-0.1.0-py3-none-any.whl
```

### For Development
```bash
# With all dev dependencies
pip install -e ".[dev]"

# Or using uv (faster)
uv pip install -e ".[dev]"
```

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

## Quickstart
1) Place semantic model YAML files in a folder (e.g., `semantic_models/`).
2) Dry-run generation to preview outputs:
   - `dbt-to-lookml generate -i semantic_models -o build/lookml --dry-run --show-summary`
3) Write LookML files:
   - `dbt-to-lookml generate -i semantic_models -o build/lookml`
4) Validate models without generating files:
   - `dbt-to-lookml validate -i semantic_models -v`

## CLI Usage
- `dbt-to-lookml generate -i <input_dir> -o <output_dir> [--view-prefix X] [--explore-prefix Y] [--dry-run] [--no-validation] [--no-formatting] [--show-summary]`
- `dbt-to-lookml validate -i <input_dir> [--strict] [-v]`

## Project Structure
- `src/dbt_to_lookml/`: Core package (`parser.py`, `generator.py`, `models.py`, CLI)
- `tests/`: Unit, integration, CLI, golden, performance, and error-handling tests
- `scripts/`: Tooling scripts and utilities
- `semantic_models/`: Sample inputs for testing/experiments
- `Makefile`: Common dev commands
- `USAGE.md`: Detailed CLI usage guide
- `INSTALL.md`: Installation instructions

## Development
- Common commands (see `Makefile`):
  - `make test` (unit + integration), `make test-full`, `make test-fast`
  - `make lint` (ruff), `make type-check` (mypy), `make format`
  - `make quality-gate` (lint + types + tests)
- Run the full test orchestration script:
  - `python scripts/run-tests.py all -v`

## Testing
- Framework: pytest; coverage threshold enforced at 95% branch coverage.
- Markers: `unit`, `integration`, `golden`, `cli`, `performance`, `error_handling`, `smoke`, `slow`.
- Examples:
  - `pytest -m unit -q`
  - `pytest tests/unit/test_parser.py -q`
  - `make test-coverage` (HTML at `htmlcov/index.html`)

## Code Style
- Ruff (line length 88; rules: E,F,I,N,W,UP) and mypy strict type checking.
- Format and fix before committing: `make format` and `make lint`.

## Contributing
- Please read `AGENTS.md` (Repository Guidelines) for coding style, tests, commit/PR conventions, and security notes.
