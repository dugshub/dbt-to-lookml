# Implementation Spec: Update test suite for time dimension organization features

## Metadata
- **Issue**: `DTL-034`
- **Stack**: `backend`
- **Generated**: 2025-11-19
- **Strategy**: Approved 2025-11-19

## Issue Context

### Problem Statement

The time dimension organization features introduced in DTL-032 (schema changes for group_label) and DTL-033 (CLI flags and generator parameters) require comprehensive test coverage to maintain the project's 95%+ branch coverage target.

Currently:
- New ConfigMeta fields (`time_dimension_group_label`) lack dedicated tests
- Dimension._to_dimension_group_dict() group_label logic is untested
- LookMLGenerator initialization with new parameters is untested
- CLI flags (--time-dimension-group-label, --use-group-item-label) lack validation tests
- Golden files don't reflect the new group_label fields
- Integration tests don't cover precedence chains (meta > parameter > default)
- Edge cases (None vs empty string, unicode, special characters) are untested

### Solution Approach

Implement a comprehensive test suite following the project's established testing patterns:

1. **Unit Tests** - Fast, isolated tests for schemas and generator components
2. **Integration Tests** - End-to-end workflow tests with precedence validation
3. **Golden Tests** - Update expected output files and add regression protection
4. **CLI Tests** - Validate all new flags and their combinations
5. **Edge Case Tests** - Cover boundary conditions and error scenarios

### Success Criteria

- 95%+ branch coverage for all modified modules (ConfigMeta, Dimension, LookMLGenerator)
- All unit tests pass with comprehensive assertions
- Golden files updated and validated against generated output
- CLI flags properly tested with all combinations
- Edge cases documented and tested
- No regression in existing tests
- All test markers correctly applied (unit, integration, golden, cli)

## Approved Strategy Summary

The approved strategy organizes tests into four phases:

1. **Phase 1**: Unit tests for schemas and generator (highest priority)
2. **Phase 2**: Integration and golden tests for regression protection
3. **Phase 3**: CLI tests for user-facing interface validation
4. **Phase 4**: Edge cases and coverage gap filling

**Key Design Decisions**:
- Use parametrized tests for multiple scenarios (group_label variations)
- Create fixtures for common test data (time dimensions, semantic models)
- Update golden files incrementally to avoid breaking existing tests
- Test precedence chain comprehensively (meta > parameter > default)
- Use temporary directories for all file operations (no test pollution)

**Estimated Effort**: 4-6 hours total
- Unit tests: 2 hours
- Integration/golden tests: 1.5 hours
- CLI tests: 1 hour
- Edge cases and polish: 1.5 hours

## Implementation Plan

### Phase 1: Unit Tests (Priority: High)

**Estimated Time**: 2 hours

**Objective**: Achieve 95%+ coverage for ConfigMeta, Dimension, and LookMLGenerator

#### 1.1 ConfigMeta Schema Tests (30 min)

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`

**Action**: Add new test class after existing ConfigMeta tests

**Tests to Add**:
1. `test_configmeta_time_dimension_group_label_field_exists`
2. `test_configmeta_time_dimension_group_label_with_custom_value`
3. `test_configmeta_time_dimension_group_label_empty_string`
4. `test_configmeta_time_dimension_group_label_none_default`

**Implementation Guidance**:
```python
class TestConfigMetaTimeDimensionGroupLabel:
    """Test time_dimension_group_label configuration in ConfigMeta."""

    def test_configmeta_time_dimension_group_label_field_exists(self) -> None:
        """Test that ConfigMeta accepts time_dimension_group_label field."""
        # Arrange & Act
        meta = ConfigMeta(time_dimension_group_label="Custom Label")

        # Assert
        assert meta.time_dimension_group_label == "Custom Label"

    def test_configmeta_time_dimension_group_label_with_custom_value(self) -> None:
        """Test setting custom group label value."""
        # Arrange & Act
        meta = ConfigMeta(
            hierarchy={"entity": "user"},
            time_dimension_group_label="Time Fields"
        )

        # Assert
        assert meta.time_dimension_group_label == "Time Fields"
        assert meta.hierarchy == {"entity": "user"}

    def test_configmeta_time_dimension_group_label_empty_string(self) -> None:
        """Test disabling grouping with empty string."""
        # Arrange & Act
        meta = ConfigMeta(time_dimension_group_label="")

        # Assert
        assert meta.time_dimension_group_label == ""

    def test_configmeta_time_dimension_group_label_none_default(self) -> None:
        """Test default None value for time_dimension_group_label."""
        # Arrange & Act
        meta = ConfigMeta()

        # Assert
        assert meta.time_dimension_group_label is None
