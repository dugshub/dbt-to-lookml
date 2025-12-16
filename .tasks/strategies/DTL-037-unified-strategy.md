# DTL-037: Unified PoP Implementation Strategy

## Overview

This strategy covers the complete implementation of Period-over-Period (PoP) support for dbt-to-lookml. The feature enables automatic generation of MTD/YTD and prior period/year comparison measures from semantic model configuration.

## Architecture Analysis

### Current State

1. **Config Schema** (`schemas/config.py`):
   - `ConfigMeta` class handles metadata like `hierarchy`, `convert_tz`, `hidden`, `bi_field`
   - Pattern: Optional fields with Pydantic validation
   - Model-level config available via `SemanticModel.config`

2. **Parser** (`parsers/dbt.py`):
   - `DbtParser._parse_semantic_model()` extracts config.meta from YAML
   - Pattern: Parse nested config → construct Pydantic models
   - Already handles dimension and measure config separately

3. **Generator** (`generators/lookml.py`):
   - `LookMLGenerator.generate_view()` creates view dict with dimensions, measures
   - Pattern: Process semantic model → generate LookML dict → dump to string
   - Timezone variants show similar pattern for multi-variant generation

4. **Type System** (`types.py`):
   - Enums for `AggregationType`, `DimensionType`, etc.
   - Pattern: String enums with mappings

### Target Architecture

```
measure.config.meta.pop → PopConfig → Parser extraction → Generator methods

Components:
1. PopConfig, PopGrain, PopComparison, PopWindow (schemas/config.py)
2. Parse pop meta from measures (parsers/dbt.py)
3. _generate_pop_dimensions() (generators/lookml.py)
4. _generate_pop_parameters() (generators/lookml.py)
5. _generate_pop_hidden_measures() (generators/lookml.py)
6. _generate_pop_visible_measures() (generators/lookml.py)
```

## Implementation Strategy

### Phase 1: Schema Foundation (DTL-038)

**File**: `src/dbt_to_lookml/schemas/config.py`

Add new schema classes:

```python
class PopGrain(str, Enum):
    """Period grains for PoP calculations."""
    SELECTED = "selected"  # Use date filter as-is
    MTD = "mtd"           # Month to date
    YTD = "ytd"           # Year to date
    # Phase 2: QTD = "qtd", WTD = "wtd"

class PopComparison(str, Enum):
    """Comparison periods for PoP."""
    PP = "pp"  # Prior period (offset by period_window)
    PY = "py"  # Prior year (always 1 year offset)

class PopWindow(str, Enum):
    """Period window definitions."""
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"

class PopConfig(BaseModel):
    """Configuration for Period-over-Period calculations."""
    enabled: bool
    grains: list[PopGrain] = [PopGrain.MTD, PopGrain.YTD]
    comparisons: list[PopComparison] = [PopComparison.PP, PopComparison.PY]
    windows: list[PopWindow] = [PopWindow.MONTH]
    format: str | None = None  # LookML value_format_name
    date_dimension: str | None = None  # Override date reference
    date_filter: str | None = None  # Override filter field

# Add to ConfigMeta:
class ConfigMeta(BaseModel):
    ...existing fields...
    pop: PopConfig | None = None
```

**Key Decisions**:
- Use string enums for YAML compatibility
- Default grains: MTD, YTD (most common business needs)
- Default comparisons: both PP and PY
- Default window: month (most common period definition)

### Phase 2: Parser Extension (DTL-039)

**File**: `src/dbt_to_lookml/parsers/dbt.py`

Extend measure parsing in `_parse_semantic_model()`:

```python
# In measure parsing loop:
pop_config = None
if "config" in measure_data:
    config_data = measure_data["config"]
    if "meta" in config_data and "pop" in config_data["meta"]:
        pop_data = config_data["meta"]["pop"]

        # Parse PopConfig
        pop_config = PopConfig(
            enabled=pop_data.get("enabled", False),
            grains=[PopGrain(g) for g in pop_data.get("grains", ["mtd", "ytd"])],
            comparisons=[PopComparison(c) for c in pop_data.get("comparisons", ["pp", "py"])],
            windows=[PopWindow(w) for w in pop_data.get("windows", ["month"])],
            format=pop_data.get("format"),
            date_dimension=pop_data.get("date_dimension"),
            date_filter=pop_data.get("date_filter"),
        )

        # Resolve date_dimension from hierarchy:
        # 1. measure pop.date_dimension
        # 2. model config.meta.pop.date_dimension
        # 3. model defaults.agg_time_dimension
        if not pop_config.date_dimension:
            # Check model-level config
            model_pop = model_data.get("config", {}).get("meta", {}).get("pop", {})
            pop_config.date_dimension = model_pop.get("date_dimension")

            if not pop_config.date_dimension:
                # Fall back to defaults.agg_time_dimension
                defaults = model_data.get("defaults", {})
                pop_config.date_dimension = defaults.get("agg_time_dimension")

        # Derive date_filter if not specified
        if not pop_config.date_filter and pop_config.date_dimension:
            pop_config.date_filter = f"{pop_config.date_dimension}_date"
```

