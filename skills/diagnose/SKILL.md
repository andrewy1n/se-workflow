---
name: diagnose
description: >-
  Separates a verification or integration failure from its cause, then
  either hands back a repair or escalates. Use when verify or integrate
  returns fail. Do not repair an unresolved cause or a repeated failure.
---

# Diagnose

Requires `artifact-runtime` and a live se-workflow store. Follow
[lifecycle.md](../lifecycle.md). Parent session writes records. The
repair itself is a `kind=repair` work-item dispatched by
`execute-phase`, not a second write path.

## Rules

- An observation is what failed. A diagnosis names the cause. "Test
  X failed" is an observation. "The debit runs outside the
  transaction" is a diagnosis.
- `diagnosis` `unresolved` escalates. It does not start a repair.
- The repair limit is 3 (`MAX_REPAIRS` in `lifecycle/loop.py`).
  Count existing `project:repair-attempt` records for the task
  subject before starting another repair. A matching
  `failure_signature` escalates even when the count is under 3.
- `failure_signature` is stable text: the criterion subject or
  integration conflict, plus the failing assertion, not a timestamp.
- After a repair is verified, write `repair-attempt`. `outcome` is
  `repaired`, `failed_again`, `unresolved`, or `escalated`.

## Steps

1. Read the failing check-runs, the integration-report, the
   execution-reports, the diff, the specification, the design, and
   prior repair attempts for this task.

```bash
adaptive-artifacts list --type project:check-run --subject <task-slug> --full
adaptive-artifacts list --type project:repair-attempt --subject <task-slug> --full
adaptive-artifacts list --type project:integration-report --where payload.phase=<phase-slug> --full
```

2. Record the observation first:

```bash
adaptive-artifacts create --type project:investigation-observation \
  --subject "<task-slug>" \
  --payload '{"source":"<cmd or log>","observed_time":"<iso>","environment":"<repo/rev>","what_was_observed":"<the failure, not the cause>","effort":"<effort-slug>"}'
```

3. If the limit or a repeated signature trips, or the cause is not
   known, escalate and stop. Set `stage` to `diagnose`.

```bash
adaptive-artifacts create --type project:finding \
  --subject "<task-slug>" \
  --payload '{"claim":"<unresolved or repeated failure>","basis":"<what was inspected>","invalidated_when":"<what would name the cause>","effort":"<effort-slug>","needs":"human"}' \
  --body "## Evidence

<observations>

## Consequence

<repair was not started>

## Follow-up

<what the user must decide>"

adaptive-artifacts create --type project:continuity-question \
  --subject "<effort-slug>" \
  --payload '{"owner":"user","blocking":true,"scope":"repair-limit:<phase-slug>"}'

adaptive-artifacts create --type project:repair-attempt \
  --subject "<task-slug>" \
  --payload '{"work_item":"<task-slug>","effort":"<effort-slug>","attempt":"<count>","failure_signature":"<signature>","outcome":"escalated","diagnosis":"unresolved"}'
```

4. When a cause is known and the limit allows a repair, write the
   finding with that cause (`needs` `none` unless a person must
   choose). Create a repair work-item that `depends_on` nothing new
   unless the fix must wait. `kind` is `repair`. `satisfies` repeats
   the criteria the failed task was responsible for. Put the cause
   in the body. Then `execute-phase` for that task only.

```bash
adaptive-artifacts create --type project:work-item \
  --subject "<task-slug>-repair-<n>" \
  --payload '{"title":"Repair <task>","phase":"<phase-slug>","kind":"repair","assignee":"","effort":"<effort-slug>","executor":"subagent","satisfies":"spec-<phase-slug>-<criterion>"}' \
  --body "## Description

<cause, and the change that removes it>

## Approach

<implementation recipe>"
```

   The repair returns through `integrate` (unless depth is
   `trivial`) and then `verify-work`. When that verification
   finishes, record the attempt:

```bash
adaptive-artifacts create --type project:repair-attempt \
  --subject "<task-slug>" \
  --payload '{"work_item":"<task-slug>","effort":"<effort-slug>","attempt":"1","failure_signature":"<signature>","outcome":"repaired","diagnosis":"<cause>"}'
```

   Use `failed_again` when verify fails again. The next diagnose
   sees that signature and escalates if it matches.

## Do not

- Repair from the test name alone
- Start a fourth repair
- Spawn a diagnose subagent when the parent holds the evidence
- Mark the original work-item `done` in this skill