```

**Coverage Target**: 100% of ConfigMeta.time_dimension_group_label field

---

#### 1.2 Dimension Group Label Tests (45 min)

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`

**Action**: Add new test class for dimension group_label logic

**Tests to Add**:
1. `test_dimension_group_label_from_meta_override`
2. `test_dimension_group_label_from_generator_default`
3. `test_dimension_group_label_hardcoded_default`
4. `test_dimension_group_label_disabled_empty_string`
5. `test_dimension_group_label_disabled_none`
6. `test_dimension_group_label_precedence_chain`
7. `test_group_item_label_enabled`
8. `test_group_item_label_disabled`
9. `test_group_item_label_template_format`

**Implementation Guidance**:
```python
class TestDimensionGroupLabel:
    """Test group_label generation logic in dimension_groups."""

    def test_dimension_group_label_from_meta_override(self) -> None:
        """Test that dimension meta time_dimension_group_label takes precedence."""
        # Arrange
        from dbt_to_lookml.schemas.config import Config, ConfigMeta

        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(time_dimension_group_label="Event Timing")
            ),
        )

        # Act
        result = dimension._to_dimension_group_dict(
            default_time_dimension_group_label="Generator Default"
        )

        # Assert
        assert result["group_label"] == "Event Timing"

    def test_dimension_group_label_from_generator_default(self) -> None:
        """Test using generator parameter when no meta override exists."""
        # Arrange
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act
        result = dimension._to_dimension_group_dict(
            default_time_dimension_group_label="Custom Default"
        )

        # Assert
        assert result["group_label"] == "Custom Default"

    def test_dimension_group_label_hardcoded_default(self) -> None:
        """Test fallback to hardcoded 'Time Dimensions' default."""
        # Arrange
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act
        result = dimension._to_dimension_group_dict()

        # Assert
        assert result["group_label"] == "Time Dimensions"

    def test_dimension_group_label_disabled_empty_string(self) -> None:
        """Test that empty string in meta disables group_label."""
        # Arrange
        from dbt_to_lookml.schemas.config import Config, ConfigMeta

        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(time_dimension_group_label="")
            ),
        )

        # Act
        result = dimension._to_dimension_group_dict()

        # Assert
        assert "group_label" not in result

    def test_dimension_group_label_precedence_chain(self) -> None:
        """Test comprehensive precedence: meta > param > default."""
        # Arrange
        from dbt_to_lookml.schemas.config import Config, ConfigMeta

        # Test 1: Meta wins over parameter
        dim_with_meta = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(time_dimension_group_label="Meta Label")
            ),
        )

        # Test 2: Parameter wins over default
        dim_without_meta = Dimension(
            name="updated_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Test 3: Default when neither meta nor param
        dim_default = Dimension(
            name="deleted_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act & Assert
        result1 = dim_with_meta._to_dimension_group_dict(
            default_time_dimension_group_label="Param Label"
        )
        assert result1["group_label"] == "Meta Label"

        result2 = dim_without_meta._to_dimension_group_dict(
            default_time_dimension_group_label="Param Label"
        )
        assert result2["group_label"] == "Param Label"

        result3 = dim_default._to_dimension_group_dict()
        assert result3["group_label"] == "Time Dimensions"

    def test_group_item_label_enabled(self) -> None:
        """Test group_item_label field when use_group_item_label=True."""
        # Arrange
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act
        result = dimension._to_dimension_group_dict(
            use_group_item_label=True
        )

        # Assert
        assert "group_item_label" in result
        assert result["group_item_label"] == "{{ _field._name | capitalize }}"

    def test_group_item_label_disabled(self) -> None:
        """Test no group_item_label when use_group_item_label=False."""
        # Arrange
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act
        result = dimension._to_dimension_group_dict(
            use_group_item_label=False
        )

        # Assert
        assert "group_item_label" not in result

    def test_group_item_label_template_format(self) -> None:
        """Test exact template format of group_item_label."""
        # Arrange
        dimension = Dimension(
            name="signup_date",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            label="Custom Signup Date"
        )

        # Act
        result = dimension._to_dimension_group_dict(
            use_group_item_label=True
        )

        # Assert
        expected_template = "{{ _field._name | capitalize }}"
        assert result["group_item_label"] == expected_template
```