**Key Decisions**:
- Resolution order: measure → model → defaults
- Auto-derive date_filter from date_dimension
- Graceful handling of missing config

### Phase 3: PoP Dimensions (DTL-040)

**File**: `src/dbt_to_lookml/generators/lookml.py`

Add new method `_generate_pop_dimensions()`:

```python
def _generate_pop_dimensions(
    self,
    pop_config: PopConfig,
    date_dimension: str,
    date_filter: str,
) -> list[dict[str, Any]]:
    """Generate hidden yesno dimensions for PoP filtering."""
    dimensions = []

    # Grain dimensions (relative to CURRENT_DATE)
    if PopGrain.MTD in pop_config.grains:
        dimensions.append({
            "name": "is_mtd",
            "hidden": "yes",
            "type": "yesno",
            "sql": f"${{{date_dimension}_raw}} >= DATE_TRUNC('month', CURRENT_DATE)"
        })

    if PopGrain.YTD in pop_config.grains:
        dimensions.append({
            "name": "is_ytd",
            "hidden": "yes",
            "type": "yesno",
            "sql": f"${{{date_dimension}_raw}} >= DATE_TRUNC('year', CURRENT_DATE)"
        })

    # Comparison dimensions (dynamic, use templated filters)
    if PopComparison.PP in pop_config.comparisons:
        dimensions.append({
            "name": "is_prior_period",
            "hidden": "yes",
            "type": "yesno",
            "sql": f"""${{{date_dimension}_raw}} BETWEEN
       DATEADD({{% parameter period_window %}}, -1, {{% date_start {date_filter} %}})
       AND DATEADD({{% parameter period_window %}}, -1, {{% date_end {date_filter} %}})"""
        })

    if PopComparison.PY in pop_config.comparisons:
        dimensions.append({
            "name": "is_prior_year",
            "hidden": "yes",
            "type": "yesno",
            "sql": f"""${{{date_dimension}_raw}} BETWEEN
       DATEADD('year', -1, {{% date_start {date_filter} %}})
       AND DATEADD('year', -1, {{% date_end {date_filter} %}})"""
        })

    # Combined grain x comparison dimensions
    for grain in pop_config.grains:
        if grain == PopGrain.SELECTED:
            continue  # No grain override for selected

        grain_trunc = "month" if grain == PopGrain.MTD else "year"

        for comparison in pop_config.comparisons:
            offset = f"{{% parameter period_window %}}" if comparison == PopComparison.PP else "'year'"
            dim_name = f"is_{grain.value}_{comparison.value}"

            dimensions.append({
                "name": dim_name,
                "hidden": "yes",
                "type": "yesno",
                "sql": f"""${{{date_dimension}_raw}} >= DATEADD({offset}, -1, DATE_TRUNC('{grain_trunc}', CURRENT_DATE))
       AND ${{{date_dimension}_raw}} <= DATEADD({offset}, -1, CURRENT_DATE)"""
            })

    return dimensions
```

**Key Decisions**:
- Use `{date_dimension}_raw` for date field reference (standard LookML pattern)
- `is_prior_period` uses `{% parameter period_window %}` for dynamic offset
- Combined dimensions handle partial period comparisons correctly

### Phase 4: PoP Parameters (DTL-041)

**File**: `src/dbt_to_lookml/generators/lookml.py`

Add `_generate_pop_parameters()`:

