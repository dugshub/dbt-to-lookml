"""Type definitions and enums for dbt-to-lookml."""

from __future__ import annotations

from enum import Enum


class AggregationType(str, Enum):
    """Supported aggregation types for measures."""

    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    SUM_BOOLEAN = "sum_boolean"
    PERCENTILE = "percentile"


class DimensionType(str, Enum):
    """Supported dimension types."""

    CATEGORICAL = "categorical"
    TIME = "time"


class TimeGranularity(str, Enum):
    """Supported time granularities."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    HOUR = "hour"
    MINUTE = "minute"


class MetricType(str, Enum):
    """Supported metric types."""

    SIMPLE = "simple"
    RATIO = "ratio"
    DERIVED = "derived"
    CONVERSION = "conversion"


# Type mapping from dbt aggregation types to LookML measure types
LOOKML_TYPE_MAP = {
    AggregationType.COUNT: "count",
    AggregationType.COUNT_DISTINCT: "count_distinct",
    AggregationType.SUM: "sum",
    AggregationType.AVERAGE: "average",
    AggregationType.MIN: "min",
    AggregationType.MAX: "max",
    AggregationType.MEDIAN: "median",
    AggregationType.SUM_BOOLEAN: "sum",
    AggregationType.PERCENTILE: "percentile",
}

# Aggregation types that need float casting to avoid integer truncation
# These operations on integer columns return integers in most SQL dialects
FLOAT_CAST_AGGREGATIONS = {
    AggregationType.AVERAGE,
    AggregationType.MEDIAN,
    AggregationType.PERCENTILE,
}


def qualify_sql_expression(expr: str | None, field_name: str) -> str:
    """Ensure SQL expressions use ${TABLE} to avoid ambiguous column references.

    This prevents ambiguous column errors in joins by ensuring all column references
    are qualified with ${TABLE}.

    Args:
        expr: Custom SQL expression or None
        field_name: Name of the field (used as default when expr is None)

    Returns:
        Qualified SQL expression

    Examples:
        >>> qualify_sql_expression(None, "revenue")
        '${TABLE}.revenue'
        >>> qualify_sql_expression("amount", "revenue")
        '${TABLE}.amount'
        >>> qualify_sql_expression("${TABLE}.amount", "revenue")
        '${TABLE}.amount'
        >>> qualify_sql_expression("1", "count_field")
        '1'
        >>> qualify_sql_expression("COALESCE(amount, 0)", "revenue")
        'COALESCE(amount, 0)'
    """
    if expr is None:
        # Default case: use ${TABLE}.field_name
        return f"${{TABLE}}.{field_name}"

    # Check if expression already contains table qualifiers
    if "${TABLE}" in expr or "${" in expr:
        # Already contains LookML references, use as-is
        return expr

    # Numeric literals (e.g., "1" for count-as-sum) - don't qualify
    # These are not column references
    if expr.strip().lstrip("-").replace(".", "", 1).isdigit():
        return expr

    # Check if it's a simple column reference (alphanumeric + underscore only)
    # This handles cases like "id" or "facility_sk"
    if expr.replace("_", "").replace(" ", "").isalnum() and " " not in expr.strip():
        # Simple column name - qualify it with ${TABLE}
        return f"${{TABLE}}.{expr}"

    # Complex expression (functions, operators, etc.)
    # Use as-is but user should ensure proper qualification
    return expr
