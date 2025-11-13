# Migration from Linear to Local Markdown

This document summarizes the conversion from Linear-based task management to local markdown-based system.

## What Changed

### Before (Linear-Based)

**Workflow:**
1. `/plan:decompose` → YAML plan
2. `/plan:create` → **Creates Linear issues via API** 📡
3. `/plan:strategy` → **Posts to Linear comment** 📡
4. User approves → **Adds Linear label** 📡
5. `/implement:spec` → **Fetches from Linear, posts result** 📡
6. `/implement` → **Updates Linear status** 📡

**Dependencies:**
- Linear API key required
- `.env` with `LINEAR_API_KEY`, `PROJECT_TEAM_KEY`
- `task-patterns` skill for ALL Linear operations
- Internet connection required
- Rate limits on API calls

**Data Storage:**
- Linear cloud (external service)
- Not in git, not versioned
- Requires login to view
- Can't work offline

---

### After (Local Markdown)

**Workflow:**
1. `/plan:decompose` → YAML plan
2. `/plan:create` → **Creates `.tasks/issues/*.md` files** 📄
3. `/plan:strategy` → **Writes to `.tasks/strategies/*.md`** 📄
4. User approves → **Edits issue file, changes `status` field** ✏️
5. `/implement:spec` → **Reads issue file, writes to `.tasks/specs/*.md`** 📄
6. `/implement` → **Updates issue file** 📄

**Dependencies:**
- Python + YAML library (already installed)
- `dtl_tasks.py` CLI (local script)
- No external services
- Works offline

**Data Storage:**
- Local `.tasks/` directory
- Tracked in git, full history
- Human-readable markdown
- Searchable with grep/code editor
- Portable (copy to any project)

---

## File Mapping

| Linear Concept | Local Equivalent | Location |
|----------------|------------------|----------|
| Issue | Markdown file | `.tasks/issues/DTL-001.md` |
| Epic | Markdown file | `.tasks/epics/DTL-001.md` |
| Labels | Frontmatter array | `labels: [stack:backend]` |
| Status | Frontmatter field | `status: ready` |
| Comments | History section | `## History` in issue file |
| Strategy comment | Strategy file | `.tasks/strategies/DTL-001-strategy.md` |
| Spec attachment | Spec file | `.tasks/specs/DTL-001-spec.md` |
| Issue list | Index file | `.tasks/index.md` |
| Configuration | Config file | `.tasks/config.yaml` |

---

## Command Changes

### `/plan:decompose`

**Before:**
- Read `.env` for `PROJECT_TEAM_KEY`
- Use `task-patterns` skill to discover Linear labels
- Reference Linear conventions

**After:**
- Read `.tasks/config.yaml` for available labels
- Read `CLAUDE.md` for project patterns
- No external API calls

**Impact:** Minimal changes, just configuration source

---

### `/plan:create`

**Before:**
- Parse YAML
- Call `task-patterns skill` → Linear API to create issues
- Call `task-patterns skill` → Linear API to add labels
- Call `task-patterns skill` → Linear API to set status
- Call `task-patterns skill` → Linear API to link parent/children
- Output: Linear issue IDs (e.g., `TEMPO-123`)

**After:**
- Parse YAML
- Generate issue IDs locally (`DTL-001`, `DTL-002`, etc.)
- Create markdown files in `.tasks/issues/` and `.tasks/epics/`
- Write frontmatter with metadata
- Update `.tasks/index.md`
- Output: Local file paths

**Impact:** Complete rewrite, no Linear API calls

---

### `/plan:strategy`

**Before:**
- `task-patterns skill` → Fetch issue from Linear
- Validate Linear labels
- Analyze codebase
- Generate strategy
- `task-patterns skill` → Post strategy as Linear comment
- `task-patterns skill` → Update Linear issue status
- `task-patterns skill` → Add Linear label `awaiting-strategy-review`

**After:**
- Read issue from `.tasks/issues/{ID}.md`
- Validate frontmatter labels
- Analyze codebase (same)
- Generate strategy
- Write to `.tasks/strategies/{ID}-strategy.md`
- Update issue status in frontmatter: `awaiting-strategy-review`
- Add history entry to issue file
- Run `reindex` to update index

**Impact:** Complete rewrite, file-based instead of API-based

**Approval Changed:**
- Before: Human adds `state:strategy-approved` label in Linear UI
- After: Human edits `.tasks/issues/{ID}.md` and changes `status: strategy-approved`

