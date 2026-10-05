---
name: verify-work
description: >-
  Captures se-workflow check-run evidence, assesses what it means for
  each requirement, and closes a work-item when that criterion is met.
  Use when a task needs to be shown done, a campaign was run, a bug was
  diagnosed, or a subagent returned verification evidence.
---

# Verify work

Requires `artifact-runtime` and a live se-workflow store. If missing,
follow [ensure-store.md](../ensure-store.md). Follow
[kinds-and-focus.md](../kinds-and-focus.md). Parent session writes
records. Git/tests own the code; this skill owns the occurrence that
a criterion was tested and any diagnose/eval conclusion.

`method` on `project:acceptance`/`project:check-run`: `tdd` | `check`
| `manual`. `kind` on the work-item: `deliver` | `repair` | `evaluate`
| `incidental`. Task state is the work-item's **lifecycle** —
`in_progress -> done` or `withdrawn` — not a payload flag; there is no
`live` field.

Red-first (fail before you fix) is an **instruction-level** convention
followed by this skill and by subagents — the engine does not enforce
it. Nothing in the contract checks that a `check-run result=fail`
record exists before a `result=pass` one for the same criterion. Do
not claim otherwise to a user; if that ordering matters, it holds
because this skill's steps are followed in order, not because a
validator would catch skipping it.

Verify and assess are two steps. Verify asks what happened. Assess
asks what that evidence means and what happens next. A check-run has
no `level` and no `next`.

## Two modes

Decision two-modes. A phase with a `project:specification` is
structured work: verify, assess, then `project:release` with `state`
`ready` only when every requirement is verified. A phase with no
specification, and incidental work, skip assessment and release and
keep pass/fail check-runs. `kind` `incidental` is incidental work even
when a specification exists for some other phase.

```bash
adaptive-artifacts list --type project:specification --subject "<phase-slug>" --state active
```

No active specification for this phase means simple work. Do not write
`project:assessment` or `project:release` on that path.

## Steps

1. Resolve focus, the task `subject`, its active `work-item`
   (`in_progress`), and its `acceptance`(s). A task can have several
   acceptances sharing a suffixed subject (`<task-slug>`,
   `<task-slug>-<suffix>` — the `plan-phase` convention); fetch the
   whole family with `list --subject <task-slug>` (exact-or-prefix
   match), not `get` on a single id. Confirm `payload.effort` is the
   focus (or the sole-goal default). If a subagent ran the check, its
   evidence is the `project:execution-report` `execute-phase` created
   for that dispatch — read that record (`list --type
   project:execution-report --subject <task-slug>`, take the most
   recent), not this session's memory of the chat — and trust it only
   after you can point at a command, test name, diff, or metric table
   inside its body; re-run when cheap. There is no execution-report
   when this task was verified without a dispatch (e.g. done directly
   in this session) — skip straight to step 2 in that case.
2. Capture diagnose/eval facts **before** closing anything:

   - `repair` — for each useful observation, `create --type
     project:investigation-observation` with the task `subject` and
     `effort`. When a root cause is known, `create --type
     project:finding` with `--body-file`/`--body` carrying
     `## Evidence`, `## Consequence`, `## Follow-up` (all required,
     all non-empty).
   - `evaluate` — if the result is comparative, a delta, or
     inconclusive, `create --type project:finding` the same way. Do
     not encode that in `check-run.result`.

```bash
adaptive-artifacts create --type project:investigation-observation \
  --subject "<task-slug>" \
  --payload '{"source":"<cmd or log>","observed_time":"<iso>","environment":"<repo/rev>","what_was_observed":"<fact>","effort":"<effort-slug>"}'

adaptive-artifacts create --type project:finding \
  --subject "<task-slug>" \
  --payload '{"claim":"<cause or comparison>","basis":"<evidence>","invalidated_when":"<what would undo this>","effort":"<effort-slug>","needs":"human"}' \
  --body "## Evidence

<what was run/observed and its output>

## Consequence

<what this means for the task/decision it bears on>

## Follow-up

<what someone should do next, or \"none\">"
```

   `needs` is `human` when this finding needs a maintainer call before
   the task can close (it then surfaces in `handoff`'s Needs Human
   section), else `none`. If this finding overturns a prior
   `project:decision`, add `--rel contradicts:<decision-record-id>` to
   the `create` call above — `contradict` (the subcommand) only works
   on record types with `contradiction: separate_record`, which is
   `project:finding` itself, not the decision it's contradicting; a
   plain `create --rel contradicts:...` is the correct shape for
   finding-contradicts-decision.

