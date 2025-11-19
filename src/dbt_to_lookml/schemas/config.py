"""Shared configuration schemas used across dbt semantic layer and LookML.

This module defines configuration structures that are used by both input
(semantic layer) and output (LookML) schemas, providing a common foundation
for metadata and hierarchy management.
"""

from __future__ import annotations

from pydantic import BaseModel

__all__ = ["Hierarchy", "ConfigMeta", "Config"]


class Hierarchy(BaseModel):
    """Represents the 3-tier hierarchy for labeling."""

    entity: str | None = None
    category: str | None = None
    subcategory: str | None = None


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


class Config(BaseModel):
    """Represents a config section in a semantic model."""

    meta: ConfigMeta | None = None
