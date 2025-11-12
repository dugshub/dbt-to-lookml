---
description: Decompose requirements into YAML issue plan
argument-hint: <task-description> [--auto-accept]
allowed-tools:
  - AskUserQuestion
  - Read
  - Write
  - TodoWrite
---

# Plan - Requirements Decomposition

Transform user requirements into structured YAML definition for local markdown issues.

## Purpose

Interactive planning that generates structured YAML for local issue creation. Deep analysis → thoughtful decomposition → structured YAML. **YAML only** - no issues created yet.

## Variables

- `$1`: Task description (required)
- `--auto-accept`: Skip approval, generate YAML immediately

## Instructions

### Phase 1: Load Configuration

**Step 1: Read Task Config** - Read `.tasks/config.yaml` for available labels (stack, type, layer, priority, state).

**Step 2: Read Project Config** - Read `CLAUDE.md` for layer rules, patterns, domain model.

---

### Phase 2: Deep Analysis

**Step 3: Understand Requirement** - Parse `$1`: what's requested, detail level, domain, constraints

**Step 4: Ultrathink** - Use reasoning for: problem, stakeholders, criteria, constraints, layers, dependencies, risks

**Step 5: Ask Questions** - Until crystal clear: scope, architecture layer, stack, approach, constraints, dependencies, testing

---

### Phase 3: Label Discovery

**Step 6: Discover Labels** - Read `.tasks/config.yaml` to see available labels. Identify: Stack (REQUIRED), Type, Layer, Priority.

Available labels from config:
- **stack**: backend, frontend, fullstack
- **type**: epic, feature, bug, chore, patch
- **layer**: atoms, features, molecules, organisms (backend only)
- **priority**: low, medium, high
- **state**: awaiting-strategy-review, strategy-approved, spec-ready

**Step 7: Determine Stack** - Backend (APIs/services/DB), Frontend (UI/components), Fullstack (end-to-end, decompose to backend+frontend subs). Rule: User touches → frontend, Data persists → backend, Both → fullstack.

---

### Phase 4: Decomposition

**Step 8: Break Down (use `<ultrathink>`)**

Epic: High-level feature, full description (problem/approach/criteria/subs), labels (`type:epic`, stack, layer, domain, priority), status `Refinement`.

Sub-Issues: ATOMIC units, ONE deliverable each, sequence (foundation → implementation → integration → testing), fullstack = backend subs first.

**Step 9: Assign Labels** - Stack (REQUIRED), Type, Layer, Domain, TDD, Priority. Rules: Epic with mixed subs = `stack:fullstack`, backend work = `stack:backend`, frontend = `stack:frontend`. ONE stack label per issue.

---

### Phase 5: Proposal & Approval

**Step 10: Present** - Show epic, sub-issues, labels, branch name, spec locations

**Step 11: Approve** - Unless `--auto-accept`, ask "Does this decomposition look correct?" and iterate

---

### Phase 6: Generate YAML

**Step 12: Create YAML** - Generate `issue-plan-{kebab-case}.yaml`:

```yaml
epic:
  title: "Epic: {title}"
  description: |
    {Problem statement}
    {Solution approach}
    {Success criteria}
    {Sub-issues list}
  labels: [{actual labels from discovery}]
  status: Refinement
  children:
    - title: "{sub-issue title}"
      description: |
        {Details}
        Parent: {Auto-set}
      labels: [{sub labels}]
      status: Refinement
```

Use actual labels, full descriptions, status `Refinement`.

**Step 13: Validate Generated YAML**

Before saving, validate YAML structure and content:

```markdown
Validate YAML has:
✅ Epic with non-empty description (min 50 chars)
✅ Each child with non-empty description (min 30 chars)
✅ All issues have stack label specified (stack:backend, stack:frontend, or stack:fullstack)
✅ All issues have type label (type:epic, type:feature, type:bug, type:chore)
✅ Epic has at least one child
✅ Each child has title different from epic title

If validation fails, auto-fix:

1. **Epic description too short or missing?**
   ⚠️  Epic description insufficient - expanding...
   Generate comprehensive description with:
   - Problem statement (2-3 sentences)
   - Solution approach (2-3 sentences)
   - Success criteria (bulleted list)
   - List of sub-issues
   ✅ Enhanced epic description

2. **Child description too short or missing?**
   ⚠️  Child "{title}" has insufficient description - expanding...
   Generate detailed description with:
   - What needs to be built
   - Why it's needed (connection to epic)
   - Technical scope from labels
   - Testing requirements
   ✅ Enhanced child description

3. **Missing stack label?**
   ⚠️  Issue "{title}" missing stack label...
   Infer from title and description:
   - API/service/DB keywords → stack:backend
   - UI/component/page keywords → stack:frontend
   - End-to-end/both → stack:fullstack
   Ask user to confirm: "Inferred stack:{stack} for '{title}'. Confirm? [Y/n]"
   If confirmed, add to YAML
   ✅ Added stack label

4. **Missing type label?**
   ⚠️  Issue "{title}" missing type label...
   Infer from title and structure:
   - Epic → type:epic
   - Child issues → type:feature (default)
   - Contains "fix"/"bug" → type:bug
   Add to YAML
   ✅ Added type label

After all fixes:
✅ YAML validation complete - ready to save
```

**Step 14: Save** - Write to project root: `issue-plan-{kebab-case}.yaml`

**Step 15: Confirm Idempotent Nature**

Display to user:
```
✅ YAML plan saved: issue-plan-{kebab-case}.yaml

This plan is idempotent:
- Run /plan:create multiple times safely
- YAML → Linear sync (creates missing, updates changed, skips synced)
- Edit YAML and re-run to update Linear issues

Next: /plan:create issue-plan-{kebab-case}.yaml [--dry-run]
```

---

### Phase 7: Commit (Optional)

**Step 16: Commit** - Optionally commit the YAML plan to git:

```bash
git add issue-plan-{name}.yaml
git commit -m "docs(planning): add issue decomposition plan for {feature}"
```

---

## Final Report

Display:
- Plan file location
- Epic structure tree
- Next steps: (1) `/plan:create {yaml}` to create markdown issues, (2) `/plan:strategy {ISSUE-ID}` for each issue, (3) `/implement {ISSUE-ID}`

## Notes

- **Modular**: YAML generation only (no API calls, no file creation)
- **Local-First**: All configuration from `.tasks/config.yaml`
- **Interactive**: Deep analysis + clarifying questions
- **Self-Validating**: Auto-validates descriptions and labels before saving
- **Auto-Fix**: Generates missing descriptions, infers missing labels
- **Idempotent-Ready**: Creates YAML that works with idempotent /plan:create command

## Validation and Self-Healing

Before saving YAML, this command:
1. **Validates structure** - Epic + children with all required fields
2. **Checks descriptions** - Min length requirements (epic: 50 chars, children: 30 chars)
3. **Verifies labels** - Stack and type labels on all issues
4. **Auto-fixes gaps** - Generates descriptions, infers labels (with confirmation)
5. **Confirms quality** - Only saves when validation passes

Result: High-quality YAML ready for /plan:create without manual editing
