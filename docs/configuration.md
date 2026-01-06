# Configuration Reference

This document describes all configuration options for `sp.yml`.

## File Location

semantic-patterns looks for configuration files in this order:
1. Path specified with `--config` flag
2. `sp.yml` in current directory
3. `sp.yaml` in current directory
4. `.sp.yml` in current directory
5. `.sp.yaml` in current directory
6. Parent directories (searched recursively up to root)

## Complete Schema

```yaml
# Required: Input and output directories
input: ./semantic_models      # Directory containing semantic model YAML files
output: ./lookml              # Directory where LookML files will be written
schema: gold                  # Database schema for sql_table_name

# Optional: Project name (names the output folder)
project: my_analytics         # Defaults to "semantic-patterns"

# Optional: Input format (default: semantic-patterns)
format: semantic-patterns     # 'semantic-patterns' or 'dbt'

# Optional: Looker model file settings
model:
  name: semantic_model        # Model filename (without .lkml extension)
  connection: database        # Looker connection name
  label: Analytics            # Optional model label

# Optional: Explore definitions
explores:
  - fact: orders              # Name of the fact semantic model
    name: order_analysis      # Override explore name (defaults to fact name)
    label: Order Analysis     # Explore label in Looker
    description: Analyze orders  # Explore description
    join_exclusions:          # Models to exclude from auto-join
      - some_model
    joins:                    # Optional join overrides
      - model: customers
        expose: all           # 'all' or 'dimensions'
        relationship: many_to_one  # Explicit join relationship

# Optional: Generator options
options:
  dialect: redshift           # SQL dialect
  pop_strategy: dynamic       # Period-over-period strategy
  date_selector: true         # Generate date selector filter
  convert_tz: false           # Convert time dimensions to UTC
  view_prefix: ""             # Prefix for view names
  explore_prefix: ""          # Prefix for explore names

# Optional: Output options
output_options:
  clean: warn                 # Orphan file handling: 'clean', 'warn', or 'ignore'
  manifest: true              # Generate .sp-manifest.json file

# Optional: GitHub push destination
github:
  enabled: false              # Enable GitHub push
  repo: owner/repo            # GitHub repo (required if enabled)
  branch: feature/branch      # Target branch (required, cannot be main/master)
  path: ""                    # Path within repo
  protected_branches: []      # Additional protected branches
  commit_message: "semantic-patterns: Update LookML"
```

## Configuration Options

### `input` (required)

Path to the directory containing semantic model YAML files.

```yaml
input: ./semantic_models
input: /absolute/path/to/models
input: ../relative/path
```

### `output` (required)

Path where generated LookML files will be written. The directory will be created if it doesn't exist.

```yaml
output: ./lookml
output: ./looker/views
```

### `schema` (required)

Database schema name used in `sql_table_name` references.

```yaml
schema: gold
schema: analytics.gold
```

Generated LookML will use:
```lookml
sql_table_name: gold.table_name ;;
```

### `project`

Project name that determines the output folder structure. This creates a named subdirectory within the output path.

```yaml
project: my_analytics         # Creates {output}/my_analytics/
project: semantic-patterns    # Default if not specified
```

The project name is used in:
- Output folder structure: `{output}/{project}/`
- Model file references
- Manifest file generation

### `format`

Input format for semantic model files.

| Value | Description |
|-------|-------------|
| `semantic-patterns` | Native semantic-patterns YAML format (default) |
| `dbt` | dbt Semantic Layer format (semantic_models + metrics) |

```yaml
format: semantic-patterns  # Default
format: dbt                # For dbt Semantic Layer files
```

### `model`

Looker model file configuration.

```yaml
model:
  name: semantic_model    # Filename: semantic_model.model.lkml
  connection: redshift_prod
  label: Semantic Analytics  # Optional display label
```

| Property | Default | Description |
|----------|---------|-------------|
| `name` | `semantic_model` | Model file name (without .lkml) |
| `connection` | `database` | Looker connection name |
| `label` | none | Optional model label |

### `explores`

List of explore definitions. Each explore is based on a fact model and optionally joins dimension models.

```yaml
explores:
  # Simple explore using model name
  - fact: orders

  # Explore with custom name and label
  - fact: orders
    name: order_analysis
    label: Order Analysis
    description: Detailed order analytics

  # Explore with join configuration
  - fact: rentals
    joins:
      - model: facilities
        expose: dimensions  # Only expose dimensions from this join
      - model: customers
        expose: all         # Expose all fields
```

