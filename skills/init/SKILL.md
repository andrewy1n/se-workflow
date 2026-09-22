---
name: init
description: >-
  Adopts the current git repo into the se-workflow store: contract,
  live goal, current phase, and later phase titles only. Does not
  write work-items or a plan document. Use when starting
  this workflow on an existing or empty project, when adding a new
  effort subject, or when handoff has no goal or position.
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
- Interview for orientation, not an executable multi-phase plan.
- Later phases: titles only. No success criteria, deps, or work-items
  for phases that are not current.
- Existing docs (README, git log, other project docs) are input.
  Confirm with the user before writing records. Do not ingest them
  as replicas.
- Current-claims change via `supersede` (new id), never `update` to
  `superseded`, never payload-only `update`.
- Parent writes records. Do not spawn subagents here.
- Several live goals may exist. A new effort is a new `subject`.
  Never supersede another subject's goal or position.

## Steps

1. Follow ensure-store. If cwd is not git, stop after saying so.
2. `adaptive-artifacts hook-start` if views were not injected.
3. Resolve **focus** (effort slug). If live goals already exist, show
   them. Keep them unless the user is replacing **that** subject.
   Adding work is a new subject or an existing one they named — not a
   rewrite of a different goal.
4. Read cheap local evidence only: README, recent `git log`, existing
   docs. Treat them as proposals, not authority.
5. Propose, then confirm (do not invent a product plan):
   - **focus** — effort slug
   - **kind** — `deliver` | `repair` | `evaluate` | `incidental`
   - **goal** — live outcome of this effort
   - **current phase** — name only; use `"-"` for incidental
   - **later titles** — ordered list, or none if unknown
   - **blocking unknown** — only if dispatch or resume cannot proceed
   - **durable decisions** — already-made choices; skip trivia
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

7. Create `project:current-position` on the same subject. `scope` is
   the current phase name (`"-"` if incidental). `position` is where
   we are, including remaining phase titles only (not a plan). If a
   position already exists **for this subject**, supersede it with
   `--expected-revision`. Do not touch other subjects.

```bash
adaptive-artifacts create --type project:current-position \
  --subject "<effort-slug>" \
  --payload '{"position":"<now; later: title, title>","scope":"<current-phase>"}'
```

8. For each confirmed durable decision: `create --type project:decision`
   with `choice`, `alternatives`, `rationale`, `phase`, `effort` (focus).
9. For each confirmed blocker: `create --type project:continuity-question`
   with `subject` = focus, `owner`, `blocking` true/false, `scope`.
10. Do **not** capture `work-item` or `acceptance`.
11. Regenerate views; validate:

```bash
adaptive-artifacts handoff --out views/handoff.md
adaptive-artifacts view --id project:plan --out views/plan.md
adaptive-artifacts validate
```

12. Show the user: focus, kind, goal, current phase, later titles, any
    blockers. Next is `plan-phase` when they want tasks for this focus.

## Do not

- Materialize future phases as work-items
- Write a roadmap document
- Run research or planner subagents
- Overlay a foreign `.artifacts/` contract
- Supersede another subject's live goal to “make room”
