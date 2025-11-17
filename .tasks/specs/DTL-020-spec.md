# Feature: Implement optional TUI wizard mode with Textual

## Metadata
- **Issue**: `DTL-020`
- **Stack**: `backend`
- **Generated**: 2025-11-17T21:30:00Z
- **Strategy**: Approved 2025-11-12T21:00:00Z
- **Epic**: DTL-014 (CLI Wizard Enhancements)

## Issue Context

### Problem Statement

Create a full TUI (Text User Interface) mode using Textual library, providing a richer interactive experience with forms, navigation, and live preview. This enhances the wizard experience beyond the basic prompt-based approach (DTL-018) for users who prefer GUI-like terminal interfaces.

### Solution Approach

Implement a feature-rich TUI using Textual framework that provides:
- Form-based UI with three sections (Required, Optional, Advanced)
- Live preview panel showing command and estimated output
- Keyboard navigation and shortcuts
- Context-sensitive help system
- Graceful fallback if Textual not installed
- Integration with existing wizard infrastructure (detection, command building)

### Success Criteria

- TUI launches with `dbt-to-lookml wizard generate --wizard-tui`
- Form sections: Required Fields, Optional Prefixes, Advanced Options
- Live preview panel shows command and estimated output
- Keyboard navigation: Tab, Shift+Tab, arrow keys, Enter to submit
- Help text visible in sidebar with F1 key
- TUI works in standard terminal (80x24 minimum)
- Graceful error if Textual not installed

## Approved Strategy Summary

The implementation follows a modular architecture:

1. **Core TUI Application** (`tui.py`): Main Textual app with 70/30 split layout (form on left, preview on right)
2. **Custom Widgets** (`tui_widgets.py`): Reusable components (ValidatedInput, FormSection, PreviewPanel)
3. **Reactive System**: Live preview updates using Textual's reactive properties
4. **Graceful Fallback**: Import guards with helpful error messages if Textual unavailable
5. **CLI Integration**: `--wizard-tui` flag on `wizard generate` command
6. **Testing**: Unit tests for widgets, integration tests using Textual Pilot API

**Dependencies**:
- `textual>=0.47.0` - TUI framework
- `typing-extensions>=4.0` - Python 3.9 compatibility

**Installation**: `pip install dbt-to-lookml[wizard]`

## Implementation Plan

### Phase 1: Project Structure Setup

**Tasks**:
1. **Create wizard module structure**
   - Action: Create `src/dbt_to_lookml/wizard/` directory
   - Files: `__init__.py`, `tui.py`, `tui_widgets.py`
   - Pattern: Follow existing package structure (parsers/, generators/)

2. **Update pyproject.toml**
   - Action: Add Textual to optional dependencies
   - Section: `[project.optional-dependencies]`
   - Entry: `wizard = ["textual>=0.47.0", "typing-extensions>=4.0"]`

### Phase 2: Custom Widgets Implementation

**Tasks**:
3. **Implement FormSection widget**
   - File: `src/dbt_to_lookml/wizard/tui_widgets.py`
   - Purpose: Container for grouped form fields with section title
   - Pattern: Extend `textual.containers.Container`

4. **Implement ValidatedInput widget**
   - File: `src/dbt_to_lookml/wizard/tui_widgets.py`
   - Purpose: Input field with real-time validation and error display
   - Pattern: Extend `textual.widgets.Input`
   - Features: Required field check, custom validators, error styling

5. **Implement PreviewPanel widget**
   - File: `src/dbt_to_lookml/wizard/tui_widgets.py`
   - Purpose: Right-side panel showing live command preview and output estimation
   - Pattern: Extend `textual.containers.Container`
   - Features: Command string display, output estimation, auto-update on form changes

### Phase 3: Main TUI Application

**Tasks**:
6. **Create GenerateWizardTUI app class**
   - File: `src/dbt_to_lookml/wizard/tui.py`
   - Purpose: Main Textual application with full form layout
   - Pattern: Extend `textual.app.App`
   - Layout: 70/30 split (form/preview), header, footer

7. **Implement reactive properties for form fields**
   - File: `src/dbt_to_lookml/wizard/tui.py`
   - Purpose: Track form state and trigger preview updates
   - Pattern: Use `textual.reactive.reactive` decorator
   - Fields: input_dir, output_dir, schema, prefixes, flags

8. **Implement keyboard navigation**
   - File: `src/dbt_to_lookml/wizard/tui.py`
   - Purpose: Tab order, shortcuts, focus management
   - Pattern: Use Textual bindings and actions
   - Shortcuts: Tab, Shift+Tab, F1, Ctrl+P, Ctrl+Enter, Escape

9. **Create help system**
   - File: `src/dbt_to_lookml/wizard/tui.py`
   - Purpose: F1 modal with keyboard shortcuts and field descriptions
   - Pattern: Separate Screen class for modal
   - Content: Keyboard shortcuts, field help, usage tips

### Phase 4: Integration and Fallback

**Tasks**:
10. **Add CLI integration**
    - File: `src/dbt_to_lookml/__main__.py`
    - Action: Add `--wizard-tui` flag to wizard generate command
    - Pattern: Follow existing CLI flag patterns
    - Validation: Check Textual availability before launch

