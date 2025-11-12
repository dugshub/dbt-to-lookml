"""Unit tests for schema models using new architecture."""

import pytest
from pydantic import ValidationError

from dbt_to_lookml.types import (
    AggregationType,
    DimensionType,
    TimeGranularity,
)
from dbt_to_lookml.schemas import (
    Config,
    ConfigMeta,
    Dimension,
    Entity,
    LookMLDimension,
    LookMLDimensionGroup,
    LookMLExplore,
    LookMLMeasure,
    LookMLView,
    Measure,
    SemanticModel,
)


class TestEntity:
    """Test cases for Entity model."""

    def test_entity_creation(self) -> None:
        """Test basic entity creation."""
        entity = Entity(name="user_id", type="primary")
        assert entity.name == "user_id"
        assert entity.type == "primary"
        assert entity.expr is None
        assert entity.description is None

    def test_entity_with_optional_fields(self) -> None:
        """Test entity creation with optional fields."""
        entity = Entity(
            name="user_id",
            type="primary",
            expr="users.id",
            description="Unique user identifier",
        )
        assert entity.name == "user_id"
        assert entity.type == "primary"
        assert entity.expr == "users.id"
        assert entity.description == "Unique user identifier"

    def test_entity_types(self) -> None:
        """Test different entity types."""
        primary_entity = Entity(name="id", type="primary")
        foreign_entity = Entity(name="customer_id", type="foreign")
        unique_entity = Entity(name="email", type="unique")

        assert primary_entity.type == "primary"
        assert foreign_entity.type == "foreign"
        assert unique_entity.type == "unique"

    def test_entity_with_complex_expression(self) -> None:
        """Test entity with complex SQL expression."""
        entity = Entity(
            name="composite_key",
            type="primary",
            expr="CONCAT(customer_id, '_', order_id)",
            description="Composite primary key"
        )
        assert entity.expr == "CONCAT(customer_id, '_', order_id)"
        assert entity.description == "Composite primary key"

    def test_entity_validation(self) -> None:
        """Test entity field validation."""
        # Test that name is required
        with pytest.raises(ValidationError):
            Entity(type="primary")  # Missing name

        # Test that type is required
        with pytest.raises(ValidationError):
            Entity(name="id")  # Missing type

    def test_entity_to_lookml_primary_hidden(self) -> None:
        """Test that primary entities are hidden in LookML output."""
        entity = Entity(name="user_id", type="primary", description="User identifier")
        lookml_dict = entity.to_lookml_dict(is_fact_table=False)

        assert lookml_dict['name'] == "user_id"
        assert lookml_dict['type'] == "string"
        assert lookml_dict['primary_key'] == "yes"
        assert lookml_dict['hidden'] == "yes"
        assert lookml_dict['sql'] == "${TABLE}.user_id"

    def test_entity_to_lookml_foreign_hidden(self) -> None:
        """Test that foreign entities are hidden in LookML output."""
        entity = Entity(name="customer_id", type="foreign", description="Foreign key")
        lookml_dict = entity.to_lookml_dict(is_fact_table=False)

        assert lookml_dict['name'] == "customer_id"
        assert lookml_dict['type'] == "string"
        assert lookml_dict['hidden'] == "yes"
        assert 'primary_key' not in lookml_dict

    def test_entity_to_lookml_unique_hidden(self) -> None:
        """Test that unique entities are hidden in LookML output."""
        entity = Entity(name="email", type="unique", description="Unique email")
        lookml_dict = entity.to_lookml_dict(is_fact_table=False)

        assert lookml_dict['name'] == "email"
        assert lookml_dict['type'] == "string"
        assert lookml_dict['hidden'] == "yes"
        assert 'primary_key' not in lookml_dict

    def test_entity_to_lookml_with_custom_expr(self) -> None:
        """Test that entities with custom expressions are hidden."""
        entity = Entity(
            name="composite_key",
            type="primary",
            expr="CONCAT(user_id, '_', order_id)"
        )
        lookml_dict = entity.to_lookml_dict(is_fact_table=True, view_label="Orders")

        assert lookml_dict['sql'] == "CONCAT(user_id, '_', order_id)"
        assert lookml_dict['hidden'] == "yes"
        assert lookml_dict['primary_key'] == "yes"


