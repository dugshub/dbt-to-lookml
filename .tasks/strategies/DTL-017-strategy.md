# Implementation Strategy: DTL-017

**Issue**: DTL-017 - Implement contextual project detection and smart defaults
**Analyzed**: 2025-11-17T10:30:00Z
**Stack**: backend
**Type**: feature

## Approach

Add intelligent project structure detection to automatically discover common directory patterns and extract sensible defaults for wizard prompts. This detection system will:

1. Scan the working directory for semantic model files in common locations
2. Detect likely output directories for LookML generation
3. Extract schema names from existing YAML files without full parsing
4. Cache detection results for performance (<100ms requirement)
5. Return fallback defaults when detection fails
6. Handle edge cases gracefully (multiple candidates, missing files)

This detection module serves as the intelligence layer for DTL-018 (prompt-based wizard), providing smart defaults that reduce user input while maintaining flexibility for overrides.

## Architecture Impact

**Layer**: CLI Infrastructure / Wizard System

**New Module Structure**:
```
src/dbt_to_lookml/wizard/
├── __init__.py           # Existing (DTL-015)
├── base.py              # Existing (DTL-015)
├── types.py             # Existing (DTL-015)
└── detection.py         # NEW - Project structure detection
```

**New Files**:
- `src/dbt_to_lookml/wizard/detection.py`: Detection module with caching
- `src/tests/unit/test_wizard_detection.py`: Unit tests for detection logic
- `src/tests/fixtures/test_projects/`: Test fixtures for various project layouts

**Modified Files**:
- `src/dbt_to_lookml/wizard/__init__.py`: Export ProjectDetector class

**No changes to**:
- Existing parsers (detection is read-only and lightweight)
- Existing generators (detection is CLI-only)
- Core schemas or types

## Dependencies

- **Depends on**: DTL-015 (wizard base infrastructure must exist)

- **Blocking**:
  - DTL-018 (prompt-based wizard needs detection for defaults)
  - DTL-019 (validation preview may use detected paths)

- **Related to**:
  - DTL-014 (parent epic)
  - Parser interface patterns (for schema name extraction strategy)

## Detailed Implementation Plan

### 1. Detection Module Design

#### Module: src/dbt_to_lookml/wizard/detection.py

**Core Responsibilities**:
1. Discover semantic model directories
2. Detect LookML output directories
3. Extract schema names from YAML files
4. Cache results for performance
5. Handle edge cases with fallback defaults

**Key Design Principles**:
- **Fast**: All detection operations complete in <100ms
- **Read-only**: Never modifies files or directories
- **Lenient**: Returns sensible defaults on failure
- **Cached**: Results cached per working directory
- **Cross-platform**: Uses pathlib for path handling

**Type safety**:
- All methods have explicit type hints
- Returns typed data classes (not plain dicts)
- Uses Optional for nullable values
- Mypy strict mode compliant

#### Data Models

