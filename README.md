# semantic-patterns

Transform semantic models (YAML) into BI tool patterns, starting with LookML views and explores.

## Overview

- Parses semantic model YAML, processes entities/dimensions/measures/metrics
- Generates `.view.lkml` and `.explore.lkml` files with proper LookML formatting
- Includes strict typing (mypy), linting (ruff), and comprehensive pytest test suite

## Requirements

- Python >= 3.10
- Optional: `uv` for fast dependency management

## Installation

### From Source

```bash
git clone https://github.com/dugshub/dbt-to-lookml.git
cd dbt-to-lookml
pip install -e .
```

### For Development

```bash
# With all dev dependencies
pip install -e ".[dev]"

# Or using uv (faster)
uv pip install -e ".[dev]"
```

## Quick Start

```bash
# Generate LookML from semantic models
sp generate -i semantic_models/ -o output/

# Or using full name
semantic-patterns generate -i semantic_models/ -o output/
```

## Project Structure

```
src/semantic_patterns/
  domain/         # Core domain models (Dimension, Measure, Metric, Model)
  ingestion/      # YAML loading and model building
  adapters/       # Output adapters (LookML)
    lookml/       # LookML generation and renderers
  __main__.py     # CLI entry point

tests/v2/         # Test suite
  fixtures/       # Test data
  test_*.py       # Test files
```

## Development

```bash
# Run tests
uv run pytest tests/v2/

# Type checking
uv run mypy src/semantic_patterns/

# Linting
uv run ruff check src/
uv run ruff format src/
```

## Testing

- Framework: pytest with coverage tracking
- Markers: `unit`, `integration`
- Run: `uv run pytest tests/v2/ -v`

## Code Style

- Ruff (line length 88; rules: E,F,I,N,W,UP)
- mypy strict type checking
- Python 3.10+
