"""Each running phase keeps its own position; handoff groups every record under its effort."""

from __future__ import annotations

import json

import helpers as h

EFFORT = "area"


def _phase_position(cli, defs, phase: str) -> dict:
    h.create_generic_record(
        cli, defs, "project:phase", subject=phase,
        extra_payload={"title": f"title of {phase}", "ordinal": 1, "effort": EFFORT},
    )
    return h.create_generic_record(
        cli, defs, "project:current-position", subject=phase,
        extra_payload={"position": f"working on {phase}", "scope": "phase", "effort": EFFORT, "phase": phase},
    )


def _handoff(cli) -> str:
    result = cli("handoff")
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def _effort_section(handoff: str) -> str:
    start = handoff.index(f"## {EFFORT}\n")
    end = handoff.find("\n## ", start + 1)
    return handoff[start:] if end == -1 else handoff[start:end]


def test_two_phases_of_one_effort_keep_separate_positions_under_the_effort(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    h.create_generic_record(
        cli, defs, "project:active-goal", subject=EFFORT,
        extra_payload={"goal": "ship the area", "kind": "deliver", "scope": "effort"},
    )
    _phase_position(cli, defs, "area-one")
    _phase_position(cli, defs, "area-two")

    assert cli("validate").returncode == 0
    handoff = _handoff(cli)
    section = _effort_section(handoff)
    assert "working on area-one" in section and "working on area-two" in section
    assert "## area-one" not in handoff and "## area-two" not in handoff


def test_closing_a_phase_position_hides_only_that_phase(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    first = _phase_position(cli, defs, "area-one")
    _phase_position(cli, defs, "area-two")
    result = cli(
        "supersede", "--type", "project:current-position", "--id", first["id"],
        "--expected-revision", first["revision"], "--payload", json.dumps({"status": "closed"}),
    )
    assert result.returncode == 0, result.stdout + result.stderr

    section = _effort_section(_handoff(cli))
    assert "working on area-one" not in section and "working on area-two" in section


def test_work_item_renders_under_its_effort_not_its_task_slug(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    phase = h.create_generic_record(
        cli, defs, "project:phase", subject="area-one",
        extra_payload={"title": "first", "ordinal": 1, "effort": EFFORT},
    )
    task = h.create_generic_record(
        cli, defs, "project:work-item", subject="some-task",
        extra_payload={"title": "a task", "phase": phase["subject"], "effort": EFFORT, "kind": "deliver"},
    )
    h.transition(cli, "project:work-item", task, "in_progress")

    handoff = _handoff(cli)
    assert "**some-task**" in _effort_section(handoff)
    assert "## some-task" not in handoff
