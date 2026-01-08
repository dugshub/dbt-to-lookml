"""Label resolution for LookML generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from semantic_patterns.config import LabelConfig
    from semantic_patterns.domain.dimension import Dimension
    from semantic_patterns.domain.measure import Measure
    from semantic_patterns.domain.metric import Metric


# Abbreviations for PoP comparisons
COMPARISON_ABBREVS: dict[str, str] = {
    "prior_year": "PY",
    "prior_month": "PM",
    "prior_quarter": "PQ",
    "prior_week": "PW",
    "prior_day": "PD",
}

# Full labels for PoP comparisons
COMPARISON_LABELS: dict[str, str] = {
    "prior_year": "Prior Year",
    "prior_month": "Prior Month",
    "prior_quarter": "Prior Quarter",
    "prior_week": "Prior Week",
    "prior_day": "Prior Day",
}

# Output type labels
OUTPUT_LABELS: dict[str, str] = {
    "previous": "",
    "change": "Δ",
    "pct_change": "%Δ",
}

OUTPUT_LABELS_VERBOSE: dict[str, str] = {
    "previous": "",
    "change": "Change",
    "pct_change": "% Change",
}

# PoP label templates by style
POP_STYLES: dict[str, dict[str, str]] = {
    "compact": {
        "previous": "{short} ({comp_abbrev})",      # "GOV (PY)"
        "change": "{short} Δ {comp_abbrev}",        # "GOV Δ PY"
        "pct_change": "{short} %Δ {comp_abbrev}",   # "GOV %Δ PY"
    },
    "standard": {
        "previous": "{label} ({comparison})",                    # "Gross Order Value (Prior Year)"
        "change": "{label} vs {comparison} Change",              # "Gross Order Value vs Prior Year Change"
        "pct_change": "{label} vs {comparison} % Change",        # "Gross Order Value vs Prior Year % Change"
    },
    "verbose": {
        "previous": "{label} - {comparison}",                    # "Gross Order Value - Prior Year"
        "change": "{label} - {comparison} Change",               # "Gross Order Value - Prior Year Change"
        "pct_change": "{label} - {comparison} % Change",         # "Gross Order Value - Prior Year % Change"
    },
}


class LabelResolver:
    """Centralized label resolution with group awareness and PoP styling."""

    def __init__(self, config: LabelConfig) -> None:
        self.config = config

    def _get_base_label(self, field: Dimension | Measure | Metric) -> str:
        """Get the base label for a field, defaulting to title-cased name."""
        return field.label or field.name.replace("_", " ").title()

    def effective_label(self, field: Dimension | Measure | Metric) -> str:
        """Get display label, using short_label if base label exceeds max length."""
        label = self._get_base_label(field)
        if len(label) > self.config.max_length and field.short_label:
            return field.short_label
        return label

    def resolve_group_labels(
        self,
        fields: list[Dimension | Measure | Metric],
    ) -> dict[str, str]:
        """
        Resolve labels for a group with conformity enforcement.

        If group_conformity is enabled and ANY field in the group needs
        its short_label (due to length), ALL fields with short_labels
        will use them for visual consistency.
        """
        if not self.config.group_conformity:
            return {f.name: self.effective_label(f) for f in fields}

        # Check if any field needs short label due to length
        any_needs_short = any(
            len(self._get_base_label(f)) > self.config.max_length
            for f in fields
        )

        result: dict[str, str] = {}
        for f in fields:
            if any_needs_short and f.short_label:
                result[f.name] = f.short_label
            else:
                result[f.name] = self.effective_label(f)
        return result

    def pop_label(
        self,
        metric: Metric,
        comparison: str,
        output: str,
    ) -> str:
        """
        Generate PoP variant label based on configured style.

        Args:
            metric: The base metric
            comparison: Comparison type (e.g., "prior_year", "prior_month")
            output: Output type (e.g., "previous", "change", "pct_change")

        Returns:
            Formatted label string based on pop_style config
        """
        style = self.config.pop_style
        if style not in POP_STYLES:
            style = "compact"

        templates = POP_STYLES[style]
        template = templates.get(output, templates["previous"])

        label = self._get_base_label(metric)
        short = metric.short_label or label

        # Truncate short label if still too long
        if len(short) > self.config.max_length:
            short = short[:self.config.max_length - 2] + "…"

        return template.format(
            label=label,
            short=short,
            comparison=COMPARISON_LABELS.get(comparison, comparison.replace("_", " ").title()),
            comp_abbrev=COMPARISON_ABBREVS.get(comparison, comparison[:2].upper()),
        )

    def pop_group_label(
        self,
        metric: Metric,
        category: str | None = None,
    ) -> str:
        """
        Generate group_label for PoP variants.

        For compact style, just uses the short/effective label.
        For other styles, may include category prefix.
        """
        effective = metric.short_label or self._get_base_label(metric)

        if self.config.pop_style == "compact":
            return effective

        if category:
            return f"{category} · {effective}"
        return effective
