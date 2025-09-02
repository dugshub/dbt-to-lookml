"""Generator for creating LookML files from semantic models."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import lkml
from rich.console import Console

from dbt_to_lookml.mapper import SemanticModelMapper
from dbt_to_lookml.models import LookMLExplore, LookMLView, SemanticModel

console = Console()


class LookMLValidationError(Exception):
    """Exception raised when LookML validation fails."""
    pass


class LookMLGenerator:
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
        self.mapper = SemanticModelMapper(
            view_prefix=view_prefix,
            explore_prefix=explore_prefix,
        )
        self.validate_syntax = validate_syntax
        self.format_output = format_output

    def generate_lookml_files(
        self,
        semantic_models: List[SemanticModel],
        output_dir: Path,
        dry_run: bool = False,
    ) -> Tuple[List[Path], List[str]]:
        """Generate LookML files from semantic models.

        Args:
            semantic_models: List of semantic models to convert.
            output_dir: Directory to write LookML files to.
            dry_run: If True, preview what would be generated without writing files.

        Returns:
            Tuple of (generated_files, validation_errors)
        """
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)

        generated_files = []
        validation_errors = []
        views = []
        explores = []

        console.print(f"[bold blue]Processing {len(semantic_models)} semantic models...[/bold blue]")

        for i, semantic_model in enumerate(semantic_models, 1):
            try:
                console.print(f"  [{i}/{len(semantic_models)}] Processing [cyan]{semantic_model.name}[/cyan]...")
                
                # Generate view
                view = self.mapper.semantic_model_to_view(semantic_model)
                views.append(view)

                # Generate view content
                view_content = self._generate_view_lookml(view)
                
                # Validate syntax if enabled
                if self.validate_syntax:
                    try:
                        self._validate_lookml_syntax(view_content)
                        console.print(f"    [green]✓[/green] View syntax valid")
                    except LookMLValidationError as e:
                        validation_errors.append(f"View {view.name}: {e}")
                        console.print(f"    [red]✗[/red] View syntax error: {e}")

                # Generate view file with sanitized name
                clean_view_name = self._sanitize_filename(view.name)
                view_file = output_dir / f"{clean_view_name}.view.lkml"
                generated_files.append(view_file)
                
                if dry_run:
                    console.print(f"    [yellow]Would create:[/yellow] {view_file}")
                    console.print(f"    [dim]Content preview (first 3 lines):[/dim]")
                    lines = view_content.strip().split('\n')[:3]
                    for line in lines:
                        console.print(f"    [dim]  {line}[/dim]")
                else:
                    with open(view_file, 'w', encoding='utf-8') as f:
                        f.write(view_content)
                    console.print(f"    [green]✓[/green] Created {view_file.name}")

                # Generate explore
                explore = self.mapper.semantic_model_to_explore(semantic_model)
                explores.append(explore)

            except Exception as e:
                validation_errors.append(f"Model {semantic_model.name}: {e}")
                console.print(f"    [red]✗[/red] Failed to process: {e}")

        # Generate explores file
        if explores:
            try:
                console.print(f"[bold blue]Generating explores file...[/bold blue]")
                explores_content = self._generate_explores_lookml(explores)
                
                # Validate explores syntax
                if self.validate_syntax:
                    try:
                        self._validate_lookml_syntax(explores_content)
                        console.print(f"  [green]✓[/green] Explores syntax valid")
                    except LookMLValidationError as e:
                        validation_errors.append(f"Explores file: {e}")
                        console.print(f"  [red]✗[/red] Explores syntax error: {e}")

                explores_file = output_dir / "explores.lkml"
                generated_files.append(explores_file)
                
                if dry_run:
                    console.print(f"  [yellow]Would create:[/yellow] {explores_file}")
                    console.print(f"  [dim]Content preview (first 5 lines):[/dim]")
                    lines = explores_content.strip().split('\n')[:5]
                    for line in lines:
                        console.print(f"  [dim]    {line}[/dim]")
                else:
                    with open(explores_file, 'w', encoding='utf-8') as f:
                        f.write(explores_content)
                    console.print(f"  [green]✓[/green] Created {explores_file.name}")
                    
            except Exception as e:
                validation_errors.append(f"Explores file: {e}")
                console.print(f"  [red]✗[/red] Failed to generate explores: {e}")

        return generated_files, validation_errors

    def _generate_view_lookml(self, view: LookMLView) -> str:
        """Generate LookML content for a view.

        Args:
            view: The LookML view to generate content for.

        Returns:
            The LookML content as a string.
        """
        view_dict: Dict[str, Any] = {
            'view': {
                view.name: {
                    'sql_table_name': view.sql_table_name,
                }
            }
        }

        # Add description if present
        if view.description:
            view_dict['view'][view.name]['description'] = view.description

        # Add dimensions
        if view.dimensions:
            dimensions: Dict[str, Any] = {}
            for dim in view.dimensions:
                dim_dict: Dict[str, Any] = {
                    'type': dim.type,
                    'sql': dim.sql,
                }
                if dim.description:
                    dim_dict['description'] = dim.description
                if dim.label:
                    dim_dict['label'] = dim.label
                if dim.hidden:
                    dim_dict['hidden'] = 'yes'
                if dim.primary_key:
                    dim_dict['primary_key'] = 'yes'

                dimensions[dim.name] = dim_dict

            view_dict['view'][view.name]['dimension'] = dimensions
            
        # Add dimension_groups
        if view.dimension_groups:
            dimension_groups: Dict[str, Any] = {}
            for dim_group in view.dimension_groups:
                dim_group_dict: Dict[str, Any] = {
                    'type': dim_group.type,
                    'timeframes': dim_group.timeframes,
                    'sql': dim_group.sql,
                }
                if dim_group.description:
                    dim_group_dict['description'] = dim_group.description
                if dim_group.label:
                    dim_group_dict['label'] = dim_group.label
                if dim_group.hidden:
                    dim_group_dict['hidden'] = 'yes'

                dimension_groups[dim_group.name] = dim_group_dict

            view_dict['view'][view.name]['dimension_group'] = dimension_groups

        # Add measures
        if view.measures:
            measures: Dict[str, Any] = {}
            for measure in view.measures:
                measure_dict: Dict[str, Any] = {
                    'type': measure.type,
                    'sql': measure.sql,
                }
                if measure.description:
                    measure_dict['description'] = measure.description
                if measure.label:
                    measure_dict['label'] = measure.label
                if measure.hidden:
                    measure_dict['hidden'] = 'yes'

                measures[measure.name] = measure_dict

            view_dict['view'][view.name]['measure'] = measures

        result = lkml.dump(view_dict)
        formatted_result = result if result is not None else ""
        
        if self.format_output:
            formatted_result = self._format_lookml_content(formatted_result)
            
        return formatted_result

    def _generate_explores_lookml(self, explores: List[LookMLExplore]) -> str:
        """Generate LookML content for explores.

        Args:
            explores: List of LookML explores to generate content for.

        Returns:
            The LookML content as a string.
        """
        explores_dict: Dict[str, Dict[str, Any]] = {'explore': {}}

        for explore in explores:
            explore_dict = {
                'type': 'table',
                'from': explore.view_name,
            }

            if explore.description:
                explore_dict['description'] = explore.description

            if explore.hidden:
                explore_dict['hidden'] = 'yes'

            explores_dict['explore'][explore.name] = explore_dict

        result = lkml.dump(explores_dict)
        formatted_result = result if result is not None else ""
        
        if self.format_output:
            formatted_result = self._format_lookml_content(formatted_result)
            
        return formatted_result

    def _validate_lookml_syntax(self, content: str) -> None:
        """Validate LookML syntax using the lkml library.
        
        Args:
            content: The LookML content to validate.
            
        Raises:
            LookMLValidationError: If the syntax is invalid.
        """
        try:
            # Attempt to parse the content
            parsed = lkml.load(content)
            if parsed is None:
                raise LookMLValidationError("Failed to parse LookML content")
        except Exception as e:
            raise LookMLValidationError(f"Invalid LookML syntax: {str(e)}")

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
