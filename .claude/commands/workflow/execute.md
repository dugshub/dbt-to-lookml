---
description: Execute full workflow for one or more issues
argument-hint: <issue-ids...> [--auto|--interactive] [--plan-only|--implement-only]
allowed-tools:
  - Bash
  - Read
  - Task
  - TodoWrite
  - AskUserQuestion
---

# Workflow Execute - End-to-End Issue Execution

Execute the complete workflow for one or more issues: strategy → spec → implement → test.

## Purpose

Automate the full lifecycle of issues from planning to implementation, with optional human checkpoints. Supports:
- **Single issue**: Execute one issue end-to-end
- **Multiple issues**: Execute several related/unrelated issues
- **Epic**: Execute an epic and all its children
- **Parallel execution**: Strategies and specs run in parallel
- **Automation levels**: Fully automated or interactive with checkpoints

## Usage

```bash
# Execute single issue (interactive)
/workflow:execute DTL-002

# Execute multiple issues
/workflow:execute DTL-002 DTL-003 DTL-004

# Execute epic and all children
/workflow:execute DTL-001  # Epic ID

# Fully automated (no prompts)
/workflow:execute DTL-002 --auto

# Interactive with checkpoints (default)
/workflow:execute DTL-002 --interactive

# Only planning phase (strategy + spec)
/workflow:execute DTL-002 --plan-only

# Only implementation phase (assumes strategy/spec exist)
/workflow:execute DTL-002 --implement-only
```

## Parameters

- `issue_ids...`: One or more issue IDs (DTL-001, DTL-002, etc.)
- `--auto`: Fully automated, no prompts (assumes all yes)
- `--interactive`: Ask before each major phase (default)
- `--plan-only`: Only execute planning (strategy + spec), skip implementation
- `--implement-only`: Skip planning, only implement (assumes strategy/spec exist)
- `--parallel`: Allow parallel implementation (experimental, may conflict)

## Workflow

### Step 1: Parse Arguments and Detect Epic

```bash
# Parse issue IDs
ISSUE_IDS=()
MODE="interactive"
PHASE="full"
PARALLEL_IMPL=false

for arg in "$@"; do
  case $arg in
    --auto)
      MODE="auto"
      ;;
    --interactive)
      MODE="interactive"
      ;;
    --plan-only)
      PHASE="plan"
      ;;
    --implement-only)
      PHASE="implement"
      ;;
    --parallel)
      PARALLEL_IMPL=true
      ;;
    DTL-*)
      ISSUE_IDS+=("$arg")
      ;;
  esac
done

# Validate at least one issue
if [ ${#ISSUE_IDS[@]} -eq 0 ]; then
  echo "❌ Error: At least one issue ID required"
  echo "Usage: /workflow:execute DTL-001 [DTL-002...] [--auto|--interactive]"
  exit 1
fi
```

**Detect if first ID is an epic:**

```bash
FIRST_ID="${ISSUE_IDS[0]}"

# Check if it's an epic
if [ -f ".tasks/epics/${FIRST_ID}.md" ]; then
  echo "📦 Detected epic: ${FIRST_ID}"

  # Read children from epic frontmatter
  CHILDREN=$(grep "^  - DTL-" ".tasks/epics/${FIRST_ID}.md" | sed 's/^  - //' || echo "")

  if [ -n "$CHILDREN" ]; then
    # Add children to issue list
    CHILD_ARRAY=($CHILDREN)
    ISSUE_IDS=("${CHILD_ARRAY[@]}")

    echo "📋 Found ${#ISSUE_IDS[@]} child issues:"
    for id in "${ISSUE_IDS[@]}"; do
      TITLE=$(grep "^title:" ".tasks/issues/${id}.md" | cut -d'"' -f2)
      echo "  - ${id}: ${title}"
    done
  else
    echo "⚠️  Epic has no children, will execute epic only"
    ISSUE_IDS=("${FIRST_ID}")
  fi
elif [ ${#ISSUE_IDS[@]} -gt 1 ]; then
  echo "📋 Executing ${#ISSUE_IDS[@]} issues:"
  for id in "${ISSUE_IDS[@]}"; do
    TITLE=$(grep "^title:" ".tasks/issues/${id}.md" | cut -d'"' -f2)
    echo "  - ${id}: ${TITLE}"
  done
fi
```

---

### Step 2: Initialize Todo List

Use TodoWrite to track all tasks:

```markdown
Create todo list with the following items:

For each issue:
  - "Generate strategy for ${ISSUE_ID}"
  - "Generate spec for ${ISSUE_ID}"
  - "Implement ${ISSUE_ID}"
  - "Run quality gates for ${ISSUE_ID}"
```

**Example for 3 issues:**

