---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-31e78aca-8c81-42ab-afc5-c6d6bf08138b",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "alternatives": "Fold into Needs you; read-only Journal/Activity only",
    "choice": "Separate Backlog panel on the effort pane for open items",
    "effort": "workflow-loop",
    "phase": "backlog-capture"
  },
  "record_type": "project:decision",
  "recorded_at": "2026-10-10T09:21:34+00:00",
  "relationships": {},
  "revision": "sha256:d884f74191b687eeb998f2ffb1a62e5c8b14f7e3fc64e1ae81702eccde0cb601",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "backlog-dashboard-surface",
  "time": {
    "as_of": "2026-10-10T09:21:34+00:00"
  }
}
---

## Rationale

Needs you is for gates that block or demand a human action now. Open backlog items are parked inventory: useful to see and clear, but not the same urgency. A separate Backlog panel on the effort pane keeps that distinction, matches Tasks / Needs you / Journal layout, and still scopes to `payload.effort`.

## Counter-argument

Folding backlog into Needs you would reuse the list, detail, and dismiss wiring with almost no new chrome. The cost is mixing deferred work into the gate list so engage-remind and the needs-you count treat parked items like unanswered questions.
