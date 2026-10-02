"""Tests for scripts/dashboard_model: the dashboard snapshot built from store records."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

import pytest

import helpers as h
from conftest import REPO_ROOT, stamped_store

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


def _seed_models(cli, defs):
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


@pytest.fixture()
def seeded(store):
    stamped_store(store, "model-seeded", lambda root, cli, defs: _seed_models(cli, defs))
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


def test_unsigned_check_reads_as_its_criterion_and_task_not_a_record_id(store, cli, defs):
    _goal(cli, defs, "alpha")
    acceptance = _record(cli, defs, "project:acceptance", "u-task-perf",
                         {"criterion": "pages render", "method": "manual", "verify_command": "", "effort": "alpha",
                          "phase": "a-one"})
    check_payload = {"method": "manual", "signed_by": "", "result": "pass", "revision": "r", "effort": "alpha"}
    _record(cli, defs, "project:check-run", "u-check", {**check_payload, "criterion_id": acceptance["id"]})
    _record(cli, defs, "project:check-run", "u-orphan", {**check_payload, "criterion_id": "rec-missing"})

    items = _effort(model.load_snapshot(_target(store)), "alpha").needs_you
    assert sorted((item.subject, item.text) for item in items) == [
        ("u-orphan", "pass"),
        ("u-task-perf", "pages render pass"),
    ]
    assert not any("rec-" in item.text or "rec-" in item.subject for item in items)


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


def _record(cli, defs, record_type: str, subject: str, payload: dict, body: str | None = None, *rels: str) -> dict:
    args = ["create", "--type", record_type, "--subject", subject, "--payload", json.dumps(payload)]
    for rel in rels:
        args.extend(["--rel", rel])
    body = body if body is not None else h.generic_body(defs[record_type])
    if body:
        args.extend(["--body", body])
    result = cli(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


@pytest.fixture()
def detail_store(store, cli, defs):
    dep = _work_item(cli, defs, "alpha", "d-dep", "a-one")
    h.transition(cli, "project:work-item", dep, "in_progress", "done")
    task = _work_item(cli, defs, "alpha", "d-task", "a-one", f"depends_on:{dep['id']}", assignee="sub-d")
    h.transition(cli, "project:work-item", task, "in_progress")
    blocked = _work_item(cli, defs, "alpha", "d-blocked", "a-two", f"depends_on:{task['id']}")
    sibling = _work_item(cli, defs, "alpha", "d-task-other", "a-one")
    _record(cli, defs, "project:acceptance", "d-task",
            {"criterion": "first", "method": "check", "verify_command": "true", "effort": "alpha", "phase": "a-one"})
    signoff = _record(cli, defs, "project:acceptance", "d-task-signoff",
                      {"criterion": "second", "method": "manual", "verify_command": "", "effort": "alpha", "phase": "a-one"})
    _record(cli, defs, "project:acceptance", "d-task-other",
            {"criterion": "foreign", "method": "check", "verify_command": "true", "effort": "alpha", "phase": "a-one"})
    first = _record(cli, defs, "project:acceptance", "d-task-first",
                    {"criterion": "third", "method": "check", "verify_command": "true", "effort": "alpha", "phase": "a-one"})
    h.run_cli_48h_ago(
        store, "create", "--type", "project:check-run", "--subject", "d-task-signoff", "--payload",
        json.dumps({"criterion_id": signoff["id"], "method": "manual", "result": "fail", "signed_by": "",
                    "revision": "rev-early", "effort": "alpha"}),
    )
    _record(cli, defs, "project:check-run", "d-task-signoff",
            {"criterion_id": signoff["id"], "method": "manual", "result": "pass", "signed_by": "ayin",
             "revision": "rev-late", "effort": "alpha"})
    _record(cli, defs, "project:check-run", "d-task-other",
            {"criterion_id": "x", "method": "check", "result": "pass", "signed_by": "", "revision": "r", "effort": "alpha"})
    _record(cli, defs, "project:check-run", "d-task-first",
            {"criterion_id": first["id"], "method": "check", "result": "pass", "signed_by": "", "revision": "r2", "effort": "beta"})
    assignment = _record(cli, defs, "project:assignment", "d-task",
                         {"work_item": task["id"], "executor": "sub-d", "effort": "alpha"}, "## Orientation\n\nstart here")
    _record(cli, defs, "project:assignment-amendment", "d-task",
            {"assignment": "d-task", "effort": "alpha"}, "## Correction\n\nuse this")
    _record(cli, defs, "project:execution-report", "d-task",
            {"work_item": task["id"], "assignment": assignment["id"], "result": "pass", "verdict": "pass", "revision": "abc"},
            "evidence body")
    _record(cli, defs, "project:execution-report", "d-task-other",
            {"work_item": sibling["id"], "assignment": "x", "result": "pass", "verdict": "pass", "revision": "zzz"}, "foreign body")
    _record(cli, defs, "project:finding", "d-task",
            {"claim": "a claim", "basis": "b", "needs": "agent", "effort": "alpha", "invalidated_when": "w"})
    _record(cli, defs, "project:finding", "d-task-other",
            {"claim": "foreign claim", "basis": "b", "needs": "agent", "effort": "alpha", "invalidated_when": "w"})
    _record(cli, defs, "project:decision", "d-task-choice",
            {"choice": "go left", "alternatives": "right", "effort": "alpha", "phase": "a-one"})
    _record(cli, defs, "project:failed-attempt", "d-task",
            {"attempted_action": "tried x", "retry_when": "later", "effort": "alpha"})
    _record(cli, defs, "project:investigation-observation", "d-task",
            {"what_was_observed": "saw y", "effort": "alpha", "environment": "e", "observed_time": "t", "source": "s"})
    return store, task, dep, blocked


def _detail(detail_store) -> model.TaskDetail:
    store, task, _, _ = detail_store
    return model.load_task_detail(_target(store), task["id"])


def test_detail_returns_the_work_item_fields(detail_store):
    detail = _detail(detail_store)
    assert (detail.id, detail.subject, detail.title, detail.status) == (
        detail_store[1]["id"], "d-task", "title of d-task", "running")
    assert (detail.phase, detail.assignee, detail.wave, detail.effort) == ("a-one", "sub-d", 2, "alpha")
    assert detail.body


def test_detail_links_dependencies_and_blocked_tasks_with_subject_and_status(detail_store):
    detail = _detail(detail_store)
    assert [(t.subject, t.status) for t in detail.depends_on] == [("d-dep", "done")]
    assert [(t.subject, t.status) for t in detail.blocks] == [("d-blocked", "waiting")]


def test_detail_pairs_each_acceptance_with_its_latest_check_run(detail_store):
    by_subject = {a.subject: a for a in _detail(detail_store).acceptances}
    assert sorted(by_subject) == ["d-task", "d-task-first", "d-task-signoff"]
    signoff = by_subject["d-task-signoff"]
    assert (signoff.criterion, signoff.method) == ("second", "manual")
    assert (signoff.check.result, signoff.check.method, signoff.check.signed_by, signoff.check.revision) == (
        "pass", "manual", "ayin", "rev-late")
    assert by_subject["d-task"].check is None
    assert by_subject["d-task-first"].check is None


def test_detail_timeline_is_oldest_first_and_carries_report_bodies(detail_store):
    timeline = _detail(detail_store).timeline
    assert [e.kind for e in timeline if e.kind != "check-run"] == ["assignment", "assignment-amendment", "execution-report"]
    stamps = [e.recorded_at for e in timeline]
    assert stamps == sorted(stamps)
    report = next(e for e in timeline if e.kind == "execution-report")
    assert report.body.strip() == "evidence body"
    assert sum(e.kind == "check-run" for e in timeline) == 2


def test_detail_timeline_events_carry_revision_for_reports_and_check_runs_only(detail_store):
    timeline = _detail(detail_store).timeline
    revisions = {e.kind: e.revision for e in timeline if e.kind != "check-run"}
    assert revisions == {"assignment": "", "assignment-amendment": "", "execution-report": "abc"}
    assert sorted(e.revision for e in timeline if e.kind == "check-run") == ["rev-early", "rev-late"]


def test_detail_lists_related_findings_decisions_attempts_and_observations(detail_store):
    related = {(r.kind, r.text) for r in _detail(detail_store).related}
    assert related == {
        ("finding", "a claim"), ("decision", "go left"), ("failed-attempt", "tried x"),
        ("observation", "saw y"),
    }


def test_detail_ignores_a_task_whose_slug_shares_a_prefix(detail_store):
    detail = _detail(detail_store)
    texts = [e.body for e in detail.timeline] + [r.text for r in detail.related]
    assert not any("foreign" in text for text in texts)
    assert all(a.criterion != "foreign" for a in detail.acceptances)


def test_detail_uses_three_cli_calls(detail_store, monkeypatch):
    calls = []
    real = model.subprocess.run
    monkeypatch.setattr(model.subprocess, "run", lambda cmd, **kw: calls.append(cmd) or real(cmd, **kw))
    _detail(detail_store)
    assert len([cmd for cmd in calls if cmd[0] != "git"]) == 3


def test_detail_of_an_unknown_id_raises_a_model_error(store):
    with pytest.raises(model.ModelError):
        model.load_task_detail(_target(store), "rec-missing")


def _signoff_task(cli, defs, effort, phase, subject, manual_signed_by=None, result="pass"):
    task = _work_item(cli, defs, effort, subject, phase)
    h.transition(cli, "project:work-item", task, "in_progress")
    acceptance = _record(cli, defs, "project:acceptance", subject,
                         {"criterion": "reviewed", "method": "manual", "verify_command": "", "effort": effort, "phase": phase})
    if manual_signed_by is not None:
        _record(cli, defs, "project:check-run", subject,
                {"criterion_id": acceptance["id"], "method": "manual", "result": result,
                 "signed_by": manual_signed_by, "revision": "r", "effort": effort})
    return task


def _awaiting(store, effort="alpha"):
    phases = _effort(model.load_snapshot(_target(store)), effort).phases
    return {p.subject: p.awaiting_signoff for p in phases}


def test_phase_awaits_sign_off_when_every_open_task_waits_only_on_an_unsigned_manual_check(store, cli, defs):
    _goal(cli, defs, "alpha")
    for ordinal, name in enumerate(("p-wait", "p-plain", "p-mixed", "p-signed", "p-failed", "p-done"), 1):
        _phase(cli, defs, "alpha", name, ordinal, "in_progress")
    _signoff_task(cli, defs, "alpha", "p-wait", "t-wait", manual_signed_by="")
    plain = _work_item(cli, defs, "alpha", "t-plain", "p-plain")
    h.transition(cli, "project:work-item", plain, "in_progress")
    _signoff_task(cli, defs, "alpha", "p-mixed", "t-mixed", manual_signed_by="")
    plain = _work_item(cli, defs, "alpha", "t-other", "p-mixed")
    h.transition(cli, "project:work-item", plain, "in_progress")
    _signoff_task(cli, defs, "alpha", "p-signed", "t-signed", manual_signed_by="ayin")
    _signoff_task(cli, defs, "alpha", "p-failed", "t-failed", manual_signed_by="", result="fail")
    finished = _work_item(cli, defs, "alpha", "t-finished", "p-done")
    h.transition(cli, "project:work-item", finished, "in_progress", "done")
    assert _awaiting(store) == {
        "p-wait": True, "p-plain": False, "p-mixed": False, "p-signed": False, "p-failed": False, "p-done": False,
    }


def test_a_phase_with_a_done_task_and_one_task_awaiting_sign_off_is_awaiting(store, cli, defs):
    _goal(cli, defs, "alpha")
    _phase(cli, defs, "alpha", "p-one", 1, "in_progress")
    finished = _work_item(cli, defs, "alpha", "t-finished", "p-one")
    h.transition(cli, "project:work-item", finished, "in_progress", "done")
    _signoff_task(cli, defs, "alpha", "p-one", "t-wait", manual_signed_by="")
    assert _awaiting(store) == {"p-one": True}


def test_phase_detail_carries_body_decisions_constraints_and_tasks(store, cli, defs):
    _goal(cli, defs, "alpha")
    _phase(cli, defs, "alpha", "p-one", 1, "in_progress")
    _phase(cli, defs, "alpha", "p-two", 2)
    task = _work_item(cli, defs, "alpha", "t-one", "p-one")
    _work_item(cli, defs, "alpha", "t-elsewhere", "p-two")
    _record(cli, defs, "project:decision", "p-one-choice",
            {"choice": "go left", "alternatives": "right", "effort": "alpha", "phase": "p-one"})
    _record(cli, defs, "project:decision", "p-two-choice",
            {"choice": "go right", "alternatives": "left", "effort": "alpha", "phase": "p-two"})
    _record(cli, defs, "project:constraint", "p-one-limit",
            {"statement": "no network", "applies_to": "p-one", "effort": "alpha"})
    _record(cli, defs, "project:constraint", "other-limit",
            {"statement": "elsewhere", "applies_to": "p-two", "effort": "alpha"})
    detail = model.load_phase_detail(_target(store), "alpha", "p-one")
    assert (detail.subject, detail.title, detail.state, detail.awaiting_signoff) == ("p-one", "title of p-one", "in_progress", False)
    assert "placeholder text for Problem" in detail.body
    assert [d.text for d in detail.decisions] == ["go left"]
    assert [c.text for c in detail.constraints] == ["no network"]
    assert [t.id for t in detail.tasks] == [task["id"]]


def test_phase_detail_for_an_unknown_phase_raises(store, cli, defs):
    _goal(cli, defs, "alpha")
    with pytest.raises(model.ModelError):
        model.load_phase_detail(_target(store), "alpha", "nope")


def _phase_row(state: str) -> model.PhaseRow:
    return model.PhaseRow(subject=f"p-{state}", title="", ordinal=1, state=state, done=0, total=0)


def _task_row(status: str) -> model.TaskRow:
    return model.TaskRow(id=status, subject=f"t-{status}", title="", phase="", assignee="", wave=None, status=status)


@pytest.mark.parametrize(("phases", "tasks", "finished"), [
    (["done"], ["done", "withdrawn"], True),
    ([], ["done"], True),
    (["done", "done"], [], True),
    ([], [], False),
    ([], ["withdrawn"], False),
    (["done", "in_progress"], ["done"], False),
    (["planned"], [], False),
    (["done"], ["done", "ready"], False),
    (["done"], ["running"], False),
    (["done"], ["waiting"], False),
])
def test_effort_is_finished_only_when_every_phase_and_counted_task_is_done(phases, tasks, finished):
    view = model.EffortView(
        effort="e", goal="", phases=[_phase_row(s) for s in phases], tasks=[_task_row(s) for s in tasks],
    )
    assert view.finished is finished


def test_finished_efforts_sort_after_live_ones(store, cli, defs):
    for effort in ("alpha", "beta", "gamma"):
        _goal(cli, defs, effort)
    _phase(cli, defs, "alpha", "a-one", 1, "in_progress", "done")
    done = _work_item(cli, defs, "alpha", "a-done", "a-one")
    h.transition(cli, "project:work-item", done, "in_progress", "done")
    _phase(cli, defs, "beta", "b-one", 1, "in_progress")
    _work_item(cli, defs, "beta", "b-ready", "b-one")
    snapshot = model.load_snapshot(_target(store))
    assert [(view.effort, view.finished) for view in snapshot.efforts] == [
        ("beta", False), ("gamma", False), ("alpha", True),
    ]
