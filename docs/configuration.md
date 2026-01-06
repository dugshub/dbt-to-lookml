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
    joins:                    # Optional join overrides
      - model: customers
        expose: all           # 'all' or 'dimensions'

# Optional: Generator options
options:
  dialect: redshift           # SQL dialect
  pop_strategy: dynamic       # Period-over-period strategy
  date_selector: true         # Generate date selector filter
  convert_tz: false           # Convert time dimensions to UTC
  view_prefix: ""             # Prefix for view names
  explore_prefix: ""          # Prefix for explore names
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
| `joins` | No | List of dimension models to join |
| `joins[].model` | Yes | Name of model to join |
| `joins[].expose` | No | Field exposure: `all` or `dimensions` |

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

## Environment Variables

The default SQL dialect can be set via environment variable:

```bash
export D2L_DIALECT=snowflake
```

This is overridden by the `options.dialect` setting in sp.yml.

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
format: semantic-patterns

model:
  name: analytics
  connection: redshift_prod
  label: Semantic Analytics

explores:
  - fact: orders
    label: Order Analysis
  - fact: customers
    label: Customer Analysis
  - fact: products
    joins:
      - model: categories
        expose: dimensions

options:
  dialect: redshift
  pop_strategy: dynamic
  date_selector: true
  convert_tz: false
  view_prefix: sem_
  explore_prefix: sem_
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
