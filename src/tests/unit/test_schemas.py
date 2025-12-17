"""Unit tests for schema models using new architecture."""

import pytest
from pydantic import ValidationError

from dbt_to_lookml.schemas.config import Config, ConfigMeta, Hierarchy
from dbt_to_lookml.schemas.lookml import (
    LookMLDimension,
    LookMLDimensionGroup,
    LookMLExplore,
    LookMLMeasure,
    LookMLSet,
    LookMLView,
)
from dbt_to_lookml.schemas.semantic_layer import (
    ConversionMetricParams,
    DerivedMetricParams,
    Dimension,
    Entity,
    Measure,
    Metric,
    MetricReference,
    RatioMetricParams,
    SemanticModel,
    SimpleMetricParams,
    _smart_title,
)
from dbt_to_lookml.types import (
    AggregationType,
    DimensionType,
)


class TestSmartTitle:
    """Test cases for _smart_title utility function."""

    def test_underscore_to_title(self) -> None:
        """Test converting underscore-separated text to title case."""
        assert _smart_title("rental_end") == "Rental End"
        assert _smart_title("user_name") == "User Name"

    def test_preserves_acronyms(self) -> None:
        """Test that common acronyms are preserved in uppercase."""
        assert _smart_title("rental_end_utc") == "Rental End UTC"
        assert _smart_title("api_key_id") == "API Key ID"
        assert _smart_title("http_url") == "HTTP URL"

    def test_preserves_preformatted_with_parentheses(self) -> None:
        """Test that pre-formatted values with parentheses are preserved as-is."""
        assert _smart_title("Facility Created (UTC)") == "Facility Created (UTC)"
        assert _smart_title("Rental Updated (UTC)") == "Rental Updated (UTC)"
        assert _smart_title("Some Value (Local)") == "Some Value (Local)"
        # Even if lowercase, parentheses trigger preservation
        assert _smart_title("test value (utc)") == "test value (utc)"

    def test_preserves_leading_whitespace(self) -> None:
        """Test that leading whitespace for sort order is preserved."""
        assert _smart_title(" Metrics") == " Metrics"
        assert _smart_title("  Date Dimensions") == "  Date Dimensions"
        assert _smart_title(" rental_end_utc") == " Rental End UTC"

    def test_preformatted_with_leading_whitespace(self) -> None:
        """Test pre-formatted values with leading whitespace are preserved."""
        assert _smart_title(" Facility Created (UTC)") == " Facility Created (UTC)"


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

    def test_entity_expr_qualification_numeric_literals(self) -> None:
        """Test that numeric literals are not qualified with ${TABLE}."""
        # Integer literal (e.g., for count-as-sum pattern)
        entity = Entity(name="row_count", type="primary", expr="1")
        lookml_dict = entity.to_lookml_dict()
        assert lookml_dict["sql"] == "1"

        # Negative integer
        entity2 = Entity(name="neg_value", type="primary", expr="-1")
        lookml_dict2 = entity2.to_lookml_dict()
        assert lookml_dict2["sql"] == "-1"

        # Decimal literal
        entity3 = Entity(name="weight", type="primary", expr="1.5")
        lookml_dict3 = entity3.to_lookml_dict()
        assert lookml_dict3["sql"] == "1.5"

        # Negative decimal
        entity4 = Entity(name="neg_weight", type="primary", expr="-0.5")
        lookml_dict4 = entity4.to_lookml_dict()
        assert lookml_dict4["sql"] == "-0.5"


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


