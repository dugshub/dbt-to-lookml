"""CLI commands for semantic-patterns.

This package contains all CLI command definitions, organized by functionality.
Commands are registered by importing them in __main__.py.
"""

from __future__ import annotations

from semantic_patterns.cli.commands.auth import auth
from semantic_patterns.cli.commands.build import build
from semantic_patterns.cli.commands.init_cmd import init
from semantic_patterns.cli.commands.validate import validate

__all__ = [
    "auth",
    "build",
    "init",
    "validate",
]
