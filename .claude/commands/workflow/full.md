---
description: Full workflow from task description to implementation
argument-hint: <task-description> [--auto|--interactive] [--plan-only]
allowed-tools:
  - Bash
  - Read
  - SlashCommand
  - TodoWrite
  - AskUserQuestion
---

# Workflow Full - Complete End-to-End Workflow

Execute the complete workflow from task description to implementation: decompose → create → plan → implement.

## Purpose

Single command that chains together the entire workflow:
1. **Decompose** requirements into YAML issue plan
2. **Create** local markdown issues from YAML
3. **Batch Plan** generate strategies and specs (parallel)
4. **Execute** implementation (optional, sequential)

Perfect for: Taking a raw feature request all the way to implementation with one command.

## Usage

```bash
# Full workflow (interactive)
/workflow:full "Add timezone conversion configuration support"

# Fully automated (no prompts)
/workflow:full "Add timezone conversion configuration support" --auto

# Plan only (decompose → create → strategies/specs, no implementation)
/workflow:full "Add timezone conversion configuration support" --plan-only

# Interactive with checkpoints (default)
/workflow:full "Add timezone conversion configuration support" --interactive
```

## Parameters

- `task_description`: Natural language description of the feature/task (required)
- `--auto`: Fully automated, no prompts (assumes all yes)
- `--interactive`: Ask before each major phase (default)
- `--plan-only`: Only execute decompose + create + planning (skip implementation)
- `--auto-accept`: Skip decomposition approval (auto-accept YAML)

## Workflow

### Step 0: Initialize Todo List

```markdown
Create comprehensive todo list tracking all phases:

[
  {"content": "Decompose requirements to YAML plan", "status": "pending", "activeForm": "Decomposing requirements to YAML plan"},
  {"content": "Create issues from YAML plan", "status": "pending", "activeForm": "Creating issues from YAML plan"},
  {"content": "Generate strategies for all issues", "status": "pending", "activeForm": "Generating strategies for all issues"},
  {"content": "Generate specs for all issues", "status": "pending", "activeForm": "Generating specs for all issues"},
  {"content": "Implement all issues", "status": "pending", "activeForm": "Implementing all issues"},
  {"content": "Run quality gates", "status": "pending", "activeForm": "Running quality gates"},
  {"content": "Create pull request", "status": "pending", "activeForm": "Creating pull request"}
]
```

### Step 1: Parse Arguments

```bash
# Parse task description and flags
TASK_DESCRIPTION="$1"
MODE="interactive"
PHASE="full"
AUTO_ACCEPT_DECOMPOSE=false

for arg in "$@"; do
  case $arg in
    --auto)
      MODE="auto"
      AUTO_ACCEPT_DECOMPOSE=true
      ;;
    --interactive)
      MODE="interactive"
      ;;
    --plan-only)
      PHASE="plan"
      ;;
    --auto-accept)
      AUTO_ACCEPT_DECOMPOSE=true
      ;;
  esac
done

# Validate task description
if [ -z "$TASK_DESCRIPTION" ]; then
  echo "❌ Error: Task description required"
  echo "Usage: /workflow:full \"<task description>\" [--auto|--interactive] [--plan-only]"
  exit 1
fi
```

---

### Step 2: Phase 1 - Decompose Requirements to YAML

Mark todo as in_progress: "Decompose requirements to YAML plan"

**Interactive mode:** Ask user first

```markdown
if MODE is "interactive":
  Use AskUserQuestion:
  "Start requirements decomposition for: '${TASK_DESCRIPTION}'?"
  Options:
    - "Yes, decompose" (proceed)
    - "I have YAML already" (ask for path, skip to Step 3)
    - "Abort" (exit)
```

**Execute decomposition:**

```bash
# Build decompose command
DECOMPOSE_CMD="/plan:1-decompose \"${TASK_DESCRIPTION}\""

if AUTO_ACCEPT_DECOMPOSE is true:
  DECOMPOSE_CMD="${DECOMPOSE_CMD} --auto-accept"
fi

# Execute via SlashCommand
Use SlashCommand tool to run: ${DECOMPOSE_CMD}

# Wait for command to complete and capture output
```

**Parse output to extract YAML file path:**

```bash
# Look for pattern: "✅ YAML plan saved: .tasks/plans/issue-plan-*.yaml"
YAML_FILE=$(echo "$OUTPUT" | grep -oE "\.tasks/plans/issue-plan-[a-z0-9-]+\.yaml" | head -1)

if [ -z "$YAML_FILE" ]; then
  echo "❌ Error: Failed to extract YAML file path from decompose output"
  exit 1
fi

echo "📄 YAML plan: ${YAML_FILE}"
```

Mark todo as completed: "Decompose requirements to YAML plan"

---

### Step 3: Phase 2 - Create Issues from YAML

Mark todo as in_progress: "Create issues from YAML plan"

**Interactive mode:** Ask user

