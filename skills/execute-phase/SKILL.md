---
name: execute-phase
description: >-
  Dispatches se-workflow work-items whose derived.ready is true, in
  dependency order, each wave inline in this session or as one
  subagent per task, recording an assignment and execution-report
  per dispatch. Parent session writes records; subagents return
  evidence only. Use when the user asks to execute a phase, run
  ready work, or continue after engage.
---

# Execute the focused effort

Requires `artifact-runtime` and a live se-workflow store. If missing,
follow [ensure-store.md](../ensure-store.md) then `init` (if no goal
for the focus) and `plan-phase`. Follow
[kinds-and-focus.md](../kinds-and-focus.md). Follow `verify-work`
after each task finishes, whether a subagent returned or this
session just implemented it inline.

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

   After plan review is answered and before the first wave, read
   `## Landing` from the phase body:

```bash
adaptive-artifacts get --type project:phase --id <phase-id>
```

   When `## Landing` is present, create branch `phase/<phase-slug>`
   from base `main` if that branch is missing, and add the worktree
   `<repo-parent>/<repo-name>--<phase-slug>` if that path is missing.
   The primary checkout is the checkout that stays on `main` and
   receives store writes; it is not the phase worktree.

```bash
git branch phase/<phase-slug> main
git worktree add <repo-parent>/<repo-name>--<phase-slug> phase/<phase-slug>
```

   Inline work runs in that directory. Each subagent is given the
   worktree absolute path and code writes only under the worktree.
   The parent keeps store writes on the primary checkout and writes
   `.artifacts` only on the primary checkout. The phase branch commit
   excludes `.artifacts`.

   When the phase body has no Landing section, keep the current
   checkout and do not create a branch: a missing Landing section
   stays in the current checkout. Incidental work stays in the
   current checkout too.
3. Group the results by `derived.wave` (each result carries it).
   Do lower waves first; different waves stay serial. A wave number
   can shift between waves as earlier tasks finish — re-run the
   `list` above before each wave rather than trusting a wave computed
   earlier in this session.

   When dispatching a wave, read `payload.executor` on each ready
   task. Missing or empty means `subagent`. Resolve that before
   comparing. The values are `inline` and `subagent`. If the tasks
   in the wave disagree, stop and name them. Do not spawn anything.
   Do not transition those tasks. If `payload.executor` is set to
   anything other than `inline` or `subagent`, stop and name that
   task. Do not spawn anything.

   The brief already carries the work-item body. Follow `## Approach`
   in that body. Do not ask the user for an implementation recipe
   when `## Approach` is present. The parent remains the only writer.
4. When the wave agrees on one executor, transition each task about
   to dispatch to `in_progress` and set `assignee`. For `subagent`,
   `assignee` is a short subagent label. For `inline`, `assignee` is
   `inline`, because this session runs the task. The assignment's
   `executor` is that assignee — who was handed the work — while the
   work-item's `payload.executor` is only the wave mode. Fetch
   `--expected-revision` from the `list`/`get` output:

```bash
adaptive-artifacts update --type project:work-item --id <id> \
  --transition in_progress \
  --expected-revision <revision> \
  --payload '{"assignee":"<assignee>"}'
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
  --payload '{"work_item":"<task-slug>","executor":"<assignee>","effort":"<focus>"}' \
  --body "## Orientation

<territory split / concurrency warning / operational context only>"
```

5. Dispatch the wave by that shared `payload.executor`.

   `subagent` keeps the current dispatch: one `generalPurpose`
   subagent per task, in parallel within the wave (`Task` /
   `generalPurpose`). Give each only:

   - repo path — the worktree absolute path
     `<repo-parent>/<repo-name>--<phase-slug>` when `## Landing` is
     present, otherwise the current checkout — task `subject` /
     title, `kind`, focus `effort`
   - the `## <task-slug>` section of `views/brief.md` (work-item body,
     acceptance, findings, constraints, position, and any prior
     amendments) — verbatim, not retyped
   - when a specification exists, its body and the acceptance
     subjects in this task's `satisfies` field — verbatim
   - when a design exists and its weight is not `skipped`, its
     interfaces, invariants, and constraints — verbatim
   - the assignment's `## Orientation` body from step 4
   - kind-specific instruction:
     - `deliver` / `incidental` — implement the change
     - `repair` — reproduce, record observations, name a root cause
       if found, then fix; do not skip diagnose
     - `evaluate` — run the campaign; return metrics / comparison;
       do not "fix" the system unless the criterion says so
   - follow `## Approach` in the work-item body; do not ask the user
     for an implementation recipe when that section is present
   - do **not** run `adaptive-artifacts` in any form that writes — that
     holds even once a `--read-only` mode exists for executors; do
     **not** edit `.artifacts/`; return the evidence block below

   `inline` does not spawn a subagent. This session implements the
   task, then still writes the execution-report and runs
   `verify-work` in step 7 — not twice. When `## Landing` is
   present, that implementation runs in the worktree. Use the same
   brief section,
   orientation, and kind-specific instruction a subagent would have
   been given. Follow `## Approach`. Fill the evidence block below
   in this session.

   Evidence block (what a subagent returns, or what this session
   records after an inline task):

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

