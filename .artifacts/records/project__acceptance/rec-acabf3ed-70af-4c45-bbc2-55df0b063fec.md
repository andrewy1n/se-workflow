---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-acabf3ed-70af-4c45-bbc2-55df0b063fec",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "criterion": "Dashboard dismiss pilots pass through the Textual app entry point for human-dismissible kinds and refuse non-human kinds",
    "effort": "workflow-loop",
    "method": "tdd",
    "phase": "needs-you-close",
    "requirement": "R4",
    "verify_command": "uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k dismiss"
  },
  "record_type": "project:acceptance",
  "recorded_at": "2026-10-10T08:19:11+00:00",
  "relationships": {},
  "revision": "sha256:74219ab22d937c752f6c3b460bb4441b7efd60e7c195f2e5374259f0aa4a7b47",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "verify-needs-you-close",
  "time": {
    "as_of": "2026-10-10T08:19:11+00:00"
  }
}
---

