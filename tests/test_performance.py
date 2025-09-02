"""Comprehensive performance and stress tests for dbt-to-lookml."""

import gc
import os
import sys
import time
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Dict, Any
from unittest.mock import patch
import concurrent.futures
import yaml

import pytest

from dbt_to_lookml.generator import LookMLGenerator
from dbt_to_lookml.models import (
    AggregationType,
    Config,
    ConfigMeta,
    Dimension,
    DimensionType,
    Entity,
    Measure,
    SemanticModel,
)
from dbt_to_lookml.parser import SemanticModelParser

# Try to import psutil for memory monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class TestPerformance:
    """Comprehensive performance and stress tests for the dbt-to-lookml pipeline."""

    def test_parse_multiple_files_performance(self) -> None:
        """Test parsing performance with multiple semantic model files."""
        semantic_models_dir = Path(__file__).parent.parent / "semantic_models"

        parser = SemanticModelParser()

        # Measure parsing time
        start_time = time.time()
        semantic_models = parser.parse_directory(semantic_models_dir)
        parsing_time = time.time() - start_time

        # Should complete parsing in reasonable time (less than 2 seconds)
        assert parsing_time < 2.0
        assert len(semantic_models) > 0

    def test_generate_large_number_of_models_performance(self) -> None:
        """Test generation performance with many semantic models."""
        # Create a large number of semantic models
        semantic_models = []
        for i in range(20):  # 20 models should be reasonable for testing
            model = SemanticModel(
                name=f"test_model_{i}",
                model=f"test_table_{i}",
                entities=[
                    Entity(name="id", type="primary"),
                    Entity(name=f"foreign_key_{j}", type="foreign")
                    for j in range(3)
                ],
                dimensions=[
                    Dimension(
                        name=f"dimension_{j}",
                        type=DimensionType.CATEGORICAL,
                        description=f"Test dimension {j}"
                    )
                    for j in range(10)
                ],
                measures=[
                    Measure(
                        name=f"measure_{j}",
                        agg=AggregationType.COUNT,
                        description=f"Test measure {j}"
                    )
                    for j in range(5)
                ]
            )
            semantic_models.append(model)

        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Measure generation time
            start_time = time.time()
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )
            generation_time = time.time() - start_time

            # Should complete generation in reasonable time (less than 10 seconds)
            assert generation_time < 10.0
            assert len(generated_files) == len(semantic_models) + 1  # +1 for explores.lkml
            assert len(validation_errors) == 0

    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
    def test_memory_usage_reasonable(self) -> None:
        """Test that memory usage remains reasonable during processing."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss  # in bytes

        # Create large semantic models
        large_semantic_models = []
        for i in range(10):
            model = SemanticModel(
                name=f"large_model_{i}",
                model=f"large_table_{i}",
                description=f"Large test model {i} with many fields",
                entities=[
                    Entity(
                        name=f"entity_{j}",
                        type="foreign" if j > 0 else "primary",
                        description=f"Entity {j} description"
                    )
                    for j in range(5)
                ],
                dimensions=[
                    Dimension(
                        name=f"dim_{j}",
                        type=DimensionType.CATEGORICAL,
                        description=f"Dimension {j} with detailed description",
                        expr=f"CASE WHEN field_{j} = 'value' THEN 'result' ELSE 'default' END"
                    )
                    for j in range(50)
                ] + [
                    Dimension(
                        name=f"time_dim_{j}",
                        type=DimensionType.TIME,
                        type_params={"time_granularity": "day"},
                        expr=f"created_at_{j}::date"
                    )
                    for j in range(5)
                ],
                measures=[
                    Measure(
                        name=f"measure_{j}",
                        agg=AggregationType.SUM,
                        expr=f"amount_{j}",
                        description=f"Measure {j} with detailed description"
                    )
                    for j in range(30)
                ]
            )
            large_semantic_models.append(model)

        parser = SemanticModelParser()
        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Generate LookML files
            generated_files, validation_errors = generator.generate_lookml_files(
                large_semantic_models, output_dir
            )
            
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            memory_increase_mb = memory_increase / (1024 * 1024)

            # Memory increase should be reasonable (less than 100MB)
            assert memory_increase_mb < 100
            assert len(validation_errors) == 0

    def test_concurrent_processing_performance(self) -> None:
        """Test performance when processing multiple models concurrently."""
        semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
        parser = SemanticModelParser()
        generator = LookMLGenerator()

        # Sequential processing
        start_time = time.time()
        semantic_models = parser.parse_directory(semantic_models_dir)
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )
        sequential_time = time.time() - start_time

        # Concurrent processing simulation (parsing files individually)
        start_time = time.time()
        yaml_files = list(semantic_models_dir.glob("*.yml"))
        all_models = []
        for yaml_file in yaml_files:
            models = parser.parse_file(yaml_file)
            all_models.extend(models)
        concurrent_time = time.time() - start_time

        # Concurrent approach should not be significantly slower
        assert len(all_models) == len(semantic_models)
        # Allow some variance but concurrent shouldn't be more than 2x slower
        assert concurrent_time < sequential_time * 2

    @pytest.mark.slow
    def test_stress_test_many_models(self) -> None:
        """Stress test with a large number of semantic models."""
        # Create many models for stress testing
        stress_models = []
        for i in range(100):  # 100 models for stress test
            model = SemanticModel(
                name=f"stress_model_{i:03d}",
                model=f"stress_table_{i:03d}",
                description=f"Stress test model {i}",
                entities=[
                    Entity(name="id", type="primary"),
                    Entity(name="parent_id", type="foreign")
                ],
                dimensions=[
                    Dimension(
                        name=f"category_{j}",
                        type=DimensionType.CATEGORICAL,
                        expr=f"category_{j}_field"
                    )
                    for j in range(5)
                ] + [
                    Dimension(
                        name="created_date",
                        type=DimensionType.TIME,
                        type_params={"time_granularity": "day"},
                        expr="created_at::date"
                    )
                ],
                measures=[
                    Measure(
                        name=f"total_{j}",
                        agg=AggregationType.SUM,
                        expr=f"amount_{j}"
                    )
                    for j in range(3)
                ] + [
                    Measure(
                        name="record_count",
                        agg=AggregationType.COUNT
                    )
                ]
            )
            stress_models.append(model)

        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            start_time = time.time()
            generated_files, validation_errors = generator.generate_lookml_files(
                stress_models, output_dir
            )
            stress_time = time.time() - start_time

            # Should complete within reasonable time (less than 60 seconds for 100 models)
            assert stress_time < 60.0
            assert len(generated_files) == 101  # 100 views + 1 explores
            assert len(validation_errors) == 0

            # Verify some files were actually created
            view_files = list(output_dir.glob("*.view.lkml"))
            assert len(view_files) == 100
            
            explores_file = output_dir / "explores.lkml"
            assert explores_file.exists()
            
            # Spot check a few files for content
            sample_view = output_dir / "stress_model_000.view.lkml"
            assert sample_view.exists()
            content = sample_view.read_text()
            assert "stress_model_000" in content
            assert "stress_table_000" in content

    def test_parsing_performance_with_complex_expressions(self) -> None:
        """Test parsing performance with complex SQL expressions."""
        # Create models with very complex SQL expressions
        complex_models = []
        for i in range(10):
            # Create a very complex CASE statement
            complex_case = "CASE"
            for j in range(20):
                complex_case += f" WHEN field_{j} = 'value_{j}' AND other_field_{j} > {j} THEN 'result_{j}'"
            complex_case += " ELSE 'default' END"
            
            model = SemanticModel(
                name=f"complex_model_{i}",
                model=f"complex_table_{i}",
                dimensions=[
                    Dimension(
                        name="complex_dimension",
                        type=DimensionType.CATEGORICAL,
                        expr=complex_case
                    ),
                    Dimension(
                        name="nested_functions",
                        type=DimensionType.CATEGORICAL,
                        expr="UPPER(TRIM(COALESCE(NULLIF(field, ''), 'default')))"
                    )
                ],
                measures=[
                    Measure(
                        name="complex_measure",
                        agg=AggregationType.SUM,
                        expr="CASE WHEN status = 'active' THEN amount * rate ELSE 0 END"
                    )
                ]
            )
            complex_models.append(model)

        generator = LookMLGenerator()

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            start_time = time.time()
            generated_files, validation_errors = generator.generate_lookml_files(
                complex_models, output_dir
            )
            processing_time = time.time() - start_time

            # Should handle complex expressions efficiently (less than 5 seconds)
            assert processing_time < 5.0
            assert len(validation_errors) == 0
            
            # Verify complex expressions are preserved
            sample_file = output_dir / "complex_model_0.view.lkml"
            content = sample_file.read_text()
            assert "CASE" in content
            assert "WHEN field_" in content
            assert "UPPER(TRIM(COALESCE" in content

    def test_file_io_performance(self) -> None:
        """Test file I/O performance with many small files."""
        semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
        parser = SemanticModelParser()
        
        # Measure file reading performance
        yaml_files = list(semantic_models_dir.glob("*.yml"))
        
        start_time = time.time()
        for _ in range(10):  # Read files multiple times
            for yaml_file in yaml_files:
                models = parser.parse_file(yaml_file)
                assert len(models) > 0
        io_time = time.time() - start_time
        
        # Should be able to read files efficiently
        total_reads = len(yaml_files) * 10
        average_time_per_read = io_time / total_reads
        assert average_time_per_read < 0.1  # Less than 0.1 seconds per file read

    def test_validation_performance_impact(self) -> None:
        """Test performance impact of validation."""
        semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
        parser = SemanticModelParser()
        semantic_models = parser.parse_directory(semantic_models_dir)

        # Generate without validation
        generator_no_validation = LookMLGenerator(validate_syntax=False)
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            start_time = time.time()
            generated_files, _ = generator_no_validation.generate_lookml_files(
                semantic_models, output_dir
            )
            time_without_validation = time.time() - start_time

        # Generate with validation
        generator_with_validation = LookMLGenerator(validate_syntax=True)
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            start_time = time.time()
            generated_files, _ = generator_with_validation.generate_lookml_files(
                semantic_models, output_dir
            )
            time_with_validation = time.time() - start_time

        # Validation should not add excessive overhead (less than 3x slower)
        assert time_with_validation < time_without_validation * 3

    def test_cpu_intensive_operations_performance(self) -> None:
        """Test performance of CPU-intensive operations."""
        # Create models with operations that require significant CPU
        cpu_intensive_models = []
        for i in range(20):
            model = SemanticModel(
                name=f"cpu_test_{i}",
                model=f"cpu_table_{i}",
                config=Config(meta=ConfigMeta(
                    domain="performance_test",
                    owner="test_suite",
                    contains_pii=False,
                    update_frequency="hourly"
                )),
                entities=[
                    Entity(
                        name="complex_key",
                        type="primary",
                        expr=f"MD5(CONCAT(field1, '_', field2, '_', {i}))"
                    )
                ],
                dimensions=[
                    Dimension(
                        name="regex_dimension",
                        type=DimensionType.CATEGORICAL,
                        expr="REGEXP_REPLACE(field, '[^a-zA-Z0-9]', '_', 'g')"
                    ),
                    Dimension(
                        name="json_extraction",
                        type=DimensionType.CATEGORICAL,
                        expr="JSON_EXTRACT_PATH_TEXT(json_column, 'nested', 'field', 'value')"
                    ),
                    Dimension(
                        name="window_function",
                        type=DimensionType.CATEGORICAL,
                        expr="CASE WHEN ROW_NUMBER() OVER (PARTITION BY category ORDER BY created_at DESC) = 1 THEN 'latest' ELSE 'historical' END"
                    )
                ],
                measures=[
                    Measure(
                        name="complex_calculation",
                        agg=AggregationType.SUM,
                        expr="CASE WHEN status IN ('completed', 'verified') THEN amount * (1 + tax_rate) ELSE 0 END"
                    ),
                    Measure(
                        name="statistical_measure",
                        agg=AggregationType.AVERAGE,
                        expr="SQRT(POWER(value1 - avg_value1, 2) + POWER(value2 - avg_value2, 2))"
                    )
                ]
            )
            cpu_intensive_models.append(model)
        
        generator = LookMLGenerator(validate_syntax=True, format_output=True)
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            start_time = time.time()
            generated_files, validation_errors = generator.generate_lookml_files(
                cpu_intensive_models, output_dir
            )
            cpu_time = time.time() - start_time
            
            # Should handle CPU-intensive operations efficiently (less than 15 seconds)
            assert cpu_time < 15.0
            assert len(validation_errors) == 0
            assert len(generated_files) == 21  # 20 views + 1 explores
            
            # Verify complex expressions are preserved
            sample_file = output_dir / "cpu_test_0.view.lkml"
            content = sample_file.read_text()
            assert "MD5(CONCAT" in content
            assert "REGEXP_REPLACE" in content
            assert "JSON_EXTRACT_PATH_TEXT" in content
            assert "ROW_NUMBER() OVER" in content

    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
    def test_memory_leak_detection(self) -> None:
        """Test for memory leaks during repeated operations."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        parser = SemanticModelParser()
        generator = LookMLGenerator()
        
        # Create a moderate-sized model for repeated processing
        test_model = SemanticModel(
            name="leak_test",
            model="leak_table",
            dimensions=[
                Dimension(name=f"dim_{i}", type=DimensionType.CATEGORICAL)
                for i in range(50)
            ],
            measures=[
                Measure(name=f"measure_{i}", agg=AggregationType.COUNT)
                for i in range(25)
            ]
        )
        
        memory_samples = []
        
        # Perform many iterations to detect leaks
        for iteration in range(20):
            with TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                generated_files, validation_errors = generator.generate_lookml_files(
                    [test_model], output_dir
                )
                assert len(validation_errors) == 0
                
                # Sample memory every few iterations
                if iteration % 5 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_samples.append(current_memory)
                    
                # Force garbage collection
                gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (less than 50MB for 20 iterations)
        assert memory_increase < 50, f"Potential memory leak: {memory_increase:.1f}MB increase"
        
        # Memory should not continuously increase
        if len(memory_samples) > 2:
            # Allow some fluctuation but no continuous growth
            max_sample = max(memory_samples)
            min_sample = min(memory_samples)
            range_mb = max_sample - min_sample
            assert range_mb < 30, f"Memory usage too variable: {range_mb:.1f}MB range"

    def test_concurrent_access_performance(self) -> None:
        """Test performance under concurrent access patterns."""
        semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
        
        def process_models(thread_id: int) -> Dict[str, Any]:
            parser = SemanticModelParser()
            generator = LookMLGenerator()
            
            start_time = time.time()
            semantic_models = parser.parse_directory(semantic_models_dir)
            
            with TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                generated_files, validation_errors = generator.generate_lookml_files(
                    semantic_models, output_dir
                )
            
            end_time = time.time()
            
            return {
                "thread_id": thread_id,
                "duration": end_time - start_time,
                "models_count": len(semantic_models),
                "files_count": len(generated_files),
                "errors_count": len(validation_errors)
            }
        
        # Run concurrent processing
        num_threads = 4
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            start_time = time.time()
            futures = [executor.submit(process_models, i) for i in range(num_threads)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            total_concurrent_time = time.time() - start_time
        
        # Run sequential processing for comparison
        start_time = time.time()
        sequential_result = process_models(0)
        sequential_time = time.time() - start_time
        
        # Verify all threads completed successfully
        assert len(results) == num_threads
        for result in results:
            assert result["errors_count"] == 0
            assert result["models_count"] > 0
            assert result["files_count"] > 0
        
        # Concurrent processing should complete in reasonable time
        # (not necessarily faster due to I/O bound operations, but not much slower)
        assert total_concurrent_time < sequential_time * 2
        
        # Individual thread performance should be reasonable
        max_thread_duration = max(result["duration"] for result in results)
        assert max_thread_duration < sequential_time * 1.5

    def test_large_file_generation_performance(self) -> None:
        """Test performance when generating very large LookML files."""
        # Create a model that will generate a large file
        large_model = SemanticModel(
            name="large_file_test",
            model="large_table",
            description="Model designed to generate large LookML files",
            entities=[
                Entity(
                    name=f"entity_{i}",
                    type="foreign" if i > 0 else "primary",
                    expr=f"entity_field_{i}",
                    description=f"Entity {i} with detailed description: " + "x" * 200
                )
                for i in range(10)
            ],
            dimensions=[
                Dimension(
                    name=f"dimension_{i}",
                    type=DimensionType.CATEGORICAL,
                    expr=f"CASE WHEN complex_condition_{i} THEN 'value_{i}' ELSE 'default_{i}' END",
                    description=f"Dimension {i}: " + "Long description " * 50
                )
                for i in range(200)  # 200 dimensions
            ] + [
                Dimension(
                    name=f"time_dimension_{i}",
                    type=DimensionType.TIME,
                    type_params={"time_granularity": "day"},
                    expr=f"timestamp_field_{i}::date",
                    description=f"Time dimension {i}: " + "Detailed time description " * 20
                )
                for i in range(20)  # 20 time dimensions
            ],
            measures=[
                Measure(
                    name=f"measure_{i}",
                    agg=AggregationType.SUM,
                    expr=f"CASE WHEN active_{i} THEN amount_{i} * rate_{i} ELSE 0 END",
                    description=f"Measure {i}: " + "Complex measure description " * 30
                )
                for i in range(100)  # 100 measures
            ]
        )
        
        generator = LookMLGenerator()
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            start_time = time.time()
            generated_files, validation_errors = generator.generate_lookml_files(
                [large_model], output_dir
            )
            generation_time = time.time() - start_time
            
            # Should handle large file generation efficiently (less than 5 seconds)
            assert generation_time < 5.0
            assert len(validation_errors) == 0
            
            # Verify large file was created
            view_file = output_dir / "large_file_test.view.lkml"
            assert view_file.exists()
            
            # File should be quite large
            file_size = view_file.stat().st_size
            assert file_size > 100000  # Should be over 100KB
            
            # Verify content is complete
            content = view_file.read_text()
            assert content.count("dimension:") >= 200
            assert content.count("measure:") >= 100
            assert content.count("dimension_group:") >= 20

    def test_benchmark_against_baseline(self) -> None:
        """Benchmark current performance against expected baseline."""
        semantic_models_dir = Path(__file__).parent.parent / "semantic_models"
        
        parser = SemanticModelParser()
        generator = LookMLGenerator(validate_syntax=True)
        
        # Measure end-to-end performance
        start_time = time.time()
        
        semantic_models = parser.parse_directory(semantic_models_dir)
        parse_time = time.time() - start_time
        
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            generation_start = time.time()
            generated_files, validation_errors = generator.generate_lookml_files(
                semantic_models, output_dir
            )
            generation_time = time.time() - generation_start
        
        total_time = time.time() - start_time
        
        # Expected performance baselines (adjust based on typical hardware)
        expected_parse_time = 2.0  # 2 seconds for parsing
        expected_generation_time = 5.0  # 5 seconds for generation
        expected_total_time = 7.0  # 7 seconds total
        
        # Performance should meet baseline expectations
        assert parse_time < expected_parse_time, f"Parsing too slow: {parse_time:.2f}s"
        assert generation_time < expected_generation_time, f"Generation too slow: {generation_time:.2f}s"
        assert total_time < expected_total_time, f"Total time too slow: {total_time:.2f}s"
        
        # Verify results are complete
        assert len(semantic_models) >= 6
        assert len(generated_files) >= 7
        assert len(validation_errors) == 0
        
        # Performance metrics for monitoring
        models_per_second = len(semantic_models) / total_time
        files_per_second = len(generated_files) / total_time
        
        # Should achieve reasonable throughput
        assert models_per_second > 0.5  # At least 0.5 models per second
        assert files_per_second > 0.5   # At least 0.5 files per second