"""DbtMapper - transform dbt semantic model dicts to our format."""

from __future__ import annotations

import re
from typing import Any


def parse_jinja_filter(filter_expr: str) -> dict[str, Any]:
    """
    Parse dbt Jinja filter expression to our filter format.

    dbt format:
        {{ Dimension('rental__transaction_type') }} = 'completed'
        {{ Dimension('rental__amount') }} > 100
        {{ Dimension('rental__segment') }} IN ('Monthly', 'Event')

    Our format:
        {field: value} for equals
        {field: '>100'} for comparison
        {field: ['Monthly', 'Event']} for IN

    Returns:
        Dict with field name as key and value/operator as value
    """
    # Extract dimension reference: {{ Dimension('entity__field') }}
    dim_pattern = r"\{\{\s*Dimension\(['\"](\w+)__(\w+)['\"]\)\s*\}\}"
    dim_match = re.search(dim_pattern, filter_expr)

    if not dim_match:
        # Try TimeDimension pattern
        time_pattern = r"\{\{\s*TimeDimension\(['\"](\w+)__(\w+)['\"]"
        time_match = re.search(time_pattern, filter_expr)
        if time_match:
            dim_match = time_match

    if not dim_match:
        # Could not parse - return empty
        return {}

    # field name is the second group (after entity__)
    field = dim_match.group(2)

    # Get the rest of the expression after the dimension reference
    rest = filter_expr[dim_match.end() :].strip()

    # Parse operator and value
    # IN pattern: IN ('val1', 'val2', ...)
    in_pattern = r"^\s*IN\s*\(([^)]+)\)"
    in_match = re.search(in_pattern, rest, re.IGNORECASE)
    if in_match:
        values_str = in_match.group(1)
        # Parse quoted values
        values = re.findall(r"['\"]([^'\"]+)['\"]", values_str)
        return {field: values}

    # NOT IN pattern
    not_in_pattern = r"^\s*NOT\s+IN\s*\(([^)]+)\)"
    not_in_match = re.search(not_in_pattern, rest, re.IGNORECASE)
    if not_in_match:
        values_str = not_in_match.group(1)
        values = re.findall(r"['\"]([^'\"]+)['\"]", values_str)
        # For NOT IN, we need to represent it differently
        # Our format uses operator prefix strings
        return {field: {"operator": "NOT IN", "value": values}}

    # Comparison operators: =, !=, >, >=, <, <=
    comp_pattern = r"^\s*(>=|<=|!=|=|>|<)\s*(.+)$"
    comp_match = re.match(comp_pattern, rest)
    if comp_match:
        operator = comp_match.group(1)
        value_str = comp_match.group(2).strip()

        # Parse value - remove quotes if present
        if (value_str.startswith("'") and value_str.endswith("'")) or (
            value_str.startswith('"') and value_str.endswith('"')
        ):
            value: str | int | float = value_str[1:-1]
        else:
            # Try to parse as number
            try:
                value = int(value_str)
            except ValueError:
                try:
                    value = float(value_str)
                except ValueError:
                    value = value_str

        if operator == "=":
            return {field: value}
        else:
            # For other operators, encode in value string
            return {field: f"{operator}{value}"}

    return {}


