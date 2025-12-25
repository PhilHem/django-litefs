# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  1. PROVISION        2. EXECUTE           3. LAND              │
│  ─────────────       ─────────────        ─────────────        │
│  /provision          /rg-beads            bd sync              │
│  (plan mode →        (TDD on ready        git push             │
│   explore →           tasks)                                   │
│   create issues)                                               │
└─────────────────────────────────────────────────────────────────┘
```

### 1. Provision Work (`/provision`)

```
/provision "Add --dry-run flag to fetch command"
```

**Staged pipeline with gates:**

| Stage | Goal | Gate |
|-------|------|------|
| 0. Deduplication | Check existing beads | No duplicates |
| 1. Decomposition | Break into tasks | Single-responsibility, 1-3h |
| 2. Architecture | Validate against rules | P0 issues have fix tasks |
| 3. Contract | Define testing reqs | TRA, tier, verification |
| 4. Dependencies | Set task order | No cycles, epic→tasks |
| 5. Review | User approval | All gates passed |
| 6. Create | Build beads issues | Validated structure |

### 2. Execute Work (`/rg-beads`)

TDD pipeline on ready issues:
- Select up to 3 related ready tasks (`bd ready`)
- Batched RED → GREEN → REFACTOR phases
- Updates issue status on completion
- Checks if parent tasks/epics can be closed

### 3. Land the Plane (Session End)

**MANDATORY before saying "done":**

```bash
git status                    # Check changes
git add <files>               # Stage code
bd sync                       # Sync beads
git commit -m "..."           # Commit
git push                      # Push to remote
git status                    # MUST show "up to date"
```

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Dependency Rules

`bd dep add <issue> <depends-on>` means "issue is blocked by depends-on".

**Direction**: Parents depend on children. Children are ready first, parents close last.

| Relationship | Command | Result |
|-------------|---------|--------|
| Epic → Tasks | `bd dep add epic-123 task-a` | Task ready, epic blocked |
| Task → Subtasks | `bd dep add task-456 subtask-x` | Subtask ready, task blocked |

**Epic pattern**:
```bash
bd dep add epic-123 task-a    # Epic depends on task-a
bd dep add epic-123 task-b    # Epic depends on task-b
```
Result: `task-a` and `task-b` are ready to work, `epic-123` closes when both done.

**Common mistake**: `bd dep add task epic` blocks the task until epic is done (backwards!)

## Critical Rules

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