**Coverage Target**: 95%+ of Dimension._to_dimension_group_dict() group_label logic

---

#### 1.3 LookMLGenerator Initialization Tests (45 min)

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_lookml_generator.py`

**Action**: Add tests to existing TestLookMLGenerator class

**Tests to Add**:
1. `test_generator_with_time_dimension_group_label`
2. `test_generator_with_use_group_item_label_true`
3. `test_generator_with_use_group_item_label_false`
4. `test_generator_with_both_time_dimension_params`
5. `test_generate_with_custom_group_label`
6. `test_generate_with_disabled_group_label`
7. `test_generate_respects_dimension_meta_override`

**Implementation Guidance**:
```python
class TestLookMLGeneratorTimeDimensionParams:
    """Test LookMLGenerator initialization with time dimension params."""

    def test_generator_with_time_dimension_group_label(self) -> None:
        """Test initializing generator with time_dimension_group_label."""
        # Arrange & Act
        generator = LookMLGenerator(
            time_dimension_group_label="Custom Time Label"
        )

        # Assert
        assert generator.time_dimension_group_label == "Custom Time Label"

    def test_generator_with_use_group_item_label_true(self) -> None:
        """Test initializing generator with use_group_item_label=True."""
        # Arrange & Act
        generator = LookMLGenerator(use_group_item_label=True)

        # Assert
        assert generator.use_group_item_label is True

    def test_generator_with_use_group_item_label_false(self) -> None:
        """Test default use_group_item_label=False."""
        # Arrange & Act
        generator = LookMLGenerator()

        # Assert
        assert generator.use_group_item_label is False

    def test_generator_with_both_time_dimension_params(self) -> None:
        """Test both time dimension parameters together."""
        # Arrange & Act
        generator = LookMLGenerator(
            time_dimension_group_label="Time Fields",
            use_group_item_label=True
        )

        # Assert
        assert generator.time_dimension_group_label == "Time Fields"
        assert generator.use_group_item_label is True

    def test_generate_with_custom_group_label(self) -> None:
        """Test generation applies custom time_dimension_group_label."""
        # Arrange
        generator = LookMLGenerator(
            time_dimension_group_label="Event Dates"
        )

        model = SemanticModel(
            name="events",
            model="ref('fct_events')",
            entities=[Entity(name="event_id", type="primary")],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                )
            ],
        )

        # Act
        result_dict = model.to_lookml_dict(
            time_dimension_group_label=generator.time_dimension_group_label
        )

        # Assert
        dimension_groups = result_dict.get("dimension_groups", [])
        assert len(dimension_groups) > 0
        assert dimension_groups[0]["group_label"] == "Event Dates"

    def test_generate_with_disabled_group_label(self) -> None:
        """Test generation with disabled grouping (empty string)."""
        # Arrange
        generator = LookMLGenerator(
            time_dimension_group_label=""
        )

        model = SemanticModel(
            name="events",
            model="ref('fct_events')",
            entities=[Entity(name="event_id", type="primary")],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                )
            ],
        )

        # Act
        result_dict = model.to_lookml_dict(
            time_dimension_group_label=generator.time_dimension_group_label
        )

        # Assert
        dimension_groups = result_dict.get("dimension_groups", [])
        assert len(dimension_groups) > 0
        assert "group_label" not in dimension_groups[0]

    def test_generate_respects_dimension_meta_override(self) -> None:
        """Test dimension meta overrides generator default."""
        # Arrange
        from dbt_to_lookml.schemas.config import Config, ConfigMeta

        generator = LookMLGenerator(
            time_dimension_group_label="Generator Default"
        )

        model = SemanticModel(
            name="events",
            model="ref('fct_events')",
            entities=[Entity(name="event_id", type="primary")],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                    config=Config(
                        meta=ConfigMeta(
                            time_dimension_group_label="Dimension Override"
                        )
                    ),
                )
            ],
        )

        # Act
        result_dict = model.to_lookml_dict(
            time_dimension_group_label=generator.time_dimension_group_label
        )

        # Assert
        dimension_groups = result_dict.get("dimension_groups", [])
        assert dimension_groups[0]["group_label"] == "Dimension Override"
