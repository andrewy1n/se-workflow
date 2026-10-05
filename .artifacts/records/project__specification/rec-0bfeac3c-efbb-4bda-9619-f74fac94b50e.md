---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-0bfeac3c-efbb-4bda-9619-f74fac94b50e",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "effort": "dashboard",
    "phase": "human-gates",
    "requirements": "R1,R2,R3,R4,R5,R6,R7,R8,R9,R10,R11",
    "weight": "full"
  },
  "record_type": "project:specification",
  "recorded_at": "2026-10-05T07:41:56+00:00",
  "relationships": {},
  "revision": "sha256:d1188923ecf69784487ebd6e0f6ec9d7ba8062c1f1c9909f510304257e3bd7f3",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "human-gates",
  "time": {
    "as_of": "2026-10-05T07:41:56+00:00"
  }
}
---

## Requirements

R1: Each Needs you row starts with an action label for its kind: plan-review question `Review plan`, other blocking question `Answer`, open question `Answer`, needs-human finding `Decide`, unsigned check `Sign off`, loop route `Route to <next>`, failed or blocked integration `Fix integration`, unmerged branch `Merge branch`. The Needs you detail screen uses the same label.
R2: A continuity question whose `scope` starts with `plan-review:` shows `Review plan` and the phase title for the slug after the prefix, not the raw scope. Other questions show their scope text as today.
R3: `c` on a Needs you item copies a prompt for the agent that names the effort, the subject or phase, and the action, for example `Walk me through the plan for phase human-gates (effort dashboard) so I can review it.` or `Sign off the manual check for as-dry-run (effort session-analysis).` On a task row `c` still copies the slug. The footer and key help say `copy prompt` when Needs you has focus.
R4: Under the goal, a next-step line shows `next:` and the first matching rule, then the effort position text in the muted colour: an open plan-review question gives `review the <phase> plan (plan-phase)`; another blocking question gives `answer: <scope>`; an unmerged done phase gives `merge phase/<slug> (execute-phase)`; a loop route gives `<next> for <R> (<skill>)`, where specify and design map to discuss, plan to plan-phase, execute and integrate to execute-phase, verify to verify-work; an unsigned check gives `sign off <subject> (verify-work)`; running tasks give `wave <n> running: <k> tasks`; ready tasks with none running give `execute-phase wave <n>`; an in-progress phase whose tasks are all done gives `close <phase> (verify-work)`; a planned next phase with no decisions gives `discuss <phase>`, otherwise `plan-phase <phase>`; with every phase done, `close the effort or add a phase`.
R5: When the selected phase's body has a `## Landing` section, the selector area shows its branch, the number of commits it has that `main` lacks, and `merged` or `not merged`; a branch that does not exist yet shows `no branch yet`. A phase without Landing shows nothing.
R6: A done phase with a Landing section whose branch exists and is not merged into `main` adds a `Merge branch` Needs you item. Enter on it opens the Needs you detail with the branch and ahead count.
R7: A running task is quiet when its latest record (assignment, amendment, execution report, or check-run) is older than twice its `estimate_minutes`, or 60 minutes when it has none. Its status reads `running <time> · quiet` in the warning colour, and its wave strip glyph uses the warning colour. Quiet tasks add no Needs you item.
R8: `se-workflow.tmux` appends a status-right segment that shows the needs-you count for the current pane's repo, for example `⚑ 3`, and nothing when the count is zero or there is no store. `@dashboard-status-right off` disables it.
R9: While the dashboard runs inside tmux, a Needs you item that was not in the previous snapshot rings the bell and shows a tmux message naming the effort, the action, and the subject. Items present at startup do not alert.
R10: With no git repository, no `git` binary, or a failing git command, landing state is omitted and no item or error appears.
R11: The dashboard writes nothing to the store or to git: landing state uses only read-only git commands.

## Acceptance criteria

R1, R2, R4, R6, R7: model tests against seeded stores in `tests/test_dashboard_model.py`, selected with `-k gates`.
R3, R9: Textual pilot tests in `tests/test_dashboard_app.py` with the clipboard and tmux calls stubbed.
R5, R6, R10, R11: tests in `tests/test_dashboard_gates.py` against a scratch git repo with phase branches, including no repo and no git; R11 checks `git status` and the store are unchanged.
R8: a `-m tmux` test against a real tmux server, on and off.

## Constraints

The dashboard stays read-only (constraint dashboard-read-only). No change to `contract/project-design.json` or `~/adaptive-artifacts`. Nothing executes until all five UX phases are discussed (constraint dashboard-ux-plan-before-execute).

## Non-goals

Acting on a gate from the dashboard (approving, signing, merging). Pushing branches. Changing the Claude Code status line segment. Alerts outside tmux.

## Invariants

Needs you ordering by kind is unchanged, with `Merge branch` after integration items. The next-step line is derived only from the loaded snapshot and landing state, never stored. Landing state never blocks a refresh: a slow or failing git call leaves the previous value.

## Assumptions

Phase bodies follow the Landing convention with branch `phase/<phase-slug>` and base `main`. tmux expands `#{pane_current_path}` inside a `#()` status command. `estimate_minutes` is on `TaskRow` once `estimate-view` lands.