class TestDimensionConvertTz:
    """Test cases for convert_tz support in Dimension and ConfigMeta."""

    def test_configmeta_convert_tz_field_exists(self) -> None:
        """Test that ConfigMeta accepts convert_tz field."""
        # Test with True
        meta_true = ConfigMeta(convert_tz=True)
        assert meta_true.convert_tz is True

        # Test with False
        meta_false = ConfigMeta(convert_tz=False)
        assert meta_false.convert_tz is False

        # Test with None (default)
        meta_none = ConfigMeta()
        assert meta_none.convert_tz is None

    def test_convert_tz_precedence_meta_override(self) -> None:
        """Test that dimension-level meta.convert_tz takes precedence over parameter."""
        # Arrange: Create dimension with convert_tz=True in meta
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(subject="events", category="timing", convert_tz=True)
            ),
        )

        # Act: Call with different parameter value
        result = dimension._to_dimension_group_dict(default_convert_tz=False)

        # Assert: Meta value wins
        assert result["convert_tz"] == "yes"

    def test_convert_tz_precedence_default_parameter(self) -> None:
        """Test that default_convert_tz parameter is used when meta is None."""
        # Arrange: Create dimension without convert_tz in meta
        dimension = Dimension(
            name="updated_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(subject="events")),
        )

        # Act: Call with default_convert_tz=True
        result = dimension._to_dimension_group_dict(default_convert_tz=True)

        # Assert: Parameter value is used
        assert result["convert_tz"] == "yes"

    def test_convert_tz_hardcoded_default(self) -> None:
        """Test that hardcoded default is False when no meta or parameter."""
        # Arrange: Create dimension with minimal config
        dimension = Dimension(
            name="registered_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act: Call without parameter (uses hardcoded default)
        result = dimension._to_dimension_group_dict()

        # Assert: Default is "no"
        assert result["convert_tz"] == "no"

    def test_convert_tz_false_meta_overrides_true_parameter(self) -> None:
        """Test that meta.convert_tz=False overrides default_convert_tz=True."""
        # Arrange: Create dimension with explicit convert_tz=False
        dimension = Dimension(
            name="deleted_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(subject="events", convert_tz=False)),
        )

        # Act: Call with default_convert_tz=True
        result = dimension._to_dimension_group_dict(default_convert_tz=True)

        # Assert: Meta False overrides parameter True
        assert result["convert_tz"] == "no"

    def test_convert_tz_none_meta_uses_parameter(self) -> None:
        """Test that None meta.convert_tz allows parameter to be used."""
        # Arrange: Create dimension with None meta.convert_tz
        dimension = Dimension(
            name="started_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(
                    subject="events",
                    convert_tz=None,  # Explicit None
                )
            ),
        )

        # Act: Call with default_convert_tz=True
        result = dimension._to_dimension_group_dict(default_convert_tz=True)

        # Assert: Parameter used when meta is None
        assert result["convert_tz"] == "yes"

    def test_convert_tz_in_dimension_group_dict(self) -> None:
        """Test that convert_tz field appears in router method output."""
        # Arrange: Create TIME dimension
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        # Act: Call router method to_lookml_dict()
        result = dimension.to_lookml_dict()

        # Assert: convert_tz is in output
        assert "convert_tz" in result
        assert result["convert_tz"] == "yes"

    def test_convert_tz_with_all_optional_fields(self) -> None:
        """Test convert_tz coexists properly with other optional fields.

        Time dimension view_label gets 1-space prefix for sort order positioning.
        """
        # Arrange: Create comprehensive dimension
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "hour"},
            description="When the event was created",
            label="Created Date",
            expr="created_timestamp",
            config=Config(
                meta=ConfigMeta(subject="events", category="timing", convert_tz=True)
            ),
        )

        # Act: Generate LookML dict
        result = dimension._to_dimension_group_dict()

        # Assert: All fields present and correct
        assert result["name"] == "created_at"
        assert result["type"] == "time"
        assert "time" in result["timeframes"]
        assert result["sql"] == "created_timestamp"
        assert result["description"] == "When the event was created"
        assert result["label"] == "Created Date"
        # Time dimensions get 1-space prefix on view_label for sort order
        assert result["view_label"] == " Events"
        assert result["group_label"] == "Timing"  # Formatted from category
        assert result["convert_tz"] == "yes"

    def test_convert_tz_no_config_uses_parameter(self) -> None:
        """Test that missing config doesn't break precedence chain."""
        # Arrange: Create dimension with no config
        dimension = Dimension(
            name="timestamp_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            # No config parameter
        )

        # Act: Call with default_convert_tz=True
        result = dimension._to_dimension_group_dict(default_convert_tz=True)

        # Assert: Parameter used when config is None
        assert result["convert_tz"] == "yes"

    def test_convert_tz_categorical_dimension_not_affected(self) -> None:
        """Test that convert_tz doesn't affect categorical dimensions."""
        # Arrange: Create categorical dimension with convert_tz config
        dimension = Dimension(
            name="status",
            type=DimensionType.CATEGORICAL,
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        # Act: Call to_lookml_dict() which routes to _to_dimension_dict()
        result = dimension.to_lookml_dict()

        # Assert: convert_tz not in categorical dimension output
        assert "convert_tz" not in result
        assert result["type"] == "string"


class TestDimensionTimeDimensionGroupLabel:
    """Test cases for time_dimension_group_label support in Dimension and ConfigMeta."""

    def test_configmeta_time_dimension_group_label_field(self) -> None:
        """Test that ConfigMeta accepts time_dimension_group_label field."""
        # Arrange & Act: Create ConfigMeta with different values
        meta_custom = ConfigMeta(time_dimension_group_label="Event Times")
        assert meta_custom.time_dimension_group_label == "Event Times"

        meta_none = ConfigMeta(time_dimension_group_label=None)
        assert meta_none.time_dimension_group_label is None

        meta_default = ConfigMeta()
        assert meta_default.time_dimension_group_label is None

    def test_time_dimension_group_label_metadata_override(self) -> None:
        """Test that dimension-level meta takes precedence over default."""
        # Arrange: Create dimension with time_dimension_group_label in meta
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(time_dimension_group_label="Event Timestamps")
            ),
        )

        # Act: Call with default_time_dimension_group_label
        result = dimension._to_dimension_group_dict(
            default_time_dimension_group_label=" Date Dimensions - Local Time"
        )

        # Assert: Metadata override takes precedence (with 1 space prefix)
        assert result["group_label"] == " Event Timestamps"

    def test_time_dimension_group_label_default(self) -> None:
        """Test that default_time_dimension_group_label is used when no meta."""
        # Arrange: Create dimension without time_dimension_group_label in meta
        dimension = Dimension(
            name="shipped_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "hour"},
        )

        # Act: Call with default_time_dimension_group_label
        result = dimension._to_dimension_group_dict(
            default_time_dimension_group_label=" Date Dimensions - Local Time"
        )

        # Assert: Default parameter is used
        assert result["group_label"] == " Date Dimensions - Local Time"

    def test_dimension_group_default_time_group_label(self) -> None:
        """Test that time dimensions have no default group_label (use hierarchy/subject)."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act - no parameters provided
        result = dim.to_lookml_dict()

        # Assert - no default group_label, use hierarchy/subject metadata instead
        assert result.get("group_label") is None

    def test_dimension_group_hierarchy_group_label_overrides_time_group_label(
        self,
    ) -> None:
        """Test that hierarchy-based group_label takes precedence over time group_label.

        Time dimension view_label gets 1-space prefix for sort order positioning.
        """
        # Arrange - dimension has hierarchy with category
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(
                    hierarchy=Hierarchy(
                        entity="event",
                        category="event_tracking",
                    ),
                    time_dimension_group_label=" Date Dimensions - Local Time",  # Should be ignored
                )
            ),
        )

        # Act
        result = dimension._to_dimension_group_dict()

        # Assert - hierarchy group_label wins
        assert result.get("group_label") == "Event Tracking"  # From hierarchy
        # Time dimensions get 1-space prefix on view_label for sort order
        assert result.get("view_label") == " Event"

    def test_time_dimension_group_label_with_generator_default(self) -> None:
        """Test that generator default applies to all time dimensions."""
        # Arrange: Create multiple time dimensions
        dim1 = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )
        dim2 = Dimension(
            name="shipped_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "hour"},
            config=Config(meta=ConfigMeta(time_dimension_group_label="Custom Times")),
        )

        # Act: Generate with default
        result1 = dim1._to_dimension_group_dict(
            default_time_dimension_group_label=" Date Dimensions - Local Time"
        )
        result2 = dim2._to_dimension_group_dict(
            default_time_dimension_group_label=" Date Dimensions - Local Time"
        )

        # Assert: First uses default, second uses metadata override
        assert result1["group_label"] == " Date Dimensions - Local Time"
        assert result2["group_label"] == " Custom Times"  # 1 space prefix

    def test_dimension_group_generator_parameter_time_group_label(self) -> None:
        """Test that generator parameter overrides default time group_label."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act - generator provides custom label
        result = dim.to_lookml_dict(
            default_time_dimension_group_label="Custom Time Dims"
        )

        # Assert (1 space prefix applied)
        assert result.get("group_label") == " Custom Time Dims"

    def test_dimension_group_metadata_overrides_generator_time_group_label(
        self,
    ) -> None:
        """Test that dimension metadata overrides generator parameter."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(time_dimension_group_label="Event Times")),
        )

        # Act - generator provides different label
        result = dim.to_lookml_dict(
            default_time_dimension_group_label="Custom Time Dims"
        )

        # Assert - metadata should win (1 space prefix applied)
        assert result.get("group_label") == " Event Times"

    def test_dimension_group_disable_time_group_label_with_empty_string_metadata(
        self,
    ) -> None:
        """Test that empty string in metadata disables time group_label."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(time_dimension_group_label="")),
        )

        # Act - even with generator default
        result = dim.to_lookml_dict(
            default_time_dimension_group_label=" Date Dimensions - Local Time"
        )

        # Assert - should have no group_label key
        assert "group_label" not in result

    def test_dimension_group_disable_time_group_label_with_empty_string_generator(
        self,
    ) -> None:
        """Test that empty string in generator parameter disables time group_label."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act
        result = dim.to_lookml_dict(default_time_dimension_group_label="")

        # Assert
        assert "group_label" not in result

    def test_dimension_group_none_uses_no_group_label(self) -> None:
        """Test that None in metadata means no group_label (use hierarchy/subject)."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(time_dimension_group_label=None)),
        )

        # Act - no generator parameter
        result = dim.to_lookml_dict()

        # Assert - no group_label, hierarchy/subject metadata takes over
        assert result.get("group_label") is None

    def test_dimension_group_time_label_precedence_chain(self) -> None:
        """Test full precedence chain: metadata > generator > None."""
        # Case 1: Metadata wins
        dim1 = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(time_dimension_group_label="Meta")),
        )
        assert (
            dim1.to_lookml_dict(default_time_dimension_group_label="Gen")["group_label"]
            == " Meta"  # 1 space prefix
        )

        # Case 2: Generator wins (no metadata)
        dim2 = Dimension(
            name="updated_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )
        assert (
            dim2.to_lookml_dict(default_time_dimension_group_label="Gen")["group_label"]
            == " Gen"  # 1 space prefix
        )

        # Case 3: No group_label when neither metadata nor generator specified
        dim3 = Dimension(
            name="deleted_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )
        assert dim3.to_lookml_dict().get("group_label") is None

    def test_dimension_group_time_label_with_convert_tz(self) -> None:
        """Test that time group_label works alongside convert_tz."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        # Act
        result = dim.to_lookml_dict(
            default_convert_tz=False, default_time_dimension_group_label="Events"
        )

        # Assert - both parameters applied (1 space prefix on group_label)
        assert result.get("group_label") == " Events"
        assert result.get("convert_tz") == "yes"  # Metadata overrides

    def test_dimension_group_label_and_time_group_label(self) -> None:
        """Test that label and time group_label can coexist."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            label="Order Created",  # Sub-category
            config=Config(
                meta=ConfigMeta(time_dimension_group_label=" Date Dimensions - Local Time")
            ),
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert
        assert result.get("label") == "Order Created"
        assert result.get("group_label") == " Date Dimensions - Local Time"

    def test_dimension_group_time_label_special_characters(self) -> None:
        """Test that special characters in time group_label are preserved."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(
                meta=ConfigMeta(time_dimension_group_label="Time/Dates & Events")
            ),
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert (1 space prefix applied)
        assert result.get("group_label") == " Time/Dates & Events"


class TestDimensionGroupItemLabel:
    """Test cases for group_item_label support in time dimensions."""

    def test_group_item_label_enabled(self) -> None:
        """Test that group_item_label is generated when default_use_group_item_label=True."""
        # Arrange
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act
        result = dimension._to_dimension_group_dict(default_use_group_item_label=True)

        # Assert
        assert "group_item_label" in result
        assert "{% assign tf =" in result["group_item_label"]
        assert "capitalize" in result["group_item_label"]

    def test_group_item_label_disabled_default(self) -> None:
        """Test that group_item_label is not generated by default."""
        # Arrange
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act
        result = dimension._to_dimension_group_dict(default_use_group_item_label=False)

        # Assert
        assert "group_item_label" not in result

    def test_group_item_label_not_present_when_none(self) -> None:
        """Test that group_item_label is not generated when parameter is None."""
        # Arrange
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act
        result = dimension._to_dimension_group_dict(default_use_group_item_label=None)

        # Assert
        assert "group_item_label" not in result

    def test_group_item_label_metadata_override_true(self) -> None:
        """Test that dimension meta overrides generator default to True."""
        # Arrange
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(use_group_item_label=True)),
        )

        # Act
        result = dimension._to_dimension_group_dict(default_use_group_item_label=False)

        # Assert - metadata override should win
        assert "group_item_label" in result

    def test_group_item_label_metadata_override_false(self) -> None:
        """Test that dimension meta overrides generator default to False."""
        # Arrange
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(use_group_item_label=False)),
        )

        # Act
        result = dimension._to_dimension_group_dict(default_use_group_item_label=True)

        # Assert - metadata override should win
        assert "group_item_label" not in result

    def test_group_item_label_template_contains_dimension_name(self) -> None:
        """Test that group_item_label template references the dimension name."""
        # Arrange
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act
        result = dimension._to_dimension_group_dict(default_use_group_item_label=True)

        # Assert - template should exist and be a Liquid template
        assert "group_item_label" in result
        assert "assign" in result["group_item_label"]  # Should be a Liquid template

    def test_group_item_label_with_different_granularities(self) -> None:
        """Test group_item_label works with different time granularities."""
        # Test with hour granularity
        dimension_hour = Dimension(
            name="timestamp",
            type=DimensionType.TIME,
            type_params={"time_granularity": "hour"},
        )
        result_hour = dimension_hour._to_dimension_group_dict(
            default_use_group_item_label=True
        )
        assert "group_item_label" in result_hour

        # Test with minute granularity
        dimension_minute = Dimension(
            name="timestamp",
            type=DimensionType.TIME,
            type_params={"time_granularity": "minute"},
        )
        result_minute = dimension_minute._to_dimension_group_dict(
            default_use_group_item_label=True
        )
        assert "group_item_label" in result_minute

    def test_group_item_label_precedence_metadata_over_generator(self) -> None:
        """Test full precedence: metadata > generator > default."""
        # Case 1: Metadata enables (overrides generator False)
        dim1 = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(use_group_item_label=True)),
        )
        assert "group_item_label" in dim1._to_dimension_group_dict(
            default_use_group_item_label=False
        )

        # Case 2: Generator enables (metadata None, defaults to False)
        dim2 = Dimension(
            name="updated_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )
        assert "group_item_label" in dim2._to_dimension_group_dict(
            default_use_group_item_label=True
        )

        # Case 3: Default (both None)
        dim3 = Dimension(
            name="deleted_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )
        assert "group_item_label" not in dim3._to_dimension_group_dict()

    def test_group_item_label_with_other_dimension_parameters(self) -> None:
        """Test group_item_label works alongside other parameters."""
        # Arrange
        dimension = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            label="Order Created",
            description="Order creation timestamp",
            config=Config(
                meta=ConfigMeta(
                    hierarchy=Hierarchy(entity="order"),
                    convert_tz=True,
                    use_group_item_label=True,
                    time_dimension_group_label="Event Dates",
                )
            ),
        )

        # Act
        result = dimension._to_dimension_group_dict()

        # Assert - all parameters should be present
        assert result["label"] == "Order Created"
        assert result["description"] == "Order creation timestamp"
        assert result["convert_tz"] == "yes"
        assert result["group_label"] == " Event Dates"  # 1 space prefix
        assert "group_item_label" in result
        # Time dimensions get 1-space prefix on view_label for sort order
        assert result["view_label"] == " Order"


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

    def test_average_measure_auto_casts_to_float(self) -> None:
        """Test that average measures auto-cast to float to avoid integer truncation."""
        measure = Measure(name="avg_rating", agg=AggregationType.AVERAGE)
        result = measure.to_lookml_dict()
        # Should auto-cast to float when no expr is provided
        assert result["sql"] == "(${TABLE}.avg_rating)::FLOAT"
        assert result["type"] == "average"

    def test_median_measure_auto_casts_to_float(self) -> None:
        """Test that median measures auto-cast to float to avoid integer truncation."""
        measure = Measure(name="median_score", agg=AggregationType.MEDIAN)
        result = measure.to_lookml_dict()
        assert result["sql"] == "(${TABLE}.median_score)::FLOAT"
        assert result["type"] == "median"

    def test_percentile_measure_auto_casts_to_float(self) -> None:
        """Test that percentile measures auto-cast to float to avoid integer truncation."""
        measure = Measure(name="p90_latency", agg=AggregationType.PERCENTILE)
        result = measure.to_lookml_dict()
        assert result["sql"] == "(${TABLE}.p90_latency)::FLOAT"
        assert result["type"] == "percentile"

    def test_average_with_expr_also_casts(self) -> None:
        """Test that average measures with explicit expr also get cast."""
        measure = Measure(
            name="avg_rating",
            agg=AggregationType.AVERAGE,
            expr="rating_value",
        )
        result = measure.to_lookml_dict()
        # Always cast for average to avoid integer truncation
        assert result["sql"] == "(rating_value)::FLOAT"

    def test_sum_measure_does_not_auto_cast(self) -> None:
        """Test that sum measures don't auto-cast (preserve integer behavior)."""
        measure = Measure(name="total_count", agg=AggregationType.SUM)
        result = measure.to_lookml_dict()
        # SUM should not cast to float
        assert result["sql"] == "${TABLE}.total_count"

    def test_min_max_measures_do_not_auto_cast(self) -> None:
        """Test that min/max measures don't auto-cast (preserve original type)."""
        min_measure = Measure(name="min_value", agg=AggregationType.MIN)
        max_measure = Measure(name="max_value", agg=AggregationType.MAX)

        min_result = min_measure.to_lookml_dict()
        max_result = max_measure.to_lookml_dict()

        assert min_result["sql"] == "${TABLE}.min_value"
        assert max_result["sql"] == "${TABLE}.max_value"


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

        # Verify dimension set includes dimension_group base names
        dimension_set = next(
            (s for s in view["sets"] if s["name"] == "dimensions_only"), None
        )
        assert dimension_set is not None
        # In LookML, dimension_groups must list each timeframe individually
        assert "created_at_date" in dimension_set["fields"]
        assert "created_at_week" in dimension_set["fields"]
        assert "created_at_month" in dimension_set["fields"]
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

    def test_semantic_model_to_lookml_dict_with_convert_tz(self) -> None:
        """Test that SemanticModel.to_lookml_dict() accepts convert_tz
        parameter."""
        model = SemanticModel(
            name="test_model",
            model="test_table",
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                )
            ],
        )

        # Test with None (default)
        result_none = model.to_lookml_dict(schema="public", convert_tz=None)
        assert isinstance(result_none, dict)
        assert "views" in result_none

        # Test with True
        result_true = model.to_lookml_dict(schema="public", convert_tz=True)
        assert isinstance(result_true, dict)
        assert "views" in result_true
        # Verify convert_tz is propagated
        views = result_true["views"]
        dimension_groups = views[0].get("dimension_groups", [])
        assert len(dimension_groups) > 0
        assert dimension_groups[0].get("convert_tz") == "yes"

        # Test with False
        result_false = model.to_lookml_dict(schema="public", convert_tz=False)
        assert isinstance(result_false, dict)
        views = result_false["views"]
        dimension_groups = views[0].get("dimension_groups", [])
        assert dimension_groups[0].get("convert_tz") == "no"

        # Test backward compatibility (no convert_tz parameter)
        result_compat = model.to_lookml_dict(schema="public")
        assert isinstance(result_compat, dict)

    def test_dimension_to_lookml_dict_with_default_convert_tz(self) -> None:
        """Test that Dimension.to_lookml_dict() accepts default_convert_tz
        parameter."""
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Test with None (default)
        result_none = dim.to_lookml_dict(default_convert_tz=None)
        assert isinstance(result_none, dict)
        assert result_none["name"] == "created_at"
        assert result_none.get("convert_tz") == "no"

        # Test with True
        result_true = dim.to_lookml_dict(default_convert_tz=True)
        assert isinstance(result_true, dict)
        assert result_true.get("convert_tz") == "yes"

        # Test with False
        result_false = dim.to_lookml_dict(default_convert_tz=False)
        assert isinstance(result_false, dict)
        assert result_false.get("convert_tz") == "no"

        # Test backward compatibility (no parameter)
        result_compat = dim.to_lookml_dict()
        assert isinstance(result_compat, dict)
        assert result_compat.get("convert_tz") == "no"

    def test_dimension_convert_tz_precedence(self) -> None:
        """Test that dimension-level convert_tz takes precedence over
        default."""
        from dbt_to_lookml.schemas import Config, ConfigMeta

        # Dimension with explicit convert_tz=True in meta
        dim_true = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        # Even if default is False, dimension meta should win
        result = dim_true.to_lookml_dict(default_convert_tz=False)
        assert result.get("convert_tz") == "yes"

        # Dimension with explicit convert_tz=False in meta
        dim_false = Dimension(
            name="updated_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=False)),
        )

        # Even if default is True, dimension meta should win
        result = dim_false.to_lookml_dict(default_convert_tz=True)
        assert result.get("convert_tz") == "no"

    def test_categorical_dimension_ignores_convert_tz(self) -> None:
        """Test that categorical dimensions ignore convert_tz parameter."""
        dim = Dimension(name="status", type=DimensionType.CATEGORICAL)

        # Convert_tz should be ignored for categorical dimensions
        result = dim.to_lookml_dict(default_convert_tz=True)
        assert isinstance(result, dict)
        assert result["name"] == "status"
        # Categorical dims don't have convert_tz
        assert "convert_tz" not in result


