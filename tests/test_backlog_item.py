"""CLI create/list/promote/dismiss for project:backlog-item.

Backlog is distinct from project:feedback: park via create, close via
current-status supersede to promoted or dismissed. Every item needs effort.
"""

from __future__ import annotations

import json

import helpers as h


def _effort(cli, defs, effort: str) -> None:
    h.create_generic_record(
        cli,
        defs,
        "project:active-goal",
        subject=effort,
        extra_payload={"goal": f"goal of {effort}", "kind": "deliver", "scope": "effort"},
    )


def _create_open(cli, subject: str, effort: str, **extra) -> dict:
    payload = {"effort": effort, "status": "open", **extra}
    result = cli(
        "create",
        "--type",
        "project:backlog-item",
        "--subject",
        subject,
        "--payload",
        json.dumps(payload),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def _list_open(cli) -> list[dict]:
    result = cli(
        "list",
        "--type",
        "project:backlog-item",
        "--state",
        "active",
        "--where",
        "payload.status=open",
        "--full",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["records"]


def _supersede_status(cli, record: dict, status: str, **extra) -> dict:
    payload = {**record["payload"], "status": status, **extra}
    result = cli(
        "supersede",
        "--type",
        "project:backlog-item",
        "--id",
        record["id"],
        "--expected-revision",
        record["revision"],
        "--payload",
        json.dumps(payload),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def test_create_list_open_backlog_item(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _effort(cli, defs, "park-effort")
    item = _create_open(cli, "park-later", "park-effort", source="chat")

    open_items = _list_open(cli)
    assert len(open_items) == 1
    assert open_items[0]["id"] == item["id"]
    assert open_items[0]["subject"] == "park-later"
    assert open_items[0]["payload"]["effort"] == "park-effort"
    assert open_items[0]["payload"]["status"] == "open"


def test_feedback_create_list_path_is_distinct(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _effort(cli, defs, "signal-effort")
    backlog = _create_open(cli, "parked-work", "signal-effort")

    fb = cli(
        "create",
        "--type",
        "project:feedback",
        "--subject",
        "route-now",
        "--payload",
        json.dumps(
            {"source": "user", "signal": "start this now", "effort": "signal-effort"}
        ),
        "--body",
        "## Signal\n\nstart this now",
    )
    assert fb.returncode == 0, fb.stdout + fb.stderr
    feedback = json.loads(fb.stdout)["record"]
    assert feedback["record_type"] == "project:feedback"

    fb_list = cli("list", "--type", "project:feedback", "--full")
    assert fb_list.returncode == 0, fb_list.stdout + fb_list.stderr
    feedback_ids = {r["id"] for r in json.loads(fb_list.stdout)["records"]}
    assert feedback["id"] in feedback_ids
    assert backlog["id"] not in feedback_ids

    open_ids = {r["id"] for r in _list_open(cli)}
    assert backlog["id"] in open_ids
    assert feedback["id"] not in open_ids


def test_promote_and_dismiss_leave_open_lists(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _effort(cli, defs, "close-effort")
    phase = h.create_generic_record(
        cli,
        defs,
        "project:phase",
        subject="close-effort-phase",
        extra_payload={"title": "next", "ordinal": 1, "effort": "close-effort"},
    )
    to_promote = _create_open(cli, "will-promote", "close-effort")
    to_dismiss = _create_open(cli, "will-dismiss", "close-effort")
    assert {r["subject"] for r in _list_open(cli)} == {"will-promote", "will-dismiss"}

    promoted = _supersede_status(
        cli, to_promote, "promoted", phase=phase["subject"]
    )
    assert promoted["payload"]["status"] == "promoted"
    assert promoted["payload"]["phase"] == phase["subject"]
    assert "will-promote" not in {r["subject"] for r in _list_open(cli)}

    dismissed = _supersede_status(cli, to_dismiss, "dismissed")
    assert dismissed["payload"]["status"] == "dismissed"
    assert _list_open(cli) == []


def test_create_without_effort_fails(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _effort(cli, defs, "need-effort")
    result = cli(
        "create",
        "--type",
        "project:backlog-item",
        "--subject",
        "missing-effort",
        "--payload",
        json.dumps({"status": "open"}),
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "effort" in combined.lower()
