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
`se-workflow`, check that the design lists `finding` and
`investigation-observation`. If those types are missing, the bundled
contract is newer: show the user and replace
`.artifacts/project-design.json` only if they approve, then
`adaptive-artifacts resolve`. Do not replace on a no.

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
