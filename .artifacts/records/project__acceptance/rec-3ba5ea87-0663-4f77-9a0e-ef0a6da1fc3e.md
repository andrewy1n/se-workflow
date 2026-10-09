---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-3ba5ea87-0663-4f77-9a0e-ef0a6da1fc3e",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "criterion": "After phase_landing runs, git status and the store directory are unchanged",
    "effort": "dashboard",
    "method": "tdd",
    "phase": "human-gates",
    "requirement": "R11",
    "verify_command": "uv run --with textual --with pytest python -m pytest tests/test_dashboard_gates.py -q -k readonly"
  },
  "record_type": "project:acceptance",
  "recorded_at": "2026-10-09T20:43:23+00:00",
  "relationships": {},
  "revision": "sha256:3d785ce977c9936ce87b96f5d62ff95876ae541daa8c463864808213b22df709",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "gates-landing-readonly",
  "time": {
    "as_of": "2026-10-09T20:43:23+00:00"
  }
}
---

