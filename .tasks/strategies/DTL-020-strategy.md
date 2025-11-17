# Implementation Strategy: DTL-020

**Issue**: DTL-020 - Implement optional TUI wizard mode with Textual
**Analyzed**: 2025-11-12T21:00:00Z
**Stack**: backend
**Type**: feature

## Approach

Create a full-featured Text User Interface (TUI) using the Textual library, providing a rich interactive experience for the `dbt-to-lookml generate` command. The TUI will feature form-based input with live preview, keyboard navigation, and contextual help, while maintaining graceful fallback behavior if Textual is not installed. This implementation builds on the prompt-based wizard (DTL-018) by offering a more sophisticated visual interface for users who prefer GUI-like interactions in the terminal.

## Architecture Impact

**Layer**: CLI / User Interface Layer (builds on DTL-015 wizard infrastructure)

**New Files**:
- `src/dbt_to_lookml/wizard/tui.py` - Main Textual application and screens
- `src/dbt_to_lookml/wizard/tui_widgets.py` - Custom Textual widgets (forms, preview panel)
- `src/tests/unit/test_wizard_tui.py` - Unit tests for TUI components
- `src/tests/integration/test_wizard_tui_integration.py` - Integration tests for full TUI workflow

**Modified Files**:
- `src/dbt_to_lookml/__main__.py` - Add `--wizard-tui` flag to wizard generate command
- `src/dbt_to_lookml/wizard/__init__.py` - Export TUI launcher function
- `pyproject.toml` - Add Textual as optional dependency in `[project.optional-dependencies]`

## Dependencies

**Depends on**:
- DTL-015: Wizard dependencies and base infrastructure (wizard module must exist)
- DTL-017: Contextual project detection (for smart defaults in TUI)
- DTL-018: Prompt-based wizard (TUI reuses same command building logic)

**External Dependencies**:
- `textual>=0.47.0` - Modern TUI framework with reactive widgets
- `typing-extensions>=4.0` - For Python 3.9 compatibility with Textual

**Packages**:
- Add to `pyproject.toml` under `[project.optional-dependencies]`:
  ```toml
  wizard = [
      "textual>=0.47.0",
      "typing-extensions>=4.0",
  ]
  ```
- Installation: `pip install dbt-to-lookml[wizard]` or `uv pip install -e ".[wizard]"`
- Graceful degradation: Import guarded by try/except, friendly error if not installed

## Detailed Implementation Plan

### 1. Create TUI Application Structure (tui.py)

**Core Textual App Class**: `GenerateWizardTUI(App)`

```python
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Input, Checkbox, Button
from textual.binding import Binding
from textual.screen import Screen

class GenerateWizardTUI(App):
    """Textual TUI for dbt-to-lookml generate command wizard.

    Layout:
    ┌─ Header ────────────────────────────────────────────┐
    ├─ Main Content ──────────────────┬─ Preview Panel ───┤
    │ Required Fields Section         │ Command Preview    │
    │   Input Directory: [_________]  │ Output Preview     │
    │   Output Directory: [________]  │                    │
    │   Schema Name: [_____________]  │                    │
    │                                 │                    │
    │ Optional Prefixes Section       │                    │
    │   View Prefix: [_____________]  │                    │
    │   Explore Prefix: [__________]  │                    │
    │                                 │                    │
    │ Advanced Options Section        │                    │
    │   ☐ Dry Run    ☐ Skip Valid.   │                    │
    │   ☐ Convert TZ ☐ Show Summary  │                    │
    │                                 │                    │
    │ [Cancel]  [Preview]  [Execute]  │                    │
    └─────────────────────────────────┴────────────────────┘
    ├─ Footer (Help/Shortcuts) ───────────────────────────┤
    """

    CSS = """
    # Custom styling for form layout
    # Split screen with 70/30 ratio
    # Focus highlighting, validation errors
    """

    BINDINGS = [
        Binding("f1", "help", "Help"),
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+p", "preview", "Preview"),
        Binding("ctrl+enter", "execute", "Execute"),
    ]
```

**Key Components**:
1. **Header**: App title and status
2. **MainForm**: Left panel with input fields organized by sections
3. **PreviewPanel**: Right panel with live command/output preview
4. **Footer**: Keyboard shortcuts and help text

