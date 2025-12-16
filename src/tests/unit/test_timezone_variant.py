"""Unit tests for timezone variant functionality.

Tests the complete timezone variant feature including:
- Parsing timezone_variant config from YAML
- TimezoneVariant schema validation
- Timezone variant grouping and toggle generation
- Edge cases (single variant, no primary, empty variants)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dbt_to_lookml.constants import GROUP_LABEL_DATE_DIMENSIONS
from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.schemas.config import Config, ConfigMeta, TimezoneVariant
from dbt_to_lookml.schemas.semantic_layer import Dimension, SemanticModel
from dbt_to_lookml.types import DimensionType


class TestTimezoneVariantSchema:
    """Test TimezoneVariant Pydantic model validation."""

    def test_timezone_variant_valid(self):
        """Test valid timezone_variant creation."""
        tz_var = TimezoneVariant(
            canonical_name="starts_at",
            variant="utc",
            is_primary=True,
        )
        assert tz_var.canonical_name == "starts_at"
        assert tz_var.variant == "utc"
        assert tz_var.is_primary is True

    def test_timezone_variant_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            TimezoneVariant(canonical_name="starts_at")

        with pytest.raises(Exception):
            TimezoneVariant(canonical_name="starts_at", variant="utc")

        with pytest.raises(Exception):
            TimezoneVariant(variant="utc", is_primary=True)

    def test_timezone_variant_types(self):
        """Test field type validation."""
        # Valid types
        tz_var = TimezoneVariant(
            canonical_name="starts_at",
            variant="local",
            is_primary=False,
        )
        assert tz_var.is_primary is False

        # Invalid types should be caught by Pydantic
        with pytest.raises(Exception):
            TimezoneVariant(
                canonical_name=123,  # Should be str
                variant="utc",
                is_primary=True,
            )

    def test_timezone_variant_variant_names(self):
        """Test various variant name patterns."""
        # Common variants
        for variant in ["utc", "local", "eastern", "pacific", "pst", "est"]:
            tz_var = TimezoneVariant(
                canonical_name="timestamp",
                variant=variant,
                is_primary=True,
            )
            assert tz_var.variant == variant


class TestDbtParserTimezoneVariant:
    """Test parsing timezone_variant configuration from YAML."""

    def test_parse_timezone_variant_basic(self, tmp_path: Path):
        """Test parsing basic timezone_variant configuration."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: schema.rentals
    defaults:
      agg_time_dimension: created_at

    entities:
      - name: rental_id
        type: primary

    dimensions:
      - name: starts_at
        type: time
        type_params:
          time_granularity: day
        config:
          meta:
            timezone_variant:
              canonical_name: "starts_at"
              variant: "utc"
              is_primary: true

      - name: starts_at_local
        type: time
        type_params:
          time_granularity: day
        config:
          meta:
            timezone_variant:
              canonical_name: "starts_at"
              variant: "local"
              is_primary: false
"""
        yaml_file = tmp_path / "rentals.yaml"
        yaml_file.write_text(yaml_content)

        parser = DbtParser()
        models = parser.parse_directory(tmp_path)

        assert len(models) == 1
        model = models[0]
        assert model.name == "rentals"

        # Check first dimension
        dim1 = model.dimensions[0]
        assert dim1.name == "starts_at"
        assert dim1.config is not None
        assert dim1.config.meta is not None
        assert dim1.config.meta.timezone_variant is not None
        assert dim1.config.meta.timezone_variant.canonical_name == "starts_at"
        assert dim1.config.meta.timezone_variant.variant == "utc"
        assert dim1.config.meta.timezone_variant.is_primary is True

        # Check second dimension
        dim2 = model.dimensions[1]
        assert dim2.name == "starts_at_local"
        assert dim2.config is not None
        assert dim2.config.meta is not None
        assert dim2.config.meta.timezone_variant is not None
        assert dim2.config.meta.timezone_variant.canonical_name == "starts_at"
        assert dim2.config.meta.timezone_variant.variant == "local"
        assert dim2.config.meta.timezone_variant.is_primary is False

    def test_parse_timezone_variant_missing_fields(self, tmp_path: Path):
        """Test parsing malformed timezone_variant logs warning and continues."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: schema.rentals
    defaults:
      agg_time_dimension: created_at

    entities:
      - name: rental_id
        type: primary

    dimensions:
      - name: starts_at
        type: time
        type_params:
          time_granularity: day
        config:
          meta:
            timezone_variant:
              canonical_name: "starts_at"
            # Missing variant and is_primary
