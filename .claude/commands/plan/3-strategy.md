# /plan:strategy

Generate implementation strategy for a local markdown issue.

## Purpose

Analyze a local issue and generate a comprehensive, high-level implementation strategy. The strategy is saved to `.tasks/strategies/{ISSUE-ID}-strategy.md` and the issue status is updated to `awaiting-strategy-review`.

Human approves by editing the issue file and changing status to `strategy-approved`.

## Usage

```bash
/plan:strategy DTL-001
/plan:3-strategy DTL-002
```

## Parameters

- `issue_id`: Issue ID (e.g., DTL-001)

## Workflow

### Step 1: Read Issue Details

```bash
# Read issue file
ISSUE_FILE=$(find .tasks/issues .tasks/epics -name "${ISSUE_ID}.md" 2>/dev/null | head -1)

if [ -z "$ISSUE_FILE" ]; then
  echo "❌ Issue ${ISSUE_ID} not found"
  exit 1
fi

# Display issue
uv run python scripts/dtl_tasks.py show ${ISSUE_ID}
```

Extract from issue:
- **Title**: Issue title
- **Description**: Full description
- **Labels**: All labels (check for `stack:*` label)
- **Status**: Current status
- **Type**: Issue type
- **Parent**: Parent epic (for context)

### Step 2: Validate and Auto-Fix Issue Prerequisites

**Check and auto-fix missing data**:

```markdown
1. **Missing or empty description?**
   if issue.description is empty or missing:
     ⚠️  Issue missing description - generating from title and labels...

     Generate description using:
     - Issue title
     - Issue type from labels (epic/feature/bug/chore)
     - Stack label (backend/frontend/fullstack)
     - Layer labels if present
     - Parent issue context if available

     Use Write tool to update issue file with generated description
     ✅ Auto-generated description for ${ISSUE_ID}

2. **Missing stack: label?**
   if no stack:* label found in frontmatter:
     ⚠️  Missing stack label - inferring from content...

     Analyze title and description to infer stack:
     - Contains "API", "service", "database", "backend" → stack:backend
     - Contains "component", "UI", "page", "frontend" → stack:frontend
     - Contains both or "end-to-end" → stack:fullstack

     Ask user: "Inferred stack:{stack} based on issue content. Confirm? [Y/n]"

     if user confirms:
       uv run python scripts/dtl_tasks.py update ${ISSUE_ID} --add-label "stack:{stack}"
       ✅ Added stack:{stack} label
     else:
       Ask user which stack label to apply

3. **Missing type: label?**
   if no type:* label found:
     ⚠️  Missing type label - inferring from title...

     Infer type from title pattern:
     - Starts with "Epic:" → type:epic
     - Starts with "Fix" or "Bug" → type:bug
     - Contains "refactor", "improve", "update" → type:chore
     - Default → type:feature

     uv run python scripts/dtl_tasks.py update ${ISSUE_ID} --add-label "type:{inferred_type}"
     ✅ Added type:{inferred_type} label

4. **Validation complete**
   ✅ All prerequisites validated and fixed
   - Description: Present
   - Stack label: {stack}
   - Type label: {type}

   → Proceed with strategy generation
```

---

### Step 3: Analyze Codebase

Analyze the codebase to understand relevant patterns and architecture.

**For backend issues**:
```bash
# Find relevant files based on stack and layer
if stack is "backend" or "fullstack":
  # Search for similar implementations
  Use Grep to find patterns related to the issue domain
  Use Glob to find files in relevant layers (atoms, features, molecules, organisms)

  # Read similar implementations for reference
  Read relevant files to understand existing patterns
fi
```

**For frontend issues**:
```bash
if stack is "frontend" or "fullstack":
  # Search for similar components
  Use Grep to find component patterns
  Use Glob to find files in src/components, src/pages, etc.

  # Read similar implementations
  Read relevant files
fi
```

**Extract**:
- List of new files to create
- List of existing files to modify
- Architecture approach description
- Dependencies list
- Testing strategy description

---

### Step 4: Generate Strategy Document

Create strategy file at `.tasks/strategies/${ISSUE_ID}-strategy.md`:

**Format** (must match this structure exactly):
```markdown
# Implementation Strategy: ${ISSUE_ID}

**Issue**: ${ISSUE_ID} - ${ISSUE_TITLE}
**Analyzed**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Stack**: ${STACK}
**Type**: ${TYPE}

## Approach

{High-level technical approach - 2-3 sentences}

## Architecture Impact

**Layer**: {atoms/features/molecules/organisms or frontend equivalent}

**New Files**:
- `{file path}` - {brief description}
- `{file path}` - {brief description}

**Modified Files**:
- `{file path}` - {changes needed}
- `{file path}` - {changes needed}

## Dependencies

- **Depends on**: {other issues if any, or "None"}
- **Packages**: {relevant packages/libraries to use}
- **Patterns**: {relevant code patterns from CLAUDE.md}

## Testing Strategy

- **Unit**: {what to unit test}
- **Integration**: {what to integration test}
- **Coverage Target**: 90%+

## Implementation Sequence

1. {Step 1}
2. {Step 2}
3. {Step 3}
4. {Step 4}
5. {Step 5 - Testing}

## Open Questions

- {Question 1} *(if any)*
- {Question 2} *(if any)*

## Estimated Complexity

**Complexity**: {Low/Medium/High}
**Estimated Time**: {hours estimate}

---

## Approval

To approve this strategy and proceed to spec generation:

1. Review this strategy document
2. Edit `.tasks/issues/${ISSUE_ID}.md`
3. Change status from `awaiting-strategy-review` to `strategy-approved`
4. Run: `/plan:spec ${ISSUE_ID}`
```

