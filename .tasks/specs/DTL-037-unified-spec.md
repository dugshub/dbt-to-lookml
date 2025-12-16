# DTL-037: Unified PoP Implementation Spec

## Overview

This specification provides detailed implementation instructions for all 8 PoP-related issues (DTL-038 through DTL-045). Each section contains exact code changes, file locations, and test requirements.

---

## DTL-038: Add PoP Configuration Schema

### File: `src/dbt_to_lookml/schemas/config.py`

#### Changes Required

1. **Add imports at top of file:**

```python
from enum import Enum
```

2. **Add new enums before `Hierarchy` class:**

```python
class PopGrain(str, Enum):
    """Period grains for PoP calculations.

    Defines how to slice the "current" period:
    - SELECTED: Use the user's date filter exactly as-is
    - MTD: Override to Month-to-Date (current month through today)
    - YTD: Override to Year-to-Date (current year through today)
    """

    SELECTED = "selected"
    MTD = "mtd"
    YTD = "ytd"


class PopComparison(str, Enum):
    """Comparison periods for PoP calculations.

    Defines what to compare against:
    - PP: Prior Period (offset by period_window parameter)
    - PY: Prior Year (always 1 year offset)
    """

    PP = "pp"
    PY = "py"


class PopWindow(str, Enum):
    """Period window definitions.

    Defines what "Prior Period" means:
    - WEEK: 1 week offset
    - MONTH: 1 month offset
    - QUARTER: 1 quarter offset
    """

    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
```

3. **Add PopConfig class after PopWindow:**

```python
class PopConfig(BaseModel):
    """Configuration for Period-over-Period calculations.

    Enables automatic generation of MTD/YTD and prior period/year
    comparison measures from a single measure definition.

    Attributes:
        enabled: Whether to generate PoP variants for this measure.
        grains: Which period grains to generate (default: MTD, YTD).
        comparisons: Which comparison periods to generate (default: PP, PY).
        windows: What "Prior Period" can mean (default: month).
        format: LookML value_format_name for generated measures.
        date_dimension: Override date dimension reference in SQL.
        date_filter: Override filter field for {% date_start/end %}.

    Example:
        ```yaml
        measures:
          - name: revenue
            agg: sum
            config:
              meta:
                pop:
                  enabled: true
                  grains: [mtd, ytd]
                  comparisons: [pp, py]
                  format: usd
        ```
    """

    enabled: bool
    grains: list[PopGrain] = [PopGrain.MTD, PopGrain.YTD]
    comparisons: list[PopComparison] = [PopComparison.PP, PopComparison.PY]
    windows: list[PopWindow] = [PopWindow.MONTH]
    format: str | None = None
    date_dimension: str | None = None
    date_filter: str | None = None
```

4. **Update ConfigMeta class - add pop field:**

```python
class ConfigMeta(BaseModel):
    """Represents metadata in a config section."""

    # ... existing fields ...
    join_cardinality: Literal["one_to_one", "many_to_one"] | None = None
    pop: PopConfig | None = None  # Add this line
```

5. **Update `__all__` exports:**

```python
__all__ = [
    "Hierarchy",
    "TimezoneVariant",
    "ConfigMeta",
    "Config",
    "PopGrain",
    "PopComparison",
    "PopWindow",
    "PopConfig",
]
```

### Tests for DTL-038

Create `src/tests/unit/test_pop_config.py`:

