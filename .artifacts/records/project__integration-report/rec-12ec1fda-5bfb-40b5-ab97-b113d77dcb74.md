---
{
  "base_kind": "observation",
  "id": "rec-12ec1fda-5bfb-40b5-ab97-b113d77dcb74",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "effort": "dashboard",
    "phase": "human-gates",
    "result": "pass",
    "revision": "dirty"
  },
  "provenance": {
    "sources": [
      "human-gates"
    ]
  },
  "record_type": "project:integration-report",
  "recorded_at": "2026-10-09T21:20:56+00:00",
  "relationships": {},
  "revision": "sha256:b1ef766bf69ee7253482791ec844f16318a8d231e6e4eab46d7501514d07cfbc",
  "subject": "human-gates",
  "time": {
    "observed": "2026-10-09T21:20:56+00:00",
    "recorded": "2026-10-09T21:20:56+00:00"
  }
}
---

## Interfaces

- `gates.action_label` / `prompt` / `next_step` / `is_quiet` used by app Needs you, next-step, quiet status/wave.
- `landing.phase_landing` + `gates.landings_for_snapshot` / `apply_landing_needs` / `count_merged_needs` / `merge_landing_needs` shared by app landing worker and `dashboard-status --tmux`.
- `PhaseRow.body` and `TaskRow.last_record_at` from model feed landing and quiet without git in `load_snapshot`.
- `NEEDS_ORDER` includes `merge-branch` after `integration`; item ids `merge:<phase>`.
- `se-workflow.tmux` status-right segment calls the same status binary merge path.

## Assumptions

Phase Landing bodies use `phase/<slug>` or a backtick branch; base is `main`. `estimate_minutes` on TaskRow drives quiet. tmux expands pane path for status commands. Position text comes from effort-scoped current-position on EffortView.

## Invariants

`load_snapshot` remains git-free. Landing merge happens outside the snapshot builder. Alert ids are stable across refresh. Status count matches merged Needs you. Dashboard stays read-only for store and git.

## Conflicts

none