6. If the assignment's terms turn out wrong or incomplete while a
   `subagent` task is still working — a change to what it was told,
   not a status ping — send the correction to that subagent directly
   (it cannot read the store to pick up a change) and record it, so
   it survives past the chat transcript. An `inline` task has no
   separate executor to message; record the same amendment if the
   terms change, and keep implementing in this session:

```bash
adaptive-artifacts create --type project:assignment-amendment \
  --subject "<task-slug>" \
  --payload '{"assignment":"<task-slug>","effort":"<focus>"}' \
  --body "## Correction

<the correction, as sent to the executor>"
```

7. When a subagent returns, or when this session finishes an
   `inline` task, record the evidence block before judging it. That
   block is the record, not raw material for this session to
   hand-pick fragments from:

```bash
adaptive-artifacts create --type project:execution-report \
  --subject "<task-slug>" \
  --payload '{"work_item":"<task-slug>","assignment":"<task-slug>","result":"<pass|fail|blocked|abandoned>","verdict":"<pass|fail|delta|inconclusive>","revision":"<git sha or dirty>"}' \
  --body "<the evidence block, verbatim>"
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
   remain in this phase (or the incidental task is closed), check the
   phase gate before closing anything. An empty task list is not proof
   the phase is done:

```bash
adaptive-artifacts list --type project:work-item \
  --where payload.effort=<focus> --where payload.phase=<phase-slug>

adaptive-artifacts list --type project:acceptance \
  --where payload.effort=<focus> --where payload.phase=<phase-slug>

adaptive-artifacts list --type project:check-run \
  --where payload.criterion_id=<acceptance-id> --order-by recorded_at
```

   The gate holds only when all of these are true:
   - The phase's verification task (the work-item that `depends_on`
     every other phase work-item) exists and is `done`.
   - Every active phase acceptance has a check-run, and the latest
     check-run per `criterion_id` has a passing `result`.
   - Every `method=manual` latest check-run has `signed_by` set.
   - When depth is `full`, or a wave ran more than one task, the
     latest `project:integration-report` for the phase has `verdict`
     `pass`. Run `integrate` before this check. A git merge that
     succeeds is not that verdict. `trivial` depth and a serial
     `standard` phase skip the report.
   - No `project:uncertainty` for this effort has `status` `open`.
     A check-run `verdict` of `unknown` is not a passing result.

   If the gate does not hold, leave the phase `in_progress`. Tell the
   user which criterion has no check-run, a failing latest check-run,
   or no signature, or that the verification task is missing. Then
   stop. Do not close the phase to move on. `deliver` and `repair`
   phases always need the verification task. Skip the gate for
   incidental work.

   When the gate holds and `## Landing` is present, commit the phase
   branch from the worktree. That commit excludes `.artifacts`. From
   the primary checkout, merge into `main`, then commit the store on
   `main`. The store commit on the primary checkout follows the phase
   close below. When Landing names push as a human stop, stop before
   pushing and ask. Push only as a human stop: push only when it is a
   human stop. Otherwise do not push. When `## Landing` is absent,
   skip the branch commit, the merge, and the store commit.

```bash
git -C <repo-parent>/<repo-name>--<phase-slug> add -A -- . ':!.artifacts'
git -C <repo-parent>/<repo-name>--<phase-slug> commit -m "<phase-slug>"
git -C <primary-checkout> merge phase/<phase-slug>
```

   Then close the phase, close its phase position
   (`subject` = phase slug) with `status: closed`, and update the
   effort position narrative (`subject` = focus). `current-position.scope`
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

   Then commit the store on `main` from the primary checkout, only
   when `## Landing` was present:

```bash
git -C <primary-checkout> add -- .artifacts
git -C <primary-checkout> commit -m "<phase-slug> store"
```

   Skip all three for incidental. Also skip the phase-branch commit,
   the merge, and the store commit for incidental. Another chat may
   have just closed a different phase; on a revision conflict,
   re-read the effort position
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

   To reopen an effort later, see kinds-and-focus, Closing and
   reopening.
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
  from chat memory of what a subagent or this session reported
- Ask the user for an implementation recipe when `## Approach` is
  present
- Spawn a subagent for an `inline` task, or spawn anything when the
  wave's tasks disagree on `payload.executor`
- Dispatch a work-item whose `derived.ready` is `false`, or another
  focus's work
- Write or recompute `ready`/`wave` — they are derived; re-query them
- Load the whole store; route by focus, then phase
- Close a phase whose gate in step 8 does not hold
- Create a branch or worktree when the phase body has no Landing section
- Let code writes leave the worktree when `## Landing` is present
- Write `.artifacts` anywhere but the primary checkout, or include
  `.artifacts` in the phase branch commit
- Push unless Landing names push as a human stop