```json
[
  {"content": "Generate strategy for DTL-002", "status": "pending", "activeForm": "Generating strategy for DTL-002"},
  {"content": "Generate strategy for DTL-003", "status": "pending", "activeForm": "Generating strategy for DTL-003"},
  {"content": "Generate strategy for DTL-004", "status": "pending", "activeForm": "Generating strategy for DTL-004"},
  {"content": "Generate spec for DTL-002", "status": "pending", "activeForm": "Generating spec for DTL-002"},
  {"content": "Generate spec for DTL-003", "status": "pending", "activeForm": "Generating spec for DTL-003"},
  {"content": "Generate spec for DTL-004", "status": "pending", "activeForm": "Generating spec for DTL-004"},
  {"content": "Implement DTL-002", "status": "pending", "activeForm": "Implementing DTL-002"},
  {"content": "Implement DTL-003", "status": "pending", "activeForm": "Implementing DTL-003"},
  {"content": "Implement DTL-004", "status": "pending", "activeForm": "Implementing DTL-004"},
  {"content": "Run quality gates", "status": "pending", "activeForm": "Running quality gates"}
]
```

---

### Step 3: Phase 1 - Generate Strategies (Parallel)

**Interactive mode:** Ask user

```markdown
if MODE is "interactive":
  Use AskUserQuestion:
  "Generate strategies for all ${#ISSUE_IDS[@]} issues?"
  Options:
    - "Yes, generate all" (proceed)
    - "Skip, strategies exist" (skip to spec phase)
    - "Abort" (exit)
```

**Execute in parallel using Task subagents:**

```markdown
⚠️ CRITICAL: You MUST delegate to Task() subagents, NOT run commands directly.

For each issue in ISSUE_IDS, create a Task subagent call:

Use Task tool to launch subagent with:
- subagent_type: "general-purpose"
- description: "Generate strategy for ${ISSUE_ID}"
- prompt: "Execute /plan:strategy ${ISSUE_ID}. Read the issue file, analyze codebase, generate comprehensive implementation strategy, save to .tasks/strategies/${ISSUE_ID}-strategy.md, update issue with state:has-strategy label. Report summary when complete."

⚠️ IMPORTANT: Send ALL Task calls in a SINGLE message (parallel execution)

Example single message with multiple Tasks:
- Task 1: Generate strategy for DTL-002
- Task 2: Generate strategy for DTL-003
- Task 3: Generate strategy for DTL-004

Wait for all to complete, then mark todos as completed.
```

**Mark todos complete:**

```markdown
After all strategy subagents complete:

Update todo list - mark all "Generate strategy" items as completed
```

---

### Step 4: Phase 2 - Generate Specs (Parallel)

**Interactive mode:** Ask user

```markdown
if MODE is "interactive":
  Use AskUserQuestion:
  "Review strategies and generate specs for all ${#ISSUE_IDS[@]} issues?"
  Options:
    - "Yes, generate specs" (proceed)
    - "Let me review first" (display strategy file paths, wait for user)
    - "Skip to implementation" (skip to implement phase)
    - "Abort" (exit)
```

**Execute in parallel using Task subagents:**

```markdown
⚠️ CRITICAL: You MUST delegate to Task() subagents, NOT run commands directly.

For each issue in ISSUE_IDS, create a Task subagent call:

Use Task tool to launch subagent with:
- subagent_type: "general-purpose"
- description: "Generate spec for ${ISSUE_ID}"
- prompt: "Execute /implement:spec ${ISSUE_ID}. Read the strategy from .tasks/strategies/${ISSUE_ID}-strategy.md, analyze codebase for patterns, generate detailed implementation spec, save to .tasks/specs/${ISSUE_ID}-spec.md, update issue status to ready and add state:has-spec label. Report summary when complete."

⚠️ IMPORTANT: Send ALL Task calls in a SINGLE message (parallel execution)

Wait for all to complete, then mark todos as completed.
```

**Mark todos complete:**

```markdown
After all spec subagents complete:

Update todo list - mark all "Generate spec" items as completed
```

---

### Step 5: Phase 3 - Implementation (Sequential or Parallel)

**Interactive mode:** Ask user

```markdown
if MODE is "interactive":
  Use AskUserQuestion:
  "Review specs and implement all ${#ISSUE_IDS[@]} issues?"
  Options:
    - "Yes, implement all" (proceed)
    - "Let me review specs first" (display spec file paths, wait for user)
    - "Implement one by one" (ask before each issue)
    - "Abort" (exit)
```

**Default: Sequential implementation** (safer, avoids git conflicts)

