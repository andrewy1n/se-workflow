---
name: discuss
description: >-
  Settles how a phase will be built before any tasks exist: reads the
  phase and the code it touches, presents two or three approaches with
  trade-offs and a recommendation, and records the user's choice as
  decisions and in the phase body. Structured work also gets one
  specification and one design. Use when engage hands off a new
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
- **Two-modes rule.** Structured work is a phase that will have a
  specification. Simple work is incidental, or a phase the user is
  leaving on pass/fail. `discuss` writes specification and design only
  for structured work. Simple work skips both records.
- Read before proposing: the phase body, live decisions and
  constraints for this effort, assessments for this phase, and the
  code the phase touches. Read-only search subagents are fine; they
  return text and write nothing.
- Present options, not a plan. Each option: what changes, what it
  costs, what it rules out. Mark one as recommended and say why.
- The user decides. Do not record a choice the user did not make. If
  the user says "your call", record your recommendation and say so in
  the Rationale.
- Skip trivia. A decision is a choice a later reader would otherwise
  re-open. The design names those decisions; it does not replace them.
- Every required section of a specification or design is present. A
  section with nothing to say says `none`.

## Steps

1. `adaptive-artifacts hook-start` if views were not injected. Resolve
   **focus**, **kind**, and the **phase** slug. If `engage` handed off
   `phase: new`, create the phase now (`init` step 7 shape) with
   `ordinal` = highest existing ordinal for this effort plus one, and
   a placeholder body.
2. Read context: the phase record, `project:decision` and
   `project:constraint` records with `payload.effort` = focus,
   assessments for this phase, and the code paths the phase names or
   implies.

```bash
adaptive-artifacts list --type project:decision --where payload.effort=<focus> --state active --full
adaptive-artifacts list --type project:constraint --where payload.effort=<focus> --state active --full
adaptive-artifacts list --type project:assessment --where payload.phase=<phase-slug> --state active --full
adaptive-artifacts list --type project:specification --where payload.phase=<phase-slug> --state active --full
adaptive-artifacts list --type project:design --where payload.phase=<phase-slug> --state active --full
```

3. Present two or three approaches. For each: a short name, what it
   changes, trade-offs, and risks. End with a recommendation. Ask the
   user to choose; use a question tool with one option per approach
   when one is available.
4. Iterate until the user settles each open choice. Narrow follow-up
   questions are fine; do not reopen choices already recorded as
   decisions unless the user asks.
5. Structured work only, before the decision step: one
   `project:specification` whose subject is the phase slug. Payload
   `requirements` is the stable ids comma-separated (`R1,R2`). The
   Requirements section uses those ids (`R1: …`). Use `weight` `light`
   when the user already fixed the behavior and there is no
   architectural choice; `full` otherwise. When an assessment for this
   phase has `next` `specify`, supersede the specification. Otherwise
   create it when the phase has none.

```bash
adaptive-artifacts create --type project:specification \
  --subject "<phase-slug>" \
  --payload '{"weight":"full","phase":"<phase-slug>","effort":"<effort-slug>","requirements":"R1,R2"}' \
  --body-file "<specification-body.md>"
```

```bash
adaptive-artifacts supersede --type project:specification --id <specification-id> \
  --expected-revision <revision> \
  --payload '{"weight":"full","phase":"<phase-slug>","effort":"<effort-slug>","requirements":"R1,R2"}' \
  --body-file "<specification-body.md>"
```

   `<specification-body.md>` has `## Requirements`, `## Acceptance
   criteria`, `## Constraints`, `## Non-goals`, `## Invariants`, and
   `## Assumptions`. Every section is present. A section with nothing
   to say says `none`. Set payload `weight` to `light` or `full` as
   the rule above says; the sample payload shows `full`.

6. For each settled choice, create a decision. `Counter-argument` is
   the strongest case for the best rejected option, not a strawman:

```bash
adaptive-artifacts create --type project:decision \
  --subject "<decision-topic>" \
  --payload '{"choice":"<adopted>","alternatives":"<rejected options>","phase":"<phase-slug>","effort":"<effort-slug>"}' \
  --body-file "<decision-body.md>"
```

   `<decision-body.md>` has `## Rationale` and `## Counter-argument`
   sections, both non-empty. A decision that overturns an earlier one
   supersedes it instead of adding a second:

```bash
adaptive-artifacts supersede --type project:decision --id <decision-id> \
  --expected-revision <revision> \
  --payload '{"choice":"<adopted>","alternatives":"<rejected options>","phase":"<phase-slug>","effort":"<effort-slug>"}' \
  --body-file "<decision-body.md>"
```

7. Structured work only, after the decisions, so `decisions` names
   them: one `project:design` with the same subject (the phase slug).
   Payload `decisions` is those decision subjects, comma-separated.
   Required sections hold the architecture, interfaces, invariants,
   assumptions, tradeoffs, and risks. Decisions remain the choices a
   later reader would re-open. When an assessment for this phase has
   `next` `design`, supersede the design and any overturned decision,
   then return to `plan-phase`. Otherwise create the design when the
   phase has none.

```bash
adaptive-artifacts create --type project:design \
  --subject "<phase-slug>" \
  --payload '{"phase":"<phase-slug>","effort":"<effort-slug>","decisions":"<decision-subject>,<decision-subject>"}' \
  --body-file "<design-body.md>"
```

```bash
adaptive-artifacts supersede --type project:design --id <design-id> \
  --expected-revision <revision> \
  --payload '{"phase":"<phase-slug>","effort":"<effort-slug>","decisions":"<decision-subject>,<decision-subject>"}' \
  --body-file "<design-body.md>"
```

   `<design-body.md>` has `## Architecture`, `## Interfaces`,
   `## Decisions`, `## Invariants`, `## Assumptions`, `## Tradeoffs`,
   and `## Risks`. Every section is present. A section with nothing
   to say says `none`.

8. Write the chosen approach into the phase body so `plan-phase`
   starts from it. The phase stays `planned`; patch the body without a
   transition:

```bash
adaptive-artifacts update --type project:phase --id <phase-id> \
  --expected-revision <revision> --body-file "<phase-body.md>"
```

   `<phase-body.md>` keeps `## Problem`, `## Approach` (now the chosen
   approach, naming its decisions), and `## Exit criteria`.

9. For each question the user could not answer yet and that blocks
   planning, open a continuity-question on the focus:

```bash
adaptive-artifacts create --type project:continuity-question \
  --subject "<effort-slug>" \
  --payload '{"owner":"<who answers>","blocking":true,"scope":"<what it blocks>"}'
```

   When the user answers it, clear it at the event (kinds-and-focus,
   Needs-you clears):

```bash
adaptive-artifacts update --type project:continuity-question --id <question-id> \
  --transition answered --expected-revision <revision>
```

10. Regenerate views and `adaptive-artifacts validate`. Show the user
    the specification, the design, the decisions, and the phase
    approach. Next is `plan-phase` for this phase, including after a
    `next` `design` supersede.

## Do not

- Write work-items, acceptance, or code
- Write a specification or a design for simple work
- Record a choice the user did not make
- Promote the phase to `in_progress` (`plan-phase` does that)
- Discuss another effort's phases
- Let subagents write records
