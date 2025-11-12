# Quick Reference Card

One-page reference for the most common task management operations.

## Essential Commands

```bash
# View next available issue ID
make tasks-next-id

# List all issues
make tasks-list

# Show issue details
make tasks-show ID=DTL-001

# Update issue status
make tasks-update ID=DTL-001 STATUS=in-progress

# Regenerate index after changes
make tasks-reindex
```

## Full Workflow

```bash
# 1. Plan
/plan:decompose "feature description"

# 2. Create issues from plan
/plan:create .tasks/plans/issue-plan-{name}.yaml

# 3. Generate strategy for an issue
/plan:strategy DTL-001

# 4. Review strategy (opens in editor)
cat .tasks/strategies/DTL-001-strategy.md

# 5. Approve strategy (edit issue file)
vi .tasks/issues/DTL-001.md
# Change: status: awaiting-strategy-review → status: strategy-approved

# 6. Generate implementation spec
/implement:spec DTL-001

# 7. Implement the issue
/implement DTL-001

# 8. After PR is merged, mark as done
make tasks-update ID=DTL-001 STATUS=done
```

## Issue Statuses

```
todo → refinement → awaiting-strategy-review → strategy-approved
  → ready → in-progress → in-review → done
```

## Common Filters

```bash
# By status
make tasks-list | grep "ready"
uv run python scripts/dtl_tasks.py list --status ready

# By type
uv run python scripts/dtl_tasks.py list --type feature
uv run python scripts/dtl_tasks.py list --type bug

# Search content
grep -r "search term" .tasks/issues/

# Find high priority
grep -r "priority:high" .tasks/issues/
```

## File Locations

```
.tasks/
├── plans/            # YAML plans: issue-plan-{name}.yaml
├── issues/           # Issues: DTL-001.md, DTL-002.md
├── epics/            # Epics: DTL-001.md (if epic)
├── strategies/       # Strategies: DTL-001-strategy.md
├── specs/            # Specs: DTL-001-spec.md
├── config.yaml       # Project configuration
└── index.md          # Auto-generated index

scripts/
└── dtl_tasks.py      # CLI tool
```

## Manual Issue Creation

```bash
# 1. Get next ID
NEXT_ID=$(make tasks-next-id)

# 2. Create file
cat > .tasks/issues/${NEXT_ID}.md <<'EOF'
---
id: DTL-001
title: "Issue title"
type: feature
stack: backend
status: todo
labels:
  - stack:backend
  - type:feature
created: $(date -u +%Y-%m-%dT%H:%M:%SZ)
updated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
---

# DTL-001: Issue Title

## Problem Statement
What needs to be done

## Success Criteria
- [ ] Criterion 1

## History
### $(date -u +%Y-%m-%d\ %H:%M) - Created
Initial creation
EOF

# 3. Update counter in .tasks/config.yaml
# Change: next_id: 2

# 4. Reindex
make tasks-reindex
```

## Git Integration

```bash
# Commit task changes
git add .tasks/
git commit -m "docs(tasks): update DTL-001 status to in-progress"

# View task history
git log --oneline .tasks/issues/DTL-001.md

# Diff task changes
git diff .tasks/issues/DTL-001.md
```

## Troubleshooting

```bash
# Index out of sync
make tasks-reindex

# Can't find issue
find .tasks -name "*.md" -type f | xargs grep -l "search"

# Wrong issue counter
# Edit .tasks/config.yaml: next_id: <correct-value>

# CLI help
uv run python scripts/dtl_tasks.py --help
uv run python scripts/dtl_tasks.py list --help
```

## Shell Aliases (Optional)

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias tl='uv run python scripts/dtl_tasks.py list'
alias ts='uv run python scripts/dtl_tasks.py show'
alias tu='uv run python scripts/dtl_tasks.py update'
alias tr='uv run python scripts/dtl_tasks.py reindex'
alias tn='uv run python scripts/dtl_tasks.py next-id'
```

Then use:
```bash
tl                    # List all
tl --status ready     # Filter by status
ts DTL-001            # Show issue
tu DTL-001 --status in-progress
tn                    # Next ID
```

## VS Code Integration

Create `.vscode/settings.json`:

```json
{
  "files.associations": {
    ".tasks/**/*.md": "markdown"
  },
  "search.exclude": {
    ".tasks/index.md": true
  }
}
```

Quick navigation:
- `Cmd+P` (Mac) / `Ctrl+P` (Windows/Linux)
- Type: `DTL-` to find issues quickly

## Documentation

- Full guide: `.tasks/GETTING_STARTED.md`
- Complete docs: `.tasks/README.md`
- Migration guide: `.tasks/MIGRATION.md`
- Technical summary: `.tasks/SUMMARY.md`

## Help

```bash
make help                                   # Makefile targets
uv run python scripts/dtl_tasks.py --help  # CLI help
cat .tasks/QUICKREF.md                     # This file
```
