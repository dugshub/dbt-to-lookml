"""CLI utilities for semantic-patterns.

This package provides Rich-based formatting utilities and custom Click
help formatters for consistent, visually appealing CLI output.
"""

from __future__ import annotations

from semantic_patterns.cli.formatting import (
    format_error,
    format_success,
    format_warning,
)
from semantic_patterns.cli.help_formatter import RichCommand, RichGroup

__all__ = [
    "format_error",
    "format_success",
    "format_warning",
    "RichCommand",
    "RichGroup",
]