```markdown
For each issue in ISSUE_IDS (one at a time):

  Mark todo as in_progress for current issue

  Use Task tool to launch subagent with:
  - subagent_type: "general-purpose"
  - model: "haiku"
  - description: "Implement ${ISSUE_ID}"
  - prompt: "Execute /implement ${ISSUE_ID}. Read spec from .tasks/specs/${ISSUE_ID}-spec.md, create feature branch if needed, implement according to spec with tests, run quality gates (format, lint, type-check, tests), commit all changes. Do NOT create PR yet. Report when complete with summary of files changed."

  Wait for completion

  Mark todo as completed for current issue

  if MODE is "interactive" and more issues remain:
    Ask user: "Continue to next issue (${NEXT_ID})?"
    If no: break
```

**Experimental: Parallel implementation** (if --parallel flag)

```markdown
⚠️ EXPERIMENTAL: May cause git conflicts if issues touch same files

if PARALLEL_IMPL is true:

  Use Task tool to launch subagents in parallel:
  - For each issue: Same as above (with model: "haiku") but all in SINGLE message

  Wait for all to complete

  Handle merge conflicts if any arise
```

---

### Step 6: Phase 4 - Quality Gates (Once for All)

**Run final quality gates across all changes:**

```markdown
Mark "Run quality gates" todo as in_progress

# Run comprehensive quality checks
make quality-gate

If failures:
  Display errors

  if MODE is "interactive":
    Ask user: "Quality gates failed. Fix and retry?"
    If yes: Wait for manual fixes, retry quality-gate
    If no: Report partial completion

  if MODE is "auto":
    Report failures and exit

If success:
  Mark todo as completed
  Proceed to PR creation
```

---

### Step 7: Create Pull Request

```markdown
# Determine PR scope
if single issue:
  PR_TITLE="${ISSUE_ID}: ${ISSUE_TITLE}"
elif multiple issues from same epic:
  PR_TITLE="${EPIC_ID}: ${EPIC_TITLE}"
else:
  PR_TITLE="feat: implement ${#ISSUE_IDS[@]} issues"

# Generate PR body
PR_BODY="
## Summary

Implemented ${#ISSUE_IDS[@]} issue(s):
$(for id in ISSUE_IDS; do echo "- ${id}: ${title}"; done)

## Issues

$(for id in ISSUE_IDS; do echo "Closes ${id}"; done)

## Changes

{High-level summary}

## Quality Gates

✅ Format
✅ Lint
✅ Type Check
✅ Tests (${COVERAGE}% coverage)

## Specs

$(for id in ISSUE_IDS; do echo "- Spec: .tasks/specs/${id}-spec.md"; done)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
"

# Create PR
gh pr create --title "${PR_TITLE}" --body "${PR_BODY}"

# Capture PR URL
PR_URL=$(gh pr view --json url -q .url)

# Update all issues
for id in ISSUE_IDS; do
  uv run python scripts/dtl_tasks.py update ${id} --status in-review

  uv run python scripts/dtl_tasks.py update ${id} \
    --event "PR Created" \
    --description "Pull request: ${PR_URL}"
done

# Reindex
uv run python scripts/dtl_tasks.py reindex
```

---

### Step 8: Final Report

```markdown
Display comprehensive summary:

═══════════════════════════════════════════════════════════
✅ WORKFLOW EXECUTION COMPLETE
═══════════════════════════════════════════════════════════

Issues Processed: ${#ISSUE_IDS[@]}
$(for id in ISSUE_IDS; do
  TITLE=$(grep "^title:" ".tasks/issues/${id}.md" | cut -d'"' -f2)
  echo "  ✅ ${id}: ${TITLE}"
done)

Phases Completed:
  ✅ Strategy generation (parallel)
  ✅ Spec generation (parallel)
  ✅ Implementation (sequential)
  ✅ Quality gates
  ✅ PR creation

Pull Request:
  URL: ${PR_URL}
  Status: in-review

Changes Summary:
  Files created: ${FILES_CREATED}
  Files modified: ${FILES_MODIFIED}
  Tests added: ${TESTS_ADDED}
  Coverage: ${COVERAGE}%

Git:
$(git diff --stat ${BASE_BRANCH}...HEAD)

Next Steps:
  1. Review PR: ${PR_URL}
  2. Address review comments if needed
  3. Merge when approved
  4. Update issues to done:
     $(for id in ISSUE_IDS; do echo "make tasks-update ID=${id} STATUS=done"; done)

═══════════════════════════════════════════════════════════
```

---

## Execution Modes

### Auto Mode (`--auto`)

- No prompts at any phase
- Proceeds through all steps automatically
- Stops only on critical errors
- Best for: Trusted workflows, simple issues

### Interactive Mode (`--interactive`) - Default

- Asks before each major phase
- Allows review of strategies/specs
- Can abort or skip phases
- Best for: Complex issues, quality assurance

### Plan Only (`--plan-only`)

- Executes: Strategy + Spec generation
- Skips: Implementation
- Best for: Batch planning, review cycles

### Implement Only (`--implement-only`)

