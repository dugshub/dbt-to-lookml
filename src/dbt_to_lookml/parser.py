"""Backward compatibility layer for parser module."""

from dbt_to_lookml.parsers.dbt import DbtParser

# Create alias for backward compatibility
SemanticModelParser = DbtParser

__all__ = ["SemanticModelParser", "DbtParser"]