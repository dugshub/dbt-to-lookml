"""Label utilities for LookML rendering."""

from typing import Any

# View labels that get 2 leading spaces (sort to top)
# All other view labels get 1 leading space
TWO_SPACE_VIEW_LABELS = {"Metrics", "Metrics (PoP)"}


def _format_view_label(view_label: str) -> str:
    """
    Format view_label with appropriate leading spaces for Looker sort order.

    - "Metrics" and "Metrics (PoP)" get 2 spaces (sort first)
    - All others (e.g., "Date Dimensions") get 1 space (sort after Metrics)
    """
    if view_label in TWO_SPACE_VIEW_LABELS:
        return f"  {view_label}"
    else:
        return f" {view_label}"


def parse_group_labels(group_parts: list[str]) -> dict[str, str]:
    """
    Parse group parts into view_label and group_label.

    Supports dot notation: "Metrics.Revenue" → view_label + group_label

    Args:
        group_parts: List of group parts (from group.split("."))

    Returns:
        Dict with 'view_label' and/or 'group_label' keys

    Examples:
        ["Metrics", "Revenue"] → {"view_label": "  Metrics", "group_label": "Revenue"}
        ["Date Dimensions", "Created"] → {"view_label": " Date Dimensions", "group_label": "Created"}
        ["Revenue"] → {"group_label": "Revenue"}
        [] → {}
    """
    if not group_parts:
        return {}

    result: dict[str, str] = {}

    if len(group_parts) >= 2:
        # Two levels: view_label.group_label
        result["view_label"] = _format_view_label(group_parts[0])
        result["group_label"] = group_parts[1]
    else:
        # Single level: just group_label
        result["group_label"] = group_parts[0]

    return result


def apply_group_labels(result: dict[str, Any], group_parts: list[str]) -> None:
    """
    Apply view_label and group_label to a LookML dict in place.

    Args:
        result: LookML dict to modify
        group_parts: List of group parts
    """
    labels = parse_group_labels(group_parts)
    result.update(labels)


def apply_pop_view_label(
    result: dict[str, Any],
    category: str | None = None,
    metric_label: str | None = None,
) -> None:
    """
    Apply PoP-specific view_label and group_label to a LookML measure dict.

    PoP measures always go to "  Metrics (PoP)" view_label.
    group_label format: "{Category} · {Metric Label}" (e.g., "Revenue · GOV")

    Args:
        result: LookML dict to modify
        category: The category (from metric's group, e.g., "Revenue", "Counts")
        metric_label: The metric's display label (e.g., "GOV", "Rental Count")
    """
    result["view_label"] = _format_view_label("Metrics (PoP)")
    if category and metric_label:
        result["group_label"] = f"{category} · {metric_label}"
    elif category:
        result["group_label"] = category
    elif metric_label:
        result["group_label"] = metric_label
