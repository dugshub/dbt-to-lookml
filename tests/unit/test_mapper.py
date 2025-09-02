"""Unit tests for semantic model mapper."""

from unittest.mock import patch

import pytest

from dbt_to_lookml.mapper import SemanticModelMapper
from dbt_to_lookml.models import (
    AggregationType,
    Config,
    ConfigMeta,
    Dimension,
    DimensionType,
    Entity,
    LookMLDimension,
    LookMLDimensionGroup,
    LookMLExplore,
    LookMLMeasure,
    LookMLView,
    Measure,
    SemanticModel,
    TimeGranularity,
)


class TestSemanticModelMapper:
    """Test cases for SemanticModelMapper."""

    def test_mapper_initialization(self) -> None:
        """Test mapper initialization with and without prefixes."""
        # Default initialization
        mapper = SemanticModelMapper()
        assert mapper.view_prefix == ""
        assert mapper.explore_prefix == ""

        # With prefixes
        mapper_with_prefixes = SemanticModelMapper(
            view_prefix="v_", explore_prefix="e_"
        )
        assert mapper_with_prefixes.view_prefix == "v_"
        assert mapper_with_prefixes.explore_prefix == "e_"

    def test_simple_semantic_model_to_view(self) -> None:
        """Test converting a simple semantic model to LookML view."""
        mapper = SemanticModelMapper()

        # Create a simple semantic model
        semantic_model = SemanticModel(
            name="users",
            model="dim_users",
            description="User dimension table",
            entities=[
                Entity(name="user_id", type="primary", description="Primary key")
            ],
            dimensions=[
                Dimension(
                    name="status",
                    type=DimensionType.CATEGORICAL,
                    description="User status"
                )
            ],
            measures=[
                Measure(
                    name="user_count",
                    agg=AggregationType.COUNT,
                    description="Total user count"
                )
            ]
        )

        # Convert to view
        view = mapper.semantic_model_to_view(semantic_model)

        # Verify view properties
        assert view.name == "users"
        assert view.sql_table_name == "dim_users"
        assert view.description == "User dimension table"

        # Verify dimensions (including primary entity)
        assert len(view.dimensions) == 2  # primary entity + regular dimension
        primary_dim = next(d for d in view.dimensions if d.primary_key)
        assert primary_dim.name == "user_id"
        assert primary_dim.primary_key is True

        status_dim = next(d for d in view.dimensions if d.name == "status")
        assert status_dim.type == "string"
        assert status_dim.sql == "${TABLE}.status"

        # Verify measures
        assert len(view.measures) == 1
        measure = view.measures[0]
        assert measure.name == "user_count"
        assert measure.type == "count"
        assert measure.sql == "1"

    def test_semantic_model_to_view_with_prefixes(self) -> None:
        """Test view conversion with prefixes."""
        mapper = SemanticModelMapper(view_prefix="v_")

        semantic_model = SemanticModel(
            name="orders",
            model="fact_orders",
        )

        view = mapper.semantic_model_to_view(semantic_model)
        assert view.name == "v_orders"
        assert view.sql_table_name == "fact_orders"

    def test_semantic_model_to_explore(self) -> None:
        """Test converting semantic model to LookML explore."""
        mapper = SemanticModelMapper()

        semantic_model = SemanticModel(
            name="customers",
            model="dim_customers",
            description="Customer dimension"
        )

        explore = mapper.semantic_model_to_explore(semantic_model)
        assert explore.name == "customers"
        assert explore.view_name == "customers"
        assert explore.description == "Customer dimension"

    def test_semantic_model_to_explore_with_prefixes(self) -> None:
        """Test explore conversion with prefixes."""
        mapper = SemanticModelMapper(view_prefix="v_", explore_prefix="e_")

        semantic_model = SemanticModel(
            name="products",
            model="dim_products"
        )

        explore = mapper.semantic_model_to_explore(semantic_model)
        assert explore.name == "e_products"
        assert explore.view_name == "v_products"

    def test_time_dimension_conversion(self) -> None:
        """Test converting time dimensions to dimension groups."""
        mapper = SemanticModelMapper()

        semantic_model = SemanticModel(
            name="events",
            model="fact_events",
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                    expr="created_at::date",
                    description="Creation date"
                )
            ]
        )

        view = mapper.semantic_model_to_view(semantic_model)

        # Should have one dimension group, no regular dimensions
        assert len(view.dimension_groups) == 1
        assert len(view.dimensions) == 0

        dim_group = view.dimension_groups[0]
        assert dim_group.name == "created_at"
        assert dim_group.type == "time"
        assert dim_group.sql == "created_at::date"
        assert "date" in dim_group.timeframes
        assert "month" in dim_group.timeframes
        assert "year" in dim_group.timeframes

    def test_time_dimension_with_hour_granularity(self) -> None:
        """Test time dimension with hour granularity."""
        mapper = SemanticModelMapper()

        semantic_model = SemanticModel(
            name="sessions",
            model="fact_sessions",
            dimensions=[
                Dimension(
                    name="session_start",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "hour"},
                    expr="session_start_time"
                )
            ]
        )

        view = mapper.semantic_model_to_view(semantic_model)
        dim_group = view.dimension_groups[0]
        
        # Should include time and hour timeframes
        assert "time" in dim_group.timeframes
        assert "hour" in dim_group.timeframes
        assert "date" in dim_group.timeframes

    def test_time_dimension_with_minute_granularity(self) -> None:
        """Test time dimension with minute granularity."""
        mapper = SemanticModelMapper()

        semantic_model = SemanticModel(
            name="events",
            model="fact_events",
            dimensions=[
                Dimension(
                    name="event_time",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "minute"},
                    expr="event_timestamp"
                )
            ]
        )

        view = mapper.semantic_model_to_view(semantic_model)
        dim_group = view.dimension_groups[0]
        
        # Should include minute timeframes
        assert "minute" in dim_group.timeframes
        assert "hour" in dim_group.timeframes
        assert "time" in dim_group.timeframes

    def test_all_aggregation_types(self) -> None:
        """Test all supported aggregation types."""
        mapper = SemanticModelMapper()

        measures = [
            Measure(name="count_measure", agg=AggregationType.COUNT),
            Measure(name="count_distinct_measure", agg=AggregationType.COUNT_DISTINCT, expr="customer_id"),
            Measure(name="sum_measure", agg=AggregationType.SUM, expr="amount"),
            Measure(name="avg_measure", agg=AggregationType.AVERAGE, expr="amount"),
            Measure(name="min_measure", agg=AggregationType.MIN, expr="amount"),
            Measure(name="max_measure", agg=AggregationType.MAX, expr="amount"),
            Measure(name="median_measure", agg=AggregationType.MEDIAN, expr="amount"),
        ]

        semantic_model = SemanticModel(
            name="sales",
            model="fact_sales",
            measures=measures
        )

        view = mapper.semantic_model_to_view(semantic_model)
        
        # Verify all measures are converted correctly
        assert len(view.measures) == 7
        
        measure_dict = {m.name: m for m in view.measures}
        
        assert measure_dict["count_measure"].type == "count"
        assert measure_dict["count_measure"].sql == "1"
        
        assert measure_dict["count_distinct_measure"].type == "count_distinct"
        assert measure_dict["count_distinct_measure"].sql == "customer_id"
        
        assert measure_dict["sum_measure"].type == "sum"
        assert measure_dict["sum_measure"].sql == "amount"
        
        assert measure_dict["avg_measure"].type == "average"
        assert measure_dict["median_measure"].type == "median"
        assert measure_dict["min_measure"].type == "min"
        assert measure_dict["max_measure"].type == "max"

    def test_complex_sql_expressions(self) -> None:
        """Test handling of complex SQL expressions."""
        mapper = SemanticModelMapper()

        semantic_model = SemanticModel(
            name="complex",
            model="base_table",
            dimensions=[
                Dimension(
                    name="case_dimension",
                    type=DimensionType.CATEGORICAL,
                    expr="CASE WHEN status = 'active' THEN 'Active User' ELSE 'Inactive' END"
                ),
                Dimension(
                    name="extract_dimension",
                    type=DimensionType.CATEGORICAL,
                    expr="EXTRACT(YEAR FROM created_at)::text"
                )
            ],
            measures=[
                Measure(
                    name="conditional_sum",
                    agg=AggregationType.SUM,
                    expr="CASE WHEN status = 'completed' THEN amount ELSE 0 END"
                )
            ]
        )

        view = mapper.semantic_model_to_view(semantic_model)
        
        # Verify complex expressions are preserved
        case_dim = next(d for d in view.dimensions if d.name == "case_dimension")
        assert "CASE WHEN status = 'active'" in case_dim.sql
        
        extract_dim = next(d for d in view.dimensions if d.name == "extract_dimension")
        assert "EXTRACT(YEAR FROM created_at)" in extract_dim.sql
        
        conditional_measure = next(m for m in view.measures if m.name == "conditional_sum")
        assert "CASE WHEN status = 'completed'" in conditional_measure.sql

    def test_dbt_ref_conversion(self) -> None:
        """Test conversion of dbt ref() syntax."""
        mapper = SemanticModelMapper()

        # Test various dbt ref formats
        test_cases = [
            ("ref('users')", "users"),
            ('ref("orders")', "orders"),
            ("ref('schema.table')", "schema.table"),
            ("regular_table", "regular_table"),
        ]

        for model_ref, expected_table in test_cases:
            semantic_model = SemanticModel(
                name="test",
                model=model_ref
            )
            
            view = mapper.semantic_model_to_view(semantic_model)
            assert view.sql_table_name == expected_table

    def test_entity_to_dimension_conversion(self) -> None:
        """Test conversion of entities to dimensions."""
        mapper = SemanticModelMapper()

        semantic_model = SemanticModel(
            name="test",
            model="test_table",
            entities=[
                Entity(name="primary_key", type="primary", expr="id", description="Primary key"),
                Entity(name="foreign_key", type="foreign", expr="customer_id", description="Foreign key"),
            ]
        )

        view = mapper.semantic_model_to_view(semantic_model)
        
        # Only primary entities should become dimensions
        assert len(view.dimensions) == 1
        primary_dim = view.dimensions[0]
        assert primary_dim.name == "primary_key"
        assert primary_dim.primary_key is True
        assert primary_dim.sql == "id"
        assert primary_dim.description == "Primary key"

    def test_sql_expression_conversion(self) -> None:
        """Test SQL expression conversion."""
        mapper = SemanticModelMapper()

        # Test various SQL expression patterns
        test_cases = [
            (None, "field_name", "${TABLE}.field_name"),  # No expression
            ("column_name", "field_name", "column_name"),  # Simple expression
            ("UPPER(name)", "name", "UPPER(name)"),  # Function expression
        ]

        for expr, field_name, expected_sql in test_cases:
            result = mapper._convert_sql_expression(expr, field_name)
            assert result == expected_sql

    def test_case_statement_preservation(self) -> None:
        """Test that complex CASE statements are preserved properly."""
        mapper = SemanticModelMapper()

        multiline_case = """CASE 
            WHEN status = 'active' AND created_at > '2023-01-01' THEN 'new_active'
            WHEN status = 'inactive' THEN 'inactive'
            ELSE 'other'
        END"""

        result = mapper._convert_sql_expression(multiline_case, "test_field")
        
        # Should preserve the structure
        assert "CASE" in result
        assert "WHEN status = 'active'" in result
        assert "THEN 'new_active'" in result
        assert "ELSE 'other'" in result
        assert "END" in result

    def test_dimension_with_label(self) -> None:
        """Test dimension conversion with labels."""
        mapper = SemanticModelMapper()

        semantic_model = SemanticModel(
            name="test",
            model="test_table",
            dimensions=[
                Dimension(
                    name="user_status",
                    type=DimensionType.CATEGORICAL,
                    label="User Status",
                    description="Status of the user"
                )
            ]
        )

        view = mapper.semantic_model_to_view(semantic_model)
        dimension = view.dimensions[0]
        
        assert dimension.name == "user_status"
        assert dimension.label is None  # LookMLDimension doesn't have label in current model

    def test_time_dimension_with_label(self) -> None:
        """Test time dimension conversion with labels."""
        mapper = SemanticModelMapper()

        semantic_model = SemanticModel(
            name="test",
            model="test_table",
            dimensions=[
                Dimension(
                    name="event_date",
                    type=DimensionType.TIME,
                    label="Event Date",
                    description="Date of the event"
                )
            ]
        )

        view = mapper.semantic_model_to_view(semantic_model)
        dim_group = view.dimension_groups[0]
        
        assert dim_group.name == "event_date"
        assert dim_group.label == "Event Date"
        assert dim_group.description == "Date of the event"

    def test_measure_with_label(self) -> None:
        """Test measure conversion with labels."""
        mapper = SemanticModelMapper()

        semantic_model = SemanticModel(
            name="test",
            model="test_table",
            measures=[
                Measure(
                    name="total_revenue",
                    agg=AggregationType.SUM,
                    expr="amount",
                    label="Total Revenue",
                    description="Sum of all amounts"
                )
            ]
        )

        view = mapper.semantic_model_to_view(semantic_model)
        measure = view.measures[0]
        
        assert measure.name == "total_revenue"
        assert measure.label is None  # LookMLMeasure doesn't have label in current model
        assert measure.description == "Sum of all amounts"

    def test_empty_semantic_model(self) -> None:
        """Test conversion of semantic model with no entities, dimensions, or measures."""
        mapper = SemanticModelMapper()

        semantic_model = SemanticModel(
            name="empty",
            model="empty_table"
        )

        view = mapper.semantic_model_to_view(semantic_model)
        
        assert view.name == "empty"
        assert view.sql_table_name == "empty_table"
        assert len(view.dimensions) == 0
        assert len(view.dimension_groups) == 0
        assert len(view.measures) == 0

        explore = mapper.semantic_model_to_explore(semantic_model)
        assert explore.name == "empty"
        assert explore.view_name == "empty"

    def test_measure_without_expression(self) -> None:
        """Test measures without explicit expressions."""
        mapper = SemanticModelMapper()

        semantic_model = SemanticModel(
            name="test",
            model="test_table",
            measures=[
                Measure(name="order_count", agg=AggregationType.COUNT),
                Measure(name="revenue", agg=AggregationType.SUM),  # No expr - should use column name
            ]
        )

        view = mapper.semantic_model_to_view(semantic_model)
        
        count_measure = next(m for m in view.measures if m.name == "order_count")
        assert count_measure.sql == "1"  # Count without expression
        
        sum_measure = next(m for m in view.measures if m.name == "revenue")
        assert sum_measure.sql == "${TABLE}.revenue"  # Uses column name

    def test_dimension_type_mapping(self) -> None:
        """Test dimension type mapping."""
        mapper = SemanticModelMapper()

        # Test categorical dimension
        categorical_dim = Dimension(name="status", type=DimensionType.CATEGORICAL)
        lookml_type = mapper._map_dimension_type(categorical_dim)
        assert lookml_type == "string"

    def test_aggregation_type_mapping(self) -> None:
        """Test all aggregation type mappings."""
        mapper = SemanticModelMapper()

        agg_mappings = {
            AggregationType.COUNT: "count",
            AggregationType.COUNT_DISTINCT: "count_distinct",
            AggregationType.SUM: "sum",
            AggregationType.AVERAGE: "average",
            AggregationType.MIN: "min",
            AggregationType.MAX: "max",
            AggregationType.MEDIAN: "median",
        }

        for agg_type, expected_lookml_type in agg_mappings.items():
            result = mapper._map_aggregation_type(agg_type)
            assert result == expected_lookml_type

    def test_complex_semantic_model_with_config(self) -> None:
        """Test conversion of semantic model with config metadata."""
        mapper = SemanticModelMapper()

        semantic_model = SemanticModel(
            name="complex_model",
            model="ref('fact_table')",
            description="Complex model with metadata",
            config=Config(
                meta=ConfigMeta(
                    domain="sales",
                    owner="Analytics Team",
                    contains_pii=True
                )
            ),
            entities=[
                Entity(name="id", type="primary", expr="fact_id")
            ],
            dimensions=[
                Dimension(
                    name="status",
                    type=DimensionType.CATEGORICAL,
                    expr="order_status"
                ),
                Dimension(
                    name="created_date",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"}
                )
            ],
            measures=[
                Measure(
                    name="total_orders",
                    agg=AggregationType.COUNT
                ),
                Measure(
                    name="total_amount",
                    agg=AggregationType.SUM,
                    expr="order_amount"
                )
            ]
        )

        # Test view conversion
        view = mapper.semantic_model_to_view(semantic_model)
        
        assert view.name == "complex_model"
        assert view.sql_table_name == "fact_table"
        assert view.description == "Complex model with metadata"
        
        # Should have primary entity + categorical dimension = 2 dimensions
        assert len(view.dimensions) == 2
        # Should have 1 time dimension group
        assert len(view.dimension_groups) == 1
        # Should have 2 measures
        assert len(view.measures) == 2

        # Test explore conversion
        explore = mapper.semantic_model_to_explore(semantic_model)
        assert explore.name == "complex_model"
        assert explore.view_name == "complex_model"
        assert explore.description == "Complex model with metadata"