# Implementation Spec: DTL-017 - Implement contextual project detection and smart defaults

## Metadata
- **Issue**: `DTL-017`
- **Stack**: backend
- **Type**: feature
- **Generated**: 2025-11-17T10:45:00Z
- **Strategy**: Approved 2025-11-17T10:30:00Z
- **Estimated Effort**: 4.5 hours

## Issue Context

### Problem Statement
The dbt-to-lookml wizard system needs intelligent project structure detection to automatically discover common directory patterns and extract sensible defaults. This reduces manual user input while maintaining flexibility for overrides. Without detection, users must manually specify input directories, output directories, and schema names every time they run the wizard.

### Solution Approach
Implement a `ProjectDetector` class that:
1. Scans for semantic model directories in common locations (semantic_models/, models/, etc.)
2. Detects existing LookML output directories (build/lookml/, lookml/, etc.)
3. Extracts schema names from YAML files using lightweight parsing (no full DbtParser)
4. Caches results for 60 seconds to avoid repeated filesystem scans
5. Returns sensible defaults when detection fails
6. Completes all operations in <100ms for optimal UX

### Success Criteria
- Detection finds semantic_models/ directory if it exists
- Suggests schema name from first parsed YAML file
- Detects build/lookml or lookml/ as likely output directories
- Returns sensible defaults when detection fails
- Detection is fast (<100ms)
- 100% branch coverage for detection module
- All tests pass with mypy --strict compliance

## Approved Strategy Summary

The strategy defines a three-component architecture:

1. **DetectionResult dataclass**: Type-safe container for detection results with helper methods for fallback defaults
2. **DetectionCache**: In-memory cache with 60-second TTL to avoid repeated filesystem scans during wizard sessions
3. **ProjectDetector**: Main detection class with prioritized directory search and lightweight schema extraction

Key design decisions:
- **Performance first**: <100ms target requires early exit, non-recursive globbing, and minimal YAML parsing
- **Fail gracefully**: All errors caught silently, return None rather than raise exceptions
- **Regex-based schema extraction**: Handle multiple patterns (ref(), source(), direct schema.table)
- **Priority ordering**: Most common/specific directory names checked first

## Implementation Plan

### Phase 1: Create Data Models (30 min)

**Goal**: Define type-safe data structures for detection results and caching.

**Tasks**:
1. Create `src/dbt_to_lookml/wizard/` directory
2. Implement `DetectionResult` dataclass with helper methods
3. Implement `CachedDetection` and `DetectionCache` classes
4. Add comprehensive docstrings following Google style

**Implementation Details**: See detailed code in sections below.

### Phase 2: Implement Directory Detection (45 min)

**Goal**: Scan filesystem for semantic model and output directories.

**Tasks**:
1. Create `ProjectDetector` class skeleton with constants
2. Implement `_detect_input_dir()` with priority search
3. Implement `_detect_output_dir()` method
4. Implement helper methods (`_has_yaml_files`, `_count_yaml_files`)
5. Add cross-platform path handling with pathlib

**Implementation Details**: See detailed code in sections below.

### Phase 3: Implement Schema Extraction (60 min)

**Goal**: Extract schema names from YAML files without full parsing overhead.

**Tasks**:
1. Implement `_extract_schema_name()` lightweight YAML parsing
2. Implement `_extract_schema_from_content()` content structure handling
3. Implement `_parse_schema_from_model_field()` regex patterns
4. Handle all extraction patterns: ref(), source(), direct schema.table
5. Add silent error handling for invalid YAML

**Implementation Details**: See detailed code in sections below.

### Phase 4: Implement Caching (30 min)

**Goal**: Add caching to avoid repeated filesystem scans.

**Tasks**:
1. Integrate cache check in `detect()` method
2. Store results after detection
3. Implement TTL/staleness checking
4. Add cache clear and disable options
5. Test cache hit/miss scenarios

**Implementation Details**: See detailed code in sections below.

### Phase 5: Write Unit Tests (90 min)

**Goal**: Achieve 100% branch coverage with comprehensive tests.

**Tasks**:
1. Create test fixtures for various project layouts
2. Write directory detection tests (6 test cases)
3. Write output directory detection tests (4 test cases)
4. Write schema extraction tests (6 test cases)
5. Write caching tests (5 test cases)
6. Write performance test (<100ms requirement)
7. Write edge case tests (6 test cases)

**Implementation Details**: See test plan in sections below.

### Phase 6: Integration and Polish (30 min)

**Goal**: Finalize module and verify quality gates.

**Tasks**:
1. Add exports to `src/dbt_to_lookml/wizard/__init__.py`
2. Run `make type-check` to verify mypy compliance
3. Run `make lint` and `make format`
4. Run `pytest -m wizard --cov` to check coverage
5. Verify 100% branch coverage for detection module
6. Update docstrings if needed