class TestDimension:
    """Test cases for Dimension model."""

    def test_dimension_creation(self) -> None:
        """Test basic dimension creation."""
        dimension = Dimension(name="status", type=DimensionType.CATEGORICAL)
        assert dimension.name == "status"
        assert dimension.type == DimensionType.CATEGORICAL

    def test_time_dimension(self) -> None:
        """Test time dimension creation."""
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )
        assert dimension.name == "created_at"
        assert dimension.type == DimensionType.TIME
        assert dimension.type_params == {"time_granularity": "day"}

    def test_dimension_with_all_fields(self) -> None:
        """Test dimension with all optional fields."""
        dimension = Dimension(
            name="user_status",
            type=DimensionType.CATEGORICAL,
            expr="UPPER(status)",
            description="User account status",
            label="User Status",
            type_params={"custom_param": "value"}
        )
        assert dimension.name == "user_status"
        assert dimension.type == DimensionType.CATEGORICAL
        assert dimension.expr == "UPPER(status)"
        assert dimension.description == "User account status"
        assert dimension.label == "User Status"
        assert dimension.type_params == {"custom_param": "value"}

    def test_time_dimension_with_params(self) -> None:
        """Test time dimension with type parameters."""
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={
                "time_granularity": "day",
                "format": "yyyy-MM-dd"
            }
        )
        assert dimension.type == DimensionType.TIME
        assert dimension.type_params["time_granularity"] == "day"
        assert dimension.type_params["format"] == "yyyy-MM-dd"

    def test_dimension_validation(self) -> None:
        """Test dimension field validation."""
        # Test that name is required
        with pytest.raises(ValidationError):
            Dimension(type=DimensionType.CATEGORICAL)  # Missing name

        # Test that type is required
        with pytest.raises(ValidationError):
            Dimension(name="status")  # Missing type

    def test_dimension_with_case_statement(self) -> None:
        """Test dimension with complex CASE statement."""
        case_expr = """CASE
            WHEN status = 'active' AND created_at > '2023-01-01' THEN 'new_active'
            WHEN status = 'inactive' THEN 'inactive'
            ELSE 'other'
        END"""

        dimension = Dimension(
            name="status_category",
            type=DimensionType.CATEGORICAL,
            expr=case_expr
        )
        assert "CASE" in dimension.expr
        assert "WHEN status = 'active'" in dimension.expr
        assert "ELSE 'other'" in dimension.expr


class TestMeasure:
    """Test cases for Measure model."""

    def test_measure_creation(self) -> None:
        """Test basic measure creation."""
        measure = Measure(name="total_revenue", agg=AggregationType.SUM)
        assert measure.name == "total_revenue"
        assert measure.agg == AggregationType.SUM

    def test_count_measure(self) -> None:
        """Test count measure creation."""
        measure = Measure(
            name="user_count",
            agg=AggregationType.COUNT,
            create_metric=True,
        )
        assert measure.name == "user_count"
        assert measure.agg == AggregationType.COUNT
        assert measure.create_metric is True

    def test_measure_with_all_fields(self) -> None:
        """Test measure with all optional fields."""
        measure = Measure(
            name="total_revenue",
            agg=AggregationType.SUM,
            expr="amount * quantity",
            description="Total revenue calculation",
            label="Total Revenue",
            create_metric=True,
            non_additive_dimension={"name": "customer_id", "window_choice": "max"}
        )
        assert measure.name == "total_revenue"
        assert measure.agg == AggregationType.SUM
        assert measure.expr == "amount * quantity"
        assert measure.description == "Total revenue calculation"
        assert measure.label == "Total Revenue"
        assert measure.create_metric is True
        assert measure.non_additive_dimension is not None

    def test_all_aggregation_types(self) -> None:
        """Test measures with all aggregation types."""
        measures = [
            Measure(name="count_all", agg=AggregationType.COUNT),
            Measure(name="unique_customers", agg=AggregationType.COUNT_DISTINCT, expr="customer_id"),
            Measure(name="total_amount", agg=AggregationType.SUM, expr="amount"),
            Measure(name="avg_amount", agg=AggregationType.AVERAGE, expr="amount"),
            Measure(name="min_amount", agg=AggregationType.MIN, expr="amount"),
            Measure(name="max_amount", agg=AggregationType.MAX, expr="amount"),
            Measure(name="median_amount", agg=AggregationType.MEDIAN, expr="amount"),
        ]

        assert len(measures) == 7
        assert measures[0].agg == AggregationType.COUNT
        assert measures[1].agg == AggregationType.COUNT_DISTINCT
        assert measures[2].agg == AggregationType.SUM
        assert measures[3].agg == AggregationType.AVERAGE
        assert measures[4].agg == AggregationType.MIN
        assert measures[5].agg == AggregationType.MAX
        assert measures[6].agg == AggregationType.MEDIAN

    def test_measure_validation(self) -> None:
        """Test measure field validation."""
        # Test that name is required
        with pytest.raises(ValidationError):
            Measure(agg=AggregationType.COUNT)  # Missing name

        # Test that agg is required
        with pytest.raises(ValidationError):
            Measure(name="test_measure")  # Missing agg

    def test_measure_with_filter_expression(self) -> None:
        """Test measure with filtering expression."""
        measure = Measure(
            name="active_user_count",
            agg=AggregationType.COUNT,
            expr="CASE WHEN status = 'active' THEN user_id END",
            description="Count of active users only"
        )
        assert "CASE WHEN status = 'active'" in measure.expr
        assert measure.description == "Count of active users only"


