# Getting Started with Local Task Management

This guide will walk you through using the local markdown-based task system.

## Quick Start

### 1. View Available Commands

```bash
make help
```

Look for the "Task Management" section.

### 2. Check Next Available ID

```bash
make tasks-next-id
# Output: DTL-001
```

### 3. List All Issues

```bash
make tasks-list
# Or with full command:
uv run python scripts/dtl_tasks.py list
```

## Creating Your First Issue

### Option A: Manual Creation

Create a file `.tasks/issues/DTL-001.md`:

```markdown
---
id: DTL-001
title: "Add comprehensive test coverage for parsers"
type: feature
stack: backend
status: todo
labels:
  - stack:backend
  - type:feature
  - priority:high
created: 2025-11-12T10:00:00Z
updated: 2025-11-12T10:00:00Z
---

# DTL-001: Add comprehensive test coverage for parsers

## Problem Statement

The parser module currently has only 68% test coverage. We need to increase
this to 90%+ to meet our quality standards.

## Success Criteria

- [ ] Parser test coverage ≥ 90%
- [ ] All edge cases covered
- [ ] Tests are fast (<5s total)
- [ ] Documentation updated

## Links

- Strategy: [.tasks/strategies/DTL-001-strategy.md](./../strategies/DTL-001-strategy.md)
- Spec: [.tasks/specs/DTL-001-spec.md](./../specs/DTL-001-spec.md)

## History

### 2025-11-12 10:00 - Issue Created
Initial creation
```

Then update the config counter and reindex:

```bash
# Update .tasks/config.yaml next_id to 2
make tasks-reindex
```

### Option B: Using /plan:decompose + /plan:create

This is the recommended approach for larger features:

```bash
# 1. Decompose requirements into YAML plan
/plan:decompose "Add comprehensive test coverage"

# This creates: issue-plan-test-coverage.yaml

# 2. Review and edit the YAML if needed
cat issue-plan-test-coverage.yaml

# 3. Create markdown issues from YAML
/plan:create issue-plan-test-coverage.yaml

# This creates:
#   .tasks/epics/DTL-001.md (if epic structure)
#   .tasks/issues/DTL-002.md
#   .tasks/issues/DTL-003.md
#   .tasks/index.md (updated)
```

## Working with an Issue

### View Issue Details

```bash
make tasks-show ID=DTL-001

# Or directly:
uv run python scripts/dtl_tasks.py show DTL-001
```

### Update Issue Status

```bash
# Update status
make tasks-update ID=DTL-001 STATUS=refinement

# Add a label
make tasks-update ID=DTL-001 LABEL="tdd:required"

# Add history entry
make tasks-update ID=DTL-001 EVENT="Started planning" DESC="Reviewing existing tests"
```

## Full Workflow Example

### 1. Plan & Create Issues

```bash
# Decompose feature into issues
/plan:decompose "Add Redis caching to improve performance"

# This creates: .tasks/plans/issue-plan-redis-caching.yaml

# Create markdown issues
/plan:create .tasks/plans/issue-plan-redis-caching.yaml

# Output:
# ✅ Issue Sync Complete!
# Epic: DTL-001 - "Epic: Redis Caching"
# Children:
#   DTL-002 - "Create cache interface"
#   DTL-003 - "Implement Redis adapter"
#   DTL-004 - "Add caching to parser"
```

### 2. Generate Strategy for First Issue

```bash
# Generate implementation strategy
/plan:strategy DTL-002

# Output:
# ✅ Implementation Strategy Generated
# Strategy File: .tasks/strategies/DTL-002-strategy.md
# Status: Awaiting strategy review
```

### 3. Review and Approve Strategy

```bash
# Review the strategy
cat .tasks/strategies/DTL-002-strategy.md

# If approved, edit the issue file
vi .tasks/issues/DTL-002.md

# Change:
#   status: awaiting-strategy-review
# To:
#   status: strategy-approved
```

### 4. Generate Detailed Spec

```bash
# Generate implementation spec
/implement:spec DTL-002

# Output:
# ✅ Spec Generated Successfully!
# Spec File: .tasks/specs/DTL-002-spec.md
# Status: ready
```

### 5. Implement the Issue

```bash
# Implement with optional TDD
/implement DTL-002

# Or force TDD mode:
/implement DTL-002 --tdd

# This will:
# 1. Create feature branch
# 2. Update issue status to in-progress
# 3. Implement according to spec
# 4. Write tests
# 5. Run quality gates
# 6. Create PR
# 7. Update issue status to in-review
```

