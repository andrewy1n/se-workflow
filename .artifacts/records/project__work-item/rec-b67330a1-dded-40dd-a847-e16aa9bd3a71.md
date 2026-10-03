---
{
  "base_kind": "task",
  "id": "rec-b67330a1-dded-40dd-a847-e16aa9bd3a71",
  "identity": "unknown",
  "lifecycle_state": "done",
  "payload": {
    "assignee": "sub-task-list-filters",
    "effort": "dashboard",
    "kind": "deliver",
    "phase": "dashboard-actions",
    "title": "Filter the task table and hide done tasks"
  },
  "record_type": "project:work-item",
  "recorded_at": "2026-10-02T03:16:21+00:00",
  "relationships": {},
  "revision": "sha256:5c8409e10f9e546bb5f259f9432cfdaa1ef7bdae8bccf0d16c82522dc8e4abf6",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "task-list-filters"
}
---

## Description

In `scripts/dashboard_app.py`, `/` opens a one-line filter input that narrows the task table by title or subject text as you type; Enter keeps the filter, Esc clears it. `d` toggles hiding done and withdrawn tasks. The Tasks panel title shows the active filter and whether done tasks are hidden. Filter state is per effort tab and survives refreshes. Footer and README list the keys.
