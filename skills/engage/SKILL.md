---
name: engage
description: >-
  Classifies a software-engineering ask as deliver, repair, evaluate,
  or incidental, names the focus subject, and hands off to init,
  plan-phase, execute-phase, or verify-work. Use when the user has
  work but has not named a phase skill, or when the work is a bug,
  one-off, integration test, or metric comparison.
---

# Engage

Thin router. Classify, name focus, stop. Follow
[kinds-and-focus.md](../kinds-and-focus.md). Follow
[ensure-store.md](../ensure-store.md) if a store will be needed.

Do not plan, implement, or verify in this skill.

## Steps

1. If views were not injected and `.artifacts/` exists:
   `adaptive-artifacts hook-start`. Read handoff. List live goal
   subjects so you do not reuse one by accident.
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
3. Name **focus** (effort slug). Reuse a live goal subject only when
   this ask is that effort. Otherwise pick a new slug (`login-500`,
   `readme-typo`, `p95-compare`). Do not rename another effort’s subject
   to steal its goal.
4. Records?

   - `incidental` + fits this chat + not interrupting another live
     phase → **no records**. Tell the user to do it in this chat.
     Stop.
   - `incidental` + may span chats or interrupts a live phase → records
     on the **new** focus subject. Next: `plan-phase`.
   - `deliver` / `repair` / `evaluate` and no store or no goal for
     this focus → `init` (new subject) then `plan-phase`.
   - Tasks for this focus already exist → `execute-phase` or
     `verify-work` if they only need a done-check.
   - Otherwise → `plan-phase`.
5. Show the routing line, then follow that skill with focus and kind
   in context:

   ```
   kind: <kind>
   focus: <effort-slug>
   records: yes | no
   next: <skill or "this chat">
   ```

## Do not

- Spawn subagents
- Supersede another subject’s goal or position
- Write work-items here
- Add a fifth kind