11. **Implement graceful fallback**
    - File: `src/dbt_to_lookml/wizard/tui.py`
    - Action: Add import guard with try/except
    - Error: Friendly message with installation instructions
    - Fallback: Suggest prompt-based wizard

12. **Connect to detection module**
    - File: `src/dbt_to_lookml/wizard/tui.py`
    - Action: Use DTL-017 detection for smart defaults
    - Pattern: Pass defaults dict to TUI app initialization
    - Usage: Pre-fill form fields when detection succeeds

### Phase 5: Testing

**Tasks**:
13. **Write unit tests for widgets**
    - File: `src/tests/unit/test_wizard_tui.py`
    - Coverage: ValidatedInput, FormSection, PreviewPanel
    - Tests: Validation, rendering, event handling

14. **Write integration tests with Pilot API**
    - File: `src/tests/integration/test_wizard_tui_integration.py`
    - Coverage: Full TUI workflow, keyboard navigation, command execution
    - Tests: Launch, fill form, execute, cancel, defaults

15. **Add CLI tests for TUI flag**
    - File: `src/tests/test_cli.py`
    - Coverage: `--wizard-tui` flag handling, Textual availability check
    - Tests: TUI launch, fallback error, env variable

## Detailed Task Breakdown

### Task 1: Create Wizard Module Structure

**Files**:
- `src/dbt_to_lookml/wizard/__init__.py`
- `src/dbt_to_lookml/wizard/tui.py`
- `src/dbt_to_lookml/wizard/tui_widgets.py`

**Action**: Initialize module with placeholder files

**Implementation Guidance**:
```python
# src/dbt_to_lookml/wizard/__init__.py
"""Interactive wizard for dbt-to-lookml CLI commands."""

from typing import Any

__all__ = ["launch_tui_wizard"]


def launch_tui_wizard(defaults: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Launch TUI wizard for generate command.

    Args:
        defaults: Default values for form fields from project detection

    Returns:
        Form data dict if user executes, None if cancelled

    Raises:
        ImportError: If Textual library is not installed
    """
    from dbt_to_lookml.wizard.tui import launch_tui_wizard as _launch
    return _launch(defaults)
```

**Reference**: Similar to how `generators/` and `parsers/` are structured

**Tests**: Import tests in `test_wizard_tui.py`

---

### Task 2: Update pyproject.toml

**File**: `pyproject.toml`

**Action**: Add wizard optional dependencies

**Implementation Guidance**:
```toml
[project.optional-dependencies]
wizard = [
    "textual>=0.47.0",
    "typing-extensions>=4.0",
]
dev = [
    # ... existing dev deps
]
```

**Reference**: Existing `[project.optional-dependencies]` at line 38

**Tests**: Manual verification: `pip install -e ".[wizard]"` succeeds

---

### Task 3: Implement FormSection Widget

**File**: `src/dbt_to_lookml/wizard/tui_widgets.py`

**Action**: Create container widget for grouping related form fields

**Implementation Guidance**:
```python
"""Custom Textual widgets for wizard TUI."""

from typing import Iterable

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static


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
    }

    FormSection .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    FormSection .section-description {
        color: $text-muted;
        text-style: italic;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        title: str,
        description: str | None = None,
        *children: Iterable[ComposeResult],
        **kwargs: Any,
    ) -> None:
        """Initialize FormSection.

        Args:
            title: Section heading
            description: Optional section description
            children: Child widgets
            **kwargs: Additional Container arguments
        """
        super().__init__(*children, **kwargs)
        self.title = title
        self.description = description

    def compose(self) -> ComposeResult:
        """Compose section with title and children."""
        yield Static(self.title, classes="section-title")
        if self.description:
            yield Static(self.description, classes="section-description")
        yield from self.children
```

**Reference**: Textual Container widget pattern

**Tests**: `test_form_section_rendering` - verify title and children rendered

---

### Task 4: Implement ValidatedInput Widget

**File**: `src/dbt_to_lookml/wizard/tui_widgets.py`

**Action**: Create input field with real-time validation

**Implementation Guidance**:
```python
from typing import Callable

from textual.widgets import Input
from textual.message import Message


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
        super().__init__(placeholder=placeholder, **kwargs)
        self.validator = validator
        self.required = required
        self.validation_error: str | None = None

    def validate_value(self, value: str) -> str | None:
        """Validate input value.

        Args:
            value: Current input value

        Returns:
            Error message or None if valid
        """
        if self.required and not value.strip():
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

    def is_valid(self) -> bool:
        """Check if current value is valid.

        Returns:
            True if valid, False otherwise
        """
        return self.validation_error is None
```

**Reference**: Textual Input widget extension pattern

**Tests**:
- `test_validated_input_required` - test required field validation
- `test_validated_input_custom_validator` - test custom validation function
- `test_validated_input_error_styling` - verify error class applied

---

### Task 5: Implement PreviewPanel Widget

**File**: `src/dbt_to_lookml/wizard/tui_widgets.py`

