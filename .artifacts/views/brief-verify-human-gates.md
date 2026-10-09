# Brief: verify-human-gates

> Derived brief — not authoritative. Composed on demand from `project:brief`; edit records, not this file.

## Work Item

### verify-human-gates
**title**: Verify human-gates phase; **phase**: human-gates; **kind**: deliver; **effort**: dashboard; state: in_progress

## Description

Prove the phase exit criteria hold together: run the integration check through `dashboard/bin/dashboard --once`, then the gated model/app/tmux suites and the full suite.

## Approach

1. Run `dashboard/bin/dashboard --once` against a seeded store that includes a plan-review item, a Landing phase, and a quiet running task; assert the frame shows action verbs, next-step, and landing on the selector line.
2. Run `tests/test_dashboard_model.py` and `tests/test_dashboard_gates.py` for labels, prompts, next-step, landing, merge-branch, and quiet.
3. Run `tests/test_dashboard_app.py -k gates` for copy-prompt and alerts.
4. Run the `-m tmux` status segment test.
5. Run the full non-tmux then tmux suites.

## Acceptance Criteria

### verify-human-gates
**criterion**: dashboard/bin/dashboard --once against a seeded store with plan-review, Landing, and a quiet task prints action verbs, a next-step line, and landing branch/ahead/merged on the selector; **method**: check; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_integration.py -q -k "gates or once"; state: active

### verify-human-gates-app
**criterion**: c copies the prompt and new items trigger the message and bell in a Textual pilot with tmux stubbed; **method**: check; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k gates; state: active

### verify-human-gates-model
**criterion**: Verbs, plan-review recognition, prompt text, next-step rules, landing state, Merge branch item, and quiet rule hold in model and gates tests; **method**: check; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py tests/test_dashboard_gates.py -q -k gates; state: active

### verify-human-gates-suite
**criterion**: The full non-tmux and tmux test suites pass; **method**: check; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m "not tmux" && uv run --with textual --with pytest python -m pytest tests -q -m tmux; state: active

### verify-human-gates-tmux
**criterion**: The status-right needs-you segment appears in a real tmux server when enabled; **method**: check; **effort**: dashboard; **verify_command**: uv run --with textual --with pytest python -m pytest tests -q -m tmux -k "status and (gates or needs or segment)"; state: active

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
