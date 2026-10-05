---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-17c17312-7c0a-4faa-9fca-cf2154ee3b5f",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "alternatives": "one line per record",
    "choice": "Activity merges consecutive items of the same kind and outcome into one line naming their subjects",
    "effort": "dashboard",
    "phase": "phase-selector"
  },
  "record_type": "project:decision",
  "recorded_at": "2026-10-05T07:34:08+00:00",
  "relationships": {},
  "revision": "sha256:02ea2273ded30e0256d82b45f84b7b7fff653da46565de5effd92598a503b006",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "activity-merge",
  "time": {
    "as_of": "2026-10-05T07:34:08+00:00"
  }
}
---

## Rationale

The user chose this. Runs like five `insufficient → verify` assessments are one fact; merging frees lines for distinct events.

## Counter-argument

One line per record keeps each line's time exact and maps one line to one record, which is easier to trust and test.
