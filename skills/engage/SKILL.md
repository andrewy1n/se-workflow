---
name: engage
description: >-
  Classifies a software-engineering ask as deliver, repair, evaluate,
  or incidental, names the focus subject, and hands off to init,
  plan-phase, execute-phase, or verify-work, and names a lifecycle
  depth. Use when the user has work but has not named a phase skill,
  or when the work is a bug, one-off, integration test, or metric
  comparison.
---

# Engage

Thin router. Classify, name focus, stop. Follow
[kinds-and-focus.md](../kinds-and-focus.md) and
[lifecycle.md](../lifecycle.md). Follow
[ensure-store.md](../ensure-store.md) if a store will be needed.

Do not plan, implement, or verify in this skill.

## Steps

1. If views were not injected and `.artifacts/` exists:
   `adaptive-artifacts hook-start`. Read handoff. List live goal
   subjects with their goal text and phases.
2. Classify the ask (first match):

   | The text is about… | kind |
   |---|---|
   | Something broken, a bug, a repro, a crash | `repair` |
   | The job is a campaign, integration suite, bake-off, or metric comparison | `evaluate` |
   | Already-planned work, “run the phase”, “continue tasks” | keep existing kind; go to step 5 |
   | “Show this is done”, tests were run | keep existing kind; go to step 5 |
   | A small chore, typo, or unrelated change | `incidental` |
   | A specified feature, phase, or known change | `deliver` |

   If two rows fit, ask the user to pick.

   Name **depth** from [lifecycle.md](../lifecycle.md):

   | The text is… | depth |
   |---|---|
   | Incidental, or the user calls it trivial (typo, comment, mechanical rename) | `trivial` |
   | A cross-cutting change, or the user asks for the full lifecycle | `full` |
   | Otherwise | `standard` |

3. Name **focus** (effort slug). An effort is a product area or
   objective; one ask is usually one phase inside it. Compare the ask
   with each live goal's text:

   - A live goal covers the same area → reuse its subject, even when
     the kind differs (`kind` lives on each work-item). If no phase
     covers the ask, it becomes a **new phase** of that effort.
   - Several goals fit, or the fit is unclear → list the candidates
     and ask the user.
   - A **closed** goal covers the area → reopen it (kinds-and-focus,
     Closing and reopening) and reuse its subject; the ask is a new
     phase there.
   - No live or closed goal covers the area → pick a new slug
     (`login-500`, `p95-compare`).
   - `incidental` with records → always a new slug (see
     kinds-and-focus).

   Do not rename another effort’s subject to steal its goal.
4. Records?

   - `incidental` + fits this chat + not interrupting another live
     phase → **no records**. Tell the user to do it in this chat.
     Stop.
   - `incidental` + may span chats or interrupts a live phase → records
     on the **new** focus subject. Next: `plan-phase`.
   - `deliver` / `repair` / `evaluate` and no store or no goal for
     this focus → `init` (new subject). Then `specify` unless depth
     is `trivial`, then `discuss`, then `design`, then `plan-phase`.
   - Existing effort and no phase covers the ask → `specify` unless
     depth is `trivial` or a specification for that phase already
     exists, then `discuss` with `phase: new`, then `design`, then
     `plan-phase`.
   - Tasks for this focus already exist → `execute-phase` or
     `verify-work` if they only need a done-check.
   - Otherwise → `discuss` if the phase has no decisions yet, else
     `design` when depth is not `trivial` and this phase has no
     design record, else `plan-phase`.

   Skip `discuss` (go straight to `design`, or to `plan-phase` when
   depth is `trivial`) when the user already fixed the approach in
   this ask, or for `incidental`. Skip `specify` and `design` for
   `trivial` and for `incidental`. A missing specification on an
   older effort does not block `plan-phase`.
5. Show the routing line, then follow that skill with focus and kind
   in context:

   ```
   kind: <kind>
   focus: <effort-slug> (existing | new)
   depth: trivial | standard | full
   phase: <phase-slug> | new | none
   records: yes | no
   next: <skill or "this chat">
   ```

## Do not

- Spawn subagents
- Supersede another subject’s goal or position
- Write work-items here
- Add a fifth kind
