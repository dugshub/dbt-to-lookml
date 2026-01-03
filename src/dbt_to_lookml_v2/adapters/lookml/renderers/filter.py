"""Filter rendering for LookML SQL expressions."""

from typing import Any

from dbt_to_lookml_v2.adapters.dialect import Dialect, SqlRenderer
from dbt_to_lookml_v2.domain import Filter, FilterCondition, FilterOperator


class FilterRenderer:
    """Render filter conditions to SQL for embedding in measure expressions."""

    def __init__(self, dialect: Dialect | None = None) -> None:
        self.sql_renderer = SqlRenderer(dialect)

    def render_case_when(self, expr: str, filter: Filter) -> str:
        """
        Wrap an expression with CASE WHEN filter conditions.

        Args:
            expr: The SQL expression to wrap (e.g., column name)
            filter: The filter conditions to apply

        Returns:
            SQL like: CASE WHEN condition THEN expr END

        Example:
            Input: expr="rental_checkout_amount", filter={transaction_type: completed}
            Output: CASE WHEN "${TABLE}".transaction_type = 'completed'
                        THEN "${TABLE}".rental_checkout_amount END
        """
        if not filter or not filter.conditions:
            return expr

        # Build WHERE clause from conditions
        where_clause = self._render_conditions(filter.conditions)

        # Wrap with CASE WHEN
        return f"CASE WHEN {where_clause} THEN {expr} END"

    def _render_conditions(self, conditions: list[FilterCondition]) -> str:
        """Render multiple conditions as AND-ed SQL."""
        sql_parts = []
        for cond in conditions:
            sql_parts.append(self._render_condition(cond))

        return " AND ".join(sql_parts)

    def _render_condition(self, cond: FilterCondition) -> str:
        """Render a single filter condition to SQL."""
        # Qualify field reference
        field_sql = self.sql_renderer.qualify_expression(cond.field)

        # Render value based on operator
        if cond.operator == FilterOperator.IN:
            values = self._render_in_values(cond.value)
            return f"{field_sql} IN ({values})"

        elif cond.operator == FilterOperator.NOT_IN:
            values = self._render_in_values(cond.value)
            return f"{field_sql} NOT IN ({values})"

        else:
            value_sql = self._render_value(cond.value)
            op = cond.operator.value
            return f"{field_sql} {op} {value_sql}"

    def _render_in_values(self, values: Any) -> str:
        """Render values for IN clause."""
        if not isinstance(values, list):
            values = [values]
        rendered = [self._render_value(v) for v in values]
        return ", ".join(rendered)

    def _render_value(self, value: Any) -> str:
        """Render a single value to SQL."""
        if isinstance(value, str):
            # Escape single quotes
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif value is None:
            return "NULL"
        else:
            return str(value)
