"""Interactive wizard system for dbt-to-lookml CLI.

This module provides prompt-based and TUI-based wizards for guiding users
through configuration and command building.
"""

from typing import Any, Optional

from dbt_to_lookml.wizard.base import BaseWizard
from dbt_to_lookml.wizard.detection import (
    DetectionResult,
    ProjectDetector,
)

__all__ = [
    "BaseWizard",
    "DetectionResult",
    "ProjectDetector",
    "launch_tui_wizard",
]


def launch_tui_wizard(
    defaults: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Launch TUI wizard for generate command.

    Args:
        defaults: Default values for form fields from project detection

    Returns:
        Form data dict if user executes, None if cancelled

    Raises:
        ImportError: If Textual library is not installed
    """
    from dbt_to_lookml.wizard.tui import launch_tui_wizard as _launch

    return _launch(defaults)
