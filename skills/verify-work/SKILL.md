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
   focus (or the sole-goal default). If a subagent already ran the
   check, trust its evidence only after you can point at a command,
   test name, diff, or metric table; re-run when cheap.
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
   with the same `subject`:

```bash
adaptive-artifacts create --type project:check-run \
  --subject "<task-slug>" \
  --payload '{"criterion_id":"<acceptance-record-id>","revision":"<git sha or dirty>","result":"pass","effort":"<effort-slug>","method":"tdd","signed_by":""}' \
  --rel informed_by:<acceptance-record-id>
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
8. Regenerate views (`handoff`, `project:plan`, `project:verification`)
   and `adaptive-artifacts validate`.

## Do not

- Dual-write CI as records if CI already owns the result
- Treat a checklist tick as pass without a `check-run` (binary) or
  a `finding` (comparative)
- Put a metric table in `check-run.result`
- Leave a `manual` check-run's `signed_by` empty once someone actually
  reviewed it — sign it, or it lingers under Unsigned Manual Check
- Transition a work-item to `done` on the strength of "red-first was
  probably followed" — nothing checks that; verify the actual command
  output for this task
- Close another focus's work-item
