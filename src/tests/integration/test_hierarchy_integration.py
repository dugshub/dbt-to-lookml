"""Integration tests for hierarchy labeling end-to-end."""

from pathlib import Path
from tempfile import TemporaryDirectory

import lkml
import yaml

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser


class TestHierarchyIntegration:
    """Integration tests for hierarchy-based labeling."""

    def test_end_to_end_hierarchy_generation(self) -> None:
        """Test complete flow from YAML with hierarchy to LookML output."""

        # Create test semantic model with hierarchy
        semantic_model_data = {
            "semantic_models": [
                {
                    "name": "rental_analytics",
                    "model": "ref('fct_rentals')",
                    "description": "Rental analytics model",
                    "entities": [
                        {"name": "rental_id", "type": "primary", "expr": "rental_id"}
                    ],
                    "dimensions": [
                        {
                            "name": "booking_status",
                            "type": "categorical",
                            "expr": "status",
                            "description": "Current booking status",
                            "config": {
                                "meta": {
                                    "hierarchy": {
                                        "entity": "rental",
                                        "category": "booking",
                                        "subcategory": "booking_status",
                                    }
                                }
                            },
                        },
                        {
                            "name": "facility_type",
                            "type": "categorical",
                            "expr": "parking_type",
                            "description": "Type of parking facility",
                            "config": {
                                "meta": {
                                    "hierarchy": {
                                        "entity": "facility",
                                        "category": "facility",
                                        "subcategory": "facility_type",
                                    }
                                }
                            },
                        },
                        {
                            "name": "created_date",
                            "type": "time",
                            "expr": "created_at",
                            "description": "Rental creation date",
                            "config": {
                                "meta": {
                                    "hierarchy": {
                                        "entity": "rental",
                                        "category": "temporal",
                                        "subcategory": "booking_time",
                                    }
                                }
                            },
                        },
                    ],
                    "measures": [
                        {
                            "name": "total_revenue",
                            "agg": "sum",
                            "expr": "checkout_amount",
                            "description": "Total checkout revenue",
                            "config": {
                                "meta": {
                                    "hierarchy": {
                                        "entity": "rental",
                                        "category": "revenue",
                                        "subcategory": "booking_revenue",
                                    }
                                }
                            },
                        },
                        {
                            "name": "booking_count",
                            "agg": "count",
                            "expr": "rental_id",
                            "description": "Number of bookings",
                            "config": {
                                "meta": {
                                    "hierarchy": {
                                        "entity": "rental",
                                        "category": "volume",
                                        "subcategory": "booking_count",
                                    }
                                }
                            },
                        },
                        {
                            "name": "avg_lead_time",
                            "agg": "average",
                            "expr": "lead_time_hours",
                            "description": "Average lead time in hours",
                            "config": {
                                "meta": {
                                    "hierarchy": {
                                        "entity": "rental",
                                        "category": "operational",
                                        "subcategory": "lead_time",
                                    }
                                }
                            },
                        },
                    ],
                }
            ]
        }

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write semantic model to file
            yaml_file = temp_path / "rental_model.yml"
            with open(yaml_file, "w") as f:
                yaml.dump(semantic_model_data, f)

            # Parse the semantic model
            parser = DbtParser()
            models = parser.parse_file(yaml_file)

            assert len(models) == 1
            models[0]

            # Generate LookML
            generator = LookMLGenerator()
            output_dir = temp_path / "lookml"
            generated_files, errors = generator.generate_lookml_files(
                models, output_dir
            )

            assert len(errors) == 0
            assert len(generated_files) > 0

            # Read and parse the generated view file
            view_file = output_dir / "rental_analytics.view.lkml"
            assert view_file.exists()

            with open(view_file) as f:
                lookml_content = f.read()

            # Parse the LookML to verify structure
            parsed_lookml = lkml.load(lookml_content)
            assert "views" in parsed_lookml
            assert len(parsed_lookml["views"]) == 1

            view = parsed_lookml["views"][0]

            # Check dimensions have correct labels
            dimensions = view.get("dimensions", [])
            booking_status_dim = next(
                (d for d in dimensions if d["name"] == "booking_status"), None
            )
            assert booking_status_dim is not None
            assert booking_status_dim.get("view_label") == "Rental"
            assert booking_status_dim.get("group_label") == "Booking"

            facility_type_dim = next(
                (d for d in dimensions if d["name"] == "facility_type"), None
            )
            assert facility_type_dim is not None
            assert facility_type_dim.get("view_label") == "Facility"
            assert facility_type_dim.get("group_label") == "Facility"

            # Check dimension_groups have correct labels
            dimension_groups = view.get("dimension_groups", [])
            created_date_group = next(
                (d for d in dimension_groups if d["name"] == "created_date"), None
            )
            assert created_date_group is not None
            assert created_date_group.get("view_label") == "Rental"
            assert created_date_group.get("group_label") == "Temporal"

            # Check measures have correct labels (measures now have _measure suffix)
            measures = view.get("measures", [])

            revenue_measure = next(
                (m for m in measures if m["name"] == "total_revenue_measure"), None
            )
            assert revenue_measure is not None
            assert revenue_measure.get("view_label") == "Revenue"
            assert revenue_measure.get("group_label") == "Booking Revenue"

            count_measure = next(
                (m for m in measures if m["name"] == "booking_count_measure"), None
            )
            assert count_measure is not None
            assert count_measure.get("view_label") == "Volume"
            assert count_measure.get("group_label") == "Booking Count"

            avg_measure = next(
                (m for m in measures if m["name"] == "avg_lead_time_measure"), None
            )
            assert avg_measure is not None
            assert avg_measure.get("view_label") == "Operational"
            assert avg_measure.get("group_label") == "Lead Time"

    def test_mixed_hierarchy_and_no_hierarchy(self) -> None:
        """Test that fields with and without hierarchy work together."""

        semantic_model_data = {
            "semantic_models": [
                {
                    "name": "mixed_model",
                    "model": "ref('test_table')",
                    "dimensions": [
                        {
                            "name": "with_hierarchy",
                            "type": "categorical",
                            "expr": "field1",
                            "config": {
                                "meta": {
                                    "hierarchy": {
                                        "entity": "rental",
                                        "category": "booking",
                                        "subcategory": "booking_type",
                                    }
                                }
                            },
                        },
                        {
                            "name": "without_hierarchy",
                            "type": "categorical",
                            "expr": "field2",
                            "description": "Field without hierarchy",
                        },
                    ],
                    "measures": [
                        {
                            "name": "measure_with_hierarchy",
                            "agg": "sum",
                            "expr": "amount",
                            "config": {
                                "meta": {
                                    "hierarchy": {
                                        "entity": "rental",
                                        "category": "revenue",
                                        "subcategory": "net_revenue",
                                    }
                                }
                            },
                        },
                        {
                            "name": "measure_without_hierarchy",
                            "agg": "count",
                            "expr": "id",
                        },
                    ],
                }
            ]
        }

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            yaml_file = temp_path / "mixed_model.yml"
            with open(yaml_file, "w") as f:
                yaml.dump(semantic_model_data, f)

            parser = DbtParser()
            models = parser.parse_file(yaml_file)

            generator = LookMLGenerator()
            output_dir = temp_path / "lookml"
            generated_files, errors = generator.generate_lookml_files(
                models, output_dir
            )

            assert len(errors) == 0

            view_file = output_dir / "mixed_model.view.lkml"
            with open(view_file) as f:
                lookml_content = f.read()

            parsed_lookml = lkml.load(lookml_content)
            view = parsed_lookml["views"][0]

            # Check that fields with hierarchy have labels
            dimensions = view.get("dimensions", [])
            with_hierarchy = next(
                (d for d in dimensions if d["name"] == "with_hierarchy"), None
            )
            assert with_hierarchy.get("view_label") == "Rental"
            assert with_hierarchy.get("group_label") == "Booking"

            # Check that fields without hierarchy don't have labels
            without_hierarchy = next(
                (d for d in dimensions if d["name"] == "without_hierarchy"), None
            )
            assert "view_label" not in without_hierarchy
            assert "group_label" not in without_hierarchy

            # Same for measures (measures now have _measure suffix)
            measures = view.get("measures", [])
            measure_with = next(
                (m for m in measures if m["name"] == "measure_with_hierarchy_measure"), None
            )
            assert measure_with.get("view_label") == "Revenue"
            assert measure_with.get("group_label") == "Net Revenue"

            measure_without = next(
                (m for m in measures if m["name"] == "measure_without_hierarchy_measure"), None
            )
            # Measures without hierarchy get default "  Metrics" view_label (2 spaces)
            # and model_name-based group_label as fallback
            assert measure_without.get("view_label") == "  Metrics"
            assert measure_without.get("group_label") == "Mixed Model Performance"
