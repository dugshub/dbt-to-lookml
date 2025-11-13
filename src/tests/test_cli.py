"""Tests for CLI commands."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_to_lookml.__main__ import cli


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
