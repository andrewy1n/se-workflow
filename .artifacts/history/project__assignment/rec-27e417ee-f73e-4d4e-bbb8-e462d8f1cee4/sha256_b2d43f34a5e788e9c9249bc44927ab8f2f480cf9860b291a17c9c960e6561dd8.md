---
{
  "base_kind": "instruction",
  "id": "rec-27e417ee-f73e-4d4e-bbb8-e462d8f1cee4",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "effort": "dashboard-ui",
    "executor": "sub-task-detail-model",
    "work_item": "task-detail-model"
  },
  "provenance": {
    "sources": [
      "task-detail-model"
    ]
  },
  "record_type": "project:assignment",
  "recorded_at": "2026-09-30T19:59:14+00:00",
  "relationships": {},
  "revision": "sha256:b2d43f34a5e788e9c9249bc44927ab8f2f480cf9860b291a17c9c960e6561dd8",
  "subject": "task-detail-model",
  "time": {
    "observed": "2026-09-30T19:59:14+00:00",
    "recorded": "2026-09-30T19:59:14+00:00"
  }
}
---

## Orientation

Work only in ~/se-workflow on branch feat/dashboard-ui (HEAD 360ebcc). Extend `scripts/dashboard_model.py` and `tests/test_dashboard_model.py`; keep the existing snapshot API unchanged. `list --subject` is exact-or-prefix, so filter to the task slug and `<slug>-<suffix>` records of this effort, and exclude records that belong to another work-item. The next task builds a Textual screen on this loader, so return plain dataclasses with no UI code.
