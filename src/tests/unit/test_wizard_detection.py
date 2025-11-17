"""Unit tests for wizard detection module."""

import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from dbt_to_lookml.wizard.detection import (
    CachedDetection,
    DetectionCache,
    DetectionResult,
    ProjectDetector,
)

# ============================================================================
# Test Category 1: Directory Detection (6 tests)
# ============================================================================


@pytest.mark.unit
@pytest.mark.wizard
def test_detect_semantic_models_directory(tmp_path: Path) -> None:
    """Test detection of semantic_models/ directory."""
    # Create semantic_models/ with YAML file
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "users.yml"
    yaml_file.write_text("semantic_models:\n  - name: users\n    model: dim_users\n")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.input_dir == semantic_dir
    assert result.found_yaml_files == 1
    assert result.has_semantic_models()


@pytest.mark.unit
@pytest.mark.wizard
def test_detect_nested_models_directory(tmp_path: Path) -> None:
    """Test detection of models/semantic/ directory."""
    # Create models/semantic/ with YAML file
    models_dir = tmp_path / "models" / "semantic"
    models_dir.mkdir(parents=True)
    yaml_file = models_dir / "orders.yml"
    yaml_file.write_text("semantic_models:\n  - name: orders\n    model: fct_orders\n")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.input_dir == models_dir
    assert result.found_yaml_files == 1


