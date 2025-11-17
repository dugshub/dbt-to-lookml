"""Custom Textual widgets for wizard TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

try:
    from textual.app import ComposeResult
    from textual.containers import Container, Vertical
    from textual.message import Message
    from textual.widgets import Input, Static

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    ComposeResult = list  # type: ignore
    Container = object  # type: ignore
    Vertical = object  # type: ignore
    Message = object  # type: ignore
    Input = object  # type: ignore
    Static = object  # type: ignore


class FormSection(Container):
    """Container for a group of form fields with section title.

    Attributes:
        title: Section heading text
        description: Optional section description
    """

    DEFAULT_CSS = """
    FormSection {
        border: solid $border;
        margin: 1 0;
        padding: 1;
        height: auto;
        layout: vertical;
    }

    FormSection .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        height: auto;
    }

    FormSection .section-description {
        color: $text-muted;
        text-style: italic;
        margin-bottom: 1;
        height: auto;
    }
    """

    def __init__(
        self,
        title: str,
        description: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize FormSection.

        Args:
            title: Section heading
            description: Optional section description
            **kwargs: Additional Container arguments
        """
        super().__init__(**kwargs)
        self.title = title
        self.description = description

    def compose(self) -> ComposeResult:
        """Compose section with title and children."""
        yield Static(self.title, classes="section-title")
        if self.description:
            yield Static(self.description, classes="section-description")


class ValidatedInput(Input):
    """Input field with validation feedback.

    Attributes:
        validator: Callable that returns None if valid, error message if invalid
        required: Whether field is required (non-empty)
        validation_error: Current validation error message or None
    """

    DEFAULT_CSS = """
    ValidatedInput {
        border: solid $border;
    }

    ValidatedInput:focus {
        border: tall $accent;
    }

    ValidatedInput.error {
        border: tall $error;
    }

    .error-message {
        color: $error;
        text-style: bold;
        margin-top: 1;
    }
    """

    class ValidationError(Message):
        """Message sent when validation fails."""

        def __init__(self, error: str | None) -> None:
            super().__init__()
            self.error = error

    def __init__(
        self,
        placeholder: str = "",
        validator: Callable[[str], str | None] | None = None,
        required: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize ValidatedInput.

        Args:
            placeholder: Placeholder text
            validator: Validation function (returns error or None)
            required: Whether field is required
            **kwargs: Additional Input arguments
        """
        self.validator = validator
        self.required = required
        self.validation_error: str | None = None
        super().__init__(placeholder=placeholder, **kwargs)

    def validate_value(self, value: str) -> str | None:
        """Validate input value.

        Args:
            value: Current input value

        Returns:
            Error message or None if valid
        """
        # Handle None values
        if value is None:
            value = ""

        # Check if required field exists before accessing it
        required = getattr(self, "required", False)
        if required and not value.strip():
            return "This field is required"
        if self.validator:
            return self.validator(value)
        return None

    def on_input_changed(self, event: Input.Changed) -> None:
        """Validate on every keystroke and update UI.

        Args:
            event: Input change event
        """
        error = self.validate_value(event.value)
        self.validation_error = error

        if error:
            self.add_class("error")
        else:
            self.remove_class("error")

        # Notify parent of validation status
        self.post_message(self.ValidationError(error))

    def validate_value_override(self) -> bool:
        """Check if current value is valid.

        Returns:
            True if valid, False otherwise
        """
        return self.validation_error is None


class PreviewPanel(Vertical):
    """Right-side panel showing command preview and estimated output.

    Updates automatically as form values change.
    """

    DEFAULT_CSS = """
    PreviewPanel {
        width: 30%;
        min-width: 30;
        background: $panel;
        border-left: solid $primary;
        padding: 1 2;
    }

    PreviewPanel .panel-title {
        text-style: bold;
        color: $primary;
        margin: 1 0;
    }

    PreviewPanel .preview-content {
        background: $surface-darken-1;
        padding: 1;
        border: solid $border;
        margin: 1 0;
        overflow-y: auto;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize PreviewPanel."""
        super().__init__(**kwargs)
        self.command_text = Static("", id="command-preview", classes="preview-content")
        self.output_text = Static("", id="output-preview", classes="preview-content")

    def compose(self) -> ComposeResult:
        """Compose preview panel with command and output sections."""
        yield Static("Command Preview", classes="panel-title")
        yield self.command_text
        yield Static("Estimated Output", classes="panel-title")
        yield self.output_text

    def update_preview(self, form_data: dict[str, Any]) -> None:
        """Update preview based on current form values.

        Args:
            form_data: Current form state
        """
        cmd = self._build_command(form_data)
        self.command_text.update(cmd)

        # Estimate output using detection if input_dir provided
        if form_data.get("input_dir"):
            output = self._estimate_output(form_data["input_dir"])
        else:
            output = "Provide input directory to see estimate"

        self.output_text.update(output)

    def _build_command(self, form_data: dict[str, Any]) -> str:
        """Build CLI command string from form data.

        Args:
            form_data: Form values

        Returns:
            CLI command string
        """
        parts = ["dbt-to-lookml generate"]

        if form_data.get("input_dir"):
            parts.append(f"-i {form_data['input_dir']}")
        if form_data.get("output_dir"):
            parts.append(f"-o {form_data['output_dir']}")
        if form_data.get("schema"):
            parts.append(f"-s {form_data['schema']}")
        if form_data.get("view_prefix"):
            parts.append(f"--view-prefix {form_data['view_prefix']}")
        if form_data.get("explore_prefix"):
            parts.append(f"--explore-prefix {form_data['explore_prefix']}")
        if form_data.get("connection"):
            parts.append(f"-c {form_data['connection']}")
        if form_data.get("model_name"):
            parts.append(f"-m {form_data['model_name']}")

        # Boolean flags
        if form_data.get("dry_run"):
            parts.append("--dry-run")
        if form_data.get("skip_validation"):
            parts.append("--no-validation")
        if form_data.get("skip_formatting"):
            parts.append("--no-formatting")
        if form_data.get("show_summary"):
            parts.append("--show-summary")

        # Timezone conversion
        if form_data.get("convert_tz") == "yes":
            parts.append("--convert-tz")
        elif form_data.get("convert_tz") == "no":
            parts.append("--no-convert-tz")

        return " \\\n  ".join(parts)

    def _estimate_output(self, input_dir: str) -> str:
        """Estimate number of views/explores that will be generated.

        Args:
            input_dir: Path to semantic models

        Returns:
            Estimated output description
        """
        try:
            yaml_files = list(Path(input_dir).glob("*.yml")) + list(
                Path(input_dir).glob("*.yaml")
            )
            model_count = len(yaml_files)

            return f"• {model_count} view files\n• 1 explore file\n• 1 model file"
        except Exception as e:
            return f"Unable to estimate: {e}"
