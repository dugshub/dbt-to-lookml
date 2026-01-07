"""Tests for explore generation - Phase 4."""

import lkml

from semantic_patterns.adapters.lookml import (
    CalendarRenderer,
    DateOption,
    ExploreGenerator,
    ExploreRenderer,
)
from semantic_patterns.adapters.lookml.types import (
    ExploreConfig,
    ExposeLevel,
    InferredJoin,
    JoinOverride,
    JoinRelationship,
)
from semantic_patterns.domain import (
    DateSelectorConfig,
    Dimension,
    DimensionType,
    Entity,
    ProcessedModel,
    TimeGranularity,
)


class TestDateOption:
    """Tests for DateOption dataclass."""

    def test_parameter_value_uses_double_underscore(self):
        option = DateOption(
            view="rentals",
            dimension="created_at",
            label="Rental Created",
            raw_ref="${rentals.created_at_raw}",
        )
        assert option.parameter_value == "rentals__created_at"

    def test_parameter_value_with_underscored_names(self):
        option = DateOption(
            view="rental_orders",
            dimension="created_at_utc",
            label="Order Created UTC",
            raw_ref="${rental_orders.created_at_utc_raw}",
        )
        assert option.parameter_value == "rental_orders__created_at_utc"


class TestCalendarRenderer:
    """Tests for calendar view rendering."""

    def test_render_calendar_view_structure(self):
        options = [
            DateOption(
                view="rentals",
                dimension="created_at",
                label="Rental Created",
                raw_ref="${rentals.created_at_raw}",
            ),
            DateOption(
                view="rentals",
                dimension="starts_at",
                label="Rental Starts",
                raw_ref="${rentals.starts_at_raw}",
            ),
        ]

        renderer = CalendarRenderer()
        result = renderer.render("rentals", options)

        assert result is not None
        assert result["name"] == "rentals_explore_calendar"
        assert len(result["parameters"]) == 1
        assert len(result["dimension_groups"]) == 1

    def test_render_parameter_with_allowed_values(self):
        options = [
            DateOption(
                view="rentals",
                dimension="created_at",
                label="Rental Created",
                raw_ref="${rentals.created_at_raw}",
            ),
            DateOption(
                view="facilities",
                dimension="opened_at",
                label="Facility Opened",
                raw_ref="${facilities.opened_at_raw}",
            ),
        ]

        renderer = CalendarRenderer()
        result = renderer.render("rentals", options)

        param = result["parameters"][0]
        assert param["name"] == "date_field"
        assert param["type"] == "unquoted"
        assert param["label"] == "Analysis Date"
        assert param["view_label"] == " Calendar"  # Space prefix
        assert param["default_value"] == "rentals__created_at"
        assert len(param["allowed_values"]) == 2
        assert param["allowed_values"][0]["label"] == "Rental Created"
        assert param["allowed_values"][0]["value"] == "rentals__created_at"

    def test_render_dimension_group_with_case(self):
        options = [
            DateOption(
                view="rentals",
                dimension="created_at",
                label="Rental Created",
                raw_ref="${rentals.created_at_raw}",
            ),
            DateOption(
                view="facilities",
                dimension="opened_at",
                label="Facility Opened",
                raw_ref="${facilities.opened_at_raw}",
            ),
        ]

        renderer = CalendarRenderer()
        result = renderer.render("rentals", options)

        dim_group = result["dimension_groups"][0]
        assert dim_group["name"] == "calendar"
        assert dim_group["type"] == "time"
        assert dim_group["view_label"] == " Calendar"
        assert "convert_tz" not in dim_group  # Removed - not needed
        assert "date" in dim_group["timeframes"]
        assert "{% parameter date_field %}" in dim_group["sql"]
        assert "rentals__created_at" in dim_group["sql"]
        assert "${rentals.created_at_raw}" in dim_group["sql"]

    def test_render_returns_none_for_empty_options(self):
        renderer = CalendarRenderer()
        result = renderer.render("rentals", [])
        assert result is None

    def test_collect_date_options_from_single_model(self):
        model = ProcessedModel(
            name="rentals",
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    label="Created At",
                    granularity=TimeGranularity.DAY,
                    expr="created_at_utc",
                ),
                Dimension(
                    name="starts_at",
                    type=DimensionType.TIME,
                    granularity=TimeGranularity.DAY,
                    expr="starts_at_utc",
                ),
            ],
            date_selector=DateSelectorConfig(dimensions=["created_at", "starts_at"]),
        )

        renderer = CalendarRenderer()
        options = renderer.collect_date_options(model, [])

        assert len(options) == 2
        assert options[0].view == "rentals"
        assert options[0].dimension == "created_at"
        assert options[0].label == "Rentals Created At"  # Smart title
        assert options[0].raw_ref == "${rentals.created_at_raw}"

    def test_collect_date_options_from_multiple_models(self):
        fact_model = ProcessedModel(
            name="rentals",
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    granularity=TimeGranularity.DAY,
                    expr="created_at_utc",
                ),
            ],
            date_selector=DateSelectorConfig(dimensions=["created_at"]),
        )

        joined_model = ProcessedModel(
            name="facilities",
            dimensions=[
                Dimension(
                    name="opened_at",
                    type=DimensionType.TIME,
                    label="Opened Date",
                    granularity=TimeGranularity.DAY,
                    expr="opened_at_utc",
                ),
            ],
            date_selector=DateSelectorConfig(dimensions=["opened_at"]),
        )

        renderer = CalendarRenderer()
        options = renderer.collect_date_options(fact_model, [joined_model])

        assert len(options) == 2
        views = {o.view for o in options}
        assert views == {"rentals", "facilities"}

    def test_collect_date_options_skips_models_without_date_selector(self):
        fact_model = ProcessedModel(
            name="rentals",
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    granularity=TimeGranularity.DAY,
                    expr="created_at_utc",
                ),
            ],
            date_selector=DateSelectorConfig(dimensions=["created_at"]),
        )

        joined_model = ProcessedModel(
            name="facilities",
            dimensions=[
                Dimension(
                    name="opened_at",
                    type=DimensionType.TIME,
                    granularity=TimeGranularity.DAY,
                    expr="opened_at_utc",
                ),
            ],
            # No date_selector
        )

        renderer = CalendarRenderer()
        options = renderer.collect_date_options(fact_model, [joined_model])

        assert len(options) == 1
        assert options[0].view == "rentals"


