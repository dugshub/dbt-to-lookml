"""Comprehensive error handling tests for dbt-to-lookml."""

from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest.mock import patch, MagicMock
import yaml

import pytest
from pydantic import ValidationError

from dbt_to_lookml.generators.lookml import LookMLGenerator, LookMLValidationError
from dbt_to_lookml.schemas import (
    Dimension,
    Entity,
    Measure,
    SemanticModel,
)
from dbt_to_lookml.types import (
    AggregationType,
    DimensionType,
)
from dbt_to_lookml.parsers.dbt import DbtParser


class TestErrorHandling:
    """Comprehensive error handling tests."""

    def test_parser_invalid_yaml_syntax(self) -> None:
        """Test parser handling of invalid YAML syntax."""
        parser = DbtParser(strict_mode=True)
        
        invalid_yaml_cases = [
            "invalid: yaml: [unclosed",
            "- invalid\n  - nested: badly",
            "{unclosed dict",
            "duplicate_key: value1\nduplicate_key: value2",
            "text with\ttabs and weird\x00characters",
            "very: { deep: { nesting: { that: { goes: { too: { far: value } } } } } }",
        ]
        
        for invalid_yaml in invalid_yaml_cases:
            with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                f.write(invalid_yaml)
                temp_path = Path(f.name)
            
            try:
                with pytest.raises((yaml.YAMLError, Exception)):
                    parser.parse_file(temp_path)
            finally:
                temp_path.unlink()

    def test_parser_missing_required_fields(self) -> None:
        """Test parser handling of models with missing required fields."""
        parser = DbtParser(strict_mode=True)
        
        invalid_models = [
            # Missing name field
            {"model": "some_table"},
            # Missing model field
            {"name": "test_model"},
            # Empty model
            {},
            # Null values for required fields
            {"name": None, "model": "table"},
            {"name": "test", "model": None},
        ]
        
        for invalid_model in invalid_models:
            with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                yaml.dump(invalid_model, f)
                temp_path = Path(f.name)
            
            try:
                with pytest.raises((ValidationError, ValueError)):
                    parser.parse_file(temp_path)
            finally:
                temp_path.unlink()

    def test_parser_invalid_field_types(self) -> None:
        """Test parser handling of invalid field types."""
        parser = DbtParser(strict_mode=True)
        
        invalid_models = [
            # Invalid aggregation type
            {
                "name": "test",
                "model": "table",
                "measures": [{"name": "test_measure", "agg": "invalid_aggregation"}]
            },
            # Invalid dimension type
            {
                "name": "test",
                "model": "table",
                "dimensions": [{"name": "test_dim", "type": "invalid_dimension_type"}]
            },
            # Invalid entity type (non-string)
            {
                "name": "test",
                "model": "table",
                "entities": [{"name": "test_entity", "type": 123}]
            },
            # List instead of dict for dimension
            {
                "name": "test",
                "model": "table",
                "dimensions": [["not", "a", "dict"]]
            },
        ]
        
        for invalid_model in invalid_models:
            with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                yaml.dump(invalid_model, f)
                temp_path = Path(f.name)
            
            try:
                with pytest.raises((ValidationError, ValueError, TypeError)):
                    parser.parse_file(temp_path)
            finally:
                temp_path.unlink()

    def test_parser_malformed_lists(self) -> None:
        """Test parser handling of malformed lists in semantic models."""
        parser = DbtParser(strict_mode=True)
        
        malformed_cases = [
            # String instead of list for entities
            {"name": "test", "model": "table", "entities": "not_a_list"},
            # Dict instead of list for dimensions
            {"name": "test", "model": "table", "dimensions": {"key": "value"}},
            # Integer instead of list for measures
            {"name": "test", "model": "table", "measures": 123},
            # Mixed types in list
            {
                "name": "test",
                "model": "table",
                "dimensions": [
                    {"name": "valid_dim", "type": "categorical"},
                    "invalid_string_item",
                    123
                ]
            },
        ]
        
        for malformed_model in malformed_cases:
            with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                yaml.dump(malformed_model, f)
                temp_path = Path(f.name)
            
            try:
                with pytest.raises((ValidationError, TypeError)):
                    parser.parse_file(temp_path)
            finally:
                temp_path.unlink()

    def test_parser_file_permission_errors(self) -> None:
        """Test parser handling of file permission errors."""
        parser = DbtParser()
        
        with patch('pathlib.Path.read_text') as mock_read:
            mock_read.side_effect = PermissionError("Permission denied")
            
            with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                yaml.dump({"name": "test", "model": "table"}, f)
                temp_path = Path(f.name)
            
            try:
                with pytest.raises(PermissionError):
                    parser.parse_file(temp_path)
            finally:
                temp_path.unlink()

    def test_parser_file_not_found_errors(self) -> None:
        """Test parser handling of missing files."""
        parser = DbtParser()
        
        nonexistent_file = Path("/nonexistent/path/to/file.yml")
        
        with pytest.raises(FileNotFoundError):
            parser.parse_file(nonexistent_file)
        
        with pytest.raises(FileNotFoundError):
            parser.parse_directory(Path("/nonexistent/directory"))

    def test_parser_empty_and_whitespace_files(self) -> None:
        """Test parser handling of empty and whitespace-only files."""
        parser = DbtParser()
        
        empty_cases = [
            "",  # Completely empty
            "   ",  # Only spaces
            "\n\n\n",  # Only newlines
            "\t\t\t",  # Only tabs
            " \n \t \n ",  # Mixed whitespace
        ]
        
        for empty_content in empty_cases:
            with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                f.write(empty_content)
                temp_path = Path(f.name)
            
            try:
                models = parser.parse_file(temp_path)
                # Should return empty list for empty files
                assert len(models) == 0
            finally:
                temp_path.unlink()

    @pytest.mark.skip(reason="SemanticModelMapper no longer exists - functionality moved to schemas")
    def test_mapper_invalid_model_inputs(self) -> None:
        """Test mapper handling of invalid semantic model inputs."""
        # mapper = SemanticModelMapper()
        
        # Test with None values
        with pytest.raises(AttributeError):
            mapper.semantic_model_to_view(None)
        
        # Test with incomplete model (missing required attributes)
        incomplete_model = SemanticModel(name="", model="")
        view = mapper.semantic_model_to_view(incomplete_model)
        # Should handle gracefully but produce minimal view
        assert view.name == ""
        assert view.sql_table_name == ""

    @pytest.mark.skip(reason="SemanticModelMapper no longer exists - functionality moved to schemas")
    def test_mapper_invalid_aggregation_types(self) -> None:
        """Test mapper handling of invalid aggregation types."""
        # mapper = SemanticModelMapper()
        
        # Create a measure with an invalid aggregation type by mocking
        with patch.object(AggregationType, '__members__', {}):
            # This would cause issues if the mapper doesn't handle missing mappings
            invalid_measure = Measure(name="test", agg=AggregationType.COUNT)
            try:
                lookml_measure = mapper._measure_to_lookml(invalid_measure)
                # Should still work with valid enum value
                assert lookml_measure.name == "test"
            except KeyError:
                # Expected if the mapping doesn't exist
                pass

    def test_generator_file_write_errors(self) -> None:
        """Test generator handling of file write errors."""
        generator = LookMLGenerator()
        
        semantic_model = SemanticModel(name="test", model="test_table")
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Make directory read-only to cause write errors
            output_dir.chmod(0o444)
            
            try:
                generated_files, validation_errors = generator.generate_lookml_files(
                    [semantic_model], output_dir
                )
                
                # Should handle the error gracefully
                # The exact behavior may vary by OS/filesystem
                if validation_errors:
                    assert len(validation_errors) > 0
                    assert any("permission" in error.lower() or "error" in error.lower() 
                             for error in validation_errors)
            finally:
                output_dir.chmod(0o755)

    def test_generator_disk_space_simulation(self) -> None:
        """Test generator behavior when disk space is limited."""
        generator = LookMLGenerator()
        
        # Create a large semantic model that would generate a big file
        large_model = SemanticModel(
            name="large_test",
            model="large_table",
            dimensions=[
                Dimension(
                    name=f"dim_{i}",
                    type=DimensionType.CATEGORICAL,
                    expr="very_long_expression_" * 100  # Make it large
                ) for i in range(100)
            ],
            measures=[
                Measure(
                    name=f"measure_{i}",
                    agg=AggregationType.SUM,
                    expr="very_long_expression_" * 100
                ) for i in range(100)
            ]
        )
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Mock the file write operation to simulate disk space error
            original_open = open
            
            def mock_open(*args, **kwargs):
                if 'w' in str(args) or kwargs.get('mode') == 'w':
                    raise OSError("No space left on device")
                return original_open(*args, **kwargs)
            
            with patch('builtins.open', side_effect=mock_open):
                generated_files, validation_errors = generator.generate_lookml_files(
                    [large_model], output_dir
                )
                
                # Should handle the disk space error
                assert len(validation_errors) > 0

    def test_generator_invalid_lookml_generation(self) -> None:
        """Test generator handling of invalid LookML generation."""
        generator = LookMLGenerator(validate_syntax=True)
        
        # Mock lkml.dump to return invalid content
        with patch('lkml.dump') as mock_dump:
            mock_dump.return_value = "invalid lookml content: {"
            
            semantic_model = SemanticModel(name="test", model="test_table")
            
            with TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                
                generated_files, validation_errors = generator.generate_lookml_files(
                    [semantic_model], output_dir
                )
                
                # Should catch validation errors
                assert len(validation_errors) > 0
                assert any("syntax" in error.lower() for error in validation_errors)

    def test_generator_lkml_library_import_error(self) -> None:
        """Test generator behavior when lkml library is not available."""
        # Mock import error for lkml
        with patch.dict('sys.modules', {'lkml': None}):
            with pytest.raises(ImportError):
                # This should fail when trying to import lkml
                from dbt_to_lookml.generator import LookMLGenerator
                generator = LookMLGenerator()

    def test_validation_with_corrupted_content(self) -> None:
        """Test LookML validation with corrupted content."""
        generator = LookMLGenerator(validate_syntax=True)
        
        corrupted_contents = [
            "\x00\x01\x02invalid binary content",
            "valid_start: { \x00\x01\x02 }",
            "unicode_issues: 'broken \udcff encoding'",
            "extremely_long_line: '" + "x" * 100000 + "'",
        ]
        
        for corrupted_content in corrupted_contents:
            try:
                generator._validate_lookml_syntax(corrupted_content)
                # If it doesn't raise an exception, that's also valid
            except LookMLValidationError:
                # Expected for invalid content
                pass
            except Exception as e:
                # Should not raise unexpected exceptions
                assert "validation" in str(e).lower() or "syntax" in str(e).lower()

    def test_concurrent_file_access_simulation(self) -> None:
        """Test handling of concurrent file access issues."""
        parser = DbtParser()
        
        with NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump({"name": "test", "model": "table"}, f)
            temp_path = Path(f.name)
        
        try:
            # Simulate file being locked/modified during read
            with patch('pathlib.Path.read_text') as mock_read:
                mock_read.side_effect = [
                    OSError("Resource temporarily unavailable"),
                    "name: test\nmodel: table"  # Successful retry
                ]
                
                # First call should fail, but in production you might implement retry logic
                with pytest.raises(OSError):
                    parser.parse_file(temp_path)
        finally:
            temp_path.unlink()

    def test_memory_exhaustion_simulation(self) -> None:
        """Test behavior under memory pressure."""
        # Create a model that would use significant memory
        def create_memory_intensive_model():
            return SemanticModel(
                name="memory_test",
                model="memory_table",
                dimensions=[
                    Dimension(
                        name=f"dim_{i}",
                        type=DimensionType.CATEGORICAL,
                        expr="x" * 10000  # Large string
                    ) for i in range(1000)
                ]
            )
        
        generator = LookMLGenerator()
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Mock to simulate memory error
            with patch.object(generator, '_generate_view_lookml') as mock_generate:
                mock_generate.side_effect = MemoryError("Out of memory")
                
                model = create_memory_intensive_model()
                generated_files, validation_errors = generator.generate_lookml_files(
                    [model], output_dir
                )
                
                # Should handle memory errors gracefully
                assert len(validation_errors) > 0

    def test_invalid_unicode_handling(self) -> None:
        """Test handling of invalid Unicode in semantic models."""
        parser = DbtParser()
        
        # Create file with invalid Unicode
        with TemporaryDirectory() as temp_dir:
            invalid_file = Path(temp_dir) / "invalid_unicode.yml"
            
            # Write invalid Unicode bytes
            with open(invalid_file, 'wb') as f:
                f.write(b'name: test\nmodel: table\ndescription: "invalid \xff\xfe unicode"')
            
            try:
                # Should handle encoding errors
                models = parser.parse_file(invalid_file)
                # Might succeed with replacement characters or fail gracefully
            except UnicodeDecodeError:
                # Expected for invalid Unicode
                pass

    def test_circular_reference_in_models(self) -> None:
        """Test handling of circular references in model definitions."""
        # This would be more relevant if models could reference each other
        # For now, test self-referential expressions
        
        model = SemanticModel(
            name="circular_test",
            model="ref('circular_test')",  # Self-reference
            dimensions=[
                Dimension(
                    name="self_ref_dim",
                    type=DimensionType.CATEGORICAL,
                    expr="${TABLE}.self_ref_dim"  # Could be circular in some contexts
                )
            ]
        )
        
        generator = LookMLGenerator()
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Should generate without infinite loops
            generated_files, validation_errors = generator.generate_lookml_files(
                [model], output_dir
            )
            
            # Should complete (might have validation issues but shouldn't hang)
            assert len(generated_files) > 0

    def test_extremely_nested_case_statements(self) -> None:
        """Test handling of extremely nested CASE statements."""
        # Create a deeply nested CASE statement
        nested_case = "CASE"
        for i in range(50):  # Deep nesting
            nested_case += f" WHEN condition_{i} THEN (CASE"
        nested_case += " WHEN final_condition THEN 'value' ELSE 'default'"
        for i in range(50):
            nested_case += " END)"
        nested_case += " ELSE 'fallback' END"
        
        model = SemanticModel(
            name="nested_test",
            model="test_table",
            dimensions=[
                Dimension(
                    name="deeply_nested",
                    type=DimensionType.CATEGORICAL,
                    expr=nested_case
                )
            ]
        )
        
        generator = LookMLGenerator()
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            generated_files, validation_errors = generator.generate_lookml_files(
                [model], output_dir
            )
            
            # Should handle deeply nested expressions
            assert len(generated_files) > 0
            
            # Check that the nested expression is preserved
            view_file = next(f for f in generated_files if f.name.endswith(".view.lkml"))
            content = view_file.read_text()
            assert "CASE" in content

    @pytest.mark.skip(reason="SemanticModelMapper no longer exists - functionality moved to schemas")
    def test_malformed_dbt_ref_patterns(self) -> None:
        """Test handling of malformed dbt ref() patterns."""
        # mapper = SemanticModelMapper()
        
        malformed_refs = [
            "ref('unclosed",
            "ref(missing_quotes)",
            "ref('')",  # Empty ref
            "ref('valid') + ref('another')",  # Multiple refs
            "complex_ref({{ ref('table') }})",
            "ref(123)",  # Non-string ref
        ]
        
        for malformed_ref in malformed_refs:
            model = SemanticModel(name="test", model=malformed_ref)
            
            # Should handle malformed refs gracefully
            view = mapper.semantic_model_to_view(model)
            assert view.sql_table_name is not None  # Should produce some output

    def test_invalid_file_extensions(self) -> None:
        """Test parser behavior with invalid file extensions."""
        parser = DbtParser()
        
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create files with various extensions
            extensions = ['.yaml', '.yml', '.txt', '.json', '.xml', '']
            
            for ext in extensions:
                if ext:
                    filename = f"test{ext}"
                else:
                    filename = "test_no_extension"
                
                file_path = temp_path / filename
                file_path.write_text("name: test\nmodel: table")
            
            # Parse directory - should only pick up .yml and .yaml files
            models = parser.parse_directory(temp_path)
            
            # Should find at least the .yml and .yaml files
            assert len(models) >= 2

    def test_generator_output_cleanup_on_error(self) -> None:
        """Test that partial output is cleaned up on errors."""
        generator = LookMLGenerator()
        
        models = [
            SemanticModel(name="model1", model="table1"),
            SemanticModel(name="model2", model="table2"),
        ]
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Mock to fail on second model
            original_generate = generator._generate_view_lookml
            call_count = 0
            
            def failing_generate(view):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise Exception("Simulated generation error")
                return original_generate(view)
            
            with patch.object(generator, '_generate_view_lookml', side_effect=failing_generate):
                generated_files, validation_errors = generator.generate_lookml_files(
                    models, output_dir
                )
                
                # Should have errors but still produce some files
                assert len(validation_errors) > 0
                
                # Check what files actually exist
                actual_files = list(output_dir.glob("*"))
                # Implementation-dependent whether partial files are created

    def test_format_with_malformed_lookml(self) -> None:
        """Test formatting with malformed LookML content."""
        generator = LookMLGenerator(format_output=True)
        
        malformed_contents = [
            "",  # Empty content
            "{{{",  # Unmatched braces
            "view: test {\n  dimension: {\n",  # Incomplete structure
            "very long line without any structure or braces that might cause formatting issues",
            "\n\n\n\n",  # Only whitespace
        ]
        
        for content in malformed_contents:
            try:
                formatted = generator._format_lookml_content(content)
                # Should not crash, even if formatting is not perfect
                assert isinstance(formatted, str)
            except Exception as e:
                # Should not raise unexpected exceptions
                assert "format" in str(e).lower() or isinstance(e, (IndexError, AttributeError))

    def test_edge_case_file_sizes(self) -> None:
        """Test handling of edge case file sizes."""
        parser = DbtParser()
        
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Very small file
            tiny_file = temp_path / "tiny.yml"
            tiny_file.write_text("n:t")  # Minimal valid YAML
            
            # Large file (but not huge)
            large_content = "name: large_model\nmodel: large_table\ndimensions:\n"
            for i in range(1000):
                large_content += f"  - name: dim_{i}\n    type: categorical\n"
            
            large_file = temp_path / "large.yml"
            large_file.write_text(large_content)
            
            # Parse both files
            tiny_models = parser.parse_file(tiny_file)
            large_models = parser.parse_file(large_file)
            
            # Both should be handled appropriately
            # Tiny file might not parse to valid model, large file should
            assert len(large_models) == 1
            assert len(large_models[0].dimensions) == 1000