### 2. Create Custom Widgets (tui_widgets.py)

**FormSection Widget**: Groups related fields with title

```python
class FormSection(Container):
    """Container for a group of form fields with section title."""

    def __init__(self, title: str, *children, **kwargs):
        super().__init__(*children, **kwargs)
        self.title = title

    def compose(self) -> ComposeResult:
        yield Static(self.title, classes="section-title")
        yield from self.children
```

**ValidatedInput Widget**: Input with real-time validation

```python
class ValidatedInput(Input):
    """Input field with validation feedback.

    Attributes:
        validator: Callable that returns None if valid, error message if invalid
        required: Whether field is required (non-empty)
    """

    def __init__(
        self,
        placeholder: str = "",
        validator: Callable[[str], str | None] | None = None,
        required: bool = False,
        **kwargs
    ):
        super().__init__(placeholder=placeholder, **kwargs)
        self.validator = validator
        self.required = required

    def validate(self, value: str) -> str | None:
        """Return error message or None if valid."""
        if self.required and not value.strip():
            return "This field is required"
        if self.validator:
            return self.validator(value)
        return None

    def on_input_changed(self, event: Input.Changed) -> None:
        """Validate on every keystroke and update UI."""
        error = self.validate(event.value)
        if error:
            self.add_class("error")
            self.set_class(error, "error-message")
        else:
            self.remove_class("error")
```

**PreviewPanel Widget**: Live-updating preview of command and output

```python
class PreviewPanel(Container):
    """Right-side panel showing command preview and estimated output."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.command_text = Static("", id="command-preview")
        self.output_text = Static("", id="output-preview")

    def compose(self) -> ComposeResult:
        yield Static("Command Preview", classes="panel-title")
        yield self.command_text
        yield Static("Estimated Output", classes="panel-title")
        yield self.output_text

    def update_preview(self, form_data: dict[str, Any]) -> None:
        """Update preview based on current form values."""
        cmd = self._build_command(form_data)
        self.command_text.update(cmd)

        # Estimate output using project detection
        output = self._estimate_output(form_data)
        self.output_text.update(output)
```

### 3. Form Layout and Sections

**Three-section form structure**:

1. **Required Fields Section**:
   - Input Directory (ValidatedInput with path validation)
   - Output Directory (ValidatedInput with path validation)
   - Schema Name (ValidatedInput, required)

2. **Optional Prefixes Section**:
   - View Prefix (Input, optional)
   - Explore Prefix (Input, optional)
   - Connection Name (Input, default: "redshift_test")
   - Model Name (Input, default: "semantic_model")

3. **Advanced Options Section**:
   - Timezone Conversion (Radio buttons: Yes/No/Unset, default: Unset)
   - Dry Run (Checkbox)
   - Skip Validation (Checkbox)
   - Skip Formatting (Checkbox)
   - Show Summary (Checkbox)

**Action Buttons**:
- Cancel: Exit without executing
- Preview: Show full command in modal dialog
- Execute: Run the generated command

### 4. Live Preview Implementation

**Reactive Updates**: Use Textual's reactive properties to update preview panel

```python
class GenerateWizardTUI(App):
    # Reactive properties that trigger preview updates
    input_dir: reactive[str] = reactive("", init=False)
    output_dir: reactive[str] = reactive("", init=False)
    schema: reactive[str] = reactive("", init=False)
    # ... other form fields as reactive properties

    def watch_input_dir(self, value: str) -> None:
        """Called whenever input_dir changes."""
        self.update_preview()

    def watch_output_dir(self, value: str) -> None:
        """Called whenever output_dir changes."""
        self.update_preview()

    # ... watchers for all form fields

    def update_preview(self) -> None:
        """Update the preview panel with current form state."""
        form_data = self.get_form_data()
        preview_panel = self.query_one(PreviewPanel)
        preview_panel.update_preview(form_data)
```

**Command Building**: Reuse logic from prompt-based wizard (DTL-018)

