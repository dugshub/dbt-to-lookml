# dbt-to-lookml Usage Guide

## Overview

`dbt-to-lookml` converts dbt semantic model YAML files into LookML views and explores. It provides validation, formatting, and a user-friendly CLI interface.

## Basic Commands

### Generate LookML Files

Convert semantic models to LookML:
```bash
dbt-to-lookml generate -i <input_dir> -o <output_dir>
```

Example:
```bash
dbt-to-lookml generate -i semantic_models/ -o lookml_output/
```

### Validate Semantic Models

Check semantic models without generating files:
```bash
dbt-to-lookml validate -i <input_dir>
```

Example:
```bash
dbt-to-lookml validate -i semantic_models/ --verbose
```

## Command Options

### Generate Command

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--input-dir` | `-i` | Directory containing semantic model YAML files | Required |
| `--output-dir` | `-o` | Directory to output LookML files | Required |
| `--view-prefix` | | Prefix to add to view names | "" |
| `--explore-prefix` | | Prefix to add to explore names | "" |
| `--dry-run` | | Preview what would be generated without writing files | False |
| `--no-validation` | | Skip LookML syntax validation | False |
| `--no-formatting` | | Skip LookML output formatting | False |
| `--show-summary` | | Show detailed generation summary | False |

### Validate Command

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--input-dir` | `-i` | Directory containing semantic model YAML files | Required |
| `--strict` | | Enable strict validation mode | False |
| `--verbose` | `-v` | Show detailed validation results | False |

## Examples

### Basic Generation
```bash
# Generate LookML files from semantic models
dbt-to-lookml generate -i semantic_models/ -o build/lookml/
```

### Dry Run Preview
```bash
# Preview what would be generated without creating files
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ --dry-run --show-summary
```

### With Prefixes
```bash
# Add prefixes to generated view and explore names
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ \
    --view-prefix "v_" \
    --explore-prefix "exp_"
```

### Skip Validation
```bash
# Generate without validating LookML syntax (faster but less safe)
dbt-to-lookml generate -i semantic_models/ -o build/lookml/ --no-validation
```

### Strict Validation
```bash
# Validate with strict mode (fails on first error)
dbt-to-lookml validate -i semantic_models/ --strict --verbose
```

## Input File Format

The tool expects dbt semantic model YAML files with the following structure:

```yaml
semantic_models:
  - name: model_name
    model: ref('table_name')
    description: "Model description"

    entities:
      - name: entity_id
        type: primary
        description: "Primary key"

    dimensions:
      - name: dimension_name
        type: categorical
        description: "Dimension description"

    measures:
      - name: measure_name
        agg: sum
        description: "Measure description"
```

## Output Structure

The tool generates:
1. Individual view files: `<model_name>.view.lkml`
2. A single explores file: `explores.lkml`

### View File Example
```lookml
view: users {
  sql_table_name: dim_users ;;

  dimension: user_id {
    primary_key: yes
    type: string
    sql: ${TABLE}.user_id ;;
  }

  measure: user_count {
    type: count
    sql: 1 ;;
  }
}
```

### Explores File Example
```lookml
explore: users {
  type: table
  from: users
  description: "User dimension"
}
```

## Advanced Usage

### Batch Processing
Process multiple directories:
```bash
for dir in project1 project2 project3; do
  dbt-to-lookml generate -i $dir/semantic_models -o $dir/lookml
done
```

### Integration with CI/CD
```yaml
# GitHub Actions example
- name: Generate LookML
  run: |
    dbt-to-lookml generate \
      -i semantic_models/ \
      -o lookml/ \
      --show-summary
```

### Validation in Pre-commit
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-semantic-models
        name: Validate Semantic Models
        entry: dbt-to-lookml validate -i semantic_models/ --strict
        language: system
        files: semantic_models/.*\.yml$
```

## Error Handling

The tool provides clear error messages:

- **Parse Errors**: Shows which file and line caused the error
- **Validation Errors**: Lists all validation issues found
- **File System Errors**: Reports permission or path issues

Example error output:
```
✗ sem_invalid.yml: Invalid semantic model structure at line 10
  Skipping file due to parse error...
```

## Tips and Best Practices

1. **Always use dry-run first** to preview changes before generating files
2. **Enable validation** (default) to catch LookML syntax errors early
3. **Use prefixes** to avoid naming conflicts in large projects
4. **Run validation** as part of your CI/CD pipeline
5. **Keep semantic models organized** in dedicated directories

## Getting Help

```bash
# View general help
dbt-to-lookml --help

# View command-specific help
dbt-to-lookml generate --help
dbt-to-lookml validate --help

# Check version
dbt-to-lookml --version
```