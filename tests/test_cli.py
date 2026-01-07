"""Tests for CLI commands in __main__.py."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from semantic_patterns.__main__ import cli


class TestCLIBuild:
    """Tests for the 'sp build' command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI runner."""
        return CliRunner()

    @pytest.fixture
    def valid_config_content(self) -> str:
        """Valid sp.yml config content."""
        return """\
input: ./semantic_models
output: ./lookml
schema: gold

model:
  name: test_model
  connection: test_connection

options:
  dialect: redshift
"""

    @pytest.fixture
    def valid_semantic_model_content(self) -> str:
        """Valid semantic model YAML content."""
        return """\
version: 2

data_models:
  - name: orders
    schema: gold
    table: orders
    connection: redshift

semantic_models:
  - name: orders
    model: orders
    entities:
      - name: order
        type: primary
        expr: order_id

    dimensions:
      - name: status
        type: categorical
        expr: order_status

    measures:
      - name: order_count
        agg: count_distinct
        expr: order_id

metrics:
  - name: orders
    type: simple
    measure: order_count
    entity: order
"""

    def test_build_with_valid_config(
        self, runner: CliRunner, valid_config_content: str, valid_semantic_model_content: str
    ) -> None:
        """Test build command with valid config creates files."""
        with runner.isolated_filesystem():
            # Create config file
            Path("sp.yml").write_text(valid_config_content, encoding="utf-8")

            # Create input directory and semantic model
            Path("semantic_models").mkdir()
            Path("semantic_models/orders.yml").write_text(
                valid_semantic_model_content, encoding="utf-8"
            )

            result = runner.invoke(cli, ["build"])

            assert result.exit_code == 0
            assert "Generated" in result.output
            assert Path("lookml").exists()

    def test_build_with_explicit_config(
        self, runner: CliRunner, valid_config_content: str, valid_semantic_model_content: str
    ) -> None:
        """Test build command with --config option."""
        with runner.isolated_filesystem():
            # Create config file in subdirectory
            Path("configs").mkdir()
            Path("configs/custom.yml").write_text(valid_config_content, encoding="utf-8")

            # Create input directory and semantic model
            Path("semantic_models").mkdir()
            Path("semantic_models/orders.yml").write_text(
                valid_semantic_model_content, encoding="utf-8"
            )

            result = runner.invoke(cli, ["build", "--config", "configs/custom.yml"])

            assert result.exit_code == 0
            assert "Generated" in result.output

    def test_build_dry_run(
        self, runner: CliRunner, valid_config_content: str, valid_semantic_model_content: str
    ) -> None:
        """Test build --dry-run doesn't write files."""
        with runner.isolated_filesystem():
            Path("sp.yml").write_text(valid_config_content, encoding="utf-8")
            Path("semantic_models").mkdir()
            Path("semantic_models/orders.yml").write_text(
                valid_semantic_model_content, encoding="utf-8"
            )

            result = runner.invoke(cli, ["build", "--dry-run"])

            assert result.exit_code == 0
            assert "Dry run mode" in result.output
            assert "Would generate" in result.output
            # Output directory should not be created
            assert not Path("lookml").exists()

    def test_build_verbose(
        self, runner: CliRunner, valid_config_content: str, valid_semantic_model_content: str
    ) -> None:
        """Test build --verbose shows detailed output."""
        with runner.isolated_filesystem():
            Path("sp.yml").write_text(valid_config_content, encoding="utf-8")
            Path("semantic_models").mkdir()
            Path("semantic_models/orders.yml").write_text(
                valid_semantic_model_content, encoding="utf-8"
            )

            result = runner.invoke(cli, ["build", "--verbose"])

            assert result.exit_code == 0
            # Verbose output should show model details
            assert "orders" in result.output

    def test_build_no_config_found(self, runner: CliRunner) -> None:
        """Test build fails gracefully when no config found."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["build"])

            assert result.exit_code != 0
            assert "sp.yml" in result.output.lower() or "config" in result.output.lower()

    def test_build_config_not_exists(self, runner: CliRunner) -> None:
        """Test build fails when specified config doesn't exist."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["build", "--config", "nonexistent.yml"])

            assert result.exit_code != 0

    def test_build_no_models_found(self, runner: CliRunner, valid_config_content: str) -> None:
        """Test build fails when input directory is empty."""
        with runner.isolated_filesystem():
            Path("sp.yml").write_text(valid_config_content, encoding="utf-8")
            Path("semantic_models").mkdir()
            # No YAML files in directory

            result = runner.invoke(cli, ["build"])

            assert result.exit_code != 0
            assert "No semantic models found" in result.output or "error" in result.output.lower()

    def test_build_input_directory_not_exists(self, runner: CliRunner) -> None:
        """Test build fails when input directory doesn't exist."""
        config = """\
input: ./nonexistent_dir
output: ./lookml
schema: gold
"""
        with runner.isolated_filesystem():
            Path("sp.yml").write_text(config, encoding="utf-8")

            result = runner.invoke(cli, ["build"])

            assert result.exit_code != 0


