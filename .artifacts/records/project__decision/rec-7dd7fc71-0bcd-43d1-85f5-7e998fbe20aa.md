---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-7dd7fc71-0bcd-43d1-85f5-7e998fbe20aa",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "alternatives": "the lowest-ordinal in-progress phase",
    "choice": "When several phases are in progress, the default is the one with the most recent activity",
    "effort": "dashboard",
    "phase": "phase-selector"
  },
  "record_type": "project:decision",
  "recorded_at": "2026-10-05T07:34:08+00:00",
  "relationships": {},
  "revision": "sha256:126700df5cd695dfef512a59f2d9d9150a1abf6720d7f50d7d3b9f758ef97b38",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "parallel-phase-default",
  "time": {
    "as_of": "2026-10-05T07:34:08+00:00"
  }
}
---

## Rationale

The user chose this. The phase with the latest activity is the one an agent is working in, which is what a glance should show.

## Counter-argument

Lowest ordinal is stable: the default would not flip between phases as two chats record work alternately.
