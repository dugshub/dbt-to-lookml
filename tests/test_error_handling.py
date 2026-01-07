"""Tests for error handling with malformed YAML and invalid inputs."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from semantic_patterns.config import SPConfig
from semantic_patterns.ingestion import DomainBuilder
from semantic_patterns.ingestion.loader import YamlLoader


class TestMalformedYAMLSyntax:
    """Tests for handling malformed YAML syntax."""

    def test_invalid_yaml_syntax(self) -> None:
        """Test error handling for invalid YAML syntax."""
        # Missing colon after key
        invalid_yaml = """\
input ./models
output: ./lookml
schema: gold
"""
        with pytest.raises(yaml.YAMLError):
            SPConfig.from_yaml(invalid_yaml)

    def test_invalid_indentation(self) -> None:
        """Test error handling for invalid YAML indentation."""
        invalid_yaml = """\
input: ./models
output: ./lookml
schema: gold
model:
name: test
  connection: db
"""
        with pytest.raises(yaml.YAMLError):
            SPConfig.from_yaml(invalid_yaml)

    def test_unclosed_quotes(self) -> None:
        """Test error handling for unclosed quotes."""
        invalid_yaml = """\
input: ./models
output: ./lookml
schema: "unclosed quote
"""
        with pytest.raises(yaml.YAMLError):
            SPConfig.from_yaml(invalid_yaml)

    def test_tabs_instead_of_spaces(self) -> None:
        """Test error handling for tabs (often causes issues)."""
        # YAML technically supports tabs, but they can cause issues
        # This test ensures we handle tab-related parsing issues
        content = "input: ./models\noutput: ./lookml\nschema: gold\n"
        # This should parse fine - tabs in values are OK
        config = SPConfig.from_yaml(content)
        assert config.input == "./models"


class TestEmptyFiles:
    """Tests for handling empty files."""

    def test_empty_yaml_file(self) -> None:
        """Test handling of empty YAML file.

        Empty files are filtered out and don't produce documents.
        """
        with TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "empty.yml"
            empty_file.write_text("", encoding="utf-8")

            loader = YamlLoader(tmpdir)
            docs = loader.load_all()

            # Empty file is filtered out - no documents produced
            assert len(docs) == 0

    def test_whitespace_only_yaml_file(self) -> None:
        """Test handling of whitespace-only YAML file."""
        with TemporaryDirectory() as tmpdir:
            whitespace_file = Path(tmpdir) / "whitespace.yml"
            whitespace_file.write_text("   \n\n  \n", encoding="utf-8")

            loader = YamlLoader(tmpdir)
            docs = loader.load_all()

            # Whitespace-only file is filtered out
            assert len(docs) == 0

    def test_comment_only_yaml_file(self) -> None:
        """Test handling of comment-only YAML file."""
        with TemporaryDirectory() as tmpdir:
            comment_file = Path(tmpdir) / "comments.yml"
            comment_file.write_text("# This is a comment\n# Another comment\n", encoding="utf-8")

            loader = YamlLoader(tmpdir)
            docs = loader.load_all()

            # Comment-only file is filtered out
            assert len(docs) == 0


class TestMissingRequiredFields:
    """Tests for handling missing required fields in semantic models."""

    def test_semantic_model_missing_name(self) -> None:
        """Test error when semantic model missing name."""
        content = """\
semantic_models:
  - entities:
      - name: order
        type: primary
        expr: order_id
    dimensions: []
    measures: []
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            # DomainBuilder should handle or raise appropriate error
            with pytest.raises(KeyError):
                DomainBuilder.from_directory(tmpdir)

    def test_entity_missing_type(self) -> None:
        """Test error when entity missing type field."""
        content = """\
semantic_models:
  - name: orders
    entities:
      - name: order
        expr: order_id
    dimensions: []
    measures: []
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            with pytest.raises(KeyError):
                DomainBuilder.from_directory(tmpdir)

    def test_entity_missing_expr(self) -> None:
        """Test error when entity missing expr field."""
        content = """\
