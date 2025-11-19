"""Unit tests for hidden parameter support in field visibility control.

Tests the hidden parameter functionality across all field types (dimensions,
measures, metrics) and ensures proper LookML output generation.
"""

import pytest

from dbt_to_lookml.schemas.config import Config, ConfigMeta
from dbt_to_lookml.schemas.semantic_layer import (
    Dimension,
    DimensionType,
    Measure,
    AggregationType,
)


class TestHiddenParameterDimension:
    """Test cases for hidden parameter on dimensions."""

    def test_dimension_with_hidden_true(self):
        """Test dimension with hidden=true generates hidden: yes."""
        dim = Dimension(
            name="internal_id",
            type=DimensionType.CATEGORICAL,
            config=Config(meta=ConfigMeta(hidden=True)),
        )
        result = dim.to_lookml_dict()
        assert result["hidden"] == "yes"
        assert result["name"] == "internal_id"

    def test_dimension_with_hidden_false(self):
        """Test dimension with hidden=false doesn't add hidden parameter."""
        dim = Dimension(
            name="public_id",
            type=DimensionType.CATEGORICAL,
            config=Config(meta=ConfigMeta(hidden=False)),
        )
        result = dim.to_lookml_dict()
        assert "hidden" not in result

    def test_dimension_without_hidden(self):
        """Test dimension without hidden field doesn't add parameter."""
        dim = Dimension(
            name="normal_dim",
            type=DimensionType.CATEGORICAL,
        )
        result = dim.to_lookml_dict()
        assert "hidden" not in result

    def test_dimension_with_hidden_and_description(self):
        """Test hidden parameter works with other metadata."""
        dim = Dimension(
            name="hidden_internal",
            type=DimensionType.CATEGORICAL,
            description="Internal use only",
            label="Internal ID",
            config=Config(meta=ConfigMeta(hidden=True)),
        )
        result = dim.to_lookml_dict()
        assert result["hidden"] == "yes"
        assert result["description"] == "Internal use only"
        assert result["label"] == "Internal ID"