---

### `/implement:spec`

**Before:**
- `task-patterns skill` → Fetch issue from Linear
- Validate `state:strategy-approved` label
- `task-patterns skill` → Fetch strategy from Linear comments
- Analyze codebase
- Generate spec
- Save spec to stack-specific location
- `task-patterns skill` → Post comment to Linear with spec link
- `task-patterns skill` → Update Linear status to "Ready"
- `task-patterns skill` → Remove label, add label

**After:**
- Read issue from `.tasks/issues/{ID}.md`
- Validate `status: strategy-approved` in frontmatter
- Read strategy from `.tasks/strategies/{ID}-strategy.md`
- Analyze codebase (same)
- Generate spec
- Write to `.tasks/specs/{ID}-spec.md`
- Update issue status: `ready`
- Add history entry
- Run `reindex`

**Impact:** Complete rewrite, file-based

---

### `/implement`

**Before:**
- `task-patterns skill` → Fetch issues from Linear
- Validate prerequisites via Linear API
- `task-patterns skill` → Update Linear status to "In Progress"
- Implement code
- Create PR
- `task-patterns skill` → Post comment to Linear
- `task-patterns skill` → Update Linear status to "In Review"

**After:**
- Read issues from `.tasks/issues/{ID}.md`
- Validate prerequisites from frontmatter
- Update issue status: `in-progress`
- Implement code (same)
- Create PR (same)
- Add history entry with PR link
- Update issue status: `in-review`
- Run `reindex`

**Impact:** Complete rewrite, file-based

---

### `/test`

**Before:**
- Run quality gates (same)
- Optionally post results to Linear

**After:**
- Run quality gates (same)
- Optionally add history entry to issue

**Impact:** Minimal, optional Linear integration removed

---

## Skills Removed

These skills are no longer needed:

1. **`task-patterns` skill** - All Linear API operations
   - Replaced with: `dtl_tasks.py` CLI + file operations

2. **`validate-env.sh` script** - Linear environment validation
   - Replaced with: Reading `.tasks/config.yaml`

3. **`session-logging.md`** - Complex session tracking
   - Simplified to: Basic history entries in issue files

---

## New Components

### 1. `dtl_tasks.py` CLI

**Location:** `scripts/dtl_tasks.py`

**Purpose:** Python CLI for managing local markdown tasks

**Commands:**
- `list` - List all issues (with filtering)
- `show <id>` - Show issue details
- `update <id>` - Update issue (status, labels, history)
- `reindex` - Regenerate index.md
- `next-id` - Get next available issue ID

**Why:** Provides structured operations on markdown files with frontmatter

---

### 2. `.tasks/` Directory

**Structure:**
```
.tasks/
├── config.yaml          # Project configuration
├── index.md             # Auto-generated index
├── issues/              # Individual issues
├── epics/               # Epic issues
├── strategies/          # Strategy documents
└── specs/               # Implementation specs
```

**Why:** Centralized location for all task data, git-trackable

---

### 3. Task Helper Library

**Location:** `.claude/commands/lib/task-helpers.md`

**Purpose:** Shared utilities for task operations

**Provides:**
- Common patterns for reading/writing issues
- YAML frontmatter parsing
- Status validation helpers
- Git integration helpers

**Why:** Reusable code across all commands

---

### 4. Makefile Targets

**Location:** `Makefile`

**New targets:**
- `make tasks-list` - List issues
- `make tasks-show ID=...` - Show issue
- `make tasks-update ID=... STATUS=...` - Update issue
- `make tasks-reindex` - Regenerate index
- `make tasks-next-id` - Next ID

**Why:** Convenient shortcuts for common operations

---

## Configuration Changes

### Removed from `.env`

```bash
# No longer needed:
LINEAR_API_KEY=...
PROJECT_TEAM_KEY=...
LINEAR_WORKSPACE=...
```

### Added: `.tasks/config.yaml`

```yaml
project:
  name: dbt-to-lookml
  prefix: DTL
  next_id: 1
  repository: dugshub/dbt-to-lookml

labels:
  stack: [backend, frontend, fullstack]
  type: [epic, feature, bug, chore, patch]
  layer: [atoms, features, molecules, organisms]
  priority: [low, medium, high]
  state: [awaiting-strategy-review, strategy-approved, spec-ready]

statuses:
  - todo
  - refinement
  - awaiting-strategy-review
  - strategy-approved
  - ready
  - in-progress
  - in-review
  - done
  - blocked
  - cancelled
```

