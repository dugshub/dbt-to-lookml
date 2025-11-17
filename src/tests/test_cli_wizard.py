"""CLI tests for wizard command group."""

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
