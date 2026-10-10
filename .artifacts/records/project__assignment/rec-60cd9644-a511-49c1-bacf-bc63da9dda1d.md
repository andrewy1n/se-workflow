---
{
  "base_kind": "instruction",
  "id": "rec-60cd9644-a511-49c1-bacf-bc63da9dda1d",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "effort": "workflow-loop",
    "executor": "verify-phase",
    "work_item": "verify-needs-you-close"
  },
  "provenance": {
    "sources": [
      "verify-needs-you-close"
    ]
  },
  "record_type": "project:assignment",
  "recorded_at": "2026-10-10T08:29:06+00:00",
  "relationships": {},
  "revision": "sha256:2f94a9223a6c34fe0937d0b2779a054014e32545254713390c1082ae9efee38d",
  "subject": "verify-needs-you-close",
  "time": {
    "observed": "2026-10-10T08:29:06+00:00",
    "recorded": "2026-10-10T08:29:06+00:00"
  }
}
---

## Orientation

Territory: read/run tests only under /home/andrewyin/se-workflow--needs-you-close. Do not change product code unless a verify command fails and a minimal fix is required; prefer returning fail evidence.

Do not edit .artifacts/. Do not call adaptive-artifacts writes. Return the evidence block only.

### Requirements (R1–R5)

R1–R3 covered by skill doc/contract tests; R4–R5 by dashboard dismiss pilots through the Textual app entry point.

### Design Invariants

No dashboard-local dismiss cache. Human-dismissible set is questions + needs-human + unsigned-check only. Skill and dashboard clears are CLI-equivalent outcomes (finding clear = update needs none).

### Decisions

- engage-remind: remind on engage; do not block routing
- dismiss-human-gates: dismiss questions, needs:human findings, and unsigned manual checks only
- dashboard-cli-writes: dashboard dismiss via adaptive-artifacts CLI
