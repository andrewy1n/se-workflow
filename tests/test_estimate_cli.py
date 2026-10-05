"""The CLI stores optional work-item size and estimate_minutes, and phases omit both."""

from __future__ import annotations

import json

import helpers as h

EFFORT = "dashboard"
PHASE = "run-facts"


def _phase(cli, defs) -> dict:
    return h.create_generic_record(
        cli, defs, "project:phase", subject=PHASE,
        extra_payload={"title": "Run facts", "ordinal": 1, "effort": EFFORT},
    )


def _work_item(cli, defs, subject: str, phase: str, **fields):
    payload = {
        "title": subject,
        "phase": phase,
        "kind": "deliver",
        "assignee": "agent",
        "effort": EFFORT,
    }
    payload.update(fields)
    return cli(
        "create", "--type", "project:work-item", "--subject", subject,
        "--payload", json.dumps(payload),
        "--body", h.generic_body(defs["project:work-item"]),
    )


def _created(result) -> dict:
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def _get(cli, record_type: str, record_id: str) -> dict:
    result = cli("get", "--type", record_type, "--id", record_id)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def _assert_valid(cli) -> None:
    result = cli("validate")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload.get("status") == "valid", payload


def test_work_item_stores_size_l_and_estimate_minutes(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    phase = _phase(cli, defs)
    item = _created(_work_item(
        cli, defs, "sized-task", phase["subject"], size="L", estimate_minutes=25,
    ))
    _assert_valid(cli)
    stored = _get(cli, "project:work-item", item["id"])
    assert stored["payload"]["size"] == "L"
    assert stored["payload"]["estimate_minutes"] == 25
    assert type(stored["payload"]["estimate_minutes"]) is int
    phase_stored = _get(cli, "project:phase", phase["id"])
    assert "size" not in phase_stored["payload"]
    assert "estimate_minutes" not in phase_stored["payload"]


def test_estimate_minutes_zero_is_stored(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    phase = _phase(cli, defs)
    item = _created(_work_item(
        cli, defs, "zero-task", phase["subject"], estimate_minutes=0,
    ))
    _assert_valid(cli)
    stored = _get(cli, "project:work-item", item["id"])
    assert stored["payload"]["estimate_minutes"] == 0
    assert type(stored["payload"]["estimate_minutes"]) is int


def test_work_item_may_omit_size_and_estimate_minutes(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    phase = _phase(cli, defs)
    item = _created(_work_item(cli, defs, "plain-task", phase["subject"]))
    _assert_valid(cli)
    stored = _get(cli, "project:work-item", item["id"])
    assert "size" not in stored["payload"]
    assert "estimate_minutes" not in stored["payload"]


def test_size_xxl_is_rejected(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    phase = _phase(cli, defs)
    result = _work_item(
        cli, defs, "too-big", phase["subject"], size="XXL", estimate_minutes=25,
    )
    assert result.returncode != 0
    assert "XXL" in result.stdout + result.stderr
