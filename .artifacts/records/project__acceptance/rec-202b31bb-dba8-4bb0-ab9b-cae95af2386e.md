---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-202b31bb-dba8-4bb0-ab9b-cae95af2386e",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "criterion": "A plugin install made with sync-plugin.sh contains an executable se-workflow.tmux.",
    "effort": "dashboard",
    "method": "check",
    "phase": "tmux-plugin-entry",
    "verify_command": "d=$(mktemp -d) && bash scripts/sync-plugin.sh \"$d/p\" && test -x \"$d/p/se-workflow.tmux\""
  },
  "record_type": "project:acceptance",
  "recorded_at": "2026-10-02T19:35:21+00:00",
  "relationships": {},
  "revision": "sha256:260473c8e5f4030f1527a786e0a3f8731114a1b14ddec1028efba62f7d10334e",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "tmux-conf-removal-install",
  "time": {
    "as_of": "2026-10-02T19:35:21+00:00"
  }
}
---

