"""UI label constants for LookML generation.

These constants define the standard labels used in generated LookML files
for organizing fields in Looker's field picker. The space prefixes control
sort order in the UI.

Sort Order Convention:
- 2 spaces: Appears at top (e.g., Metrics)
- 1 space: Appears near top (e.g., Time dimensions)
- No space: Normal alphabetical position
"""

# =============================================================================
# View Labels (control top-level grouping in Looker field picker)
# =============================================================================

# Metrics view labels (2-space prefix for top sorting)
VIEW_LABEL_METRICS_POP = "  Metrics (PoP)"  # Period-over-Period metrics
VIEW_LABEL_METRICS = "Metrics"  # Standard metrics (space prefix added when applied)

# Date dimensions view label (1-space prefix, sorts after Metrics)
VIEW_LABEL_DATE_DIMENSIONS = " Date Dimensions"

# =============================================================================
# Group Labels (control sub-grouping within view labels)
# =============================================================================

# Entity grouping
GROUP_LABEL_JOIN_KEYS = "Join Keys"  # Primary key entities in fact tables

# Time dimension grouping
GROUP_LABEL_DATE_DIMENSIONS = " Date Dimensions"  # Timezone selector (1 space prefix)
GROUP_LABEL_TIME_DIMENSIONS = "Time Dimensions"  # Generic time dimensions

# =============================================================================
# Label Suffixes (used in f-string patterns)
# =============================================================================

# Period-over-Period suffix: f"{label} {SUFFIX_POP}"
SUFFIX_POP = "PoP"

# Performance fallback: f"{model_name} {SUFFIX_PERFORMANCE}"
SUFFIX_PERFORMANCE = "Performance"
