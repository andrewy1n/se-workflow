# Kinds and focus

Shared rules for every se-workflow skill. Do not invent extra skills for
bugs, one-offs, or evals.

## Kinds

`kind` is `deliver` | `repair` | `evaluate` | `incidental`. Put it on
`active-goal` (the effort) and each `work-item`. Missing `kind` means
`deliver`.

| Kind | Unknown | Done | Records |
|---|---|---|---|
| `deliver` | how | change + binary check | work-item + acceptance + check-run |
| `repair` | what is wrong | cause + repro gone | those, plus observation / finding |
| `evaluate` | whether it holds / which is better | campaign result | check-run if binary; finding if comparative or inconclusive |
| `incidental` | usually nothing | change landed | none, or one work-item (see below) |

`acceptance.method` stays `tdd` | `check` | `manual`. Do not stuff a
metric delta into `check-run.result`. Use `project:finding` (`claim`,
`basis`, `invalidated_when`).

## Focus

Focus is a **subject string**, not a record. Name it (from `engage`, the
user, or the only live `active-goal` subject). Then:

- Read the `## <focus>` section of handoff (grouped by subject) and the
  `## <focus>` section of `project:plan` (grouped by `effort`).
- Ignore other live goals. Do not supersede `active-goal` or
  `current-position` whose `subject` is not the focus.
- Task-scoped records (`work-item`, `acceptance`, `check-run`,
  `decision`, `failed-attempt`, `investigation-observation`, `finding`)
  use `subject` = task slug and `payload.effort` = focus.
- Goal, position, and continuity-question use `subject` = focus.
- If `payload.effort` is missing (old records) and exactly one active
  goal exists, treat that subject as the effort. If several goals exist
  and `effort` is missing, stop and ask.

A new effort is a new subject. Create its goal/position. Leave the
others active.

## Incidental

- Fits this chat and is not an interrupt of another live effort: **no
  records**. Do the work in this session.
- May span chats, or it interrupts a live phase: one `work-item` +
  `acceptance`, `kind=incidental`, `phase="-"`, `effort` = a **new**
  subject (not the interrupted effort). Work-item `subject` may equal
  that effort slug when there is only one task. Do not supersede the
  main goal.

## Writer

Only the parent session calls `adaptive-artifacts`. Subagents return
evidence. Single-writer store.