class TestExploreRenderer:
    """Tests for explore rendering."""

    def test_single_model_explore(self):
        fact_model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
            ],
        )

        config = ExploreConfig(name="rentals", fact_model="rentals")
        renderer = ExploreRenderer()
        result, includes = renderer.render(config, fact_model, {"rentals": fact_model})

        assert result["name"] == "rentals"
        assert result["label"] == "Rentals"
        # No joins for single model (except calendar if has dates)
        assert "joins" not in result or len(result["joins"]) == 0

    def test_many_to_one_relationship(self):
        fact_model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
                Entity(name="facility", type="foreign", expr="facility_sk"),
            ],
        )

        dim_model = ProcessedModel(
            name="facilities",
            entities=[
                Entity(name="facility", type="primary", expr="facility_sk"),
            ],
        )

        models = {"rentals": fact_model, "facilities": dim_model}
        config = ExploreConfig(name="rentals", fact_model="rentals")

        renderer = ExploreRenderer()
        result, includes = renderer.render(config, fact_model, models)

        assert "joins" in result
        join = next(j for j in result["joins"] if j["name"] == "facilities")
        assert join["relationship"] == "many_to_one"
        assert join["type"] == "left_outer"
        assert "${rentals.facility_sk}" in join["sql_on"]
        assert "${facilities.facility_sk}" in join["sql_on"]

    def test_one_to_many_relationship(self):
        fact_model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
            ],
        )

        child_model = ProcessedModel(
            name="reviews",
            entities=[
                Entity(name="review", type="primary", expr="review_id"),
                Entity(name="rental", type="foreign", expr="rental_sk"),
            ],
        )

        models = {"rentals": fact_model, "reviews": child_model}
        config = ExploreConfig(name="rentals", fact_model="rentals")

        renderer = ExploreRenderer()
        result, includes = renderer.render(config, fact_model, models)

        assert "joins" in result
        join = next(j for j in result["joins"] if j["name"] == "reviews")
        assert join["relationship"] == "one_to_many"

    def test_complete_true_exposes_all_fields(self):
        fact_model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
            ],
        )

        child_model = ProcessedModel(
            name="reviews",
            entities=[
                Entity(name="review", type="primary", expr="review_id"),
                Entity(name="rental", type="foreign", expr="rental_sk", complete=True),
            ],
        )

        models = {"rentals": fact_model, "reviews": child_model}
        config = ExploreConfig(name="rentals", fact_model="rentals")

        renderer = ExploreRenderer()
        result, includes = renderer.render(config, fact_model, models)

        join = next(j for j in result["joins"] if j["name"] == "reviews")
        # No field restriction when complete=true
        assert "fields" not in join

    def test_complete_false_exposes_dimensions_only(self):
        fact_model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
            ],
        )

        child_model = ProcessedModel(
            name="searches",
            entities=[
                Entity(name="search", type="primary", expr="search_id"),
                Entity(name="rental", type="foreign", expr="rental_sk", complete=False),
            ],
        )

        models = {"rentals": fact_model, "searches": child_model}
        config = ExploreConfig(name="rentals", fact_model="rentals")

        renderer = ExploreRenderer()
        result, includes = renderer.render(config, fact_model, models)

        join = next(j for j in result["joins"] if j["name"] == "searches")
        assert join["fields"] == ["searches.dimensions_only*"]

    def test_join_override_changes_expose_level(self):
        fact_model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
            ],
        )

        child_model = ProcessedModel(
            name="reviews",
            entities=[
                Entity(name="review", type="primary", expr="review_id"),
                Entity(name="rental", type="foreign", expr="rental_sk", complete=True),
            ],
        )

        models = {"rentals": fact_model, "reviews": child_model}

        # Override to only expose dimensions even though complete=true
        config = ExploreConfig(
            name="rentals",
            fact_model="rentals",
            join_overrides=[
                JoinOverride(model="reviews", expose=ExposeLevel.DIMENSIONS)
            ],
        )

        renderer = ExploreRenderer()
        result, includes = renderer.render(config, fact_model, models)

        join = next(j for j in result["joins"] if j["name"] == "reviews")
        assert join["fields"] == ["reviews.dimensions_only*"]

    def test_multi_join_explore(self):
        fact_model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
                Entity(name="facility", type="foreign", expr="facility_sk"),
                Entity(name="customer", type="foreign", expr="customer_sk"),
            ],
        )

        facilities = ProcessedModel(
            name="facilities",
            entities=[Entity(name="facility", type="primary", expr="facility_sk")],
        )

        customers = ProcessedModel(
            name="customers",
            entities=[Entity(name="customer", type="primary", expr="customer_sk")],
        )

        models = {
            "rentals": fact_model,
            "facilities": facilities,
            "customers": customers,
        }
        config = ExploreConfig(name="rentals", fact_model="rentals")

        renderer = ExploreRenderer()
        result, includes = renderer.render(config, fact_model, models)

        join_names = {j["name"] for j in result["joins"]}
        assert "facilities" in join_names
        assert "customers" in join_names

    def test_infer_joins_many_to_one(self):
        fact_model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
                Entity(name="facility", type="foreign", expr="facility_sk"),
            ],
        )

        dim_model = ProcessedModel(
            name="facilities",
            entities=[Entity(name="facility", type="primary", expr="facility_sk")],
        )

        models = {"rentals": fact_model, "facilities": dim_model}
        config = ExploreConfig(name="rentals", fact_model="rentals")

        renderer = ExploreRenderer()
        joins = renderer.infer_joins(fact_model, models, config)

        assert len(joins) == 1
        assert joins[0].model == "facilities"
        assert joins[0].relationship == JoinRelationship.MANY_TO_ONE
        assert joins[0].entity == "facility"