```markdown
if MODE is "interactive":
  Use AskUserQuestion:
  "Create markdown issues from ${YAML_FILE}?"
  Options:
    - "Yes, create issues" (proceed)
    - "Let me review YAML first" (display file path, wait for user confirmation)
    - "Abort" (exit)
```

**Execute issue creation:**

```bash
# Execute via SlashCommand
Use SlashCommand tool to run: /plan:2-create ${YAML_FILE}

# Wait for command to complete and capture output
```

**Parse output to extract issue IDs:**

```bash
# Look for patterns:
# "✅ Created Epic: DTL-XXX - Title"
# "✅ Created: DTL-XXX - Title"

# Extract epic ID
EPIC_ID=$(echo "$OUTPUT" | grep -oE "Created Epic: (DTL-[0-9]+)" | grep -oE "DTL-[0-9]+" | head -1)

# Extract child IDs
ISSUE_IDS=($(echo "$OUTPUT" | grep -oE "Created: (DTL-[0-9]+)" | grep -oE "DTL-[0-9]+"))

# If no children were created but epic was, use epic ID
if [ ${#ISSUE_IDS[@]} -eq 0 ] && [ -n "$EPIC_ID" ]; then
  # Check if epic has children in frontmatter
  CHILDREN=$(grep "^  - DTL-" ".tasks/epics/${EPIC_ID}.md" | sed 's/^  - //' || echo "")

  if [ -n "$CHILDREN" ]; then
    ISSUE_IDS=($CHILDREN)
  else
    ISSUE_IDS=("$EPIC_ID")
  fi
fi

if [ ${#ISSUE_IDS[@]} -eq 0 ]; then
  echo "❌ Error: No issue IDs extracted from create output"
  exit 1
fi

echo "📋 Created issues: ${ISSUE_IDS[@]}"
```

Mark todo as completed: "Create issues from YAML plan"

---

### Step 4: Phase 3 - Batch Plan (Strategies + Specs)

Mark todo as in_progress: "Generate strategies for all issues"

**Interactive mode:** Ask user

```markdown
if MODE is "interactive":
  Use AskUserQuestion:
  "Generate strategies and specs for ${#ISSUE_IDS[@]} issues?"
  Options:
    - "Yes, generate all" (proceed)
    - "Skip to implementation" (skip to Step 5, only if PHASE is "full")
    - "Abort" (exit)
```

**Determine planning command:**

```bash
# Build planning command based on PHASE
if PHASE is "plan":
  # Plan-only mode: use batch-plan (strategies + specs, no implementation)
  PLAN_CMD="/workflow:batch-plan ${ISSUE_IDS[@]}"

  if MODE is "auto":
    PLAN_CMD="${PLAN_CMD} --auto"
  fi

  # Execute via SlashCommand
  Use SlashCommand tool to run: ${PLAN_CMD}

  # Mark planning todos as completed
  Mark completed: "Generate strategies for all issues"
  Mark completed: "Generate specs for all issues"

  # Skip to final report (no implementation in plan-only mode)
  Jump to Step 6

else:
  # Full mode: use workflow:execute with all phases
  EXECUTE_CMD="/workflow:execute ${ISSUE_IDS[@]}"

  if MODE is "auto":
    EXECUTE_CMD="${EXECUTE_CMD} --auto"
  elif MODE is "interactive":
    EXECUTE_CMD="${EXECUTE_CMD} --interactive"
  fi

  # Execute via SlashCommand (this will handle strategies, specs, implementation, quality gates, PR)
  Use SlashCommand tool to run: ${EXECUTE_CMD}

  # Mark all remaining todos as completed
  Mark completed: "Generate strategies for all issues"
  Mark completed: "Generate specs for all issues"
  Mark completed: "Implement all issues"
  Mark completed: "Run quality gates"
  Mark completed: "Create pull request"

  # Jump to final report
  Jump to Step 6
fi
```

---

### Step 5: (This step is now handled by /workflow:execute delegation in Step 4)

*Removed - implementation is delegated to /workflow:execute*

---

### Step 6: Final Report

```markdown
Display comprehensive summary:

═══════════════════════════════════════════════════════════
✅ FULL WORKFLOW COMPLETE
═══════════════════════════════════════════════════════════

Task: "${TASK_DESCRIPTION}"

Phases Completed:
  ✅ Requirements decomposition
  ✅ Issue creation
  ✅ Strategy generation (parallel)
  ✅ Spec generation (parallel)
$(if PHASE is "full":)
  ✅ Implementation (sequential)
  ✅ Quality gates
  ✅ Pull request creation
$(fi)

Artifacts Created:
  📄 YAML Plan: ${YAML_FILE}
  📋 Epic: ${EPIC_ID}
  📋 Issues: ${#ISSUE_IDS[@]}
$(for id in ISSUE_IDS; do
  TITLE=$(grep "^title:" ".tasks/issues/${id}.md" | cut -d'"' -f2)
  echo "    - ${id}: ${TITLE}"
done)
  📋 Strategies: .tasks/strategies/${ISSUE_ID}-strategy.md (for each)
  📋 Specs: .tasks/specs/${ISSUE_ID}-spec.md (for each)
$(if PHASE is "full":)
  🔀 Pull Request: ${PR_URL}
$(fi)

$(if PHASE is "plan":)
Next Steps:
  Review strategies and specs, then run:
    /workflow:execute ${ISSUE_IDS[@]} --implement-only
$(else:)
Next Steps:
  1. Review PR: ${PR_URL}
  2. Address review comments if needed
  3. Merge when approved
  4. Close issues:
     $(for id in ISSUE_IDS; do echo "make tasks-update ID=${id} STATUS=done"; done)
$(fi)

═══════════════════════════════════════════════════════════
```

