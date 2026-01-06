# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **GitHub destination** - Push generated LookML directly to GitHub repositories via API; supports branch targeting, protected branch validation, and atomic commits
- **Secure credential storage** - `credentials.py` module with system keychain integration (macOS Keychain, Windows Credential Locker, Linux Secret Service); falls back to env vars for CI
- **CLI --push flag** - `sp build --push` skips confirmation prompt for GitHub push; interactive confirmation when `github.enabled=true`
- **Domain-based output structure** - Views organized in domain folders (`views/{model}/{model}.view.lkml`), explores in dedicated folder (`explores/{explore}.explore.lkml`), rollup model file at project root (`{project}.model.lkml`)
- **Manifest system** - `.sp-manifest.json` tracks all generated files with hashes, enabling future orphan cleanup and incremental builds; includes model summaries with dimension/measure/metric counts
- **Project name configuration** - `project` config option names output folder (defaults to "semantic-patterns")
- **Output options** - `output_options.clean` ("clean" | "warn" | "ignore") and `output_options.manifest` (true | false)
- **Join exclusions** - `join_exclusions` config to exclude specific models from auto-join
- **Relationship override** - Explicit `relationship` config for join relationships (one_to_one, many_to_one, one_to_many)
- **GitHubConfig** - Configuration for GitHub push: `enabled`, `repo`, `branch`, `path`, `protected_branches`, `commit_message`

### Changed

- **Output structure** - Explores now in `explores/` folder (was `models/`); model file moved to project root (was `models/`)
- **Join system** - Switched to exclude-based auto-join where all entity-linked models are joined by default

## [0.3.0] - 2025-01-05

Major refactor: renamed from `dbt-to-lookml` to `semantic-patterns` with a cleaner architecture.

### Added

- **dbt Semantic Layer ingestion** - Load and transform dbt semantic models and metrics into semantic-patterns format
- **SpotHero examples** - Complete semantic model examples (rentals, reviews, facilities) demonstrating real-world usage
- **Config-driven CLI** - New `sp build` command reads from `sp.yml` configuration file
- **Dynamic PoP strategy** - Period-over-period comparisons with dynamic date range support
- **Model file generation** - Generates `.model.lkml` files with connection and includes
- **View and explore prefixes** - Configurable prefixes for namespacing generated LookML
- **Explore generation** - Auto-generate explores from semantic model entities
- **Multiple dialect support** - Redshift, Snowflake, BigQuery, Postgres, DuckDB, Starburst (Trino)

### Changed

- **Renamed package** - `dbt-to-lookml` is now `semantic-patterns`
- **New package structure** - Moved from `src/semantic_patterns/` to `semantic_patterns/` at root level
- **Clean domain architecture** - Separated domain models, ingestion, and adapters
- **CLI redesign** - Replaced `sp generate -i ... -o ...` with config-driven `sp build`

### Fixed

- **view_prefix application** - Fixed bug where prefix was only applied to filenames, not LookML view names
- **Metric entity filtering** - Metrics now correctly filter by primary entity only
- **LookML SQL fields** - Removed duplicate semicolons in SQL field output
- **Time dimension convert_tz** - Properly set `convert_tz: no` on all time dimensions

## [0.2.0] - 2024-11-18

### Added

- Initial LookML adapter with split file generation (views, metrics, explores)
- Domain types for dimensions, measures, metrics, and models
- YAML loader and domain builder for semantic model ingestion
- Dialect-aware SQL rendering with sqlglot integration
- Comprehensive test suite with pytest

### Changed

- Established clean domain-driven architecture

## [0.1.0] - 2024-11-06

### Added

- Initial project setup
- Basic LookML view generation from semantic models
- CLI entry point (`sp` command)
