"""Tests for configuration loading and validation in config.py."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

from semantic_patterns.adapters.dialect import Dialect
from semantic_patterns.adapters.lookml.types import ExploreConfig, ExploreJoinConfig
from semantic_patterns.config import (
    ModelConfig,
    OptionsConfig,
    SPConfig,
    find_config,
    load_config,
)


class TestSPConfigFromYaml:
    """Tests for SPConfig.from_yaml parsing."""

    def test_minimal_valid_config(self) -> None:
        """Test parsing minimal valid config."""
        content = """\
input: ./models
output: ./lookml
schema: gold
"""
        config = SPConfig.from_yaml(content)

        assert config.input == "./models"
        assert config.output == "./lookml"
        assert config.schema_name == "gold"

    def test_full_config(self) -> None:
        """Test parsing config with all sections."""
        content = """\
input: ./semantic_models
output: ./generated
schema: analytics
format: semantic-patterns

options:
  dialect: snowflake
  pop_strategy: native
  date_selector: false
  convert_tz: true
  view_prefix: sm_
  explore_prefix: explore_

looker:
  enabled: true
  repo: test/repo
  branch: sp-generated

  model:
    name: my_model
    connection: redshift_prod
    label: My Analytics Model

  explores:
    - fact: orders
    - fact: users
      name: user_analytics
      label: User Insights
"""
        config = SPConfig.from_yaml(content)

        assert config.input == "./semantic_models"
        assert config.output == "./generated"
        assert config.schema_name == "analytics"
        assert config.format == "semantic-patterns"

        # Model settings
        assert config.model.name == "my_model"
        assert config.model.connection == "redshift_prod"
        assert config.model.label == "My Analytics Model"

        # Explores
        assert len(config.explores) == 2
        assert config.explores[0].fact == "orders"
        assert config.explores[1].fact == "users"
        assert config.explores[1].name == "user_analytics"
        assert config.explores[1].label == "User Insights"

        # Options
        assert config.options.dialect == Dialect.SNOWFLAKE
        assert config.options.pop_strategy == "native"
        assert config.options.date_selector is False
        assert config.options.convert_tz is True
        assert config.options.view_prefix == "sm_"
        assert config.options.explore_prefix == "explore_"


class TestSPConfigDefaults:
    """Tests for default values in SPConfig."""

    def test_default_format(self) -> None:
        """Test default format is semantic-patterns."""
        content = """\
input: ./models
output: ./lookml
schema: gold
"""
        config = SPConfig.from_yaml(content)
        assert config.format == "semantic-patterns"

    def test_default_model_settings(self) -> None:
        """Test default model settings."""
        content = """\
input: ./models
output: ./lookml
schema: gold
"""
        config = SPConfig.from_yaml(content)

        assert config.model.name == "semantic_model"
        assert config.model.connection == "database"
        assert config.model.label is None

    def test_default_options(self) -> None:
        """Test default option values."""
        content = """\
input: ./models
output: ./lookml
schema: gold
"""
        config = SPConfig.from_yaml(content)

        assert config.options.dialect == Dialect.REDSHIFT
        assert config.options.pop_strategy == "dynamic"
        assert config.options.date_selector is True
        assert config.options.convert_tz is False
        assert config.options.view_prefix == ""
        assert config.options.explore_prefix == ""

    def test_default_explores_empty(self) -> None:
        """Test explores defaults to empty list."""
        content = """\
input: ./models
output: ./lookml
schema: gold
"""
        config = SPConfig.from_yaml(content)
        assert config.explores == []


class TestSPConfigPaths:
    """Tests for path property methods."""

    def test_input_path(self) -> None:
        """Test input_path returns Path object."""
        content = """\
input: ./semantic_models
output: ./lookml
schema: gold
"""
        config = SPConfig.from_yaml(content)

        assert isinstance(config.input_path, Path)
        assert config.input_path == Path("./semantic_models")

    def test_output_path(self) -> None:
        """Test output_path returns Path object."""
        content = """\
input: ./models
output: /absolute/path/lookml
schema: gold
"""
        config = SPConfig.from_yaml(content)

        assert isinstance(config.output_path, Path)
        assert config.output_path == Path("/absolute/path/lookml")


class TestSPConfigValidation:
    """Tests for config validation errors."""

    def test_missing_required_input(self) -> None:
        """Test error when input is missing."""
        content = """\
