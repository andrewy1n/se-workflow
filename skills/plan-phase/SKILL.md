---
name: plan-phase
description: >-
  Materializes the current effort's work-item and acceptance records
  (this phase only, or a single incidental task). Use when the user
  finished a planning conversation, engage handed off here, or they
  asked to generate tasks for the focused effort.
---

# Plan the current effort

Requires `artifact-runtime` and `adaptive-artifacts` on PATH. Follow
[ensure-store.md](../ensure-store.md) in the **current work repo**
before writing records. Follow [kinds-and-focus.md](../kinds-and-focus.md).
Do not copy this plugin into the project.

Skip this skill for incidental work that fits in the current chat and
is not an interrupt. If handoff has no goal for the focus and the
user is not ready to specify tasks, use `init` first (`engage` if
kind/focus are unset).

## Rules

- Records plus the derived `project:plan` view are the plan authority.
- Materialize **this focus** only. For `deliver` / `repair` /
  `evaluate`, materialize **this phase only**. Future phases: titles
  in this subject's `current-position`, no work-items.
- Same `subject` (task slug) for a work-item and its acceptance.
  `payload.effort` is the focus on both.
- `kind` on each work-item. `ready` is `"yes"` or `"no"`; `live` is
  `"yes"` while the task is open; `stage` is `planned` until dispatch.
  `wave` is an integer; same wave may run in parallel.
- Incidental: one task, `phase="-"`, `wave` 1, new focus subject.
- Current-claims change via `supersede` (new id), never `update` to
  `superseded`, never payload-only `update`.
- One `capture --bundle project:specified-work` per task (bundle allows
  one of each type).
- Parent writes records. Do not spawn subagents here.
- Never supersede another subject's goal or position.

## Steps

1. Read views if not already in context:
   `adaptive-artifacts hook-start`
   Resolve **focus** and **kind**. Use the `## <focus>` plan section.
2. If this focus has no `active-goal` / `current-position`, create
   them (`init` steps 6–7) for **this subject only**. If they exist,
   supersede only when the user is changing **this** effort's goal or
   phase. `current-position.payload.scope` is the phase name (`"-"`
   if incidental). `position` includes remaining phase titles only.
3. For each durable choice from planning, `create --type project:decision`
   with `choice`, `alternatives`, `rationale`, `phase`, `effort`.
   Skip trivia.
4. For each task in **this** phase (or the one incidental task):

```bash
adaptive-artifacts capture --bundle project:specified-work --records "$(cat <<'EOF'
[
  {
    "type": "project:work-item",
    "subject": "<task-slug>",
    "payload": {
      "title": "<short title>",
      "phase": "<current-phase>",
      "wave": 1,
      "ready": "yes",
      "assignee": "",
      "stage": "planned",
      "live": "yes",
      "kind": "deliver",
      "effort": "<effort-slug>"
    }
  },
  {
    "type": "project:acceptance",
    "subject": "<task-slug>",
    "payload": {
      "criterion": "<observable done-check>",
      "method": "tdd",
      "phase": "<current-phase>",
      "effort": "<effort-slug>"
    }
  }
]
EOF
)"
```

   Set `kind` and `phase` from the effort (`phase` is `"-"` when
   incidental). `method` is `tdd`, `check`, or `manual`.

   - `repair` — criterion is repro-gone plus a regression check, not
     “we investigated.” Diagnose happens at execute/verify.
   - `evaluate` — criterion is the campaign (suite, comparison).
     Binary gate → `method=check`. Comparative / inconclusive lives
     in a finding at verify, not in `method`.
   - `incidental` — one observable done-check; usually `check` or
     `manual`.

   Set `ready` to `"no"` when another **same-focus, current-phase**
   task must finish first; put later parallel groups in a higher
   `wave`.
5. Regenerate views:

```bash
adaptive-artifacts handoff --out views/handoff.md
adaptive-artifacts view --id project:plan --out views/plan.md
adaptive-artifacts validate
```

6. Show the user the focus task list (slug, kind, wave, ready,
   acceptance). Do not execute unless they ask (`execute-phase`).
