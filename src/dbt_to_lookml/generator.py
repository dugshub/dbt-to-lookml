"""Backward compatibility layer for generator module."""

from dbt_to_lookml.generators.lookml import LookMLGenerator, LookMLValidationError

__all__ = ["LookMLGenerator", "LookMLValidationError"]