## Verify

Verify asks what happened. Write check-runs here. Do not write
`level` or `next` on them.

3. Run the binary criterion when `method` is `tdd` / `check` / a
   `manual` pass/fail, or when `evaluate` has a binary gate:

   - `tdd` — tests live in git. A first failing run is expected;
     capture it as `result=fail`, then implement, then capture
     `result=pass`. Do not record a `failed-attempt` for that first
     red.
   - `check` — run the stated `acceptance.verify_command`.
   - `manual` — user-visible check; do not mark pass without evidence
     the user would accept, and plan to set `signed_by` (step 4) once
     they do.

   Skip `check-run` only when `evaluate` is inconclusive or purely
   comparative with no binary gate. A finding is then required; do
   **not** transition the work-item to `done` unless the user accepts
   that finding as done.
4. When a binary result exists, `create --type project:check-run`
   with the same `subject`. Add a second `--rel informed_by:` pointing
   at the execution-report from step 1 when one exists for this
   dispatch — omit it only when this task was verified without a
   subagent:

```bash
adaptive-artifacts create --type project:check-run \
  --subject "<task-slug>" \
  --payload '{"criterion_id":"<acceptance-record-id>","revision":"<git sha or dirty>","result":"pass","effort":"<effort-slug>","method":"tdd","signed_by":""}' \
  --rel informed_by:<acceptance-record-id> \
  --rel informed_by:<execution-report-id>
```

   Prefer `git rev-parse HEAD` after a commit. `dirty` is allowed for
   a failing TDD red. Passing `check`/`tdd` should be a real revision
   when possible. `signed_by` is the maintainer's name/handle once
   they've reviewed a `manual` check-run's evidence; leave it `""`
   only while still awaiting that review — a `method=manual` check-run
   with `signed_by=""` surfaces under `handoff`'s Unsigned Manual
   Check role and stays there until someone signs it. `tdd`/`check`
   results don't need a signer; leave `signed_by` `""` for those.

   That example is simple work: `result` is `pass` or `fail`, and the
   payload has no `requirement` and no `evidence_kind`. `result` is
   not a contract enum. Do not add one. On either path, `result` is
   `pass`, `fail`, `blocked`, or `insufficient`.

   - `pass` — the criterion was met. Evidence for that requirement
     only. A pass on one requirement does not verify another, and a
     pass of one `evidence_kind` does not cover a criterion that was
     not run.
   - `fail` — the criterion ran and was not met. It does not say the
     design is wrong. A failing concurrency test does not itself claim
     the design is wrong.
   - `blocked` — the check could not run.
   - `insufficient` — the criterion was not exercised.

   When the acceptance has `requirement`, the check-run payload
   includes that `requirement` and an `evidence_kind` from the contract
   enum (`unit`, `integration`, `acceptance`, `static`, `types`,
   `security`, `property`, `fuzz`, `review`, `runtime`, `other`). Still
   no `level` and no `next`:

```bash
adaptive-artifacts create --type project:check-run \
  --subject "<task-slug>" \
  --payload '{"criterion_id":"<acceptance-record-id>","revision":"<git sha or dirty>","result":"fail","effort":"<effort-slug>","method":"check","signed_by":"","requirement":"<requirement-id>","evidence_kind":"unit"}' \
  --rel informed_by:<acceptance-record-id> \
  --rel informed_by:<execution-report-id>
```

## Assess

Skip this section for simple work (a phase with no specification, and
incidental work). Structured work runs Assess after the check-runs and
before step 5.

