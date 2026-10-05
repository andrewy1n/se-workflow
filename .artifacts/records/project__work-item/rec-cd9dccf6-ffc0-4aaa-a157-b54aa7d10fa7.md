---
{
  "base_kind": "task",
  "id": "rec-cd9dccf6-ffc0-4aaa-a157-b54aa7d10fa7",
  "identity": "unknown",
  "lifecycle_state": "done",
  "payload": {
    "assignee": "model",
    "decisions": "evidence-under-phase,evidence-view-scope,unassessed-requirement-status,loop-needs-you-triggers,release-ready-badge,stage-strip-placement",
    "effort": "dashboard",
    "executor": "subagent",
    "kind": "deliver",
    "phase": "evidence-view",
    "requirements": "R1,R2,R3,R5,R6,R7,R8,R9,R10",
    "title": "Load evidence-loop records into the dashboard model"
  },
  "record_type": "project:work-item",
  "recorded_at": "2026-10-05T04:34:53+00:00",
  "relationships": {},
  "revision": "sha256:bb51647a689a4e08ea41de832c76bdf61f48ca2ca328731f7389ab1f98fd6195",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "evidence-model"
}
---

## Description

Teach `dashboard/model.py` to read specification, design, assessment, integration-report, and release records, and to build the evidence data every screen in this phase renders. No UI change.

## Approach

Read the design record `evidence-view` first; its Interfaces section is the contract for waves 2 and 3.

1. Listing: add the five evidence types to the snapshot listing. A type the contract does not know (CLI error) yields an empty list instead of `ModelError`, so an older contract still loads. List specification with `--full` (the body holds requirement text and non-goals).
2. Types: add `RequirementRow(phase, id, text, status, next, latest_check, tasks)` and `PhaseEvidence(phase, weight, requirements, stage, integration, release_ready, decisions, non_goals)`. Add `evidence: PhaseEvidence | None = None` to `PhaseRow` and `release_ready: bool = False` to `EffortView`, both defaulted so existing constructors keep working.
3. Joins: requirement ids come from the specification payload `requirements` (comma-split, trimmed); text from `R<n>: text` lines under `## Requirements`. Traced tasks are work-items in the phase whose `requirements` include the id. Status is the latest active assessment for (phase, id); else `unassessed`, with `latest_check` the latest check-run whose `requirement` is the id and whose acceptance (by `criterion_id`) is in the phase.
4. Stage, first match wins: latest release `ready` gives `release`; else the earliest `next` in loop order among non-verified latest assessments; else all verified gives `release`; else no design gives `design`, no work-items gives `plan`, a work-item not done gives `execute`, a wave with more than one task and no passing integration-report gives `integrate`, an acceptance with a requirement and no check-run gives `verify`, else `assess`.
5. Needs you: kind `loop-route` for a latest assessment with `next` in specify/design/plan, status `blocked`, or confidence `low`; kind `integration` for a latest integration-report `fail` or `blocked`. Carry phase and requirement id (add defaulted fields to `NeedsYouItem`). Add both kinds to `NEEDS_ORDER` after `blocking-question`.
6. Activity: kinds `assessment` (summary names requirement, status, next; mark upstream routes and a level change from the previous assessment), `integration`, and `release`; `failed` for fail, failed, or blocked.
7. `load_requirement_detail(target, effort, phase, requirement) -> RequirementDetail`: text, status, decisions of the traced tasks (subject and choice), traced tasks, acceptances with their latest check-run and `evidence_kind`, and every assessment for (phase, id) including superseded, oldest first, with status, level, next, confidence.
8. A phase with no specification keeps `evidence=None` and adds no items. Do not touch `finished`.

Tests go in `tests/test_dashboard_model.py`, each name containing `evidence`, against seeded stores built through the CLI like the existing fixtures: one structured phase with spec, design, tasks, acceptances with `requirement`, check-runs with `requirement` and `evidence_kind`, superseded and current assessments, an integration-report, and a release; plus one simple phase. Write each test first and see it fail.