### 6. After PR Merge

```bash
# Manually update status to done
make tasks-update ID=DTL-002 STATUS=done EVENT="PR Merged" DESC="PR #42 merged to main"
```

## Common Tasks

### List Issues by Status

```bash
# Show all ready issues
uv run python scripts/dtl_tasks.py list --status ready

# Show all in-progress issues
uv run python scripts/dtl_tasks.py list --status in-progress

# Show all done issues
uv run python scripts/dtl_tasks.py list --status done
```

### List Issues by Type

```bash
# Show all features
uv run python scripts/dtl_tasks.py list --type feature

# Show all bugs
uv run python scripts/dtl_tasks.py list --type bug
```

### Search Issues

```bash
# Find issues mentioning "Redis"
grep -r "Redis" .tasks/issues/

# Find backend issues
grep -r "stack:backend" .tasks/issues/

# Find high-priority issues
grep -r "priority:high" .tasks/issues/
```

### View Index

```bash
# View the auto-generated index
cat .tasks/index.md

# Or open in your editor
code .tasks/index.md
```

## Issue Lifecycle

```
todo
  ↓
refinement (planning, asking questions)
  ↓
(Generate strategy via /plan:strategy)
  ↓
awaiting-strategy-review (review strategy file)
  ↓
(Manually approve: edit issue, change status)
  ↓
strategy-approved
  ↓
(Generate spec via /implement:spec)
  ↓
ready (spec generated, ready to implement)
  ↓
(Implement via /implement)
  ↓
in-progress (actively coding)
  ↓
(Create PR, quality gates pass)
  ↓
in-review (PR created, awaiting code review)
  ↓
(PR approved and merged)
  ↓
done ✅
```

## Tips & Tricks

### Use VS Code for Quick Navigation

Install these VS Code extensions:
- Markdown All in One
- Markdown Preview Enhanced

Then use `Cmd+P` (Mac) or `Ctrl+P` (Windows/Linux) and type:
- `DTL-` to find issues quickly
- `strategy` to find strategy files
- `spec` to find spec files

### Create Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
# Task shortcuts
alias tl='uv run python scripts/dtl_tasks.py list'
alias ts='uv run python scripts/dtl_tasks.py show'
alias tu='uv run python scripts/dtl_tasks.py update'
alias tr='uv run python scripts/dtl_tasks.py reindex'
alias tn='uv run python scripts/dtl_tasks.py next-id'

# Usage:
# tl --status ready
# ts DTL-001
# tu DTL-001 --status in-progress
```

### Git Workflow

Commit task changes regularly:

```bash
# After creating issues
git add .tasks/
git commit -m "docs(tasks): create Redis caching epic and sub-issues"

# After generating strategy
git add .tasks/
git commit -m "docs(tasks): add strategy for DTL-002"

# After updating status
git add .tasks/
git commit -m "docs(tasks): update DTL-002 status to in-progress"
```

### Batch Operations

```bash
# Create strategies for multiple issues
for id in DTL-002 DTL-003 DTL-004; do
  /plan:strategy $id
done

# Update multiple issues to refinement
for id in DTL-002 DTL-003 DTL-004; do
  make tasks-update ID=$id STATUS=refinement
done
```

## Troubleshooting

### Index is Out of Sync

```bash
make tasks-reindex
```

### Issue ID Counter is Wrong

Edit `.tasks/config.yaml` and update `next_id` to the correct value.

### Can't Find an Issue

```bash
# Search all issues
find .tasks -name "*.md" -type f | grep -v index | xargs grep -l "search term"
```

### Need to Archive Old Issues

```bash
# Create archive directory
mkdir -p .tasks/archive

# Move old/cancelled issues
mv .tasks/issues/DTL-old.md .tasks/archive/

# Reindex
make tasks-reindex
```

## Next Steps

- Read `.tasks/README.md` for detailed documentation
- Review `CLAUDE.md` for project patterns and architecture
- Explore `.claude/commands/plan/` for planning workflow details
- Check `.claude/commands/implement/` for implementation workflow

## Getting Help

- Check task status: `make tasks-show ID=<issue-id>`
- View all commands: `make help`
- View CLI help: `uv run python scripts/dtl_tasks.py --help`
- Read this guide: `.tasks/GETTING_STARTED.md`
- Read full docs: `.tasks/README.md`
