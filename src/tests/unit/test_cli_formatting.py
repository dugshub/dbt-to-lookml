"""Unit tests for CLI formatting utilities."""

from collections.abc import Sequence

from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from dbt_to_lookml.cli.formatting import (
    create_example_panel,
    create_options_table,
    format_error,
    format_success,
    format_warning,
    syntax_highlight_bash,
)


class TestSyntaxHighlighting:
    """Test syntax highlighting functions."""

    def test_syntax_highlight_bash_basic(self) -> None:
        """Test basic bash syntax highlighting."""
        code = "ls -la /tmp"
        result = syntax_highlight_bash(code)

        assert isinstance(result, Syntax)
        # Syntax object stores code in its code attribute
        assert result.code == code

    def test_syntax_highlight_bash_with_line_numbers(self) -> None:
        """Test bash syntax highlighting with line numbers."""
        code = "echo 'hello'\necho 'world'"
        result = syntax_highlight_bash(code, line_numbers=True)

        assert isinstance(result, Syntax)
        assert result.line_numbers is True

    def test_syntax_highlight_bash_multiline(self) -> None:
        """Test multiline bash code with backslashes."""
        code = "dbt-to-lookml generate -i models/ \\\n  -o lookml/ -s prod"
        result = syntax_highlight_bash(code)

        assert isinstance(result, Syntax)

    def test_empty_code_highlighting(self) -> None:
        """Test syntax highlighting with empty code."""
        result = syntax_highlight_bash("")

        assert isinstance(result, Syntax)


class TestExamplePanel:
    """Test example panel creation."""

    def test_create_example_panel_single_example(self) -> None:
        """Test creating panel with single example."""
        examples: Sequence[tuple[str, str]] = [("Basic usage", "command --flag value")]
        result = create_example_panel("Examples", examples)

        assert isinstance(result, Panel)

    def test_create_example_panel_multiple_examples(self) -> None:
        """Test creating panel with multiple examples."""
        examples: Sequence[tuple[str, str]] = [
            ("Basic usage", "command --flag value"),
            ("Advanced usage", "command --flag1 value1 --flag2 value2"),
        ]
        result = create_example_panel("Examples", examples)

        assert isinstance(result, Panel)

    def test_create_example_panel_custom_width(self) -> None:
        """Test creating panel with custom width."""
        examples: Sequence[tuple[str, str]] = [("Example", "command")]
        result = create_example_panel("Examples", examples, width=60)

        assert isinstance(result, Panel)


class TestOptionsTable:
    """Test options table creation."""

    def test_create_options_table_basic(self) -> None:
        """Test creating basic options table."""
        options: Sequence[tuple[str, str, str, bool]] = [
            ("--input-dir", "-i", "Input directory", True),
            ("--output-dir", "-o", "Output directory", True),
            ("--dry-run", "", "Preview without writing", False),
        ]
        result = create_options_table(options)

        assert isinstance(result, Table)

    def test_create_options_table_required_flags(self) -> None:
        """Test options table with required/optional distinction."""
        options: Sequence[tuple[str, str, str, bool]] = [
            ("--required-opt", "-r", "Required option", True),
            ("--optional-opt", "-o", "Optional option", False),
        ]
        result = create_options_table(options)

        assert isinstance(result, Table)

    def test_create_options_table_empty(self) -> None:
        """Test creating options table with empty options."""
        options: Sequence[tuple[str, str, str, bool]] = []
        result = create_options_table(options)

        assert isinstance(result, Table)


class TestMessageFormatting:
    """Test message formatting functions."""

    def test_format_error_basic(self) -> None:
        """Test error formatting without context."""
        result = format_error("Something went wrong")

        assert isinstance(result, Panel)

    def test_format_error_with_context(self) -> None:
        """Test error formatting with context."""
        result = format_error(
            "Invalid path",
            context="Make sure the directory exists",
        )

        assert isinstance(result, Panel)

    def test_format_warning_basic(self) -> None:
        """Test warning formatting without context."""
        result = format_warning("This is a warning")

        assert isinstance(result, Panel)

    def test_format_warning_with_context(self) -> None:
        """Test warning formatting with context."""
        result = format_warning(
            "Deprecated option used",
            context="Use --new-option instead",
        )

        assert isinstance(result, Panel)

    def test_format_success_basic(self) -> None:
        """Test success formatting without details."""
        result = format_success("Operation completed")

        assert isinstance(result, Panel)

    def test_format_success_with_details(self) -> None:
        """Test success formatting with details."""
        result = format_success(
            "Files generated successfully",
            details="Generated 5 files in /output/",
        )

        assert isinstance(result, Panel)


class TestFormattingEdgeCases:
    """Test edge cases in formatting functions."""

    def test_empty_code_highlighting_edge_case(self) -> None:
        """Test highlighting empty code string."""
        result = syntax_highlight_bash("")

        assert isinstance(result, Syntax)

    def test_long_code_highlighting(self) -> None:
        """Test highlighting very long code."""
        long_code = "echo 'hello' && " * 100
        result = syntax_highlight_bash(long_code)

        assert isinstance(result, Syntax)

    def test_special_characters_in_messages(self) -> None:
        """Test messages with special characters."""
        result = format_error(
            "Error with [brackets] and /slashes/",
            context="Context with $variables and @symbols",
        )

        assert isinstance(result, Panel)

    def test_unicode_in_messages(self) -> None:
        """Test messages with unicode characters."""
        result = format_success(
            "Success with emoji: ✓",
            details="Details with unicode: ü ö ä",
        )

        assert isinstance(result, Panel)
