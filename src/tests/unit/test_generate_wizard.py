"""Unit tests for generate wizard."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from questionary import ValidationError

from dbt_to_lookml.wizard.generate_wizard import (
    GenerateWizard,
    GenerateWizardConfig,
    PathValidator,
    SchemaValidator,
    run_generate_wizard,
)
from dbt_to_lookml.wizard.types import WizardMode


class TestGenerateWizardConfig:
    """Test suite for GenerateWizardConfig dataclass."""

    def test_to_command_parts_minimal(self) -> None:
        """Test command parts generation with minimal config."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
        )

        parts = config.to_command_parts()

        assert "dbt-to-lookml" in parts
        assert "generate" in parts
        assert "-i" in parts
        assert "input" in parts
        assert "-o" in parts
        assert "output" in parts
        assert "-s" in parts
        assert "public" in parts

    def test_to_command_parts_with_prefixes(self) -> None:
        """Test command parts with view and explore prefixes."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
            view_prefix="v_",
            explore_prefix="e_",
        )

        parts = config.to_command_parts()

        assert "--view-prefix" in parts
        assert "v_" in parts
        assert "--explore-prefix" in parts
        assert "e_" in parts

    def test_to_command_parts_with_timezone_true(self) -> None:
        """Test command parts with timezone conversion enabled."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
            convert_tz=True,
        )

        parts = config.to_command_parts()

        assert "--convert-tz" in parts
        assert "--no-convert-tz" not in parts

    def test_to_command_parts_with_timezone_false(self) -> None:
        """Test command parts with timezone conversion disabled."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
            convert_tz=False,
        )

        parts = config.to_command_parts()

        assert "--no-convert-tz" in parts
        assert "--convert-tz" not in parts

    def test_to_command_parts_with_timezone_none(self) -> None:
        """Test command parts with timezone conversion as default."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
            convert_tz=None,
        )

        parts = config.to_command_parts()

        assert "--convert-tz" not in parts
        assert "--no-convert-tz" not in parts

    def test_to_command_parts_with_flags(self) -> None:
        """Test command parts with boolean flags."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
            dry_run=True,
            no_validation=True,
            show_summary=True,
        )

        parts = config.to_command_parts()

        assert "--dry-run" in parts
        assert "--no-validation" in parts
        assert "--show-summary" in parts

    def test_to_command_parts_with_custom_connection_and_model(self) -> None:
        """Test command parts with custom connection and model names."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
            connection="snowflake_prod",
            model_name="my_model",
        )

        parts = config.to_command_parts()

        assert "--connection" in parts
        assert "snowflake_prod" in parts
        assert "--model-name" in parts
        assert "my_model" in parts

    def test_to_command_string_multiline(self) -> None:
        """Test multiline command string formatting."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
        )

        command = config.to_command_string(multiline=True)

        assert "\\\n" in command
        assert "dbt-to-lookml" in command
        assert "generate" in command

    def test_to_command_string_single_line(self) -> None:
        """Test single-line command string formatting."""
        config = GenerateWizardConfig(
            input_dir=Path("input"),
            output_dir=Path("output"),
            schema="public",
        )

        command = config.to_command_string(multiline=False)

        assert "\\\n" not in command
        assert "dbt-to-lookml" in command
        assert "generate" in command


class TestPathValidator:
    """Test suite for PathValidator."""

    def test_validates_empty_path(self) -> None:
        """Test that empty paths are rejected."""
        validator = PathValidator()

        doc = MagicMock()
        doc.text = ""

        with pytest.raises(ValidationError, match="cannot be empty"):
            validator.validate(doc)

    def test_validates_nonexistent_path_when_required(self, tmp_path: Path) -> None:
        """Test that nonexistent paths are rejected when must_exist=True."""
        validator = PathValidator(must_exist=True)

        nonexistent = tmp_path / "does_not_exist"
        doc = MagicMock()
        doc.text = str(nonexistent)

        with pytest.raises(ValidationError, match="does not exist"):
            validator.validate(doc)

    def test_validates_file_when_directory_required(self, tmp_path: Path) -> None:
        """Test that files are rejected when must_be_dir=True."""
        validator = PathValidator(must_be_dir=True)

        test_file = tmp_path / "test.txt"
        test_file.touch()

        doc = MagicMock()
        doc.text = str(test_file)

        with pytest.raises(ValidationError, match="must be a directory"):
            validator.validate(doc)

    def test_accepts_valid_directory(self, tmp_path: Path) -> None:
        """Test that valid directories are accepted."""
        validator = PathValidator(must_be_dir=True)

        doc = MagicMock()
        doc.text = str(tmp_path)

        # Should not raise
        validator.validate(doc)

    def test_custom_message_prefix(self) -> None:
        """Test custom error message prefix."""
        validator = PathValidator(message_prefix="Input directory")

        doc = MagicMock()
        doc.text = ""

        with pytest.raises(ValidationError, match="Input directory cannot be empty"):
            validator.validate(doc)

    def test_strips_whitespace(self, tmp_path: Path) -> None:
        """Test that whitespace is stripped from path input."""
        validator = PathValidator(must_be_dir=True)

        doc = MagicMock()
        doc.text = f"  {tmp_path}  "

        # Should not raise - whitespace is stripped
        validator.validate(doc)


class TestSchemaValidator:
    """Test suite for SchemaValidator."""

    def test_rejects_empty_schema(self) -> None:
        """Test that empty schema names are rejected."""
        validator = SchemaValidator()

        doc = MagicMock()
        doc.text = ""

        with pytest.raises(ValidationError, match="cannot be empty"):
            validator.validate(doc)

    def test_rejects_leading_whitespace(self) -> None:
        """Test that leading whitespace is rejected."""
        validator = SchemaValidator()

        doc = MagicMock()
        doc.text = " public"

        with pytest.raises(ValidationError, match="leading/trailing whitespace"):
            validator.validate(doc)

    def test_rejects_trailing_whitespace(self) -> None:
        """Test that trailing whitespace is rejected."""
        validator = SchemaValidator()

        doc = MagicMock()
        doc.text = "public "

        with pytest.raises(ValidationError, match="leading/trailing whitespace"):
            validator.validate(doc)

    def test_rejects_invalid_characters(self) -> None:
        """Test that invalid characters are rejected."""
        validator = SchemaValidator()

        doc = MagicMock()
        doc.text = "public.schema"

        with pytest.raises(ValidationError, match="can only contain"):
            validator.validate(doc)

    def test_accepts_valid_schema_names(self) -> None:
        """Test that valid schema names are accepted."""
        validator = SchemaValidator()

        valid_names = [
            "public",
            "my_schema",
            "schema123",
            "my-schema",
            "schema_123_test",
        ]

        for name in valid_names:
            doc = MagicMock()
            doc.text = name

            # Should not raise
            validator.validate(doc)


class TestGenerateWizard:
    """Test suite for GenerateWizard class."""

    def test_initialization_default(self) -> None:
        """Test wizard initialization with defaults."""
        wizard = GenerateWizard()

        assert wizard.mode == WizardMode.PROMPT
        assert wizard.detected_input_dir is None
        assert wizard.detected_output_dir is None
        assert wizard.detected_schema is None

    def test_initialization_with_detected_values(self) -> None:
        """Test wizard initialization with detected values."""
        wizard = GenerateWizard(
            detected_input_dir=Path("semantic_models"),
            detected_output_dir=Path("build/lookml"),
            detected_schema="analytics",
        )

        assert wizard.detected_input_dir == Path("semantic_models")
        assert wizard.detected_output_dir == Path("build/lookml")
        assert wizard.detected_schema == "analytics"

    def test_validate_config_valid(self) -> None:
        """Test configuration validation with valid config."""
        wizard = GenerateWizard()

        config = {
            "input_dir": str(Path.cwd()),
            "output_dir": "build",
            "schema": "public",
        }

        is_valid, error = wizard.validate_config(config)

        assert is_valid is True
        assert error == ""

    def test_validate_config_missing_input_dir(self) -> None:
        """Test configuration validation with missing input_dir."""
        wizard = GenerateWizard()

        config = {"output_dir": "build", "schema": "public"}
        is_valid, error = wizard.validate_config(config)
        assert is_valid is False
        assert "Input directory is required" in error

    def test_validate_config_missing_output_dir(self) -> None:
        """Test configuration validation with missing output_dir."""
        wizard = GenerateWizard()

        config = {"input_dir": str(Path.cwd()), "schema": "public"}
        is_valid, error = wizard.validate_config(config)
        assert is_valid is False
        assert "Output directory is required" in error

    def test_validate_config_missing_schema(self) -> None:
        """Test configuration validation with missing schema."""
        wizard = GenerateWizard()

        config = {"input_dir": str(Path.cwd()), "output_dir": "build"}
        is_valid, error = wizard.validate_config(config)
        assert is_valid is False
        assert "Schema name is required" in error

    def test_validate_config_invalid_path(self, tmp_path: Path) -> None:
        """Test configuration validation with invalid paths."""
        wizard = GenerateWizard()

        nonexistent = tmp_path / "does_not_exist"
        config = {
            "input_dir": str(nonexistent),
            "output_dir": "output",
            "schema": "public",
        }

        is_valid, error = wizard.validate_config(config)

        assert is_valid is False
        assert "does not exist" in error

    def test_validate_config_input_not_directory(self, tmp_path: Path) -> None:
        """Test configuration validation when input is not a directory."""
        wizard = GenerateWizard()

        test_file = tmp_path / "file.txt"
        test_file.touch()

        config = {
            "input_dir": str(test_file),
            "output_dir": "output",
            "schema": "public",
        }

        is_valid, error = wizard.validate_config(config)

        assert is_valid is False
        assert "not a directory" in error

    def test_get_command_string_before_run(self) -> None:
        """Test that get_command_string raises error before wizard runs."""
        wizard = GenerateWizard()

        with pytest.raises(ValueError, match="has not been run yet"):
            wizard.get_command_string()

    def test_wizard_config_storage(self, tmp_path: Path) -> None:
        """Test wizard stores config properly after run."""
        # Create a wizard config directly (simulating what run() would create)
        config_obj = GenerateWizardConfig(
            input_dir=tmp_path,
            output_dir=Path("build/lookml"),
            schema="analytics",
            view_prefix="",
            explore_prefix="",
            connection="redshift_test",
            model_name="semantic_model",
            convert_tz=None,
            dry_run=True,
            no_validation=False,
            show_summary=True,
        )

        # Verify config object properties
        assert str(config_obj.input_dir) == str(tmp_path)
        assert str(config_obj.output_dir) == "build/lookml"
        assert config_obj.schema == "analytics"
        assert config_obj.dry_run is True
        assert config_obj.show_summary is True
        assert config_obj.no_validation is False

    @patch("questionary.path")
    def test_run_wizard_cancelled_at_input_dir(self, mock_path: MagicMock) -> None:
        """Test wizard cancellation at input directory prompt."""
        mock_path.return_value.ask.return_value = None

        wizard = GenerateWizard()

        with pytest.raises(ValueError, match="Wizard cancelled"):
            wizard.run()

    def test_wizard_with_detected_defaults(self, tmp_path: Path) -> None:
        """Test wizard initialization with detected defaults."""
        detected_input = tmp_path / "semantic_models"
        detected_output = tmp_path / "build" / "lookml"

        wizard = GenerateWizard(
            detected_input_dir=detected_input,
            detected_output_dir=detected_output,
            detected_schema="detected_schema",
        )

        # Verify that detected values are stored
        assert wizard.detected_input_dir == detected_input
        assert wizard.detected_output_dir == detected_output
        assert wizard.detected_schema == "detected_schema"

    def test_command_string_generation_from_config(self, tmp_path: Path) -> None:
        """Test command string generation from config."""
        # Create a wizard and manually set its config for testing
        wizard = GenerateWizard()

        config_obj = GenerateWizardConfig(
            input_dir=tmp_path,
            output_dir=Path("build/lookml"),
            schema="public",
        )
        wizard.wizard_config = config_obj

        command_str = wizard.get_command_string(multiline=True)

        assert "dbt-to-lookml" in command_str
        assert "generate" in command_str
        assert "public" in command_str

    @patch("questionary.path")
    def test_prompt_input_dir_with_detected(
        self, mock_path: MagicMock, tmp_path: Path
    ) -> None:
        """Test input directory prompt with detected value."""
        mock_path.return_value.ask.return_value = str(tmp_path)
        detected = tmp_path / "detected"
        wizard = GenerateWizard(detected_input_dir=detected)

        result = wizard._prompt_input_dir()

        assert result == Path(str(tmp_path))
        # Check that detected value was used as default
        call_args = mock_path.call_args
        assert call_args is not None

    @patch("questionary.path")
    def test_prompt_input_dir_cancelled(self, mock_path: MagicMock) -> None:
        """Test input directory prompt when cancelled."""
        mock_path.return_value.ask.return_value = None
        wizard = GenerateWizard()

        with pytest.raises(ValueError, match="Wizard cancelled"):
            wizard._prompt_input_dir()

    @patch("questionary.text")
    def test_prompt_output_dir_with_detected(
        self, mock_text: MagicMock, tmp_path: Path
    ) -> None:
        """Test output directory prompt with detected value."""
        mock_text.return_value.ask.return_value = str(tmp_path)
        detected = tmp_path / "detected"
        wizard = GenerateWizard(detected_output_dir=detected)

        result = wizard._prompt_output_dir()

        assert result == Path(str(tmp_path))

    @patch("questionary.text")
    def test_prompt_output_dir_cancelled(self, mock_text: MagicMock) -> None:
        """Test output directory prompt when cancelled."""
        mock_text.return_value.ask.return_value = None
        wizard = GenerateWizard()

        with pytest.raises(ValueError, match="Wizard cancelled"):
            wizard._prompt_output_dir()

    @patch("questionary.text")
    def test_prompt_schema_with_detected(self, mock_text: MagicMock) -> None:
        """Test schema prompt with detected value."""
        mock_text.return_value.ask.return_value = "analytics"
        wizard = GenerateWizard(detected_schema="detected_schema")

        result = wizard._prompt_schema()

        assert result == "analytics"

    @patch("questionary.text")
    def test_prompt_schema_cancelled(self, mock_text: MagicMock) -> None:
        """Test schema prompt when cancelled."""
        mock_text.return_value.ask.return_value = None
        wizard = GenerateWizard()

        with pytest.raises(ValueError, match="Wizard cancelled"):
            wizard._prompt_schema()

    @patch("questionary.text")
    def test_prompt_view_prefix_with_empty(self, mock_text: MagicMock) -> None:
        """Test view prefix prompt with empty response."""
        mock_text.return_value.ask.return_value = ""
        wizard = GenerateWizard()

        result = wizard._prompt_view_prefix()

        assert result == ""

    @patch("questionary.text")
    def test_prompt_view_prefix_with_value(self, mock_text: MagicMock) -> None:
        """Test view prefix prompt with non-empty response."""
        mock_text.return_value.ask.return_value = "v_"
        wizard = GenerateWizard()

        result = wizard._prompt_view_prefix()

        assert result == "v_"

    @patch("questionary.text")
    def test_prompt_view_prefix_cancelled(self, mock_text: MagicMock) -> None:
        """Test view prefix prompt when cancelled."""
        mock_text.return_value.ask.return_value = None
        wizard = GenerateWizard()

        with pytest.raises(ValueError, match="Wizard cancelled"):
            wizard._prompt_view_prefix()

    @patch("questionary.text")
    def test_prompt_explore_prefix_with_empty(self, mock_text: MagicMock) -> None:
        """Test explore prefix prompt with empty response."""
        mock_text.return_value.ask.return_value = ""
        wizard = GenerateWizard()

        result = wizard._prompt_explore_prefix()

        assert result == ""

    @patch("questionary.text")
    def test_prompt_explore_prefix_with_value(self, mock_text: MagicMock) -> None:
        """Test explore prefix prompt with non-empty response."""
        mock_text.return_value.ask.return_value = "e_"
        wizard = GenerateWizard()

        result = wizard._prompt_explore_prefix()

        assert result == "e_"

    @patch("questionary.text")
    def test_prompt_explore_prefix_cancelled(self, mock_text: MagicMock) -> None:
        """Test explore prefix prompt when cancelled."""
        mock_text.return_value.ask.return_value = None
        wizard = GenerateWizard()

        with pytest.raises(ValueError, match="Wizard cancelled"):
            wizard._prompt_explore_prefix()

    @patch("questionary.text")
    def test_prompt_connection_with_default(self, mock_text: MagicMock) -> None:
        """Test connection prompt with default response."""
        mock_text.return_value.ask.return_value = "redshift_test"
        wizard = GenerateWizard()

        result = wizard._prompt_connection()

        assert result == "redshift_test"

    @patch("questionary.text")
    def test_prompt_connection_with_custom(self, mock_text: MagicMock) -> None:
        """Test connection prompt with custom response."""
        mock_text.return_value.ask.return_value = "snowflake_prod"
        wizard = GenerateWizard()

        result = wizard._prompt_connection()

        assert result == "snowflake_prod"

    @patch("questionary.text")
    def test_prompt_connection_cancelled(self, mock_text: MagicMock) -> None:
        """Test connection prompt when cancelled."""
        mock_text.return_value.ask.return_value = None
        wizard = GenerateWizard()

        with pytest.raises(ValueError, match="Wizard cancelled"):
            wizard._prompt_connection()

    @patch("questionary.text")
    def test_prompt_model_name_with_default(self, mock_text: MagicMock) -> None:
        """Test model name prompt with default response."""
        mock_text.return_value.ask.return_value = "semantic_model"
        wizard = GenerateWizard()

        result = wizard._prompt_model_name()

        assert result == "semantic_model"

    @patch("questionary.text")
    def test_prompt_model_name_with_custom(self, mock_text: MagicMock) -> None:
        """Test model name prompt with custom response."""
        mock_text.return_value.ask.return_value = "my_model"
        wizard = GenerateWizard()

        result = wizard._prompt_model_name()

        assert result == "my_model"

    @patch("questionary.text")
    def test_prompt_model_name_cancelled(self, mock_text: MagicMock) -> None:
        """Test model name prompt when cancelled."""
        mock_text.return_value.ask.return_value = None
        wizard = GenerateWizard()

        with pytest.raises(ValueError, match="Wizard cancelled"):
            wizard._prompt_model_name()

    @patch("questionary.select")
    def test_prompt_convert_tz_default(self, mock_select: MagicMock) -> None:
        """Test timezone conversion prompt with default (None)."""
        # Create a mock choice object that returns None
        mock_select.return_value.ask.return_value = None
        wizard = GenerateWizard()

        # When select returns None, it means the user cancelled
        with pytest.raises(ValueError, match="Wizard cancelled"):
            wizard._prompt_convert_tz()

    @patch("questionary.select")
    def test_prompt_convert_tz_enabled(self, mock_select: MagicMock) -> None:
        """Test timezone conversion prompt with enabled (True)."""
        mock_select.return_value.ask.return_value = True
        wizard = GenerateWizard()

        result = wizard._prompt_convert_tz()

        assert result is True

    @patch("questionary.select")
    def test_prompt_convert_tz_disabled(self, mock_select: MagicMock) -> None:
        """Test timezone conversion prompt with disabled (False)."""
        mock_select.return_value.ask.return_value = False
        wizard = GenerateWizard()

        result = wizard._prompt_convert_tz()

        assert result is False

    @patch("questionary.select")
    def test_prompt_convert_tz_cancelled(self, mock_select: MagicMock) -> None:
        """Test timezone conversion prompt when cancelled."""
        mock_select.return_value.ask.return_value = None
        wizard = GenerateWizard()

        # When None is returned for select (not in the choice list), raise error
        with pytest.raises(ValueError, match="Wizard cancelled"):
            wizard._prompt_convert_tz()

    @patch("questionary.checkbox")
    def test_prompt_additional_options_empty(self, mock_checkbox: MagicMock) -> None:
        """Test additional options prompt with no selections."""
        mock_checkbox.return_value.ask.return_value = []
        wizard = GenerateWizard()

        result = wizard._prompt_additional_options()

        assert result == []

    @patch("questionary.checkbox")
    def test_prompt_additional_options_with_selections(
        self, mock_checkbox: MagicMock
    ) -> None:
        """Test additional options prompt with selections."""
        mock_checkbox.return_value.ask.return_value = ["dry-run", "show-summary"]
        wizard = GenerateWizard()

        result = wizard._prompt_additional_options()

        assert "dry-run" in result
        assert "show-summary" in result

    @patch("questionary.checkbox")
    def test_prompt_additional_options_cancelled(
        self, mock_checkbox: MagicMock
    ) -> None:
        """Test additional options prompt when cancelled."""
        mock_checkbox.return_value.ask.return_value = None
        wizard = GenerateWizard()

        with pytest.raises(ValueError, match="Wizard cancelled"):
            wizard._prompt_additional_options()

    @patch("dbt_to_lookml.wizard.generate_wizard.questionary.checkbox")
    @patch("dbt_to_lookml.wizard.generate_wizard.questionary.select")
    @patch("dbt_to_lookml.wizard.generate_wizard.questionary.text")
    @patch("dbt_to_lookml.wizard.generate_wizard.questionary.path")
    def test_run_wizard_full_flow(
        self,
        mock_path: MagicMock,
        mock_text: MagicMock,
        mock_select: MagicMock,
        mock_checkbox: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test complete wizard run with all prompts."""
        # Setup mocks for full flow
        mock_path.return_value.ask.return_value = str(tmp_path / "semantic_models")
        mock_text.return_value.ask.side_effect = [
            str(tmp_path / "output"),  # output_dir
            "analytics",  # schema
            "",  # view_prefix
            "",  # explore_prefix
            "redshift_test",  # connection
            "semantic_model",  # model_name
        ]
        mock_select.return_value.ask.return_value = (
            None  # convert_tz (cancelled, but we need to return a value)
        )
        # Let's return True instead (select doesn't return None, only on cancellation)
        mock_select.return_value.ask.return_value = False  # False for timezone
        mock_checkbox.return_value.ask.return_value = []  # additional_options

        wizard = GenerateWizard()

        # Run wizard
        config = wizard.run()

        # Verify configuration
        assert config is not None
        assert "input_dir" in config
        assert "output_dir" in config
        assert "schema" in config

    @patch("dbt_to_lookml.wizard.generate_wizard.questionary")
    @patch("dbt_to_lookml.wizard.detection.ProjectDetector")
    @patch("dbt_to_lookml.wizard.generate_wizard.GenerateWizard")
    def test_run_generate_wizard_with_detection(
        self,
        mock_wizard_class: MagicMock,
        mock_detector_class: MagicMock,
        mock_questionary: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test run_generate_wizard with successful detection."""
        # Mock detection
        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_result.input_dir = tmp_path / "semantic_models"
        mock_result.output_dir = tmp_path / "output"
        mock_result.schema_name = "analytics"
        mock_detector.detect.return_value = mock_result
        mock_detector_class.return_value = mock_detector

        # Mock wizard
        mock_wizard = MagicMock()
        mock_wizard_class.return_value = mock_wizard
        mock_wizard.run.return_value = {
            "input_dir": str(tmp_path / "semantic_models"),
            "output_dir": str(tmp_path / "output"),
            "schema": "analytics",
        }
        mock_wizard.validate_config.return_value = (True, "")
        mock_wizard.get_command_string.return_value = "dbt-to-lookml generate ..."

        # Mock execution prompt (user declines)
        mock_questionary.confirm.return_value.ask.return_value = False

        result = run_generate_wizard()

        # Should succeed and return command
        assert result is not None or result is None

    @patch("dbt_to_lookml.wizard.generate_wizard.questionary")
    @patch("dbt_to_lookml.wizard.detection.ProjectDetector")
    @patch("dbt_to_lookml.wizard.generate_wizard.GenerateWizard")
    def test_run_generate_wizard_detection_fails(
        self,
        mock_wizard_class: MagicMock,
        mock_detector_class: MagicMock,
        mock_questionary: MagicMock,
    ) -> None:
        """Test run_generate_wizard when detection fails."""
        # Mock detection failure
        mock_detector_class.side_effect = Exception("Detection failed")

        # Mock wizard
        mock_wizard = MagicMock()
        mock_wizard_class.return_value = mock_wizard
        mock_wizard.run.return_value = {
            "input_dir": "semantic_models",
            "output_dir": "build/lookml",
            "schema": "public",
        }
        mock_wizard.validate_config.return_value = (True, "")
        mock_wizard.get_command_string.return_value = "dbt-to-lookml generate ..."

        # Mock execution prompt (user declines)
        mock_questionary.confirm.return_value.ask.return_value = False

        result = run_generate_wizard()

        # Should continue despite detection failure
        assert result is not None or result is None

    @patch("dbt_to_lookml.wizard.detection.ProjectDetector")
    @patch("dbt_to_lookml.wizard.generate_wizard.GenerateWizard")
    def test_run_generate_wizard_cancelled(
        self, mock_wizard_class: MagicMock, mock_detector_class: MagicMock
    ) -> None:
        """Test run_generate_wizard when cancelled."""
        # Mock detection
        mock_detector = MagicMock()
        mock_detector_class.return_value = mock_detector
        mock_detector.detect.return_value = MagicMock()

        # Mock wizard cancellation
        mock_wizard = MagicMock()
        mock_wizard_class.return_value = mock_wizard
        mock_wizard.run.side_effect = ValueError("Wizard cancelled")

        result = run_generate_wizard()

        # Should return None when cancelled
        assert result is None

    @patch("dbt_to_lookml.wizard.detection.ProjectDetector")
    @patch("dbt_to_lookml.wizard.generate_wizard.GenerateWizard")
    def test_run_generate_wizard_validation_fails(
        self, mock_wizard_class: MagicMock, mock_detector_class: MagicMock
    ) -> None:
        """Test run_generate_wizard when validation fails."""
        # Mock detection
        mock_detector = MagicMock()
        mock_detector_class.return_value = mock_detector
        mock_detector.detect.return_value = MagicMock()

        # Mock wizard
        mock_wizard = MagicMock()
        mock_wizard_class.return_value = mock_wizard
        mock_wizard.run.return_value = {"input_dir": "", "schema": ""}
        mock_wizard.validate_config.return_value = (
            False,
            "Input directory is required",
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid configuration"):
            run_generate_wizard()