```python
def _generate_pop_parameters(
    self,
    pop_config: PopConfig,
) -> list[dict[str, Any]]:
    """Generate global parameters for PoP control."""
    parameters = []

    # period_window parameter (controls "Prior Period" offset)
    if PopComparison.PP in pop_config.comparisons:
        window_values = []
        for window in pop_config.windows:
            window_values.append({
                "label": window.value.capitalize(),
                "value": window.value
            })

        parameters.append({
            "name": "period_window",
            "label": "Period Window",
            "type": "unquoted",
            "description": "Define what 'Prior Period' means (week/month/quarter)",
            "allowed_value": window_values,
            "default_value": pop_config.windows[0].value if pop_config.windows else "month"
        })

    # period_grain parameter (MTD/YTD/Selected)
    grain_values = []
    grain_values.append({"label": "Selected Range", "value": "selected"})
    for grain in pop_config.grains:
        if grain != PopGrain.SELECTED:
            grain_values.append({
                "label": grain.value.upper(),
                "value": grain.value
            })

    parameters.append({
        "name": "period_grain",
        "label": "Reporting Grain",
        "type": "unquoted",
        "description": "Use date filter as-is or override to to-date",
        "allowed_value": grain_values,
        "default_value": "selected"
    })

    # comparison_period parameter
    comparison_values = []
    if PopComparison.PP in pop_config.comparisons:
        comparison_values.append({"label": "Prior Period", "value": "pp"})
    if PopComparison.PY in pop_config.comparisons:
        comparison_values.append({"label": "Prior Year", "value": "py"})

    if comparison_values:
        parameters.append({
            "name": "comparison_period",
            "label": "Compare To",
            "type": "unquoted",
            "description": "Select comparison period",
            "allowed_value": comparison_values,
            "default_value": "py"
        })

    return parameters
```

**Key Decisions**:
- Only generate period_window if PP comparison is used
- Default period_grain to "selected" (no override)
- Default comparison to "py" (prior year is more common)

### Phase 5: Hidden PoP Measures (DTL-042)

**File**: `src/dbt_to_lookml/generators/lookml.py`

Add `_generate_pop_hidden_measures()`:

```python
def _generate_pop_hidden_measures(
    self,
    measure: Measure,
    pop_config: PopConfig,
) -> list[dict[str, Any]]:
    """Generate hidden measures for each grain x comparison combo."""
    measures = []
    base_name = measure.name
    base_type = LOOKML_TYPE_MAP.get(measure.agg, "number")
    base_sql = self._qualify_measure_sql(measure.expr, measure.name)

    # Apply float cast if needed
    if measure.agg in FLOAT_CAST_AGGREGATIONS:
        base_sql = f"({base_sql})::FLOAT"

    # Base measure (current period, no filter)
    measures.append({
        "name": f"{base_name}_measure",
        "hidden": "yes",
        "type": base_type,
        "sql": base_sql if measure.agg != AggregationType.COUNT else None,
    })

    # Grain measures
    for grain in pop_config.grains:
        if grain == PopGrain.SELECTED:
            continue

        measure_dict = {
            "name": f"{base_name}_{grain.value}_measure",
            "hidden": "yes",
            "type": base_type,
            "filters": [{"field": f"is_{grain.value}", "value": "yes"}]
        }
        if measure.agg != AggregationType.COUNT:
            measure_dict["sql"] = base_sql
        measures.append(measure_dict)

    # Comparison measures
    for comparison in pop_config.comparisons:
        filter_name = "is_prior_period" if comparison == PopComparison.PP else "is_prior_year"
        measure_dict = {
            "name": f"{base_name}_{comparison.value}_measure",
            "hidden": "yes",
            "type": base_type,
            "filters": [{"field": filter_name, "value": "yes"}]
        }
        if measure.agg != AggregationType.COUNT:
            measure_dict["sql"] = base_sql
        measures.append(measure_dict)

    # Combined grain x comparison measures
    for grain in pop_config.grains:
        if grain == PopGrain.SELECTED:
            continue

        for comparison in pop_config.comparisons:
            filter_name = f"is_{grain.value}_{comparison.value}"
            measure_dict = {
                "name": f"{base_name}_{grain.value}_{comparison.value}_measure",
                "hidden": "yes",
                "type": base_type,
                "filters": [{"field": filter_name, "value": "yes"}]
            }
            if measure.agg != AggregationType.COUNT:
                measure_dict["sql"] = base_sql
            measures.append(measure_dict)

    return measures
```

**Key Decisions**:
- Preserve original aggregation type
- Use LookML `filters` parameter (cleaner than SQL CASE)
- Only add `sql` for non-count aggregations

### Phase 6: Visible PoP Measures (DTL-043)

**File**: `src/dbt_to_lookml/generators/lookml.py`

Add `_generate_pop_visible_measures()`:

