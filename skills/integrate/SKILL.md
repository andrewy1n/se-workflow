---
name: integrate
description: >-
  Records a semantic integration verdict after execution and before
  phase close. Use when depth is full, or when a standard phase ran
  more than one task in a wave. Git merge success is not this verdict.
---

# Integrate

Requires `artifact-runtime` and a live se-workflow store. Follow
[lifecycle.md](../lifecycle.md). Parent session writes records.

The Landing branch and worktree from `plan-phase` / `execute-phase`
are the git mechanism. This skill does not create a second branch
or a second merge. It judges the tree those mechanisms produced.

## Rules

- Skip, and write no report, when depth is `trivial`, or when
  `standard` dispatched no parallel wave. Say that the checkpoint
  was skipped.
- `full`, and any parallel wave, always writes one
  `project:integration-report` for the phase revision.
- `verdict` is `pass` | `fail` | `blocked` | `unknown`.
- A clean merge with disagreeing interfaces or assumptions is
  `fail`. An empty combined claim (no executor reported interfaces
  or assumptions, and no integration check ran) is `unknown`, not
  `pass`.
- `fail` or `unknown` does not proceed to a passing verify. Hand
  `fail` to `diagnose`. Leave `unknown` and `blocked` in place and
  tell the user what is missing.

## Steps

1. Read execution reports for this phase and the diff on the phase
   branch against `main`. Note interfaces and assumptions each task
   claimed. Note git conflicts separately from semantic conflicts.
2. When Landing says to merge, `execute-phase` performs that merge.
   Do it once, there. Then judge the result. A merge conflict is
   `blocked` until a human or a repair resolves the git conflict,
   and it is still not a semantic pass after the conflict is gone.
3. Write the report:

```bash
adaptive-artifacts create --type project:integration-report \
  --subject "integrate-<phase-slug>" \
  --payload '{"phase":"<phase-slug>","effort":"<effort-slug>","verdict":"fail","revision":"<git sha or dirty>","summary":"<one line>"}' \
  --body "## Merged work

<tasks and revisions now on the phase branch>

## Conflicts

<semantic conflicts, git conflicts, or none>

## Invariants

<cross-task invariants checked, or not checked>

## Assumptions

<assumptions the tasks shared or contradicted>"
```

4. Set the phase position `stage` to `integrate`. On `pass`, the
   parent runs `verify-work` for the phase gate. On `fail`, the
   parent runs `diagnose`.

## Do not

- Treat `git merge` exit 0 as `verdict` `pass`
- Close the phase in this skill
- Spawn an integration agent when the parent can read the diff
