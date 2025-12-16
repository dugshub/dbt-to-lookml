"""Unit tests for PoP configuration parsing in DbtParser."""

import tempfile
from pathlib import Path

import pytest
import yaml

from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.schemas.config import PopComparison, PopGrain, PopWindow


class TestPopParsing:
    """Tests for PoP configuration parsing."""

    def test_parse_measure_with_full_pop_config(self) -> None:
        """Test parsing measure with full PoP config."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    measures:
      - name: revenue
        agg: sum
        expr: checkout_amount
        config:
          meta:
            pop:
              enabled: true
              grains: [mtd, ytd]
              comparisons: [pp, py]
              windows: [month]
              format: usd
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)

            assert len(models) == 1
            assert len(models[0].measures) == 1

            measure = models[0].measures[0]
            assert measure.config is not None
            assert measure.config.meta is not None
            assert measure.config.meta.pop is not None

            pop = measure.config.meta.pop
            assert pop.enabled is True
            assert pop.grains == [PopGrain.MTD, PopGrain.YTD]
            assert pop.comparisons == [PopComparison.PP, PopComparison.PY]
            assert pop.windows == [PopWindow.MONTH]
            assert pop.format == "usd"
            # Should fall back to defaults.agg_time_dimension
            assert pop.date_dimension == "selected_date"
            # Should derive from date_dimension
            assert pop.date_filter == "selected_date_date"
        finally:
            temp_path.unlink()

    def test_pop_date_dimension_resolution_from_defaults(self) -> None:
        """Test date_dimension falls back to defaults.agg_time_dimension."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: rental_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            assert measure.config.meta.pop is not None
            assert measure.config.meta.pop.date_dimension == "rental_date"
            assert measure.config.meta.pop.date_filter == "rental_date_date"
        finally:
            temp_path.unlink()

    def test_pop_date_dimension_explicit_override(self) -> None:
        """Test explicit date_dimension overrides defaults."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: created_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
              date_dimension: completed_date
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            measure = models[0].measures[0]
            pop = measure.config.meta.pop

            # Should use explicit value, not defaults
            assert pop.date_dimension == "completed_date"
            assert pop.date_filter == "completed_date_date"
        finally:
            temp_path.unlink()

    def test_pop_date_filter_explicit_override(self) -> None:
        """Test explicit date_filter overrides derived value."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
              date_filter: custom_filter_date
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            measure = models[0].measures[0]
            pop = measure.config.meta.pop

            assert pop.date_filter == "custom_filter_date"
        finally:
            temp_path.unlink()

    def test_pop_disabled_returns_none(self) -> None:
        """Test that disabled pop config is not stored."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: false
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            assert measure.config is not None
            assert measure.config.meta is not None
            # Pop should be None when disabled
            assert measure.config.meta.pop is None
        finally:
            temp_path.unlink()

    def test_measure_without_pop(self) -> None:
        """Test measures without pop config work normally."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    measures:
      - name: revenue
        agg: sum
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            assert len(models) == 1

            measure = models[0].measures[0]
            # Measure should work fine without pop
            assert measure.name == "revenue"
            # Config might be None or have no pop
            if measure.config and measure.config.meta:
                assert measure.config.meta.pop is None
        finally:
            temp_path.unlink()

    def test_pop_with_custom_grains(self) -> None:
        """Test pop config with custom grain configuration."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
              grains: [selected, ytd]
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            pop = models[0].measures[0].config.meta.pop

            assert pop.grains == [PopGrain.SELECTED, PopGrain.YTD]
        finally:
            temp_path.unlink()

    def test_pop_with_custom_comparisons(self) -> None:
        """Test pop config with custom comparison configuration."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
              comparisons: [py]
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            pop = models[0].measures[0].config.meta.pop

            assert pop.comparisons == [PopComparison.PY]
        finally:
            temp_path.unlink()

    def test_pop_with_custom_windows(self) -> None:
        """Test pop config with custom window configuration."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
              windows: [week, quarter]
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            pop = models[0].measures[0].config.meta.pop

            assert pop.windows == [PopWindow.WEEK, PopWindow.QUARTER]
        finally:
            temp_path.unlink()

    def test_pop_with_defaults_when_not_specified(self) -> None:
        """Test pop config uses defaults when grains/comparisons/windows not specified."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            pop = models[0].measures[0].config.meta.pop

            # Should use defaults
            assert pop.grains == [PopGrain.MTD, PopGrain.YTD]
            assert pop.comparisons == [PopComparison.PP, PopComparison.PY]
            assert pop.windows == [PopWindow.MONTH]
        finally:
            temp_path.unlink()

    def test_pop_date_dimension_resolution_from_model_level_pop(self) -> None:
        """Test date_dimension resolution from model-level pop config."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    config:
      meta:
        pop:
          date_dimension: model_level_date
    defaults:
      agg_time_dimension: defaults_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            pop = models[0].measures[0].config.meta.pop

            # Should use model-level pop config before falling back to defaults
            assert pop.date_dimension == "model_level_date"
            assert pop.date_filter == "model_level_date_date"
        finally:
            temp_path.unlink()

    def test_pop_no_date_dimension_available(self) -> None:
        """Test pop config when no date_dimension is available."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            pop = models[0].measures[0].config.meta.pop

            # Should be None when no date_dimension is available
            assert pop.date_dimension is None
            assert pop.date_filter is None
        finally:
            temp_path.unlink()

    def test_multiple_measures_with_mixed_pop_config(self) -> None:
        """Test model with multiple measures, some with pop and some without."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
      - name: order_count
        agg: count
      - name: avg_amount
        agg: average
        config:
          meta:
            pop:
              enabled: false
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            measures = models[0].measures

            assert len(measures) == 3

            # First measure has pop enabled
            assert measures[0].config.meta.pop is not None
            assert measures[0].config.meta.pop.enabled is True

            # Second measure has no pop config
            if measures[1].config and measures[1].config.meta:
                assert measures[1].config.meta.pop is None

            # Third measure has pop disabled (returns None)
            if measures[2].config and measures[2].config.meta:
                assert measures[2].config.meta.pop is None
        finally:
            temp_path.unlink()

    def test_pop_with_invalid_grain_raises_error(self) -> None:
        """Test that invalid grain value raises validation error."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
              grains: [invalid_grain]
