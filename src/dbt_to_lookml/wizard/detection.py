"""Project structure detection for wizard defaults."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

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

    input_dir: Path | None
    output_dir: Path | None
    schema_name: str | None
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

    def get(self, working_dir: Path) -> DetectionResult | None:
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
        self, working_dir: Path | None = None, cache_enabled: bool = True
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

    def _detect_input_dir(self) -> Path | None:
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

    def _detect_output_dir(self) -> Path | None:
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

    def _extract_schema_name(self, input_dir: Path) -> str | None:
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

    def _extract_schema_from_content(self, content: dict[str, object]) -> str | None:
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
        models: list[object] = []

        # Handle different YAML structures
        if isinstance(content, dict):
            if "semantic_models" in content:
                semantic_models = content["semantic_models"]
                if isinstance(semantic_models, list):
                    models = semantic_models
                else:
                    models = []
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
        if not model_field or not isinstance(model_field, str):
            return None

        # Parse model field for schema name
        return self._parse_schema_from_model_field(model_field)

    def _parse_schema_from_model_field(self, model_field: str) -> str | None:
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
        # Also handles whitespace: ref( 'schema.model' )
        ref_pattern = r"ref\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
        ref_match = re.search(ref_pattern, model_field)

        if ref_match:
            ref_value = ref_match.group(1)
            # Check if ref contains schema.model pattern
            if "." in ref_value:
                return ref_value.split(".")[0]
            return None

        # Pattern 2: source('schema', 'model')
        source_pattern = r"source\(['\"]([^'\"]+)['\"]\s*,"
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
