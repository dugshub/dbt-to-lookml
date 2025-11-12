# Local Task Management System

This directory contains the local markdown-based task management system for dbt-to-lookml.

## Overview

Instead of using external issue tracking (like Linear), we use local markdown files to track issues, epics, strategies, and specs. All data is stored in git and human-readable.

## Directory Structure

```
.tasks/
├── config.yaml          # Project configuration (issue counter, labels)
├── index.md             # Auto-generated index of all issues
├── plans/               # YAML planning files (issue-plan-{name}.yaml)
├── issues/              # Individual issue files (DTL-001.md, DTL-002.md, etc.)
├── epics/               # Epic files (DTL-001.md for epics)
├── strategies/          # Implementation strategies (DTL-001-strategy.md)
└── specs/               # Implementation specs (DTL-001-spec.md)
```

## Issue File Format

Each issue is a markdown file with YAML frontmatter:

```markdown
---
id: DTL-001
title: "Add Redis caching layer"
type: feature
stack: backend
status: refinement
labels:
  - stack:backend
  - layer:atoms
  - type:feature
created: 2025-11-12T10:00:00Z
updated: 2025-11-12T12:30:00Z
parent: EPIC-001  # Optional - links to epic
---

# DTL-001: Add Redis caching layer

## Problem Statement
{Description of what needs to be done}

## Success Criteria
- [ ] Redis adapter implemented
- [ ] Tests passing
- [ ] Documentation updated

## Links
- Strategy: [.tasks/strategies/DTL-001-strategy.md](.tasks/strategies/DTL-001-strategy.md)
- Spec: [.tasks/specs/DTL-001-spec.md](.tasks/specs/DTL-001-spec.md)
- PR: #42

## History
### 2025-11-12 12:30 - Strategy Generated
Strategy posted to `.tasks/strategies/DTL-001-strategy.md`

### 2025-11-12 10:00 - Issue Created
Created from epic EPIC-001
```

## CLI Usage

Use the `dtl-tasks` command (via `uv run python scripts/dtl_tasks.py`):

```bash
# List all issues
uv run python scripts/dtl_tasks.py list

# Filter by status
uv run python scripts/dtl_tasks.py list --status ready

# Show issue details
uv run python scripts/dtl_tasks.py show DTL-001

# Update issue status
uv run python scripts/dtl_tasks.py update DTL-001 --status in-progress

# Add label
uv run python scripts/dtl_tasks.py update DTL-001 --add-label "tdd:required"

# Add history entry
uv run python scripts/dtl_tasks.py update DTL-001 \
  --event "Implementation Started" \
  --description "Branch created: feature/DTL-001-add-caching"

# Regenerate index
uv run python scripts/dtl_tasks.py reindex

# Get next available ID
uv run python scripts/dtl_tasks.py next-id
```

## Workflow

### 1. Plan & Decompose

```bash
# Decompose requirements into YAML plan
/plan:decompose "Add user authentication system"

# Creates: .tasks/plans/issue-plan-user-authentication.yaml
```

### 2. Create Issues

```bash
# Create markdown issues from YAML
/plan:create .tasks/plans/issue-plan-user-authentication.yaml

# Creates:
#   .tasks/epics/DTL-001.md (epic)
#   .tasks/issues/DTL-002.md (sub-issue 1)
#   .tasks/issues/DTL-003.md (sub-issue 2)
#   .tasks/index.md (updated)
```

### 3. Generate Strategy

```bash
# Generate implementation strategy
/plan:strategy DTL-002

# Creates: .tasks/strategies/DTL-002-strategy.md
# Updates issue status to: awaiting-strategy-review
```

### 4. Approve Strategy

**Manual step:**
```bash
# Review strategy
cat .tasks/strategies/DTL-002-strategy.md

# Approve by editing issue file
# Change: status: awaiting-strategy-review → status: strategy-approved
vi .tasks/issues/DTL-002.md
```

### 5. Generate Spec

```bash
# Generate detailed implementation spec
/plan:spec DTL-002

# Creates: .tasks/specs/DTL-002-spec.md
# Updates issue status to: ready
```

### 6. Implement

