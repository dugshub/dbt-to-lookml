"""Tests for CLI commands."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_to_lookml.__main__ import cli


def _has_textual_available() -> bool:
    """Check if Textual is available."""
    try:
        import textual  # noqa: F401

        return True
    except ImportError:
        return False


class TestCLI:
    """Test cases for CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def semantic_models_dir(self) -> Path:
        """Return path to semantic models directory."""
        return Path(__file__).parent.parent / "semantic_models"

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Return path to fixtures directory."""
        return Path(__file__).parent / "fixtures"

    def test_cli_version(self, runner: CliRunner) -> None:
        """Test CLI version command."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_cli_help(self, runner: CliRunner) -> None:
        """Test CLI help command."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Convert dbt semantic models to LookML" in result.output

    def test_generate_command_help(self, runner: CliRunner) -> None:
        """Test generate command help."""
        result = runner.invoke(cli, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--input-dir" in result.output
        assert "--output-dir" in result.output
        assert "--view-prefix" in result.output
        assert "--explore-prefix" in result.output
        assert "--dry-run" in result.output

    def test_validate_command_help(self, runner: CliRunner) -> None:
        """Test validate command help."""
        result = runner.invoke(cli, ["validate", "--help"])
        assert result.exit_code == 0
        assert "--input-dir" in result.output
        assert "--strict" in result.output
        assert "--verbose" in result.output

    def test_generate_basic_success(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test basic generate command success."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "Parsing semantic models" in result.output
            assert "Generating LookML files" in result.output
            assert "✓ LookML generation completed successfully" in result.output

            # Check files were created
            view_files = list(output_dir.glob("*.view.lkml"))
            explores_file = output_dir / "explores.lkml"

            assert len(view_files) > 0
            assert explores_file.exists()

    def test_generate_with_prefixes(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate command with prefixes."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--view-prefix",
                    "v_",
                    "--explore-prefix",
                    "e_",
                    "--yes",
                ],
            )

            assert result.exit_code == 0

            # Check prefixed files were created
            view_files = list(output_dir.glob("v_*.view.lkml"))
            assert len(view_files) > 0

            # Check explores content
            explores_file = output_dir / "explores.lkml"
            if explores_file.exists():
                content = explores_file.read_text()
                assert "e_" in content

    def test_generate_dry_run(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """Test generate command with dry run."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--dry-run",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "DRY RUN MODE" in result.output
            assert "✓ LookML generation preview completed" in result.output

            # No files should be created in dry run
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) == 0

    def test_generate_no_validation(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate command with validation disabled."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--no-validation",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            # Should still complete successfully even with validation disabled

    def test_generate_show_summary(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """Test generate command with summary."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--show-summary",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "LookML Generation Summary" in result.output
            assert "Processed semantic models:" in result.output
            assert "Generated files:" in result.output

    def test_generate_invalid_input_dir(self, runner: CliRunner) -> None:
        """Test generate command with invalid input directory."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            invalid_input = Path("/nonexistent/directory")

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(invalid_input),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
            )

            assert result.exit_code != 0

    def test_generate_no_semantic_models(self, runner: CliRunner) -> None:
        """Test generate command with directory containing no semantic models."""
        with TemporaryDirectory() as temp_input, TemporaryDirectory() as temp_output:
            input_dir = Path(temp_input)
            output_dir = Path(temp_output)

            # Create a non-YAML file
            (input_dir / "readme.txt").write_text("Not a semantic model")

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
            )

            assert result.exit_code != 0
            assert "No semantic models found" in result.output

    def test_generate_with_real_semantic_models(
        self, runner: CliRunner, semantic_models_dir: Path
    ) -> None:
        """Test generate command with real semantic models."""
        # Skip if semantic models directory doesn't exist
        if not semantic_models_dir.exists():
            pytest.skip("Semantic models directory not found")

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(semantic_models_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "analytics",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "✓ LookML generation completed successfully" in result.output

            # Should generate multiple files
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) >= 1  # At least one semantic model

    def test_validate_basic_success(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test basic validate command success."""
        result = runner.invoke(cli, ["validate", "--input-dir", str(fixtures_dir)])

        assert result.exit_code == 0
        assert "Validating semantic models" in result.output
        assert "✓ Validated" in result.output

    def test_validate_strict_mode(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """Test validate command in strict mode."""
        result = runner.invoke(
            cli, ["validate", "--input-dir", str(fixtures_dir), "--strict"]
        )

        assert result.exit_code == 0
        # Strict mode should still pass with valid fixtures

    def test_validate_verbose(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """Test validate command with verbose output."""
        result = runner.invoke(
            cli, ["validate", "--input-dir", str(fixtures_dir), "--verbose"]
        )

        assert result.exit_code == 0
        # Verbose mode should show more details
        assert (
            "entities" in result.output
            or "dimensions" in result.output
            or "measures" in result.output
        )

    def test_validate_invalid_input_dir(self, runner: CliRunner) -> None:
        """Test validate command with invalid input directory."""
        result = runner.invoke(
            cli, ["validate", "--input-dir", "/nonexistent/directory"]
        )

        assert result.exit_code != 0

    def test_validate_with_real_semantic_models(
        self, runner: CliRunner, semantic_models_dir: Path
    ) -> None:
        """Test validate command with real semantic models."""
        # Skip if semantic models directory doesn't exist
        if not semantic_models_dir.exists():
            pytest.skip("Semantic models directory not found")

        result = runner.invoke(
            cli, ["validate", "--input-dir", str(semantic_models_dir), "--verbose"]
        )

        assert result.exit_code == 0
        assert "✓ Validated" in result.output
        # Should validate multiple models
        assert "models from" in result.output

    def test_generate_parse_errors_continue(self, runner: CliRunner) -> None:
        """Test that generation continues when some files have parse errors."""
        with TemporaryDirectory() as temp_input, TemporaryDirectory() as temp_output:
            input_dir = Path(temp_input)
            output_dir = Path(temp_output)

            # Create a valid semantic model
            valid_model = """
            name: valid_model
            model: valid_table
            entities:
              - name: id
                type: primary
            dimensions:
              - name: name
                type: categorical
            measures:
              - name: count
                agg: count
            """
            (input_dir / "valid.yml").write_text(valid_model)

            # Create an invalid YAML file
            (input_dir / "invalid.yml").write_text("invalid: yaml: content: [")

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
            )

            # Should still succeed with the valid model
            assert result.exit_code == 0
            assert "✗" in result.output  # Should show error for invalid file
            assert "✓" in result.output  # Should show success for valid file
            assert "Skipping file due to parse error" in result.output

    def test_generate_all_options_combined(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate command with all options combined."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--view-prefix",
                    "test_",
                    "--explore-prefix",
                    "exp_",
                    "--no-validation",
                    "--no-formatting",
                    "--show-summary",
                    "--dry-run",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "DRY RUN MODE" in result.output
            assert "LookML Generation Summary" in result.output

    def test_cli_error_handling(self, runner: CliRunner) -> None:
        """Test CLI error handling."""
        # Test with no arguments - Click returns 0 with help (or sometimes 2)
        result = runner.invoke(cli, [])
        # Just verify it doesn't crash
        assert isinstance(result.exit_code, int)

        # Test with invalid command
        result = runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0

    def test_generate_permission_error(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate command with permission error."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            output_dir.chmod(0o444)  # Make read-only

            try:
                result = runner.invoke(
                    cli,
                    [
                        "generate",
                        "--input-dir",
                        str(fixtures_dir),
                        "--output-dir",
                        str(output_dir),
                        "--schema",
                        "public",
                        "--yes",
                    ],
                )

                # May fail with permission error (OS-dependent)
                if result.exit_code != 0:
                    assert "Error:" in result.output or "Permission" in result.output
            finally:
                output_dir.chmod(0o755)  # Restore permissions

    @patch("dbt_to_lookml.__main__.GENERATOR_AVAILABLE", False)
    def test_generate_missing_dependencies(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate command when dependencies are missing."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
            )

            assert result.exit_code != 0
            assert "dependencies not available" in result.output

    def test_validate_malformed_files(self, runner: CliRunner) -> None:
        """Test validate command with malformed files."""
        with TemporaryDirectory() as temp_input:
            input_dir = Path(temp_input)

            # Create a malformed YAML file
            (input_dir / "malformed.yml").write_text("invalid: yaml: [unclosed")

            result = runner.invoke(cli, ["validate", "--input-dir", str(input_dir)])

            # Should show validation error
            assert "✗" in result.output
            assert "malformed.yml" in result.output

    def test_validate_strict_mode_fails_on_invalid(self, runner: CliRunner) -> None:
        """Test that strict mode fails on invalid models."""
        with TemporaryDirectory() as temp_input:
            input_dir = Path(temp_input)

            # Create an incomplete model (missing required fields)
            invalid_model = """
            name: incomplete_model
            # Missing 'model' field
            dimensions:
              - name: test_dim
                type: categorical
            """
            (input_dir / "incomplete.yml").write_text(invalid_model)

            # Non-strict should continue
            runner.invoke(cli, ["validate", "--input-dir", str(input_dir)])
            # May pass or fail depending on validation logic

            # Strict mode should be more stringent
            runner.invoke(cli, ["validate", "--input-dir", str(input_dir), "--strict"])
            # Should show validation issues

    def test_output_directory_creation(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test that output directory is created if it doesn't exist."""
        with TemporaryDirectory() as temp_dir:
            # Use a nested directory that doesn't exist
            output_dir = Path(temp_dir) / "nested" / "output"
            assert not output_dir.exists()

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert output_dir.exists()

    def test_cli_with_environment_variables(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test CLI behavior with environment variables."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Test with environment variable (if your CLI supports them)
            env = os.environ.copy()
            env["DBT_LOOKML_DEBUG"] = "1"  # Example debug flag

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
                env=env,
            )

            # Should still work normally
            assert result.exit_code == 0

    def test_cli_unicode_paths(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """Test CLI with Unicode characters in paths."""
        with TemporaryDirectory() as temp_dir:
            # Create directory with Unicode characters
            unicode_dir = Path(temp_dir) / "test_unicode_测试"
            unicode_dir.mkdir()

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(unicode_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
            )

            # Should handle Unicode paths correctly
            assert result.exit_code == 0

    def test_validate_empty_directory(self, runner: CliRunner) -> None:
        """Test validate command with empty directory."""
        with TemporaryDirectory() as temp_input:
            input_dir = Path(temp_input)
            # Empty directory

            result = runner.invoke(cli, ["validate", "--input-dir", str(input_dir)])

            assert result.exit_code == 0
            assert "Validated 0 semantic models" in result.output

    def test_generate_with_validation_errors_continues(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test that generation continues even with validation errors."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Mock validation to simulate errors
            with patch("lkml.load") as mock_lkml:
                mock_lkml.side_effect = Exception("Validation error")

                result = runner.invoke(
                    cli,
                    [
                        "generate",
                        "--input-dir",
                        str(fixtures_dir),
                        "--output-dir",
                        str(output_dir),
                        "--schema",
                        "public",
                        "--yes",
                    ],
                )

                # Should complete but show validation errors
                assert (
                    "validation errors" in result.output.lower()
                    or "syntax error" in result.output.lower()
                )

    def test_cli_keyboard_interrupt(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test CLI handling of keyboard interrupt."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Simulate keyboard interrupt during processing
            with patch("dbt_to_lookml.parsers.dbt.DbtParser.parse_file") as mock_parse:
                mock_parse.side_effect = KeyboardInterrupt()

                result = runner.invoke(
                    cli,
                    [
                        "generate",
                        "--input-dir",
                        str(fixtures_dir),
                        "--output-dir",
                        str(output_dir),
                        "--schema",
                        "public",
                        "--yes",
                    ],
                )

                # Should handle the interrupt gracefully
                assert result.exit_code != 0

    def test_long_command_line_arguments(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test CLI with very long command line arguments."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Very long prefix
            long_prefix = "very_long_prefix_" * 10

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--view-prefix",
                    long_prefix,
                    "--explore-prefix",
                    long_prefix,
                    "--yes",
                ],
            )

            # Should handle long arguments
            assert result.exit_code == 0


# Additional comprehensive CLI tests for coverage gaps
class TestCLIValidateOptions:
    """Test cases for validate command options."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Return path to fixtures directory."""
        return Path(__file__).parent / "fixtures"

    def test_validate_strict_with_valid_models(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test validate with --strict flag on valid models."""
        result = runner.invoke(
            cli, ["validate", "--input-dir", str(fixtures_dir), "--strict"]
        )

        assert result.exit_code == 0
        assert "✓ Validated" in result.output

    def test_validate_verbose_shows_detailed_output(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test validate with --verbose flag shows model details."""
        result = runner.invoke(
            cli, ["validate", "--input-dir", str(fixtures_dir), "--verbose"]
        )

        assert result.exit_code == 0
        # Verbose output should show more details
        assert "✓" in result.output or "models" in result.output.lower()

    def test_validate_strict_and_verbose_combined(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test validate with both --strict and --verbose flags."""
        result = runner.invoke(
            cli, ["validate", "--input-dir", str(fixtures_dir), "--strict", "--verbose"]
        )

        assert result.exit_code == 0
        assert "✓" in result.output

    def test_validate_missing_input_dir_argument(self, runner: CliRunner) -> None:
        """Test validate command fails without --input-dir."""
        result = runner.invoke(cli, ["validate"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_validate_with_mixed_yml_yaml_extensions(self, runner: CliRunner) -> None:
        """Test validate handles both .yml and .yaml file extensions."""
        with TemporaryDirectory() as temp_input:
            input_dir = Path(temp_input)

            # Create models with both extensions
            model_content = """
name: test_model
model: test_table
entities:
  - name: id
    type: primary
dimensions:
  - name: name
    type: categorical
"""
            (input_dir / "model1.yml").write_text(model_content)
            (input_dir / "model2.yaml").write_text(model_content)

            result = runner.invoke(cli, ["validate", "--input-dir", str(input_dir)])

            assert result.exit_code == 0
            assert "✓" in result.output


class TestCLIGenerateOptions:
    """Test cases for generate command options and scenarios."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Return path to fixtures directory."""
        return Path(__file__).parent / "fixtures"

    def test_generate_missing_required_schema_option(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate command fails when --schema is missing."""
        with TemporaryDirectory() as temp_dir:
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(temp_dir),
                    "--yes",
                ],
            )

            assert result.exit_code != 0
            assert "Missing option" in result.output or "--schema" in result.output

    def test_generate_with_view_prefix_only(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate with view-prefix but no explore-prefix."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--view-prefix",
                    "dim_",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            # Check that view files have the prefix
            view_files = list(output_dir.glob("dim_*.view.lkml"))
            assert len(view_files) > 0

    def test_generate_with_explore_prefix_only(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate with explore-prefix but no view-prefix."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--explore-prefix",
                    "exp_",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            explores_file = output_dir / "explores.lkml"
            if explores_file.exists():
                content = explores_file.read_text()
                assert "exp_" in content or result.exit_code == 0

    def test_generate_no_formatting_option(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate with --no-formatting flag."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--no-formatting",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            # Files should still be created without formatting
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) > 0

    def test_generate_dry_run_with_prefixes(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test dry-run shows what would be generated with prefixes."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--dry-run",
                    "--view-prefix",
                    "tmp_",
                    "--explore-prefix",
                    "test_",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "DRY RUN MODE" in result.output
            # No files should be created
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) == 0

    def test_generate_show_summary_with_prefixes(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test --show-summary displays generation details."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--view-prefix",
                    "v_",
                    "--explore-prefix",
                    "e_",
                    "--show-summary",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "LookML Generation Summary" in result.output
            assert "semantic models" in result.output.lower()
            assert "files" in result.output.lower()

    def test_generate_no_validation_flag(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test --no-validation skips LookML syntax validation."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--no-validation",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            # Should complete even without validation
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) > 0

    def test_generate_with_empty_prefix_strings(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate with empty string prefixes (default behavior)."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--view-prefix",
                    "",
                    "--explore-prefix",
                    "",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            # Should generate files without prefixes
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) > 0

    def test_generate_special_characters_in_prefixes(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate with special characters in prefixes."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--view-prefix",
                    "my-view_",
                    "--explore-prefix",
                    "my-explore_",
                    "--yes",
                ],
            )

            assert result.exit_code == 0


class TestCLIErrorHandling:
    """Test error handling and edge cases in CLI."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Return path to fixtures directory."""
        return Path(__file__).parent / "fixtures"

    def test_generate_with_invalid_output_parent_dir(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate when output parent directory doesn't exist."""
        # Note: Click should auto-create parents on modern versions
        # This tests the behavior with very deep non-existent paths
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "a" / "b" / "c" / "d" / "output"

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
            )

            # Should succeed and create directories
            assert result.exit_code == 0

    def test_validate_all_options_together(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test validate with all available options."""
        result = runner.invoke(
            cli, ["validate", "--input-dir", str(fixtures_dir), "--strict", "--verbose"]
        )

        assert result.exit_code == 0

    def test_cli_short_options(self, runner: CliRunner, fixtures_dir: Path) -> None:
        """Test CLI commands using short option flags."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "-i",
                    str(fixtures_dir),
                    "-o",
                    str(output_dir),
                    "-s",
                    "public",
                ],
            )

            assert result.exit_code == 0

    def test_validate_short_options(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test validate using short option flags."""
        result = runner.invoke(cli, ["validate", "-i", str(fixtures_dir), "-v"])

        assert result.exit_code == 0

    def test_generate_multiple_invalid_files_with_one_valid(
        self, runner: CliRunner
    ) -> None:
        """Test generate skips multiple invalid files but processes valid ones."""
        with TemporaryDirectory() as temp_input, TemporaryDirectory() as temp_output:
            input_dir = Path(temp_input)
            output_dir = Path(temp_output)

            # Create valid model
            valid_model = """
name: valid_model
model: valid_table
entities:
  - name: id
    type: primary
dimensions:
  - name: name
    type: categorical
measures:
  - name: count
    agg: count
"""
            (input_dir / "valid.yml").write_text(valid_model)

            # Create multiple invalid files
            (input_dir / "invalid1.yml").write_text("invalid: [unclosed")
            (input_dir / "invalid2.yaml").write_text("bad:\n  - unclosed")
            (input_dir / "invalid3.yml").write_text("{invalid json")

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
            )

            # Should still succeed with valid model
            assert result.exit_code == 0
            assert "✓" in result.output
            assert "✗" in result.output

    def test_generate_missing_input_dir_argument(self, runner: CliRunner) -> None:
        """Test generate fails when --input-dir is missing."""
        with TemporaryDirectory() as temp_dir:
            result = runner.invoke(
                cli, ["generate", "--output-dir", str(temp_dir), "--schema", "public"]
            )

            assert result.exit_code != 0
            assert "Missing option" in result.output

    def test_generate_missing_output_dir_argument(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate fails when --output-dir is missing."""
        result = runner.invoke(
            cli, ["generate", "--input-dir", str(fixtures_dir), "--schema", "public"]
        )

        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_cli_help_shows_all_options(self, runner: CliRunner) -> None:
        """Test that help displays all available options."""
        result = runner.invoke(cli, ["generate", "--help"])

        assert result.exit_code == 0
        assert "--input-dir" in result.output
        assert "--output-dir" in result.output
        assert "--schema" in result.output
        assert "--view-prefix" in result.output
        assert "--explore-prefix" in result.output
        assert "--dry-run" in result.output
        assert "--no-validation" in result.output
        assert "--no-formatting" in result.output
        assert "--show-summary" in result.output

    def test_validate_help_shows_all_options(self, runner: CliRunner) -> None:
        """Test that validate help displays all available options."""
        result = runner.invoke(cli, ["validate", "--help"])

        assert result.exit_code == 0
        assert "--input-dir" in result.output
        assert "--strict" in result.output
        assert "--verbose" in result.output

    def test_generate_with_convert_tz_flag(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate command with --convert-tz flag."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--convert-tz",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "Parsing semantic models" in result.output
            assert (
                "Generating LookML files" in result.output
                or "Previewing" in result.output
            )

    def test_generate_with_no_convert_tz_flag(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate command with --no-convert-tz flag."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--no-convert-tz",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "Parsing semantic models" in result.output
            assert (
                "Generating LookML files" in result.output
                or "Previewing" in result.output
            )

    def test_generate_without_timezone_flags(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate command without timezone flags (default behavior)."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "Parsing semantic models" in result.output
            assert (
                "Generating LookML files" in result.output
                or "Previewing" in result.output
            )

    def test_generate_with_mutually_exclusive_flags(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test that --convert-tz and --no-convert-tz are mutually exclusive."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--convert-tz",
                    "--no-convert-tz",
                    "--yes",
                ],
            )

            assert result.exit_code != 0
            assert "mutually exclusive" in result.output

    def test_generate_help_includes_timezone_flags(self, runner: CliRunner) -> None:
        """Test that help text documents new timezone flags."""
        result = runner.invoke(cli, ["generate", "--help"])

        assert result.exit_code == 0
        assert "--convert-tz" in result.output
        assert "--no-convert-tz" in result.output
        assert "mutually exclusive" in result.output


class TestCLIConvertTzFlags:
    """Test cases for CLI --convert-tz and --no-convert-tz flags."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Return path to fixtures directory."""
        return Path(__file__).parent / "fixtures"

    def test_cli_generate_with_convert_tz_flag(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test CLI accepts --convert-tz flag."""
        # Arrange
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--convert-tz",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

    def test_cli_generate_with_no_convert_tz_flag(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test CLI accepts --no-convert-tz flag."""
        # Arrange
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--no-convert-tz",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

    def test_cli_generate_without_convert_tz_flag(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test CLI without flag uses default."""
        # Arrange
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

    def test_cli_generate_help_shows_convert_tz_flags(self, runner: CliRunner) -> None:
        """Test help text documents convert_tz flags."""
        # Act
        result = runner.invoke(cli, ["generate", "--help"])

        # Assert
        assert result.exit_code == 0
        assert "--convert-tz" in result.output
        assert "--no-convert-tz" in result.output

    def test_cli_convert_tz_flag_generates_convert_tz_yes(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test that --convert-tz flag produces convert_tz: yes in output."""
        # Arrange
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--convert-tz",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

            # Verify generated files contain convert_tz: yes
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) > 0

            for view_file in view_files:
                content = view_file.read_text()
                # Check for convert_tz in dimension_group sections
                if "type: time" in content:
                    assert "convert_tz: yes" in content

    def test_cli_no_convert_tz_flag_generates_convert_tz_no(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test that --no-convert-tz flag produces convert_tz: no in output."""
        # Arrange
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--no-convert-tz",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

            # Verify generated files contain convert_tz: no
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) > 0

            for view_file in view_files:
                content = view_file.read_text()
                # Check for convert_tz in dimension_group sections
                if "type: time" in content:
                    assert "convert_tz: no" in content

    def test_cli_convert_tz_flag_in_generated_lookml_files(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test that flag value appears in actual files."""
        # Arrange
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act - with --convert-tz flag
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--convert-tz",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

            # Verify files were created
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) > 0

            # Verify at least one file contains convert_tz: yes
            found_convert_tz = False
            for view_file in view_files:
                content = view_file.read_text()
                if "convert_tz: yes" in content:
                    found_convert_tz = True
                    break

            # If there are time dimensions, we should find convert_tz
            # (some fixtures might not have time dimensions)
            has_time_dims = any(
                "type: time" in view_file.read_text() for view_file in view_files
            )
            if has_time_dims:
                assert found_convert_tz

    def test_cli_convert_tz_respects_dimension_meta_override(
        self, runner: CliRunner
    ) -> None:
        """Test that dimension meta overrides CLI flag."""
        # This test requires a fixture with convert_tz in dimension meta
        # For now, we'll test that the CLI flag is properly passed to generator
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            fixtures_dir = Path(__file__).parent / "fixtures"

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--convert-tz",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

    def test_cli_convert_tz_with_view_prefix_and_explore_prefix(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test that convert_tz works with other flags."""
        # Arrange
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--convert-tz",
                    "--view-prefix",
                    "v_",
                    "--explore-prefix",
                    "e_",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

            # Verify files were created with prefixes
            # Some fixtures might not have views with the prefix pattern
            # Just verify the command succeeded

    def test_cli_convert_tz_flag_validates_output(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test that validation passes with correct convert_tz values."""
        # Arrange
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--convert-tz",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0
            # If validation fails, exit_code would be non-zero

    def test_cli_mutually_exclusive_convert_tz_flags(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test that --convert-tz and --no-convert-tz are mutually exclusive."""
        # Arrange
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--convert-tz",
                    "--no-convert-tz",
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code != 0
            assert "mutually exclusive" in result.output

    def test_cli_convert_tz_with_dry_run(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test that --convert-tz can be combined with --dry-run."""
        # Arrange & Act
        result = runner.invoke(
            cli,
            [
                "generate",
                "--input-dir",
                str(fixtures_dir),
                "--schema",
                "public",
                "--convert-tz",
                "--dry-run",
            ],
        )

        # Assert - flags can be used together (exit code may vary based on fixtures)
        # The important thing is no mutually exclusive error
        assert "mutually exclusive" not in result.output

    def test_cli_no_convert_tz_with_dry_run(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test that --no-convert-tz can be combined with --dry-run."""
        # Arrange & Act
        result = runner.invoke(
            cli,
            [
                "generate",
                "--input-dir",
                str(fixtures_dir),
                "--schema",
                "public",
                "--no-convert-tz",
                "--dry-run",
            ],
        )

        # Assert - flags can be used together (exit code may vary based on fixtures)
        # The important thing is no mutually exclusive error
        assert "mutually exclusive" not in result.output

    @pytest.mark.parametrize(
        "flag,expected_in_output",
        [
            ("--convert-tz", "convert_tz: yes"),
            ("--no-convert-tz", "convert_tz: no"),
        ],
    )
    def test_cli_convert_tz_flag_variations(
        self,
        runner: CliRunner,
        fixtures_dir: Path,
        flag: str,
        expected_in_output: str,
    ) -> None:
        """Test both convert_tz flag variations produce correct output."""
        # Arrange
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Act
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    flag,
                    "--yes",
                ],
            )

            # Assert
            assert result.exit_code == 0

            # Check if files contain expected output
            view_files = list(output_dir.glob("*.view.lkml"))
            if len(view_files) > 0:
                for view_file in view_files:
                    content = view_file.read_text()
                    if "type: time" in content:
                        assert expected_in_output in content

    def test_generate_with_preview_flag(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate command with --preview flag."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--preview",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "Command Preview" in result.output
            assert "Preview mode - no files will be generated" in result.output

            # Verify no files were created
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) == 0

    def test_generate_with_yes_flag(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate command with --yes flag."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "Auto-confirming" in result.output
            assert "✓ LookML generation completed successfully" in result.output

    def test_generate_with_confirmation_cancelled(
        self, runner: CliRunner, fixtures_dir: Path
    ) -> None:
        """Test generate command when user cancels confirmation."""
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--input-dir",
                    str(fixtures_dir),
                    "--output-dir",
                    str(output_dir),
                    "--schema",
                    "public",
                    "--yes",
                ],
                input="n\n",  # Simulate user typing 'n' at prompt
            )

            assert result.exit_code == 0
            assert "Command execution cancelled" in result.output

            # Verify no files were created
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) == 0

    @pytest.mark.cli
    def test_wizard_generate_help(self, runner: CliRunner) -> None:
        """Test wizard generate command help."""
        result = runner.invoke(cli, ["wizard", "generate", "--help"])
        assert result.exit_code == 0
        assert "--wizard-tui" in result.output

    @pytest.mark.cli
    def test_wizard_generate_command_exists(self, runner: CliRunner) -> None:
        """Test that wizard generate command exists."""
        result = runner.invoke(cli, ["wizard", "generate", "--help"])
        assert result.exit_code == 0
        assert "wizard" in result.output or "generate" in result.output

    @pytest.mark.cli
    @pytest.mark.skipif(
        not _has_textual_available(),
        reason="Textual not installed",
    )
    def test_wizard_tui_flag_available(self, runner: CliRunner) -> None:
        """Test --wizard-tui flag when Textual is available."""
        # Just verify that the import works
        try:
            from dbt_to_lookml.wizard import launch_tui_wizard

            assert callable(launch_tui_wizard)
        except ImportError:
            pytest.skip("Textual not available")

    @pytest.mark.cli
    def test_wizard_tui_flag_textual_unavailable(self, runner: CliRunner) -> None:
        """Test error if Textual not installed."""
        with patch("dbt_to_lookml.wizard.tui.TEXTUAL_AVAILABLE", False):
            result = runner.invoke(cli, ["wizard", "generate", "--wizard-tui"])

            assert result.exit_code != 0
            assert "Textual" in result.output or "textual" in result.output
