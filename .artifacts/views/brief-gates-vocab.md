# Brief: gates-vocab

> Derived brief — not authoritative. Composed on demand from `project:brief`; edit records, not this file.

## Work Item

### gates-vocab
**title**: Gate vocabulary: labels, prompts, next step, quiet; **phase**: human-gates; **kind**: deliver; **effort**: dashboard; state: in_progress

## Description

Add `dashboard/gates.py` with the pure gate vocabulary used by Needs you, the next-step line, and quiet detection.

## Approach

1. Create `dashboard/gates.py` with `action_label(item, view)`, `prompt(item, view)`, `next_step(view, landing)`, and `is_quiet(task, now)` per the design Interfaces section.
2. `action_label` maps each Needs you kind to its verb (R1) and recognizes `plan-review:` scopes, looking the slug up in `view.phases` for the phase title (R2).
3. `prompt` builds the ready agent string for each kind (R3).
4. `next_step` applies the fixed priority rule list from R4 and returns the skill-named line only (position text is appended by the UI).
5. `is_quiet` compares `now - task.last_record_at` to `2 * estimate_minutes` or 60 minutes (R7); return False when not running or when `last_record_at` is None.
6. Cover with TDD in `tests/test_dashboard_model.py` selected by `-k gates` (or a new gates-named module imported from there). Do not edit `app.py`, `model.py` loaders, or git helpers.

## Acceptance Criteria

### gates-vocab
**criterion**: action_label returns the R1 verbs for each Needs you kind, and a plan-review scope shows Review plan plus the phase title not the raw scope; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py -q -k 'gates and (label or plan_review or action)'; state: active

### gates-vocab-next
**criterion**: next_step returns the first matching R4 rule string for seeded effort states including plan-review, merge, unsigned, running, ready, and discuss/plan next phase; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py -q -k 'gates and next_step'; state: active

### gates-vocab-prompt
**criterion**: prompt(item, view) returns a ready agent string naming the effort, subject or phase, and action for each Needs you kind; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py -q -k 'gates and prompt'; state: active

### gates-vocab-quiet
**criterion**: is_quiet is true when a running task's last_record_at is older than twice estimate_minutes, or 60 minutes with no estimate, and false otherwise; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py -q -k 'gates and quiet'; state: active

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
