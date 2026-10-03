---
{
  "base_kind": "instruction",
  "id": "rec-e2ef23ca-beff-40b6-abf7-c9ea861d294b",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "effort": "dashboard-ui",
    "executor": "sub-copy-and-commit-actions",
    "work_item": "copy-and-commit-actions"
  },
  "provenance": {
    "sources": [
      "copy-and-commit-actions"
    ]
  },
  "record_type": "project:assignment",
  "recorded_at": "2026-09-30T21:28:03+00:00",
  "relationships": {},
  "revision": "sha256:878dc11a0ca09f98768d4983ad22a00589675317712bd3caa4cebbcde902e4fb",
  "subject": "copy-and-commit-actions",
  "time": {
    "observed": "2026-09-30T21:28:03+00:00",
    "recorded": "2026-09-30T21:28:03+00:00"
  }
}
---

## Orientation

Work only in ~/se-workflow on branch feat/dashboard-ui (HEAD e3b7751). Changes go in `scripts/dashboard_app.py`, `tests/test_dashboard_app.py`, and the README key list; `TaskDetail.timeline` from `scripts/dashboard_model.py` already carries report and check-run revisions in its events, so extend the model only if a revision field is missing. The dashboard footer is already full at 60 columns (`/ filter  d done  enter open  tab switch  r refresh  q quit`), so show `c copy` on the detail footer and keep it hidden or swap out `r refresh` on the dashboard footer. `dashboard-read-only` applies. Run git commands with `cwd` = the target's repo root, never through a shell string.
