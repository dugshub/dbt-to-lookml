"""Unit tests for schema models using new architecture."""

import pytest
from pydantic import ValidationError

from dbt_to_lookml.schemas import (
    Config,
    ConfigMeta,
    Dimension,
    Entity,
    LookMLDimension,
    LookMLDimensionGroup,
    LookMLExplore,
    LookMLMeasure,
    LookMLSet,
    LookMLView,
    Measure,
    SemanticModel,
)
from dbt_to_lookml.types import (
    AggregationType,
    DimensionType,
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
            description="Composite primary key",
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

        assert lookml_dict["name"] == "user_id"
        assert lookml_dict["type"] == "string"
        assert lookml_dict["primary_key"] == "yes"
        assert lookml_dict["hidden"] == "yes"
        assert lookml_dict["sql"] == "${TABLE}.user_id"

    def test_entity_to_lookml_foreign_hidden(self) -> None:
        """Test that foreign entities are hidden in LookML output."""
        entity = Entity(name="customer_id", type="foreign", description="Foreign key")
        lookml_dict = entity.to_lookml_dict(is_fact_table=False)

        assert lookml_dict["name"] == "customer_id"
        assert lookml_dict["type"] == "string"
        assert lookml_dict["hidden"] == "yes"
        assert "primary_key" not in lookml_dict

    def test_entity_to_lookml_unique_hidden(self) -> None:
        """Test that unique entities are hidden in LookML output."""
        entity = Entity(name="email", type="unique", description="Unique email")
        lookml_dict = entity.to_lookml_dict(is_fact_table=False)

        assert lookml_dict["name"] == "email"
        assert lookml_dict["type"] == "string"
        assert lookml_dict["hidden"] == "yes"
        assert "primary_key" not in lookml_dict

    def test_entity_to_lookml_with_custom_expr(self) -> None:
        """Test that entities with custom expressions are hidden."""
        entity = Entity(
            name="composite_key", type="primary", expr="CONCAT(user_id, '_', order_id)"
        )
        lookml_dict = entity.to_lookml_dict(is_fact_table=True, view_label="Orders")

        assert lookml_dict["sql"] == "CONCAT(user_id, '_', order_id)"
        assert lookml_dict["hidden"] == "yes"
        assert lookml_dict["primary_key"] == "yes"

    def test_entity_expr_qualification_simple_column(self) -> None:
        """Test that simple column names in expr get qualified with ${TABLE}."""
        # Simple column name should be qualified
        entity = Entity(name="facility_sk", type="foreign", expr="id")
        lookml_dict = entity.to_lookml_dict()
        assert lookml_dict["sql"] == "${TABLE}.id"

        # Column with underscores should also be qualified
        entity2 = Entity(name="user_key", type="foreign", expr="facility_sk")
        lookml_dict2 = entity2.to_lookml_dict()
        assert lookml_dict2["sql"] == "${TABLE}.facility_sk"

    def test_entity_expr_qualification_already_qualified(self) -> None:
        """Test that expressions already containing ${TABLE} are unchanged."""
        entity = Entity(name="user_id", type="primary", expr="${TABLE}.id")
        lookml_dict = entity.to_lookml_dict()
        assert lookml_dict["sql"] == "${TABLE}.id"

        # With other LookML references
        entity2 = Entity(name="ref_id", type="foreign", expr="${other_view.id}")
        lookml_dict2 = entity2.to_lookml_dict()
        assert lookml_dict2["sql"] == "${other_view.id}"

    def test_entity_expr_qualification_none_default(self) -> None:
        """Test that None expr defaults to ${TABLE}.{name}."""
        entity = Entity(name="user_id", type="primary")
        lookml_dict = entity.to_lookml_dict()
        assert lookml_dict["sql"] == "${TABLE}.user_id"

    def test_entity_expr_qualification_complex_expression(self) -> None:
        """Test that complex expressions are left as-is."""
        # Expression with functions
        entity = Entity(
            name="full_name", type="unique", expr="CONCAT(first_name, ' ', last_name)"
        )
        lookml_dict = entity.to_lookml_dict()
        # Complex expressions with spaces and functions are not auto-qualified
        assert lookml_dict["sql"] == "CONCAT(first_name, ' ', last_name)"

        # Expression with CASE statement
        entity2 = Entity(
            name="status_code",
            type="primary",
            expr="CASE WHEN active THEN 1 ELSE 0 END",
        )
        lookml_dict2 = entity2.to_lookml_dict()
        assert lookml_dict2["sql"] == "CASE WHEN active THEN 1 ELSE 0 END"

    def test_entity_expr_qualification_with_cast(self) -> None:
        """Test expressions with CAST are left as-is."""
        entity = Entity(
            name="user_id_str", type="primary", expr="CAST(user_id AS VARCHAR)"
        )
        lookml_dict = entity.to_lookml_dict()
        assert lookml_dict["sql"] == "CAST(user_id AS VARCHAR)"


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
            type_params={"custom_param": "value"},
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
            type_params={"time_granularity": "day", "format": "yyyy-MM-dd"},
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
            name="status_category", type=DimensionType.CATEGORICAL, expr=case_expr
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
            non_additive_dimension={"name": "customer_id", "window_choice": "max"},
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
            Measure(
                name="unique_customers",
                agg=AggregationType.COUNT_DISTINCT,
                expr="customer_id",
            ),
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
            description="Count of active users only",
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
            config=config,
        )
        assert model.config is not None
        assert model.config.meta.domain == "sales"
        assert model.config.meta.owner == "Team"

    def test_semantic_model_with_defaults(self) -> None:
        """Test semantic model with defaults configuration."""
        model = SemanticModel(
            name="events",
            model="fact_events",
            defaults={"agg_time_dimension": "created_at"},
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
            Entity(name="customer_id", type="foreign"),
        ]

        dimensions = [
            Dimension(name="status", type=DimensionType.CATEGORICAL),
            Dimension(
                name="created_date",
                type=DimensionType.TIME,
                type_params={"time_granularity": "day"},
            ),
            Dimension(
                name="category",
                type=DimensionType.CATEGORICAL,
                expr="CASE WHEN amount > 100 THEN 'high_value' ELSE 'standard' END",
            ),
        ]

        measures = [
            Measure(name="order_count", agg=AggregationType.COUNT),
            Measure(name="total_revenue", agg=AggregationType.SUM, expr="amount"),
            Measure(
                name="unique_customers",
                agg=AggregationType.COUNT_DISTINCT,
                expr="customer_id",
            ),
        ]

        config = Config(
            meta=ConfigMeta(domain="commerce", owner="Data Team", contains_pii=False)
        )

        model = SemanticModel(
            name="order_analytics",
            model="ref('fact_orders')",
            description="Order analytics semantic model",
            config=config,
            entities=entities,
            dimensions=dimensions,
            measures=measures,
            defaults={"agg_time_dimension": "created_date"},
        )

        assert len(model.entities) == 2
        assert len(model.dimensions) == 3
        assert len(model.measures) == 3
        assert model.config.meta.domain == "commerce"
        assert model.defaults["agg_time_dimension"] == "created_date"

    def test_semantic_model_dimension_set_generation(self) -> None:
        """Test that semantic model generates dimension sets correctly."""
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

        lookml_dict = model.to_lookml_dict()

        # Verify sets are present in the output
        assert "views" in lookml_dict
        assert len(lookml_dict["views"]) == 1
        view = lookml_dict["views"][0]
        assert "sets" in view
        assert len(view["sets"]) > 0

        # Verify dimensions_only set exists
        dimension_set = next(
            (s for s in view["sets"] if s["name"] == "dimensions_only"), None
        )
        assert dimension_set is not None

        # Verify all dimension fields are in the set
        assert "user_id" in dimension_set["fields"]  # entity
        assert "status" in dimension_set["fields"]  # dimension

    def test_semantic_model_dimension_set_with_time_dimensions(self) -> None:
        """Test dimension set includes time dimension names (dimension_groups)."""
        entity = Entity(name="event_id", type="primary")
        time_dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )
        regular_dim = Dimension(name="event_type", type=DimensionType.CATEGORICAL)

        model = SemanticModel(
            name="events",
            model="fact_events",
            entities=[entity],
            dimensions=[time_dim, regular_dim],
        )

        lookml_dict = model.to_lookml_dict()
        view = lookml_dict["views"][0]

        # Verify dimension_groups are in the view
        assert "dimension_groups" in view
        assert len(view["dimension_groups"]) > 0

        # Verify dimension set includes time dimension base name
        dimension_set = next(
            (s for s in view["sets"] if s["name"] == "dimensions_only"), None
        )
        assert dimension_set is not None
        assert "created_at" in dimension_set["fields"]
        assert "event_type" in dimension_set["fields"]
        assert "event_id" in dimension_set["fields"]

    def test_semantic_model_no_dimension_set_when_no_dimensions(self) -> None:
        """Test that no dimension set is generated when there are no dimensions."""
        measure = Measure(name="total", agg=AggregationType.SUM)

        model = SemanticModel(
            name="metrics",
            model="fact_metrics",
            measures=[measure],
        )

        lookml_dict = model.to_lookml_dict()
        view = lookml_dict["views"][0]

        # Verify no sets when no dimensions
        assert "sets" not in view or len(view.get("sets", [])) == 0

    def test_semantic_model_dimension_set_includes_hidden_entities(self) -> None:
        """Test that dimension set includes all entity types including foreign and unique."""
        primary_entity = Entity(name="order_id", type="primary")
        foreign_entity = Entity(name="customer_id", type="foreign")
        unique_entity = Entity(name="tracking_id", type="unique")
        dimension = Dimension(name="order_status", type=DimensionType.CATEGORICAL)

        model = SemanticModel(
            name="orders",
            model="fct_orders",
            entities=[primary_entity, foreign_entity, unique_entity],
            dimensions=[dimension],
            measures=[Measure(name="order_count", agg=AggregationType.COUNT)],
        )

        lookml_dict = model.to_lookml_dict()
        view = lookml_dict["views"][0]

        # Verify all entities are in the dimension set
        dimension_set = next(
            (s for s in view["sets"] if s["name"] == "dimensions_only"), None
        )
        assert dimension_set is not None
        assert "order_id" in dimension_set["fields"]
        assert "customer_id" in dimension_set["fields"]
        assert "tracking_id" in dimension_set["fields"]
        assert "order_status" in dimension_set["fields"]

    def test_semantic_model_dimension_set_with_schema(self) -> None:
        """Test that dimension set is generated correctly when schema is provided."""
        entity = Entity(name="user_id", type="primary")
        dimension = Dimension(name="status", type=DimensionType.CATEGORICAL)

        model = SemanticModel(
            name="users",
            model="dim_users",
            entities=[entity],
            dimensions=[dimension],
        )

        # Generate with schema
        lookml_dict = model.to_lookml_dict(schema="analytics")

        view = lookml_dict["views"][0]

        # Verify schema is applied to table name
        assert view["sql_table_name"] == "analytics.dim_users"

        # Verify dimension set is still generated
        dimension_set = next(
            (s for s in view["sets"] if s["name"] == "dimensions_only"), None
        )
        assert dimension_set is not None
        assert "user_id" in dimension_set["fields"]
        assert "status" in dimension_set["fields"]


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
            update_frequency="daily",
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
            hidden=False,
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
            label="Created At",
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
            hidden=False,
        )
        assert measure.name == "total_count"
        assert measure.type == "count"
        assert measure.sql == "1"
        assert measure.hidden is False

    def test_lookml_view_creation(self) -> None:
        """Test LookML view creation."""
        dimensions = [LookMLDimension(name="id", type="string", sql="${TABLE}.id")]
        measures = [LookMLMeasure(name="count", type="count", sql="1")]

        view = LookMLView(
            name="users",
            sql_table_name="dim_users",
            description="User dimension",
            dimensions=dimensions,
            measures=measures,
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
            joins=[],
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
                sql="${TABLE}.created_at",
            )
        ]

        view = LookMLView(
            name="events",
            sql_table_name="fact_events",
            dimension_groups=dimension_groups,
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

    def test_lookml_view_with_sets(self) -> None:
        """Test LookML view creation with sets."""
        sets = [
            LookMLSet(name="dimension_set", fields=["dim1", "dim2"]),
            LookMLSet(name="another_set", fields=["dim3"]),
        ]
        dimensions = [LookMLDimension(name="dim1", type="string", sql="${TABLE}.dim1")]

        view = LookMLView(
            name="test_view",
            sql_table_name="schema.table",
            sets=sets,
            dimensions=dimensions,
        )

        assert len(view.sets) == 2
        assert view.sets[0].name == "dimension_set"
        assert view.sets[1].name == "another_set"

    def test_lookml_view_without_sets_backward_compatibility(self) -> None:
        """Test LookML view creation without sets (backward compatibility)."""
        view = LookMLView(name="test_view", sql_table_name="schema.table")

        assert len(view.sets) == 0
        assert view.sets == []

    def test_lookml_view_to_lookml_dict_with_sets(self) -> None:
        """Test to_lookml_dict() includes sets in output."""
        sets = [
            LookMLSet(name="dimension_set", fields=["dim1", "dim2"]),
            LookMLSet(name="another_set", fields=["dim3"]),
        ]
        view = LookMLView(name="test_view", sql_table_name="schema.table", sets=sets)

        result = view.to_lookml_dict()
        view_dict = result["views"][0]

        assert "sets" in view_dict
        assert len(view_dict["sets"]) == 2
        assert view_dict["sets"][0]["name"] == "dimension_set"
        assert view_dict["sets"][0]["fields"] == ["dim1", "dim2"]
        assert view_dict["sets"][1]["name"] == "another_set"
        assert view_dict["sets"][1]["fields"] == ["dim3"]

    def test_lookml_view_to_lookml_dict_without_sets(self) -> None:
        """Test to_lookml_dict() omits sets when empty."""
        view = LookMLView(name="test_view", sql_table_name="schema.table")

        result = view.to_lookml_dict()
        view_dict = result["views"][0]

        assert "sets" not in view_dict

    def test_lookml_view_to_lookml_dict_sets_ordering(self) -> None:
        """Test that sets appear in correct order in to_lookml_dict() output."""
        sets = [LookMLSet(name="set1", fields=["f1"])]
        dimensions = [LookMLDimension(name="dim1", type="string", sql="${TABLE}.dim1")]
        measures = [LookMLMeasure(name="measure1", type="count", sql="1")]

        view = LookMLView(
            name="test_view",
            sql_table_name="schema.table",
            description="Test view",
            sets=sets,
            dimensions=dimensions,
            measures=measures,
        )

        result = view.to_lookml_dict()
        view_dict = result["views"][0]

        # Get dict keys in order
        keys = list(view_dict.keys())

        # Verify order: name -> sql_table_name -> description -> sets -> dimensions -> measures
        assert keys.index("name") < keys.index("sql_table_name")
        assert keys.index("sql_table_name") < keys.index("description")
        assert keys.index("description") < keys.index("sets")
        assert keys.index("sets") < keys.index("dimensions")
        assert keys.index("dimensions") < keys.index("measures")

    def test_lookml_view_to_lookml_dict_multiple_sets(self) -> None:
        """Test to_lookml_dict() with multiple sets."""
        sets = [
            LookMLSet(name="set1", fields=["f1", "f2"]),
            LookMLSet(name="set2", fields=["f3"]),
            LookMLSet(name="set3", fields=["f4", "f5", "f6"]),
        ]
        view = LookMLView(name="test_view", sql_table_name="schema.table", sets=sets)

        result = view.to_lookml_dict()
        view_dict = result["views"][0]

        assert len(view_dict["sets"]) == 3
        assert view_dict["sets"][0]["name"] == "set1"
        assert view_dict["sets"][1]["name"] == "set2"
        assert view_dict["sets"][2]["name"] == "set3"
        assert len(view_dict["sets"][2]["fields"]) == 3


class TestLookMLSet:
    """Test cases for LookMLSet model."""

    def test_lookml_set_creation(self) -> None:
        """Test basic LookMLSet creation."""
        set_obj = LookMLSet(name="test_set", fields=["dim1", "dim2"])
        assert set_obj.name == "test_set"
        assert set_obj.fields == ["dim1", "dim2"]

    def test_lookml_set_with_multiple_fields(self) -> None:
        """Test LookMLSet with multiple fields."""
        fields = ["field1", "field2", "field3", "field4", "field5"]
        set_obj = LookMLSet(name="multi_set", fields=fields)
        assert set_obj.name == "multi_set"
        assert set_obj.fields == fields
        assert len(set_obj.fields) == 5

    def test_lookml_set_with_empty_fields(self) -> None:
        """Test LookMLSet with empty fields list."""
        set_obj = LookMLSet(name="empty_set", fields=[])
        assert set_obj.name == "empty_set"
        assert set_obj.fields == []

    def test_lookml_set_validation_missing_name(self) -> None:
        """Test that LookMLSet validation fails without name."""
        with pytest.raises(ValidationError):
            LookMLSet(fields=["dim1", "dim2"])  # Missing name

    def test_lookml_set_validation_missing_fields(self) -> None:
        """Test that LookMLSet validation fails without fields."""
        with pytest.raises(ValidationError):
            LookMLSet(name="test_set")  # Missing fields
