"""Tests for dashboard.journal model loaders, Agent work, and JournalScreen pilots."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("textual")

import helpers as h
from conftest import REPO_ROOT, stamped_store

sys.path.insert(0, str(REPO_ROOT))
from dashboard import app as app_module  # noqa: E402
from dashboard import artifact_store  # noqa: E402
from dashboard import journal  # noqa: E402
from dashboard import model  # noqa: E402
from dashboard import pager  # noqa: E402
from dashboard import task_detail as detail_module  # noqa: E402
from dashboard.journal import JournalScreen, JournalTable, RecordDetailScreen  # noqa: E402
from test_dashboard_app import _detail_run, _open_by_enter, _run, _shown, _until  # noqa: E402
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


# --- Kind Journal panel on EffortPane (R7) ---

def _journal_panel_text(app) -> str:
    panel = app.query_one("#journal", app_module.JournalPanel)
    return "\n".join(
        str(panel.get_option_at_index(i).prompt) for i in range(panel.option_count)
    )


def _seed_repair_panel(cli, defs, effort: str = "alpha", open_count: int = 2) -> list[dict]:
    _goal(cli, defs, effort, kind="repair")
    _phase(cli, defs, effort, "p-one", 1, "in_progress")
    _phase(cli, defs, effort, "p-two", 2)
    _work_item(cli, defs, effort, "jp-task", "p-one")
    created = []
    for index in range(open_count):
        created.append(_record(
            cli, defs, "project:continuity-question", effort,
            {"owner": "user", "blocking": False, "scope": f"open-{index}"},
        ))
    _record(
        cli, defs, "project:finding", "jp-task",
        {"claim": "phase finding", "basis": "b", "needs": "human", "effort": effort, "invalidated_when": "w"},
    )
    return created


def test_journal_panel_shows_for_repair_kind(store, cli, defs):
    _seed_repair_panel(cli, defs)

    async def scenario(app, pilot):
        panel = app.query_one("#journal", app_module.JournalPanel)
        assert panel.display
        assert panel.option_count >= 1
        text = _journal_panel_text(app)
        assert "question" in text or "?" in text
        assert "finding" in text or "!" in text
        tasks = app.query_one("#tasks")
        assert panel.region.y < tasks.region.y

    _run(store, 100, scenario, height=40)


def test_journal_panel_shows_for_evaluate_kind(store, cli, defs):
    _goal(cli, defs, "eval", kind="evaluate")
    _phase(cli, defs, "eval", "e-phase", 1, "in_progress")
    _work_item(cli, defs, "eval", "e-task", "e-phase")
    _record(
        cli, defs, "project:finding", "e-task",
        {"claim": "eval claim", "basis": "b", "needs": "human", "effort": "eval", "invalidated_when": "w"},
    )

    async def scenario(app, pilot):
        panel = app.query_one("#journal", app_module.JournalPanel)
        assert panel.display
        assert "eval claim" in _journal_panel_text(app)

    _run(store, 100, scenario, height=40)


def test_journal_panel_hidden_for_deliver_kind(store, cli, defs):
    _goal(cli, defs, "alpha", kind="deliver")
    _phase(cli, defs, "alpha", "p-one", 1, "in_progress")
    _work_item(cli, defs, "alpha", "jp-task", "p-one")
    _record(
        cli, defs, "project:finding", "jp-task",
        {"claim": "hidden claim", "basis": "b", "needs": "human", "effort": "alpha", "invalidated_when": "w"},
    )

    async def scenario(app, pilot):
        panel = app.query_one("#journal", app_module.JournalPanel)
        assert not panel.display

    _run(store, 100, scenario, height=40)


def test_journal_panel_hidden_for_incidental_kind(store, cli, defs):
    _goal(cli, defs, "alpha", kind="incidental")
    _phase(cli, defs, "alpha", "p-one", 1, "in_progress")
    _work_item(cli, defs, "alpha", "jp-task", "p-one")
    _record(
        cli, defs, "project:finding", "jp-task",
        {"claim": "incidental claim", "basis": "b", "needs": "human", "effort": "alpha", "invalidated_when": "w"},
    )

    async def scenario(app, pilot):
        assert not app.query_one("#journal", app_module.JournalPanel).display

    _run(store, 100, scenario, height=40)


def test_journal_panel_hidden_when_repair_has_no_open_items(store, cli, defs):
    _goal(cli, defs, "alpha", kind="repair")
    _phase(cli, defs, "alpha", "p-one", 1, "in_progress")
    _work_item(cli, defs, "alpha", "jp-task", "p-one")
    _record(
        cli, defs, "project:failed-attempt", "jp-task",
        {"attempted_action": "tried", "retry_when": "", "effort": "alpha"},
    )

    async def scenario(app, pilot):
        assert not app.query_one("#journal", app_module.JournalPanel).display

    _run(store, 100, scenario, height=40)


def test_journal_panel_caps_five_rows_plus_more(store, cli, defs):
    _goal(cli, defs, "alpha", kind="repair")
    _phase(cli, defs, "alpha", "p-one", 1, "in_progress")
    for index in range(7):
        _record(
            cli, defs, "project:continuity-question", "alpha",
            {"owner": "user", "blocking": False, "scope": f"many-{index}"},
        )

    async def scenario(app, pilot):
        panel = app.query_one("#journal", app_module.JournalPanel)
        assert panel.display
        assert len(panel.items) == 5
        assert panel.option_count == 6
        assert "+2 more" in _journal_panel_text(app)

    _run(store, 100, scenario, height=40)


def test_journal_panel_scoped_to_selected_phase(store, cli, defs):
    _seed_repair_panel(cli, defs, open_count=1)
    _record(
        cli, defs, "project:continuity-question", "alpha",
        {"owner": "user", "blocking": True, "scope": "plan-review:p-two"},
    )

    async def scenario(app, pilot):
        app.select_phase("alpha", "p-one")
        await pilot.pause()
        text = _journal_panel_text(app)
        assert "phase finding" in text or "finding" in text
        assert "plan-review:p-two" not in text
        assert "title of p-two" not in text
        app.select_phase("alpha", "p-two")
        await pilot.pause()
        text = _journal_panel_text(app)
        assert "p-two" in text or "title of p-two" in text
        assert "phase finding" not in text

    _run(store, 100, scenario, height=40)


def test_journal_panel_enter_opens_record_detail(store, cli, defs):
    _seed_repair_panel(cli, defs, open_count=1)

    async def scenario(app, pilot):
        panel = app.query_one("#journal", app_module.JournalPanel)
        assert panel.display
        panel.focus()
        panel.highlighted = 0
        await pilot.pause()
        expected = panel.items[0].id
        await pilot.press("enter")
        await _until(pilot, lambda: app.screen is not app.screen_stack[0])
        screen = app.screen
        detail_cls = getattr(journal, "RecordDetailScreen", None) or app_module._RecordDetailStub
        assert isinstance(screen, detail_cls)
        assert getattr(screen, "record_id", None) == expected

    _run(store, 100, scenario, height=40)


# --- JournalScreen / RecordDetailScreen (R1, R5, R6) ---

_CLI_CACHE: dict = {}


def _store_digest(store):
    digest = hashlib.sha1()
    for path in sorted(store.rglob("*")):
        if path.is_file():
            digest.update(f"{path.relative_to(store)}\0".encode())
            digest.update(path.read_bytes())
    return digest.digest()


@pytest.fixture(autouse=True)
def _memoized_cli(monkeypatch):
    real = model._run

    def run(target, *args):
        key = (args, _store_digest(target.store))
        if key not in _CLI_CACHE:
            _CLI_CACHE[key] = real(target, *args)
        return copy.deepcopy(_CLI_CACHE[key])

    monkeypatch.setattr(model, "_run", run)


def _build_journal_ui(store, cli, defs):
    _seed_journal(cli, defs, "alpha")
    return None


@pytest.fixture()
def journal_ui(store):
    stamped_store(store, "journal-ui", _build_journal_ui)
    return store


def _journal_run(store, scenario, size=(120, 40), interval=60.0):
    async def go():
        app = app_module.DashboardApp(artifact_store.resolve(store), interval=interval)
        async with app.run_test(size=size) as pilot:
            await _until(pilot, lambda: app.snapshot is not None and bool(app.query("#goal")))
            await app.workers.wait_for_complete()
            await pilot.pause()
            await scenario(app, pilot)

    asyncio.run(go())


async def _journal_shown(app, pilot):
    await _until(
        pilot,
        lambda: isinstance(app.screen, JournalScreen) and app.screen.loaded,
    )
    await pilot.pause(0.2)
    return app.screen


async def _record_shown(app, pilot):
    await _until(
        pilot,
        lambda: isinstance(app.screen, RecordDetailScreen) and app.screen.loaded,
    )
    await pilot.pause(0.2)
    return app.screen


def test_journal_screen_opens_with_J_for_selected_phase(journal_ui):
    store = journal_ui

    async def scenario(app, pilot):
        app.select_phase("alpha", "p-one")
        await pilot.pause()
        await pilot.press("J")
        screen = await _journal_shown(app, pilot)
        assert screen.effort == "alpha"
        assert screen.phase == "p-one"
        assert "p-one" in str(screen.query_one("#journal-bar").render())
        table = screen.query_one("#journal-table", JournalTable)
        subjects = {item.subject for item in table.items if item.id}
        assert "j-task-a" in subjects or any("j-task" in s for s in subjects)
        assert not any(item.phase == "p-two" for item in table.items if item.id)

    _journal_run(store, scenario)


def test_journal_screen_opens_effort_scope_on_all_phases(journal_ui):
    store = journal_ui

    async def scenario(app, pilot):
        app.select_phase("alpha", None)
        await pilot.pause()
        await pilot.press("J")
        screen = await _journal_shown(app, pilot)
        assert screen.phase is None
        assert "effort" in str(screen.query_one("#journal-bar").render())
        table = screen.query_one("#journal-table", JournalTable)
        phases = {item.phase for item in table.items if item.id}
        assert "p-one" in phases and "p-two" in phases

    _journal_run(store, scenario)


def test_journal_screen_a_toggles_effort_scope(journal_ui):
    store = journal_ui

    async def scenario(app, pilot):
        app.select_phase("alpha", "p-one")
        await pilot.pause()
        await pilot.press("J")
        screen = await _journal_shown(app, pilot)
        assert screen.phase == "p-one"
        await pilot.press("a")
        await pilot.pause()
        assert screen.phase is None
        assert "effort" in str(screen.query_one("#journal-bar").render())
        table = screen.query_one("#journal-table", JournalTable)
        assert any(item.phase == "p-two" for item in table.items if item.id)
        await pilot.press("a")
        await pilot.pause()
        assert screen.phase == "p-one"

    _journal_run(store, scenario)


def test_journal_screen_escape_returns_to_main(journal_ui):
    store = journal_ui

    async def scenario(app, pilot):
        dashboard = app.screen
        app.select_phase("alpha", "p-one")
        await pilot.pause()
        await pilot.press("J")
        await _journal_shown(app, pilot)
        await pilot.press("escape")
        await _until(pilot, lambda: app.screen is dashboard)
        assert not isinstance(app.screen, JournalScreen)

    _journal_run(store, scenario)


def test_journal_filter_matches_subject_and_text(journal_ui):
    store = journal_ui

    async def scenario(app, pilot):
        app.select_phase("alpha", None)
        await pilot.pause()
        await pilot.press("J")
        screen = await _journal_shown(app, pilot)
        table = screen.query_one("#journal-table", JournalTable)
        before = len([i for i in table.items if i.id])
        assert before > 1
        await pilot.press("slash")
        await pilot.pause()
        box = screen.query_one("#journal-filter")
        assert box.display
        box.value = "root cause"
        screen.filter_text = "root cause"
        screen.repaint()
        await pilot.pause(0.2)
        after = [i for i in table.items if i.id]
        assert after
        assert all("root cause" in i.text.lower() or "root cause" in i.subject.lower() for i in after)
        assert len(after) < before

    _journal_run(store, scenario)


def test_journal_detail_opens_on_enter_with_type_subject_payload_body(journal_ui):
    store = journal_ui

    async def scenario(app, pilot):
        app.select_phase("alpha", "p-one")
        await pilot.pause()
        await pilot.press("J")
        screen = await _journal_shown(app, pilot)
        table = screen.query_one("#journal-table", JournalTable)
        amendment = next(i for i in table.items if i.record_type == "project:assignment-amendment")
        table.move_cursor(row=table._keys.index(amendment.id))
        await pilot.pause()
        await pilot.press("enter")
        detail = await _record_shown(app, pilot)
        assert detail.record is not None
        assert detail.record["record_type"] == "project:assignment-amendment"
        assert "j-task-a" in (detail.record.get("subject") or "")
        assert "assignment" in model._payload(detail.record)
        body_src = detail.query_one("#record-body Markdown").source
        assert "use the other path" in body_src
        assert "Correction" in body_src or "use the other path" in body_src

    _journal_run(store, scenario)


def test_journal_detail_enter_on_linked_task_opens_task_detail(journal_ui):
    store = journal_ui

    async def scenario(app, pilot):
        app.select_phase("alpha", "p-one")
        await pilot.pause()
        await pilot.press("J")
        screen = await _journal_shown(app, pilot)
        table = screen.query_one("#journal-table", JournalTable)
        linked = next(i for i in table.items if i.task_id and i.record_type == "project:failed-attempt")
        table.move_cursor(row=table._keys.index(linked.id))
        await pilot.pause()
        await pilot.press("enter")
        detail = await _record_shown(app, pilot)
        links = detail.query_one("#record-links")
        assert links.display and links.option_count == 1
        links.focus()
        links.highlighted = 0
        await pilot.pause()
        await pilot.press("enter")
        await _until(pilot, lambda: isinstance(app.screen, detail_module.TaskDetailScreen) and app.screen.loaded)
        assert app.screen.task_id == linked.task_id

    _journal_run(store, scenario)


def test_journal_pager_pages_list_with_stub(journal_ui, tmp_path, monkeypatch):
    store = journal_ui
    script = tmp_path / "stub-pager"
    script.write_text(STUB_PAGER, encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PAGER", str(script))
    monkeypatch.setattr(pager.shutil, "which", lambda name: None)

    async def scenario(app, pilot):
        app.select_phase("alpha", "p-one")
        await pilot.pause()
        await pilot.press("J")
        await _journal_shown(app, pilot)
        monkeypatch.setattr(app, "suspend", lambda: __import__("contextlib").nullcontext())
        await pilot.press("o")
        await pilot.pause(0.3)
        out = script.with_suffix(".out")
        assert out.is_file(), "stub pager did not run"
        recorded_path_line, _, contents = out.read_text(encoding="utf-8").partition("\n")
        recorded = Path(recorded_path_line)
        assert recorded.suffix == ".md"
        assert ".artifacts" not in recorded.parts
        assert "Journal" in contents
        assert not recorded.exists()

    _journal_run(store, scenario)


def test_journal_detail_pager_pages_record_with_stub(journal_ui, tmp_path, monkeypatch):
    store = journal_ui
    script = tmp_path / "stub-pager"
    script.write_text(STUB_PAGER, encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PAGER", str(script))
    monkeypatch.setattr(pager.shutil, "which", lambda name: None)

    async def scenario(app, pilot):
        app.select_phase("alpha", "p-one")
        await pilot.pause()
        await pilot.press("J")
        screen = await _journal_shown(app, pilot)
        table = screen.query_one("#journal-table", JournalTable)
        item = next(i for i in table.items if i.id)
        table.move_cursor(row=table._keys.index(item.id))
        await pilot.pause()
        await pilot.press("enter")
        await _record_shown(app, pilot)
        monkeypatch.setattr(app, "suspend", lambda: __import__("contextlib").nullcontext())
        await pilot.press("o")
        await pilot.pause(0.3)
        out = script.with_suffix(".out")
        assert out.is_file(), "stub pager did not run"
        recorded_path_line, _, contents = out.read_text(encoding="utf-8").partition("\n")
        recorded = Path(recorded_path_line)
        assert recorded.suffix == ".md"
        assert ".artifacts" not in recorded.parts
        assert item.record_type in contents or item.subject in contents
        assert not recorded.exists()

    _journal_run(store, scenario)
