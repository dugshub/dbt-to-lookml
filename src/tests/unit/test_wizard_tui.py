"""Unit tests for wizard TUI widgets."""

import pytest

# Skip all tests if Textual not available
pytest.importorskip("textual")

from dbt_to_lookml.wizard.tui_widgets import (
    FormSection,
    PreviewPanel,
    ValidatedInput,
)


class TestValidatedInput:
    """Test ValidatedInput widget."""

    @pytest.mark.unit
    def test_required_field_validation(self) -> None:
        """Test required field validation."""
        input_widget = ValidatedInput(
            placeholder="test",
            required=True,
        )

        # Empty value should fail
        error = input_widget.validate_value("")
        assert error == "This field is required"

        # Non-empty value should pass
        error = input_widget.validate_value("value")
        assert error is None

    @pytest.mark.unit
    def test_optional_field_validation(self) -> None:
        """Test optional field allows empty values."""
        input_widget = ValidatedInput(
            placeholder="test",
            required=False,
        )

        # Empty value should pass for optional field
        error = input_widget.validate_value("")
        assert error is None

        # Non-empty value should also pass
        error = input_widget.validate_value("value")
        assert error is None

    @pytest.mark.unit
    def test_custom_validator(self) -> None:
        """Test custom validation function."""

        def path_validator(value: str) -> str | None:
            if not value.endswith("/"):
                return "Path must end with /"
            return None

        input_widget = ValidatedInput(
            validator=path_validator,
        )

        # Invalid path
        error = input_widget.validate_value("path")
        assert error == "Path must end with /"

        # Valid path
        error = input_widget.validate_value("path/")
        assert error is None

    @pytest.mark.unit
    def test_validation_error_styling(self) -> None:
        """Test error status in validation."""
        input_widget = ValidatedInput(required=True)

        # Simulate validation error
        input_widget.validation_error = "This field is required"
        assert not input_widget.validate_value_override()

        # Clear validation error
        input_widget.validation_error = None
        assert input_widget.validate_value_override()

    @pytest.mark.unit
    def test_custom_validator_with_required(self) -> None:
        """Test custom validator combined with required check."""

        def schema_validator(value: str) -> str | None:
            if value and not value.isalnum():
                return "Schema must be alphanumeric"
            return None

        input_widget = ValidatedInput(
            validator=schema_validator,
            required=True,
        )

        # Empty value fails (required)
        error = input_widget.validate_value("")
        assert error == "This field is required"

        # Invalid format fails (custom validator)
        error = input_widget.validate_value("my-schema")
        assert error == "Schema must be alphanumeric"

        # Valid value passes
        error = input_widget.validate_value("myschema")
        assert error is None


class TestFormSection:
    """Test FormSection widget."""

    @pytest.mark.unit
    def test_section_with_title(self) -> None:
        """Test FormSection renders title."""
        section = FormSection(
            title="Test Section",
            description="Test description",
        )

        assert section.title == "Test Section"
        assert section.description == "Test description"

    @pytest.mark.unit
    def test_section_without_description(self) -> None:
        """Test FormSection without description."""
        section = FormSection(title="Test Section")

        assert section.title == "Test Section"
        assert section.description is None

    @pytest.mark.unit
    def test_section_css_defined(self) -> None:
        """Test FormSection has CSS defined."""
        assert FormSection.DEFAULT_CSS is not None
        assert "FormSection" in FormSection.DEFAULT_CSS
        assert "section-title" in FormSection.DEFAULT_CSS


