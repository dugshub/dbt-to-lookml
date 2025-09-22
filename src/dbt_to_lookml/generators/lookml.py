"""Generator for creating LookML files from semantic models."""

from pathlib import Path
from typing import Dict, List, Tuple

import lkml
from rich.console import Console

from dbt_to_lookml.interfaces.generator import Generator
from dbt_to_lookml.models import SemanticModel

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
        format_output: bool = True
    ) -> None:
        """Initialize the generator.

        Args:
            view_prefix: Prefix to add to view names.
            explore_prefix: Prefix to add to explore names.
            validate_syntax: Whether to validate generated LookML syntax.
            format_output: Whether to format LookML output for readability.
        """
        super().__init__(
            validate_syntax=validate_syntax,
            format_output=format_output,
            view_prefix=view_prefix,
            explore_prefix=explore_prefix
        )
        self.view_prefix = view_prefix
        self.explore_prefix = explore_prefix
        # Backward compatibility attribute
        class MapperCompat:
            def __init__(self, vp, ep):
                self.view_prefix = vp
                self.explore_prefix = ep
            def semantic_model_to_view(self, model):
                # Stub method for backward compatibility
                return model
        self.mapper = MapperCompat(view_prefix, explore_prefix)

    def generate(self, models: List[SemanticModel]) -> Dict[str, str]:
        """Generate LookML files from semantic models.

        Args:
            models: List of semantic models to generate from.

        Returns:
            Dictionary mapping filename to file content.
        """
        files = {}

        console.print(f"[bold blue]Processing {len(models)} semantic models...[/bold blue]")

        # Generate individual view files
        for i, model in enumerate(models, 1):
            console.print(f"  [{i}/{len(models)}] Processing [cyan]{model.name}[/cyan]...")

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

        return files

    def validate_output(self, content: str) -> Tuple[bool, str]:
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
        semantic_models: List[SemanticModel],
        output_dir: Path,
        dry_run: bool = False,
    ) -> Tuple[List[Path], List[str]]:
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

    def _generate_view_lookml(self, semantic_model) -> str:
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
                    **{k: v for k, v in semantic_model.model_dump().items() if k != 'name'}
                )
                view_dict = prefixed_model.to_lookml_dict()
            else:
                view_dict = semantic_model.to_lookml_dict()
        else:
            raise TypeError(f"Expected SemanticModel or LookMLView, got {type(semantic_model)}")

        result = lkml.dump(view_dict)
        formatted_result = result if result is not None else ""

        if self.format_output:
            formatted_result = self._format_lookml_content(formatted_result)

        return formatted_result

    def _generate_explores_lookml(self, semantic_models: List[SemanticModel]) -> str:
        """Generate LookML content for explores from semantic models.

        Args:
            semantic_models: List of semantic models to create explores for.

        Returns:
            The LookML content as a string.
        """
        explores = []

        for model in semantic_models:
            explore_name = f"{self.explore_prefix}{model.name}"
            view_name = f"{self.view_prefix}{model.name}"

            explore_dict = {
                'name': explore_name,
                'type': 'table',
                'from': view_name,
            }
            if model.description:
                explore_dict['description'] = model.description

            explores.append(explore_dict)

        # Handle empty explores list to maintain structure
        if not explores:
            formatted_result = "explore:\n"
        else:
            result = lkml.dump({'explores': explores})
            formatted_result = result if result is not None else ""

            if self.format_output:
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

        lines = content.split('\n')
        formatted_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append('')
                continue

            # Decrease indent for closing braces
            if stripped == '}':
                indent_level = max(0, indent_level - 1)

            # Add line with proper indentation
            formatted_lines.append('  ' * indent_level + stripped)

            # Increase indent after opening braces and certain keywords
            if (stripped.endswith('{') or
                stripped.startswith('view:') or
                stripped.startswith('explore:') or
                stripped.startswith('dimension:') or
                stripped.startswith('measure:') or
                stripped.startswith('dimension_group:')):
                indent_level += 1

        return '\n'.join(formatted_lines)

    def get_generation_summary(
        self,
        semantic_models: List[SemanticModel],
        generated_files: List[Path],
        validation_errors: List[str]
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
        view_count = sum(1 for f in generated_files if f.name.endswith('.view.lkml'))
        explore_count = sum(1 for f in generated_files if f.name == 'explores.lkml')

        summary_lines.append("Statistics:")
        summary_lines.append(f"  - View files: {view_count}")
        summary_lines.append(f"  - Explore files: {explore_count}")
        summary_lines.append("")

        return '\n'.join(summary_lines)

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
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)

        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)

        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')

        # Ensure it's not empty and starts with a letter or underscore
        if not sanitized or sanitized[0].isdigit():
            sanitized = f"view_{sanitized}"

        return sanitized.lower()