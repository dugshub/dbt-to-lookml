---
id: DTL-033-strategy
issue: DTL-033
title: "Implementation Strategy: Add group_item_label support for cleaner timeframe labels"
created: 2025-11-19
status: approved
---

# DTL-033: Implementation Strategy

## Overview

This strategy outlines the implementation approach for adding optional `group_item_label` support to time dimension_groups in LookML generation. This feature uses Liquid templating to display cleaner timeframe labels (e.g., "Date", "Month", "Quarter") instead of repetitive full names (e.g., "Rental Created Date", "Rental Created Month", "Rental Created Quarter").

## Background

### Current State

Time dimension_groups currently generate fields like:
- `rental_date_date` → displays as "Rental Date Date"
- `rental_date_month` → displays as "Rental Date Month"
- `rental_date_quarter` → displays as "Rental Date Quarter"

The generated LookML does not include `group_item_label`, so field labels are derived from the full field name.

### Desired State

With `group_item_label` enabled, the same fields would display as:
- `rental_date_date` → displays as "Date"
- `rental_date_month` → displays as "Month"
- `rental_date_quarter` → displays as "Quarter"

This works in conjunction with DTL-032's `group_label` to create hierarchical organization:
```
Time Dimensions
  Rental Date
    Date
    Month
    Quarter
    Week
    Year
```

## Technical Approach

### 1. LookML Liquid Templating Pattern

LookML supports Liquid templating for dynamic label generation. The `group_item_label` parameter uses the special variable `_field._name` to access the full field name.

**Liquid Template Design:**

```lookml
dimension_group: rental_date {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.booking_date ;;
  group_item_label: "{% assign tf = _field._name | remove: 'rental_date_' | replace: '_', ' ' | capitalize %}{{ tf }}"
}
```

**Template Breakdown:**
1. `_field._name` → Full field name (e.g., "rental_date_month")
2. `remove: 'rental_date_'` → Remove the dimension group prefix (e.g., "month")
3. `replace: '_', ' '` → Replace underscores with spaces (e.g., "month")
4. `capitalize` → Capitalize first letter (e.g., "Month")
5. `{{ tf }}` → Output the transformed value

**Special Cases:**
- `rental_date_raw` → "Raw" (for raw timestamp access)
- `rental_date_time` → "Time" (for hour/minute granularity)
- `rental_date_date` → "Date"

### 2. Configuration Architecture

The feature follows the existing multi-level configuration pattern used for `convert_tz`:

**Configuration Precedence (highest to lowest):**

1. **Dimension-level metadata** (in semantic model YAML)
2. **Generator parameter** (in Python code)
3. **CLI flag** (command-line argument)
4. **Default** (False, disabled for backward compatibility)

**Example Configurations:**

```yaml
# Dimension-level override (highest priority)
dimensions:
  - name: created_at
    type: time
    config:
      meta:
        use_group_item_label: true  # Enable for this dimension only
```

```python
# Generator parameter
generator = LookMLGenerator(
    view_prefix="stg_",
    use_group_item_label=True  # Enable for all dimensions
)
```

```bash
# CLI flag
dbt-to-lookml generate -i semantic_models/ -o build/ --use-group-item-label
```

### 3. Schema Changes

**File:** `src/dbt_to_lookml/schemas/config.py`

Add `use_group_item_label` to the `ConfigMeta` model:

```python
class ConfigMeta(BaseModel):
    """Metadata configuration for semantic model elements."""

    # ... existing fields ...
    convert_tz: bool | None = None
    use_group_item_label: bool | None = None  # NEW FIELD
    # ... rest of fields ...
```

This allows dimension-level configuration via YAML:

```yaml
dimensions:
  - name: booking_date
    type: time
    config:
      meta:
        use_group_item_label: true
```

### 4. Generator Changes

**File:** `src/dbt_to_lookml/generators/lookml.py`

**4.1. Add Generator Parameter**

Update `LookMLGenerator.__init__()`:

```python
def __init__(
    self,
    # ... existing parameters ...
    convert_tz: bool | None = None,
    use_bi_field_filter: bool = False,
    use_group_item_label: bool = False,  # NEW PARAMETER
    fact_models: list[str] | None = None,
) -> None:
    """Initialize the generator.

    Args:
        # ... existing args ...
        use_group_item_label: Whether to add group_item_label to dimension_groups
            for cleaner timeframe labels. When enabled, timeframes display as
            "Date", "Month", etc. instead of repeating the dimension group name.
            Default: False (backward compatible).
    """
    # ... existing initialization ...
    self.use_group_item_label = use_group_item_label
```

