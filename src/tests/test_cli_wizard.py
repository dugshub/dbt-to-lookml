"""CLI tests for wizard command group."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dbt_to_lookml.__main__ import cli


class TestWizardCLI:
    """Test suite for wizard CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a Click test runner."""
        return CliRunner()

    def test_wizard_group_help(self, runner: CliRunner) -> None:
        """Test wizard command group help text."""
        result = runner.invoke(cli, ["wizard", "--help"])

        assert result.exit_code == 0
        assert "Interactive wizard" in result.output
        assert "test" in result.output

    def test_wizard_test_command_prompt_mode(self, runner: CliRunner) -> None:
        """Test wizard test command in prompt mode."""
        result = runner.invoke(cli, ["wizard", "test", "--mode", "prompt"])

        assert result.exit_code == 0
        assert "Wizard infrastructure working" in result.output
        assert "Mode: prompt" in result.output

    def test_wizard_test_command_tui_mode(self, runner: CliRunner) -> None:
        """Test wizard test command in TUI mode."""
        result = runner.invoke(cli, ["wizard", "test", "--mode", "tui"])

        assert result.exit_code == 0
        # Should either work (if Textual installed) or fall back to prompt
        assert "Wizard infrastructure working" in result.output

    def test_wizard_test_default_mode(self, runner: CliRunner) -> None:
        """Test wizard test command with default mode."""
        result = runner.invoke(cli, ["wizard", "test"])

        assert result.exit_code == 0
        assert "Mode: prompt" in result.output  # Default is prompt


class TestWizardGenerateCommand:
    """Test suite for wizard generate command."""

    def test_wizard_generate_command_exists(self) -> None:
        """Test that wizard generate command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["wizard", "generate", "--help"])

        assert result.exit_code == 0
        assert "Interactive wizard" in result.output
        assert "--execute" in result.output

    def test_wizard_generate_command_cancelled(self) -> None:
        """Test wizard generate command when user cancels."""
        runner = CliRunner()

        # Mock the run_generate_wizard to simulate cancellation
        with patch(
            "dbt_to_lookml.wizard.generate_wizard.run_generate_wizard"
        ) as mock_wizard:
            mock_wizard.return_value = None

            result = runner.invoke(cli, ["wizard", "generate"])

            assert result.exit_code == 0

    @patch("dbt_to_lookml.wizard.detection.ProjectDetector")
    def test_wizard_generate_with_mocked_inputs(
        self,
        mock_detector_class: MagicMock,
    ) -> None:
        """Test wizard generate command help and existence."""
        runner = CliRunner()

        # Mock detector to return None (no detection)
        mock_detector = MagicMock()
        mock_detector.detect.return_value.input_dir = None
        mock_detector.detect.return_value.output_dir = None
        mock_detector.detect.return_value.schema_name = None
        mock_detector_class.return_value = mock_detector

        # Just test that the command exists and responds with help info
        result = runner.invoke(cli, ["wizard", "generate", "--help"])

        assert result.exit_code == 0
        assert "Interactive wizard" in result.output
