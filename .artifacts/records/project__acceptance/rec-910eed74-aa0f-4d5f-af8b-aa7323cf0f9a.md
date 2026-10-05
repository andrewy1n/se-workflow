---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-910eed74-aa0f-4d5f-af8b-aa7323cf0f9a",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "criterion": "test_estimate_view_blank_executor fails before the change and passes after: a task with no size and no estimate_minutes still has executor subagent, an empty size, and no minutes.",
    "effort": "dashboard",
    "method": "tdd",
    "phase": "estimate-view",
    "requirement": "R7",
    "verify_command": "uv run --with pytest python -m pytest tests/test_dashboard_model.py -q -k estimate_view_blank_executor"
  },
  "record_type": "project:acceptance",
  "recorded_at": "2026-10-05T06:20:57+00:00",
  "relationships": {},
  "revision": "sha256:9e607fe4690a21c7cb49461fcc067ced2b419f144ff9c5ba6850102803252107",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "estimate-model-blank",
  "time": {
    "as_of": "2026-10-05T06:20:57+00:00"
  }
}
---