"""
        yaml_file = tmp_path / "rentals.yaml"
        yaml_file.write_text(yaml_content)

        parser = DbtParser()
        # Should handle gracefully and continue parsing
        models = parser.parse_directory(tmp_path)

        # Model should still be parsed
        assert len(models) == 1
        model = models[0]
        dim = model.dimensions[0]

        # timezone_variant should be None (skipped due to error)
        assert dim.config is None or dim.config.meta is None or dim.config.meta.timezone_variant is None

    def test_parse_without_timezone_variant(self, tmp_path: Path):
        """Test parsing dimensions without timezone_variant works normally."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: schema.rentals
    defaults:
      agg_time_dimension: created_at

    entities:
      - name: rental_id
        type: primary

    dimensions:
      - name: starts_at
        type: time
        type_params:
          time_granularity: day
"""
        yaml_file = tmp_path / "rentals.yaml"
        yaml_file.write_text(yaml_content)

        parser = DbtParser()
        models = parser.parse_directory(tmp_path)

        assert len(models) == 1
        model = models[0]
        dim = model.dimensions[0]
        assert dim.name == "starts_at"
        assert dim.config is None or dim.config.meta is None or dim.config.meta.timezone_variant is None


class TestGetCanonicalKey:
    """Test _get_canonical_key method."""

    def test_get_canonical_key_auto_prefix(self):
        """Test auto-prefixing canonical_name with model name."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[],
        )

        dimension = Dimension(
            name="starts_at",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                        canonical_name="starts_at",
                        variant="utc",
                        is_primary=True,
                    )
                )
            ),
        )

        generator = LookMLGenerator()
        canonical_key = generator._get_canonical_key(model, dimension)
        assert canonical_key == "rentals_starts_at"

    def test_get_canonical_key_already_prefixed(self):
        """Test idempotent behavior when already prefixed."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[],
        )

        dimension = Dimension(
            name="starts_at",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="rentals_starts_at",  # Already prefixed
                    variant="utc",
                    is_primary=True,
                )
                )
            ),
        )

        generator = LookMLGenerator()
        canonical_key = generator._get_canonical_key(model, dimension)
        assert canonical_key == "rentals_starts_at"  # No double prefix

    def test_get_canonical_key_missing_config(self):
        """Test error when timezone_variant config missing."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[],
        )

        dimension = Dimension(
            name="starts_at",
            type=DimensionType.TIME,
        )

        generator = LookMLGenerator()
        with pytest.raises(ValueError, match="missing timezone_variant configuration"):
            generator._get_canonical_key(model, dimension)