class TestExploreGenerator:
    """Tests for explore generator orchestrator."""

    def test_generate_explore_file(self):
        fact_model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
            ],
        )

        models = {"rentals": fact_model}
        config = ExploreConfig(name="rentals", fact_model="rentals")

        generator = ExploreGenerator()
        files = generator.generate([config], models)

        assert "rentals.explore.lkml" in files
        content = files["rentals.explore.lkml"]
        assert "explore: rentals" in content

    def test_generate_explore_and_calendar(self):
        fact_model = ProcessedModel(
            name="rentals",
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    granularity=TimeGranularity.DAY,
                    expr="created_at_utc",
                ),
            ],
            date_selector=DateSelectorConfig(dimensions=["created_at"]),
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
            ],
        )

        models = {"rentals": fact_model}
        config = ExploreConfig(name="rentals", fact_model="rentals")

        generator = ExploreGenerator()
        files = generator.generate([config], models)

        assert "rentals.explore.lkml" in files
        assert "rentals_explore_calendar.view.lkml" in files

        calendar_content = files["rentals_explore_calendar.view.lkml"]
        assert "view: rentals_explore_calendar" in calendar_content
        assert "parameter: date_field" in calendar_content

    def test_skip_calendar_when_no_dates(self):
        fact_model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
            ],
            # No date_selector
        )

        models = {"rentals": fact_model}
        config = ExploreConfig(name="rentals", fact_model="rentals")

        generator = ExploreGenerator()
        files = generator.generate([config], models)

        assert "rentals.explore.lkml" in files
        assert "rentals_explore_calendar.view.lkml" not in files

    def test_generated_explore_is_valid_lookml(self):
        fact_model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
                Entity(name="facility", type="foreign", expr="facility_sk"),
            ],
        )

        dim_model = ProcessedModel(
            name="facilities",
            entities=[Entity(name="facility", type="primary", expr="facility_sk")],
        )

        models = {"rentals": fact_model, "facilities": dim_model}
        config = ExploreConfig(name="rentals", fact_model="rentals")

        generator = ExploreGenerator()
        files = generator.generate([config], models)

        # Should be parseable LookML
        content = files["rentals.explore.lkml"]
        parsed = lkml.load(content)
        assert "explores" in parsed
        assert len(parsed["explores"]) == 1
        assert parsed["explores"][0]["name"] == "rentals"

    def test_generated_calendar_is_valid_lookml(self):
        fact_model = ProcessedModel(
            name="rentals",
            dimensions=[
                Dimension(
                    name="created_at",
                    type=DimensionType.TIME,
                    granularity=TimeGranularity.DAY,
                    expr="created_at_utc",
                ),
            ],
            date_selector=DateSelectorConfig(dimensions=["created_at"]),
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
            ],
        )

        models = {"rentals": fact_model}
        config = ExploreConfig(name="rentals", fact_model="rentals")

        generator = ExploreGenerator()
        files = generator.generate([config], models)

        # Should be parseable LookML
        content = files["rentals_explore_calendar.view.lkml"]
        parsed = lkml.load(content)
        assert "views" in parsed
        assert parsed["views"][0]["name"] == "rentals_explore_calendar"

    def test_skip_explore_when_fact_model_not_found(self):
        fact_model = ProcessedModel(
            name="rentals",
            entities=[
                Entity(name="rental", type="primary", expr="rental_sk"),
            ],
        )

        models = {"rentals": fact_model}
        # Config references non-existent model
        config = ExploreConfig(name="orders", fact_model="orders")

        generator = ExploreGenerator()
        files = generator.generate([config], models)

        # Should generate nothing for missing model
        assert "orders.explore.lkml" not in files

    def test_generate_multiple_explores(self):
        rentals = ProcessedModel(
            name="rentals",
            entities=[Entity(name="rental", type="primary", expr="rental_sk")],
        )
        orders = ProcessedModel(
            name="orders",
            entities=[Entity(name="order", type="primary", expr="order_sk")],
        )

        models = {"rentals": rentals, "orders": orders}
        configs = [
            ExploreConfig(name="rentals", fact_model="rentals"),
            ExploreConfig(name="orders", fact_model="orders"),
        ]

        generator = ExploreGenerator()
        files = generator.generate(configs, models)

        assert "rentals.explore.lkml" in files
        assert "orders.explore.lkml" in files


