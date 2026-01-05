# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**semantic-patterns** transforms semantic models (YAML) into BI tool patterns, starting with LookML views and explores. Features a clean domain-driven architecture with strict typing (mypy) and comprehensive testing (pytest).

## Core Architecture

### Package Structure

```
src/semantic_patterns/
├── domain/              # Core domain models (Dimension, Measure, Metric, Model)
├── ingestion/           # YAML loading and model building
├── adapters/            # Output adapters (LookML, future: Cube.js, etc.)
│   └── lookml/          # LookML generation
│       ├── renderers/   # Component renderers (view, dimension, measure, etc.)
│       └── generator.py # Main LookML generator
├── config.py            # Configuration classes
└── __main__.py          # CLI entry point (Click + rich)
```

### Data Flow

```
YAML → Loader → Builder → ProcessedModel →
LookMLGenerator → Dict[filename, content] → .lkml files
```

## Essential Commands

```bash
# Testing
uv run pytest tests/v2/                    # Run all tests
uv run pytest tests/v2/ -v                 # Verbose output
uv run pytest tests/v2/test_domain.py      # Run specific test file

# Code Quality
uv run ruff check src/                     # Linting
uv run ruff format src/                    # Auto-format
uv run mypy src/semantic_patterns/         # Type checking

# CLI
sp generate -i semantic_models/ -o output/
semantic-patterns generate -i semantic_models/ -o output/
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
- `ProcessedModel` - Complete model ready for generation

### Adapters (`adapters/`)

- Dialect-agnostic SQL transformations
- LookML renderers for each component type
- Explore generation with join inference

## Environment

- **Python**: 3.10+ (tested 3.10-3.13)
- **Package manager**: `uv` preferred
- **Install**: `uv pip install -e ".[dev]"`