class TestGroupTimezoneVariants:
    """Test _group_timezone_variants method."""

    def test_group_timezone_variants_basic(self):
        """Test grouping two variants by canonical_name."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="utc",
                            is_primary=True,
                        )
                        )
                    ),
                ),
                Dimension(
                    name="starts_at_local",
                    type=DimensionType.TIME,
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="local",
                            is_primary=False,
                        )
                        )
                    ),
                ),
            ],
        )

        generator = LookMLGenerator()
        groups = generator._group_timezone_variants(model)

        assert len(groups) == 1
        assert "rentals_starts_at" in groups
        assert len(groups["rentals_starts_at"]) == 2

    def test_group_timezone_variants_multiple_groups(self):
        """Test grouping multiple sets of variants."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                # First group
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="utc",
                            is_primary=True,
                        )
                        )
                    ),
                ),
                Dimension(
                    name="starts_at_local",
                    type=DimensionType.TIME,
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="local",
                            is_primary=False,
                        )
                        )
                    ),
                ),
                # Second group
                Dimension(
                    name="ends_at",
                    type=DimensionType.TIME,
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="ends_at",
                            variant="utc",
                            is_primary=True,
                        )
                        )
                    ),
                ),
                Dimension(
                    name="ends_at_local",
                    type=DimensionType.TIME,
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="ends_at",
                            variant="local",
                            is_primary=False,
                        )
                        )
                    ),
                ),
            ],
        )

        generator = LookMLGenerator()
        groups = generator._group_timezone_variants(model)

        assert len(groups) == 2
        assert "rentals_starts_at" in groups
        assert "rentals_ends_at" in groups
        assert len(groups["rentals_starts_at"]) == 2
        assert len(groups["rentals_ends_at"]) == 2

    def test_group_timezone_variants_empty(self):
        """Test grouping when no timezone variants exist."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                )
            ],
        )

        generator = LookMLGenerator()
        groups = generator._group_timezone_variants(model)

        assert len(groups) == 0

    def test_group_timezone_variants_non_time_dimensions_ignored(self):
        """Test that non-time dimensions are ignored even with timezone_variant."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="category",
                    type=DimensionType.CATEGORICAL,
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="category",
                            variant="utc",
                            is_primary=True,
                        )
                        )
                    ),
                ),
            ],
        )

        generator = LookMLGenerator()
        groups = generator._group_timezone_variants(model)

        assert len(groups) == 0


class TestGenerateTimezoneParameter:
    """Test _generate_timezone_parameter method."""

    def test_generate_timezone_parameter_basic(self):
        """Test generating parameter with two variants."""
        dim1 = Dimension(
            name="starts_at",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="utc",
                    is_primary=True,
                )
                )
            ),
        )
        dim2 = Dimension(
            name="starts_at_local",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="local",
                    is_primary=False,
                )
                )
            ),
        )

        variant_groups = {"rentals_starts_at": [dim1, dim2]}

        generator = LookMLGenerator()
        param = generator._generate_timezone_parameter(variant_groups)

        assert param is not None
        assert param["name"] == "timezone_selector"
        assert param["type"] == "unquoted"
        assert param["label"] == "Timezone"
        assert param["default_value"] == "_utc"  # Primary variant

        # Check group_label defaults to GROUP_LABEL_DATE_DIMENSIONS (leading space for sort order)
        assert param["group_label"] == GROUP_LABEL_DATE_DIMENSIONS

        # Check allowed values
        assert len(param["allowed_value"]) == 2
        values = {av["label"]: av["value"] for av in param["allowed_value"]}
        assert values["LOCAL"] == "_local"
        assert values["UTC"] == "_utc"

    def test_generate_timezone_parameter_custom_group_label(self):
        """Test generating parameter with custom group_label."""
        dim1 = Dimension(
            name="starts_at",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="utc",
                    is_primary=True,
                )
                )
            ),
        )
        dim2 = Dimension(
            name="starts_at_local",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="local",
                    is_primary=False,
                )
                )
            ),
        )

        variant_groups = {"rentals_starts_at": [dim1, dim2]}

        generator = LookMLGenerator()
        param = generator._generate_timezone_parameter(
            variant_groups, group_label="Custom Time Group"
        )

        assert param is not None
        assert param["group_label"] == "Custom Time Group"

    def test_generate_timezone_parameter_no_primary(self):
        """Test parameter uses first alphabetical variant when no primary."""
        dim1 = Dimension(
            name="starts_at",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="utc",
                    is_primary=False,
                )
                )
            ),
        )
        dim2 = Dimension(
            name="starts_at_local",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="local",
                    is_primary=False,
                )
                )
            ),
        )

        variant_groups = {"rentals_starts_at": [dim1, dim2]}

        generator = LookMLGenerator()
        param = generator._generate_timezone_parameter(variant_groups)

        assert param is not None
        # Should default to "local" (first alphabetically)
        assert param["default_value"] == "_local"

    def test_generate_timezone_parameter_empty_groups(self):
        """Test parameter returns None for empty groups."""
        variant_groups: dict[str, list[Dimension]] = {}

        generator = LookMLGenerator()
        param = generator._generate_timezone_parameter(variant_groups)

        assert param is None

    def test_generate_timezone_parameter_multiple_groups(self):
        """Test parameter includes all unique variants from multiple groups."""
        dim1 = Dimension(
            name="starts_at",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="utc",
                    is_primary=True,
                )
                )
            ),
        )
        dim2 = Dimension(
            name="starts_at_eastern",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="eastern",
                    is_primary=False,
                )
                )
            ),
        )
        dim3 = Dimension(
            name="ends_at",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="ends_at",
                    variant="utc",
                    is_primary=True,
                )
                )
            ),
        )
        dim4 = Dimension(
            name="ends_at_pacific",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="ends_at",
                    variant="pacific",
                    is_primary=False,
                )
                )
            ),
        )

        variant_groups = {
            "rentals_starts_at": [dim1, dim2],
            "rentals_ends_at": [dim3, dim4],
        }

        generator = LookMLGenerator()
        param = generator._generate_timezone_parameter(variant_groups)

        assert param is not None
        # Should have all unique variants: eastern, pacific, utc
        assert len(param["allowed_value"]) == 3
        values = {av["label"]: av["value"] for av in param["allowed_value"]}
        assert values["EASTERN"] == "_eastern"
        assert values["PACIFIC"] == "_pacific"
        assert values["UTC"] == "_utc"