**4.2. Propagate to Model Generation**

Update `SemanticModel.to_lookml_dict()` call in `_generate_view_lookml()`:

```python
view_dict = prefixed_model.to_lookml_dict(
    schema=self.schema,
    convert_tz=self.convert_tz,
    use_group_item_label=self.use_group_item_label  # NEW PARAMETER
)
```

### 5. Semantic Layer Schema Changes

**File:** `src/dbt_to_lookml/schemas/semantic_layer.py`

**5.1. Update SemanticModel.to_lookml_dict()**

Add `use_group_item_label` parameter and pass to dimension conversion:

```python
def to_lookml_dict(
    self,
    schema: str = "",
    convert_tz: bool | None = None,
    use_group_item_label: bool | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
    """Convert entire semantic model to lkml views format.

    Args:
        schema: Optional database schema name to prepend to table name.
        convert_tz: Optional timezone conversion setting.
        use_group_item_label: Optional group_item_label setting for
            dimension_groups. Passed to time dimensions as default.
    """
    # ... existing code ...

    for dim in self.dimensions:
        if dim.type == DimensionType.TIME:
            dim_dict = dim.to_lookml_dict(
                default_convert_tz=convert_tz,
                default_use_group_item_label=use_group_item_label  # NEW PARAMETER
            )
        else:
            dim_dict = dim.to_lookml_dict()

        # ... rest of logic ...
```

**5.2. Update Dimension.to_lookml_dict()**

Add parameter to time dimension handling:

```python
def to_lookml_dict(
    self,
    default_convert_tz: bool | None = None,
    default_use_group_item_label: bool | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
    """Convert dimension to LookML format.

    Args:
        default_convert_tz: Optional default timezone conversion setting.
        default_use_group_item_label: Optional default group_item_label setting.
    """
    if self.type == DimensionType.TIME:
        return self._to_dimension_group_dict(
            default_convert_tz=default_convert_tz,
            default_use_group_item_label=default_use_group_item_label  # NEW PARAMETER
        )
    else:
        return self._to_dimension_dict()
```

**5.3. Update Dimension._to_dimension_group_dict()**

This is where the core logic is implemented:

```python
def _to_dimension_group_dict(
    self,
    default_convert_tz: bool | None = None,
    default_use_group_item_label: bool | None = None,  # NEW PARAMETER
) -> dict[str, Any]:
    """Convert time dimension to LookML dimension_group.

    Args:
        default_convert_tz: Default timezone conversion setting.
        default_use_group_item_label: Default group_item_label setting.
            When True, adds Liquid template to display clean timeframe labels.
    """
    timeframes = self._get_timeframes()

    result: dict[str, Any] = {
        "name": self.name,
        "type": "time",
        "timeframes": timeframes,
        "sql": self.expr or f"${{TABLE}}.{self.name}",
    }

    # ... existing description, label, hierarchy labels ...

    # Add convert_tz (existing logic)
    # ... existing convert_tz logic ...

    # Add group_item_label if enabled (NEW LOGIC)
    # Determine use_group_item_label with three-tier precedence:
    # 1. Dimension-level meta.use_group_item_label (highest)
    # 2. default_use_group_item_label parameter
    # 3. Hardcoded default: False
    use_group_item_label = False
    if default_use_group_item_label is not None:
        use_group_item_label = default_use_group_item_label
    if (self.config and self.config.meta and
        self.config.meta.use_group_item_label is not None):
        use_group_item_label = self.config.meta.use_group_item_label

    if use_group_item_label:
        # Generate Liquid template for group_item_label
        # Template extracts timeframe name from field name
        result["group_item_label"] = (
            "{% assign tf = _field._name | remove: '" + self.name + "_' | "
            "replace: '_', ' ' | capitalize %}{{ tf }}"
        )

    # ... existing hidden parameter logic ...

    return result
```

### 6. CLI Changes

**File:** `src/dbt_to_lookml/__main__.py`

Add mutually exclusive CLI flags similar to `convert_tz`:

```python
@cli.command(cls=RichCommand)
@click.option(
    "-i", "--input-dir",
    # ... existing options ...
)
# ... other existing options ...
@click.option(
    "--use-group-item-label",
    is_flag=True,
    default=False,
    help="Add group_item_label to dimension_groups for cleaner timeframe labels "
         "(e.g., 'Date', 'Month' instead of 'Rental Date', 'Rental Month')",
)
@click.option(
    "--no-group-item-label",
    is_flag=True,
    default=False,
    help="Explicitly disable group_item_label (useful to override defaults)",
)
def generate(
    input_dir: str,
    # ... other params ...
    use_group_item_label: bool,
    no_group_item_label: bool,
) -> None:
    """Generate LookML files from semantic models."""

    # Validate mutually exclusive flags
    if use_group_item_label and no_group_item_label:
        raise click.UsageError(
            "Cannot use both --use-group-item-label and --no-group-item-label"
        )

    # Determine group_item_label setting
    group_item_label_setting = None
    if use_group_item_label:
        group_item_label_setting = True
    elif no_group_item_label:
        group_item_label_setting = False
    # else: None (use default/dimension-level settings)

    # ... existing parsing logic ...

    generator = LookMLGenerator(
        view_prefix=view_prefix,
        explore_prefix=explore_prefix,
        # ... other params ...
        convert_tz=convert_tz_setting,
        use_group_item_label=group_item_label_setting,  # NEW PARAMETER
        fact_models=fact_models_list,
    )

    # ... rest of generation logic ...
```

## Testing Strategy

### 7.1 Unit Tests

**File:** `src/tests/unit/test_schemas.py`

Add tests to `TestDimension` class:

```python
class TestDimension:
    """Tests for Dimension model."""

    # ... existing tests ...

    def test_dimension_group_with_group_item_label_enabled(self) -> None:
        """Test group_item_label is added when enabled via parameter."""
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        result = dimension._to_dimension_group_dict(
            default_use_group_item_label=True
        )

        assert "group_item_label" in result
        expected_template = (
            "{% assign tf = _field._name | remove: 'created_at_' | "
            "replace: '_', ' ' | capitalize %}{{ tf }}"
        )
        assert result["group_item_label"] == expected_template

    def test_dimension_group_with_group_item_label_disabled(self) -> None:
        """Test group_item_label is not added when disabled (default)."""
        dimension = Dimension(
            name="updated_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        result = dimension._to_dimension_group_dict(
            default_use_group_item_label=False
        )

        assert "group_item_label" not in result

    def test_dimension_group_item_label_metadata_override(self) -> None:
        """Test dimension-level metadata overrides generator default."""
        dimension = Dimension(
            name="shipped_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(use_group_item_label=True)  # Override
            ),
        )

        # Even with False default, metadata override should enable it
        result = dimension._to_dimension_group_dict(
            default_use_group_item_label=False
        )

        assert "group_item_label" in result

    def test_dimension_group_item_label_metadata_disable_override(self) -> None:
        """Test dimension-level metadata can disable when generator enables."""
        dimension = Dimension(
            name="deleted_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(use_group_item_label=False)  # Override
            ),
        )

        # Even with True default, metadata override should disable it
        result = dimension._to_dimension_group_dict(
            default_use_group_item_label=True
        )

        assert "group_item_label" not in result

    def test_dimension_group_item_label_default_none(self) -> None:
        """Test no group_item_label when parameter is None (default)."""
        dimension = Dimension(
            name="processed_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        result = dimension._to_dimension_group_dict()

        assert "group_item_label" not in result

    def test_group_item_label_template_correctness(self) -> None:
        """Test Liquid template generates correct structure."""
        dimension = Dimension(
            name="rental_date",
            type=DimensionType.TIME,
        )

        result = dimension._to_dimension_group_dict(
            default_use_group_item_label=True
        )

        template = result["group_item_label"]

        # Verify template structure
        assert "{% assign tf = _field._name" in template
        assert "remove: 'rental_date_'" in template
        assert "replace: '_', ' '" in template
        assert "capitalize" in template
        assert "{{ tf }}" in template
```

**File:** `src/tests/unit/test_lookml_generator.py`

Add generator-level tests:

```python
class TestLookMLGenerator:
    """Tests for LookMLGenerator."""

    # ... existing tests ...

    def test_generator_use_group_item_label_parameter(self) -> None:
        """Test use_group_item_label parameter is stored."""
        generator = LookMLGenerator(use_group_item_label=True)

        assert generator.use_group_item_label is True

    def test_generator_use_group_item_label_default(self) -> None:
        """Test use_group_item_label defaults to False."""
        generator = LookMLGenerator()

        assert generator.use_group_item_label is False

    def test_generator_propagates_group_item_label_to_views(
        self, sample_time_dimension_model: SemanticModel
    ) -> None:
        """Test generator propagates use_group_item_label to view generation."""
        generator = LookMLGenerator(use_group_item_label=True)

        files = generator.generate([sample_time_dimension_model])

        # Get the generated view content
        view_content = files[f"{sample_time_dimension_model.name}.view.lkml"]

        # Verify group_item_label is present
        assert "group_item_label:" in view_content
        assert "_field._name" in view_content
```

### 7.2 Integration Tests

**File:** `src/tests/integration/test_group_item_label.py` (NEW FILE)

```python
"""Integration tests for group_item_label feature."""

from pathlib import Path

import lkml
import pytest

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser


class TestGroupItemLabelIntegration:
    """Integration tests for group_item_label in dimension_groups."""

    def test_group_item_label_with_cli_flag_enabled(
        self, tmp_path: Path, sample_semantic_models_dir: Path
    ) -> None:
        """Test group_item_label generation with CLI flag enabled."""
        parser = DbtParser()
        models = parser.parse_directory(str(sample_semantic_models_dir))

        generator = LookMLGenerator(
            use_group_item_label=True,
            schema="public",
        )

        files = generator.generate(models)

        # Verify all dimension_groups have group_item_label
        for filename, content in files.items():
            if filename.endswith(".view.lkml"):
                parsed = lkml.load(content)
                views = parsed.get("views", [])

                for view in views:
                    dimension_groups = view.get("dimension_groups", [])

                    for dg in dimension_groups:
                        assert "group_item_label" in dg, (
                            f"dimension_group {dg['name']} in {filename} "
                            f"missing group_item_label"
                        )

                        # Verify template structure
                        template = dg["group_item_label"]
                        assert "_field._name" in template
                        assert "remove:" in template
                        assert "capitalize" in template

    def test_group_item_label_with_cli_flag_disabled(
        self, tmp_path: Path, sample_semantic_models_dir: Path
    ) -> None:
        """Test no group_item_label when CLI flag disabled (default)."""
        parser = DbtParser()
        models = parser.parse_directory(str(sample_semantic_models_dir))

        generator = LookMLGenerator(
            use_group_item_label=False,
            schema="public",
        )

        files = generator.generate(models)

        # Verify no dimension_groups have group_item_label
        for filename, content in files.items():
            if filename.endswith(".view.lkml"):
                parsed = lkml.load(content)
                views = parsed.get("views", [])

                for view in views:
                    dimension_groups = view.get("dimension_groups", [])

                    for dg in dimension_groups:
                        assert "group_item_label" not in dg, (
                            f"dimension_group {dg['name']} in {filename} "
                            f"unexpectedly has group_item_label"
                        )

    def test_group_item_label_dimension_level_override(
        self, tmp_path: Path
    ) -> None:
        """Test dimension-level metadata overrides generator setting."""
        from dbt_to_lookml.schemas import (
            Config,
            ConfigMeta,
            Dimension,
            DimensionType,
            Entity,
            SemanticModel,
        )

        # Create model with mixed group_item_label settings
        model = SemanticModel(
            name="test_model",
            model="ref('test_table')",
            entities=[
                Entity(name="id", type="primary")
            ],
            dimensions=[
                # This one enables group_item_label via metadata
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    config=Config(
                        meta=ConfigMeta(use_group_item_label=True)
                    ),
                ),
                # This one uses generator default (False)
                Dimension(
                    name="updated_at",
                    type=DimensionType.TIME,
                ),
                # This one explicitly disables via metadata
                Dimension(
                    name="deleted_at",
                    type=DimensionType.TIME,
                    config=Config(
                        meta=ConfigMeta(use_group_item_label=False)
                    ),
                ),
            ],
        )

        # Generator has use_group_item_label=False (default)
        generator = LookMLGenerator(use_group_item_label=False)

        files = generator.generate([model])
        content = files["test_model.view.lkml"]
        parsed = lkml.load(content)

        dimension_groups = parsed["views"][0]["dimension_groups"]
        dg_dict = {dg["name"]: dg for dg in dimension_groups}

        # created_at should have group_item_label (metadata override)
        assert "group_item_label" in dg_dict["created_at"]

        # updated_at should NOT have group_item_label (uses generator default)
        assert "group_item_label" not in dg_dict["updated_at"]

        # deleted_at should NOT have group_item_label (metadata override)
        assert "group_item_label" not in dg_dict["deleted_at"]

    def test_group_item_label_liquid_template_validation(
        self, tmp_path: Path
    ) -> None:
        """Test that generated Liquid templates are syntactically valid."""
        from dbt_to_lookml.schemas import (
            Dimension,
            DimensionType,
            Entity,
            SemanticModel,
        )

        # Test various dimension names to ensure template works correctly
        test_cases = [
            "created_at",
            "booking_date",
            "rental_timestamp",
            "user_signup_datetime",
        ]

        for dim_name in test_cases:
            model = SemanticModel(
                name="test_model",
                model="ref('test_table')",
                entities=[Entity(name="id", type="primary")],
                dimensions=[
                    Dimension(
                        name=dim_name,
                        type=DimensionType.TIME,
                    )
                ],
            )

            generator = LookMLGenerator(use_group_item_label=True)
            files = generator.generate([model])

            content = files["test_model.view.lkml"]

            # Verify template contains dimension name
            assert f"remove: '{dim_name}_'" in content

            # Verify LookML is valid
            parsed = lkml.load(content)
            assert parsed is not None
```