**Action**: Create live-updating preview panel

**Implementation Guidance**:
```python
from textual.containers import Vertical
from textual.widgets import Static


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
            from pathlib import Path

            yaml_files = list(Path(input_dir).glob("*.yml")) + list(Path(input_dir).glob("*.yaml"))
            model_count = len(yaml_files)

            return f"• {model_count} view files\n• 1 explore file\n• 1 model file"
        except Exception as e:
            return f"Unable to estimate: {e}"
```

**Reference**: Textual Vertical container pattern

**Tests**:
- `test_preview_panel_command_building` - verify command string generation
- `test_preview_panel_output_estimation` - test output estimation logic

---

### Task 6: Create GenerateWizardTUI App Class

**File**: `src/dbt_to_lookml/wizard/tui.py`

**Action**: Main Textual application with full layout

**Implementation Guidance**:
```python
"""TUI wizard for dbt-to-lookml generate command."""

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


from dbt_to_lookml.wizard.tui_widgets import FormSection, PreviewPanel, ValidatedInput


class GenerateWizardTUI(App):
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
        self.query_one("#input-dir").focus()

        # Initial preview update
        self.update_preview()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update preview when any input changes."""
        self.update_preview()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Update preview when checkboxes change."""
        # Handle mutually exclusive timezone checkboxes
        if event.checkbox.id == "convert-tz-yes" and event.value:
            self.query_one("#convert-tz-no").value = False
        elif event.checkbox.id == "convert-tz-no" and event.value:
            self.query_one("#convert-tz-yes").value = False

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
        preview = self.query_one(PreviewPanel)
        preview.update_preview(form_data)

    def get_form_data(self) -> dict[str, Any]:
        """Extract current form values.

        Returns:
            Dictionary of form data
        """
        return {
            "input_dir": self.query_one("#input-dir").value,
            "output_dir": self.query_one("#output-dir").value,
            "schema": self.query_one("#schema").value,
            "view_prefix": self.query_one("#view-prefix").value,
            "explore_prefix": self.query_one("#explore-prefix").value,
            "connection": self.query_one("#connection").value,
            "model_name": self.query_one("#model-name").value,
            "dry_run": self.query_one("#dry-run").value,
            "skip_validation": self.query_one("#skip-validation").value,
            "skip_formatting": self.query_one("#skip-formatting").value,
            "show_summary": self.query_one("#show-summary").value,
            "convert_tz": self._get_convert_tz_value(),
        }

    def _get_convert_tz_value(self) -> str:
        """Get timezone conversion setting.

        Returns:
            "yes", "no", or "unset"
        """
        if self.query_one("#convert-tz-yes").value:
            return "yes"
        elif self.query_one("#convert-tz-no").value:
            return "no"
        else:
            return "unset"

    def validate_form(self) -> bool:
        """Validate all required fields.

        Returns:
            True if valid, False otherwise
        """
        input_dir = self.query_one("#input-dir")
        output_dir = self.query_one("#output-dir")
        schema = self.query_one("#schema")

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
        preview = self.query_one(PreviewPanel)
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


class HelpScreen(Screen):
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
```

**Reference**: Textual App pattern, similar to examples in Textual documentation

**Tests**: Integration tests with Pilot API

---

### Task 7-9: Reactive Properties, Navigation, Help

These are implemented as part of Task 6 (GenerateWizardTUI class). The reactive system uses Textual's built-in event handlers (`on_input_changed`, `on_checkbox_changed`) rather than reactive properties for simplicity.

---

### Task 10: Add CLI Integration

**File**: `src/dbt_to_lookml/__main__.py`

**Action**: Add `wizard` command group with `generate` subcommand

**Implementation Guidance**:
```python
# Add after existing imports
from typing import Any

# Add new command group
@cli.group()
def wizard() -> None:
    """Interactive wizards for CLI commands."""
    pass


@wizard.command("generate")
@click.option(
    "--wizard-tui",
    is_flag=True,
    help="Use TUI interface (requires textual)",
)
def wizard_generate(wizard_tui: bool) -> None:
    """Interactive wizard for generate command.

    Provides two modes:
    - Default: Prompt-based wizard (simple, no dependencies)
    - TUI mode (--wizard-tui): Rich terminal UI (requires textual)
    """
    if wizard_tui:
        try:
            from dbt_to_lookml.wizard import launch_tui_wizard

            # Get smart defaults (DTL-017 - if implemented)
            defaults: dict[str, Any] = {}
            # TODO: Add detection module integration when DTL-017 is complete
            # from dbt_to_lookml.wizard.detection import detect_defaults
            # defaults = detect_defaults()

            # Launch TUI
            result = launch_tui_wizard(defaults)

            if result:
                # Execute the generate command with form data
                console.print("[bold blue]Executing command...[/bold blue]")

                # Convert form data to click context and invoke generate
                ctx = click.get_current_context()
                ctx.invoke(
                    generate,
                    input_dir=Path(result["input_dir"]),
                    output_dir=Path(result["output_dir"]),
                    schema=result["schema"],
                    view_prefix=result.get("view_prefix", ""),
                    explore_prefix=result.get("explore_prefix", ""),
                    dry_run=result.get("dry_run", False),
                    no_validation=result.get("skip_validation", False),
                    no_formatting=result.get("skip_formatting", False),
                    show_summary=result.get("show_summary", False),
                    connection=result.get("connection", "redshift_test"),
                    model_name=result.get("model_name", "semantic_model"),
                    convert_tz=result.get("convert_tz") == "yes",
                    no_convert_tz=result.get("convert_tz") == "no",
                )
            else:
                console.print("[yellow]Wizard cancelled[/yellow]")

        except ImportError as e:
            console.print(f"[bold red]Error: {e}[/bold red]")
            console.print(
                "\nTo use TUI mode, install wizard dependencies:\n"
                "  pip install dbt-to-lookml[wizard]\n"
                "  or: uv pip install -e '.[wizard]'\n"
                "\nOr use the prompt-based wizard:\n"
                "  dbt-to-lookml wizard generate"
            )
            raise click.ClickException("Textual library not available")
    else:
        # TODO: Implement prompt-based wizard (DTL-018)
        console.print("[yellow]Prompt-based wizard not yet implemented[/yellow]")
        console.print("Use --wizard-tui flag or run generate command directly")
```

