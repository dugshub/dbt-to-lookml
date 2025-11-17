"""Custom Click help formatter with Rich integration.

This module provides a custom Click command class and help formatter
that integrates Rich components for enhanced visual presentation.
"""

from __future__ import annotations

from io import StringIO
from typing import Any

import click
from rich.console import Console

from dbt_to_lookml.cli.formatting import (
    create_example_panel,
    create_options_table,
)


class RichHelpFormatter(click.HelpFormatter):
    """Custom help formatter using Rich for enhanced output.

    Extends Click's HelpFormatter to support Rich components like
    panels and tables for better visual presentation.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize formatter with Rich support."""
        super().__init__(*args, **kwargs)
        self.examples: list[tuple[str, str]] = []
        self.options_data: list[tuple[str, str, str, bool]] = []

    def add_examples(self, examples: list[tuple[str, str]]) -> None:
        """Add examples to help output.

        Args:
            examples: List of (description, code) tuples
        """
        self.examples = examples

    def add_options_table(self, options: list[tuple[str, str, str, bool]]) -> None:
        """Add options table to help output.

        Args:
            options: List of (name, short_flag, description, required) tuples
        """
        self.options_data = options

    def getvalue(self) -> str:
        """Get formatted help text with Rich components.

        Returns:
            Formatted help text string
        """
        # Get base help text from parent
        base_output = super().getvalue()

        # Create output buffer for Rich rendering
        output_buffer = StringIO()
        console = Console(file=output_buffer, width=80, force_terminal=True)

        # Print base help text
        console.print(base_output, soft_wrap=True)

        # Add examples if provided
        if self.examples:
            console.print()
            panel = create_example_panel("Examples", self.examples)
            console.print(panel)

        # Add options table if provided
        if self.options_data:
            console.print()
            table = create_options_table(self.options_data)
            console.print(table)

        return output_buffer.getvalue()


class RichCommand(click.Command):
    """Custom Click command using RichHelpFormatter.

    This command class automatically formats help text using Rich
    components, providing a more visually appealing CLI interface.
    """

    def get_help(self, ctx: click.Context) -> str:
        """Get help text for command.

        Args:
            ctx: Click context

        Returns:
            Formatted help text
        """
        formatter = RichHelpFormatter(width=80)
        self.format_help(ctx, formatter)
        return formatter.getvalue()

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format help text including examples and options.

        Args:
            ctx: Click context
            formatter: Help formatter instance
        """
        # Call parent to set up base help
        super().format_help(ctx, formatter)

        # Extract options from parameters for display
        if isinstance(formatter, RichHelpFormatter):
            options_list: list[tuple[str, str, str, bool]] = []

            for param in self.get_params(ctx):
                if isinstance(param, click.Option):
                    # Get option name and short flag
                    option_names = param.opts
                    option_name = option_names[0] if option_names else ""
                    short_flag = option_names[1] if len(option_names) > 1 else ""

                    # Get description (help text)
                    description = param.help or ""

                    # Check if required
                    is_required = param.required

                    options_list.append(
                        (option_name, short_flag, description, is_required)
                    )

            # Add options table if there are options
            if options_list:
                formatter.add_options_table(options_list)