```

**Coverage Target**: 95%+ of LookMLGenerator initialization and generation with new params

---

### Phase 2: Integration & Golden Tests (Priority: High)

**Estimated Time**: 1.5 hours

#### 2.1 Update Golden Files (30 min)

**Files to Update**:
- `/Users/dug/Work/repos/dbt-to-lookml/src/tests/golden/expected_users.view.lkml`
- `/Users/dug/Work/repos/dbt-to-lookml/src/tests/golden/expected_searches.view.lkml`
- `/Users/dug/Work/repos/dbt-to-lookml/src/tests/golden/expected_rental_orders.view.lkml`

**Action**: Add `group_label: "Time Dimensions"` to all dimension_group blocks

**Example Change**:
```lookml
# BEFORE
dimension_group: created_date {
  type: time
  timeframes: [
  date,
  week,
  month,
  quarter,
  year,
  ]
  sql: created_at ;;
  description: "Date when user account was created"
  convert_tz: no
}

# AFTER
dimension_group: created_date {
  type: time
  timeframes: [
  date,
  week,
  month,
  quarter,
  year,
  ]
  sql: created_at ;;
  description: "Date when user account was created"
  convert_tz: no
  group_label: "Time Dimensions"
}
```

**Implementation Steps**:
1. Locate all `dimension_group:` blocks in golden files
2. Add `group_label: "Time Dimensions"` after `convert_tz` field
3. Maintain exact indentation (2 spaces per level)
4. Run golden tests to verify no other unexpected changes

---

#### 2.2 Golden Test Validation (30 min)

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/test_golden.py`

**Action**: Add validation tests for time dimension organization in golden files

**Tests to Add**:
1. `test_golden_files_have_group_label`
2. `test_golden_with_custom_group_label` (optional new golden file)

**Implementation Guidance**:
```python
class TestTimeDimensionGoldenFiles:
    """Test golden files include time dimension organization."""

    def test_golden_files_have_group_label(self, golden_dir: Path) -> None:
        """Test that all golden files include group_label in dimension_groups."""
        import lkml

        # Arrange
        golden_files = [
            golden_dir / "expected_users.view.lkml",
            golden_dir / "expected_searches.view.lkml",
            golden_dir / "expected_rental_orders.view.lkml",
        ]

        # Act & Assert
        for golden_file in golden_files:
            if not golden_file.exists():
                continue

            content = golden_file.read_text()
            parsed = lkml.parse(content)

            # Extract dimension_groups
            views = parsed.get("views", [])
            for view in views:
                dimension_groups = view.get("dimension_groups", [])

                # Assert all dimension_groups have group_label
                for dg in dimension_groups:
                    assert "group_label" in dg, (
                        f"dimension_group '{dg.get('name')}' in {golden_file.name} "
                        f"missing group_label field"
                    )
                    # Default should be "Time Dimensions"
                    assert dg["group_label"] == "Time Dimensions"
```

