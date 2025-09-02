"""Mapper for converting semantic models to LookML structures."""


from typing import Optional

from dbt_to_lookml.models import (
    AggregationType,
    Dimension,
    DimensionType,
    Entity,
    LookMLDimension,
    LookMLDimensionGroup,
    LookMLExplore,
    LookMLMeasure,
    LookMLView,
    Measure,
    SemanticModel,
)


class SemanticModelMapper:
    """Maps semantic models to LookML views and explores."""

    def __init__(self, view_prefix: str = "", explore_prefix: str = "") -> None:
        """Initialize the mapper.

        Args:
            view_prefix: Prefix to add to view names.
            explore_prefix: Prefix to add to explore names.
        """
        self.view_prefix = view_prefix
        self.explore_prefix = explore_prefix

    def semantic_model_to_view(self, semantic_model: SemanticModel) -> LookMLView:
        """Convert a semantic model to a LookML view.

        Args:
            semantic_model: The semantic model to convert.

        Returns:
            A LookML view representation.
        """
        view_name = f"{self.view_prefix}{semantic_model.name}"

        # Convert SQL table name (handle dbt refs)
        sql_table_name = self._convert_model_ref(semantic_model.model)

        # Convert primary entities to dimensions with primary_key: yes
        lookml_dimensions = []
        for entity in semantic_model.entities:
            if entity.type == "primary":
                lookml_dim = self._entity_to_lookml_dimension(entity)
                lookml_dimensions.append(lookml_dim)

        # Convert dimensions
        lookml_dimension_groups = []
        for dimension in semantic_model.dimensions:
            if dimension.type == DimensionType.TIME:
                # Convert time dimensions to dimension_groups
                lookml_dim_group = self._time_dimension_to_dimension_group(dimension)
                lookml_dimension_groups.append(lookml_dim_group)
            else:
                # Convert regular dimensions
                lookml_dim = self._dimension_to_lookml(dimension)
                lookml_dimensions.append(lookml_dim)

        # Convert measures
        lookml_measures = []
        for measure in semantic_model.measures:
            lookml_measure = self._measure_to_lookml(measure)
            lookml_measures.append(lookml_measure)

        return LookMLView(
            name=view_name,
            sql_table_name=sql_table_name,
            description=semantic_model.description,
            dimensions=lookml_dimensions,
            dimension_groups=lookml_dimension_groups,
            measures=lookml_measures,
        )

    def semantic_model_to_explore(self, semantic_model: SemanticModel) -> LookMLExplore:
        """Convert a semantic model to a LookML explore.

        Args:
            semantic_model: The semantic model to convert.

        Returns:
            A LookML explore representation.
        """
        explore_name = f"{self.explore_prefix}{semantic_model.name}"
        view_name = f"{self.view_prefix}{semantic_model.name}"

        return LookMLExplore(
            name=explore_name,
            view_name=view_name,
            description=semantic_model.description,
        )

    def _dimension_to_lookml(self, dimension: Dimension) -> LookMLDimension:
        """Convert a semantic model dimension to a LookML dimension.

        Args:
            dimension: The dimension to convert.

        Returns:
            A LookML dimension.
        """
        # Determine LookML dimension type
        lookml_type = self._map_dimension_type(dimension)

        # Use expression if provided, otherwise use column name
        sql = dimension.expr or f"${{TABLE}}.{dimension.name}"

        return LookMLDimension(
            name=dimension.name,
            type=lookml_type,
            sql=sql,
            description=dimension.description,
        )

    def _measure_to_lookml(self, measure: Measure) -> LookMLMeasure:
        """Convert a semantic model measure to a LookML measure.

        Args:
            measure: The measure to convert.

        Returns:
            A LookML measure.
        """
        # Map aggregation type to LookML type
        lookml_type = self._map_aggregation_type(measure.agg)

        # Build SQL expression
        if measure.expr:
            if measure.agg == AggregationType.COUNT:
                sql = measure.expr
            else:
                sql = f"{measure.expr}"
        else:
            if measure.agg == AggregationType.COUNT:
                sql = "1"
            else:
                # Default to measure name as column
                sql = f"${{TABLE}}.{measure.name}"

        return LookMLMeasure(
            name=measure.name,
            type=lookml_type,
            sql=sql,
            description=measure.description,
        )

    def _map_dimension_type(self, dimension: Dimension) -> str:
        """Map semantic model dimension type to LookML dimension type.

        Args:
            dimension: The dimension to map.

        Returns:
            The corresponding LookML dimension type.
        """
        if dimension.type == DimensionType.CATEGORICAL:
            return "string"
        else:
            # Default fallback - should not reach here for time dimensions
            # as they are handled separately as dimension_groups
            return "string"

    def _convert_model_ref(self, model: str) -> str:
        """Convert dbt model reference to proper SQL table name.
        
        Args:
            model: The model string, potentially with ref() syntax.
            
        Returns:
            The converted SQL table name.
        """
        import re
        
        # Match ref('table_name') pattern
        ref_pattern = r"ref\(['\"]([^'\"]+)['\"]\)"
        match = re.match(ref_pattern, model.strip())
        
        if match:
            table_name = match.group(1)
            # Return the table name - in production, this might need schema prefixes
            return table_name
        
        # If not a ref(), return as-is
        return model
        
    def _entity_to_lookml_dimension(self, entity: Entity) -> LookMLDimension:
        """Convert a primary entity to a LookML dimension with primary_key: yes.
        
        Args:
            entity: The entity to convert.
            
        Returns:
            A LookML dimension with primary_key set.
        """
        sql = self._convert_sql_expression(entity.expr, entity.name)
        
        return LookMLDimension(
            name=entity.name,
            type="string",
            sql=sql,
            description=entity.description,
            primary_key=True,
        )
        
    def _time_dimension_to_dimension_group(self, dimension: Dimension) -> LookMLDimensionGroup:
        """Convert a time dimension to a LookML dimension_group.
        
        Args:
            dimension: The time dimension to convert.
            
        Returns:
            A LookML dimension_group.
        """
        sql = self._convert_sql_expression(dimension.expr, dimension.name)
        
        # Determine timeframes based on time granularity
        timeframes = ["date", "week", "month", "quarter", "year"]
        if dimension.type_params and 'time_granularity' in dimension.type_params:
            granularity = dimension.type_params['time_granularity']
            # Customize timeframes based on granularity if needed
            if granularity == "hour":
                timeframes = ["time", "hour", "date", "week", "month", "quarter", "year"]
            elif granularity == "minute":
                timeframes = ["time", "minute", "hour", "date", "week", "month", "quarter", "year"]
        
        return LookMLDimensionGroup(
            name=dimension.name,
            type="time",
            timeframes=timeframes,
            sql=sql,
            description=dimension.description,
            label=dimension.label,
        )
        
    def _convert_sql_expression(self, expr: Optional[str], field_name: str) -> str:
        """Convert SQL expression to LookML-compatible format.
        
        Args:
            expr: The SQL expression to convert.
            field_name: The field name as fallback.
            
        Returns:
            The converted SQL expression.
        """
        if not expr:
            return f"${{TABLE}}.{field_name}"
            
        # Convert the expression to use ${TABLE} references
        # This is a simplified conversion - in practice, you might need more sophisticated parsing
        converted_expr = expr.strip()
        
        # Handle multi-line CASE statements by preserving formatting
        if "case" in converted_expr.lower() and "when" in converted_expr.lower():
            # For CASE statements, keep the formatting but ensure proper ${TABLE} references
            # This preserves the complex logic from the semantic models
            lines = converted_expr.split('\n')
            processed_lines = []
            for line in lines:
                # Skip empty lines and preserve indentation
                if line.strip():
                    processed_lines.append(line)
                elif processed_lines:  # Keep empty lines in the middle
                    processed_lines.append(line)
            converted_expr = '\n'.join(processed_lines)
            
        return converted_expr

    def _map_aggregation_type(self, agg_type: AggregationType) -> str:
        """Map semantic model aggregation type to LookML measure type.

        Args:
            agg_type: The aggregation type to map.

        Returns:
            The corresponding LookML measure type.
        """
        agg_map = {
            AggregationType.COUNT: "count",
            AggregationType.COUNT_DISTINCT: "count_distinct",
            AggregationType.SUM: "sum",
            AggregationType.AVERAGE: "average",
            AggregationType.MIN: "min",
            AggregationType.MAX: "max",
            AggregationType.MEDIAN: "median",
        }
        return agg_map[agg_type]