```python
def build_command_from_form(self, form_data: dict[str, Any]) -> str:
    """Build CLI command string from form data.

    Reuses command builder from prompt wizard for consistency.
    """
    from dbt_to_lookml.wizard.generate_wizard import build_generate_command
    return build_generate_command(form_data)
```

**Output Estimation**: Use project detection to estimate generation results

```python
def estimate_output(self, input_dir: str) -> str:
    """Estimate number of views/explores that will be generated.

    Uses detection module (DTL-017) to scan semantic models.
    """
    from dbt_to_lookml.wizard.detection import detect_semantic_models

    try:
        model_count = detect_semantic_models(input_dir)
        return f"• {model_count} views\n• 1 explore\n• 1 model file"
    except Exception as e:
        return f"Unable to estimate: {e}"
```

### 5. Keyboard Navigation

**Tab Order**: Logical flow through form fields

```python
class GenerateWizardTUI(App):
    def on_mount(self) -> None:
        """Set up focus chain on app startup."""
        # Focus first input field
        self.query_one("#input-dir-field").focus()

    def action_next_field(self) -> None:
        """Move to next input field (Tab)."""
        focused = self.focused
        if focused:
            # Get next focusable widget in tab order
            next_widget = self._get_next_focusable(focused)
            if next_widget:
                next_widget.focus()

    def action_prev_field(self) -> None:
        """Move to previous input field (Shift+Tab)."""
        focused = self.focused
        if focused:
            prev_widget = self._get_prev_focusable(focused)
            if prev_widget:
                prev_widget.focus()
```

**Keyboard Shortcuts**:
- `Tab`: Next field
- `Shift+Tab`: Previous field
- `Arrow keys`: Navigate within field
- `Enter`: Submit (on buttons) or next field (on inputs)
- `Space`: Toggle checkbox
- `F1`: Show help modal
- `Ctrl+P`: Preview command
- `Ctrl+Enter`: Execute command
- `Escape`: Cancel
- `Ctrl+C`: Quit

### 6. Help System

**F1 Help Modal**: Context-sensitive help screen

```python
class HelpScreen(Screen):
    """Modal help screen with keyboard shortcuts and field descriptions."""

    BINDINGS = [
        Binding("escape", "pop_screen", "Close"),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Help & Keyboard Shortcuts", classes="help-title"),
            Static(HELP_TEXT, classes="help-content"),
            Button("Close", variant="primary", id="close-help"),
            classes="help-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-help":
            self.app.pop_screen()

HELP_TEXT = """
[bold]Keyboard Shortcuts:[/bold]
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
  Convert TZ         Enable timezone conversion for time dimensions
  Advanced Options   Control validation, formatting, dry-run
"""
```

**Inline Help**: Tooltip-like help for each field

```python
class FieldWithHelp(Container):
    """Input field with inline help text."""

    def __init__(self, label: str, help_text: str, input_widget: Widget, **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.help_text = help_text
        self.input_widget = input_widget

    def compose(self) -> ComposeResult:
        yield Static(self.label, classes="field-label")
        yield self.input_widget
        yield Static(self.help_text, classes="field-help")
```

### 7. Graceful Fallback if Textual Not Installed

**Import Guard**: Check for Textual availability

```python
# src/dbt_to_lookml/wizard/tui.py
try:
    from textual.app import App
    from textual.widgets import Input, Button, Checkbox, Static
    from textual.containers import Container
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    App = object  # Dummy class for type hints

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
    result = app.run()
    return result
```

**CLI Error Handling**: Friendly error message

```python
# src/dbt_to_lookml/__main__.py
@wizard_group.command("generate")
@click.option("--wizard-tui", is_flag=True, help="Use TUI interface (requires textual)")
def wizard_generate(wizard_tui: bool) -> None:
    """Interactive wizard for generate command."""

    if wizard_tui:
        try:
            from dbt_to_lookml.wizard.tui import launch_tui_wizard

            # Get smart defaults from detection
            from dbt_to_lookml.wizard.detection import detect_defaults
            defaults = detect_defaults()

            # Launch TUI
            result = launch_tui_wizard(defaults)

            if result:
                # Execute the command
                execute_generate_command(result)
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
        # Use prompt-based wizard (DTL-018)
        from dbt_to_lookml.wizard.generate_wizard import prompt_wizard
        prompt_wizard()
```

