"""Unit tests for wizard base functionality."""

from typing import Any

import pytest

from dbt_to_lookml.wizard.base import BaseWizard
from dbt_to_lookml.wizard.types import WizardMode


class TestBaseWizard:
    """Test suite for BaseWizard class."""

    def test_init_default_mode(self) -> None:
        """Test wizard initializes with default prompt mode."""

        class MinimalWizard(BaseWizard):
            def run(self) -> dict[str, Any]:
                return {}

            def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
                return (True, "")

        wizard = MinimalWizard()
        assert wizard.mode == WizardMode.PROMPT
        assert wizard.config == {}

    def test_init_with_tui_mode(self) -> None:
        """Test wizard initializes with TUI mode."""

        class MinimalWizard(BaseWizard):
            def run(self) -> dict[str, Any]:
                return {}

            def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
                return (True, "")

        wizard = MinimalWizard(mode=WizardMode.TUI)
        assert wizard.mode == WizardMode.TUI

    def test_get_summary_empty_config(self) -> None:
        """Test summary generation with empty config."""

        class MinimalWizard(BaseWizard):
            def run(self) -> dict[str, Any]:
                return {}

            def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
                return (True, "")

        wizard = MinimalWizard()
        summary = wizard.get_summary()
        assert "No configuration collected yet" in summary

    def test_get_summary_with_config(self) -> None:
        """Test summary generation with configuration."""

        class MinimalWizard(BaseWizard):
            def run(self) -> dict[str, Any]:
                return {}

            def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
                return (True, "")

        wizard = MinimalWizard()
        wizard.config = {"input_dir": "semantic_models/", "output_dir": "build/"}
        summary = wizard.get_summary()

        assert "Wizard Configuration" in summary
        assert "input_dir: semantic_models/" in summary
        assert "output_dir: build/" in summary

    def test_check_tui_available_when_installed(self) -> None:
        """Test TUI availability check when Textual is installed."""

        class MinimalWizard(BaseWizard):
            def run(self) -> dict[str, Any]:
                return {}

            def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
                return (True, "")

        wizard = MinimalWizard()

        # This test will pass if Textual is installed, fail otherwise
        # In CI/dev environments with [tui] extra, should pass
        try:
            import textual  # noqa: F401

            assert wizard.check_tui_available() is True
        except ImportError:
            assert wizard.check_tui_available() is False

    def test_handle_tui_unavailable_falls_back_to_prompt(self) -> None:
        """Test graceful degradation from TUI to prompt mode."""

        class MinimalWizard(BaseWizard):
            def run(self) -> dict[str, Any]:
                return {}

            def validate_config(self, config: dict[str, Any]) -> tuple[bool, str]:
                return (True, "")

        wizard = MinimalWizard(mode=WizardMode.TUI)
        assert wizard.mode == WizardMode.TUI

        wizard.handle_tui_unavailable()
        assert wizard.mode == WizardMode.PROMPT

    def test_abstract_methods_must_be_implemented(self) -> None:
        """Test that BaseWizard cannot be instantiated without abstract methods."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseWizard()  # type: ignore[abstract]
