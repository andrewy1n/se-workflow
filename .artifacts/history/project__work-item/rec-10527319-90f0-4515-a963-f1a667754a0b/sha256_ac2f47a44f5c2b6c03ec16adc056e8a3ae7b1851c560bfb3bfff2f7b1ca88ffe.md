---
{
  "base_kind": "task",
  "id": "rec-10527319-90f0-4515-a963-f1a667754a0b",
  "identity": "unknown",
  "lifecycle_state": "planned",
  "payload": {
    "assignee": "",
    "effort": "dashboard-ui",
    "kind": "deliver",
    "phase": "task-details",
    "title": "Load a task's records for the detail screen"
  },
  "record_type": "project:work-item",
  "recorded_at": "2026-09-30T19:55:30+00:00",
  "relationships": {},
  "revision": "sha256:ac2f47a44f5c2b6c03ec16adc056e8a3ae7b1851c560bfb3bfff2f7b1ca88ffe",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "task-detail-model"
}
---

## Description

Add a task-detail loader to `scripts/dashboard_model.py`. Given a work-item id, it returns the work-item (title, status, phase, wave, assignee, body), its depends-on and blocks tasks by subject and status, each acceptance with its latest check-run (result, method, signed_by, revision), a timeline of assignments, amendments, execution reports (with body), and check-runs oldest first, and any findings, decisions, failed attempts, and observations on the task. It uses one `list --subject <slug> --full` call and one `get`, and keeps only records for this task and effort.
