# Brief: gates-model

> Derived brief — not authoritative. Composed on demand from `project:brief`; edit records, not this file.

## Work Item

### gates-model
**title**: Wire landing merge, last_record_at, and quiet into the model; **phase**: human-gates; **kind**: deliver; **effort**: dashboard; state: in_progress

## Description

Wire gate vocabulary and landing into the snapshot model: phase bodies, last-record timestamps, Merge branch Needs you items, and quiet status/wave glyphs.

## Approach

1. Keep `PhaseRow.body` on each phase from the phase record so landing needs no extra query.
2. Set `TaskRow.last_record_at` to the latest of assignment, amendment, execution-report, and check-run `recorded_at` where `running_since` is set today.
3. Add a pure `merge_landing_needs(view, landing)` (in `gates.py` or beside it) that appends a `merge-branch` Needs you item for each done phase whose landing exists and is not merged, ordered after integration in `NEEDS_ORDER` (R6). Keep `load_snapshot` git-free.
4. Update `tasks.status_label` / row styling so a quiet running task shows `running <time> · quiet` in the warning colour, and `selection.wave_strip` uses the warning colour for quiet glyphs (R7). Quiet adds no Needs you item.
5. Cover with `-k gates` model tests for merge-branch items and quiet labels. Do not edit `app.py` or status scripts.

## Acceptance Criteria

### gates-model
**criterion**: A done phase with Landing whose branch exists and is not merged into main yields a Merge branch Needs you item after integration items; Enter detail carries branch and ahead count; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py tests/test_dashboard_gates.py -q -k "gates and (merge or landing_item)"; state: active

### gates-model-quiet
**criterion**: A quiet running task shows running <time> · quiet in warning colour and its wave strip glyph uses warning colour; quiet tasks add no Needs you item; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py tests/test_dashboard_tasks.py -q -k "gates and quiet"; state: active

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
