# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**semantic-patterns** transforms semantic models (YAML) into BI tool patterns, starting with LookML views and explores. Features a clean domain-driven architecture with strict typing (mypy) and comprehensive testing (pytest).

## Core Architecture

### Package Structure

```
semantic_patterns/
├── domain/              # Core domain models (Dimension, Measure, Metric, Model)
├── ingestion/           # YAML loading and model building
│   ├── builder.py       # DomainBuilder for native format
│   └── dbt/             # dbt Semantic Layer ingestion
│       ├── loader.py    # Load dbt YAML files
│       └── mapper.py    # Transform dbt → semantic-patterns format
├── adapters/            # Output adapters (LookML, future: Cube.js, etc.)
│   └── lookml/          # LookML generation
│       ├── renderers/   # Component renderers (view, dimension, measure, etc.)
│       ├── generator.py # Main LookML generator
│       ├── explore_generator.py  # Explore with entity-based joins
│       └── paths.py     # Domain-based output structure
├── destinations/        # Output destinations (GitHub, etc.)
│   ├── base.py          # Destination protocol
│   └── github.py        # GitHub API integration
├── config.py            # Configuration classes (sp.yml schema)
├── credentials.py       # Secure credential storage (keychain)
├── manifest.py          # Output manifest tracking (.sp-manifest.json)
└── __main__.py          # CLI entry point (Click + rich)
```

### Data Flow

```
# Native format
YAML → DomainBuilder → ProcessedModel → LookMLGenerator → .lkml files

# dbt format
YAML → DbtLoader → DbtMapper → DomainBuilder → ProcessedModel → .lkml files
```

### Output Structure

Generated LookML uses domain-based folder organization:

```
{output}/{project}/
├── {project}.model.lkml                     # Rollup model file (at project root)
├── views/{model}/{model}.view.lkml          # Base views
├── views/{model}/{model}.metrics.view.lkml  # Metric refinements
├── explores/{explore}.explore.lkml          # Explores
└── .sp-manifest.json                        # Tracks generated files
```

## Essential Commands

```bash
# Testing
uv run pytest tests/                    # Run all tests
uv run pytest tests/ -v                 # Verbose output
uv run pytest tests/test_domain.py      # Run specific test file

# Code Quality
uv run ruff check semantic_patterns/    # Linting
uv run ruff format semantic_patterns/   # Auto-format
uv run mypy semantic_patterns/          # Type checking

# CLI
sp build                                # Build from sp.yml in current dir
sp build --config ./configs/sp.yml      # Use specific config
sp build --dry-run                      # Preview without writing
sp build --push                         # Build and push to GitHub (skip confirmation)
sp validate                             # Validate config and models
```

## Code Style

- **Type hints**: All functions (mypy --strict)
- **Line length**: 88 characters
- **Imports**: Sorted with ruff
- **Naming**: snake_case functions, PascalCase classes
- **CLI output**: Use `rich.console.Console` (never print())

## Key Concepts

### Domain Layer (`domain/`)

- `Dimension` - Categorical/time fields with type, label, visibility
- `Measure` - Aggregations (sum, count, avg, etc.)
- `Metric` - Business metrics with optional PoP variants
- `Entity` - Primary/foreign keys for join inference
- `ProcessedModel` - Complete model ready for generation

### Ingestion Layer (`ingestion/`)

- `DomainBuilder` - Builds domain models from native YAML format
- `DbtLoader` - Loads dbt semantic_models and metrics from YAML
- `DbtMapper` - Transforms dbt format to semantic-patterns format

### Adapters (`adapters/`)

- Dialect-agnostic SQL transformations (Redshift, Snowflake, BigQuery, etc.)
- LookML renderers for each component type
- Explore generation with entity-based join inference
- OutputPaths for domain-based folder structure

### Configuration (`config.py`)

Key config options in sp.yml:
- `project` - Names output folder (default: "semantic-patterns")
- `format` - Input format: "semantic-patterns" or "dbt"
- `explores` - List of explores with join_exclusions and relationship overrides
- `output_options` - manifest (bool), clean ("clean"|"warn"|"ignore")
- `github` - GitHub push destination (enabled, repo, branch, path, protected_branches)

### Destinations (`destinations/`)

- `GitHubDestination` - Push generated LookML to GitHub via API
- Uses `credentials.py` for secure token storage (env → keychain → prompt)
- Protected branches (main/master) cannot be pushed to

## Environment

- **Python**: 3.10+ (tested 3.10-3.13)
- **Package manager**: `uv` preferred
- **Install**: `uv pip install -e ".[dev]"`