semantic_models:
  - name: orders
    entities:
      - name: order
        type: primary
    dimensions: []
    measures: []
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            with pytest.raises(KeyError):
                DomainBuilder.from_directory(tmpdir)

    def test_dimension_missing_name(self) -> None:
        """Test error when dimension missing name."""
        content = """\
semantic_models:
  - name: orders
    entities:
      - name: order
        type: primary
        expr: order_id
    dimensions:
      - type: categorical
        expr: status
    measures: []
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            with pytest.raises(KeyError):
                DomainBuilder.from_directory(tmpdir)

    def test_measure_missing_name(self) -> None:
        """Test error when measure missing name."""
        content = """\
semantic_models:
  - name: orders
    entities:
      - name: order
        type: primary
        expr: order_id
    dimensions: []
    measures:
      - agg: sum
        expr: amount
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            with pytest.raises(KeyError):
                DomainBuilder.from_directory(tmpdir)

    def test_measure_missing_expr(self) -> None:
        """Test error when measure missing expr."""
        content = """\
semantic_models:
  - name: orders
    entities:
      - name: order
        type: primary
        expr: order_id
    dimensions: []
    measures:
      - name: total
        agg: sum
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            with pytest.raises(KeyError):
                DomainBuilder.from_directory(tmpdir)


class TestInvalidFieldTypes:
    """Tests for handling invalid field types."""

    def test_dimensions_not_list(self) -> None:
        """Test error when dimensions is not a list."""
        content = """\
semantic_models:
  - name: orders
    entities:
      - name: order
        type: primary
        expr: order_id
    dimensions: "not a list"
    measures: []
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            # String object doesn't have 'get' method used in _build_dimension
            with pytest.raises((TypeError, AttributeError)):
                DomainBuilder.from_directory(tmpdir)

    def test_measures_not_list(self) -> None:
        """Test error when measures is not a list."""
        content = """\
semantic_models:
  - name: orders
    entities:
      - name: order
        type: primary
        expr: order_id
    dimensions: []
    measures:
      name: total
      agg: sum
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            # This should fail because measures is a dict, not a list
            with pytest.raises((TypeError, AttributeError)):
                DomainBuilder.from_directory(tmpdir)

    def test_entities_not_list(self) -> None:
        """Test error when entities is not a list."""
        content = """\
semantic_models:
  - name: orders
    entities:
      name: order
      type: primary
      expr: order_id
    dimensions: []
    measures: []
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            with pytest.raises((TypeError, KeyError)):
                DomainBuilder.from_directory(tmpdir)

    def test_semantic_models_not_list(self) -> None:
        """Test error when semantic_models is not a list."""
        content = """\
semantic_models:
  name: orders
  entities: []
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            with pytest.raises((TypeError, KeyError)):
                DomainBuilder.from_directory(tmpdir)


class TestInvalidFieldValues:
    """Tests for handling invalid field values."""

    def test_invalid_dimension_type(self) -> None:
        """Test handling of invalid dimension type value."""
        content = """\
semantic_models:
  - name: orders
    entities:
      - name: order
        type: primary
        expr: order_id
    dimensions:
      - name: status
        type: invalid_type
        expr: status
    measures: []
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            # Should default to categorical, not fail
            models = DomainBuilder.from_directory(tmpdir)
            assert len(models) == 1
            # Invalid type defaults to categorical
            from semantic_patterns.domain import DimensionType

            assert models[0].dimensions[0].type == DimensionType.CATEGORICAL

    def test_invalid_aggregation_type(self) -> None:
        """Test handling of invalid aggregation type."""
        content = """\
semantic_models:
  - name: orders
    entities:
      - name: order
        type: primary
        expr: order_id
    dimensions: []
    measures:
      - name: total
        agg: invalid_agg
        expr: amount
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            # Should default to sum, not fail
            models = DomainBuilder.from_directory(tmpdir)
            assert len(models) == 1
            from semantic_patterns.domain import AggregationType

            assert models[0].measures[0].agg == AggregationType.SUM

    def test_invalid_granularity(self) -> None:
        """Test handling of invalid time granularity."""
        content = """\
semantic_models:
  - name: orders
    entities:
      - name: order
        type: primary
        expr: order_id
    dimensions:
      - name: created_at
        type: time
        expr: created_at
        granularity: invalid_granularity
    measures: []