**Coverage Target**: All golden files validated for time dimension organization

---

#### 2.3 Integration Tests (30 min)

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/integration/test_end_to_end.py`

**Action**: Add new test class for time dimension organization

**Tests to Add**:
1. `test_parse_and_generate_with_time_dimension_grouping`
2. `test_parse_and_generate_with_custom_group_label`
3. `test_parse_and_generate_with_group_item_label`
4. `test_precedence_dimension_meta_overrides_generator`

**Implementation Guidance**:
```python
class TestTimeDimensionOrganizationIntegration:
    """Integration tests for time dimension organization features."""

    def test_parse_and_generate_with_time_dimension_grouping(self) -> None:
        """Test default time dimension grouping in full pipeline."""
        from tempfile import TemporaryDirectory

        # Arrange
        fixture_path = Path(__file__).parent.parent / "fixtures"
        parser = DbtParser()
        semantic_models = parser.parse_directory(fixture_path)

        generator = LookMLGenerator()

        # Act
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Assert
            assert len(validation_errors) == 0

            # Check view files for group_label
            view_files = list(output_dir.glob("*.view.lkml"))
            for view_file in view_files:
                content = view_file.read_text()
                if "dimension_group:" in content:
                    # Should have group_label: "Time Dimensions"
                    assert 'group_label: "Time Dimensions"' in content

    def test_parse_and_generate_with_custom_group_label(self) -> None:
        """Test custom time_dimension_group_label in full pipeline."""
        from tempfile import TemporaryDirectory

        # Arrange
        fixture_path = Path(__file__).parent.parent / "fixtures"
        parser = DbtParser()
        semantic_models = parser.parse_directory(fixture_path)

        generator = LookMLGenerator(
            time_dimension_group_label="Event Timing"
        )

        # Act
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Assert
            assert len(validation_errors) == 0

            # Check for custom label
            view_files = list(output_dir.glob("*.view.lkml"))
            for view_file in view_files:
                content = view_file.read_text()
                if "dimension_group:" in content:
                    assert 'group_label: "Event Timing"' in content

    def test_parse_and_generate_with_group_item_label(self) -> None:
        """Test use_group_item_label flag in full pipeline."""
        from tempfile import TemporaryDirectory

        # Arrange
        fixture_path = Path(__file__).parent.parent / "fixtures"
        parser = DbtParser()
        semantic_models = parser.parse_directory(fixture_path)

        generator = LookMLGenerator(use_group_item_label=True)

        # Act
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Assert
            assert len(validation_errors) == 0

            # Check for group_item_label
            view_files = list(output_dir.glob("*.view.lkml"))
            for view_file in view_files:
                content = view_file.read_text()
                if "dimension_group:" in content:
                    assert "group_item_label:" in content
```

**Coverage Target**: End-to-end workflows with all configuration combinations

---

### Phase 3: CLI Tests (Priority: Medium)

**Estimated Time**: 1 hour

#### 3.1 CLI Flag Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/test_cli.py`

**Action**: Add new test class for time dimension CLI flags

**Tests to Add**:
1. `test_cli_generate_with_time_dimension_group_label_flag`
2. `test_cli_generate_with_no_time_dimension_group_label_flag`
3. `test_cli_generate_with_use_group_item_label_flag`
4. `test_cli_generate_without_time_dimension_flags`
5. `test_cli_help_shows_time_dimension_flags`
6. `test_cli_time_dimension_flags_with_other_flags`

