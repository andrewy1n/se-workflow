---
{
  "base_kind": "task",
  "id": "rec-06631dac-f66b-4c00-bc9f-f0fcd3d9b071",
  "identity": "unknown",
  "lifecycle_state": "done",
  "payload": {
    "assignee": "contract",
    "decisions": "task-agent-estimate,glance-run-facts",
    "effort": "dashboard",
    "executor": "subagent",
    "kind": "deliver",
    "phase": "run-facts",
    "requirements": "R1,R2",
    "title": "Allow size and estimate_minutes on work-items"
  },
  "record_type": "project:work-item",
  "recorded_at": "2026-10-05T05:59:49+00:00",
  "relationships": {},
  "revision": "sha256:34c4652305071cbac58f8dd93be5c8f7636b0e26f37400b1f93eeff7f1d47f00",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "estimate-contract"
}
---

## Description

Add optional `size` and `estimate_minutes` to the work-item contract so a task can record how big it is and how long its executor should take.

## Approach

Read the design record `run-facts` and specification `run-facts` first. Requirements R1 and R2. Decisions task-agent-estimate and glance-run-facts.

1. In `contract/project-design.json`, on the `work-item` record, add `size` and `estimate_minutes` to both `payload` and `optional_payload`. Add `payload_enum.size` as `["XS", "S", "M", "L", "XL"]`. Leave `estimate_minutes` out of `payload_enum`. The runtime has no integer type, so the field stays free at the contract layer. Do not add `minutes` or `hours`.
2. Do not add either field to the `phase` record. Its payload stays `title`, `ordinal`, and `effort`.
3. Copy the edited file onto `.artifacts/project-design.json` so the two files stay byte-identical. Do not run `adaptive-artifacts`. Do not edit `dashboard/`, `skills/`, or `~/adaptive-artifacts`.
4. Write `tests/test_estimate_contract.py` first. Assert the size enum is exactly those five values and `size` is optional; `estimate_minutes` is optional and not an enum; the phase payload has neither field; the work-item has no `minutes` or `hours` field.
5. `create_generic_record` fills every payload field, so generic work-items gain `size` `XS` and `estimate_minutes` `test-estimate_minutes`. Run `tests/test_contract_self_consistency.py` and `tests/test_plan_wave_rules.py`. If a test fails only because those keys appeared, update that assertion in this task. Do not special-case the helper.
