"""Unit tests for hierarchy labeling functionality."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml

from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.schemas import (
    Config,
    ConfigMeta,
    Dimension,
    Hierarchy,
    Measure,
)
from dbt_to_lookml.types import (
    AggregationType,
    DimensionType,
)


class TestHierarchyLabeling:
    """Test cases for hierarchy-based labeling."""

    def test_dimension_hierarchy_labels(self) -> None:
        """Test that dimensions get correct view_label and group_label from hierarchy."""
        hierarchy = Hierarchy(
            entity="rental", category="booking", subcategory="booking_status"
        )
        config = Config(meta=ConfigMeta(hierarchy=hierarchy))

        dimension = Dimension(
            name="status",
            type=DimensionType.CATEGORICAL,
            expr="booking_status",
            config=config,
        )

        view_label, group_label = dimension.get_dimension_labels()
        assert view_label == "Rental"
        assert group_label == "Booking"

    def test_measure_hierarchy_labels(self) -> None:
        """Test that measures get correct view_label and group_label from hierarchy."""
        hierarchy = Hierarchy(
            entity="rental",  # Not used for measures
            category="revenue",
            subcategory="booking_revenue",
        )
        config = Config(meta=ConfigMeta(hierarchy=hierarchy))

        measure = Measure(
            name="total_checkout",
            agg=AggregationType.SUM,
            expr="checkout_amount",
            config=config,
        )

        view_label, group_label = measure.get_measure_labels()
        # With hierarchy: category → view_label, subcategory → group_label
        assert view_label == "Revenue"  # from category
        assert group_label == "Booking Revenue"  # from subcategory

    def test_dimension_lookml_with_hierarchy(self) -> None:
        """Test dimension LookML output includes hierarchy labels."""
        hierarchy = Hierarchy(
            entity="facility", category="facility", subcategory="facility_type"
        )
        config = Config(meta=ConfigMeta(hierarchy=hierarchy))

        dimension = Dimension(
            name="parking_type",
            type=DimensionType.CATEGORICAL,
            expr="facility_type",
            description="Type of parking facility",
            config=config,
        )

        lookml_dict = dimension.to_lookml_dict()
        assert lookml_dict["view_label"] == "Facility"
        assert lookml_dict["group_label"] == "Facility"
        assert lookml_dict["name"] == "parking_type"
        assert lookml_dict["sql"] == "facility_type"

    def test_measure_lookml_with_hierarchy(self) -> None:
        """Test measure LookML output includes hierarchy labels."""
        hierarchy = Hierarchy(
            entity="rental", category="volume", subcategory="booking_count"
        )
        config = Config(meta=ConfigMeta(hierarchy=hierarchy))

        measure = Measure(
            name="rental_count",
            agg=AggregationType.COUNT,
            expr="rental_id",
            description="Number of rentals",
            config=config,
        )

        lookml_dict = measure.to_lookml_dict()
        # With hierarchy: category → view_label, subcategory → group_label
        assert lookml_dict["view_label"] == "Volume"  # from category
        assert lookml_dict["group_label"] == "Booking Count"  # from subcategory
        assert lookml_dict["name"] == "rental_count"
        assert lookml_dict["type"] == "count"

    def test_time_dimension_with_hierarchy(self) -> None:
        """Test time dimension_group includes hierarchy labels."""
        hierarchy = Hierarchy(
            entity="rental", category="temporal", subcategory="booking_time"
        )
        config = Config(meta=ConfigMeta(hierarchy=hierarchy))

        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            expr="rental_created_date",
            config=config,
        )

        lookml_dict = dimension.to_lookml_dict()
        assert lookml_dict["view_label"] == "Rental"
        assert lookml_dict["group_label"] == "Temporal"
        assert lookml_dict["type"] == "time"
        assert "timeframes" in lookml_dict

    def test_no_hierarchy_no_labels(self) -> None:
        """Test that fields without hierarchy don't get labels."""
        dimension = Dimension(
            name="status", type=DimensionType.CATEGORICAL, expr="booking_status"
        )

        view_label, group_label = dimension.get_dimension_labels()
        assert view_label is None
        assert group_label is None

        lookml_dict = dimension.to_lookml_dict()
        assert "view_label" not in lookml_dict
        assert "group_label" not in lookml_dict

    def test_label_formatting(self) -> None:
        """Test that labels are properly formatted with title case."""
        hierarchy = Hierarchy(
            entity="renter_profile",
            category="customer_behavior",
            subcategory="repeat_rate",
        )
        config = Config(meta=ConfigMeta(hierarchy=hierarchy))

        dimension = Dimension(
            name="is_repeat", type=DimensionType.CATEGORICAL, config=config
        )

        view_label, group_label = dimension.get_dimension_labels()
        assert view_label == "Renter Profile"
        assert group_label == "Customer Behavior"

    def test_parser_with_hierarchy(self) -> None:
        """Test that parser correctly extracts hierarchy from YAML."""
        parser = DbtParser()

        model_data = {
            "semantic_models": [
                {
                    "name": "test_model",
                    "model": "ref('test_table')",
                    "dimensions": [
                        {
                            "name": "status",
                            "type": "categorical",
                            "expr": "booking_status",
                            "config": {
                                "meta": {
                                    "hierarchy": {
                                        "entity": "rental",
                                        "category": "booking",
                                        "subcategory": "booking_status",
                                    }
                                }
                            },
                        }
                    ],
                    "measures": [
                        {
                            "name": "total_revenue",
                            "agg": "sum",
                            "expr": "revenue",
                            "config": {
                                "meta": {
                                    "hierarchy": {
                                        "entity": "rental",
                                        "category": "revenue",
                                        "subcategory": "booking_revenue",
                                    }
                                }
                            },
                        }
                    ],
                }
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert len(model.dimensions) == 1
            assert len(model.measures) == 1

            # Check dimension hierarchy
            dim = model.dimensions[0]
            assert dim.config is not None
            assert dim.config.meta is not None
            assert dim.config.meta.hierarchy is not None
            assert dim.config.meta.hierarchy.entity == "rental"
            assert dim.config.meta.hierarchy.category == "booking"

            # Check measure hierarchy
            measure = model.measures[0]
            assert measure.config is not None
            assert measure.config.meta is not None
            assert measure.config.meta.hierarchy is not None
            assert measure.config.meta.hierarchy.category == "revenue"
            assert measure.config.meta.hierarchy.subcategory == "booking_revenue"

        finally:
            temp_path.unlink()
