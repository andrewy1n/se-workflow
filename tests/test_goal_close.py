"""Closing an effort supersedes its goal and position with status closed; views drop it."""

from __future__ import annotations

import json

import helpers as h


def _effort(cli, defs, effort: str) -> tuple[dict, dict]:
    goal = h.create_generic_record(
        cli, defs, "project:active-goal", subject=effort,
        extra_payload={"goal": f"goal of {effort}", "kind": "deliver", "scope": "effort"},
    )
    phase = h.create_generic_record(
        cli, defs, "project:phase", subject=f"{effort}-phase",
        extra_payload={"title": "only phase", "ordinal": 1, "effort": effort},
    )
    position = h.create_generic_record(
        cli, defs, "project:current-position", subject=effort,
        extra_payload={"position": f"position of {effort}", "scope": "effort", "effort": effort, "phase": phase["subject"]},
    )
    return goal, position


def _close(cli, record_type: str, record: dict) -> None:
    payload = {**record["payload"], "status": "closed"}
    result = cli(
        "supersede", "--type", record_type, "--id", record["id"],
        "--expected-revision", record["revision"], "--payload", json.dumps(payload),
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _render(cli, *args: str) -> str:
    result = cli(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_closed_effort_leaves_handoff_brief_and_dashboard(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _effort(cli, defs, "open-effort")
    goal, position = _effort(cli, defs, "done-effort")
    _close(cli, "project:active-goal", goal)
    _close(cli, "project:current-position", position)

    for args in (("handoff",), ("view", "--id", "project:dashboard"), ("view", "--id", "project:brief")):
        rendered = _render(cli, *args)
        assert "done-effort" not in rendered, (args, rendered)
    handoff = _render(cli, "handoff")
    assert "goal of open-effort" in handoff and "position of open-effort" in handoff
    assert "goal of open-effort" in _render(cli, "view", "--id", "project:dashboard")
    assert _render(cli, "validate")


def test_status_rejects_values_other_than_open_or_closed(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    goal, _ = _effort(cli, defs, "some-effort")
    payload = {**goal["payload"], "status": "finished"}
    result = cli(
        "supersede", "--type", "project:active-goal", "--id", goal["id"],
        "--expected-revision", goal["revision"], "--payload", json.dumps(payload),
    )
    assert result.returncode != 0
