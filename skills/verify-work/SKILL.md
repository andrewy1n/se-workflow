---
name: verify-work
description: >-
  Captures se-workflow check-run and finding evidence and closes a
  work-item when its acceptance criterion is met. Use when a task
  needs to be shown done, a campaign was run, a bug was diagnosed,
  or a subagent returned verification evidence.
---

# Verify work

Requires `artifact-runtime` and a live se-workflow store. If missing,
follow [ensure-store.md](../ensure-store.md). Follow
[kinds-and-focus.md](../kinds-and-focus.md). Parent session writes
records. Git/tests own the code; this skill owns the occurrence that
a criterion was tested and any diagnose/eval conclusion.

`method` on `project:acceptance`: `tdd` | `check` | `manual`.
`kind` on the work-item: `deliver` | `repair` | `evaluate` |
`incidental`.

## Steps

1. Resolve focus, the task `subject`, active `work-item`, and active
   `acceptance` (same subject). Confirm `payload.effort` is the focus
   (or the sole-goal default). If a subagent already ran the check,
   trust its evidence only after you can point at a command, test
   name, diff, or metric table; re-run when cheap.
2. Capture diagnose/eval facts **before** closing anything:

   - `repair` — for each useful observation, `create --type
     project:investigation-observation` with the task `subject` and
     `effort`. When a root cause is known, `create --type
     project:finding` (`claim`, `basis`, `invalidated_when`, `effort`).
   - `evaluate` — if the result is comparative, a delta, or
     inconclusive, `create --type project:finding` the same way.
     Do not encode that in `check-run.result`.

```bash
adaptive-artifacts create --type project:investigation-observation \
  --subject "<task-slug>" \
  --payload '{"source":"<cmd or log>","observed_time":"<iso>","environment":"<repo/rev>","what_was_observed":"<fact>","effort":"<effort-slug>"}'

adaptive-artifacts create --type project:finding \
  --subject "<task-slug>" \
  --payload '{"claim":"<cause or comparison>","basis":"<evidence>","invalidated_when":"<what would undo this>","effort":"<effort-slug>"}'
```

3. Run the binary criterion when `method` is `tdd` / `check` / a
   `manual` pass/fail, or when `evaluate` has a binary gate:

   - `tdd` — tests live in git. A first failing run is expected;
     capture it as `result=fail`, then implement, then capture
     `result=pass`. Do not record a `failed-attempt` for that first
     red.
   - `check` — run the stated command/tests.
   - `manual` — user-visible check; do not mark pass without evidence
     the user would accept.

   Skip `check-run` only when `evaluate` is inconclusive or purely
   comparative with no binary gate. A finding is then required; do
   **not** set `live=no` unless the user accepts that finding as done.

4. When a binary result exists, `create --type project:check-run`
   with the same `subject`:

```bash
adaptive-artifacts create --type project:check-run \
  --subject "<task-slug>" \
  --payload '{"criterion_id":"<acceptance-record-id>","revision":"<git sha or dirty>","result":"pass","effort":"<effort-slug>"}' \
  --rel informed_by:<acceptance-record-id>
```

   Prefer `git rev-parse HEAD` after a commit. `dirty` is allowed for
   a failing TDD red. Passing `check`/`tdd` should be a real revision
   when possible.
5. On **pass** (binary gate met, or evaluate finding accepted as
   done): supersede the work-item; keep `subject`, `kind`, `effort`;
   set `live=no` and leave other payload fields. That is "done"
   (current-claim has no completed state). The acceptance definition
   stays active.
6. On **fail** (not the intentional TDD red you will fix next): leave
   the work-item `in_progress`. Optionally create
   `project:continuity-question` on the **focus** subject with
   `blocking=true` if dispatch must stop.
7. On **abandoned** approach: `create --type project:failed-attempt`
   with `attempted_action`, `retry_when`, `effort`. Do not set
   `live=no` unless the whole task is dropped; if dropped, supersede
   `live=no` the same way as pass.
8. Regenerate views (`handoff`, `project:plan`, `project:verification`)
   and `adaptive-artifacts validate`.

## Do not

- Dual-write CI as records if CI already owns the result
- Treat a checklist tick as pass without a `check-run` (binary) or
  a `finding` (comparative)
- Put a metric table in `check-run.result`
- `update` a work-item to `superseded`
- Close another focus's work-item
