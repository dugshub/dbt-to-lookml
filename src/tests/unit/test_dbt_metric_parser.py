"""Unit tests for DbtMetricParser."""

from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest
import yaml

from dbt_to_lookml.parsers.dbt_metrics import (
    DbtMetricParser,
    extract_measure_dependencies,
    find_measure_model,
    resolve_primary_entity,
)
from dbt_to_lookml.schemas import (
    ConversionMetricParams,
    DerivedMetricParams,
    Entity,
    Measure,
    Metric,
    MetricReference,
    RatioMetricParams,
    SemanticModel,
    SimpleMetricParams,
)


class TestDbtMetricParser:
    """Test cases for DbtMetricParser."""

    def test_parse_empty_file(self) -> None:
        """Test parsing an empty YAML file."""
        parser = DbtMetricParser()

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump({}, f)
            temp_path = Path(f.name)

        try:
            metrics = parser.parse_file(temp_path)
            assert len(metrics) == 0
        finally:
            temp_path.unlink()

    def test_parse_file_not_found(self) -> None:
        """Test parsing a file that doesn't exist."""
        parser = DbtMetricParser()

        with pytest.raises(FileNotFoundError):
            parser.parse_file(Path("/nonexistent/file.yml"))

    def test_parse_invalid_yaml(self) -> None:
        """Test parsing invalid YAML."""
        parser = DbtMetricParser(strict_mode=True)

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)

        try:
            with pytest.raises(Exception):  # yaml.YAMLError
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_parse_simple_metric(self) -> None:
        """Test parsing a simple metric."""
        parser = DbtMetricParser()

        metric_data = {
            "name": "total_revenue",
            "type": "simple",
            "type_params": {"measure": "revenue"},
            "label": "Total Revenue",
            "description": "Sum of all revenue",
            "meta": {"primary_entity": "rental"},
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump({"metrics": [metric_data]}, f)
            temp_path = Path(f.name)

        try:
            metrics = parser.parse_file(temp_path)
            assert len(metrics) == 1
            assert metrics[0].name == "total_revenue"
            assert metrics[0].type == "simple"
            assert isinstance(metrics[0].type_params, SimpleMetricParams)
            assert metrics[0].type_params.measure == "revenue"
            assert metrics[0].label == "Total Revenue"
            assert metrics[0].description == "Sum of all revenue"
            assert metrics[0].meta == {"primary_entity": "rental"}
        finally:
            temp_path.unlink()

    def test_parse_ratio_metric(self) -> None:
        """Test parsing a ratio metric."""
        parser = DbtMetricParser()

        metric_data = {
            "name": "conversion_rate",
            "type": "ratio",
            "type_params": {"numerator": "rental_count", "denominator": "search_count"},
            "label": "Conversion Rate",
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump({"metrics": [metric_data]}, f)
            temp_path = Path(f.name)

        try:
            metrics = parser.parse_file(temp_path)
            assert len(metrics) == 1
            assert metrics[0].name == "conversion_rate"
            assert metrics[0].type == "ratio"
            assert isinstance(metrics[0].type_params, RatioMetricParams)
            assert metrics[0].type_params.numerator == "rental_count"
            assert metrics[0].type_params.denominator == "search_count"
        finally:
            temp_path.unlink()

    def test_parse_derived_metric(self) -> None:
        """Test parsing a derived metric."""
        parser = DbtMetricParser()

        metric_data = {
            "name": "revenue_growth",
            "type": "derived",
            "type_params": {
                "expr": "current_revenue - previous_revenue",
                "metrics": [
                    {"name": "total_revenue", "alias": "current_revenue"},
                    {
                        "name": "total_revenue",
                        "alias": "previous_revenue",
                        "offset_window": "1 month",
                    },
                ],
            },
            "meta": {"primary_entity": "rental"},
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump({"metrics": [metric_data]}, f)
            temp_path = Path(f.name)

        try:
            metrics = parser.parse_file(temp_path)
            assert len(metrics) == 1
            assert metrics[0].name == "revenue_growth"
            assert metrics[0].type == "derived"
            assert isinstance(metrics[0].type_params, DerivedMetricParams)
            assert metrics[0].type_params.expr == "current_revenue - previous_revenue"
            assert len(metrics[0].type_params.metrics) == 2
            assert isinstance(metrics[0].type_params.metrics[0], MetricReference)
            assert metrics[0].type_params.metrics[0].name == "total_revenue"
            assert metrics[0].type_params.metrics[0].alias == "current_revenue"
            assert metrics[0].type_params.metrics[1].offset_window == "1 month"
        finally:
            temp_path.unlink()

    def test_parse_conversion_metric(self) -> None:
        """Test parsing a conversion metric."""
        parser = DbtMetricParser()

        metric_data = {
            "name": "user_conversion",
            "type": "conversion",
            "type_params": {
                "conversion_type_params": {
                    "base_measure": "search_count",
                    "conversion_measure": "rental_count",
                    "entity": "user_id",
                }
            },
            "meta": {"primary_entity": "user"},
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump({"metrics": [metric_data]}, f)
            temp_path = Path(f.name)

        try:
            metrics = parser.parse_file(temp_path)
            assert len(metrics) == 1
            assert metrics[0].name == "user_conversion"
            assert metrics[0].type == "conversion"
            assert isinstance(metrics[0].type_params, ConversionMetricParams)
            assert (
                metrics[0].type_params.conversion_type_params["base_measure"]
                == "search_count"
            )
            assert (
                metrics[0].type_params.conversion_type_params["conversion_measure"]
                == "rental_count"
            )
        finally:
            temp_path.unlink()

    def test_parse_multiple_metrics_in_list(self) -> None:
        """Test parsing multiple metrics in one file."""
        parser = DbtMetricParser()

        metrics_data = {
            "metrics": [
                {
                    "name": "metric1",
                    "type": "simple",
                    "type_params": {"measure": "measure1"},
                    "meta": {"primary_entity": "entity1"},
                },
                {
                    "name": "metric2",
                    "type": "simple",
                    "type_params": {"measure": "measure2"},
                    "meta": {"primary_entity": "entity2"},
                },
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(metrics_data, f)
            temp_path = Path(f.name)

        try:
            metrics = parser.parse_file(temp_path)
            assert len(metrics) == 2
            assert metrics[0].name == "metric1"
            assert metrics[1].name == "metric2"
        finally:
            temp_path.unlink()

    def test_parse_metrics_key_structure(self) -> None:
        """Test parsing YAML with 'metrics:' key."""
        parser = DbtMetricParser()

        metrics_data = {
            "metrics": [
                {
                    "name": "test_metric",
                    "type": "simple",
                    "type_params": {"measure": "test_measure"},
                    "meta": {"primary_entity": "test"},
                }
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(metrics_data, f)
            temp_path = Path(f.name)

        try:
            metrics = parser.parse_file(temp_path)
            assert len(metrics) == 1
            assert metrics[0].name == "test_metric"
        finally:
            temp_path.unlink()

    def test_parse_direct_metric_structure(self) -> None:
        """Test parsing single metric without 'metrics:' wrapper."""
        parser = DbtMetricParser()

        metric_data = {
            "name": "direct_metric",
            "type": "simple",
            "type_params": {"measure": "direct_measure"},
            "meta": {"primary_entity": "test"},
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(metric_data, f)
            temp_path = Path(f.name)

        try:
            metrics = parser.parse_file(temp_path)
            assert len(metrics) == 1
            assert metrics[0].name == "direct_metric"
        finally:
            temp_path.unlink()

    def test_parse_top_level_list(self) -> None:
        """Test parsing top-level list of metrics."""
        parser = DbtMetricParser()

        metrics_list = [
            {
                "name": "list_metric1",
                "type": "simple",
                "type_params": {"measure": "measure1"},
                "meta": {"primary_entity": "test"},
            },
            {
                "name": "list_metric2",
                "type": "simple",
                "type_params": {"measure": "measure2"},
                "meta": {"primary_entity": "test"},
            },
        ]

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(metrics_list, f)
            temp_path = Path(f.name)

        try:
            metrics = parser.parse_file(temp_path)
            assert len(metrics) == 2
            assert metrics[0].name == "list_metric1"
            assert metrics[1].name == "list_metric2"
        finally:
            temp_path.unlink()

    def test_parse_directory_single_file(self) -> None:
        """Test parsing directory with one file."""
        parser = DbtMetricParser()

        metric_data = {
            "metrics": [
                {
                    "name": "dir_metric",
                    "type": "simple",
                    "type_params": {"measure": "dir_measure"},
                    "meta": {"primary_entity": "test"},
                }
            ]
        }

        with TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            metric_file = temp_dir / "metric.yml"
            with open(metric_file, "w") as f:
                yaml.dump(metric_data, f)

            metrics = parser.parse_directory(temp_dir)
            assert len(metrics) == 1
            assert metrics[0].name == "dir_metric"

    def test_parse_directory_multiple_files(self) -> None:
        """Test parsing directory with multiple files."""
        parser = DbtMetricParser()

        metric1_data = {
            "metrics": [
                {
                    "name": "metric1",
                    "type": "simple",
                    "type_params": {"measure": "measure1"},
                    "meta": {"primary_entity": "test"},
                }
            ]
        }

        metric2_data = {
            "metrics": [
                {
                    "name": "metric2",
                    "type": "simple",
                    "type_params": {"measure": "measure2"},
                    "meta": {"primary_entity": "test"},
                }
            ]
        }

        with TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            file1 = temp_dir / "metric1.yml"
            with open(file1, "w") as f:
                yaml.dump(metric1_data, f)

            file2 = temp_dir / "metric2.yml"
            with open(file2, "w") as f:
                yaml.dump(metric2_data, f)

            metrics = parser.parse_directory(temp_dir)
            assert len(metrics) == 2
            metric_names = {m.name for m in metrics}
            assert metric_names == {"metric1", "metric2"}

    def test_parse_directory_nested(self) -> None:
        """Test recursive directory parsing."""
        parser = DbtMetricParser()

        # Root level metric
        root_metric_data = {
            "metrics": [
                {
                    "name": "root_metric",
                    "type": "simple",
                    "type_params": {"measure": "root_measure"},
                    "meta": {"primary_entity": "test"},
                }
            ]
        }

        # Nested metric
        nested_metric_data = {
            "metrics": [
                {
                    "name": "nested_metric",
                    "type": "simple",
                    "type_params": {"measure": "nested_measure"},
                    "meta": {"primary_entity": "test"},
                }
            ]
        }

        # Deeply nested metric
        deep_metric_data = {
            "metrics": [
                {
                    "name": "deep_metric",
                    "type": "simple",
                    "type_params": {"measure": "deep_measure"},
                    "meta": {"primary_entity": "test"},
                }
            ]
        }

        with TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            # Root level metric
            root_file = temp_dir / "root_metric.yml"
            with open(root_file, "w") as f:
                yaml.dump(root_metric_data, f)

            # Nested metric
            nested_dir = temp_dir / "nested"
            nested_dir.mkdir()
            nested_file = nested_dir / "metric.yml"
            with open(nested_file, "w") as f:
                yaml.dump(nested_metric_data, f)

            # Deeply nested metric
            deep_dir = temp_dir / "nested" / "deep" / "path"
            deep_dir.mkdir(parents=True)
            deep_file = deep_dir / "metric.yaml"
            with open(deep_file, "w") as f:
                yaml.dump(deep_metric_data, f)

            # Parse directory recursively
            metrics = parser.parse_directory(temp_dir)

            # Should find all 3 metrics
            assert len(metrics) == 3
            metric_names = {m.name for m in metrics}
            assert metric_names == {"root_metric", "nested_metric", "deep_metric"}

    def test_parse_directory_mixed_extensions(self) -> None:
        """Test parsing both .yml and .yaml files."""
        parser = DbtMetricParser()

        metric_data = {
            "metrics": [
                {
                    "name": "test_metric",
                    "type": "simple",
                    "type_params": {"measure": "test_measure"},
                    "meta": {"primary_entity": "test"},
                }
            ]
        }

        with TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            yml_file = temp_dir / "metric1.yml"
            with open(yml_file, "w") as f:
                yaml.dump(metric_data, f)

            yaml_file = temp_dir / "metric2.yaml"
            with open(yaml_file, "w") as f:
                yaml.dump(metric_data, f)

            metrics = parser.parse_directory(temp_dir)
            assert len(metrics) == 2

    def test_validate_valid_metric_structure(self) -> None:
        """Test validation of valid metric structure."""
        parser = DbtMetricParser()

        content = {
            "metrics": [
                {
                    "name": "test",
                    "type": "simple",
                    "type_params": {"measure": "test_measure"},
                }
            ]
        }

        assert parser.validate(content) is True

    def test_validate_missing_name(self) -> None:
        """Test validation fails when name is missing."""
        parser = DbtMetricParser()

        content = {"metrics": [{"type": "simple", "type_params": {"measure": "test"}}]}

        assert parser.validate(content) is False

    def test_validate_missing_type(self) -> None:
        """Test validation fails when type is missing."""
        parser = DbtMetricParser()

        content = {"metrics": [{"name": "test", "type_params": {"measure": "test"}}]}

        assert parser.validate(content) is False

    def test_validate_missing_type_params(self) -> None:
        """Test validation fails when type_params is missing."""
        parser = DbtMetricParser()

        content = {"metrics": [{"name": "test", "type": "simple"}]}

        assert parser.validate(content) is False

    def test_validate_invalid_metric_type(self) -> None:
        """Test validation fails for invalid metric type."""
        parser = DbtMetricParser()

        content = {
            "metrics": [
                {
                    "name": "test",
                    "type": "invalid_type",
                    "type_params": {"measure": "test"},
                }
            ]
        }

        assert parser.validate(content) is False

    def test_strict_mode_raises_on_invalid(self) -> None:
        """Test strict mode raises on invalid metric."""
        parser = DbtMetricParser(strict_mode=True)

        invalid_data = {
            "metrics": [
                {
                    "name": "invalid_metric",
                    "type": "simple",
                    # Missing type_params
                }
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(invalid_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(Exception):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_lenient_mode_continues_on_invalid(self) -> None:
        """Test lenient mode continues on invalid metric."""
        parser = DbtMetricParser(strict_mode=False)

        mixed_data = {
            "metrics": [
                {
                    "name": "valid_metric",
                    "type": "simple",
                    "type_params": {"measure": "test"},
                    "meta": {"primary_entity": "test"},
                },
                {
                    "name": "invalid_metric",
                    "type": "simple",
                    # Missing type_params
                },
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(mixed_data, f)
            temp_path = Path(f.name)

        try:
            metrics = parser.parse_file(temp_path)
            # Should only parse the valid metric
            assert len(metrics) == 1
            assert metrics[0].name == "valid_metric"
        finally:
            temp_path.unlink()

    def test_parse_unknown_metric_type(self) -> None:
        """Test parsing unknown metric type raises error."""
        parser = DbtMetricParser(strict_mode=True)

        metric_data = {
            "metrics": [
                {
                    "name": "unknown_type_metric",
                    "type": "unknown_type",
                    "type_params": {"some": "param"},
                }
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(metric_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(Exception) as exc_info:
                parser.parse_file(temp_path)
            assert "unknown_type" in str(exc_info.value).lower()
        finally:
            temp_path.unlink()

    def test_parse_metric_missing_required_fields(self) -> None:
        """Test parsing metric with missing required fields."""
        parser = DbtMetricParser(strict_mode=True)

        metric_data = {
            "metrics": [
                {
                    "name": "incomplete_metric",
                    # Missing type and type_params
                }
            ]
        }

        with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(metric_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(Exception):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()


class TestPrimaryEntityResolution:
    """Test cases for resolve_primary_entity function."""

    def test_explicit_primary_entity(self) -> None:
        """Test explicit primary_entity in meta is used."""
        metric = Metric(
            name="test_metric",
            type="simple",
            type_params=SimpleMetricParams(measure="test_measure"),
            meta={"primary_entity": "explicit_entity"},
        )

        result = resolve_primary_entity(metric, [])
        assert result == "explicit_entity"

    def test_infer_from_denominator_ratio_metric(self) -> None:
        """Test inferring primary entity from denominator for ratio metrics."""
        # Create semantic models
        search_model = SemanticModel(
            name="searches",
            model="fct_searches",
            entities=[Entity(name="search", type="primary")],
            dimensions=[],
            measures=[Measure(name="search_count", agg="count")],
        )

        rental_model = SemanticModel(
            name="rentals",
            model="fct_rentals",
            entities=[Entity(name="rental", type="primary")],
            dimensions=[],
            measures=[Measure(name="rental_count", agg="count")],
        )

        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="rental_count", denominator="search_count"
            ),
        )

        result = resolve_primary_entity(metric, [search_model, rental_model])
        assert result == "search"

    def test_error_when_cannot_infer(self) -> None:
        """Test error raised when can't infer primary entity."""
        metric = Metric(
            name="simple_metric",
            type="simple",
            type_params=SimpleMetricParams(measure="test_measure"),
        )

        with pytest.raises(ValueError) as exc_info:
            resolve_primary_entity(metric, [])

        assert "Cannot determine primary entity" in str(exc_info.value)
        assert "simple_metric" in str(exc_info.value)

    def test_error_simple_metric_no_primary(self) -> None:
        """Test simple metric requires explicit primary entity."""
        metric = Metric(
            name="revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="revenue_measure"),
        )

        with pytest.raises(ValueError) as exc_info:
            resolve_primary_entity(metric, [])

        assert "Cannot determine primary entity" in str(exc_info.value)
        assert "primary_entity" in str(exc_info.value)

    def test_error_derived_metric_no_primary(self) -> None:
        """Test derived metric requires explicit primary entity."""
        metric = Metric(
            name="growth",
            type="derived",
            type_params=DerivedMetricParams(
                expr="a - b",
                metrics=[
                    MetricReference(name="metric_a", alias="a"),
                    MetricReference(name="metric_b", alias="b"),
                ],
            ),
        )

        with pytest.raises(ValueError) as exc_info:
            resolve_primary_entity(metric, [])

        assert "Cannot determine primary entity" in str(exc_info.value)

    def test_denominator_measure_not_found(self) -> None:
        """Test error when denominator measure not found in any model."""
        metric = Metric(
            name="ratio_metric",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="measure1", denominator="nonexistent_measure"
            ),
        )

        model = SemanticModel(
            name="test_model",
            model="test_table",
            entities=[Entity(name="test", type="primary")],
            dimensions=[],
            measures=[Measure(name="measure1", agg="count")],
        )

        with pytest.raises(ValueError) as exc_info:
            resolve_primary_entity(metric, [model])

        assert "nonexistent_measure" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_denominator_model_no_primary_entity(self) -> None:
        """Test error when denominator's model has no primary entity."""
        model = SemanticModel(
            name="test_model",
            model="test_table",
            entities=[Entity(name="test", type="foreign")],  # No primary entity
            dimensions=[],
            measures=[Measure(name="test_measure", agg="count")],
        )

        metric = Metric(
            name="ratio_metric",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="test_measure", denominator="test_measure"
            ),
        )

        with pytest.raises(ValueError) as exc_info:
            resolve_primary_entity(metric, [model])

        assert "no primary entity" in str(exc_info.value)


class TestDependencyExtraction:
    """Test cases for extract_measure_dependencies function."""

    def test_simple_metric_dependencies(self) -> None:
        """Test extracting dependencies from simple metric."""
        metric = Metric(
            name="revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="revenue_measure"),
        )

        deps = extract_measure_dependencies(metric)
        assert deps == {"revenue_measure"}

    def test_ratio_metric_dependencies(self) -> None:
        """Test extracting dependencies from ratio metric."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="rental_count", denominator="search_count"
            ),
        )

        deps = extract_measure_dependencies(metric)
        assert deps == {"rental_count", "search_count"}

    def test_derived_metric_dependencies(self) -> None:
        """Test derived metric returns empty set (references metrics not measures)."""
        metric = Metric(
            name="growth",
            type="derived",
            type_params=DerivedMetricParams(
                expr="a - b",
                metrics=[
                    MetricReference(name="metric_a", alias="a"),
                    MetricReference(name="metric_b", alias="b"),
                ],
            ),
        )

        deps = extract_measure_dependencies(metric)
        assert deps == set()

    def test_conversion_metric_dependencies(self) -> None:
        """Test extracting dependencies from conversion metric."""
        metric = Metric(
            name="user_conversion",
            type="conversion",
            type_params=ConversionMetricParams(
                conversion_type_params={
                    "base_measure": "search_count",
                    "conversion_measure": "rental_count",
                    "entity": "user_id",
                }
            ),
        )

        deps = extract_measure_dependencies(metric)
        assert deps == {"search_count", "rental_count"}

    def test_conversion_metric_partial_params(self) -> None:
        """Test conversion metric with only some measure params."""
        metric = Metric(
            name="conversion",
            type="conversion",
            type_params=ConversionMetricParams(
                conversion_type_params={
                    "base_measure": "base",
                    "entity": "user_id",
                    # No conversion_measure
                }
            ),
        )

        deps = extract_measure_dependencies(metric)
        assert "base" in deps


class TestFindMeasureModel:
    """Test cases for find_measure_model function."""

    def test_find_measure_in_first_model(self) -> None:
        """Test finding measure in first model."""
        model1 = SemanticModel(
            name="model1",
            model="table1",
            entities=[],
            dimensions=[],
            measures=[Measure(name="target_measure", agg="count")],
        )

        model2 = SemanticModel(
            name="model2",
            model="table2",
            entities=[],
            dimensions=[],
            measures=[Measure(name="other_measure", agg="sum")],
        )

        result = find_measure_model("target_measure", [model1, model2])
        assert result == model1

    def test_find_measure_in_second_model(self) -> None:
        """Test finding measure in second model."""
        model1 = SemanticModel(
            name="model1",
            model="table1",
            entities=[],
            dimensions=[],
            measures=[Measure(name="measure1", agg="count")],
        )

        model2 = SemanticModel(
            name="model2",
            model="table2",
            entities=[],
            dimensions=[],
            measures=[Measure(name="target_measure", agg="sum")],
        )

        result = find_measure_model("target_measure", [model1, model2])
        assert result == model2

    def test_measure_not_found(self) -> None:
        """Test returns None when measure not found."""
        model = SemanticModel(
            name="model",
            model="table",
            entities=[],
            dimensions=[],
            measures=[Measure(name="existing_measure", agg="count")],
        )

        result = find_measure_model("nonexistent_measure", [model])
        assert result is None

    def test_empty_semantic_models(self) -> None:
        """Test returns None for empty model list."""
        result = find_measure_model("any_measure", [])
        assert result is None