| Property | Required | Description |
|----------|----------|-------------|
| `fact` | Yes | Name of the fact semantic model |
| `name` | No | Explore name (defaults to fact model name) |
| `label` | No | Display label in Looker |
| `description` | No | Explore description |
| `join_exclusions` | No | List of model names to exclude from auto-join |
| `joins` | No | List of dimension models to join |
| `joins[].model` | Yes | Name of model to join |
| `joins[].expose` | No | Field exposure: `all` or `dimensions` |
| `joins[].relationship` | No | Explicit join relationship (overrides auto-inferred) |

#### `join_exclusions`

Exclude specific models from automatic join inference. Useful when you want to prevent certain dimension models from being joined even if they share keys with the fact model.

```yaml
explores:
  - fact: orders
    join_exclusions:
      - internal_metrics
      - staging_customers
```

#### `relationship` (in joins)

Explicitly specify the join relationship, overriding the auto-inferred relationship.

| Value | Description |
|-------|-------------|
| `one_to_one` | 1:1 relationship |
| `many_to_one` | Many-to-one relationship (default for dimension joins) |
| `one_to_many` | One-to-many relationship |

```yaml
explores:
  - fact: orders
    joins:
      - model: customers
        relationship: many_to_one
      - model: order_items
        relationship: one_to_many
```

### `options`

Generator configuration options.

#### `dialect`

SQL dialect for query generation. Affects date functions and SQL syntax.

| Value | Description |
|-------|-------------|
| `redshift` | Amazon Redshift (default) |
| `snowflake` | Snowflake |
| `bigquery` | Google BigQuery |
| `postgres` | PostgreSQL |
| `duckdb` | DuckDB |
| `trino` | Starburst/Trino |

```yaml
options:
  dialect: snowflake
```

#### `pop_strategy`

Period-over-period comparison strategy for metrics.

| Value | Description |
|-------|-------------|
| `dynamic` | Dynamic date ranges using Looker liquid (default) |
| `native` | Native Looker period-over-period (if supported) |

```yaml
options:
  pop_strategy: dynamic
```

When metrics define `pop` configurations:
```yaml
metrics:
  - name: revenue
    pop:
      comparisons: [py, pm]  # Prior Year, Prior Month
      outputs: [previous, change, pct_change]
```

The generator creates additional measures like `revenue_py`, `revenue_py_change`, etc.

#### `date_selector`

Generate a date selector filter field for dimensions marked with `date_selector: true`.

```yaml
options:
  date_selector: true  # Default
```

#### `convert_tz`

Whether to apply timezone conversion to time dimensions.

```yaml
options:
  convert_tz: false  # Default - timestamps as-is
  convert_tz: true   # Convert to Looker's configured timezone
```

#### `view_prefix`

Prefix added to all generated view names. Useful for namespacing.

```yaml
options:
  view_prefix: sm_  # Views become: sm_orders, sm_customers
```

This affects:
- View names in LookML
- View filenames
- Join references in explores

#### `explore_prefix`

Prefix added to explore names. Defaults to `view_prefix` if not specified.

```yaml
options:
  view_prefix: sm_
  explore_prefix: exp_  # Explores become: exp_orders
```

### `output_options`

Controls output file handling and manifest generation.

```yaml
output_options:
  clean: warn       # How to handle orphan files
  manifest: true    # Generate manifest file
```

#### `clean`

Controls how orphan files (files from previous runs that are no longer generated) are handled.

| Value | Description |
|-------|-------------|
| `clean` | Automatically delete orphan files |
| `warn` | Warn about orphan files but don't delete (default) |
| `ignore` | Ignore orphan files entirely |

```yaml
output_options:
  clean: clean   # Delete orphan files
  clean: warn    # Warn about orphans (default)
  clean: ignore  # Ignore orphans
```

#### `manifest`

Whether to generate a `.sp-manifest.json` file in the output directory. The manifest tracks all generated files and enables orphan detection.

```yaml
output_options:
  manifest: true   # Generate manifest (default)
  manifest: false  # Skip manifest generation
```

The manifest file contains:
- List of all generated files
- Generation timestamp
- Configuration metadata

## Output Structure

semantic-patterns generates LookML files in a domain-based folder structure:

```
{output}/{project}/
├── {project}.model.lkml
├── views/
│   └── {model}/
│       ├── {model}.view.lkml
│       └── {model}.metrics.view.lkml
├── explores/
│   └── {explore}.explore.lkml
└── .sp-manifest.json
```

### Directory Layout

| Directory | Contents |
|-----------|----------|
| `views/{model}/` | View files organized by semantic model name |
| `explores/` | Explore definition files |
| Project root | Main model file |