def _extract_meta(dbt_obj: dict[str, Any]) -> dict[str, Any]:
    """
    Extract metadata from dbt config.meta, supporting both structures:

    1. Nested (preferred): config.meta.semantic_patterns.*
    2. Flat (legacy): config.meta.* directly

    Also maps legacy field names to our standard names:
    - group + category -> group (as "group.category" dot notation)
    - subject + category -> group (as "subject.category" dot notation)
    - group or subject alone -> group
    - primary_entity -> entity
    - bi_field: false -> hidden: true

    Returns normalized metadata dict.
    """
    config: dict[str, Any] = dbt_obj.get("config", {})
    meta: dict[str, Any] = config.get("meta", {})

    # Check for nested semantic_patterns structure first
    sp_meta: dict[str, Any] = meta.get("semantic_patterns", {})
    if sp_meta:
        return sp_meta

    # Fall back to flat meta structure - extract and normalize fields
    result: dict[str, Any] = {}

    # Map group/subject + category -> group with dot notation for hierarchical labels
    # group/subject becomes view_label, category becomes group_label
    # Support both conventions: "group + category" and "subject + category"
    view_label_field = meta.get("group") or meta.get("subject")
    category = meta.get("category")

    if view_label_field:
        if category:
            # Combine into dot notation: "ViewLabel.Category"
            result["group"] = f"{view_label_field}.{category}"
        else:
            result["group"] = view_label_field

    # Map primary_entity -> entity (or use entity directly)
    if "entity" in meta:
        result["entity"] = meta["entity"]
    elif "primary_entity" in meta:
        result["entity"] = meta["primary_entity"]

    # Direct mappings
    if "format" in meta:
        result["format"] = meta["format"]
    if "hidden" in meta:
        result["hidden"] = meta["hidden"]
    if "complete" in meta:
        result["complete"] = meta["complete"]
    if "date_selector" in meta:
        result["date_selector"] = meta["date_selector"]
    if "entity_group" in meta:
        result["entity_group"] = meta["entity_group"]
    if "short_label" in meta:
        result["short_label"] = meta["short_label"]

    # Handle bi_field: false -> hidden: true (inverse)
    if "bi_field" in meta and not meta["bi_field"] and "hidden" not in result:
        result["hidden"] = True

    # Handle PoP config - normalize their format to ours
    if "pop" in meta:
        dbt_pop = meta["pop"]
        if isinstance(dbt_pop, dict) and dbt_pop.get("enabled"):
            our_pop: dict[str, Any] = {}

            # Map comparisons: pp->pm (prior period->prior month as fallback)
            if "comparisons" in dbt_pop:
                comp_map = {"py": "py", "pm": "pm", "pq": "pq", "pw": "pw", "pp": "pm"}
                our_pop["comparisons"] = [
                    comp_map.get(c, c) for c in dbt_pop["comparisons"]
                ]

            # Add default outputs if not specified
            if "outputs" in dbt_pop:
                our_pop["outputs"] = dbt_pop["outputs"]
            else:
                # Default outputs when not specified
                our_pop["outputs"] = ["previous", "pct_change"]

            if our_pop:
                result["pop"] = our_pop

    return result


# Keep old name as alias for compatibility
_extract_semantic_patterns_meta = _extract_meta


def map_dimension(dbt_dim: dict[str, Any]) -> dict[str, Any]:
    """
    Transform dbt dimension dict to our format.

    dbt format:
        name: created_at
        label: "Rental Created"
        type: time
        type_params:
          time_granularity: day
        expr: rental_created_at_utc
        config:
          meta:
            semantic_patterns:
              group: "Dates"
              date_selector: true

    Our format:
        name: created_at
        label: Rental Created
        type: time
        granularity: day
        expr: rental_created_at_utc
        group: Dates
    """
    result: dict[str, Any] = {
        "name": dbt_dim["name"],
    }

    # Direct mappings
    if "label" in dbt_dim:
        result["label"] = dbt_dim["label"]
    if "description" in dbt_dim:
        result["description"] = dbt_dim["description"]
    if "expr" in dbt_dim:
        result["expr"] = dbt_dim["expr"]

    # Type mapping
    dim_type = dbt_dim.get("type", "categorical")
    result["type"] = dim_type

    # Flatten type_params.time_granularity -> granularity
    type_params = dbt_dim.get("type_params", {})
    if "time_granularity" in type_params:
        result["granularity"] = type_params["time_granularity"]

    # Extract semantic_patterns metadata
    sp_meta = _extract_semantic_patterns_meta(dbt_dim)
    if "group" in sp_meta:
        result["group"] = sp_meta["group"]
    if "hidden" in sp_meta:
        result["hidden"] = sp_meta["hidden"]

    # Extract short_label from meta or as direct field
    short_label = (
        dbt_dim.get("meta", {}).get("short_label")
        or dbt_dim.get("short_label")
        or sp_meta.get("short_label")
    )
    if short_label:
        result["short_label"] = short_label

    return result


def map_measure(dbt_measure: dict[str, Any]) -> dict[str, Any]:
    """
    Transform dbt measure dict to our format.

    dbt format:
        name: checkout_amount
        label: "Checkout Amount"
        agg: sum
        expr: rental_checkout_amount_local
        config:
          meta:
            semantic_patterns:
              group: "Revenue"
              format: usd
              hidden: true

    Our format:
        name: checkout_amount
        label: Checkout Amount
        agg: sum
        expr: rental_checkout_amount_local
        group: Revenue
        format: usd
        hidden: true
    """
    result: dict[str, Any] = {
        "name": dbt_measure["name"],
    }

    # Direct mappings
    if "label" in dbt_measure:
        result["label"] = dbt_measure["label"]
    if "description" in dbt_measure:
        result["description"] = dbt_measure["description"]
    if "expr" in dbt_measure:
        result["expr"] = dbt_measure["expr"]
    if "agg" in dbt_measure:
        result["agg"] = dbt_measure["agg"]

    # Extract semantic_patterns metadata
    sp_meta = _extract_semantic_patterns_meta(dbt_measure)
    if "group" in sp_meta:
        result["group"] = sp_meta["group"]
    if "format" in sp_meta:
        result["format"] = sp_meta["format"]
    if "hidden" in sp_meta:
        result["hidden"] = sp_meta["hidden"]

    # Extract short_label from meta or as direct field
    short_label = (
        dbt_measure.get("meta", {}).get("short_label")
        or dbt_measure.get("short_label")
        or sp_meta.get("short_label")
    )
    if short_label:
        result["short_label"] = short_label

    return result


