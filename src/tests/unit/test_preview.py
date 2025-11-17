"""Tests for preview and confirmation utilities."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from dbt_to_lookml.preview import (
    CommandPreview,
    PreviewData,
    count_yaml_files,
    estimate_output_files,
    format_command_parts,
    show_preview_and_confirm,
)


class TestCountYamlFiles:
    """Tests for count_yaml_files function."""

    def test_count_yml_files(self, tmp_path: Path) -> None:
        """Test counting .yml files."""
        (tmp_path / "model1.yml").touch()
        (tmp_path / "model2.yml").touch()
        (tmp_path / "readme.txt").touch()

        count = count_yaml_files(tmp_path)
        assert count == 2

    def test_count_yaml_files(self, tmp_path: Path) -> None:
        """Test counting .yaml files."""
        (tmp_path / "model1.yaml").touch()
        (tmp_path / "model2.yaml").touch()

        count = count_yaml_files(tmp_path)
        assert count == 2

    def test_count_mixed_extensions(self, tmp_path: Path) -> None:
        """Test counting both .yml and .yaml files."""
        (tmp_path / "model1.yml").touch()
        (tmp_path / "model2.yaml").touch()
        (tmp_path / "model3.yml").touch()

        count = count_yaml_files(tmp_path)
        assert count == 3

    def test_count_empty_directory(self, tmp_path: Path) -> None:
        """Test counting in empty directory."""
        count = count_yaml_files(tmp_path)
        assert count == 0


class TestEstimateOutputFiles:
    """Tests for estimate_output_files function."""

    def test_estimate_single_input(self) -> None:
        """Test estimation with single input file."""
        views, explores, models = estimate_output_files(1)
        assert views == 1
        assert explores == 1
        assert models == 1

    def test_estimate_multiple_inputs(self) -> None:
        """Test estimation with multiple input files."""
        views, explores, models = estimate_output_files(5)
        assert views == 5
        assert explores == 1
        assert models == 1

    def test_estimate_zero_inputs(self) -> None:
        """Test estimation with zero input files."""
        views, explores, models = estimate_output_files(0)
        assert views == 0
        assert explores == 1
        assert models == 1


class TestFormatCommandParts:
    """Tests for format_command_parts function."""

    def test_minimal_command(self) -> None:
        """Test formatting minimal command with required args only."""
        parts = format_command_parts(
            "dbt-to-lookml generate",
            Path("input/"),
            Path("output/"),
            "public",
        )

        assert "dbt-to-lookml generate" in parts
        command = " ".join(parts)
        assert "-i input" in command
        assert "-o output" in command
        assert "-s public" in command

    def test_command_with_prefixes(self) -> None:
        """Test formatting command with view/explore prefixes."""
        parts = format_command_parts(
            "dbt-to-lookml generate",
            Path("input/"),
            Path("output/"),
            "public",
            view_prefix="v_",
            explore_prefix="e_",
        )

        command = " ".join(parts)
        assert "--view-prefix v_" in command
        assert "--explore-prefix e_" in command

    def test_command_with_timezone_flags(self) -> None:
        """Test formatting command with timezone conversion flags."""
        # Test --convert-tz
        parts = format_command_parts(
            "dbt-to-lookml generate",
            Path("input/"),
            Path("output/"),
            "public",
            convert_tz=True,
        )
        assert "--convert-tz" in parts

        # Test --no-convert-tz
        parts = format_command_parts(
            "dbt-to-lookml generate",
            Path("input/"),
            Path("output/"),
            "public",
            convert_tz=False,
        )
        assert "--no-convert-tz" in parts

    def test_command_with_boolean_flags(self) -> None:
        """Test formatting command with boolean flags."""
        parts = format_command_parts(
            "dbt-to-lookml generate",
            Path("input/"),
            Path("output/"),
            "public",
            dry_run=True,
            no_validation=True,
            show_summary=True,
        )

        command = " ".join(parts)
        assert "--dry-run" in command
        assert "--no-validation" in command
        assert "--show-summary" in command


class TestPreviewData:
    """Tests for PreviewData dataclass."""

    def test_dataclass_initialization(self) -> None:
        """Test PreviewData initialization."""
        preview_data = PreviewData(
            input_dir=Path("input/"),
            output_dir=Path("output/"),
            schema="public",
            input_file_count=5,
            estimated_views=5,
            estimated_explores=1,
            estimated_models=1,
            command_parts=["dbt-to-lookml generate"],
            additional_config={},
        )

        assert preview_data.input_file_count == 5
        assert preview_data.schema == "public"
        assert preview_data.estimated_views == 5
        assert preview_data.estimated_explores == 1
        assert preview_data.estimated_models == 1


class TestCommandPreview:
    """Tests for CommandPreview class."""

    @pytest.fixture
    def sample_preview_data(self) -> PreviewData:
        """Create sample preview data for testing."""
        return PreviewData(
            input_dir=Path("semantic_models/"),
            output_dir=Path("build/lookml/"),
            schema="production_analytics",
            input_file_count=5,
            estimated_views=5,
            estimated_explores=1,
            estimated_models=1,
            command_parts=[
                "dbt-to-lookml generate",
                "-i semantic_models/",
                "-o build/lookml/",
                "-s production_analytics",
            ],
            additional_config={"View prefix": "stg_"},
        )

    def test_preview_initialization(self) -> None:
        """Test CommandPreview initialization."""
        preview = CommandPreview()
        assert preview.console is not None

    def test_preview_with_custom_console(self) -> None:
        """Test CommandPreview with custom console."""
        console = Console()
        preview = CommandPreview(console=console)
        assert preview.console is console

    def test_render_preview_panel(self, sample_preview_data: PreviewData) -> None:
        """Test rendering preview panel."""
        preview = CommandPreview()
        panel = preview.render_preview_panel(sample_preview_data)

        assert panel is not None
        assert "Command Preview" in panel.title

    def test_render_command_syntax(self, sample_preview_data: PreviewData) -> None:
        """Test rendering command with syntax highlighting."""
        preview = CommandPreview()
        syntax = preview.render_command_syntax(sample_preview_data.command_parts)

        assert syntax is not None
        # Verify it's a Syntax object
        assert hasattr(syntax, 'code')

    def test_render_preview_panel_with_config(self) -> None:
        """Test preview panel includes additional config."""
        preview_data = PreviewData(
            input_dir=Path("input/"),
            output_dir=Path("output/"),
            schema="public",
            input_file_count=3,
            estimated_views=3,
            estimated_explores=1,
            estimated_models=1,
            command_parts=["dbt-to-lookml generate"],
            additional_config={"View prefix": "v_", "Connection": "redshift"},
        )

        preview = CommandPreview()
        panel = preview.render_preview_panel(preview_data)

        # Panel should be created successfully
        assert panel is not None


class TestShowPreviewAndConfirm:
    """Tests for show_preview_and_confirm function."""

    @pytest.fixture
    def sample_preview_data(self) -> PreviewData:
        """Create sample preview data."""
        return PreviewData(
            input_dir=Path("input/"),
            output_dir=Path("output/"),
            schema="public",
            input_file_count=3,
            estimated_views=3,
            estimated_explores=1,
            estimated_models=1,
            command_parts=["dbt-to-lookml generate", "-i input/", "-o output/"],
            additional_config={},
        )

    @patch("dbt_to_lookml.preview.console.input")
    def test_confirm_yes(
        self, mock_input: MagicMock, sample_preview_data: PreviewData
    ) -> None:
        """Test confirmation with 'yes' response."""
        mock_input.return_value = "y"

        result = show_preview_and_confirm(sample_preview_data, auto_confirm=False)
        assert result is True

    @patch("dbt_to_lookml.preview.console.input")
    def test_confirm_no(
        self, mock_input: MagicMock, sample_preview_data: PreviewData
    ) -> None:
        """Test confirmation with 'no' response."""
        mock_input.return_value = "n"

        result = show_preview_and_confirm(sample_preview_data, auto_confirm=False)
        assert result is False

    @patch("dbt_to_lookml.preview.console.input")
    def test_confirm_empty_defaults_to_no(
        self, mock_input: MagicMock, sample_preview_data: PreviewData
    ) -> None:
        """Test that empty response defaults to No for safety."""
        mock_input.return_value = ""

        result = show_preview_and_confirm(sample_preview_data, auto_confirm=False)
        assert result is False

    @patch("dbt_to_lookml.preview.console.input")
    def test_confirm_yes_full_word(
        self, mock_input: MagicMock, sample_preview_data: PreviewData
    ) -> None:
        """Test confirmation with full 'yes' word."""
        mock_input.return_value = "yes"

        result = show_preview_and_confirm(sample_preview_data, auto_confirm=False)
        assert result is True

    def test_auto_confirm_bypasses_prompt(
        self, sample_preview_data: PreviewData
    ) -> None:
        """Test that auto_confirm=True bypasses prompt."""
        result = show_preview_and_confirm(sample_preview_data, auto_confirm=True)
        assert result is True
