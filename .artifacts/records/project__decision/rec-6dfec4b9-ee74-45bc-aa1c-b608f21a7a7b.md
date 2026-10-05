---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-6dfec4b9-ee74-45bc-aa1c-b608f21a7a7b",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "alternatives": "everything follows the selected phase, including Needs you and Activity; only the task table follows",
    "choice": "Each effort selects a phase, by default the current one. The task table, status-tab counts, and progress bar follow the selection; Needs you and Activity stay effort-wide",
    "effort": "dashboard",
    "phase": "phase-selector"
  },
  "record_type": "project:decision",
  "recorded_at": "2026-10-05T07:34:07+00:00",
  "relationships": {},
  "revision": "sha256:3b86df7b923bc1d2f4285ef1d858d6bf2ac9db43af27765715cafc69e1d86b4a",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "phase-selection-scope",
  "time": {
    "as_of": "2026-10-05T07:34:07+00:00"
  }
}
---

## Rationale

The user chose this. Scoping the table and its counts removes finished tasks from view and gives the per-phase views a selection to follow. Keeping Needs you and Activity effort-wide means nothing waiting on the user is hidden by a selection.

## Counter-argument

Scoping everything would make the screen consistent: every number on it would describe one phase, and a user would never have to ask which scope a panel uses.