**Implementation Guidance**:
```python
class TestCLITimeDimensionFlags:
    """Test CLI flags for time dimension organization."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Return path to fixtures directory."""
        return Path(__file__).parent / "fixtures"

    def test_cli_generate_with_time_dimension_group_label_flag(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test --time-dimension-group-label flag."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir", str(fixtures_dir),
                    "--output-dir", str(output_dir),
                    "--schema", "public",
                    "--time-dimension-group-label", "Custom Time Label",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

            # Check generated files contain custom label
            view_files = list(output_dir.glob("*.view.lkml"))
            for view_file in view_files:
                content = view_file.read_text()
                if "dimension_group:" in content:
                    assert 'group_label: "Custom Time Label"' in content

    def test_cli_generate_with_no_time_dimension_group_label_flag(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test --no-time-dimension-group-label flag disables grouping."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir", str(fixtures_dir),
                    "--output-dir", str(output_dir),
                    "--schema", "public",
                    "--no-time-dimension-group-label",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

            # Check no group_label in generated files
            view_files = list(output_dir.glob("*.view.lkml"))
            for view_file in view_files:
                content = view_file.read_text()
                # group_label should not appear in dimension_group blocks
                # Note: May appear in regular dimensions, so check carefully
                import lkml
                parsed = lkml.parse(content)
                for view in parsed.get("views", []):
                    for dg in view.get("dimension_groups", []):
                        assert "group_label" not in dg

    def test_cli_generate_with_use_group_item_label_flag(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test --use-group-item-label flag."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir", str(fixtures_dir),
                    "--output-dir", str(output_dir),
                    "--schema", "public",
                    "--use-group-item-label",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

            # Check group_item_label in generated files
            view_files = list(output_dir.glob("*.view.lkml"))
            for view_file in view_files:
                content = view_file.read_text()
                if "dimension_group:" in content:
                    assert "group_item_label:" in content

    def test_cli_generate_without_time_dimension_flags(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test default behavior without time dimension flags."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir", str(fixtures_dir),
                    "--output-dir", str(output_dir),
                    "--schema", "public",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

            # Should use default "Time Dimensions"
            view_files = list(output_dir.glob("*.view.lkml"))
            for view_file in view_files:
                content = view_file.read_text()
                if "dimension_group:" in content:
                    assert 'group_label: "Time Dimensions"' in content

    def test_cli_help_shows_time_dimension_flags(
        self, runner: CliRunner
    ) -> None:
        """Test help text documents time dimension flags."""
        # Act
        result = runner.invoke(cli, ["generate", "--help"])

        # Assert
        assert result.exit_code == 0
        assert "--time-dimension-group-label" in result.output
        assert "--no-time-dimension-group-label" in result.output
        assert "--use-group-item-label" in result.output

    def test_cli_time_dimension_flags_with_other_flags(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test time dimension flags work with other flags."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir", str(fixtures_dir),
                    "--output-dir", str(output_dir),
                    "--schema", "public",
                    "--view-prefix", "v_",
                    "--convert-tz",
                    "--time-dimension-group-label", "Event Dates",
                    "--use-group-item-label",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

            # Verify all flags applied
            view_files = list(output_dir.glob("v_*.view.lkml"))
            assert len(view_files) > 0

            for view_file in view_files:
                content = view_file.read_text()
                if "dimension_group:" in content:
                    assert 'group_label: "Event Dates"' in content
                    assert "group_item_label:" in content
                    assert "convert_tz: yes" in content
```

**Coverage Target**: All CLI flag combinations and error cases

---

### Phase 4: Edge Cases & Polish (Priority: Low)

**Estimated Time**: 1.5 hours

#### 4.1 Edge Case Tests

**File**: `/Users/dug/Work/repos/dbt-to-lookml/src/tests/unit/test_schemas.py`

**Action**: Add edge case tests to existing test classes

**Tests to Add**:
1. `test_no_time_dimensions_in_model`
2. `test_single_time_dimension`
3. `test_unicode_in_group_label`
4. `test_special_characters_in_group_label`
5. `test_very_long_group_label`
6. `test_multiple_time_dimensions_different_groups`