- Skips: Strategy + Spec generation
- Executes: Implementation only
- Requires: Strategies/specs already exist
- Best for: Re-running after fixes

---

## Parallel Execution Strategy

### Always Parallel

1. **Strategy Generation**: Safe to run in parallel (read-only analysis)
2. **Spec Generation**: Safe to run in parallel (independent file writes)

### Always Sequential

3. **Implementation**: Default sequential (may touch same files)
4. **Quality Gates**: Single run after all changes

### Experimental Parallel

- Implementation with `--parallel` flag
- Risk: Git conflicts if issues touch same files
- Benefit: Faster completion for independent issues

---

## Task Delegation Pattern

**CRITICAL RULE:** This command NEVER executes /plan or /implement commands directly.

Instead, it:
1. Launches Task() subagents for each operation
2. Sends multiple Task calls in SINGLE message for parallel execution
3. Waits for subagent completion
4. Aggregates results

**Example parallel delegation:**

```markdown
# CORRECT: Single message with 3 Task calls (parallel)
Send one message with three Task tool uses:
  1. Task: Generate strategy for DTL-002
  2. Task: Generate strategy for DTL-003
  3. Task: Generate strategy for DTL-004

# WRONG: Multiple messages (sequential, slow)
Send message with Task for DTL-002, wait for response
Send message with Task for DTL-003, wait for response
Send message with Task for DTL-004, wait for response
```

---

## Error Handling

### Strategy/Spec Generation Failures

- Log error for specific issue
- Continue with other issues
- Report failed issues in final summary

### Implementation Failures

- Stop at failed issue (sequential mode)
- Report error details
- Allow user to fix and retry
- Or skip failed issue and continue

### Quality Gate Failures

- Display all errors
- In auto mode: Exit with error report
- In interactive mode: Offer retry after manual fixes

### Git Conflicts (Parallel Implementation)

- Detect conflicts
- Report conflicted files
- Abort parallel execution
- Suggest sequential retry

---

## Examples

### Example 1: Execute Epic with All Children

```bash
/workflow:execute DTL-001 --auto
```

**Output:**
```
📦 Detected epic: DTL-001
📋 Found 5 child issues:
  - DTL-002: Add LookML set support
  - DTL-003: Generate dimension-only field sets
  - DTL-004: Update join generation
  - DTL-005: Update unit tests
  - DTL-006: Update integration tests

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

Phase 3: Implementing (sequential)...
  ✅ DTL-002 implemented
  ✅ DTL-003 implemented
  ✅ DTL-004 implemented
  ✅ DTL-005 implemented
  ✅ DTL-006 implemented

Phase 4: Quality gates...
  ✅ All gates passed

Phase 5: Creating PR...
  ✅ PR #42 created

✅ WORKFLOW COMPLETE
```

---

### Example 2: Execute Multiple Unrelated Issues

```bash
/workflow:execute DTL-007 DTL-009 DTL-012 --interactive
```

**Prompts:**
- "Generate strategies for 3 issues?" → Yes
- "Review strategies and generate specs?" → Let me review first
  - (Shows strategy file paths)
  - (Waits for user to review)
- "Continue with spec generation?" → Yes
- "Implement all 3 issues?" → Implement one by one
  - "Implement DTL-007?" → Yes (proceeds)
  - "Implement DTL-009?" → Yes (proceeds)
  - "Implement DTL-012?" → Yes (proceeds)

---

### Example 3: Plan Only (Batch Planning)

```bash
/workflow:execute DTL-010 DTL-011 DTL-012 DTL-013 --plan-only --auto
```

**Generates:**
- Strategies for all 4 issues (parallel)
- Specs for all 4 issues (parallel)
- Stops (no implementation)

**Use case:** Friday afternoon batch planning for Monday implementation

---

## Related Commands

- `/plan:strategy` - Generate single strategy (this delegates to it)
- `/implement:spec` - Generate single spec (this delegates to it)
- `/implement` - Implement single issue (this delegates to it)
- `/workflow:batch-plan` - Plan-only wrapper (calls this with --plan-only)

---

## Benefits

1. **Automation**: Full end-to-end execution with one command
2. **Parallelization**: Strategies and specs run concurrently
3. **Flexibility**: Auto or interactive modes
4. **Safety**: Sequential implementation by default
5. **Visibility**: TodoWrite tracks all steps
6. **Efficiency**: Batch process multiple issues
7. **Epic Support**: Automatically handles epic children

---

## Notes

- **Subagent Delegation**: All operations via Task() subagents (required)
- **Parallel by Default**: Strategies and specs always parallel
- **Sequential Implementation**: Safe default, use --parallel experimentally
- **Interactive Default**: Safe mode with checkpoints
- **Git Safety**: Creates single PR for all changes
- **Quality Gates**: Run once after all implementation
