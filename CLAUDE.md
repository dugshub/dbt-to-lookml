# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**dbt-to-lookml** converts dbt semantic models (YAML) into LookML views and explores. Features strict typing (mypy), comprehensive testing (pytest 95%+ coverage), and a rich CLI.

## Core Architecture

### Package Structure

```
src/dbt_to_lookml/
├── interfaces/          # Abstract base classes (Parser, Generator)
├── parsers/             # DbtParser - parses semantic model YAML
├── generators/          # LookMLGenerator - generates .view.lkml and explores.lkml
├── schemas/             # Pydantic models (semantic_layer.py, config.py, lookml.py)
├── wizard/              # Interactive command builder
├── types.py             # Enums and type mappings
└── __main__.py          # CLI entry point (Click + rich)
```

### Data Flow

```
YAML → DbtParser.parse_directory() → List[SemanticModel] →
LookMLGenerator.generate() → Dict[filename, content] →
Generator.write_files() → .lkml files
```

## Essential Commands

```bash
# Testing
make test              # Unit + integration tests
make test-fast         # Unit tests only
make test-full         # All test suites
make test-coverage     # Generate coverage report (95% target)

# Code Quality
make lint              # Ruff linting
make format            # Auto-format
make type-check        # Mypy strict
make quality-gate      # All checks (pre-commit)

# LookML Generation
make lookml-preview    # Dry-run summary
make lookml-generate INPUT_DIR=semantic_models OUTPUT_DIR=build/lookml

# CLI
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ -s public
dbt-to-lookml generate --preview     # Preview only
dbt-to-lookml generate --yes         # Auto-confirm
dbt-to-lookml wizard generate        # Interactive mode
```

### Fact Model Selection

```bash
# Required to generate explores (otherwise views only)
dbt-to-lookml generate -i semantic_models/ -o build/ -s public --fact-models rentals,orders
```

### Date Selector (Dynamic Calendar)

```bash
# Enable date selector for fact models (allows switching analysis date field)
dbt-to-lookml generate ... --fact-models rentals --date-selector

# Use explicit mode (only include dims with meta.date_selector: true)
dbt-to-lookml generate ... --date-selector --date-selector-mode explicit
```

Generated LookML includes a `calendar_date` parameter and `calendar` dimension_group that lets users dynamically choose which date field to analyze by.

## Code Style

- **Type hints**: All functions (mypy --strict)
- **Line length**: 88 characters
- **Imports**: Sorted with ruff
- **Naming**: snake_case functions, PascalCase classes
- **CLI output**: Use `rich.console.Console` (never print())

## Common Pitfalls

1. **Interface-based design**: Use `Parser.parse_directory()` and `Generator.write_files()`
2. **Pydantic compatibility**: Use `Optional` for new schema fields
3. **Test isolation**: Unit tests never write to disk
4. **Wizard mocking**: Mock at module level (`dbt_to_lookml.wizard.generate_wizard.questionary`)

## Key Conversion Rules

| dbt Concept | LookML Output |
|-------------|---------------|
| Entities | `dimension` with `hidden: yes` (primary gets `primary_key: yes`) |
| Dimensions | `dimension` or `dimension_group` (time) |
| Measures | Only written if used by complex metrics without simple metric exposure |
| Simple Metrics | `measure` with direct aggregation (`type: sum`, etc.) |
| Complex Metrics | `measure` with `type: number` referencing other measures |
| Metric PoP | `period_over_period` measures referencing metric directly (no hidden base) |

**Smart Optimization**: Simple metrics generate as direct aggregates. Hidden `_measure` versions only created when needed by complex metrics. Unused measures excluded entirely.

### Period-over-Period (PoP) on Metrics

Define PoP directly on simple metrics (cleaner than measure-level PoP):

```yaml
metrics:
  - name: total_revenue
    type: simple
    type_params:
      measure: revenue
    meta:
      primary_entity: order
      pop:
        enabled: true
        comparisons: [pp, py]  # prior period, prior year
        windows: [month]       # month, quarter, week
        format: usd            # optional value format
```

**Limitation**: Only simple metrics are supported (they generate direct aggregates). Ratio/derived metrics silently skip PoP due to Looker `type: number` limitations.

See `.claude/ai-docs/conversion-rules.md` for full details.

## Detailed Documentation

Extended documentation is available in `.claude/ai-docs/`:

| File | Content |
|------|---------|
| `lookml-features.md` | Timezone conversion, field visibility, time dimension labels, timezone variants, join cardinality |
| `wizard-system.md` | Interactive wizard architecture, detection, prompts, testing |
| `conversion-rules.md` | Semantic model → LookML translation rules |
| `testing-guide.md` | Test organization, markers, coverage requirements |

## Environment

- **Python**: 3.9+ (tested 3.9-3.13)
- **Package manager**: `uv` preferred
- **Install**: `pip install -e ".[dev]"`

## CI/CD

- Workflow: `.github/workflows/test.yml`
- Quality gate must pass: lint + types + tests
