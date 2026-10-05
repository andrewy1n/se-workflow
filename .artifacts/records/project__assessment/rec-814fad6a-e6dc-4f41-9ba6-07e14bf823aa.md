---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-814fad6a-e6dc-4f41-9ba6-07e14bf823aa",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "confidence": "high",
    "effort": "dashboard",
    "level": "",
    "missing": "",
    "next": "release",
    "phase": "evidence-view",
    "requirement": "R2",
    "status": "verified"
  },
  "record_type": "project:assessment",
  "recorded_at": "2026-10-05T06:46:42+00:00",
  "relationships": {
    "supersedes": [
      "rec-bda06719-7d35-4b82-9f30-3535eaca1b8b"
    ]
  },
  "revision": "sha256:45b2c31478452bfa351a29c7f13d7e5084ba0df6d48fed1dd9cb4b71cc7b464a",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "evidence-view-R2",
  "time": {
    "as_of": "2026-10-05T06:46:42+00:00"
  }
}
---

## Evidence

tests/test_dashboard_model.py -q -k evidence passed 8, including the R2 model checks. Check-run rec-571ad7b4-d991-4250-8066-99335077a868 passed.

## Missing

none

## Reason

The evidence model tests pass, so the requirement rows still come from the latest assessment.