### 8. Terminal Compatibility

**Minimum Size Check**: Ensure terminal is large enough

```python
class GenerateWizardTUI(App):
    MIN_WIDTH = 80
    MIN_HEIGHT = 24

    def on_mount(self) -> None:
        """Check terminal size on startup."""
        size = self.size
        if size.width < self.MIN_WIDTH or size.height < self.MIN_HEIGHT:
            self.push_screen(
                MessageScreen(
                    f"Terminal too small!\n\n"
                    f"Minimum: {self.MIN_WIDTH}x{self.MIN_HEIGHT}\n"
                    f"Current: {size.width}x{size.height}\n\n"
                    f"Please resize and try again."
                )
            )
```

**Responsive Layout**: Adapt to terminal size

```python
# CSS for responsive layout
CSS = """
Container {
    layout: horizontal;
}

#main-form {
    width: 70%;
    min-width: 50;
}

#preview-panel {
    width: 30%;
    min-width: 30;
}

/* Stack vertically on narrow terminals */
@media (max-width: 100) {
    Container {
        layout: vertical;
    }

    #main-form, #preview-panel {
        width: 100%;
    }
}
"""
```

### 9. Testing Strategy

**Unit Tests** (`test_wizard_tui.py`):

1. **test_tui_import_guard**:
   - Mock Textual as unavailable
   - Verify ImportError with helpful message

2. **test_form_validation**:
   - Test ValidatedInput with valid/invalid paths
   - Test required field validation
   - Test custom validators (path exists, schema format)

3. **test_command_building**:
   - Create TUI app with test data
   - Verify command string matches expected format
   - Test all optional flags combinations

4. **test_preview_updates**:
   - Change reactive properties
   - Verify preview panel updates correctly
   - Test output estimation logic

5. **test_keyboard_navigation**:
   - Simulate Tab/Shift+Tab keypresses
   - Verify focus moves to correct widget
   - Test all keyboard shortcuts (F1, Escape, Ctrl+P, etc.)

**Integration Tests** (`test_wizard_tui_integration.py`):

