"""Unit tests for date selector feature (DTL-046 epic)."""

from __future__ import annotations

import pytest

from dbt_to_lookml.generators.lookml import LookMLGenerator, TimeDimensionInfo
from dbt_to_lookml.schemas.config import Config, ConfigMeta
from dbt_to_lookml.schemas.semantic_layer import (
    Dimension,
    Entity,
    SemanticModel,
)
from dbt_to_lookml.types import DimensionType


class TestTimeDimensionDetection:
    """Tests for _get_date_selector_dimensions and _should_include_in_date_selector."""

    def _create_time_dimension(
        self,
        name: str,
        label: str | None = None,
        expr: str | None = None,
        date_selector: bool | None = None,
    ) -> Dimension:
        """Helper to create a time dimension."""
        config = None
        if date_selector is not None:
            config = Config(meta=ConfigMeta(date_selector=date_selector))
        return Dimension(
            name=name,
            type=DimensionType.TIME,
            label=label,
            expr=expr,
            config=config,
        )

    def _create_model_with_dims(
        self,
        dims: list[Dimension],
        agg_time_dimension: str | None = None,
    ) -> SemanticModel:
        """Helper to create a semantic model with dimensions."""
        defaults = None
        if agg_time_dimension:
            defaults = {"agg_time_dimension": agg_time_dimension}
        return SemanticModel(
            name="test_model",
            model="ref('test')",
            entities=[Entity(name="test_id", type="primary", expr="id")],
            dimensions=dims,
            measures=[],
            defaults=defaults,
        )

    def test_auto_mode_includes_all_by_default(self) -> None:
        """Auto mode includes all time dimensions unless explicitly excluded."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=True,
            date_selector_mode="auto",
            fact_models=["test_model"],
        )

        dims = [
            self._create_time_dimension("created_at", expr="created_at_utc"),
            self._create_time_dimension("updated_at", expr="updated_at_utc"),
        ]
        model = self._create_model_with_dims(dims)

        result = generator._get_date_selector_dimensions(model)

        assert len(result) == 2
        assert result[0].name == "created_at"
        assert result[1].name == "updated_at"

    def test_auto_mode_excludes_marked_false(self) -> None:
        """Auto mode excludes dimensions with date_selector: false."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=True,
            date_selector_mode="auto",
            fact_models=["test_model"],
        )

        dims = [
            self._create_time_dimension("created_at", expr="created_at_utc"),
            self._create_time_dimension("updated_at", expr="updated_at_utc", date_selector=False),
        ]
        model = self._create_model_with_dims(dims)

        result = generator._get_date_selector_dimensions(model)

        assert len(result) == 1
        assert result[0].name == "created_at"

    def test_explicit_mode_excludes_all_by_default(self) -> None:
        """Explicit mode excludes dimensions unless explicitly included."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=True,
            date_selector_mode="explicit",
            fact_models=["test_model"],
        )

        dims = [
            self._create_time_dimension("created_at", expr="created_at_utc"),
            self._create_time_dimension("updated_at", expr="updated_at_utc"),
        ]
        model = self._create_model_with_dims(dims)

        result = generator._get_date_selector_dimensions(model)

        assert len(result) == 0

    def test_explicit_mode_includes_marked_true(self) -> None:
        """Explicit mode includes dimensions with date_selector: true."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=True,
            date_selector_mode="explicit",
            fact_models=["test_model"],
        )

        dims = [
            self._create_time_dimension("created_at", expr="created_at_utc", date_selector=True),
            self._create_time_dimension("updated_at", expr="updated_at_utc"),
        ]
        model = self._create_model_with_dims(dims)

        result = generator._get_date_selector_dimensions(model)

        assert len(result) == 1
        assert result[0].name == "created_at"

    def test_default_selection_uses_agg_time_dimension(self) -> None:
        """Default is set based on agg_time_dimension."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=True,
            date_selector_mode="auto",
            fact_models=["test_model"],
        )

        dims = [
            self._create_time_dimension("created_at", expr="created_at_utc"),
            self._create_time_dimension("updated_at", expr="updated_at_utc"),
        ]
        model = self._create_model_with_dims(dims, agg_time_dimension="updated_at")

        result = generator._get_date_selector_dimensions(model)

        assert len(result) == 2
        assert result[0].is_default is False  # created_at
        assert result[1].is_default is True   # updated_at (matches agg_time_dimension)

    def test_default_fallback_to_first(self) -> None:
        """Default falls back to first dimension if no agg_time_dimension."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=True,
            date_selector_mode="auto",
            fact_models=["test_model"],
        )

        dims = [
            self._create_time_dimension("created_at", expr="created_at_utc"),
            self._create_time_dimension("updated_at", expr="updated_at_utc"),
        ]
        model = self._create_model_with_dims(dims)  # No agg_time_dimension

        result = generator._get_date_selector_dimensions(model)

        assert len(result) == 2
        assert result[0].is_default is True   # first one is default
        assert result[1].is_default is False

    def test_label_extraction(self) -> None:
        """Uses dimension label when available, falls back to smart_title."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=True,
            date_selector_mode="auto",
            fact_models=["test_model"],
        )

        dims = [
            self._create_time_dimension("created_at", label="Created Date", expr="created_at_utc"),
            self._create_time_dimension("updated_at", expr="updated_at_utc"),  # No label
        ]
        model = self._create_model_with_dims(dims)

        result = generator._get_date_selector_dimensions(model)

        assert result[0].label == "Created Date"
        assert result[1].label == "Updated At"  # smart_title applied

    def test_no_time_dimensions(self) -> None:
        """Returns empty list if model has no time dimensions."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=True,
            date_selector_mode="auto",
            fact_models=["test_model"],
        )

        model = self._create_model_with_dims([])  # No dimensions

        result = generator._get_date_selector_dimensions(model)

        assert len(result) == 0


