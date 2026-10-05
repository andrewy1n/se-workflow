---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-621bafff-feec-415c-9bd0-a16342b2bcde",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "confidence": "high",
    "effort": "dashboard",
    "missing": "",
    "next": "release",
    "phase": "phase-selector",
    "requirement": "R7",
    "status": "verified"
  },
  "record_type": "project:assessment",
  "recorded_at": "2026-10-05T20:50:45+00:00",
  "relationships": {},
  "revision": "sha256:f742d5589fd856af2dc1e809afeb6cc5c74c23e1674360abcca111217de7cea6",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "phase-selector-R7",
  "time": {
    "as_of": "2026-10-05T20:50:45+00:00"
  }
}
---

## Evidence

Check-run rec-c5cfe635-9a9b-4497-8f2b-5c5bfb4588e3 passed. `tests/test_dashboard_model.py -k 'follow or pin'` passed 4. Selection follows the default until a different phase is picked, stays pinned, and resumes following when the current default is picked again.

## Missing

none

## Reason

Follow, pin, resume, and missing-phase fallback are covered by the passing unit checks.