Write this to `.tasks/strategies/${ISSUE_ID}-strategy.md`

---

### Step 5: Update Issue Status and History

```bash
# Update issue status
uv run python scripts/dtl_tasks.py update ${ISSUE_ID} --status awaiting-strategy-review

# Add history entry
uv run python scripts/dtl_tasks.py update ${ISSUE_ID} \
  --event "Strategy Generated" \
  --description "Strategy posted to .tasks/strategies/${ISSUE_ID}-strategy.md"

# Update index
uv run python scripts/dtl_tasks.py reindex
```

---

### Step 6: Display Report

Show user-friendly summary of what was accomplished.

```
✅ Implementation Strategy Generated

**Issue**: ${ISSUE_ID} - ${ISSUE_TITLE}
**Strategy File**: .tasks/strategies/${ISSUE_ID}-strategy.md
**Status**: Awaiting strategy review

## Strategy Summary

{Display 2-3 sentence summary of the approach}

**Complexity**: {Low/Medium/High} ({hours})
**Layer**: {atoms/features/molecules/organisms}

## Next Steps

1. Review the strategy:
   cat .tasks/strategies/${ISSUE_ID}-strategy.md

2. Approve the strategy:
   - Edit .tasks/issues/${ISSUE_ID}.md
   - Change: status: awaiting-strategy-review → status: strategy-approved

3. Generate spec (after approval):
   /plan:spec ${ISSUE_ID}
```

---

## Error Handling

### Issue Not Found

```bash
if issue file does not exist:
  echo "❌ Issue ${ISSUE_ID} not found in .tasks/issues/ or .tasks/epics/"
  echo "Available issues:"
  uv run python scripts/dtl_tasks.py list
  exit 1
fi
```

### Strategy Already Exists

```bash
if [ -f ".tasks/strategies/${ISSUE_ID}-strategy.md" ]; then
  echo "⚠️  Strategy already exists for ${ISSUE_ID}"
  read -p "Overwrite? (y/N): " confirm
  if [ "$confirm" != "y" ]; then
    exit 0
  fi
fi
```

---

## Implementation Notes

### No External Dependencies

This command:
- Reads from `.tasks/issues/${ISSUE_ID}.md`
- Writes to `.tasks/strategies/${ISSUE_ID}-strategy.md`
- Updates issue via `dtl_tasks.py` CLI
- No Linear API, no external services

### Human Approval Gate

The status `awaiting-strategy-review` acts as a gate:
1. Strategy is generated but not yet approved
2. Human reviews strategy document
3. Human manually edits issue file to approve (change status to `strategy-approved`)
4. Only then can `/plan:spec` proceed

### Self-Healing Behavior

This command validates and auto-fixes prerequisites:
1. **Missing description?** → Generates from title + labels
2. **Missing stack label?** → Infers from content (with confirmation)
3. **Missing type label?** → Infers from title pattern

Benefits:
- Command rarely fails - fixes most issues automatically
- Can run on incomplete issues - fills in gaps intelligently
- User confirmation required for label inference (safety gate)

Result: Issues are enriched with complete data before strategy generation

---

## Related Commands

- `/plan:decompose` - Creates YAML plan
- `/plan:create` - Creates markdown issues from YAML
- `/plan:spec` - Generates detailed specs (requires approved strategy)
- `/implement` - Implements issues

---

## Examples

### Example 1: Backend Feature

```bash
$ /plan:strategy DTL-002

✅ Implementation Strategy Generated

**Issue**: DTL-002 - Add Redis caching layer
**Strategy File**: .tasks/strategies/DTL-002-strategy.md
**Status**: Awaiting strategy review

## Strategy Summary

Create Redis cache adapter in atoms layer, add caching to UserService in
features layer. Use configuration from CLAUDE.md for patterns.

**Complexity**: Medium (4-5 hours)
**Layer**: atoms, features

## Next Steps

1. Review: cat .tasks/strategies/DTL-002-strategy.md
2. Approve: Edit .tasks/issues/DTL-002.md, change status to strategy-approved
3. Generate spec: /plan:spec DTL-002
```

---

### Example 2: Frontend Component

```bash
$ /plan:strategy DTL-005

✅ Implementation Strategy Generated

**Issue**: DTL-005 - Create LookML preview component
**Strategy File**: .tasks/strategies/DTL-005-strategy.md
**Status**: Awaiting strategy review

## Strategy Summary

Build Preview component using syntax highlighting library. Integrate with
existing generator to show live LookML output.

**Complexity**: Low (2-3 hours)
**Layer**: components

## Next Steps

1. Review: cat .tasks/strategies/DTL-005-strategy.md
2. Approve: Edit .tasks/issues/DTL-005.md, change status to strategy-approved
3. Generate spec: /plan:spec DTL-005
```

---

## Benefits

1. **Self-Healing**: Auto-generates missing descriptions, infers missing labels
2. **Local-First**: All data stored in `.tasks/`, no external dependencies
3. **Git-Friendly**: Strategy documents are markdown, trackable in git
4. **Human Gate**: Manual approval prevents proceeding with bad strategies
5. **Pattern Consistency**: References CLAUDE.md for project patterns
6. **Transparent**: Strategy is human-readable markdown document