class TestCLIInit:
    """Tests for the 'sp init' command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI runner."""
        return CliRunner()

    def test_init_creates_config(self, runner: CliRunner) -> None:
        """Test init creates sp.yml file."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert Path("sp.yml").exists()
            assert "Created" in result.output

    def test_init_config_has_expected_sections(self, runner: CliRunner) -> None:
        """Test init creates config with expected content."""
        with runner.isolated_filesystem():
            runner.invoke(cli, ["init"])

            content = Path("sp.yml").read_text(encoding="utf-8")

            assert "input:" in content
            assert "output:" in content
            assert "schema:" in content
            assert "model:" in content
            assert "options:" in content

    def test_init_fails_if_config_exists(self, runner: CliRunner) -> None:
        """Test init fails when sp.yml already exists."""
        with runner.isolated_filesystem():
            Path("sp.yml").write_text("existing: content", encoding="utf-8")

            result = runner.invoke(cli, ["init"])

            assert result.exit_code != 0
            assert "already exists" in result.output


class TestCLIValidate:
    """Tests for the 'sp validate' command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI runner."""
        return CliRunner()

    @pytest.fixture
    def valid_config_content(self) -> str:
        """Valid sp.yml config content."""
        return """\
input: ./semantic_models
output: ./lookml
schema: gold

model:
  name: test_model
  connection: test_connection
"""

    @pytest.fixture
    def valid_semantic_model_content(self) -> str:
        """Valid semantic model content."""
        return """\
data_models:
  - name: orders
    schema: gold
    table: orders

semantic_models:
  - name: orders
    model: orders
    entities:
      - name: order
        type: primary
        expr: order_id
    dimensions:
      - name: status
        type: categorical
        expr: status
    measures:
      - name: count
        agg: count
        expr: "1"
"""

    def test_validate_valid_config(
        self, runner: CliRunner, valid_config_content: str, valid_semantic_model_content: str
    ) -> None:
        """Test validate passes for valid config and models."""
        with runner.isolated_filesystem():
            Path("sp.yml").write_text(valid_config_content, encoding="utf-8")
            Path("semantic_models").mkdir()
            Path("semantic_models/orders.yml").write_text(
                valid_semantic_model_content, encoding="utf-8"
            )

            result = runner.invoke(cli, ["validate"])

            assert result.exit_code == 0
            assert "valid" in result.output.lower() or "passed" in result.output.lower()

    def test_validate_no_config_found(self, runner: CliRunner) -> None:
        """Test validate fails when no config found."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["validate"])

            assert result.exit_code != 0

    def test_validate_input_not_exists(self, runner: CliRunner) -> None:
        """Test validate fails when input directory doesn't exist."""
        config = """\
input: ./nonexistent
output: ./lookml
schema: gold
"""
        with runner.isolated_filesystem():
            Path("sp.yml").write_text(config, encoding="utf-8")

            result = runner.invoke(cli, ["validate"])

            assert result.exit_code != 0
            assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_validate_with_explores(self, runner: CliRunner) -> None:
        """Test validate checks explore fact model references."""
        config = """\
input: ./semantic_models
output: ./lookml
schema: gold

looker:
  enabled: true
  repo: test/repo
  branch: sp-generated
  explores:
    - fact: nonexistent_model
"""
        model_content = """\
semantic_models:
  - name: orders
    entities:
      - name: order
        type: primary
        expr: order_id
    dimensions:
      - name: status
        type: categorical
        expr: status
    measures:
      - name: count
        agg: count
        expr: "1"
"""
        with runner.isolated_filesystem():
            Path("sp.yml").write_text(config, encoding="utf-8")
            Path("semantic_models").mkdir()
            Path("semantic_models/orders.yml").write_text(model_content, encoding="utf-8")

            result = runner.invoke(cli, ["validate"])

            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_validate_with_explicit_config(
        self, runner: CliRunner, valid_config_content: str, valid_semantic_model_content: str
    ) -> None:
        """Test validate with --config option."""
        with runner.isolated_filesystem():
            Path("configs").mkdir()
            Path("configs/test.yml").write_text(valid_config_content, encoding="utf-8")
            Path("semantic_models").mkdir()
            Path("semantic_models/orders.yml").write_text(
                valid_semantic_model_content, encoding="utf-8"
            )

            result = runner.invoke(cli, ["validate", "--config", "configs/test.yml"])

            assert result.exit_code == 0