class TestDimensionConvertTzComprehensive:
    """Test cases for comprehensive Dimension convert_tz handling."""

    @pytest.mark.parametrize(
        "convert_tz_value,expected_lookml",
        [
            (True, "yes"),
            (False, "no"),
            (None, "no"),  # Default is False
        ],
    )
    def test_dimension_group_convert_tz_output(
        self, convert_tz_value: bool | None, expected_lookml: str
    ) -> None:
        """Test convert_tz appears in LookML output with correct value."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            config=Config(meta=ConfigMeta(convert_tz=convert_tz_value))
            if convert_tz_value is not None
            else None,
            type_params={"time_granularity": "day"},
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert
        assert result.get("convert_tz") == expected_lookml

    def test_dimension_group_convert_tz_default_false(self) -> None:
        """Test that default convert_tz is False when not specified."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert
        assert result.get("convert_tz") == "no"

    def test_dimension_convert_tz_ignored_for_non_time_dimensions(self) -> None:
        """Test that convert_tz in meta for categorical dimensions is ignored."""
        # Arrange
        dim = Dimension(
            name="status",
            type=DimensionType.CATEGORICAL,
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert - categorical dimensions should not have convert_tz
        assert "convert_tz" not in result

    def test_dimension_group_convert_tz_with_custom_timeframes(self) -> None:
        """Test that convert_tz works with custom time granularity."""
        # Arrange - hour granularity should include additional timeframes
        dim = Dimension(
            name="event_timestamp",
            type=DimensionType.TIME,
            type_params={"time_granularity": "hour"},
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert
        assert result.get("convert_tz") == "yes"
        # Verify timeframes are correctly set for hour granularity
        assert "timeframes" in result
        assert "time" in result["timeframes"]
        assert "hour" in result["timeframes"]

    def test_dimension_group_convert_tz_precedence_meta_overrides_default(
        self,
    ) -> None:
        """Test that dimension meta convert_tz overrides default."""
        # Arrange - meta says True
        dim_true = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        # Act - even with default_convert_tz=False
        result_true = dim_true.to_lookml_dict(default_convert_tz=False)

        # Assert - meta should win
        assert result_true.get("convert_tz") == "yes"

        # Arrange - meta says False
        dim_false = Dimension(
            name="updated_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=False)),
        )

        # Act - even with default_convert_tz=True
        result_false = dim_false.to_lookml_dict(default_convert_tz=True)

        # Assert - meta should win
        assert result_false.get("convert_tz") == "no"

    def test_dimension_group_convert_tz_serialization(self) -> None:
        """Test that convert_tz is serialized as string, not boolean."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert - must be string "yes", not boolean True
        assert result.get("convert_tz") == "yes"
        assert isinstance(result.get("convert_tz"), str)
        assert result.get("convert_tz") is not True

    def test_multiple_dimensions_different_convert_tz_settings(self) -> None:
        """Test multiple dimensions with different convert_tz values."""
        # Arrange
        dim1 = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        dim2 = Dimension(
            name="updated_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=False)),
        )

        dim3 = Dimension(
            name="deleted_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            # No convert_tz in config - uses default
        )

        # Act
        result1 = dim1.to_lookml_dict()
        result2 = dim2.to_lookml_dict()
        result3 = dim3.to_lookml_dict()

        # Assert - each respects its own setting
        assert result1.get("convert_tz") == "yes"
        assert result2.get("convert_tz") == "no"
        assert result3.get("convert_tz") == "no"

    def test_dimension_group_convert_tz_with_minute_granularity(self) -> None:
        """Test convert_tz with minute granularity includes time timeframe."""
        # Arrange
        dim = Dimension(
            name="precise_timestamp",
            type=DimensionType.TIME,
            type_params={"time_granularity": "minute"},
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert
        assert result.get("convert_tz") == "yes"
        assert "timeframes" in result
        # Minute granularity uses hour granularity timeframes
        assert "time" in result["timeframes"]
        assert "hour" in result["timeframes"]

    def test_dimension_group_convert_tz_explicit_true(self) -> None:
        """Test dimension with meta.convert_tz=True."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert
        assert "convert_tz" in result
        assert result["convert_tz"] == "yes"

    def test_dimension_group_convert_tz_explicit_false(self) -> None:
        """Test dimension with meta.convert_tz=False."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=False)),
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert
        assert "convert_tz" in result
        assert result["convert_tz"] == "no"

    def test_dimension_group_convert_tz_none(self) -> None:
        """Test dimension with no convert_tz uses default."""
        # Arrange
        dim = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
        )

        # Act
        result = dim.to_lookml_dict()

        # Assert
        assert "convert_tz" in result
        assert result["convert_tz"] == "no"

    def test_dimension_group_convert_tz_in_lookml_output(self) -> None:
        """Test convert_tz appears correctly in dimension_group dict."""
        # Arrange
        dim_yes = Dimension(
            name="created_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        dim_no = Dimension(
            name="updated_at",
            type=DimensionType.TIME,
            type_params={"time_granularity": "day"},
            config=Config(meta=ConfigMeta(convert_tz=False)),
        )

        # Act
        result_yes = dim_yes.to_lookml_dict()
        result_no = dim_no.to_lookml_dict()

        # Assert
        assert result_yes.get("convert_tz") == "yes"
        assert result_no.get("convert_tz") == "no"

    def test_dimension_convert_tz_with_categorical_dimension_multiple(self) -> None:
        """Test that categorical dimensions ignore convert_tz consistently."""
        # Arrange
        dim1 = Dimension(
            name="status",
            type=DimensionType.CATEGORICAL,
            config=Config(meta=ConfigMeta(convert_tz=True)),
        )

        dim2 = Dimension(
            name="category",
            type=DimensionType.CATEGORICAL,
            config=Config(meta=ConfigMeta(convert_tz=False)),
        )

        # Act
        result1 = dim1.to_lookml_dict()
        result2 = dim2.to_lookml_dict()

        # Assert - categorical dimensions should never have convert_tz
        assert "convert_tz" not in result1
        assert "convert_tz" not in result2


# ============================================================================
# Metric Schema Tests
# ============================================================================


class TestMetricReference:
    """Test cases for MetricReference model."""

    def test_metric_reference_creation(self) -> None:
        """Test basic metric reference creation with only name."""
        ref = MetricReference(name="revenue")
        assert ref.name == "revenue"
        assert ref.alias is None
        assert ref.offset_window is None

    def test_metric_reference_with_alias(self) -> None:
        """Test metric reference with name and alias."""
        ref = MetricReference(name="revenue", alias="current_revenue")
        assert ref.name == "revenue"
        assert ref.alias == "current_revenue"
        assert ref.offset_window is None

    def test_metric_reference_with_offset_window(self) -> None:
        """Test metric reference with name and offset_window."""
        ref = MetricReference(name="revenue", offset_window="1 month")
        assert ref.name == "revenue"
        assert ref.alias is None
        assert ref.offset_window == "1 month"

    def test_metric_reference_with_all_fields(self) -> None:
        """Test metric reference with all fields."""
        ref = MetricReference(
            name="revenue", alias="prior_revenue", offset_window="1 month"
        )
        assert ref.name == "revenue"
        assert ref.alias == "prior_revenue"
        assert ref.offset_window == "1 month"

    def test_metric_reference_validation(self) -> None:
        """Test that name is required."""
        with pytest.raises(ValidationError):
            MetricReference()  # type: ignore


class TestSimpleMetricParams:
    """Test cases for SimpleMetricParams model."""

    def test_simple_metric_params_creation(self) -> None:
        """Test simple metric params creation."""
        params = SimpleMetricParams(measure="revenue")
        assert params.measure == "revenue"

    def test_simple_metric_params_validation(self) -> None:
        """Test that measure is required."""
        with pytest.raises(ValidationError):
            SimpleMetricParams()  # type: ignore


class TestRatioMetricParams:
    """Test cases for RatioMetricParams model."""

    def test_ratio_metric_params_creation(self) -> None:
        """Test ratio metric params creation."""
        params = RatioMetricParams(numerator="orders", denominator="searches")
        assert params.numerator == "orders"
        assert params.denominator == "searches"

    def test_ratio_metric_params_validation_missing_denominator(self) -> None:
        """Test that denominator is required."""
        with pytest.raises(ValidationError):
            RatioMetricParams(numerator="orders")  # type: ignore

    def test_ratio_metric_params_validation_missing_numerator(self) -> None:
        """Test that numerator is required."""
        with pytest.raises(ValidationError):
            RatioMetricParams(denominator="searches")  # type: ignore


class TestDerivedMetricParams:
    """Test cases for DerivedMetricParams model."""

    def test_derived_metric_params_creation(self) -> None:
        """Test derived metric params creation with empty metrics list."""
        params = DerivedMetricParams(expr="revenue * 1.1", metrics=[])
        assert params.expr == "revenue * 1.1"
        assert params.metrics == []

    def test_derived_metric_params_with_single_metric(self) -> None:
        """Test derived metric params with single metric reference."""
        ref = MetricReference(name="revenue")
        params = DerivedMetricParams(expr="revenue * 1.1", metrics=[ref])
        assert params.expr == "revenue * 1.1"
        assert len(params.metrics) == 1
        assert params.metrics[0].name == "revenue"

    def test_derived_metric_params_with_multiple_metrics(self) -> None:
        """Test derived metric params with multiple metric references."""
        refs = [
            MetricReference(name="revenue", alias="current"),
            MetricReference(name="revenue", alias="prior", offset_window="1 month"),
        ]
        params = DerivedMetricParams(expr="(current - prior) / prior", metrics=refs)
        assert params.expr == "(current - prior) / prior"
        assert len(params.metrics) == 2
        assert params.metrics[0].alias == "current"
        assert params.metrics[1].alias == "prior"
        assert params.metrics[1].offset_window == "1 month"

    def test_derived_metric_params_validation(self) -> None:
        """Test that expr is required."""
        with pytest.raises(ValidationError):
            DerivedMetricParams(metrics=[])  # type: ignore

    def test_derived_metric_params_validation_missing_metrics(self) -> None:
        """Test that metrics list is required."""
        with pytest.raises(ValidationError):
            DerivedMetricParams(expr="revenue * 1.1")  # type: ignore


class TestConversionMetricParams:
    """Test cases for ConversionMetricParams model."""

    def test_conversion_metric_params_creation(self) -> None:
        """Test conversion metric params creation."""
        params = ConversionMetricParams(
            conversion_type_params={
                "entity": "order",
                "calculation": "conversion_rate",
            }
        )
        assert params.conversion_type_params["entity"] == "order"
        assert params.conversion_type_params["calculation"] == "conversion_rate"

    def test_conversion_metric_params_flexible_structure(self) -> None:
        """Test conversion params accepts various dict structures."""
        # Simple structure
        params1 = ConversionMetricParams(conversion_type_params={"entity": "user"})
        assert params1.conversion_type_params["entity"] == "user"

        # Complex structure
        params2 = ConversionMetricParams(
            conversion_type_params={
                "entity": "order",
                "calculation": "conversion_rate",
                "base_event": "page_view",
                "conversion_event": "purchase",
                "window": "7 days",
            }
        )
        assert len(params2.conversion_type_params) == 5
        assert params2.conversion_type_params["window"] == "7 days"

    def test_conversion_metric_params_validation(self) -> None:
        """Test that conversion_type_params is required."""
        with pytest.raises(ValidationError):
            ConversionMetricParams()  # type: ignore


class TestMetric:
    """Test cases for Metric model."""

    def test_metric_simple_creation(self) -> None:
        """Test simple metric creation."""
        metric = Metric(
            name="total_revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="revenue"),
        )
        assert metric.name == "total_revenue"
        assert metric.type == "simple"
        assert isinstance(metric.type_params, SimpleMetricParams)
        assert metric.type_params.measure == "revenue"
        assert metric.label is None
        assert metric.description is None
        assert metric.meta is None

    def test_metric_ratio_creation(self) -> None:
        """Test ratio metric creation."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(numerator="orders", denominator="searches"),
        )
        assert metric.name == "conversion_rate"
        assert metric.type == "ratio"
        assert isinstance(metric.type_params, RatioMetricParams)
        assert metric.type_params.numerator == "orders"
        assert metric.type_params.denominator == "searches"

    def test_metric_derived_creation(self) -> None:
        """Test derived metric creation."""
        refs = [
            MetricReference(name="revenue", alias="current"),
            MetricReference(name="revenue", alias="prior", offset_window="1 month"),
        ]
        metric = Metric(
            name="revenue_growth",
            type="derived",
            type_params=DerivedMetricParams(
                expr="(current - prior) / prior", metrics=refs
            ),
        )
        assert metric.name == "revenue_growth"
        assert metric.type == "derived"
        assert isinstance(metric.type_params, DerivedMetricParams)
        assert metric.type_params.expr == "(current - prior) / prior"
        assert len(metric.type_params.metrics) == 2

    def test_metric_conversion_creation(self) -> None:
        """Test conversion metric creation."""
        metric = Metric(
            name="checkout_conversion",
            type="conversion",
            type_params=ConversionMetricParams(
                conversion_type_params={
                    "entity": "order",
                    "calculation": "conversion_rate",
                }
            ),
        )
        assert metric.name == "checkout_conversion"
        assert metric.type == "conversion"
        assert isinstance(metric.type_params, ConversionMetricParams)
        assert metric.type_params.conversion_type_params["entity"] == "order"

    def test_metric_with_all_optional_fields(self) -> None:
        """Test metric with label, description, and meta."""
        metric = Metric(
            name="total_revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="revenue"),
            label="Total Revenue",
            description="Sum of all revenue",
            meta={"primary_entity": "order", "category": "financial"},
        )
        assert metric.label == "Total Revenue"
        assert metric.description == "Sum of all revenue"
        assert metric.meta is not None
        assert metric.meta["primary_entity"] == "order"
        assert metric.meta["category"] == "financial"

    def test_metric_validation_missing_name(self) -> None:
        """Test that name is required."""
        with pytest.raises(ValidationError):
            Metric(  # type: ignore
                type="simple",
                type_params=SimpleMetricParams(measure="revenue"),
            )

    def test_metric_validation_missing_type(self) -> None:
        """Test that type is required."""
        with pytest.raises(ValidationError):
            Metric(  # type: ignore
                name="total_revenue",
                type_params=SimpleMetricParams(measure="revenue"),
            )

    def test_metric_validation_missing_type_params(self) -> None:
        """Test that type_params is required."""
        with pytest.raises(ValidationError):
            Metric(name="total_revenue", type="simple")  # type: ignore

    def test_metric_validation_invalid_type(self) -> None:
        """Test that invalid type is rejected."""
        with pytest.raises(ValidationError):
            Metric(  # type: ignore
                name="total_revenue",
                type="invalid",  # type: ignore
                type_params=SimpleMetricParams(measure="revenue"),
            )

    def test_metric_primary_entity_present(self) -> None:
        """Test primary_entity property when present in meta."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(numerator="orders", denominator="searches"),
            meta={"primary_entity": "search"},
        )
        assert metric.primary_entity == "search"

    def test_metric_primary_entity_missing(self) -> None:
        """Test primary_entity property when meta is None."""
        metric = Metric(
            name="total_revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="revenue"),
        )
        assert metric.primary_entity is None

    def test_metric_primary_entity_meta_without_field(self) -> None:
        """Test primary_entity when meta exists but lacks primary_entity."""
        metric = Metric(
            name="total_revenue",
            type="simple",
            type_params=SimpleMetricParams(measure="revenue"),
            meta={"category": "performance"},
        )
        assert metric.primary_entity is None

    def test_metric_primary_entity_nested_meta(self) -> None:
        """Test primary_entity extraction from complex meta block."""
        metric = Metric(
            name="conversion_rate",
            type="ratio",
            type_params=RatioMetricParams(numerator="orders", denominator="searches"),
            meta={
                "primary_entity": "order",
                "category": "conversion",
                "tags": ["important", "revenue"],
            },
        )
        assert metric.primary_entity == "order"
        assert metric.meta is not None
        assert metric.meta["category"] == "conversion"

    @pytest.mark.parametrize(
        "metric_type,params_class,params_dict",
        [
            ("simple", SimpleMetricParams, {"measure": "revenue"}),
            (
                "ratio",
                RatioMetricParams,
                {"numerator": "orders", "denominator": "searches"},
            ),
            (
                "derived",
                DerivedMetricParams,
                {"expr": "revenue * 1.1", "metrics": []},
            ),
            (
                "conversion",
                ConversionMetricParams,
                {"conversion_type_params": {"entity": "user"}},
            ),
        ],
    )
    def test_metric_all_types_valid(
        self, metric_type: str, params_class: type, params_dict: dict
    ) -> None:
        """Test all metric types can be instantiated successfully."""
        params = params_class(**params_dict)
        metric = Metric(
            name=f"test_{metric_type}_metric",
            type=metric_type,  # type: ignore
            type_params=params,  # type: ignore
        )
        assert metric.name == f"test_{metric_type}_metric"
        assert metric.type == metric_type
        assert isinstance(metric.type_params, params_class)
