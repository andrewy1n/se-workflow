# CLAUDE.md

Follow [AGENTS.md](AGENTS.md). It is the protocol for this plugin and
for when a change belongs in adaptive-artifacts instead.

## Testing

While editing, run only the affected test files. Before closing the
task, run that task's `verify_command`. `pytest.ini` already skips
`tmux`.

The suite needs a checkout of adaptive-artifacts at
`~/adaptive-artifacts` (override with `ADAPTIVE_ARTIFACTS_ROOT`). It
calls that repo's `tools/artifacts.py`. It does not import the runtime.
Dashboard tests need `textual`, which the `uv run --with textual` form
provides. More detail is in the README, section "Testing".

## Store

Records are the authority. `.artifacts/views/` is derived — regenerate
with `adaptive-artifacts`, do not edit view files. Write records with
the `adaptive-artifacts` CLI. A hand-edited record fails validation.

Only this session writes the store. Subagents return evidence in their
response and do not call `adaptive-artifacts`.

An incidental edit that fits this chat gets no records.

## Adaptive-artifacts

Leave `~/adaptive-artifacts` alone unless the user has approved an
extension change. That approval is the gate in
`~/adaptive-artifacts/AGENTS.md` ("Changing the extension"): capture the
amendment in that repo's store first. `reassess-artifacts` is for a
project's own contract, not for the runtime.

If se-workflow's `contract/project-design.json` can express the need,
change that file here. After any skill edit, the documented CLI
invocations must still be legal:
`python3 -m pytest tests/test_skill_contract_consistency.py -q`.

## Skills

Use the installed skills (`engage`, `init`, `discuss`, `plan-phase`,
`execute-phase`, `verify-work`). Do not copy this repo into the project
you are building. Shared rules are `skills/kinds-and-focus.md` and
`skills/ensure-store.md`. If a work repo already has a
`project-design.json` whose `"project"` is not `se-workflow`, stop.