Write one `project:assessment` per requirement the check-runs speak
to. Subject is `<phase-slug>-<requirement-id>`. The Reason section
names the cause in words. The check-run does not. Payload:
`requirement`, `status`, `level` (omit only when `status` is
`verified`), `next`, `confidence` (`high` when `verified`, otherwise
`low`), `phase`, `effort`, `missing` (what evidence is absent, or
empty). Body sections, all non-empty: `## Evidence`, `## Missing`,
`## Reason`.

List the active assessment for that subject. Create when there is
none. Supersede when one is active — `supersede` keeps the subject.
Compare with that previous assessment before choosing `level` (see
Evidence escalation below).

```bash
adaptive-artifacts list --type project:assessment --subject "<phase-slug>-<requirement-id>" --state active --full
```

Choose the first `next` from the evidence. Do not send every failure
to execute. Use the first row the evidence supports:

| Evidence | status | level | next |
|---|---|---|---|
| `failed` and the cause is the task's code | `failed` | `implementation` | `execute` |
| `failed` and the design cannot satisfy the requirement | `failed` | `design` | `design` |
| `failed` and no task covers the requirement | `failed` | `plan` | `plan` |
| `failed` and the requirement is ambiguous or contradicted | `failed` | `specification` | `specify` |
| integration-report `fail`, and a task must change | `failed` | `integration` | `execute` |
| integration-report `fail`, otherwise | `failed` | `integration` | `integrate` |
| `insufficient` (the criterion was not exercised) | `insufficient` | `verification` | `verify` |
| `level` `environment` or `unknown` | `blocked` | `environment` or `unknown` | `verify` |
| every check the requirement needs passed | `verified` | omit | `release` |

A row is `failed` when the check-run `result` is `fail` and the cause
column matches. Read the phase integration report before using the
integration rows:

```bash
adaptive-artifacts list --type project:integration-report --where payload.phase=<phase-slug> --full
```

`insufficient`: set `missing` to the absent check. Prefer the first
missing kind in this order: acceptance, integration, unit, property,
fuzz, review. A passing check-run of a different kind does not force
`status` `verified`.

`level` `environment` or `unknown`: the cause is the environment, or
the evidence does not say. Set `next` to `verify`. Do not set `next`
to `execute`. Open a blocking `project:continuity-question` and a
finding with `needs` `human` (the same two writes as a repeated
`specification` below). Leave the work-item `in_progress`.

`failed` and the cause is the task's code: `level` `implementation`,
`next` `execute`. Leave the work-item `in_progress`.

```bash
adaptive-artifacts create --type project:assessment \
  --subject "<phase-slug>-<requirement-id>" \
  --payload '{"requirement":"<requirement-id>","status":"failed","level":"implementation","next":"execute","confidence":"low","phase":"<phase-slug>","effort":"<effort-slug>","missing":""}' \
  --body "## Evidence

<check-runs for this requirement and their results>

## Missing

none

## Reason

<the cause in words: the task's code failed the requirement>"
```

Design, plan, and specification use the same create (or supersede)
shape with that row's `status`, `level`, `next`, and `confidence`
`low`. Integration uses `level` `integration` and `next` `execute`
when a task must change, otherwise `next` `integrate`.

```bash
adaptive-artifacts create --type project:assessment \
  --subject "<phase-slug>-<requirement-id>" \
  --payload '{"requirement":"<requirement-id>","status":"insufficient","level":"verification","next":"verify","confidence":"low","phase":"<phase-slug>","effort":"<effort-slug>","missing":"acceptance"}' \
  --body "## Evidence

<which checks ran and which did not>

## Missing

acceptance

## Reason

<the criterion was not exercised>"
```

```bash
adaptive-artifacts create --type project:assessment \
  --subject "<phase-slug>-<requirement-id>" \
  --payload '{"requirement":"<requirement-id>","status":"blocked","level":"environment","next":"verify","confidence":"low","phase":"<phase-slug>","effort":"<effort-slug>","missing":"<absent environment fact, or empty>"}' \
  --body "## Evidence

<the blocked check and the environment fact>

## Missing

<absent environment fact, or none>

## Reason

<environment or unknown; not the task's code>"
```

