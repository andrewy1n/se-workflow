---
name: execute-phase
description: >-
  Dispatches se-workflow work-items in waves to parallel subagents
  for the focused effort. Parent session writes records; subagents
  return evidence only. Use when the user asks to execute a phase,
  run ready work, or continue after engage.
---

# Execute the focused effort

Requires `artifact-runtime` and a live se-workflow store. If missing,
follow [ensure-store.md](../ensure-store.md) then `init` (if no goal
for the focus) and `plan-phase`. Follow
[kinds-and-focus.md](../kinds-and-focus.md). Follow `verify-work`
after each subagent returns.

The git-filesystem backend is **single-writer**. Only this parent
session may call `adaptive-artifacts`.

## Steps

1. `adaptive-artifacts hook-start` if views were not injected. Resolve
   **focus**. Read `project:plan` section `## <focus>` and blocking
   `continuity-question`s for that subject. Do not dispatch while a
   blocking question is open on this focus. Do not dispatch another
   effort's tasks.
2. Select active work-items with `live=yes`, `ready=yes`,
   `payload.effort` = focus (or missing `effort` only if this is the
   sole live goal). For `deliver` / `repair` / `evaluate`, also require
   `phase` = this subject's `current-position.payload.scope`. For
   `incidental`, `phase` is `"-"`. If none exist, stop and point to
   `plan-phase`.
3. Work in ascending `wave`. Within a wave, run independent tasks in
   parallel. Different waves stay serial.
4. For each task in the wave, **supersede** the work-item (copy
   payload, set `stage=in_progress`, `assignee` to a short subagent
   label). Use `--expected-revision` from `adaptive-artifacts get` or
   the create output. Keep `subject`, `kind`, `effort`, and `live=yes`.
5. Spawn one subagent per in-progress task (`Task` /
   `generalPurpose`). Give it only:

   - repo path, task `subject` / title, `kind`, focus `effort`
   - acceptance `criterion` and `method`
   - any `failed-attempt` and `investigation-observation` /
     `finding` records for that subject
   - kind-specific instruction:
     - `deliver` / `incidental` — implement the change
     - `repair` — reproduce, record observations, name a root cause
       if found, then fix; do not skip diagnose
     - `evaluate` — run the campaign; return metrics / comparison;
       do not “fix” the system unless the criterion says so
   - do **not** run `adaptive-artifacts`; do **not** edit
     `.artifacts/`; return the evidence block below

   Subagent return shape:

   ```
   subject: <task-slug>
   kind: deliver | repair | evaluate | incidental
   result: pass | fail | blocked | abandoned
   revision: <git sha or "dirty">
   evidence: <what was run>
   observations: <repair/evaluate: what was seen>
   root_cause: <repair, if known>
   verdict: pass | fail | delta | inconclusive
   metrics: <evaluate: baseline vs candidate>
   claim: <evaluate/repair finding text, if any>
   attempted_action: <only if abandoned>
   retry_when: <only if abandoned>
   blocker: <only if blocked>
   ```

6. When a subagent returns, run `verify-work` in this parent. Then
   supersede any still-live same-focus work-item that was waiting on
   it to `ready=yes` if its dependency is now done.
7. Next wave. When no live same-focus work-items remain in this phase
   (or the incidental task is closed), supersede **this subject's**
   `current-position` to say the phase is done and name the next
   phase title (omit for incidental). Do **not** materialize the next
   phase unless the user asks (`plan-phase`). Do not touch other
   subjects.
8. Regenerate views; `adaptive-artifacts validate`.

## Do not

- Write a plan document as authority
- Let subagents create/supersede records
- Dispatch `ready=no` work or another focus's work
- Load the whole store; route by focus, then phase
