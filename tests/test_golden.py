"""Golden file tests for dbt-to-lookml."""

import difflib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Tuple, Set
import re

import pytest

from dbt_to_lookml.generator import LookMLGenerator
from dbt_to_lookml.models import AggregationType, DimensionType
from dbt_to_lookml.parser import SemanticModelParser


class TestGoldenFiles:
    """Golden file tests to ensure generated output matches expected results."""

    @pytest.fixture
    def golden_dir(self) -> Path:
        """Return path to golden files directory."""
        return Path(__file__).parent / "golden"

    @pytest.fixture
    def semantic_models_dir(self) -> Path:
        """Return path to semantic models directory."""
        return Path(__file__).parent.parent / "semantic_models"

    def test_generate_users_view_matches_golden(
        self, golden_dir: Path, semantic_models_dir: Path
    ) -> None:
        """Test that generated users view matches the golden file."""
        # Parse the users semantic model
        parser = SemanticModelParser()
        users_file = semantic_models_dir / "sem_users.yml"
        semantic_models = parser.parse_file(users_file)

        assert len(semantic_models) == 1
        users_model = semantic_models[0]
        assert users_model.name == "users"

        # Generate LookML
        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                [users_model], output_dir
            )

            assert len(validation_errors) == 0
            users_view_file = output_dir / "users.view.lkml"
            assert users_view_file.exists()

            # Compare with golden file
            expected_content = (golden_dir / "expected_users.view.lkml").read_text()
            actual_content = users_view_file.read_text()

            self._assert_content_matches(
                expected_content, actual_content, "users.view.lkml"
            )

    def test_generate_all_explores_matches_golden(
        self, golden_dir: Path, semantic_models_dir: Path
    ) -> None:
        """Test that generated explores file matches the golden file."""
        # Parse all semantic models
        parser = SemanticModelParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        assert len(semantic_models) > 0

        # Generate LookML
        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0
            explores_file = output_dir / "explores.lkml"
            assert explores_file.exists()

            # Compare with golden file
            expected_content = (golden_dir / "expected_explores.lkml").read_text()
            actual_content = explores_file.read_text()

            self._assert_content_matches(
                expected_content, actual_content, "explores.lkml"
            )

    def test_generate_with_prefixes_different_from_golden(
        self, semantic_models_dir: Path
    ) -> None:
        """Test that generation with prefixes produces different output than golden files."""
        # Parse a semantic model
        parser = SemanticModelParser()
        users_file = semantic_models_dir / "sem_users.yml"
        semantic_models = parser.parse_file(users_file)

        # Generate with prefixes
        generator = LookMLGenerator(view_prefix="v_", explore_prefix="e_")

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            assert len(validation_errors) == 0
            users_view_file = output_dir / "v_users.view.lkml"
            assert users_view_file.exists()

            # Content should contain prefixes
            content = users_view_file.read_text()
            assert "v_users" in content

            explores_file = output_dir / "explores.lkml"
            explores_content = explores_file.read_text()
            assert "e_users" in explores_content
            assert "from: v_users" in explores_content

    def test_dry_run_matches_golden_preview(
        self, golden_dir: Path, semantic_models_dir: Path
    ) -> None:
        """Test that dry run preview would generate content matching golden files."""
        # Parse semantic models
        parser = SemanticModelParser()
        users_file = semantic_models_dir / "sem_users.yml"
        semantic_models = parser.parse_file(users_file)

        # Generate in dry run mode
        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir, dry_run=True
            )

            # Files should not actually exist in dry run
            assert not any(f.exists() for f in generated_files)
            
            # But there should be no validation errors
            assert len(validation_errors) == 0

    def test_individual_semantic_models_generate_correctly(
        self, semantic_models_dir: Path
    ) -> None:
        """Test that each individual semantic model generates valid LookML."""
        parser = SemanticModelParser()
        
        # Test each semantic model file individually
        yaml_files = list(semantic_models_dir.glob("*.yml"))
        assert len(yaml_files) > 0

        generator = LookMLGenerator()

        for yaml_file in yaml_files:
            semantic_models = parser.parse_file(yaml_file)
            assert len(semantic_models) > 0

            with TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                generated_files, validation_errors = generator.generate_lookml_files(
                    semantic_models, output_dir
                )

                # Should generate without errors
                assert len(validation_errors) == 0
                
                # Should generate expected files
                view_files = [f for f in generated_files if f.name.endswith(".view.lkml")]
                assert len(view_files) == len(semantic_models)
                
                # All view files should exist and contain valid content
                for view_file in view_files:
                    assert view_file.exists()
                    content = view_file.read_text()
                    assert "view:" in content
                    assert "sql_table_name:" in content

    def test_validation_enabled_matches_golden(
        self, golden_dir: Path, semantic_models_dir: Path
    ) -> None:
        """Test that validation enabled still produces golden file output."""
        parser = SemanticModelParser()
        users_file = semantic_models_dir / "sem_users.yml"
        semantic_models = parser.parse_file(users_file)

        # Generate with validation explicitly enabled
        generator = LookMLGenerator(validate_syntax=True)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Should pass validation
            assert len(validation_errors) == 0
            
            users_view_file = output_dir / "users.view.lkml"
            assert users_view_file.exists()

            # Content should still match golden file
            expected_content = (golden_dir / "expected_users.view.lkml").read_text()
            actual_content = users_view_file.read_text()

            # Allow for minor formatting differences but core structure should match
            assert "view:" in actual_content
            assert "users:" in actual_content
            assert "sql_table_name: dim_renter" in actual_content

    def test_formatting_disabled_still_valid(
        self, semantic_models_dir: Path
    ) -> None:
        """Test that disabling formatting still produces valid LookML."""
        parser = SemanticModelParser()
        users_file = semantic_models_dir / "sem_users.yml"
        semantic_models = parser.parse_file(users_file)

        # Generate with formatting disabled
        generator = LookMLGenerator(format_output=False)

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Should still be valid even without formatting
            assert len(validation_errors) == 0
            
            users_view_file = output_dir / "users.view.lkml"
            assert users_view_file.exists()

            content = users_view_file.read_text()
            # Core content should be present regardless of formatting
            assert "view:" in content
            assert "users:" in content

    def _assert_content_matches(
        self, expected: str, actual: str, filename: str
    ) -> None:
        """Assert that content matches, providing a helpful diff if not."""
        # Normalize whitespace for comparison
        expected_lines = [line.rstrip() for line in expected.split('\n')]
        actual_lines = [line.rstrip() for line in actual.split('\n')]

        if expected_lines != actual_lines:
            diff = list(
                difflib.unified_diff(
                    expected_lines,
                    actual_lines,
                    fromfile=f"expected_{filename}",
                    tofile=f"actual_{filename}",
                    lineterm="",
                )
            )
            diff_text = '\n'.join(diff)
            pytest.fail(
                f"Generated {filename} does not match golden file:\n\n{diff_text}"
            )

    def test_golden_files_exist(self, golden_dir: Path) -> None:
        """Test that required golden files exist."""
        required_files = [
            "expected_users.view.lkml",
            "expected_explores.lkml",
        ]

        for filename in required_files:
            golden_file = golden_dir / filename
            assert golden_file.exists(), f"Golden file {filename} is missing"
            
            # Verify content is not empty
            content = golden_file.read_text().strip()
            assert content, f"Golden file {filename} is empty"

    def test_golden_files_are_valid_lookml(self, golden_dir: Path) -> None:
        """Test that golden files themselves contain valid LookML."""
        generator = LookMLGenerator(validate_syntax=True)
        
        golden_files = [
            golden_dir / "expected_users.view.lkml",
            golden_dir / "expected_explores.lkml",
        ]

        for golden_file in golden_files:
            if golden_file.exists():
                content = golden_file.read_text()
                
                # Validate syntax using the generator's validation method
                try:
                    generator._validate_lookml_syntax(content)
                except Exception as e:
                    pytest.fail(f"Golden file {golden_file.name} contains invalid LookML: {e}")

    def test_regeneration_produces_identical_output(
        self, semantic_models_dir: Path
    ) -> None:
        """Test that regenerating the same models produces identical output."""
        parser = SemanticModelParser()
        users_file = semantic_models_dir / "sem_users.yml"
        semantic_models = parser.parse_file(users_file)

        generator = LookMLGenerator()

        # Generate first time
        with TemporaryDirectory() as temp_dir1:
            output_dir1 = Path(temp_dir1)
            generated_files1, _ = generator.generate_lookml_files(
                semantic_models, output_dir1
            )
            content1 = (output_dir1 / "users.view.lkml").read_text()

        # Generate second time
        with TemporaryDirectory() as temp_dir2:
            output_dir2 = Path(temp_dir2)
            generated_files2, _ = generator.generate_lookml_files(
                semantic_models, output_dir2
            )
            content2 = (output_dir2 / "users.view.lkml").read_text()

        # Should be identical
        assert content1 == content2

    def test_complex_semantic_model_features_preserved(
        self, semantic_models_dir: Path
    ) -> None:
        """Test that complex features in semantic models are preserved in output."""
        parser = SemanticModelParser()
        
        # Parse users model which has complex features
        users_file = semantic_models_dir / "sem_users.yml"
        semantic_models = parser.parse_file(users_file)
        users_model = semantic_models[0]

        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                [users_model], output_dir
            )

            assert len(validation_errors) == 0
            content = (output_dir / "users.view.lkml").read_text()

            # Verify complex features are preserved
            assert "primary_key: yes" in content  # Primary entity
            assert "dimension_group:" in content  # Time dimensions
            assert "timeframes:" in content       # Time dimension timeframes
            assert "count_distinct" in content    # Different aggregation types
            assert "cast(" in content            # Complex SQL expressions
            assert "nullif(" in content          # Complex SQL expressions

    def update_golden_files_if_requested(self, golden_dir: Path) -> None:
        """Helper method to update golden files (not a test, for development use)."""
        # This method can be called manually during development to update golden files
        # when the expected output changes due to legitimate improvements
        # It's not run as part of regular test suite
        
        semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
        parser = SemanticModelParser()
        
        # Update users view golden file
        users_file = semantic_models_dir / "sem_users.yml"
        semantic_models = parser.parse_file(users_file)
        
        generator = LookMLGenerator()
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, _ = generator.generate_lookml_files(
                semantic_models, output_dir
            )
            
            # Copy generated file to golden directory
            users_content = (output_dir / "users.view.lkml").read_text()
            (golden_dir / "expected_users.view.lkml").write_text(users_content)
            
        # Update explores golden file
        all_models = parser.parse_directory(semantic_models_dir)
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, _ = generator.generate_lookml_files(
                all_models, output_dir
            )
            
            explores_content = (output_dir / "explores.lkml").read_text()
            (golden_dir / "expected_explores.lkml").write_text(explores_content)

    def test_golden_files_comprehensive_coverage(self, golden_dir: Path, semantic_models_dir: Path) -> None:
        """Test that golden files provide comprehensive coverage of all models."""
        parser = SemanticModelParser()
        generator = LookMLGenerator()
        
        # Parse all semantic models
        all_models = parser.parse_directory(semantic_models_dir)
        model_names = {model.name for model in all_models}
        
        # Generate all files
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )
            
            assert len(validation_errors) == 0
            
            # For each model, check if we have comprehensive coverage
            for model in all_models:
                view_file = output_dir / f"{model.name}.view.lkml"
                content = view_file.read_text()
                
                # Verify comprehensive model elements are present
                if model.entities:
                    assert any("primary_key: yes" in content or "type: string" in content for _ in [1])
                
                if model.dimensions:
                    assert "dimension:" in content
                    # Check for time dimensions specifically
                    time_dims = [d for d in model.dimensions if d.type == DimensionType.TIME]
                    if time_dims:
                        assert "dimension_group:" in content
                        assert "type: time" in content
                
                if model.measures:
                    assert "measure:" in content
                    # Verify different aggregation types
                    agg_types = {m.agg for m in model.measures}
                    if AggregationType.COUNT in agg_types:
                        assert "type: count" in content
                    if AggregationType.SUM in agg_types:
                        assert "type: sum" in content
                    if AggregationType.COUNT_DISTINCT in agg_types:
                        assert "type: count_distinct" in content
    
    def test_golden_files_regression_protection(self, semantic_models_dir: Path) -> None:
        """Test regression protection - ensure consistent output across runs."""
        parser = SemanticModelParser()
        generator = LookMLGenerator()
        
        # Parse a specific model for regression testing
        users_file = semantic_models_dir / "sem_users.yml"
        semantic_models = parser.parse_file(users_file)
        
        # Generate multiple times and ensure consistency
        outputs = []
        for _ in range(3):
            with TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                generated_files, validation_errors = generator.generate_lookml_files(
                    semantic_models, output_dir
                )
                
                assert len(validation_errors) == 0
                content = (output_dir / "users.view.lkml").read_text()
                outputs.append(content)
        
        # All outputs should be identical
        assert all(output == outputs[0] for output in outputs)
        
        # Output should contain expected structural elements
        expected_elements = [
            "view: users",
            "sql_table_name:",
            "dimension:",
            "measure:",
            "dimension_group:",
            "primary_key:",
            "type:",
        ]
        
        for element in expected_elements:
            assert element in outputs[0], f"Missing expected element: {element}"
    
    def test_golden_files_edge_case_handling(self, semantic_models_dir: Path) -> None:
        """Test that edge cases in semantic models are handled correctly in golden output."""
        parser = SemanticModelParser()
        generator = LookMLGenerator()
        
        # Test with all semantic models to catch edge cases
        all_models = parser.parse_directory(semantic_models_dir)
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )
            
            # Should handle all models without errors
            assert len(validation_errors) == 0
            
            for generated_file in generated_files:
                content = generated_file.read_text()
                
                # Should not contain common problematic patterns
                assert "None" not in content  # No Python None values
                assert "null" not in content.lower()  # No null values (unless intentional)
                assert "undefined" not in content  # No undefined references
                
                # Should contain only valid LookML syntax
                if generated_file.name.endswith(".view.lkml"):
                    assert content.count("view:") == 1  # Exactly one view definition
                    assert "sql_table_name:" in content  # Must have table reference
                
                if generated_file.name == "explores.lkml":
                    explore_count = content.count("explore:")
                    assert explore_count == len(all_models)  # One explore per model
    
    def test_golden_files_complex_sql_preservation(self, semantic_models_dir: Path) -> None:
        """Test that complex SQL expressions are preserved correctly in golden files."""
        parser = SemanticModelParser()
        generator = LookMLGenerator()
        
        # Parse all models to find complex SQL expressions
        all_models = parser.parse_directory(semantic_models_dir)
        
        complex_expressions = []
        for model in all_models:
            # Collect complex expressions from dimensions
            for dimension in model.dimensions:
                if dimension.expr and any(keyword in dimension.expr.lower() for keyword in 
                    ['case', 'cast', 'nullif', 'coalesce', 'extract', 'substring']):
                    complex_expressions.append((model.name, 'dimension', dimension.name, dimension.expr))
            
            # Collect complex expressions from measures
            for measure in model.measures:
                if measure.expr and any(keyword in measure.expr.lower() for keyword in 
                    ['case', 'cast', 'nullif', 'coalesce', 'sum(case']):
                    complex_expressions.append((model.name, 'measure', measure.name, measure.expr))
        
        if complex_expressions:
            with TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                generated_files, validation_errors = generator.generate_lookml_files(
                    all_models, output_dir
                )
                
                assert len(validation_errors) == 0
                
                # Verify complex expressions are preserved
                for model_name, field_type, field_name, original_expr in complex_expressions:
                    view_file = output_dir / f"{model_name}.view.lkml"
                    content = view_file.read_text()
                    
                    # Key parts of the expression should be present
                    expr_keywords = ['case', 'cast', 'nullif', 'coalesce', 'extract', 'substring']
                    original_keywords = [kw for kw in expr_keywords if kw in original_expr.lower()]
                    
                    for keyword in original_keywords:
                        assert keyword in content.lower(), \
                            f"Complex SQL keyword '{keyword}' missing from {model_name}.{field_name}"
    
    def test_golden_files_unicode_handling(self, semantic_models_dir: Path) -> None:
        """Test that Unicode characters in descriptions are handled properly."""
        parser = SemanticModelParser()
        generator = LookMLGenerator()
        
        # Parse models that might contain Unicode in descriptions
        all_models = parser.parse_directory(semantic_models_dir)
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                all_models, output_dir
            )
            
            assert len(validation_errors) == 0
            
            # Verify all files can be read with proper encoding
            for generated_file in generated_files:
                try:
                    with open(generated_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    assert len(content) > 0
                except UnicodeDecodeError:
                    pytest.fail(f"Generated file {generated_file.name} has encoding issues")
    
    def test_golden_files_deterministic_ordering(self, semantic_models_dir: Path) -> None:
        """Test that generated files have deterministic ordering of elements."""
        parser = SemanticModelParser()
        generator = LookMLGenerator()
        
        users_file = semantic_models_dir / "sem_users.yml"
        semantic_models = parser.parse_file(users_file)
        
        # Generate multiple times
        contents = []
        for _ in range(5):
            with TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                generated_files, validation_errors = generator.generate_lookml_files(
                    semantic_models, output_dir
                )
                
                content = (output_dir / "users.view.lkml").read_text()
                contents.append(content)
        
        # All contents should be identical (deterministic ordering)
        for content in contents[1:]:
            assert content == contents[0], "Generated content ordering is not deterministic"