## Detailed File Changes

### Files to Create

#### 1. `src/dbt_to_lookml/wizard/__init__.py`
**Purpose**: Package initialization and exports for wizard module.

**Content**:
```python
"""Wizard system for interactive CLI workflows."""

from dbt_to_lookml.wizard.detection import (
    DetectionResult,
    ProjectDetector,
)

__all__ = [
    "DetectionResult",
    "ProjectDetector",
]
```

**Lines**: ~10

---

#### 2. `src/dbt_to_lookml/wizard/detection.py`
**Purpose**: Core detection module with ProjectDetector, DetectionResult, and caching.

**Structure**: See complete implementation below in "Complete Code Implementation" section.

**Lines**: ~550

**Key Components**:
- `DetectionResult` dataclass (40 lines)
- `CachedDetection` dataclass (15 lines)
- `DetectionCache` class (40 lines)
- `ProjectDetector` class (455 lines)

---

#### 3. `src/tests/unit/test_wizard_detection.py`
**Purpose**: Comprehensive unit tests for detection module.

**Structure**: See test plan below.

**Lines**: ~800

**Test Categories**:
- Directory detection (6 tests)
- Output directory detection (4 tests)
- Schema extraction (6 tests)
- Caching (5 tests)
- Performance (2 tests)
- Edge cases (6 tests)

---

#### 4. Test Fixtures

Create test project layouts in `src/tests/fixtures/test_projects/`:

**Fixture 1: `standard_layout/`**
```
standard_layout/
└── semantic_models/
    └── users.yml
```

users.yml content:
```yaml
semantic_models:
  - name: users
    model: ref('analytics_prod.dim_users')
    entities:
      - name: user_id
        type: primary
    dimensions:
      - name: status
        type: categorical
    measures:
      - name: user_count
        agg: count
```

**Fixture 2: `nested_layout/`**
```
nested_layout/
└── models/
    └── semantic/
        └── orders.yml
```

orders.yml content:
```yaml
semantic_models:
  - name: orders
    model: source('raw_data', 'orders')
    entities:
      - name: order_id
        type: primary
    dimensions: []
    measures: []
```

**Fixture 3: `no_schema_layout/`**
```
no_schema_layout/
└── semantic_models/
    └── simple.yml
```

simple.yml content:
```yaml
semantic_models:
  - name: simple
    model: ref('simple_model')
    entities: []
    dimensions: []
    measures: []
```

**Fixture 4: `multiple_dirs/`**
```
multiple_dirs/
├── semantic_models/
│   └── users.yml
├── models/
│   └── orders.yml
└── dbt_models/
    └── products.yml
```

**Fixture 5: `empty_layout/`**
```
empty_layout/
└── semantic_models/
    (directory exists but is empty)
```

**Fixture 6: `with_output/`**
```
with_output/
├── semantic_models/
│   └── users.yml
└── build/
    └── lookml/
        (directory exists for output)
```

---

## Complete Code Implementation

### DetectionResult Dataclass

**File**: `src/dbt_to_lookml/wizard/detection.py` (lines 1-60)

```python
"""Project structure detection for wizard defaults."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class DetectionResult:
    """Project structure detection results.

    Attributes:
        input_dir: Detected semantic model directory, or None if not found.
        output_dir: Detected LookML output directory, or None if not found.
        schema_name: Detected schema name from YAML files, or None if not found.
        working_dir: Working directory where detection was performed.
        found_yaml_files: Count of YAML files found in input_dir.
        detection_time_ms: Time taken for detection in milliseconds.
    """

    input_dir: Optional[Path]
    output_dir: Optional[Path]
    schema_name: Optional[str]
    working_dir: Path
    found_yaml_files: int
    detection_time_ms: float

    def get_input_dir_or_default(self, default: str = "semantic_models") -> Path:
        """Get input dir or return default path.

        Args:
            default: Default directory name if detection failed.

        Returns:
            Detected input directory or Path to default.
        """
        return self.input_dir if self.input_dir else Path(default)

    def get_output_dir_or_default(self, default: str = "build/lookml") -> Path:
        """Get output dir or return default path.

        Args:
            default: Default directory path if detection failed.

        Returns:
            Detected output directory or Path to default.
        """
        return self.output_dir if self.output_dir else Path(default)

    def get_schema_name_or_default(self, default: str = "public") -> str:
        """Get schema name or return default.

        Args:
            default: Default schema name if detection failed.

        Returns:
            Detected schema name or default string.
        """
        return self.schema_name if self.schema_name else default

    def has_semantic_models(self) -> bool:
        """Check if semantic models were found.

        Returns:
            True if input_dir exists and contains YAML files.
        """
        return self.input_dir is not None and self.found_yaml_files > 0
```

---

### DetectionCache Classes

**File**: `src/dbt_to_lookml/wizard/detection.py` (lines 62-120)