### 7.3 Golden Tests

**File:** `src/tests/test_golden.py`

Add new golden test case:

```python
class TestGoldenFiles:
    """Tests that verify golden file outputs."""

    # ... existing tests ...

    def test_golden_group_item_label_disabled_by_default(
        self, golden_dir: Path
    ) -> None:
        """Test that golden files don't have group_item_label (backward compat).

        Since use_group_item_label defaults to False, golden files should
        not contain group_item_label unless explicitly enabled in test data.
        """
        golden_files = list(golden_dir.glob("expected_*.view.lkml"))
        assert len(golden_files) > 0, "No golden view files found"

        for golden_file in golden_files:
            content = golden_file.read_text()

            # Golden files should not have group_item_label (feature disabled)
            assert "group_item_label:" not in content, (
                f"Golden file {golden_file.name} unexpectedly has "
                f"group_item_label (feature should be opt-in)"
            )
```

### 7.4 CLI Tests

**File:** `src/tests/test_cli.py`

Add CLI flag tests:

```python
class TestCLIGenerate:
    """Tests for generate command."""

    # ... existing tests ...

    def test_generate_with_use_group_item_label_flag(
        self, runner: CliRunner, tmp_path: Path, sample_models_dir: Path
    ) -> None:
        """Test --use-group-item-label flag enables feature."""
        output_dir = tmp_path / "output"

        result = runner.invoke(
            cli,
            [
                "generate",
                "-i", str(sample_models_dir),
                "-o", str(output_dir),
                "-s", "public",
                "--use-group-item-label",
            ],
        )

        assert result.exit_code == 0

        # Check generated files contain group_item_label
        view_files = list(output_dir.glob("*.view.lkml"))
        assert len(view_files) > 0

        for view_file in view_files:
            content = view_file.read_text()
            if "dimension_group:" in content:
                assert "group_item_label:" in content

    def test_generate_without_group_item_label_flag(
        self, runner: CliRunner, tmp_path: Path, sample_models_dir: Path
    ) -> None:
        """Test default behavior does not add group_item_label."""
        output_dir = tmp_path / "output"

        result = runner.invoke(
            cli,
            [
                "generate",
                "-i", str(sample_models_dir),
                "-o", str(output_dir),
                "-s", "public",
            ],
        )

        assert result.exit_code == 0

        # Check generated files do not contain group_item_label
        view_files = list(output_dir.glob("*.view.lkml"))

        for view_file in view_files:
            content = view_file.read_text()
            assert "group_item_label:" not in content

    def test_generate_mutually_exclusive_group_item_label_flags(
        self, runner: CliRunner, tmp_path: Path, sample_models_dir: Path
    ) -> None:
        """Test that --use-group-item-label and --no-group-item-label are exclusive."""
        output_dir = tmp_path / "output"

        result = runner.invoke(
            cli,
            [
                "generate",
                "-i", str(sample_models_dir),
                "-o", str(output_dir),
                "-s", "public",
                "--use-group-item-label",
                "--no-group-item-label",
            ],
        )

        assert result.exit_code != 0
        assert "Cannot use both" in result.output
```

## Implementation Steps

