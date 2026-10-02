---
name: init
description: >-
  Adopts the current git repo into the se-workflow store: contract,
  live goal, and a project:phase record for every phase you can
  currently name. Does not write work-items or a plan document. Use
  when starting this workflow on an existing or empty project, when
  adding a new effort subject, or when handoff has no goal or
  position.
---

# Adopt this repo

Requires `artifact-runtime` and `adaptive-artifacts` on PATH. Follow
[ensure-store.md](../ensure-store.md) in the **current work repo**.
Follow [kinds-and-focus.md](../kinds-and-focus.md). Do not copy this
plugin into the project.

Skip this skill for incidental work that fits in the current chat.
If `engage` already named a new focus, use that subject here.
If the user already has this focus's tasks, use `plan-phase`.

## Rules

- Records plus derived views are the authority. Do not write a plan
  or roadmap file as authority.
- Interview for orientation, not an executable multi-phase plan. A
  phase record's body must have real content in every required
  section, but "not yet scoped" is real content for a phase that
  hasn't started — do not fabricate success criteria or dependencies
  for it.
- Every phase you can currently name gets a `project:phase` record,
  `planned`, ordinal in sequence. None of them start `in_progress`
  here — `plan-phase` promotes the one it's about to materialize work
  for. Incidental work gets **no** phase record at all.
- Existing docs (README, git log, other project docs) are input.
  Confirm with the user before writing records. Do not ingest them
  as replicas.
- Current-claims (`active-goal`, `current-position`, `decision`,
  `constraint`) change via `supersede` (new id), never `update` to
  `superseded`, never payload-only `update`. `project:phase` is a
  different trait (staged lifecycle) — it changes via `update
  --transition`, never `supersede`.
- Parent writes records. Do not spawn subagents here.
- Several live goals may exist. A new effort is a new `subject`, and
  needs a reason: no live goal covers this area. Never supersede
  another subject's goal or position.

## Steps

1. Follow ensure-store. If cwd is not git, stop after saying so.
2. `adaptive-artifacts hook-start` if views were not injected.
3. Resolve **focus** (effort slug). If live goals already exist, show
   them. Keep them unless the user is replacing **that** subject.
   If a live goal covers the same area, the work is a new phase there
   (`plan-phase`), not a new subject. Never rewrite a different goal.
   If a closed goal has this subject or covers the area, reopen it
   (kinds-and-focus) instead of creating a new goal.
4. Read cheap local evidence only: README, recent `git log`, existing
   docs. Treat them as proposals, not authority.
5. Propose, then confirm (do not invent a product plan):
   - **focus** — effort slug
   - **kind** — `deliver` | `repair` | `evaluate` | `incidental`
   - **goal** — live outcome of this effort
   - **phases** — ordered list of `{slug, title}`, current phase
     first; empty for incidental
   - **blocking unknown** — only if dispatch or resume cannot proceed
   - **durable decisions / constraints** — already-made choices or
     confirmed non-negotiables; skip trivia
   Ask only what is still missing after the proposal. If the user
   starts listing tasks or acceptance, stop and point to `plan-phase`.
6. Same `subject` for goal and position (the focus slug). Create
   `project:active-goal` for that subject only:

```bash
adaptive-artifacts create --type project:active-goal \
  --subject "<effort-slug>" \
  --payload '{"goal":"<live outcome>","scope":"<effort or repo>","kind":"deliver"}'
```

   `kind` is the effort kind from step 5.

7. For each phase in step 5's list (skip entirely for incidental),
   `create --type project:phase`, `ordinal` starting at 1. Give a
   later phase's Approach/Exit-criteria a short honest placeholder
   ("decide at plan-phase") rather than guessing detail — a plan-phase
   run for that phase will overwrite it. Use `--body-file` once the
   text is more than a couple of lines:

```bash
adaptive-artifacts create --type project:phase \
  --subject "<phase-slug>" \
  --payload '{"title":"<phase title>","ordinal":1,"effort":"<effort-slug>"}' \
  --body-file "<phase-body.md>"
```

   `<phase-body.md>` has `## Problem`, `## Approach`, `## Exit
   criteria` headings; every section needs non-empty text or the
   record is rejected.

8. Create `project:current-position` on the same subject as step 6.
   `scope` is a **stable** value for this subject (same convention as
   `active-goal.scope`, e.g. "effort or repo") — never the current
   phase slug. `supersede` (the only legal way to update an `active`
   current-claim) refuses a successor whose `payload.scope` differs
   from the predecessor's, so a `scope` that changes every phase makes
   this record un-updatable the moment the phase advances. `phase` is
   a required payload reference to a real `project:phase` subject —
   set it to the first phase from step 5's list (the one step 7 just
   created at `ordinal: 1`). That is a pointer for this record, not an
   authority: which phase is actually current is still derived by
   querying `project:phase` for this effort with
   `lifecycle_state=in_progress` (nothing is `in_progress` yet this
   early — `plan-phase` promotes it) — never read off this field.
   `position` is a short "where we are now" narrative (may name the
   current phase in prose) — do not restate the phase list, that's
   what the `project:phase` records are for. If a position already
   exists **for this subject**, supersede it with `--expected-revision`,
   keeping `scope` identical to the predecessor's and `phase` current.
   Do not touch other subjects.

```bash
adaptive-artifacts create --type project:current-position \
  --subject "<effort-slug>" \
  --payload '{"position":"<short now-statement>","scope":"<effort or repo>","effort":"<effort-slug>","phase":"<first-phase-slug>"}'
```

9. For each confirmed durable choice among alternatives,
   `create --type project:decision` with `choice`, `alternatives`,
   `phase`, `effort` payload and a body with `## Rationale` and
   `## Counter-argument` sections (both required, both non-empty —
   state the real counter-argument, not a strawman):

```bash
adaptive-artifacts create --type project:decision \
  --subject "<decision-topic>" \
  --payload '{"choice":"<adopted>","alternatives":"<a, b>","phase":"<phase-slug>","effort":"<effort-slug>"}' \
  --body-file "<decision-body.md>"
```

   For a confirmed constraint that is **not** a choice — no real
   alternative existed — use `project:constraint` instead, with a
   `## Basis` section:

```bash
adaptive-artifacts create --type project:constraint \
  --subject "<constraint-slug>" \
  --payload '{"statement":"<the constraint>","applies_to":"<what it binds>","effort":"<effort-slug>"}' \
  --body "## Basis

<why this is confirmed, not a choice>"
```

10. For each confirmed blocker: `create --type project:continuity-question`
    with `subject` = focus, `owner`, `blocking` true/false, `scope`.
11. Do **not** capture `work-item` or `acceptance`.
12. Regenerate views; validate:

```bash
adaptive-artifacts handoff --out views/handoff.md
adaptive-artifacts view --id project:plan --out views/plan.md
adaptive-artifacts validate
```

13. Show the user: focus, kind, goal, phase list (slug + title +
    lifecycle), any blockers. Next is `plan-phase` when they want tasks
    for the current phase.

## Do not

- Materialize future phases as work-items or full plans — a
  placeholder Problem/Approach/Exit-criteria body is enough
- Write a roadmap document
- Run research or planner subagents
- Overlay a foreign `.artifacts/` contract
- Supersede another subject's live goal to "make room"
- Transition any phase to `in_progress` here — that's `plan-phase`'s job
