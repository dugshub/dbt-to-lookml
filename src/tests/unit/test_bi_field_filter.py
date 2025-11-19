"""Unit tests for bi_field filtering in LookMLGenerator.

Tests the bi_field opt-in mechanism for selective field exposure in explores.
"""

import pytest

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.schemas.config import Config, ConfigMeta
from dbt_to_lookml.schemas.semantic_layer import (
    Dimension,
    DimensionType,
    Entity,
    Measure,
    AggregationType,
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
        # When disabled, should return original list
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

        assert result_default == result_false == fields


class TestBiFieldFilterEnabled:
    """Test bi_field filtering when enabled."""

    def test_filtering_enabled(self):
        """Test that bi_field filtering can be enabled."""
        generator = LookMLGenerator(use_bi_field_filter=True)
        assert generator.use_bi_field_filter is True

    def test_primary_keys_always_included(self, sample_model):
        """Test that primary keys are always included regardless of bi_field."""
        generator = LookMLGenerator(use_bi_field_filter=True)
        fields = ["orders.dimensions_only*"]
        result = generator._filter_fields_by_bi_field(sample_model, fields)

        # Primary key should always be included
        assert any("order_id" in field for field in result)

    def test_bi_field_true_included(self, sample_model):
        """Test that fields with bi_field: true are included."""
        generator = LookMLGenerator(use_bi_field_filter=True)
        fields = ["orders.dimensions_only*"]
        result = generator._filter_fields_by_bi_field(sample_model, fields)

        # Fields marked as bi_field: true should be included
        assert any("customer_id" in field for field in result)
        assert any("revenue" in field for field in result)

    def test_bi_field_false_excluded(self, sample_model):
        """Test that fields with bi_field: false are excluded."""
        generator = LookMLGenerator(use_bi_field_filter=True)
        fields = ["orders.dimensions_only*"]
        result = generator._filter_fields_by_bi_field(sample_model, fields)

        # Fields marked as bi_field: false should be excluded
        assert not any("internal_notes" in field for field in result)
        assert not any("internal_cost" in field for field in result)

    def test_bi_field_none_excluded(self):
        """Test that fields without bi_field setting are excluded."""
        generator = LookMLGenerator(use_bi_field_filter=True)
        model = SemanticModel(
            name="test",
            model="ref('test')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(name="no_bi_field", type=DimensionType.CATEGORICAL),
            ],
        )
        fields = ["test.dimensions_only*"]
        result = generator._filter_fields_by_bi_field(model, fields)

        # Should only have primary key (no_bi_field dimension excluded)
        assert len(result) == 1
        assert "id" in result[0]


class TestBiFieldFilterViewPrefix:
    """Test bi_field filtering with view prefixes."""

    def test_filter_respects_view_prefix(self):
        """Test that filtering includes view_prefix in field names."""
        generator = LookMLGenerator(view_prefix="stg_", use_bi_field_filter=True)
        model = SemanticModel(
            name="orders",
            model="ref('orders')",
            entities=[Entity(name="order_id", type="primary")],
            dimensions=[
                Dimension(
                    name="status",
                    type=DimensionType.CATEGORICAL,
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
            ],
        )
        fields = ["stg_orders.dimensions_only*"]
        result = generator._filter_fields_by_bi_field(model, fields)

        # Should include view prefix
        assert any("stg_orders" in field for field in result)
        assert any("status" in field for field in result)


class TestBiFieldFilterMinimumFields:
    """Test minimum field inclusion when bi_field filtering."""

    def test_minimum_primary_key_when_no_bi_fields(self):
        """Test that at least primary key is returned even if no bi_fields."""
        generator = LookMLGenerator(use_bi_field_filter=True)
        model = SemanticModel(
            name="empty",
            model="ref('empty')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
                Dimension(
                    name="no_bi_field",
                    type=DimensionType.CATEGORICAL,
                )
            ],
        )
        fields = ["empty.dimensions_only*"]
        result = generator._filter_fields_by_bi_field(model, fields)

        # Should at minimum return primary key
        assert len(result) >= 1
        assert any("id" in field for field in result)


class TestBiFieldFilterComplexModel:
    """Test bi_field filtering with complex models."""

    def test_multiple_entity_types(self):
        """Test filtering with multiple entity types."""
        generator = LookMLGenerator(use_bi_field_filter=True)
        model = SemanticModel(
            name="complex",
            model="ref('complex')",
            entities=[
                Entity(name="order_id", type="primary"),
                Entity(name="customer_id", type="foreign"),
                Entity(name="product_id", type="foreign"),
            ],
            dimensions=[
                Dimension(
                    name="status",
                    type=DimensionType.CATEGORICAL,
                    config=Config(meta=ConfigMeta(bi_field=True)),
                ),
            ],
        )
        fields = ["complex.dimensions_only*"]
        result = generator._filter_fields_by_bi_field(model, fields)

        # Should include primary key
        assert any("order_id" in field for field in result)
        # Should include bi_field dimension
        assert any("status" in field for field in result)

    def test_mixed_time_and_categorical_dimensions(self):
        """Test filtering with mixed dimension types."""
        generator = LookMLGenerator(use_bi_field_filter=True)
        model = SemanticModel(
            name="mixed",
            model="ref('mixed')",
            entities=[Entity(name="id", type="primary")],
            dimensions=[
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
        fields = ["mixed.dimensions_only*"]
        result = generator._filter_fields_by_bi_field(model, fields)

        # Should include time dimension with bi_field
        assert any("created_at" in field for field in result)
        # Should exclude hidden metadata
        assert not any("hidden_metadata" in field for field in result)


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

        # Should return at least primary key
        assert len(result) >= 1

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
