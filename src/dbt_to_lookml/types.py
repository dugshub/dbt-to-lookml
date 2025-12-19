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
    are qualified with ${TABLE}. Uses sqlglot to parse complex SQL expressions and
    identify bare column references while preserving SQL keywords, functions, and literals.

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
        'COALESCE(${TABLE}.amount, 0)'
        >>> qualify_sql_expression("CASE WHEN status = 'active' THEN 1 END", "flag")
        "CASE WHEN ${TABLE}.status = 'active' THEN 1 END"
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

    # Complex expression - use sqlglot to parse and qualify column references
    return _qualify_with_sqlglot(expr)


def _qualify_with_sqlglot(expr: str) -> str:
    """Parse a complex SQL expression with sqlglot and qualify bare column references.

    Uses sqlglot's AST to identify Column nodes without table qualifiers and adds
    ${TABLE}. prefix to them.
    """
    from sqlglot import exp, parse_one
    from sqlglot.errors import ParseError

    try:
        tree = parse_one(expr)
    except ParseError:
        # If sqlglot can't parse it, return as-is (might be dialect-specific)
        return expr

    # Find all column references and add table qualifier if missing
    for column in tree.find_all(exp.Column):
        if not column.table:
            # Column has no table qualifier - add ${TABLE}
            column.set("table", exp.to_identifier("${TABLE}"))

    # Convert back to SQL string
    # Use identify=False to prevent quoting of identifiers
    result = tree.sql(identify=False)

    # sqlglot may quote ${TABLE} - remove the quotes
    result = result.replace('"${TABLE}"', "${TABLE}")
    result = result.replace("'${TABLE}'", "${TABLE}")

    return result
