# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
