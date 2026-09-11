# se-workflow

Agent skills for a software-engineering delivery loop: plan a phase as
records, execute independent tasks with parallel subagents, verify with
TDD or checks. Install this repo as a plugin. It is not a template you
copy into other projects.

Requires the **adaptive-artifacts** plugin (`adaptive-artifacts` on PATH).

The plan is a derived view over records, not a `PLAN.md`. Only the
**current phase** is materialized as `work-item` + `acceptance`.

## Install

### Claude Code

```
/plugin marketplace add andrewy1n/se-workflow
/plugin install se-workflow@se-workflow
```

### Cursor

From a clone:

```bash
git clone https://github.com/andrewy1n/se-workflow.git
./se-workflow/scripts/sync-plugin.sh
```

Then reload Cursor so it picks up `~/.cursor/plugins/local/se-workflow`.
Or install from the repository URL in the Cursor plugin flow.

### Codex / other Agent Skills hosts

Copy or symlink `skills/se-plan-phase`, `skills/se-execute-phase`, and
`skills/se-verify-work` into the host's skills directory. Keep
`contract/project-design.json` next to `skills/` as in this repo (two
levels above each `SKILL.md`).

## Use

In whatever repo you are building:

| Skill | When |
|---|---|
| `se-plan-phase` | Planning conversation finished, or starting the next phase |
| `se-execute-phase` | Dispatch ready work in waves to subagents |
| `se-verify-work` | Show a task is done (tests / TDD / check) |

On first use in a repo, `se-plan-phase` writes the bundled contract into
that repo's `.artifacts/` and inits the store. Skills stay in the plugin.

A one-shot task that fits in one chat gets no records. Subagents must
not call `adaptive-artifacts` (single-writer store).

## Skills in this pack

- `se-plan-phase`
- `se-execute-phase`
- `se-verify-work`

Shared first-run steps: [skills/ensure-store.md](skills/ensure-store.md).
