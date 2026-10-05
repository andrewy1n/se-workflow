---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-c0d759c4-aad3-4a6f-a4bc-f07a3bee69fa",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "effort": "dashboard",
    "phase": "journal-view",
    "requirements": "R1,R2,R3,R4,R5,R6,R7,R8,R9",
    "weight": "full"
  },
  "record_type": "project:specification",
  "recorded_at": "2026-10-05T07:50:28+00:00",
  "relationships": {},
  "revision": "sha256:f9fd1df6b105fad0aa1706b80b17e3fa6f08725bd650bbd3b47f8f2c8fbb1345",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "journal-view",
  "time": {
    "as_of": "2026-10-05T07:50:28+00:00"
  }
}
---

## Requirements

R1: `J` on the main screen opens a Journal screen for the selected phase, or for the whole effort on All phases. `a` toggles between the phase and the whole effort. Esc returns to the main screen.
R2: The journal lists these active records for the effort: failed attempts, investigation observations, findings, continuity questions (open and answered), and assignment amendments. A task-scoped record belongs to its task's phase. A continuity question belongs to the phase named by a `plan-review:` scope, otherwise to the effort only. The phase scope shows the phase's items plus effort-only open questions.
R3: Each row shows a type glyph and label, the subject, its time, and one line of text: a failed attempt shows `attempted_action` and is marked `don't retry` (with `retry when <retry_when>` when set); an observation shows `what_was_observed`; a finding shows `claim` and `needs`; a question shows its scope as R2 of human-gates renders it and its state; an amendment shows the first line of its `Correction` section and the assignment's task.
R4: Open items come first, newest first: open continuity questions, findings whose `needs` is `human`, and observations whose subject has no finding. A separator line follows, then every other item newest first.
R5: Enter on a row opens a detail screen with the record's type, subject, payload fields, and full body. Enter on a linked task opens its task detail. `o` opens the shown record or the whole list in the pager as in spec-view.
R6: The `/` filter on the Journal matches subject and text.
R7: An effort whose goal `kind` is `repair` or `evaluate` shows a Journal panel above its task table with its open items, as in R4, for the selected phase, at most 5 rows plus `+k more`. Enter on a row opens its detail. With no open items the panel is hidden. A `deliver` or `incidental` effort shows no panel.
R8: The task detail adds an Agent work section: the latest assignment's `Orientation` and the rest of its body, each of its amendments' `Correction`, and its execution report with result and verdict. Each block is collapsed to 8 lines with a `+n lines` marker, and Enter expands or collapses it. `o` opens the focused block in the pager. Earlier assignments are listed by time with executor and report result, and Enter on one shows its blocks.
R9: A store whose contract lacks any of these types loads with no error, and the type is left out.

## Acceptance criteria

R2 scoping, R3 text, R4 order and open rules, R7 panel rule, R8 block selection, and R9: model tests in `tests/test_dashboard_model.py` and `tests/test_dashboard_journal.py` against seeded stores, selected with `-k journal`.
R1, R5, R6, R7 on screen, and R8 collapse, expand, and `o`: Textual pilot tests in `tests/test_dashboard_journal.py` and `tests/test_dashboard_app.py`, with the pager stubbed.

## Constraints

The dashboard stays read-only (constraint dashboard-read-only). No change to `contract/project-design.json` or `~/adaptive-artifacts`. Nothing executes until all five UX phases are discussed (constraint dashboard-ux-plan-before-execute).

## Non-goals

Decisions, assessments, check-runs, integration reports, and phase transitions in the journal. Answering questions or resolving findings from the dashboard. Changing Needs you.

## Invariants

The journal shows record text as stored, never summarised beyond taking the first line. The open rules in R4 and the Needs you rules agree for questions and findings. A delivery effort's main screen is unchanged by this phase.

## Assumptions

`needs` on a finding uses `human` for items that need the user, as Needs you reads it today. An observation and its finding share the task subject.
