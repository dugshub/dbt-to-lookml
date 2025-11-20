"""Integration tests for join field exposure control."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

lkml = pytest.importorskip("lkml")

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser


def _extract_dimension_fields_from_view(
    view_dict: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Extract dimension and measure field names from parsed LookML view.

    Note: For dimension_groups, the set contains individual timeframe names
    (e.g., 'created_date_date', 'created_date_week') not the base name.

    Args:
        view_dict: Parsed LookML view dictionary

    Returns:
        Tuple of (dimension_field_names, measure_field_names)
    """
    dimension_fields = []
    measure_fields = []

    # Regular dimensions
    for dim in view_dict.get("dimensions", []):
        dimension_fields.append(dim["name"])

    # Dimension groups (time dimensions) - extract individual timeframe fields
    for dg in view_dict.get("dimension_groups", []):
        base_name = dg["name"]
        timeframes = dg.get("timeframes", [])
        # In LookML sets, dimension_groups are referenced by individual timeframes
        for timeframe in timeframes:
            dimension_fields.append(f"{base_name}_{timeframe}")

    # Measures
    for measure in view_dict.get("measures", []):
        measure_fields.append(measure["name"])

    return dimension_fields, measure_fields


def _verify_set_contains_only_dimensions(
    set_fields: list[str],
    dimension_fields: list[str],
    measure_fields: list[str],
    view_name: str,
) -> None:
    """Verify that a dimensions_only set contains all dimensions and no measures.

    Args:
        set_fields: List of field names in the set
        dimension_fields: List of expected dimension field names
        measure_fields: List of measure field names (should NOT be in set)
        view_name: Name of the view (for error messages)

    Raises:
        AssertionError: If validation fails
    """
    # Verify all dimensions are present
    for dim_field in dimension_fields:
        assert dim_field in set_fields, (
            f"Dimension {dim_field} missing from {view_name}.dimensions_only set"
        )

    # Verify no measures are present
    for measure_field in measure_fields:
        assert measure_field not in set_fields, (
            f"Measure {measure_field} should NOT be in {view_name}.dimensions_only set"
        )

    # Verify set doesn't contain unexpected fields
    for field in set_fields:
        assert field in dimension_fields, (
            f"Unexpected field {field} in {view_name}.dimensions_only set"
        )


