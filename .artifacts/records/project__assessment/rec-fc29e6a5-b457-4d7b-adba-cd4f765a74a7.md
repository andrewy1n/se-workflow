---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-fc29e6a5-b457-4d7b-adba-cd4f765a74a7",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "confidence": "high",
    "effort": "dashboard",
    "missing": "",
    "next": "release",
    "phase": "waits-on-compact",
    "requirement": "R3",
    "status": "verified"
  },
  "record_type": "project:assessment",
  "recorded_at": "2026-10-10T08:31:41+00:00",
  "relationships": {},
  "revision": "sha256:a6ecf9620354b1a97fef060c39e41ce91ece0eb7bf2dde169e79eebe012989e1",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "waits-on-compact-R3",
  "time": {
    "as_of": "2026-10-10T08:31:41+00:00"
  }
}
---

## Evidence

App pilot waiting_row at 60/120: no waits on, no newline in title cell with several unfinished deps.

## Missing

none

## Reason

All check-runs for R3 passed after the title_cell change; the requirement holds.