def map_entity(dbt_entity: dict[str, Any]) -> dict[str, Any]:
    """
    Transform dbt entity dict to our format.

    dbt format:
        name: rental
        type: primary
        expr: unique_rental_sk
        label: "Reservation"
        config:
          meta:
            semantic_patterns:
              complete: true

    Our format:
        name: rental
        type: primary
        expr: unique_rental_sk
        label: Reservation
        complete: true
    """
    result: dict[str, Any] = {
        "name": dbt_entity["name"],
        "type": dbt_entity["type"],
    }

    # Direct mappings
    if "expr" in dbt_entity:
        result["expr"] = dbt_entity["expr"]
    if "label" in dbt_entity:
        result["label"] = dbt_entity["label"]

    # Extract semantic_patterns metadata
    sp_meta = _extract_semantic_patterns_meta(dbt_entity)
    if "complete" in sp_meta:
        result["complete"] = sp_meta["complete"]

    return result


def map_metric(dbt_metric: dict[str, Any]) -> dict[str, Any]:
    """
    Transform dbt metric dict to our format.

    dbt format:
        name: gov
        label: "Gross Order Value (GOV)"
        type: simple
        type_params:
          measure: checkout_amount
        filter:
          - "{{ Dimension('rental__transaction_type') }} = 'completed'"
        config:
          meta:
            semantic_patterns:
              format: usd
              group: "Revenue"
              entity: rental
              pop:
                comparisons: [py, pm]
                outputs: [previous, change, pct_change]

    Our format:
        name: gov
        label: Gross Order Value (GOV)
        type: simple
        measure: checkout_amount
        filter:
          transaction_type: completed
        format: usd
        group: Revenue
        entity: rental
        pop:
          comparisons: [py, pm]
          outputs: [previous, change, pct_change]
    """
    result: dict[str, Any] = {
        "name": dbt_metric["name"],
    }

    # Direct mappings
    if "label" in dbt_metric:
        result["label"] = dbt_metric["label"]
    if "description" in dbt_metric:
        result["description"] = dbt_metric["description"]
    if "type" in dbt_metric:
        result["type"] = dbt_metric["type"]

    # Extract type_params
    type_params = dbt_metric.get("type_params", {})

    # Map type_params based on metric type
    metric_type = dbt_metric.get("type", "simple")

    if metric_type == "simple":
        if "measure" in type_params:
            result["measure"] = type_params["measure"]
        # Handle measure as dict with name key
        elif isinstance(type_params.get("measure"), dict):
            result["measure"] = type_params["measure"].get("name")

    elif metric_type == "derived":
        if "expr" in type_params:
            result["expr"] = type_params["expr"]
        if "metrics" in type_params:
            # metrics can be list of strings or list of dicts with name
            metrics_list = type_params["metrics"]
            result["metrics"] = [
                m["name"] if isinstance(m, dict) else m for m in metrics_list
            ]

    elif metric_type == "ratio":
        if "numerator" in type_params:
            num = type_params["numerator"]
            result["numerator"] = num["name"] if isinstance(num, dict) else num
        if "denominator" in type_params:
            denom = type_params["denominator"]
            result["denominator"] = denom["name"] if isinstance(denom, dict) else denom

    # Parse filter (list of Jinja expressions)
    dbt_filter = dbt_metric.get("filter", [])
    if dbt_filter:
        parsed_filter: dict[str, Any] = {}
        for filter_expr in dbt_filter:
            if isinstance(filter_expr, str):
                parsed = parse_jinja_filter(filter_expr)
                parsed_filter.update(parsed)
        if parsed_filter:
            result["filter"] = parsed_filter

    # Extract semantic_patterns metadata
    sp_meta = _extract_semantic_patterns_meta(dbt_metric)
    if "format" in sp_meta:
        result["format"] = sp_meta["format"]
    if "group" in sp_meta:
        result["group"] = sp_meta["group"]
    if "entity" in sp_meta:
        result["entity"] = sp_meta["entity"]
    if "pop" in sp_meta:
        result["pop"] = sp_meta["pop"]

    # Extract short_label from meta or as direct field
    short_label = (
        dbt_metric.get("meta", {}).get("short_label")
        or dbt_metric.get("short_label")
        or sp_meta.get("short_label")
    )
    if short_label:
        result["short_label"] = short_label

    return result


