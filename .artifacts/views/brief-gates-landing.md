# Brief: gates-landing

> Derived brief — not authoritative. Composed on demand from `project:brief`; edit records, not this file.

## Work Item

### gates-landing
**title**: Read-only phase Landing git state; **phase**: human-gates; **kind**: deliver; **effort**: dashboard; state: in_progress

## Description

Add `dashboard/landing.py` that reads a phase body's Landing section and reports branch existence, ahead count, and merged state with read-only git only.

## Approach

1. Create `dashboard/landing.py` with `Landing(branch, exists, ahead, merged)` and `phase_landing(root, body, subject) -> Landing | None`.
2. Return None when the body has no `## Landing` heading.
3. Prefer a backtick branch name after `branch` in the Landing text; else default to `phase/<subject>`.
4. Run `git rev-parse --verify --quiet refs/heads/<branch>`, `git rev-list --count main..<branch>`, and `git merge-base --is-ancestor <branch> main`, each with a 2s timeout; any failure returns None (R5, R10).
5. Use only read-only git; never write the store or mutate the repo (R11).
6. Cover in `tests/test_dashboard_gates.py` against a scratch git repo including no-repo and missing-git cases. Do not edit `app.py` or the snapshot loader.

## Acceptance Criteria

### gates-landing
**criterion**: phase_landing reports branch, exists, ahead, and merged or not merged for a scratch repo with a Landing section; no Landing heading returns None; missing branch shows exists false; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_gates.py -q -k 'landing and not (nogr or readonly)'; state: active

### gates-landing-failsoft
**criterion**: With no git repository, no git binary, or a failing git command, phase_landing returns None and raises nothing; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_gates.py -q -k 'nogr or no_git or fail'; state: active

### gates-landing-readonly
**criterion**: After phase_landing runs, git status and the store directory are unchanged; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_gates.py -q -k readonly; state: active

## Findings

_None._

## Constraints

### adaptive-artifacts-change-gate
**statement**: Runtime changes in the adaptive-artifacts repo follow its AGENTS.md gate: capture them in that repo's store and apply only with human approval; **applies_to**: work-items that edit ~/adaptive-artifacts; **effort**: dashboard; state: active

## Basis

~/adaptive-artifacts/AGENTS.md, section Changing the extension.

### dashboard-autonomy-dashboard-bugfix
**statement**: Plan and promote each next phase without asking once the current one closes; stop only for failures, needs-human findings, or a push or merge; **applies_to**: dashboard-bugfix; **effort**: dashboard; state: active

## Basis

User instruction before execution.

### dashboard-autonomy-dashboard-features
**statement**: Plan and promote each next phase without asking once the current one closes; stop only for failures, needs-human findings, or a push or merge; **applies_to**: dashboard-features; **effort**: dashboard; state: active

## Basis

User instruction before execution.

### dashboard-branches-dashboard-bugfix
**statement**: Work on stacked branches: fix/dashboard-bugfix from main, feat/dashboard-features from it; one commit per task; commit at each effort end; no merge to main until both efforts are done and the user says so; **applies_to**: dashboard-bugfix; **effort**: dashboard; state: active

## Basis

User instruction when adopting both efforts.

### dashboard-branches-dashboard-features
**statement**: Work on stacked branches: fix/dashboard-bugfix from main, feat/dashboard-features from it; one commit per task; commit at each effort end; no merge to main until both efforts are done and the user says so; **applies_to**: dashboard-features; **effort**: dashboard; state: active

## Basis

User instruction when adopting both efforts.

### dashboard-read-only
**statement**: The dashboard never writes to the artifact store; actions that change records go through the parent Claude session; **applies_to**: scripts/dashboard_app.py and scripts/dashboard_model.py; **effort**: dashboard; state: active

## Basis

The store is single-writer: only the parent session calls adaptive-artifacts in a form that writes (skills/kinds-and-focus.md, Writer). A dashboard write would race that session's --expected-revision.

### dashboard-read-only-dashboard-bugfix
**statement**: The dashboard never writes to the store; copy actions hand work to the agent; **applies_to**: dashboard-bugfix; **effort**: dashboard; state: active

## Basis

The skills assume a single-writer store owned by the parent agent session; the user confirmed this when adopting the effort.

### dashboard-read-only-dashboard-features
**statement**: The dashboard never writes to the store; copy actions hand work to the agent; **applies_to**: dashboard-features; **effort**: dashboard; state: active

## Basis

The skills assume a single-writer store owned by the parent agent session; the user confirmed this when adopting the effort.

### dashboard-ux-plan-before-execute
**statement**: Do not execute any of the five dashboard UX phases until all five have been discussed and planned; **applies_to**: phase-selector,human-gates,spec-view,evidence-matrix,journal-view; **effort**: dashboard; state: active

## Basis

User instruction during the dashboard UX discussion: plan the phases, no executions yet.

## Position

### dashboard
**position**: phase-selector done; next up: human-gates; **scope**: effort; state: active

### evidence-matrix
**position**: evidence-matrix plan approved; ready for execute after prior UX deps; **scope**: phase; state: active

### human-gates
**position**: human-gates plan approved; UX plan-before-execute cleared; ready for execute-phase; **scope**: phase; state: active

### journal-view
**position**: journal-view plan approved; ready for execute after prior UX deps; **scope**: phase; state: active

### spec-view
**position**: spec-view plan approved; ready for execute after prior UX deps; **scope**: phase; state: active

## Unapplied Amendments

_None._
