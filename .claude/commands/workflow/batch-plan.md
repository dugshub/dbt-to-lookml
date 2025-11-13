---
description: Batch generate strategies and specs for multiple issues
argument-hint: <issue-ids...> [--auto]
allowed-tools:
  - Bash
  - SlashCommand
---

# Workflow Batch Plan

Wrapper around `/workflow:execute` with `--plan-only` flag for batch planning.

## Purpose

Quickly generate strategies and specs for multiple issues without implementing them. Perfect for:
- Friday afternoon planning sessions
- Preparing issues for team review
- Bulk strategy generation for epics

## Usage

```bash
# Plan all children of an epic
/workflow:batch-plan DTL-001

# Plan multiple specific issues
/workflow:batch-plan DTL-002 DTL-003 DTL-004

# Fully automated (no prompts)
/workflow:batch-plan DTL-002 DTL-003 --auto
```

## Implementation

This is a simple wrapper that delegates to `/workflow:execute`:

```bash
# Get all arguments
ARGS="$@"

# Append --plan-only flag
ARGS="${ARGS} --plan-only"

# Execute workflow
Use SlashCommand to run: /workflow:execute ${ARGS}
```

## What It Does

1. **Generates strategies** (parallel) for all issues
2. **Generates specs** (parallel) for all issues
3. **Stops** - no implementation

## Example

```bash
/workflow:batch-plan DTL-001 --auto
```

**Output:**
```
📦 Detected epic: DTL-001
📋 Found 5 child issues

Phase 1: Generating strategies (parallel)...
  ✅ DTL-002 strategy complete
  ✅ DTL-003 strategy complete
  ✅ DTL-004 strategy complete
  ✅ DTL-005 strategy complete
  ✅ DTL-006 strategy complete

Phase 2: Generating specs (parallel)...
  ✅ DTL-002 spec complete
  ✅ DTL-003 spec complete
  ✅ DTL-004 spec complete
  ✅ DTL-005 spec complete
  ✅ DTL-006 spec complete

✅ Planning complete. All issues ready for review and implementation.

Next: Review specs, then run:
  /workflow:execute DTL-001 --implement-only
```

## Benefits

- **Fast**: Parallel strategy/spec generation
- **Non-destructive**: Doesn't implement anything
- **Reviewable**: All strategies/specs in git for review
- **Team-friendly**: Generate plans, team reviews, then implement