class TestJoinFieldExposure:
    """Test field exposure control in explore joins."""

    @pytest.fixture
    def semantic_models_dir(self) -> Path:
        """Return path to semantic models test fixtures."""
        return Path(__file__).parent.parent.parent / "semantic_models"

    def test_single_join_has_field_constraint(self, semantic_models_dir: Path) -> None:
        """Test that single join includes fields parameter with dimensions_only set.

        Scenario: Fact table (rental_orders) joins dimension table (users)
        Expected: Join should have fields: [users.dimensions_only*]
        """
        parser = DbtParser()
        # Specify rental_orders as fact model to generate explores
        generator = LookMLGenerator(fact_models=["rental_orders"])

        # Parse rental_orders (fact) and users (dimension)
        all_models = parser.parse_directory(semantic_models_dir)
        fact_models = [m for m in all_models if m.name == "rental_orders"]

        assert len(fact_models) == 1

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )

            assert len(validation_errors) == 0

            # Parse explores file
            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            parsed = lkml.load(explores_content)

            # Find rental_orders explore
            rental_explore = None
            for explore in parsed.get("explores", []):
                if explore["name"] == "rental_orders":
                    rental_explore = explore
                    break

            assert rental_explore is not None, "rental_orders explore not found"

            # Verify joins exist
            joins = rental_explore.get("joins", [])
            assert len(joins) >= 1, "Expected at least one join"

            # Find users join
            users_join = None
            for join in joins:
                if join["name"] == "users":
                    users_join = join
                    break

            assert users_join is not None, "users join not found"

            # Verify fields parameter exists and references dimensions_only
            assert "fields" in users_join, "fields parameter missing from join"
            fields_value = users_join["fields"]

            # Should be a list with one element: "users.dimensions_only*"
            assert isinstance(fields_value, list)
            assert len(fields_value) == 1
            assert fields_value[0] == "users.dimensions_only*"

    def test_multi_hop_joins_have_field_constraints(
        self, semantic_models_dir: Path
    ) -> None:
        """Test that multi-hop joins maintain field constraints at each level.

        Scenario: rental_orders → users, rental_orders → searches
        Expected: Both joins should have fields parameter
        """
        parser = DbtParser()
        # Specify rental_orders as fact model to generate explores
        generator = LookMLGenerator(fact_models=["rental_orders"])

        all_models = parser.parse_directory(semantic_models_dir)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )

            assert len(validation_errors) == 0

            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            parsed = lkml.load(explores_content)

            # Find rental_orders explore
            rental_explore = None
            for explore in parsed.get("explores", []):
                if explore["name"] == "rental_orders":
                    rental_explore = explore
                    break

            assert rental_explore is not None
            joins = rental_explore.get("joins", [])

            # Should have at least 2 joins (users and searches)
            assert len(joins) >= 2

            # Verify each join has fields parameter
            for join in joins:
                join_name = join["name"]
                assert "fields" in join, (
                    f"fields parameter missing from {join_name} join"
                )

                fields_value = join["fields"]
                assert isinstance(fields_value, list)
                assert len(fields_value) == 1

                # Should reference the joined view's dimensions_only set
                expected_field = f"{join_name}.dimensions_only*"
                assert fields_value[0] == expected_field, (
                    f"Expected {expected_field}, got {fields_value[0]}"
                )

    def test_join_fields_exclude_measures(self, semantic_models_dir: Path) -> None:
        """Test that joined views only expose dimensions, not measures.

        Verification: Parse generated view to extract dimension names,
        then verify the dimensions_only set matches those dimensions
        and does NOT include measure names.
        """
        parser = DbtParser()
        generator = LookMLGenerator()

        all_models = parser.parse_directory(semantic_models_dir)
        next(m for m in all_models if m.name == "users")

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )

            assert len(validation_errors) == 0

            # Parse users view
            users_view_file = output_dir / "users.view.lkml"
            users_content = users_view_file.read_text()
            parsed_view = lkml.load(users_content)

            view = parsed_view["views"][0]

            # Extract set definition
            sets = view.get("sets", [])
            assert len(sets) == 1, "Expected exactly one set (dimensions_only)"

            dimensions_only_set = sets[0]
            assert dimensions_only_set["name"] == "dimensions_only"

            set_fields = dimensions_only_set["fields"]

            # Collect actual dimension names from view
            dimension_fields, measure_fields = _extract_dimension_fields_from_view(view)

            # Verify all dimensions are in the set
            for dim_field in dimension_fields:
                assert dim_field in set_fields, (
                    f"Dimension {dim_field} missing from dimensions_only set"
                )

            # Verify measures are NOT in the set
            for measure_name in measure_fields:
                assert measure_name not in set_fields, (
                    f"Measure {measure_name} should NOT be in dimensions_only set"
                )

    def test_hidden_entities_included_in_dimension_sets(
        self, semantic_models_dir: Path
    ) -> None:
        """Test that hidden entities (primary/foreign keys) are included in dimension sets.

        Rationale: Hidden entities are needed for join relationships to work,
        so they must be in the dimensions_only set even though they're hidden.
        """
        parser = DbtParser()
        generator = LookMLGenerator()

        all_models = parser.parse_directory(semantic_models_dir)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )

            assert len(validation_errors) == 0

            # Check users view (has user_sk primary entity)
            users_view_file = output_dir / "users.view.lkml"
            users_content = users_view_file.read_text()
            parsed_view = lkml.load(users_content)

            view = parsed_view["views"][0]

            # Find the primary key dimension (should be hidden)
            user_sk_dim = None
            for dim in view.get("dimensions", []):
                if dim["name"] == "user_sk":
                    user_sk_dim = dim
                    break

            assert user_sk_dim is not None, "user_sk dimension not found"
            assert user_sk_dim.get("hidden") == "yes", "user_sk should be hidden"
            assert user_sk_dim.get("primary_key") == "yes", (
                "user_sk should be primary key"
            )

            # Verify it's in the dimensions_only set
            sets = view.get("sets", [])
            dimensions_only_set = next(
                s for s in sets if s["name"] == "dimensions_only"
            )

            assert "user_sk" in dimensions_only_set["fields"], (
                "Hidden entity user_sk must be in dimensions_only set for joins to work"
            )

    def test_comprehensive_field_exposure_validation(
        self, semantic_models_dir: Path
    ) -> None:
        """Comprehensive test validating entire field exposure control system.

        This test validates:
        1. All views have dimensions_only sets
        2. Sets contain all dimensions (including hidden entities)
        3. Sets exclude all measures
        4. All joins reference the correct sets
        5. Multi-hop joins maintain constraints
        """
        parser = DbtParser()
        generator = LookMLGenerator()

        all_models = parser.parse_directory(semantic_models_dir)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )

            assert len(validation_errors) == 0

            # Phase 1: Validate all views have correct sets
            view_sets = {}  # Track set contents for join validation

            view_files = [f for f in generated_files if f.name.endswith(".view.lkml")]
            for view_file in view_files:
                content = view_file.read_text()
                parsed = lkml.load(content)
                view = parsed["views"][0]
                view_name = view["name"]

                # Verify set exists
                sets = view.get("sets", [])
                assert len(sets) == 1, f"View {view_name} should have exactly 1 set"

                dimensions_only_set = sets[0]
                assert dimensions_only_set["name"] == "dimensions_only"

                # Extract fields
                dimension_fields, measure_fields = _extract_dimension_fields_from_view(
                    view
                )
                set_fields = dimensions_only_set["fields"]

                # Validate set contents
                _verify_set_contains_only_dimensions(
                    set_fields, dimension_fields, measure_fields, view_name
                )

                # Track for join validation
                view_sets[view_name] = set_fields

            # Phase 2: Validate explore joins reference correct sets
            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            parsed_explores = lkml.load(explores_content)

            for explore in parsed_explores.get("explores", []):
                joins = explore.get("joins", [])

                for join in joins:
                    join_name = join["name"]

                    # Verify fields parameter exists
                    assert "fields" in join, (
                        f"Join {join_name} missing fields parameter in explore {explore['name']}"
                    )

                    # Verify correct format
                    fields_value = join["fields"]
                    expected_field = f"{join_name}.dimensions_only*"
                    assert fields_value == [expected_field], (
                        f"Join {join_name} should have fields: [{expected_field}], got {fields_value}"
                    )

                    # Verify referenced view exists and has the set
                    assert join_name in view_sets, (
                        f"Join references {join_name} but that view was not generated"
                    )

    def test_two_level_join_chain_field_constraints(
        self, semantic_models_dir: Path
    ) -> None:
        """Test field constraints in two-level join chain.

        Graph:
            rental_orders (fact)
            ├── users (dim via user_sk)
            └── searches (dim via search_sk)

        Verification:
        - rental_orders explore has 2 joins
        - Each join has fields parameter
        - Fields reference correct view's dimensions_only set
        """
        parser = DbtParser()
        # Specify rental_orders as fact model to generate explores
        generator = LookMLGenerator(fact_models=["rental_orders"])

        all_models = parser.parse_directory(semantic_models_dir)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )

            assert len(validation_errors) == 0

            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            parsed = lkml.load(explores_content)

            # Find rental_orders explore
            rental_explore = next(
                (e for e in parsed["explores"] if e["name"] == "rental_orders"),
                None,
            )
            assert rental_explore is not None

            joins = rental_explore.get("joins", [])
            join_names = {j["name"] for j in joins}

            # Verify expected joins
            assert "users" in join_names, "Expected users join"
            assert "searches" in join_names, "Expected searches join"

            # Verify each join has correct fields parameter
            for join in joins:
                join_name = join["name"]
                assert "fields" in join
                assert join["fields"] == [f"{join_name}.dimensions_only*"]

                # Verify relationship is correct (many_to_one for FK → PK)
                assert join["relationship"] == "many_to_one"

                # Verify sql_on clause references correct entities
                sql_on = join["sql_on"]
                assert "${rental_orders." in sql_on
                assert "${" + join_name + "." in sql_on
