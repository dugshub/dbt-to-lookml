"""Rich formatting utilities for CLI output.

This module provides reusable Rich components for consistent visual
formatting across CLI commands, including syntax highlighting, panels,
and formatted error/warning/success messages.
"""

from __future__ import annotations

from rich.panel import Panel
from rich.syntax import Syntax


def syntax_highlight_bash(code: str, line_numbers: bool = False) -> Syntax:
    """Create syntax-highlighted bash code block.

    Args:
        code: Bash code to highlight
        line_numbers: Whether to include line numbers

    Returns:
        Syntax object with bash highlighting
    """
    return Syntax(
        code,
        "bash",
        theme="monokai",
        line_numbers=line_numbers,
        background_color="default",
        word_wrap=True,
    )


def format_error(message: str, context: str | None = None) -> Panel:
    """Create formatted error panel.

    Args:
        message: Error message
        context: Optional context hint for resolution

    Returns:
        Panel with error formatting
    """
    content = f"[bold red]{message}[/bold red]"
    if context:
        content += f"\n\n[dim]{context}[/dim]"

    return Panel(
        content,
        title="[bold red]Error[/bold red]",
        border_style="red",
        width=78,
        expand=False,
    )


def format_warning(message: str, context: str | None = None) -> Panel:
    """Create formatted warning panel.

    Args:
        message: Warning message
        context: Optional additional information

    Returns:
        Panel with warning formatting
    """
    content = f"[bold yellow]{message}[/bold yellow]"
    if context:
        content += f"\n\n[dim]{context}[/dim]"

    return Panel(
        content,
        title="[bold yellow]Warning[/bold yellow]",
        border_style="yellow",
        width=78,
        expand=False,
    )


def format_success(message: str, details: str | None = None) -> Panel:
    """Create formatted success panel.

    Args:
        message: Success message
        details: Optional details about the result

    Returns:
        Panel with success formatting
    """
    content = f"[bold green]✓ {message}[/bold green]"
    if details:
        content += f"\n\n[dim]{details}[/dim]"

    return Panel(
        content,
        title="[bold green]Success[/bold green]",
        border_style="green",
        width=78,
        expand=False,
    )
