"""Parser for dbt metric filter expressions.

Converts Jinja-style filter syntax from dbt semantic layer metrics
to SQL column references for LookML generation.

The dbt semantic layer uses Jinja-style syntax for metric filters:
    {{ Dimension('entity__dimension_name') }} = 'value'
    {{ TimeDimension('entity__time_dim', 'day') }} >= '2024-01-01'

This module parses these expressions and resolves them to actual
SQL column references by looking up dimension expressions in the
semantic models.

Example:
    >>> from dbt_to_lookml.parsers.metric_filter import MetricFilterParser
    >>> parser = MetricFilterParser(semantic_models)
    >>> sql = parser.parse("{{ Dimension('rental__transaction_type') }} = 'completed'")
    >>> print(sql)
    "rental_event_type = 'completed'"
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dbt_to_lookml.schemas.semantic_layer import SemanticModel


class MetricFilterParser:
    """Parses dbt metric filter syntax into SQL-ready expressions.

    Handles the following Jinja-style patterns:
      - {{ Dimension('entity__dimension_name') }} = 'value'
      - {{ TimeDimension('entity__dimension_name', 'granularity') }} >= 'date'

    The parser builds a lookup table of entity__dimension -> column_expr
    from the provided semantic models, then uses regex substitution to
    replace Jinja references with actual column expressions.

    Attributes:
        semantic_models: List of semantic models for dimension lookup.

    Example:
        >>> parser = MetricFilterParser(semantic_models)
        >>> sql = parser.parse("{{ Dimension('rental__transaction_type') }} = 'completed'")
        >>> print(sql)
        "rental_event_type = 'completed'"

        >>> sql = parser.parse_filters([
        ...     "{{ Dimension('rental__transaction_type') }} = 'completed'",
        ...     "{{ Dimension('rental__is_monthly') }} = true"
        ... ])
        >>> print(sql)
        "rental_event_type = 'completed' AND is_monthly_rental = true"
    """

    # Regex pattern for {{ Dimension('entity__dimension_name') }}
    DIMENSION_PATTERN = re.compile(
        r"\{\{\s*Dimension\(\s*['\"](\w+)__(\w+)['\"]\s*\)\s*\}\}"
    )

    # Regex pattern for {{ TimeDimension('entity__dimension_name', 'granularity') }}
    TIME_DIMENSION_PATTERN = re.compile(
        r"\{\{\s*TimeDimension\(\s*['\"](\w+)__(\w+)['\"]"
        r"\s*,\s*['\"](\w+)['\"]\s*\)\s*\}\}"
    )

    def __init__(self, semantic_models: list[SemanticModel]):
        """Initialize parser with semantic models for dimension lookup.

        Args:
            semantic_models: List of semantic models containing dimension
                definitions. Used to resolve entity__dimension references
                to actual column expressions.
        """
        self._models = {m.name: m for m in semantic_models}
        self._dimension_lookup = self._build_dimension_lookup(semantic_models)

    def _build_dimension_lookup(
        self, semantic_models: list[SemanticModel]
    ) -> dict[str, str]:
        """Build entity__dimension -> column_expr lookup table.

        Iterates through all semantic models, finds the primary entity,
        and creates a mapping from 'entity__dimension' keys to the
        dimension's SQL expression.

        Args:
            semantic_models: List of semantic models to process.

        Returns:
            Dictionary mapping 'entity__dimension' strings to SQL expressions.

        Example:
            If a model has primary entity 'rental' and dimension 'transaction_type'
            with expr='rental_event_type', creates mapping:
            {'rental__transaction_type': 'rental_event_type'}
        """
        lookup: dict[str, str] = {}

        for model in semantic_models:
            # Find the primary entity for this model
            primary_entity = None
            for entity in model.entities:
                if entity.type == "primary":
                    primary_entity = entity
                    break

            if not primary_entity:
                continue

            # Map each dimension to its expression
            for dim in model.dimensions:
                key = f"{primary_entity.name}__{dim.name}"
                # Use the dimension's expr, or fall back to name if no expr
                lookup[key] = dim.expr if dim.expr else dim.name

        return lookup

    def parse(self, filter_expr: str) -> str:
        """Convert a single filter expression to SQL.

        Parses Jinja-style dimension references and replaces them with
        actual column expressions from the semantic models.

        Args:
            filter_expr: A filter expression string, e.g.,
                "{{ Dimension('rental__transaction_type') }} = 'completed'"

        Returns:
            SQL-ready filter expression, e.g.,
                "rental_event_type = 'completed'"

        Raises:
            ValueError: If a dimension reference cannot be resolved.

        Example:
            >>> parser.parse("{{ Dimension('rental__transaction_type') }} = 'completed'")
            "rental_event_type = 'completed'"
        """
        result = filter_expr

        # Replace Dimension references
        result = self.DIMENSION_PATTERN.sub(
            lambda m: self._resolve_dimension(m.group(1), m.group(2)),
            result,
        )

        # Replace TimeDimension references (ignore granularity for now)
        result = self.TIME_DIMENSION_PATTERN.sub(
            lambda m: self._resolve_dimension(m.group(1), m.group(2)),
            result,
        )

        return result

    def parse_filters(self, filters: list[str]) -> str:
        """Convert a list of filter expressions to a SQL WHERE clause.

        Parses each filter expression and joins them with AND.

        Args:
            filters: List of filter expression strings.

        Returns:
            SQL-ready filter clause with expressions AND-joined.

        Example:
            >>> parser.parse_filters([
            ...     "{{ Dimension('rental__transaction_type') }} = 'completed'",
            ...     "{{ Dimension('rental__is_monthly') }} = true"
            ... ])
            "rental_event_type = 'completed' AND is_monthly_rental = true"
        """
        if not filters:
            return ""

        parsed = [self.parse(f) for f in filters]
        return " AND ".join(parsed)

    def _resolve_dimension(self, entity: str, dimension: str) -> str:
        """Look up actual column expression for an entity__dimension reference.

        Args:
            entity: The entity name (e.g., 'rental').
            dimension: The dimension name (e.g., 'transaction_type').

        Returns:
            The SQL column expression for this dimension.

        Raises:
            ValueError: If the entity__dimension combination is not found
                in any semantic model.
        """
        key = f"{entity}__{dimension}"

        if key not in self._dimension_lookup:
            available = ", ".join(sorted(self._dimension_lookup.keys())[:10])
            raise ValueError(
                f"Unknown dimension reference: '{key}'. "
                f"Available dimensions include: {available}..."
            )

        return self._dimension_lookup[key]
