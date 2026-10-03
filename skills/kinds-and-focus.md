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

`acceptance.method` stays `tdd` | `check` | `manual`; `verify_command`
holds the literal command that backs it (empty string for a `manual`
check with no script). Do not stuff a metric delta into
`check-run.result`. Use `project:finding` (`claim`, `basis`,
`invalidated_when`, `needs`).

`executor` on a work-item is `inline` or `subagent`. Every task in a
wave uses the same executor. Missing `executor` means `subagent`.

The phase body includes a `## Landing` section with branch
`phase/<phase-slug>`, worktree
`<repo-parent>/<repo-name>--<phase-slug>`, base `main`, and these
close actions: commit code on the phase branch, merge that branch
into `main`, then commit the store on the primary checkout. Push
appears only when it is one of the human stops. Incidental work has
no Landing section. A phase body that omits Landing is not ready
for plan review.

## Focus

A **live** goal is an `active-goal` in lifecycle `active` whose
`payload.status` is not `closed` (missing means open).

### Closing and reopening

`status` (`open` | `closed`) on `active-goal` and `current-position`
says whether an effort is live. It is a payload field, not the
lifecycle. Closing and reopening both `supersede` the effort's goal and
position with the new `status`; `supersede` merges the payload, so the
other fields carry over.

- **Close** only when the user says no more phases follow.
  `execute-phase` asks when an effort's last phase is done. An effort
  whose phases and tasks are all done is "finished" on the dashboard,
  but it stays open until the user closes it.
- **Reopen** when work returns to a closed effort: supersede its goal
  and position with `status: open`, then add the phase. Never create a
  second goal with a closed effort's subject.

Closed goals do not show in views. Find them with:

```bash
adaptive-artifacts list --type project:active-goal --state active --where payload.status=closed

adaptive-artifacts supersede --type project:active-goal --id <goal-id> \
  --expected-revision <revision> --payload '{"status":"open"}'

adaptive-artifacts supersede --type project:current-position --id <position-id> \
  --expected-revision <revision> --payload '{"status":"open"}'
```

Focus is a **subject string**, not a record. Name it (from `engage`, the
user, or the only live `active-goal` subject). Then:

- Read the `## <focus>` section of handoff (grouped by `effort`) and
  the focus's phases in `project:plan` (grouped by phase).
- Ignore other live goals. Do not supersede `active-goal` or
  `current-position` that belongs to another effort.
- Task-scoped records (`work-item`, `acceptance`, `check-run`,
  `decision`, `failed-attempt`, `investigation-observation`, `finding`,
  `assignment`, `assignment-amendment`, `execution-report`) use
  `subject` = task slug and `payload.effort` = focus.
- Goal, the effort position, and continuity-question use `subject` =
  focus. A running phase also has its own position: `subject` = phase
  slug, `scope` = `phase`, `payload.effort` = focus. Each chat writes
  only its own phase's position; the effort position changes when a
  phase closes.
- If `payload.effort` is missing (old records) and exactly one active
  goal exists, treat that subject as the effort. If several goals exist
  and `effort` is missing, stop and ask.

An effort is a product area or objective, not one ask. New work in
an area a live goal already covers is a new phase of that effort. A
new effort is a new subject only when no live goal covers the area.
Create its goal/position. Leave the others active.

## Incidental

- Fits this chat and is not an interrupt of another live effort: **no
  records**. Do the work in this session.
- May span chats, or it interrupts a live phase: one `work-item` +
  `acceptance`, `kind=incidental`, `phase=""` (no phase record exists
  for incidental work — `validate` checks a non-empty `phase` against
  real `project:phase` subjects, so leaving it unset is required, not
  optional), `effort` = a **new** subject (not the interrupted effort).
  Work-item `subject` may equal that effort slug when there is only one
  task. Do not supersede the main goal.

## Writer

Only the parent session calls `adaptive-artifacts` in any form that
writes. Subagents return evidence in their response text, never by
writing to the store — and never will, even once a `--read-only`
executor mode exists: that mode names what an executor may read, it
does not make the store multi-writer. Single-writer store.