class TestHiddenParameterDimensionGroup:
    """Test cases for hidden parameter on time dimensions (dimension_groups)."""

    def test_time_dimension_with_hidden_true(self):
        """Test time dimension with hidden=true generates hidden: yes."""
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(hidden=True)),
        )
        result = dim.to_lookml_dict()
        assert result["hidden"] == "yes"
        assert result["type"] == "time"
        assert result["name"] == "created_at"

    def test_time_dimension_with_hidden_and_convert_tz(self):
        """Test hidden parameter works with convert_tz."""
        dim = Dimension(
            name="updated_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "hour"},
            config=Config(
                meta=ConfigMeta(hidden=True, convert_tz=True)
            ),
        )
        result = dim.to_lookml_dict()
        assert result["hidden"] == "yes"
        assert result["convert_tz"] == "yes"

    def test_time_dimension_without_hidden(self):
        """Test time dimension without hidden doesn't add parameter."""
        dim = Dimension(
            name="shipped_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )
        result = dim.to_lookml_dict()
        assert "hidden" not in result


class TestHiddenParameterMeasure:
    """Test cases for hidden parameter on measures."""

    def test_measure_with_hidden_true(self):
        """Test measure with hidden=true generates hidden: yes."""
        measure = Measure(
            name="total_revenue",
            agg=AggregationType.SUM,
            config=Config(meta=ConfigMeta(hidden=True)),
        )
        result = measure.to_lookml_dict()
        assert result["hidden"] == "yes"
        assert result["name"] == "total_revenue"

    def test_measure_with_hidden_false(self):
        """Test measure with hidden=false doesn't add hidden parameter."""
        measure = Measure(
            name="order_count",
            agg=AggregationType.COUNT,
            config=Config(meta=ConfigMeta(hidden=False)),
        )
        result = measure.to_lookml_dict()
        assert "hidden" not in result

    def test_measure_without_hidden(self):
        """Test measure without hidden doesn't add parameter."""
        measure = Measure(
            name="average_price",
            agg=AggregationType.AVERAGE,
        )
        result = measure.to_lookml_dict()
        assert "hidden" not in result

    def test_measure_with_hidden_and_label(self):
        """Test hidden parameter works with measure label."""
        measure = Measure(
            name="internal_cost",
            agg=AggregationType.SUM,
            label="Cost (Internal)",
            description="Internal cost tracking",
            config=Config(meta=ConfigMeta(hidden=True)),
        )
        result = measure.to_lookml_dict()
        assert result["hidden"] == "yes"
        assert result["label"] == "Cost (Internal)"
        assert result["description"] == "Internal cost tracking"


class TestHiddenParameterBackwardCompatibility:
    """Test backward compatibility of hidden parameter."""

    def test_existing_dimensions_unaffected(self):
        """Test that existing dimensions without hidden are unaffected."""
        dim = Dimension(
            name="customer_id",
            type=DimensionType.CATEGORICAL,
            label="Customer",
        )
        result = dim.to_lookml_dict()
        assert result["name"] == "customer_id"
        assert result["label"] == "Customer"
        assert "hidden" not in result

    def test_existing_measures_unaffected(self):
        """Test that existing measures without hidden are unaffected."""
        measure = Measure(
            name="revenue",
            agg=AggregationType.SUM,
            label="Total Revenue",
        )
        result = measure.to_lookml_dict()
        assert result["name"] == "revenue"
        assert result["label"] == "Total Revenue"
        assert "hidden" not in result

    def test_configmeta_none_hidden(self):
        """Test ConfigMeta with no hidden field."""
        meta = ConfigMeta(domain="sales", owner="analytics")
        assert meta.hidden is None
        assert meta.domain == "sales"

    def test_no_config_no_hidden(self):
        """Test dimension with no config doesn't have hidden."""
        dim = Dimension(
            name="test_dim",
            type=DimensionType.CATEGORICAL,
        )
        result = dim.to_lookml_dict()
        assert "hidden" not in result


class TestHiddenParameterEdgeCases:
    """Test edge cases for hidden parameter."""

    def test_hidden_none_vs_false(self):
        """Test that hidden: None and hidden: False behave the same."""
        dim_none = Dimension(
            name="dim1",
            type=DimensionType.CATEGORICAL,
            config=Config(meta=ConfigMeta(hidden=None)),
        )
        dim_false = Dimension(
            name="dim2",
            type=DimensionType.CATEGORICAL,
            config=Config(meta=ConfigMeta(hidden=False)),
        )
        assert "hidden" not in dim_none.to_lookml_dict()
        assert "hidden" not in dim_false.to_lookml_dict()

    def test_hidden_with_all_metadata(self):
        """Test hidden parameter with complete metadata."""
        dim = Dimension(
            name="full_metadata",
            type=DimensionType.CATEGORICAL,
            description="Test dimension",
            label="Full Metadata",
            config=Config(
                meta=ConfigMeta(
                    hidden=True,
                    domain="test",
                    owner="team",
                    subject="dimensions",
                    category="test_category",
                )
            ),
        )
        result = dim.to_lookml_dict()
        assert result["hidden"] == "yes"
        assert result["description"] == "Test dimension"
        assert result["label"] == "Full Metadata"

    def test_multiple_hidden_dimensions_in_list(self):
        """Test multiple dimensions with mixed hidden settings."""
        dims = [
            Dimension(
                name="visible",
                type=DimensionType.CATEGORICAL,
                config=Config(meta=ConfigMeta(hidden=False)),
            ),
            Dimension(
                name="hidden",
                type=DimensionType.CATEGORICAL,
                config=Config(meta=ConfigMeta(hidden=True)),
            ),
            Dimension(
                name="default",
                type=DimensionType.CATEGORICAL,
            ),
        ]
        results = [d.to_lookml_dict() for d in dims]
        assert "hidden" not in results[0]
        assert results[1]["hidden"] == "yes"
        assert "hidden" not in results[2]
