# Quickstart Guide

This guide walks you through installing semantic-patterns and generating your first LookML files.

## Installation

### Using uv (recommended)

```bash
uv pip install semantic-patterns
```

### Using pip

```bash
pip install semantic-patterns
```

### From source

```bash
git clone https://github.com/dugshub/semantic-patterns.git
cd semantic-patterns
pip install -e .
```

## Create Your First Config

Initialize a configuration file in your project directory:

```bash
sp init
```

This creates `sp.yml` with default settings:

```yaml
# semantic-patterns configuration

input: ./semantic_models
output: ./lookml
schema: gold
project: my_project

# Looker model file settings
model:
  name: semantic_model
  connection: database

# Generator options
options:
  dialect: redshift
  pop_strategy: dynamic
  date_selector: true
  convert_tz: false
```

Edit the config to match your environment:
- `input`: Directory containing your semantic model YAML files
- `output`: Where to write generated LookML
- `schema`: Database schema name for table references
- `project`: Names the output folder (e.g., `lookml/my_project/`)
- `model.connection`: Your Looker connection name

## Create a Semantic Model

Create a file `semantic_models/orders.yml`:

```yaml
semantic_models:
  - name: orders
    description: Order transactions

    entities:
      - name: order
        type: primary
        expr: order_id
      - name: customer
        type: foreign
        expr: customer_id

    dimensions:
      - name: created_at
        label: Order Created
        type: time
        granularity: day
        expr: created_at
        group: Dates

      - name: status
        label: Order Status
        type: categorical
        expr: order_status
        group: Order Details

      - name: channel
        label: Sales Channel
        type: categorical
        expr: sales_channel
        group: Order Details

    measures:
      - name: order_count
        label: Order Count
        agg: count_distinct
        expr: order_id
        hidden: true

      - name: total_revenue
        label: Total Revenue
        agg: sum
        expr: order_total
        hidden: true

metrics:
  - name: orders
    label: Orders
    description: Count of orders
    type: simple
    measure: order_count
    format: decimal_0
    entity: order

  - name: revenue
    label: Revenue
    description: Total order revenue
    type: simple
    measure: total_revenue
    format: usd
    entity: order
    pop:
      comparisons: [py, pm]
      outputs: [previous, change, pct_change]
```

## Generate LookML

Run the build command:

```bash
sp build
```

You should see output like:

```
Config: sp.yml
Input: ./semantic_models
Format: semantic-patterns
  Found 1 models
Output: ./lookml/my_project
  Generated 2 view files
  Generated 1 explore file
  Generated model file: semantic_model.model.lkml

Generated 4 files
```

## Review Generated Output

The generated LookML files are organized by domain in your output directory:

```
lookml/my_project/
├── my_project.model.lkml
├── views/
│   └── orders/
│       ├── orders.view.lkml
│       └── orders.metrics.view.lkml
├── explores/
│   └── orders.explore.lkml
└── .sp-manifest.json
```

- **{project}.model.lkml**: Main model file at project root
- **views/{model}/**: Each semantic model gets its own folder containing the base view and metrics view
- **explores/**: Contains explore files
- **.sp-manifest.json**: Tracks all generated files (useful for cleanup and CI/CD)

### `views/orders/orders.view.lkml`

Contains the base view with dimensions and measures:

```lookml
view: orders {
  sql_table_name: gold.orders ;;

  dimension: order_id {
    type: string
    primary_key: yes
    sql: ${TABLE}.order_id ;;
  }

  dimension_group: created_at {
    type: time
    label: "Order Created"
    timeframes: [raw, date, week, month, quarter, year]
    sql: ${TABLE}.created_at ;;
    group_label: "Dates"
  }

  dimension: status {
    type: string
    label: "Order Status"
    sql: ${TABLE}.order_status ;;
    group_label: "Order Details"
  }

  # ... more dimensions and measures
}
```

### `views/orders/orders.metrics.view.lkml`

Contains metric refinements with business logic:

```lookml
view: +orders {
  measure: orders {
    type: count_distinct
    label: "Orders"
    description: "Count of orders"
    sql: ${order_id} ;;
  }

  measure: revenue {
    type: sum
    label: "Revenue"
    description: "Total order revenue"
    sql: ${TABLE}.order_total ;;
    value_format_name: usd
  }

  # Period-over-period measures
  measure: revenue_py {
    type: sum
    label: "Revenue (PY)"
    # ... dynamic PoP logic
  }
}
```

### `my_project.model.lkml`

The model file at project root ties everything together:

```lookml
connection: "database"

include: "/views/**/*.view.lkml"
include: "/explores/**/*.explore.lkml"
```

## Add an Explore

Update `sp.yml` to add an explore configuration:

```yaml
input: ./semantic_models
output: ./lookml
schema: gold
project: my_project

model:
  name: semantic_model
  connection: database

explores:
  - fact: orders
    label: Order Analysis

options:
  dialect: redshift
```

Run `sp build` again. The explore will be generated at `explores/orders.explore.lkml`.

## Push to GitHub (Optional)

You can push generated LookML directly to a GitHub repository. Add a `github` section to your config:

```yaml
github:
  enabled: true
  repo: myorg/looker-models
  branch: semantic-patterns/dev    # Cannot be main or master
  path: lookml/                     # Path within repo (optional)
```

Then run:

```bash
# Build and prompt before pushing
sp build

# Build and push without confirmation
sp build --push
```

On first run, you'll be prompted to enter a GitHub Personal Access Token (with `repo` scope). The token is saved to your system keychain for future use.

## Next Steps

- Read the [Configuration Reference](configuration.md) for all sp.yml options
- Explore the `examples/` directory for more complex semantic models
- Try the `--dry-run` flag to preview changes before writing files
- Use `sp validate` to check your config and semantic models
- Set up [GitHub integration](configuration.md#github) for automated deployments
