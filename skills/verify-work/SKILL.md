---
name: verify-work
description: >-
  Captures se-workflow check-run and finding evidence and closes a
  work-item's lifecycle when its acceptance criterion is met. Use when
  a task needs to be shown done, a campaign was run, a bug was
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
5. On **pass** (binary gate met, or evaluate finding accepted as
   done): transition the work-item to `done`:

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
6. On **fail** (not the intentional TDD red you will fix next): leave
   the work-item `in_progress`. Optionally create
   `project:continuity-question` on the **focus** subject with
   `blocking=true` if dispatch must stop.
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

`close` is steps 3-5 above, executed as one write instead of one
`create`/`update` per criterion — use it once every active acceptance
for this work-item has been judged (step 3) and any diagnose/eval
records from step 2 are already written. It still leaves `in_progress`
on a `fail` (step 6) or drives `withdrawn` (step 7) — `close` only
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
