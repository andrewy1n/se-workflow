---
name: se-verify-work
description: >-
  Captures se-workflow check-run evidence and closes a work-item when
  its acceptance criterion passes (TDD, command check, or manual).
  Use when a task needs to be shown done, tests were run, or a subagent
  returned verification evidence.
---

# Verify work

Requires `artifact-runtime` and a live se-workflow store. If missing,
follow [ensure-store.md](../ensure-store.md). Parent session writes
records. Git/tests own the code; this skill owns the occurrence that a
criterion was tested.

`method` on `project:acceptance`: `tdd` | `check` | `manual`.

## Steps

1. Resolve the task `subject`, active `work-item`, and active
   `acceptance` (same subject). If a subagent already ran the check,
   trust its evidence only after you can point at a command, test name,
   or diff; re-run when cheap.
2. Run the criterion:
   - `tdd` — tests live in git. A first failing run is expected; capture
     it as `result=fail`, then implement, then capture `result=pass`.
     Do not record a `failed-attempt` for that first red.
   - `check` — run the stated command/tests.
   - `manual` — user-visible check; do not mark pass without evidence
     the user would accept.
3. `create --type project:check-run` with the same `subject`:

```bash
adaptive-artifacts create --type project:check-run \
  --subject "<task-slug>" \
  --payload '{"criterion_id":"<acceptance-record-id>","revision":"<git sha or dirty>","result":"pass"}' \
  --rel informed_by:<acceptance-record-id>
```

   Prefer `git rev-parse HEAD` after a commit. `dirty` is allowed for a
   failing TDD red. Passing `check`/`tdd` should be a real revision
   when possible.
4. On **pass**: supersede the work-item; keep `subject`; set `live=no`
   and leave other payload fields. That is "done" (current-claim has no
   completed state). The acceptance definition stays active.
5. On **fail** (not the intentional TDD red you will fix next): leave
   the work-item `in_progress`. Optionally create
   `project:continuity-question` with `blocking=true` if dispatch must
   stop.
6. On **abandoned** approach: `create --type project:failed-attempt`
   with `attempted_action` and `retry_when`. Do not set `live=no`
   unless the whole task is dropped; if dropped, supersede `live=no`
   the same way as pass.
7. Regenerate views (`handoff`, `project:plan`, `project:verification`)
   and `adaptive-artifacts validate`.

## Do not

- Dual-write CI as records if CI already owns the result
- Treat a checklist tick as pass without a `check-run`
- `update` a work-item to `superseded`
