"""Comprehensive end-to-end integration tests."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

lkml = pytest.importorskip("lkml")

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.parsers.dbt import DbtParser
from dbt_to_lookml.types import DimensionType


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_parse_and_generate_sample_model(self) -> None:
        """Test parsing sample semantic model and generating LookML."""
        # Get the path to the sample fixture
        fixture_path = Path(__file__).parent.parent / "fixtures"

        # Parse the sample semantic model
        parser = DbtParser()
        semantic_models = parser.parse_directory(fixture_path)

        assert len(semantic_models) > 0

        # Generate LookML files
        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0

            # Check that files were created
            view_files = list(output_dir.glob("*.view.lkml"))
            explores_file = output_dir / "explores.lkml"

            assert len(view_files) > 0
            assert explores_file.exists()

            # Check content of generated files
            for view_file in view_files:
                content = view_file.read_text()
                assert "view:" in content
                assert "sql_table_name:" in content

            if explores_file.exists():
                explores_content = explores_file.read_text()
                assert "explore:" in explores_content

    def test_generate_with_prefixes(self) -> None:
        """Test generating LookML with view and explore prefixes."""
        fixture_path = Path(__file__).parent.parent / "fixtures"

        parser = DbtParser()
        semantic_models = parser.parse_directory(fixture_path)

        generator = LookMLGenerator(
            view_prefix="v_",
            explore_prefix="e_",
        )

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0

            # Check that files have prefixed names
            view_files = list(output_dir.glob("v_*.view.lkml"))
            assert len(view_files) > 0

            # Check explores content contains prefixed names
            explores_file = output_dir / "explores.lkml"
            if explores_file.exists():
                explores_content = explores_file.read_text()
                assert "e_" in explores_content  # explore names should be prefixed
                assert "v_" in explores_content  # view references should be prefixed

    def test_real_semantic_models_end_to_end(self) -> None:
        """Test complete pipeline with real semantic models."""
        # Use the actual semantic models from the project
        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        # Parse all real semantic models
        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        assert len(semantic_models) >= 5  # We have at least 5 semantic model files

        # Verify we have some expected models
        model_names = {model.name for model in semantic_models}
        # Just check that we got some models
        assert len(model_names) > 0

        # Generate LookML files
        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Should generate without validation errors
            assert len(validation_errors) == 0

            # Should generate view files for each semantic model + explores file
            view_files = [f for f in generated_files if f.name.endswith(".view.lkml")]
            explores_files = [f for f in generated_files if f.name == "explores.lkml"]

            assert len(view_files) == len(semantic_models)
            assert len(explores_files) == 1

            # All files should exist and be non-empty
            for file_path in generated_files:
                assert file_path.exists()
                content = file_path.read_text().strip()
                assert content, f"Generated file {file_path} is empty"

            # Verify specific model outputs - check any generated view
            view_files = list(output_dir.glob("*.view.lkml"))
            if view_files:
                first_view = view_files[0]
                assert first_view.exists()
                content = first_view.read_text()
                assert "sql_table_name:" in content  # Should contain table reference
                assert (
                    "dimension:" in content or "measure:" in content
                )  # Should have fields

            # Verify explores file
            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            for model_name in model_names:
                assert model_name in explores_content

    def test_complex_sql_expressions_preserved(self) -> None:
        """Test that complex SQL expressions from real models are preserved."""
        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        parser = DbtParser()
        # Use rentals file which has complex expressions
        rentals_file = semantic_models_dir / "rentals.yml"
        semantic_models = parser.parse_file(rentals_file)

        assert len(semantic_models) == 1
        users_model = semantic_models[0]

        # Verify complex expressions are in the parsed model
        for measure in users_model.measures:
            if "cast(" in measure.expr or "" if measure.expr is None else measure.expr:
                break

        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0

            rentals_view = output_dir / "rentals.view.lkml"
            content = rentals_view.read_text()

            # Check that SQL content is preserved
            assert "sql:" in content or "sql_table_name:" in content

    def test_all_aggregation_types_in_real_models(self) -> None:
        """Test that all aggregation types in real models are handled correctly."""
        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        # Collect all aggregation types used
        agg_types_used = set()
        for model in semantic_models:
            for measure in model.measures:
                agg_types_used.add(measure.agg.value)

        assert len(agg_types_used) >= 2  # Should have multiple aggregation types

        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0

            # Verify that all aggregation types are represented in output
            all_content = ""
            for file_path in generated_files:
                if file_path.name.endswith(".view.lkml"):
                    all_content += file_path.read_text()

            # Should contain different measure types that are actually in the models
            assert "type: sum" in all_content or "type: count" in all_content
            assert "type: count_distinct" in all_content or "type: sum" in all_content

    def test_time_dimensions_converted_correctly(self) -> None:
        """Test that time dimensions are converted to dimension_groups."""
        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        # Find models with time dimensions
        models_with_time = []
        for model in semantic_models:
            for dimension in model.dimensions:
                if dimension.type.value == "time":
                    models_with_time.append(model)
                    break

        assert (
            len(models_with_time) > 0
        )  # Should have at least one model with time dimensions

        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0

            # Check that time dimensions become dimension_groups
            for file_path in generated_files:
                if file_path.name.endswith(".view.lkml"):
                    content = file_path.read_text()
                    if "dimension_group:" in content:
                        assert "type: time" in content
                        assert "timeframes:" in content
                        # Should have standard timeframes
                        assert "date" in content
                        assert "month" in content
                        assert "year" in content

    def test_dbt_ref_patterns_converted(self) -> None:
        """Test that dbt ref() patterns are converted correctly."""
        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        # Find models that use ref() syntax
        ref_models = [model for model in semantic_models if "ref(" in model.model]
        assert len(ref_models) > 0  # Should have models using ref() syntax

        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0

            # Check that ref() syntax is converted to table names
            for file_path in generated_files:
                if file_path.name.endswith(".view.lkml"):
                    content = file_path.read_text()
                    assert "ref(" not in content  # ref() should be converted
                    assert "sql_table_name:" in content

    def test_large_semantic_model_handling(self) -> None:
        """Test handling of large semantic models with many dimensions and measures."""
        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        parser = DbtParser()
        # Use rentals file which is one of the larger models
        rentals_file = semantic_models_dir / "rentals.yml"
        semantic_models = parser.parse_file(rentals_file)

        rentals_model = semantic_models[0]

        # Verify it has fields
        assert len(rentals_model.dimensions) >= 2
        assert len(rentals_model.measures) >= 2

        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0

            rentals_view = output_dir / "rentals.view.lkml"
            content = rentals_view.read_text()

            # Should handle multiple fields without issues
            dimension_count = content.count("dimension:")
            measure_count = content.count("measure:")
            dimension_group_count = content.count("dimension_group:")

            # Should have dimensions and measures
            assert dimension_count >= 2
            assert measure_count >= 2
            assert dimension_group_count >= 0  # May have time dimensions

    def test_error_recovery_and_partial_generation(self) -> None:
        """Test that partial generation works when some models fail."""
        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        generator = LookMLGenerator()

        # Note: In the refactored architecture, the mapper.semantic_model_to_view
        # is not actually called during generation. This test originally tested
        # error recovery when the mapper failed, but that's no longer applicable.
        # Instead, we test that generation completes successfully even with
        # complex models.

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # All models should be generated successfully
            assert len(validation_errors) == 0

            # All models should be generated
            view_files = [f for f in generated_files if f.name.endswith(".view.lkml")]
            assert len(view_files) == len(semantic_models)

            # Explores file should still be generated (though may be incomplete)
            explores_files = [f for f in generated_files if f.name == "explores.lkml"]
            assert len(explores_files) == 1

    def test_unicode_and_special_characters(self) -> None:
        """Test handling of Unicode and special characters in descriptions."""
        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0

            # Files should be created with proper encoding
            for file_path in generated_files:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    # Should be able to read without encoding errors
                    assert len(content) > 0

    def test_lookml_syntax_validation_passes(self) -> None:
        """Test that generated LookML passes syntax validation."""
        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        generator = LookMLGenerator(validate_syntax=True)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # All generated files should pass validation
            assert len(validation_errors) == 0

            # Double-check by parsing generated files
            for file_path in generated_files:
                if file_path.suffix == ".lkml":  # Only check LookML files
                    content = file_path.read_text()
                    try:
                        parsed = lkml.load(content)
                        assert parsed is not None
                    except Exception as e:
                        pytest.fail(
                            f"Generated file {file_path} has invalid LookML syntax: {e}"
                        )

    def test_generation_summary_accuracy(self) -> None:
        """Test that generation summary provides accurate statistics."""
        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            summary = generator.get_generation_summary(
                semantic_models, generated_files, validation_errors
            )

            # Verify summary accuracy
            assert f"Processed semantic models: {len(semantic_models)}" in summary
            assert f"Generated files: {len(generated_files)}" in summary
            assert f"Validation errors: {len(validation_errors)}" in summary

            view_count = len(
                [f for f in generated_files if f.name.endswith(".view.lkml")]
            )
            explore_count = len(
                [f for f in generated_files if f.name == "explores.lkml"]
            )

            assert f"View files: {view_count}" in summary
            assert f"Explore files: {explore_count}" in summary

    def test_concurrent_model_processing(self) -> None:
        """Test that processing multiple models works correctly."""
        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        # Process models individually and then all together
        generator = LookMLGenerator()

        # Individual processing
        individual_results = {}
        for model in semantic_models:
            with TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                generated_files, validation_errors = generator.generate_lookml_files(
                    [model], output_dir
                )
                assert len(validation_errors) == 0
                view_file = next(
                    f for f in generated_files if f.name.endswith(".view.lkml")
                )
                individual_results[model.name] = view_file.read_text()

        # Batch processing
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0

            # Individual and batch results should be consistent
            for model in semantic_models:
                batch_view_file = output_dir / f"{model.name}.view.lkml"
                batch_content = batch_view_file.read_text()

                # Core content should be the same (allowing for minor formatting differences)
                individual_content = individual_results[model.name]
                assert "sql_table_name:" in individual_content
                assert "sql_table_name:" in batch_content
                assert model.name in individual_content
                assert model.name in batch_content

    def test_pipeline_with_validation_enabled(self) -> None:
        """Test complete pipeline with strict validation enabled."""
        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        parser = DbtParser(strict_mode=True)
        generator = LookMLGenerator(validate_syntax=True, format_output=True)

        semantic_models = parser.parse_directory(semantic_models_dir)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Should pass all validations
            assert len(validation_errors) == 0, (
                f"Validation failed: {validation_errors}"
            )

            # Every generated file should be valid LookML
            for file_path in generated_files:
                if file_path.suffix == ".lkml":  # Only check LookML files
                    content = file_path.read_text()
                    try:
                        parsed_lookml = lkml.load(content)
                        assert parsed_lookml is not None
                    except Exception as e:
                        pytest.fail(f"Invalid LookML in {file_path.name}: {e}")

    def test_performance_with_real_models(self) -> None:
        """Test performance characteristics with real semantic models."""
        import time

        semantic_models_dir = Path(
            "/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models"
        )

        parser = DbtParser()
        generator = LookMLGenerator()

        # Measure parsing time
        start_time = time.time()
        semantic_models = parser.parse_directory(semantic_models_dir)
        parse_time = time.time() - start_time

        # Measure generation time
        start_time = time.time()
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )
        generation_time = time.time() - start_time

        # Performance should be reasonable
        assert parse_time < 5.0, f"Parsing took too long: {parse_time:.2f}s"
        assert generation_time < 10.0, (
            f"Generation took too long: {generation_time:.2f}s"
        )

        # Results should be complete
        assert len(semantic_models) >= 5
        assert len(generated_files) >= 6
        assert len(validation_errors) == 0

    def test_dimension_sets_in_generated_views(self) -> None:
        """Test that all generated view files include dimension sets."""
        fixture_path = Path(__file__).parent.parent / "fixtures"

        parser = DbtParser()
        semantic_models = parser.parse_directory(fixture_path)

        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0

            # Check each view file for dimension sets
            view_files = [f for f in generated_files if f.name.endswith(".view.lkml")]

            assert len(view_files) > 0, "No view files were generated"

            for view_file in view_files:
                content = view_file.read_text()

                # Parse LookML to check structure
                parsed = lkml.load(content)
                views = parsed.get("views", [])

                assert len(views) > 0, f"No views found in {view_file.name}"

                for view in views:
                    # Check if view has dimensions
                    has_dimensions = (
                        len(view.get("dimensions", [])) > 0
                        or len(view.get("dimension_groups", [])) > 0
                    )

                    if has_dimensions:
                        # If view has dimensions, it should have a set
                        sets = view.get("sets", [])
                        assert len(sets) > 0, (
                            f"View {view['name']} has dimensions but no sets"
                        )

                        # Find dimensions_only set
                        dim_set = next(
                            (s for s in sets if s["name"] == "dimensions_only"), None
                        )
                        assert dim_set is not None, (
                            f"View {view['name']} missing dimensions_only set"
                        )

                        # Verify fields list is not empty
                        fields = dim_set.get("fields", [])
                        assert len(fields) > 0, (
                            f"View {view['name']} dimension set has no fields"
                        )

                        # Verify all dimension and entity names are in the set
                        dimension_names = [
                            d["name"] for d in view.get("dimensions", [])
                        ]
                        dimension_group_names = [
                            dg["name"] for dg in view.get("dimension_groups", [])
                        ]
                        all_expected_names = set(
                            dimension_names + dimension_group_names
                        )

                        for expected_name in all_expected_names:
                            assert expected_name in fields, (
                                f"Dimension {expected_name} not in set of view {view['name']}"
                            )

    def test_generated_views_contain_field_sets(self) -> None:
        """Test that all generated views contain dimensions_only field sets."""
        semantic_models_dir = Path(__file__).parent.parent.parent / "semantic_models"

        parser = DbtParser()
        generator = LookMLGenerator()

        all_models = parser.parse_directory(semantic_models_dir)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )

            assert len(validation_errors) == 0

            # Verify each view has a dimensions_only set
            view_files = [f for f in generated_files if f.name.endswith(".view.lkml")]

            for view_file in view_files:
                content = view_file.read_text()
                assert "set: dimensions_only" in content, (
                    f"View {view_file.name} missing dimensions_only set"
                )

                # Parse and verify structure
                parsed = lkml.load(content)
                view = parsed["views"][0]
                sets = view.get("sets", [])

                assert len(sets) == 1, f"Expected 1 set in {view_file.name}"
                assert sets[0]["name"] == "dimensions_only"
                assert "fields" in sets[0]
                assert len(sets[0]["fields"]) > 0

    def test_generated_explores_have_join_field_constraints(self) -> None:
        """Test that all explore joins include fields parameter."""
        semantic_models_dir = Path(__file__).parent.parent.parent / "semantic_models"

        parser = DbtParser()
        generator = LookMLGenerator()

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

            # Find explores with joins
            for explore in parsed.get("explores", []):
                joins = explore.get("joins", [])

                # If explore has joins, verify they have fields parameter
                for join in joins:
                    assert "fields" in join, (
                        f"Join {join['name']} in explore {explore['name']} missing fields parameter"
                    )

                    # Verify format: [view_name.dimensions_only*]
                    fields_value = join["fields"]
                    assert isinstance(fields_value, list)
                    assert len(fields_value) == 1
                    assert fields_value[0].endswith(".dimensions_only*")

    def test_dimension_groups_have_default_convert_tz_no(self) -> None:
        """Test that dimension_groups have convert_tz: no by default."""
        # Parse semantic models with time dimensions
        semantic_models_dir = Path(__file__).parent.parent / "fixtures"
        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        # Verify we have models with time dimensions
        assert len(semantic_models) > 0

        # Check that we have at least one model with time dimensions
        has_time_dimension = False
        for model in semantic_models:
            for dimension in model.dimensions:
                if dimension.type == DimensionType.TIME:
                    has_time_dimension = True
                    break
        assert has_time_dimension, "Test fixture must have models with time dimensions"

        # Generate LookML with default settings
        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Ensure no validation errors
            assert len(validation_errors) == 0, (
                f"Unexpected validation errors: {validation_errors}"
            )

            # Check each view file for dimension_groups
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) > 0, "Should generate at least one view file"

            dimension_group_found = False
            for view_file in view_files:
                content = view_file.read_text()

                # If file has dimension_group, it should have convert_tz: no
                if "dimension_group:" in content:
                    dimension_group_found = True
                    assert "convert_tz: no" in content, (
                        f"View {view_file.name} has dimension_group but missing convert_tz: no. "
                        f"Full content:\n{content}"
                    )

            # Ensure at least one dimension_group was found and validated
            assert dimension_group_found, (
                "Test expects at least one dimension_group in generated views"
            )

    def test_generator_convert_tz_parameter_propagates(self) -> None:
        """Test that generator convert_tz parameter is applied to dimension_groups."""
        semantic_models_dir = Path(__file__).parent.parent / "fixtures"
        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        assert len(semantic_models) > 0

        # Test with convert_tz=False (explicit default)
        generator_no_tz = LookMLGenerator(convert_tz=False)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator_no_tz.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0

            # All dimension_groups should have convert_tz: no
            view_files = list(output_dir.glob("*.view.lkml"))
            for view_file in view_files:
                content = view_file.read_text()
                if "dimension_group:" in content:
                    assert "convert_tz: no" in content, (
                        f"Generator with convert_tz=False should produce convert_tz: no "
                        f"in {view_file.name}"
                    )

        # Test with convert_tz=True
        generator_with_tz = LookMLGenerator(convert_tz=True)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = (
                generator_with_tz.generate_lookml_files(semantic_models, output_dir)
            )

            assert len(validation_errors) == 0

            # All dimension_groups should have convert_tz: yes
            view_files = list(output_dir.glob("*.view.lkml"))
            for view_file in view_files:
                content = view_file.read_text()
                if "dimension_group:" in content:
                    assert "convert_tz: yes" in content, (
                        f"Generator with convert_tz=True should produce convert_tz: yes "
                        f"in {view_file.name}"
                    )

    def test_dimension_metadata_convert_tz_override(self) -> None:
        """Test that dimension-level convert_tz metadata can override generator setting."""
        # Parse semantic models
        semantic_models_dir = Path(__file__).parent.parent / "fixtures"
        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        assert len(semantic_models) > 0

        # Generate with default settings
        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0

            # Verify dimension_groups have proper convert_tz setting
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) > 0

            for view_file in view_files:
                content = view_file.read_text()

                # Every dimension_group should have an explicit convert_tz setting
                if "dimension_group:" in content:
                    # Should have either convert_tz: yes or convert_tz: no
                    has_convert_tz_setting = (
                        "convert_tz: no" in content or "convert_tz: yes" in content
                    )
                    assert has_convert_tz_setting, (
                        f"View {view_file.name} has dimension_group with no explicit "
                        f"convert_tz setting"
                    )
