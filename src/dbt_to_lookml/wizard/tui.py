"""TUI wizard for dbt-to-lookml generate command."""

from __future__ import annotations

from typing import Any

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical
    from textual.screen import Screen
    from textual.widgets import Button, Checkbox, Footer, Header, Input, Static

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    App = object  # type: ignore
    ComposeResult = list  # type: ignore
    Binding = object  # type: ignore
    Container = object  # type: ignore
    Horizontal = object  # type: ignore
    Vertical = object  # type: ignore
    Screen = object  # type: ignore
    Button = object  # type: ignore
    Checkbox = object  # type: ignore
    Footer = object  # type: ignore
    Header = object  # type: ignore
    Input = object  # type: ignore
    Static = object  # type: ignore

from dbt_to_lookml.wizard.tui_widgets import FormSection, PreviewPanel, ValidatedInput


class GenerateWizardTUI(App):  # type: ignore
    """Textual TUI for dbt-to-lookml generate command wizard.

    Provides form-based interface with live preview for generating LookML files.
    """

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary;
        color: $text;
        text-style: bold;
    }

    Footer {
        background: $panel;
        color: $text-muted;
    }

    #main-container {
        layout: horizontal;
        height: 100%;
    }

    #main-form {
        width: 70%;
        padding: 1 2;
        overflow-y: auto;
    }

    #preview-panel {
        width: 30%;
    }

    #button-bar {
        layout: horizontal;
        height: auto;
        margin: 2 0;
    }

    Button {
        margin: 0 1;
    }

    .field-container {
        margin: 1 0;
    }

    .field-label {
        color: $text;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("f1", "help", "Help"),
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+p", "preview_command", "Preview"),
        Binding("ctrl+enter", "execute", "Execute"),
    ]

    MIN_WIDTH = 80
    MIN_HEIGHT = 24

    def __init__(self, defaults: dict[str, Any] | None = None, **kwargs: Any) -> None:
        """Initialize TUI wizard.

        Args:
            defaults: Default values for form fields
            **kwargs: Additional App arguments
        """
        super().__init__(**kwargs)
        self.defaults = defaults or {}
        self.result: dict[str, Any] | None = None

    def compose(self) -> ComposeResult:
        """Compose TUI layout."""
        yield Header(show_clock=False)

        with Container(id="main-container"):
            with Vertical(id="main-form"):
                # Required Fields Section
                with FormSection(
                    "Required Fields",
                    description="Essential settings for LookML generation",
                ):
                    yield Static("Input Directory:", classes="field-label")
                    yield ValidatedInput(
                        placeholder="semantic_models/",
                        value=self.defaults.get("input_dir", ""),
                        required=True,
                        id="input-dir",
                    )

                    yield Static("Output Directory:", classes="field-label")
                    yield ValidatedInput(
                        placeholder="build/lookml/",
                        value=self.defaults.get("output_dir", ""),
                        required=True,
                        id="output-dir",
                    )

                    yield Static("Schema Name:", classes="field-label")
                    yield ValidatedInput(
                        placeholder="prod_analytics",
                        value=self.defaults.get("schema", ""),
                        required=True,
                        id="schema",
                    )

                # Optional Prefixes Section
                with FormSection(
                    "Optional Prefixes",
                    description="Customize view and explore names",
                ):
                    yield Static("View Prefix:", classes="field-label")
                    yield Input(
                        placeholder="(optional)",
                        value=self.defaults.get("view_prefix", ""),
                        id="view-prefix",
                    )

                    yield Static("Explore Prefix:", classes="field-label")
                    yield Input(
                        placeholder="(optional)",
                        value=self.defaults.get("explore_prefix", ""),
                        id="explore-prefix",
                    )

                    yield Static("Connection Name:", classes="field-label")
                    yield Input(
                        placeholder="redshift_test",
                        value=self.defaults.get("connection", "redshift_test"),
                        id="connection",
                    )

                    yield Static("Model Name:", classes="field-label")
                    yield Input(
                        placeholder="semantic_model",
                        value=self.defaults.get("model_name", "semantic_model"),
                        id="model-name",
                    )

                # Advanced Options Section
                with FormSection(
                    "Advanced Options",
                    description="Control validation, formatting, and execution",
                ):
                    with Horizontal(classes="field-container"):
                        yield Checkbox("Dry Run", id="dry-run")
                        yield Checkbox("Skip Validation", id="skip-validation")

                    with Horizontal(classes="field-container"):
                        yield Checkbox("Skip Formatting", id="skip-formatting")
                        yield Checkbox("Show Summary", id="show-summary")

                    yield Static("Timezone Conversion:", classes="field-label")
                    with Horizontal(classes="field-container"):
                        yield Checkbox("Enable (--convert-tz)", id="convert-tz-yes")
                        yield Checkbox("Disable (--no-convert-tz)", id="convert-tz-no")

                # Action Buttons
                with Horizontal(id="button-bar"):
                    yield Button("Cancel", variant="default", id="cancel-btn")
                    yield Button("Preview", variant="primary", id="preview-btn")
                    yield Button("Execute", variant="success", id="execute-btn")

            yield PreviewPanel(id="preview-panel")

        yield Footer()

    def on_mount(self) -> None:
        """Set up app on mount."""
        # Check terminal size
        size = self.size
        if size.width < self.MIN_WIDTH or size.height < self.MIN_HEIGHT:
            self.notify(
                f"Terminal too small! Minimum: {self.MIN_WIDTH}x{self.MIN_HEIGHT}, "
                f"Current: {size.width}x{size.height}",
                severity="warning",
                timeout=10,
            )

        # Focus first input
        self.query_one("#input-dir", expect_type=ValidatedInput).focus()

        # Initial preview update
        self.update_preview()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update preview when any input changes."""
        self.update_preview()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Update preview when checkboxes change."""
        # Handle mutually exclusive timezone checkboxes
        if event.checkbox.id == "convert-tz-yes" and event.value:
            self.query_one("#convert-tz-no", expect_type=Checkbox).value = False
        elif event.checkbox.id == "convert-tz-no" and event.value:
            self.query_one("#convert-tz-yes", expect_type=Checkbox).value = False

        self.update_preview()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "cancel-btn":
            self.action_cancel()
        elif event.button.id == "preview-btn":
            self.action_preview_command()
        elif event.button.id == "execute-btn":
            self.action_execute()

    def update_preview(self) -> None:
        """Update preview panel with current form state."""
        form_data = self.get_form_data()
        preview = self.query_one("#preview-panel", expect_type=PreviewPanel)
        preview.update_preview(form_data)

    def get_form_data(self) -> dict[str, Any]:
        """Extract current form values.

        Returns:
            Dictionary of form data
        """
        return {
            "input_dir": self.query_one("#input-dir", expect_type=Input).value,
            "output_dir": self.query_one("#output-dir", expect_type=Input).value,
            "schema": self.query_one("#schema", expect_type=Input).value,
            "view_prefix": self.query_one("#view-prefix", expect_type=Input).value,
            "explore_prefix": self.query_one(
                "#explore-prefix", expect_type=Input
            ).value,
            "connection": self.query_one("#connection", expect_type=Input).value,
            "model_name": self.query_one("#model-name", expect_type=Input).value,
            "dry_run": self.query_one("#dry-run", expect_type=Checkbox).value,
            "skip_validation": self.query_one(
                "#skip-validation", expect_type=Checkbox
            ).value,
            "skip_formatting": self.query_one(
                "#skip-formatting", expect_type=Checkbox
            ).value,
            "show_summary": self.query_one("#show-summary", expect_type=Checkbox).value,
            "convert_tz": self._get_convert_tz_value(),
        }

    def _get_convert_tz_value(self) -> str:
        """Get timezone conversion setting.

        Returns:
            "yes", "no", or "unset"
        """
        if self.query_one("#convert-tz-yes", expect_type=Checkbox).value:
            return "yes"
        elif self.query_one("#convert-tz-no", expect_type=Checkbox).value:
            return "no"
        else:
            return "unset"

    def validate_form(self) -> bool:
        """Validate all required fields.

        Returns:
            True if valid, False otherwise
        """
        input_dir = self.query_one("#input-dir", expect_type=Input)
        output_dir = self.query_one("#output-dir", expect_type=Input)
        schema = self.query_one("#schema", expect_type=Input)

        all_valid = True

        if not input_dir.value.strip():
            all_valid = False
            input_dir.add_class("error")

        if not output_dir.value.strip():
            all_valid = False
            output_dir.add_class("error")

        if not schema.value.strip():
            all_valid = False
            schema.add_class("error")

        if not all_valid:
            self.notify("Please fill in all required fields", severity="error")

        return all_valid

    def action_cancel(self) -> None:
        """Cancel and exit without executing."""
        self.result = None
        self.exit()

    def action_preview_command(self) -> None:
        """Show full command in notification."""
        form_data = self.get_form_data()
        preview = self.query_one("#preview-panel", expect_type=PreviewPanel)
        cmd = preview._build_command(form_data)
        self.notify(f"Command:\n{cmd}", timeout=10)

    def action_execute(self) -> None:
        """Execute command with current form values."""
        if not self.validate_form():
            return

        self.result = self.get_form_data()
        self.exit()

    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())


