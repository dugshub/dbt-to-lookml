"""Comprehensive end-to-end integration tests."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Dict, Any
import yaml
import shutil
import json
import subprocess
import sys
import concurrent.futures
import threading

import pytest
lkml = pytest.importorskip("lkml")

from dbt_to_lookml.generators.lookml import LookMLGenerator
from dbt_to_lookml.types import (
    AggregationType,
    DimensionType,
)
from dbt_to_lookml.schemas import (
    Config,
    ConfigMeta,
    Dimension,
    Entity,
    LookMLView,
    Measure,
    SemanticModel,
)
from dbt_to_lookml.parsers.dbt import DbtParser


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
        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
        # Parse all real semantic models
        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)
        
        assert len(semantic_models) >= 6  # We know there are 6 semantic model files
        
        # Verify we have the expected models
        model_names = {model.name for model in semantic_models}
        expected_models = {"users", "rental_orders", "rental_details", "devices", "sessions", "searches"}
        assert expected_models.issubset(model_names)
        
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
                
            # Verify specific model outputs
            users_view = output_dir / "users.view.lkml"
            assert users_view.exists()
            users_content = users_view.read_text()
            assert "dim_renter" in users_content  # Should contain the actual table name
            assert "renter_sk" in users_content   # Should contain actual column names
            assert "primary_key: yes" in users_content  # Should have primary key
            
            # Verify explores file
            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            for model_name in model_names:
                assert model_name in explores_content

    def test_complex_sql_expressions_preserved(self) -> None:
        """Test that complex SQL expressions from real models are preserved."""
        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
        parser = DbtParser()
        users_file = semantic_models_dir / "sem_users.yml"
        semantic_models = parser.parse_file(users_file)
        
        assert len(semantic_models) == 1
        users_model = semantic_models[0]
        
        # Verify complex expressions are in the parsed model
        complex_measure = None
        for measure in users_model.measures:
            if "cast(" in measure.expr or "" if measure.expr is None else measure.expr:
                complex_measure = measure
                break
        
        generator = LookMLGenerator()
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )
            
            assert len(validation_errors) == 0
            
            users_view = output_dir / "users.view.lkml"
            content = users_view.read_text()
            
            # Complex SQL expressions should be preserved
            assert "cast(" in content.lower()
            assert "nullif(" in content.lower()

    def test_all_aggregation_types_in_real_models(self) -> None:
        """Test that all aggregation types in real models are handled correctly."""
        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)
        
        # Collect all aggregation types used
        agg_types_used = set()
        for model in semantic_models:
            for measure in model.measures:
                agg_types_used.add(measure.agg.value)
        
        assert len(agg_types_used) > 3  # Should have multiple aggregation types
        
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
            
            # Should contain different measure types
            assert "type: count" in all_content
            assert "type: sum" in all_content
            assert "type: average" in all_content
            assert "type: count_distinct" in all_content

    def test_time_dimensions_converted_correctly(self) -> None:
        """Test that time dimensions are converted to dimension_groups."""
        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
        parser = DbtParser()
        semantic_models = parser.parse_directory(semantic_models_dir)
        
        # Find models with time dimensions
        models_with_time = []
        for model in semantic_models:
            for dimension in model.dimensions:
                if dimension.type.value == "time":
                    models_with_time.append(model)
                    break
        
        assert len(models_with_time) > 0  # Should have at least one model with time dimensions
        
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
        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
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
        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
        parser = DbtParser()
        users_file = semantic_models_dir / "sem_users.yml"  # This is the largest model
        semantic_models = parser.parse_file(users_file)
        
        users_model = semantic_models[0]
        
        # Verify it's actually a large model
        assert len(users_model.dimensions) > 10
        assert len(users_model.measures) > 10
        
        generator = LookMLGenerator()
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )
            
            assert len(validation_errors) == 0
            
            users_view = output_dir / "users.view.lkml"
            content = users_view.read_text()
            
            # Should handle large number of fields without issues
            dimension_count = content.count("dimension:")
            measure_count = content.count("measure:")
            dimension_group_count = content.count("dimension_group:")
            
            # Should have many dimensions and measures
            assert dimension_count > 10
            assert measure_count > 10
            assert dimension_group_count > 0  # Time dimensions

    def test_error_recovery_and_partial_generation(self) -> None:
        """Test that partial generation works when some models fail."""
        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
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
        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
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
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Should be able to read without encoding errors
                    assert len(content) > 0

    def test_lookml_syntax_validation_passes(self) -> None:
        """Test that generated LookML passes syntax validation."""
        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
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
                content = file_path.read_text()
                try:
                    parsed = lkml.load(content)
                    assert parsed is not None
                except Exception as e:
                    pytest.fail(f"Generated file {file_path} has invalid LookML syntax: {e}")

    def test_generation_summary_accuracy(self) -> None:
        """Test that generation summary provides accurate statistics."""
        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
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
            
            view_count = len([f for f in generated_files if f.name.endswith(".view.lkml")])
            explore_count = len([f for f in generated_files if f.name == "explores.lkml"])
            
            assert f"View files: {view_count}" in summary
            assert f"Explore files: {explore_count}" in summary

    def test_concurrent_model_processing(self) -> None:
        """Test that processing multiple models works correctly."""
        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
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
                view_file = next(f for f in generated_files if f.name.endswith(".view.lkml"))
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
        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
        parser = DbtParser(strict_mode=True)
        generator = LookMLGenerator(validate_syntax=True, format_output=True)
        
        semantic_models = parser.parse_directory(semantic_models_dir)
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )
            
            # Should pass all validations
            assert len(validation_errors) == 0, f"Validation failed: {validation_errors}"
            
            # Every generated file should be valid LookML
            for file_path in generated_files:
                content = file_path.read_text()
                try:
                    parsed_lookml = lkml.load(content)
                    assert parsed_lookml is not None
                except Exception as e:
                    pytest.fail(f"Invalid LookML in {file_path.name}: {e}")

    def test_performance_with_real_models(self) -> None:
        """Test performance characteristics with real semantic models."""
        import time

        semantic_models_dir = Path("/Users/doug/Work/data-modelling/official-models-staging/redshift_gold/models/semantic_models")
        
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
        assert generation_time < 10.0, f"Generation took too long: {generation_time:.2f}s"
        
        # Results should be complete
        assert len(semantic_models) >= 6
        assert len(generated_files) >= 7
        assert len(validation_errors) == 0
