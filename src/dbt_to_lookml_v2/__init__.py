"""
dbt-to-lookml v2: Domain-driven semantic layer to LookML generation.

Architecture:
    dbt YAML → DSI → DomainBuilder → ProcessedModel → LookMLAdapter → .lkml

Key Concepts:
    - Metrics own their variants (PoP, benchmarks) - they're not separate entities
    - Domain model knows what it IS, adapters know how to RENDER it
    - DSI handles parsing, we handle domain modeling and output generation
"""

__version__ = "2.0.0-dev"
