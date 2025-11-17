"""Type definitions for wizard system."""

from enum import Enum
from typing import Any, Protocol


class WizardMode(Enum):
    """Wizard interaction modes."""

    PROMPT = "prompt"  # Simple prompt-based wizard
    TUI = "tui"  # Full-screen Textual TUI


class WizardStep(Protocol):
    """Protocol for wizard step implementations."""

    def validate(self) -> tuple[bool, str]:
        """Validate step input.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is empty string if valid.
        """
        ...

    def get_summary(self) -> str:
        """Get summary of step configuration.

        Returns:
            Human-readable summary string.
        """
        ...


# Type alias for wizard configuration
WizardConfig = dict[str, Any]
