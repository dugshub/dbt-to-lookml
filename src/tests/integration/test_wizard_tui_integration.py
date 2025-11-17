"""Integration tests for wizard TUI using Textual Pilot API."""

import pytest

# Skip all tests if Textual not available
pytest.importorskip("textual")

from dbt_to_lookml.wizard.tui import GenerateWizardTUI


@pytest.mark.integration
@pytest.mark.wizard
class TestWizardTUIIntegration:
    """Integration tests for TUI wizard."""

    @pytest.mark.asyncio
    async def test_tui_app_initialization(self) -> None:
        """Test TUI app can be initialized."""
        app = GenerateWizardTUI()

        async with app.run_test(size=(120, 40)) as pilot:
            # Verify app is running
            assert pilot.app is not None
            assert pilot.app.result is None

    @pytest.mark.asyncio
    async def test_tui_form_field_access(self) -> None:
        """Test accessing form fields in TUI."""
        app = GenerateWizardTUI()

        async with app.run_test(size=(120, 40)) as pilot:
            # Verify we can access form fields
            input_dir = pilot.app.query_one("#input-dir")
            assert input_dir is not None

            output_dir = pilot.app.query_one("#output-dir")
            assert output_dir is not None

            schema = pilot.app.query_one("#schema")
            assert schema is not None

    @pytest.mark.asyncio
    async def test_tui_preview_panel_exists(self) -> None:
        """Test that preview panel exists."""
        app = GenerateWizardTUI()

        async with app.run_test(size=(120, 40)) as pilot:
            # Verify preview panel exists
            preview_panel = pilot.app.query_one("#preview-panel")
            assert preview_panel is not None

    @pytest.mark.asyncio
    async def test_tui_keyboard_escape(self) -> None:
        """Test keyboard escape navigation."""
        app = GenerateWizardTUI()

        async with app.run_test(size=(120, 40)) as pilot:
            # Start at first field, press escape to cancel
            await pilot.press("escape")

            # App should exit with no result
            assert app.result is None

    @pytest.mark.asyncio
    async def test_tui_keyboard_tab(self) -> None:
        """Test keyboard tab navigation."""
        app = GenerateWizardTUI()

        async with app.run_test(size=(120, 40)) as pilot:
            # Press tab to navigate
            await pilot.press("tab")

            # Verify app is still running
            assert pilot.app.screen is not None
