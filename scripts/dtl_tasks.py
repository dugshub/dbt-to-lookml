#!/usr/bin/env python3
"""
DTL Task Management CLI

Simple CLI for managing local markdown-based tasks.
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import yaml


class TaskManager:
    """Manager for local markdown tasks."""

    def __init__(self, tasks_dir: Path = Path(".tasks")):
        self.tasks_dir = tasks_dir
        self.config_file = tasks_dir / "config.yaml"
        self.index_file = tasks_dir / "index.md"
        self.issues_dir = tasks_dir / "issues"
        self.epics_dir = tasks_dir / "epics"
        self.strategies_dir = tasks_dir / "strategies"
        self.specs_dir = tasks_dir / "specs"

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from config.yaml."""
        with open(self.config_file) as f:
            return yaml.safe_load(f)

    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to config.yaml."""
        with open(self.config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    def generate_issue_id(self) -> str:
        """Generate next issue ID and increment counter."""
        config = self.load_config()
        prefix = config["project"]["prefix"]
        next_id = config["project"]["next_id"]
        issue_id = f"{prefix}-{next_id:03d}"

        # Increment counter
        config["project"]["next_id"] = next_id + 1
        self.save_config(config)

        return issue_id

    def parse_frontmatter(self, content: str) -> tuple[Dict[str, Any], str]:
        """Parse YAML frontmatter from markdown content."""
        if not content.startswith("---\n"):
            return {}, content

        parts = content.split("---\n", 2)
        if len(parts) < 3:
            return {}, content

        frontmatter = yaml.safe_load(parts[1])
        body = parts[2]
        return frontmatter, body

    def serialize_issue(self, frontmatter: Dict[str, Any], body: str) -> str:
        """Serialize issue to markdown with frontmatter."""
        fm_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        return f"---\n{fm_yaml}---\n\n{body}"

    def read_issue(self, issue_id: str) -> Optional[Dict[str, Any]]:
        """Read issue from file."""
        # Try issues dir first
        issue_path = self.issues_dir / f"{issue_id}.md"
        if not issue_path.exists():
            # Try epics dir
            issue_path = self.epics_dir / f"{issue_id}.md"
            if not issue_path.exists():
                return None

        content = issue_path.read_text()
        frontmatter, body = self.parse_frontmatter(content)

        return {
            "id": issue_id,
            "path": issue_path,
            "frontmatter": frontmatter,
            "body": body,
            "is_epic": issue_path.parent.name == "epics"
        }

    def write_issue(self, issue_id: str, frontmatter: Dict[str, Any], body: str, is_epic: bool = False) -> Path:
        """Write issue to file."""
        target_dir = self.epics_dir if is_epic else self.issues_dir
        issue_path = target_dir / f"{issue_id}.md"

        content = self.serialize_issue(frontmatter, body)
        issue_path.write_text(content)

        return issue_path

    def update_issue(self, issue_id: str, updates: Dict[str, Any]) -> bool:
        """Update issue with new data."""
        issue = self.read_issue(issue_id)
        if not issue:
            return False

        frontmatter = issue["frontmatter"]
        body = issue["body"]

        # Update frontmatter
        for key, value in updates.items():
            if key == "status":
                frontmatter["status"] = value
                frontmatter["updated"] = datetime.utcnow().isoformat() + "Z"
            elif key == "labels":
                frontmatter["labels"] = value
            elif key == "add_label":
                if "labels" not in frontmatter:
                    frontmatter["labels"] = []
                if value not in frontmatter["labels"]:
                    frontmatter["labels"].append(value)
            elif key == "remove_label":
                if "labels" in frontmatter and value in frontmatter["labels"]:
                    frontmatter["labels"].remove(value)
            elif key == "add_history":
                # Add history entry to body
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
                history_entry = f"\n### {timestamp} - {value['event']}\n{value['description']}\n"

                # Find or create History section
                if "## History" in body:
                    body = body.replace("## History\n", f"## History\n{history_entry}")
                else:
                    body += f"\n## History\n{history_entry}"

        # Write back
        self.write_issue(issue_id, frontmatter, body, issue["is_epic"])
        return True

    def list_issues(self, status: Optional[str] = None, issue_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all issues with optional filtering."""
        issues = []

        # Read all issues
        for issue_file in self.issues_dir.glob("*.md"):
            issue_id = issue_file.stem
            issue = self.read_issue(issue_id)
            if issue:
                issues.append(issue)

        # Read all epics
        for epic_file in self.epics_dir.glob("*.md"):
            epic_id = epic_file.stem
            epic = self.read_issue(epic_id)
            if epic:
                issues.append(epic)

        # Filter
        if status:
            issues = [i for i in issues if i["frontmatter"].get("status") == status]
        if issue_type:
            issues = [i for i in issues if i["frontmatter"].get("type") == issue_type]

        return issues

    def update_index(self) -> None:
        """Update the index.md file with current statistics."""
        issues = self.list_issues()
        epics = [i for i in issues if i["is_epic"]]

        # Count by status
        status_counts: Dict[str, List[Dict[str, Any]]] = {}
        for issue in issues:
            status = issue["frontmatter"].get("status", "todo")
            if status not in status_counts:
                status_counts[status] = []
            status_counts[status].append(issue)

        # Build index content
        content = f"""# Task Index

Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Statistics

- Total Issues: {len(issues)}
- Epics: {len(epics)}
- Active: {len([i for i in issues if i["frontmatter"].get("status") in ["in-progress", "in-review"]])}
- Completed: {len([i for i in issues if i["frontmatter"].get("status") == "done"])}

## Issues by Status

"""

        # Add sections for each status with issues
        for status in ["todo", "refinement", "awaiting-strategy-review", "strategy-approved",
                       "ready", "in-progress", "in-review", "blocked", "done"]:
            section_issues = status_counts.get(status, [])
            content += f"### {status.replace('-', ' ').title()}\n"
            if section_issues:
                for issue in section_issues:
                    issue_id = issue["frontmatter"]["id"]
                    title = issue["frontmatter"]["title"]
                    issue_type = issue["frontmatter"].get("type", "issue")
                    emoji = "📦" if issue["is_epic"] else "🔹"
                    file_path = f"epics/{issue_id}.md" if issue["is_epic"] else f"issues/{issue_id}.md"
                    content += f"- {emoji} [{issue_id}: {title}]({file_path}) `{issue_type}`\n"
            else:
                content += "*No issues*\n"
            content += "\n"

        content += """---
*Generated automatically by dtl-tasks*
"""

        self.index_file.write_text(content)