class TestExtractBaseColumn:
    """Test _extract_base_column method."""

    def test_extract_base_column_with_suffix(self):
        """Test extracting base column when suffix matches variant."""
        dim = Dimension(
            name="starts_at",
            type=DimensionType.TIME,
            expr="rental_starts_at_utc",
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="utc",
                    is_primary=True,
                )
                )
            ),
        )

        generator = LookMLGenerator()
        base_column = generator._extract_base_column([dim])

        assert base_column == "rental_starts_at"

    def test_extract_base_column_no_suffix_match(self):
        """Test fallback when expression doesn't end with expected suffix."""
        dim = Dimension(
            name="starts_at",
            type=DimensionType.TIME,
            expr="custom_column_name",
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="utc",
                    is_primary=True,
                )
                )
            ),
        )

        generator = LookMLGenerator()
        base_column = generator._extract_base_column([dim])

        # Should return expression as-is
        assert base_column == "custom_column_name"

    def test_extract_base_column_no_expr_uses_name(self):
        """Test using dimension name when expr is None."""
        dim = Dimension(
            name="starts_at_utc",
            type=DimensionType.TIME,
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="utc",
                    is_primary=True,
                )
                )
            ),
        )

        generator = LookMLGenerator()
        base_column = generator._extract_base_column([dim])

        assert base_column == "starts_at"

    def test_extract_base_column_empty_list(self):
        """Test error when variants list is empty."""
        generator = LookMLGenerator()

        with pytest.raises(ValueError, match="empty variants list"):
            generator._extract_base_column([])