```python
def _generate_pop_visible_measures(
    self,
    measure: Measure,
    pop_config: PopConfig,
) -> list[dict[str, Any]]:
    """Generate user-facing measure group with current, comparison, delta, %change."""
    measures = []
    base_name = measure.name
    label = measure.label or _smart_title(base_name)
    format_name = pop_config.format

    # Build CASE for current value (switches on period_grain)
    current_cases = ["CASE {% parameter period_grain %}"]
    current_cases.append(f"  WHEN 'selected' THEN ${{{base_name}_measure}}")
    for grain in pop_config.grains:
        if grain != PopGrain.SELECTED:
            current_cases.append(f"  WHEN '{grain.value}' THEN ${{{base_name}_{grain.value}_measure}}")
    current_cases.append("END")

    measures.append({
        "name": base_name,
        "group_label": label,
        "label": label,
        "type": "number",
        "sql": "\n".join(current_cases),
        **({"value_format_name": format_name} if format_name else {})
    })

    # Build CASE for comparison value (switches on grain AND comparison)
    comparison_cases = ["CASE"]
    for grain in [PopGrain.SELECTED] + list(pop_config.grains):
        grain_cond = f"{{% parameter period_grain %}} = '{grain.value}'"

        for comparison in pop_config.comparisons:
            comp_cond = f"{{% parameter comparison_period %}} = '{comparison.value}'"

            if grain == PopGrain.SELECTED:
                measure_ref = f"${{{base_name}_{comparison.value}_measure}}"
            else:
                measure_ref = f"${{{base_name}_{grain.value}_{comparison.value}_measure}}"

            comparison_cases.append(f"  WHEN {grain_cond} AND {comp_cond} THEN {measure_ref}")
    comparison_cases.append("END")

    measures.append({
        "name": f"{base_name}_comparison",
        "group_label": label,
        "label": f"{label} (Comp)",
        "type": "number",
        "sql": "\n".join(comparison_cases),
        "required_fields": [base_name],
        **({"value_format_name": format_name} if format_name else {})
    })

    # Delta (change)
    measures.append({
        "name": f"{base_name}_change",
        "group_label": label,
        "label": f"{label} \u0394",  # Delta symbol
        "type": "number",
        "sql": f"${{{base_name}}} - ${{{base_name}_comparison}}",
        "required_fields": [base_name, f"{base_name}_comparison"],
        **({"value_format_name": format_name} if format_name else {})
    })

    # Percent change
    measures.append({
        "name": f"{base_name}_pct_change",
        "group_label": label,
        "label": f"{label} %\u0394",
        "type": "number",
        "sql": f"(${{{base_name}}} - ${{{base_name}_comparison}}) / NULLIF(${{{base_name}_comparison}}, 0)",
        "required_fields": [base_name, f"{base_name}_comparison"],
        "value_format_name": "percent_1"
    })

    return measures
```

**Key Decisions**:
- Group label = measure label for clean organization
- Delta uses unicode symbol for compact display
- NULLIF protects against division by zero
- Percent change always uses percent_1 format

### Phase 7: Pipeline Integration (DTL-044)

**File**: `src/dbt_to_lookml/generators/lookml.py`

Modify `generate_view()` to detect and integrate PoP:

```python
def generate_view(
    self,
    model: SemanticModel,
    required_measures: set[str] | None = None,
    usage_map: dict[str, dict[str, Any]] | None = None,
) -> dict:
    """Generate LookML view dict with PoP support."""

    # ... existing view generation ...

    # Check for PoP-enabled measures
    pop_measures = [
        m for m in model.measures
        if m.config and m.config.meta and m.config.meta.pop
        and m.config.meta.pop.enabled
    ]

    if pop_measures:
        # Get first PoP config for shared dimensions/parameters
        first_pop = pop_measures[0].config.meta.pop

        # Resolve date_dimension
        date_dim = first_pop.date_dimension
        if not date_dim and model.defaults:
            date_dim = model.defaults.get("agg_time_dimension")

        date_filter = first_pop.date_filter or f"{date_dim}_date"

        # Generate PoP dimensions (shared across all PoP measures)
        pop_dims = self._generate_pop_dimensions(first_pop, date_dim, date_filter)

        # Generate PoP parameters (shared)
        pop_params = self._generate_pop_parameters(first_pop)

        # Add to view dict
        if "dimensions" not in view_dict:
            view_dict["dimensions"] = []
        view_dict["dimensions"].extend(pop_dims)

        if "parameters" not in view_dict:
            view_dict["parameters"] = []
        view_dict["parameters"] = pop_params + view_dict.get("parameters", [])

        # Generate hidden and visible measures for each PoP measure
        for measure in pop_measures:
            pop_config = measure.config.meta.pop

            # Hidden measures
            hidden_measures = self._generate_pop_hidden_measures(measure, pop_config)
            view_dict["measures"].extend(hidden_measures)

            # Visible measures
            visible_measures = self._generate_pop_visible_measures(measure, pop_config)
            view_dict["measures"].extend(visible_measures)

    return base_view_dict
```