def _extract_dbt_model_ref(model_ref: str) -> str | None:
    """
    Extract the model name from a dbt ref() expression.

    Examples:
        ref('fct_review') -> 'fct_review'
        ref("rentals") -> 'rentals'
        fct_review -> 'fct_review'  # Already plain name

    Returns:
        The extracted model name, or None if parsing fails.
    """
    if not model_ref:
        return None

    # Pattern: ref('model_name') or ref("model_name")
    ref_pattern = r"ref\(['\"](\w+)['\"]\)"
    match = re.match(ref_pattern, model_ref.strip())
    if match:
        return match.group(1)

    # If no ref() wrapper, treat as plain model name
    # (for cases where it's already extracted or native format)
    if re.match(r"^\w+$", model_ref.strip()):
        return model_ref.strip()

    return None


def map_semantic_model(dbt_model: dict[str, Any]) -> dict[str, Any]:
    """
    Transform dbt semantic_model dict to our format.

    Orchestrates all component mappings and collects date_selector dimensions.
    """
    result: dict[str, Any] = {
        "name": dbt_model["name"],
    }

    # Direct mappings
    if "description" in dbt_model:
        result["description"] = dbt_model["description"]

    # Extract model-level semantic_patterns metadata (for entity_group, etc.)
    sp_meta = _extract_meta(dbt_model)
    if sp_meta:
        result["meta"] = sp_meta

    # Extract dbt model reference (the actual table name)
    # dbt format: model: ref('fct_review') -> table is 'fct_review'
    model_ref = dbt_model.get("model")
    if model_ref:
        table_name = _extract_dbt_model_ref(model_ref)
        if table_name:
            # Store in meta for builder.py to use when creating DataModel
            result["meta"] = result.get("meta", {})
            result["meta"]["dbt_table"] = table_name

    # Map entities
    entities = dbt_model.get("entities", [])
    if entities:
        result["entities"] = [map_entity(e) for e in entities]

    # Map dimensions and collect date_selector dimensions
    dimensions = dbt_model.get("dimensions", [])
    date_selector_dims: list[str] = []
    mapped_dims: list[dict[str, Any]] = []

    for dim in dimensions:
        mapped = map_dimension(dim)
        mapped_dims.append(mapped)

        # Check for date_selector in semantic_patterns meta
        sp_meta = _extract_semantic_patterns_meta(dim)
        if sp_meta.get("date_selector"):
            date_selector_dims.append(dim["name"])

    if mapped_dims:
        result["dimensions"] = mapped_dims

    # Build date_selector config if any dimensions have date_selector: true
    if date_selector_dims:
        result["date_selector"] = {"dimensions": date_selector_dims}

    # Map measures
    measures = dbt_model.get("measures", [])
    if measures:
        result["measures"] = [map_measure(m) for m in measures]

    # Handle defaults.agg_time_dimension -> time_dimension
    defaults = dbt_model.get("defaults", {})
    if "agg_time_dimension" in defaults:
        result["time_dimension"] = defaults["agg_time_dimension"]

    return result


class DbtMapper:
    """
    Stateful mapper for transforming dbt format to our format.

    Handles the full transformation of semantic_models and metrics,
    then returns dicts ready for DomainBuilder.
    """

    def __init__(self) -> None:
        self._semantic_models: list[dict[str, Any]] = []
        self._metrics: list[dict[str, Any]] = []

    def add_semantic_models(self, dbt_models: list[dict[str, Any]]) -> None:
        """Add dbt semantic models to be mapped."""
        for model in dbt_models:
            mapped = map_semantic_model(model)
            self._semantic_models.append(mapped)

    def add_metrics(self, dbt_metrics: list[dict[str, Any]]) -> None:
        """Add dbt metrics to be mapped."""
        for metric in dbt_metrics:
            mapped = map_metric(metric)
            self._metrics.append(mapped)

    def get_documents(self) -> list[dict[str, Any]]:
        """
        Get mapped documents ready for DomainBuilder.

        Returns list of dicts with semantic_models and metrics keys,
        matching the format expected by DomainBuilder._collect_from_document.
        """
        # Return a single document containing all models and metrics
        return [
            {
                "semantic_models": self._semantic_models,
                "metrics": self._metrics,
            }
        ]
