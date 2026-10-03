---
{
  "base_kind": "instruction",
  "id": "rec-9d00fbec-bc87-40b3-b37b-38e00bea73db",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "assignment": "status-tabs",
    "effort": "dashboard-ui"
  },
  "provenance": {
    "sources": [
      "status-tabs"
    ]
  },
  "record_type": "project:assignment-amendment",
  "recorded_at": "2026-10-01T20:44:50+00:00",
  "relationships": {},
  "revision": "sha256:6a136a3b3c5dcfc96953354347e69919435f6b6849871c03d0aaf98203e78c33",
  "subject": "status-tabs",
  "time": {
    "observed": "2026-10-01T20:44:50+00:00",
    "recorded": "2026-10-01T20:44:50+00:00"
  }
}
---

## Correction

status-tabs closed with 5 tabs. The work-item description asks for more. Finish it:

Status tabs with counts replace the tiles and the d key: Active (default: running, ready, waiting), Running, Ready, Waiting, Needs you (tasks with an open needs-you item), Done, All. Keys 1-7, left/right on the tab row, or a click. The / filter applies on top. Per effort tab, kept across refreshes. Footer, README, and --once updated.

Add the Waiting and All tabs, keys 1-7, left/right on the tab row, and the README update (tiles text and key table). Keep edits small and local. Adapt tests that count tabs or keys. Run touched tests with -k during work and the acceptance command once at the end. Commit with a short Conventional Commits subject. Do not push.
