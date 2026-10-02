---
name: execute-phase
description: >-
  Dispatches se-workflow work-items whose derived.ready is true, in
  dependency order, to parallel subagents for the focused effort,
  recording an assignment and execution-report per dispatch. Parent
  session writes records; subagents return evidence only. Use when
  the user asks to execute a phase, run ready work, or continue after
  engage.
---

# Execute the focused effort

Requires `artifact-runtime` and a live se-workflow store. If missing,
follow [ensure-store.md](../ensure-store.md) then `init` (if no goal
for the focus) and `plan-phase`. Follow
[kinds-and-focus.md](../kinds-and-focus.md). Follow `verify-work`
after each subagent returns.

The git-filesystem backend is **single-writer**. Only this parent
session may call `adaptive-artifacts` in any form that writes.
Subagents never do — not now (they have no store access) and not once
a `--read-only` executor mode exists elsewhere in this project: that
mode names what an executor may *read*, it does not make the store
multi-writer, and a subagent write would race this session's
`--expected-revision`.

Task state is the work-item's lifecycle: `planned -> in_progress ->
done`, or `withdrawn`. Readiness (`derived.ready`) and wave
(`derived.wave`) are computed by the engine from the `depends_on`
graph at read time — this skill never writes either.

Each dispatch is recorded, not hand-transcribed: a `project:assignment`
for what an executor was handed, an optional `project:assignment-amendment`
for any mid-flight correction, and a `project:execution-report` for
what came back, verbatim. The `project:brief` view — not the
assignment body — is what tells an executor its acceptance criteria,
findings, constraints, and position; an assignment carries only what
that view cannot: territory splits, concurrency warnings, and
operational orientation.

## Steps

1. `adaptive-artifacts hook-start` if views were not injected. Resolve
   **focus**. Read `project:plan` section `## <focus>` and blocking
   `continuity-question`s for that subject. Do not dispatch while a
   blocking question is open on this focus. A question whose `scope`
   is `plan-review:<phase-slug>` is the plan review gate: it blocks
   only that phase, and the user clears it by approving the plan. Do
   not dispatch another effort's tasks.
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
   `plan-phase`. Several may be `in_progress` (one chat per phase):
   use the one named in context, and ask if none is named.
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

   Regenerate the brief so it is current for this dispatch, then
   record the assignment. Its `## Orientation` body carries only what
   `project:brief` does not already say for this subject — territory
   splits between concurrent executors, concurrency warnings,
   operational orientation (paths, sandbox, tooling quirks). Do not
   restate `criterion`, `verify_command`, or finding text in it — that
   is what the brief view is for, and copying it in creates a second,
   staleness-prone copy of the same fact:

```bash
adaptive-artifacts view --id project:brief --out views/brief.md

adaptive-artifacts create --type project:assignment \
  --subject "<task-slug>" \
  --payload '{"work_item":"<task-slug>","executor":"<subagent-label>","effort":"<focus>"}' \
  --body "## Orientation

<territory split / concurrency warning / operational context only>"
```

5. Spawn one subagent per in-progress task (`Task` /
   `generalPurpose`). Give it only:

   - repo path, task `subject` / title, `kind`, focus `effort`
   - the `## <task-slug>` section of `views/brief.md` (work-item body,
     acceptance, findings, constraints, position, and any prior
     amendments) — verbatim, not retyped
   - the assignment's `## Orientation` body from step 4
   - kind-specific instruction:
     - `deliver` / `incidental` — implement the change
     - `repair` — reproduce, record observations, name a root cause
       if found, then fix; do not skip diagnose
     - `evaluate` — run the campaign; return metrics / comparison;
       do not "fix" the system unless the criterion says so
   - do **not** run `adaptive-artifacts` in any form that writes — that
     holds even once a `--read-only` mode exists for executors; do
     **not** edit `.artifacts/`; return the evidence block below

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

6. If the assignment's terms turn out wrong or incomplete while the
   subagent is still working — a change to what it was told, not a
   status ping — send the correction to the subagent directly (it
   cannot read the store to pick up a change) and record it, so it
   survives past the chat transcript:

