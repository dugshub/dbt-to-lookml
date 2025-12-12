"""Generator for creating LookML files from semantic models."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import lkml
from rich.console import Console

from dbt_to_lookml.interfaces.generator import Generator
from dbt_to_lookml.schemas.semantic_layer import Metric, SemanticModel, _smart_title
from dbt_to_lookml.types import DimensionType

if TYPE_CHECKING:
    from dbt_to_lookml.schemas.semantic_layer import Measure

console = Console()


class LookMLValidationError(Exception):
    """Exception raised when LookML validation fails."""

    pass


class LookMLGenerator(Generator):
    """Generates LookML files from semantic models with validation and advanced
    features."""

    def __init__(
        self,
        view_prefix: str = "",
        explore_prefix: str | None = None,
        measure_suffix: str = "_measure",
        validate_syntax: bool = True,
        format_output: bool = True,
        schema: str = "",
        connection: str = "redshift_test",
        model_name: str = "semantic_model",
        convert_tz: bool | None = None,
        use_bi_field_filter: bool = False,
        use_group_item_label: bool | None = None,
        fact_models: list[str] | None = None,
        time_dimension_group_label: str | None = None,
    ) -> None:
        """Initialize the generator.

        Configures LookML generation with support for timezone conversion,
        field visibility control, view/explore naming, syntax validation, and
        output formatting. The convert_tz and use_group_item_label parameters
        establish the default behavior for all generated dimension_groups, which
        can be overridden at the dimension level through semantic model metadata.

        Args:
            view_prefix: Prefix to add to all generated view names. Useful
                for namespacing views by environment or project.
            explore_prefix: Prefix to add to all generated explore names.
                Defaults to view_prefix value if not specified to ensure
                consistent naming and avoid join reference errors.
            validate_syntax: Whether to validate generated LookML syntax
                using the lkml library. Validation runs automatically unless
                explicitly disabled.
            format_output: Whether to format LookML output for human
                readability. Applies consistent indentation and spacing to
                generated files.
            schema: Database schema name for sql_table_name in generated
                views. Used to qualify table references (e.g., "public.orders").
            connection: Looker connection name for the generated .model.lkml
                file. This tells Looker which database connection to use for
                the model.
            model_name: Name for the generated model file (without
                .model.lkml extension). Allows multiple models to be generated
                from different semantic model sets.
            convert_tz: Default timezone conversion setting for all
                dimension_groups. Controls the convert_tz parameter in generated
                LookML dimension_groups.
                - True: Enable timezone conversion globally (convert_tz: yes)
                - False: Disable timezone conversion globally (convert_tz: no)
                - None: Use hardcoded default (False, disabled by default)
                This setting is overridden by per-dimension config.meta.convert_tz
                in semantic models, allowing fine-grained control at the
                dimension level.
            use_bi_field_filter: Whether to filter explore fields based on
                config.meta.bi_field settings.
                - False (default): All fields included in explores (backward compatible)
                - True: Only fields with bi_field: true included (selective exposure)
                Primary keys (entities) are always included regardless of setting.
            use_group_item_label: Whether to add group_item_label to
                dimension_groups for cleaner timeframe labels. When enabled,
                timeframes display as "Date", "Month", "Quarter" instead of
                repeating the dimension group name. Uses Liquid templating to
                extract timeframe name from field name.
                - True: Generate group_item_label with Liquid template
                - False: No group_item_label (default, backward compatible)
                - None: Use hardcoded default (False, disabled by default)
                This setting is overridden by per-dimension
                config.meta.use_group_item_label in semantic models.
            fact_models: Optional list of model names to generate explores for.
                If provided, only these models will have explores generated.
                If None, no explores will be generated.
                Join relationships are discovered automatically via foreign keys.
            time_dimension_group_label: Top-level group label for time
                dimension_groups. Controls the group_label parameter for organizing
                time dimensions in Looker's field picker.
                - String value: Set as group_label for all time dimension_groups
                - None: Disable group labeling (no group_label set)
                - Default: "Time Dimensions" (provides better organization)
                This setting is overridden by per-dimension
                config.meta.time_dimension_group_label in semantic models, allowing
                fine-grained control at the dimension level.

        Example:
            Enable group_item_label globally:

            ```python
            generator = LookMLGenerator(
                view_prefix="fact_",
                use_group_item_label=True
            )
            ```

            Combine with other features:

            ```python
            generator = LookMLGenerator(
                view_prefix="dim_",
                convert_tz=True,
                use_group_item_label=True,
                use_bi_field_filter=True
            )
            ```

        See Also:
            CLAUDE.md: "Timezone Conversion Configuration" section for
                multi-level precedence rules and detailed examples.
            CLAUDE.md: "Field Visibility Control" section for bi_field
                filtering details.
            CLAUDE.md: "Field Label Customization (group_item_label)" section.
            Dimension._to_dimension_group_dict(): Implements group_item_label
                generation with precedence handling.
        """
        # Default explore_prefix to view_prefix if not specified
        # This ensures consistent naming and avoids join reference errors
        if explore_prefix is None:
            explore_prefix = view_prefix

        super().__init__(
            validate_syntax=validate_syntax,
            format_output=format_output,
            view_prefix=view_prefix,
            explore_prefix=explore_prefix,
            schema=schema,
        )
        self.view_prefix = view_prefix
        self.explore_prefix = explore_prefix
        self.measure_suffix = measure_suffix
        self.schema = schema
        self.connection = connection
        self.model_name = model_name
        self.convert_tz = convert_tz
        self.use_bi_field_filter = use_bi_field_filter
        self.use_group_item_label = use_group_item_label
        self.fact_models = fact_models
        self.time_dimension_group_label = time_dimension_group_label

        # Backward compatibility attribute
        class MapperCompat:
            def __init__(self, vp: str, ep: str) -> None:
                self.view_prefix = vp
                self.explore_prefix = ep

            def semantic_model_to_view(self, model: SemanticModel) -> SemanticModel:
                # Stub method for backward compatibility
                return model

        self.mapper = MapperCompat(view_prefix, explore_prefix)

    def get_measure_lookml_name(self, measure: Measure) -> str:
        """Translate dbt measure name to LookML field name.

        Applies the generator's measure naming convention (suffix).
        All dbt measures are translated to hidden LookML measures with a suffix
        to distinguish them from user-facing metrics (also measures in LookML).

        This is the single source of truth for measure name translation.

        Args:
            measure: The dbt Measure object to translate.

        Returns:
            LookML field name with suffix (e.g., 'revenue_measure').
        """

        return f"{measure.name}{self.measure_suffix}"

    def _get_canonical_key(
        self,
        model: SemanticModel,
        dimension: "Dimension",
    ) -> str:
        """Get scoped canonical key for timezone variant grouping.

        Auto-prefixes canonical_name with model name for scoping unless already
        prefixed. This prevents collisions when multiple models have dimensions
        with the same canonical_name.

        Args:
            model: The semantic model containing the dimension.
            dimension: The dimension with timezone_variant configuration.

        Returns:
            Scoped canonical key (e.g., "rentals_starts_at").

        Example:
            >>> # Auto-prefix case
            >>> canonical_name = "starts_at"
            >>> _get_canonical_key(model, dim)  # Returns "rentals_starts_at"
            >>>
            >>> # Already prefixed case
            >>> canonical_name = "rentals_starts_at"
            >>> _get_canonical_key(model, dim)  # Returns "rentals_starts_at" (no double prefix)
        """
        if (
            not dimension.config
            or not dimension.config.meta
            or not dimension.config.meta.timezone_variant
        ):
            raise ValueError("Dimension missing timezone_variant configuration")

        canonical_name = dimension.config.meta.timezone_variant.canonical_name

        # If already prefixed with model name, use as-is (idempotent)
        if canonical_name.startswith(f"{model.name}_"):
            return canonical_name

        # Otherwise auto-prefix for scoping
        return f"{model.name}_{canonical_name}"

    def _group_timezone_variants(
        self,
        model: SemanticModel,
    ) -> dict[str, list["Dimension"]]:
        """Group time dimensions by timezone variant canonical name.

        Detects dimensions with timezone_variant configuration and groups them
        by their scoped canonical_name. Only time-type dimensions are processed.
        Groups with 2+ variants can be collapsed into a single dimension_group
        with timezone toggle logic.

        Args:
            model: The semantic model to process.

        Returns:
            Dictionary mapping canonical keys to dimension lists.
            Keys are scoped (e.g., "rentals_starts_at").
            Values are lists of dimensions sharing that canonical name.

        Example:
            >>> groups = _group_timezone_variants(rentals_model)
            >>> groups
            {
                "rentals_starts_at": [starts_at_dim, starts_at_local_dim],
                "rentals_ends_at": [ends_at_dim, ends_at_local_dim],
            }

        Note:
            - Non-time dimensions with timezone_variant are ignored
            - Dimensions without timezone_variant are ignored
            - Groups with 1 dimension indicate misconfiguration (warning candidate)
        """
        groups: dict[str, list["Dimension"]] = {}

        for dim in model.dimensions:
            # Only process time dimensions with timezone_variant config
            if dim.type != DimensionType.TIME:
                continue

            if (
                not dim.config
                or not dim.config.meta
                or not dim.config.meta.timezone_variant
            ):
                continue

            # Get scoped canonical key and group
            canonical_key = self._get_canonical_key(model, dim)
            groups.setdefault(canonical_key, []).append(dim)

        return groups

    def _has_timezone_variants(self, model: SemanticModel) -> bool:
        """Check if a semantic model has any timezone variant dimensions.

        Quick check to determine if a model contains timezone variants that
        would result in a timezone_selector parameter being generated.

        Args:
            model: The semantic model to check.

        Returns:
            True if the model has 2+ dimensions with matching timezone_variant
            canonical_names (indicating toggleable variants), False otherwise.
        """
        groups = self._group_timezone_variants(model)
        # Need at least one group with 2+ variants
        return any(len(variants) >= 2 for variants in groups.values())

    def _generate_timezone_parameter(
        self,
        variant_groups: dict[str, list["Dimension"]],
        group_label: str | None = None,
    ) -> dict | None:
        """Generate timezone selector parameter using variant names from meta.

        Extracts unique variants from timezone_variant groups and generates
        a parameter with values as column suffixes (e.g., "_utc", "_local").

        Args:
            variant_groups: Dictionary of grouped timezone variants from
                _group_timezone_variants(). Keys are scoped canonical names,
                values are lists of paired dimensions.
            group_label: Optional group label for the parameter. When provided,
                groups the timezone_selector with time dimensions in Looker's
                field picker. Defaults to "Time Dimensions" if not specified.

        Returns:
            Parameter dictionary for LookML output, or None if no variants exist.

        Example:
            Given variants ["utc", "local"], generates:

            ```
            {
                "parameter": "timezone_selector",
                "type": "unquoted",
                "label": "Timezone",
                "group_label": "Time Dimensions",
                "allowed_value": [
                    {"label": "LOCAL", "value": "_local"},
                    {"label": "UTC", "value": "_utc"}
                ],
                "default_value": "_local"
            }
            ```

        Note:
            - Parameter values are column suffixes, not variant names
            - Default is set to primary variant's suffix
            - Falls back to first alphabetical variant if no primary specified
            - group_label defaults to "Time Dimensions" to match time dimension grouping
        """
        if not variant_groups:
            return None

        # Extract unique variants from meta
        variants = set()
        default_variant = None

        for canonical_key, dims in variant_groups.items():
            for dim in dims:
                if not dim.config or not dim.config.meta or not dim.config.meta.timezone_variant:
                    continue

                variant_cfg = dim.config.meta.timezone_variant
                variants.add(variant_cfg.variant)

                # Use primary variant as default
                if variant_cfg.is_primary and default_variant is None:
                    default_variant = variant_cfg.variant

        if not variants:
            return None

        # Default to first variant alphabetically if no primary specified
        # IMPORTANT: Don't hardcode "local" - user may not have that variant
        default_variant = default_variant or sorted(variants)[0]

        # Use provided group_label or default to "Time Dimensions"
        effective_group_label = group_label if group_label is not None else "Time Dimensions"

        return {
            "name": "timezone_selector",
            "type": "unquoted",
            "label": "Timezone",
            "group_label": effective_group_label,
            "description": "Select timezone for time dimensions",
            "allowed_value": [
                {
                    "label": variant.upper(),  # "UTC", "LOCAL"
                    "value": f"_{variant}"     # "_utc", "_local"
                }
                for variant in sorted(variants)
            ],
            "default_value": f"_{default_variant}",  # "_local"
        }

    def _extract_base_column(self, variants: list["Dimension"]) -> str:
        """Extract base column name by removing variant suffix from expression.

        Uses the variant name from timezone_variant meta to strip the suffix
        from the dimension's expression, revealing the base column name.

        Args:
            variants: List of paired dimension variants (2+ dimensions with
                same canonical_name).

        Returns:
            Base column name without variant suffix (e.g., "rental_starts_at").

        Example:
            Given dimension with:
            - expr: "rental_starts_at_utc"
            - variant: "utc"

            Returns: "rental_starts_at"

        Note:
            - If expr doesn't end with expected suffix, returns expr as-is
            - Uses first variant in list for extraction
            - Handles custom naming conventions (user controls via variant field)
        """
        if not variants:
            raise ValueError("Cannot extract base column from empty variants list")

        # Use first variant's expression
        first = variants[0]
        expr = first.expr or first.name

        # Get variant suffix from meta
        if not first.config or not first.config.meta or not first.config.meta.timezone_variant:
            # Fallback if no timezone_variant (shouldn't happen but be safe)
            return expr

        variant = first.config.meta.timezone_variant.variant
        suffix = f"_{variant}"

        # Strip suffix if present
        if expr.endswith(suffix):
            return expr[:-len(suffix)]

        # Fallback: use as-is (user might have custom naming)
        return expr

    def _generate_toggleable_dimension_group(
        self,
        primary_dim: "Dimension",
        variants: list["Dimension"],
    ) -> dict:
        """Generate dimension_group with timezone toggle using parameter injection.

        Creates a dimension_group that switches between timezone variants using
        the timezone_selector parameter. Uses the pattern:
        ${TABLE}.base_column{% parameter timezone_selector %}

        Args:
            primary_dim: Primary dimension (is_primary=true) whose configuration
                is used for the generated dimension_group.
            variants: All dimensions in the variant group (2+ dimensions).

        Returns:
            Dictionary representation of LookML dimension_group with toggle logic.

        Example:
            Given:
            - base_column: "rental_starts_at"
            - variants: [starts_at (utc), starts_at_local (local)]

            Generates dimension_group with:
            sql: ${TABLE}.rental_starts_at{% parameter timezone_selector %}

            When user selects "UTC", expands to: rental_starts_at_utc
            When user selects "Local", expands to: rental_starts_at_local

        Note:
            - Label is used as-is from primary dimension (should be clean)
            - Description is enhanced with toggle instruction
            - Inherits all other properties from primary (convert_tz, group labels, etc.)
        """
        # Get base configuration from primary dimension
        result = primary_dim._to_dimension_group_dict(
            default_convert_tz=self.convert_tz,
            default_time_dimension_group_label=self.time_dimension_group_label,
            default_use_group_item_label=self.use_group_item_label,
        )

        # Extract base column name (strips variant suffix)
        base_column = self._extract_base_column(variants)

        # Generate SQL with parameter injection pattern
        result["sql"] = f"${{TABLE}}.{base_column}{{% parameter timezone_selector %}}"

        # Update description to mention toggle
        if "description" in result:
            result["description"] += " Use timezone selector to toggle timezone."
        else:
            result["description"] = "Use timezone selector to toggle timezone."

        # Label is used as-is from primary dimension
        # User should provide clean label (without timezone indicator)
        # No automatic cleaning - keep it simple and explicit

        return result

    def _process_timezone_variants(
        self,
        model: SemanticModel,
        tz_variant_groups: dict[str, list["Dimension"]],
        group_label: str | None = None,
    ) -> tuple[dict | None, set[str], dict[str, list["Dimension"]]]:
        """Process timezone variant groups to determine toggleable dimensions.

        Analyzes variant groups to identify:
        - Which dimensions should be toggleable (have 2+ variants)
        - Which dimensions should be skipped (non-primary variants)
        - The parameter dict for timezone selection

        Args:
            model: The semantic model being processed.
            tz_variant_groups: Groups from _group_timezone_variants().
            group_label: Optional group label for the timezone_selector parameter.
                Passed through to _generate_timezone_parameter().

        Returns:
            Tuple of (parameter_dict, skip_dimensions, toggleable_dimensions):
            - parameter_dict: LookML parameter for timezone selection, or None
            - skip_dimensions: Set of dimension names to exclude from output
            - toggleable_dimensions: Map of primary dim name -> all variants
        """
        skip_dimensions: set[str] = set()
        toggleable_dimensions: dict[str, list["Dimension"]] = {}

        for canonical_key, variants in tz_variant_groups.items():
            if len(variants) < 2:
                # Only 1 variant found - skip toggle (misconfiguration or incomplete pair)
                continue

            # Find primary variant
            primary = None
            for dim in variants:
                if dim.config.meta.timezone_variant.is_primary:
                    primary = dim
                    break

            # Fallback to first if no primary specified
            if primary is None:
                primary = variants[0]

            # Store primary dimension and its variants
            toggleable_dimensions[primary.name] = variants

            # Mark all non-primary variants for skipping
            for dim in variants:
                if dim != primary:
                    skip_dimensions.add(dim.name)

        # Generate timezone parameter if any toggleable dimensions exist
        parameter_dict = None
        if toggleable_dimensions:
            parameter_dict = self._generate_timezone_parameter(
                tz_variant_groups, group_label=group_label
            )

        return parameter_dict, skip_dimensions, toggleable_dimensions

    def _rebuild_dimension_groups(
        self,
        model: SemanticModel,
        existing_dimension_groups: list[dict],
        skip_dimensions: set[str],
        toggleable_dimensions: dict[str, list["Dimension"]],
    ) -> list[dict]:
        """Rebuild dimension_groups with timezone toggle logic.

        Processes existing dimension_groups, skipping non-primary variants
        and replacing primary variants with toggleable versions.

        Args:
            model: The semantic model being processed.
            existing_dimension_groups: Original dimension_groups from base view.
            skip_dimensions: Dimension names to exclude.
            toggleable_dimensions: Map of primary dim name -> all variants.

        Returns:
            New list of dimension_group dicts with toggle logic applied.
        """
        new_dimension_groups = []

        for dim_group in existing_dimension_groups:
            dim_name = dim_group.get("name")

            # Skip non-primary variants
            if dim_name in skip_dimensions:
                continue

            # Check if this is a toggleable time dimension
            if dim_name in toggleable_dimensions:
                # Find the dimension object
                primary_dim = next(
                    (d for d in model.dimensions if d.name == dim_name), None
                )
                if primary_dim:
                    # Regenerate with timezone toggle
                    toggleable_dim_group = self._generate_toggleable_dimension_group(
                        primary_dim=primary_dim,
                        variants=toggleable_dimensions[dim_name],
                    )
                    new_dimension_groups.append(toggleable_dim_group)
                else:
                    # Shouldn't happen, but keep original if we can't find dimension
                    new_dimension_groups.append(dim_group)
            else:
                # Keep original dimension group
                new_dimension_groups.append(dim_group)

        return new_dimension_groups

    def _filter_sets_for_skipped_dims(
        self,
        view_dict: dict,
        skip_dimensions: set[str],
    ) -> None:
        """Remove references to skipped dimensions from sets.

        Updates sets in-place to filter out timeframe fields that belong
        to skipped (non-primary) timezone variant dimensions.

        Args:
            view_dict: The view dictionary to modify in-place.
            skip_dimensions: Dimension names whose fields should be removed.
        """
        if not skip_dimensions or "sets" not in view_dict:
            return

        for set_dict in view_dict["sets"]:
            if "fields" not in set_dict:
                continue

            # Filter out any timeframe fields from skipped dimensions
            # e.g., "starts_at_local_time" starts with "starts_at_local"
            set_dict["fields"] = [
                field
                for field in set_dict["fields"]
                if not any(
                    field.startswith(f"{skip_dim}_") for skip_dim in skip_dimensions
                )
            ]

    def _add_parameter_to_view(
        self,
        view_dict: dict,
        parameter_dict: dict,
    ) -> dict:
        """Add timezone parameter to view with proper ordering.

        Creates a new view dict with the parameter inserted after
        name and sql_table_name but before other fields.

        Args:
            view_dict: The original view dictionary.
            parameter_dict: The timezone selector parameter.

        Returns:
            New view dict with parameter added.
        """
        ordered_view_dict: dict = {}
        ordered_view_dict["name"] = view_dict.get("name")
        if "sql_table_name" in view_dict:
            ordered_view_dict["sql_table_name"] = view_dict["sql_table_name"]

        # Add parameter
        ordered_view_dict["parameter"] = [parameter_dict]

        # Add remaining fields
        for key, value in view_dict.items():
            if key not in ["name", "sql_table_name", "parameter"]:
                ordered_view_dict[key] = value

        return ordered_view_dict

    def generate_view(
        self,
        model: SemanticModel,
        required_measures: set[str] | None = None,
    ) -> dict:
        """Generate LookML view dict from semantic model with timezone toggle support.

        This method enhances the standard view generation with timezone variant
        handling. When timezone_variant configuration is detected, it:
        1. Collapses variant pairs into single toggleable dimension_groups
        2. Generates a timezone_selector parameter
        3. Uses parameter injection for timezone switching

        Args:
            model: The semantic model to generate a view from.
            required_measures: Optional set of measure names that must be included
                regardless of bi_field status.

        Returns:
            Dictionary representation of LookML view with timezone toggle logic.

        Note:
            - Models without timezone_variant generate normally (backward compatible)
            - Non-primary variants are excluded from output
            - Parameter is added before dimensions in the view
        """
        # Start with base view dict from semantic model
        base_view_dict = model.to_lookml_dict(
            schema=self.schema,
            convert_tz=self.convert_tz,
            time_dimension_group_label=self.time_dimension_group_label,
            use_group_item_label=self.use_group_item_label,
            use_bi_field_filter=self.use_bi_field_filter,
            required_measures=required_measures,
        )

        # Extract the view from the wrapper dict
        if "views" not in base_view_dict or not base_view_dict["views"]:
            return base_view_dict

        view_dict = base_view_dict["views"][0]

        # Group dimensions by timezone variant
        tz_variant_groups = self._group_timezone_variants(model)

        if not tz_variant_groups:
            # No timezone variants - return base view as-is
            return base_view_dict

        # Process variant groups to get toggleable dimensions and skips
        parameter_dict, skip_dimensions, toggleable_dimensions = (
            self._process_timezone_variants(
                model, tz_variant_groups, group_label=self.time_dimension_group_label
            )
        )

        # Rebuild dimension_groups with toggle logic
        existing_dimension_groups = view_dict.get("dimension_groups", [])
        new_dimension_groups = self._rebuild_dimension_groups(
            model, existing_dimension_groups, skip_dimensions, toggleable_dimensions
        )
        if new_dimension_groups:
            view_dict["dimension_groups"] = new_dimension_groups

        # Filter sets to remove skipped dimension references
        self._filter_sets_for_skipped_dims(view_dict, skip_dimensions)

        # Add parameter to view with proper ordering
        if parameter_dict:
            view_dict = self._add_parameter_to_view(view_dict, parameter_dict)

        # Rebuild wrapper dict
        base_view_dict["views"][0] = view_dict

        return base_view_dict

    def _validate_metrics(
        self, metrics: list[Metric], models: list[SemanticModel]
    ) -> None:
        """Validate metrics for entity connectivity.

        Performs entity connectivity validation using the EntityConnectivityValidator.
        Raises LookMLValidationError if any validation errors are found. Warnings are
        logged but do not stop generation.

        Args:
            metrics: List of metrics to validate.
            models: List of semantic models for validation.

        Raises:
            LookMLValidationError: If validation errors are found.
        """
        from dbt_to_lookml.validation import EntityConnectivityValidator

        validator = EntityConnectivityValidator(models)
        result = validator.validate_metrics(metrics)

        if result.has_errors():
            console.print("[red]Validation errors:[/red]")
            console.print(result.format_report())
            error_count = len([i for i in result.issues if i.severity == "error"])
            raise LookMLValidationError(
                f"Metric validation failed with {error_count} errors"
            )

        if result.has_warnings():
            console.print("[yellow]Validation warnings:[/yellow]")
            console.print(result.format_report())

    def _find_model_by_primary_entity(
        self, entity_name: str, models: list[SemanticModel]
    ) -> SemanticModel | None:
        """Find a semantic model that has a primary entity with the given name.

        Args:
            entity_name: Name of the entity to search for.
            models: List of semantic models to search within.

        Returns:
            The semantic model with the matching primary entity, or None if not found.
        """
        for model in models:
            for entity in model.entities:
                if entity.name == entity_name and entity.type == "primary":
                    return model
        return None

    def _find_model_with_measure(
        self, measure_name: str, models: dict[str, SemanticModel]
    ) -> SemanticModel | None:
        """Find which semantic model contains the given measure.

        Args:
            measure_name: Name of the measure to search for.
            models: Dictionary mapping model names to SemanticModel objects.

        Returns:
            The semantic model containing the measure, or None if not found.
        """
        for model in models.values():
            for measure in model.measures:
                if measure.name == measure_name:
                    return model
        return None

    def _resolve_measure_reference(
        self, measure_name: str, primary_entity: str, models: dict[str, SemanticModel]
    ) -> str:
        """Resolve measure name to LookML reference syntax.

        Args:
            measure_name: Name of the measure to reference.
            primary_entity: Primary entity of the metric (determines "same view").
            models: Dictionary mapping model names to SemanticModel objects.

        Returns:
            LookML reference with suffix: "${measure_measure}" or
            "${view_prefix}{model}.{measure_measure}"

        Raises:
            ValueError: If measure not found in any model.
        """
        source_model = self._find_model_with_measure(measure_name, models)
        if not source_model:
            raise ValueError(
                f"Measure '{measure_name}' not found in any semantic model"
            )

        primary_model = self._find_model_by_primary_entity(
            primary_entity, list(models.values())
        )

        if not primary_model:
            raise ValueError(f"No model found with primary entity '{primary_entity}'")

        # Find the dbt Measure object to translate its name
        measure = next(m for m in source_model.measures if m.name == measure_name)
        lookml_name = self.get_measure_lookml_name(measure)

        # Same view reference (no prefix needed)
        if source_model.name == primary_model.name:
            return f"${{{lookml_name}}}"

        # Cross-view reference (apply view prefix)
        view_name = f"{self.view_prefix}{source_model.name}"
        return f"${{{view_name}.{lookml_name}}}"

    def _generate_simple_sql(
        self, metric: Metric, models: dict[str, SemanticModel]
    ) -> str:
        """Generate SQL for simple metric.

        Args:
            metric: The metric with SimpleMetricParams.
            models: Dictionary of all semantic models.

        Returns:
            LookML SQL expression referencing the measure.

        Raises:
            TypeError: If metric.type_params is not SimpleMetricParams.
            ValueError: If metric has no primary_entity.
        """
        from dbt_to_lookml.schemas import SimpleMetricParams

        if not isinstance(metric.type_params, SimpleMetricParams):
            raise TypeError(
                f"Expected SimpleMetricParams, got {type(metric.type_params)}"
            )

        measure_name = metric.type_params.measure
        primary_entity = metric.primary_entity

        if not primary_entity:
            raise ValueError(f"Metric '{metric.name}' has no primary_entity")

        return self._resolve_measure_reference(measure_name, primary_entity, models)

    def _generate_ratio_sql(
        self, metric: Metric, models: dict[str, SemanticModel]
    ) -> str:
        """Generate SQL for ratio metric.

        Args:
            metric: The metric with RatioMetricParams.
            models: Dictionary of all semantic models.

        Returns:
            LookML SQL expression: "1.0 * num / NULLIF(denom, 0)"

        Raises:
            TypeError: If metric.type_params is not RatioMetricParams.
            ValueError: If metric has no primary_entity.
        """
        from dbt_to_lookml.schemas import RatioMetricParams

        if not isinstance(metric.type_params, RatioMetricParams):
            raise TypeError(
                f"Expected RatioMetricParams, got {type(metric.type_params)}"
            )

        numerator = metric.type_params.numerator
        denominator = metric.type_params.denominator
        primary_entity = metric.primary_entity

        if not primary_entity:
            raise ValueError(f"Metric '{metric.name}' has no primary_entity")

        # Resolve numerator reference
        num_ref = self._resolve_measure_reference(numerator, primary_entity, models)

        # Resolve denominator reference
        denom_ref = self._resolve_measure_reference(denominator, primary_entity, models)

        # Build ratio SQL with null safety
        return f"1.0 * {num_ref} / NULLIF({denom_ref}, 0)"

    def _generate_derived_sql(
        self,
        metric: Metric,
        models: dict[str, SemanticModel],
        all_metrics: list[Metric],
    ) -> str:
        """Generate SQL for derived metric.

        NOTE: MVP implementation uses simple string replacement.
        Limitations: Does not handle complex expressions with operators/functions
        that might conflict with metric names.

        Args:
            metric: The metric with DerivedMetricParams.
            models: Dictionary of all semantic models.
            all_metrics: List of all metrics (to resolve metric references).

        Returns:
            LookML SQL expression with metric references replaced.

        Raises:
            TypeError: If metric.type_params is not DerivedMetricParams.
            ValueError: If metric has no primary_entity.
        """
        from dbt_to_lookml.schemas import DerivedMetricParams

        if not isinstance(metric.type_params, DerivedMetricParams):
            raise TypeError(
                f"Expected DerivedMetricParams, got {type(metric.type_params)}"
            )

        expr = metric.type_params.expr
        metric_refs = metric.type_params.metrics
        primary_entity = metric.primary_entity

        if not primary_entity:
            raise ValueError(f"Metric '{metric.name}' has no primary_entity")

        # Build replacement map: alias/metric_name → ${view.measure}
        # Use alias if provided (what appears in expr), otherwise metric name
        replacements = {}
        for ref in metric_refs:
            # Find the metric definition (metrics map to measures via same name)
            # This is a simplification - assumes metric name = measure name
            measure_name = ref.name
            measure_ref = self._resolve_measure_reference(
                measure_name, primary_entity, models
            )
            # Use alias as replacement key if provided, otherwise use metric name
            replacement_key = ref.alias if ref.alias else ref.name
            replacements[replacement_key] = measure_ref

        # Replace all aliases/metric names in expression with LookML measure references
        result_expr = expr
        for alias_or_name, measure_ref in replacements.items():
            result_expr = result_expr.replace(alias_or_name, measure_ref)

        return result_expr

    def _extract_required_fields(
        self,
        metric: Metric,
        primary_model: SemanticModel,
        all_models: list[SemanticModel],
    ) -> list[str]:
        """Extract required_fields list for metric.

        Only includes cross-view dependencies (measures from other views).

        Args:
            metric: The metric to extract dependencies from.
            primary_model: The semantic model that owns this metric.
            all_models: All available semantic models.

        Returns:
            Sorted list of required field references (e.g., ["view.measure"]).
        """
        from dbt_to_lookml.schemas import (
            DerivedMetricParams,
            RatioMetricParams,
            SimpleMetricParams,
        )

        required = set()

        # Extract measure references based on type
        measures = []
        if isinstance(metric.type_params, SimpleMetricParams):
            measures = [metric.type_params.measure]
        elif isinstance(metric.type_params, RatioMetricParams):
            measures = [metric.type_params.numerator, metric.type_params.denominator]
        elif isinstance(metric.type_params, DerivedMetricParams):
            # Extract from metric references (assume metric name = measure name)
            measures = [ref.name for ref in metric.type_params.metrics]

        # Build models lookup
        models_dict = {model.name: model for model in all_models}

        # Filter to cross-view references only
        for measure_name in measures:
            source_model = self._find_model_with_measure(measure_name, models_dict)
            if source_model and source_model.name != primary_model.name:
                # Find the dbt Measure object to translate its name
                measure = next(
                    m for m in source_model.measures if m.name == measure_name
                )
                lookml_name = self.get_measure_lookml_name(measure)
                view_name = f"{self.view_prefix}{source_model.name}"
                required.add(f"{view_name}.{lookml_name}")

        return sorted(list(required))

    def _infer_value_format(self, metric: Metric) -> str | None:
        """Infer LookML value_format_name from metric type and name.

        Priority:
        1. meta.value_format_name (explicit override)
        2. Ratio metrics → "percent_2"
        3. Names with "revenue" or "price" → "usd"
        4. Names with "count" → "decimal_0"
        5. Default → None (Looker default)

        Args:
            metric: The metric to infer format for.

        Returns:
            Format name or None.
        """
        from dbt_to_lookml.schemas import RatioMetricParams

        # Check explicit override first
        if metric.meta and "value_format_name" in metric.meta:
            return metric.meta["value_format_name"]

        if isinstance(metric.type_params, RatioMetricParams):
            return "percent_2"

        name_lower = metric.name.lower()
        if "revenue" in name_lower or "price" in name_lower:
            return "usd"
        if "count" in name_lower:
            return "decimal_0"

        return None

    def _infer_group_label(
        self, metric: Metric, primary_model: SemanticModel
    ) -> str | None:
        """Infer group_label for metric.

        Priority:
        1. metric.meta.category (if present)
        2. "{Model Name} Performance" (from primary model)

        Args:
            metric: The metric to infer label for.
            primary_model: The model that owns this metric.

        Returns:
            Group label string or None.
        """
        if metric.meta and "category" in metric.meta:
            category = metric.meta["category"]
            if isinstance(category, str):
                return _smart_title(category)

        # Default: "{Model} Performance"
        model_name = _smart_title(primary_model.name)
        return f"{model_name} Performance"

    def _generate_metric_measure(
        self,
        metric: Metric,
        primary_model: SemanticModel,
        all_models: list[SemanticModel],
        all_metrics: list[Metric] | None = None,
    ) -> dict[str, Any]:
        """Generate LookML measure dict from metric definition.

        Args:
            metric: The metric to convert.
            primary_model: The semantic model that owns this metric.
            all_models: All available semantic models.
            all_metrics: All metrics (needed for derived metric resolution).

        Returns:
            Complete LookML measure dictionary.

        Raises:
            ValueError: If metric type is unsupported or validation fails.
        """
        from dbt_to_lookml.schemas import (
            DerivedMetricParams,
            RatioMetricParams,
            SimpleMetricParams,
        )

        # Build models lookup dict for SQL generation
        models_dict = {model.name: model for model in all_models}

        # Generate SQL based on metric type
        if isinstance(metric.type_params, SimpleMetricParams):
            sql = self._generate_simple_sql(metric, models_dict)
        elif isinstance(metric.type_params, RatioMetricParams):
            sql = self._generate_ratio_sql(metric, models_dict)
        elif isinstance(metric.type_params, DerivedMetricParams):
            if all_metrics is None:
                raise ValueError("all_metrics required for derived metric generation")
            sql = self._generate_derived_sql(metric, models_dict, all_metrics)
        else:
            raise ValueError(f"Unsupported metric type: {type(metric.type_params)}")

        # Extract required fields
        required_fields = self._extract_required_fields(
            metric, primary_model, all_models
        )

        # Build measure dict (2 space prefix on view_label for sort order)
        measure_dict: dict[str, Any] = {
            "name": metric.name,
            "type": "number",  # Always number for cross-entity metrics
            "sql": sql,
            "view_label": "  Metrics",  # 2 spaces prefix for top sort order
        }

        # Add value format
        value_format = self._infer_value_format(metric)
        if value_format:
            measure_dict["value_format_name"] = value_format

        # Add optional fields
        if metric.label:
            measure_dict["label"] = metric.label
        if metric.description:
            measure_dict["description"] = metric.description
        if required_fields:
            measure_dict["required_fields"] = required_fields

        # Add group_label
        group_label = self._infer_group_label(metric, primary_model)
        if group_label:
            measure_dict["group_label"] = group_label

        return measure_dict

    def _identify_fact_models(self, models: list[SemanticModel]) -> list[SemanticModel]:
        """Identify which models should have explores generated.

        Args:
            models: List of semantic models to analyze.

        Returns:
            List of models that should have explores.
        """
        if self.fact_models is not None:
            # Explicit mode: only generate explores for specified models
            fact_model_set = set(self.fact_models)
            identified = [model for model in models if model.name in fact_model_set]

            # Warn about missing models
            found_names = {model.name for model in identified}
            missing = fact_model_set - found_names
            if missing:
                missing_list = ", ".join(missing)
                console.print(
                    f"[yellow]Warning: Fact models not found: {missing_list}[/yellow]"
                )

            return identified
        else:
            # No fact models specified - no explores will be generated
            return []

    def _infer_relationship(
        self, from_entity_type: str, to_entity_type: str, entity_name_match: bool
    ) -> str:
        """Infer the join relationship cardinality based on entity types.

        Args:
            from_entity_type: Entity type in the source model ('primary' or 'foreign').
            to_entity_type: Entity type in the target model ('primary' or 'foreign').
            entity_name_match: Whether the entity names match (e.g., both
                named 'rental').

        Returns:
            The relationship type: 'one_to_one' or 'many_to_one'.
        """
        # If both entities are primary with matching names,
        # it's a one-to-one relationship
        if (
            from_entity_type == "primary"
            and to_entity_type == "primary"
            and entity_name_match
        ):
            return "one_to_one"
        # Foreign to primary is many-to-one
        return "many_to_one"

    def _generate_sql_on_clause(
        self, from_view: str, from_entity: str, to_view: str, to_entity: str
    ) -> str:
        """Generate the SQL ON clause for a LookML join.

        Args:
            from_view: Name of the source view.
            from_entity: Name of the entity in the source view.
            to_view: Name of the target view.
            to_entity: Name of the entity in the target view.

        Returns:
            LookML-formatted SQL ON clause
            (e.g., "${from_view.entity} = ${to_view.entity}").
        """
        return f"${{{from_view}.{from_entity}}} = ${{{to_view}.{to_entity}}}"

    def _identify_metric_requirements(
        self,
        base_model: SemanticModel,
        metrics: list[Metric],
        all_models: list[SemanticModel],
    ) -> dict[str, set[str]]:
        """Identify measures from joined views required by cross-entity metrics.

        This method determines which measures from other semantic models need to be
        exposed in the explore's join definitions to support cross-entity metrics
        owned by the base model.

        A metric is "owned" by an explore if its primary_entity matches the explore's
        primary entity. Only owned metrics are considered when building requirements.

        Args:
            base_model: The semantic model serving as the explore base/spine.
            metrics: All metrics in the project.
            all_models: All semantic models for measure-to-model lookup.

        Returns:
            Dictionary mapping model name to set of required measure names.
            Example: {"rental_orders": {"rental_count"}, "users": {"user_count"}}

            Note: Model names in keys are unprefixed (internal representation).
            Measures from the base model itself are excluded.

        Example:
            >>> # Given search_conversion_rate metric owned by searches model
            >>> # that requires rental_count from rental_orders model
            >>> requirements = generator._identify_metric_requirements(
            ...     searches_model, [conversion_metric], all_models
            ... )
            >>> requirements
            {"rental_orders": {"rental_count"}}
        """
        from dbt_to_lookml.parsers.dbt_metrics import extract_measure_dependencies

        requirements: dict[str, set[str]] = {}

        # Find the primary entity name for this base model
        base_entity_name = None
        for entity in base_model.entities:
            if entity.type == "primary":
                base_entity_name = entity.name
                break

        if not base_entity_name:
            # No primary entity, can't own metrics
            return requirements

        # Filter to metrics owned by this explore
        owned_metrics = [m for m in metrics if m.primary_entity == base_entity_name]

        # Build model name → measures mapping for efficient lookup
        model_measures: dict[str, set[str]] = {}
        for model in all_models:
            model_measures[model.name] = {m.name for m in model.measures}

        # For each owned metric, extract measure dependencies
        for metric in owned_metrics:
            measure_deps = extract_measure_dependencies(metric)

            for measure_name in measure_deps:
                # Find which model owns this measure
                owner_model_name = None
                for model_name, measures in model_measures.items():
                    if measure_name in measures:
                        owner_model_name = model_name
                        break

                if not owner_model_name:
                    # Measure not found in any model - validation issue
                    # Log warning but don't fail (validation should catch this)
                    continue

                # Skip if measure is from the base model itself
                if owner_model_name == base_model.name:
                    continue

                # Add to requirements
                if owner_model_name not in requirements:
                    requirements[owner_model_name] = set()
                requirements[owner_model_name].add(measure_name)

        return requirements

    def _filter_fields_by_bi_field(
        self, model: SemanticModel, fields_list: list[str]
    ) -> list[str]:
        """Pass through fields list (filtering now happens at view generation).

        Previously this method expanded wildcards and filtered fields based on
        bi_field metadata. Now filtering happens earlier during view generation
        via the use_bi_field_filter parameter to SemanticModel.to_lookml_dict().
        This keeps explores clean by using dimension sets (dimensions_only*).

        Args:
            model: The semantic model (unused, kept for API compatibility).
            fields_list: The current list of field references.

        Returns:
            The same fields_list unchanged.
        """
        # Filtering now happens at view generation time
        # This method kept for API compatibility but no longer modifies fields
        return fields_list

    def _build_join_graph(
        self,
        fact_model: SemanticModel,
        all_models: list[SemanticModel],
        metrics: list[Metric] | None = None,
    ) -> list[dict[str, Any]]:
        """Build a complete join graph for a fact table including multi-hop joins.

        This method traverses foreign key relationships to build a complete join graph.
        It handles both direct joins (fact → dimension) and multi-hop joins
        (fact → dim1 → dim2), as in rentals → searches → sessions.

        When metrics are provided, join field lists are enhanced to include measures
        required by cross-entity metrics owned by the fact model.

        Args:
            fact_model: The fact table semantic model to build joins for.
            all_models: All available semantic models.
            metrics: Optional list of metrics to analyze for required measure exposure.

        Returns:
            List of join dictionaries with keys: view_name, sql_on, relationship,
            type, fields.
        """
        joins = []
        visited = set()  # Track models we've already joined to avoid cycles

        # Identify metric requirements if metrics provided
        metric_requirements: dict[str, set[str]] = {}
        if metrics:
            metric_requirements = self._identify_metric_requirements(
                fact_model, metrics, all_models
            )

        # Track the view names for models (with prefix applied)
        model_view_names = {
            model.name: f"{self.view_prefix}{model.name}" for model in all_models
        }

        fact_view_name = f"{self.view_prefix}{fact_model.name}"
        visited.add(fact_model.name)

        # Queue for BFS traversal: (source_model, source_view_name, depth)
        from collections import deque

        queue = deque([(fact_model, fact_view_name, 0)])

        # Track join paths to handle multi-hop joins correctly
        # Maps model_name → (parent_view_name, parent_entity_name)
        join_paths = {}

        while queue:
            current_model, current_view_name, depth = queue.popleft()

            # Limit to 2 hops maximum
            # (depth 0 = fact, depth 1 = direct, depth 2 = multi-hop)
            if depth >= 2:
                continue

            # Process all foreign key entities in the current model
            for entity in current_model.entities:
                if entity.type != "foreign":
                    continue

                # Find the target model with this entity as primary key
                target_model = self._find_model_by_primary_entity(
                    entity.name, all_models
                )

                if not target_model or target_model.name in visited:
                    continue

                # Mark as visited to prevent cycles
                visited.add(target_model.name)

                target_view_name = model_view_names[target_model.name]

                # Find the primary entity in the target model
                target_primary_entity = None
                for target_entity in target_model.entities:
                    if (
                        target_entity.name == entity.name
                        and target_entity.type == "primary"
                    ):
                        target_primary_entity = target_entity
                        break

                if not target_primary_entity:
                    continue

                # Determine relationship cardinality
                # Check if both source and target have the same entity name as primary
                source_primary_entity = None
                for src_entity in current_model.entities:
                    if src_entity.type == "primary" and src_entity.name == entity.name:
                        source_primary_entity = src_entity
                        break

                entity_name_match = source_primary_entity is not None
                from_entity_type = (
                    source_primary_entity.type if source_primary_entity else "foreign"
                )
                to_entity_type = target_primary_entity.type

                relationship = self._infer_relationship(
                    from_entity_type, to_entity_type, entity_name_match
                )

                # Check for explicit join_cardinality override on the foreign entity
                # This allows users to declare one-to-one relationships when the
                # automatic inference would be incorrect (e.g., when target has
                # different primary key but relationship is still semantically 1:1)
                # TODO: Future enhancement - support reverse join discovery where
                # models that have FKs TO the fact model can be discovered and
                # joined automatically. See: https://github.com/...
                if entity.config and entity.config.meta:
                    explicit_cardinality = entity.config.meta.join_cardinality
                    if explicit_cardinality:
                        relationship = explicit_cardinality

                # Generate SQL ON clause
                sql_on = self._generate_sql_on_clause(
                    current_view_name,
                    entity.name,
                    target_view_name,
                    target_primary_entity.name,
                )

                # Create join block with fields list
                fields_list: list[str] = [f"{target_view_name}.dimensions_only*"]

                # For one-to-one relationships, include ALL measures from joined view
                # This is safe because there's no aggregation fan-out risk
                if relationship == "one_to_one":
                    for measure in target_model.measures:
                        lookml_name = self.get_measure_lookml_name(measure)
                        measure_ref = f"{target_view_name}.{lookml_name}"
                        if measure_ref not in fields_list:
                            fields_list.append(measure_ref)

                # Enhance fields list with required measures for cross-entity metrics
                # (This handles many_to_one joins that need specific measures)
                if target_model.name in metric_requirements:
                    required_measures = sorted(metric_requirements[target_model.name])
                    for measure_name in required_measures:
                        # Find the dbt Measure object to translate its name
                        measure = next(
                            m for m in target_model.measures if m.name == measure_name
                        )
                        lookml_name = self.get_measure_lookml_name(measure)
                        measure_ref = f"{target_view_name}.{lookml_name}"
                        if measure_ref not in fields_list:
                            fields_list.append(measure_ref)

                # Apply bi_field filtering if enabled
                fields_list = self._filter_fields_by_bi_field(target_model, fields_list)

                join = {
                    "view_name": target_view_name,
                    "sql_on": sql_on,
                    "relationship": relationship,
                    "type": "left_outer",
                    "fields": fields_list,
                }

                joins.append(join)

                # Add to queue for multi-hop processing
                queue.append((target_model, target_view_name, depth + 1))

                # Track the join path for this model
                join_paths[target_model.name] = (current_view_name, entity.name)

        return joins

    def generate(
        self,
        models: list[SemanticModel],
        metrics: list[Metric] | None = None,
        validate: bool = True,
    ) -> dict[str, str]:
        """Generate LookML files from semantic models and metrics.

        Args:
            models: List of semantic models to generate from.
            metrics: Optional list of metrics to generate measures for.
            validate: If True, run entity connectivity validation before generation.

        Returns:
            Dictionary mapping filename to file content.

        Raises:
            LookMLValidationError: If metric validation fails.
        """
        files = {}

        console.print(
            f"[bold blue]Processing {len(models)} semantic models...[/bold blue]"
        )
        if metrics:
            console.print(
                f"[bold blue]Processing {len(metrics)} metrics...[/bold blue]"
            )

            # Late validation before generation
            if validate:
                self._validate_metrics(metrics, models)

        # Build metric ownership mapping: model_name → [metrics]
        metric_map: dict[str, list[Metric]] = {}
        if metrics:
            for metric in metrics:
                primary_entity = metric.primary_entity
                if not primary_entity:
                    console.print(
                        f"[yellow]Warning: Metric '{metric.name}' has no "
                        f"primary_entity, skipping[/yellow]"
                    )
                    continue

                # Find model with this primary entity
                owner_model = self._find_model_by_primary_entity(primary_entity, models)
                if not owner_model:
                    console.print(
                        f"[yellow]Warning: No model found for "
                        f"primary_entity '{primary_entity}', "
                        f"skipping metric '{metric.name}'[/yellow]"
                    )
                    continue

                if owner_model.name not in metric_map:
                    metric_map[owner_model.name] = []
                metric_map[owner_model.name].append(metric)

        # Calculate required measures for each model from bi_field metrics
        # This ensures measures needed by metrics are included even without bi_field
        required_measures_map: dict[str, set[str]] = {}
        if self.use_bi_field_filter and metrics:
            from dbt_to_lookml.parsers.dbt_metrics import extract_measure_dependencies

            for metric in metrics:
                # Check if metric has bi_field: true (in meta dict)
                has_bi_field = (
                    metric.meta
                    and metric.meta.get("bi_field") is True
                )
                if not has_bi_field:
                    continue

                # Find the owner model for this metric
                primary_entity = metric.primary_entity
                if not primary_entity:
                    continue
                owner_model = self._find_model_by_primary_entity(primary_entity, models)
                if not owner_model:
                    continue

                # Extract measure dependencies and add to required set
                measure_deps = extract_measure_dependencies(metric)
                if owner_model.name not in required_measures_map:
                    required_measures_map[owner_model.name] = set()
                required_measures_map[owner_model.name].update(measure_deps)

        # Generate individual view files
        for i, model in enumerate(models, 1):
            console.print(
                f"  [{i}/{len(models)}] Processing [cyan]{model.name}[/cyan]..."
            )

            # Get required measures for this model (from bi_field metrics)
            required_measures = required_measures_map.get(model.name)

            # Generate view content
            view_content = self._generate_view_lookml(model, required_measures)

            # Check if we need to add metrics to this view
            owned_metrics = metric_map.get(model.name, [])
            if owned_metrics:
                console.print(
                    f"    Adding {len(owned_metrics)} metric(s) to {model.name}"
                )

                # Parse the existing view content back to dict to append measures
                view_dict = lkml.load(view_content)

                # Generate metric measures (filter by bi_field if enabled)
                metric_measures = []
                for metric in owned_metrics:
                    # Skip metrics without bi_field when filtering is enabled
                    if self.use_bi_field_filter:
                        has_bi_field = (
                            metric.meta and metric.meta.get("bi_field") is True
                        )
                        if not has_bi_field:
                            continue

                    try:
                        measure_dict = self._generate_metric_measure(
                            metric, model, models, metrics
                        )
                        metric_measures.append(measure_dict)
                    except Exception as e:
                        console.print(
                            f"[red]Error generating metric '{metric.name}': {e}[/red]"
                        )

                # Append to existing measures in view_dict
                if metric_measures:
                    if "measures" not in view_dict["views"][0]:
                        view_dict["views"][0]["measures"] = []
                    view_dict["views"][0]["measures"].extend(metric_measures)

                    # Re-dump to LookML
                    dumped_content = lkml.dump(view_dict)
                    if dumped_content is not None:
                        view_content = dumped_content
                        if self.format_output:
                            view_content = self._format_lookml_content(view_content)

            # Add to files dict with sanitized filename
            view_name = f"{self.view_prefix}{model.name}"
            clean_view_name = self._sanitize_filename(view_name)
            filename = f"{clean_view_name}.view.lkml"

            files[filename] = view_content
            console.print(f"    [green]✓[/green] Generated {filename}")

        # Generate explores file if there are models
        if models:
            console.print("[bold blue]Generating explores file...[/bold blue]")
            explores_content = self._generate_explores_lookml(models, metrics)
            files["explores.lkml"] = explores_content
            console.print("  [green]✓[/green] Generated explores.lkml")

        # Generate model file if there are models
        if models:
            console.print("[bold blue]Generating model file...[/bold blue]")
            model_content = self._generate_model_lookml()
            model_filename = f"{self._sanitize_filename(self.model_name)}.model.lkml"
            files[model_filename] = model_content
            console.print(f"  [green]✓[/green] Generated {model_filename}")

        return files

    def validate_output(self, content: str) -> tuple[bool, str]:
        """Validate LookML syntax.

        Args:
            content: LookML content to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            # Attempt to parse the content
            parsed = lkml.load(content)
            if parsed is None:
                return False, "Failed to parse LookML content"
            return True, ""
        except Exception as e:
            return False, f"Invalid LookML syntax: {str(e)}"

    def generate_lookml_files(
        self,
        semantic_models: list[SemanticModel],
        output_dir: Path,
        dry_run: bool = False,
    ) -> tuple[list[Path], list[str]]:
        """Generate LookML files from semantic models (backward compatibility method).

        This method maintains backward compatibility with existing code.

        Args:
            semantic_models: List of semantic models to convert.
            output_dir: Directory to write LookML files to.
            dry_run: If True, preview what would be generated without writing files.

        Returns:
            Tuple of (generated_files, validation_errors)
        """
        # Generate files using new interface
        files = self.generate(semantic_models)

        # Write files using base class method
        written_files, validation_errors = self.write_files(
            output_dir, files, dry_run=dry_run, verbose=True
        )

        return written_files, validation_errors

    def _generate_view_lookml(
        self,
        semantic_model: SemanticModel,
        required_measures: set[str] | None = None,
    ) -> str:
        """Generate LookML content for a semantic model or LookMLView.

        Args:
            semantic_model: The semantic model or LookMLView to generate content for.
            required_measures: Optional set of measure names that must be included
                regardless of bi_field status (e.g., measures needed by metrics).

        Returns:
            The LookML content as a string.
        """
        from dbt_to_lookml.schemas import LookMLView

        # Handle both SemanticModel and LookMLView objects
        if isinstance(semantic_model, LookMLView):
            # LookMLView.to_lookml_dict() doesn't accept parameters
            view_dict = semantic_model.to_lookml_dict()
        elif isinstance(semantic_model, SemanticModel):
            # Apply view prefix if configured
            if self.view_prefix:
                prefixed_model = SemanticModel(
                    name=f"{self.view_prefix}{semantic_model.name}",
                    **{
                        k: v
                        for k, v in semantic_model.model_dump().items()
                        if k != "name"
                    },
                )
                # Use new generate_view() method with timezone toggle support
                view_dict = self.generate_view(
                    model=prefixed_model,
                    required_measures=required_measures,
                )
            else:
                # Use new generate_view() method with timezone toggle support
                view_dict = self.generate_view(
                    model=semantic_model,
                    required_measures=required_measures,
                )
        else:
            raise TypeError(
                f"Expected SemanticModel or LookMLView, got {type(semantic_model)}"
            )

        result = lkml.dump(view_dict)
        formatted_result = result if result is not None else ""

        if self.format_output:
            formatted_result = self._format_lookml_content(formatted_result)

        return formatted_result

    def _generate_model_lookml(self) -> str:
        """Generate LookML model file content.

        The model file defines the connection and includes explore and view files.

        Returns:
            LookML model file content as a string.
        """
        model_dict = {
            "connection": self.connection,
            "include": ["explores.lkml", "*.view.lkml"],
        }

        result = lkml.dump(model_dict)
        formatted_result = result if result is not None else ""

        if self.format_output:
            formatted_result = self._format_lookml_content(formatted_result)

        return formatted_result

    def _generate_explores_lookml(
        self, semantic_models: list[SemanticModel], metrics: list[Metric] | None = None
    ) -> str:
        """Generate LookML content for explores from semantic models.

        Only generates explores for fact tables (models with measures) and includes
        automatic join graph generation based on entity relationships.

        Args:
            semantic_models: List of semantic models to create explores for.
            metrics: Optional list of metrics for metric-aware join generation.

        Returns:
            The LookML content as a string with include statements and explores.
        """
        # Generate include statements for all view files
        include_statements = []
        for model in semantic_models:
            view_filename = f"{self.view_prefix}{model.name}.view.lkml"
            include_statements.append(f'include: "{view_filename}"')

        # Identify fact models (requires explicit --fact-models flag)
        fact_models = self._identify_fact_models(semantic_models)

        if self.fact_models is not None:
            count = len(fact_models)
            console.print(
                f"[blue]Generating {count} explores from specified fact models[/blue]"
            )
        else:
            msg = "No fact models specified. Use --fact-models to generate explores."
            console.print(f"[yellow]{msg}[/yellow]")
            console.print("[dim]Example: --fact-models rentals,orders[/dim]")

        explores = []

        # Generate explores only for fact models with join graphs
        for fact_model in fact_models:
            explore_name = f"{self.explore_prefix}{fact_model.name}"
            view_name = f"{self.view_prefix}{fact_model.name}"

            explore_dict: dict[str, Any] = {
                "name": explore_name,
                "from": view_name,
            }

            if fact_model.description:
                explore_dict["description"] = fact_model.description

            # Build join graph for this fact model
            joins = self._build_join_graph(fact_model, semantic_models, metrics)

            # Add joins to explore if any exist
            if joins:
                # Convert join dicts to LookML format
                # lkml library expects 'joins' as a list of dicts
                # with specific structure
                explore_dict["joins"] = []
                for join in joins:
                    join_dict = {
                        "name": join["view_name"],
                        "sql_on": join["sql_on"],
                        "relationship": join["relationship"],
                        "type": join["type"],
                        "fields": join["fields"],
                    }
                    explore_dict["joins"].append(join_dict)

            # Add always_filter for timezone_selector if fact model has timezone variants
            if self._has_timezone_variants(fact_model):
                explore_dict["always_filter"] = {
                    "filters": [f"{view_name}.timezone_selector: \"\""]
                }

            explores.append(explore_dict)

        # Combine include statements and explores
        result_parts = []

        # Add include statements
        if include_statements:
            result_parts.append("\n".join(include_statements))

        # Generate LookML for explores (only if there are explores to generate)
        if explores:
            result_parts.append("")  # Blank line before explores
            explores_content = lkml.dump({"explores": explores})
            if explores_content:
                result_parts.append(explores_content)

        formatted_result = "\n".join(result_parts)

        if self.format_output and formatted_result.strip():
            formatted_result = self._format_lookml_content(formatted_result)

        return formatted_result

    def _format_lookml_content(self, content: str) -> str:
        """Format LookML content for better readability.

        Args:
            content: The raw LookML content to format.

        Returns:
            Formatted LookML content.
        """
        if not content.strip():
            return content

        lines = content.split("\n")
        formatted_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append("")
                continue

            # Decrease indent for closing braces
            if stripped == "}":
                indent_level = max(0, indent_level - 1)

            # Add line with proper indentation
            formatted_lines.append("  " * indent_level + stripped)

            # Increase indent after opening braces and certain keywords
            if (
                stripped.endswith("{")
                or stripped.startswith("view:")
                or stripped.startswith("explore:")
                or stripped.startswith("dimension:")
                or stripped.startswith("measure:")
                or stripped.startswith("dimension_group:")
            ):
                indent_level += 1

        return "\n".join(formatted_lines)

    def get_generation_summary(
        self,
        semantic_models: list[SemanticModel],
        generated_files: list[Path],
        validation_errors: list[str],
    ) -> str:
        """Generate a summary of the generation process.

        Args:
            semantic_models: The semantic models that were processed.
            generated_files: List of files that were generated.
            validation_errors: List of validation errors encountered.

        Returns:
            A formatted summary string.
        """
        summary_lines = []
        summary_lines.append("=" * 60)
        summary_lines.append("LookML Generation Summary")
        summary_lines.append("=" * 60)
        summary_lines.append("")

        summary_lines.append(f"Processed semantic models: {len(semantic_models)}")
        summary_lines.append(f"Generated files: {len(generated_files)}")
        summary_lines.append(f"Validation errors: {len(validation_errors)}")
        summary_lines.append("")

        if generated_files:
            summary_lines.append("Generated Files:")
            for file_path in generated_files:
                summary_lines.append(f"  - {file_path}")
            summary_lines.append("")

        if validation_errors:
            summary_lines.append("Validation Errors:")
            for error in validation_errors:
                summary_lines.append(f"  - {error}")
            summary_lines.append("")

        # Count statistics
        view_count = sum(1 for f in generated_files if f.name.endswith(".view.lkml"))
        explore_count = sum(1 for f in generated_files if f.name == "explores.lkml")

        summary_lines.append("Statistics:")
        summary_lines.append(f"  - View files: {view_count}")
        summary_lines.append(f"  - Explore files: {explore_count}")
        summary_lines.append("")

        return "\n".join(summary_lines)

    def _validate_lookml_syntax(self, content: str) -> None:
        """Validate LookML syntax (backward compatibility method).

        Args:
            content: LookML content to validate.

        Raises:
            LookMLValidationError: If the LookML syntax is invalid.
        """
        is_valid, error_msg = self.validate_output(content)
        if not is_valid:
            raise LookMLValidationError(error_msg)

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a name for use as a filename.

        Args:
            name: The name to sanitize.

        Returns:
            A filename-safe version of the name.
        """
        import re

        # Replace spaces and special characters with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)

        # Remove multiple consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)

        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")

        # Ensure it's not empty and starts with a letter or underscore
        if not sanitized or sanitized[0].isdigit():
            sanitized = f"view_{sanitized}"

        return sanitized.lower()
