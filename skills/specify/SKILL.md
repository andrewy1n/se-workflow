---
name: specify
description: >-
  Writes the phase specification and its acceptance criteria before
  design or planning. Use when engage hands off a standard or full
  deliver, repair, or evaluate phase. Skip for trivial and incidental
  work.
---

# Specify

Requires `artifact-runtime` and a live se-workflow store. Follow
[lifecycle.md](../lifecycle.md) and
[kinds-and-focus.md](../kinds-and-focus.md). Parent session writes
records. Do not write a design, work-items, or code here.

## Rules

- One specification per phase. `subject` is `spec-<phase-slug>`.
- `weight` is `light` when depth is `standard`, and `full` when
  depth is `full`. `light` is one honest sentence per section.
  `full` names concrete behavior, constraints, and success.
- Acceptance criteria are records, created here, not reconstructed
  at verify. `subject` is `spec-<phase-slug>-<criterion>`. Set
  `specification` to the specification subject. `method` is `tdd`,
  `check`, or `manual`. `verify_command` is the command, or `""`
  for a manual check with no script.
- `trivial` depth and `incidental` kind: write nothing. Tell the
  parent to continue at `plan-phase` or, for incidental that fits
  this chat, to do the work with no records.

## Steps

1. `adaptive-artifacts hook-start` if views were not injected.
   Resolve focus, depth, and the phase slug. If depth is `trivial`,
   stop.
2. Read the goal, the phase body, and the code the phase will touch.
3. Write the specification. Every section below is required and
   non-empty. Out of scope is a list of behaviors this phase will
   not build.

```bash
adaptive-artifacts capture --bundle project:lifecycle-spec --records "$(cat <<'EOF'
[
  {
    "type": "project:specification",
    "subject": "spec-<phase-slug>",
    "payload": {
      "summary": "<one line>",
      "weight": "light",
      "phase": "<phase-slug>",
      "effort": "<effort-slug>"
    },
    "body": "## Problem\n\n<what is wrong or missing>\n\n## Required behavior\n\n<what the system must do>\n\n## Constraints\n\n<limits that are not choices>\n\n## Success\n\n<what holds when this is done>\n\n## Out of scope\n\n<what this phase will not do>"
  },
  {
    "type": "project:acceptance",
    "subject": "spec-<phase-slug>-<criterion>",
    "payload": {
      "criterion": "<observable behavior>",
      "method": "check",
      "phase": "<phase-slug>",
      "effort": "<effort-slug>",
      "verify_command": "<command>",
      "specification": "spec-<phase-slug>"
    }
  }
]
EOF
)"
```

   Further criteria are separate creates, same payload shape. Do not
   reuse a subject.

```bash
adaptive-artifacts create --type project:acceptance \
  --subject "spec-<phase-slug>-<another-criterion>" \
  --payload '{"criterion":"<observable behavior>","method":"tdd","phase":"<phase-slug>","effort":"<effort-slug>","verify_command":"<command>","specification":"spec-<phase-slug>"}'
```

4. Set the phase position `stage` to `specify`
   ([lifecycle.md](../lifecycle.md)).
5. `adaptive-artifacts validate`. Next is `discuss` when the approach
   is not settled, otherwise `design`.

## Do not

- Treat the goal sentence as the specification
- Leave acceptance criteria implied in prose
- Write work-items (`plan-phase` does that)
- Specify another effort's phase
