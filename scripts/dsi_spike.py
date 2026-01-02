#!/usr/bin/env python3
"""
DSI Spike Results (2025-01-02)
==============================

This spike evaluated dbt-semantic-interfaces (DSI) for YAML parsing.

FINDINGS:
---------
1. DSI's `parse_yaml_files_to_semantic_manifest()` FAILED
   - Expects full dbt project context
   - Complains about `version` key in YAML files
   - Error: "Document should have one type of key"

2. DSI's `PydanticMetric` instantiation WORKS
   - Can instantiate from raw YAML dict
   - Preserves `config.meta.pop` structure

3. Simple PyYAML loading WORKS
   - No dependencies
   - Full control
   - Preserves all metadata

DECISION: Use PyYAML + our own Pydantic models
- DSI adds complexity without benefit
- Our domain models give us control over variant expansion
- Fewer dependencies

REMOVED: dbt-semantic-interfaces dependency

Run with: uv run python scripts/dsi_spike.py
"""

import yaml
from pathlib import Path


def demonstrate_simple_yaml_loading():
    """Demonstrate how simple YAML loading works with our semantic models."""

    semantic_dir = Path(
        "/Users/doug/Work/data-modelling/official-models/redshift_gold/models/3_semantic"
    )

    if not semantic_dir.exists():
        print(f"Semantic models directory not found: {semantic_dir}")
        print("This spike was run against real semantic models.")
        return

    print("=" * 60)
    print("SIMPLE YAML LOADING (The approach we're using)")
    print("=" * 60)

    # Load semantic models
    print("\nSEMANTIC MODELS:")
    for yaml_path in (semantic_dir / "models").rglob("*.yaml"):
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        for m in data.get("semantic_models", []):
            measures = len(m.get("measures", []))
            dims = len(m.get("dimensions", []))
            entities = len(m.get("entities", []))
            print(f"  {m['name']}: {measures} measures, {dims} dims, {entities} entities")

    # Load metrics with PoP config
    print("\nMETRICS (with PoP detection):")
    for yaml_path in (semantic_dir / "metrics").rglob("*.yaml"):
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        for m in data.get("metrics", []):
            meta = m.get("config", {}).get("meta", {})
            pop = meta.get("pop", {})
            pop_str = " [PoP]" if pop.get("enabled") else ""
            print(f"  {m['name']}: {m['type']}{pop_str}")

    # Show PoP config structure
    print("\nPOP CONFIG STRUCTURE (from first metric with PoP):")
    for yaml_path in (semantic_dir / "metrics").rglob("*.yaml"):
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        for m in data.get("metrics", []):
            pop = m.get("config", {}).get("meta", {}).get("pop", {})
            if pop.get("enabled"):
                print(f"  Metric: {m['name']}")
                print(f"    enabled: {pop.get('enabled')}")
                print(f"    comparisons: {pop.get('comparisons')}")
                print(f"    windows: {pop.get('windows')}")
                print(f"    grains: {pop.get('grains')}")
                print(f"    format: {pop.get('format')}")
                return


if __name__ == "__main__":
    print(__doc__)
    demonstrate_simple_yaml_loading()