class TestGenerateToggleableDimensionGroup:
    """Test _generate_toggleable_dimension_group method."""

    def test_generate_toggleable_dimension_group_basic(self):
        """Test generating toggleable dimension_group with parameter injection."""
        primary = Dimension(
            name="starts_at",
            type=DimensionType.TIME,
            expr="rental_starts_at_utc",
            label="Rental Start",
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="utc",
                    is_primary=True,
                )
                )
            ),
        )
        variant = Dimension(
            name="starts_at_local",
            type=DimensionType.TIME,
            expr="rental_starts_at_local",
            label="Rental Start",
            config=Config(
                meta=ConfigMeta(
                    timezone_variant=TimezoneVariant(
                    canonical_name="starts_at",
                    variant="local",
                    is_primary=False,
                )
                )
            ),
        )

        generator = LookMLGenerator()
        dim_group = generator._generate_toggleable_dimension_group(
            primary_dim=primary,
            variants=[primary, variant],
        )

        # Check SQL uses Liquid conditionals (variants sorted alphabetically: local, utc)
        expected_sql = "\n".join([
            "{% if timezone_selector._parameter_value == '_local' %}",
            "${TABLE}.rental_starts_at_local",
            "{% elsif timezone_selector._parameter_value == '_utc' %}",
            "${TABLE}.rental_starts_at_utc",
            "{% endif %}",
        ])
        assert dim_group["sql"] == expected_sql

        # Check description mentions toggle
        assert "toggle timezone" in dim_group["description"]

        # Check label is preserved from primary
        assert dim_group["label"] == "Rental Start"

    def test_generate_toggleable_dimension_group_inherits_config(self):
        """Test toggleable dimension inherits configuration from primary."""
        primary = Dimension(
            name="starts_at",
            type=DimensionType.TIME,
            expr="rental_starts_at_utc",
            label="Rental Start",
            description="Original description",
            config=Config(
                meta=ConfigMeta(
                    convert_tz=True,
                    timezone_variant=TimezoneVariant(
                        canonical_name="starts_at",
                        variant="utc",
                        is_primary=True,
                    ),
                )
            ),
        )

        generator = LookMLGenerator(convert_tz=False)
        dim_group = generator._generate_toggleable_dimension_group(
            primary_dim=primary,
            variants=[primary],
        )

        # Should inherit convert_tz from primary dimension (overrides generator default)
        assert dim_group["convert_tz"] == "yes"

        # Description should be enhanced
        assert "Original description" in dim_group["description"]
        assert "toggle timezone" in dim_group["description"]


class TestGenerateViewWithTimezoneVariants:
    """Test generate_view method with timezone variant integration."""

    def test_generate_view_no_timezone_variants(self):
        """Test backward compatibility when no timezone_variant config."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                )
            ],
        )

        generator = LookMLGenerator()
        view_dict = generator.generate_view(model)

        # Should generate normally without parameter
        assert "views" in view_dict
        view = view_dict["views"][0]
        assert "parameter" not in view or not view.get("parameter")

    def test_generate_view_with_timezone_variants(self):
        """Test view generation with timezone variants creates toggle."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_utc",
                    label="Rental Start",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="utc",
                            is_primary=True,
                        )
                        )
                    ),
                ),
                Dimension(
                    name="starts_at_local",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_local",
                    label="Rental Start",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="local",
                            is_primary=False,
                        )
                        )
                    ),
                ),
            ],
        )

        generator = LookMLGenerator()
        view_dict = generator.generate_view(model)

        assert "views" in view_dict
        view = view_dict["views"][0]

        # Should have parameter
        assert "parameter" in view
        assert len(view["parameter"]) == 1
        assert view["parameter"][0]["name"] == "timezone_selector"

        # Should have only one dimension_group (collapsed)
        dimension_groups = view.get("dimension_groups", [])
        dim_group_names = [dg["name"] for dg in dimension_groups]
        assert "starts_at" in dim_group_names
        assert "starts_at_local" not in dim_group_names  # Should be excluded

        # Check the dimension_group has toggle SQL (Liquid conditional pattern)
        starts_at_dg = next(dg for dg in dimension_groups if dg["name"] == "starts_at")
        assert "timezone_selector._parameter_value" in starts_at_dg["sql"]

    def test_generate_view_single_variant_no_toggle(self):
        """Test single variant doesn't generate toggle (misconfiguration)."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_utc",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="utc",
                            is_primary=True,
                        )
                        )
                    ),
                ),
            ],
        )

        generator = LookMLGenerator()
        view_dict = generator.generate_view(model)

        assert "views" in view_dict
        view = view_dict["views"][0]

        # Should NOT have parameter (needs 2+ variants)
        assert "parameter" not in view or not view.get("parameter")

        # Should have dimension_group as normal
        dimension_groups = view.get("dimension_groups", [])
        assert len(dimension_groups) == 1
        assert dimension_groups[0]["name"] == "starts_at"

        # Should NOT have parameter injection in SQL
        assert "{% parameter timezone_selector %}" not in dimension_groups[0]["sql"]

    def test_generate_view_updates_sets(self):
        """Test that sets are updated to exclude non-primary variants."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_utc",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="utc",
                            is_primary=True,
                        )
                        )
                    ),
                ),
                Dimension(
                    name="starts_at_local",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_local",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="local",
                            is_primary=False,
                        )
                        )
                    ),
                ),
                Dimension(
                    name="category",
                    type=DimensionType.CATEGORICAL,
                ),
            ],
        )

        generator = LookMLGenerator()
        view_dict = generator.generate_view(model)

        assert "views" in view_dict
        view = view_dict["views"][0]

        # Check sets if they exist
        if "sets" in view:
            for set_dict in view["sets"]:
                fields = set_dict.get("fields", [])
                # Should not include starts_at_local fields
                for field in fields:
                    assert not field.startswith("starts_at_local_")


