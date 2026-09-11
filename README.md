# se-workflow

Personal software-engineering artifact contract: conversation → current
phase as records → parallel subagents → verification. Requires the
`adaptive-artifacts` plugin on PATH (`project-design@0.3.0`).

The plan is a **derived view**, not a Markdown file agents edit. Only the
**current phase** is materialized as `work-item` + `acceptance` records.

## Prerequisites

- `adaptive-artifacts` on PATH (Cursor/Claude plugin)
- Git repo for any project that will hold a live store

## Use on a real engineering repo

```bash
~/se-workflow/scripts/plant.sh /path/to/work-repo
```

That copies this design, discovery pointers, and the three skills, then
`resolve` + `init`. Open that repo and follow `artifact-runtime`.

A one-shot task that fits in one chat gets **no** records.

## Skills

| Skill | When |
|---|---|
| `se-plan-phase` | Planning conversation finished, or starting the next phase |
| `se-execute-phase` | Dispatch ready work in waves to subagents |
| `se-verify-work` | Show a task is done (tests/TDD/check) |

Runtime writes stay with `artifact-runtime`. Subagents must not write records.

## Record map

| Type | Pattern | Done / change |
|---|---|---|
| `work-item` | current-status | `live=yes` while open; supersede `live=no` when finished or dropped. `stage` is `planned` or `in_progress`. Payload updates also go through **supersede** (the CLI cannot patch a current-claim without a transition). |
| `acceptance` | definition | What done means. Same `subject` as the work-item. |
| `check-run` | event | A test of that criterion at a git revision. |
| `active-goal` / `current-position` | current-status | Effort outcome; current phase + remaining phase *titles* only. |
| `decision` | decision | Durable choices from planning. |
| `continuity-question` | question | Dispatch/resume blockers. |
| `failed-attempt` | event | Abandoned approach. |

Dependencies are `ready` + `wave` on the work-item (the catalog has no
`depends_on`). Git owns code and tests. Do not dual-write GSD `.planning/`.

## This repo

Has its own store for the workflow pack itself. Do not copy `.artifacts/records/`
into a work repo — only `project-design.json`.