# CLI Commands

@click.group()
@click.pass_context
def cli(ctx):
    """DTL Task Management CLI."""
    ctx.ensure_object(dict)
    ctx.obj["manager"] = TaskManager()


@cli.command()
@click.argument("issue_id")
@click.pass_context
def show(ctx, issue_id):
    """Show details of an issue."""
    manager = ctx.obj["manager"]
    issue = manager.read_issue(issue_id)

    if not issue:
        click.echo(f"❌ Issue {issue_id} not found", err=True)
        sys.exit(1)

    fm = issue["frontmatter"]

    click.echo(f"\n{'='*60}")
    click.echo(f"{fm['id']}: {fm['title']}")
    click.echo(f"{'='*60}\n")
    click.echo(f"Type: {fm.get('type', 'N/A')}")
    click.echo(f"Status: {fm.get('status', 'N/A')}")
    click.echo(f"Stack: {fm.get('stack', 'N/A')}")

    if "labels" in fm and fm["labels"]:
        click.echo(f"Labels: {', '.join(fm['labels'])}")

    if "parent" in fm:
        click.echo(f"Parent: {fm['parent']}")

    if "children" in fm and fm["children"]:
        click.echo(f"Children: {', '.join(fm['children'])}")

    click.echo(f"\nCreated: {fm.get('created', 'N/A')}")
    click.echo(f"Updated: {fm.get('updated', 'N/A')}")
    click.echo(f"\n{issue['body']}")


@cli.command()
@click.option("--status", help="Filter by status")
@click.option("--type", "issue_type", help="Filter by type")
@click.option("--format", "output_format", default="table", type=click.Choice(["table", "json"]), help="Output format")
@click.pass_context
def list(ctx, status, issue_type, output_format):
    """List all issues."""
    manager = ctx.obj["manager"]
    issues = manager.list_issues(status=status, issue_type=issue_type)

    if not issues:
        click.echo("No issues found")
        return

    if output_format == "json":
        import json
        data = [
            {
                "id": i["frontmatter"]["id"],
                "title": i["frontmatter"]["title"],
                "status": i["frontmatter"].get("status"),
                "type": i["frontmatter"].get("type"),
                "is_epic": i["is_epic"]
            }
            for i in issues
        ]
        click.echo(json.dumps(data, indent=2))
    else:
        # Table format
        click.echo(f"\n{'ID':<12} {'Title':<40} {'Status':<20} {'Type':<10}")
        click.echo("-" * 85)
        for issue in issues:
            fm = issue["frontmatter"]
            issue_id = fm["id"]
            title = fm["title"][:37] + "..." if len(fm["title"]) > 40 else fm["title"]
            status_str = fm.get("status", "N/A")
            type_str = fm.get("type", "N/A")

            emoji = "📦" if issue["is_epic"] else "  "
            click.echo(f"{emoji} {issue_id:<10} {title:<40} {status_str:<20} {type_str:<10}")

        click.echo(f"\nTotal: {len(issues)} issues")


@cli.command()
@click.argument("issue_id")
@click.option("--status", help="Update status")
@click.option("--add-label", help="Add label")
@click.option("--remove-label", help="Remove label")
@click.option("--event", help="Add history event (requires --description)")
@click.option("--description", help="History event description")
@click.pass_context
def update(ctx, issue_id, status, add_label, remove_label, event, description):
    """Update an issue."""
    manager = ctx.obj["manager"]

    updates = {}

    if status:
        updates["status"] = status

    if add_label:
        updates["add_label"] = add_label

    if remove_label:
        updates["remove_label"] = remove_label

    if event and description:
        updates["add_history"] = {"event": event, "description": description}

    if not updates:
        click.echo("❌ No updates specified", err=True)
        sys.exit(1)

    if manager.update_issue(issue_id, updates):
        click.echo(f"✅ Updated {issue_id}")

        # Update index
        manager.update_index()
        click.echo("✅ Updated index")
    else:
        click.echo(f"❌ Issue {issue_id} not found", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def reindex(ctx):
    """Regenerate the index.md file."""
    manager = ctx.obj["manager"]
    manager.update_index()
    click.echo("✅ Index updated")


@cli.command()
@click.pass_context
def next_id(ctx):
    """Show next available issue ID."""
    manager = ctx.obj["manager"]
    config = manager.load_config()
    prefix = config["project"]["prefix"]
    next_id = config["project"]["next_id"]
    click.echo(f"{prefix}-{next_id:03d}")


if __name__ == "__main__":
    cli(obj={})