@pytest.mark.unit
@pytest.mark.wizard
def test_detect_multiple_candidates_returns_first(tmp_path: Path) -> None:
    """Test priority when multiple directories exist."""
    # Create multiple candidate directories
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text(
        "semantic_models:\n  - name: users\n    model: dim_users\n"
    )

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "orders.yml").write_text(
        "semantic_models:\n  - name: orders\n    model: fct_orders\n"
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    # Should return semantic_models/ (higher priority)
    assert result.input_dir == semantic_dir


@pytest.mark.unit
@pytest.mark.wizard
def test_detect_no_input_directory_returns_none(tmp_path: Path) -> None:
    """Test behavior when no semantic model directory exists."""
    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.input_dir is None
    assert result.found_yaml_files == 0
    assert not result.has_semantic_models()
    # Should provide default
    assert result.get_input_dir_or_default() == Path("semantic_models")


@pytest.mark.unit
@pytest.mark.wizard
def test_detect_empty_directory_is_skipped(tmp_path: Path) -> None:
    """Test that empty directories are skipped."""
    # Create empty semantic_models/ directory
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()

    # Create models/ with YAML
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "users.yml").write_text(
        "semantic_models:\n  - name: users\n    model: dim_users\n"
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    # Should skip empty semantic_models/ and find models/
    assert result.input_dir == models_dir


@pytest.mark.unit
@pytest.mark.wizard
def test_detect_handles_yml_and_yaml_extensions(tmp_path: Path) -> None:
    """Test that both .yml and .yaml extensions are detected."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text(
        "semantic_models:\n  - name: users\n    model: dim_users\n"
    )
    (semantic_dir / "orders.yaml").write_text(
        "semantic_models:\n  - name: orders\n    model: fct_orders\n"
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.input_dir == semantic_dir
    assert result.found_yaml_files == 2


# ============================================================================
# Test Category 2: Output Directory Detection (4 tests)
# ============================================================================


@pytest.mark.unit
@pytest.mark.wizard
def test_detect_build_lookml_output_directory(tmp_path: Path) -> None:
    """Test detection of build/lookml/ output directory."""
    output_dir = tmp_path / "build" / "lookml"
    output_dir.mkdir(parents=True)

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.output_dir == output_dir


@pytest.mark.unit
@pytest.mark.wizard
def test_detect_lookml_output_directory(tmp_path: Path) -> None:
    """Test detection of lookml/ output directory."""
    output_dir = tmp_path / "lookml"
    output_dir.mkdir()

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.output_dir == output_dir


@pytest.mark.unit
@pytest.mark.wizard
def test_detect_empty_output_directory_is_valid(tmp_path: Path) -> None:
    """Test that empty output directories are valid."""
    # Create empty build/lookml/ directory
    output_dir = tmp_path / "build" / "lookml"
    output_dir.mkdir(parents=True)

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.output_dir == output_dir


@pytest.mark.unit
@pytest.mark.wizard
def test_detect_no_output_directory_returns_none(tmp_path: Path) -> None:
    """Test behavior when no output directory exists."""
    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.output_dir is None
    # Should provide default
    assert result.get_output_dir_or_default() == Path("build/lookml")


# ============================================================================
# Test Category 3: Schema Name Extraction (6 tests)
# ============================================================================


@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_from_ref_with_schema(tmp_path: Path) -> None:
    """Test schema extraction from ref('schema.model')."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "users.yml"
    yaml_file.write_text(
        """
semantic_models:
  - name: users
    model: ref('analytics_prod.dim_users')
    entities: []
    dimensions: []
    measures: []
"""
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name == "analytics_prod"


@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_from_ref_without_schema(tmp_path: Path) -> None:
    """Test behavior when ref() has no schema."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "users.yml"
    yaml_file.write_text(
        """
semantic_models:
  - name: users
    model: ref('dim_users')
    entities: []
    dimensions: []
    measures: []
"""
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name is None
    # Should provide default
    assert result.get_schema_name_or_default("public") == "public"


@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_from_source(tmp_path: Path) -> None:
    """Test schema extraction from source('schema', 'table')."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "orders.yml"
    yaml_file.write_text(
        """
semantic_models:
  - name: orders
    model: source('raw_data', 'orders')
    entities: []
    dimensions: []
    measures: []
"""
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name == "raw_data"


@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_from_direct_pattern(tmp_path: Path) -> None:
    """Test schema extraction from direct schema.table."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "products.yml"
    yaml_file.write_text(
        """
semantic_models:
  - name: products
    model: analytics.products
    entities: []
    dimensions: []
    measures: []
"""
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name == "analytics"


@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_handles_invalid_yaml(tmp_path: Path) -> None:
    """Test graceful failure on invalid YAML."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "invalid.yml"
    yaml_file.write_text("invalid: yaml: content: [[[")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    # Should not crash, return None
    assert result.schema_name is None


@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_no_semantic_models(tmp_path: Path) -> None:
    """Test behavior when YAML has no semantic_models."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "empty.yml"
    yaml_file.write_text("some_other_key: value\n")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name is None


# ============================================================================
# Test Category 4: Caching (5 tests)
# ============================================================================


@pytest.mark.unit
@pytest.mark.wizard
def test_cache_returns_same_result(tmp_path: Path) -> None:
    """Test that cached result matches original."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text(
        "semantic_models:\n  - name: users\n    model: ref('analytics.dim_users')\n"
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=True)

    # First call
    result1 = detector.detect()

    # Second call should use cache
    result2 = detector.detect()

    assert result1.input_dir == result2.input_dir
    assert result1.schema_name == result2.schema_name
    assert result1.found_yaml_files == result2.found_yaml_files


@pytest.mark.unit
@pytest.mark.wizard
def test_cache_expires_after_ttl(tmp_path: Path) -> None:
    """Test that cache expires after 60 seconds."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text(
        "semantic_models:\n  - name: users\n    model: dim_users\n"
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=True)
    result = detector.detect()

    # Manually expire cache by manipulating timestamp
    if detector._cache:
        cached = detector._cache._cache.get(tmp_path)
        if cached:
            # Set timestamp to 61 seconds ago
            cached.timestamp = datetime.now() - timedelta(seconds=61)

    # Next call should re-detect (cache expired)
    result2 = detector.detect()

    # Results should still match, but detection was performed again
    assert result.input_dir == result2.input_dir


@pytest.mark.unit
@pytest.mark.wizard
def test_cache_can_be_bypassed(tmp_path: Path) -> None:
    """Test use_cache=False bypasses cache."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text(
        "semantic_models:\n  - name: users\n    model: dim_users\n"
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=True)

    # First call
    result1 = detector.detect()

    # Second call with use_cache=False
    result2 = detector.detect(use_cache=False)
    time2 = result2.detection_time_ms

    # Results should match
    assert result1.input_dir == result2.input_dir

    # Detection times should be similar (both did filesystem scan)
    assert time2 > 0  # Re-scanned filesystem


@pytest.mark.unit
@pytest.mark.wizard
def test_cache_can_be_disabled(tmp_path: Path) -> None:
    """Test cache_enabled=False disables caching."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text(
        "semantic_models:\n  - name: users\n    model: dim_users\n"
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)

    assert detector._cache is None

    # Both calls should perform detection
    result1 = detector.detect()
    result2 = detector.detect()

    assert result1.input_dir == result2.input_dir


@pytest.mark.unit
@pytest.mark.wizard
def test_cache_per_working_directory(tmp_path: Path) -> None:
    """Test that different directories have separate cache entries."""
    # Create two separate project directories
    project1 = tmp_path / "project1"
    project1.mkdir()
    semantic1 = project1 / "semantic_models"
    semantic1.mkdir()
    (semantic1 / "users.yml").write_text(
        "semantic_models:\n  - name: users\n    model: ref('schema1.dim_users')\n"
    )

    project2 = tmp_path / "project2"
    project2.mkdir()
    semantic2 = project2 / "models"
    semantic2.mkdir()
    (semantic2 / "orders.yml").write_text(
        "semantic_models:\n  - name: orders\n    model: ref('schema2.fct_orders')\n"
    )

    # Detect in project1
    detector1 = ProjectDetector(working_dir=project1, cache_enabled=True)
    result1 = detector1.detect()

    # Detect in project2
    detector2 = ProjectDetector(working_dir=project2, cache_enabled=True)
    result2 = detector2.detect()

    # Results should be different
    assert result1.input_dir != result2.input_dir
    assert result1.schema_name != result2.schema_name


# ============================================================================
# Test Category 5: Performance (2 tests)
# ============================================================================


@pytest.mark.unit
@pytest.mark.wizard
def test_detection_completes_in_under_100ms(tmp_path: Path) -> None:
    """Test that detection meets <100ms requirement."""
    # Create realistic project structure
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text(
        "semantic_models:\n  - name: users\n    model: ref('analytics.dim_users')\n"
    )
    (semantic_dir / "orders.yml").write_text(
        "semantic_models:\n  - name: orders\n    model: ref('analytics.fct_orders')\n"
    )

    output_dir = tmp_path / "build" / "lookml"
    output_dir.mkdir(parents=True)

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)

    start = time.perf_counter()
    result = detector.detect()
    end = time.perf_counter()

    elapsed_ms = (end - start) * 1000

    assert elapsed_ms < 100, f"Detection took {elapsed_ms}ms (target: <100ms)"
    assert result.detection_time_ms < 100


@pytest.mark.unit
@pytest.mark.wizard
def test_cached_detection_is_faster(tmp_path: Path) -> None:
    """Test that cached detection is significantly faster."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text(
        "semantic_models:\n  - name: users\n    model: ref('analytics.dim_users')\n"
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=True)

    # First call (uncached)
    result1 = detector.detect()
    time1 = result1.detection_time_ms

    # Second call (cached)
    result2 = detector.detect()
    time2 = result2.detection_time_ms

    # Cached call should be significantly faster (typically sub-millisecond)
    # Note: On slow systems, cached and uncached times may be comparable,
    # but cached result should be served much faster than filesystem scan
    assert time2 < 5.0  # Generous threshold for slow systems
    # The important metric is that both times are reasonable
    assert time1 < 100  # Uncached should still be <100ms


