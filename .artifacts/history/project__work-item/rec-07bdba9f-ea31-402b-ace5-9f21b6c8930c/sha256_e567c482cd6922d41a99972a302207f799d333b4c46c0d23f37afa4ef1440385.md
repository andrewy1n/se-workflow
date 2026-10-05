---
{
  "base_kind": "task",
  "id": "rec-07bdba9f-ea31-402b-ace5-9f21b6c8930c",
  "identity": "unknown",
  "lifecycle_state": "planned",
  "payload": {
    "assignee": "",
    "effort": "workflow-loop",
    "executor": "subagent",
    "kind": "deliver",
    "phase": "evidence-loop",
    "title": "Stamp tasks with requirements and decisions"
  },
  "record_type": "project:work-item",
  "recorded_at": "2026-10-05T01:56:37+00:00",
  "relationships": {
    "depends_on": [
      "rec-2ff3de0f-4884-4df0-973b-2d94bc0919d6"
    ]
  },
  "revision": "sha256:e567c482cd6922d41a99972a302207f799d333b4c46c0d23f37afa4ef1440385",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "trace-plan"
}
---

## Description

Stamp each planned task with the requirements and design decisions it implements.

## Approach

In `skills/plan-phase/SKILL.md`, when a `project:specification` exists for the phase, set work-item payload `requirements` to the comma-separated requirement ids that task implements and `decisions` to the comma-separated decision subjects it follows. Set each acceptance payload `requirement` to one of those ids. Several acceptances keep the existing subject-suffix rule. When no specification exists, omit the new fields.

Do not write `assessment` or `integration-report` from this skill. Dependencies stay `--rel depends_on`. Do not write `ready` or `wave`.

Add `tests/test_plan_trace.py`. It asserts the skill's work-item create payloads include `requirements` and `decisions`, and the acceptance payloads include `requirement`, and that those invocations are contract-legal via `skill_extraction.check_skill_text`.

Do not edit `discuss`, `execute-phase`, or `verify-work`.
