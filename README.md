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
- **Extensible** - Clean adapter architecture for adding new output formats

## Features

- **Domain-based output** - Views organized by domain with clean folder structure
- **dbt Semantic Layer support** - Ingest dbt semantic models and metrics directly
- **Period-over-period** - Dynamic PoP comparisons (prior year, prior month, etc.)
- **Entity-based joins** - Auto-infer explore joins from entity relationships
- **Manifest tracking** - `.sp-manifest.json` tracks generated files for change detection
- **Multi-dialect** - Redshift, Snowflake, BigQuery, Postgres, DuckDB, Trino
- **GitHub integration** - Push generated LookML directly to GitHub with secure keychain auth

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

# Build and push to GitHub (when github.enabled=true)
sp build --push

# Validate config and models without building
sp validate
```

## Output Structure

Generated LookML is organized by domain for clean separation:

```
{output}/{project}/
├── my_project.model.lkml
├── views/
│   ├── orders/
│   │   ├── orders.view.lkml
│   │   └── orders.metrics.view.lkml
│   └── customers/
│       ├── customers.view.lkml
│       └── customers.metrics.view.lkml
├── explores/
│   └── orders.explore.lkml
└── .sp-manifest.json
```

The manifest file tracks generated files with content hashes, enabling future incremental builds and orphan cleanup.

## Documentation

- [Quickstart Guide](docs/quickstart.md) - Get started in 5 minutes
- [Configuration Reference](docs/configuration.md) - All sp.yml options
- [YAML Schema](docs/schema.md) - Native semantic model format
- [dbt Format Guide](docs/dbt-format.md) - Using dbt Semantic Layer format

## Package Structure

```
semantic_patterns/
  domain/         # Core domain models (Dimension, Measure, Metric, Model)
  ingestion/      # YAML loading, dbt mapper
  adapters/       # Output adapters (LookML)
    lookml/       # LookML generation and renderers
  destinations/   # Output destinations (GitHub)
  config.py       # Configuration schema (sp.yml)
  credentials.py  # Secure credential storage (keychain)
  manifest.py     # Output manifest tracking
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