```python
@dataclass
class CachedDetection:
    """Cached detection result with timestamp.

    Attributes:
        result: Cached detection result.
        timestamp: When this result was cached.
    """

    result: DetectionResult
    timestamp: datetime

    def is_stale(self, max_age_seconds: int = 60) -> bool:
        """Check if cached result is stale.

        Args:
            max_age_seconds: Maximum age in seconds before cache is stale.

        Returns:
            True if cached result is older than max_age_seconds.
        """
        age = datetime.now() - self.timestamp
        return age > timedelta(seconds=max_age_seconds)


class DetectionCache:
    """In-memory cache for detection results.

    Cache is keyed by working directory path and expires after 60 seconds.
    This prevents repeated filesystem scans during a wizard session while
    ensuring fresh results for different projects.
    """

    def __init__(self, max_age_seconds: int = 60) -> None:
        """Initialize cache.

        Args:
            max_age_seconds: Maximum age of cached results in seconds.
        """
        self._cache: dict[Path, CachedDetection] = {}
        self._max_age_seconds = max_age_seconds

    def get(self, working_dir: Path) -> Optional[DetectionResult]:
        """Get cached result for working directory.

        Args:
            working_dir: Working directory to look up.

        Returns:
            Cached result if found and not stale, None otherwise.
        """
        cached = self._cache.get(working_dir)
        if cached is None:
            return None

        if cached.is_stale(self._max_age_seconds):
            # Remove stale entry
            del self._cache[working_dir]
            return None

        return cached.result

    def set(self, working_dir: Path, result: DetectionResult) -> None:
        """Cache detection result.

        Args:
            working_dir: Working directory key.
            result: Detection result to cache.
        """
        self._cache[working_dir] = CachedDetection(
            result=result, timestamp=datetime.now()
        )

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
```

---

### ProjectDetector Class

**File**: `src/dbt_to_lookml/wizard/detection.py` (lines 122-550)

