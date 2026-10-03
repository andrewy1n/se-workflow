---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-66a8f44a-bfea-4ee2-aea0-cbe426d17d69",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "criterion": "The isolated tmux test passes: the side pane shows the repo's dashboard, the popup binding runs the launcher in the pane directory and renders, and the status segment counts match",
    "effort": "dashboard",
    "method": "tdd",
    "phase": "tmux-integration",
    "verify_command": "cd ~/se-workflow && python3 -m pytest tests/test_tmux_integration.py -q"
  },
  "record_type": "project:acceptance",
  "recorded_at": "2026-10-02T03:16:24+00:00",
  "relationships": {},
  "revision": "sha256:400e1b7aeef2507a687156c48cdd66e29ed75a9f0eb37ea0584abc5bd9ba8037",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "verify-tmux-integration-phase",
  "time": {
    "as_of": "2026-09-29T23:13:46+00:00"
  }
}
---

