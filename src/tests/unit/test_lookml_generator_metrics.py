"""Unit tests for metric measure generation in LookMLGenerator."""

import pytest

from dbt_to_lookml.constants import SUFFIX_PERFORMANCE, VIEW_LABEL_METRICS
from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.schemas.semantic_layer import (
    DerivedMetricParams,
    Entity,
    Measure,
    Metric,
    MetricReference,
    RatioMetricParams,
    SemanticModel,
    SimpleMetricParams,
)
from dbt_to_lookml.types import AggregationType


class TestHelperMethods:
    """Test helper methods for model and measure lookup."""

    @pytest.fixture
    def generator(self) -> LookMLGenerator:
        """Create a LookMLGenerator instance."""
        return LookMLGenerator()

    @pytest.fixture
    def models_dict(self) -> dict[str, SemanticModel]:
        """Create test semantic models with measures."""
        orders_model = SemanticModel(
            name="orders",
            model="ref('orders')",
            entities=[Entity(name="order", type="primary")],
            measures=[
                Measure(name="order_count", agg=AggregationType.COUNT),
                Measure(name="revenue", agg=AggregationType.SUM),
            ],
        )

        searches_model = SemanticModel(
            name="searches",
            model="ref('searches')",
            entities=[Entity(name="search", type="primary")],
            measures=[Measure(name="search_count", agg=AggregationType.COUNT)],
        )

        return {"orders": orders_model, "searches": searches_model}

    def test_find_model_with_measure_found(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test finding a model that contains a measure."""
        result = generator._find_model_with_measure("order_count", models_dict)
        assert result is not None
        assert result.name == "orders"

    def test_find_model_with_measure_not_found(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test finding a measure that doesn't exist."""
        result = generator._find_model_with_measure("nonexistent", models_dict)
        assert result is None

    def test_find_model_with_measure_empty_dict(
        self, generator: LookMLGenerator
    ) -> None:
        """Test finding a measure in an empty dictionary."""
        result = generator._find_model_with_measure("order_count", {})
        assert result is None

    def test_resolve_measure_reference_same_view(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test resolving a measure reference in the same view."""
        result = generator._resolve_measure_reference(
            "order_count", "order", models_dict
        )
        assert result == "${order_count_measure}"

    def test_resolve_measure_reference_cross_view(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test resolving a measure reference in a different view."""
        result = generator._resolve_measure_reference(
            "search_count", "order", models_dict
        )
        assert result == "${searches.search_count_measure}"

    def test_resolve_measure_reference_with_prefix(
        self, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test resolving a measure reference with view prefix."""
        generator = LookMLGenerator(view_prefix="v_")
        result = generator._resolve_measure_reference(
            "search_count", "order", models_dict
        )
        assert result == "${v_searches.search_count_measure}"

    def test_resolve_measure_reference_missing_measure(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test resolving a measure that doesn't exist."""
        with pytest.raises(ValueError, match="Measure 'nonexistent' not found"):
            generator._resolve_measure_reference("nonexistent", "order", models_dict)

    def test_resolve_measure_reference_missing_primary_entity(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test resolving with a primary entity that doesn't exist."""
        with pytest.raises(ValueError, match="No model found with primary entity"):
            generator._resolve_measure_reference(
                "order_count", "nonexistent", models_dict
            )


class TestSQLGenerationSimple:
    """Test SQL generation for simple metrics."""

    @pytest.fixture
    def generator(self) -> LookMLGenerator:
        """Create a LookMLGenerator instance."""
        return LookMLGenerator()

    @pytest.fixture
    def models_dict(self) -> dict[str, SemanticModel]:
        """Create test semantic models."""
        return {
            "orders": SemanticModel(
                name="orders",
                model="ref('orders')",
                entities=[Entity(name="order", type="primary")],
                measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
            ),
            "searches": SemanticModel(
                name="searches",
                model="ref('searches')",
                entities=[Entity(name="search", type="primary")],
                measures=[Measure(name="search_count", agg=AggregationType.COUNT)],
            ),
        }

    def test_generate_simple_sql_same_view(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test simple metric SQL generation for same view."""
        metric = Metric(
            name="total_orders",
            type="simple",
            type_params=SimpleMetricParams(measure="order_count"),
            meta={"primary_entity": "order"},
        )
        sql = generator._generate_simple_sql(metric, models_dict)
        assert sql == "${order_count_measure}"

    def test_generate_simple_sql_cross_view(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test simple metric SQL generation for cross-view reference."""
        metric = Metric(
            name="total_searches",
            type="simple",
            type_params=SimpleMetricParams(measure="search_count"),
            meta={"primary_entity": "order"},
        )
        sql = generator._generate_simple_sql(metric, models_dict)
        assert sql == "${searches.search_count_measure}"

    def test_generate_simple_sql_with_prefix(
        self, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test simple metric SQL generation with view prefix."""
        generator = LookMLGenerator(view_prefix="v_")
        metric = Metric(
            name="total_searches",
            type="simple",
            type_params=SimpleMetricParams(measure="search_count"),
            meta={"primary_entity": "order"},
        )
        sql = generator._generate_simple_sql(metric, models_dict)
        assert sql == "${v_searches.search_count_measure}"

    def test_generate_simple_sql_missing_primary_entity(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test simple metric SQL generation without primary entity."""
        metric = Metric(
            name="total_orders",
            type="simple",
            type_params=SimpleMetricParams(measure="order_count"),
        )
        with pytest.raises(ValueError, match="has no primary_entity"):
            generator._generate_simple_sql(metric, models_dict)

    def test_generate_simple_sql_wrong_type_params(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test simple metric SQL generation with wrong type params."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "order"},
        )
        with pytest.raises(TypeError, match="Expected SimpleMetricParams"):
            generator._generate_simple_sql(metric, models_dict)


class TestSQLGenerationRatio:
    """Test SQL generation for ratio metrics."""

    @pytest.fixture
    def generator(self) -> LookMLGenerator:
        """Create a LookMLGenerator instance."""
        return LookMLGenerator()

    @pytest.fixture
    def models_dict(self) -> dict[str, SemanticModel]:
        """Create test semantic models."""
        return {
            "orders": SemanticModel(
                name="orders",
                model="ref('orders')",
                entities=[Entity(name="order", type="primary")],
                measures=[
                    Measure(name="order_count", agg=AggregationType.COUNT),
                    Measure(name="revenue", agg=AggregationType.SUM),
                ],
            ),
            "searches": SemanticModel(
                name="searches",
                model="ref('searches')",
                entities=[Entity(name="search", type="primary")],
                measures=[Measure(name="search_count", agg=AggregationType.COUNT)],
            ),
        }

    def test_generate_ratio_sql_both_same_view(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test ratio metric SQL with both measures in same view."""
        metric = Metric(
            name="revenue_per_order",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="revenue", denominator="order_count"
            ),
            meta={"primary_entity": "order"},
        )
        sql = generator._generate_ratio_sql(metric, models_dict)
        assert sql == "1.0 * ${revenue_measure} / NULLIF(${order_count_measure}, 0)"

    def test_generate_ratio_sql_both_cross_view(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test ratio metric SQL with both measures in other views."""
        # Add a third model to use as base
        models_dict["users"] = SemanticModel(
            name="users",
            model="ref('users')",
            entities=[Entity(name="user", type="primary")],
            measures=[],
        )
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "user"},
        )
        sql = generator._generate_ratio_sql(metric, models_dict)
        assert (
            sql
            == "1.0 * ${orders.order_count_measure} / NULLIF(${searches.search_count_measure}, 0)"
        )

    def test_generate_ratio_sql_num_same_denom_cross(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test ratio metric SQL with numerator same view, denominator cross-view."""
        metric = Metric(
            name="order_to_search_ratio",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "order"},
        )
        sql = generator._generate_ratio_sql(metric, models_dict)
        assert (
            sql
            == "1.0 * ${order_count_measure} / NULLIF(${searches.search_count_measure}, 0)"
        )

    def test_generate_ratio_sql_num_cross_denom_same(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test ratio metric SQL with numerator cross-view, denominator same view."""
        metric = Metric(
            name="search_to_order_ratio",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "search"},
        )
        sql = generator._generate_ratio_sql(metric, models_dict)
        assert (
            sql
            == "1.0 * ${orders.order_count_measure} / NULLIF(${search_count_measure}, 0)"
        )

    def test_generate_ratio_sql_with_prefix(
        self, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test ratio metric SQL with view prefix."""
        generator = LookMLGenerator(view_prefix="v_")
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "order"},
        )
        sql = generator._generate_ratio_sql(metric, models_dict)
        assert (
            sql
            == "1.0 * ${order_count_measure} / NULLIF(${v_searches.search_count_measure}, 0)"
        )

    def test_generate_ratio_sql_nullif_safety(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test that ratio SQL includes NULLIF for division by zero safety."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "order"},
        )
        sql = generator._generate_ratio_sql(metric, models_dict)
        assert "NULLIF" in sql
        assert ", 0)" in sql

    def test_generate_ratio_sql_missing_primary_entity(
        self, generator: LookMLGenerator, models_dict: dict[str, SemanticModel]
    ) -> None:
        """Test ratio metric SQL without primary entity."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
        )
        with pytest.raises(ValueError, match="has no primary_entity"):
            generator._generate_ratio_sql(metric, models_dict)


class TestSQLGenerationDerived:
    """Test SQL generation for derived metrics."""

    @pytest.fixture
    def generator(self) -> LookMLGenerator:
        """Create a LookMLGenerator instance."""
        return LookMLGenerator()

    @pytest.fixture
    def models_dict(self) -> dict[str, SemanticModel]:
        """Create test semantic models."""
        return {
            "orders": SemanticModel(
                name="orders",
                model="ref('orders')",
                entities=[Entity(name="order", type="primary")],
                measures=[
                    Measure(name="order_count", agg=AggregationType.COUNT),
                    Measure(name="revenue", agg=AggregationType.SUM),
                ],
            ),
            "searches": SemanticModel(
                name="searches",
                model="ref('searches')",
                entities=[Entity(name="search", type="primary")],
                measures=[Measure(name="search_count", agg=AggregationType.COUNT)],
            ),
        }

    @pytest.fixture
    def all_metrics(self) -> list[Metric]:
        """Create test metrics."""
        return [
            Metric(
                name="order_count",
                type="simple",
                type_params=SimpleMetricParams(measure="order_count"),
                meta={"primary_entity": "order"},
            ),
            Metric(
                name="revenue",
                type="simple",
                type_params=SimpleMetricParams(measure="revenue"),
                meta={"primary_entity": "order"},
            ),
            Metric(
                name="search_count",
                type="simple",
                type_params=SimpleMetricParams(measure="search_count"),
                meta={"primary_entity": "search"},
            ),
        ]

    def test_generate_derived_sql_simple_addition(
        self,
        generator: LookMLGenerator,
        models_dict: dict[str, SemanticModel],
        all_metrics: list[Metric],
    ) -> None:
        """Test derived metric with simple addition."""
        metric = Metric(
            name="total_count",
            type="derived",
            type_params=DerivedMetricParams(
                expr="order_count + search_count",
                metrics=[
                    MetricReference(name="order_count"),
                    MetricReference(name="search_count"),
                ],
            ),
            meta={"primary_entity": "order"},
        )
        sql = generator._generate_derived_sql(metric, models_dict, all_metrics)
        assert sql == "${order_count} + ${searches.search_count}"

    def test_generate_derived_sql_simple_subtraction(
        self,
        generator: LookMLGenerator,
        models_dict: dict[str, SemanticModel],
        all_metrics: list[Metric],
    ) -> None:
        """Test derived metric with simple subtraction."""
        metric = Metric(
            name="net_metric",
            type="derived",
            type_params=DerivedMetricParams(
                expr="order_count - search_count",
                metrics=[
                    MetricReference(name="order_count"),
                    MetricReference(name="search_count"),
                ],
            ),
            meta={"primary_entity": "order"},
        )
        sql = generator._generate_derived_sql(metric, models_dict, all_metrics)
        assert sql == "${order_count} - ${searches.search_count}"

    def test_generate_derived_sql_with_parentheses(
        self,
        generator: LookMLGenerator,
        models_dict: dict[str, SemanticModel],
        all_metrics: list[Metric],
    ) -> None:
        """Test derived metric with parentheses."""
        metric = Metric(
            name="average_metric",
            type="derived",
            type_params=DerivedMetricParams(
                expr="(order_count + search_count) / 2",
                metrics=[
                    MetricReference(name="order_count"),
                    MetricReference(name="search_count"),
                ],
            ),
            meta={"primary_entity": "order"},
        )
        sql = generator._generate_derived_sql(metric, models_dict, all_metrics)
        assert sql == "(${order_count} + ${searches.search_count}) / 2"

    def test_generate_derived_sql_cross_view_refs(
        self,
        generator: LookMLGenerator,
        models_dict: dict[str, SemanticModel],
        all_metrics: list[Metric],
    ) -> None:
        """Test derived metric with cross-view references."""
        metric = Metric(
            name="combined_revenue",
            type="derived",
            type_params=DerivedMetricParams(
                expr="revenue + search_count",
                metrics=[
                    MetricReference(name="revenue"),
                    MetricReference(name="search_count"),
                ],
            ),
            meta={"primary_entity": "order"},
        )
        sql = generator._generate_derived_sql(metric, models_dict, all_metrics)
        assert sql == "${revenue} + ${searches.search_count}"

    def test_generate_derived_sql_with_aliases(
        self,
        generator: LookMLGenerator,
        models_dict: dict[str, SemanticModel],
        all_metrics: list[Metric],
    ) -> None:
        """Test derived metric with aliases (the actual bug fix).

        This tests the scenario where metric references use aliases in the expr,
        which was the original bug: aliases weren't being replaced with LookML
        measure references.
        """
        metric = Metric(
            name="average_order_value",
            type="derived",
            type_params=DerivedMetricParams(
                expr="total_rev / total_orders",
                metrics=[
                    MetricReference(name="revenue", alias="total_rev"),
                    MetricReference(name="order_count", alias="total_orders"),
                ],
            ),
            meta={"primary_entity": "order"},
        )
        sql = generator._generate_derived_sql(metric, models_dict, all_metrics)
        # Should replace aliases (total_rev, total_orders) not metric names
        assert sql == "${revenue} / ${order_count}"
        # Verify aliases were replaced (not present in final SQL)
        assert "total_rev" not in sql
        assert "total_orders" not in sql

    def test_generate_derived_sql_missing_primary_entity(
        self,
        generator: LookMLGenerator,
        models_dict: dict[str, SemanticModel],
        all_metrics: list[Metric],
    ) -> None:
        """Test derived metric without primary entity."""
        metric = Metric(
            name="total_count",
            type="derived",
            type_params=DerivedMetricParams(
                expr="order_count + search_count",
                metrics=[
                    MetricReference(name="order_count"),
                    MetricReference(name="search_count"),
                ],
            ),
        )
        with pytest.raises(ValueError, match="has no primary_entity"):
            generator._generate_derived_sql(metric, models_dict, all_metrics)


class TestRequiredFieldsExtraction:
    """Test required_fields extraction for metrics."""

    @pytest.fixture
    def generator(self) -> LookMLGenerator:
        """Create a LookMLGenerator instance."""
        return LookMLGenerator()

    @pytest.fixture
    def all_models(self) -> list[SemanticModel]:
        """Create test semantic models."""
        return [
            SemanticModel(
                name="orders",
                model="ref('orders')",
                entities=[Entity(name="order", type="primary")],
                measures=[
                    Measure(name="order_count", agg=AggregationType.COUNT),
                    Measure(name="revenue", agg=AggregationType.SUM),
                ],
            ),
            SemanticModel(
                name="searches",
                model="ref('searches')",
                entities=[Entity(name="search", type="primary")],
                measures=[Measure(name="search_count", agg=AggregationType.COUNT)],
            ),
        ]

    def test_extract_required_fields_simple_same_view(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test required fields for simple metric in same view."""
        metric = Metric(
            name="total_orders",
            type="simple",
            type_params=SimpleMetricParams(measure="order_count"),
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]  # orders
        required = generator._extract_required_fields(metric, primary_model, all_models)
        assert required == []

    def test_extract_required_fields_simple_cross_view(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test required fields for simple metric in different view."""
        metric = Metric(
            name="total_searches",
            type="simple",
            type_params=SimpleMetricParams(measure="search_count"),
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]  # orders
        required = generator._extract_required_fields(metric, primary_model, all_models)
        assert required == ["searches.search_count_measure"]

    def test_extract_required_fields_ratio_both_cross(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test required fields for ratio metric with both cross-view."""
        # Add a third model
        all_models.append(
            SemanticModel(
                name="users",
                model="ref('users')",
                entities=[Entity(name="user", type="primary")],
                measures=[],
            )
        )
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "user"},
        )
        primary_model = all_models[2]  # users
        required = generator._extract_required_fields(metric, primary_model, all_models)
        assert sorted(required) == [
            "orders.order_count_measure",
            "searches.search_count_measure",
        ]

    def test_extract_required_fields_ratio_mixed(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test required fields for ratio metric with mixed views."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]  # orders
        required = generator._extract_required_fields(metric, primary_model, all_models)
        assert required == ["searches.search_count_measure"]

    def test_extract_required_fields_derived_multiple(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test required fields for derived metric with multiple dependencies."""
        metric = Metric(
            name="total_count",
            type="derived",
            type_params=DerivedMetricParams(
                expr="order_count + search_count",
                metrics=[
                    MetricReference(name="order_count"),
                    MetricReference(name="search_count"),
                ],
            ),
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]  # orders
        required = generator._extract_required_fields(metric, primary_model, all_models)
        # Derived metrics reference other METRICS, not dbt measures, so no _measure suffix
        assert required == ["searches.search_count"]

    def test_extract_required_fields_with_prefix(
        self, all_models: list[SemanticModel]
    ) -> None:
        """Test required fields with view prefix."""
        generator = LookMLGenerator(view_prefix="v_")
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]  # orders
        required = generator._extract_required_fields(metric, primary_model, all_models)
        assert required == ["v_searches.search_count_measure"]

    def test_extract_required_fields_sorted(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test that required fields are sorted."""
        # Add a third model
        all_models.append(
            SemanticModel(
                name="users",
                model="ref('users')",
                entities=[Entity(name="user", type="primary")],
                measures=[],
            )
        )
        metric = Metric(
            name="combined",
            type="derived",
            type_params=DerivedMetricParams(
                expr="search_count + order_count",
                metrics=[
                    MetricReference(name="search_count"),
                    MetricReference(name="order_count"),
                ],
            ),
            meta={"primary_entity": "user"},
        )
        primary_model = all_models[2]  # users
        required = generator._extract_required_fields(metric, primary_model, all_models)
        # Should be sorted alphabetically
        # Derived metrics reference other METRICS, not dbt measures, so no _measure suffix
        assert required == [
            "orders.order_count",
            "searches.search_count",
        ]


class TestInferenceMethods:
    """Test value format and group label inference."""

    @pytest.fixture
    def generator(self) -> LookMLGenerator:
        """Create a LookMLGenerator instance."""
        return LookMLGenerator()

    @pytest.fixture
    def primary_model(self) -> SemanticModel:
        """Create a test semantic model."""
        return SemanticModel(
            name="orders",
            model="ref('orders')",
            entities=[Entity(name="order", type="primary")],
            measures=[],
        )

    def test_infer_value_format_ratio(self, generator: LookMLGenerator) -> None:
        """Test value format inference for ratio metrics."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "order"},
        )
        format_name = generator._infer_value_format(metric)
        assert format_name == "percent_2"

    def test_infer_value_format_revenue(self, generator: LookMLGenerator) -> None:
        """Test value format inference for revenue metrics."""
        metric = Metric(
            name="total_revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="revenue"),
            meta={"primary_entity": "order"},
        )
        format_name = generator._infer_value_format(metric)
        assert format_name == "usd"

    def test_infer_value_format_price(self, generator: LookMLGenerator) -> None:
        """Test value format inference for price metrics."""
        metric = Metric(
            name="average_price",
            type="simple",
            type_params=SimpleMetricParams(measure="price"),
            meta={"primary_entity": "order"},
        )
        format_name = generator._infer_value_format(metric)
        assert format_name == "usd"

    def test_infer_value_format_count(self, generator: LookMLGenerator) -> None:
        """Test value format inference for count metrics."""
        metric = Metric(
            name="total_count",
            type="simple",
            type_params=SimpleMetricParams(measure="order_count"),
            meta={"primary_entity": "order"},
        )
        format_name = generator._infer_value_format(metric)
        assert format_name == "decimal_0"

    def test_infer_value_format_other(self, generator: LookMLGenerator) -> None:
        """Test value format inference for other metrics."""
        metric = Metric(
            name="some_metric",
            type="simple",
            type_params=SimpleMetricParams(measure="some_measure"),
            meta={"primary_entity": "order"},
        )
        format_name = generator._infer_value_format(metric)
        assert format_name is None

    def test_infer_value_format_case_insensitive(
        self, generator: LookMLGenerator
    ) -> None:
        """Test value format inference is case insensitive."""
        metric = Metric(
            name="Total_Revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="revenue"),
            meta={"primary_entity": "order"},
        )
        format_name = generator._infer_value_format(metric)
        assert format_name == "usd"

    def test_infer_value_format_meta_override(
        self, generator: LookMLGenerator
    ) -> None:
        """Test that meta.value_format_name overrides inference."""
        metric = Metric(
            name="avg_star_rating",
            type="simple",
            type_params=SimpleMetricParams(measure="star_rating"),
            meta={"primary_entity": "review", "value_format_name": "decimal_2"},
        )
        format_name = generator._infer_value_format(metric)
        assert format_name == "decimal_2"

    def test_infer_value_format_meta_override_trumps_heuristics(
        self, generator: LookMLGenerator
    ) -> None:
        """Test that explicit meta.value_format_name overrides heuristics like 'revenue' → 'usd'."""
        # This metric has 'revenue' in the name, which would normally infer 'usd'
        metric = Metric(
            name="monthly_revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="revenue"),
            meta={"primary_entity": "order", "value_format_name": "decimal_0"},
        )
        format_name = generator._infer_value_format(metric)
        # Explicit override should win over heuristic
        assert format_name == "decimal_0"

    def test_infer_group_label_with_meta(
        self, generator: LookMLGenerator, primary_model: SemanticModel
    ) -> None:
        """Test group label inference with meta category."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "order", "category": "conversion_metrics"},
        )
        label = generator._infer_group_label(metric, primary_model)
        assert label == "Conversion Metrics"

    def test_infer_group_label_without_meta(
        self, generator: LookMLGenerator, primary_model: SemanticModel
    ) -> None:
        """Test group label inference without meta category."""
        metric = Metric(
            name="total_orders",
            type="simple",
            type_params=SimpleMetricParams(measure="order_count"),
            meta={"primary_entity": "order"},
        )
        label = generator._infer_group_label(metric, primary_model)
        assert label == f"Orders {SUFFIX_PERFORMANCE}"

    def test_infer_group_label_formatting(self, generator: LookMLGenerator) -> None:
        """Test group label formatting with underscores."""
        model = SemanticModel(
            name="rental_orders",
            model="ref('rental_orders')",
            entities=[Entity(name="rental", type="primary")],
            measures=[],
        )
        metric = Metric(
            name="total_rentals",
            type="simple",
            type_params=SimpleMetricParams(measure="rental_count"),
            meta={"primary_entity": "rental"},
        )
        label = generator._infer_group_label(metric, model)
        assert label == f"Rental Orders {SUFFIX_PERFORMANCE}"


class TestMetricMeasureGeneration:
    """Test metric-to-measure conversion."""

    @pytest.fixture
    def generator(self) -> LookMLGenerator:
        """Create a LookMLGenerator instance."""
        return LookMLGenerator()

    @pytest.fixture
    def all_models(self) -> list[SemanticModel]:
        """Create test semantic models."""
        return [
            SemanticModel(
                name="orders",
                model="ref('orders')",
                entities=[Entity(name="order", type="primary")],
                measures=[
                    Measure(name="order_count", agg=AggregationType.COUNT),
                    Measure(name="revenue", agg=AggregationType.SUM),
                ],
            ),
            SemanticModel(
                name="searches",
                model="ref('searches')",
                entities=[Entity(name="search", type="primary")],
                measures=[Measure(name="search_count", agg=AggregationType.COUNT)],
            ),
        ]

    def test_generate_metric_measure_simple(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test generating measure dict for simple metric.

        Simple metrics now generate as direct aggregates (type: count, sum, etc.)
        instead of type: number wrappers per smart optimization.
        """
        metric = Metric(
            name="total_orders",
            type="simple",
            type_params=SimpleMetricParams(measure="order_count"),
            label="Total Orders",
            description="Total count of orders",
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]
        measure_dict = generator._generate_metric_measure(
            metric, primary_model, all_models
        )

        assert measure_dict["name"] == "total_orders"
        # Smart optimization: simple metrics use direct aggregate type
        assert measure_dict["type"] == "count"
        # COUNT type doesn't have sql field
        assert "sql" not in measure_dict
        assert measure_dict["view_label"] == f"  {VIEW_LABEL_METRICS}"
        assert measure_dict["label"] == "Total Orders"
        assert measure_dict["description"] == "Total count of orders"
        assert measure_dict["group_label"] == f"Orders {SUFFIX_PERFORMANCE}"
        # value_format_name is not set because "total_orders" doesn't match heuristics
        assert "value_format_name" not in measure_dict

    def test_generate_metric_measure_ratio(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test generating measure dict for ratio metric."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            label="Conversion Rate",
            description="Orders per search",
            meta={"primary_entity": "order", "category": "performance"},
        )
        primary_model = all_models[0]
        measure_dict = generator._generate_metric_measure(
            metric, primary_model, all_models
        )

        assert measure_dict["name"] == "conversion_rate"
        assert measure_dict["type"] == "number"
        assert "NULLIF" in measure_dict["sql"]
        assert "${order_count_measure}" in measure_dict["sql"]
        assert "${searches.search_count_measure}" in measure_dict["sql"]
        assert measure_dict["view_label"] == f"  {VIEW_LABEL_METRICS}"
        assert measure_dict["value_format_name"] == "percent_2"
        assert measure_dict["required_fields"] == ["searches.search_count_measure"]
        assert measure_dict["group_label"] == "Performance"

    def test_generate_metric_measure_derived(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test generating measure dict for derived metric."""
        all_metrics = [
            Metric(
                name="order_count",
                type="simple",
                type_params=SimpleMetricParams(measure="order_count"),
                meta={"primary_entity": "order"},
            ),
            Metric(
                name="search_count",
                type="simple",
                type_params=SimpleMetricParams(measure="search_count"),
                meta={"primary_entity": "search"},
            ),
        ]
        metric = Metric(
            name="total_count",
            type="derived",
            type_params=DerivedMetricParams(
                expr="order_count + search_count",
                metrics=[
                    MetricReference(name="order_count"),
                    MetricReference(name="search_count"),
                ],
            ),
            label="Total Count",
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]
        measure_dict = generator._generate_metric_measure(
            metric, primary_model, all_models, all_metrics
        )

        assert measure_dict["name"] == "total_count"
        assert measure_dict["type"] == "number"
        assert "${order_count}" in measure_dict["sql"]
        assert "${searches.search_count}" in measure_dict["sql"]
        assert measure_dict["required_fields"] == ["searches.search_count"]

    def test_generate_metric_measure_required_fields(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test that required_fields is populated for cross-view ratio metrics.

        Simple metrics no longer have required_fields (they're direct aggregates).
        Ratio metrics still need required_fields for cross-view measure references.
        """
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]
        measure_dict = generator._generate_metric_measure(
            metric, primary_model, all_models
        )

        assert "required_fields" in measure_dict
        assert measure_dict["required_fields"] == ["searches.search_count_measure"]

    def test_generate_metric_measure_no_required_fields(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test that required_fields is absent for same-view metrics."""
        metric = Metric(
            name="total_orders",
            type="simple",
            type_params=SimpleMetricParams(measure="order_count"),
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]
        measure_dict = generator._generate_metric_measure(
            metric, primary_model, all_models
        )

        assert "required_fields" not in measure_dict

    def test_generate_metric_measure_labels(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test that label and description are included."""
        metric = Metric(
            name="total_orders",
            type="simple",
            type_params=SimpleMetricParams(measure="order_count"),
            label="Total Orders",
            description="Count of all orders",
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]
        measure_dict = generator._generate_metric_measure(
            metric, primary_model, all_models
        )

        assert measure_dict["label"] == "Total Orders"
        assert measure_dict["description"] == "Count of all orders"

    def test_generate_metric_measure_view_label(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test that view_label is always ' Metrics' with leading space."""
        metric = Metric(
            name="total_orders",
            type="simple",
            type_params=SimpleMetricParams(measure="order_count"),
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]
        measure_dict = generator._generate_metric_measure(
            metric, primary_model, all_models
        )

        assert measure_dict["view_label"] == "  Metrics"
        assert measure_dict["view_label"].startswith(" ")

    def test_generate_metric_measure_group_label(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test that group_label is inferred correctly."""
        metric = Metric(
            name="total_orders",
            type="simple",
            type_params=SimpleMetricParams(measure="order_count"),
            meta={"primary_entity": "order", "category": "sales_metrics"},
        )
        primary_model = all_models[0]
        measure_dict = generator._generate_metric_measure(
            metric, primary_model, all_models
        )

        assert measure_dict["group_label"] == "Sales Metrics"

    def test_generate_metric_measure_value_format(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test that value_format_name is inferred correctly."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(
                numerator="order_count", denominator="search_count"
            ),
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]
        measure_dict = generator._generate_metric_measure(
            metric, primary_model, all_models
        )

        assert measure_dict["value_format_name"] == "percent_2"

    def test_generate_metric_measure_unsupported_type(
        self, generator: LookMLGenerator, all_models: list[SemanticModel]
    ) -> None:
        """Test that unsupported metric type raises ValueError."""
        from dbt_to_lookml.schemas import ConversionMetricParams

        metric = Metric(
            name="checkout_conversion",
            type="conversion",
            type_params=ConversionMetricParams(
                conversion_type_params={"entity": "order"}
            ),
            meta={"primary_entity": "order"},
        )
        primary_model = all_models[0]

        with pytest.raises(ValueError, match="Unsupported metric type"):
            generator._generate_metric_measure(metric, primary_model, all_models)


class TestMetricIntegration:
    """Test integration of metrics with view generation."""

    @pytest.fixture
    def all_models(self) -> list[SemanticModel]:
        """Create test semantic models."""
        return [
            SemanticModel(
                name="orders",
                model="ref('orders')",
                entities=[Entity(name="order", type="primary")],
                measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
            ),
            SemanticModel(
                name="searches",
                model="ref('searches')",
                entities=[Entity(name="search", type="primary")],
                measures=[Measure(name="search_count", agg=AggregationType.COUNT)],
            ),
        ]

    def test_generate_without_metrics(self, all_models: list[SemanticModel]) -> None:
        """Test generate method without metrics parameter (backward compatible)."""
        generator = LookMLGenerator()
        files = generator.generate(all_models)

        assert len(files) > 0
        assert "orders.view.lkml" in files
        assert "searches.view.lkml" in files

    def test_generate_with_metrics(self, all_models: list[SemanticModel]) -> None:
        """Test generate method with metrics parameter."""
        generator = LookMLGenerator()
        metrics = [
            Metric(
                name="total_orders",
                type="simple",
                type_params=SimpleMetricParams(measure="order_count"),
                meta={"primary_entity": "order"},
            )
        ]
        files = generator.generate(all_models, metrics)

        assert len(files) > 0
        assert "orders.view.lkml" in files
        # Check that the metric is in the orders view
        assert "total_orders" in files["orders.view.lkml"]

    def test_generate_metric_ownership(self, all_models: list[SemanticModel]) -> None:
        """Test that metrics are added to correct views based on primary_entity."""
        generator = LookMLGenerator()
        metrics = [
            Metric(
                name="total_orders",
                type="simple",
                type_params=SimpleMetricParams(measure="order_count"),
                meta={"primary_entity": "order"},
            ),
            Metric(
                name="total_searches",
                type="simple",
                type_params=SimpleMetricParams(measure="search_count"),
                meta={"primary_entity": "search"},
            ),
        ]
        files = generator.generate(all_models, metrics)

        # total_orders should be in orders view
        assert "total_orders" in files["orders.view.lkml"]
        assert "total_orders" not in files["searches.view.lkml"]

        # total_searches should be in searches view
        assert "total_searches" in files["searches.view.lkml"]
        assert "total_searches" not in files["orders.view.lkml"]

    def test_generate_metrics_appended(self, all_models: list[SemanticModel]) -> None:
        """Test that metrics are generated in view files.

        With smart optimization, simple metrics generate as direct aggregates.
        Hidden _measure versions are only created when needed by complex metrics.
        """
        generator = LookMLGenerator()
        metrics = [
            Metric(
                name="total_orders",
                type="simple",
                type_params=SimpleMetricParams(measure="order_count"),
                meta={"primary_entity": "order"},
            )
        ]
        files = generator.generate(all_models, metrics)

        # Metric should be present as a direct aggregate measure
        assert "total_orders" in files["orders.view.lkml"]
        # With smart optimization, hidden _measure versions are not created
        # unless needed by complex metrics (ratio, derived)

    def test_generate_missing_primary_entity_warning(
        self, all_models: list[SemanticModel]
    ) -> None:
        """Test error when metric has no primary_entity."""
        from dbt_to_lookml.generators.lookml import LookMLValidationError

        generator = LookMLGenerator()
        metrics = [
            Metric(
                name="orphan_metric",
                type="simple",
                type_params=SimpleMetricParams(measure="order_count"),
            )
        ]

        # Should raise validation error for missing primary_entity
        with pytest.raises(LookMLValidationError):
            generator.generate(all_models, metrics)

    def test_generate_unknown_primary_entity_warning(
        self, all_models: list[SemanticModel]
    ) -> None:
        """Test error when primary_entity doesn't match any model."""
        from dbt_to_lookml.generators.lookml import LookMLValidationError

        generator = LookMLGenerator()
        metrics = [
            Metric(
                name="orphan_metric",
                type="simple",
                type_params=SimpleMetricParams(measure="order_count"),
                meta={"primary_entity": "nonexistent"},
            )
        ]

        # Should raise validation error for invalid primary_entity
        with pytest.raises(LookMLValidationError):
            generator.generate(all_models, metrics)

    def test_generate_metric_error_handling(
        self, all_models: list[SemanticModel]
    ) -> None:
        """Test error handling during metric generation."""
        from dbt_to_lookml.generators.lookml import LookMLValidationError

        generator = LookMLGenerator()
        # Create a metric that will cause an error
        # (missing measure and invalid primary_entity)
        metrics = [
            Metric(
                name="broken_metric",
                type="simple",
                type_params=SimpleMetricParams(measure="nonexistent_measure"),
                meta={"primary_entity": "order"},
            )
        ]

        # Should raise validation error for invalid primary_entity
        # or missing measure
        with pytest.raises(LookMLValidationError):
            generator.generate(all_models, metrics)
