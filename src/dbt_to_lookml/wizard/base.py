"""Base wizard class for all interactive wizards."""

from abc import ABC, abstractmethod

from rich.console import Console

from dbt_to_lookml.wizard.types import WizardConfig, WizardMode

console = Console()


class BaseWizard(ABC):
    """Base class for all wizard implementations.

    Provides common functionality:
    - Mode detection (prompt vs TUI)
    - Configuration validation
    - Summary generation
    - Error handling
    """

    def __init__(self, mode: WizardMode = WizardMode.PROMPT) -> None:
        """Initialize the wizard.

        Args:
            mode: Wizard interaction mode (prompt or TUI).
        """
        self.mode = mode
        self.config: WizardConfig = {}

    @abstractmethod
    def run(self) -> WizardConfig:
        """Run the wizard and collect configuration.

        Returns:
            Dictionary of configuration values collected from user.

        Raises:
            ValueError: If wizard is cancelled or invalid input provided.
        """
        pass

    @abstractmethod
    def validate_config(self, config: WizardConfig) -> tuple[bool, str]:
        """Validate wizard configuration.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is empty string if valid.
        """
        pass

    def get_summary(self) -> str:
        """Get summary of wizard configuration.

        Returns:
            Human-readable summary of configuration.
        """
        if not self.config:
            return "[dim]No configuration collected yet[/dim]"

        lines = ["[bold]Wizard Configuration:[/bold]"]
        for key, value in self.config.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def check_tui_available(self) -> bool:
        """Check if Textual TUI mode is available.

        Returns:
            True if Textual is installed and TUI mode can be used.
        """
        try:
            import textual  # noqa: F401

            return True
        except ImportError:
            return False

    def handle_tui_unavailable(self) -> None:
        """Handle graceful degradation when TUI is not available."""
        console.print(
            "[yellow]Warning: Textual TUI not available. "
            "Install with: pip install dbt-to-lookml[tui][/yellow]"
        )
        console.print("[dim]Falling back to prompt-based wizard...[/dim]")
        self.mode = WizardMode.PROMPT