**Implementation Guidance**:
```python
class TestTimeDimensionEdgeCases:
    """Edge cases for time dimension organization."""

    def test_no_time_dimensions_in_model(self) -> None:
        """Test model with only categorical dimensions."""
        # Arrange
        model = SemanticModel(
            name="categories",
            model="ref('dim_categories')",
            entities=[Entity(name="category_id", type="primary")],
            dimensions=[
                Dimension(
                    name="category_name",
                    type=DimensionType.CATEGORICAL,
                )
            ],
        )

        # Act
        result_dict = model.to_lookml_dict()

        # Assert - should have no dimension_groups
        assert "dimension_groups" not in result_dict or len(result_dict.get("dimension_groups", [])) == 0

    def test_single_time_dimension(self) -> None:
        """Test model with exactly one time dimension still gets group_label."""
        # Arrange
        model = SemanticModel(
            name="events",
            model="ref('fct_events')",
            entities=[Entity(name="event_id", type="primary")],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                )
            ],
        )

        # Act
        result_dict = model.to_lookml_dict()

        # Assert
        dimension_groups = result_dict.get("dimension_groups", [])
        assert len(dimension_groups) == 1
        assert dimension_groups[0]["group_label"] == "Time Dimensions"

    def test_unicode_in_group_label(self) -> None:
        """Test custom label with unicode characters."""
        # Arrange
        from dbt_to_lookml.schemas.config import Config, ConfigMeta

        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(time_dimension_group_label="时间维度")  # Chinese
            ),
        )

        # Act
        result = dimension._to_dimension_group_dict()

        # Assert
        assert result["group_label"] == "时间维度"

    def test_special_characters_in_group_label(self) -> None:
        """Test label with special characters."""
        # Arrange
        from dbt_to_lookml.schemas.config import Config, ConfigMeta

        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(time_dimension_group_label="Time & Dates (Primary)")
            ),
        )

        # Act
        result = dimension._to_dimension_group_dict()

        # Assert
        assert result["group_label"] == "Time & Dates (Primary)"

    def test_very_long_group_label(self) -> None:
        """Test edge case with very long label string."""
        # Arrange
        from dbt_to_lookml.schemas.config import Config, ConfigMeta

        long_label = "A" * 200  # 200 character label

        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(time_dimension_group_label=long_label)
            ),
        )

        # Act
        result = dimension._to_dimension_group_dict()

        # Assert
        assert result["group_label"] == long_label

    def test_multiple_time_dimensions_different_groups(self) -> None:
        """Test multiple time dimensions with different group labels."""
        # Arrange
        from dbt_to_lookml.schemas.config import Config, ConfigMeta

        model = SemanticModel(
            name="events",
            model="ref('fct_events')",
            entities=[Entity(name="event_id", type="primary")],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                    config=Config(
                        meta=ConfigMeta(time_dimension_group_label="Creation Dates")
                    ),
                ),
                Dimension(
                    name="updated_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                    config=Config(
                        meta=ConfigMeta(time_dimension_group_label="Update Dates")
                    ),
                ),
                Dimension(
                    name="deleted_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                    # No meta - uses default
                ),
            ],
        )

        # Act
        result_dict = model.to_lookml_dict()

        # Assert
        dimension_groups = result_dict.get("dimension_groups", [])
        assert len(dimension_groups) == 3

        # Find each by name and check group_label
        created_dg = next(dg for dg in dimension_groups if dg["name"] == "created_at")
        updated_dg = next(dg for dg in dimension_groups if dg["name"] == "updated_at")
        deleted_dg = next(dg for dg in dimension_groups if dg["name"] == "deleted_at")

        assert created_dg["group_label"] == "Creation Dates"
        assert updated_dg["group_label"] == "Update Dates"
        assert deleted_dg["group_label"] == "Time Dimensions"
```

**Coverage Target**: All edge cases and boundary conditions

---

## Testing Checklist

### Pre-Implementation
- [ ] Review approved strategy (DTL-034-strategy.md)
- [ ] Understand existing test patterns in codebase
- [ ] Set up test environment with fixtures

