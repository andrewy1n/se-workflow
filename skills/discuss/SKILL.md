---
name: discuss
description: >-
  Settles how a phase will be built before any tasks exist: reads the
  phase and the code it touches, presents two or three approaches with
  trade-offs and a recommendation, and records the user's choice as
  decisions and in the phase body. Use when engage hands off a new
  deliver, repair, or evaluate phase, or when the user wants to talk
  through an approach before plan-phase.
---

# Discuss the approach

Requires `artifact-runtime` and a live se-workflow store. If missing,
follow [ensure-store.md](../ensure-store.md). Follow
[kinds-and-focus.md](../kinds-and-focus.md). Parent session writes
records.

Do not write work-items, acceptance, or code in this skill. That is
`plan-phase` and `execute-phase`.

## Rules

- One phase per discussion. Resolve focus and phase from `engage` or
  the user; if several phases fit, ask.
- Read before proposing: the phase body, live decisions and
  constraints for this effort, and the code the phase touches. Read-only
  search subagents are fine; they return text and write nothing.
- Present options, not a plan. Each option: what changes, what it
  costs, what it rules out. Mark one as recommended and say why.
- The user decides. Do not record a choice the user did not make. If
  the user says "your call", record your recommendation and say so in
  the Rationale.
- Skip trivia. A decision is a choice a later reader would otherwise
  re-open.

## Steps

1. `adaptive-artifacts hook-start` if views were not injected. Resolve
   **focus**, **kind**, and the **phase** slug. If `engage` handed off
   `phase: new`, create the phase now (`init` step 7 shape) with
   `ordinal` = highest existing ordinal for this effort plus one, and
   a placeholder body.
2. Read context: the phase record, `project:decision` and
   `project:constraint` records with `payload.effort` = focus, and the
   code paths the phase names or implies.

```bash
adaptive-artifacts list --type project:decision --where payload.effort=<focus> --state active --full
adaptive-artifacts list --type project:constraint --where payload.effort=<focus> --state active --full
```

3. Present two or three approaches. For each: a short name, what it
   changes, trade-offs, and risks. End with a recommendation. Ask the
   user to choose; use a question tool with one option per approach
   when one is available.
4. Iterate until the user settles each open choice. Narrow follow-up
   questions are fine; do not reopen choices already recorded as
   decisions unless the user asks.
5. For each settled choice, create a decision. `Counter-argument` is
   the strongest case for the best rejected option, not a strawman:

```bash
adaptive-artifacts create --type project:decision \
  --subject "<decision-topic>" \
  --payload '{"choice":"<adopted>","alternatives":"<rejected options>","phase":"<phase-slug>","effort":"<effort-slug>"}' \
  --body-file "<decision-body.md>"
```

   `<decision-body.md>` has `## Rationale` and `## Counter-argument`
   sections, both non-empty. A decision that overturns an earlier one
   supersedes it instead of adding a second.

6. Write the chosen approach into the phase body so `plan-phase`
   starts from it. The phase stays `planned`; patch the body without a
   transition:

```bash
adaptive-artifacts update --type project:phase --id <phase-id> \
  --expected-revision <revision> --body-file "<phase-body.md>"
```

   `<phase-body.md>` keeps `## Problem`, `## Approach` (now the chosen
   approach, naming its decisions), and `## Exit criteria`.

7. For each question the user could not answer yet and that blocks
   planning, open a continuity-question on the focus:

```bash
adaptive-artifacts create --type project:continuity-question \
  --subject "<effort-slug>" \
  --payload '{"owner":"<who answers>","blocking":true,"scope":"<what it blocks>"}'
```

8. Regenerate views and `adaptive-artifacts validate`. Show the user
   the decisions and the phase approach. Next is `plan-phase` for this
   phase.

## Do not

- Write work-items, acceptance, or code
- Record a choice the user did not make
- Promote the phase to `in_progress` (`plan-phase` does that)
- Discuss another effort's phases
- Let subagents write records