class TestSemanticModel:
    """Test cases for SemanticModel."""

    def test_semantic_model_creation(self) -> None:
        """Test basic semantic model creation."""
        model = SemanticModel(name="users", model="dim_users")
        assert model.name == "users"
        assert model.model == "dim_users"
        assert len(model.entities) == 0
        assert len(model.dimensions) == 0
        assert len(model.measures) == 0

    def test_semantic_model_with_components(self) -> None:
        """Test semantic model with entities, dimensions, and measures."""
        entity = Entity(name="user_id", type="primary")
        dimension = Dimension(name="status", type=DimensionType.CATEGORICAL)
        measure = Measure(name="user_count", agg=AggregationType.COUNT)

        model = SemanticModel(
            name="users",
            model="dim_users",
            entities=[entity],
            dimensions=[dimension],
            measures=[measure],
        )

        assert len(model.entities) == 1
        assert len(model.dimensions) == 1
        assert len(model.measures) == 1
        assert model.entities[0].name == "user_id"
        assert model.dimensions[0].name == "status"
        assert model.measures[0].name == "user_count"

    def test_semantic_model_with_config(self) -> None:
        """Test semantic model with configuration."""
        config = Config(meta=ConfigMeta(domain="sales", owner="Team"))
        model = SemanticModel(
            name="sales_orders",
            model="ref('fact_orders')",
            description="Sales order semantic model",
            config=config
        )
        assert model.config is not None
        assert model.config.meta.domain == "sales"
        assert model.config.meta.owner == "Team"

    def test_semantic_model_with_defaults(self) -> None:
        """Test semantic model with defaults configuration."""
        model = SemanticModel(
            name="events",
            model="fact_events",
            defaults={"agg_time_dimension": "created_at"}
        )
        assert model.defaults is not None
        assert model.defaults["agg_time_dimension"] == "created_at"

    def test_semantic_model_validation(self) -> None:
        """Test semantic model field validation."""
        # Test that name is required
        with pytest.raises(ValidationError):
            SemanticModel(model="test_table")  # Missing name

        # Test that model is required
        with pytest.raises(ValidationError):
            SemanticModel(name="test")  # Missing model

    def test_complex_semantic_model(self) -> None:
        """Test complex semantic model with all components."""
        entities = [
            Entity(name="order_id", type="primary", expr="id"),
            Entity(name="customer_id", type="foreign")
        ]

        dimensions = [
            Dimension(name="status", type=DimensionType.CATEGORICAL),
            Dimension(
                name="created_date",
                type=DimensionType.TIME,
                type_params={"time_granularity": "day"}
            ),
            Dimension(
                name="category",
                type=DimensionType.CATEGORICAL,
                expr="CASE WHEN amount > 100 THEN 'high_value' ELSE 'standard' END"
            )
        ]

        measures = [
            Measure(name="order_count", agg=AggregationType.COUNT),
            Measure(name="total_revenue", agg=AggregationType.SUM, expr="amount"),
            Measure(name="unique_customers", agg=AggregationType.COUNT_DISTINCT, expr="customer_id")
        ]

        config = Config(meta=ConfigMeta(
            domain="commerce",
            owner="Data Team",
            contains_pii=False
        ))

        model = SemanticModel(
            name="order_analytics",
            model="ref('fact_orders')",
            description="Order analytics semantic model",
            config=config,
            entities=entities,
            dimensions=dimensions,
            measures=measures,
            defaults={"agg_time_dimension": "created_date"}
        )

        assert len(model.entities) == 2
        assert len(model.dimensions) == 3
        assert len(model.measures) == 3
        assert model.config.meta.domain == "commerce"
        assert model.defaults["agg_time_dimension"] == "created_date"