```bash
# Implement the issue
/implement DTL-002

# - Creates feature branch
# - Implements code
# - Writes tests
# - Runs quality gates
# - Creates PR
# - Updates issue status to: in-review
```

## Issue Statuses

Issues progress through these statuses:

1. **todo** - Created but not yet refined
2. **refinement** - Being refined/planned
3. **awaiting-strategy-review** - Strategy generated, awaiting human review
4. **strategy-approved** - Strategy approved, ready for spec
5. **ready** - Spec generated, ready for implementation
6. **in-progress** - Currently being implemented
7. **in-review** - PR created, awaiting code review
8. **done** - Completed and merged
9. **blocked** - Blocked by dependencies
10. **cancelled** - Cancelled/won't do

## Labels

Available labels (from `.tasks/config.yaml`):

### Stack (REQUIRED)
- `stack:backend` - Backend/Python work
- `stack:frontend` - Frontend/UI work
- `stack:fullstack` - Full-stack (both backend and frontend)

### Type (REQUIRED)
- `type:epic` - Epic (collection of sub-issues)
- `type:feature` - New feature
- `type:bug` - Bug fix
- `type:chore` - Maintenance/refactoring
- `type:patch` - Quick fix/patch

### Layer (Backend only)
- `layer:atoms` - Atomic layer (low-level utilities)
- `layer:features` - Features layer (business logic)
- `layer:molecules` - Molecules layer (API/services)
- `layer:organisms` - Organisms layer (entry points)

### Priority
- `priority:low`
- `priority:medium`
- `priority:high`

### State
- `state:awaiting-strategy-review`
- `state:strategy-approved`
- `state:spec-ready`

## Benefits

### vs. External Issue Trackers (Linear, Jira, etc.)

✅ **No External Dependencies**: Works offline, no API keys, no rate limits
✅ **Git-Native**: Full history, branching, merging
✅ **Markdown**: Human-readable, searchable, diff-able
✅ **Local-First**: Instant access, no network latency
✅ **Free**: No subscription costs
✅ **Portable**: Copy `.tasks/` to any project
✅ **Transparent**: All data visible in editor/terminal
✅ **Scriptable**: Easy to build custom tools

### vs. Git Issues

✅ **Faster**: No network calls
✅ **Offline**: Works without internet
✅ **Flexible**: Custom frontmatter, no platform constraints
✅ **Richer**: Embedded strategies and specs

## Tips

### VS Code Integration

Add this to `.vscode/settings.json`:

```json
{
  "files.associations": {
    ".tasks/issues/*.md": "markdown",
    ".tasks/epics/*.md": "markdown"
  },
  "markdown.extension.toc.levels": "1..3",
  "markdown.extension.list.indentationSize": "adaptive"
}
```

### Quick Navigation

Use fuzzy finder to jump to issues:

```bash
# fzf
cat .tasks/index.md | fzf

# Or use VS Code quick open
# Cmd+P → type "DTL-"
```

### Git Commits

Commit task changes regularly:

```bash
git add .tasks/
git commit -m "docs(tasks): update issue DTL-002 status to in-progress"
```

### Searching

```bash
# Find all issues with specific label
grep -r "stack:backend" .tasks/issues/

# Find issues by status
grep -r "status: ready" .tasks/issues/

# Search issue content
grep -r "Redis" .tasks/issues/
```

## Maintenance

### Reindex

Run this if index.md gets out of sync:

```bash
uv run python scripts/dtl_tasks.py reindex
```

### Cleanup

Remove old/cancelled issues:

```bash
# Move to archive
mkdir -p .tasks/archive
mv .tasks/issues/DTL-old.md .tasks/archive/

# Then reindex
uv run python scripts/dtl_tasks.py reindex
```

## Configuration

Edit `.tasks/config.yaml` to:
- Change issue ID prefix (default: `DTL`)
- Add custom labels
- Modify status transitions
- Set project metadata

## Related Documentation

- `CLAUDE.md` - Project patterns and architecture
- `.claude/commands/plan/` - Planning workflow commands
- `.claude/commands/implement/` - Implementation commands
- `scripts/dtl_tasks.py` - CLI source code
