"""Filter domain - conditions for filtering metrics and dimensions."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FilterOperator(str, Enum):
    """Supported filter operators."""

    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUALS = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUALS = "<="
    IN = "IN"
    NOT_IN = "NOT IN"


class FilterCondition(BaseModel):
    """A single filter condition."""

    field: str
    operator: FilterOperator
    value: str | int | float | bool | list[Any]

    # NOTE: SQL generation is handled by adapters (dialect-specific)
    # See adapters/lookml/filter_renderer.py (future)

    model_config = {"frozen": True}


class Filter(BaseModel):
    """
    A collection of filter conditions (AND-ed together).

    Supports parsing from dict format:
        filter:
          field1: value           # equals
          field2: [a, b, c]       # IN
          field3: '>10'           # comparison

    NOTE: SQL generation is handled by adapters (dialect-specific).
    """

    conditions: list[FilterCondition] = Field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Filter:
        """
        Parse filter from dict format.

        Rules:
        - Plain value -> equals
        - List -> IN
        - Quoted string starting with operator -> parse operator
        """
        conditions = []
        for field, value in data.items():
            condition = cls._parse_condition(field, value)
            conditions.append(condition)
        return cls(conditions=conditions)

    @classmethod
    def _parse_condition(cls, field: str, value: Any) -> FilterCondition:
        """Parse a single condition from field and value."""
        # List -> IN
        if isinstance(value, list):
            return FilterCondition(field=field, operator=FilterOperator.IN, value=value)

        # String with operator prefix
        if isinstance(value, str):
            parsed = cls._parse_operator_string(value)
            if parsed:
                op, val = parsed
                return FilterCondition(field=field, operator=op, value=val)

        # Default: equals
        return FilterCondition(field=field, operator=FilterOperator.EQUALS, value=value)

    @classmethod
    def _parse_operator_string(cls, value: str) -> tuple[FilterOperator, Any] | None:
        """
        Parse operator from string like '>10', '>=5', '<100'.

        Returns (operator, parsed_value) or None if not an operator string.
        """
        patterns = [
            (r"^>=\s*(.+)$", FilterOperator.GREATER_THAN_OR_EQUALS),
            (r"^<=\s*(.+)$", FilterOperator.LESS_THAN_OR_EQUALS),
            (r"^!=\s*(.+)$", FilterOperator.NOT_EQUALS),
            (r"^>\s*(.+)$", FilterOperator.GREATER_THAN),
            (r"^<\s*(.+)$", FilterOperator.LESS_THAN),
        ]

        for pattern, operator in patterns:
            match = re.match(pattern, value)
            if match:
                raw_value = match.group(1).strip()
                # Try to parse as number
                parsed_value = cls._parse_value(raw_value)
                return (operator, parsed_value)

        return None

    @staticmethod
    def _parse_value(value: str) -> str | int | float:
        """Parse a string value to appropriate type."""
        # Try int
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string (strip quotes if present)
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            return value[1:-1]
        return value

    model_config = {"frozen": False}