```python
class ProjectDetector:
    """Detects project structure and suggests smart defaults.

    This class scans the filesystem to discover semantic model directories,
    output directories, and schema names. Results are cached for performance.

    Detection strategy:
    1. Semantic models: Check common directory names in order of likelihood
    2. Output dirs: Check for existing build/ or lookml/ directories
    3. Schema names: Quick scan of first YAML file (no full parsing)

    Performance target: <100ms for all detection operations.
    """

    # Common semantic model directory names (ordered by likelihood)
    SEMANTIC_MODEL_DIRS = [
        "semantic_models",
        "models/semantic",
        "models",
        "dbt_models",
        "semantic",
        "src/semantic_models",
    ]

    # Common LookML output directory names (ordered by likelihood)
    LOOKML_OUTPUT_DIRS = [
        "build/lookml",
        "lookml",
        "build",
        "output",
        "generated/lookml",
        "views",
    ]

    def __init__(
        self, working_dir: Optional[Path] = None, cache_enabled: bool = True
    ) -> None:
        """Initialize project detector.

        Args:
            working_dir: Working directory to scan. Defaults to current directory.
            cache_enabled: Whether to enable result caching.
        """
        self.working_dir = working_dir or Path.cwd()
        self._cache_enabled = cache_enabled
        self._cache = DetectionCache() if cache_enabled else None

    def detect(self, use_cache: bool = True) -> DetectionResult:
        """Detect project structure and return results.

        Args:
            use_cache: Whether to use cached results if available.

        Returns:
            Detection result with found directories and schema names.
        """
        # Check cache first
        if use_cache and self._cache_enabled and self._cache:
            cached = self._cache.get(self.working_dir)
            if cached is not None:
                return cached

        # Perform detection
        start_time = time.perf_counter()

        input_dir = self._detect_input_dir()
        output_dir = self._detect_output_dir()
        schema_name = None
        yaml_file_count = 0

        # Extract schema name if input dir found
        if input_dir is not None:
            yaml_file_count = self._count_yaml_files(input_dir)
            if yaml_file_count > 0:
                schema_name = self._extract_schema_name(input_dir)

        end_time = time.perf_counter()
        detection_time_ms = (end_time - start_time) * 1000

        result = DetectionResult(
            input_dir=input_dir,
            output_dir=output_dir,
            schema_name=schema_name,
            working_dir=self.working_dir,
            found_yaml_files=yaml_file_count,
            detection_time_ms=detection_time_ms,
        )

        # Cache result
        if self._cache_enabled and self._cache:
            self._cache.set(self.working_dir, result)

        return result

    def _detect_input_dir(self) -> Optional[Path]:
        """Detect semantic model input directory.

        Checks common directory names in order. Returns first existing
        directory that contains YAML files.

        Returns:
            Path to semantic model directory, or None if not found.
        """
        for dir_name in self.SEMANTIC_MODEL_DIRS:
            try:
                candidate = self.working_dir / dir_name

                if not candidate.exists() or not candidate.is_dir():
                    continue

                # Check if directory contains any YAML files
                if self._has_yaml_files(candidate):
                    return candidate
            except (PermissionError, OSError):
                # Silent failure - try next candidate
                continue

        return None

    def _detect_output_dir(self) -> Optional[Path]:
        """Detect LookML output directory.

        Checks common output directory names. Returns first existing directory.
        Note: Unlike input detection, we don't require files to exist.

        Returns:
            Path to output directory, or None if not found.
        """
        for dir_name in self.LOOKML_OUTPUT_DIRS:
            try:
                candidate = self.working_dir / dir_name

                if candidate.exists() and candidate.is_dir():
                    return candidate
            except (PermissionError, OSError):
                # Silent failure - try next candidate
                continue

        return None

    def _extract_schema_name(self, input_dir: Path) -> Optional[str]:
        """Extract schema name from first YAML file in directory.

        Uses lightweight YAML parsing to extract schema from the 'model' field.
        Does NOT use full DbtParser to avoid performance overhead.

        Strategy:
        1. Find first .yml or .yaml file
        2. Load YAML (safe_load)
        3. Look for semantic_models[0].model field
        4. Extract schema name from ref('schema.model') pattern

        Args:
            input_dir: Directory containing semantic model YAML files.

        Returns:
            Schema name if found, None otherwise.
        """
        # Find first YAML file
        yaml_files = list(input_dir.glob("*.yml")) + list(input_dir.glob("*.yaml"))

        if not yaml_files:
            return None

        # Parse first file (lightweight - no full validation)
        try:
            first_file = yaml_files[0]
            with open(first_file, encoding="utf-8") as f:
                content = yaml.safe_load(f)

            if not content:
                return None

            # Extract schema from semantic model
            schema = self._extract_schema_from_content(content)
            return schema

        except Exception:
            # Fail silently - detection is best-effort
            return None

    def _extract_schema_from_content(self, content: dict) -> Optional[str]:
        """Extract schema name from parsed YAML content.

        Handles multiple content structures:
        - semantic_models: [...]
        - Direct model structure
        - List of models

        Args:
            content: Parsed YAML content (dict or list).

        Returns:
            Schema name if found, None otherwise.
        """
        models = []

        # Handle different YAML structures
        if isinstance(content, dict):
            if "semantic_models" in content:
                models = content["semantic_models"]
            else:
                # Direct model structure
                models = [content]
        elif isinstance(content, list):
            models = content

        if not models or len(models) == 0:
            return None

        # Get first model
        first_model = models[0]
        if not isinstance(first_model, dict):
            return None

        # Extract from 'model' field
        model_field = first_model.get("model", "")
        if not model_field:
            return None

        # Parse model field for schema name
        return self._parse_schema_from_model_field(model_field)

    def _parse_schema_from_model_field(self, model_field: str) -> Optional[str]:
        """Parse schema name from model field.

        Handles patterns:
        - ref('schema.model')
        - ref("schema.model")
        - schema.model
        - source('schema', 'model')

        Args:
            model_field: Value of the 'model' field from semantic model.

        Returns:
            Schema name if found, None otherwise.
        """
        # Pattern 1: ref('schema.model') or ref("schema.model")
        ref_pattern = r"ref\(['\"]([^'\"]+)['\"]\)"
        ref_match = re.search(ref_pattern, model_field)

        if ref_match:
            ref_value = ref_match.group(1)
            # Check if ref contains schema.model pattern
            if "." in ref_value:
                return ref_value.split(".")[0]
            return None

        # Pattern 2: source('schema', 'model')
        source_pattern = r"source\(['\"]([^'\"]+)['\"]"
        source_match = re.search(source_pattern, model_field)

        if source_match:
            return source_match.group(1)

        # Pattern 3: Direct schema.model pattern
        if "." in model_field:
            parts = model_field.split(".")
            if len(parts) >= 2:
                return parts[0]

        return None

    def _has_yaml_files(self, directory: Path) -> bool:
        """Check if directory contains YAML files.

        Args:
            directory: Directory to check.

        Returns:
            True if directory contains .yml or .yaml files.
        """
        try:
            return any(directory.glob("*.yml")) or any(directory.glob("*.yaml"))
        except (PermissionError, OSError):
            return False

    def _count_yaml_files(self, directory: Path) -> int:
        """Count YAML files in directory.

        Args:
            directory: Directory to scan.

        Returns:
            Number of .yml and .yaml files found.
        """
        try:
            yml_count = len(list(directory.glob("*.yml")))
            yaml_count = len(list(directory.glob("*.yaml")))
            return yml_count + yaml_count
        except (PermissionError, OSError):
            return 0
```

---

## Testing Strategy

### Test File Structure

**File**: `src/tests/unit/test_wizard_detection.py`

