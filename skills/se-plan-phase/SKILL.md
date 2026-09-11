---
name: se-plan-phase
description: >-
  Materializes only the current delivery phase as adaptive-artifacts
  work-item and acceptance records (not PLAN.md or GSD .planning/).
  Use when a project has the se-workflow design and the user finished a
  planning conversation, asked to start a phase, or asked to generate
  tasks for the current phase.
---

# Plan the current phase

Requires `artifact-runtime` and a live se-workflow store. If
`.artifacts/project-design.json` is missing or its `"project"` is not
`se-workflow`, stop and run `scripts/plant.sh` from `~/se-workflow`
(or tell the user to). Do not invent a parallel plan file.

Skip this skill for a one-shot task that fits in the current chat.

## Rules

- Records plus the derived `project:plan` view are the plan authority.
- Materialize **this phase only**. Future phases: titles in
  `current-position`, no work-items.
- Same `subject` (task slug) for a work-item and its acceptance.
- `ready` is `"yes"` or `"no"`; `live` is `"yes"` while the task is open;
  `stage` is `planned` until dispatch. `wave` is an integer; same wave
  may run in parallel.
- Current-claims change via `supersede` (new id), never `update` to
  `superseded`, never payload-only `update`.
- One `capture --bundle project:specified-work` per task (bundle allows
  one of each type).
- Parent writes records. Do not spawn subagents here.

## Steps

1. Read views if not already in context:
   `adaptive-artifacts hook-start`
2. Name the current phase. If several remain, pick with the user unless
   they already named it.
3. Create or supersede `project:active-goal` (effort outcome) and
   `project:current-position` (`scope` = current phase name; `position`
   includes remaining phase titles only).
4. For each durable choice from planning, `create --type project:decision`
   with `choice`, `alternatives`, `rationale`, `phase`. Skip trivia.
5. For each task in **this** phase:

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
      "live": "yes"
    }
  },
  {
    "type": "project:acceptance",
    "subject": "<task-slug>",
    "payload": {
      "criterion": "<observable done-check>",
      "method": "tdd",
      "phase": "<current-phase>"
    }
  }
]
EOF
)"
```

   `method` is `tdd`, `check`, or `manual`. Set `ready` to `"no"` when
   another **current-phase** task must finish first; put later parallel
   groups in a higher `wave`.
6. Regenerate views:

```bash
adaptive-artifacts handoff --out views/handoff.md
adaptive-artifacts view --id project:plan --out views/plan.md
adaptive-artifacts validate
```

7. Show the user the current-phase task list (slug, wave, ready,
   acceptance). Do not execute unless they ask (`se-execute-phase`).