class TestCLIVersionAndHelp:
    """Tests for version and help output."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI runner."""
        return CliRunner()

    def test_help_output(self, runner: CliRunner) -> None:
        """Test --help shows usage information."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "build" in result.output
        assert "init" in result.output
        assert "validate" in result.output

    def test_build_help(self, runner: CliRunner) -> None:
        """Test build --help shows command options."""
        result = runner.invoke(cli, ["build", "--help"])

        assert result.exit_code == 0
        assert "--config" in result.output
        assert "--dry-run" in result.output
        assert "--verbose" in result.output

    def test_version_output(self, runner: CliRunner) -> None:
        """Test --version shows version information."""
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        # Should show some version info
        assert "version" in result.output.lower() or "." in result.output


class TestCLIAuth:
    """Tests for the 'sp auth' command group."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI runner."""
        return CliRunner()

    def test_auth_help(self, runner: CliRunner) -> None:
        """Test auth --help shows available commands."""
        result = runner.invoke(cli, ["auth", "--help"])

        assert result.exit_code == 0
        assert "Manage authentication credentials" in result.output
        assert "status" in result.output
        assert "clear" in result.output
        assert "test" in result.output
        assert "reset" in result.output
        assert "whoami" in result.output

    @patch("semantic_patterns.credentials.get_credential_store")
    def test_auth_status_no_credentials(self, mock_store_fn, runner: CliRunner) -> None:
        """Test auth status shows 'not configured' when no credentials set."""
        mock_store = MagicMock()
        mock_store.get.return_value = None
        mock_store_fn.return_value = mock_store

        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(cli, ["auth", "status"])

            assert result.exit_code == 0
            assert "Not configured" in result.output
            assert "GitHub" in result.output
            assert "Looker" in result.output

    @patch("semantic_patterns.credentials.get_credential_store")
    def test_auth_status_with_github_env(self, mock_store_fn, runner: CliRunner) -> None:
        """Test auth status shows GitHub env var override."""
        mock_store = MagicMock()
        mock_store.get.return_value = None
        mock_store_fn.return_value = mock_store

        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"}):
            result = runner.invoke(cli, ["auth", "status"])

            assert result.exit_code == 0
            assert "GITHUB_TOKEN env var will override keychain" in result.output

    def test_auth_clear_github_with_force(self, runner: CliRunner) -> None:
        """Test auth clear github --force doesn't prompt."""
        result = runner.invoke(cli, ["auth", "clear", "github", "--force"])

        # Should complete without prompting
        assert result.exit_code == 0
        assert "Cancelled" not in result.output

    def test_auth_clear_looker_with_force(self, runner: CliRunner) -> None:
        """Test auth clear looker --force doesn't prompt."""
        result = runner.invoke(cli, ["auth", "clear", "looker", "--force"])

        assert result.exit_code == 0

    def test_auth_clear_all_with_force(self, runner: CliRunner) -> None:
        """Test auth clear all --force clears all credentials."""
        result = runner.invoke(cli, ["auth", "clear", "all", "--force"])

        assert result.exit_code == 0
        assert "Looker client ID" in result.output
        assert "Looker client secret" in result.output
        assert "GitHub token" in result.output

    def test_auth_clear_cancellation(self, runner: CliRunner) -> None:
        """Test auth clear prompts and respects cancellation."""
        result = runner.invoke(cli, ["auth", "clear", "github"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output

    def test_auth_clear_confirmation(self, runner: CliRunner) -> None:
        """Test auth clear prompts and respects confirmation."""
        result = runner.invoke(cli, ["auth", "clear", "all"], input="y\n")

        assert result.exit_code == 0
        assert "Continue?" in result.output

    def test_auth_reset_with_force(self, runner: CliRunner) -> None:
        """Test auth reset --force clears all credentials."""
        result = runner.invoke(cli, ["auth", "reset", "--force"])

        assert result.exit_code == 0

    def test_auth_reset_without_force_prompts(self, runner: CliRunner) -> None:
        """Test auth reset without --force prompts for confirmation."""
        result = runner.invoke(cli, ["auth", "reset"], input="n\n")

        assert result.exit_code == 0
        assert "Continue?" in result.output

    @patch("semantic_patterns.credentials.get_credential_store")
    def test_auth_test_github_no_credentials(self, mock_store_fn, runner: CliRunner) -> None:
        """Test auth test github shows error when no credentials configured."""
        mock_store = MagicMock()
        mock_store.get.return_value = None
        mock_store_fn.return_value = mock_store

        result = runner.invoke(cli, ["auth", "test", "github"])

        assert result.exit_code == 0
        assert "No GitHub token configured" in result.output

    @patch("semantic_patterns.credentials.get_credential_store")
    def test_auth_test_looker_no_credentials(self, mock_store_fn, runner: CliRunner) -> None:
        """Test auth test looker shows error when no credentials configured."""
        mock_store = MagicMock()
        mock_store.get.return_value = None
        mock_store_fn.return_value = mock_store

        result = runner.invoke(cli, ["auth", "test", "looker"])

        assert result.exit_code == 0
        assert "Looker credentials not configured" in result.output

    @patch("semantic_patterns.credentials.get_credential_store")
    def test_auth_whoami_no_credentials(self, mock_store_fn, runner: CliRunner) -> None:
        """Test auth whoami shows 'not authenticated' when no credentials."""
        mock_store = MagicMock()
        mock_store.get.return_value = None
        mock_store_fn.return_value = mock_store

        result = runner.invoke(cli, ["auth", "whoami"])

        assert result.exit_code == 0
        assert "Not authenticated" in result.output
        assert "GitHub" in result.output
        assert "Looker" in result.output

    def test_auth_clear_help(self, runner: CliRunner) -> None:
        """Test auth clear --help shows usage information."""
        result = runner.invoke(cli, ["auth", "clear", "--help"])

        assert result.exit_code == 0
        assert "SERVICE" in result.output
        assert "github" in result.output.lower()
        assert "looker" in result.output.lower()
        assert "all" in result.output.lower()

    def test_auth_test_help(self, runner: CliRunner) -> None:
        """Test auth test --help shows usage information."""
        result = runner.invoke(cli, ["auth", "test", "--help"])

        assert result.exit_code == 0
        assert "SERVICE" in result.output
        assert "github" in result.output.lower()
        assert "looker" in result.output.lower()
        assert "--debug" in result.output

    def test_auth_status_help(self, runner: CliRunner) -> None:
        """Test auth status --help shows usage information."""
        result = runner.invoke(cli, ["auth", "status", "--help"])

        assert result.exit_code == 0

    def test_auth_reset_help(self, runner: CliRunner) -> None:
        """Test auth reset --help shows usage information."""
        result = runner.invoke(cli, ["auth", "reset", "--help"])

        assert result.exit_code == 0
        assert "--force" in result.output

    def test_auth_whoami_help(self, runner: CliRunner) -> None:
        """Test auth whoami --help shows usage information."""
        result = runner.invoke(cli, ["auth", "whoami", "--help"])

        assert result.exit_code == 0
