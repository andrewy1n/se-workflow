---
{
  "base_kind": "instruction",
  "id": "rec-01a21c7b-08b3-4648-a637-ebce9beeddf0",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "effort": "dashboard",
    "executor": "gates-ui-agent",
    "work_item": "gates-ui"
  },
  "provenance": {
    "sources": [
      "gates-ui"
    ]
  },
  "record_type": "project:assignment",
  "recorded_at": "2026-10-09T21:07:03+00:00",
  "relationships": {},
  "revision": "sha256:7ca874d96d5e1fabd1dc852f6205a826d924127a427a62b8de8377257dc6b0c8",
  "subject": "gates-ui",
  "time": {
    "observed": "2026-10-09T21:07:03+00:00",
    "recorded": "2026-10-09T21:07:03+00:00"
  }
}
---

## Orientation

Territory: `dashboard/app.py` (NEEDS_LABEL→action_label, #next-step, c copies prompt, seen_needs alerts/bell/tmux message, landing worker/cache merge into needs_you). Tests in `tests/test_dashboard_app.py` `-k gates`. Do not edit status scripts or `se-workflow.tmux` (gates-status owns those). Do not rewrite gates.py/landing.py pure APIs unless a tiny hook is required.

Worktree: `/home/andrewyin/se-workflow--human-gates`
Do not edit `.artifacts/` or call `adaptive-artifacts`. Concurrent: gates-status.

Follow `## Approach`.

### Requirements (R3, R4, R5, R9)

R3: c on Needs you copies prompt; on task row still copies slug; footer/key help say copy prompt when Needs you focused.
R4: next-step line under goal shows next: + first matching rule, then position text in muted.
R5: selected phase Landing shows branch, ahead, merged/not merged / no branch yet on selector.
R9: new Needs you ids (not at startup) bell + tmux display-message when $TMUX set.

### Design Invariants

load_snapshot stays git-free; landing merged by app. Alert ids are record ids or merge:<phase>.

### Decisions

needs-you-copy-prompt, next-step-source, landing-display, needs-you-alerts.
