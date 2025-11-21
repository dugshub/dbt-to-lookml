"""Unit tests for bi_field filtering in LookMLGenerator.

Tests the bi_field opt-in mechanism for selective field exposure in views.
Filtering now happens at view generation time via SemanticModel.to_lookml_dict().
"""

import pytest

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.schemas.config import Config, ConfigMeta
from dbt_to_lookml.schemas.semantic_layer import (
    AggregationType,
    Dimension,
    DimensionType,
    Entity,
    Measure,
    SemanticModel,
)


@pytest.fixture
def sample_model():
    """Create a sample semantic model with mixed field configurations."""
    return SemanticModel(
        name="orders",
        model="ref('orders')",
        entities=[
            Entity(name="order_id", type="primary"),
        ],
        dimensions=[
            Dimension(
                name="customer_id",
                type=DimensionType.CATEGORICAL,
                config=Config(meta=ConfigMeta(bi_field=True)),
            ),
            Dimension(
                name="internal_notes",
                type=DimensionType.CATEGORICAL,
                config=Config(meta=ConfigMeta(bi_field=False)),
            ),
            Dimension(
                name="order_date",
                type=DimensionType.TIME,
                type_params={"time_granularity": "day"},
                config=Config(meta=ConfigMeta(bi_field=True)),
            ),
        ],
        measures=[
            Measure(
                name="revenue",
                agg=AggregationType.SUM,
                config=Config(meta=ConfigMeta(bi_field=True)),
            ),
            Measure(
                name="internal_cost",
                agg=AggregationType.SUM,
                config=Config(meta=ConfigMeta(bi_field=False)),
            ),
        ],
    )


class TestBiFieldFilterDisabled:
    """Test bi_field filtering when disabled (default behavior)."""

    def test_filtering_disabled_by_default(self):
        """Test that bi_field filtering is disabled by default."""
        generator = LookMLGenerator()
        assert generator.use_bi_field_filter is False

    def test_no_filtering_when_disabled(self, sample_model):
        """Test that all fields are returned when filtering is disabled."""
        generator = LookMLGenerator(use_bi_field_filter=False)
        fields = ["orders.dimensions_only*"]
        result = generator._filter_fields_by_bi_field(sample_model, fields)
        # When disabled, method should return original list unchanged
        assert result == fields

    def test_backward_compatibility(self, sample_model):
        """Test backward compatibility - default behavior unchanged."""
        generator_default = LookMLGenerator()
        generator_explicit_false = LookMLGenerator(use_bi_field_filter=False)

        fields = ["orders.dimensions_only*"]
        result_default = generator_default._filter_fields_by_bi_field(
            sample_model, fields
        )
        result_false = generator_explicit_false._filter_fields_by_bi_field(
            sample_model, fields
        )

        # Both should return original list unchanged
        assert result_default == result_false == fields


