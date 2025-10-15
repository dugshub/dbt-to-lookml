# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added
- Initial implementation of dbt to LookML converter
- Parse dbt semantic model YAML files
- Generate LookML view files (.view.lkml)
- Generate LookML explore files (explores.lkml)
- CLI interface with `generate` and `validate` commands
- Support for entities, dimensions, and measures mapping
- Dry-run mode for preview without file generation
- Validation mode to check semantic models without generation
- Comprehensive test suite with >95% coverage
- Type checking with mypy (strict mode)
- Code formatting with ruff
- Support for custom prefixes for views and explores
- Rich CLI output with progress indicators and summaries
- Error handling and detailed error messages
- Support for Python 3.13+

### Features in Development
- Additional LookML features (derived tables, refinements)
- Support for more complex dbt semantic model patterns
- Performance optimizations for large projects
- Extended validation rules