class TestTimezoneVariantEdgeCases:
    """Test edge cases for timezone variant feature."""

    def test_no_primary_specified_uses_first_variant(self):
        """Test fallback to first variant when no primary specified."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="starts_at_local",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_local",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="local",
                            is_primary=False,
                        )
                        )
                    ),
                ),
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_utc",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="utc",
                            is_primary=False,
                        )
                        )
                    ),
                ),
            ],
        )

        generator = LookMLGenerator()
        view_dict = generator.generate_view(model)

        assert "views" in view_dict
        view = view_dict["views"][0]

        # Should use first variant in list (starts_at_local)
        dimension_groups = view.get("dimension_groups", [])
        dim_group_names = [dg["name"] for dg in dimension_groups]
        # First in the list becomes the "primary"
        assert "starts_at_local" in dim_group_names

    def test_mixed_timezone_variant_and_normal_dimensions(self):
        """Test model with both timezone variant and normal dimensions."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_utc",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="utc",
                            is_primary=True,
                        )
                        )
                    ),
                ),
                Dimension(
                    name="starts_at_local",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_local",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                            canonical_name="starts_at",
                            variant="local",
                            is_primary=False,
                        )
                        )
                    ),
                ),
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                ),
                Dimension(
                    name="category",
                    type=DimensionType.CATEGORICAL,
                ),
            ],
        )

        generator = LookMLGenerator()
        view_dict = generator.generate_view(model)

        assert "views" in view_dict
        view = view_dict["views"][0]

        # Should have parameter for timezone variants
        assert "parameter" in view
        assert view["parameter"][0]["name"] == "timezone_selector"

        # Should have toggleable starts_at
        dimension_groups = view.get("dimension_groups", [])
        dim_group_names = [dg["name"] for dg in dimension_groups]
        assert "starts_at" in dim_group_names
        assert "starts_at_local" not in dim_group_names

        # Should have normal created_at
        assert "created_at" in dim_group_names

        # Should have normal category dimension
        dimensions = view.get("dimensions", [])
        dim_names = [d["name"] for d in dimensions]
        assert "category" in dim_names


