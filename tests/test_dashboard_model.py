"""Tests for dashboard.model: the dashboard snapshot built from store records."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

import pytest

import helpers as h
from conftest import CONTRACT_PATH, REPO_ROOT, make_git_repo, run_cli, stamped_store

sys.path.insert(0, str(REPO_ROOT))
from dashboard import artifact_store  # noqa: E402
from dashboard import model  # noqa: E402


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


def test_needs_you_items_carry_record_type_and_full_body(store, cli, defs):
    _goal(cli, defs, "alpha")
    _record(cli, defs, "project:continuity-question", "alpha",
            {"subject": "alpha", "owner": "ayin", "blocking": True, "scope": "which renderer"},
            "Pick the PDF renderer before the render task starts.")
    _record(cli, defs, "project:finding", "f-human",
            {"claim": "human decides", "basis": "b", "needs": "human", "effort": "alpha", "invalidated_when": "w"})

    items = {item.kind: item for item in _effort(model.load_snapshot(_target(store)), "alpha").needs_you}
    assert items["blocking-question"].record_type == "project:continuity-question"
    assert items["blocking-question"].body.strip() == "Pick the PDF renderer before the render task starts."
    assert items["needs-human"].record_type == "project:finding"
    assert "placeholder text for Follow-up." in items["needs-human"].body


def test_needs_you_items_link_to_the_task_with_the_longest_matching_slug(store, cli, defs):
    _goal(cli, defs, "alpha")
    _goal(cli, defs, "beta")
    pdf = _work_item(cli, defs, "alpha", "pdf", "a-one")
    render = _work_item(cli, defs, "alpha", "pdf-render", "a-one")
    _work_item(cli, defs, "beta", "pdf-render-check", "b-one")
    finding = {"basis": "b", "needs": "human", "effort": "alpha", "invalidated_when": "w"}
    _record(cli, defs, "project:finding", "pdf-render", {**finding, "claim": "exact"})
    _record(cli, defs, "project:finding", "pdf-render-check", {**finding, "claim": "prefix"})
    _record(cli, defs, "project:finding", "pdfx-render", {**finding, "claim": "no boundary"})
    _record(cli, defs, "project:finding", "pdf-other", {**finding, "claim": "short prefix"})
    acceptance = _record(cli, defs, "project:acceptance", "pdf-render-perf",
                         {"criterion": "pages render", "method": "manual", "verify_command": "", "effort": "alpha",
                          "phase": "a-one"})
    _record(cli, defs, "project:check-run", "u-check",
            {"method": "manual", "signed_by": "", "result": "pass", "revision": "r", "effort": "alpha",
             "criterion_id": acceptance["id"]})

    items = _effort(model.load_snapshot(_target(store)), "alpha").needs_you
    assert sorted((item.text, item.task_id) for item in items) == sorted([
        ("exact", render["id"]),
        ("prefix", render["id"]),
        ("no boundary", ""),
        ("short prefix", pdf["id"]),
        ("pages render pass", render["id"]),
    ])


def test_needs_you_effort_level_question_links_to_no_task(store, cli, defs):
    _goal(cli, defs, "alpha")
    _work_item(cli, defs, "alpha", "alpha-task", "a-one")
    h.create_generic_record(
        cli, defs, "project:continuity-question", subject="alpha",
        extra_payload={"blocking": False, "scope": "effort scope"},
    )

    items = _effort(model.load_snapshot(_target(store)), "alpha").needs_you
    assert [(item.kind, item.task_id) for item in items] == [("open-question", "")]


def test_needs_you_item_defaults_keep_the_four_field_constructor_working():
    item = model.NeedsYouItem("needs-human", "rec-1", "s", "t")
    assert (item.record_type, item.body, item.task_id) == ("", "", "")


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


def test_activity_marks_failed_check_runs_and_failed_reports_only(store, cli, defs):
    _goal(cli, defs, "alpha")
    item = _work_item(cli, defs, "alpha", "a-task", "a-phase")
    h.create_generic_record(
        cli, defs, "project:assignment", subject="a-assign",
        extra_payload={"work_item": item["id"], "executor": "sub-1", "effort": "alpha"},
    )
    for subject, result, verdict in (
        ("a-report-pass", "pass", "pass"), ("a-report-result-fail", "fail", "pass"), ("a-report-verdict-fail", "pass", "fail"),
    ):
        h.create_generic_record(
            cli, defs, "project:execution-report", subject=subject,
            extra_payload={"work_item": item["id"], "result": result, "verdict": verdict},
        )
    for subject, result in (("a-check-pass", "pass"), ("a-check-fail", "fail")):
        h.create_generic_record(
            cli, defs, "project:check-run", subject=subject,
            extra_payload={"method": "check", "signed_by": "", "result": result, "effort": "alpha"},
        )

    activity = _effort(model.load_snapshot(_target(store)), "alpha").activity
    assert sorted(a.subject for a in activity if a.failed) == [
        "a-check-fail", "a-report-result-fail", "a-report-verdict-fail",
    ]
    assert len(activity) == 6


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


def test_skips_an_effort_whose_goal_is_closed(store, cli, defs):
    _goal(cli, defs, "open-one")
    closed = h.create_generic_record(
        cli, defs, "project:active-goal", subject="closed-one",
        extra_payload={"goal": "ship closed-one", "kind": "deliver"},
    )
    result = cli(
        "supersede", "--type", "project:active-goal", "--id", closed["id"],
        "--expected-revision", closed["revision"], "--payload", json.dumps({**closed["payload"], "status": "closed"}),
    )
    assert result.returncode == 0, result.stdout + result.stderr

    assert [view.effort for view in model.load_snapshot(_target(store)).efforts] == ["open-one"]


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


def test_detail_uses_four_cli_calls(detail_store, monkeypatch):
    calls = []
    real = model.subprocess.run
    monkeypatch.setattr(model.subprocess, "run", lambda cmd, **kw: calls.append(cmd) or real(cmd, **kw))
    _detail(detail_store)
    assert len([cmd for cmd in calls if cmd[0] != "git"]) == 4


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


def _assign(cli, defs, work_item: str, executor: str) -> dict:
    return h.create_generic_record(
        cli, defs, "project:assignment", subject=f"{executor}-assign",
        extra_payload={"work_item": work_item, "executor": executor, "effort": "alpha"},
    )


def test_waits_on_lists_only_unfinished_dependency_slugs_in_dependency_order(store, cli, defs):
    _goal(cli, defs, "alpha")
    done = _work_item(cli, defs, "alpha", "w-done", "p-one")
    h.transition(cli, "project:work-item", done, "in_progress", "done")
    later = _work_item(cli, defs, "alpha", "w-later", "p-one")
    active = _work_item(cli, defs, "alpha", "w-active", "p-one")
    h.transition(cli, "project:work-item", active, "in_progress")
    _work_item(
        cli, defs, "alpha", "w-task", "p-one",
        f"depends_on:{later['id']}", f"depends_on:{done['id']}", f"depends_on:{active['id']}",
    )
    tasks = {task.subject: task for task in _effort(model.load_snapshot(_target(store)), "alpha").tasks}
    assert tasks["w-task"].waits_on == ("w-later", "w-active")
    assert tasks["w-later"].waits_on == ()


def test_phase_detail_task_rows_carry_waits_on(store, cli, defs):
    _goal(cli, defs, "alpha")
    _phase(cli, defs, "alpha", "p-one", 1, "in_progress")
    dep = _work_item(cli, defs, "alpha", "w-dep", "p-one")
    _work_item(cli, defs, "alpha", "w-task", "p-one", f"depends_on:{dep['id']}")
    tasks = {t.subject: t for t in model.load_phase_detail(_target(store), "alpha", "p-one").tasks}
    assert tasks["w-task"].waits_on == ("w-dep",)


def test_running_since_is_the_latest_assignment_time_for_a_running_task(store, cli, defs):
    _goal(cli, defs, "alpha")
    running = _work_item(cli, defs, "alpha", "r-running", "p-one")
    h.transition(cli, "project:work-item", running, "in_progress")
    h.run_cli_48h_ago(
        store, "create", "--type", "project:assignment", "--subject", "old-assign",
        "--payload", json.dumps({"work_item": running["id"], "executor": "old", "effort": "alpha"}),
        "--body", h.generic_body(defs["project:assignment"]),
    )
    latest = _assign(cli, defs, "r-running", "new")
    tasks = {task.subject: task for task in _effort(model.load_snapshot(_target(store)), "alpha").tasks}
    assert tasks["r-running"].running_since == datetime.fromisoformat(latest["recorded_at"])


def test_running_since_is_none_unless_the_task_is_in_progress(store, cli, defs):
    _goal(cli, defs, "alpha")
    ready = _work_item(cli, defs, "alpha", "r-ready", "p-one")
    _assign(cli, defs, ready["id"], "ready")
    done = _work_item(cli, defs, "alpha", "r-done", "p-one")
    _assign(cli, defs, done["id"], "done")
    h.transition(cli, "project:work-item", done, "in_progress", "done")
    unassigned = _work_item(cli, defs, "alpha", "r-unassigned", "p-one")
    h.transition(cli, "project:work-item", unassigned, "in_progress")
    tasks = {task.subject: task for task in _effort(model.load_snapshot(_target(store)), "alpha").tasks}
    assert [tasks[s].running_since for s in ("r-ready", "r-done", "r-unassigned")] == [None, None, None]


def test_task_row_defaults_leave_waits_on_empty_and_running_since_unset():
    row = _task_row("running")
    assert (row.waits_on, row.running_since) == ((), None)


def _merged_store(cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="merged",
        extra_payload={"goal": "ship merged", "kind": "deliver", "merged_from": ["old-a", "old-b"]},
    )
    _phase(cli, defs, "merged", "m-one", 1, "in_progress")
    task = _work_item(cli, defs, "merged", "m-task", "m-one")
    h.transition(cli, "project:work-item", task, "in_progress")
    _record(cli, defs, "project:check-run", "m-task",
            {"criterion_id": "x", "method": "manual", "result": "pass", "signed_by": "", "revision": "r", "effort": "old-a"})
    return task


def test_snapshot_counts_a_check_run_of_a_merged_effort_under_the_new_effort(store, cli, defs):
    _merged_store(cli, defs)
    view = _effort(model.load_snapshot(_target(store)), "merged")
    assert [item.kind for item in view.needs_you] == ["unsigned-check"]
    assert [item.kind for item in view.activity] == ["check-run"]


def test_task_detail_lists_a_check_run_recorded_under_a_merged_effort(store, cli, defs):
    task = _merged_store(cli, defs)
    detail = model.load_task_detail(_target(store), task["id"])
    assert [e.kind for e in detail.timeline] == ["check-run"]


def _body(defs, record_type: str, fills: dict | None = None) -> str | None:
    required = defs[record_type].get("required_sections") or []
    if not required:
        return None
    fills = fills or {}
    return "\n\n".join(f"## {name}\n\n{fills.get(name, 'placeholder.')}" for name in required)


def _spec(cli, defs, phase: str, requirements: str = "R1", *, weight: str = "light", body: str | None = None, non_goals: str = "none", effort: str = "alpha") -> dict:
    if body is None:
        lines = "\n".join(f"{part.strip()}: text of {part.strip()}" for part in requirements.split(",") if part.strip())
        body = _body(defs, "project:specification", {"Requirements": lines, "Non-goals": non_goals})
    return _record(cli, defs, "project:specification", phase, {
        "weight": weight, "phase": phase, "effort": effort, "requirements": requirements,
    }, body)


def _design(cli, defs, phase: str, decisions: str = "", *, effort: str = "alpha") -> dict:
    return _record(cli, defs, "project:design", phase, {"phase": phase, "effort": effort, "decisions": decisions})


def _decision(cli, defs, subject: str, phase: str, choice: str, *, effort: str = "alpha") -> dict:
    return _record(cli, defs, "project:decision", subject, {
        "choice": choice, "alternatives": "other", "phase": phase, "effort": effort,
    })


def _task(cli, defs, subject: str, phase: str, requirements: str = "", decisions: str = "", *, done: bool = False, effort: str = "alpha") -> dict:
    payload = {"title": subject, "phase": phase, "kind": "deliver", "assignee": "", "effort": effort}
    if requirements:
        payload["requirements"] = requirements
    if decisions:
        payload["decisions"] = decisions
    record = _record(cli, defs, "project:work-item", subject, payload)
    if done:
        record = h.transition(cli, "project:work-item", record, "in_progress", "done")
    return record


def _accept(cli, defs, subject: str, phase: str, requirement: str, *, effort: str = "alpha") -> dict:
    return _record(cli, defs, "project:acceptance", subject, {
        "criterion": subject, "method": "check", "phase": phase, "effort": effort,
        "verify_command": "true", "requirement": requirement,
    })


def _check(cli, defs, subject: str, acceptance_id: str, result: str, requirement: str, evidence_kind: str) -> dict:
    return _record(cli, defs, "project:check-run", subject, {
        "criterion_id": acceptance_id, "revision": "dirty", "result": result, "effort": "alpha",
        "method": "check", "signed_by": "ayin", "requirement": requirement, "evidence_kind": evidence_kind,
    })


def _assessment(cli, defs, phase: str, requirement: str, **fields) -> dict:
    payload = {
        "requirement": requirement, "phase": phase, "effort": fields.pop("effort", "alpha"), "missing": "",
        "confidence": "high", "status": "failed", "next": "execute", "level": "implementation",
    }
    payload.update(fields)
    if payload.get("status") == "verified":
        payload.pop("level", None)
    return _record(cli, defs, "project:assessment", f"{phase}-{requirement}", payload)


def _supersede(cli, defs, record_type: str, record: dict, payload: dict) -> dict:
    args = [
        "supersede", "--type", record_type, "--id", record["id"],
        "--expected-revision", record["revision"], "--payload", json.dumps({**record["payload"], **payload}),
    ]
    body = _body(defs, record_type)
    if body:
        args.extend(["--body", body])
    result = cli(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def _report(cli, defs, phase: str, result: str, conflicts: str = "none", *, subject: str | None = None, effort: str = "alpha") -> dict:
    body = _body(defs, "project:integration-report", {"Conflicts": conflicts})
    return _record(cli, defs, "project:integration-report", subject or f"{phase}-report", {
        "phase": phase, "effort": effort, "result": result, "revision": "dirty",
    }, body)


def _release(cli, defs, phase: str, state: str, *, effort: str = "alpha") -> dict:
    return _record(cli, defs, "project:release", phase, {"state": state, "phase": phase, "effort": effort})


ROW_SPEC = """## Non-goals