**DetectionResult** (dataclass for type safety):
```python
"""Result of project structure detection."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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

**DetectionCache** (internal class for caching):
```python
"""Cache for detection results to avoid repeated filesystem scans."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


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
            result=result,
            timestamp=datetime.now()
        )

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
```

#### ProjectDetector Class

**Main detection class**:
```python
"""Project structure detection for wizard defaults."""

import time
from pathlib import Path
from typing import Optional

import yaml


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
        self,
        working_dir: Optional[Path] = None,
        cache_enabled: bool = True
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
            candidate = self.working_dir / dir_name

            if not candidate.exists() or not candidate.is_dir():
                continue

            # Check if directory contains any YAML files
            if self._has_yaml_files(candidate):
                return candidate

        return None

    def _detect_output_dir(self) -> Optional[Path]:
        """Detect LookML output directory.

        Checks common output directory names. Returns first existing directory.
        Note: Unlike input detection, we don't require files to exist.

        Returns:
            Path to output directory, or None if not found.
        """
        for dir_name in self.LOOKML_OUTPUT_DIRS:
            candidate = self.working_dir / dir_name

            if candidate.exists() and candidate.is_dir():
                return candidate

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
        # Patterns:
        # - "ref('schema.model')" -> "schema"
        # - "ref('model')" -> None (no schema)
        # - "schema.model" -> "schema"
        # - "model" -> None

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
        import re

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
        return any(directory.glob("*.yml")) or any(directory.glob("*.yaml"))

    def _count_yaml_files(self, directory: Path) -> int:
        """Count YAML files in directory.

        Args:
            directory: Directory to scan.

        Returns:
            Number of .yml and .yaml files found.
        """
        yml_count = len(list(directory.glob("*.yml")))
        yaml_count = len(list(directory.glob("*.yaml")))
        return yml_count + yaml_count
```

**Key Implementation Notes**:
1. **Ordered search**: Check most common directory names first for performance
2. **Lazy evaluation**: Stop searching once a valid directory is found
3. **Lightweight parsing**: Extract schema without full semantic model parsing
4. **Regex patterns**: Handle multiple ref() and source() syntax variations
5. **Silent failures**: Detection errors don't raise exceptions (best-effort)

### 2. Semantic Model Directory Detection

**Strategy**:
- Check directories in order of likelihood (most common first)
- Require directory to exist AND contain YAML files
- Return first matching directory

**Common patterns** (priority order):
1. `semantic_models/` - dbt convention
2. `models/semantic/` - nested dbt structure
3. `models/` - generic dbt models directory
4. `dbt_models/` - alternative naming
5. `semantic/` - simplified naming
6. `src/semantic_models/` - source-nested structure

**Edge cases**:
- Multiple candidate directories exist: Return first match (priority order)
- No YAML files in candidate: Skip and continue search
- Directory is symlink: Follow symlink (pathlib handles this)
- Permission denied: Skip and continue (silent failure)

**Performance optimization**:
- Use `Path.glob()` with early exit on first match
- Don't recursively scan directories
- Cache results for 60 seconds

### 3. LookML Output Directory Detection

**Strategy**:
- Check common output directory patterns
- Return first existing directory (files not required)
- Less strict than input detection (output may be empty)

**Common patterns** (priority order):
1. `build/lookml/` - build artifact convention
2. `lookml/` - direct naming
3. `build/` - generic build directory
4. `output/` - generic output directory
5. `generated/lookml/` - generated artifacts convention
6. `views/` - Looker view directory

**Edge cases**:
- Multiple output directories exist: Return first match (priority order)
- Directory exists but is empty: Still return it (valid output location)
- Directory doesn't exist: Return None (wizard will prompt or use default)

### 4. Schema Name Extraction

**Strategy**:
- Extract from first YAML file only (performance optimization)
- Use lightweight YAML parsing (not full DbtParser)
- Parse `model` field for schema name

**Extraction patterns**:

**Pattern 1**: ref() with schema
```yaml
semantic_models:
  - name: users
    model: ref('analytics_prod.dim_users')  # Extract "analytics_prod"
```

**Pattern 2**: ref() without schema
```yaml
semantic_models:
  - name: users
    model: ref('dim_users')  # No schema - return None
```

**Pattern 3**: source() function
```yaml
semantic_models:
  - name: users
    model: source('raw_data', 'users')  # Extract "raw_data"
```

**Pattern 4**: Direct schema.table
```yaml
semantic_models:
  - name: users
    model: analytics.users  # Extract "analytics"
```

**Regex patterns**:
```python
# ref('schema.model') or ref("schema.model")
ref_pattern = r"ref\(['\"]([^'\"]+)['\"]\)"

# source('schema', 'model')
source_pattern = r"source\(['\"]([^'\"]+)['\"]"

# Direct schema.model
if "." in model_field:
    schema = model_field.split(".")[0]
```

**Edge cases**:
- File contains no semantic_models: Return None
- Model field is empty: Return None
- Multiple schemas found: Return first (from first model in first file)
- Invalid YAML syntax: Return None (silent failure)
- Permission denied reading file: Return None (silent failure)

**Performance consideration**:
- Only parse first YAML file found
- Use `yaml.safe_load()` (not full DbtParser)
- No Pydantic validation overhead
- Target: <10ms for schema extraction

### 5. Caching Strategy

**Cache design**:
- In-memory cache (dict-based)
- Key: Working directory path
- Value: DetectionResult + timestamp
- TTL: 60 seconds (configurable)

**Cache invalidation**:
- Time-based: Results older than 60 seconds are stale
- Manual: `clear()` method for testing
- Per-directory: Different projects have separate cache entries

**Cache behavior**:
```python
# First call: Performs detection (~50ms)
result1 = detector.detect()  # Scans filesystem

# Second call within 60s: Uses cache (<1ms)
result2 = detector.detect()  # Returns cached result

# Force refresh: Bypass cache
result3 = detector.detect(use_cache=False)  # Re-scans filesystem
```

**Cache disable**:
```python
# Disable caching entirely (for testing)
detector = ProjectDetector(cache_enabled=False)
```

**Why 60 seconds?**:
- Long enough: Avoid repeated scans during wizard session
- Short enough: Capture file system changes (new directories)
- Balances: Performance vs. staleness

### 6. Edge Case Handling

**Edge Case 1**: Multiple semantic model directories exist

**Scenario**:
```
project/
├── semantic_models/     # Has YAML files
├── models/              # Also has YAML files
└── dbt_models/          # Also has YAML files
```

**Behavior**: Return first match in priority order (`semantic_models/`)

**Rationale**: Most specific naming wins

---

**Edge Case 2**: No YAML files found anywhere

**Scenario**:
```
project/
├── src/
└── tests/
```

**Behavior**:
- `input_dir`: None
- `found_yaml_files`: 0
- `has_semantic_models()`: False

**Wizard fallback**: Prompt user with default "semantic_models"

---

**Edge Case 3**: YAML files exist but no schema extractable

**Scenario**:
```yaml
# File uses ref() without schema
semantic_models:
  - name: users
    model: ref('users')  # No schema prefix
```

**Behavior**:
- `input_dir`: Found (contains YAML)
- `schema_name`: None
- `get_schema_name_or_default("public")`: Returns "public"

**Wizard fallback**: Prompt user with default "public" or last CLI value

---

**Edge Case 4**: Permission denied on directory

**Scenario**: User doesn't have read permission on directory

**Behavior**:
- Exception caught silently
- Continue to next candidate directory
- If all fail: Return None

**Rationale**: Detection is best-effort, not critical

---

**Edge Case 5**: Symlink to directory

**Scenario**:
```
project/
├── semantic_models -> /shared/semantic_models/
```

**Behavior**: Follow symlink (pathlib does this automatically)

**Verification**: Check that `Path.exists()` and `Path.is_dir()` both return True

---

**Edge Case 6**: Empty semantic_models directory

**Scenario**:
```
project/
└── semantic_models/     # Directory exists but empty
```

**Behavior**:
- Directory found but skipped (no YAML files)
- Continue searching other candidates
- If all empty: Return None

**Rationale**: Empty directory is not a valid input directory

---

**Edge Case 7**: Nested .yml files in subdirectories

**Scenario**:
```
semantic_models/
├── finance/
│   └── orders.yml
└── marketing/
    └── users.yml
```

**Behavior**:
- `_has_yaml_files()` uses `glob("*.yml")` (non-recursive)
- Directory appears empty, skipped

**Future enhancement**: Add `--recursive` flag to wizard (not in this issue)

**Current behavior**: User must point to parent directory

---

**Edge Case 8**: Detection takes >100ms

**Scenario**: Large directory structure or slow filesystem

**Mitigation strategies**:
1. Early exit on first match
2. Non-recursive globbing
3. Limit YAML parsing to first file only
4. Cache results for subsequent calls

**Monitoring**: `detection_time_ms` field in result for observability

**Fallback**: If detection is slow, cache becomes more valuable

### 7. Performance Requirements

**Target**: All detection operations complete in <100ms

**Performance breakdown**:
- Directory scanning: ~20-30ms (worst case: 6 directories)
- YAML file listing: ~10-20ms
- Schema extraction: ~5-10ms (one file)
- Total: ~35-60ms (typical)
- Cache hit: <1ms

**Performance tests** (included in test suite):
```python
def test_detection_performance():
    """Test that detection completes in <100ms."""
    detector = ProjectDetector(cache_enabled=False)

    start = time.perf_counter()
    result = detector.detect()
    end = time.perf_counter()

    elapsed_ms = (end - start) * 1000
    assert elapsed_ms < 100, f"Detection took {elapsed_ms}ms (target: <100ms)"
    assert result.detection_time_ms < 100
```

**Performance optimization checklist**:
- [ ] Use `Path.glob()` instead of `os.walk()` (non-recursive)
- [ ] Early exit on first match
- [ ] Parse only first YAML file
- [ ] Cache results for 60 seconds
- [ ] No Pydantic validation in detection
- [ ] No full DbtParser usage

**Benchmark results target**:
```
Detection (no cache):     50-80ms
Detection (cached):       <1ms
Schema extraction:        5-10ms
Directory scan (6 dirs):  20-30ms
YAML file listing:        10-20ms
```

### 8. Integration with Wizard System

**Usage in prompt-based wizard** (DTL-018):

```python
from dbt_to_lookml.wizard.detection import ProjectDetector
from dbt_to_lookml.wizard.base import BaseWizard
import questionary


class GenerateWizard(BaseWizard):
    """Wizard for generate command with smart defaults."""

    def run(self) -> dict[str, Any]:
        """Run wizard with detection-based defaults."""
        # Detect project structure
        detector = ProjectDetector()
        detected = detector.detect()

        # Use detected values as defaults
        input_dir = questionary.path(
            "Semantic model input directory:",
            default=str(detected.get_input_dir_or_default()),
            only_directories=True,
        ).ask()

        schema_name = questionary.text(
            "Database schema name:",
            default=detected.get_schema_name_or_default("public"),
        ).ask()

        output_dir = questionary.path(
            "LookML output directory:",
            default=str(detected.get_output_dir_or_default()),
            only_directories=True,
        ).ask()

        # ... rest of wizard prompts
```

**Key integration points**:
1. **Instantiation**: Create `ProjectDetector()` at wizard start
2. **Detection**: Call `detect()` once before prompts
3. **Defaults**: Use `get_*_or_default()` methods for prompt defaults
4. **Fallback**: Always provide sensible defaults if detection fails
5. **User override**: User can edit any detected value

**Benefits for user experience**:
- Pre-filled prompts reduce typing
- Smart detection feels intelligent
- User can still override any value
- Works even when detection fails (fallbacks)

### 9. Testing Strategy

#### Unit Tests: src/tests/unit/test_wizard_detection.py

**Test coverage areas**:

**Category 1: Directory Detection**
```python
def test_detect_semantic_models_directory():
    """Test detection of semantic_models/ directory."""

def test_detect_nested_models_directory():
    """Test detection of models/semantic/ directory."""

def test_detect_multiple_candidates_returns_first():
    """Test priority when multiple directories exist."""

def test_detect_no_input_directory_returns_none():
    """Test behavior when no semantic model directory exists."""

def test_detect_empty_directory_is_skipped():
    """Test that empty directories are skipped."""
```

**Category 2: Output Directory Detection**
```python
def test_detect_build_lookml_output_directory():
    """Test detection of build/lookml/ output directory."""

def test_detect_lookml_output_directory():
    """Test detection of lookml/ output directory."""

def test_detect_empty_output_directory_is_valid():
    """Test that empty output directories are valid."""

def test_detect_no_output_directory_returns_none():
    """Test behavior when no output directory exists."""
```

**Category 3: Schema Name Extraction**
```python
def test_extract_schema_from_ref_with_schema():
    """Test schema extraction from ref('schema.model')."""

def test_extract_schema_from_ref_without_schema():
    """Test behavior when ref() has no schema."""

def test_extract_schema_from_source():
    """Test schema extraction from source('schema', 'table')."""

def test_extract_schema_from_direct_pattern():
    """Test schema extraction from direct schema.table."""

def test_extract_schema_handles_invalid_yaml():
    """Test graceful failure on invalid YAML."""

def test_extract_schema_no_semantic_models():
    """Test behavior when YAML has no semantic_models."""
```

**Category 4: Caching**
```python
def test_cache_returns_same_result():
    """Test that cached result matches original."""

def test_cache_expires_after_ttl():
    """Test that cache expires after 60 seconds."""

def test_cache_can_be_bypassed():
    """Test use_cache=False bypasses cache."""

def test_cache_can_be_disabled():
    """Test cache_enabled=False disables caching."""

def test_cache_per_working_directory():
    """Test that different directories have separate cache entries."""
```

**Category 5: Performance**
```python
def test_detection_completes_in_under_100ms():
    """Test that detection meets <100ms requirement."""

def test_cached_detection_is_faster():
    """Test that cached detection is significantly faster."""
```

**Category 6: Edge Cases**
```python
def test_handle_permission_denied_gracefully():
    """Test silent failure on permission denied."""

def test_handle_symlink_directories():
    """Test that symlinks are followed correctly."""

def test_handle_non_utf8_yaml_files():
    """Test graceful failure on encoding errors."""

def test_default_methods_return_sensible_values():
    """Test get_*_or_default() methods."""
```

**Test fixtures**:
```
src/tests/fixtures/test_projects/
├── standard_layout/           # semantic_models/ with schema
│   └── semantic_models/
│       └── users.yml
├── nested_layout/             # models/semantic/ structure
│   └── models/
│       └── semantic/
│           └── orders.yml
├── no_schema_layout/          # ref() without schema
│   └── semantic_models/
│       └── simple.yml
├── multiple_dirs/             # Multiple candidate directories
│   ├── semantic_models/
│   ├── models/
│   └── dbt_models/
└── empty_layout/              # No YAML files
```

**Coverage target**: 100% branch coverage for detection module

#### Integration with Existing Test Suite

**Test markers**:
```python
@pytest.mark.unit
@pytest.mark.wizard
def test_detection_function():
    ...
```

**Run commands**:
```bash
# Run only detection tests
pytest src/tests/unit/test_wizard_detection.py -v

# Run all wizard tests
pytest -m wizard

# Run with coverage
pytest src/tests/unit/test_wizard_detection.py --cov=src/dbt_to_lookml/wizard/detection
```

### 10. Error Handling and Fallbacks

**Error handling philosophy**:
- Detection is **best-effort**, not critical
- All errors are caught silently
- Return None for failed detections
- Provide sensible defaults via `get_*_or_default()` methods

**Error scenarios**:

**Scenario 1**: Permission denied reading directory
```python
def _detect_input_dir(self) -> Optional[Path]:
    for dir_name in self.SEMANTIC_MODEL_DIRS:
        try:
            candidate = self.working_dir / dir_name
            if candidate.exists() and candidate.is_dir():
                if self._has_yaml_files(candidate):
                    return candidate
        except PermissionError:
            # Silent failure - try next candidate
            continue
    return None
```

**Scenario 2**: Invalid YAML in first file
```python
def _extract_schema_name(self, input_dir: Path) -> Optional[str]:
    try:
        # ... YAML parsing
        return schema
    except yaml.YAMLError:
        return None  # Silent failure
    except Exception:
        return None  # Catch-all for any parsing error
```

**Scenario 3**: Encoding error reading file
```python
try:
    with open(first_file, encoding="utf-8") as f:
        content = yaml.safe_load(f)
except UnicodeDecodeError:
    return None  # Not UTF-8, skip
except OSError:
    return None  # File system error
```

**Fallback chain**:
```
Detection attempt
    ↓
Catches exception
    ↓
Returns None
    ↓
get_*_or_default() provides fallback
    ↓
Wizard uses fallback as prompt default
    ↓
User can override
```

**No exceptions raised**:
- Detection never raises exceptions
- All errors return None
- Wizard handles None gracefully
- User always sees sensible defaults

## Implementation Checklist

- [ ] Create `src/dbt_to_lookml/wizard/detection.py` module
- [ ] Implement `DetectionResult` dataclass
- [ ] Implement `CachedDetection` and `DetectionCache` classes
- [ ] Implement `ProjectDetector` class
- [ ] Implement `_detect_input_dir()` method with priority search
- [ ] Implement `_detect_output_dir()` method
- [ ] Implement `_extract_schema_name()` with lightweight parsing
- [ ] Implement `_parse_schema_from_model_field()` with regex patterns
- [ ] Implement caching with 60-second TTL
- [ ] Add exports to `src/dbt_to_lookml/wizard/__init__.py`
- [ ] Create test fixtures in `src/tests/fixtures/test_projects/`
- [ ] Write unit tests for directory detection
- [ ] Write unit tests for schema extraction (all patterns)
- [ ] Write unit tests for caching behavior
- [ ] Write unit tests for edge cases
- [ ] Write performance test (<100ms requirement)
- [ ] Run `make type-check` to verify mypy compliance
- [ ] Run `pytest -m wizard` to verify all tests pass
- [ ] Verify 100% branch coverage for detection module
- [ ] Test integration with wizard base classes (manual)
- [ ] Document detection strategy in module docstrings

## Implementation Order

1. **Create data models** - 30 min
   - DetectionResult dataclass
   - CachedDetection and DetectionCache classes
   - Test instantiation and methods

2. **Implement directory detection** - 45 min
   - ProjectDetector skeleton
   - `_detect_input_dir()` with priority search
   - `_detect_output_dir()` method
   - Helper methods (`_has_yaml_files`, `_count_yaml_files`)

3. **Implement schema extraction** - 60 min
   - `_extract_schema_name()` lightweight parsing
   - `_extract_schema_from_content()` handling multiple formats
   - `_parse_schema_from_model_field()` regex patterns
   - Test all extraction patterns

4. **Implement caching** - 30 min
   - Cache check in `detect()` method
   - Cache storage after detection
   - TTL and staleness logic
   - Cache clear/disable methods

5. **Write unit tests** - 90 min
   - Create test fixtures (multiple project layouts)
   - Directory detection tests
   - Schema extraction tests (all patterns)
   - Caching tests
   - Edge case tests
   - Performance test

6. **Integration and polish** - 30 min
   - Add exports to wizard __init__.py
   - Verify type hints with mypy
   - Run full test suite
   - Check coverage report

**Estimated total**: 4.5 hours

## Rollout Impact

### User-Facing Changes

- **No direct user-facing changes**: Detection is internal to wizard
- **Indirect benefit**: Wizard prompts will have smarter defaults
- **Performance**: First wizard invocation may be slightly slower (~50ms)
- **Subsequent invocations**: Faster due to caching (<1ms)

### Developer-Facing Changes

- **New module**: `dbt_to_lookml.wizard.detection`
- **New imports**: `from dbt_to_lookml.wizard import ProjectDetector`
- **API usage**:
  ```python
  detector = ProjectDetector()
  result = detector.detect()
  input_dir = result.get_input_dir_or_default("semantic_models")
  ```

### Backward Compatibility

- **Fully backward compatible**: New module, no changes to existing code
- **No breaking changes**: Existing CLI commands unaffected
- **Optional feature**: Detection is only used by wizard (DTL-018)

### Performance Impact

- **First detection**: ~50-80ms (within <100ms requirement)
- **Cached detection**: <1ms (significant speedup)
- **Memory**: Minimal (~1KB per cached result)
- **No impact on**: Existing generate/validate commands (don't use detection)

## Notes for Implementation

1. **Lightweight parsing is key**:
   - Don't use DbtParser (too slow)
   - Use `yaml.safe_load()` directly
   - No Pydantic validation
   - Parse only first file

2. **Cache is crucial for UX**:
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

## Success Metrics

- [ ] Detection completes in <100ms (measured in tests)
- [ ] Cache reduces subsequent calls to <1ms
- [ ] Detects `semantic_models/` directory if present
- [ ] Extracts schema from ref('schema.model') pattern
- [ ] Extracts schema from source('schema', 'table') pattern
- [ ] Detects `build/lookml` or `lookml/` output directories
- [ ] Returns sensible defaults when detection fails
- [ ] Handles edge cases gracefully (multiple dirs, no files, etc.)
- [ ] 100% branch coverage for detection module
- [ ] All unit tests pass
- [ ] Type checking passes (mypy --strict)
- [ ] No performance regressions in existing commands

## Pre-Implementation Checklist

Before starting DTL-017 implementation:

- [ ] DTL-015 is complete (wizard base infrastructure exists)
- [ ] Review DTL-014 epic to understand wizard context
- [ ] Verify wizard module structure exists:
  - [ ] `src/dbt_to_lookml/wizard/__init__.py`
  - [ ] `src/dbt_to_lookml/wizard/base.py`
  - [ ] `src/dbt_to_lookml/wizard/types.py`
- [ ] Create test fixture directories
- [ ] Review existing parser patterns in `src/dbt_to_lookml/parsers/dbt.py`
- [ ] Understand pathlib API for cross-platform paths
- [ ] Review YAML parsing patterns in existing code

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/DTL-017.md`
3. Change status from `refinement` to `awaiting-strategy-review`, then to `strategy-approved`
4. Run: `/implement:1-spec DTL-017`