---

## Benefits of Migration

### 1. No External Dependencies
- ✅ Works offline
- ✅ No API keys required
- ✅ No rate limits
- ✅ No subscription costs
- ✅ No service outages

### 2. Git-Native
- ✅ Full history in git
- ✅ Branching/merging of tasks
- ✅ Diff-able changes
- ✅ Code review of task changes
- ✅ Blame shows who changed what

### 3. Human-Readable
- ✅ Markdown files
- ✅ Searchable with grep
- ✅ Editable in any text editor
- ✅ Preview in GitHub/VS Code
- ✅ No special tools needed

### 4. Fast
- ✅ No network latency
- ✅ Instant searches
- ✅ Local file operations
- ✅ Faster than API calls

### 5. Flexible
- ✅ Custom frontmatter fields
- ✅ Any label structure
- ✅ Rich markdown content
- ✅ Embedded code/diagrams
- ✅ No platform constraints

### 6. Portable
- ✅ Copy `.tasks/` to any project
- ✅ No vendor lock-in
- ✅ Data is yours forever
- ✅ Can migrate to any system

### 7. Privacy
- ✅ No cloud storage
- ✅ No data sharing
- ✅ Full control
- ✅ No telemetry

---

## Trade-offs

### What We Lost

❌ **Web UI**: No browser-based interface
- Mitigation: Use VS Code, GitHub web interface, or any markdown viewer

❌ **Real-time Collaboration**: No live updates
- Mitigation: Use git for collaboration (pull, push, merge)

❌ **Notifications**: No email/Slack alerts
- Mitigation: Watch git commits, use GitHub notifications

❌ **Integrations**: No Slack/Zapier/etc. integrations
- Mitigation: Build custom scripts if needed (all data is local and accessible)

❌ **Advanced Filtering**: No complex queries
- Mitigation: Use grep, jq, or build custom scripts

❌ **Issue Numbers**: No global issue counter across projects
- Mitigation: Use project-specific prefixes (DTL-, PROJ-, etc.)

### What We Gained

✅ **Simplicity**: Just markdown files
✅ **Speed**: No network calls
✅ **Ownership**: Your data, your control
✅ **Flexibility**: Extend however you want
✅ **Cost**: Free forever
✅ **Reliability**: No service dependencies

---

## Migration Checklist

If you were using Linear and want to migrate:

- [ ] Export Linear issues to JSON/CSV
- [ ] Create `.tasks/` directory structure
- [ ] Set up `.tasks/config.yaml` with project details
- [ ] Convert Linear issues to markdown format
- [ ] Create strategy files for issues with strategies
- [ ] Create spec files for issues with specs
- [ ] Update issue statuses to match local statuses
- [ ] Run `make tasks-reindex` to generate index
- [ ] Commit to git
- [ ] Test commands with sample issue
- [ ] Train team on new workflow
- [ ] Archive or delete Linear workspace

---

## Rollback Plan

If you need to go back to Linear:

1. Keep Linear workspace active during transition
2. Maintain `.claude/commands/*.backup` files
3. Can recreate Linear issues from markdown:
   ```python
   # Read all .tasks/issues/*.md
   # Parse frontmatter
   # Call Linear API to create issues
   # Map local IDs to Linear IDs
   ```

---

## Future Enhancements

Possible additions to local system:

1. **Web UI**: Build a simple web viewer for `.tasks/`
2. **GitHub Integration**: Sync with GitHub Issues
3. **Search Tool**: Build indexed search
4. **Dashboard**: Generate HTML dashboard
5. **Mobile App**: Mobile-friendly viewer
6. **Export/Import**: JSON/CSV export/import
7. **Time Tracking**: Add time tracking to issues
8. **Dependencies**: Visualize issue dependencies
9. **Burndown Charts**: Generate progress charts
10. **Custom Scripts**: Add project-specific automation

All of these can be built on top of the markdown foundation without external dependencies.

---

## Summary

**From:** Cloud-based, API-dependent, requires internet, vendor lock-in
**To:** Local-first, git-native, offline-capable, portable, yours forever

The migration removes external dependencies while maintaining the same workflow and adding new flexibility. All data is local, version-controlled, and human-readable.