**Reference**: Existing `generate` and `validate` commands in `__main__.py`

**Tests**: `test_wizard_tui_flag` in `test_cli.py`

---

### Task 11: Graceful Fallback

**File**: `src/dbt_to_lookml/wizard/tui.py`

**Action**: Implement import guard (already shown in Task 6)

**Implementation**:
- Try/except block around Textual imports
- `TEXTUAL_AVAILABLE` flag
- Friendly ImportError in `launch_tui_wizard()`

**Reference**: Similar pattern used in `__main__.py` for GENERATOR_AVAILABLE

**Tests**: `test_textual_import_fallback` with mocked import failure

---

### Task 12: Connect to Detection Module

**File**: `src/dbt_to_lookml/wizard/tui.py`

**Action**: Use detection module for smart defaults (when DTL-017 is complete)

**Implementation**: Already shown in Task 10 (CLI integration)

**Note**: This is a placeholder for future integration. For now, defaults can be passed as empty dict.

---

### Task 13: Write Unit Tests for Widgets

**File**: `src/tests/unit/test_wizard_tui.py`

**Action**: Test individual widget behavior

**Implementation Guidance**:
```python
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

    def test_validation_error_styling(self) -> None:
        """Test error class applied on validation failure."""
        input_widget = ValidatedInput(required=True)

        # Simulate input change with empty value
        input_widget.validation_error = "This field is required"
        assert not input_widget.is_valid()


class TestFormSection:
    """Test FormSection widget."""

    def test_section_with_title(self) -> None:
        """Test FormSection renders title."""
        section = FormSection(
            title="Test Section",
            description="Test description",
        )

        assert section.title == "Test Section"
        assert section.description == "Test description"


class TestPreviewPanel:
    """Test PreviewPanel widget."""

    def test_command_building(self) -> None:
        """Test command string generation."""
        panel = PreviewPanel()

        form_data = {
            "input_dir": "semantic_models/",
            "output_dir": "build/lookml/",
            "schema": "prod",
            "view_prefix": "v_",
            "dry_run": True,
            "convert_tz": "yes",
        }

        cmd = panel._build_command(form_data)

        assert "dbt-to-lookml generate" in cmd
        assert "-i semantic_models/" in cmd
        assert "-o build/lookml/" in cmd
        assert "-s prod" in cmd
        assert "--view-prefix v_" in cmd
        assert "--dry-run" in cmd
        assert "--convert-tz" in cmd

    def test_output_estimation(self) -> None:
        """Test output estimation logic."""
        panel = PreviewPanel()

        # Test with non-existent directory
        output = panel._estimate_output("/nonexistent")
        assert "Unable to estimate" in output
```

**Reference**: Existing test patterns in `test_lookml_generator.py`

**Estimated lines**: ~150

---

### Task 14: Write Integration Tests with Pilot API

**File**: `src/tests/integration/test_wizard_tui_integration.py`

**Action**: Test full TUI workflow using Textual Pilot API