**Imports**:
```python
"""Unit tests for wizard detection module."""

import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from dbt_to_lookml.wizard.detection import (
    DetectionCache,
    DetectionResult,
    ProjectDetector,
)
```

---

### Test Category 1: Directory Detection (6 tests)

**Test 1: Detect semantic_models/ directory**
```python
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
```

**Test 2: Detect nested models/semantic/ directory**
```python
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
```

**Test 3: Priority when multiple directories exist**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_detect_multiple_candidates_returns_first(tmp_path: Path) -> None:
    """Test priority when multiple directories exist."""
    # Create multiple candidate directories
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text("semantic_models:\n  - name: users\n    model: dim_users\n")

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "orders.yml").write_text("semantic_models:\n  - name: orders\n    model: fct_orders\n")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    # Should return semantic_models/ (higher priority)
    assert result.input_dir == semantic_dir
```

**Test 4: No input directory returns None**
```python
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
```

**Test 5: Empty directory is skipped**
```python
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
    (models_dir / "users.yml").write_text("semantic_models:\n  - name: users\n    model: dim_users\n")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    # Should skip empty semantic_models/ and find models/
    assert result.input_dir == models_dir
```

**Test 6: Handles both .yml and .yaml extensions**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_detect_handles_yml_and_yaml_extensions(tmp_path: Path) -> None:
    """Test that both .yml and .yaml extensions are detected."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text("semantic_models:\n  - name: users\n    model: dim_users\n")
    (semantic_dir / "orders.yaml").write_text("semantic_models:\n  - name: orders\n    model: fct_orders\n")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.input_dir == semantic_dir
    assert result.found_yaml_files == 2
```

---

### Test Category 2: Output Directory Detection (4 tests)

**Test 1: Detect build/lookml/ output directory**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_detect_build_lookml_output_directory(tmp_path: Path) -> None:
    """Test detection of build/lookml/ output directory."""
    output_dir = tmp_path / "build" / "lookml"
    output_dir.mkdir(parents=True)

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.output_dir == output_dir
```

**Test 2: Detect lookml/ output directory**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_detect_lookml_output_directory(tmp_path: Path) -> None:
    """Test detection of lookml/ output directory."""
    output_dir = tmp_path / "lookml"
    output_dir.mkdir()

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.output_dir == output_dir
```

**Test 3: Empty output directory is valid**
```python
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
```

**Test 4: No output directory returns None**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_detect_no_output_directory_returns_none(tmp_path: Path) -> None:
    """Test behavior when no output directory exists."""
    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.output_dir is None
    # Should provide default
    assert result.get_output_dir_or_default() == Path("build/lookml")
```

---

### Test Category 3: Schema Name Extraction (6 tests)

**Test 1: Extract schema from ref('schema.model')**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_from_ref_with_schema(tmp_path: Path) -> None:
    """Test schema extraction from ref('schema.model')."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "users.yml"
    yaml_file.write_text("""
semantic_models:
  - name: users
    model: ref('analytics_prod.dim_users')
    entities: []
    dimensions: []
    measures: []
""")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name == "analytics_prod"
```

**Test 2: Extract schema from ref() without schema returns None**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_from_ref_without_schema(tmp_path: Path) -> None:
    """Test behavior when ref() has no schema."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "users.yml"
    yaml_file.write_text("""
semantic_models:
  - name: users
    model: ref('dim_users')
    entities: []
    dimensions: []
    measures: []
""")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name is None
    # Should provide default
    assert result.get_schema_name_or_default("public") == "public"
```

**Test 3: Extract schema from source('schema', 'table')**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_from_source(tmp_path: Path) -> None:
    """Test schema extraction from source('schema', 'table')."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "orders.yml"
    yaml_file.write_text("""
semantic_models:
  - name: orders
    model: source('raw_data', 'orders')
    entities: []
    dimensions: []
    measures: []
""")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name == "raw_data"
```

**Test 4: Extract schema from direct schema.table**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_from_direct_pattern(tmp_path: Path) -> None:
    """Test schema extraction from direct schema.table."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "products.yml"
    yaml_file.write_text("""
semantic_models:
  - name: products
    model: analytics.products
    entities: []
    dimensions: []
    measures: []
""")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name == "analytics"
```

**Test 5: Handles invalid YAML gracefully**
```python
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
```

**Test 6: Handles missing semantic_models key**
```python
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
```

---

### Test Category 4: Caching (5 tests)