output: ./lookml
schema: gold
"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            SPConfig.from_yaml(content)

    def test_missing_required_output(self) -> None:
        """Test error when output is missing."""
        content = """\
input: ./models
schema: gold
"""
        with pytest.raises(Exception):
            SPConfig.from_yaml(content)

    def test_missing_required_schema(self) -> None:
        """Test error when schema is missing."""
        content = """\
input: ./models
output: ./lookml
"""
        with pytest.raises(Exception):
            SPConfig.from_yaml(content)

    def test_invalid_format_value(self) -> None:
        """Test error for invalid format value."""
        content = """\
input: ./models
output: ./lookml
schema: gold
format: invalid_format
"""
        with pytest.raises(ValueError, match="Invalid format"):
            SPConfig.from_yaml(content)

    def test_invalid_dialect_value(self) -> None:
        """Test error for invalid dialect value."""
        content = """\
input: ./models
output: ./lookml
schema: gold
options:
  dialect: invalid_dialect
"""
        with pytest.raises(ValueError, match="Invalid dialect"):
            SPConfig.from_yaml(content)


class TestFormatValidation:
    """Tests for format field validation."""

    def test_format_dbt(self) -> None:
        """Test 'dbt' is a valid format."""
        content = """\
input: ./models
output: ./lookml
schema: gold
format: dbt
"""
        config = SPConfig.from_yaml(content)
        assert config.format == "dbt"

    def test_format_semantic_patterns(self) -> None:
        """Test 'semantic-patterns' is a valid format."""
        content = """\
input: ./models
output: ./lookml
schema: gold
format: semantic-patterns
"""
        config = SPConfig.from_yaml(content)
        assert config.format == "semantic-patterns"

    def test_format_case_insensitive(self) -> None:
        """Test format is case insensitive."""
        content = """\
input: ./models
output: ./lookml
schema: gold
format: DBT
"""
        config = SPConfig.from_yaml(content)
        assert config.format == "dbt"


class TestDialectValidation:
    """Tests for dialect field validation."""

    @pytest.mark.parametrize(
        "dialect_str,expected",
        [
            ("redshift", Dialect.REDSHIFT),
            ("postgres", Dialect.POSTGRES),
            ("snowflake", Dialect.SNOWFLAKE),
            ("bigquery", Dialect.BIGQUERY),
            ("duckdb", Dialect.DUCKDB),
            ("trino", Dialect.STARBURST),
        ],
    )
    def test_valid_dialects(self, dialect_str: str, expected: Dialect) -> None:
        """Test all valid dialects are parsed correctly."""
        content = f"""\
input: ./models
output: ./lookml
schema: gold
options:
  dialect: {dialect_str}
"""
        config = SPConfig.from_yaml(content)
        assert config.options.dialect == expected

    def test_dialect_case_insensitive(self) -> None:
        """Test dialect is case insensitive."""
        content = """\
input: ./models
output: ./lookml
schema: gold
options:
  dialect: SNOWFLAKE
"""
        config = SPConfig.from_yaml(content)
        assert config.options.dialect == Dialect.SNOWFLAKE


class TestExploreConfig:
    """Tests for ExploreConfig model."""

    def test_explore_effective_name_default(self) -> None:
        """Test effective_name defaults to fact."""
        explore = ExploreConfig(fact="orders")
        assert explore.effective_name == "orders"

    def test_explore_effective_name_custom(self) -> None:
        """Test effective_name uses name if provided."""
        explore = ExploreConfig(fact="orders", name="order_analytics")
        assert explore.effective_name == "order_analytics"

    def test_explore_with_joins(self) -> None:
        """Test explore with join configuration."""
        content = """\
input: ./models
output: ./lookml
schema: gold
looker:
  enabled: true
  repo: test/repo
  branch: sp-generated
  explores:
    - fact: orders
      joins:
        - model: users
          expose: dimensions
        - model: products
          expose: all
"""
        config = SPConfig.from_yaml(content)

        explore = config.explores[0]
        assert len(explore.joins) == 2
        assert explore.joins[0].model == "users"
        assert explore.joins[0].expose == "dimensions"
        assert explore.joins[1].model == "products"
        assert explore.joins[1].expose == "all"


class TestOptionsConfig:
    """Tests for OptionsConfig model."""

    def test_effective_explore_prefix_default(self) -> None:
        """Test effective_explore_prefix defaults to view_prefix."""
        options = OptionsConfig(view_prefix="sm_")
        assert options.effective_explore_prefix == "sm_"

    def test_effective_explore_prefix_explicit(self) -> None:
        """Test effective_explore_prefix uses explore_prefix if set."""
        options = OptionsConfig(view_prefix="sm_", explore_prefix="exp_")
        assert options.effective_explore_prefix == "exp_"

    def test_effective_explore_prefix_empty(self) -> None:
        """Test effective_explore_prefix with no prefixes."""
        options = OptionsConfig()
        assert options.effective_explore_prefix == ""


