# se-workflow

Agent skills for a software-engineering loop on adaptive-artifacts:
classify the ask, plan only the focused effort, execute independent
tasks with parallel subagents, verify with TDD, checks, or findings.
Install this repo as a plugin. It is not a template you copy into
other projects.

Requires the **adaptive-artifacts** plugin (`adaptive-artifacts` on PATH).
Install that dependency before this plugin (see Install below).

The plan is a derived view over records. Only the **focused effort**
is written; for delivery-shaped work, only the **current phase** is
materialized as `work-item` + `acceptance`.

## Kinds

`kind` is data on the goal and each work-item, not a new skill:

| Kind | Use |
|---|---|
| `deliver` | Specified change; done is a binary check |
| `repair` | Something is wrong; diagnose, then fix |
| `evaluate` | The work is a campaign or comparison |
| `incidental` | One-off; no records if it fits this chat |

Focus is a subject string (which effort this chat is on). Other live
goals stay live. Views group handoff by subject and the plan by
`effort`. See [skills/kinds-and-focus.md](skills/kinds-and-focus.md).

## Install

Requires **adaptive-artifacts** first (`adaptive-artifacts` on PATH).
That plugin is not in Anthropic's official marketplace.

### 1. adaptive-artifacts (dependency)

```bash
claude plugin marketplace add andrewy1n/adaptive-artifacts
claude plugin install adaptive-artifacts@adaptive-artifacts -y
```