### Phase 1: Schema Foundation (Est. 2 hours)

1. **Update ConfigMeta schema** (`schemas/config.py`)
   - Add `use_group_item_label: bool | None = None` field
   - Update docstrings with examples
   - Run unit tests: `pytest src/tests/unit/test_schemas.py::TestConfig -xvs`

2. **Verify schema changes**
   - Create test semantic model YAML with `use_group_item_label: true`
   - Parse and verify the field is captured correctly

### Phase 2: Core Logic Implementation (Est. 3 hours)

3. **Update Dimension._to_dimension_group_dict()** (`schemas/semantic_layer.py`)
   - Add `default_use_group_item_label` parameter
   - Implement three-tier precedence logic
   - Generate Liquid template when enabled
   - Write comprehensive unit tests

4. **Update Dimension.to_lookml_dict()**
   - Add parameter pass-through to `_to_dimension_group_dict()`
   - Update docstring

5. **Update SemanticModel.to_lookml_dict()**
   - Add `use_group_item_label` parameter
   - Propagate to dimension conversion
   - Update docstring

### Phase 3: Generator Integration (Est. 2 hours)

6. **Update LookMLGenerator** (`generators/lookml.py`)
   - Add `use_group_item_label` to `__init__()`
   - Store as instance variable
   - Propagate to `_generate_view_lookml()`
   - Update docstrings

### Phase 4: CLI Integration (Est. 2 hours)

7. **Update CLI** (`__main__.py`)
   - Add `--use-group-item-label` flag
   - Add `--no-group-item-label` flag
   - Implement mutual exclusion validation
   - Wire up to generator instantiation

### Phase 5: Testing (Est. 4 hours)

8. **Write unit tests** (see section 7.1)
   - Test schema changes
   - Test dimension logic
   - Test generator parameter
   - Target: 95%+ branch coverage

9. **Write integration tests** (see section 7.2)
   - Create `test_group_item_label.py`
   - Test end-to-end generation
   - Test precedence rules
   - Test Liquid template correctness

10. **Update golden tests** (see section 7.3)
    - Verify backward compatibility
    - Ensure no group_item_label in existing golden files

11. **Write CLI tests** (see section 7.4)
    - Test flag behavior
    - Test mutual exclusion
    - Test generated output

### Phase 6: Validation (Est. 1 hour)

12. **Run full test suite**
    - `make test-full`
    - Verify 95%+ coverage maintained
    - Fix any failing tests

13. **Manual testing**
    - Generate LookML with flag enabled
    - Verify Liquid template syntax
    - Test in Looker if available (optional)

## Edge Cases and Considerations

### 1. Dimension Names with Underscores

**Scenario:** Dimension name is `created_at_utc`

**Liquid Template:**
```
remove: 'created_at_utc_'
```

**Field Examples:**
- `created_at_utc_date` → "Date"
- `created_at_utc_month` → "Month"

**Result:** Works correctly because we remove the entire dimension name prefix.

### 2. Special Timeframes

**Scenario:** Hour granularity includes `time` and `hour` timeframes

**Field Examples:**
- `booking_timestamp_time` → "Time"
- `booking_timestamp_hour` → "Hour"
- `booking_timestamp_date` → "Date"

**Result:** Template works for all timeframe types.

### 3. Multi-word Timeframes (Future)

**Scenario:** Looker adds new timeframe like `fiscal_quarter`

**Current Template:** Would produce "Fiscal quarter"

**Improvement:** Could enhance template with `split` and `map: 'capitalize'` if needed in future.

### 4. Interaction with group_label (DTL-032)

Both `group_label` and `group_item_label` can coexist:

```lookml
dimension_group: created_at {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.created_at ;;
  group_label: "Time Dimensions"  # From DTL-032
  group_item_label: "{% assign tf = ... %}{{ tf }}"  # From DTL-033
}
```

**Result:** Creates hierarchical organization:
```
Time Dimensions
  Created At
    Date
    Month
    Quarter
```

### 5. Backward Compatibility

**Key Principle:** Feature is opt-in (disabled by default)

- Existing code without flag → No change in output
- Golden files → No group_item_label present
- Users must explicitly enable via flag or metadata

## Risks and Mitigations

### Risk 1: Liquid Template Syntax Errors

**Mitigation:**
- Write comprehensive integration tests
- Test with lkml library parsing
- Validate against LookML spec
- Consider manual testing in Looker instance

