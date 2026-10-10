---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-2ad10a07-f300-4aee-b79c-4cabb9cb3e3f",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "criterion": "Focused dashboard tasks/app tests that formerly expected row waits on pass against the dropped form",
    "effort": "dashboard",
    "method": "check",
    "phase": "waits-on-compact",
    "requirement": "R3",
    "verify_command": "uv run --with textual --with pytest python -m pytest tests/test_dashboard_tasks.py tests/test_dashboard_app.py -q -k 'waits or title_cell or waiting_row'"
  },
  "record_type": "project:acceptance",
  "recorded_at": "2026-10-10T08:25:55+00:00",
  "relationships": {},
  "revision": "sha256:ca12615af0149e7569beaba27cb515e35818b88da7f8d40745f36fe49729d395",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "verify-waits-on-compact-suite",
  "time": {
    "as_of": "2026-10-10T08:25:55+00:00"
  }
}
---