class TestHasTimezoneVariants:
    """Test _has_timezone_variants helper method."""

    def test_has_timezone_variants_true(self):
        """Test returns True when model has valid timezone variant pairs."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                                canonical_name="starts_at",
                                variant="utc",
                                is_primary=True,
                            )
                        )
                    ),
                ),
                Dimension(
                    name="starts_at_local",
                    type=DimensionType.TIME,
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                                canonical_name="starts_at",
                                variant="local",
                                is_primary=False,
                            )
                        )
                    ),
                ),
            ],
        )

        generator = LookMLGenerator()
        assert generator._has_timezone_variants(model) is True

    def test_has_timezone_variants_false_no_variants(self):
        """Test returns False when model has no timezone variants."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                ),
            ],
        )

        generator = LookMLGenerator()
        assert generator._has_timezone_variants(model) is False

    def test_has_timezone_variants_false_single_variant(self):
        """Test returns False when only one variant exists (needs 2+ to toggle)."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                                canonical_name="starts_at",
                                variant="utc",
                                is_primary=True,
                            )
                        )
                    ),
                ),
            ],
        )

        generator = LookMLGenerator()
        assert generator._has_timezone_variants(model) is False


class TestTimezoneVariantGroupLabel:
    """Test group_label integration with timezone_selector parameter."""

    def test_view_generation_includes_group_label(self):
        """Test that generated view includes group_label on timezone_selector."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_utc",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                                canonical_name="starts_at",
                                variant="utc",
                                is_primary=True,
                            )
                        )
                    ),
                ),
                Dimension(
                    name="starts_at_local",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_local",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                                canonical_name="starts_at",
                                variant="local",
                                is_primary=False,
                            )
                        )
                    ),
                ),
            ],
        )

        generator = LookMLGenerator()
        view_dict = generator.generate_view(model)

        view = view_dict["views"][0]
        assert "parameter" in view
        param = view["parameter"][0]
        assert param["group_label"] == GROUP_LABEL_DATE_DIMENSIONS  # Leading space for sort order

    def test_view_generation_custom_group_label(self):
        """Test that custom time_dimension_group_label is applied."""
        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[],
            dimensions=[
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_utc",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                                canonical_name="starts_at",
                                variant="utc",
                                is_primary=True,
                            )
                        )
                    ),
                ),
                Dimension(
                    name="starts_at_local",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_local",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                                canonical_name="starts_at",
                                variant="local",
                                is_primary=False,
                            )
                        )
                    ),
                ),
            ],
        )

        generator = LookMLGenerator(time_dimension_group_label="Custom Time Fields")
        view_dict = generator.generate_view(model)

        view = view_dict["views"][0]
        param = view["parameter"][0]
        assert param["group_label"] == "Custom Time Fields"


class TestTimezoneVariantAlwaysFilter:
    """Test always_filter generation for explores with timezone variants."""

    def test_explore_with_timezone_variants_has_always_filter(self):
        """Test that explores with timezone variants include always_filter."""
        from dbt_to_lookml.schemas.semantic_layer import Entity

        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[
                Entity(name="rental_id", type="primary"),
            ],
            dimensions=[
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_utc",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                                canonical_name="starts_at",
                                variant="utc",
                                is_primary=True,
                            )
                        )
                    ),
                ),
                Dimension(
                    name="starts_at_local",
                    type=DimensionType.TIME,
                    expr="rental_starts_at_local",
                    config=Config(
                        meta=ConfigMeta(
                            timezone_variant=TimezoneVariant(
                                canonical_name="starts_at",
                                variant="local",
                                is_primary=False,
                            )
                        )
                    ),
                ),
            ],
            measures=[],
        )

        generator = LookMLGenerator(fact_models=["rentals"])
        explores_content = generator._generate_explores_lookml([model])

        # Verify always_filter is in the output
        assert "always_filter" in explores_content
        assert "timezone_selector" in explores_content

    def test_explore_without_timezone_variants_no_always_filter(self):
        """Test that explores without timezone variants don't have always_filter."""
        from dbt_to_lookml.schemas.semantic_layer import Entity

        model = SemanticModel(
            name="rentals",
            model="schema.rentals",
            entities=[
                Entity(name="rental_id", type="primary"),
            ],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                ),
            ],
            measures=[],
        )

        generator = LookMLGenerator(fact_models=["rentals"])
        explores_content = generator._generate_explores_lookml([model])

        # Verify always_filter is NOT in the output
        assert "always_filter" not in explores_content
