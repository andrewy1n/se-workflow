"""Tests for dashboard.journal model loaders (R2–R4, R9) and Agent work on task detail."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("textual")

import helpers as h
from conftest import REPO_ROOT, stamped_store

sys.path.insert(0, str(REPO_ROOT))
from dashboard import artifact_store  # noqa: E402
from dashboard import journal  # noqa: E402
from dashboard import model  # noqa: E402
from dashboard import pager  # noqa: E402
from dashboard import task_detail as detail_module  # noqa: E402
from test_dashboard_app import _detail_run, _open_by_enter, _shown, _until  # noqa: E402
from test_dashboard_pager import STUB_PAGER  # noqa: E402


def _goal(cli, defs, effort: str, kind: str = "deliver") -> None:
    h.create_generic_record(
        cli, defs, "project:active-goal", subject=effort,
        extra_payload={"goal": f"ship {effort}", "kind": kind},
    )


def _phase(cli, defs, effort: str, subject: str, ordinal: int, *states: str) -> None:
    record = h.create_generic_record(
        cli, defs, "project:phase", subject=subject,
        extra_payload={"title": f"title of {subject}", "ordinal": ordinal, "effort": effort},
    )
    h.transition(cli, "project:phase", record, *states)


def _work_item(cli, defs, effort: str, subject: str, phase: str) -> dict:
    payload = {"title": f"title of {subject}", "phase": phase, "kind": "deliver", "assignee": "", "effort": effort}
    result = cli(
        "create", "--type", "project:work-item", "--subject", subject,
        "--payload", json.dumps(payload), "--body", h.generic_body(defs["project:work-item"]),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def _record(cli, defs, record_type: str, subject: str, payload: dict, body: str | None = None) -> dict:
    args = ["create", "--type", record_type, "--subject", subject, "--payload", json.dumps(payload)]
    body = body if body is not None else h.generic_body(defs[record_type])
    if body:
        args.extend(["--body", body])
    result = cli(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def _target(store):
    return artifact_store.resolve(store)


@pytest.fixture()
def defs(resolved_contract):
    return h.record_defs_by_id(resolved_contract)


def _seed_journal(cli, defs, effort: str = "alpha") -> None:
    _goal(cli, defs, effort, kind="repair")
    _phase(cli, defs, effort, "p-one", 1, "in_progress")
    _phase(cli, defs, effort, "p-two", 2)
    task_a = _work_item(cli, defs, effort, "j-task-a", "p-one")
    task_b = _work_item(cli, defs, effort, "j-task-b", "p-two")
    _work_item(cli, defs, effort, "j-task-c", "p-one")
    assignment = _record(
        cli, defs, "project:assignment", "j-task-a",
        {"work_item": task_a["id"], "executor": "sub", "effort": effort},
        "## Orientation\n\ndo the work",
    )
    _record(
        cli, defs, "project:assignment-amendment", "j-task-a",
        {"assignment": assignment["subject"], "effort": effort},
        "## Correction\n\nuse the other path\n\nmore detail",
    )
    _record(
        cli, defs, "project:failed-attempt", "j-task-a",
        {"attempted_action": "tried x", "retry_when": "later", "effort": effort},
    )
    _record(
        cli, defs, "project:investigation-observation", "j-task-c",
        {"what_was_observed": "saw y", "effort": effort, "environment": "e", "observed_time": "t", "source": "s"},
    )
    _record(
        cli, defs, "project:investigation-observation", "j-task-b",
        {"what_was_observed": "closed by finding", "effort": effort, "environment": "e", "observed_time": "t", "source": "s"},
    )
    _record(
        cli, defs, "project:finding", "j-task-b",
        {"claim": "root cause", "basis": "b", "needs": "human", "effort": effort, "invalidated_when": "w"},
    )
    _record(
        cli, defs, "project:finding", "j-task-a",
        {"claim": "agent claim", "basis": "b", "needs": "agent", "effort": effort, "invalidated_when": "w"},
    )
    _record(
        cli, defs, "project:continuity-question", effort,
        {"owner": "user", "blocking": True, "scope": "plan-review:p-one"},
    )
    open_q = _record(
        cli, defs, "project:continuity-question", effort,
        {"owner": "user", "blocking": False, "scope": "effort-wide"},
    )
    answered = _record(
        cli, defs, "project:continuity-question", effort,
        {"owner": "user", "blocking": True, "scope": "old-scope"},
    )
    h.transition(cli, "project:continuity-question", answered, "answered")
    del open_q, task_b


def test_journal_load_returns_types_phase_and_one_line_text(store, cli, defs):
    _seed_journal(cli, defs)
    items = journal.load_journal(_target(store), "alpha")
    by_type = {}
    for item in items:
        by_type.setdefault(item.record_type, []).append(item)

    assert set(by_type) == set(journal.JOURNAL_TYPES)
    attempt = by_type["project:failed-attempt"][0]
    assert attempt.phase == "p-one"
    assert attempt.text == "tried x · don't retry · retry when later"
    assert attempt.open is False

    obs_open = next(i for i in by_type["project:investigation-observation"] if i.subject == "j-task-c")
    assert obs_open.text == "saw y"
    assert obs_open.open is True
    obs_closed = next(i for i in by_type["project:investigation-observation"] if i.subject == "j-task-b")
    assert obs_closed.open is False

    human = next(i for i in by_type["project:finding"] if i.subject == "j-task-b")
    assert human.text == "root cause · needs human"
    assert human.open is True
    agent = next(i for i in by_type["project:finding"] if i.subject == "j-task-a")
    assert agent.open is False

    plan = next(i for i in by_type["project:continuity-question"] if i.phase == "p-one")
    assert "title of p-one" in plan.text
    assert "plan-review:" not in plan.text
    assert plan.open is True

    effort_q = next(i for i in by_type["project:continuity-question"] if i.phase is None and "effort-wide" in i.text)
    assert effort_q.open is True
    answered = next(i for i in by_type["project:continuity-question"] if "old-scope" in i.text)
    assert answered.open is False
    assert "answered" in answered.text

    amendment = by_type["project:assignment-amendment"][0]
    assert amendment.phase == "p-one"
    assert amendment.text.startswith("use the other path")
    assert "j-task-a" in amendment.text
    assert amendment.open is False


def test_journal_order_open_first_newest_first(store, cli, defs):
    _goal(cli, defs, "alpha", kind="repair")
    _phase(cli, defs, "alpha", "p-one", 1, "in_progress")
    _work_item(cli, defs, "alpha", "j-task", "p-one")
    older = h.run_cli_48h_ago(
        store, "create", "--type", "project:continuity-question", "--subject", "alpha",
        "--payload", json.dumps({"owner": "user", "blocking": True, "scope": "older-open"}),
    )
    newer = _record(
        cli, defs, "project:continuity-question", "alpha",
        {"owner": "user", "blocking": False, "scope": "newer-open"},
    )
    _record(
        cli, defs, "project:failed-attempt", "j-task",
        {"attempted_action": "tried", "retry_when": "", "effort": "alpha"},
    )
    finding = _record(
        cli, defs, "project:finding", "j-task",
        {"claim": "needs a human", "basis": "b", "needs": "human", "effort": "alpha", "invalidated_when": "w"},
    )
    items = journal.load_journal(_target(store), "alpha")
    open_items, rest = journal.ordered(items)
    assert [i.open for i in open_items] == [True] * len(open_items)
    assert all(not i.open for i in rest)
    open_ids = [i.id for i in open_items]
    assert open_ids.index(newer["id"]) < open_ids.index(older["id"])
    assert finding["id"] in open_ids
    assert rest
    stamps = [i.recorded_at for i in rest]
    assert stamps == sorted(stamps, reverse=True)


def test_journal_scope_phase_plus_effort_only_open_questions(store, cli, defs):
    _seed_journal(cli, defs)
    items = journal.load_journal(_target(store), "alpha")
    scoped = journal.journal_scope(items, "p-one")
    phases = {i.phase for i in scoped}
    assert phases <= {"p-one", None}
    assert any(i.phase is None and i.open and i.record_type == "project:continuity-question" for i in scoped)
    assert all(i.phase == "p-one" or (i.phase is None and i.open) for i in scoped)
    assert not any(i.phase == "p-two" for i in scoped)
    assert not any(i.phase is None and not i.open for i in scoped)

    all_items = journal.journal_scope(items, None)
    assert len(all_items) == len(items)


def test_journal_missing_types_do_not_error(store, cli, defs, monkeypatch):
    _goal(cli, defs, "alpha", kind="repair")
    real = model._list

    def missing(target, record_type, **kwargs):
        if record_type in journal.JOURNAL_TYPES:
            raise model.ModelError(f"unknown type {record_type}")
        return real(target, record_type, **kwargs)

    monkeypatch.setattr(model, "_list", missing)
    items = journal.load_journal(_target(store), "alpha")
    assert items == []



def test_journal_load_drops_orphan_effort_when_several_goals(store, cli, defs):
    _goal(cli, defs, "alpha", kind="repair")
    _goal(cli, defs, "beta", kind="deliver")
    _phase(cli, defs, "alpha", "p-one", 1)
    _work_item(cli, defs, "alpha", "j-task", "p-one")
    orphan = {
        "attempted_action": "no effort field",
        "retry_when": "",
    }
    # Create via CLI then strip effort is hard; create with effort then correct away is also hard.
    # Seed a record whose payload.effort is beta while subject is j-task — filtered out of alpha.
    _record(cli, defs, "project:failed-attempt", "j-task", {**orphan, "effort": "beta"})
    _record(
        cli, defs, "project:failed-attempt", "j-task",
        {"attempted_action": "alpha try", "retry_when": "", "effort": "alpha"},
    )
    items = journal.load_journal(_target(store), "alpha")
    attempts = [i for i in items if i.record_type == "project:failed-attempt"]
    assert [i.text for i in attempts] == ["alpha try · don't retry"]


# --- Agent work on task detail (R8) ---

LONG_ORIENTATION = "## Orientation\n\n" + "\n".join(f"orientation line {i}" for i in range(1, 13))


def _build_agent_task(store, cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="alpha",
        extra_payload={"goal": "ship it", "kind": "deliver"},
    )
    _phase(cli, defs, "alpha", "agent-phase", 1, "in_progress")
    task = _work_item(cli, defs, "alpha", "agent-task", "agent-phase")
    h.transition(cli, "project:work-item", task, "in_progress")
    older = h.run_cli_48h_ago(
        store, "create", "--type", "project:assignment", "--subject", "agent-task-old",
        "--body", "## Orientation\n\nold orientation\n\n## Requirements\n\nold rest",
        "--payload", json.dumps({"work_item": task["id"], "executor": "old-exec", "effort": "alpha"}),
    )
    h.run_cli_48h_ago(
        store, "create", "--type", "project:execution-report", "--subject", "agent-task-old-report",
        "--body", "old report body",
        "--payload", json.dumps({
            "work_item": task["id"], "assignment": older["id"],
            "result": "no", "verdict": "fail", "revision": "r0",
        }),
    )
    assignment = _record(
        cli, defs, "project:assignment", "agent-task",
        {"work_item": task["id"], "executor": "new-exec", "effort": "alpha"},
        LONG_ORIENTATION + "\n\n## Requirements\n\nR8: collapse to eight lines.",
    )
    _record(
        cli, defs, "project:assignment-amendment", "agent-task",
        {"assignment": "agent-task", "effort": "alpha"},
        "## Correction\n\n" + "\n".join(f"correction line {i}" for i in range(1, 11)),
    )
    _record(
        cli, defs, "project:execution-report", "agent-task",
        {
            "work_item": task["id"], "assignment": assignment["id"],
            "result": "ok", "verdict": "pass", "revision": "r2",
        },
        "report body line\n" + "\n".join(f"report extra {i}" for i in range(1, 10)),
    )
    return task


@pytest.fixture()
def agent_store(store):
    task = stamped_store(store, "agent-work", _build_agent_task)
    return store, task


def test_agent_work_model_groups_newest_first_with_orientation_amendment_and_report(agent_store):
    store, task = agent_store
    detail = model.load_task_detail(_target(store), task["id"])
    assert len(detail.agent_work) == 2
    latest = detail.agent_work[0]
    assert latest.assignment.executor == "new-exec"
    assert "orientation line 1" in latest.assignment.orientation
    assert "R8: collapse" in latest.assignment.body
    assert "Orientation" not in latest.assignment.body
    assert len(latest.amendments) == 1
    assert "correction line 1" in latest.amendments[0].correction
    assert latest.report is not None
    assert (latest.report.result, latest.report.verdict) == ("ok", "pass")
    earlier = detail.agent_work[1]
    assert earlier.assignment.executor == "old-exec"
    assert earlier.report is not None and earlier.report.result == "no"


def test_agent_work_collapsed_to_eight_lines_with_marker(agent_store):
    store, task = agent_store

    async def scenario(app, pilot):
        await _open_by_enter(app, pilot, task["id"])
        screen = await _shown(app, pilot)
        panel = screen.query_one("#agent-work", detail_module.AgentWorkPanel)
        assert panel.display
        assert panel.border_title == "Agent work"
        blocks = list(panel.query(detail_module.CollapsibleBlock))
        assert [block.block_title for block in blocks] == ["Orientation", "Assignment", "Correction", "Report"]
        orientation = blocks[0]
        full_lines = orientation.full_text.splitlines()
        assert len(full_lines) > 8
        rendered = orientation.render().plain
        for line in full_lines[:8]:
            if line:
                assert line in rendered
        assert full_lines[8] not in rendered
        assert f"+{len(full_lines) - 8} lines" in rendered
        assert not orientation.expanded

    _detail_run(store, (100, 50), scenario)


def test_agent_work_enter_expands_and_collapses_focused_block(agent_store):
    store, task = agent_store

    async def scenario(app, pilot):
        await _open_by_enter(app, pilot, task["id"])
        screen = await _shown(app, pilot)
        block = screen.query_one("#agent-block-0", detail_module.CollapsibleBlock)
        block.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        marker = f"+{len(block.full_text.splitlines()) - 8} lines"
        assert block.expanded
        assert "orientation line 12" in block.render().plain
        assert marker not in block.render().plain
        await pilot.press("enter")
        await pilot.pause()
        assert not block.expanded
        assert marker in block.render().plain

    _detail_run(store, (100, 50), scenario)


def test_agent_work_o_pages_focused_block(agent_store, tmp_path, monkeypatch):
    store, task = agent_store
    script = tmp_path / "stub-pager"
    script.write_text(STUB_PAGER, encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PAGER", str(script))
    monkeypatch.setattr(pager.shutil, "which", lambda name: None)

    async def scenario(app, pilot):
        await _open_by_enter(app, pilot, task["id"])
        screen = await _shown(app, pilot)
        block = screen.query_one("#agent-block-0", detail_module.CollapsibleBlock)
        block.focus()
        await pilot.pause()
        monkeypatch.setattr(app, "suspend", lambda: __import__("contextlib").nullcontext())
        await pilot.press("o")
        await pilot.pause(0.3)
        out = script.with_suffix(".out")
        assert out.is_file(), "stub pager did not run"
        recorded_path_line, _, contents = out.read_text(encoding="utf-8").partition("\n")
        recorded = Path(recorded_path_line)
        assert recorded.suffix == ".md"
        assert ".artifacts" not in recorded.parts
        assert "orientation line 1" in contents
        assert "orientation line 12" in contents
        assert not recorded.exists()

    _detail_run(store, (100, 50), scenario)


def test_agent_work_earlier_assignments_listed_and_enter_shows_their_blocks(agent_store):
    store, task = agent_store

    async def scenario(app, pilot):
        await _open_by_enter(app, pilot, task["id"])
        screen = await _shown(app, pilot)
        panel = screen.query_one("#agent-work", detail_module.AgentWorkPanel)
        listing = panel.query_one("#agent-earlier", detail_module.EarlierList)
        assert listing.option_count == 1
        labels = [str(listing.get_option_at_index(0).prompt)]
        assert "old-exec" in labels[0] and "no" in labels[0]
        listing.focus()
        listing.highlighted = 0
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause(0.2)
        await _until(pilot, lambda: any(
            b.block_title == "Orientation" and "old orientation" in b.full_text
            for b in panel.query(detail_module.CollapsibleBlock)
        ))
        blocks = list(panel.query(detail_module.CollapsibleBlock))
        assert blocks[0].full_text.strip() == "old orientation"
        assert any(b.block_title == "Report" and "old report body" in b.full_text for b in blocks)

    _detail_run(store, (100, 50), scenario)
