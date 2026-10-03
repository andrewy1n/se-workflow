---
{
  "base_kind": "task",
  "id": "rec-74df5b9c-cfe6-45a9-b8fe-5b99eb7a0a9a",
  "identity": "unknown",
  "lifecycle_state": "done",
  "payload": {
    "assignee": "sub-verify-needs-you-phase",
    "effort": "dashboard",
    "kind": "deliver",
    "phase": "features-needs-you",
    "title": "Integration-test Needs you and finished efforts and verify the phase"
  },
  "record_type": "project:work-item",
  "recorded_at": "2026-10-02T03:16:23+00:00",
  "relationships": {
    "depends_on": [
      "rec-2a08ea17-ba31-45d1-a6b3-aa43a15f1db2",
      "rec-eb663e33-23d9-4ad8-96e4-1d10d1cf1d65"
    ]
  },
  "revision": "sha256:99f4952d5eceb62d11b0ff1d9f3be894a9fc7120452c41cc9349c1eb55010f21",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "verify-needs-you-phase"
}
---

## Description

Add a tmux popup test that presses n, walks the list, opens a task-linked item and a question, returns with esc, and sees a finished effort sorted last with All N tasks done. Update README keys and screens. Run the full suite. Waits on needs-you-list and finished-effort-view.
