# Brief: gates-status

> Derived brief — not authoritative. Composed on demand from `project:brief`; edit records, not this file.

## Work Item

### gates-status
**title**: tmux status-right needs-you count segment; **phase**: human-gates; **kind**: deliver; **effort**: dashboard; state: in_progress

## Description

Expose the needs-you count on tmux status-right via `dashboard-status --tmux`, matching the dashboard's merged Needs you count including Merge branch items.

## Approach

1. Add `dashboard/bin/dashboard-status --tmux DIR` that prints `⚑ <n>` or nothing when the count is zero or there is no store.
2. Reuse the same landing-merge path the app uses so the segment count matches the live Needs you list.
3. Update `se-workflow.tmux` to read `@dashboard-status-right` (default `on`) and append `#(cd '#{pane_current_path}' && <launcher>/dashboard-status --tmux .)` to `status-right` once, guarding against duplicates on reload.
4. Cover with a `-m tmux` test that asserts the segment appears when on and is absent when `@dashboard-status-right off`. Do not edit `app.py` beyond what status helpers already share.

## Acceptance Criteria

### gates-status
**criterion**: In a real tmux server, status-right shows the needs-you count for the pane repo when @dashboard-status-right is on, and shows nothing when off or the count is zero; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests -q -m tmux -k "status and (gates or needs or segment)"; state: active

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