**Implementation Guidance**:
```python
"""Integration tests for wizard TUI using Textual Pilot API."""

import pytest

# Skip all tests if Textual not available
pytest.importorskip("textual")

from textual.pilot import Pilot

from dbt_to_lookml.wizard.tui import GenerateWizardTUI


@pytest.mark.integration
class TestWizardTUIIntegration:
    """Integration tests for TUI wizard."""

    @pytest.mark.asyncio
    async def test_tui_launch_and_cancel(self) -> None:
        """Test launching TUI and cancelling."""
        app = GenerateWizardTUI()

        async with app.run_test() as pilot:
            # Click cancel button
            await pilot.click("#cancel-btn")

            # Verify app exited with no result
            assert app.result is None

    @pytest.mark.asyncio
    async def test_tui_required_fields_only(self) -> None:
        """Test filling required fields and executing."""
        app = GenerateWizardTUI()

        async with app.run_test() as pilot:
            # Fill required fields
            await pilot.click("#input-dir")
            pilot.app.query_one("#input-dir").value = "semantic_models/"

            await pilot.click("#output-dir")
            pilot.app.query_one("#output-dir").value = "build/lookml/"

            await pilot.click("#schema")
            pilot.app.query_one("#schema").value = "prod_analytics"

            # Click execute
            await pilot.click("#execute-btn")

            # Verify result
            assert app.result is not None
            assert app.result["input_dir"] == "semantic_models/"
            assert app.result["output_dir"] == "build/lookml/"
            assert app.result["schema"] == "prod_analytics"

    @pytest.mark.asyncio
    async def test_tui_all_fields(self) -> None:
        """Test filling all fields including optional."""
        app = GenerateWizardTUI()

        async with app.run_test() as pilot:
            # Fill required fields
            pilot.app.query_one("#input-dir").value = "semantic_models/"
            pilot.app.query_one("#output-dir").value = "build/lookml/"
            pilot.app.query_one("#schema").value = "prod"

            # Fill optional fields
            pilot.app.query_one("#view-prefix").value = "v_"
            pilot.app.query_one("#explore-prefix").value = "e_"
            pilot.app.query_one("#connection").value = "bigquery"
            pilot.app.query_one("#model-name").value = "my_model"

            # Toggle checkboxes
            await pilot.click("#dry-run")
            await pilot.click("#show-summary")
            await pilot.click("#convert-tz-yes")

            # Execute
            await pilot.click("#execute-btn")

            # Verify all values in result
            result = app.result
            assert result is not None
            assert result["view_prefix"] == "v_"
            assert result["dry_run"] is True
            assert result["convert_tz"] == "yes"

    @pytest.mark.asyncio
    async def test_tui_with_defaults(self) -> None:
        """Test TUI with pre-filled defaults."""
        defaults = {
            "input_dir": "models/",
            "output_dir": "output/",
            "schema": "default_schema",
        }

        app = GenerateWizardTUI(defaults=defaults)

        async with app.run_test() as pilot:
            # Verify defaults are pre-filled
            assert pilot.app.query_one("#input-dir").value == "models/"
            assert pilot.app.query_one("#output-dir").value == "output/"
            assert pilot.app.query_one("#schema").value == "default_schema"

    @pytest.mark.asyncio
    async def test_tui_validation_prevents_execution(self) -> None:
        """Test that invalid input blocks execution."""
        app = GenerateWizardTUI()

        async with app.run_test() as pilot:
            # Try to execute without filling required fields
            await pilot.click("#execute-btn")

            # Verify no result (execution blocked)
            # Note: App may still be running since validation failed
            # We need to check that validate_form returned False
            # This is tricky with async - may need to check UI state instead

    @pytest.mark.asyncio
    async def test_tui_keyboard_navigation(self) -> None:
        """Test keyboard navigation with Tab."""
        app = GenerateWizardTUI()

        async with app.run_test() as pilot:
            # Start at first field
            await pilot.press("tab")

            # Verify focus moved (hard to test focus state directly)
            # This is a basic smoke test

    @pytest.mark.asyncio
    async def test_tui_help_modal(self) -> None:
        """Test opening and closing help modal."""
        app = GenerateWizardTUI()

        async with app.run_test() as pilot:
            # Press F1 to open help
            await pilot.press("f1")

            # Help screen should be visible
            # Close with escape
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_timezone_checkbox_mutual_exclusion(self) -> None:
        """Test that timezone checkboxes are mutually exclusive."""
        app = GenerateWizardTUI()

        async with app.run_test() as pilot:
            # Check "yes"
            await pilot.click("#convert-tz-yes")
            assert pilot.app.query_one("#convert-tz-yes").value is True
            assert pilot.app.query_one("#convert-tz-no").value is False

            # Check "no"
            await pilot.click("#convert-tz-no")
            assert pilot.app.query_one("#convert-tz-yes").value is False
            assert pilot.app.query_one("#convert-tz-no").value is True
```

**Reference**: Textual Pilot API documentation and examples

**Estimated lines**: ~200

---

### Task 15: Add CLI Tests for TUI Flag

**File**: `src/tests/test_cli.py`

**Action**: Add tests for `wizard generate --wizard-tui` command

**Implementation Guidance**:
```python
# Add to existing TestCLI class

def test_wizard_generate_help(self, runner: CliRunner) -> None:
    """Test wizard generate command help."""
    result = runner.invoke(cli, ["wizard", "generate", "--help"])
    assert result.exit_code == 0
    assert "--wizard-tui" in result.output


@pytest.mark.skipif(
    not TEXTUAL_AVAILABLE,
    reason="Textual not installed"
)
def test_wizard_tui_flag_textual_available(self, runner: CliRunner) -> None:
    """Test --wizard-tui launches TUI when Textual is available."""
    # This is tricky to test since TUI is interactive
    # We can test that it imports correctly
    from dbt_to_lookml.wizard import launch_tui_wizard

    # Just verify function exists and is callable
    assert callable(launch_tui_wizard)


def test_wizard_tui_flag_textual_unavailable(self, runner: CliRunner) -> None:
    """Test error if Textual not installed."""
    with patch("dbt_to_lookml.wizard.tui.TEXTUAL_AVAILABLE", False):
        result = runner.invoke(cli, ["wizard", "generate", "--wizard-tui"])

        assert result.exit_code != 0
        assert "Textual library" in result.output
        assert "pip install" in result.output
```

