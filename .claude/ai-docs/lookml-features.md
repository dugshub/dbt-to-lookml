# LookML Feature Documentation

This document covers advanced LookML generation features including timezone handling, field visibility, dimension organization, and join configuration.

## Timezone Conversion Configuration

LookML dimension_groups support timezone conversion through the `convert_tz` parameter, which controls whether timestamp values are converted from database timezone to the user's viewing timezone.

### Default Behavior

- **Default**: `convert_tz: no` (timezone conversion explicitly disabled)
- Prevents unexpected timezone shifts and provides predictable behavior
- Users must explicitly enable timezone conversion if needed

### Configuration Precedence (Highest to Lowest)

1. **Dimension Metadata Override** (Highest priority)
   ```yaml
   dimensions:
     - name: created_at
       type: time
       config:
         meta:
           convert_tz: yes  # Enable for this dimension only
   ```

2. **Generator Parameter**
   ```python
   generator = LookMLGenerator(convert_tz=True)
   ```

3. **CLI Flag**
   ```bash
   dbt-to-lookml generate --convert-tz      # Enable
   dbt-to-lookml generate --no-convert-tz   # Disable explicitly
   ```

4. **Default**: `convert_tz: no`

### Implementation

- `Dimension._to_dimension_group_dict()`: Checks `config.meta.convert_tz` first, then `default_convert_tz` parameter
- `LookMLGenerator.__init__()`: Accepts `convert_tz: bool | None` parameter
- CLI uses mutually exclusive `--convert-tz` / `--no-convert-tz` flags

---

## Field Visibility Control

### Hidden Parameter

Hide fields from LookML output:

```yaml
dimensions:
  - name: internal_id
    type: categorical
    config:
      meta:
        hidden: true  # Generates hidden: yes in LookML
```

**Behavior**:
- Applied to dimensions (categorical and time) and measures
- Generates `hidden: yes` in LookML output
- Respected in both views and explores

### BI Field Filtering

Selectively expose fields using `bi_field` parameter:

```yaml
dimensions:
  - name: customer_id
    config:
      meta:
        bi_field: true   # Include in --bi-field-only explores
  - name: internal_notes
    config:
      meta:
        bi_field: false  # Exclude from --bi-field-only explores
```

**CLI Usage**:
```bash
dbt-to-lookml generate -s public                  # All fields (default)
dbt-to-lookml generate -s public --bi-field-only  # Only bi_field: true
```

**Implementation**:
- `LookMLGenerator._filter_fields_by_bi_field()` filters explore join fields
- Primary keys (entities) always included for join relationships
- Only applied when `use_bi_field_filter=True`

---

## Time Dimension Group Labels

Controls how time dimensions are grouped in Looker's field picker.

### Default Behavior

- **Default**: `group_label: "Date Dimensions - Local Time"`
- Groups all time dimensions together in field picker

### Configuration Precedence

1. **Dimension Metadata Override**
   ```yaml
   config:
     meta:
       time_dimension_group_label: "Event Timestamps"
   ```

2. **Generator Parameter**
   ```python
   generator = LookMLGenerator(time_dimension_group_label="Time Periods")
   ```

3. **CLI Flags**
   ```bash
   --time-dimension-group-label "Custom Label"
   --no-time-dimension-group-label  # Disable grouping
   ```

### Group Item Label

Provides cleaner field labels using Liquid templating:

```yaml
config:
  meta:
    group_item_label: true  # Shows "Date", "Week" instead of "Order Date", "Order Week"
```

**CLI**: `--use-group-item-label`

**Generated LookML**:
```lookml
dimension_group: order_date {
  group_label: "Time Dimensions"
  group_item_label: "{% assign tf = _field._name | remove: 'order_date_' | replace: '_', ' ' | capitalize %}{{ tf }}"
}
```

---

## Join Cardinality Configuration

Explicitly declare join relationships when automatic inference isn't sufficient.

### Use Case

When a fact table has a one-to-one relationship (e.g., every rental has exactly one review), include ALL fields from the joined table.

### Configuration

```yaml
entities:
  - name: review_id
    type: foreign
    config:
      meta:
        join_cardinality: one_to_one  # Include dimensions AND measures
```

### Options

| Value | Behavior |
|-------|----------|
| `one_to_one` | Include ALL fields (dimensions + measures) |
| `many_to_one` | Include only dimensions (default) |
| `None` (omitted) | Use automatic inference |

### Generated LookML

With `one_to_one`:
```lookml
join: gold_reviews {
  relationship: one_to_one
  fields: [
    gold_reviews.dimensions_only*,
    gold_reviews.review_count_measure,
    gold_reviews.avg_rating_measure
  ]
}
```

### Implementation

- `ConfigMeta.join_cardinality`: `Literal["one_to_one", "many_to_one"] | None`
- `LookMLGenerator._build_join_graph()`: Checks entity config and includes measures for `one_to_one`
