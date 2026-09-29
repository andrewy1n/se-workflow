"""The project:dashboard view renders one section per role, in role order."""

from __future__ import annotations

import json

import helpers as h

EFFORT = "demo"

SECTIONS = [
    "Goal",
    "Phase",
    "Blocking Question",
    "Open Question",
    "Needs Human",
    "Unsigned Manual Check",
    "Running",
    "Ready",
    "Waiting",
    "Done Recent",
]

def _work_item(cli, defs, subject: str, phase: str, **payload) -> dict:
    return h.create_generic_record(
        cli, defs, "project:work-item", subject=subject,
        extra_payload={"title": f"title of {subject}", "phase": phase, "effort": EFFORT, **payload},
    )


def _seed(store, cli, defs) -> None:
    h.create_generic_record(
        cli, defs, "project:active-goal", subject=EFFORT,
        extra_payload={"goal": "ship the dashboard", "kind": "deliver"},
    )
    phase = h.create_generic_record(
        cli, defs, "project:phase", subject="demo-phase-1",
        extra_payload={"title": "first phase", "ordinal": 1, "effort": EFFORT},
    )
    h.transition(cli, "project:phase", phase, "in_progress")
    h.create_generic_record(
        cli, defs, "project:continuity-question", subject=EFFORT,
        extra_payload={"blocking": True, "scope": "blocking-scope"},
    )
    h.create_generic_record(
        cli, defs, "project:continuity-question", subject=EFFORT,
        extra_payload={"blocking": False, "scope": "open-scope"},
    )
    h.create_generic_record(
        cli, defs, "project:finding", subject="demo-finding",
        extra_payload={"claim": "a human must decide", "needs": "human", "effort": EFFORT},
    )
    h.create_generic_record(
        cli, defs, "project:check-run", subject="demo-check",
        extra_payload={"method": "manual", "signed_by": "", "result": "pass", "effort": EFFORT},
    )
    running = _work_item(cli, defs, "running-item", "demo-phase-1", assignee="agent-7")
    h.transition(cli, "project:work-item", running, "in_progress")
    ready = _work_item(cli, defs, "ready-item", "demo-phase-1")
    waiting_payload = {
        "title": "title of waiting-item", "phase": "demo-phase-1", "kind": "deliver",
        "assignee": "", "effort": EFFORT,
    }
    result = cli(
        "create", "--type", "project:work-item", "--subject", "waiting-item",
        "--payload", json.dumps(waiting_payload), "--rel", f"depends_on:{ready['id']}",
        "--body", h.generic_body(defs["project:work-item"]),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    done = _work_item(cli, defs, "done-item", "demo-phase-1")
    h.transition(cli, "project:work-item", done, "in_progress", "done")

    old = _work_item(cli, defs, "old-done-item", "demo-phase-1")
    old = h.transition(cli, "project:work-item", old, "in_progress")
    h.run_cli_48h_ago(
        store, "update", "--type", "project:work-item", "--id", old["id"],
        "--transition", "done", "--expected-revision", old["revision"],
    )


def _section(rendered: str, heading: str) -> str:
    start = rendered.index(f"### {heading}\n")
    end = rendered.find("\n### ", start + 1)
    return rendered[start:] if end == -1 else rendered[start:end]


def test_dashboard_renders_every_section_in_order_with_labeled_fields(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _seed(store, cli, defs)

    result = cli("view", "--id", "project:dashboard")
    assert result.returncode == 0, result.stdout + result.stderr
    rendered = result.stdout

    assert f"## {EFFORT}\n" in rendered
    positions = [rendered.index(f"### {name}\n") for name in SECTIONS]
    assert positions == sorted(positions), rendered

    assert "goal: ship the dashboard" in _section(rendered, "Goal")
    assert "title: first phase" in _section(rendered, "Phase")
    assert "scope: blocking-scope" in _section(rendered, "Blocking Question")
    assert "scope: open-scope" in _section(rendered, "Open Question")
    assert "blocking-scope" not in _section(rendered, "Open Question")
    assert "claim: a human must decide" in _section(rendered, "Needs Human")
    assert "method: manual" in _section(rendered, "Unsigned Manual Check")
    running = _section(rendered, "Running")
    assert "**running-item**" in running and "assignee: agent-7" in running
    assert "**ready-item**" in _section(rendered, "Ready")
    assert "**waiting-item**" not in _section(rendered, "Ready")
    assert "**waiting-item**" in _section(rendered, "Waiting")
    assert "**done-item**" in _section(rendered, "Done Recent")


def test_dashboard_omits_work_done_more_than_24h_ago(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _seed(store, cli, defs)

    result = cli("view", "--id", "project:dashboard")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "**old-done-item**" not in result.stdout