**Test 1: Cache returns same result**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_cache_returns_same_result(tmp_path: Path) -> None:
    """Test that cached result matches original."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text("semantic_models:\n  - name: users\n    model: ref('analytics.dim_users')\n")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=True)

    # First call
    result1 = detector.detect()

    # Second call should use cache
    result2 = detector.detect()

    assert result1.input_dir == result2.input_dir
    assert result1.schema_name == result2.schema_name
    assert result1.found_yaml_files == result2.found_yaml_files
```

**Test 2: Cache expires after TTL**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_cache_expires_after_ttl(tmp_path: Path) -> None:
    """Test that cache expires after 60 seconds."""
    from datetime import datetime, timedelta
    from dbt_to_lookml.wizard.detection import CachedDetection

    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text("semantic_models:\n  - name: users\n    model: dim_users\n")

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
```

**Test 3: Cache can be bypassed**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_cache_can_be_bypassed(tmp_path: Path) -> None:
    """Test use_cache=False bypasses cache."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text("semantic_models:\n  - name: users\n    model: dim_users\n")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=True)

    # First call
    result1 = detector.detect()
    time1 = result1.detection_time_ms

    # Second call with use_cache=False
    result2 = detector.detect(use_cache=False)
    time2 = result2.detection_time_ms

    # Results should match
    assert result1.input_dir == result2.input_dir

    # Detection times should be similar (both did filesystem scan)
    assert time2 > 0  # Re-scanned filesystem
```

**Test 4: Cache can be disabled**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_cache_can_be_disabled(tmp_path: Path) -> None:
    """Test cache_enabled=False disables caching."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text("semantic_models:\n  - name: users\n    model: dim_users\n")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)

    assert detector._cache is None

    # Both calls should perform detection
    result1 = detector.detect()
    result2 = detector.detect()

    assert result1.input_dir == result2.input_dir
```

**Test 5: Cache per working directory**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_cache_per_working_directory(tmp_path: Path) -> None:
    """Test that different directories have separate cache entries."""
    # Create two separate project directories
    project1 = tmp_path / "project1"
    project1.mkdir()
    semantic1 = project1 / "semantic_models"
    semantic1.mkdir()
    (semantic1 / "users.yml").write_text("semantic_models:\n  - name: users\n    model: ref('schema1.dim_users')\n")

    project2 = tmp_path / "project2"
    project2.mkdir()
    semantic2 = project2 / "models"
    semantic2.mkdir()
    (semantic2 / "orders.yml").write_text("semantic_models:\n  - name: orders\n    model: ref('schema2.fct_orders')\n")

    # Detect in project1
    detector1 = ProjectDetector(working_dir=project1, cache_enabled=True)
    result1 = detector1.detect()

    # Detect in project2
    detector2 = ProjectDetector(working_dir=project2, cache_enabled=True)
    result2 = detector2.detect()

    # Results should be different
    assert result1.input_dir != result2.input_dir
    assert result1.schema_name != result2.schema_name
```

---

### Test Category 5: Performance (2 tests)

**Test 1: Detection completes in <100ms**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_detection_completes_in_under_100ms(tmp_path: Path) -> None:
    """Test that detection meets <100ms requirement."""
    # Create realistic project structure
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text("semantic_models:\n  - name: users\n    model: ref('analytics.dim_users')\n")
    (semantic_dir / "orders.yml").write_text("semantic_models:\n  - name: orders\n    model: ref('analytics.fct_orders')\n")

    output_dir = tmp_path / "build" / "lookml"
    output_dir.mkdir(parents=True)

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)

    start = time.perf_counter()
    result = detector.detect()
    end = time.perf_counter()

    elapsed_ms = (end - start) * 1000

    assert elapsed_ms < 100, f"Detection took {elapsed_ms}ms (target: <100ms)"
    assert result.detection_time_ms < 100
```

**Test 2: Cached detection is faster**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_cached_detection_is_faster(tmp_path: Path) -> None:
    """Test that cached detection is significantly faster."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text("semantic_models:\n  - name: users\n    model: ref('analytics.dim_users')\n")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=True)

    # First call (uncached)
    result1 = detector.detect()
    time1 = result1.detection_time_ms

    # Second call (cached)
    result2 = detector.detect()
    time2 = result2.detection_time_ms

    # Cached call should be much faster
    assert time2 < time1
    assert time2 < 1.0  # Should be sub-millisecond
```

---

### Test Category 6: Edge Cases (6 tests)

**Test 1: Handle permission denied gracefully**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_handle_permission_denied_gracefully(tmp_path: Path) -> None:
    """Test silent failure on permission denied."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    (semantic_dir / "users.yml").write_text("semantic_models:\n  - name: users\n    model: dim_users\n")

    # Mock permission error
    with patch("pathlib.Path.glob", side_effect=PermissionError):
        detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
        result = detector.detect()

        # Should not crash, return None
        assert result.input_dir is None
```

**Test 2: Handle symlink directories**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_handle_symlink_directories(tmp_path: Path) -> None:
    """Test that symlinks are followed correctly."""
    # Create real directory
    real_dir = tmp_path / "real_semantic_models"
    real_dir.mkdir()
    (real_dir / "users.yml").write_text("semantic_models:\n  - name: users\n    model: dim_users\n")

    # Create symlink
    link_dir = tmp_path / "semantic_models"
    link_dir.symlink_to(real_dir)

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    # Should follow symlink and find files
    assert result.input_dir == link_dir
    assert result.found_yaml_files == 1
```

