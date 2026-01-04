"""Integration tests using real-world semantic model fixtures."""

import pytest
from pathlib import Path

import lkml

from dbt_to_lookml_v2.ingestion import DomainBuilder
from dbt_to_lookml_v2.adapters.lookml import LookMLGenerator, ExploreGenerator


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "integration"


class TestIntegrationWithFixtures:
    """Integration tests loading real-world style fixtures."""

    def test_load_fixtures_directory(self):
        """Test that fixtures load without errors."""
        models = DomainBuilder.from_directory(FIXTURES_DIR)

        # Should load 3 models: rentals, facilities, reviews
        assert len(models) == 3
        model_names = {m.name for m in models}
        assert model_names == {"rentals", "facilities", "reviews"}

    def test_explore_configs_from_fact_models(self):
        """Test creating explore configs from fact model names."""
        # Explore configuration is now owned by the adapter, not ingestion
        explores = ExploreGenerator.configs_from_fact_models(["rentals"])

        assert len(explores) == 1
        assert explores[0].name == "rentals"
        assert explores[0].fact_model == "rentals"

    def test_rentals_model_structure(self):
        """Test rentals fact model is parsed correctly."""
        models = DomainBuilder.from_directory(FIXTURES_DIR)
        rentals = next(m for m in models if m.name == "rentals")

        # Check entities
        assert rentals.primary_entity is not None
        assert rentals.primary_entity.name == "rental"
        assert len(rentals.foreign_entities) == 1
        assert rentals.foreign_entities[0].name == "facility"

        # Check dimensions (should have time variants expanded)
        dim_names = {d.name for d in rentals.dimensions}
        assert "transaction_type" in dim_names
        assert "rental_segment" in dim_names

        # Check time dimensions
        time_dims = rentals.time_dimensions
        assert len(time_dims) >= 2  # created_at, starts_at (with variants)

        # Check date selector
        assert rentals.date_selector is not None
        assert "created_at" in rentals.date_selector.dimensions

        # Check measures
        assert len(rentals.measures) >= 3
        measure_names = {m.name for m in rentals.measures}
        assert "checkout_amount" in measure_names
        assert "rental_count" in measure_names

        # Check metrics
        assert len(rentals.metrics) >= 3
        metric_names = {m.name for m in rentals.metrics}
        assert "gov" in metric_names
        assert "gmv" in metric_names
        assert "rental_count" in metric_names

    def test_reviews_model_has_complete_entity(self):
        """Test reviews model has complete: true on rental entity."""
        models = DomainBuilder.from_directory(FIXTURES_DIR)
        reviews = next(m for m in models if m.name == "reviews")

        # Find the rental foreign entity
        rental_entity = next(
            (e for e in reviews.foreign_entities if e.name == "rental"),
            None,
        )
        assert rental_entity is not None
        assert rental_entity.complete is True

    def test_generate_view_files(self):
        """Test LookML view generation for all models."""
        models = DomainBuilder.from_directory(FIXTURES_DIR)

        generator = LookMLGenerator()
        files = generator.generate(models)

        # Check files generated
        assert "rentals.view.lkml" in files
        assert "rentals.metrics.view.lkml" in files
        assert "facilities.view.lkml" in files
        assert "reviews.view.lkml" in files

        # Verify valid LookML
        for filename, content in files.items():
            parsed = lkml.load(content)
            assert "views" in parsed
            assert len(parsed["views"]) > 0

    def test_rentals_view_content(self):
        """Test rentals view has expected content."""
        models = DomainBuilder.from_directory(FIXTURES_DIR)
        generator = LookMLGenerator()
        files = generator.generate(models)

        content = files["rentals.view.lkml"]

        # Should have sql_table_name
        assert "sql_table_name:" in content
        assert "gold_production.rentals" in content

        # Should have dimensions
        assert "dimension:" in content
        assert "transaction_type" in content

        # Should have time dimensions with timeframes
        assert "type: time" in content
        assert "timeframes:" in content

    def test_generate_explore_files(self):
        """Test explore generation with joins."""
        models = DomainBuilder.from_directory(FIXTURES_DIR)

        # Build model lookup
        model_dict = {m.name: m for m in models}

        # Create explore configs from fact model names (adapter owns this)
        explores = ExploreGenerator.configs_from_fact_models(["rentals"])

        generator = ExploreGenerator()
        files = generator.generate(explores, model_dict)

        # Check explore file generated
        assert "rentals.explore.lkml" in files

        # Verify valid LookML
        content = files["rentals.explore.lkml"]
        parsed = lkml.load(content)
        assert "explores" in parsed
        assert len(parsed["explores"]) == 1
        assert parsed["explores"][0]["name"] == "rentals"

    def test_explore_has_inferred_joins(self):
        """Test that explores have joins inferred from entities."""
        models = DomainBuilder.from_directory(FIXTURES_DIR)
        model_dict = {m.name: m for m in models}

        explores = ExploreGenerator.configs_from_fact_models(["rentals"])
        generator = ExploreGenerator()
        files = generator.generate(explores, model_dict)

        content = files["rentals.explore.lkml"]
        parsed = lkml.load(content)

        explore = parsed["explores"][0]
        joins = explore.get("joins", [])

        # Should have facilities join (many_to_one from rentals.facility FK)
        join_names = {j["name"] for j in joins}
        assert "facilities" in join_names

        # Should have reviews join (one_to_many - reviews has FK to rentals)
        assert "reviews" in join_names

        # Check facilities join properties
        facilities_join = next(j for j in joins if j["name"] == "facilities")
        assert facilities_join["relationship"] == "many_to_one"

        # Check reviews join properties
        reviews_join = next(j for j in joins if j["name"] == "reviews")
        assert reviews_join["relationship"] == "one_to_many"
        # Reviews has complete: true, so should NOT have field restriction
        assert "fields" not in reviews_join

    def test_explore_calendar_generated(self):
        """Test that calendar view is generated for explores with date selector."""
        models = DomainBuilder.from_directory(FIXTURES_DIR)
        model_dict = {m.name: m for m in models}

        explores = ExploreGenerator.configs_from_fact_models(["rentals"])
        generator = ExploreGenerator()
        files = generator.generate(explores, model_dict)

        # Should have calendar view
        assert "rentals_explore_calendar.view.lkml" in files

        content = files["rentals_explore_calendar.view.lkml"]
        parsed = lkml.load(content)

        view = parsed["views"][0]
        assert view["name"] == "rentals_explore_calendar"

        # Should have parameter
        assert "parameters" in view
        param = view["parameters"][0]
        assert param["name"] == "date_field"

        # Should have allowed values for date selector dimensions
        allowed = param.get("allowed_values", [])
        labels = {av["label"] for av in allowed}
        # Should include rentals date options
        assert any("Rental" in label or "rental" in label.lower() for label in labels)

    def test_pop_variants_generated(self):
        """Test that PoP variants are generated for metrics with pop config."""
        models = DomainBuilder.from_directory(FIXTURES_DIR)
        rentals = next(m for m in models if m.name == "rentals")

        # Find GOV metric which has PoP config
        gov_metric = rentals.get_metric("gov")
        assert gov_metric is not None
        assert gov_metric.has_pop

        # Generate and check pop file
        generator = LookMLGenerator()
        files = generator.generate(models)

        assert "rentals.pop.view.lkml" in files

        content = files["rentals.pop.view.lkml"]
        # Should have prior year and prior month variants
        assert "gov_py" in content or "gmv_py" in content

    def test_full_generation_output(self):
        """Test full generation and print summary."""
        models = DomainBuilder.from_directory(FIXTURES_DIR)
        model_dict = {m.name: m for m in models}

        view_generator = LookMLGenerator()
        explore_generator = ExploreGenerator()

        # Create explores from fact model names (adapter owns this config)
        explores = ExploreGenerator.configs_from_fact_models(["rentals"])

        view_files = view_generator.generate(models)
        explore_files = explore_generator.generate(explores, model_dict)

        all_files = {**view_files, **explore_files}

        print("\n=== Generated Files ===")
        for filename in sorted(all_files.keys()):
            lines = all_files[filename].count("\n")
            print(f"  {filename}: {lines} lines")

        print(f"\nTotal: {len(all_files)} files")

        # All files should be valid LookML
        for filename, content in all_files.items():
            try:
                lkml.load(content)
            except Exception as e:
                pytest.fail(f"Invalid LookML in {filename}: {e}")


