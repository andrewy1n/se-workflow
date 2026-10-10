---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-c77c5dad-af36-456c-9bc0-f5ab73cd30b8",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "decisions": "engage-remind,dismiss-human-gates,dashboard-cli-writes",
    "effort": "workflow-loop",
    "phase": "needs-you-close"
  },
  "record_type": "project:design",
  "recorded_at": "2026-10-10T08:16:52+00:00",
  "relationships": {},
  "revision": "sha256:5cf05b8d2ad2684520d7e18fd85cdd8b88419dc691fe5732cfcb73f39ceba053",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "needs-you-close",
  "time": {
    "as_of": "2026-10-10T08:16:52+00:00"
  }
}
---

## Architecture

Two writers, one clear model. Agent skills clear human-dismissible Needs-you sources when the user settles them in chat. The dashboard dismisses the same kinds by shelling out to adaptive-artifacts. Derived Needs you continues to read store state only.

## Interfaces

Skill clear commands (parent session):
- continuity-question: `update --transition answered`
- finding needs human: `supersede` with `needs` `none` (claim/basis/invalidated_when carried or restated)
- unsigned manual check: `correct` (or contract-legal successor) setting `signed_by`

engage: after focus is named, list open human-dismissible items for that effort; remind; do not block routing.

Dashboard: on Needs you list/detail, a dismiss binding for human-dismissible kinds only; invoke CLI with store root from the current target; refresh snapshot; on failure keep the item and show the error. Non-dismissible kinds keep copy-prompt / existing actions only.

## Decisions

- engage-remind
- dismiss-human-gates
- dashboard-cli-writes

## Invariants

No dashboard-local dismiss cache. Human-dismissible set is questions + needs-human + unsigned-check only. Skill and dashboard clears are CLI-equivalent outcomes.

## Assumptions

adaptive-artifacts available to the dashboard process. Signer identity for manual checks is available (config, env, or short prompt).

## Tradeoffs

Remind over gate: less friction, relies on the reminder and dismiss key to prevent drift. CLI over library: consistency over latency. Human-gates only: safer dismiss, merge/integration still need agent prompts.

## Risks

Agents still skip the remind step; mitigate with an explicit engage checklist line. Dashboard CLI failures confuse users; mitigate with a clear error and unchanged panel. Wrong signer string on dismiss; mitigate with a single configured default.
