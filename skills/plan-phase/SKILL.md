---
name: plan-phase
description: >-
  Promotes the current phase and materializes the current effort's
  work-item and acceptance records (this phase only, or a single
  incidental task), with depends_on edges between tasks that must
  run in order. Use when the user finished a planning conversation,
  engage handed off here, or they asked to generate tasks for the
  focused effort.
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
  `evaluate`, materialize **this phase only**. Future phases stay
  `project:phase` records with placeholder bodies (from `init`) — no
  work-items for them yet.
- Same `subject` (task slug) for a work-item and its acceptance(s).
  `payload.effort` is the focus on both. `payload.phase` is the
  current phase's slug (must match a real `project:phase` subject —
  `validate` checks this against the whole store); `""` for incidental.
- A task can have several acceptance criteria. Give the first the
  task slug as `subject`; give any additional ones `<task-slug>-<short
  suffix>` (e.g. `checkout-fix-perf`). Two active records of the same
  type sharing one exact `subject` fail `validate` (the current-claim
  identity check has no scope field to distinguish them) — the suffix
  avoids the collision while `list --subject <task-slug>` (exact-or-
  prefix match) still finds the whole family. Do not pick a task slug
  that is itself a prefix of another task's slug in the same phase.
- Task state is the work-item's **lifecycle** — `planned` (default) ->
  `in_progress` -> `done`, or `withdrawn`. Never write `stage`, `live`,
  `ready`, or `wave` — they don't exist in this contract.
- Dependencies are `depends_on` **relationships**, set with `--rel
  depends_on:<work-item-id>` when a task in this phase can't start
  until another one finishes. `derived.ready` / `derived.wave` are
  computed by the engine from that graph at read time — never write
  them, and never hand-assign a wave number.
- `capture --bundle project:specified-work` cannot carry `--rel` (a
  bundle part is `{type, subject, payload, body}` only). Use the
  bundle for a task with no dependency; for a task that depends on
  another, `create` its work-item directly with `--rel depends_on:...`
  and `create` its acceptance(s) as separate plain calls (still same
  subject convention).
- Current-claims (`decision`) change via `supersede` (new id), never
  `update` to `superseded`, never payload-only `update`.
- Parent writes records. Do not spawn subagents here.
- Never supersede another subject's goal or position.

## Steps

1. Read views if not already in context:
   `adaptive-artifacts hook-start`
   Resolve **focus** and **kind**. Use the `## <focus>` plan section.
2. If this focus has no `active-goal`, create it (`init` step 6) for
   **this subject only**. Resolve the current phase's slug by querying
   `project:phase` for this effort (`--where payload.effort=<focus>`)
   and taking the one that is `in_progress`, or the lowest-`ordinal`
   `planned` one if none is `in_progress` yet — never
   `current-position.payload.scope`, which is a stable per-subject
   value, not the phase slug (incidental has no phase). If `engage`
   handed off `phase: new`, the current phase is a new one: create it
   in step 3 with `ordinal` = highest existing ordinal for this effort
   plus one.
3. Promote the current phase to `in_progress` with its real plan.
   `Get` its record to check lifecycle and `revision`:

```bash
adaptive-artifacts get --type project:phase --id <phase-id>
```

   If it's `planned` (created by `init`, or new here), replace the
   placeholder body and transition it in one call:

```bash
adaptive-artifacts update --type project:phase --id <phase-id> \
  --transition in_progress \
  --expected-revision "<revision>" \
  --body-file "<phase-plan.md>"
```

   `<phase-plan.md>` has real `## Problem`, `## Approach`, `## Exit
   criteria` sections now — this body is the phase's plan of record.
   If the phase record doesn't exist yet, `create --type project:phase`
   first (`init` step 7 shape), then run the `update` above with the
   revision `create` returned. Skip this step entirely for incidental
   (no phase record).
4. For each durable choice from planning, `create --type
   project:decision` with `choice`, `alternatives`, `phase`, `effort`
   payload and a `--body-file` with `## Rationale` / `##
   Counter-argument` sections. Skip trivia.
5. For each **independent** task in this phase (or the one incidental
   task), capture work-item + acceptance(s) together — bodies inline
   since `capture` takes JSON, not a file flag; keep the Description
   short here and use plain `create --body-file` instead if it needs
   more than a few lines:

```bash
adaptive-artifacts capture --bundle project:specified-work --records "$(cat <<'EOF'
[
  {
    "type": "project:work-item",
    "subject": "<task-slug>",
    "payload": {
      "title": "<short title>",
      "phase": "<current-phase-slug>",
      "kind": "deliver",
      "assignee": "",
      "effort": "<effort-slug>"
    },
    "body": "## Description\n\n<what this task builds/fixes>"
  },
  {
    "type": "project:acceptance",
    "subject": "<task-slug>",
    "payload": {
      "criterion": "<observable done-check>",
      "method": "tdd",
      "phase": "<current-phase-slug>",
      "effort": "<effort-slug>",
      "verify_command": "<command that proves it>"
    }
  },
  {
    "type": "project:acceptance",
    "subject": "<task-slug>-perf",
    "payload": {
      "criterion": "<second observable done-check, if there is one>",
      "method": "check",
      "phase": "<current-phase-slug>",
      "effort": "<effort-slug>",
      "verify_command": "<command that proves it>"
    }
  }
]
EOF
)"
```

   Drop the second acceptance object entirely when there's only one
   criterion — the bundle just needs at least one `work-item` and at
   least one `acceptance`, not exactly one of each.

   Set `kind` and `phase` from the effort (`phase` is `""` when
   incidental). `method` is `tdd`, `check`, or `manual`; `verify_command`
   is the literal command (empty string for `manual` with no script).

   - `repair` — criterion is repro-gone plus a regression check, not
     "we investigated." Diagnose happens at execute/verify.
   - `evaluate` — criterion is the campaign (suite, comparison).
     Binary gate -> `method=check`. Comparative / inconclusive lives
     in a finding at verify, not in `method`.
   - `incidental` — one observable done-check; usually `check` or
     `manual`.

6. For each **dependent** task (needs another same-phase task done
   first), create it outside the bundle so the dependency edge can be
   set at creation:

```bash
adaptive-artifacts create --type project:work-item \
  --subject "<task-slug>" \
  --payload '{"title":"<short title>","phase":"<current-phase-slug>","kind":"deliver","assignee":"","effort":"<effort-slug>"}' \
  --body "## Description

<what this task builds/fixes, and why it waits>" \
  --rel depends_on:<prerequisite-work-item-id>

adaptive-artifacts create --type project:acceptance \
  --subject "<task-slug>" \
  --payload '{"criterion":"<observable done-check>","method":"tdd","phase":"<current-phase-slug>","effort":"<effort-slug>","verify_command":"<command>"}'
```

7. Regenerate views:

```bash
adaptive-artifacts handoff --out views/handoff.md
adaptive-artifacts view --id project:plan --out views/plan.md
adaptive-artifacts validate
```

8. Show the user the focus task list. `project:plan`'s rendered view
   doesn't carry `derived.ready`/`wave` (they aren't in the contract's
   `requires_payload` for that role) — query them directly if useful:

```bash
adaptive-artifacts list --type project:work-item \
  --where payload.effort=<effort-slug> --where payload.phase=<current-phase-slug>
```

   Do not execute unless the user asks (`execute-phase`).