When `status` is `verified`, omit `level`. `next` is `release`.
`confidence` is `high`. `missing` is empty.

```bash
adaptive-artifacts create --type project:assessment \
  --subject "<phase-slug>-<requirement-id>" \
  --payload '{"requirement":"<requirement-id>","status":"verified","next":"release","confidence":"high","phase":"<phase-slug>","effort":"<effort-slug>","missing":""}' \
  --body "## Evidence

<the passing check-runs for this requirement>

## Missing

none

## Reason

<why the evidence is sufficient for this requirement>"
```

### Evidence escalation

Decision evidence-escalation. Compare this assessment with the
previous one for the same requirement. Stay at the same `level` only
when the new check-runs add evidence (a new `evidence_kind`, a
narrower failing case, or a cause that was unnamed and is now named)
or the previous cause is resolved. Otherwise raise one step on
`implementation` → `design` → `specification`, set `next` to that
stage (`design`, then `specify`), and say in Reason that the evidence
did not increase. Do not use a failure count. `plan` and `integration`
are chosen only when the evidence says so. They are not inserted under
a repeated implementation failure.

A repeat that adds no evidence raises `implementation` to `design`
only in that case. The first implementation failure still uses `next`
`execute`. When the new check-run adds an `evidence_kind`, names a
narrower failing case, or names a cause that was unnamed, supersede
and stay at `implementation` / `execute`. When the previous cause is
resolved and the requirement now passes, `status` is `verified` and
`level` is omitted — that is not a raise.

```bash
adaptive-artifacts supersede --type project:assessment --id <assessment-id> \
  --expected-revision <revision> \
  --payload '{"requirement":"<requirement-id>","status":"failed","level":"design","next":"design","confidence":"low","phase":"<phase-slug>","effort":"<effort-slug>","missing":""}' \
  --body "## Evidence

<previous check-runs and the new ones>

## Missing

none

## Reason

The evidence did not increase. <the same cause, still unnamed beyond the task's code>"
```

When `specification` repeats and the evidence still did not increase,
supersede again with `level` `specification` and `next` `specify`, and
say in Reason that the evidence did not increase. Do not raise further
and do not set `next` to `execute`. Open a blocking
`project:continuity-question` and a finding with `needs` `human`. The
same two writes cover `level` `environment` or `unknown`.

```bash
adaptive-artifacts create --type project:continuity-question \
  --subject "<effort-slug>" \
  --payload '{"owner":"user","blocking":true,"scope":"assess:<phase-slug>-<requirement-id>"}'

adaptive-artifacts create --type project:finding \
  --subject "<phase-slug>-<requirement-id>" \
  --payload '{"claim":"<requirement-id> needs a human: specification repeated without new evidence, or the level is environment or unknown","basis":"<the assessments and check-runs>","invalidated_when":"<a new evidence_kind, a named cause, or a human answer>","effort":"<effort-slug>","needs":"human"}' \
  --body "## Evidence

<the repeated assessment or the environment or unknown level>

## Consequence

<dispatch stays stopped>

## Follow-up

<what the human must answer>"
```

### Release

Decision release-ready. `ready` means the evidence is sufficient.
When every assessment for the phase is `verified`, create
`project:release` with `state` `ready`. Read the specification's
`requirements` and the active assessments for the phase; every
requirement id must have an active assessment whose `status` is
`verified`. Do not write `merged`, `deployed`, or any other state in
this skill. Do not deploy.

```bash
adaptive-artifacts list --type project:assessment --where payload.phase=<phase-slug> --state active --full

adaptive-artifacts create --type project:release \
  --subject "<phase-slug>" \
  --payload '{"state":"ready","phase":"<phase-slug>","effort":"<effort-slug>"}'
```

Leave the work-item `in_progress` when any assessment for its
requirements is not `verified`. Go to step 5 only when each of those
assessments is `verified`.

5. On **pass** (simple work: binary gate met, or evaluate finding
   accepted as done; structured work: Assess recorded `verified` for
   each requirement this work-item covers): transition the work-item
   to `done`:

```bash
adaptive-artifacts update --type project:work-item --id <id> \
  --transition done --expected-revision <revision>
```

   The acceptance definition stays `active` (it is a `definition`
   record, not part of the work-item's lifecycle).

   A work-item reaching `done` is not itself proof its criteria were
   met — the lifecycle state alone does not say whether verification
   happened, only that this session declared it over. If you are
   closing to `done` while the criterion's most recent `check-run`
   shows `result=fail` or no `check-run` exists at all (live
   verification deliberately deferred, an accepted risk, or similar),
   that is only legitimate as an explicit call, and it must leave a
   trace a reader can find without decoding "done" — `create --type
   project:finding` on the task subject with `needs":"human"` first,
   naming what was deferred and why, **before** the `update
   --transition done` above:

```bash
adaptive-artifacts create --type project:finding \
  --subject "<task-slug>" \
  --payload '{"claim":"<task-slug> closed done with an unmet or unverified criterion","basis":"<why it was closed anyway>","invalidated_when":"<what would undo this acceptance>","effort":"<effort-slug>","needs":"human"}' \
  --body "## Evidence

<the failing/missing check-run and why closing proceeded anyway>

## Consequence

<what remains unverified>

## Follow-up

<what someone should do to close the gap, or \"none\">"
```

   This surfaces under `handoff`'s Needs Human role so the gap is
   visible without anyone having to already suspect it.
6. On **fail** for simple work (not the intentional TDD red you will
   fix next): leave the work-item `in_progress`. Optionally create
   `project:continuity-question` on the **focus** subject with
   `blocking=true` if dispatch must stop. Structured work does not
   stop in this step: a `fail` is evidence for Assess, and Assess
   chooses `next`. Do not send every failure to execute.
7. On **abandoned** approach: `create --type project:failed-attempt`
   with `attempted_action`, `retry_when`, `effort`. If the whole task
   is dropped (not just this attempt), transition the work-item to
   `withdrawn` instead of `done`:

```bash
adaptive-artifacts update --type project:work-item --id <id> \
  --transition withdrawn --expected-revision <revision>
```

   Otherwise leave it `in_progress` for a retry.
8. Regenerate views (`handoff`, `project:plan`, `project:verification`,
   `project:brief`) and `adaptive-artifacts validate`.

## Close

`close` is the simple-work batch for steps 3-5 (a phase with no
specification, and incidental work). It skips assessment and release.
A result other than `pass` is already unmet there; do not route
`blocked` or `insufficient` through `close`. Structured work writes
each check-run with `requirement` and `evidence_kind`, then Assess.
`close` does not copy those fields. Use the simple-work batch once
every active acceptance for this work-item has been judged (step 3)
and any diagnose/eval records from step 2 are already written. It
still leaves `in_progress` on a `fail` (step 6) or drives `withdrawn`
(step 7) — `close` only
covers the `done` path, including the deliberate "done anyway" path
step 5 requires a `finding` for. It **enforces** that requirement
instead of merely stating it: it refuses to build the batch at all —
prints which criteria are unmet and writes nothing — when `transition`
is `done`, a criterion is unmet or was never checked, and no `finding`
was given. Do not hand-write the batch to route around a refusal.

Script path: `<plugin>/scripts/close_batch.py` (resolve `<plugin>` per
[ensure-store.md](../ensure-store.md)).

1. Fetch the active acceptances — superseded ones are retired
   definitions and must not be re-checked:

```bash
adaptive-artifacts list --type project:acceptance --subject "<task-slug>" --state active
```

2. Fetch the most recent execution-report for this dispatch (omit this
   and leave `execution_report_id` `null` below when this task was
   verified without one, per step 1 above):

```bash
adaptive-artifacts list --type project:execution-report --subject "<task-slug>" --full --order-by recorded_at
```

   Take the last entry — `recorded_at` sorts oldest first.
3. Judge each active acceptance exactly as step 3 above directs
   (`tdd`/`check`/`manual`, `revision` from `git rev-parse HEAD` once
   committed, `dirty` for a failing TDD red, `signed_by` for a
   reviewed `manual` check). Write a close-request JSON: `criteria`
   holds one entry per acceptance actually checked; `acceptance_ids`
   lists **every** active acceptance from step 1, checked or not, so
   the refusal check can see one that was skipped. Leave `finding`
   `null` when every criterion passed:

```bash
cat > /tmp/close-request.json <<'EOF'
{
  "subject": "<task-slug>",
  "effort": "<effort-slug>",
  "work_item_id": "<work-item-record-id>",
  "transition": "done",
  "execution_report_id": "<execution-report-record-id-or-null>",
  "acceptance_ids": ["<acceptance-id-1>", "<acceptance-id-2>"],
  "criteria": [
    {"criterion_id": "<acceptance-id-1>", "result": "pass", "method": "tdd", "revision": "<git sha or dirty>", "signed_by": ""},
    {"criterion_id": "<acceptance-id-2>", "result": "pass", "method": "check", "revision": "<git sha or dirty>", "signed_by": ""}
  ],
  "finding": null
}
EOF
```

   When closing anyway on an unmet/unverified criterion, `finding`
   carries exactly step 5's fields (`needs` is forced to `"human"`
   regardless of what is written here):

