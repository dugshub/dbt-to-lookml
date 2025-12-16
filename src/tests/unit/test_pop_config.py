"""Unit tests for PoP configuration schema."""

import pytest
from pydantic import ValidationError

from dbt_to_lookml.schemas.config import (
    PopComparison,
    PopConfig,
    PopGrain,
    PopWindow,
)


class TestPopGrain:
    """Tests for PopGrain enum."""

    def test_valid_grain_values(self) -> None:
        """Test all valid grain values."""
        assert PopGrain.SELECTED == "selected"
        assert PopGrain.MTD == "mtd"
        assert PopGrain.YTD == "ytd"

    def test_grain_from_string(self) -> None:
        """Test creating grain from string value."""
        assert PopGrain("mtd") == PopGrain.MTD


class TestPopComparison:
    """Tests for PopComparison enum."""

    def test_valid_comparison_values(self) -> None:
        """Test all valid comparison values."""
        assert PopComparison.PP == "pp"
        assert PopComparison.PY == "py"


class TestPopWindow:
    """Tests for PopWindow enum."""

    def test_valid_window_values(self) -> None:
        """Test all valid window values."""
        assert PopWindow.WEEK == "week"
        assert PopWindow.MONTH == "month"
        assert PopWindow.QUARTER == "quarter"


class TestPopConfig:
    """Tests for PopConfig model."""

    def test_minimal_config(self) -> None:
        """Test minimal valid PoP config with defaults."""
        config = PopConfig(enabled=True)

        assert config.enabled is True
        assert config.grains == [PopGrain.MTD, PopGrain.YTD]
        assert config.comparisons == [PopComparison.PP, PopComparison.PY]
        assert config.windows == [PopWindow.MONTH]
        assert config.format is None
        assert config.date_dimension is None
        assert config.date_filter is None

    def test_disabled_config(self) -> None:
        """Test disabled PoP config."""
        config = PopConfig(enabled=False)
        assert config.enabled is False

    def test_custom_grains(self) -> None:
        """Test custom grain configuration."""
        config = PopConfig(enabled=True, grains=[PopGrain.YTD])
        assert config.grains == [PopGrain.YTD]

    def test_custom_comparisons(self) -> None:
        """Test custom comparison configuration."""
        config = PopConfig(enabled=True, comparisons=[PopComparison.PY])
        assert config.comparisons == [PopComparison.PY]

    def test_custom_windows(self) -> None:
        """Test custom window configuration."""
        config = PopConfig(
            enabled=True, windows=[PopWindow.WEEK, PopWindow.QUARTER]
        )
        assert config.windows == [PopWindow.WEEK, PopWindow.QUARTER]

    def test_full_config(self) -> None:
        """Test fully specified PoP config."""
        config = PopConfig(
            enabled=True,
            grains=[PopGrain.SELECTED, PopGrain.MTD],
            comparisons=[PopComparison.PP],
            windows=[PopWindow.MONTH],
            format="usd",
            date_dimension="selected_date",
            date_filter="selected_date_date",
        )

        assert config.enabled is True
        assert config.format == "usd"
        assert config.date_dimension == "selected_date"
        assert config.date_filter == "selected_date_date"

    def test_invalid_grain_raises_error(self) -> None:
        """Test that invalid grain value raises ValidationError."""
        with pytest.raises(ValidationError):
            PopConfig(enabled=True, grains=["invalid"])

    def test_invalid_comparison_raises_error(self) -> None:
        """Test that invalid comparison value raises ValidationError."""
        with pytest.raises(ValidationError):
            PopConfig(enabled=True, comparisons=["invalid"])

    def test_invalid_window_raises_error(self) -> None:
        """Test that invalid window value raises ValidationError."""
        with pytest.raises(ValidationError):
            PopConfig(enabled=True, windows=["invalid"])

    def test_enabled_required(self) -> None:
        """Test that enabled field is required."""
        with pytest.raises(ValidationError):
            PopConfig()
