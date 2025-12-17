"""Shared configuration schemas used across dbt semantic layer and LookML.

This module defines configuration structures that are used by both input
(semantic layer) and output (LookML) schemas, providing a common foundation
for metadata and hierarchy management.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel

__all__ = [
    "Hierarchy",
    "TimezoneVariant",
    "ConfigMeta",
    "Config",
    "PopGrain",
    "PopComparison",
    "PopWindow",
    "PopConfig",
]


class PopGrain(str, Enum):
    """Period grains for PoP calculations.

    Defines how to slice the "current" period:
    - SELECTED: Use the user's date filter exactly as-is
    - MTD: Override to Month-to-Date (current month through today)
    - YTD: Override to Year-to-Date (current year through today)
    """

    SELECTED = "selected"
    MTD = "mtd"
    YTD = "ytd"


class PopComparison(str, Enum):
    """Comparison periods for PoP calculations.

    Defines what to compare against:
    - PP: Prior Period (offset by period_window parameter)
    - PY: Prior Year (always 1 year offset)
    """

    PP = "pp"
    PY = "py"


class PopWindow(str, Enum):
    """Period window definitions.

    Defines what "Prior Period" means:
    - WEEK: 1 week offset
    - MONTH: 1 month offset
    - QUARTER: 1 quarter offset
    """

    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"


class PopConfig(BaseModel):
    """Configuration for Period-over-Period calculations.

    Enables automatic generation of MTD/YTD and prior period/year
    comparison measures from a single measure definition.

    Attributes:
        enabled: Whether to generate PoP variants for this measure.
        short_label: Short label for PoP measure names (e.g., "GOV" instead of
            "Gross Order Value (GOV)"). If not provided, uses the metric's label.
        grains: Which period grains to generate (default: MTD, YTD).
        comparisons: Which comparison periods to generate (default: PP, PY).
        windows: What "Prior Period" can mean (default: month).
        format: LookML value_format_name for generated measures.
        date_dimension: Override date dimension reference in SQL.
        date_filter: Override filter field for {% date_start/end %}.

    Example:
        ```yaml
        measures:
          - name: revenue
            agg: sum
            config:
              meta:
                pop:
                  enabled: true
                  short_label: "Revenue"  # PoP labels: "Revenue PP", "Revenue PY Δ%"
                  comparisons: [pp, py]
                  format: usd
        ```
    """

    enabled: bool
    short_label: str | None = None
    grains: list[PopGrain] = [PopGrain.MTD, PopGrain.YTD]
    comparisons: list[PopComparison] = [PopComparison.PP, PopComparison.PY]
    windows: list[PopWindow] = [PopWindow.MONTH]
    format: str | None = None
    date_dimension: str | None = None
    date_filter: str | None = None


class Hierarchy(BaseModel):
    """Represents the 3-tier hierarchy for labeling."""

    entity: str | None = None
    category: str | None = None
    subcategory: str | None = None


class TimezoneVariant(BaseModel):
    """Configuration for timezone variant dimensions.

    Used to group multiple timezone representations of the same time dimension
    (e.g., UTC and local time) into a single toggleable dimension_group in LookML.

    Attributes:
        canonical_name: The base name shared by all variants of this dimension.
            Used for grouping variants together. Can optionally be prefixed with
            the model name for scoping (e.g., "rentals_starts_at"). If not prefixed,
            the generator will auto-prefix to prevent collisions across models.
        variant: The timezone variant identifier (e.g., "utc", "local", "eastern").
            Must match the suffix of the column expression exactly (case-sensitive).
            For example, if expr is "rental_starts_at_utc", variant should be "utc".
        is_primary: Whether this variant should be used as the primary dimension in
            the generated LookML. Only one variant per canonical_name should have
            is_primary: true. The primary variant's configuration (labels, descriptions,
            etc.) will be used in the generated toggleable dimension_group.

    Example:
        ```yaml
        dimensions:
          - name: starts_at
            label: "Rental Start"  # Clean label without timezone indicator
            type: time
            expr: rental_starts_at_utc
            config:
              meta:
                timezone_variant:
                  canonical_name: "starts_at"
                  variant: "utc"
                  is_primary: true

          - name: starts_at_local
            label: "Rental Start"  # Same clean label
            type: time
            expr: rental_starts_at_local
            config:
              meta:
                timezone_variant:
                  canonical_name: "starts_at"
                  variant: "local"
                  is_primary: false
        ```

    See Also:
        PHASE_1B_FINAL_PLAN.md: Implementation details and requirements
        TIMEZONE_TOGGLE_DESIGN.md: Design rationale and examples
    """

    canonical_name: str
    variant: str
    is_primary: bool


class ConfigMeta(BaseModel):
    """Represents metadata in a config section.

    Supports flexible metadata configuration for dimensions and measures, including
    optional hierarchy labels, data governance tags, and feature-specific overrides
    like timezone conversion.

    Attributes:
        domain: Data domain classification (e.g., "customer", "product").
        owner: Owner or team responsible for this data element.
        contains_pii: Whether the dimension contains personally identifiable
            information.
        update_frequency: How frequently the underlying data is updated
            (e.g., "daily", "real-time").
        subject: Flat structure view label for dimensions (preferred over
            hierarchy).
        category: Flat structure group label for dimensions/measures
            (preferred over hierarchy).
        hierarchy: Nested hierarchy structure for 3-tier labeling:
            - entity: Maps to view_label for dimensions
            - category: Maps to group_label for dimensions, view_label for measures
            - subcategory: Maps to group_label for measures
        convert_tz: Override timezone conversion behavior for this specific
            dimension. Controls whether the dimension_group's convert_tz
            parameter is set to yes/no.
            - True/yes: Enable timezone conversion (convert_tz: yes in LookML)
            - False/no: Disable timezone conversion (convert_tz: no in LookML)
            - Omitted: Use generator or CLI default setting
            This provides the highest-priority override in the configuration
            precedence chain.
        hidden: Control field visibility in generated LookML.
            - True: Field will have hidden: yes in LookML output
            - False/None: Field will not have hidden parameter (visible by default)
            Useful for hiding internal/technical fields from BI tools.
        bi_field: Mark field for selective exposure in BI explores.
            - True: Field included in explores when --bi-field-only is enabled
            - False/None: Field excluded from filtered explores
            Used with LookMLGenerator use_bi_field_filter=True for opt-in.
        use_group_item_label: Control group_item_label generation for dimension_groups.
            - True: Generate group_item_label with Liquid template for clean labels
            - False/None: No group_item_label parameter (default behavior)
            When enabled, timeframe fields display as "Date", "Month", "Quarter"
            instead of repeating the full dimension group name.
            This provides the highest-priority override in the configuration
            precedence chain (dimension > generator > CLI > default).
        time_dimension_group_label: Control top-level group label for time
            dimension_groups.
            - String value: Set custom group_label (e.g., "Time Periods")
            - None: Disable time dimension grouping (preserves hierarchy labels)
            - Default in generator: "Time Dimensions" (better organization)
            This provides highest-priority override in configuration precedence chain.
            When set, overrides any group_label from hierarchy metadata for time
            dimensions.
        join_cardinality: Override relationship inference for foreign key entities.
            Used on Entity config to explicitly declare join cardinality when
            the automatic inference would be incorrect.
            - "one_to_one": Include ALL fields (dimensions + measures) from joined view
            - "many_to_one": Include only dimensions from joined view (default behavior)
            - None: Use automatic relationship inference
            This is useful when a foreign key relationship is semantically one-to-one
            (e.g., every rental has exactly one review) but the target model has a
            different primary key (e.g., review_id instead of rental_id).
        date_selector: Control inclusion in date selector parameter for fact views.
            - True: Include this time dimension in the calendar date selector
            - False: Exclude this time dimension from the calendar date selector
            - None: Use mode default (auto=include, explicit=exclude)
            Only applicable to time dimensions when --date-selector is enabled.

    Example:
        Dimension with timezone override and hierarchy labels:

        ```yaml
        config:
          meta:
            domain: "events"
            owner: "analytics"
            contains_pii: false
            convert_tz: yes  # Override generator default for this dimension
            hidden: true  # Hide this internal dimension from LookML
            bi_field: false  # Don't include in bi_field filter
            use_group_item_label: yes  # Enable clean labels for this dimension
            hierarchy:
              entity: "event"
              category: "timing"
              subcategory: "creation"
        ```

    See Also:
        CLAUDE.md: "Timezone Conversion Configuration" section for detailed
            precedence rules and configuration examples.
        CLAUDE.md: "Field Visibility Control" section for hidden and bi_field
            parameters.
        CLAUDE.md: "Field Label Customization (group_item_label)" section for
            detailed precedence rules and usage examples.
    """

    domain: str | None = None
    owner: str | None = None
    contains_pii: bool | None = None
    update_frequency: str | None = None
    # Support both flat structure (subject, category) and nested (hierarchy)
    subject: str | None = None
    category: str | None = None
    hierarchy: Hierarchy | None = None
    convert_tz: bool | None = None
    hidden: bool | None = None
    bi_field: bool | None = None
    use_group_item_label: bool | None = None
    time_dimension_group_label: str | None = None
    timezone_variant: TimezoneVariant | None = None
    join_cardinality: Literal["one_to_one", "many_to_one"] | None = None
    date_selector: bool | None = None
    pop: PopConfig | None = None


class Config(BaseModel):
    """Represents a config section in a semantic model."""

    meta: ConfigMeta | None = None
