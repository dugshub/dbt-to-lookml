"""CLI utility functions for semantic-patterns."""

from __future__ import annotations

from pathlib import Path

from rich.tree import Tree


def build_file_tree(files: list[Path], project_path: Path) -> Tree:
    """Build a Rich Tree from generated file paths.

    Args:
        files: List of file paths to display
        project_path: Base project path for relative path calculation

    Returns:
        Rich Tree object for display
    """
    tree = Tree(f"[bold]{project_path.name}/[/bold]")
    nodes: dict[str, Tree] = {}

    for f in sorted(files):
        try:
            rel = f.relative_to(project_path)
        except ValueError:
            continue

        parts = rel.parts
        parent = tree

        # Build directory nodes
        for i, part in enumerate(parts[:-1]):
            key = "/".join(parts[: i + 1])
            if key not in nodes:
                nodes[key] = parent.add(f"[blue]{part}/[/blue]")
            parent = nodes[key]

        # Add file with color based on type
        fname = parts[-1]
        if ".explore.lkml" in fname:
            parent.add(f"[yellow]{fname}[/yellow]")
        elif ".model.lkml" in fname:
            parent.add(f"[magenta]{fname}[/magenta]")
        else:
            parent.add(f"[green]{fname}[/green]")

    return tree
