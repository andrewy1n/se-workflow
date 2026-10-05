# AGENTS.md

Plugin **0.3.0**. Agent skills for a software-engineering loop on
adaptive-artifacts: classify the ask, plan only the focused effort,
execute independent tasks with parallel subagents, verify with TDD,
checks, or findings. Install this repo as a plugin. It is not a
template you copy into other projects.

Requires the **adaptive-artifacts** plugin (`adaptive-artifacts` on
PATH). That runtime is unpublished experimental **0.1.0**. Its agent
protocol is `~/adaptive-artifacts/AGENTS.md`.

## Two trees

| You are in… | Store | What you edit |
|---|---|---|
| This repo, building the plugin | this repo's `.artifacts/` | `skills/`, `contract/`, `dashboard/`, `scripts/`, `tests/` |
| Some other repo, using the skills | that repo's `.artifacts/` | that repo's code, through the skills |

Do not copy `skills/`, rules, or this tree into a work project. The
bundled contract is `contract/project-design.json`. `init`,
`plan-phase`, or `engage` copies it into the work repo on first use.
If that repo's `.artifacts/project-design.json` has a `"project"` other
than `se-workflow`, stop. Do not overlay a foreign contract. See
[skills/ensure-store.md](skills/ensure-store.md).

## Live protocol

This repo's own memory is `.artifacts/`. At session start, if views
were not injected, run `adaptive-artifacts hook-start` and read the
derived views. Capture at the event with the `adaptive-artifacts` CLI.
Views under `.artifacts/views/` are derived — regenerate them; do not
edit them. At session end, if facts changed, write records, regenerate
views, and run `adaptive-artifacts hook-stop`. Fix validation errors
before finishing.

Only the parent session writes the store. Subagents return evidence in
their response. They do not call `adaptive-artifacts`.

A hand-edited record fails validation (`record revision tamper
detected`). Redo the edit through the CLI.

An incidental change that fits this chat gets no records. Kinds, focus,
phase positions, and closing an effort: [skills/kinds-and-focus.md](skills/kinds-and-focus.md).

## Skills

| Skill | When |
|---|---|
| `engage` | Classify kind, focus, and depth, then hand off. Do not implement inside it. |
| `init` | First time on a repo, or a new effort subject. Goal and phase titles only. |
| `specify` | Specification and acceptance criteria before design. Skip when depth is trivial. |
| `discuss` | Settle the approach with the user before planning. |
| `design` | Record the approach, or an explicit skip, before planning. |
| `plan-phase` | Approach settled. Write this phase's tasks, then wait for plan review. |
| `execute-phase` | Dispatch ready work in waves. |
| `integrate` | Semantic integration checkpoint. A git merge is not this pass. |
| `verify-work` | Evidence for the specification (`pass`, `fail`, `blocked`, `unknown`). |
| `diagnose` | Separate the failure from its cause. Escalate unresolved, repeated, or over-limit repairs. |
| `release` | Record release posture after sufficient evidence. Does not deploy. |
| `feedback` | Record a runtime or user signal and return it to intent. |
| `analyze-sessions` | User-invoked. Propose edits; write nothing until the user picks. |

Shared rules live in `skills/kinds-and-focus.md` and
`skills/ensure-store.md`, not in a fifth kind of skill.

`plan-phase` sets each work-item's `executor` to `inline` or
`subagent`. Every task in a wave uses the same executor. Missing
`executor` means `subagent`. A delivery phase body includes `## Landing`
(`phase/<phase-slug>`, worktree
`<repo-parent>/<repo-name>--<phase-slug>`, base `main`). Code commits
land on the phase branch; the store commits on the primary checkout.
Push only when Landing names it as a human stop. Incidental work has
no Landing section.

## Contract and the runtime

`contract/project-design.json` is the se-workflow design. Record types
are expected to grow. Tests and skills must not hardcode today's type
list as if it were frozen.

Every `adaptive-artifacts` invocation under `skills/` has to be one the
contract allows. `tests/test_skill_contract_consistency.py` fails when a
skill documents a type, transition, `--rel`, or bundle the contract
does not permit. Change the skill or the contract together, and run
that test.

Tests drive the public CLI as a subprocess
(`~/adaptive-artifacts/tools/artifacts.py`, or
`ADAPTIVE_ARTIFACTS_ROOT`). They do not import the runtime's Python
modules. The suite builds a fresh git-backed store from this contract.
It does not touch a real store.

## Adaptive-artifacts changes

A change to the runtime, catalog, hooks, or adaptive-artifacts skills
is an extension change. Follow `~/adaptive-artifacts/AGENTS.md`, section
"Changing the extension": capture it in **that** repo's store and apply
it only with human approval. Do not patch `~/adaptive-artifacts` mid-task
from a se-workflow session. `reassess-artifacts` redesigns a project's
own contract. It does not edit the extension.

If the se-workflow contract can express the need, change
`contract/project-design.json` here and leave the runtime alone.

## Testing

`pytest.ini` skips tests marked `tmux` unless `-m tmux` is set. While
editing, run the affected files. Before closing the task, run the full
suite: non-tmux tests in parallel, then the tmux tests alone.

```bash
uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m "not tmux" \
  && uv run --with textual --with pytest python -m pytest tests -q -m tmux
```

Dashboard tests need `textual` (the `uv run --with textual` form).
Commands and the `ADAPTIVE_ARTIFACTS_ROOT` override are in the README,
section "Testing".

## What to read

| Need | Where |
|---|---|
| Live goal, position, next | `.artifacts/views/handoff.md` (derived) |
| This protocol | this file |
| Kinds, focus, single writer | `skills/kinds-and-focus.md` |
| First-run store | `skills/ensure-store.md` |
| Bundled design | `contract/project-design.json` |
| Install, dashboard keys, test commands | `README.md` |
| Runtime change gate | `~/adaptive-artifacts/AGENTS.md` |