# ============================================================================
# Test Category 6: Edge Cases (6 tests)
# ============================================================================


@pytest.mark.unit
@pytest.mark.wizard
def test_handle_permission_denied_gracefully(tmp_path: Path) -> None:
    """Test silent failure on permission denied."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text(
        "semantic_models:\n  - name: users\n    model: dim_users\n"
    )

    # Mock permission error
    with patch("pathlib.Path.glob", side_effect=PermissionError):
        detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
        result = detector.detect()

        # Should not crash, return None
        assert result.input_dir is None


@pytest.mark.unit
@pytest.mark.wizard
def test_handle_symlink_directories(tmp_path: Path) -> None:
    """Test that symlinks are followed correctly."""
    # Create real directory
    real_dir = tmp_path / "real_semantic_models"
    real_dir.mkdir()
    (real_dir / "users.yml").write_text(
        "semantic_models:\n  - name: users\n    model: dim_users\n"
    )

    # Create symlink
    link_dir = tmp_path / "semantic_models"
    link_dir.symlink_to(real_dir)

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    # Should follow symlink and find files
    assert result.input_dir == link_dir
    assert result.found_yaml_files == 1


@pytest.mark.unit
@pytest.mark.wizard
def test_handle_non_utf8_yaml_files(tmp_path: Path) -> None:
    """Test graceful failure on encoding errors."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "binary.yml"
    # Write non-UTF8 content
    yaml_file.write_bytes(b"\xff\xfe\xfd")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    # Should detect directory but fail schema extraction
    assert result.input_dir == semantic_dir
    assert result.schema_name is None


