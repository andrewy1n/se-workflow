---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-b0c9ad6b-d149-4fdc-bc6d-a85e62f7eb49",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "alternatives": "per-task executor including workflow; always one subagent per task",
    "choice": "Each wave is inline or subagent. Tasks in a wave share that executor. There is no workflow executor.",
    "effort": "workflow-loop",
    "phase": "wave-executor"
  },
  "record_type": "project:decision",
  "recorded_at": "2026-10-03T08:34:28+00:00",
  "relationships": {},
  "revision": "sha256:68a6e7527bfae598d4765028b798dc081089f371a1ae385e309ac84caee507f7",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "wave-executor-mode",
  "time": {
    "as_of": "2026-10-03T08:34:28+00:00"
  }
}
---

## Rationale

The phases already run are a few tasks in one area. An implementation wave is uniform, and the verification task sits alone in the last wave because it depends on the rest. Choosing inline or subagent for that wave covers both. A workflow script does not run in Cursor, and none of those phases needed one.

## Counter-argument

A workflow executor would matter for a sweep across many independent items, such as auditing every skill for the same mistake. Leaving it out means that future phase has to be expressed as subagents, which the parent coordinates turn by turn.