```python
"""Unit tests for PoP configuration schema."""

import pytest
from pydantic import ValidationError

from dbt_to_lookml.schemas.config import (
    PopConfig,
    PopGrain,
    PopComparison,
    PopWindow,
)


class TestPopGrain:
    """Tests for PopGrain enum."""

    def test_valid_grain_values(self) -> None:
        """Test all valid grain values."""
        assert PopGrain.SELECTED == "selected"
        assert PopGrain.MTD == "mtd"
        assert PopGrain.YTD == "ytd"

    def test_grain_from_string(self) -> None:
        """Test creating grain from string value."""
        assert PopGrain("mtd") == PopGrain.MTD


class TestPopComparison:
    """Tests for PopComparison enum."""

    def test_valid_comparison_values(self) -> None:
        """Test all valid comparison values."""
        assert PopComparison.PP == "pp"
        assert PopComparison.PY == "py"


class TestPopWindow:
    """Tests for PopWindow enum."""

    def test_valid_window_values(self) -> None:
        """Test all valid window values."""
        assert PopWindow.WEEK == "week"
        assert PopWindow.MONTH == "month"
        assert PopWindow.QUARTER == "quarter"


class TestPopConfig:
    """Tests for PopConfig model."""

    def test_minimal_config(self) -> None:
        """Test minimal valid PoP config with defaults."""
        config = PopConfig(enabled=True)

        assert config.enabled is True
        assert config.grains == [PopGrain.MTD, PopGrain.YTD]
        assert config.comparisons == [PopComparison.PP, PopComparison.PY]
        assert config.windows == [PopWindow.MONTH]
        assert config.format is None
        assert config.date_dimension is None
        assert config.date_filter is None

    def test_disabled_config(self) -> None:
        """Test disabled PoP config."""
        config = PopConfig(enabled=False)
        assert config.enabled is False

    def test_custom_grains(self) -> None:
        """Test custom grain configuration."""
        config = PopConfig(enabled=True, grains=[PopGrain.YTD])
        assert config.grains == [PopGrain.YTD]

    def test_custom_comparisons(self) -> None:
        """Test custom comparison configuration."""
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])
        assert config.comparisons == [PopComparison.PY]

    def test_custom_windows(self) -> None:
        """Test custom window configuration."""
        config = PopConfig(
            enabled=True, windows=[PopWindow.WEEK, PopWindow.QUARTER]
        )
        assert config.windows == [PopWindow.WEEK, PopWindow.QUARTER]

    def test_full_config(self) -> None:
        """Test fully specified PoP config."""
        config = PopConfig(
            enabled=True,
            grains=[PopGrain.SELECTED, PopGrain.MTD],
            comparisons=[PopComparison.PP],
            windows=[PopWindow.MONTH],
            format="usd",
            date_dimension="selected_date",
            date_filter="selected_date_date",
        )

        assert config.enabled is True
        assert config.format == "usd"
        assert config.date_dimension == "selected_date"
        assert config.date_filter == "selected_date_date"

    def test_invalid_grain_raises_error(self) -> None:
        """Test that invalid grain value raises ValidationError."""
        with pytest.raises(ValidationError):
            PopConfig(enabled=True, grains=["invalid"])

    def test_invalid_comparison_raises_error(self) -> None:
        """Test that invalid comparison value raises ValidationError."""
        with pytest.raises(ValidationError):
            PopConfig(enabled=True, comparisons=["invalid"])

    def test_invalid_window_raises_error(self) -> None:
        """Test that invalid window value raises ValidationError."""
        with pytest.raises(ValidationError):
            PopConfig(enabled=True, windows=["invalid"])

    def test_enabled_required(self) -> None:
        """Test that enabled field is required."""
        with pytest.raises(ValidationError):
            PopConfig()  # Missing enabled
```

---

## DTL-039: Parse Pop Meta from Measures

### File: `src/dbt_to_lookml/parsers/dbt.py`

#### Changes Required

1. **Add imports at top of file:**

```python
from dbt_to_lookml.schemas.config import (
    Config,
    ConfigMeta,
    Hierarchy,
    PopConfig,
    PopGrain,
    PopComparison,
    PopWindow,
)
```

2. **Add helper method to DbtParser class:**

```python
def _parse_pop_config(
    self,
    pop_data: dict[str, Any],
    model_data: dict[str, Any],
) -> PopConfig | None:
    """Parse PoP configuration from measure meta with resolution.

    Resolves date_dimension and date_filter through hierarchy:
    1. Measure-level pop config
    2. Model-level pop config
    3. Model defaults.agg_time_dimension

    Args:
        pop_data: The pop config dict from measure meta.
        model_data: The full model data for fallback resolution.

    Returns:
        Parsed PopConfig or None if not enabled.
    """
    if not pop_data.get("enabled", False):
        return None

    # Parse enum values
    grains = [
        PopGrain(g) for g in pop_data.get("grains", ["mtd", "ytd"])
    ]
    comparisons = [
        PopComparison(c) for c in pop_data.get("comparisons", ["pp", "py"])
    ]
    windows = [
        PopWindow(w) for w in pop_data.get("windows", ["month"])
    ]

    # Get explicit values from measure config
    date_dimension = pop_data.get("date_dimension")
    date_filter = pop_data.get("date_filter")

    # Resolve date_dimension if not specified
    if not date_dimension:
        # Try model-level pop config
        model_meta = model_data.get("config", {}).get("meta", {})
        model_pop = model_meta.get("pop", {})
        date_dimension = model_pop.get("date_dimension")

        # Fall back to defaults.agg_time_dimension
        if not date_dimension:
            defaults = model_data.get("defaults", {})
            date_dimension = defaults.get("agg_time_dimension")

    # Derive date_filter if not specified
    if not date_filter and date_dimension:
        date_filter = f"{date_dimension}_date"

    return PopConfig(
        enabled=True,
        grains=grains,
        comparisons=comparisons,
        windows=windows,
        format=pop_data.get("format"),
        date_dimension=date_dimension,
        date_filter=date_filter,
    )
```

3. **Modify measure parsing in `_parse_semantic_model()` method:**

Find the measure parsing loop (around line 355-446) and update the config parsing:

```python
# Parse measures
measures = []
for measure_data in model_data.get("measures", []):
    try:
        # Handle complex expressions (multiline)
        expr = measure_data.get("expr")
        if expr and isinstance(expr, str):
            expr = expr.strip()

        # Parse config with hierarchy and pop if present
        measure_config = None
        if "config" in measure_data:
            config_data = measure_data["config"]
            config_meta = None
            if "meta" in config_data:
                meta_data = config_data["meta"]
                hierarchy = None
                # ... existing hierarchy parsing ...

                # Parse pop config if present
                pop_config = None
                if "pop" in meta_data:
                    pop_config = self._parse_pop_config(
                        meta_data["pop"], model_data
                    )

                config_meta = ConfigMeta(
                    domain=meta_data.get("domain"),
                    owner=meta_data.get("owner"),
                    contains_pii=meta_data.get("contains_pii"),
                    update_frequency=meta_data.get("update_frequency"),
                    subject=meta_data.get("subject"),
                    category=meta_data.get("category"),
                    hierarchy=hierarchy,
                    convert_tz=meta_data.get("convert_tz"),
                    hidden=meta_data.get("hidden"),
                    bi_field=meta_data.get("bi_field"),
                    time_dimension_group_label=meta_data.get(
                        "time_dimension_group_label"
                    ),
                    pop=pop_config,  # Add this line
                )
            measure_config = Config(meta=config_meta)

        measure = Measure(
            name=measure_data["name"],
            agg=AggregationType(measure_data["agg"]),
            expr=expr,
            description=measure_data.get("description"),
            label=measure_data.get("label"),
            create_metric=measure_data.get("create_metric"),
            config=measure_config,
        )
        measures.append(measure)
    except Exception as e:
        measure_name = measure_data.get("name", "unknown")
        raise ValueError(
            f"Error parsing measure '{measure_name}': {e}"
        ) from e
```

### Tests for DTL-039

Add to `src/tests/unit/test_dbt_parser.py`:

```python
class TestPopParsing:
    """Tests for PoP configuration parsing."""

    def test_parse_measure_with_pop_config(self) -> None:
        """Test parsing measure with full PoP config."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    measures:
      - name: revenue
        agg: sum
        expr: checkout_amount
        config:
          meta:
            pop:
              enabled: true
              grains: [mtd, ytd]
              comparisons: [pp, py]
              windows: [month]
              format: usd
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()

            models = parser.parse_file(Path(f.name))

            assert len(models) == 1
            assert len(models[0].measures) == 1

            measure = models[0].measures[0]
            assert measure.config is not None
            assert measure.config.meta is not None
            assert measure.config.meta.pop is not None

            pop = measure.config.meta.pop
            assert pop.enabled is True
            assert pop.grains == [PopGrain.MTD, PopGrain.YTD]
            assert pop.format == "usd"

    def test_pop_date_dimension_resolution(self) -> None:
        """Test date_dimension falls back to defaults.agg_time_dimension."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: rental_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
"""
        parser = DbtParser()
        # ... parse and verify date_dimension == "rental_date"
        # ... and date_filter == "rental_date_date"

    def test_pop_disabled_returns_none(self) -> None:
        """Test that disabled pop config is not stored."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: false
"""
        # ... parse and verify pop is None

    def test_measure_without_pop(self) -> None:
        """Test measures without pop config work normally."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    measures:
      - name: revenue
        agg: sum
"""
        # ... parse and verify measure works, pop is None
```

---

## DTL-040: Generate PoP Date Dimensions

### File: `src/dbt_to_lookml/generators/lookml.py`

#### Add New Method

