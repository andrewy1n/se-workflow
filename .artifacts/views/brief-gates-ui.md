# Brief: gates-ui

> Derived brief — not authoritative. Composed on demand from `project:brief`; edit records, not this file.

## Work Item

### gates-ui
**title**: Next-step line, copy prompt, and new-item alerts; **phase**: human-gates; **kind**: deliver; **effort**: dashboard; state: in_progress

## Description

Surface gate vocabulary in the Textual app: action labels everywhere Needs you renders, next-step under the goal, c copies a prompt, and new items ring the bell with a tmux message.

## Approach

1. Replace `NEEDS_LABEL` usage with `gates.action_label` in the Needs you list, detail chips, and footer so they agree (R1/R2 already covered by vocab; wire here).
2. Add `#next-step` Static under `#goal` filled from `next_step(view, landing)` plus muted position text (R4).
3. Dispatch `c` by focus: Needs you copies `prompt(item, view)`; task table still copies the slug. Footer and key help say `copy prompt` when Needs you has focus (R3).
4. After each snapshot load, compute landing in a worker, cache by `git rev-parse main <branches>`, merge landing Needs you into `view.needs_you`, and refresh the UI.
5. Keep `seen_needs: set[str]` of item ids; after the first load, new ids call `self.bell()` and, when `$TMUX` is set, `tmux display-message -d 4000 "<effort>: <label> <subject>"` (R9). Use record ids, or `merge:<phase>` for branch items.
6. Cover with Textual pilots in `tests/test_dashboard_app.py` with clipboard and tmux stubbed. Do not edit status scripts or `se-workflow.tmux`.

## Acceptance Criteria

### gates-ui
**criterion**: c on a Needs you item copies the ready agent prompt; c on a task row still copies the slug; footer and key help say copy prompt when Needs you has focus; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k "gates and (copy or prompt)"; state: active

### gates-ui-alert
**criterion**: A Needs you item absent from the previous snapshot rings the bell and shows a stubbed tmux message naming effort, action, and subject; items present at startup do not alert; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k "gates and (alert or bell or message)"; state: active

### gates-ui-next
**criterion**: Under the goal, a next-step line shows next: plus the first matching R4 rule, then the position text in muted colour; **method**: tdd; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k "gates and next"; state: active

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