**Key Decisions**:
- PoP dimensions/parameters are shared (use first PoP config)
- Hidden + visible measures generated per PoP-enabled measure
- Maintains backward compatibility (no changes if no PoP config)

### Phase 8: Test Suite (DTL-045)

**File**: `src/tests/unit/test_pop.py`

```python
"""Unit tests for PoP functionality."""

import pytest
from dbt_to_lookml.schemas.config import PopConfig, PopGrain, PopComparison, PopWindow
from dbt_to_lookml.generators.lookml import LookMLGenerator

class TestPopConfig:
    """Test PopConfig schema validation."""

    def test_minimal_config(self):
        """Test minimal valid PoP config."""
        config = PopConfig(enabled=True)
        assert config.enabled is True
        assert config.grains == [PopGrain.MTD, PopGrain.YTD]
        assert config.comparisons == [PopComparison.PP, PopComparison.PY]

    def test_custom_grains(self):
        """Test custom grain configuration."""
        config = PopConfig(enabled=True, grains=[PopGrain.YTD])
        assert config.grains == [PopGrain.YTD]

    def test_date_filter_derivation(self):
        """Test date_filter defaults from date_dimension."""
        # This is handled at parse time, not in schema
        pass

class TestPopDimensions:
    """Test PoP dimension generation."""

    def test_mtd_dimension(self):
        """Test is_mtd dimension SQL."""
        generator = LookMLGenerator()
        config = PopConfig(enabled=True, grains=[PopGrain.MTD])
        dims = generator._generate_pop_dimensions(config, "selected_date", "selected_date_date")

        assert len(dims) >= 1
        mtd_dim = next(d for d in dims if d["name"] == "is_mtd")
        assert "DATE_TRUNC('month', CURRENT_DATE)" in mtd_dim["sql"]

    def test_prior_period_uses_parameter(self):
        """Test is_prior_period uses period_window parameter."""
        generator = LookMLGenerator()
        config = PopConfig(enabled=True, comparisons=[PopComparison.PP])
        dims = generator._generate_pop_dimensions(config, "selected_date", "selected_date_date")

        pp_dim = next(d for d in dims if d["name"] == "is_prior_period")
        assert "{% parameter period_window %}" in pp_dim["sql"]

class TestPopMeasures:
    """Test PoP measure generation."""

    def test_hidden_measure_count(self):
        """Test correct number of hidden measures generated."""
        # With grains=[mtd, ytd] and comparisons=[pp, py]:
        # 1 base + 2 grains + 2 comparisons + 4 combined = 9
        pass

    def test_visible_measure_group(self):
        """Test visible measures have correct group_label."""
        pass

class TestPopIntegration:
    """Test full PoP pipeline integration."""

    def test_end_to_end_generation(self):
        """Test complete PoP view generation."""
        pass

    def test_backward_compatibility(self):
        """Test models without PoP are unchanged."""
        pass
```

## Implementation Order

1. **DTL-038**: Schema (no dependencies)
2. **DTL-039**: Parser (depends on DTL-038)
3. **DTL-040**: Dimensions (depends on DTL-038)
4. **DTL-041**: Parameters (depends on DTL-038)
5. **DTL-042**: Hidden measures (depends on DTL-038, DTL-040)
6. **DTL-043**: Visible measures (depends on DTL-042)
7. **DTL-044**: Pipeline integration (depends on all above)
8. **DTL-045**: Tests (parallel with implementation)

## Risk Mitigation

1. **SQL Dialect Compatibility**: Use standard SQL (DATEADD, DATE_TRUNC) - works with Redshift, Snowflake, BigQuery (with minor syntax differences)

2. **Backward Compatibility**: PoP is opt-in via `pop.enabled: true` - no changes to existing behavior

3. **Test Coverage**: Comprehensive unit tests for each component + integration tests

## Success Criteria

- [ ] `PopConfig` validates all configuration options
- [ ] Parser extracts PoP config with correct resolution order
- [ ] Generated dimensions filter data correctly
- [ ] Parameters provide user control over grain/comparison
- [ ] Hidden measures provide all required variants
- [ ] Visible measures switch correctly based on parameters
- [ ] 95%+ test coverage on PoP code
- [ ] All existing tests continue to pass