```bash
adaptive-artifacts create --type project:assignment-amendment \
  --subject "<task-slug>" \
  --payload '{"assignment":"<task-slug>","effort":"<focus>"}' \
  --body "## Correction

<the correction, as sent to the executor>"
```

7. When a subagent returns, record its evidence before judging it —
   the returned block is the record, not raw material for this
   session to hand-pick fragments from:

```bash
adaptive-artifacts create --type project:execution-report \
  --subject "<task-slug>" \
  --payload '{"work_item":"<task-slug>","assignment":"<task-slug>","result":"<pass|fail|blocked|abandoned>","verdict":"<pass|fail|delta|inconclusive>","revision":"<git sha or dirty>"}' \
  --body "<the subagent's full returned evidence block, verbatim>"
```

   Then run `verify-work` in this parent. It derives
   `investigation-observation` / `finding` / `check-run` records from
   this execution-report — not from this session's memory of the chat
   — and transitions the work-item to `done` or `withdrawn`, or leaves
   it `in_progress` on fail/blocked. Do not supersede or re-derive
   anything yourself — a dependent task's `derived.ready` flips to
   `true` automatically the moment its dependency's lifecycle reaches
   its terminal success state; the next wave's `list` in step 3 will
   see it.
8. Next wave. When no `planned`/`in_progress` same-focus work-items
   remain in this phase (or the incidental task is closed), close the
   phase, close its phase position (`subject` = phase slug) with
   `status: closed`, and update the effort position narrative
   (`subject` = focus). `current-position.scope`
   is a stable per-subject value — never change it here, and never put
   the next phase's slug into it; `supersede` rejects a successor whose
   `scope` differs from the predecessor's ("breaks identity
   continuity"). `phase` is a required payload reference to a real
   `project:phase` subject — set it to the next phase this narrative
   names, but that is a pointer, not the authority: which phase is
   current is still derived by querying `project:phase` state, not
   read off this record:

```bash
adaptive-artifacts update --type project:phase --id <phase-id> \
  --transition done --expected-revision <revision>

adaptive-artifacts supersede --type project:current-position --id <phase-position-id> \
  --expected-revision <revision> --payload '{"status":"closed"}'

adaptive-artifacts supersede --type project:current-position --id <effort-position-id> \
  --expected-revision <revision> \
  --payload '{"position":"<phase-slug> done; next up: <next-phase-slug>","scope":"<unchanged from predecessor>","effort":"<focus>","phase":"<next-phase-slug>"}'
```

   Skip all three for incidental. Another chat may have just closed a
   different phase; on a revision conflict, re-read the effort position
   and retry. Do **not** materialize the next phase's
   tasks unless the user asks (`plan-phase` promotes it). Do not touch
   other subjects.

   If no `planned` or `in_progress` phase is left for this effort, ask
   the user whether more phases follow. If yes, stop; `plan-phase`
   adds the next one. If no, close the effort: supersede its goal and
   position with `status: closed` (`supersede` merges the payload, so
   the other fields carry over). Closed efforts drop out of handoff,
   brief and the dashboard:

```bash
adaptive-artifacts supersede --type project:active-goal --id <goal-id> \
  --expected-revision <revision> --payload '{"status":"closed"}'

adaptive-artifacts supersede --type project:current-position --id <position-id> \
  --expected-revision <revision> --payload '{"status":"closed"}'
```

   To reopen an effort, supersede the goal with `status: open`.
9. Regenerate views (including `project:brief`); `adaptive-artifacts validate`.

## Do not

- Write a plan document as authority
- Let subagents create/supersede/transition records, in any current or
  future executor mode — the store is single-writer regardless of what
  an executor is allowed to read
- Restate acceptance criteria, verify commands, or finding text inside
  an assignment's `## Orientation` — that duplicates a fact
  `project:brief` already carries, and goes stale the moment its
  source does
- Skip the `project:execution-report` and derive check-runs straight
  from chat memory of what a subagent said
- Dispatch a work-item whose `derived.ready` is `false`, or another
  focus's work
- Write or recompute `ready`/`wave` — they are derived; re-query them
- Load the whole store; route by focus, then phase
