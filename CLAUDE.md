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
├── app/                 # Web UI (sp serve)
│   ├── server/          # FastAPI backend
│   └── client/          # React frontend
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
sp serve                                # Launch web UI (API + frontend)
sp serve --api-only                     # API only mode
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

## Web UI (`sp serve`)

A visual interface for exploring and configuring semantic models.

### Architecture

```
semantic_patterns/app/
├── server/                    # FastAPI backend
│   ├── main.py               # App factory, CORS, routes
│   ├── state.py              # In-memory state (config + models)
│   └── routes/
│       ├── config.py         # GET/PUT /api/config
│       ├── models.py         # GET /api/models, /api/stats
│       └── build.py          # POST /api/validate, /api/reload
└── client/                   # React frontend
    ├── src/
    │   ├── api/              # Axios client + TanStack Query hooks
    │   ├── types/            # TypeScript types (mirrors Python domain)
    │   ├── components/
    │   │   ├── layout/       # Shell with sidebar navigation
    │   │   └── common/       # GroupedList, badges, etc.
    │   └── pages/            # Dashboard, Models, Metrics, Config
    └── dist/                 # Built frontend assets
```

### Running the UI

```bash
sp serve                      # Starts API (8000) + Frontend (3000)
sp serve --api-only           # API only, opens /docs
sp serve --no-open            # Don't auto-open browser
sp serve --port 9000          # Custom API port
```

### Key Features

- **Dashboard** - Project stats overview
- **Models** - List all semantic models with counts
- **Model Detail** - Tabbed view of dimensions/measures/metrics/entities
  - Dimensions/Measures grouped by 2-tier hierarchy (subject.category)
  - Metrics displayed as cards with variant breakdown
- **Cross-model views** - Dimensions, Measures, Metrics across all models
- **Config** - View and edit sp.yml

### Display Conventions

- **Labels first**: Human-readable `label` shown prominently, technical `name` as secondary
- **2-tier grouping**: Uses `group` field with dot notation (e.g., "Date Dimensions.Timestamps")
- **Metric variants**: Shows friendly names ("Prior Year", "Prior Month % Change") with technical suffix below
- **Badges**: Type indicators (time/categorical, aggregation type, format, PoP enabled)

### Frontend Development

```bash
cd semantic_patterns/app/client
npm install                   # Install dependencies
npm run dev                   # Start Vite dev server
npm run build                 # Build for production
```

Tech stack: React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router