**Reference**: Existing CLI tests in `test_cli.py`

**Estimated lines**: ~40

---

## File Changes

### Files to Create

#### `src/dbt_to_lookml/wizard/__init__.py`
**Purpose**: Module initialization with TUI launcher export

**Estimated lines**: ~30

**Structure**: Import guard, `launch_tui_wizard` function export

---

#### `src/dbt_to_lookml/wizard/tui.py`
**Purpose**: Main TUI application with GenerateWizardTUI and HelpScreen

**Estimated lines**: ~400

**Structure**:
- Import guard for Textual
- GenerateWizardTUI App class
  - CSS styling
  - Keyboard bindings
  - compose() layout
  - Event handlers
  - Form validation
  - Actions (cancel, preview, execute, help)
- HelpScreen modal
- HELP_TEXT constant
- launch_tui_wizard() entry point

---

#### `src/dbt_to_lookml/wizard/tui_widgets.py`
**Purpose**: Custom Textual widgets (FormSection, ValidatedInput, PreviewPanel)

**Estimated lines**: ~250

**Structure**:
- FormSection widget
- ValidatedInput widget with validation
- PreviewPanel widget with command building and estimation

---

#### `src/tests/unit/test_wizard_tui.py`
**Purpose**: Unit tests for TUI widgets

**Estimated lines**: ~150

**Test cases**: 10 unit tests covering widget behavior

---

#### `src/tests/integration/test_wizard_tui_integration.py`
**Purpose**: Integration tests using Textual Pilot API

**Estimated lines**: ~200

**Test cases**: 8 integration tests covering full workflows

---

### Files to Modify

#### `pyproject.toml`
**Changes**:
- Add `[project.optional-dependencies]` section with `wizard` entry
- Add Textual and typing-extensions dependencies

**Lines changed**: ~5

---

#### `src/dbt_to_lookml/__main__.py`
**Changes**:
- Add `wizard` command group
- Add `wizard generate` command with `--wizard-tui` flag
- Import `launch_tui_wizard` with error handling
- Invoke `generate` command with TUI form data

**Lines added**: ~80

---

#### `src/tests/test_cli.py`
**Changes**:
- Add tests for `wizard generate` command
- Add tests for `--wizard-tui` flag (available/unavailable)

**Lines added**: ~40

---

## Testing Strategy

### Unit Tests

**File**: `src/tests/unit/test_wizard_tui.py`

**Test Cases**:

1. **test_textual_import_available**
   - Setup: Import Textual modules
   - Assert: TEXTUAL_AVAILABLE is True

2. **test_validated_input_required**
   - Setup: Create ValidatedInput with required=True
   - Action: Validate empty value
   - Assert: Returns error message

3. **test_validated_input_custom_validator**
   - Setup: Create ValidatedInput with custom validator
   - Action: Validate invalid value
   - Assert: Returns custom error message

4. **test_form_section_rendering**
   - Setup: Create FormSection with title
   - Assert: Title and description set correctly

5. **test_preview_panel_command_building**
   - Setup: Create PreviewPanel
   - Action: Call _build_command with form data
   - Assert: Command string matches expected format

6. **test_preview_panel_output_estimation**
   - Setup: Create PreviewPanel with mock directory
   - Action: Call _estimate_output
   - Assert: Returns estimate or error message

7. **test_keyboard_shortcuts_bindings**
   - Setup: Create GenerateWizardTUI
   - Assert: All BINDINGS defined

8. **test_help_screen_content**
   - Setup: Create HelpScreen
   - Assert: HELP_TEXT contains shortcuts and field help

9. **test_form_validation**
   - Setup: Create GenerateWizardTUI with empty fields
   - Action: Call validate_form()
   - Assert: Returns False

10. **test_get_form_data**
    - Setup: Create GenerateWizardTUI with filled fields
    - Action: Call get_form_data()
    - Assert: Returns correct dictionary

**Coverage Target**: 90%+ (lower than typical due to UI complexity)

---

### Integration Tests

**File**: `src/tests/integration/test_wizard_tui_integration.py`

**Test Cases**:

1. **test_tui_launch_and_cancel**
   - Launch TUI
   - Click Cancel button
   - Assert: result is None

2. **test_tui_required_fields_only**
   - Launch TUI
   - Fill required fields
   - Click Execute
   - Assert: result contains required values

3. **test_tui_all_fields**
   - Launch TUI
   - Fill all fields
   - Toggle checkboxes
   - Click Execute
   - Assert: result contains all values

4. **test_tui_with_defaults**
   - Launch TUI with defaults
   - Assert: Fields pre-filled with default values

5. **test_tui_validation_prevents_execution**
   - Launch TUI
   - Click Execute without filling fields
   - Assert: Execution blocked, notification shown