### Risk 2: Interaction with Other Features

**Mitigation:**
- Test alongside `group_label` (DTL-032)
- Test with `convert_tz` configuration
- Test with `hidden` parameter
- Ensure precedence logic is clear and documented

### Risk 3: Breaking Changes to Golden Files

**Mitigation:**
- Feature disabled by default
- Golden files should not change unless test data explicitly enables feature
- Add explicit test for backward compatibility

### Risk 4: Performance Impact

**Mitigation:**
- Liquid template is static string generation (no runtime cost)
- No performance impact expected
- Performance tests already cover dimension generation

## Success Criteria

- [ ] `use_group_item_label` parameter added to `ConfigMeta` schema
- [ ] `use_group_item_label` parameter added to `LookMLGenerator.__init__()`
- [ ] `--use-group-item-label` CLI flag implemented
- [ ] `--no-group-item-label` CLI flag implemented (mutual exclusion)
- [ ] Three-tier precedence logic working (metadata > generator > CLI > default)
- [ ] Liquid template correctly generates for all dimension names
- [ ] All unit tests pass (95%+ coverage maintained)
- [ ] All integration tests pass
- [ ] Golden tests verify backward compatibility
- [ ] CLI tests verify flag behavior
- [ ] Documentation updated in CLAUDE.md
- [ ] No breaking changes to existing functionality

## Documentation Updates

**CLAUDE.md sections to update:**

1. **"Important Implementation Details"** - Add section on `group_item_label` similar to timezone conversion:

```markdown
### Field Label Customization (group_item_label)

Dimension_groups support label customization using the `group_item_label` parameter with Liquid templating.
This feature enables cleaner timeframe labels that display just the timeframe name (e.g., "Date", "Month")
instead of repeating the full dimension name.

#### Configuration Levels (Precedence: Highest to Lowest)

1. **Dimension Metadata Override** (Highest priority)
   ```yaml
   dimensions:
     - name: created_at
       type: time
       config:
         meta:
           use_group_item_label: yes
   ```

2. **Generator Parameter**
   ```python
   generator = LookMLGenerator(use_group_item_label=True)
   ```

3. **CLI Flag**
   ```bash
   dbt-to-lookml generate -i models -o lookml --use-group-item-label
   ```

4. **Default** (Lowest priority): `False` - Feature disabled for backward compatibility

#### Generated LookML

With `use_group_item_label: true`:

```lookml
dimension_group: rental_date {
  type: time
  timeframes: [date, week, month, quarter, year]
  sql: ${TABLE}.booking_date ;;
  group_item_label: "{% assign tf = _field._name | remove: 'rental_date_' | replace: '_', ' ' | capitalize %}{{ tf }}"
  convert_tz: no
}
```

This uses Liquid templating to extract the timeframe name from the generated field name.
```

2. **Update CLI examples** with `--use-group-item-label` flag examples

## Dependencies

- **DTL-032 (group_label)**: Soft dependency - features work independently but complement each other
- **lkml library**: Already in use for LookML generation and validation
- **pydantic**: Already in use for schema validation

## Estimated Effort

- **Total: 14 hours** (1.75 days)
  - Schema changes: 2 hours
  - Core logic: 3 hours
  - Generator integration: 2 hours
  - CLI integration: 2 hours
  - Testing: 4 hours
  - Validation: 1 hour

## Rollout Plan

1. **Implementation:** Complete all phases in order
2. **Testing:** Run full test suite, verify coverage
3. **Documentation:** Update CLAUDE.md with examples
4. **Review:** Code review focusing on precedence logic and tests
5. **Merge:** Merge to main after approval
6. **Release:** Include in next minor version (backward compatible)

## Next Steps

After DTL-033 is complete:

1. **DTL-034:** Update test suite for time dimension organization features (comprehensive testing)
2. **DTL-035:** Update documentation for time dimension organization (user-facing docs)
3. **DTL-029 Epic:** Complete remaining sub-issues to finish the epic

## References

- Issue: `.tasks/issues/DTL-033.md`
- Epic: `.tasks/epics/DTL-029.md`
- Related: DTL-032 (group_label implementation)
- LookML Documentation: https://cloud.google.com/looker/docs/reference/param-field-dimension-group
- Liquid Templating: https://shopify.github.io/liquid/

---

**Strategy Status:** Approved
**Ready for Implementation:** Yes
**Estimated Complexity:** Medium (straightforward feature with good precedent)
