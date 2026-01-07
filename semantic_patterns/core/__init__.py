"""Core build functionality for semantic-patterns.

This module contains the main build logic extracted from the CLI,
allowing programmatic access to the build process.
"""

from semantic_patterns.core.builder import (
    BuildStatistics,
    generate_model_file_content,
    run_build,
)
from semantic_patterns.core.looker_push import handle_looker_push

__all__ = [
    "BuildStatistics",
    "generate_model_file_content",
    "handle_looker_push",
    "run_build",
]