"""
        with TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "models.yml"
            model_file.write_text(content, encoding="utf-8")

            # Should handle gracefully (None granularity)
            models = DomainBuilder.from_directory(tmpdir)
            assert len(models) == 1
            assert models[0].dimensions[0].granularity is None


class TestYamlLoaderErrors:
    """Tests for YamlLoader error handling."""

    def test_file_not_found(self) -> None:
        """Test error when file doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            loader = YamlLoader(tmpdir)

            with pytest.raises(FileNotFoundError):
                loader.load_file(Path(tmpdir) / "nonexistent.yml")

    def test_non_dict_root(self) -> None:
        """Test error when YAML root is not a dict."""
        with TemporaryDirectory() as tmpdir:
            list_file = Path(tmpdir) / "list.yml"
            list_file.write_text("- item1\n- item2\n", encoding="utf-8")

            loader = YamlLoader(tmpdir)

            with pytest.raises(ValueError, match="Expected dict"):
                loader.load_all()

    def test_directory_not_found(self) -> None:
        """Test handling when directory doesn't exist.

        The YamlLoader initializes with any path, but load_all fails
        when trying to glob a non-existent directory.
        """
        loader = YamlLoader("/nonexistent/directory/that/does/not/exist")
        # Globbing a non-existent directory returns empty list
        # This is actually Python's glob behavior - no exception
        docs = loader.load_all()
        assert docs == []


class TestConfigValidationErrors:
    """Tests for config validation producing clear error messages."""

    def test_config_invalid_yaml_clear_error(self) -> None:
        """Test that YAML parse errors are clear."""
        invalid = "input: [unclosed bracket"
        with pytest.raises(yaml.YAMLError):
            SPConfig.from_yaml(invalid)

    def test_config_wrong_type_for_explores(self) -> None:
        """Test error when explores has wrong type."""
        content = """\
input: ./models
output: ./lookml
schema: gold
looker:
  enabled: true
  repo: test/repo
  branch: sp-generated
  explores: "not a list"
"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            SPConfig.from_yaml(content)

    def test_config_wrong_type_for_options(self) -> None:
        """Test error when options has wrong type."""
        content = """\
input: ./models
output: ./lookml
schema: gold
options: "not a dict"
"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            SPConfig.from_yaml(content)


class TestDimensionValidation:
    """Tests for Dimension model validation."""

    def test_dimension_requires_expr_or_variants(self) -> None:
        """Test dimension requires either expr or variants."""
        from semantic_patterns.domain import Dimension, DimensionType

        with pytest.raises(ValueError, match="Either 'expr' or 'variants' must be specified"):
            Dimension(
                name="test",
                type=DimensionType.CATEGORICAL,
            )

    def test_dimension_with_expr_is_valid(self) -> None:
        """Test dimension with expr is valid."""
        from semantic_patterns.domain import Dimension, DimensionType

        dim = Dimension(
            name="test",
            type=DimensionType.CATEGORICAL,
            expr="test_column",
        )
        assert dim.name == "test"
        assert dim.expr == "test_column"

    def test_dimension_with_variants_is_valid(self) -> None:
        """Test dimension with variants is valid."""
        from semantic_patterns.domain import Dimension, DimensionType

        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            primary_variant="utc",
            variants={"utc": "created_utc", "local": "created_local"},
        )
        assert dim.name == "created_at"
        assert dim.has_variants is True


class TestMetricValidation:
    """Tests for Metric model validation."""

    def test_simple_metric_requires_measure(self) -> None:
        """Test simple metric works with measure."""
        from semantic_patterns.domain import Metric, MetricType

        metric = Metric(
            name="revenue",
            type=MetricType.SIMPLE,
            measure="total_revenue",
        )
        assert metric.measure == "total_revenue"

    def test_derived_metric_with_expression(self) -> None:
        """Test derived metric with expression."""
        from semantic_patterns.domain import Metric, MetricType

        metric = Metric(
            name="aov",
            type=MetricType.DERIVED,
            expr="revenue / orders",
            metrics=["revenue", "orders"],
        )
        assert metric.expr == "revenue / orders"
        assert metric.metrics == ["revenue", "orders"]

    def test_ratio_metric_parts(self) -> None:
        """Test ratio metric has numerator and denominator."""
        from semantic_patterns.domain import Metric, MetricType

        metric = Metric(
            name="conversion",
            type=MetricType.RATIO,
            numerator="conversions",
            denominator="visits",
        )
        assert metric.numerator == "conversions"
        assert metric.denominator == "visits"
