"""Tests for domain-based output structure and manifest system."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from semantic_patterns.__main__ import cli
from semantic_patterns.manifest import (
    ModelSummary,
    OutputInfo,
    SourceInfo,
    SPManifest,
    compute_content_hash,
)
from semantic_patterns.adapters.lookml.paths import OutputPaths


class TestOutputPaths:
    """Test OutputPaths path generation."""

    def test_project_path(self) -> None:
        paths = OutputPaths(project="myproject", base_path=Path("/output"))
        assert paths.project_path == Path("/output/myproject")

    def test_views_path(self) -> None:
        paths = OutputPaths(project="myproject", base_path=Path("/output"))
        assert paths.views_path == Path("/output/myproject/views")

    def test_explores_path(self) -> None:
        paths = OutputPaths(project="myproject", base_path=Path("/output"))
        assert paths.explores_path == Path("/output/myproject/explores")

    def test_manifest_path(self) -> None:
        paths = OutputPaths(project="myproject", base_path=Path("/output"))
        assert paths.manifest_path == Path("/output/myproject/.sp-manifest.json")

    def test_view_file_path(self) -> None:
        paths = OutputPaths(project="myproject", base_path=Path("/output"))
        assert paths.view_file_path("orders") == Path(
            "/output/myproject/views/orders/orders.view.lkml"
        )

    def test_view_file_path_with_suffix(self) -> None:
        paths = OutputPaths(project="myproject", base_path=Path("/output"))
        assert paths.view_file_path("orders", ".metrics") == Path(
            "/output/myproject/views/orders/orders.metrics.view.lkml"
        )

    def test_explore_file_path(self) -> None:
        paths = OutputPaths(project="myproject", base_path=Path("/output"))
        assert paths.explore_file_path("orders") == Path(
            "/output/myproject/explores/orders.explore.lkml"
        )

    def test_model_file_path(self) -> None:
        paths = OutputPaths(project="myproject", base_path=Path("/output"))
        assert paths.model_file_path() == Path(
            "/output/myproject/myproject.model.lkml"
        )

    def test_relative_view_include(self) -> None:
        paths = OutputPaths(project="myproject", base_path=Path("/output"))
        assert paths.relative_view_include("orders") == "/views/orders/orders.view.lkml"

    def test_relative_view_include_with_suffix(self) -> None:
        paths = OutputPaths(project="myproject", base_path=Path("/output"))
        assert (
            paths.relative_view_include("orders", ".metrics")
            == "/views/orders/orders.metrics.view.lkml"
        )

    def test_relative_explore_include(self) -> None:
        paths = OutputPaths(project="myproject", base_path=Path("/output"))
        assert paths.relative_explore_include("orders") == "/explores/orders.explore.lkml"


class TestManifest:
    """Test manifest creation and operations."""

    def test_create_manifest(self) -> None:
        manifest = SPManifest.create(
            project="test",
            config_hash="abc123",
        )
        assert manifest.project == "test"
        assert manifest.config_hash == "abc123"
        assert manifest.version == "1.0.0"
        assert manifest.generated_at is not None

    def test_manifest_with_sources(self) -> None:
        sources = [
            SourceInfo(path="orders.yml", hash="def456", model_name="orders"),
        ]
        manifest = SPManifest.create(
            project="test",
            config_hash="abc123",
            sources=sources,
        )
        assert len(manifest.sources) == 1
        assert manifest.sources[0].model_name == "orders"

    def test_manifest_with_outputs(self) -> None:
        outputs = [
            OutputInfo(path="views/orders/orders.view.lkml", hash="ghi789", type="view"),
        ]
        manifest = SPManifest.create(
            project="test",
            config_hash="abc123",
            outputs=outputs,
        )
        assert len(manifest.outputs) == 1
        assert manifest.outputs[0].type == "view"

    def test_manifest_to_json(self) -> None:
        manifest = SPManifest.create(project="test", config_hash="abc123")
        json_str = manifest.to_json()
        data = json.loads(json_str)
        assert data["project"] == "test"

    def test_manifest_from_file(self, tmp_path: Path) -> None:
        manifest = SPManifest.create(project="test", config_hash="abc123")
        path = tmp_path / ".sp-manifest.json"
        path.write_text(manifest.to_json())

        loaded = SPManifest.from_file(path)
        assert loaded is not None
        assert loaded.project == "test"

    def test_manifest_from_missing_file(self, tmp_path: Path) -> None:
        path = tmp_path / ".sp-manifest.json"
        loaded = SPManifest.from_file(path)
        assert loaded is None

    def test_find_orphaned_files(self) -> None:
        manifest = SPManifest.create(
            project="test",
            config_hash="abc",
            outputs=[
                OutputInfo(path="a.lkml", hash="1", type="view"),
                OutputInfo(path="b.lkml", hash="2", type="view"),
                OutputInfo(path="c.lkml", hash="3", type="view"),
            ],
        )
        new_outputs = [
            OutputInfo(path="a.lkml", hash="1", type="view"),
            OutputInfo(path="d.lkml", hash="4", type="view"),
        ]
        orphaned = manifest.find_orphaned_files(new_outputs)
        assert sorted(orphaned) == ["b.lkml", "c.lkml"]

    def test_find_modified_files(self) -> None:
        manifest = SPManifest.create(
            project="test",
            config_hash="abc",
            outputs=[
                OutputInfo(path="a.lkml", hash="1", type="view"),
                OutputInfo(path="b.lkml", hash="2", type="view"),
            ],
        )
        new_outputs = [
            OutputInfo(path="a.lkml", hash="1", type="view"),  # unchanged
            OutputInfo(path="b.lkml", hash="999", type="view"),  # modified
        ]
        modified = manifest.find_modified_files(new_outputs)
        assert modified == ["b.lkml"]


class TestModelSummary:
    """Test model summary creation."""

    def test_model_summary(self) -> None:
        summary = ModelSummary(
            name="orders",
            dimension_count=10,
            measure_count=5,
            metric_count=3,
            entities=["order", "customer"],
        )
        assert summary.name == "orders"
        assert summary.dimension_count == 10


class TestHashFunctions:
    """Test hash functions."""

    def test_compute_content_hash(self) -> None:
        hash1 = compute_content_hash("hello world")
        hash2 = compute_content_hash("hello world")
        hash3 = compute_content_hash("different")
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 16  # truncated


class TestOutputStructureIntegration:
    """Integration tests for output structure."""

    @pytest.fixture
    def sample_project(self, tmp_path: Path) -> Path:
        """Create a minimal project for testing."""
        # Create models subdirectory
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        config = tmp_path / "sp.yml"
        config.write_text(
            f"""