class TestBiFieldFilterViewGeneration:
    """Test bi_field filtering at view generation time."""

    def test_filtering_disabled_includes_all_fields(self):
        """Test that without filtering, all fields appear in view."""
        model = SemanticModel(
            name="test",
            model="ref('test')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(
                    name="field1",
                    type=DimensionType.CATEGORICAL,
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
                Dimension(
                    name="field2",
                    type=DimensionType.CATEGORICAL,
                    config=Config(meta=ConfigMeta(bi_field=False)),
                ),
                Dimension(name="field3", type=DimensionType.CATEGORICAL),
            ],
        )

        view_dict = model.to_lookml_dict(use_bi_field_filter=False)

        # All dimensions should be present (1 entity + 3 dimensions)
        assert len(view_dict["views"][0]["dimensions"]) == 4

        # dimensions_only set should include all
        dim_set = view_dict["views"][0]["sets"][0]
        assert "id" in dim_set["fields"]
        assert "field1" in dim_set["fields"]
        assert "field2" in dim_set["fields"]
        assert "field3" in dim_set["fields"]

    def test_filtering_enabled_only_bi_field_true(self):
        """Test that with filtering, only bi_field: true fields appear."""
        model = SemanticModel(
            name="test",
            model="ref('test')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(
                    name="field1",
                    type=DimensionType.CATEGORICAL,
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
                Dimension(
                    name="field2",
                    type=DimensionType.CATEGORICAL,
                    config=Config(meta=ConfigMeta(bi_field=False)),
                ),
                Dimension(name="field3", type=DimensionType.CATEGORICAL),
            ],
            measures=[
                Measure(
                    name="metric1",
                    agg=AggregationType.SUM,
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
                Measure(
                    name="metric2",
                    agg=AggregationType.SUM,
                    config=Config(meta=ConfigMeta(bi_field=False)),
                ),
            ],
        )

        view_dict = model.to_lookml_dict(use_bi_field_filter=True)

        # Only bi_field: true dimensions (+ entities always included)
        assert len(view_dict["views"][0]["dimensions"]) == 2  # 1 entity + 1 bi_field dim

        # Only bi_field: true measures
        assert len(view_dict["views"][0]["measures"]) == 1

        # dimensions_only set should only include bi_field: true + entities
        dim_set = view_dict["views"][0]["sets"][0]
        assert "id" in dim_set["fields"]  # Entity always included
        assert "field1" in dim_set["fields"]  # bi_field: true
        assert "field2" not in dim_set["fields"]  # bi_field: false
        assert "field3" not in dim_set["fields"]  # no bi_field

    def test_entities_always_included_when_filtering(self):
        """Test that entities are always included regardless of bi_field."""
        model = SemanticModel(
            name="test",
            model="ref('test')",
            entities=[
                Entity(name="primary_id", type="primary"),
                Entity(name="foreign_id", type="foreign"),
            ],
            dimensions=[
                Dimension(
                    name="visible_field",
                    type=DimensionType.CATEGORICAL,
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
            ],
        )

        view_dict = model.to_lookml_dict(use_bi_field_filter=True)

        # Should have 2 entities + 1 dimension
        assert len(view_dict["views"][0]["dimensions"]) == 3

        # dimensions_only set should include both entities
        dim_set = view_dict["views"][0]["sets"][0]
        assert "primary_id" in dim_set["fields"]
        assert "foreign_id" in dim_set["fields"]
        assert "visible_field" in dim_set["fields"]

    def test_time_dimensions_with_filtering(self):
        """Test that time dimensions respect bi_field filtering."""
        model = SemanticModel(
            name="test",
            model="ref('test')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
                Dimension(
                    name="hidden_timestamp",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                    config=Config(meta=ConfigMeta(bi_field=False)),
                ),
            ],
        )

        view_dict = model.to_lookml_dict(use_bi_field_filter=True)

        # Should have 1 entity dimension
        assert len(view_dict["views"][0]["dimensions"]) == 1

        # Should have 1 dimension_group (only created_at)
        assert len(view_dict["views"][0]["dimension_groups"]) == 1
        assert view_dict["views"][0]["dimension_groups"][0]["name"] == "created_at"

        # dimensions_only set should include created_at timeframes but not hidden_timestamp
        dim_set = view_dict["views"][0]["sets"][0]
        assert "created_at_date" in dim_set["fields"]
        assert "created_at_week" in dim_set["fields"]
        assert "hidden_timestamp_date" not in dim_set["fields"]

    def test_no_bi_field_dimensions_excluded_when_filtering(self):
        """Test that dimensions without bi_field setting are excluded."""
        model = SemanticModel(
            name="test",
            model="ref('test')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(name="no_bi_field", type=DimensionType.CATEGORICAL),
                Dimension(
                    name="explicit_bi_field",
                    type=DimensionType.CATEGORICAL,
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
            ],
        )

        view_dict = model.to_lookml_dict(use_bi_field_filter=True)

        # Should have 1 entity + 1 explicit bi_field dimension
        assert len(view_dict["views"][0]["dimensions"]) == 2

        dim_set = view_dict["views"][0]["sets"][0]
        assert "id" in dim_set["fields"]
        assert "explicit_bi_field" in dim_set["fields"]
        assert "no_bi_field" not in dim_set["fields"]

    def test_empty_view_when_no_bi_fields(self):
        """Test that only entities remain when no bi_field: true fields."""
        model = SemanticModel(
            name="test",
            model="ref('test')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(
                    name="excluded1",
                    type=DimensionType.CATEGORICAL,
                    config=Config(meta=ConfigMeta(bi_field=False)),
                ),
                Dimension(name="excluded2", type=DimensionType.CATEGORICAL),
            ],
            measures=[
                Measure(
                    name="excluded_measure",
                    agg=AggregationType.SUM,
                    config=Config(meta=ConfigMeta(bi_field=False)),
                ),
            ],
        )

        view_dict = model.to_lookml_dict(use_bi_field_filter=True)

        # Should only have 1 entity dimension
        assert len(view_dict["views"][0]["dimensions"]) == 1
        assert view_dict["views"][0]["dimensions"][0]["name"] == "id"

        # Should have no measures
        assert "measures" not in view_dict["views"][0]

        # dimensions_only set should only have entity
        dim_set = view_dict["views"][0]["sets"][0]
        assert dim_set["fields"] == ["id"]


