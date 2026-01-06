"""
dbt-to-lookml v2: Domain-driven semantic layer to LookML generation.

Architecture:
    YAML → Ingestion (DomainBuilder) → Domain (ProcessedModel) → Adapter → .lkml

Layers:
    - domain/: Pure semantic types (models, dims, measures, metrics, entities)
    - ingestion/: YAML loading and domain object construction
    - adapters/: Output-specific rendering (LookML, future: Cube.js, etc.)

Key Concepts:
    - Metrics own their variants (PoP, benchmarks) - not separate entities
    - Domain knows what it IS, adapters know how to RENDER it
    - LookML-specific concepts (explores, joins) live in adapters/lookml/types.py
"""

__version__ = "0.3.0"