"""
        parser = DbtParser(strict_mode=True)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_pop_with_invalid_comparison_raises_error(self) -> None:
        """Test that invalid comparison value raises validation error."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
              comparisons: [invalid_comparison]
"""
        parser = DbtParser(strict_mode=True)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_pop_with_invalid_window_raises_error(self) -> None:
        """Test that invalid window value raises validation error."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    measures:
      - name: revenue
        agg: sum
        config:
          meta:
            pop:
              enabled: true
              windows: [invalid_window]
"""
        parser = DbtParser(strict_mode=True)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError):
                parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_pop_preserves_other_measure_metadata(self) -> None:
        """Test that pop config doesn't interfere with other metadata."""
        yaml_content = """
semantic_models:
  - name: rentals
    model: ref('rentals')
    defaults:
      agg_time_dimension: selected_date
    measures:
      - name: revenue
        agg: sum
        expr: checkout_amount
        description: "Total revenue"
        label: "Revenue"
        config:
          meta:
            domain: "finance"
            owner: "finance_team"
            category: "metrics"
            pop:
              enabled: true
              format: usd
"""
        parser = DbtParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            models = parser.parse_file(temp_path)
            measure = models[0].measures[0]

            # Check measure properties
            assert measure.name == "revenue"
            assert measure.expr == "checkout_amount"
            assert measure.description == "Total revenue"
            assert measure.label == "Revenue"

            # Check other metadata preserved
            assert measure.config.meta.domain == "finance"
            assert measure.config.meta.owner == "finance_team"
            assert measure.config.meta.category == "metrics"

            # Check pop config present
            assert measure.config.meta.pop is not None
            assert measure.config.meta.pop.format == "usd"
        finally:
            temp_path.unlink()