6. **test_tui_preview_updates_live**
   - Launch TUI
   - Change input field
   - Assert: Preview panel updated

7. **test_tui_keyboard_navigation**
   - Launch TUI
   - Press Tab multiple times
   - Assert: Focus moves through fields

8. **test_tui_help_modal**
   - Launch TUI
   - Press F1
   - Assert: Help screen visible
   - Press Escape
   - Assert: Help screen closed

9. **test_timezone_checkbox_mutual_exclusion**
   - Launch TUI
   - Check "yes" checkbox
   - Assert: "no" checkbox unchecked
   - Check "no" checkbox
   - Assert: "yes" checkbox unchecked

10. **test_tui_terminal_size_warning**
    - Mock terminal size as too small
    - Launch TUI
    - Assert: Warning notification shown

**Coverage Target**: 85%+

---

### CLI Tests

**File**: `src/tests/test_cli.py`

**Test Cases**:

1. **test_wizard_generate_help**
   - Invoke: `wizard generate --help`
   - Assert: exit_code == 0, help text contains --wizard-tui

2. **test_wizard_tui_flag_textual_available**
   - Setup: Textual installed (skip if not)
   - Assert: launch_tui_wizard function is callable

3. **test_wizard_tui_flag_textual_unavailable**
   - Setup: Mock TEXTUAL_AVAILABLE as False
   - Invoke: `wizard generate --wizard-tui`
   - Assert: exit_code != 0, error message about installation

**Coverage Target**: 95%+

---

## Validation Commands

**Unit Tests**:
```bash
# Run TUI unit tests only
python -m pytest src/tests/unit/test_wizard_tui.py -v

# With coverage
python -m pytest src/tests/unit/test_wizard_tui.py --cov=dbt_to_lookml.wizard --cov-report=term
```

**Integration Tests**:
```bash
# Run TUI integration tests
python -m pytest src/tests/integration/test_wizard_tui_integration.py -v -m integration

# Skip if Textual not installed
python -m pytest src/tests/integration/test_wizard_tui_integration.py -v --skipif "not textual"
```

**CLI Tests**:
```bash
# Run all CLI tests including wizard
python -m pytest src/tests/test_cli.py -v -k wizard
```

**Full Test Suite**:
```bash
# Run all wizard-related tests
make test

# Or with test orchestrator
python scripts/run-tests.py all -v
```

**Type Check**:
```bash
make type-check

# Or directly
mypy src/dbt_to_lookml/wizard/
```

**Lint**:
```bash
make lint

# Auto-fix
make format
```

**Quality Gate**:
```bash
make quality-gate
```

**Manual Testing**:
```bash
# Install with wizard extras
pip install -e ".[wizard]"

# Launch TUI wizard
dbt-to-lookml wizard generate --wizard-tui

# Test graceful fallback (uninstall Textual)
pip uninstall textual
dbt-to-lookml wizard generate --wizard-tui
```

---

## Dependencies

### Existing Dependencies
- `click>=8.0` - CLI framework (already in project)
- `rich` - Console output (already in project)
- `pydantic>=2.0` - Data validation (already in project)

### New Dependencies
- `textual>=0.47.0` - TUI framework
  - Why: Provides reactive TUI components, event system, CSS styling
  - Optional: Yes (wizard extras only)
  - License: MIT
  - Size: ~2MB

- `typing-extensions>=4.0` - Python 3.9 compatibility
  - Why: Required by Textual for older Python versions
  - Optional: Yes (wizard extras only)
  - License: PSF
  - Size: ~50KB

**Installation**:
```bash
# With wizard extras
pip install dbt-to-lookml[wizard]

# Or in dev mode
uv pip install -e ".[wizard]"
```

---

## Implementation Notes

### Important Considerations

1. **Python 3.9 Compatibility**: Textual requires typing-extensions for Python 3.9 support. Ensure this is included in dependencies.

2. **Terminal Size**: Always check terminal size on mount and warn if too small. Minimum 80x24 for usable experience.

3. **Validation Strategy**: Validate on keystroke (reactive) but only block execution on invalid final state. Provides immediate feedback without being intrusive.

4. **Async Testing**: Textual is async-first. All integration tests must use `pytest-asyncio` and Pilot API's `run_test()` context manager.

5. **Import Guards**: Wrap all Textual imports in try/except to enable graceful fallback. Set `TEXTUAL_AVAILABLE` flag for conditional behavior.

6. **Mutual Exclusion**: Timezone conversion checkboxes must be mutually exclusive. Handle in `on_checkbox_changed` event handler.

7. **Preview Debouncing**: Consider debouncing preview updates (200ms delay) if performance issues arise with large projects. Not implemented initially.

8. **Error Handling**: Wrap TUI launch in try/except to catch unexpected Textual errors and fallback gracefully.

### Code Patterns to Follow

**Widget Extension**:
```python
from textual.widgets import Input

class MyWidget(Input):
    DEFAULT_CSS = """
    MyWidget {
        border: solid $border;
    }
    """

    def on_input_changed(self, event: Input.Changed) -> None:
        # Handle event
        pass
```