project: test_project
input: {models_dir}
output: {tmp_path / "output"}
schema: test

model:
  connection: test_conn

output_options:
  clean: clean
  manifest: true
"""
        )

        model = models_dir / "orders.yml"
        model.write_text(
            """
semantic_models:
  - name: orders
    data_model:
      schema: test
      table: orders
    entities:
      - name: order
        type: primary
        expr: order_id
    dimensions:
      - name: status
        type: categorical
        expr: status
    measures:
      - name: order_count
        agg: count
        expr: order_id
"""
        )
        return tmp_path

    def test_creates_project_folder(self, sample_project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["build", "--config", str(sample_project / "sp.yml")]
        )
        assert result.exit_code == 0, f"Build failed: {result.output}"
        assert (sample_project / "output/test_project").exists()

    def test_creates_views_folder(self, sample_project: Path) -> None:
        runner = CliRunner()
        runner.invoke(cli, ["build", "--config", str(sample_project / "sp.yml")])
        assert (sample_project / "output/test_project/views").exists()

    def test_creates_explores_folder(self, sample_project: Path) -> None:
        runner = CliRunner()
        runner.invoke(cli, ["build", "--config", str(sample_project / "sp.yml")])
        assert (sample_project / "output/test_project/explores").exists()

    def test_creates_domain_folder(self, sample_project: Path) -> None:
        runner = CliRunner()
        runner.invoke(cli, ["build", "--config", str(sample_project / "sp.yml")])
        assert (sample_project / "output/test_project/views/orders").exists()

    def test_creates_view_file_in_domain(self, sample_project: Path) -> None:
        runner = CliRunner()
        runner.invoke(cli, ["build", "--config", str(sample_project / "sp.yml")])
        assert (
            sample_project / "output/test_project/views/orders/orders.view.lkml"
        ).exists()

    def test_creates_manifest(self, sample_project: Path) -> None:
        runner = CliRunner()
        runner.invoke(cli, ["build", "--config", str(sample_project / "sp.yml")])
        manifest_path = sample_project / "output/test_project/.sp-manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["project"] == "test_project"

    def test_creates_rollup_model(self, sample_project: Path) -> None:
        runner = CliRunner()
        runner.invoke(cli, ["build", "--config", str(sample_project / "sp.yml")])
        model_file = sample_project / "output/test_project/test_project.model.lkml"
        assert model_file.exists()

    def test_model_uses_relative_includes(self, sample_project: Path) -> None:
        runner = CliRunner()
        runner.invoke(cli, ["build", "--config", str(sample_project / "sp.yml")])
        model_file = sample_project / "output/test_project/test_project.model.lkml"
        content = model_file.read_text()
        assert "/views/orders/orders.view.lkml" in content

    def test_project_defaults_to_semantic_patterns(self, tmp_path: Path) -> None:
        """Test that project defaults to 'semantic-patterns' if not specified."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        config = tmp_path / "sp.yml"
        config.write_text(
            f"""
input: {models_dir}
output: {tmp_path / "output"}
schema: test
model:
  connection: test_conn
output_options:
  clean: clean
"""
        )
        model = models_dir / "orders.yml"
        model.write_text(
            """
semantic_models:
  - name: orders
    data_model:
      schema: test
      table: orders
    dimensions:
      - name: status
        type: categorical
        expr: status
"""
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["build", "--config", str(config)])
        assert result.exit_code == 0, f"Build failed: {result.output}"
        assert (tmp_path / "output/semantic-patterns").exists()
