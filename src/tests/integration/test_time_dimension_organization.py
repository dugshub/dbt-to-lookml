"""Integration tests for time dimension organization with group_label."""

from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser


def test_multiple_time_dimensions_with_group_label() -> None:
    """Test that multiple time dimensions all get same group_label."""
    # Arrange - semantic model with multiple time dimensions
    semantic_model_data = {
        "semantic_models": [
            {
                "name": "orders",
                "model": "ref('orders')",
                "entities": [{"name": "order_id", "type": "primary"}],
                "dimensions": [
                    {
                        "name": "created_at",
                        "type": "time",
                        "type_params": {"time_granularity": "day"},
                        "config": {
                            "meta": {"time_dimension_group_label": "Event Times"}
                        },
                    },
                    {
                        "name": "updated_at",
                        "type": "time",
                        "type_params": {"time_granularity": "day"},
                        # No metadata - should use generator default
                    },
                    {
                        "name": "shipped_at",
                        "type": "time",
                        "type_params": {"time_granularity": "day"},
                        "config": {
                            "meta": {
                                "time_dimension_group_label": ""
                            }  # Explicitly disabled
                        },
                    },
                ],
                "measures": [{"name": "order_count", "agg": "count"}],
            }
        ]
    }

    with TemporaryDirectory() as tmp_dir:
        # Write semantic model to YAML
        yaml_file = Path(tmp_dir) / "orders.yaml"
        yaml_file.write_text(yaml.dump(semantic_model_data))

        # Parse and generate
        parser = DbtParser()
        models = parser.parse_directory(Path(tmp_dir))

        generator = LookMLGenerator(
            schema="public",
            time_dimension_group_label="Order Times",  # Generator default
        )
        output = generator.generate(models)

        # Assert
        view_content = output["orders.view.lkml"]

        # created_at should use metadata override (with 1 space prefix)
        assert "dimension_group: created_at" in view_content
        assert view_content.index("dimension_group: created_at") < view_content.index(
            'group_label: " Event Times"'
        )

        # updated_at should use generator default (with 1 space prefix)
        assert "dimension_group: updated_at" in view_content
        assert view_content.index("dimension_group: updated_at") < view_content.index(
            'group_label: " Order Times"'
        )

        # shipped_at should have NO group_label (explicitly disabled)
        # Verify that the shipped_at dimension_group doesn't have a group_label
        shipped_at_start = view_content.index("dimension_group: shipped_at")
        # Find the end of the shipped_at block (next measure or set)
        shipped_at_end = min(
            (
                view_content.index("measure:", shipped_at_start)
                if "measure:" in view_content[shipped_at_start:]
                else len(view_content)
            ),
            (
                view_content.index("set:", shipped_at_start)
                if "set:" in view_content[shipped_at_start:]
                else len(view_content)
            ),
        )
        shipped_at_block = view_content[shipped_at_start:shipped_at_end]
        assert "group_label:" not in shipped_at_block


def test_time_dimension_group_label_with_hierarchy() -> None:
    """Test that hierarchy group_label takes precedence over time group_label."""
    # Arrange
    semantic_model_data = {
        "semantic_models": [
            {
                "name": "events",
                "model": "ref('events')",
                "entities": [{"name": "event_id", "type": "primary"}],
                "dimensions": [
                    {
                        "name": "event_timestamp",
                        "type": "time",
                        "type_params": {"time_granularity": "hour"},
                        "config": {
                            "meta": {
                                "hierarchy": {"category": "event_tracking"},
                                "time_dimension_group_label": "Time Dimensions",  # Should be ignored
                            }
                        },
                    }
                ],
                "measures": [{"name": "event_count", "agg": "count"}],
            }
        ]
    }

    with TemporaryDirectory() as tmp_dir:
        # Write semantic model to YAML
        yaml_file = Path(tmp_dir) / "events.yaml"
        yaml_file.write_text(yaml.dump(semantic_model_data))

        parser = DbtParser()
        models = parser.parse_directory(Path(tmp_dir))

        generator = LookMLGenerator(schema="public")
        output = generator.generate(models)

        view_content = output["events.view.lkml"]

        # Hierarchy should win
        assert 'group_label: "Event Tracking"' in view_content
        # Time dimension group label should NOT appear
        assert 'group_label: "Time Dimensions"' not in view_content
