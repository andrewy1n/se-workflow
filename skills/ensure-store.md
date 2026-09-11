# Ensure the current project has an se-workflow store

This plugin is installed once. Do **not** copy skills, rules, or this
repo into the work project. The store is created in the **current
working tree** the first time a delivery skill runs.

Requires `adaptive-artifacts` on PATH.

## Plugin root

This skill file lives at `<plugin>/skills/<name>/SKILL.md`. The bundled
design is `<plugin>/contract/project-design.json`.

Resolve `<plugin>` in order:

1. Directory two levels above this `SKILL.md`
2. `$CLAUDE_PLUGIN_ROOT` if that path contains `contract/project-design.json`
3. `$HOME/.cursor/plugins/local/se-workflow`

## First run in a work repo

Skip if `.artifacts/project-design.json` exists and `"project"` is
`se-workflow`. Otherwise:

```bash
mkdir -p .artifacts
cp "<plugin>/contract/project-design.json" .artifacts/project-design.json
adaptive-artifacts resolve
adaptive-artifacts init
```

`init` needs a git repo. If cwd is not git, leave design-only and tell
the user. Do not write `PLAN.md`, GSD `.planning/`, or extra skill copies.
