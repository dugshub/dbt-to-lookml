# semantic-patterns

<!-- Badges placeholder -->
<!-- [![CI](https://github.com/dugshub/semantic-patterns/actions/workflows/ci.yml/badge.svg)](https://github.com/dugshub/semantic-patterns/actions/workflows/ci.yml) -->
<!-- [![PyPI](https://img.shields.io/pypi/v/semantic-patterns.svg)](https://pypi.org/project/semantic-patterns/) -->
<!-- [![Python](https://img.shields.io/pypi/pyversions/semantic-patterns.svg)](https://pypi.org/project/semantic-patterns/) -->

Transform semantic models (YAML) into BI tool patterns, starting with LookML views and explores.

## Why semantic-patterns?

**The Problem**: Analytics teams spend significant time manually translating semantic definitions into BI tool configurations. This leads to:
- Inconsistent naming and logic between data models and dashboards
- Drift between semantic definitions and BI implementations
- Tedious, error-prone manual work maintaining LookML, Cube.js, or other BI configs

**The Solution**: semantic-patterns automates this translation. Define your dimensions, measures, and metrics once in a clean YAML format, and generate consistent BI tool configurations automatically.

**Key Benefits**:
- **Single source of truth** - Semantic definitions drive BI tool output
- **Consistency** - Generated configs follow best practices and naming conventions
- **Speed** - Go from semantic model to working LookML in seconds
- **Flexibility** - Supports dbt Semantic Layer format or native semantic-patterns YAML
- **Extensible** - Clean adapter architecture for adding new output formats (Cube.js, MetricFlow, etc.)

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
# Create a config file in your project
sp init

# Build LookML from semantic models
sp build

# Preview without writing files
sp build --dry-run

# Use specific config file
sp build --config ./configs/sp.yml
```

## Project Structure

```
semantic_patterns/
  domain/         # Core domain models (Dimension, Measure, Metric, Model)
  ingestion/      # YAML loading and model building
  adapters/       # Output adapters (LookML)
    lookml/       # LookML generation and renderers
  config.py       # Configuration schema (sp.yml)
  __main__.py     # CLI entry point

tests/            # Test suite
  fixtures/       # Test data
  test_*.py       # Test files
```

## Development

```bash
# Run tests
uv run pytest tests/

# Type checking
uv run mypy semantic_patterns/

# Linting
uv run ruff check semantic_patterns/
uv run ruff format semantic_patterns/
```

## Testing

- Framework: pytest with coverage tracking
- Markers: `unit`, `integration`
- Run: `uv run pytest tests/ -v`

## Code Style

- Ruff (line length 88; rules: E,F,I,N,W,UP)
- mypy strict type checking
- Python 3.10+
