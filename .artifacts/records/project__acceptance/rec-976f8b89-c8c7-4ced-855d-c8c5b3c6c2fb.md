---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-976f8b89-c8c7-4ced-855d-c8c5b3c6c2fb",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "criterion": "The dashboard files are in dashboard/, none remain in scripts/, and the non-tmux dashboard tests pass at the new paths.",
    "effort": "dashboard",
    "method": "tdd",
    "phase": "dashboard-package",
    "verify_command": "test ! -e scripts/dashboard_app.py && test ! -e scripts/dashboard_model.py && test ! -e scripts/artifact_store.py && uv run --with pytest --with textual pytest tests/test_dashboard_app.py tests/test_dashboard_model.py tests/test_dashboard_launcher.py tests/test_dashboard_status.py tests/test_dashboard_view.py tests/test_dashboard_integration.py"
  },
  "record_type": "project:acceptance",
  "recorded_at": "2026-10-02T18:57:13+00:00",
  "relationships": {},
  "revision": "sha256:e3e2ac23874e52e9d5345c4704656883a9683aec04da4c8a336d6b47b8314ec1",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "package-move",
  "time": {
    "as_of": "2026-10-02T18:57:13+00:00"
  }
}
---