1. **test_tui_full_workflow**:
   - Launch TUI with pilot API (Textual's testing framework)
   - Fill in all required fields
   - Toggle optional checkboxes
   - Press Execute button
   - Verify command is executed with correct arguments

2. **test_tui_cancel**:
   - Launch TUI
   - Press Cancel button
   - Verify no command is executed

3. **test_tui_with_defaults**:
   - Launch TUI with pre-filled defaults from detection
   - Verify form fields show default values
   - Verify defaults can be edited

**Textual Pilot API Example**:

```python
import pytest
from textual.pilot import Pilot

@pytest.mark.asyncio
async def test_tui_full_workflow():
    """Test complete TUI workflow using pilot API."""
    app = GenerateWizardTUI()

    async with app.run_test() as pilot:
        # Fill in required fields
        await pilot.click("#input-dir-field")
        await pilot.press(*"semantic_models/")

        await pilot.click("#output-dir-field")
        await pilot.press(*"build/lookml/")

        await pilot.click("#schema-field")
        await pilot.press(*"prod_analytics")

        # Toggle dry-run checkbox
        await pilot.click("#dry-run-checkbox")

        # Preview command
        await pilot.press("ctrl+p")
        assert "dbt-to-lookml generate" in pilot.app.preview_text

        # Execute
        await pilot.click("#execute-button")

        # Verify result
        result = pilot.app.result
        assert result["input_dir"] == "semantic_models/"
        assert result["dry_run"] is True
```

**Coverage Target**: 90%+ for TUI module (lower than 95% due to UI testing complexity)

### 10. CSS Styling

**Visual Design**: Professional terminal UI with color scheme

```python
# src/dbt_to_lookml/wizard/tui.py
CSS = """
/* Global Styles */
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

/* Main Layout */
#main-container {
    layout: horizontal;
    height: 100%;
}

#main-form {
    width: 70%;
    padding: 1 2;
}

#preview-panel {
    width: 30%;
    background: $panel;
    padding: 1 2;
    border-left: solid $primary;
}

/* Form Sections */
.section-title {
    text-style: bold;
    color: $accent;
    margin: 1 0;
}

FormSection {
    margin: 1 0;
    padding: 1;
    border: solid $border;
}

/* Input Fields */
.field-label {
    color: $text;
    margin-bottom: 1;
}

.field-help {
    color: $text-muted;
    text-style: italic;
    margin-top: 1;
}

Input {
    margin: 1 0;
}

Input:focus {
    border: tall $accent;
}

Input.error {
    border: tall $error;
}

.error-message {
    color: $error;
    text-style: bold;
}

/* Checkboxes */
Checkbox {
    margin: 1 0;
}

/* Buttons */
Button {
    margin: 1 2;
}

Button:focus {
    text-style: bold reverse;
}

/* Preview Panel */
.panel-title {
    text-style: bold;
    color: $primary;
    margin: 1 0;
}

#command-preview {
    background: $surface-darken-1;
    padding: 1;
    border: solid $border;
    margin: 1 0;
}

#output-preview {
    background: $surface-darken-1;
    padding: 1;
    border: solid $border;
    margin: 1 0;
}

/* Help Modal */
.help-modal {
    align: center middle;
    background: $surface;
    border: thick $primary;
    width: 80;
    height: 30;
    padding: 2;
}

.help-title {
    text-style: bold;
    color: $primary;
    text-align: center;
    margin-bottom: 1;
}

.help-content {
    overflow-y: auto;
    height: 20;
}
"""
```

## Implementation Sequence

**Phase 1: Core TUI Structure (4 hours)**:
1. Create `tui.py` with basic App class and layout (1 hour)
2. Implement FormSection widget and three-section structure (1 hour)
3. Add ValidatedInput widget with real-time validation (1 hour)
4. Set up CSS styling and responsive layout (1 hour)

**Phase 2: Functionality (4 hours)**:
5. Implement PreviewPanel widget with command building (1.5 hours)
6. Add reactive properties and live preview updates (1 hour)
7. Implement keyboard navigation and shortcuts (1 hour)
8. Create help system (F1 modal and inline help) (0.5 hour)

**Phase 3: Integration (2 hours)**:
9. Add CLI integration with `--wizard-tui` flag (0.5 hour)
10. Implement graceful fallback for missing Textual (0.5 hour)
11. Connect to detection module for smart defaults (0.5 hour)
12. Connect to command execution logic (0.5 hour)

**Phase 4: Testing (4 hours)**:
13. Write unit tests for widgets and validation (2 hours)
14. Write integration tests with Pilot API (1.5 hours)
15. Test terminal compatibility (80x24, resize handling) (0.5 hour)

**Phase 5: Polish (1 hour)**:
16. Refine CSS and visual design (0.5 hour)
17. Add error handling and edge cases (0.5 hour)

**Total Estimated Time**: 15 hours

## Testing Strategy

### Unit Test Coverage

**File**: `src/tests/unit/test_wizard_tui.py`

Test cases:
1. `test_textual_import_available` - Verify Textual imports work
2. `test_textual_import_fallback` - Mock unavailable Textual, check error
3. `test_validated_input_required` - Test required field validation
4. `test_validated_input_path_validation` - Test path validator
5. `test_validated_input_custom_validator` - Test custom validation logic
6. `test_form_section_rendering` - Test FormSection widget composition
7. `test_preview_panel_command_building` - Test command string generation
8. `test_preview_panel_output_estimation` - Test output estimation
9. `test_keyboard_shortcuts_bindings` - Test all key bindings defined
10. `test_help_screen_content` - Test help modal content

### Integration Test Coverage

**File**: `src/tests/integration/test_wizard_tui_integration.py`

Test cases:
1. `test_tui_launch_and_cancel` - Launch TUI, press Cancel, verify exit
2. `test_tui_required_fields_only` - Fill required fields, execute
3. `test_tui_all_fields` - Fill all fields including optional, execute
4. `test_tui_validation_prevents_execution` - Invalid input blocks Execute
5. `test_tui_preview_updates_live` - Type in fields, verify preview updates
6. `test_tui_keyboard_navigation` - Tab through all fields
7. `test_tui_help_modal` - Press F1, verify help appears, close
8. `test_tui_with_smart_defaults` - Launch with detection defaults
9. `test_tui_terminal_size_warning` - Mock small terminal, verify warning
10. `test_tui_dry_run_execution` - Enable dry-run, verify no files written

### CLI Test Coverage

**File**: `src/tests/test_cli.py` (add to existing)

Test cases:
1. `test_wizard_tui_flag_textual_available` - Test `--wizard-tui` launches TUI
2. `test_wizard_tui_flag_textual_unavailable` - Test error if Textual missing
3. `test_wizard_tui_with_env_var` - Test `WIZARD_MODE=tui` env variable

### Coverage Target

- **Unit tests**: 90%+ branch coverage for TUI widgets
- **Integration tests**: 85%+ coverage for full TUI workflow
- **CLI tests**: 95%+ coverage for TUI flag handling

Lower targets for UI code due to Textual's internal complexity and async testing challenges.

## Open Questions

1. **Color Theme**: Should we use Textual's default theme or define custom colors?
   - *Recommendation*: Use Textual's default themes with minor customization for brand consistency

2. **Clipboard Support**: Should we copy the final command to clipboard?
   - *Recommendation*: Yes, use `pyperclip` (optional) if available, graceful fallback if not

3. **Field History**: Should we remember previous inputs across sessions?
   - *Recommendation*: Not in initial version (scope creep), consider for future enhancement

4. **Progress Indication**: Should we show progress bar during command execution?
   - *Recommendation*: Yes, use Textual's ProgressBar widget during execution

5. **Form Persistence**: Should we allow saving/loading form configurations?
   - *Recommendation*: Not in initial version, consider as separate issue

## Rollout Impact

**User Experience**:
- New optional install: `pip install dbt-to-lookml[wizard]`
- New CLI flag: `--wizard-tui` on `wizard generate` command
- Alternative to prompt-based wizard for users who prefer GUI-like interfaces
- Zero impact on existing CLI usage (completely opt-in)

**Documentation**:
- Update README with TUI mode documentation
- Add screenshots of TUI interface
- Document keyboard shortcuts and navigation
- Update installation instructions for wizard extras

**Dependencies**:
- Textual library added as optional dependency
- No impact on core functionality if not installed
- ~2MB additional package size if wizard extras installed

**Performance**:
- TUI startup: ~100-200ms (Textual initialization)
- No performance impact on command execution itself
- Preview updates: Real-time (reactive system)

## Notes for Implementation

1. **Textual Version Compatibility**: Pin to `textual>=0.47.0` for stability. Textual has a stable API since v0.40+, but newer versions have better performance.

2. **Async Testing**: Textual uses asyncio extensively. Use Pilot API for testing, which handles async properly:
   ```python
   async with app.run_test() as pilot:
       await pilot.click("#button-id")
   ```

3. **Widget IDs**: Use descriptive IDs for all interactive widgets to enable easy testing and CSS targeting.

4. **Validation Strategy**: Validate on every keystroke (reactive) but only block execution on invalid final state. This provides immediate feedback without being intrusive.

5. **Preview Debouncing**: Consider debouncing preview updates (e.g., 200ms delay) if performance becomes an issue with large projects.

6. **Error Handling**: Wrap all Textual operations in try/except to provide graceful fallback to prompt wizard if TUI fails unexpectedly.

7. **Accessibility**: Textual apps work with screen readers. Ensure all widgets have proper labels and roles.

8. **Cross-Platform Testing**: Textual works on Windows/Mac/Linux, but test on all platforms due to terminal differences.

## Estimated Complexity

**Complexity**: Medium-High

**Reasoning**:
- New library (Textual) with learning curve
- Complex UI state management with reactive properties
- Async testing requirements
- Multiple custom widgets to implement
- Integration with existing wizard infrastructure

**Estimated Time**: 15-20 hours

**Risk Factors**:
- Textual API changes (mitigated by pinning version)
- Terminal compatibility issues (mitigated by minimum size check)
- Async testing complexity (mitigated by using Pilot API)

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-020.md`
3. Change status from `refinement` to `strategy-approved`
4. Run: `/plan:spec DTL-020`