class TestBiFieldFilterValidation:
    """Test validation and error handling for bi_field filtering."""

    def test_empty_model_fields(self):
        """Test filtering with model that has no dimensions/measures."""
        generator = LookMLGenerator(use_bi_field_filter=True)
        model = SemanticModel(
            name="empty",
            model="ref('empty')",
            entities=[Entity(name="id", type="primary")],
        )
        fields = ["empty.dimensions_only*"]
        result = generator._filter_fields_by_bi_field(model, fields)

        # Method now returns fields unchanged (filtering at view generation)
        assert result == fields

    def test_none_fields_list(self):
        """Test filtering handles various field list scenarios."""
        generator = LookMLGenerator(use_bi_field_filter=False)
        model = SemanticModel(
            name="test",
            model="ref('test')",
            entities=[Entity(name="id", type="primary")],
        )
        # When disabled, should return as-is
        assert generator._filter_fields_by_bi_field(model, []) == []

    def test_filter_method_returns_unchanged_list(self):
        """Test that _filter_fields_by_bi_field now returns list unchanged."""
        generator_enabled = LookMLGenerator(use_bi_field_filter=True)
        generator_disabled = LookMLGenerator(use_bi_field_filter=False)

        model = SemanticModel(
            name="test",
            model="ref('test')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(
                    name="field1",
                    type=DimensionType.CATEGORICAL,
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
            ],
        )

        fields = ["test.dimensions_only*", "test.measures*"]

        # Both should return the same unchanged list (filtering happens elsewhere)
        result_enabled = generator_enabled._filter_fields_by_bi_field(model, fields)
        result_disabled = generator_disabled._filter_fields_by_bi_field(model, fields)

        assert result_enabled == result_disabled == fields


class TestBiFieldFilterMixedTypes:
    """Test bi_field filtering with mixed dimension and measure types."""

    def test_mixed_categorical_and_time_dimensions(self):
        """Test filtering with mixed dimension types."""
        model = SemanticModel(
            name="mixed",
            model="ref('mixed')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(
                    name="category",
                    type=DimensionType.CATEGORICAL,
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
                Dimension(
                    name="hidden_metadata",
                    type=DimensionType.CATEGORICAL,
                    config=Config(meta=ConfigMeta(bi_field=False)),
                ),
            ],
        )

        view_dict = model.to_lookml_dict(use_bi_field_filter=True)

        # Should have 1 entity + 1 categorical dimension
        assert len(view_dict["views"][0]["dimensions"]) == 2

        # Should have 1 time dimension_group
        assert len(view_dict["views"][0]["dimension_groups"]) == 1
        assert view_dict["views"][0]["dimension_groups"][0]["name"] == "created_at"

        # dimensions_only set should include both visible fields
        dim_set = view_dict["views"][0]["sets"][0]
        assert "id" in dim_set["fields"]
        assert "category" in dim_set["fields"]
        assert "created_at_date" in dim_set["fields"]
        assert "hidden_metadata" not in dim_set["fields"]

    def test_multiple_measures_with_filtering(self):
        """Test that measures are properly filtered."""
        model = SemanticModel(
            name="test",
            model="ref('test')",
            entities=[Entity(name="id", type="primary")],
            measures=[
                Measure(
                    name="revenue",
                    agg=AggregationType.SUM,
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
                Measure(
                    name="cost",
                    agg=AggregationType.SUM,
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
                Measure(
                    name="internal_metric",
                    agg=AggregationType.COUNT,
                    config=Config(meta=ConfigMeta(bi_field=False)),
                ),
                Measure(
                    name="no_bi_field_set",
                    agg=AggregationType.AVERAGE,
                ),
            ],
        )

        view_dict = model.to_lookml_dict(use_bi_field_filter=True)

        # Should have 2 measures with bi_field: true
        assert len(view_dict["views"][0]["measures"]) == 2

        measure_names = [m["name"] for m in view_dict["views"][0]["measures"]]
        assert "revenue_measure" in measure_names
        assert "cost_measure" in measure_names
        assert "internal_metric_measure" not in measure_names
        assert "no_bi_field_set_measure" not in measure_names
