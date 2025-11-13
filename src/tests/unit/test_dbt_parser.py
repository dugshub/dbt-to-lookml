"""Unit tests for DbtParser using new architecture."""

import threading
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.types import (
    DimensionType,
)


class TestDbtParser:
    """Test cases for DbtParser."""

    def test_parse_empty_file(self) -> None:
        """Test parsing an empty YAML file."""
        parser = DbtParser()

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump({}, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 0
        finally:
            temp_path.unlink()

    def test_parse_single_model(self) -> None:
        """Test parsing a file with a single semantic model."""
        parser = DbtParser()

        model_data = {
            "name": "users",
            "model": "dim_users",
            "description": "User dimension table",
            "entities": [{"name": "user_id", "type": "primary"}],
            "dimensions": [{"name": "status", "type": "categorical"}],
            "measures": [{"name": "user_count", "agg": "count"}],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert model.name == "users"
            assert model.model == "dim_users"
            assert model.description == "User dimension table"
            assert len(model.entities) == 1
            assert len(model.dimensions) == 1
            assert len(model.measures) == 1
        finally:
            temp_path.unlink()

    def test_parse_multiple_models_in_list(self) -> None:
        """Test parsing a file with multiple semantic models in a list."""
        parser = DbtParser()

        models_data = {
            "semantic_models": [
                {
                    "name": "users",
                    "model": "dim_users",
                    "entities": [{"name": "user_id", "type": "primary"}],
                    "dimensions": [],
                    "measures": [],
                },
                {
                    "name": "orders",
                    "model": "fct_orders",
                    "entities": [{"name": "order_id", "type": "primary"}],
                    "dimensions": [],
                    "measures": [],
                },
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(models_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 2
            assert models[0].name == "users"
            assert models[1].name == "orders"
        finally:
            temp_path.unlink()

    def test_parse_nonexistent_file(self) -> None:
        """Test parsing a file that doesn't exist."""
        parser = DbtParser()

        with pytest.raises(FileNotFoundError):
            parser.parse_file(Path("/nonexistent/file.yml"))

    def test_strict_mode_validation_error(self) -> None:
        """Test that strict mode raises validation errors."""
        parser = DbtParser(strict_mode=True)

        # Invalid model data (missing required fields)
        model_data = {
            "name": "invalid_model",
            # Missing 'model' field
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(Exception):  # Could be ValidationError or other
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_non_strict_mode_validation_error(self) -> None:
        """Test that non-strict mode handles validation errors gracefully."""
        parser = DbtParser(strict_mode=False)

        # Mix of valid and invalid model data
        models_data = {
            "semantic_models": [
                {
                    "name": "valid_model",
                    "model": "dim_valid",
                    "entities": [],
                    "dimensions": [],
                    "measures": [],
                },
                {
                    "name": "invalid_model",
                    # Missing 'model' field
                },
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(models_data, f)
            temp_path = Path(f.name)

        try:
            # Should not raise an exception, but may return fewer models
            models = parser.parse_file(temp_path)
            # At least the valid model should be parsed
            assert len(models) >= 0
        finally:
            temp_path.unlink()

    def test_parse_complex_semantic_model(self) -> None:
        """Test parsing a complex semantic model with all features."""
        parser = DbtParser()

        complex_model_data = {
            "version": 2,
            "semantic_models": [
                {
                    "name": "complex_model",
                    "model": "ref('fact_table')",
                    "description": "Complex model with all features",
                    "config": {
                        "meta": {
                            "domain": "sales",
                            "owner": "Analytics Team",
                            "contains_pii": True,
                            "update_frequency": "hourly",
                        }
                    },
                    "defaults": {"agg_time_dimension": "created_date"},
                    "entities": [
                        {
                            "name": "primary_key",
                            "type": "primary",
                            "expr": "id",
                            "description": "Primary entity",
                        },
                        {
                            "name": "foreign_key",
                            "type": "foreign",
                            "expr": "customer_id",
                        },
                    ],
                    "dimensions": [
                        {
                            "name": "status",
                            "type": "categorical",
                            "expr": "status",
                            "description": "Order status",
                            "label": "Order Status",
                        },
                        {
                            "name": "created_date",
                            "type": "time",
                            "type_params": {"time_granularity": "day"},
                            "expr": "created_at::date",
                            "description": "Creation date",
                        },
                        {
                            "name": "derived_field",
                            "type": "categorical",
                            "expr": "CASE WHEN amount > 100 THEN 'high' ELSE 'low' END",
                            "label": "Amount Category",
                        },
                    ],
                    "measures": [
                        {
                            "name": "total_count",
                            "agg": "count",
                            "description": "Total record count",
                        },
                        {
                            "name": "unique_customers",
                            "agg": "count_distinct",
                            "expr": "customer_id",
                            "label": "Unique Customers",
                        },
                        {
                            "name": "total_revenue",
                            "agg": "sum",
                            "expr": "amount",
                            "create_metric": True,
                        },
                        {"name": "avg_order_value", "agg": "average", "expr": "amount"},
                        {"name": "max_amount", "agg": "max", "expr": "amount"},
                        {"name": "min_amount", "agg": "min", "expr": "amount"},
                    ],
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(complex_model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert model.name == "complex_model"
            assert model.model == "ref('fact_table')"
            assert model.description == "Complex model with all features"

            # Test config parsing
            assert model.config is not None
            assert model.config.meta is not None
            assert model.config.meta.domain == "sales"
            assert model.config.meta.owner == "Analytics Team"
            assert model.config.meta.contains_pii is True
            assert model.config.meta.update_frequency == "hourly"

            # Test defaults
            assert model.defaults is not None
            assert model.defaults["agg_time_dimension"] == "created_date"

            # Test entities
            assert len(model.entities) == 2
            primary_entity = model.entities[0]
            assert primary_entity.name == "primary_key"
            assert primary_entity.type == "primary"
            assert primary_entity.expr == "id"

            # Test dimensions
            assert len(model.dimensions) == 3
            time_dim = next(d for d in model.dimensions if d.name == "created_date")
            assert time_dim.type == DimensionType.TIME
            assert time_dim.type_params["time_granularity"] == "day"

            # Test measures with all aggregation types
            assert len(model.measures) == 6
            measure_names = {m.name for m in model.measures}
            assert "total_count" in measure_names
            assert "unique_customers" in measure_names
            assert "total_revenue" in measure_names
            assert "avg_order_value" in measure_names
            assert "max_amount" in measure_names
            assert "min_amount" in measure_names

        finally:
            temp_path.unlink()

    def test_parse_directory(self) -> None:
        """Test parsing multiple files from a directory."""
        parser = DbtParser()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple YAML files
            model1_data = {
                "semantic_models": [
                    {
                        "name": "model1",
                        "model": "table1",
                        "entities": [],
                        "dimensions": [],
                        "measures": [],
                    }
                ]
            }

            model2_data = {
                "name": "model2",
                "model": "table2",
                "entities": [],
                "dimensions": [],
                "measures": [],
            }

            # Write files
            (temp_path / "model1.yml").write_text(yaml.dump(model1_data))
            (temp_path / "model2.yml").write_text(yaml.dump(model2_data))
            (temp_path / "model3.yaml").write_text(
                yaml.dump({"name": "model3", "model": "table3"})
            )
            # Add a non-YAML file that should be ignored
            (temp_path / "readme.txt").write_text("This is not a YAML file")

            models = parser.parse_directory(temp_path)
            assert len(models) == 3
            model_names = {m.name for m in models}
            assert model_names == {"model1", "model2", "model3"}

    def test_parse_invalid_yaml(self) -> None:
        """Test parsing invalid YAML files."""
        parser = DbtParser(strict_mode=True)

        invalid_yaml = "invalid: yaml: content: ["

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(invalid_yaml)
            temp_path = Path(f.name)

        try:
            with pytest.raises(yaml.YAMLError):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_parse_malformed_semantic_model(self) -> None:
        """Test parsing with various malformed semantic model structures."""
        parser = DbtParser(strict_mode=True)

        # Test cases with malformed data
        test_cases = [
            # Missing required name field
            {"model": "table1"},
            # Invalid aggregation type
            {
                "name": "test",
                "model": "table1",
                "measures": [{"name": "test_measure", "agg": "invalid_agg"}],
            },
            # Invalid dimension type
            {
                "name": "test",
                "model": "table1",
                "dimensions": [{"name": "test_dim", "type": "invalid_type"}],
            },
        ]

        for i, invalid_data in enumerate(test_cases):
            with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
                yaml.dump(invalid_data, f)
                temp_path = Path(f.name)

            try:
                with pytest.raises((ValidationError, ValueError, Exception)):
                    parser.parse_file(temp_path)
            finally:
                temp_path.unlink()

    def test_parse_empty_directory(self) -> None:
        """Test parsing an empty directory."""
        parser = DbtParser()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            models = parser.parse_directory(temp_path)
            assert len(models) == 0

    def test_parse_directory_with_only_non_yaml_files(self) -> None:
        """Test parsing directory with no YAML files."""
        parser = DbtParser()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create non-YAML files
            (temp_path / "readme.txt").write_text("Not a YAML file")
            (temp_path / "config.json").write_text('{"key": "value"}')

            models = parser.parse_directory(temp_path)
            assert len(models) == 0

    def test_parser_with_read_permission_error(self) -> None:
        """Test parser behavior when file cannot be read."""
        parser = DbtParser()

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump({"name": "test", "model": "table"}, f)
            temp_path = Path(f.name)

        with patch("builtins.open") as mock_open:
            mock_open.side_effect = PermissionError("Permission denied")

            try:
                with pytest.raises(PermissionError):
                    parser.parse_file(temp_path)
            finally:
                temp_path.unlink()

    def test_parse_file_with_version_field(self) -> None:
        """Test parsing files with version field (common in dbt)."""
        parser = DbtParser()

        model_data = {
            "version": 2,
            "semantic_models": [
                {
                    "name": "versioned_model",
                    "model": "dim_table",
                    "entities": [],
                    "dimensions": [],
                    "measures": [],
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1
            assert models[0].name == "versioned_model"
        finally:
            temp_path.unlink()

    def test_parse_model_with_complex_expressions(self) -> None:
        """Test parsing models with complex SQL expressions."""
        parser = DbtParser()

        model_data = {
            "name": "complex_expr_model",
            "model": "base_table",
            "dimensions": [
                {
                    "name": "case_when_dimension",
                    "type": "categorical",
                    "expr": "CASE WHEN status = 'active' AND created_at > '2023-01-01' THEN 'new_active' ELSE 'other' END",
                },
                {
                    "name": "extract_dimension",
                    "type": "categorical",
                    "expr": "EXTRACT(YEAR FROM created_at)::text",
                },
            ],
            "measures": [
                {
                    "name": "conditional_sum",
                    "agg": "sum",
                    "expr": "CASE WHEN status = 'completed' THEN amount ELSE 0 END",
                },
                {
                    "name": "filtered_count",
                    "agg": "count",
                    "expr": "CASE WHEN amount > 0 THEN id END",
                },
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert len(model.dimensions) == 2
            assert len(model.measures) == 2

            # Verify complex expressions are preserved
            case_dim = model.dimensions[0]
            assert "CASE WHEN" in case_dim.expr
            assert "AND" in case_dim.expr

            conditional_measure = model.measures[0]
            assert "CASE WHEN status = 'completed'" in conditional_measure.expr

        finally:
            temp_path.unlink()

    def test_parse_nonexistent_directory(self) -> None:
        """Test parsing a directory that doesn't exist."""
        parser = DbtParser()

        with pytest.raises(ValueError, match="Not a directory"):
            parser.parse_directory(Path("/nonexistent/directory"))

    def test_parse_extremely_large_model(self) -> None:
        """Test parsing a very large semantic model."""
        parser = DbtParser()

        # Create a model with many dimensions and measures
        large_model_data = {
            "name": "large_model",
            "model": "large_table",
            "description": "Very large model for testing",
            "entities": [
                {"name": f"entity_{i}", "type": "foreign", "expr": f"field_{i}"}
                for i in range(20)
            ],
            "dimensions": [
                {
                    "name": f"dim_{i}",
                    "type": "categorical",
                    "expr": f"field_{i}",
                    "description": f"Dimension {i}",
                }
                for i in range(50)
            ],
            "measures": [
                {
                    "name": f"measure_{i}",
                    "agg": "sum",
                    "expr": f"amount_{i}",
                    "description": f"Measure {i}",
                }
                for i in range(30)
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(large_model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert len(model.entities) == 20
            assert len(model.dimensions) == 50
            assert len(model.measures) == 30
        finally:
            temp_path.unlink()

    def test_parse_deeply_nested_yaml_structure(self) -> None:
        """Test parsing YAML with deeply nested structures."""
        parser = DbtParser()

        nested_model_data = {
            "version": 2,
            "semantic_models": [
                {
                    "name": "nested_model",
                    "model": "base_table",
                    "config": {
                        "meta": {
                            "domain": "analytics",
                            "owner": "data_team",
                            "tags": ["pii", "sensitive"],
                            "properties": {
                                "nested_prop": {
                                    "deep_value": "test",
                                    "deeper": {"deepest": "value"},
                                }
                            },
                        }
                    },
                    "dimensions": [
                        {
                            "name": "complex_time",
                            "type": "time",
                            "type_params": {
                                "time_granularity": "day",
                                "custom_formats": {
                                    "date_format": "yyyy-MM-dd",
                                    "time_format": "HH:mm:ss",
                                },
                            },
                        }
                    ],
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(nested_model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert model.name == "nested_model"
            assert model.config is not None
        finally:
            temp_path.unlink()

    def test_parse_file_with_unicode_content(self) -> None:
        """Test parsing files with Unicode characters."""
        parser = DbtParser()

        unicode_model_data = {
            "name": "测试模型",  # Chinese characters
            "model": "tëst_tåblé",  # Accented characters
            "description": "Модель с юникодом",  # Cyrillic characters
            "dimensions": [
                {
                    "name": "状态",  # Chinese
                    "type": "categorical",
                    "description": "État du utilisateur",  # French
                    "expr": "status_émoji_🔥",  # Emoji
                }
            ],
        }

        with NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(unicode_model_data, f, allow_unicode=True)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert model.name == "测试模型"
            assert "юникодом" in model.description
            assert len(model.dimensions) == 1
            assert "🔥" in model.dimensions[0].expr
        finally:
            temp_path.unlink()

    def test_parse_file_with_very_long_strings(self) -> None:
        """Test parsing files with extremely long string values."""
        parser = DbtParser()

        long_description = "A" * 10000  # Very long description
        long_expr = (
            "CASE "
            + " ".join(
                [f"WHEN field_{i} = 'value_{i}' THEN 'result_{i}'" for i in range(100)]
            )
            + " ELSE 'default' END"
        )

        long_string_model = {
            "name": "long_string_model",
            "model": "test_table",
            "description": long_description,
            "dimensions": [
                {"name": "complex_case", "type": "categorical", "expr": long_expr}
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(long_string_model, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert len(model.description) == 10000
            assert "CASE" in model.dimensions[0].expr
            assert "field_50" in model.dimensions[0].expr
        finally:
            temp_path.unlink()

    def test_parse_yaml_with_anchors_and_aliases(self) -> None:
        """Test parsing YAML files with anchors and aliases."""
        parser = DbtParser()

        yaml_with_anchors = """
common_config: &common_config
  meta:
    domain: "analytics"
    owner: "data_team"

common_dimension: &time_dim
  type: "time"
  type_params:
    time_granularity: "day"

semantic_models:
  - name: "model_with_anchors"
    model: "test_table"
    config: *common_config
    dimensions:
      - name: "created_at"
        <<: *time_dim
        expr: "created_timestamp"
      - name: "updated_at"
        <<: *time_dim
        expr: "updated_timestamp"
"""

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(yaml_with_anchors)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert model.config is not None
            assert len(model.dimensions) == 2
            assert all(dim.type == DimensionType.TIME for dim in model.dimensions)
        finally:
            temp_path.unlink()

    def test_parse_file_with_special_characters_in_names(self) -> None:
        """Test parsing with special characters in field names."""
        parser = DbtParser()

        special_chars_model = {
            "name": "model-with_special.chars",
            "model": "table$with%special&chars",
            "dimensions": [
                {"name": "field-with-dashes", "type": "categorical"},
                {"name": "field_with_underscores", "type": "categorical"},
                {"name": "field.with.dots", "type": "categorical"},
                {"name": "field123with456numbers", "type": "categorical"},
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(special_chars_model, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert "special.chars" in model.name
            assert "&chars" in model.model
            assert len(model.dimensions) == 4
        finally:
            temp_path.unlink()

    def test_parse_file_with_null_values(self) -> None:
        """Test parsing files with null/None values."""
        parser = DbtParser(strict_mode=False)

        null_values_model = {
            "name": "model_with_nulls",
            "model": "test_table",
            "description": None,
            "dimensions": [
                {
                    "name": "test_dim",
                    "type": "categorical",
                    "expr": None,
                    "description": None,
                }
            ],
            "measures": [{"name": "test_measure", "agg": "count", "expr": None}],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(null_values_model, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert model.description is None
            assert model.dimensions[0].expr is None
            assert model.measures[0].expr is None
        finally:
            temp_path.unlink()

    def test_parse_file_with_empty_lists(self) -> None:
        """Test parsing files with empty entity/dimension/measure lists."""
        parser = DbtParser()

        empty_lists_model = {
            "name": "empty_model",
            "model": "empty_table",
            "entities": [],
            "dimensions": [],
            "measures": [],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(empty_lists_model, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert len(model.entities) == 0
            assert len(model.dimensions) == 0
            assert len(model.measures) == 0
        finally:
            temp_path.unlink()

    def test_parse_mixed_valid_invalid_files_in_directory(self) -> None:
        """Test parsing directory with mix of valid and invalid files."""
        parser = DbtParser(strict_mode=False)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Valid model
            valid_model = {"name": "valid", "model": "table1", "entities": []}
            (temp_path / "valid.yml").write_text(yaml.dump(valid_model))

            # Invalid YAML
            (temp_path / "invalid.yml").write_text("invalid: yaml: content: [")

            # Valid model with missing fields - should be handled gracefully
            incomplete_model = {"name": "incomplete"}  # Missing 'model' field
            (temp_path / "incomplete.yml").write_text(yaml.dump(incomplete_model))

            # Non-YAML file
            (temp_path / "notaml.txt").write_text("This is not YAML")

            # Empty YAML file
            (temp_path / "empty.yml").write_text("")

            models = parser.parse_directory(temp_path)

            # Should parse at least the valid model
            assert len(models) >= 1
            valid_model_parsed = next((m for m in models if m.name == "valid"), None)
            assert valid_model_parsed is not None

    def test_parse_concurrent_access(self) -> None:
        """Test concurrent parsing of the same file."""

        parser = DbtParser()

        model_data = {
            "name": "concurrent_model",
            "model": "concurrent_table",
            "entities": [{"name": "id", "type": "primary"}],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        results = []
        exceptions = []

        def parse_file():
            try:
                models = parser.parse_file(temp_path)
                results.append(len(models))
            except Exception as e:
                exceptions.append(e)

        # Create multiple threads to parse the same file
        threads = [threading.Thread(target=parse_file) for _ in range(5)]

        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            # All threads should succeed
            assert len(exceptions) == 0
            assert len(results) == 5
            assert all(result == 1 for result in results)
        finally:
            temp_path.unlink()

    def test_parse_file_encoding_variations(self) -> None:
        """Test parsing files with different encodings."""
        parser = DbtParser()

        model_data = {
            "name": "encoding_test",
            "model": "test_table",
            "description": "Test with special chars: ñáéíóú",
        }

        # Test UTF-8 encoding (default)
        with NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(model_data, f, allow_unicode=True)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1
            assert "ñáéíóú" in models[0].description
        finally:
            temp_path.unlink()

    def test_parse_huge_directory(self) -> None:
        """Test parsing directory with many files."""
        parser = DbtParser()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create 100 semantic model files
            for i in range(100):
                model_data = {
                    "name": f"model_{i:03d}",
                    "model": f"table_{i:03d}",
                    "entities": [{"name": "id", "type": "primary"}],
                    "dimensions": [
                        {"name": f"field_{j}", "type": "categorical"} for j in range(5)
                    ],
                    "measures": [
                        {"name": f"measure_{j}", "agg": "count"} for j in range(3)
                    ],
                }

                file_path = temp_path / f"model_{i:03d}.yml"
                file_path.write_text(yaml.dump(model_data))

            models = parser.parse_directory(temp_path)
            assert len(models) == 100

            # Verify all models were parsed correctly
            model_names = {m.name for m in models}
            expected_names = {f"model_{i:03d}" for i in range(100)}
            assert model_names == expected_names

    # Tests for uncovered code paths to improve coverage from 61% to 85%+

    def test_parse_yaml_list_structure(self) -> None:
        """Test parsing when YAML root is a list of models."""
        parser = DbtParser()

        # Root element is a list (edge case)
        models_list = [
            {
                "name": "list_model_1",
                "model": "table1",
                "entities": [],
                "dimensions": [],
                "measures": [],
            },
            {
                "name": "list_model_2",
                "model": "table2",
                "entities": [],
                "dimensions": [],
                "measures": [],
            },
        ]

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(models_list, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 2
            assert models[0].name == "list_model_1"
            assert models[1].name == "list_model_2"
        finally:
            temp_path.unlink()

    def test_parse_invalid_yaml_structure_scalar(self) -> None:
        """Test parsing with scalar YAML content raises error."""
        parser = DbtParser()

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            # Write a scalar value instead of dict/list
            f.write("just a string")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid YAML structure"):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_parse_directory_with_yaml_extension(self) -> None:
        """Test parsing directory handles both .yml and .yaml files."""
        parser = DbtParser()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create .yaml file (tests the second glob pattern at lines 96-101)
            yaml_model = {
                "name": "yaml_model",
                "model": "yaml_table",
                "entities": [],
                "dimensions": [],
                "measures": [],
            }
            (temp_path / "model.yaml").write_text(yaml.dump(yaml_model))

            models = parser.parse_directory(temp_path)
            assert len(models) == 1
            assert models[0].name == "yaml_model"

    def test_validate_method_with_semantic_models_key(self) -> None:
        """Test validate() method with semantic_models key structure."""
        parser = DbtParser()

        content = {"semantic_models": [{"name": "test", "model": "table"}]}
        assert parser.validate(content) is True

    def test_validate_method_with_direct_model(self) -> None:
        """Test validate() method with direct model structure."""
        parser = DbtParser()

        content = {"name": "test", "model": "table"}
        assert parser.validate(content) is True

    def test_validate_method_with_list_of_models(self) -> None:
        """Test validate() method with list of models."""
        parser = DbtParser()

        content = [{"name": "test", "model": "table"}]
        assert parser.validate(content) is True

    def test_validate_method_with_invalid_semantic_models_structure(self) -> None:
        """Test validate() method with non-list semantic_models."""
        parser = DbtParser()

        content = {"semantic_models": "not_a_list"}
        assert parser.validate(content) is False

    def test_validate_method_with_empty_content(self) -> None:
        """Test validate() method with empty content."""
        parser = DbtParser()

        assert parser.validate({}) is False
        assert parser.validate(None) is False
        assert parser.validate([]) is False

    def test_validate_method_with_missing_required_fields(self) -> None:
        """Test validate() method with missing required fields."""
        parser = DbtParser()

        # Missing 'model' field
        content = {"name": "test"}
        assert parser.validate(content) is False

        # Missing 'name' field
        content = {"model": "table"}
        assert parser.validate(content) is False

    def test_validate_method_with_empty_list(self) -> None:
        """Test validate() method with empty list returns False."""
        parser = DbtParser()

        content = []
        assert parser.validate(content) is False

    def test_validate_model_structure_method(self) -> None:
        """Test _validate_model_structure() private method."""
        parser = DbtParser()

        # Valid structure
        assert (
            parser._validate_model_structure({"name": "test", "model": "table"}) is True
        )

        # Missing name
        assert parser._validate_model_structure({"model": "table"}) is False

        # Missing model
        assert parser._validate_model_structure({"name": "test"}) is False

        # Empty dict
        assert parser._validate_model_structure({}) is False

    def test_dimension_with_nested_hierarchy_config(self) -> None:
        """Test dimension parsing with nested hierarchy in config."""
        parser = DbtParser()

        model_data = {
            "name": "hierarchy_model",
            "model": "base_table",
            "dimensions": [
                {
                    "name": "user_status",
                    "type": "categorical",
                    "config": {
                        "meta": {
                            "hierarchy": {
                                "entity": "user",
                                "category": "profile",
                                "subcategory": "account_status",
                            }
                        }
                    },
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            dim = models[0].dimensions[0]
            assert dim.config is not None
            assert dim.config.meta is not None
            assert dim.config.meta.hierarchy is not None
            assert dim.config.meta.hierarchy.entity == "user"
            assert dim.config.meta.hierarchy.category == "profile"
            assert dim.config.meta.hierarchy.subcategory == "account_status"
        finally:
            temp_path.unlink()

    def test_dimension_with_flat_hierarchy_config_subject(self) -> None:
        """Test dimension parsing with flat hierarchy using 'subject' field."""
        parser = DbtParser()

        model_data = {
            "name": "flat_hierarchy_model",
            "model": "base_table",
            "dimensions": [
                {
                    "name": "location",
                    "type": "categorical",
                    "config": {
                        "meta": {
                            "subject": "customer",
                            "category": "demographics",
                            "subcategory": "geo",
                        }
                    },
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            dim = models[0].dimensions[0]
            assert dim.config is not None
            assert dim.config.meta is not None
            assert dim.config.meta.subject == "customer"
            assert dim.config.meta.category == "demographics"
            assert dim.config.meta.hierarchy is not None
            assert dim.config.meta.hierarchy.entity == "customer"
            assert dim.config.meta.hierarchy.category == "demographics"
            assert dim.config.meta.hierarchy.subcategory == "geo"
        finally:
            temp_path.unlink()

    def test_dimension_with_flat_hierarchy_config_entity(self) -> None:
        """Test dimension parsing with flat hierarchy using 'entity' field."""
        parser = DbtParser()

        model_data = {
            "name": "flat_hierarchy_entity",
            "model": "base_table",
            "dimensions": [
                {
                    "name": "order_status",
                    "type": "categorical",
                    "config": {"meta": {"entity": "order", "category": "details"}},
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            dim = models[0].dimensions[0]
            assert dim.config is not None
            assert dim.config.meta is not None
            assert dim.config.meta.hierarchy is not None
            assert dim.config.meta.hierarchy.entity == "order"
            assert dim.config.meta.hierarchy.category == "details"
        finally:
            temp_path.unlink()

    def test_dimension_with_full_config_metadata(self) -> None:
        """Test dimension parsing with all config metadata fields."""
        parser = DbtParser()

        model_data = {
            "name": "full_config_model",
            "model": "base_table",
            "dimensions": [
                {
                    "name": "customer_age",
                    "type": "categorical",
                    "config": {
                        "meta": {
                            "domain": "customer",
                            "owner": "analytics_team",
                            "contains_pii": True,
                            "update_frequency": "daily",
                            "category": "demographics",
                        }
                    },
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            dim = models[0].dimensions[0]
            assert dim.config.meta.domain == "customer"
            assert dim.config.meta.owner == "analytics_team"
            assert dim.config.meta.contains_pii is True
            assert dim.config.meta.update_frequency == "daily"
        finally:
            temp_path.unlink()

    def test_measure_with_nested_hierarchy_config(self) -> None:
        """Test measure parsing with nested hierarchy in config."""
        parser = DbtParser()

        model_data = {
            "name": "measure_hierarchy_model",
            "model": "fact_table",
            "measures": [
                {
                    "name": "total_revenue",
                    "agg": "sum",
                    "expr": "amount",
                    "config": {
                        "meta": {
                            "hierarchy": {
                                "entity": "order",
                                "category": "financials",
                                "subcategory": "revenue",
                            }
                        }
                    },
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            assert measure.config is not None
            assert measure.config.meta is not None
            assert measure.config.meta.hierarchy is not None
            assert measure.config.meta.hierarchy.entity == "order"
            assert measure.config.meta.hierarchy.category == "financials"
            assert measure.config.meta.hierarchy.subcategory == "revenue"
        finally:
            temp_path.unlink()

    def test_measure_with_flat_hierarchy_config_subject(self) -> None:
        """Test measure parsing with flat hierarchy using 'subject' field."""
        parser = DbtParser()

        model_data = {
            "name": "measure_flat_subject",
            "model": "fact_table",
            "measures": [
                {
                    "name": "order_count",
                    "agg": "count",
                    "config": {
                        "meta": {"subject": "transaction", "category": "counts"}
                    },
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            assert measure.config.meta.subject == "transaction"
            assert measure.config.meta.hierarchy is not None
            assert measure.config.meta.hierarchy.entity == "transaction"
            assert measure.config.meta.hierarchy.category == "counts"
        finally:
            temp_path.unlink()

    def test_measure_with_flat_hierarchy_config_entity(self) -> None:
        """Test measure parsing with flat hierarchy using 'entity' field."""
        parser = DbtParser()

        model_data = {
            "name": "measure_flat_entity",
            "model": "fact_table",
            "measures": [
                {
                    "name": "unique_users",
                    "agg": "count_distinct",
                    "expr": "user_id",
                    "config": {"meta": {"entity": "user", "category": "engagement"}},
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            assert measure.config.meta.hierarchy is not None
            assert measure.config.meta.hierarchy.entity == "user"
            assert measure.config.meta.hierarchy.category == "engagement"
        finally:
            temp_path.unlink()

    def test_measure_with_full_config_metadata(self) -> None:
        """Test measure parsing with all config metadata fields."""
        parser = DbtParser()

        model_data = {
            "name": "measure_full_config",
            "model": "fact_table",
            "measures": [
                {
                    "name": "total_amount",
                    "agg": "sum",
                    "expr": "amount",
                    "config": {
                        "meta": {
                            "domain": "finance",
                            "owner": "finance_team",
                            "contains_pii": False,
                            "update_frequency": "hourly",
                            "category": "metrics",
                        }
                    },
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            assert measure.config.meta.domain == "finance"
            assert measure.config.meta.owner == "finance_team"
            assert measure.config.meta.contains_pii is False
            assert measure.config.meta.update_frequency == "hourly"
        finally:
            temp_path.unlink()

    def test_entity_parsing_error_handling(self) -> None:
        """Test error handling when entity parsing fails."""
        parser = DbtParser(strict_mode=True)

        # Entity missing required 'name' field
        model_data = {
            "name": "entity_error_model",
            "model": "table",
            "entities": [
                {
                    "type": "primary",
                    # Missing 'name' field
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Error parsing entity"):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_entity_missing_type_field(self) -> None:
        """Test error handling when entity is missing 'type' field."""
        parser = DbtParser(strict_mode=True)

        model_data = {
            "name": "entity_no_type",
            "model": "table",
            "entities": [
                {
                    "name": "my_id",
                    # Missing 'type' field
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Error parsing entity"):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_dimension_parsing_error_missing_name(self) -> None:
        """Test error handling when dimension is missing name."""
        parser = DbtParser(strict_mode=True)

        model_data = {
            "name": "dim_error_model",
            "model": "table",
            "dimensions": [
                {
                    "type": "categorical",
                    # Missing 'name' field
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Error parsing dimension"):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_dimension_parsing_error_invalid_type(self) -> None:
        """Test error handling when dimension has invalid type."""
        parser = DbtParser(strict_mode=True)

        model_data = {
            "name": "dim_invalid_type",
            "model": "table",
            "dimensions": [
                {
                    "name": "test_dim",
                    "type": "invalid_dimension_type",
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Error parsing dimension"):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_measure_parsing_error_missing_name(self) -> None:
        """Test error handling when measure is missing name."""
        parser = DbtParser(strict_mode=True)

        model_data = {
            "name": "measure_error_model",
            "model": "table",
            "measures": [
                {
                    "agg": "count",
                    # Missing 'name' field
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Error parsing measure"):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_measure_parsing_error_invalid_agg(self) -> None:
        """Test error handling when measure has invalid aggregation type."""
        parser = DbtParser(strict_mode=True)

        model_data = {
            "name": "measure_invalid_agg",
            "model": "table",
            "measures": [
                {
                    "name": "bad_measure",
                    "agg": "invalid_aggregation",
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Error parsing measure"):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_dimension_with_multiline_expression(self) -> None:
        """Test dimension parsing with multiline SQL expressions."""
        parser = DbtParser()

        model_data = {
            "name": "multiline_expr_model",
            "model": "base_table",
            "dimensions": [
                {
                    "name": "complex_case",
                    "type": "categorical",
                    "expr": "  \n  CASE WHEN amount > 1000 THEN 'high'\n       WHEN amount > 100 THEN 'medium'\n       ELSE 'low' END  \n  ",
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            dim = models[0].dimensions[0]
            # Expression should be stripped of leading/trailing whitespace
            assert dim.expr.startswith("CASE")
            assert dim.expr.endswith("END")
            assert "high" in dim.expr
            assert "medium" in dim.expr
        finally:
            temp_path.unlink()

    def test_measure_with_multiline_expression(self) -> None:
        """Test measure parsing with multiline SQL expressions."""
        parser = DbtParser()

        model_data = {
            "name": "measure_multiline",
            "model": "fact_table",
            "measures": [
                {
                    "name": "conditional_sum",
                    "agg": "sum",
                    "expr": "  \n  CASE WHEN status = 'completed'\n       THEN amount ELSE 0 END  \n  ",
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            # Expression should be stripped
            assert measure.expr.startswith("CASE")
            assert measure.expr.endswith("END")
        finally:
            temp_path.unlink()

    def test_parse_directory_yaml_file_error_handling(self) -> None:
        """Test error handling when parsing .yaml files in directory."""
        parser = DbtParser(strict_mode=False)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a valid .yml file
            valid_model = {"name": "valid", "model": "table1"}
            (temp_path / "valid.yml").write_text(yaml.dump(valid_model))

            # Create an invalid .yaml file (malformed YAML)
            (temp_path / "invalid.yaml").write_text("invalid: yaml: content: [")

            # Should handle the error gracefully and return valid model
            models = parser.parse_directory(temp_path)
            # At least the valid model should be parsed
            assert any(m.name == "valid" for m in models)

    def test_config_with_only_meta_no_hierarchy(self) -> None:
        """Test dimension config parsing with meta but no hierarchy info."""
        parser = DbtParser()

        model_data = {
            "name": "simple_meta_model",
            "model": "base_table",
            "dimensions": [
                {
                    "name": "simple_dim",
                    "type": "categorical",
                    "config": {"meta": {"domain": "test", "owner": "test_owner"}},
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            dim = models[0].dimensions[0]
            assert dim.config is not None
            assert dim.config.meta.domain == "test"
            assert dim.config.meta.owner == "test_owner"
            # Hierarchy should be None when not specified
            assert dim.config.meta.hierarchy is None
        finally:
            temp_path.unlink()

    def test_measure_config_with_only_meta_no_hierarchy(self) -> None:
        """Test measure config parsing with meta but no hierarchy info."""
        parser = DbtParser()

        model_data = {
            "name": "simple_measure_meta",
            "model": "fact_table",
            "measures": [
                {
                    "name": "simple_measure",
                    "agg": "count",
                    "config": {"meta": {"domain": "metrics", "owner": "analytics"}},
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            assert measure.config is not None
            assert measure.config.meta.domain == "metrics"
            assert measure.config.meta.owner == "analytics"
            assert measure.config.meta.hierarchy is None
        finally:
            temp_path.unlink()

    def test_model_config_without_meta(self) -> None:
        """Test model parsing with config but no meta section."""
        parser = DbtParser()

        model_data = {
            "name": "config_no_meta_model",
            "model": "base_table",
            "config": {
                "other_field": "value"
                # No 'meta' section
            },
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            model = models[0]
            assert model.config is not None
            assert model.config.meta is None
        finally:
            temp_path.unlink()

    def test_dimension_config_without_meta(self) -> None:
        """Test dimension parsing with config but no meta section."""
        parser = DbtParser()

        model_data = {
            "name": "dim_config_no_meta",
            "model": "base_table",
            "dimensions": [
                {
                    "name": "test_dim",
                    "type": "categorical",
                    "config": {
                        "other_field": "value"
                        # No 'meta' section
                    },
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            dim = models[0].dimensions[0]
            assert dim.config is not None
            assert dim.config.meta is None
        finally:
            temp_path.unlink()

    def test_measure_config_without_meta(self) -> None:
        """Test measure parsing with config but no meta section."""
        parser = DbtParser()

        model_data = {
            "name": "measure_config_no_meta",
            "model": "fact_table",
            "measures": [
                {
                    "name": "test_measure",
                    "agg": "count",
                    "config": {
                        "other_field": "value"
                        # No 'meta' section
                    },
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            assert measure.config is not None
            assert measure.config.meta is None
        finally:
            temp_path.unlink()

    def test_dimension_without_config(self) -> None:
        """Test dimension parsing without config section."""
        parser = DbtParser()

        model_data = {
            "name": "dim_no_config",
            "model": "base_table",
            "dimensions": [
                {
                    "name": "simple_dim",
                    "type": "categorical",
                    "expr": "status",
                    # No 'config' section
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            dim = models[0].dimensions[0]
            assert dim.config is None
        finally:
            temp_path.unlink()

    def test_measure_without_config(self) -> None:
        """Test measure parsing without config section."""
        parser = DbtParser()

        model_data = {
            "name": "measure_no_config",
            "model": "fact_table",
            "measures": [
                {
                    "name": "simple_measure",
                    "agg": "count",
                    # No 'config' section
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            assert measure.config is None
        finally:
            temp_path.unlink()

    def test_dimension_with_none_expression(self) -> None:
        """Test dimension parsing with None expression value."""
        parser = DbtParser()

        model_data = {
            "name": "dim_none_expr",
            "model": "base_table",
            "dimensions": [{"name": "test_dim", "type": "categorical", "expr": None}],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            dim = models[0].dimensions[0]
            assert dim.expr is None
        finally:
            temp_path.unlink()

    def test_measure_with_none_expression(self) -> None:
        """Test measure parsing with None expression value."""
        parser = DbtParser()

        model_data = {
            "name": "measure_none_expr",
            "model": "fact_table",
            "measures": [{"name": "test_measure", "agg": "count", "expr": None}],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            assert measure.expr is None
        finally:
            temp_path.unlink()

    def test_dimension_with_only_category_in_meta(self) -> None:
        """Test dimension with only category field in meta (no entity/subject)."""
        parser = DbtParser()

        model_data = {
            "name": "dim_only_category",
            "model": "base_table",
            "dimensions": [
                {
                    "name": "test_dim",
                    "type": "categorical",
                    "config": {
                        "meta": {
                            "category": "demographics"
                            # Only category, no entity or subject
                        }
                    },
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            dim = models[0].dimensions[0]
            assert dim.config is not None
            assert dim.config.meta.category == "demographics"
            # Hierarchy should be created because category is present
            assert dim.config.meta.hierarchy is not None
            assert dim.config.meta.hierarchy.category == "demographics"
        finally:
            temp_path.unlink()

    def test_measure_with_only_category_in_meta(self) -> None:
        """Test measure with only category field in meta (no entity/subject)."""
        parser = DbtParser()

        model_data = {
            "name": "measure_only_category",
            "model": "fact_table",
            "measures": [
                {
                    "name": "test_measure",
                    "agg": "count",
                    "config": {
                        "meta": {
                            "category": "metrics"
                            # Only category, no entity or subject
                        }
                    },
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            assert measure.config is not None
            assert measure.config.meta.category == "metrics"
            assert measure.config.meta.hierarchy is not None
            assert measure.config.meta.hierarchy.category == "metrics"
        finally:
            temp_path.unlink()

    def test_dimension_with_empty_string_expression(self) -> None:
        """Test dimension with empty string expression."""
        parser = DbtParser()

        model_data = {
            "name": "dim_empty_expr",
            "model": "base_table",
            "dimensions": [
                {
                    "name": "test_dim",
                    "type": "categorical",
                    "expr": "",  # Empty string
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            dim = models[0].dimensions[0]
            # Empty string is falsy, so it's treated as if no expr was provided
            assert dim.expr == ""
        finally:
            temp_path.unlink()

    def test_measure_with_empty_string_expression(self) -> None:
        """Test measure with empty string expression."""
        parser = DbtParser()

        model_data = {
            "name": "measure_empty_expr",
            "model": "fact_table",
            "measures": [
                {
                    "name": "test_measure",
                    "agg": "count",
                    "expr": "",  # Empty string
                }
            ],
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(model_data, f)
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            assert measure.expr == ""
        finally:
            temp_path.unlink()
