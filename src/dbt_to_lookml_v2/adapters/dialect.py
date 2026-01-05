"""SQL dialect handling with sqlglot integration."""

import os
from enum import Enum
from typing import Any

import sqlglot
from sqlglot import exp


class Dialect(str, Enum):
    """Supported SQL dialects for LookML generation."""

    REDSHIFT = "redshift"
    POSTGRES = "postgres"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    DUCKDB = "duckdb"
    STARBURST = "trino"  # Starburst uses Trino dialect


# Environment variable for default dialect
DEFAULT_DIALECT_ENV = "D2L_DIALECT"


def get_default_dialect() -> Dialect:
    """Get default dialect from environment or fall back to Redshift."""
    env_value = os.environ.get(DEFAULT_DIALECT_ENV, "redshift").lower()
    try:
        return Dialect(env_value)
    except ValueError:
        return Dialect.REDSHIFT


class SqlRenderer:
    """
    Render SQL expressions with dialect-aware formatting.

    Uses sqlglot for parsing and transpilation.
    """

    def __init__(self, dialect: Dialect | None = None) -> None:
        self.dialect = dialect or get_default_dialect()
        self._sqlglot_dialect = self._map_to_sqlglot_dialect()

    def _map_to_sqlglot_dialect(self) -> str:
        """Map our dialect enum to sqlglot dialect string."""
        mapping = {
            Dialect.REDSHIFT: "redshift",
            Dialect.POSTGRES: "postgres",
            Dialect.SNOWFLAKE: "snowflake",
            Dialect.BIGQUERY: "bigquery",
            Dialect.DUCKDB: "duckdb",
            Dialect.STARBURST: "trino",
        }
        return mapping.get(self.dialect, "redshift")

    def qualify_expression(self, expr: str, table_alias: str = "${TABLE}") -> str:
        """
        Add table qualifier to bare column references.

        Transforms: rental_status
        To: ${TABLE}.rental_status
        """
        if not expr or not expr.strip():
            return expr

        try:
            parsed = sqlglot.parse_one(expr, dialect=self._sqlglot_dialect)
        except Exception:
            # If parsing fails, return original
            return expr

        # Find all column references without table qualifiers
        for column in parsed.find_all(exp.Column):
            if column.table is None or column.table == "":
                column.set("table", exp.to_identifier(table_alias))

        return parsed.sql(dialect=self._sqlglot_dialect)

    def transpile(self, expr: str, to_dialect: Dialect) -> str:
        """
        Transpile SQL expression from current dialect to target dialect.

        Useful for generating SQL that works across warehouses.
        """
        target = SqlRenderer(to_dialect)._sqlglot_dialect

        try:
            result = sqlglot.transpile(
                expr,
                read=self._sqlglot_dialect,
                write=target,
            )
            return result[0] if result else expr
        except Exception:
            return expr

    def extract_columns(self, expr: str) -> list[str]:
        """Extract column names referenced in an expression."""
        if not expr or not expr.strip():
            return []

        try:
            parsed = sqlglot.parse_one(expr, dialect=self._sqlglot_dialect)
            return [col.name for col in parsed.find_all(exp.Column)]
        except Exception:
            return []

    def render_string_literal(self, value: str) -> str:
        """Render a string literal with proper quoting for dialect."""
        # Most dialects use single quotes
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

    def render_in_list(self, values: list[Any]) -> str:
        """Render an IN clause value list."""
        formatted = []
        for v in values:
            if isinstance(v, str):
                formatted.append(self.render_string_literal(v))
            elif isinstance(v, bool):
                formatted.append("true" if v else "false")
            else:
                formatted.append(str(v))
        return f"({', '.join(formatted)})"

    def dateadd(self, period: str, amount: int, date_expr: str) -> str:
        """
        Generate dialect-specific DATEADD expression.

        Args:
            period: Time period (year, month, quarter, week, day)
            amount: Number of periods to add (negative for subtraction)
            date_expr: The date expression to offset

        Returns:
            Dialect-appropriate date arithmetic SQL
        """
        if self.dialect in (Dialect.REDSHIFT, Dialect.SNOWFLAKE):
            # DATEADD(period, amount, date)
            return f"DATEADD({period}, {amount}, {date_expr})"

        elif self.dialect == Dialect.BIGQUERY:
            # DATE_ADD(date, INTERVAL amount period)
            return f"DATE_ADD({date_expr}, INTERVAL {amount} {period.upper()})"

        elif self.dialect in (Dialect.POSTGRES, Dialect.DUCKDB):
            # date + INTERVAL 'amount period'
            if amount >= 0:
                return f"{date_expr} + INTERVAL '{amount} {period}'"
            else:
                return f"{date_expr} - INTERVAL '{abs(amount)} {period}'"

        elif self.dialect == Dialect.STARBURST:
            # date_add('period', amount, date)
            return f"date_add('{period}', {amount}, {date_expr})"

        else:
            # Fallback to Redshift syntax
            return f"DATEADD({period}, {amount}, {date_expr})"
