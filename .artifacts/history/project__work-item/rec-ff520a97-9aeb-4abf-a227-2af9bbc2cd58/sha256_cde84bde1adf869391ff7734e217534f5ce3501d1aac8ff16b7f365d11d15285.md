---
{
  "base_kind": "task",
  "id": "rec-ff520a97-9aeb-4abf-a227-2af9bbc2cd58",
  "identity": "unknown",
  "lifecycle_state": "planned",
  "payload": {
    "assignee": "",
    "effort": "workflow-loop",
    "executor": "subagent",
    "kind": "deliver",
    "phase": "evidence-loop",
    "title": "Assess evidence and choose the next stage"
  },
  "record_type": "project:work-item",
  "recorded_at": "2026-10-05T01:56:37+00:00",
  "relationships": {
    "depends_on": [
      "rec-2ff3de0f-4884-4df0-973b-2d94bc0919d6"
    ]
  },
  "revision": "sha256:cde84bde1adf869391ff7734e217534f5ce3501d1aac8ff16b7f365d11d15285",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "assess-route"
}
---

## Description

Turn verification into evidence plus an assessment that picks the stage to revisit.

## Approach

In `skills/verify-work/SKILL.md`, when the acceptance has `requirement`, the check-run payload includes that `requirement` and an `evidence_kind` from the contract enum. `result` `insufficient` means the criterion was not exercised. `pass` is evidence for that requirement only.

After the check-runs, write one `project:assessment` per requirement. Subject is `<phase-slug>-<requirement-id>`. Supersede the active assessment with that subject. Payload: `requirement`, `status`, `level` (omit only when `status` is `verified`), `next`, `confidence` (`high` when `verified`, otherwise `low`), `phase`, `effort`, `missing` (what evidence is absent, or empty).

Choose `next` as follows. Do not send every failure to execute.

- `failed` and the cause is the task's code: `level` `implementation`, `next` `execute`. Leave the work-item `in_progress`.
- `failed` and the design cannot satisfy the requirement: `level` `design`, `next` `design`.
- `failed` and no task covers the requirement: `level` `plan`, `next` `plan`.
- `failed` and the requirement is ambiguous or contradicted: `level` `specification`, `next` `specify`.
- integration-report `fail`: `level` `integration`, `next` `execute` when a task must change, otherwise `next` `integrate`.
- `insufficient`: `level` `verification`, `next` `verify`. Set `missing` to the absent check. Prefer the first missing kind in this order: acceptance, integration, unit, property, fuzz, review.
- `level` `environment` or `unknown`: open a blocking `project:continuity-question` and a finding with `needs` `human`. Do not set `next` to `execute`.

Count failed assessments for that requirement, including superseded ones. At three, open a blocking continuity-question and a finding with `needs` `human`, and do not set `next` to `execute`.

When every assessment for the phase is `verified`, create `project:release` with `state` `ready`. Do not deploy. A phase with no specification skips assessment and release. Incidental work skips them too.

In `skills/engage/SKILL.md`, a `project:feedback` record is new intent for the effort it names. Route it through `discuss` (specify). Do not collect feedback. Document a `list --type project:feedback` invocation.

Add `tests/test_assess_routing.py`. It asserts the routing table, the three-failure escalation, the release `ready` write, and that the documented invocations are contract-legal.

Do not edit `scripts/close_batch.py`. A result other than `pass` is already unmet there.
