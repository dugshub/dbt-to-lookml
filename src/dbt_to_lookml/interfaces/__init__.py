"""Abstract base classes for parsers and generators."""

from dbt_to_lookml.interfaces.generator import Generator
from dbt_to_lookml.interfaces.parser import Parser

__all__ = ["Parser", "Generator"]
