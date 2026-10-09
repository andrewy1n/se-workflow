---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-8c8cd3b5-eac9-461a-b480-58bd3af0f8fe",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "criterion": "load_journal and ordered return correct types, phase scope, open-first ordering, and one-line text for seeded stores; missing types do not error",
    "effort": "dashboard",
    "method": "tdd",
    "phase": "journal-view",
    "requirement": "R2",
    "verify_command": "uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py tests/test_dashboard_journal.py -q -k 'journal and (load or order or scope or missing)'"
  },
  "record_type": "project:acceptance",
  "recorded_at": "2026-10-09T20:50:48+00:00",
  "relationships": {},
  "revision": "sha256:c860aed1b4e81d355f2d040504864b7ac381015f78039562ded73affa7c155bc",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "journal-model",
  "time": {
    "as_of": "2026-10-09T20:50:48+00:00"
  }
}
---

