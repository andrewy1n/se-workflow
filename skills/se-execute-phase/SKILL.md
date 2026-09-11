---
name: se-execute-phase
description: >-
  Dispatches se-workflow work-items in waves to parallel subagents.
  Parent session writes records; subagents return verification evidence
  only. Use when a project has the se-workflow design and the user asks
  to execute a phase, run tasks in parallel, or continue ready work.
---

# Execute the current phase

Requires `artifact-runtime` and a live se-workflow store (`"project":
"se-workflow"` in `.artifacts/project-design.json`). If missing, plant
from `~/se-workflow` and stop. Follow `se-verify-work` after each
subagent returns.

The git-filesystem backend is **single-writer**. Only this parent
session may call `adaptive-artifacts`.

## Steps

1. `adaptive-artifacts hook-start` if views were not injected. Read
   `project:plan` (current phase) and blocking `continuity-question`s.
   Do not dispatch while a blocking question is open.
2. Current phase = `current-position.payload.scope`. Select active
   work-items with `live=yes`, that `phase`, and `ready=yes`.
3. Work in ascending `wave`. Within a wave, run independent tasks in
   parallel. Different waves stay serial.
4. For each task in the wave, **supersede** the work-item (copy payload,
   set `stage=in_progress`, `assignee` to a short subagent label). Use
   `--expected-revision` from `adaptive-artifacts get` or the create
   output. Keep `subject` and `live=yes`.
5. Spawn one subagent per in-progress task (`Task` /
   `generalPurpose`). Give it only:

   - repo path and task `subject` / title
   - acceptance `criterion` and `method`
   - any `failed-attempt` records for that subject
   - instruction: implement in this repo; do **not** run
     `adaptive-artifacts`; do **not** edit `.artifacts/`; return the
     evidence block below

   Subagent return shape:

   ```
   subject: <task-slug>
   result: pass | fail | blocked | abandoned
   revision: <git sha or "dirty">
   evidence: <what was run>
   attempted_action: <only if abandoned>
   retry_when: <only if abandoned>
   blocker: <only if blocked>
   ```

6. When a subagent returns, run `se-verify-work` in this parent (capture
   `check-run`, supersede `live=no` on pass, etc.). Then supersede any
   still-live work-item that was waiting on it to `ready=yes` if its
   dependency is now done.
7. Next wave. When no live work-items remain in this phase, supersede
   `current-position` to say the phase is done and name the next phase
   title. Do **not** materialize the next phase unless the user asks
   (`se-plan-phase`).
8. Regenerate views; `adaptive-artifacts validate`.

## Do not

- Write `PLAN.md` or GSD `.planning/` as authority
- Let subagents create/supersede records
- Dispatch `ready=no` work
- Load the whole store; route by the current phase
