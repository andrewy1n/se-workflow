---
{
  "base_kind": "instruction",
  "id": "rec-0d0efff3-c79a-4174-a21d-ef79a8ccda1d",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "effort": "dashboard-features",
    "executor": "sub-task-detail-links",
    "work_item": "task-detail-links"
  },
  "provenance": {
    "sources": [
      "task-detail-links"
    ]
  },
  "record_type": "project:assignment",
  "recorded_at": "2026-10-02T01:43:01+00:00",
  "relationships": {},
  "revision": "sha256:eea2f86e4b1d7b7b70055f8857161909e2d746a95c2a0860febbd388bc21165f",
  "subject": "task-detail-links",
  "time": {
    "observed": "2026-10-02T01:43:01+00:00",
    "recorded": "2026-10-02T01:43:01+00:00"
  }
}
---

## Orientation

Work in /home/ayin/se-workflow/.claude/worktrees/task-detail-links (branch wt/task-detail-links from feat/dashboard-features). Never cd to /home/ayin/se-workflow: another session works there on main. You own TaskDetailScreen and the app-level guards it needs in scripts/dashboard_app.py, plus new tests in tests/test_dashboard_app.py. phase-detail-tasks runs in parallel and changes PhaseDetailScreen: do not touch it. Commit once.