```python
def _generate_pop_dimensions(
    self,
    pop_config: "PopConfig",
    date_dimension: str,
    date_filter: str,
) -> list[dict[str, Any]]:
    """Generate hidden yesno dimensions for PoP date filtering.

    Creates dimensions that isolate data for specific time periods:
    - Grain dimensions (is_mtd, is_ytd): Relative to CURRENT_DATE
    - Comparison dimensions (is_prior_period, is_prior_year): Use templated filters
    - Combined dimensions (is_mtd_pp, is_mtd_py, etc.): For partial period comparisons

    Args:
        pop_config: The PopConfig with grains and comparisons.
        date_dimension: Name of the date dimension (e.g., "selected_date").
        date_filter: Name of the filter field (e.g., "selected_date_date").

    Returns:
        List of dimension dicts ready for LookML output.
    """
    from dbt_to_lookml.schemas.config import PopGrain, PopComparison

    dimensions: list[dict[str, Any]] = []

    # Grain dimensions (static, relative to CURRENT_DATE)
    if PopGrain.MTD in pop_config.grains:
        dimensions.append({
            "name": "is_mtd",
            "hidden": "yes",
            "type": "yesno",
            "sql": f"${{{date_dimension}_raw}} >= DATE_TRUNC('month', CURRENT_DATE)",
            "description": "True if date is in current month-to-date period",
        })

    if PopGrain.YTD in pop_config.grains:
        dimensions.append({
            "name": "is_ytd",
            "hidden": "yes",
            "type": "yesno",
            "sql": f"${{{date_dimension}_raw}} >= DATE_TRUNC('year', CURRENT_DATE)",
            "description": "True if date is in current year-to-date period",
        })

    # Comparison dimensions (dynamic, use templated filters)
    if PopComparison.PP in pop_config.comparisons:
        dimensions.append({
            "name": "is_prior_period",
            "hidden": "yes",
            "type": "yesno",
            "sql": f"""${{{date_dimension}_raw}} BETWEEN
    DATEADD({{% parameter period_window %}}, -1, {{% date_start {date_filter} %}})
    AND DATEADD({{% parameter period_window %}}, -1, {{% date_end {date_filter} %}})""",
            "description": "True if date is in the prior period (offset by period_window)",
        })

    if PopComparison.PY in pop_config.comparisons:
        dimensions.append({
            "name": "is_prior_year",
            "hidden": "yes",
            "type": "yesno",
            "sql": f"""${{{date_dimension}_raw}} BETWEEN
    DATEADD('year', -1, {{% date_start {date_filter} %}})
    AND DATEADD('year', -1, {{% date_end {date_filter} %}})""",
            "description": "True if date is in the same period last year",
        })

    # Combined grain x comparison dimensions
    for grain in pop_config.grains:
        if grain == PopGrain.SELECTED:
            continue  # No grain override for selected

        grain_trunc = "month" if grain == PopGrain.MTD else "year"
        grain_label = "MTD" if grain == PopGrain.MTD else "YTD"

        for comparison in pop_config.comparisons:
            if comparison == PopComparison.PP:
                offset = "{% parameter period_window %}"
                comp_label = "prior period"
            else:
                offset = "'year'"
                comp_label = "prior year"

            dim_name = f"is_{grain.value}_{comparison.value}"

            dimensions.append({
                "name": dim_name,
                "hidden": "yes",
                "type": "yesno",
                "sql": f"""${{{date_dimension}_raw}} >= DATEADD({offset}, -1, DATE_TRUNC('{grain_trunc}', CURRENT_DATE))
    AND ${{{date_dimension}_raw}} <= DATEADD({offset}, -1, CURRENT_DATE)""",
                "description": f"True if date is in {grain_label} of {comp_label}",
            })

    return dimensions
```

### Tests for DTL-040

Add to `src/tests/unit/test_pop_generator.py`:

```python
class TestPopDimensions:
    """Tests for PoP dimension generation."""

    def test_mtd_dimension_sql(self) -> None:
        """Test is_mtd dimension generates correct SQL."""
        generator = LookMLGenerator()
        config = PopConfig(enabled=True, grains=[PopGrain.MTD])

        dims = generator._generate_pop_dimensions(
            config, "selected_date", "selected_date_date"
        )

        mtd_dim = next(d for d in dims if d["name"] == "is_mtd")
        assert mtd_dim["hidden"] == "yes"
        assert mtd_dim["type"] == "yesno"
        assert "DATE_TRUNC('month', CURRENT_DATE)" in mtd_dim["sql"]
        assert "${selected_date_raw}" in mtd_dim["sql"]

    def test_prior_period_uses_parameter(self) -> None:
        """Test is_prior_period uses period_window parameter."""
        generator = LookMLGenerator()
        config = PopConfig(enabled=True, comparisons=[PopComparison.PP])

        dims = generator._generate_pop_dimensions(
            config, "selected_date", "selected_date_date"
        )

        pp_dim = next(d for d in dims if d["name"] == "is_prior_period")
        assert "{% parameter period_window %}" in pp_dim["sql"]
        assert "{% date_start selected_date_date %}" in pp_dim["sql"]

    def test_combined_dimensions_generated(self) -> None:
        """Test combined grain x comparison dimensions."""
        generator = LookMLGenerator()
        config = PopConfig(
            enabled=True,
            grains=[PopGrain.MTD, PopGrain.YTD],
            comparisons=[PopComparison.PP, PopComparison.PY],
        )

        dims = generator._generate_pop_dimensions(
            config, "selected_date", "selected_date_date"
        )

        dim_names = {d["name"] for d in dims}
        assert "is_mtd_pp" in dim_names
        assert "is_mtd_py" in dim_names
        assert "is_ytd_pp" in dim_names
        assert "is_ytd_py" in dim_names
```

---

## DTL-041: Generate PoP Global Parameters

### File: `src/dbt_to_lookml/generators/lookml.py`

#### Add New Method

