"""Custom Click help formatter with Rich integration.

This module provides a custom Click command class that uses standard
Click formatting (no Rich rendering to avoid formatting issues).
"""

from __future__ import annotations

import click


class RichCommand(click.Command):
    """Custom Click command with enhanced help formatting.

    Uses standard Click formatting with improved width for readability.
    """

    def get_help(self, ctx: click.Context) -> str:
        """Get help text for command.

        Args:
            ctx: Click context

        Returns:
            Formatted help text
        """
        formatter = click.HelpFormatter(width=88)
        self.format_help(ctx, formatter)
        return formatter.getvalue()


class RichGroup(click.Group):
    """Custom Click group with enhanced help formatting.

    Uses standard Click formatting with improved width for readability.
    """

    def get_help(self, ctx: click.Context) -> str:
        """Get help text for group.

        Args:
            ctx: Click context

        Returns:
            Formatted help text
        """
        formatter = click.HelpFormatter(width=88)
        self.format_help(ctx, formatter)
        return formatter.getvalue()
