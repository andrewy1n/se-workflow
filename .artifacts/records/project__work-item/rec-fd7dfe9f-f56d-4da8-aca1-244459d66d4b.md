---
{
  "base_kind": "task",
  "id": "rec-fd7dfe9f-f56d-4da8-aca1-244459d66d4b",
  "identity": "unknown",
  "lifecycle_state": "done",
  "payload": {
    "assignee": "sub-commit-stat-width",
    "effort": "dashboard",
    "kind": "deliver",
    "phase": "dashboard-actions",
    "title": "Fit the commit stat to the pane width"
  },
  "record_type": "project:work-item",
  "recorded_at": "2026-10-02T03:16:21+00:00",
  "relationships": {},
  "revision": "sha256:92980e1412e045fdb79325766d446c57a144cc7ce33c8ff6c5afcdfc3bae2df0",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "commit-stat-width"
}
---

## Description

The commit screen runs `git show --stat` with git's default graph width, so at 80 columns a stat line wraps and splits its count from its graph. Size the stat to the screen width (`--stat=<width>`) and re-load on resize.
