"""Generator for creating LookML files from semantic models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import lkml
from rich.console import Console

from dbt_to_lookml.interfaces.generator import Generator
from dbt_to_lookml.schemas import SemanticModel

console = Console()


class LookMLValidationError(Exception):
    """Exception raised when LookML validation fails."""

    pass


class LookMLGenerator(Generator):
    """Generates LookML files from semantic models with validation and advanced features."""

    def __init__(
        self,
        view_prefix: str = "",
        explore_prefix: str = "",
        validate_syntax: bool = True,
        format_output: bool = True,
        schema: str = "",
        connection: str = "redshift_test",
        model_name: str = "semantic_model",
    ) -> None:
        """Initialize the generator.

        Args:
            view_prefix: Prefix to add to view names.
            explore_prefix: Prefix to add to explore names.
            validate_syntax: Whether to validate generated LookML syntax.
            format_output: Whether to format LookML output for readability.
            schema: Database schema name for sql_table_name.
            connection: Looker connection name for the model file.
            model_name: Name for the generated model file (without .model.lkml extension).
        """
        super().__init__(
            validate_syntax=validate_syntax,
            format_output=format_output,
            view_prefix=view_prefix,
            explore_prefix=explore_prefix,
            schema=schema,
        )
        self.view_prefix = view_prefix
        self.explore_prefix = explore_prefix
        self.schema = schema
        self.connection = connection
        self.model_name = model_name

        # Backward compatibility attribute
        class MapperCompat:
            def __init__(self, vp: str, ep: str) -> None:
                self.view_prefix = vp
                self.explore_prefix = ep

            def semantic_model_to_view(self, model: SemanticModel) -> SemanticModel:
                # Stub method for backward compatibility
                return model

        self.mapper = MapperCompat(view_prefix, explore_prefix)

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

    def _identify_fact_models(self, models: list[SemanticModel]) -> list[SemanticModel]:
        """Identify fact tables (models with measures) that should become base explores.

        Args:
            models: List of semantic models to analyze.

        Returns:
            List of semantic models that have measures (fact tables).
        """
        return [model for model in models if len(model.measures) > 0]

    def _infer_relationship(
        self, from_entity_type: str, to_entity_type: str, entity_name_match: bool
    ) -> str:
        """Infer the join relationship cardinality based on entity types.

        Args:
            from_entity_type: Entity type in the source model ('primary' or 'foreign').
            to_entity_type: Entity type in the target model ('primary' or 'foreign').
            entity_name_match: Whether the entity names match (e.g., both named 'rental').

        Returns:
            The relationship type: 'one_to_one' or 'many_to_one'.
        """
        # If both entities are primary with matching names, it's a one-to-one relationship
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
            LookML-formatted SQL ON clause (e.g., "${from_view.entity} = ${to_view.entity}").
        """
        return f"${{{from_view}.{from_entity}}} = ${{{to_view}.{to_entity}}}"

    def _build_join_graph(
        self, fact_model: SemanticModel, all_models: list[SemanticModel]
    ) -> list[dict[str, Any]]:
        """Build a complete join graph for a fact table including multi-hop joins.

        This method traverses foreign key relationships to build a complete join graph.
        It handles both direct joins (fact → dimension) and multi-hop joins
        (fact → dim1 → dim2), as in rentals → searches → sessions.

        Args:
            fact_model: The fact table semantic model to build joins for.
            all_models: All available semantic models.

        Returns:
            List of join dictionaries with keys: view_name, sql_on, relationship, type, fields.
        """
        joins = []
        visited = set()  # Track models we've already joined to avoid cycles

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

            # Limit to 2 hops maximum (depth 0 = fact, depth 1 = direct, depth 2 = multi-hop)
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

                # Generate SQL ON clause
                sql_on = self._generate_sql_on_clause(
                    current_view_name,
                    entity.name,
                    target_view_name,
                    target_primary_entity.name,
                )

                # Create join block
                join = {
                    "view_name": target_view_name,
                    "sql_on": sql_on,
                    "relationship": relationship,
                    "type": "left_outer",
                    "fields": [f"{target_view_name}.dimensions_only*"],
                }

                joins.append(join)

                # Add to queue for multi-hop processing
                queue.append((target_model, target_view_name, depth + 1))

                # Track the join path for this model
                join_paths[target_model.name] = (current_view_name, entity.name)

        return joins

    def generate(self, models: list[SemanticModel]) -> dict[str, str]:
        """Generate LookML files from semantic models.

        Args:
            models: List of semantic models to generate from.

        Returns:
            Dictionary mapping filename to file content.
        """
        files = {}

        console.print(
            f"[bold blue]Processing {len(models)} semantic models...[/bold blue]"
        )

        # Generate individual view files
        for i, model in enumerate(models, 1):
            console.print(
                f"  [{i}/{len(models)}] Processing [cyan]{model.name}[/cyan]..."
            )

            # Generate view content
            view_content = self._generate_view_lookml(model)

            # Add to files dict with sanitized filename
            view_name = f"{self.view_prefix}{model.name}"
            clean_view_name = self._sanitize_filename(view_name)
            filename = f"{clean_view_name}.view.lkml"

            files[filename] = view_content
            console.print(f"    [green]✓[/green] Generated {filename}")

        # Generate explores file if there are models
        if models:
            console.print("[bold blue]Generating explores file...[/bold blue]")
            explores_content = self._generate_explores_lookml(models)
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

    def _generate_view_lookml(self, semantic_model: SemanticModel) -> str:
        """Generate LookML content for a semantic model or LookMLView.

        Args:
            semantic_model: The semantic model or LookMLView to generate content for.

        Returns:
            The LookML content as a string.
        """
        from dbt_to_lookml.schemas import LookMLView

        # Handle both SemanticModel and LookMLView objects
        if isinstance(semantic_model, LookMLView):
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
                view_dict = prefixed_model.to_lookml_dict(schema=self.schema)
            else:
                view_dict = semantic_model.to_lookml_dict(schema=self.schema)
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

    def _generate_explores_lookml(self, semantic_models: list[SemanticModel]) -> str:
        """Generate LookML content for explores from semantic models.

        Only generates explores for fact tables (models with measures) and includes
        automatic join graph generation based on entity relationships.

        Args:
            semantic_models: List of semantic models to create explores for.

        Returns:
            The LookML content as a string with include statements and explores.
        """
        # Generate include statements for all view files
        include_statements = []
        for model in semantic_models:
            view_filename = f"{self.view_prefix}{model.name}.view.lkml"
            include_statements.append(f'include: "{view_filename}"')

        # Identify fact models (those with measures)
        fact_models = self._identify_fact_models(semantic_models)

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
            joins = self._build_join_graph(fact_model, semantic_models)

            # Add joins to explore if any exist
            if joins:
                # Convert join dicts to LookML format
                # lkml library expects 'joins' as a list of dicts with specific structure
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

            explores.append(explore_dict)

        # Combine include statements and explores
        result_parts = []

        # Add include statements
        if include_statements:
            result_parts.append("\n".join(include_statements))
            result_parts.append("")  # Blank line after includes

        # Handle empty explores list to maintain structure
        if not explores:
            result_parts.append("explore:\n")
        else:
            # Generate LookML for explores
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