R1: decoy

No new screen.

## Requirements

R1: alpha holds
R2: beta holds

## Acceptance criteria

ok

## Constraints

ok

## Invariants

ok

## Assumptions

ok
"""


def test_evidence_requirement_rows_join_by_phase_and_id(store, cli, defs):
    _goal(cli, defs, "alpha")
    _phase(cli, defs, "alpha", "p-rows", 1, "in_progress")
    _phase(cli, defs, "alpha", "p-other", 2)
    _spec(cli, defs, "p-rows", "R1, R2", weight="full", body=ROW_SPEC)
    _design(cli, defs, "p-rows", "use-columns")
    _decision(cli, defs, "use-columns", "p-rows", "two")
    _task(cli, defs, "row-a", "p-rows", "R1")
    _task(cli, defs, "row-b", "p-rows", "R1")
    _task(cli, defs, "row-c", "p-rows", "R2")
    _task(cli, defs, "row-d", "p-rows", "R10")
    verified = _assessment(cli, defs, "p-rows", "R1", status="verified", next="release", confidence="high")
    _supersede(cli, defs, "project:assessment", verified, {
        "status": "failed", "level": "design", "next": "design", "confidence": "high",
    })
    own = _accept(cli, defs, "row-c-check", "p-rows", "R2")
    h.run_cli_48h_ago(
        store, "create", "--type", "project:check-run", "--subject", "row-c-pass",
        "--payload", json.dumps({
            "criterion_id": own["id"], "revision": "dirty", "result": "pass", "effort": "alpha",
            "method": "check", "signed_by": "ayin", "requirement": "R2", "evidence_kind": "unit",
        }),
    )
    _check(cli, defs, "row-c-fail", own["id"], "fail", "R2", "integration")
    other = _accept(cli, defs, "other-check", "p-other", "R2")
    _check(cli, defs, "other-pass", other["id"], "pass", "R2", "unit")

    view = _effort(model.load_snapshot(_target(store)), "alpha")
    phase = next(row for row in view.phases if row.subject == "p-rows")
    evidence = phase.evidence
    assert evidence is not None
    assert evidence.phase == "p-rows"
    assert evidence.weight == "full"
    assert evidence.non_goals == "R1: decoy\n\nNo new screen."
    assert [(item.subject, item.choice) for item in evidence.decisions] == [("use-columns", "two")]
    assert [(row.id, row.phase, row.text, row.status, row.next, row.tasks) for row in evidence.requirements] == [
        ("R1", "p-rows", "alpha holds", "failed", "design", 2),
        ("R2", "p-rows", "beta holds", "unassessed", "", 1),
    ]
    assert evidence.requirements[0].latest_check is None
    assert evidence.requirements[1].latest_check.result == "fail"
    detail = model.load_phase_detail(_target(store), "alpha", "p-rows")
    assert [row.id for row in detail.evidence.requirements] == ["R1", "R2"]


def test_evidence_requirement_detail_includes_superseded_assessments(store, cli, defs, monkeypatch):
    _goal(cli, defs, "alpha")
    _phase(cli, defs, "alpha", "p-detail", 1, "in_progress")
    _spec(cli, defs, "p-detail", "R1", body=_body(defs, "project:specification", {
        "Requirements": "R1: the traced requirement",
    }))
    _design(cli, defs, "p-detail", "design-only")
    _decision(cli, defs, "design-only", "p-detail", "nope")
    _decision(cli, defs, "pick-a", "p-detail", "alpha")
    _decision(cli, defs, "pick-b", "p-detail", "beta")
    traced = _task(cli, defs, "trace-yes", "p-detail", "R1", "pick-a, pick-b")
    _task(cli, defs, "trace-no", "p-detail", "R2", "design-only")
    acceptance = _accept(cli, defs, "trace-yes-acc", "p-detail", "R1")
    _accept(cli, defs, "other-acc", "p-detail", "R2")
    h.run_cli_48h_ago(
        store, "create", "--type", "project:check-run", "--subject", "trace-early",
        "--payload", json.dumps({
            "criterion_id": acceptance["id"], "revision": "dirty", "result": "fail", "effort": "alpha",
            "method": "check", "signed_by": "ayin", "requirement": "R1", "evidence_kind": "integration",
        }),
    )
    _check(cli, defs, "trace-late", acceptance["id"], "pass", "R1", "unit")
    first = _assessment(
        cli, defs, "p-detail", "R1", status="failed", level="implementation", next="execute", confidence="low",
    )
    second = _supersede(cli, defs, "project:assessment", first, {
        "status": "failed", "level": "design", "next": "design", "confidence": "high",
    })

    calls = []
    real = model.subprocess.run

    def spy(cmd, **kwargs):
        calls.append(cmd)
        return real(cmd, **kwargs)

    monkeypatch.setattr(model.subprocess, "run", spy)
    detail = model.load_requirement_detail(_target(store), "alpha", "p-detail", "R1")
    assert any(
        "project:assessment" in cmd and "--state" in cmd and "superseded" in cmd for cmd in calls
    )
    assert (detail.phase, detail.id, detail.text, detail.status, detail.next) == (
        "p-detail", "R1", "the traced requirement", "failed", "design",
    )
    assert [(item.subject, item.choice) for item in detail.decisions] == [("pick-a", "alpha"), ("pick-b", "beta")]
    assert [task.id for task in detail.tasks] == [traced["id"]]
    assert len(detail.acceptances) == 1
    assert (detail.acceptances[0].check.result, detail.acceptances[0].check.evidence_kind) == ("pass", "unit")
    assert [(item.id, item.status, item.level, item.next, item.confidence) for item in detail.assessments] == [
        (first["id"], "failed", "implementation", "execute", "low"),
        (second["id"], "failed", "design", "design", "high"),
    ]


def test_evidence_activity_marks_upstream_and_failed(store, cli, defs):
    _goal(cli, defs, "alpha")
    for ordinal, subject in enumerate(("act", "act-pass", "act-block", "act-bad", "act-ok", "act-old"), 1):
        _phase(cli, defs, "alpha", subject, ordinal)
        _spec(cli, defs, subject, "R1, R2, R3" if subject == "act" else "R1")
    old_body = _body(defs, "project:assessment")
    h.run_cli_48h_ago(
        store, "create", "--type", "project:assessment", "--subject", "act-old-R9",
        "--payload", json.dumps({
            "requirement": "R9", "status": "failed", "level": "implementation", "next": "execute",
            "confidence": "high", "phase": "act-old", "effort": "alpha", "missing": "",
        }),
        "--body", old_body,
    )
    h.run_cli_48h_ago(
        store, "create", "--type", "project:integration-report", "--subject", "act-old-report",
        "--payload", json.dumps({"phase": "act-old", "effort": "alpha", "result": "fail", "revision": "dirty"}),
        "--body", _body(defs, "project:integration-report"),
    )
    previous = _assessment(
        cli, defs, "act", "R1", status="failed", level="implementation", next="execute", confidence="high",
    )
    _supersede(cli, defs, "project:assessment", previous, {
        "status": "failed", "level": "design", "next": "design", "confidence": "low",
    })
    _assessment(cli, defs, "act", "R2", status="verified", next="release", confidence="high")
    _assessment(cli, defs, "act", "R3", status="blocked", level="plan", next="plan", confidence="high")
    _report(cli, defs, "act", "fail", "ports disagree")
    _report(cli, defs, "act-pass", "pass", "clean")
    _report(cli, defs, "act-block", "blocked", "waiting")
    _release(cli, defs, "act-bad", "failed")
    _release(cli, defs, "act-ok", "ready")

    activity = _effort(model.load_snapshot(_target(store)), "alpha").activity
    assert all("R9" not in item.summary and item.subject != "act-old-report" for item in activity)
    assessments = [item for item in activity if item.kind == "assessment"]
    assert sorted(item.summary for item in assessments if item.summary.startswith("R1 ")) == [
        "R1 failed design upstream level implementation to design",
        "R1 failed execute",
    ]
    assert all(item.failed for item in assessments if item.summary.startswith("R1 "))
    verified = next(item for item in assessments if item.summary.startswith("R2 "))
    assert verified.summary == "R2 verified release"
    assert verified.failed is False
    blocked = next(item for item in assessments if item.summary.startswith("R3 "))
    assert blocked.summary == "R3 blocked plan upstream"
    assert blocked.failed is True
    assert {(item.summary, item.failed) for item in activity if item.kind == "integration"} == {
        ("act fail", True), ("act-pass pass", False), ("act-block blocked", True),
    }
    assert {(item.summary, item.failed) for item in activity if item.kind == "release"} == {
        ("act-bad failed", True), ("act-ok ready", False),
    }


def test_evidence_needs_you_for_routes_and_integration(store, cli, defs):
    _goal(cli, defs, "alpha")
    h.create_generic_record(
        cli, defs, "project:continuity-question", subject="alpha",
        extra_payload={"blocking": True, "scope": "hold"},
    )
    cases = {
        "n-up": dict(status="failed", level="design", next="design", confidence="high"),
        "n-block": dict(status="blocked", level="verification", next="verify", confidence="high"),
        "n-low": dict(status="failed", level="integration", next="integrate", confidence="low"),
        "n-exec": dict(status="failed", level="implementation", next="execute", confidence="low"),
        "n-ver": dict(status="failed", level="verification", next="verify", confidence="low"),
        "n-ins": dict(status="insufficient", level="specification", next="specify", confidence="low"),
        "n-execblock": dict(status="blocked", level="implementation", next="execute", confidence="high"),
    }
    for ordinal, (subject, fields) in enumerate(cases.items(), 1):
        _phase(cli, defs, "alpha", subject, ordinal)
        _spec(cli, defs, subject)
        _assessment(cli, defs, subject, "R1", **fields)
    for ordinal, subject in enumerate(("n-fail", "n-blocked", "n-pass"), len(cases) + 1):
        _phase(cli, defs, "alpha", subject, ordinal)
        _spec(cli, defs, subject)
    _report(cli, defs, "n-fail", "fail", "ports disagree")
    _report(cli, defs, "n-blocked", "blocked", "stuck")
    h.run_cli_48h_ago(
        store, "create", "--type", "project:integration-report", "--subject", "n-pass-old",
        "--payload", json.dumps({"phase": "n-pass", "effort": "alpha", "result": "fail", "revision": "dirty"}),
        "--body", _body(defs, "project:integration-report", {"Conflicts": "old"}),
    )
    _report(cli, defs, "n-pass", "pass", "clean", subject="n-pass-new")

    view = _effort(model.load_snapshot(_target(store)), "alpha")
    assert model.NEEDS_ORDER[:3] == ("blocking-question", "loop-route", "integration")
    kinds = [item.kind for item in view.needs_you]
    assert kinds == sorted(kinds, key=lambda kind: model.NEEDS_ORDER.index(kind))
    assert kinds[0] == "blocking-question"
    routes = [item for item in view.needs_you if item.kind == "loop-route"]
    assert sorted((item.phase, item.requirement, item.status, item.next) for item in routes) == [
        ("n-block", "R1", "blocked", "verify"),
        ("n-low", "R1", "failed", "integrate"),
        ("n-up", "R1", "failed", "design"),
    ]
    assert all(item.requirement in item.text and item.status in item.text and item.next in item.text for item in routes)
    integrations = [item for item in view.needs_you if item.kind == "integration"]
    assert sorted((item.phase, item.requirement, item.result) for item in integrations) == [
        ("n-blocked", "", "blocked"),
        ("n-fail", "", "fail"),
    ]
    assert all(item.phase in item.text and item.result in item.text for item in integrations)
    assert not any(item.phase in {"n-exec", "n-ver", "n-ins", "n-execblock", "n-pass"} for item in view.needs_you)
    by_phase = {phase.subject: phase for phase in view.phases}
    assert (by_phase["n-fail"].evidence.integration.result, by_phase["n-fail"].evidence.integration.conflicts) == (
        "fail", "ports disagree",
    )
    assert by_phase["n-pass"].evidence.integration.result == "pass"
    assert by_phase["n-pass"].evidence.integration.conflicts == "clean"


def test_evidence_release_ready_sets_flags_and_leaves_finished(store, cli, defs):
    _goal(cli, defs, "alpha")
    _goal(cli, defs, "beta")
    _goal(cli, defs, "gamma")
    _phase(cli, defs, "alpha", "rel-open", 1, "in_progress")
    _spec(cli, defs, "rel-open")
    _task(cli, defs, "rel-open-task", "rel-open")
    _release(cli, defs, "rel-open", "ready")
    _phase(cli, defs, "beta", "rel-done", 1, "in_progress", "done")
    _spec(cli, defs, "rel-done", effort="beta")
    _task(cli, defs, "rel-done-task", "rel-done", done=True, effort="beta")
    _release(cli, defs, "rel-done", "ready", effort="beta")
    _phase(cli, defs, "gamma", "rel-failed", 1, "in_progress")
    _spec(cli, defs, "rel-failed", effort="gamma")
    _release(cli, defs, "rel-failed", "failed", effort="gamma")

    snapshot = model.load_snapshot(_target(store))
    alpha = _effort(snapshot, "alpha")
    beta = _effort(snapshot, "beta")
    gamma = _effort(snapshot, "gamma")
    assert alpha.release_ready is True
    assert alpha.finished is False
    assert alpha.phases[0].evidence.release_ready is True
    assert beta.release_ready is True
    assert beta.finished is True
    assert gamma.release_ready is False
    assert gamma.phases[0].evidence is not None
    assert gamma.phases[0].evidence.release_ready is False
    live = model.EffortView(
        "e", "", phases=[_phase_row("in_progress")], tasks=[_task_row("ready")], release_ready=True,
    )
    done = model.EffortView(
        "e", "", phases=[_phase_row("done")], tasks=[_task_row("done")], release_ready=True,
    )
    assert live.finished is False
    assert done.finished is True


def test_evidence_simple_phase_adds_no_items(store, cli, defs):
    _goal(cli, defs, "alpha")
    _phase(cli, defs, "alpha", "p-simple", 1, "in_progress")
    _task(cli, defs, "simple-task", "p-simple")
    _assessment(cli, defs, "p-simple", "R1", status="failed", level="design", next="design", confidence="low")
    _report(cli, defs, "p-simple", "fail", "clash")
    _release(cli, defs, "p-simple", "ready")

    view = _effort(model.load_snapshot(_target(store)), "alpha")
    assert view.phases[0].evidence is None
    assert view.release_ready is False
    assert view.finished is False
    assert view.needs_you == []
    assert view.activity == []
    assert model.load_phase_detail(_target(store), "alpha", "p-simple").evidence is None


def test_evidence_legacy_store_loads_when_types_are_rejected(monkeypatch):
    import shutil

    design = json.loads(CONTRACT_PATH.read_text())
    drop = {"specification", "design", "assessment", "integration-report", "release"}
    design["records"] = [record for record in design["records"] if record["name"] not in drop]
    root = make_git_repo()
    try:
        artifacts = root / ".artifacts"
        artifacts.mkdir()
        (artifacts / "project-design.json").write_text(json.dumps(design))
        assert run_cli("resolve", root=root).returncode == 0
        assert run_cli("init", root=root).returncode == 0
        rejected = run_cli("list", "--type", "project:assessment", root=root)
        assert rejected.returncode != 0
        defs = h.record_defs_by_id(json.loads((artifacts / "resolved-contract.json").read_text()))

        def cli(*args):
            return run_cli(*args, root=root)

        _goal(cli, defs, "alpha")
        _phase(cli, defs, "alpha", "legacy-phase", 1)
        view = _effort(model.load_snapshot(_target(root)), "alpha")
        assert view.phases[0].evidence is None
        assert view.release_ready is False
        assert view.needs_you == []

        real = model._run

        def boom(target, *args):
            if "project:work-item" in args:
                raise model.ModelError("work-item failed")
            return real(target, *args)

        monkeypatch.setattr(model, "_run", boom)
        with pytest.raises(model.ModelError):
            model.load_snapshot(_target(root))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_evidence_stage_returns_each_rule(store, cli, defs):
    _goal(cli, defs, "alpha")

    def open_phase(subject: str, ordinal: int) -> None:
        _phase(cli, defs, "alpha", subject, ordinal)
        _spec(cli, defs, subject, "R1, R2" if subject in {"s-verified", "s-earliest", "s-partial"} else "R1")

    open_phase("s-ready", 1)
    _assessment(cli, defs, "s-ready", "R1", status="failed", next="execute", level="implementation")
    _release(cli, defs, "s-ready", "ready")

    for ordinal, (subject, nxt, level) in enumerate((
        ("s-specify", "specify", "specification"),
        ("s-design", "design", "design"),
        ("s-plan", "plan", "plan"),
        ("s-execute", "execute", "implementation"),
        ("s-nextint", "integrate", "integration"),
        ("s-nextverify", "verify", "verification"),
        ("s-nextrelease", "release", "unknown"),
    ), 2):
        open_phase(subject, ordinal)
        _assessment(cli, defs, subject, "R1", status="failed", next=nxt, level=level, confidence="high")

    open_phase("s-verified", 9)
    _assessment(cli, defs, "s-verified", "R1", status="verified", next="release", confidence="high")
    _assessment(cli, defs, "s-verified", "R2", status="verified", next="release", confidence="high")
    _release(cli, defs, "s-verified", "failed")

    open_phase("s-earliest", 10)
    _assessment(cli, defs, "s-earliest", "R1", status="failed", next="verify", level="verification")
    _assessment(cli, defs, "s-earliest", "R2", status="failed", next="plan", level="plan")

    open_phase("s-partial", 11)
    _assessment(cli, defs, "s-partial", "R1", status="verified", next="release", confidence="high")

    open_phase("s-nodesign", 12)

    open_phase("s-notasks", 13)
    _design(cli, defs, "s-notasks")

    open_phase("s-opentask", 14)
    _design(cli, defs, "s-opentask")
    _task(cli, defs, "s-opentask-task", "s-opentask")

    open_phase("s-integrate", 15)
    _design(cli, defs, "s-integrate")
    _task(cli, defs, "s-integrate-a", "s-integrate", done=True)
    _task(cli, defs, "s-integrate-b", "s-integrate", done=True)
    _report(cli, defs, "s-integrate", "fail", "drift")
    _accept(cli, defs, "s-integrate-acc", "s-integrate", "R1")

    open_phase("s-verify", 16)
    _design(cli, defs, "s-verify")
    _task(cli, defs, "s-verify-task", "s-verify", done=True)
    _accept(cli, defs, "s-verify-acc", "s-verify", "R1")

    open_phase("s-assess", 17)
    _design(cli, defs, "s-assess")
    _task(cli, defs, "s-assess-task", "s-assess", done=True)
    acceptance = _accept(cli, defs, "s-assess-acc", "s-assess", "R1")
    _check(cli, defs, "s-assess-check", acceptance["id"], "pass", "R1", "unit")

    view = _effort(model.load_snapshot(_target(store)), "alpha")
    integrate = [task for task in view.tasks if task.phase == "s-integrate"]
    assert len(integrate) == 2 and len({task.wave for task in integrate}) == 1
    assert {phase.subject: phase.evidence.stage for phase in view.phases} == {
        "s-ready": "release",
        "s-specify": "specify",
        "s-design": "design",
        "s-plan": "plan",
        "s-execute": "execute",
        "s-nextint": "integrate",
        "s-nextverify": "verify",
        "s-nextrelease": "release",
        "s-verified": "release",
        "s-earliest": "plan",
        "s-partial": "design",
        "s-nodesign": "design",
        "s-notasks": "plan",
        "s-opentask": "execute",
        "s-integrate": "integrate",
        "s-verify": "verify",
        "s-assess": "assess",
    }
    flags = {phase.subject: phase.evidence.release_ready for phase in view.phases}
    assert flags["s-ready"] is True
    assert flags["s-verified"] is False
    assert flags["s-nextrelease"] is False
    assert view.release_ready is True


def _estimated(ident: str, wave: int | None, executor: str, minutes: int | None) -> model.TaskRow:
    return model.TaskRow(
        id=ident, subject=ident, title="", phase="p", assignee="", wave=wave, status="ready",
        executor=executor, estimate_minutes=minutes,
    )


def test_estimate_view_sitting_phrase():
    assert model.sitting_phrase("Size: more than one sitting") == "more than one"
    assert model.sitting_phrase("Size: more than one sitting.") == "more than one"
    assert model.sitting_phrase("## Approach\n\nSize: one sitting\n") == "one sitting"
    assert model.sitting_phrase("Size: one sitting\nSize: more than one sitting") == "one sitting"
    assert model.sitting_phrase("## Problem\n\nNo size line here.\n") == ""


def test_estimate_view_wave_rule():
    tasks = [
        _estimated("in-a", 1, "inline", 10),
        _estimated("in-b", 1, "inline", 15),
        _estimated("sub-a", 2, "subagent", 10),
        _estimated("sub-b", 2, "subagent", 40),
        _estimated("sub-blank", 2, "subagent", None),
        _estimated("zero", 3, "inline", 0),
    ]
    elapsed, unset = model.phase_elapsed(tasks)
    assert elapsed == 10 + 15 + 40
    assert elapsed != sum(task.estimate_minutes or 0 for task in tasks)
    assert unset == 1
    assert model.phase_elapsed([_estimated("only-zero", 1, "subagent", 0)]) == (0, 0)
    separate = [
        _estimated("lone-a", None, "subagent", 10),
        _estimated("lone-b", None, "subagent", 40),
    ]
    assert model.phase_elapsed(separate) == (50, 0)


def test_estimate_view_unset_count():
    elapsed, unset = model.phase_elapsed([
        _estimated("missing-a", 1, "inline", None),
        _estimated("missing-b", 1, "inline", None),
        _estimated("known", 1, "inline", 25),
    ])
    assert (elapsed, unset) == (25, 2)
    elapsed, unset = model.phase_elapsed([
        _estimated("none-a", 1, "subagent", None),
        _estimated("none-b", 2, "inline", None),
    ])
    assert elapsed is None
    assert unset == 2


def _estimate_record(subject: str, **payload) -> dict:
    fields = {"title": subject, "phase": "p-est", "assignee": ""}
    fields.update(payload)
    return {
        "id": f"id-{subject}",
        "subject": subject,
        "lifecycle_state": "planned",
        "payload": fields,
        "derived": {"wave": 1, "ready": True},
        "relationships": {},
    }


def test_estimate_view_row_fields(store, cli, defs):
    sized = _estimate_record("sized", size="L", estimate_minutes=25, executor="inline")
    zero = _estimate_record("zero", size="", estimate_minutes=0, executor="")
    blank = _estimate_record("blank")
    null = _estimate_record("null", size=None, estimate_minutes=None, executor=None)
    rows = {row.subject: row for row in model._task_rows([sized, zero, blank, null])}
    assert (rows["sized"].size, rows["sized"].estimate_minutes, rows["sized"].executor) == ("L", 25, "inline")
    assert (rows["zero"].size, rows["zero"].estimate_minutes, rows["zero"].executor) == ("", 0, "subagent")
    assert (rows["blank"].size, rows["blank"].estimate_minutes, rows["blank"].executor) == ("", None, "subagent")
    assert rows["null"].estimate_minutes is None
    assert rows["null"].executor == "subagent"

    phase = {
        "id": "phase-est",
        "subject": "p-est",
        "lifecycle_state": "in_progress",
        "payload": {"title": "Estimates", "ordinal": 1},
        "body": "Size: more than one sitting.",
    }
    phase_row = model._phase_rows([phase], [sized])[0]
    assert phase_row.sitting == "more than one"
    assert phase_row.elapsed_minutes == 25
    assert phase_row.unset_estimates == 0

    _goal(cli, defs, "alpha")
    body = "## Problem\n\nplaceholder.\n\n## Approach\n\nSize: more than one sitting.\n\n## Exit criteria\n\nplaceholder.\n"
    _record(cli, defs, "project:phase", "p-snap", {"title": "Snap", "ordinal": 1, "effort": "alpha"}, body)
    _record(cli, defs, "project:work-item", "snap-task", {
        "title": "Snap task", "phase": "p-snap", "kind": "deliver", "assignee": "", "effort": "alpha",
        "size": "L", "estimate_minutes": 25, "executor": "inline",
    })
    _record(cli, defs, "project:work-item", "snap-zero", {
        "title": "Snap zero", "phase": "p-snap", "kind": "deliver", "assignee": "", "effort": "alpha",
        "estimate_minutes": 0, "executor": "inline",
    })
    view = _effort(model.load_snapshot(_target(store)), "alpha")
    snap = view.phases[0]
    assert snap.sitting == "more than one"
    assert snap.elapsed_minutes == 25
    assert snap.unset_estimates == 0
    tasks = {task.subject: task for task in view.tasks}
    assert (tasks["snap-task"].size, tasks["snap-task"].estimate_minutes, tasks["snap-task"].executor) == (
        "L", 25, "inline",
    )
    assert tasks["snap-zero"].estimate_minutes == 0
    assert tasks["snap-zero"].size == ""


def test_estimate_view_blank_executor(store, cli, defs):
    task = _work_item(cli, defs, "alpha", "blank-task", "p-one")
    detail = model.load_task_detail(_target(store), task["id"])
    assert detail.executor == "subagent"
    assert detail.size == ""
    assert detail.estimate_minutes is None