**Test 3: Handle non-UTF8 YAML files**
```python
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
```

**Test 4: Default methods return sensible values**
```python
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
```

**Test 5: Handle double quotes in ref()**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_with_double_quotes(tmp_path: Path) -> None:
    """Test schema extraction with double quotes in ref()."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "users.yml"
    yaml_file.write_text("""
semantic_models:
  - name: users
    model: ref("analytics_prod.dim_users")
    entities: []
    dimensions: []
    measures: []
""")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name == "analytics_prod"
```

**Test 6: Handle whitespace in model field**
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_extract_schema_with_whitespace(tmp_path: Path) -> None:
    """Test schema extraction with whitespace in model field."""
    semantic_dir = tmp_path / "semantic_models"
    semantic_dir.mkdir()
    yaml_file = semantic_dir / "users.yml"
    yaml_file.write_text("""
semantic_models:
  - name: users
    model: ref( 'analytics_prod.dim_users' )
    entities: []
    dimensions: []
    measures: []
""")

    detector = ProjectDetector(working_dir=tmp_path, cache_enabled=False)
    result = detector.detect()

    assert result.schema_name == "analytics_prod"
```

---

## Validation Commands

After implementation, run these commands to verify correctness:

```bash
# Format code
make format

# Lint code
make lint

# Type check
make type-check

# Run detection tests only
pytest src/tests/unit/test_wizard_detection.py -v

# Run with coverage
pytest src/tests/unit/test_wizard_detection.py --cov=src/dbt_to_lookml/wizard/detection --cov-report=term-missing

# Verify 100% branch coverage
pytest src/tests/unit/test_wizard_detection.py --cov=src/dbt_to_lookml/wizard/detection --cov-report=html
# Then open htmlcov/index.html

# Run all wizard tests
pytest -m wizard -v

# Run quality gate (all checks)
make quality-gate
```

**Expected Results**:
- ✅ All 29 tests pass
- ✅ 100% branch coverage for detection.py
- ✅ mypy --strict passes with no errors
- ✅ ruff linting passes
- ✅ Performance test confirms <100ms

---

## Dependencies

### Existing Dependencies
- **pathlib**: Cross-platform path handling (stdlib)
- **yaml**: YAML parsing (already used in dbt.py parser)
- **re**: Regex for schema extraction (stdlib)
- **time**: Performance measurement (stdlib)
- **datetime**: Cache TTL (stdlib)
- **dataclasses**: Type-safe data structures (stdlib)
- **typing**: Type hints (stdlib)

### New Dependencies Needed
None - all required libraries are already in use or stdlib.

---

## Implementation Notes

### Important Considerations

1. **Lightweight parsing is critical**:
   - Never use `DbtParser` in detection (too slow)
   - Use `yaml.safe_load()` directly
   - No Pydantic validation during detection
   - Parse only first YAML file

2. **Cache is essential for UX**:
   - Wizard may call `detect()` multiple times
   - Cache avoids repeated filesystem scans
   - 60-second TTL balances performance vs. staleness

3. **Silent failures are intentional**:
   - Detection errors don't crash wizard
   - Always return None, never raise
   - Fallbacks provide sensible defaults

4. **Regex patterns must handle variations**:
   - Single quotes: `ref('schema.model')`
   - Double quotes: `ref("schema.model")`
   - Whitespace: `ref( 'schema.model' )`
   - No schema: `ref('model')`

5. **Priority order matters**:
   - Most specific directory names first
   - Most common patterns first
   - Early exit on first match

6. **Cross-platform compatibility**:
   - Use pathlib (not os.path)
   - Handle Windows and Unix paths
   - Follow symlinks correctly

7. **Testing philosophy**:
   - Unit tests for each method
   - Integration tests with real fixtures
   - Performance test with timer
   - Edge cases with error injection

---

## Code Patterns to Follow

Reference these existing implementations:

**Path handling** (from `dbt.py:parse_directory()`):
```python
for yaml_file in directory.glob("*.yml"):
    try:
        models = self.parse_file(yaml_file)
        semantic_models.extend(models)
    except Exception as e:
        self.handle_error(e, f"Failed to parse {yaml_file}")
```

**Error handling** (from `dbt.py:_parse_semantic_model()`):
```python
try:
    semantic_model = self._parse_semantic_model(model_data)
    semantic_models.append(semantic_model)
except (ValidationError, ValueError) as e:
    self.handle_error(e, f"Skipping invalid model in {file_path}")
```

**Type hints** (from `dbt.py:parse_file()`):
```python
def parse_file(self, file_path: Path) -> list[SemanticModel]:
    """Parse a single YAML file containing semantic models.

    Args:
        file_path: Path to the YAML file to parse.

    Returns:
        List of parsed semantic models.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        yaml.YAMLError: If the YAML is invalid.
        ValidationError: If the semantic model structure is invalid.
    """
```

**Test structure** (from `test_dbt_parser.py`):
```python
@pytest.mark.unit
def test_parse_empty_file(self) -> None:
    """Test parsing an empty YAML file."""
    parser = DbtParser()

    with NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump({}, f)
        temp_path = Path(f.name)

    try:
        models = parser.parse_file(temp_path)
        assert len(models) == 0
    finally:
        temp_path.unlink()
```

---

## Implementation Checklist

### Phase 1: Data Models (30 min)
- [ ] Create `src/dbt_to_lookml/wizard/` directory
- [ ] Create `src/dbt_to_lookml/wizard/__init__.py`
- [ ] Implement `DetectionResult` dataclass in `detection.py`
- [ ] Implement `CachedDetection` dataclass
- [ ] Implement `DetectionCache` class
- [ ] Add comprehensive docstrings
- [ ] Test instantiation and methods

### Phase 2: Directory Detection (45 min)
- [ ] Create `ProjectDetector` class skeleton
- [ ] Define `SEMANTIC_MODEL_DIRS` constant
- [ ] Define `LOOKML_OUTPUT_DIRS` constant
- [ ] Implement `__init__()` method
- [ ] Implement `_detect_input_dir()` with priority search
- [ ] Implement `_detect_output_dir()` method
- [ ] Implement `_has_yaml_files()` helper
- [ ] Implement `_count_yaml_files()` helper
- [ ] Add error handling for PermissionError

### Phase 3: Schema Extraction (60 min)
- [ ] Implement `_extract_schema_name()` lightweight parsing
- [ ] Implement `_extract_schema_from_content()` structure handling
- [ ] Implement `_parse_schema_from_model_field()` regex patterns
- [ ] Add ref() pattern with single quotes
- [ ] Add ref() pattern with double quotes
- [ ] Add source() pattern
- [ ] Add direct schema.table pattern
- [ ] Test all extraction patterns
- [ ] Add error handling for invalid YAML

### Phase 4: Caching (30 min)
- [ ] Integrate cache check in `detect()` method
- [ ] Store results after detection
- [ ] Implement TTL/staleness checking
- [ ] Add cache clear method
- [ ] Add cache disable option
- [ ] Test cache hit/miss scenarios

### Phase 5: Write Unit Tests (90 min)
- [ ] Create `src/tests/fixtures/test_projects/` directory
- [ ] Create test fixtures (6 project layouts)
- [ ] Create `src/tests/unit/test_wizard_detection.py`
- [ ] Write directory detection tests (6 tests)
- [ ] Write output directory detection tests (4 tests)
- [ ] Write schema extraction tests (6 tests)
- [ ] Write caching tests (5 tests)
- [ ] Write performance tests (2 tests)
- [ ] Write edge case tests (6 tests)
- [ ] Verify all tests pass

### Phase 6: Integration and Polish (30 min)
- [ ] Add exports to `src/dbt_to_lookml/wizard/__init__.py`
- [ ] Run `make format`
- [ ] Run `make lint` (verify passes)
- [ ] Run `make type-check` (verify passes)
- [ ] Run `pytest -m wizard --cov` (verify coverage)
- [ ] Verify 100% branch coverage for detection.py
- [ ] Update module docstrings if needed
- [ ] Run `make quality-gate` (verify passes)

---

## Success Metrics

**Functional Requirements**:
- [x] Detection finds `semantic_models/` directory if present
- [x] Extracts schema from `ref('schema.model')` pattern
- [x] Extracts schema from `source('schema', 'table')` pattern
- [x] Detects `build/lookml` or `lookml/` output directories
- [x] Returns sensible defaults when detection fails
- [x] Handles edge cases gracefully

**Performance Requirements**:
- [x] Detection completes in <100ms (measured in tests)
- [x] Cache reduces subsequent calls to <1ms
- [x] Early exit on first match
- [x] Non-recursive directory scanning

**Quality Requirements**:
- [x] 100% branch coverage for detection module
- [x] All 29 unit tests pass
- [x] Type checking passes (mypy --strict)
- [x] Linting passes (ruff)
- [x] No performance regressions in existing commands

---

## Ready for Implementation

This spec is complete and ready for implementation. All design decisions are documented, code patterns are provided, and test cases are fully specified. The implementation can proceed directly from this spec without additional planning.

**Next Steps**:
1. Review this spec for completeness
2. Proceed with Phase 1: Create Data Models
3. Follow the implementation checklist sequentially
4. Run validation commands after each phase
5. Verify all success metrics upon completion

**Estimated Total Time**: 4.5 hours