class TestFindConfig:
    """Tests for find_config function."""

    def test_find_config_in_current_dir(self) -> None:
        """Test finding config in current directory."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sp.yml"
            config_path.write_text("input: ./models\noutput: ./lookml\nschema: gold")

            found = find_config(tmpdir)
            # Use resolve() to handle macOS /private symlink
            assert found is not None
            assert found.resolve() == config_path.resolve()

    def test_find_config_sp_yaml(self) -> None:
        """Test finding sp.yaml (alternative extension)."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sp.yaml"
            config_path.write_text("input: ./models\noutput: ./lookml\nschema: gold")

            found = find_config(tmpdir)
            assert found is not None
            assert found.resolve() == config_path.resolve()

    def test_find_config_dot_sp_yml(self) -> None:
        """Test finding .sp.yml (hidden file)."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".sp.yml"
            config_path.write_text("input: ./models\noutput: ./lookml\nschema: gold")

            found = find_config(tmpdir)
            assert found is not None
            assert found.resolve() == config_path.resolve()

    def test_find_config_in_parent_dir(self) -> None:
        """Test finding config in parent directory."""
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            child = parent / "subdir"
            child.mkdir()

            config_path = parent / "sp.yml"
            config_path.write_text("input: ./models\noutput: ./lookml\nschema: gold")

            found = find_config(child)
            assert found is not None
            assert found.resolve() == config_path.resolve()

    def test_find_config_not_found(self) -> None:
        """Test None returned when no config found."""
        with TemporaryDirectory() as tmpdir:
            found = find_config(tmpdir)
            assert found is None


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_from_path(self) -> None:
        """Test loading config from explicit path."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "custom.yml"
            config_path.write_text(
                "input: ./models\noutput: ./lookml\nschema: gold",
                encoding="utf-8",
            )

            config = load_config(config_path)

            assert config.input == "./models"
            assert config.schema_name == "gold"

    def test_load_config_auto_find(self) -> None:
        """Test loading config with auto-discovery."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sp.yml"
            config_path.write_text(
                "input: ./models\noutput: ./lookml\nschema: gold",
                encoding="utf-8",
            )

            # Change to temp directory for auto-discovery
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = load_config()
                assert config.input == "./models"
            finally:
                os.chdir(original_cwd)

    def test_load_config_not_found_raises(self) -> None:
        """Test FileNotFoundError when no config found."""
        with TemporaryDirectory() as tmpdir:
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                with pytest.raises(FileNotFoundError, match="No sp.yml found"):
                    load_config()
            finally:
                os.chdir(original_cwd)


class TestSPConfigFromFile:
    """Tests for SPConfig.from_file method."""

    def test_from_file(self) -> None:
        """Test loading config from file path."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test.yml"
            config_path.write_text(
                "input: ./src\noutput: ./out\nschema: test",
                encoding="utf-8",
            )

            config = SPConfig.from_file(config_path)

            assert config.input == "./src"
            assert config.output == "./out"
            assert config.schema_name == "test"

    def test_from_file_string_path(self) -> None:
        """Test loading config from string path."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test.yml"
            config_path.write_text(
                "input: ./models\noutput: ./lookml\nschema: gold",
                encoding="utf-8",
            )

            config = SPConfig.from_file(str(config_path))

            assert config.input == "./models"


class TestModelConfig:
    """Tests for ModelConfig model."""

    def test_model_config_defaults(self) -> None:
        """Test ModelConfig default values."""
        model = ModelConfig()

        assert model.name == "semantic_model"
        assert model.connection == "database"
        assert model.label is None

    def test_model_config_custom(self) -> None:
        """Test ModelConfig with custom values."""
        model = ModelConfig(
            name="analytics",
            connection="warehouse",
            label="Analytics Model",
        )

        assert model.name == "analytics"
        assert model.connection == "warehouse"
        assert model.label == "Analytics Model"


class TestExploreJoinConfig:
    """Tests for ExploreJoinConfig model."""

    def test_join_config_minimal(self) -> None:
        """Test minimal join config."""
        join = ExploreJoinConfig(model="users")

        assert join.model == "users"
        assert join.expose is None

    def test_join_config_with_expose(self) -> None:
        """Test join config with expose option."""
        join = ExploreJoinConfig(model="users", expose="dimensions")

        assert join.model == "users"
        assert join.expose == "dimensions"
