"""Manifest system for tracking generated files and source hashes."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SourceInfo(BaseModel):
    """Information about a source file."""

    path: str
    hash: str
    model_name: str

    model_config = {"frozen": True}


class OutputInfo(BaseModel):
    """Information about a generated output file."""

    path: str
    hash: str
    type: str  # "view", "explore", "model", "calendar"

    model_config = {"frozen": True}


class ModelSummary(BaseModel):
    """Summary of a semantic model."""

    name: str
    dimension_count: int
    measure_count: int
    metric_count: int
    entities: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}


class GitHubPushInfo(BaseModel):
    """Information about a GitHub push operation."""

    repo: str  # owner/repo format
    branch: str
    commit_sha: str
    pushed_at: str  # ISO timestamp
    files_pushed: int
    commit_url: str | None = None

    model_config = {"frozen": True}

    @classmethod
    def create(
        cls,
        repo: str,
        branch: str,
        commit_sha: str,
        files_pushed: int,
    ) -> GitHubPushInfo:
        """Create a new GitHubPushInfo with current timestamp."""
        return cls(
            repo=repo,
            branch=branch,
            commit_sha=commit_sha,
            pushed_at=datetime.now(timezone.utc).isoformat(),
            files_pushed=files_pushed,
            commit_url=f"https://github.com/{repo}/commit/{commit_sha}",
        )


class SPManifest(BaseModel):
    """Manifest tracking generated files and sources."""

    version: str = "1.0.0"
    project: str
    generated_at: str
    config_hash: str
    sources: list[SourceInfo] = Field(default_factory=list)
    outputs: list[OutputInfo] = Field(default_factory=list)
    models: list[ModelSummary] = Field(default_factory=list)
    github_push: GitHubPushInfo | None = None

    model_config = {"frozen": True}

    @classmethod
    def create(
        cls,
        project: str,
        config_hash: str,
        sources: list[SourceInfo] | None = None,
        outputs: list[OutputInfo] | None = None,
        models: list[ModelSummary] | None = None,
        github_push: GitHubPushInfo | None = None,
    ) -> SPManifest:
        """Create a new manifest with current timestamp."""
        return cls(
            project=project,
            generated_at=datetime.now(timezone.utc).isoformat(),
            config_hash=config_hash,
            sources=sources or [],
            outputs=outputs or [],
            models=models or [],
            github_push=github_push,
        )

    def to_json(self) -> str:
        """Serialize manifest to JSON string."""
        return json.dumps(self.model_dump(), indent=2)

    @classmethod
    def from_file(cls, path: Path) -> SPManifest | None:
        """Load manifest from file, returns None if file doesn't exist."""
        if not path.exists():
            return None
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            return cls.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            return None

    def get_output_paths(self) -> set[str]:
        """Get set of all output file paths."""
        return {o.path for o in self.outputs}

    def find_orphaned_files(self, new_outputs: list[OutputInfo]) -> list[str]:
        """Find files in current manifest that are not in new outputs."""
        current_paths = self.get_output_paths()
        new_paths = {o.path for o in new_outputs}
        return sorted(current_paths - new_paths)

    def find_modified_files(self, new_outputs: list[OutputInfo]) -> list[str]:
        """Find files that exist in both but have different hashes."""
        current_hashes = {o.path: o.hash for o in self.outputs}
        modified = []
        for output in new_outputs:
            if output.path in current_hashes:
                if current_hashes[output.path] != output.hash:
                    modified.append(output.path)
        return sorted(modified)


def compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of file contents (first 16 chars)."""
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of string content (first 16 chars)."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def compute_config_hash(config: Any) -> str:
    """Compute hash of config for change detection."""
    config_str = json.dumps(config.model_dump(by_alias=True), sort_keys=True)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


def create_model_summary(model: Any) -> ModelSummary:
    """Create a ModelSummary from a ProcessedModel."""
    return ModelSummary(
        name=model.name,
        dimension_count=len(model.dimensions),
        measure_count=len(model.measures),
        metric_count=len(model.metrics),
        entities=[e.name for e in model.entities],
    )