class TestConfigMeta:
    """Test cases for ConfigMeta model."""

    def test_config_meta_creation(self) -> None:
        """Test basic config meta creation."""
        meta = ConfigMeta(domain="sales")
        assert meta.domain == "sales"
        assert meta.owner is None
        assert meta.contains_pii is None
        assert meta.update_frequency is None

    def test_config_meta_with_all_fields(self) -> None:
        """Test config meta with all fields."""
        meta = ConfigMeta(
            domain="sales",
            owner="Analytics Team",
            contains_pii=True,
            update_frequency="daily"
        )
        assert meta.domain == "sales"
        assert meta.owner == "Analytics Team"
        assert meta.contains_pii is True
        assert meta.update_frequency == "daily"


class TestConfig:
    """Test cases for Config model."""

    def test_config_creation(self) -> None:
        """Test basic config creation."""
        config = Config()
        assert config.meta is None

    def test_config_with_meta(self) -> None:
        """Test config with metadata."""
        meta = ConfigMeta(domain="sales", owner="Team")
        config = Config(meta=meta)
        assert config.meta is not None
        assert config.meta.domain == "sales"
        assert config.meta.owner == "Team"


class TestLookMLModels:
    """Test cases for LookML data models."""

    def test_lookml_dimension_creation(self) -> None:
        """Test LookML dimension creation."""
        dimension = LookMLDimension(
            name="user_id",
            type="string",
            sql="${TABLE}.user_id",
            description="User identifier",
            primary_key=True,
            hidden=False
        )
        assert dimension.name == "user_id"
        assert dimension.type == "string"
        assert dimension.sql == "${TABLE}.user_id"
        assert dimension.primary_key is True
        assert dimension.hidden is False

    def test_lookml_dimension_group_creation(self) -> None:
        """Test LookML dimension group creation."""
        dim_group = LookMLDimensionGroup(
            name="created",
            type="time",
            timeframes=["date", "week", "month", "year"],
            sql="${TABLE}.created_at",
            description="Creation timestamp",
            label="Created At"
        )
        assert dim_group.name == "created"
        assert dim_group.type == "time"
        assert "date" in dim_group.timeframes
        assert "year" in dim_group.timeframes
        assert dim_group.label == "Created At"

    def test_lookml_measure_creation(self) -> None:
        """Test LookML measure creation."""
        measure = LookMLMeasure(
            name="total_count",
            type="count",
            sql="1",
            description="Total record count",
            hidden=False
        )
        assert measure.name == "total_count"
        assert measure.type == "count"
        assert measure.sql == "1"
        assert measure.hidden is False

    def test_lookml_view_creation(self) -> None:
        """Test LookML view creation."""
        dimensions = [
            LookMLDimension(name="id", type="string", sql="${TABLE}.id")
        ]
        measures = [
            LookMLMeasure(name="count", type="count", sql="1")
        ]

        view = LookMLView(
            name="users",
            sql_table_name="dim_users",
            description="User dimension",
            dimensions=dimensions,
            measures=measures
        )

        assert view.name == "users"
        assert view.sql_table_name == "dim_users"
        assert len(view.dimensions) == 1
        assert len(view.measures) == 1
        assert len(view.dimension_groups) == 0

    def test_lookml_explore_creation(self) -> None:
        """Test LookML explore creation."""
        explore = LookMLExplore(
            name="user_analysis",
            view_name="users",
            description="User data exploration",
            type="table",
            joins=[]
        )

        assert explore.name == "user_analysis"
        assert explore.view_name == "users"
        assert explore.type == "table"
        assert len(explore.joins) == 0

    def test_lookml_view_with_dimension_groups(self) -> None:
        """Test LookML view with dimension groups."""
        dimension_groups = [
            LookMLDimensionGroup(
                name="created",
                type="time",
                timeframes=["date", "month"],
                sql="${TABLE}.created_at"
            )
        ]

        view = LookMLView(
            name="events",
            sql_table_name="fact_events",
            dimension_groups=dimension_groups
        )

        assert len(view.dimension_groups) == 1
        assert view.dimension_groups[0].name == "created"

    def test_lookml_models_validation(self) -> None:
        """Test validation of LookML models."""
        # Test that name is required for all models
        with pytest.raises(ValidationError):
            LookMLDimension(type="string", sql="${TABLE}.field")  # Missing name

        with pytest.raises(ValidationError):
            LookMLMeasure(type="count", sql="1")  # Missing name

        with pytest.raises(ValidationError):
            LookMLView(sql_table_name="table")  # Missing name