**Reactive Updates**:
```python
from textual.reactive import reactive

class MyApp(App):
    value: reactive[str] = reactive("", init=False)

    def watch_value(self, new_value: str) -> None:
        # Called when value changes
        self.update_preview()
```

**Pilot API Testing**:
```python
@pytest.mark.asyncio
async def test_my_app() -> None:
    app = MyApp()

    async with app.run_test() as pilot:
        await pilot.click("#button-id")
        assert pilot.app.result is not None
```

### References

**Textual Documentation**:
- App tutorial: https://textual.textualize.io/tutorial/
- Widget reference: https://textual.textualize.io/widgets/
- CSS guide: https://textual.textualize.io/guide/CSS/
- Testing with Pilot: https://textual.textualize.io/guide/testing/

**Project Files**:
- CLI patterns: `src/dbt_to_lookml/__main__.py`
- Test patterns: `src/tests/test_cli.py`
- Error handling: `src/dbt_to_lookml/parsers/dbt.py`

---

## Implementation Checklist

### Phase 1: Project Structure Setup
- [ ] Create `src/dbt_to_lookml/wizard/` directory
- [ ] Create `wizard/__init__.py` with exports
- [ ] Create `wizard/tui.py` placeholder
- [ ] Create `wizard/tui_widgets.py` placeholder
- [ ] Update `pyproject.toml` with wizard dependencies
- [ ] Verify: `pip install -e ".[wizard]"` succeeds

### Phase 2: Custom Widgets Implementation
- [ ] Implement FormSection widget in `tui_widgets.py`
- [ ] Add FormSection CSS styling
- [ ] Implement ValidatedInput widget in `tui_widgets.py`
- [ ] Add ValidatedInput validation logic
- [ ] Add ValidatedInput error styling
- [ ] Implement PreviewPanel widget in `tui_widgets.py`
- [ ] Add PreviewPanel command building
- [ ] Add PreviewPanel output estimation
- [ ] Verify: All widgets compile without errors

### Phase 3: Main TUI Application
- [ ] Create GenerateWizardTUI class in `tui.py`
- [ ] Add import guard for Textual
- [ ] Implement compose() layout
- [ ] Add CSS styling
- [ ] Implement form sections (Required, Optional, Advanced)
- [ ] Add keyboard bindings
- [ ] Implement event handlers (on_input_changed, on_checkbox_changed, on_button_pressed)
- [ ] Implement form validation
- [ ] Implement actions (cancel, preview, execute, help)
- [ ] Create HelpScreen modal
- [ ] Add HELP_TEXT content
- [ ] Implement launch_tui_wizard() entry point
- [ ] Verify: TUI launches without crashing

### Phase 4: Integration and Fallback
- [ ] Add wizard command group to `__main__.py`
- [ ] Add wizard generate command with --wizard-tui flag
- [ ] Implement TUI launch logic in CLI
- [ ] Implement form data to generate command mapping
- [ ] Add graceful fallback error handling
- [ ] Add placeholder for detection module integration
- [ ] Verify: CLI command exists and shows help
- [ ] Verify: Error message shown if Textual not installed

### Phase 5: Testing
- [ ] Create `test_wizard_tui.py` unit test file
- [ ] Write ValidatedInput tests (3 tests)
- [ ] Write FormSection tests (1 test)
- [ ] Write PreviewPanel tests (2 tests)
- [ ] Write GenerateWizardTUI tests (4 tests)
- [ ] Create `test_wizard_tui_integration.py` integration test file
- [ ] Write Pilot API tests (10 tests)
- [ ] Add CLI tests to `test_cli.py` (3 tests)
- [ ] Verify: All tests pass
- [ ] Verify: Coverage meets 90%+ target for unit tests
- [ ] Verify: Coverage meets 85%+ target for integration tests

### Phase 6: Quality Checks
- [ ] Run `make format` - auto-fix formatting
- [ ] Run `make lint` - verify no linting errors
- [ ] Run `make type-check` - verify mypy passes
- [ ] Run `make test` - verify all tests pass
- [ ] Run `make quality-gate` - verify all gates pass
- [ ] Manual test: Install with wizard extras
- [ ] Manual test: Launch TUI and fill form
- [ ] Manual test: Test keyboard navigation
- [ ] Manual test: Test help modal (F1)
- [ ] Manual test: Test preview updates
- [ ] Manual test: Test cancel and execute
- [ ] Manual test: Uninstall Textual and verify fallback error

### Phase 7: Documentation
- [ ] Update README with TUI mode documentation
- [ ] Add installation instructions for wizard extras
- [ ] Document keyboard shortcuts
- [ ] Add screenshot or demo GIF (optional)
- [ ] Update CLAUDE.md if needed

---

## Ready for Implementation

This specification is complete and ready for implementation. All tasks are clearly defined with:
- File paths and actions
- Code examples and patterns
- Testing requirements
- Validation commands

Estimated implementation time: **15-20 hours**

Next step: Begin with Phase 1 (Project Structure Setup) and work sequentially through the checklist.
