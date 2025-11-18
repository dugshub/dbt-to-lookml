"""Integration tests for metric parsing end-to-end."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.parsers.dbt_metrics import (
    DbtMetricParser,
    extract_measure_dependencies,
    resolve_primary_entity,
)


class TestMetricParsingIntegration:
    """Integration tests for metric parsing with real fixtures."""

    def test_parse_real_metric_files(self) -> None:
        """Test parsing all fixture metric files."""
        parser = DbtMetricParser()

        # Use the actual fixtures directory
        fixtures_dir = Path(__file__).parent.parent / "fixtures" / "metrics"

        if not fixtures_dir.exists():
            pytest.skip("Fixtures directory not found")

        metrics = parser.parse_directory(fixtures_dir)

        # Should find metrics from simple, ratio, derived, conversion files
        # (nested directory is not recursively scanned)
        assert len(metrics) > 0

        # Verify we have different metric types
        metric_types = {m.type for m in metrics}
        assert "simple" in metric_types
        assert "ratio" in metric_types
        assert "derived" in metric_types
        assert "conversion" in metric_types

        # Verify all metrics have names
        for metric in metrics:
            assert metric.name
            assert metric.type in ["simple", "ratio", "derived", "conversion"]
            assert metric.type_params is not None

    def test_parse_with_semantic_models(self) -> None:
        """Test parsing metrics and validating against semantic models."""
        # Create temporary semantic models
        with TemporaryDirectory() as tmpdir:
            models_dir = Path(tmpdir) / "models"
            models_dir.mkdir()

            # Create semantic models with measures
            search_model_data = {
                "name": "searches",
                "model": "fct_searches",
                "entities": [{"name": "search", "type": "primary"}],
                "dimensions": [],
                "measures": [{"name": "search_count", "agg": "count"}],
            }

            rental_model_data = {
                "name": "rentals",
                "model": "fct_rentals",
                "entities": [{"name": "rental", "type": "primary"}],
                "dimensions": [],
                "measures": [{"name": "rental_count", "agg": "count"}],
            }

            with open(models_dir / "searches.yml", "w") as f:
                yaml.dump({"semantic_models": [search_model_data]}, f)

            with open(models_dir / "rentals.yml", "w") as f:
                yaml.dump({"semantic_models": [rental_model_data]}, f)

            # Parse semantic models
            model_parser = DbtParser()
            models = model_parser.parse_directory(models_dir)
            assert len(models) == 2

            # Create metrics that reference these models
            metrics_dir = Path(tmpdir) / "metrics"
            metrics_dir.mkdir()

            ratio_metric_data = {
                "metrics": [
                    {
                        "name": "conversion_rate",
                        "type": "ratio",
                        "type_params": {
                            "numerator": "rental_count",
                            "denominator": "search_count",
                        },
                    }
                ]
            }

            with open(metrics_dir / "metrics.yml", "w") as f:
                yaml.dump(ratio_metric_data, f)

            # Parse metrics
            metric_parser = DbtMetricParser()
            metrics = metric_parser.parse_directory(metrics_dir)
            assert len(metrics) == 1

            # Validate measure dependencies exist
            for metric in metrics:
                deps = extract_measure_dependencies(metric)
                for dep in deps:
                    # Check that measure exists in one of the models
                    found = False
                    for model in models:
                        if any(m.name == dep for m in model.measures):
                            found = True
                            break
                    assert found, f"Measure {dep} not found in any semantic model"

    def test_primary_entity_resolution_end_to_end(self) -> None:
        """Test resolving primary entities for all metrics."""
        with TemporaryDirectory() as tmpdir:
            # Create semantic models
            models_dir = Path(tmpdir) / "models"
            models_dir.mkdir()

            user_model_data = {
                "name": "users",
                "model": "dim_users",
                "entities": [{"name": "user", "type": "primary"}],
                "dimensions": [],
                "measures": [{"name": "user_count", "agg": "count"}],
            }

            order_model_data = {
                "name": "orders",
                "model": "fct_orders",
                "entities": [{"name": "order", "type": "primary"}],
                "dimensions": [],
                "measures": [{"name": "order_count", "agg": "count"}],
            }

            with open(models_dir / "users.yml", "w") as f:
                yaml.dump({"semantic_models": [user_model_data]}, f)

            with open(models_dir / "orders.yml", "w") as f:
                yaml.dump({"semantic_models": [order_model_data]}, f)

            # Parse semantic models
            model_parser = DbtParser()
            models = model_parser.parse_directory(models_dir)

            # Create metrics with explicit and inferred entities
            metrics_dir = Path(tmpdir) / "metrics"
            metrics_dir.mkdir()

            metrics_data = {
                "metrics": [
                    {
                        "name": "total_users",
                        "type": "simple",
                        "type_params": {"measure": "user_count"},
                        "meta": {"primary_entity": "user"},  # Explicit
                    },
                    {
                        "name": "orders_per_user",
                        "type": "ratio",
                        "type_params": {
                            "numerator": "order_count",
                            "denominator": "user_count",
                        },
                        # No explicit entity - should infer from denominator
                    },
                ]
            }

            with open(metrics_dir / "metrics.yml", "w") as f:
                yaml.dump(metrics_data, f)

            # Parse metrics
            metric_parser = DbtMetricParser()
            metrics = metric_parser.parse_directory(metrics_dir)

            # Resolve primary entities
            entities = {}
            for metric in metrics:
                entity = resolve_primary_entity(metric, models)
                entities[metric.name] = entity

            # Verify resolution
            assert entities["total_users"] == "user"  # Explicit
            assert entities["orders_per_user"] == "user"  # Inferred from denominator

    def test_nested_directory_structure(self) -> None:
        """Test parsing nested directory structure."""
        with TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            # Create metrics at multiple levels
            root_metric = {
                "metrics": [
                    {
                        "name": "root_metric",
                        "type": "simple",
                        "type_params": {"measure": "root_measure"},
                        "meta": {"primary_entity": "test"},
                    }
                ]
            }

            with open(temp_dir / "root.yml", "w") as f:
                yaml.dump(root_metric, f)

            # Note: Current implementation doesn't recursively scan subdirectories
            # This test verifies that behavior
            nested_dir = temp_dir / "nested"
            nested_dir.mkdir()

            nested_metric = {
                "metrics": [
                    {
                        "name": "nested_metric",
                        "type": "simple",
                        "type_params": {"measure": "nested_measure"},
                        "meta": {"primary_entity": "test"},
                    }
                ]
            }

            with open(nested_dir / "nested.yml", "w") as f:
                yaml.dump(nested_metric, f)

            parser = DbtMetricParser()
            metrics = parser.parse_directory(temp_dir)

            # Should only find root metric (no recursive scanning)
            assert len(metrics) == 1
            assert metrics[0].name == "root_metric"

    def test_all_metric_types_with_validation(self) -> None:
        """Test all metric types parse correctly with full validation."""
        parser = DbtMetricParser()

        with TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            all_types_data = {
                "metrics": [
                    {
                        "name": "simple_metric",
                        "type": "simple",
                        "type_params": {"measure": "simple_measure"},
                        "label": "Simple Metric",
                        "description": "A simple metric",
                        "meta": {"primary_entity": "test"},
                    },
                    {
                        "name": "ratio_metric",
                        "type": "ratio",
                        "type_params": {
                            "numerator": "numerator_measure",
                            "denominator": "denominator_measure",
                        },
                        "label": "Ratio Metric",
                        "meta": {"primary_entity": "test"},
                    },
                    {
                        "name": "derived_metric",
                        "type": "derived",
                        "type_params": {
                            "expr": "a + b",
                            "metrics": [
                                {"name": "metric_a", "alias": "a"},
                                {"name": "metric_b", "alias": "b"},
                            ],
                        },
                        "label": "Derived Metric",
                        "meta": {"primary_entity": "test"},
                    },
                    {
                        "name": "conversion_metric",
                        "type": "conversion",
                        "type_params": {
                            "conversion_type_params": {
                                "base_measure": "base",
                                "conversion_measure": "conversion",
                                "entity": "user_id",
                            }
                        },
                        "label": "Conversion Metric",
                        "meta": {"primary_entity": "test"},
                    },
                ]
            }

            with open(temp_dir / "all_types.yml", "w") as f:
                yaml.dump(all_types_data, f)

            metrics = parser.parse_directory(temp_dir)

            # Verify all parsed
            assert len(metrics) == 4

            # Verify each type
            by_type = {m.type: m for m in metrics}
            assert "simple" in by_type
            assert "ratio" in by_type
            assert "derived" in by_type
            assert "conversion" in by_type

            # Verify all have required fields
            for metric in metrics:
                assert metric.name
                assert metric.type
                assert metric.type_params
                assert metric.label
                assert metric.meta
                assert metric.meta.get("primary_entity") == "test"
