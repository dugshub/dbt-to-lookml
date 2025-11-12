---
description: Create local markdown issues from YAML/JSON
argument-hint: <definition-file> [--dry-run]
allowed-tools:
  - Bash
  - Read
  - Write
---

# Create Issues from Definition

Create local markdown epic + sub-issues from a structured YAML/JSON definition file.

## Purpose

Automates the mechanical work of creating local markdown issues from a decomposed plan. Separates issue **creation** (mechanical) from issue **planning** (strategic).

## Usage

```bash
# Standard mode - create/update issues
/plan:create issue-plan-user-auth.yaml
/plan:2-create issue-plan-caching.yaml

# Dry-run mode - show what would be created/updated
/plan:create my-epic.yaml --dry-run
```

## Variables

- `$1`: Path to definition file (YAML or JSON)
- `--dry-run`: Show what would be created/updated without making changes (exit 0)

## Definition Format

```yaml
epic:
  title: "Epic: Feature name"
  description: "Multi-line epic description"
  labels: [type:epic, stack:backend, priority:high]
  status: refinement  # Optional

  children:
    - title: "Sub-task 1: Component name"
      description: "Detailed description"
      labels: [type:feature, stack:backend]
      status: refinement
```

## Workflow

### Step 1: Read and Validate YAML Structure

Read YAML/JSON file and validate structure:
- Has epic with title + description
- Has children array
- Each child has title + description

If validation fails:
  Report specific missing fields
  exit 1

Generate descriptions for any empty fields:
```markdown
if epic.description is empty:
  ⚠️  Epic description is empty - generating from title...
  Generate description based on:
  - Epic title
  - Child issue titles (what this epic encompasses)
  - Labels (technical scope)
  Update YAML epic.description

for each child with empty description:
  ⚠️  Child "{title}" missing description - generating...
  Generate description based on:
  - Child title
  - Child labels
  - Epic context
  Update YAML child.description

✅ All descriptions validated
```

### Step 2: Check Existing Issues (Idempotent Mode)

**This command is idempotent - safe to run multiple times**

Check if epic already exists:
```bash
# Search for epic with matching title in .tasks/epics/
EPIC_FILES=$(grep -l "title: \"${EPIC_TITLE}\"" .tasks/epics/*.md 2>/dev/null || echo "")

if [ -n "$EPIC_FILES" ]; then
  EPIC_EXISTS=true
  EPIC_ID=$(basename "$EPIC_FILES" .md)

  # Compare YAML vs markdown
  # - Description different? → Add to update_list
  # - Labels different? → Add to update_list
  # - Status different? → Add to update_list
  # - All same? → Log "Epic unchanged, skipping"
else
  EPIC_EXISTS=false
  Add epic to create_list
fi
```

Check each child:
```bash
for each child in epic.children:
  # Search for child with matching title in .tasks/issues/
  CHILD_FILE=$(grep -l "title: \"${CHILD_TITLE}\"" .tasks/issues/*.md 2>/dev/null || echo "")

  if [ -n "$CHILD_FILE" ]; then
    CHILD_ID=$(basename "$CHILD_FILE" .md)

    # Compare YAML vs markdown
    # - Description different? → Add to update_list
    # - Labels different? → Add to update_list
    # - Status different? → Add to update_list
    # - Parent different or missing? → Add to update_list
    # - All same? → Add to skip_list
  else:
    Add child to create_list
  fi
done
```

Display plan:
```
📋 Idempotent Issue Sync Plan:

Epic:
  ✅ Exists: DTL-001 (no changes needed)
  OR
  📝 Will create: "Epic: User Authentication"
  OR
  🔄 Will update: DTL-001 (description, labels changed)

Children:
  📝 Create: 2 issues
    - "Implement JWT tokens"
    - "Add password hashing"
  🔄 Update: 1 issue
    - DTL-003: "Create login endpoint" (labels changed)
  ✅ Skip: 0 issues (already in sync)
```

### Step 3: Dry Run Check

If `--dry-run` flag is set:
- Display the plan above
- Exit without creating files
- Exit code 0

### Step 4: Execute Plan - Create or Update Epic

```bash
# Use dtl_tasks.py to generate issue ID
if epic in create_list:
  EPIC_ID=$(uv run python scripts/dtl_tasks.py next-id)

  # Create epic markdown file
  cat > .tasks/epics/${EPIC_ID}.md <<EOF
---
id: ${EPIC_ID}
title: "${EPIC_TITLE}"
type: epic
status: ${EPIC_STATUS:-refinement}
labels:
$(for label in "${EPIC_LABELS[@]}"; do echo "  - $label"; done)
created: $(date -u +%Y-%m-%dT%H:%M:%SZ)
updated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
children: []
---

# ${EPIC_ID}: ${EPIC_TITLE}

## Problem Statement
${EPIC_DESCRIPTION}

## Success Criteria
- [ ] All sub-issues completed
- [ ] Integration tests passing
- [ ] Documentation updated

## Sub-Issues
*Will be populated as children are created*

## Links
- Plan: ${YAML_FILE}

## History
### $(date -u +%Y-%m-%d\ %H:%M) - Epic Created
Created from plan: ${YAML_FILE}
EOF

  echo "✅ Created Epic: ${EPIC_ID} - ${EPIC_TITLE}"
fi

if epic in update_list:
  # Update epic frontmatter using Python or yq
  uv run python scripts/dtl_tasks.py update ${EPIC_ID} --status ${NEW_STATUS}
  # Update labels, description manually via Write tool
  echo "🔄 Updated Epic: ${EPIC_ID} - {changes}"
fi

if epic unchanged:
  echo "✅ Epic: ${EPIC_ID} - ${EPIC_TITLE} (no changes)"
fi
```