---

## Execution Modes

### Auto Mode (`--auto`)

- No prompts at any phase
- Auto-accepts decomposition YAML
- Proceeds through all steps automatically
- Best for: Trusted workflows, simple tasks

### Interactive Mode (`--interactive`) - Default

- Asks before decomposition starts
- Allows review of YAML before issue creation
- Asks before strategy/spec generation
- Delegates interactive behavior to `/workflow:execute`
- Best for: Complex tasks, quality assurance

### Plan Only (`--plan-only`)

- Executes: Decompose → Create → Strategies + Specs
- Skips: Implementation
- Best for: Batch planning, review cycles, Friday afternoon prep

---

## Command Chain

This command chains together:

1. **`/plan:1-decompose`** - Deep analysis → YAML plan
2. **`/plan:2-create`** - YAML → Markdown issues (idempotent)
3. **`/workflow:execute`** - Full execution (or batch-plan if plan-only)

Each sub-command is executed via SlashCommand tool, with output parsing to pass data forward.

---

## Error Handling

### Decomposition Failures

- Report validation errors
- Allow user to fix task description and retry
- In auto mode: Exit with error

### Issue Creation Failures

- Report YAML validation errors
- Display which fields are missing
- Exit with error

### Planning/Implementation Failures

- Delegated to `/workflow:execute` (see that command's error handling)
- Reports issues that failed
- Allows partial completion

---

## Examples

### Example 1: Full Workflow (Interactive)

```bash
/workflow:full "Add timezone conversion configuration support for dimension groups"
```

**Flow:**
1. Decomposes task → asks to approve YAML
2. Creates issues → shows epic + children
3. Asks to generate strategies/specs
4. Asks to implement
5. Creates PR

**Result:** Complete implementation with PR

---

### Example 2: Full Workflow (Automated)

```bash
/workflow:full "Add support for LookML sets in explores" --auto
```

**Flow:**
- No prompts
- Decomposes → creates → plans → implements → PR
- Stops only on errors

**Result:** Complete implementation with PR (5-15 minutes depending on complexity)

---

### Example 3: Planning Session

```bash
/workflow:full "Implement error handling improvements" --plan-only --interactive
```

**Flow:**
1. Decomposes task → asks to approve YAML
2. Creates issues → shows epic + children
3. Generates strategies (parallel)
4. Generates specs (parallel)
5. Stops (no implementation)

**Result:** Issues with strategies and specs ready for review

---

## Benefits

1. **Single Command**: Task description → implementation in one command
2. **Automation**: Chains 4 commands automatically
3. **Flexibility**: Auto, interactive, or plan-only modes
4. **Idempotent**: Safe to re-run (issue creation is idempotent)
5. **Trackable**: TodoWrite tracks all phases
6. **Efficient**: Parallel planning phases
7. **Safe**: Interactive checkpoints by default

---

## Related Commands

- `/plan:1-decompose` - Requirements decomposition (this calls it)
- `/plan:2-create` - Issue creation (this calls it)
- `/workflow:batch-plan` - Batch planning only (alternative to this with --plan-only)
- `/workflow:execute` - Execute issues (this calls it)

---

## Notes

- **Delegation Model**: Delegates to sub-commands via SlashCommand tool
- **Output Parsing**: Extracts YAML path and issue IDs from command outputs
- **Idempotent**: Can re-run safely (issue creation checks for existing issues)
- **Interactive Default**: Safe mode with checkpoints
- **Auto Mode**: Fast but requires trust in automated decisions
- **Plan Only**: Perfect for batch planning sessions

---

## Use Cases

### Friday Afternoon Planning

```bash
/workflow:full "Implement caching layer" --plan-only --auto
```

- Generates full plan with strategies/specs
- Team reviews Monday morning
- Implement Monday with: `/workflow:execute EPIC-ID --implement-only`

### Rapid Prototyping

```bash
/workflow:full "Add new export format" --auto
```

- Decomposes, plans, implements, creates PR
- Perfect for small, well-defined features

### Careful Development

```bash
/workflow:full "Refactor parser architecture" --interactive
```

- Checkpoints at each phase
- Review strategies before specs
- Review specs before implementation
- Perfect for complex, high-risk changes
