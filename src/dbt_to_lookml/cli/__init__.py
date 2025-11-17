"""CLI utilities for dbt-to-lookml.

This module provides Rich-based formatting utilities for the CLI,
including help text formatters, syntax highlighting, and structured displays.
"""

from dbt_to_lookml.cli.formatting import (
    create_example_panel,
    create_options_table,
    format_error,
    format_success,
    format_warning,
    syntax_highlight_bash,
)
from dbt_to_lookml.cli.help_formatter import RichCommand, RichHelpFormatter

__all__ = [
    "RichCommand",
    "RichHelpFormatter",
    "create_example_panel",
    "create_options_table",
    "format_error",
    "format_success",
    "format_warning",
    "syntax_highlight_bash",
]
