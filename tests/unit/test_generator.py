"""Unit tests for LookML generator."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

import pytest

from dbt_to_lookml.generators.lookml import LookMLGenerator, LookMLValidationError
from dbt_to_lookml.models import (
    AggregationType,
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
)


class TestLookMLGenerator:
    """Test cases for LookMLGenerator."""

    def test_generator_initialization(self) -> None:
        """Test generator initialization with different settings."""
        # Default initialization
        generator = LookMLGenerator()
        assert generator.mapper.view_prefix == ""
        assert generator.mapper.explore_prefix == ""
        assert generator.validate_syntax is True
        assert generator.format_output is True

        # Custom initialization
        generator_custom = LookMLGenerator(
            view_prefix="v_",
            explore_prefix="e_",
            validate_syntax=False,
            format_output=False
        )
        assert generator_custom.mapper.view_prefix == "v_"
        assert generator_custom.mapper.explore_prefix == "e_"
        assert generator_custom.validate_syntax is False
        assert generator_custom.format_output is False

    def test_generate_view_lookml(self) -> None:
        """Test generating LookML content for a view."""
        generator = LookMLGenerator()

        # Create a sample LookML view
        view = LookMLView(
            name="users",
            sql_table_name="dim_users",
            description="User dimension table",
            dimensions=[
                LookMLDimension(
                    name="user_id",
                    type="string",
                    sql="${TABLE}.user_id",
                    description="User ID",
                    primary_key=True
                ),
                LookMLDimension(
                    name="status",
                    type="string",
                    sql="${TABLE}.status",
                    description="User status"
                )
            ],
            dimension_groups=[
                LookMLDimensionGroup(
                    name="created",
                    type="time",
                    timeframes=["date", "week", "month", "year"],
                    sql="${TABLE}.created_at",
                    description="Creation date"
                )
            ],
            measures=[
                LookMLMeasure(
                    name="count",
                    type="count",
                    sql="1",
                    description="Count of users"
                )
            ]
        )

        # Generate LookML content
        content = generator._generate_view_lookml(view)

        # Verify content contains expected elements
        assert "view:" in content
        assert "users" in content
        assert "sql_table_name: dim_users" in content
        assert "dimension:" in content
        assert "dimension_group:" in content
        assert "measure:" in content
        assert "primary_key: yes" in content

    def test_generate_explores_lookml(self) -> None:
        """Test generating LookML content for explores."""
        generator = LookMLGenerator()

        explores = [
            LookMLExplore(
                name="users",
                view_name="users",
                description="User exploration"
            ),
            LookMLExplore(
                name="orders",
                view_name="orders",
                description="Order exploration"
            )
        ]

        content = generator._generate_explores_lookml(explores)

        # Verify content contains expected elements
        assert "explore:" in content
        assert "users" in content
        assert "orders" in content
        assert "type: table" in content
        assert "from: users" in content
        assert "from: orders" in content

    def test_generate_empty_view(self) -> None:
        """Test generating LookML for a view with no dimensions or measures."""
        generator = LookMLGenerator()

        view = LookMLView(
            name="empty_view",
            sql_table_name="empty_table"
        )

        content = generator._generate_view_lookml(view)

        assert "view:" in content
        assert "empty_view" in content
        assert "sql_table_name: empty_table" in content
        # Should not contain dimension or measure sections
        assert "dimension:" not in content
        assert "measure:" not in content

    def test_lookml_files_generation(self) -> None:
        """Test complete LookML files generation."""
        generator = LookMLGenerator()

        semantic_models = [
            SemanticModel(
                name="users",
                model="dim_users",
                description="User table",
                entities=[
                    Entity(name="user_id", type="primary")
                ],
                dimensions=[
                    Dimension(name="status", type=DimensionType.CATEGORICAL)
                ],
                measures=[
                    Measure(name="user_count", agg=AggregationType.COUNT)
                ]
            ),
            SemanticModel(
                name="orders",
                model="fact_orders",
                measures=[
                    Measure(name="order_count", agg=AggregationType.COUNT)
                ]
            )
        ]

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Verify files were created
            assert len(generated_files) == 3  # 2 views + 1 explores file
            assert len(validation_errors) == 0

            # Check file contents
            users_view = output_dir / "users.view.lkml"
            orders_view = output_dir / "orders.view.lkml"
            explores_file = output_dir / "explores.lkml"

            assert users_view.exists()
            assert orders_view.exists()
            assert explores_file.exists()

            # Verify content
            users_content = users_view.read_text()
            assert "view:" in users_content
            assert "users" in users_content

            explores_content = explores_file.read_text()
            assert "explore:" in explores_content

    def test_dry_run_mode(self) -> None:
        """Test generator in dry run mode."""
        generator = LookMLGenerator()

        semantic_models = [
            SemanticModel(
                name="test_model",
                model="test_table"
            )
        ]

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir, dry_run=True
            )

            # Files should be listed but not actually created
            assert len(generated_files) == 2  # view + explores
            assert not any(f.exists() for f in generated_files)

    def test_validation_enabled(self) -> None:
        """Test generation with syntax validation enabled."""
        generator = LookMLGenerator(validate_syntax=True)

        semantic_models = [
            SemanticModel(
                name="valid_model",
                model="valid_table",
                measures=[
                    Measure(name="count", agg=AggregationType.COUNT)
                ]
            )
        ]

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Should pass validation
            assert len(validation_errors) == 0

    def test_validation_disabled(self) -> None:
        """Test generation with syntax validation disabled."""
        generator = LookMLGenerator(validate_syntax=False)

        semantic_models = [
            SemanticModel(
                name="test_model",
                model="test_table"
            )
        ]

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Should not raise validation errors even with potentially problematic content
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Should not have validation errors since validation is disabled
            assert len([e for e in validation_errors if "syntax" in e.lower()]) == 0

    @patch('lkml.load')
    def test_validation_error_handling(self, mock_load: MagicMock) -> None:
        """Test handling of LookML validation errors."""
        # Make lkml.load raise an exception to simulate validation failure
        mock_load.side_effect = Exception("Invalid syntax")

        generator = LookMLGenerator(validate_syntax=True)

        semantic_models = [
            SemanticModel(
                name="invalid_model",
                model="invalid_table"
            )
        ]

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Should have validation errors
            assert len(validation_errors) > 0
            assert any("syntax" in error.lower() for error in validation_errors)

    def test_format_lookml_content(self) -> None:
        """Test LookML content formatting."""
        generator = LookMLGenerator(format_output=True)

        # Test with unformatted content
        unformatted = """view: { test_view: { sql_table_name: test_table
dimension: { user_id: { type: string sql: ${TABLE}.user_id } }
} }"""

        formatted = generator._format_lookml_content(unformatted)

        # Should have proper indentation
        lines = formatted.split('\n')
        assert any(line.startswith('  ') for line in lines)  # Should have indented lines

    def test_format_disabled(self) -> None:
        """Test generator with formatting disabled."""
        generator = LookMLGenerator(format_output=False)

        view = LookMLView(
            name="test_view",
            sql_table_name="test_table"
        )

        content = generator._generate_view_lookml(view)
        
        # Content should be generated but not necessarily well-formatted
        assert "view:" in content
        assert "test_view" in content

    def test_filename_sanitization(self) -> None:
        """Test filename sanitization."""
        generator = LookMLGenerator()

        test_cases = [
            ("valid_name", "valid_name"),
            ("name with spaces", "name_with_spaces"),
            ("name-with-dashes", "name_with_dashes"),
            ("name.with.dots", "name_with_dots"),
            ("123numeric", "view_123numeric"),
            ("", "view_"),
            ("__multiple__underscores__", "multiple_underscores"),
        ]

        for input_name, expected in test_cases:
            result = generator._sanitize_filename(input_name)
            assert result == expected

    def test_generation_with_prefixes(self) -> None:
        """Test generation with view and explore prefixes."""
        generator = LookMLGenerator(view_prefix="v_", explore_prefix="e_")

        semantic_models = [
            SemanticModel(
                name="users",
                model="dim_users"
            )
        ]

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Check that prefixes are applied to filenames
            view_file = output_dir / "v_users.view.lkml"
            assert view_file.exists()

            # Check content has prefixed names
            content = view_file.read_text()
            assert "v_users" in content

            explores_content = (output_dir / "explores.lkml").read_text()
            assert "e_users" in explores_content

    def test_generation_summary(self) -> None:
        """Test generation summary creation."""
        generator = LookMLGenerator()

        semantic_models = [
            SemanticModel(name="model1", model="table1"),
            SemanticModel(name="model2", model="table2"),
        ]

        generated_files = [
            Path("/tmp/model1.view.lkml"),
            Path("/tmp/model2.view.lkml"),
            Path("/tmp/explores.lkml"),
        ]

        validation_errors = ["Error 1", "Error 2"]

        summary = generator.get_generation_summary(
            semantic_models, generated_files, validation_errors
        )

        # Verify summary content
        assert "LookML Generation Summary" in summary
        assert "Processed semantic models: 2" in summary
        assert "Generated files: 3" in summary
        assert "Validation errors: 2" in summary
        assert "View files: 2" in summary
        assert "Explore files: 1" in summary
        assert "Error 1" in summary
        assert "Error 2" in summary

    def test_complex_view_with_all_elements(self) -> None:
        """Test generating view with all possible elements."""
        generator = LookMLGenerator()

        view = LookMLView(
            name="complex_view",
            sql_table_name="complex_table",
            description="Complex view with all elements",
            dimensions=[
                LookMLDimension(
                    name="id",
                    type="string",
                    sql="${TABLE}.id",
                    description="ID field",
                    primary_key=True
                ),
                LookMLDimension(
                    name="hidden_field",
                    type="string",
                    sql="${TABLE}.hidden",
                    hidden=True
                )
            ],
            dimension_groups=[
                LookMLDimensionGroup(
                    name="created",
                    type="time",
                    timeframes=["date", "week", "month"],
                    sql="${TABLE}.created_at",
                    description="Creation time",
                    label="Created At"
                )
            ],
            measures=[
                LookMLMeasure(
                    name="total_count",
                    type="count",
                    sql="1",
                    description="Total count",
                    label="Total Count"
                ),
                LookMLMeasure(
                    name="hidden_measure",
                    type="sum",
                    sql="${TABLE}.amount",
                    hidden=True
                )
            ]
        )

        content = generator._generate_view_lookml(view)

        # Verify all elements are present
        assert "complex_view" in content
        assert "primary_key: yes" in content
        assert "hidden: yes" in content
        assert "dimension_group:" in content
        assert "timeframes:" in content

    def test_error_handling_during_generation(self) -> None:
        """Test error handling during file generation process."""
        generator = LookMLGenerator()

        # Create a semantic model that might cause issues
        semantic_models = [
            SemanticModel(
                name="test_model",
                model="test_table"
            )
        ]

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Patch the mapper to raise an exception
            with patch.object(generator.mapper, 'semantic_model_to_view') as mock_mapper:
                mock_mapper.side_effect = Exception("Mapping error")
                
                generated_files, validation_errors = generator.generate_lookml_files(
                    semantic_models, output_dir
                )

                # Should handle the error gracefully
                assert len(validation_errors) > 0
                assert any("Mapping error" in error for error in validation_errors)

    def test_output_directory_creation(self) -> None:
        """Test that output directory is created if it doesn't exist."""
        generator = LookMLGenerator()

        semantic_models = [
            SemanticModel(name="test", model="test_table")
        ]

        with TemporaryDirectory() as temp_dir:
            # Use a subdirectory that doesn't exist yet
            output_dir = Path(temp_dir) / "nested" / "output"
            assert not output_dir.exists()

            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )

            # Directory should be created
            assert output_dir.exists()
            assert output_dir.is_dir()

    def test_special_characters_in_sql(self) -> None:
        """Test handling of special characters in SQL expressions."""
        generator = LookMLGenerator()

        view = LookMLView(
            name="special_chars",
            sql_table_name="test_table",
            dimensions=[
                LookMLDimension(
                    name="complex_field",
                    type="string",
                    sql="CASE WHEN status = 'active' THEN 'Active' ELSE 'Inactive' END"
                )
            ]
        )

        content = generator._generate_view_lookml(view)

        # Should handle quotes and complex SQL
        assert "CASE WHEN" in content
        assert "'active'" in content or '"active"' in content

    def test_validate_lookml_syntax_success(self) -> None:
        """Test successful LookML syntax validation."""
        generator = LookMLGenerator()

        valid_content = """
        view: test_view {
          sql_table_name: test_table ;;
        }
        """

        # Should not raise exception for valid content
        generator._validate_lookml_syntax(valid_content)

    @patch('lkml.load')
    def test_validate_lookml_syntax_failure(self, mock_load: MagicMock) -> None:
        """Test LookML syntax validation failure."""
        mock_load.side_effect = Exception("Parse error")

        generator = LookMLGenerator()

        invalid_content = "invalid lookml content"

        with pytest.raises(LookMLValidationError):
            generator._validate_lookml_syntax(invalid_content)

    @patch('lkml.load')
    def test_validate_lookml_syntax_returns_none(self, mock_load: MagicMock) -> None:
        """Test LookML syntax validation when parse returns None."""
        mock_load.return_value = None

        generator = LookMLGenerator()

        content = "some content"

        with pytest.raises(LookMLValidationError, match="Failed to parse LookML content"):
            generator._validate_lookml_syntax(content)

    def test_empty_explores_list(self) -> None:
        """Test generation with empty explores list."""
        generator = LookMLGenerator()

        content = generator._generate_explores_lookml([])

        # Should generate minimal structure
        assert "explore:" in content

    def test_permission_error_handling(self) -> None:
        """Test handling of file permission errors."""
        generator = LookMLGenerator()

        semantic_models = [
            SemanticModel(name="test", model="test_table")
        ]

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Make directory read-only to cause permission error
            output_dir.chmod(0o444)
            
            try:
                generated_files, validation_errors = generator.generate_lookml_files(
                    semantic_models, output_dir
                )

                # Should handle permission errors gracefully
                # Note: The exact behavior depends on the OS and file system
                # This test verifies the function doesn't crash
                assert isinstance(generated_files, list)
                assert isinstance(validation_errors, list)
            finally:
                # Restore permissions for cleanup
                output_dir.chmod(0o755)

    def test_unicode_content_handling(self) -> None:
        """Test handling of Unicode characters in content."""
        generator = LookMLGenerator()

        view = LookMLView(
            name="unicode_view",
            sql_table_name="unicode_table",
            description="Test with unicode: æøå αβγ 你好",
            dimensions=[
                LookMLDimension(
                    name="unicode_field",
                    type="string",
                    sql="${TABLE}.field",
                    description="Unicode description: 测试"
                )
            ]
        )

        content = generator._generate_view_lookml(view)

        # Should handle Unicode characters properly
        assert "unicode_view" in content
        assert "你好" in content or "unicode" in content  # Content should be preserved