class TestPreviewPanel:
    """Test PreviewPanel widget."""

    @pytest.mark.unit
    def test_command_building_minimal(self) -> None:
        """Test minimal command string generation."""
        panel = PreviewPanel()

        form_data = {
            "input_dir": "semantic_models/",
            "output_dir": "build/lookml/",
            "schema": "prod",
        }

        cmd = panel._build_command(form_data)

        assert "dbt-to-lookml generate" in cmd
        assert "-i semantic_models/" in cmd
        assert "-o build/lookml/" in cmd
        assert "-s prod" in cmd

    @pytest.mark.unit
    def test_command_building_full(self) -> None:
        """Test full command string generation."""
        panel = PreviewPanel()

        form_data = {
            "input_dir": "semantic_models/",
            "output_dir": "build/lookml/",
            "schema": "prod",
            "view_prefix": "v_",
            "explore_prefix": "e_",
            "connection": "redshift_prod",
            "model_name": "my_model",
            "dry_run": True,
            "skip_validation": True,
            "skip_formatting": False,
            "show_summary": True,
            "convert_tz": "yes",
        }

        cmd = panel._build_command(form_data)

        assert "dbt-to-lookml generate" in cmd
        assert "-i semantic_models/" in cmd
        assert "-o build/lookml/" in cmd
        assert "-s prod" in cmd
        assert "--view-prefix v_" in cmd
        assert "--explore-prefix e_" in cmd
        assert "-c redshift_prod" in cmd
        assert "-m my_model" in cmd
        assert "--dry-run" in cmd
        assert "--no-validation" in cmd
        assert "--show-summary" in cmd
        assert "--convert-tz" in cmd

    @pytest.mark.unit
    def test_command_building_convert_tz_no(self) -> None:
        """Test command with convert_tz: no."""
        panel = PreviewPanel()

        form_data = {
            "input_dir": "semantic_models/",
            "output_dir": "build/lookml/",
            "schema": "prod",
            "convert_tz": "no",
        }

        cmd = panel._build_command(form_data)

        assert "--no-convert-tz" in cmd
        assert "--convert-tz" not in cmd or "--convert-tz" in "--no-convert-tz"

    @pytest.mark.unit
    def test_command_building_no_optional_fields(self) -> None:
        """Test command excludes empty optional fields."""
        panel = PreviewPanel()

        form_data = {
            "input_dir": "semantic_models/",
            "output_dir": "build/lookml/",
            "schema": "prod",
            "view_prefix": "",
            "explore_prefix": "",
            "connection": "",
            "model_name": "",
            "dry_run": False,
            "convert_tz": "unset",
        }

        cmd = panel._build_command(form_data)

        assert "dbt-to-lookml generate" in cmd
        assert "-i semantic_models/" in cmd
        assert "--view-prefix" not in cmd
        assert "--explore-prefix" not in cmd
        assert "--convert-tz" not in cmd
        assert "--no-convert-tz" not in cmd

    @pytest.mark.unit
    def test_output_estimation_nonexistent(self) -> None:
        """Test output estimation with nonexistent directory."""
        panel = PreviewPanel()

        output = panel._estimate_output("/nonexistent/path/that/does/not/exist")
        # Path that doesn't exist should fail or estimate 0
        assert "Unable to estimate" in output or "0 view files" in output

    @pytest.mark.unit
    def test_output_estimation_empty_directory(self, tmp_path):  # type: ignore
        """Test output estimation with empty directory."""
        panel = PreviewPanel()

        output = panel._estimate_output(str(tmp_path))
        assert "• 0 view files" in output

    @pytest.mark.unit
    def test_output_estimation_with_files(self, tmp_path):  # type: ignore
        """Test output estimation with YAML files."""
        # Create test YAML files
        (tmp_path / "model1.yml").write_text("test")
        (tmp_path / "model2.yaml").write_text("test")

        panel = PreviewPanel()
        output = panel._estimate_output(str(tmp_path))

        assert "• 2 view files" in output
        assert "• 1 explore file" in output
        assert "• 1 model file" in output

    @pytest.mark.unit
    def test_preview_panel_css_defined(self) -> None:
        """Test PreviewPanel has CSS defined."""
        assert PreviewPanel.DEFAULT_CSS is not None
        assert "PreviewPanel" in PreviewPanel.DEFAULT_CSS
        assert "panel-title" in PreviewPanel.DEFAULT_CSS
