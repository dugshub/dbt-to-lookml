"""Rich formatting utilities for CLI output.

This module provides reusable Rich components for consistent visual
formatting across CLI commands, including syntax highlighting, panels,
tables, and formatted error/warning/success messages.
"""

from __future__ import annotations

from collections.abc import Sequence

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

console = Console()


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


def create_example_panel(
    title: str,
    examples: Sequence[tuple[str, str]],
    width: int = 78,
) -> Panel:
    """Create panel with code examples.

    Args:
        title: Panel title
        examples: Sequence of (description, code) tuples
        width: Panel width in characters

    Returns:
        Panel containing formatted examples
    """
    content_lines: list[str] = []

    for i, (description, code) in enumerate(examples):
        # Add description in bold cyan
        content_lines.append(f"[bold cyan]{description}:[/bold cyan]")

        # Add syntax-highlighted code
        syntax_obj = syntax_highlight_bash(code)
        content_lines.append(str(syntax_obj))

        # Add blank line between examples (except after last one)
        if i < len(examples) - 1:
            content_lines.append("")

    content_text = "\n".join(content_lines)

    return Panel(
        content_text,
        title=title,
        border_style="blue",
        width=width,
        expand=False,
    )


def create_options_table(options: Sequence[tuple[str, str, str, bool]]) -> Table:
    """Create table showing command options.

    Args:
        options: Sequence of (option_name, short_flag, description, required) tuples

    Returns:
        Table with formatted options
    """
    table = Table(
        title="Options",
        border_style="blue",
        width=78,
        show_header=True,
    )

    table.add_column("Option", style="cyan", width=20)
    table.add_column("Short", style="cyan", width=10)
    table.add_column("Description", width=35)
    table.add_column("Required", width=10)

    for option_name, short_flag, description, required in options:
        required_style = "red" if required else "dim"
        required_text = Text("Yes" if required else "No", style=required_style)

        table.add_row(
            option_name,
            short_flag or "-",
            description,
            required_text,
        )

    return table


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