### Generated Files

| File Pattern | Description |
|--------------|-------------|
| `{model}.view.lkml` | Main view with dimensions and measures |
| `{model}.metrics.view.lkml` | Extended view with metric definitions (if model has metrics) |
| `{explore}.explore.lkml` | Explore definition with joins |
| `{project}.model.lkml` | Main Looker model file with connection and includes |
| `.sp-manifest.json` | Manifest tracking generated files (if enabled) |

### Example

With this configuration:
```yaml
output: ./lookml
project: analytics
```

And semantic models `orders` and `customers`, the output structure would be:
```
lookml/
└── analytics/
    ├── analytics.model.lkml
    ├── views/
    │   ├── orders/
    │   │   ├── orders.view.lkml
    │   │   └── orders.metrics.view.lkml
    │   └── customers/
    │       └── customers.view.lkml
    ├── explores/
    │   └── order_analysis.explore.lkml
    └── .sp-manifest.json
```

## GitHub Integration

Push generated LookML directly to a GitHub repository. This is useful for CI/CD workflows and keeping Looker in sync with your semantic models.

### Configuration

```yaml
github:
  enabled: true
  repo: myorg/looker-models           # owner/repo format (required)
  branch: semantic-patterns/dev       # Target branch (required, cannot be main/master)
  path: lookml/                       # Path within repo (optional)
  protected_branches:                 # Additional branches to protect (optional)
    - production
    - release
  commit_message: "semantic-patterns: Update LookML"
```

| Property | Required | Default | Description |
|----------|----------|---------|-------------|
| `enabled` | No | `false` | Enable GitHub push |
| `repo` | Yes* | - | Repository in `owner/repo` format |
| `branch` | Yes* | - | Target branch (cannot be `main` or `master`) |
| `path` | No | `""` | Path within repo for files |
| `protected_branches` | No | `[]` | Additional branches to block |
| `commit_message` | No | `"semantic-patterns: Update LookML"` | Commit message |

*Required when `enabled: true`

### Authentication

GitHub authentication uses a Personal Access Token (PAT) with `repo` scope. The token is resolved in this order:

1. `GITHUB_TOKEN` environment variable (for CI/automation)
2. System keychain (macOS Keychain, Windows Credential Locker, Linux Secret Service)
3. Interactive prompt (one-time setup, saves to keychain)

To create a token:
1. Go to https://github.com/settings/tokens/new
2. Select `repo` scope
3. Generate and copy the token

### Usage

```bash
# Build and prompt before pushing (when github.enabled=true)
sp build

# Build and push without confirmation
sp build --push

# Preview what would be pushed
sp build --dry-run
```

### Protected Branches

The following branches are always protected and cannot be pushed to:
- `main`
- `master`

You can add additional protected branches in your config:

```yaml
github:
  enabled: true
  repo: myorg/looker-models
  branch: feature/semantic-patterns
  protected_branches:
    - production
    - staging
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `D2L_DIALECT` | Default SQL dialect (overridden by `options.dialect`) |
| `GITHUB_TOKEN` | GitHub Personal Access Token for push |

```bash
export D2L_DIALECT=snowflake
export GITHUB_TOKEN=ghp_xxxx
```

## Example Configurations

### Minimal Configuration

```yaml
input: ./semantic_models
output: ./lookml
schema: gold
```

### Full Configuration

```yaml
input: ./semantic_models
output: ./lookml
schema: analytics.gold
project: analytics
format: semantic-patterns

model:
  name: analytics
  connection: redshift_prod
  label: Semantic Analytics

explores:
  - fact: orders
    label: Order Analysis
    join_exclusions:
      - internal_metrics
  - fact: customers
    label: Customer Analysis
  - fact: products
    joins:
      - model: categories
        expose: dimensions
        relationship: many_to_one

options:
  dialect: redshift
  pop_strategy: dynamic
  date_selector: true
  convert_tz: false
  view_prefix: sem_
  explore_prefix: sem_

output_options:
  clean: warn
  manifest: true
```

### dbt Semantic Layer Configuration

```yaml
input: ./models/semantic
output: ./lookml
schema: gold
format: dbt

model:
  name: dbt_metrics
  connection: snowflake_prod

explores:
  - fact: orders

options:
  dialect: snowflake
```

## Validation

Validate your configuration without generating files:

```bash
sp validate
sp validate --config ./path/to/sp.yml
```

This checks:
- Configuration file syntax
- Input directory exists
- Semantic models parse correctly
- Explore fact models exist