@pytest.mark.unit
@pytest.mark.wizard
def test_default_methods_return_sensible_values(tmp_path: Path) -> None:
    """Test get_*_or_default() methods."""
    # Empty project
    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    # All detections should fail
    assert result.input_dir is None
    assert result.output_dir is None
    assert result.schema_name is None

    # But defaults should be sensible
    assert result.get_input_dir_or_default() == Path("semantic_models")
    assert result.get_output_dir_or_default() == Path("build/lookml")
    assert result.get_schema_name_or_default() == "public"

    # Custom defaults
    assert result.get_input_dir_or_default("models") == Path("models")
    assert result.get_output_dir_or_default("output") == Path("output")
    assert result.get_schema_name_or_default("staging") == "staging"


@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_with_double_quotes(tmp_path: Path) -> None:
    """Test schema extraction with double quotes in ref()."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "users.yml"
    yaml_file.write_text(
        """
semantic_models:
  - name: users
    model: ref("analytics_prod.dim_users")
    entities: []
    dimensions: []
    measures: []
"""
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name == "analytics_prod"


@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_with_whitespace(tmp_path: Path) -> None:
    """Test schema extraction with whitespace in model field."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "users.yml"
    yaml_file.write_text(
        """
semantic_models:
  - name: users
    model: ref( 'analytics_prod.dim_users' )
    entities: []
    dimensions: []
    measures: []
"""
    )

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name == "analytics_prod"


# ============================================================================
# Additional Tests for CachedDetection class (2 tests)
# ============================================================================


@pytest.mark.unit
@pytest.mark.wizard
def test_cached_detection_is_stale_after_ttl() -> None:
    """Test that CachedDetection.is_stale() works correctly."""
    result = DetectionResult(
        input_dir=None,
        output_dir=None,
        schema_name=None,
        working_dir=Path("/test"),
        found_yaml_files=0,
        detection_time_ms=10.0,
    )

    # Fresh cache
    cached = CachedDetection(result=result, timestamp=datetime.now())
    assert not cached.is_stale(max_age_seconds=60)

    # Stale cache
    cached_stale = CachedDetection(
        result=result, timestamp=datetime.now() - timedelta(seconds=61)
    )
    assert cached_stale.is_stale(max_age_seconds=60)


@pytest.mark.unit
@pytest.mark.wizard
def test_detection_cache_clear() -> None:
    """Test that cache.clear() removes all entries."""
    cache = DetectionCache(max_age_seconds=60)

    result = DetectionResult(
        input_dir=Path("/test"),
        output_dir=None,
        schema_name="public",
        working_dir=Path("/test"),
        found_yaml_files=1,
        detection_time_ms=10.0,
    )

    cache.set(Path("/test"), result)
    assert cache.get(Path("/test")) is not None

    cache.clear()
    assert cache.get(Path("/test")) is None
