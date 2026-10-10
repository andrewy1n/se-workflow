---
{
  "base_kind": "instruction",
  "id": "rec-9bb777bd-2172-4f96-bba6-7df542adcd9d",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "effort": "workflow-loop",
    "executor": "verify-subagent",
    "work_item": "verify-backlog-capture"
  },
  "provenance": {
    "sources": [
      "verify-backlog-capture"
    ]
  },
  "record_type": "project:assignment",
  "recorded_at": "2026-10-10T09:36:32+00:00",
  "relationships": {},
  "revision": "sha256:376669a07661abb9bc9fdd7bd4819d4b6a0bd7e7f30b9f469a94d45b86132efe",
  "subject": "verify-backlog-capture",
  "time": {
    "observed": "2026-10-10T09:36:32+00:00",
    "recorded": "2026-10-10T09:36:32+00:00"
  }
}
---

## Orientation

Worktree: /home/andrewyin/se-workflow--backlog-capture
Do not write .artifacts. Run phase-scoped verify commands only; do not edit product code unless a tiny fix is required (prefer fail with evidence).
No concurrent peers.

### Requirements
R1–R6 as in the phase specification (all must hold together).

### Design Invariants
Feedback never stores deferred backlog; only status=open in handoff/Backlog panel; Needs you never lists backlog; structured promote does not skip discuss.

### Decisions
All backlog-capture decisions apply; this task only verifies.