class TestDateSelectorParameterGeneration:
    """Tests for _generate_date_selector_parameter."""

    def test_basic_parameter_generation(self) -> None:
        """Generates parameter with allowed_values and default."""
        generator = LookMLGenerator(schema="test")

        time_dims = [
            TimeDimensionInfo(name="created_at", label="Created", column="created_at_utc", is_default=True),
            TimeDimensionInfo(name="updated_at", label="Updated", column="updated_at_utc", is_default=False),
        ]

        result = generator._generate_date_selector_parameter(time_dims)

        assert result["name"] == "calendar_date"
        assert result["type"] == "unquoted"
        assert result["label"] == "Calendar Date"
        assert len(result["allowed_value"]) == 2
        assert result["allowed_value"][0]["label"] == "Created"
        assert result["allowed_value"][0]["value"] == "created_at_utc"
        assert result["default_value"] == "created_at_utc"

    def test_default_value_selection(self) -> None:
        """Default value comes from is_default=True dimension."""
        generator = LookMLGenerator(schema="test")

        time_dims = [
            TimeDimensionInfo(name="created_at", label="Created", column="created_at_utc", is_default=False),
            TimeDimensionInfo(name="updated_at", label="Updated", column="updated_at_utc", is_default=True),
        ]

        result = generator._generate_date_selector_parameter(time_dims)

        assert result["default_value"] == "updated_at_utc"


class TestCalendarDimensionGroupGeneration:
    """Tests for _generate_calendar_dimension_group."""

    def test_basic_dimension_group_generation(self) -> None:
        """Generates dimension_group with Liquid template."""
        generator = LookMLGenerator(schema="test")

        result = generator._generate_calendar_dimension_group()

        assert result["name"] == "calendar"
        assert result["type"] == "time"
        assert "{% parameter calendar_date %}" in result["sql"]
        assert result["convert_tz"] == "no"
        assert "date" in result["timeframes"]
        assert "month" in result["timeframes"]
        assert "year" in result["timeframes"]


class TestDateSelectorFieldsIntegration:
    """Tests for _generate_date_selector_fields integration method."""

    def _create_model(self, name: str = "test_model") -> SemanticModel:
        """Create a basic semantic model with time dimensions."""
        return SemanticModel(
            name=name,
            model="ref('test')",
            entities=[Entity(name="test_id", type="primary", expr="id")],
            dimensions=[
                Dimension(name="created_at", type=DimensionType.TIME, expr="created_at_utc"),
            ],
            measures=[],
        )

    def test_disabled_returns_empty(self) -> None:
        """Returns empty when date_selector is disabled."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=False,
            fact_models=["test_model"],
        )
        model = self._create_model()

        params, dim_groups = generator._generate_date_selector_fields(model)

        assert params == []
        assert dim_groups == []

    def test_non_fact_model_returns_empty(self) -> None:
        """Returns empty when model is not in fact_models list."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=True,
            fact_models=["other_model"],  # Not test_model
        )
        model = self._create_model()

        params, dim_groups = generator._generate_date_selector_fields(model)

        assert params == []
        assert dim_groups == []

    def test_enabled_for_fact_model(self) -> None:
        """Returns parameter and dimension_group for fact model."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=True,
            date_selector_mode="auto",
            fact_models=["test_model"],
        )
        model = self._create_model()

        params, dim_groups = generator._generate_date_selector_fields(model)

        assert len(params) == 1
        assert params[0]["name"] == "calendar_date"
        assert len(dim_groups) == 1
        assert dim_groups[0]["name"] == "calendar"


class TestDateSelectorEdgeCases:
    """Edge case tests for date selector feature."""

    def test_all_dimensions_excluded_auto_mode(self) -> None:
        """Skip date selector when all dimensions are excluded."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=True,
            date_selector_mode="auto",
            fact_models=["test_model"],
        )

        model = SemanticModel(
            name="test_model",
            model="ref('test')",
            entities=[Entity(name="test_id", type="primary", expr="id")],
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    expr="created_at_utc",
                    config=Config(meta=ConfigMeta(date_selector=False)),
                ),
            ],
            measures=[],
        )

        params, dim_groups = generator._generate_date_selector_fields(model)

        assert params == []
        assert dim_groups == []

    def test_single_time_dimension(self) -> None:
        """Still generates with single time dimension."""
        generator = LookMLGenerator(
            schema="test",
            date_selector=True,
            date_selector_mode="auto",
            fact_models=["test_model"],
        )

        model = SemanticModel(
            name="test_model",
            model="ref('test')",
            entities=[Entity(name="test_id", type="primary", expr="id")],
            dimensions=[
                Dimension(name="created_at", type=DimensionType.TIME, expr="created_at_utc"),
            ],
            measures=[],
        )

        params, dim_groups = generator._generate_date_selector_fields(model)

        assert len(params) == 1
        assert len(params[0]["allowed_value"]) == 1