class HelpScreen(Screen):  # type: ignore
    """Modal help screen with keyboard shortcuts and field descriptions."""

    BINDINGS = [
        Binding("escape", "pop_screen", "Close"),
    ]

    def compose(self) -> ComposeResult:
        """Compose help modal."""
        with Container(classes="help-modal"):
            yield Static("Help & Keyboard Shortcuts", classes="help-title")
            yield Static(HELP_TEXT, classes="help-content")
            yield Button("Close", variant="primary", id="close-help")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Close help on button click."""
        if event.button.id == "close-help":
            self.app.pop_screen()


HELP_TEXT = """[bold]Keyboard Shortcuts:[/bold]
  Tab / Shift+Tab    Navigate between fields
  F1                 Show this help
  Ctrl+P             Preview command
  Ctrl+Enter         Execute command
  Escape             Cancel and exit

[bold]Required Fields:[/bold]
  Input Directory    Path to semantic model YAML files
  Output Directory   Where to write generated LookML files
  Schema Name        Database schema for sql_table_name

[bold]Optional Settings:[/bold]
  Prefixes           Add prefixes to view/explore names
  Connection         Looker connection name (default: redshift_test)
  Model Name         Generated model file name (default: semantic_model)
  Convert TZ         Enable/disable timezone conversion for time dimensions
  Advanced Options   Control validation, formatting, dry-run
"""


def launch_tui_wizard(defaults: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Launch TUI wizard for generate command.

    Args:
        defaults: Default values for form fields from project detection

    Returns:
        Form data dict if user executes, None if cancelled

    Raises:
        ImportError: If Textual library is not installed
    """
    if not TEXTUAL_AVAILABLE:
        raise ImportError(
            "Textual library is required for TUI mode.\n"
            "Install with: pip install dbt-to-lookml[wizard]\n"
            "Or use prompt-based wizard: dbt-to-lookml wizard generate"
        )

    app = GenerateWizardTUI(defaults=defaults)
    app.run()
    return app.result