```python
def _generate_pop_parameters(
    self,
    pop_config: "PopConfig",
) -> list[dict[str, Any]]:
    """Generate global parameters for PoP UI control.

    Creates parameters for:
    - period_window: What's a "period"? (week/month/quarter)
    - period_grain: Use filter as-is or to-date? (selected/mtd/ytd)
    - comparison_period: Compare to what? (pp/py)

    Args:
        pop_config: The PopConfig with grains, comparisons, windows.

    Returns:
        List of parameter dicts ready for LookML output.
    """
    from dbt_to_lookml.schemas.config import PopGrain, PopComparison

    parameters: list[dict[str, Any]] = []

    # period_window parameter (controls "Prior Period" offset)
    if PopComparison.PP in pop_config.comparisons:
        window_values = [
            {"label": w.value.capitalize(), "value": w.value}
            for w in pop_config.windows
        ]

        parameters.append({
            "name": "period_window",
            "label": "Period Window",
            "type": "unquoted",
            "description": "Define what 'Prior Period' means",
            "allowed_value": window_values,
            "default_value": pop_config.windows[0].value if pop_config.windows else "month",
        })

    # period_grain parameter (MTD/YTD/Selected)
    grain_values = [{"label": "Selected Range", "value": "selected"}]
    for grain in pop_config.grains:
        if grain != PopGrain.SELECTED:
            grain_values.append({
                "label": grain.value.upper(),
                "value": grain.value,
            })

    parameters.append({
        "name": "period_grain",
        "label": "Reporting Grain",
        "type": "unquoted",
        "description": "Use date filter as-is or override to to-date",
        "allowed_value": grain_values,
        "default_value": "selected",
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
            "default_value": "py",
        })

    return parameters
```

### Tests for DTL-041

```python
class TestPopParameters:
    """Tests for PoP parameter generation."""

    def test_period_window_parameter(self) -> None:
        """Test period_window parameter has correct values."""
        generator = LookMLGenerator()
        config = PopConfig(
            enabled=True,
            windows=[PopWindow.WEEK, PopWindow.MONTH, PopWindow.QUARTER],
        )

        params = generator._generate_pop_parameters(config)

        window_param = next(p for p in params if p["name"] == "period_window")
        assert window_param["type"] == "unquoted"
        assert len(window_param["allowed_value"]) == 3
        assert window_param["default_value"] == "week"

    def test_period_grain_always_includes_selected(self) -> None:
        """Test period_grain always has 'Selected Range' option."""
        generator = LookMLGenerator()
        config = PopConfig(enabled=True, grains=[PopGrain.MTD])

        params = generator._generate_pop_parameters(config)

        grain_param = next(p for p in params if p["name"] == "period_grain")
        values = [v["value"] for v in grain_param["allowed_value"]]
        assert "selected" in values
        assert "mtd" in values

    def test_no_period_window_when_pp_not_used(self) -> None:
        """Test period_window not generated when only PY comparison."""
        generator = LookMLGenerator()
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])

        params = generator._generate_pop_parameters(config)

        param_names = [p["name"] for p in params]
        assert "period_window" not in param_names
```

---

## DTL-042: Generate Hidden PoP Measures

### File: `src/dbt_to_lookml/generators/lookml.py`

#### Add New Method

```python
def _generate_pop_hidden_measures(
    self,
    measure: "Measure",
    pop_config: "PopConfig",
) -> list[dict[str, Any]]:
    """Generate hidden measures for each grain x comparison combination.

    Creates measures filtered by PoP dimensions:
    - Base measure (current period, no filter)
    - Grain measures (mtd, ytd)
    - Comparison measures (pp, py)
    - Combined measures (mtd_pp, mtd_py, ytd_pp, ytd_py)

    Args:
        measure: The source measure with PoP config.
        pop_config: The PopConfig specifying variants to generate.

    Returns:
        List of hidden measure dicts ready for LookML output.
    """
    from dbt_to_lookml.schemas.config import PopGrain, PopComparison
    from dbt_to_lookml.types import FLOAT_CAST_AGGREGATIONS, LOOKML_TYPE_MAP, AggregationType

    measures: list[dict[str, Any]] = []
    base_name = measure.name
    base_type = LOOKML_TYPE_MAP.get(measure.agg, "number")
    base_sql = self._qualify_measure_sql(measure.expr, measure.name)

    # Apply float cast if needed
    if measure.agg in FLOAT_CAST_AGGREGATIONS:
        base_sql = f"({base_sql})::FLOAT"

    # Base measure (current period, no filter)
    base_measure: dict[str, Any] = {
        "name": f"{base_name}_measure",
        "hidden": "yes",
        "type": base_type,
    }
    if measure.agg != AggregationType.COUNT:
        base_measure["sql"] = base_sql
    measures.append(base_measure)

    # Grain measures
    for grain in pop_config.grains:
        if grain == PopGrain.SELECTED:
            continue

        measure_dict: dict[str, Any] = {
            "name": f"{base_name}_{grain.value}_measure",
            "hidden": "yes",
            "type": base_type,
            "filters": [{"field": f"is_{grain.value}", "value": "yes"}],
        }
        if measure.agg != AggregationType.COUNT:
            measure_dict["sql"] = base_sql
        measures.append(measure_dict)

    # Comparison measures
    for comparison in pop_config.comparisons:
        filter_field = "is_prior_period" if comparison == PopComparison.PP else "is_prior_year"
        measure_dict: dict[str, Any] = {
            "name": f"{base_name}_{comparison.value}_measure",
            "hidden": "yes",
            "type": base_type,
            "filters": [{"field": filter_field, "value": "yes"}],
        }
        if measure.agg != AggregationType.COUNT:
            measure_dict["sql"] = base_sql
        measures.append(measure_dict)

    # Combined grain x comparison measures
    for grain in pop_config.grains:
        if grain == PopGrain.SELECTED:
            continue

        for comparison in pop_config.comparisons:
            filter_field = f"is_{grain.value}_{comparison.value}"
            measure_dict: dict[str, Any] = {
                "name": f"{base_name}_{grain.value}_{comparison.value}_measure",
                "hidden": "yes",
                "type": base_type,
                "filters": [{"field": filter_field, "value": "yes"}],
            }
            if measure.agg != AggregationType.COUNT:
                measure_dict["sql"] = base_sql
            measures.append(measure_dict)

    return measures
```

