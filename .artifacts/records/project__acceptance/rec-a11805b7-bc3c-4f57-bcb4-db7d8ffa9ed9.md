---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-a11805b7-bc3c-4f57-bcb4-db7d8ffa9ed9",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "criterion": "Full non-tmux and tmux test suites pass",
    "effort": "dashboard",
    "method": "check",
    "phase": "phase-selector",
    "requirement": "R4",
    "verify_command": "uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m not tmux && uv run --with textual --with pytest python -m pytest tests -q -m tmux"
  },
  "record_type": "project:acceptance",
  "recorded_at": "2026-10-05T17:39:28+00:00",
  "relationships": {},
  "revision": "sha256:893736e58bac475e78c7123667766970686c82bd2f7a570103cbdccc99b4974e",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "verify-phase-selector-suite",
  "time": {
    "as_of": "2026-10-05T17:39:28+00:00"
  }
}
---

