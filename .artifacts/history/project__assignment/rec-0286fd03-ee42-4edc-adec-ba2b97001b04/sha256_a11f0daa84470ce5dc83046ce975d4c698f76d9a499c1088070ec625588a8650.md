---
{
  "base_kind": "instruction",
  "id": "rec-0286fd03-ee42-4edc-adec-ba2b97001b04",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "effort": "dashboard",
    "executor": "drop-row-waits-on-agent",
    "work_item": "drop-row-waits-on"
  },
  "provenance": {
    "sources": [
      "drop-row-waits-on"
    ]
  },
  "record_type": "project:assignment",
  "recorded_at": "2026-10-10T08:27:07+00:00",
  "relationships": {},
  "revision": "sha256:a11f0daa84470ce5dc83046ce975d4c698f76d9a499c1088070ec625588a8650",
  "subject": "drop-row-waits-on",
  "time": {
    "observed": "2026-10-10T08:27:07+00:00",
    "recorded": "2026-10-10T08:27:07+00:00"
  }
}
---

## Orientation

Worktree only: `/home/andrewyin/se-workflow--waits-on-compact` on branch `phase/waits-on-compact`. Do not edit `.artifacts/`. Do not call adaptive-artifacts. Primary checkout holds the store.

Single task in this wave — no territory split.

Requirements (R1–R3):
R1: A waiting task's title cell does not include a `waits on …` note; unfinished dependencies are not listed in the task table row.
R2: Task detail still lists unfinished and finished depends-on links so the blocker list remains available without the row note.
R3: A waiting row with many unfinished dependencies stays one table line at typical dashboard widths (no wrap caused by dependency text in the title cell).

Design Invariants:
- Title cell for waiting tasks must not contain the substring `waits on`.
- Dependency membership for display remains available via task detail Depends on links.

Design Assumptions:
- No other dashboard surface (activity, Needs you, phase tasks tab) depends on the row waits-on note for correctness; grep and fix any that do as part of the same change.

Decision drop-waits-on-from-row: Drop the waits-on note from the task row; blocker names only in task detail