### Tests for DTL-042

```python
class TestPopHiddenMeasures:
    """Tests for hidden PoP measure generation."""

    def test_correct_measure_count(self) -> None:
        """Test correct number of hidden measures generated."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM, expr="amount")
        config = PopConfig(
            enabled=True,
            grains=[PopGrain.MTD, PopGrain.YTD],
            comparisons=[PopComparison.PP, PopComparison.PY],
        )

        measures = generator._generate_pop_hidden_measures(measure, config)

        # 1 base + 2 grains + 2 comparisons + 4 combined = 9
        assert len(measures) == 9

    def test_filter_syntax_correct(self) -> None:
        """Test filters use correct LookML syntax."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM)
        config = PopConfig(enabled=True, grains=[PopGrain.MTD])

        measures = generator._generate_pop_hidden_measures(measure, config)

        mtd_measure = next(m for m in measures if m["name"] == "revenue_mtd_measure")
        assert mtd_measure["filters"] == [{"field": "is_mtd", "value": "yes"}]

    def test_count_measures_no_sql(self) -> None:
        """Test COUNT measures don't have sql parameter."""
        generator = LookMLGenerator()
        measure = Measure(name="order_count", agg=AggregationType.COUNT)
        config = PopConfig(enabled=True, grains=[PopGrain.MTD])

        measures = generator._generate_pop_hidden_measures(measure, config)

        for m in measures:
            assert "sql" not in m
```

---

## DTL-043: Generate Visible PoP Measure Group

### File: `src/dbt_to_lookml/generators/lookml.py`

#### Add New Method

```python
def _generate_pop_visible_measures(
    self,
    measure: "Measure",
    pop_config: "PopConfig",
) -> list[dict[str, Any]]:
    """Generate user-facing measure group with current, comparison, delta, %change.

    Creates four visible measures:
    - {name}: Current value (switches on period_grain)
    - {name}_comparison: Comparison value (switches on grain + comparison)
    - {name}_change: Delta (current - comparison)
    - {name}_pct_change: Percent change

    Args:
        measure: The source measure with PoP config.
        pop_config: The PopConfig specifying variants.

    Returns:
        List of visible measure dicts ready for LookML output.
    """
    from dbt_to_lookml.schemas.config import PopGrain, PopComparison
    from dbt_to_lookml.schemas.semantic_layer import _smart_title

    measures: list[dict[str, Any]] = []
    base_name = measure.name
    label = measure.label or _smart_title(base_name)
    format_name = pop_config.format

    # Build CASE for current value (switches on period_grain)
    current_cases = ["CASE {% parameter period_grain %}"]
    current_cases.append(f"  WHEN 'selected' THEN ${{{base_name}_measure}}")
    for grain in pop_config.grains:
        if grain != PopGrain.SELECTED:
            current_cases.append(
                f"  WHEN '{grain.value}' THEN ${{{base_name}_{grain.value}_measure}}"
            )
    current_cases.append("END")

    current_measure: dict[str, Any] = {
        "name": base_name,
        "group_label": label,
        "label": label,
        "type": "number",
        "sql": "\n".join(current_cases),
    }
    if format_name:
        current_measure["value_format_name"] = format_name
    measures.append(current_measure)

    # Build CASE for comparison value (switches on grain AND comparison)
    comparison_cases = ["CASE"]

    # Add selected grain cases
    for comparison in pop_config.comparisons:
        comp_cond = f"{{% parameter comparison_period %}} = '{comparison.value}'"
        grain_cond = "{% parameter period_grain %} = 'selected'"
        measure_ref = f"${{{base_name}_{comparison.value}_measure}}"
        comparison_cases.append(f"  WHEN {grain_cond} AND {comp_cond} THEN {measure_ref}")

    # Add grain x comparison cases
    for grain in pop_config.grains:
        if grain == PopGrain.SELECTED:
            continue
        grain_cond = f"{{% parameter period_grain %}} = '{grain.value}'"

        for comparison in pop_config.comparisons:
            comp_cond = f"{{% parameter comparison_period %}} = '{comparison.value}'"
            measure_ref = f"${{{base_name}_{grain.value}_{comparison.value}_measure}}"
            comparison_cases.append(f"  WHEN {grain_cond} AND {comp_cond} THEN {measure_ref}")

    comparison_cases.append("END")

    comparison_measure: dict[str, Any] = {
        "name": f"{base_name}_comparison",
        "group_label": label,
        "label": f"{label} (Comp)",
        "type": "number",
        "sql": "\n".join(comparison_cases),
        "required_fields": [base_name],
    }
    if format_name:
        comparison_measure["value_format_name"] = format_name
    measures.append(comparison_measure)

    # Delta (change)
    change_measure: dict[str, Any] = {
        "name": f"{base_name}_change",
        "group_label": label,
        "label": f"{label} \u0394",  # Greek capital delta
        "type": "number",
        "sql": f"${{{base_name}}} - ${{{base_name}_comparison}}",
        "required_fields": [base_name, f"{base_name}_comparison"],
    }
    if format_name:
        change_measure["value_format_name"] = format_name
    measures.append(change_measure)

    # Percent change
    measures.append({
        "name": f"{base_name}_pct_change",
        "group_label": label,
        "label": f"{label} %\u0394",
        "type": "number",
        "sql": f"(${{{base_name}}} - ${{{base_name}_comparison}}) / NULLIF(${{{base_name}_comparison}}, 0)",
        "required_fields": [base_name, f"{base_name}_comparison"],
        "value_format_name": "percent_1",
    })

    return measures
```

