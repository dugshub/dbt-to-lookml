"""Label utilities for LookML rendering."""

from typing import Any


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
        ["Revenue"] → {"group_label": "Revenue"}
        [] → {}
    """
    if not group_parts:
        return {}

    result: dict[str, str] = {}

    if len(group_parts) >= 2:
        # Two levels: view_label.group_label
        # Space prefix on view_label for Looker sort ordering
        result["view_label"] = f"  {group_parts[0]}"
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
