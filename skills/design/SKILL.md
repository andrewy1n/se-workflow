---
name: design
description: >-
  Records the architectural approach for a phase after discuss and
  before plan-phase. Use when a standard or full phase has a
  specification. A skipped design is an explicit record, not a
  missing one.
---

# Design

Requires `artifact-runtime` and a live se-workflow store. Follow
[lifecycle.md](../lifecycle.md). Parent session writes records. Do
not write work-items or code here. `discuss` settles choices with
the user; this skill records the approach those choices add up to.

## Rules

- `subject` is `design-<phase-slug>`. `weight` is `light`, `full`,
  or `skipped`.
- `full` depth uses `weight` `full`, never `skipped`.
- `standard` uses `light`, or `skipped` only when the change adds
  no interface, invariant, or cross-task assumption. Every section
  still says why, for example `Skipped: local rename, no new
  interface.`
- `trivial` writes nothing.
- Link `specification` when a specification exists. Omit the field
  when it does not (older efforts).

## Steps

1. Read the specification, the phase decisions, and the code the
   approach touches.

```bash
adaptive-artifacts list --type project:specification --where payload.phase=<phase-slug> --state active --full
adaptive-artifacts list --type project:decision --where payload.phase=<phase-slug> --state active --full
```

2. Write the design. Sections, all non-empty: Approach, Decisions,
   Interfaces, Invariants, Alternatives, Risks, Consequences.

```bash
adaptive-artifacts create --type project:design \
  --subject "design-<phase-slug>" \
  --payload '{"summary":"<one line>","weight":"light","phase":"<phase-slug>","effort":"<effort-slug>","specification":"spec-<phase-slug>"}' \
  --body-file "<design-body.md>"
```

   For `weight` `skipped`, omit `specification` only when no
   specification exists, and keep the same sections.

3. Point each decision at the criteria it serves. `serves` is a
   comma-separated list of acceptance subjects. `supersede` merges
   the rest of the payload:

```bash
adaptive-artifacts supersede --type project:decision --id <decision-id> \
  --expected-revision <revision> \
  --payload '{"serves":"spec-<phase-slug>-<criterion>"}'
```

4. Set the phase position `stage` to `design`. Validate. Next is
   `plan-phase`.

## Do not

- Re-open a decision the user already made
- Hide a skip by leaving the design record unwritten
- Put implementation tasks in the design body