Or for Cursor: clone/sync adaptive-artifacts and put `bin/adaptive-artifacts`
on PATH (see that repo's README).

### 2. se-workflow

#### Claude Code

```bash
claude plugin marketplace add andrewy1n/se-workflow
claude plugin install se-workflow@se-workflow -y
```

Install id is `se-workflow@se-workflow`. If a marketplace with that name
already points elsewhere: `claude plugin marketplace remove se-workflow`
then add again.

#### Cursor

From a clone:

```bash
git clone https://github.com/andrewy1n/se-workflow.git
./se-workflow/scripts/sync-plugin.sh
```

Then reload Cursor so it picks up `~/.cursor/plugins/local/se-workflow`.
Or install from the repository URL in the Cursor plugin flow.

#### Codex / other Agent Skills hosts

Copy or symlink `skills/init`, `skills/plan-phase`, `skills/execute-phase`,
`skills/verify-work`, and `skills/engage` into the host's skills
directory. Keep `contract/project-design.json` and
`skills/kinds-and-focus.md` / `skills/ensure-store.md` next to
`skills/` as in this repo (two levels above each `SKILL.md`).

## Use

In whatever repo you are building:

| Skill | When |
|---|---|
| `engage` | Classify kind + focus, then hand off |
| `init` | First time on a repo, or a new effort subject |
| `plan-phase` | Planning finished, or tasks for this focus |
| `execute-phase` | Dispatch ready work in waves to subagents |
| `verify-work` | Show a task is done (check-run and/or finding) |

On first use, `init`, `plan-phase`, or `engage` writes the bundled
contract into that repo's `.artifacts/` and inits the store. Skills
stay in the plugin.

`init` writes goal, kind, and a `project:phase` record for every phase
it can currently name (all `planned`) — not work-items. `plan-phase`
materializes this focus's tasks and promotes the current phase to
`in_progress` with its real plan in the body.

Task state is the work-item's lifecycle (`planned -> in_progress ->
done`, plus `withdrawn`/`superseded`), not a payload flag. Dependencies
are `depends_on` edges between work-items; readiness and wave are
derived by the engine at read time (`derived.ready`, `derived.wave`) —
nothing writes them.

A one-shot that fits in one chat and is not an interrupt gets no
records. An interrupt or a chore that may span chats gets
`kind=incidental` on its **own** subject. Subagents must not call
`adaptive-artifacts` (single-writer store).

Existing se-workflow stores created before staged task lifecycle,
phase records, and dependency edges existed need a human-approved
contract replace (`ensure-store.md`).

## Skills in this pack

- `engage`
- `init`
- `plan-phase`
- `execute-phase`
- `verify-work`

Shared rules: [skills/kinds-and-focus.md](skills/kinds-and-focus.md).
Shared first-run steps: [skills/ensure-store.md](skills/ensure-store.md).

## Dashboard in tmux

`scripts/dashboard` runs the Textual app `scripts/dashboard_app.py`
through `uv` for the repo of the current directory. The app shows one
tab per live effort: the goal, the phase stepper, progress, status
tabs with counts (Active, Running, Ready, Waiting, Done, All), the task
table, a Needs you panel titled with its item count, and recent activity. Active is the
default and holds running, ready, and waiting tasks. It reloads when the store changes.

An effort is finished when every phase and every task that is not
withdrawn is done. Finished efforts sort after live ones, and their tabs
are dimmed. On the Active tab with no filter, a finished effort shows
`All N tasks done` in place of the task table.

The task table groups tasks under phase header rows in ordinal order.
In-progress phases and phases awaiting sign-off are expanded. Done and
planned phases are collapsed. When more than two phases are done, the
older ones fold into one `N earlier phases done` row. A phase awaits
sign-off when every open task waits only on an unsigned manual check.
The progress bar covers the whole effort.

The task table columns are status, task, wave, and assignee. The
grouped table has no phase column; `--once` still prints one. A running
task's status shows its running time, counted from its latest
assignment (for example `running 2h`). A waiting task's title ends with
a muted `waits on <subjects>` note that lists its unfinished
dependencies. In recent activity, a failed check-run or execution
report shows `✗` and is red.

It needs `uv`. The first run downloads `textual`.

| Key | Action |
|---|---|
| `tab` / `shift+tab` | Switch effort |
| `enter` / click | Open the task detail, or expand or collapse a phase header or the earlier-phases row |
| `p` | Open the phase detail (body, decisions, constraints, tasks) for the selected row |
| `n` | Focus the Needs you list; arrows or `j` / `k` move, `esc` returns to the task table |
| `enter` on a Needs you item | Open the task detail when the item has a task, else the Needs you detail (kind, record type, full text, body) |
| `/` | Filter tasks by title or subject; `enter` keeps it, `esc` clears it |
| `1`-`6` / `left` / `right` / click | Pick a status tab; the filter applies on top |
| `esc` | Clear the filter, or go back one screen |
| `c` | Copy the selected task's slug, or the subject of the selected Needs you item |
| `g` | In the detail, show the commit of the task's latest revision |
| `l` | In the task detail, focus the links (depends on, blocks, phase); arrows or `j` / `k` move, `enter` opens the task or phase detail |
| `enter` on a phase detail task | Open the task detail; the phase detail opens with its task list focused, arrows or `j` / `k` move |
| `r` | Refresh now |
| `q` | Quit |

`scripts/dashboard --once` prints one plain-text frame and exits.
`scripts/dashboard --interval S` sets the seconds between change checks
(default 2).

The launcher finds the store from the git toplevel of the directory:

1. `~/.artifacts/<toplevel name>`, if it has `meta.json`.
2. `<toplevel>/.artifacts`, if it has `meta.json`.

It runs the app from the toplevel. The app finds the runtime binary in
this order:

1. `$ADAPTIVE_ARTIFACTS_BIN`.
2. `~/adaptive-artifacts/bin/adaptive-artifacts`, if it is executable.
3. `adaptive-artifacts` on `PATH`.

The launcher finds `uv` in this order:

1. `$SE_WORKFLOW_UV`.
2. `uv` on `PATH`.
3. `~/.local/bin/uv`.

tmux popups run a non-interactive shell, so shell functions and aliases
do not apply there. If the launcher finds no store or no `uv`, it prints
the reason and waits for a key.

To install the key bindings, add this line to `~/.tmux.conf`:

```tmux
source-file ~/se-workflow/scripts/tmux-dashboard.conf
```

Then reload tmux with `tmux source-file ~/.tmux.conf`. The snippet adds:

| Keys | Opens |
|---|---|
| prefix + `A` | The dashboard in a popup (80% of the window) |
| prefix + `S` | The dashboard in a side pane (40% of the width) |

Both open in the directory of the current pane. The snippet sets the
tmux global environment variable `SE_WORKFLOW_SCRIPTS` to its own
directory. If `SE_WORKFLOW_SCRIPTS` is empty, the bindings use
`~/se-workflow/scripts`. Change the keys in your copy if `A` or `S` is
already bound.

### Status line segment

`scripts/dashboard-status` prints one line per effort the dashboard
shows, for example:

```text
watch-dashboard · 1 running · 2 ready · 1 needs you
```

"needs you" counts blocking questions, open questions, findings that
need a human, and unsigned manual checks. The segment omits zero counts.
It builds the same snapshot as the dashboard, so an effort without an
active goal gets no line. It finds the store and the binary like
`scripts/dashboard`. It prints nothing when there is no store, the CLI
fails, or the snapshot takes more than 2 seconds.

It reads Claude Code status JSON on stdin (`workspace.current_dir`, else
`cwd`), or takes a directory argument. To add it to an existing status
line script that has the status JSON in `$input`, append:

```bash
echo "$input" | ~/se-workflow/scripts/dashboard-status
```

## Testing

The suite in `tests/` needs a sibling checkout of `adaptive-artifacts`
(the runtime this contract resolves against) and `pytest`:

```bash
python3 -m pip install --user pytest   # if not already available
python3 -m pytest tests -q
```

For a fast run, use `pytest-xdist` for everything except the tmux tests,
which run serially because parallel load makes them flaky:

```bash
uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m "not tmux" \
  && uv run --with textual --with pytest python -m pytest tests -q -m tmux
```

By default it looks for the runtime at `~/adaptive-artifacts`. Point it
elsewhere with `ADAPTIVE_ARTIFACTS_ROOT`:

```bash
ADAPTIVE_ARTIFACTS_ROOT=/path/to/adaptive-artifacts python3 -m pytest tests -q
```

Every test drives `adaptive-artifacts`'s public CLI against a fresh,
disposable, git-backed store built from this repo's own
`contract/project-design.json` — nothing here touches a real store, and
nothing hardcodes today's record types, since the contract is expected
to keep growing. `test_contract_self_consistency.py` proves every
declared record type, lifecycle transition, bundle relationship, and
payload reference actually works end to end. `test_skill_contract_consistency.py`
extracts every `adaptive-artifacts` invocation documented under `skills/`
and asserts the contract actually permits it — a red result there names
a skill instructing an operation (a record type, transition, `--rel`,
or bundle membership) the contract does not currently allow.