### Phase 1: Unit Tests
- [ ] Add ConfigMeta tests (4 tests)
- [ ] Add Dimension group_label tests (9 tests)
- [ ] Add LookMLGenerator tests (7 tests)
- [ ] Run unit tests: `make test-fast`
- [ ] Verify 95%+ coverage for modified code

### Phase 2: Integration & Golden Tests
- [ ] Update golden files (3 files)
- [ ] Add golden validation tests (2 tests)
- [ ] Add integration tests (4 tests)
- [ ] Run integration tests: `pytest src/tests/integration -v`
- [ ] Run golden tests: `pytest src/tests/test_golden.py -v`

### Phase 3: CLI Tests
- [ ] Add CLI flag tests (6 tests)
- [ ] Test help text documentation
- [ ] Test flag combinations
- [ ] Run CLI tests: `pytest src/tests/test_cli.py::TestCLITimeDimensionFlags -v`

### Phase 4: Edge Cases
- [ ] Add edge case tests (6 tests)
- [ ] Test unicode and special characters
- [ ] Test boundary conditions
- [ ] Run all tests: `make test`

### Final Validation
- [ ] Run full test suite: `make test-full`
- [ ] Generate coverage report: `make test-coverage`
- [ ] Verify 95%+ branch coverage for:
  - `schemas/config.py` (ConfigMeta)
  - `schemas/semantic_layer.py` (Dimension)
  - `generators/lookml.py` (LookMLGenerator)
  - `__main__.py` (CLI)
- [ ] Check for any test flakiness
- [ ] Verify all test markers applied correctly
- [ ] No regression in existing tests

## Coverage Targets by Module

| Module | Target Coverage | Tests Added |
|--------|----------------|-------------|
| `schemas/config.py` (ConfigMeta) | 95%+ | 4 unit tests |
| `schemas/semantic_layer.py` (Dimension) | 95%+ | 15 unit tests |
| `generators/lookml.py` (LookMLGenerator) | 95%+ | 7 unit tests |
| `__main__.py` (CLI) | 95%+ | 6 CLI tests |
| Integration workflows | End-to-end | 4 integration tests |
| Golden files | Regression | 2 golden tests + file updates |

**Total New Tests**: ~40-45 test methods

## Test Markers

Apply these markers to all new tests:

```python
@pytest.mark.unit
def test_configmeta_time_dimension_group_label_field_exists():
    ...

@pytest.mark.integration
def test_parse_and_generate_with_time_dimension_grouping():
    ...

@pytest.mark.golden
def test_golden_files_have_group_label():
    ...

@pytest.mark.cli
def test_cli_generate_with_time_dimension_group_label_flag():
    ...
```

## Success Metrics

1. **Coverage**: 95%+ branch coverage for all modified modules
2. **Test Count**: 40-45 new test methods added
3. **Golden Files**: 3 files updated with group_label fields
4. **No Regressions**: All existing tests continue to pass
5. **Documentation**: All tests have clear docstrings explaining what is tested
6. **Performance**: Test suite runs in < 30 seconds for unit tests

## Risk Mitigation

### Risk 1: Breaking Existing Golden Tests
**Mitigation**: Update golden files incrementally and run tests after each update

### Risk 2: Coverage Gaps in Edge Cases
**Mitigation**: Use parametrized tests and coverage report to identify untested branches

### Risk 3: Test Flakiness in Integration Tests
**Mitigation**: Use temporary directories, avoid timing dependencies, clean up resources

### Risk 4: CLI Flag Interaction Bugs
**Mitigation**: Test all flag combinations, especially mutually exclusive flags

## Next Steps After Implementation

1. Update issue status to `Ready` (has spec)
2. Add `state:has-spec` label to DTL-034
3. Begin implementation following this spec
4. Update issue status to `In Progress` when starting
5. Run tests incrementally during implementation
6. Update issue status to `Done` when all tests pass with 95%+ coverage