class TestInferredJoin:
    """Tests for InferredJoin domain type."""

    def test_sql_on_property(self):
        join = InferredJoin(
            model="facilities",
            entity="facility",
            relationship=JoinRelationship.MANY_TO_ONE,
            expose=ExposeLevel.ALL,
            fact_entity_expr="facility_sk",
            joined_entity_expr="facility_sk",
        )

        # sql_on is a template with ${FACT} placeholder
        assert "facility_sk" in join.sql_on
        assert "${FACT}" in join.sql_on
        assert "${facilities}" in join.sql_on


class TestExploreConfig:
    """Tests for ExploreConfig domain type."""

    def test_get_override_returns_matching_override(self):
        config = ExploreConfig(
            name="rentals",
            fact_model="rentals",
            join_overrides=[
                JoinOverride(model="reviews", expose=ExposeLevel.DIMENSIONS),
                JoinOverride(model="facilities", expose=ExposeLevel.ALL),
            ],
        )

        override = config.get_override("reviews")
        assert override is not None
        assert override.expose == ExposeLevel.DIMENSIONS

    def test_get_override_returns_none_for_no_match(self):
        config = ExploreConfig(
            name="rentals",
            fact_model="rentals",
            join_overrides=[
                JoinOverride(model="reviews", expose=ExposeLevel.DIMENSIONS),
            ],
        )

        override = config.get_override("facilities")
        assert override is None
