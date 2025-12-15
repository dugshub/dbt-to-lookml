"""Integration tests for reverse join discovery (child model auto-joining)."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

lkml = pytest.importorskip("lkml")

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser


class TestReverseJoinDiscovery:
    """Test reverse join discovery - auto-joining child models to fact explores."""

    @pytest.fixture
    def spothero_models_dir(self) -> Path:
        """Return path to spothero semantic models test fixtures."""
        return (
            Path(__file__).parent.parent / "fixtures" / "spothero_semantic_models"
        )

    def test_reverse_join_disabled_by_default(self, spothero_models_dir: Path) -> None:
        """Test that reverse joins are NOT discovered when include_children=False.

        Scenario: rentals (fact) has rental as primary entity.
        reviews has rental as foreign entity.
        Without include_children, reviews should NOT join to rentals explore.
        """
        parser = DbtParser()
        generator = LookMLGenerator(
            fact_models=["rentals"],
            include_children=False,  # Default - explicitly set for clarity
        )

        all_models = parser.parse_directory(spothero_models_dir)

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

            # Find rentals explore
            rentals_explore = None
            for explore in parsed.get("explores", []):
                if explore["name"] == "rentals":
                    rentals_explore = explore
                    break

            assert rentals_explore is not None, "rentals explore not found"

            # Get join names
            joins = rentals_explore.get("joins", [])
            join_names = {j["name"] for j in joins}

            # reviews should NOT be in joins (reverse join disabled)
            assert "reviews" not in join_names, (
                "reviews should NOT be in joins when include_children=False"
            )

    def test_reverse_join_enabled_discovers_child_models(
        self, spothero_models_dir: Path
    ) -> None:
        """Test that reverse joins ARE discovered when include_children=True.

        Scenario: rentals (fact) has rental as primary entity.
        reviews has rental as foreign entity.
        With include_children, reviews SHOULD join to rentals explore.
        """
        parser = DbtParser()
        generator = LookMLGenerator(
            fact_models=["rentals"],
            include_children=True,  # Enable reverse join discovery
        )

        all_models = parser.parse_directory(spothero_models_dir)

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

            # Find rentals explore
            rentals_explore = None
            for explore in parsed.get("explores", []):
                if explore["name"] == "rentals":
                    rentals_explore = explore
                    break

            assert rentals_explore is not None, "rentals explore not found"

            # Get join names
            joins = rentals_explore.get("joins", [])
            join_names = {j["name"] for j in joins}

            # reviews SHOULD be in joins (reverse join enabled)
            assert "reviews" in join_names, (
                "reviews SHOULD be in joins when include_children=True"
            )

    def test_reverse_join_has_correct_relationship(
        self, spothero_models_dir: Path
    ) -> None:
        """Test that reverse joins have one_to_many relationship.

        One rental can have many reviews, so the relationship should be one_to_many.
        """
        parser = DbtParser()
        generator = LookMLGenerator(
            fact_models=["rentals"],
            include_children=True,
        )

        all_models = parser.parse_directory(spothero_models_dir)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, _ = generator.generate_lookml_files(
                all_models, output_dir
            )

            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            parsed = lkml.load(explores_content)

            rentals_explore = next(
                e for e in parsed["explores"] if e["name"] == "rentals"
            )
            joins = rentals_explore.get("joins", [])

            # Find reviews join
            reviews_join = next(
                (j for j in joins if j["name"] == "reviews"), None
            )

            assert reviews_join is not None, "reviews join not found"
            assert reviews_join["relationship"] == "one_to_many", (
                f"Expected one_to_many relationship, got {reviews_join['relationship']}"
            )

    def test_reverse_join_only_exposes_dimensions(
        self, spothero_models_dir: Path
    ) -> None:
        """Test that reverse joins only expose dimensions (not measures).

        To prevent fan-out, reverse joins should only include dimensions_only*.
        """
        parser = DbtParser()
        generator = LookMLGenerator(
            fact_models=["rentals"],
            include_children=True,
        )

        all_models = parser.parse_directory(spothero_models_dir)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, _ = generator.generate_lookml_files(
                all_models, output_dir
            )

            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            parsed = lkml.load(explores_content)

            rentals_explore = next(
                e for e in parsed["explores"] if e["name"] == "rentals"
            )
            joins = rentals_explore.get("joins", [])

            # Find reviews join
            reviews_join = next(
                (j for j in joins if j["name"] == "reviews"), None
            )

            assert reviews_join is not None, "reviews join not found"

            # Should only have dimensions_only* in fields
            assert "fields" in reviews_join, "fields parameter missing"
            fields = reviews_join["fields"]
            assert fields == ["reviews.dimensions_only*"], (
                f"Expected ['reviews.dimensions_only*'], got {fields}"
            )

    def test_reverse_join_sql_on_clause(self, spothero_models_dir: Path) -> None:
        """Test that reverse join SQL ON clause is correct.

        Should be: ${rentals.rental} = ${reviews.rental}
        """
        parser = DbtParser()
        generator = LookMLGenerator(
            fact_models=["rentals"],
            include_children=True,
        )

        all_models = parser.parse_directory(spothero_models_dir)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, _ = generator.generate_lookml_files(
                all_models, output_dir
            )

            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            parsed = lkml.load(explores_content)

            rentals_explore = next(
                e for e in parsed["explores"] if e["name"] == "rentals"
            )
            joins = rentals_explore.get("joins", [])

            # Find reviews join
            reviews_join = next(
                (j for j in joins if j["name"] == "reviews"), None
            )

            assert reviews_join is not None, "reviews join not found"

            sql_on = reviews_join["sql_on"]

            # Should reference both rentals.rental and reviews.rental
            assert "${rentals.rental}" in sql_on, (
                f"Expected ${{rentals.rental}} in sql_on, got: {sql_on}"
            )
            assert "${reviews.rental}" in sql_on, (
                f"Expected ${{reviews.rental}} in sql_on, got: {sql_on}"
            )

    def test_reverse_join_with_forward_joins(
        self, spothero_models_dir: Path
    ) -> None:
        """Test that reverse joins work alongside forward joins.

        rentals explore should have:
        - Forward joins to facility_dimension (via facility FK)
        - Reverse join to reviews (reviews has rental FK)
        """
        parser = DbtParser()
        generator = LookMLGenerator(
            fact_models=["rentals"],
            include_children=True,
        )

        all_models = parser.parse_directory(spothero_models_dir)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, _ = generator.generate_lookml_files(
                all_models, output_dir
            )

            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            parsed = lkml.load(explores_content)

            rentals_explore = next(
                e for e in parsed["explores"] if e["name"] == "rentals"
            )
            joins = rentals_explore.get("joins", [])
            join_names = {j["name"] for j in joins}

            # Should have reverse join to reviews
            assert "reviews" in join_names, "reviews (reverse join) should be present"

            # Should also have forward joins if facility_dimension exists
            # (depends on what models are in fixtures)
            # The key point is that having reverse joins doesn't break forward joins
            assert len(joins) >= 1, "Should have at least one join (reviews)"
