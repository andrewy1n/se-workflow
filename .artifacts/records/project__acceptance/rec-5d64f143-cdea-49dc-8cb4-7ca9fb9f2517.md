---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-5d64f143-cdea-49dc-8cb4-7ca9fb9f2517",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "criterion": "The tmux popup layout test passes, README shows the tab row with number keys, and the full suite passes",
    "effort": "dashboard",
    "method": "check",
    "phase": "features-layout",
    "verify_command": "uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux -rf"
  },
  "record_type": "project:acceptance",
  "recorded_at": "2026-10-02T03:16:28+00:00",
  "relationships": {},
  "revision": "sha256:ade09efe12f25ae3d6faa7575d23d496bd7584d5ea6c312ae28e5a5552689879",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "verify-layout-phase",
  "time": {
    "as_of": "2026-10-02T02:00:03+00:00"
  }
}
---