### Tests for DTL-043

```python
class TestPopVisibleMeasures:
    """Tests for visible PoP measure generation."""

    def test_measure_group_created(self) -> None:
        """Test four measures created with same group_label."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM, label="Revenue")
        config = PopConfig(enabled=True, format="usd")

        measures = generator._generate_pop_visible_measures(measure, config)

        assert len(measures) == 4
        for m in measures:
            assert m["group_label"] == "Revenue"

    def test_current_measure_case_statement(self) -> None:
        """Test current measure has correct CASE statement."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM)
        config = PopConfig(enabled=True, grains=[PopGrain.MTD, PopGrain.YTD])

        measures = generator._generate_pop_visible_measures(measure, config)

        current = next(m for m in measures if m["name"] == "revenue")
        assert "{% parameter period_grain %}" in current["sql"]
        assert "${revenue_measure}" in current["sql"]
        assert "${revenue_mtd_measure}" in current["sql"]

    def test_pct_change_nullif_protection(self) -> None:
        """Test percent change has NULLIF for division by zero."""
        generator = LookMLGenerator()
        measure = Measure(name="revenue", agg=AggregationType.SUM)
        config = PopConfig(enabled=True)

        measures = generator._generate_pop_visible_measures(measure, config)

        pct = next(m for m in measures if m["name"] == "revenue_pct_change")
        assert "NULLIF" in pct["sql"]
        assert pct["value_format_name"] == "percent_1"
```

---

## DTL-044: Wire PoP into Generation Pipeline

### File: `src/dbt_to_lookml/generators/lookml.py`

#### Modify `generate_view()` Method

Add PoP processing after timezone variant handling (around line 860):

```python
def generate_view(
    self,
    model: SemanticModel,
    required_measures: set[str] | None = None,
    usage_map: dict[str, dict[str, Any]] | None = None,
) -> dict:
    """Generate LookML view dict with PoP support."""

    # ... existing code up to timezone variant processing ...

    # Extract the view from the wrapper dict
    if "views" not in base_view_dict or not base_view_dict["views"]:
        return base_view_dict

    view_dict = base_view_dict["views"][0]

    # ... existing timezone variant processing ...

    # PoP processing - check for pop-enabled measures
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

        if date_dim:
            date_filter = first_pop.date_filter or f"{date_dim}_date"

            # Generate PoP dimensions (shared across all PoP measures)
            pop_dims = self._generate_pop_dimensions(first_pop, date_dim, date_filter)

            # Generate PoP parameters (shared)
            pop_params = self._generate_pop_parameters(first_pop)

            # Add dimensions to view
            if "dimensions" not in view_dict:
                view_dict["dimensions"] = []
            view_dict["dimensions"].extend(pop_dims)

            # Add parameters (before other parameters if any)
            if pop_params:
                existing_params = view_dict.get("parameter", [])
                if not isinstance(existing_params, list):
                    existing_params = [existing_params] if existing_params else []
                view_dict["parameter"] = pop_params + existing_params

            # Initialize measures list if not present
            if "measures" not in view_dict:
                view_dict["measures"] = []

            # Generate hidden and visible measures for each PoP measure
            for measure in pop_measures:
                pop_config = measure.config.meta.pop

                # Hidden measures
                hidden_measures = self._generate_pop_hidden_measures(measure, pop_config)
                view_dict["measures"].extend(hidden_measures)

                # Visible measures
                visible_measures = self._generate_pop_visible_measures(measure, pop_config)
                view_dict["measures"].extend(visible_measures)

    # ... rest of existing code ...

    return base_view_dict
```

