---
{
  "base_kind": "instruction",
  "id": "rec-dddc149c-8993-4213-b67c-71ff7484ef11",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "effort": "dashboard-bugfix",
    "executor": "sub-column-resize",
    "work_item": "column-resize"
  },
  "provenance": {
    "sources": [
      "column-resize"
    ]
  },
  "record_type": "project:assignment",
  "recorded_at": "2026-10-01T23:05:32+00:00",
  "relationships": {},
  "revision": "sha256:c08a803c7b2e9c45fd0320bebe40cf648eaff4ccb0bcbefc1bfc4b9c836f96a3",
  "subject": "column-resize",
  "time": {
    "observed": "2026-10-01T23:05:32+00:00",
    "recorded": "2026-10-01T23:05:32+00:00"
  }
}
---

## Orientation

Repo /home/ayin/se-workflow; you run in your own git worktree from main. Another executor works on table-focus in parallel in scripts/dashboard_app.py and tests/test_dashboard_app.py: keep your diff to the code paths your task needs and add new tests rather than rewriting shared helpers. Commit once in your worktree with a Conventional Commits subject. Run tests with: uv run -q --with textual --with pytest python -m pytest <files> -q (the runtime CLI lives at ~/adaptive-artifacts). Textual pilot tests set TEXTUAL_ANIMATIONS=none via conftest.