class TestGeneratedLookMLContent:
    """Tests verifying specific LookML content generation."""

    @pytest.fixture
    def generated_files(self):
        """Generate all files from fixtures."""
        models = DomainBuilder.from_directory(FIXTURES_DIR)
        model_dict = {m.name: m for m in models}

        view_generator = LookMLGenerator()
        explore_generator = ExploreGenerator()

        # Create explores from fact model names (adapter owns this config)
        explores = ExploreGenerator.configs_from_fact_models(["rentals"])

        view_files = view_generator.generate(models)
        explore_files = explore_generator.generate(explores, model_dict)

        return {**view_files, **explore_files}

    def test_rentals_view_has_primary_key(self, generated_files):
        """Test that rentals view has primary key dimension."""
        content = generated_files["rentals.view.lkml"]
        parsed = lkml.load(content)

        view = parsed["views"][0]
        dims = view.get("dimensions", [])

        # Find the rental entity dimension
        rental_dim = next((d for d in dims if d["name"] == "rental"), None)
        assert rental_dim is not None
        assert rental_dim.get("primary_key") == "yes"

    def test_facilities_join_is_many_to_one(self, generated_files):
        """Test facilities join has correct relationship."""
        content = generated_files["rentals.explore.lkml"]
        parsed = lkml.load(content)

        explore = parsed["explores"][0]
        facilities_join = next(
            (j for j in explore.get("joins", []) if j["name"] == "facilities"),
            None,
        )

        assert facilities_join is not None
        assert facilities_join["relationship"] == "many_to_one"
        # Facilities is a dimension model, should have field restriction
        assert facilities_join.get("fields") == ["facilities.dimensions_only*"]

    def test_reviews_join_exposes_all_fields(self, generated_files):
        """Test reviews join exposes all fields due to complete: true."""
        content = generated_files["rentals.explore.lkml"]
        parsed = lkml.load(content)

        explore = parsed["explores"][0]
        reviews_join = next(
            (j for j in explore.get("joins", []) if j["name"] == "reviews"),
            None,
        )

        assert reviews_join is not None
        assert reviews_join["relationship"] == "one_to_many"
        # complete: true means no field restriction
        assert "fields" not in reviews_join

    def test_calendar_has_case_statement(self, generated_files):
        """Test calendar view has CASE statement for dynamic date selection."""
        content = generated_files["rentals_explore_calendar.view.lkml"]
        parsed = lkml.load(content)

        view = parsed["views"][0]
        dim_groups = view.get("dimension_groups", [])
        calendar = next((d for d in dim_groups if d["name"] == "calendar"), None)

        assert calendar is not None
        assert "CASE" in calendar["sql"]
        assert "{% parameter date_field %}" in calendar["sql"]