### Step 5: Execute Plan - Create or Update Children

```bash
CHILD_IDS=()

for each child in create_list:
  CHILD_ID=$(uv run python scripts/dtl_tasks.py next-id)
  CHILD_IDS+=("$CHILD_ID")

  # Extract child details from YAML
  CHILD_TITLE="${child.title}"
  CHILD_DESC="${child.description}"
  CHILD_STATUS="${child.status:-refinement}"
  CHILD_LABELS=("${child.labels[@]}")

  # Create child markdown file
  cat > .tasks/issues/${CHILD_ID}.md <<EOF
---
id: ${CHILD_ID}
title: "${CHILD_TITLE}"
type: ${child.type:-feature}
stack: ${child.stack:-backend}
status: ${CHILD_STATUS}
labels:
$(for label in "${CHILD_LABELS[@]}"; do echo "  - $label"; done)
created: $(date -u +%Y-%m-%dT%H:%M:%SZ)
updated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
parent: ${EPIC_ID}
---

# ${CHILD_ID}: ${CHILD_TITLE}

## Problem Statement
${CHILD_DESC}

## Success Criteria
- [ ] Implementation complete
- [ ] Tests passing
- [ ] Documentation updated

## Links
- Epic: [${EPIC_ID}](./../epics/${EPIC_ID}.md)
- Strategy: [.tasks/strategies/${CHILD_ID}-strategy.md](./../strategies/${CHILD_ID}-strategy.md)
- Spec: [.tasks/specs/${CHILD_ID}-spec.md](./../specs/${CHILD_ID}-spec.md)

## History
### $(date -u +%Y-%m-%d\ %H:%M) - Issue Created
Created from epic ${EPIC_ID}
EOF

  echo "✅ Created: ${CHILD_ID} - ${CHILD_TITLE}"
done

for each child in update_list:
  # Update child using dtl_tasks.py
  uv run python scripts/dtl_tasks.py update ${CHILD_ID} --status ${NEW_STATUS}
  echo "🔄 Updated: ${CHILD_ID} - {changes}"
done

for each child in skip_list:
  echo "✅ Synced: ${CHILD_ID} - ${CHILD_TITLE} (no changes)"
done
```

### Step 6: Update Epic with Children Links

```bash
# Update epic markdown file with children list
# Read current epic file
EPIC_FILE=".tasks/epics/${EPIC_ID}.md"

# Update frontmatter children array (use yq or Python)
# Update "Sub-Issues" section in body
SUB_ISSUES_TEXT=""
for CHILD_ID in "${CHILD_IDS[@]}"; do
  CHILD_TITLE=$(grep "^title:" .tasks/issues/${CHILD_ID}.md | cut -d'"' -f2)
  CHILD_STATUS=$(grep "^status:" .tasks/issues/${CHILD_ID}.md | cut -d' ' -f2)
  SUB_ISSUES_TEXT+="- [${CHILD_ID}: ${CHILD_TITLE}](./../issues/${CHILD_ID}.md) - 📋 ${CHILD_STATUS}\n"
done

# Use Write tool to update epic file's "Sub-Issues" section
```

### Step 7: Update Index

```bash
# Regenerate index.md
uv run python scripts/dtl_tasks.py reindex

echo "✅ Index updated"
```

### Step 8: Report Results

Display summary:
```
✅ Issue Sync Complete!

Epic: DTL-001 - "Epic: User Authentication"
  Status: Created
  File: .tasks/epics/DTL-001.md

Children:
  📝 Created: 2
    - DTL-002 - "Implement JWT tokens"
    - DTL-003 - "Add password hashing"
  🔄 Updated: 0
  ✅ Already synced: 0

Files created:
  .tasks/epics/DTL-001.md
  .tasks/issues/DTL-002.md
  .tasks/issues/DTL-003.md
  .tasks/index.md (updated)

YAML and local tasks are now in sync.

Next steps:
  /plan:strategy DTL-002
  /plan:strategy DTL-003
```

Generate JSON output (optional):
```json
{
  "epic": "DTL-001",
  "children": ["DTL-002", "DTL-003"],
  "created": ["DTL-002", "DTL-003"],
  "updated": [],
  "skipped": []
}
```

## Error Handling

**Invalid YAML**: Report syntax errors with line numbers
**Missing Required Fields**: Report which fields are missing (title, description)
**Label Conflicts**: Log warning, continue with available labels
**File Write Failures**: Report error, return partial results

## Notes

- **Idempotent**: Safe to run multiple times - creates missing, updates changed, skips synced
- **Self-Healing**: Auto-generates missing descriptions from title and labels
- **Dry-Run**: --dry-run shows plan without creating files
- **Local Only**: No external API calls, all data in `.tasks/` directory
- **Git-Friendly**: All files are markdown, trackable in git
- **YAML Sync**: Edit YAML and re-run to update markdown issues

## Idempotent Behavior

This command can be run multiple times safely:
- **Issues exist with same title?** → Compare and update if changed
- **Issues missing?** → Create new
- **Labels changed in YAML?** → Update labels in markdown
- **Descriptions updated in YAML?** → Update descriptions in markdown
- **Status changed in YAML?** → Update status in markdown
- **Everything synced?** → Skip with confirmation message

Result: YAML and markdown stay perfectly in sync

## Implementation Notes

- Uses `scripts/dtl_tasks.py` CLI for ID generation and updates
- Frontmatter contains structured data (id, title, type, status, labels, dates)
- Body contains human-readable content (description, success criteria, history)
- History entries are appended with timestamps
- Parent-child relationships tracked in frontmatter and as markdown links