### Tests for DTL-044

```python
class TestPopPipelineIntegration:
    """Tests for PoP pipeline integration."""

    def test_end_to_end_generation(self) -> None:
        """Test complete PoP view generation."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    expr="amount",
                    config=Config(
                        meta=ConfigMeta(
                            pop=PopConfig(
                                enabled=True,
                                grains=[PopGrain.MTD],
                                comparisons=[PopComparison.PY],
                            )
                        )
                    ),
                )
            ],
        )

        result = generator.generate_view(model)

        view = result["views"][0]

        # Check dimensions exist
        dim_names = {d["name"] for d in view.get("dimensions", [])}
        assert "is_mtd" in dim_names
        assert "is_prior_year" in dim_names

        # Check parameters exist
        param_names = {p["name"] for p in view.get("parameter", [])}
        assert "period_grain" in param_names
        assert "comparison_period" in param_names

        # Check measures exist
        measure_names = {m["name"] for m in view.get("measures", [])}
        assert "revenue_measure" in measure_names
        assert "revenue" in measure_names
        assert "revenue_comparison" in measure_names

    def test_backward_compatibility(self) -> None:
        """Test models without PoP are unchanged."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            measures=[
                Measure(name="revenue", agg=AggregationType.SUM, expr="amount")
            ],
        )

        result = generator.generate_view(model)

        view = result["views"][0]
        dim_names = {d["name"] for d in view.get("dimensions", [])}

        # No PoP dimensions should be present
        assert "is_mtd" not in dim_names
        assert "is_prior_period" not in dim_names

    def test_mixed_pop_non_pop_measures(self) -> None:
        """Test model with both PoP and non-PoP measures."""
        generator = LookMLGenerator()
        model = SemanticModel(
            name="rentals",
            model="ref('rentals')",
            defaults={"agg_time_dimension": "selected_date"},
            measures=[
                Measure(name="count", agg=AggregationType.COUNT),  # No PoP
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    config=Config(
                        meta=ConfigMeta(pop=PopConfig(enabled=True))
                    ),
                ),
            ],
        )

        result = generator.generate_view(model)

        # Both measures should exist, only revenue has PoP variants
        view = result["views"][0]
        measure_names = {m["name"] for m in view.get("measures", [])}
        assert "count_measure" in measure_names or "count" in measure_names
        assert "revenue_measure" in measure_names
        assert "revenue_pct_change" in measure_names
        # count should NOT have PoP variants
        assert "count_pct_change" not in measure_names
```

---

## DTL-045: Test Suite Organization

### Test Files Structure

```
src/tests/unit/
├── test_pop_config.py       # DTL-038 tests
├── test_pop_parser.py       # DTL-039 tests
├── test_pop_generator.py    # DTL-040, 041, 042, 043 tests
└── test_pop_integration.py  # DTL-044 tests

src/tests/integration/
└── test_pop_e2e.py          # Full end-to-end tests
```

### Integration Test Example

```python
"""Integration tests for PoP functionality."""

import tempfile
from pathlib import Path

import pytest

from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.generators.lookml import LookMLGenerator


class TestPopEndToEnd:
    """End-to-end tests for PoP feature."""

    def test_full_pipeline_yaml_to_lookml(self) -> None:
        """Test complete pipeline from YAML to LookML output."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    dimensions:
      - name: selected_date
        type: time
        expr: rental_date
    measures:
      - name: revenue
        agg: sum
        expr: checkout_amount
        config:
          meta:
            pop:
              enabled: true
              grains: [mtd, ytd]
              comparisons: [pp, py]
              format: usd
"""
        # Parse
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            models = parser.parse_file(Path(f.name))

        # Generate
        generator = LookMLGenerator(schema="gold")
        files = generator.generate(models)

        # Verify output
        assert "rentals.view.lkml" in files
        content = files["rentals.view.lkml"]

        # Check key elements
        assert "is_mtd" in content
        assert "is_ytd" in content
        assert "is_prior_period" in content
        assert "period_window" in content
        assert "period_grain" in content
        assert "revenue_comparison" in content
        assert "NULLIF" in content  # Division protection
```

---

## Quality Gates

Before merging:

```bash
# Run all tests
make test

# Check coverage
make test-coverage
# Target: 95%+ on new PoP code

# Type checking
make type-check

# Linting
make lint

# Format
make format
```

## Implementation Checklist

- [ ] DTL-038: PopConfig, PopGrain, PopComparison, PopWindow enums
- [ ] DTL-039: `_parse_pop_config()` with resolution
- [ ] DTL-040: `_generate_pop_dimensions()`
- [ ] DTL-041: `_generate_pop_parameters()`
- [ ] DTL-042: `_generate_pop_hidden_measures()`
- [ ] DTL-043: `_generate_pop_visible_measures()`
- [ ] DTL-044: Integration in `generate_view()`
- [ ] DTL-045: All test files created with passing tests
- [ ] All quality gates pass
- [ ] PR created and ready for review
