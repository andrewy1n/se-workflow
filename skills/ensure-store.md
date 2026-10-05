# Ensure the current project has an se-workflow store

This plugin is installed once. Do **not** copy skills, rules, or this
repo into the work project. The store is created in the **current
working tree** the first time `init`, `plan-phase`, or `engage` needs
records.

Requires `adaptive-artifacts` on PATH.

## Plugin root

This skill file lives at `<plugin>/skills/<name>/SKILL.md`. The bundled
design is `<plugin>/contract/project-design.json`.

Resolve `<plugin>` in order:

1. Directory two levels above this `SKILL.md`
2. `$CLAUDE_PLUGIN_ROOT` if that path contains `contract/project-design.json`
3. `$HOME/.cursor/plugins/local/se-workflow`

## First run in a work repo

If `.artifacts/project-design.json` exists and `"project"` is
`se-workflow`, check that the design lists a `phase` record, a
`constraint` record, an `assignment` record, and an `execution-report`
record, and that `work-item` has `required_sections`. A design is
current only when it also lists `specification`, `design`,
`assessment`, `integration-report`, `release`, and `feedback`. If those
are missing, the bundled contract is newer (it predates staged task
lifecycle, phase records, dependency edges, the assignment/
execution-report dispatch loop, or the evidence-loop records): show the
user and replace `.artifacts/project-design.json` only if they approve,
then `adaptive-artifacts resolve`. Do not replace on a no. This is a
one-time upgrade check at first touch, not a standing gate — once the
design is current, nothing in the other skills re-checks it before
dispatching.

If `.artifacts/project-design.json` exists and `"project"` is something
else, **stop**. Do not overlay a foreign contract.

Otherwise:

```bash
mkdir -p .artifacts
cp "<plugin>/contract/project-design.json" .artifacts/project-design.json
adaptive-artifacts resolve
adaptive-artifacts init
```

`adaptive-artifacts init` needs a git repo. If cwd is not git, leave
design-only and tell the user. Do not write a plan document or extra
skill copies.

## Committing store writes

`validate` accepts an uncommitted record rewrite when the record matches
its own op log, so an `update`, `supersede`, or `close` batch does not
have to be committed before validating or before `hook-stop` runs.

Still commit store writes as part of the work they belong to — the
record diff is what shows a reader what changed and why:

```bash
git add .artifacts && git commit -m "records: <what changed>"
```

A record edited by hand, outside the runtime, fails validation:

```
record revision tamper detected: .artifacts/records/.../rec-....md
```

Fix that by redoing the edit through `adaptive-artifacts update` rather
than by hand-patching the file.