```bash
cat > /tmp/close-request.json <<'EOF'
{
  "subject": "<task-slug>",
  "effort": "<effort-slug>",
  "work_item_id": "<work-item-record-id>",
  "transition": "done",
  "execution_report_id": "<execution-report-record-id-or-null>",
  "acceptance_ids": ["<acceptance-id-1>"],
  "criteria": [
    {"criterion_id": "<acceptance-id-1>", "result": "fail", "method": "check", "revision": "<git sha or dirty>", "signed_by": ""}
  ],
  "finding": {
    "claim": "<task-slug> closed done with an unmet or unverified criterion",
    "basis": "<why it was closed anyway>",
    "invalidated_when": "<what would undo this acceptance>",
    "body": "## Evidence\n\n<the failing/missing check-run and why closing proceeded anyway>\n\n## Consequence\n\n<what remains unverified>\n\n## Follow-up\n\n<what someone should do to close the gap, or \"none\">"
  }
}
EOF
```

4. Build the batch:

```bash
python3 "<plugin>/scripts/close_batch.py" --input /tmp/close-request.json --out /tmp/close-batch.ndjson
```

   Exit `0` means the batch was written — run `apply` next. Exit `2`
   means refused (unmet/unverified criterion, no `finding`) — stderr
   names the criteria; go back to step 3, either resolve them or add
   the `finding`, and do **not** run `apply`. Exit `1` means the
   close-request JSON was malformed — fix it and retry.
5. Only after a `0` exit, apply the batch — one `project:check-run`
   per criterion (each `informed_by` both its acceptance and the
   execution-report), the `finding` if one was given, then the
   work-item transition, all in one process:

```bash
adaptive-artifacts apply /tmp/close-batch.ndjson
```

6. Regenerate views and validate as step 8 above.

## Do not

- Dual-write CI as records if CI already owns the result
- Treat a checklist tick as pass without a `check-run` (binary) or
  a `finding` (comparative)
- Transition a work-item to `done` on an unmet or unverified criterion
  without the `finding` from step 5 — a bare `done` must never be the
  only trace of that
- Put a metric table in `check-run.result`
- Leave a `manual` check-run's `signed_by` empty once someone actually
  reviewed it — sign it, or it lingers under Unsigned Manual Check
- Transition a work-item to `done` on the strength of "red-first was
  probably followed" — nothing checks that; verify the actual command
  output for this task
- Close another focus's work-item
- Skip `close_batch.py` and hand-assemble the `apply` NDJSON for a
  multi-criterion close — that is exactly the ad-hoc path that let a
  `done` work-item carry a failing check-run with no `finding` before
- Put `level` or `next` on a check-run
- Treat a failing concurrency test as a claim that the design is wrong
- Send every failure to `execute`
- Escalate by a failure count
- Insert `plan` or `integration` under a repeated implementation failure
- Write `project:release` with `state` other than `ready`, or deploy
- Write an assessment or a release for incidental work or a phase with
  no specification
