---
name: execute-phase
description: >-
  Dispatches se-workflow work-items whose derived.ready is true, in
  dependency order, to parallel subagents for the focused effort.
  Parent session writes records; subagents return evidence only. Use
  when the user asks to execute a phase, run ready work, or continue
  after engage.
---

# Execute the focused effort

Requires `artifact-runtime` and a live se-workflow store. If missing,
follow [ensure-store.md](../ensure-store.md) then `init` (if no goal
for the focus) and `plan-phase`. Follow
[kinds-and-focus.md](../kinds-and-focus.md). Follow `verify-work`
after each subagent returns.

The git-filesystem backend is **single-writer**. Only this parent
session may call `adaptive-artifacts`.

Task state is the work-item's lifecycle: `planned -> in_progress ->
done`, or `withdrawn`. Readiness (`derived.ready`) and wave
(`derived.wave`) are computed by the engine from the `depends_on`
graph at read time — this skill never writes either.

## Steps

1. `adaptive-artifacts hook-start` if views were not injected. Resolve
   **focus**. Read `project:plan` section `## <focus>` and blocking
   `continuity-question`s for that subject. Do not dispatch while a
   blocking question is open on this focus. Do not dispatch another
   effort's tasks.
2. Select dispatchable work-items directly — `project:plan`'s rendered
   view does not carry `derived.ready`/`wave`, so query the store:

```bash
adaptive-artifacts list --type project:work-item --state planned \
  --where payload.effort=<focus> --where payload.phase=<current-phase-slug> \
  --where derived.ready=true
```

   For `incidental`, drop the `payload.phase` filter (its work-item
   has `phase=""`) and expect at most one result. `current-phase-slug`
   is the subject of the `project:phase` record for this effort whose
   `lifecycle_state` is `in_progress` (`list --type project:phase
   --state in_progress --where payload.effort=<focus>`) — never
   `current-position.payload.scope`, which stays fixed per subject and
   does not track the phase. If none exist, stop and point to
   `plan-phase`.
3. Group the results by `derived.wave` (each result carries it).
   Within a wave, run independent tasks in parallel. Do lower waves
   first; different waves stay serial. A wave number can shift between
   waves as earlier tasks finish — re-run the `list` above before each
   wave rather than trusting a wave computed earlier in this session.
4. For each task about to dispatch, transition it to `in_progress` and
   set `assignee` to a short subagent label. Fetch `--expected-revision`
   from the `list`/`get` output:

```bash
adaptive-artifacts update --type project:work-item --id <id> \
  --transition in_progress \
  --expected-revision <revision> \
  --payload '{"assignee":"<subagent-label>"}'
```

5. Spawn one subagent per in-progress task (`Task` /
   `generalPurpose`). Give it only:

   - repo path, task `subject` / title, `kind`, focus `effort`
   - the work-item's `## Description` body (`adaptive-artifacts get
     --type project:work-item --id <id>` — the body is in the record)
   - acceptance `criterion`, `method`, and `verify_command`
   - any `failed-attempt` and `investigation-observation` /
     `finding` records for that subject
   - kind-specific instruction:
     - `deliver` / `incidental` — implement the change
     - `repair` — reproduce, record observations, name a root cause
       if found, then fix; do not skip diagnose
     - `evaluate` — run the campaign; return metrics / comparison;
       do not "fix" the system unless the criterion says so
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
   needs_human: <true/false — if the verdict needs a maintainer call>
   attempted_action: <only if abandoned>
   retry_when: <only if abandoned>
   blocker: <only if blocked>
   ```

6. When a subagent returns, run `verify-work` in this parent. It
   transitions the work-item to `done` or `withdrawn`, or leaves it
   `in_progress` on fail/blocked. Do not supersede or re-derive
   anything yourself — a dependent task's `derived.ready` flips to
   `true` automatically the moment its dependency's lifecycle reaches
   its terminal success state; the next wave's `list` in step 3 will
   see it.
7. Next wave. When no `planned`/`in_progress` same-focus work-items
   remain in this phase (or the incidental task is closed), close the
   phase and update the position narrative. `current-position.scope`
   is a stable per-subject value — never change it here, and never put
   the next phase's slug into it; `supersede` rejects a successor whose
   `scope` differs from the predecessor's ("breaks identity
   continuity"). Which phase is current is derived by querying
   `project:phase` state, not read off this record:

```bash
adaptive-artifacts update --type project:phase --id <phase-id> \
  --transition done --expected-revision <revision>

adaptive-artifacts supersede --type project:current-position --id <id> \
  --expected-revision <revision> \
  --payload '{"position":"<phase-slug> done; next up: <next-phase-slug>","scope":"<unchanged from predecessor>","effort":"<focus>"}'
```

   Skip both for incidental. Do **not** materialize the next phase's
   tasks unless the user asks (`plan-phase` promotes it). Do not touch
   other subjects.
8. Regenerate views; `adaptive-artifacts validate`.

## Do not

- Write a plan document as authority
- Let subagents create/supersede/transition records
- Dispatch a work-item whose `derived.ready` is `false`, or another
  focus's work
- Write or recompute `ready`/`wave` — they are derived; re-query them
- Load the whole store; route by focus, then phase
