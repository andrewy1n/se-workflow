"""Tests for scripts/dashboard_model: the dashboard snapshot built from store records."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

import pytest

import helpers as h
from conftest import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import artifact_store  # noqa: E402
import dashboard_model as model  # noqa: E402


def _goal(cli, defs, effort: str) -> None:
    h.create_generic_record(
        cli, defs, "project:active-goal", subject=effort,
        extra_payload={"goal": f"ship {effort}", "kind": "deliver"},
    )


def _phase(cli, defs, effort: str, subject: str, ordinal: int, *states: str) -> None:
    record = h.create_generic_record(
        cli, defs, "project:phase", subject=subject,
        extra_payload={"title": f"title of {subject}", "ordinal": ordinal, "effort": effort},
    )
    h.transition(cli, "project:phase", record, *states)


def _work_item(cli, defs, effort: str, subject: str, phase: str, *rels: str, assignee: str = "") -> dict:
    payload = {"title": f"title of {subject}", "phase": phase, "kind": "deliver", "assignee": assignee, "effort": effort}
    args = ["create", "--type", "project:work-item", "--subject", subject, "--payload", json.dumps(payload)]
    for rel in rels:
        args.extend(["--rel", rel])
    result = cli(*args, "--body", h.generic_body(defs["project:work-item"]))
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def _target(store):
    return artifact_store.resolve(store)


def _effort(snapshot: model.Snapshot, name: str) -> model.EffortView:
    return next(view for view in snapshot.efforts if view.effort == name)


@pytest.fixture()
def defs(resolved_contract):
    return h.record_defs_by_id(resolved_contract)


@pytest.fixture()
def seeded(store, cli, defs):
    _goal(cli, defs, "alpha")
    _goal(cli, defs, "beta")
    _phase(cli, defs, "alpha", "a-one", 1, "in_progress", "done")
    _phase(cli, defs, "alpha", "a-two", 2, "in_progress")
    _phase(cli, defs, "beta", "b-one", 1)
    running = _work_item(cli, defs, "alpha", "a-running", "a-two", assignee="agent-7")
    h.transition(cli, "project:work-item", running, "in_progress")
    _work_item(cli, defs, "alpha", "a-ready", "a-two")
    _work_item(cli, defs, "alpha", "a-waiting", "a-two", f"depends_on:{running['id']}")
    done = _work_item(cli, defs, "alpha", "a-done", "a-one")
    h.transition(cli, "project:work-item", done, "in_progress", "done")
    withdrawn = _work_item(cli, defs, "alpha", "a-withdrawn", "a-one")
    h.transition(cli, "project:work-item", withdrawn, "withdrawn")
    _work_item(cli, defs, "beta", "b-ready", "b-one")
    _work_item(cli, defs, "gone", "gone-ready", "gone-phase")
    return store


def test_groups_records_per_live_effort_and_skips_efforts_without_an_active_goal(seeded):
    snapshot = model.load_snapshot(_target(seeded))
    assert sorted(view.effort for view in snapshot.efforts) == ["alpha", "beta"]
    assert _effort(snapshot, "alpha").goal == "ship alpha"
    assert [task.subject for task in _effort(snapshot, "beta").tasks] == ["b-ready"]


def test_classifies_tasks_with_title_phase_assignee_and_wave(seeded):
    tasks = {task.subject: task for task in _effort(model.load_snapshot(_target(seeded)), "alpha").tasks}
    assert {subject: task.status for subject, task in tasks.items()} == {
        "a-running": "running", "a-ready": "ready", "a-waiting": "waiting",
        "a-done": "done", "a-withdrawn": "withdrawn",
    }
    running = tasks["a-running"]
    assert (running.title, running.phase, running.assignee, running.wave) == ("title of a-running", "a-two", "agent-7", 1)
    assert tasks["a-waiting"].wave == 2


def test_orders_tasks_running_ready_waiting_done_withdrawn(seeded):
    tasks = _effort(model.load_snapshot(_target(seeded)), "alpha").tasks
    assert [task.status for task in tasks] == ["running", "ready", "waiting", "done", "withdrawn"]


def test_reports_phase_ordinal_state_and_done_over_total_excluding_withdrawn(seeded):
    phases = _effort(model.load_snapshot(_target(seeded)), "alpha").phases
    assert [(p.ordinal, p.title, p.state, p.done, p.total) for p in phases] == [
        (1, "title of a-one", "done", 1, 1),
        (2, "title of a-two", "in_progress", 0, 3),
    ]
    assert _effort(model.load_snapshot(_target(seeded)), "beta").phases[0].state == "planned"


def test_collects_needs_you_items_and_drops_resolved_or_corrected_ones(store, cli, defs):
    _goal(cli, defs, "alpha")
    for blocking, scope in ((True, "block-scope"), (False, "open-scope")):
        h.create_generic_record(
            cli, defs, "project:continuity-question", subject="alpha",
            extra_payload={"blocking": blocking, "scope": scope},
        )
    answered = h.create_generic_record(
        cli, defs, "project:continuity-question", subject="alpha",
        extra_payload={"blocking": True, "scope": "answered-scope"},
    )
    h.transition(cli, "project:continuity-question", answered, "answered")
    h.create_generic_record(
        cli, defs, "project:finding", subject="f-human",
        extra_payload={"claim": "human decides", "needs": "human", "effort": "alpha"},
    )
    h.create_generic_record(
        cli, defs, "project:finding", subject="f-agent",
        extra_payload={"claim": "agent decides", "needs": "agent", "effort": "alpha"},
    )
    retracted = h.create_generic_record(
        cli, defs, "project:finding", subject="f-retracted",
        extra_payload={"claim": "retracted claim", "needs": "human", "effort": "alpha"},
    )
    h.transition(cli, "project:finding", retracted, "retracted")
    check_payload = {"method": "manual", "signed_by": "", "result": "pass", "effort": "alpha"}
    h.create_generic_record(cli, defs, "project:check-run", subject="c-unsigned", extra_payload=check_payload)
    h.create_generic_record(
        cli, defs, "project:check-run", subject="c-signed", extra_payload={**check_payload, "signed_by": "ayin"},
    )
    h.create_generic_record(
        cli, defs, "project:check-run", subject="c-automatic", extra_payload={**check_payload, "method": "check"},
    )
    corrected = h.create_generic_record(cli, defs, "project:check-run", subject="c-corrected", extra_payload=check_payload)
    result = cli("correct", "--type", "project:check-run", "--id", corrected["id"], "--payload", json.dumps({"signed_by": "ayin"}))
    assert result.returncode == 0, result.stdout + result.stderr

    items = _effort(model.load_snapshot(_target(store)), "alpha").needs_you
    assert sorted((item.kind, item.text) for item in items if item.kind != "unsigned-check") == [
        ("blocking-question", "block-scope"),
        ("needs-human", "human decides"),
        ("open-question", "open-scope"),
    ]
    assert sorted(item.subject for item in items if item.kind == "unsigned-check") == ["c-unsigned"]
    assert [item.kind for item in items][:1] == ["blocking-question"]


def test_recent_activity_lists_last_24h_newest_first_and_resolves_reports_to_their_effort(store, cli, defs):
    _goal(cli, defs, "alpha")
    _goal(cli, defs, "beta")
    item = _work_item(cli, defs, "alpha", "a-task", "a-phase")
    h.create_generic_record(
        cli, defs, "project:assignment", subject="a-assign",
        extra_payload={"work_item": item["id"], "executor": "sub-1", "effort": "alpha"},
    )
    h.create_generic_record(
        cli, defs, "project:execution-report", subject="a-report",
        extra_payload={"work_item": item["id"], "result": "done it", "verdict": "pass"},
    )
    h.create_generic_record(
        cli, defs, "project:check-run", subject="a-check",
        extra_payload={"method": "check", "signed_by": "", "result": "pass", "effort": "alpha"},
    )
    h.run_cli_48h_ago(
        store, "create", "--type", "project:check-run", "--subject", "a-old-check",
        "--payload", json.dumps({
            "method": "check", "signed_by": "", "result": "pass", "effort": "alpha",
            "criterion_id": "c-1", "revision": "r-1",
        }),
    )

    snapshot = model.load_snapshot(_target(store))
    activity = _effort(snapshot, "alpha").activity
    assert sorted((a.kind, a.subject) for a in activity) == [
        ("assignment", "a-assign"), ("check-run", "a-check"), ("execution-report", "a-report"),
    ]
    stamps = [a.recorded_at for a in activity]
    assert stamps == sorted(stamps, reverse=True)
    assert _effort(snapshot, "beta").activity == []


def test_activity_window_follows_the_supplied_clock(store, cli, defs):
    _goal(cli, defs, "alpha")
    h.create_generic_record(
        cli, defs, "project:check-run", subject="a-check",
        extra_payload={"method": "check", "signed_by": "", "result": "pass", "effort": "alpha"},
    )
    later = datetime.now(timezone.utc) + timedelta(hours=25)
    assert _effort(model.load_snapshot(_target(store), now=later), "alpha").activity == []


def test_change_token_is_stable_until_the_store_changes(store, cli, defs):
    _goal(cli, defs, "alpha")
    target = _target(store)
    first = model.load_snapshot(target).token
    assert model.load_snapshot(target).token == first
    assert model.change_token(target) == first
    _work_item(cli, defs, "alpha", "a-task", "a-phase")
    assert model.change_token(target) != first


def test_update_to_an_existing_record_changes_the_token(store, cli, defs):
    _goal(cli, defs, "alpha")
    item = _work_item(cli, defs, "alpha", "a-task", "a-phase")
    target = _target(store)
    before = model.change_token(target)
    h.transition(cli, "project:work-item", item, "in_progress")
    assert model.change_token(target) != before


def test_raises_a_model_error_when_the_cli_fails(store, monkeypatch):
    monkeypatch.setenv("ADAPTIVE_ARTIFACTS_BIN", "/bin/false")
    with pytest.raises(model.ModelError):
        model.load_snapshot(_target(store))


def test_store_with_no_goals_has_no_efforts(store):
    assert model.load_snapshot(_target(store)).efforts == []
