"""LookML-specific SQL expression qualification.

Handles the LookML distinction between:
- Field references: ${dimension_name} - references to defined dimensions/measures
- SQL references: ${TABLE}.column_name - raw SQL column access
"""

import re

import sqlglot
import sqlglot.expressions as exp

from semantic_patterns.adapters.dialect import Dialect, SqlRenderer


def qualify_table_columns(expr: str) -> str:
    """
    Simple helper to qualify bare columns with ${TABLE}.

    For use in dimension definitions where we always want ${TABLE}.column_name.

    Args:
        expr: SQL expression

    Returns:
        Expression with ${TABLE}. prefix on bare columns

    Example:
        qualify_table_columns("transaction_type") → "${TABLE}.transaction_type"
    """
    if not expr or not expr.strip():
        return expr

    try:
        parsed = sqlglot.parse_one(expr)
    except Exception:
        return expr

    # Add ${TABLE} to bare columns
    for column in parsed.find_all(exp.Column):
        if column.table is None or column.table == "":
            column.set("table", exp.to_identifier("__LOOKML_TABLE__"))

    result = parsed.sql()

    # Replace marker with ${TABLE}
    result = re.sub(r'"?__LOOKML_TABLE__"?\."?(\w+)"?', r'${TABLE}.\1', result)
    result = re.sub(r"'?__LOOKML_TABLE__'?\.'?(\w+)'?", r'${TABLE}.\1', result)
    result = re.sub(r'`?__LOOKML_TABLE__`?\.`?(\w+)`?', r'${TABLE}.\1', result)

    return result


class LookMLSqlQualifier:
    """
    Qualify SQL expressions for LookML output.

    Intelligently chooses between:
    - ${field_name} for columns that are already defined as dimensions
    - ${TABLE}.column_name for raw SQL columns
    """

    def __init__(self, dialect: Dialect | None = None, defined_fields: dict[str, str] | None = None) -> None:
        self.sql_renderer = SqlRenderer(dialect)
        self.defined_fields = defined_fields or {}

    def qualify(self, expr: str, defined_fields: dict[str, str] | None = None) -> str:
        """
        Qualify a SQL expression for LookML.

        Args:
            expr: SQL expression to qualify
            defined_fields: Map of column_name -> field_name (overrides instance default)

        Returns:
            LookML-compatible SQL with field references or ${TABLE} qualifiers

        Examples:
            # Column exists as dimension
            qualify("transaction_type", {"transaction_type": "transaction_type"})
            # → "${transaction_type}"

            # Column doesn't exist
            qualify("amount", {})
            # → "${TABLE}.amount"

            # Complex expression
            qualify("CASE WHEN status = 'active' THEN amount END", {"status": "status"})
            # → "CASE WHEN ${status} = 'active' THEN ${TABLE}.amount END"
        """
        if not expr or not expr.strip():
            return expr

        fields = defined_fields if defined_fields is not None else self.defined_fields

        # Parse expression
        try:
            parsed = sqlglot.parse_one(expr)
        except Exception:
            # If parsing fails, return original
            return expr

        # Find all column references without table qualifiers
        for column in parsed.find_all(exp.Column):
            if column.table is None or column.table == "":
                column_name = column.name

                if column_name in fields:
                    # Mark for field reference replacement
                    column.set("table", exp.to_identifier("__LOOKML_FIELD__"))
                    column.set("this", exp.to_identifier(fields[column_name]))
                else:
                    # Mark for ${TABLE} replacement
                    column.set("table", exp.to_identifier("__LOOKML_TABLE__"))

        # Get SQL output
        result = parsed.sql()

        # Replace markers with LookML syntax
        # Field references: __LOOKML_FIELD__.field_name → ${field_name}
        result = re.sub(r'"?__LOOKML_FIELD__"?\."?(\w+)"?', r'${\1}', result)
        result = re.sub(r"'?__LOOKML_FIELD__'?\.'?(\w+)'?", r'${\1}', result)
        result = re.sub(r'`?__LOOKML_FIELD__`?\.`?(\w+)`?', r'${\1}', result)

        # Table references: __LOOKML_TABLE__.column_name → ${TABLE}.column_name
        result = re.sub(r'"?__LOOKML_TABLE__"?\."?(\w+)"?', r'${TABLE}.\1', result)
        result = re.sub(r"'?__LOOKML_TABLE__'?\.'?(\w+)'?", r'${TABLE}.\1', result)
        result = re.sub(r'`?__LOOKML_TABLE__`?\.`?(\w+)`?', r'${TABLE}.\1', result)

        return result
