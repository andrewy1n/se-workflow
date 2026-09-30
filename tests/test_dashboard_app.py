"""Tests for scripts/dashboard_app: the Textual dashboard and its --once frame."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time

import pytest

pytest.importorskip("textual")

import helpers as h  # noqa: E402
from conftest import REPO_ROOT  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import artifact_store  # noqa: E402
import dashboard_app as app_module  # noqa: E402

SCRIPT = REPO_ROOT / "scripts" / "dashboard_app.py"
WIDTHS = (60, 120)


def _work_item(cli, defs, effort, subject, phase, *rels, assignee=""):
    payload = {"title": f"title of {subject}", "phase": phase, "kind": "deliver", "assignee": assignee, "effort": effort}
    args = ["create", "--type", "project:work-item", "--subject", subject, "--payload", json.dumps(payload)]
    for rel in rels:
        args.extend(["--rel", rel])
    result = cli(*args, "--body", h.generic_body(defs["project:work-item"]))
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def _phase(cli, defs, effort, subject, ordinal, *states):
    record = h.create_generic_record(
        cli, defs, "project:phase", subject=subject,
        extra_payload={"title": f"Phase {subject}", "ordinal": ordinal, "effort": effort},
    )
    h.transition(cli, "project:phase", record, *states)


@pytest.fixture()
def defs(resolved_contract):
    return h.record_defs_by_id(resolved_contract)


@pytest.fixture()
def seeded(store, cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="alpha",
        extra_payload={"goal": "ship the alpha dashboard", "kind": "deliver"},
    )
    _phase(cli, defs, "alpha", "one", 1, "in_progress", "done")
    _phase(cli, defs, "alpha", "two", 2, "in_progress")
    _phase(cli, defs, "alpha", "three", 3)
    running = _work_item(cli, defs, "alpha", "a-running", "two", assignee="agent-7")
    h.transition(cli, "project:work-item", running, "in_progress")
    _work_item(cli, defs, "alpha", "a-ready", "two")
    _work_item(cli, defs, "alpha", "a-waiting", "two", f"depends_on:{running['id']}")
    done = _work_item(cli, defs, "alpha", "a-done", "one")
    h.transition(cli, "project:work-item", done, "in_progress", "done")
    h.create_generic_record(
        cli, defs, "project:continuity-question", subject="alpha",
        extra_payload={"blocking": True, "scope": "which backend"},
    )
    h.create_generic_record(
        cli, defs, "project:check-run", subject="a-check",
        extra_payload={"method": "check", "signed_by": "", "result": "pass", "effort": "alpha"},
    )
    return store


def _text(app, selector):
    return str(app.query_one(selector).render())


def _run(store, width, scenario, interval=60.0):
    async def go():
        app = app_module.DashboardApp(artifact_store.resolve(store), interval=interval)
        async with app.run_test(size=(width, 40)) as pilot:
            await _until(pilot, lambda: bool(app.query("#goal")) and bool(_text(app, "#goal")))
            await scenario(app, pilot)

    asyncio.run(go())


async def _until(pilot, condition, timeout=20.0):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        await pilot.pause(0.1)


@pytest.mark.parametrize("width", WIDTHS)
def test_shows_goal_stepper_progress_and_tiles(seeded, width):
    async def scenario(app, pilot):
        assert "ship the alpha dashboard" in _text(app, "#goal")
        stepper = _text(app, "#stepper")
        assert "✓ Phase one" in stepper and "● Phase two 0/3" in stepper and "○ Phase three" in stepper
        assert stepper.index("one") < stepper.index("two") < stepper.index("three")
        assert _text(app, "#progress-label") == "phase 2/3 · 0 of 3 tasks"
        bar = app.query_one("#progress")
        assert (bar.progress, bar.total) == (0, 3)
        tiles = {name: _text(app, f"#tile-{name}") for name in ("running", "ready", "needs", "done")}
        assert tiles["running"].split() == ["1", "Running"]
        assert tiles["ready"].split() == ["1", "Ready"]
        assert tiles["needs"].split() == ["1", "Needs", "you"]
        assert tiles["done"].split() == ["1", "Done"]

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_task_table_lists_rows_by_status_with_task_id_keys(seeded, width):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        rows = [table.get_row_at(i) for i in range(table.row_count)]
        statuses = [str(row[0]).split()[-1] for row in rows]
        assert statuses == ["running", "ready", "waiting", "done"]
        assert "title of a-running" in str(rows[0][1])
        assert "w" in str(rows[0][2])
        assert all(key.value for key in table.rows)

    _run(seeded, width, scenario)


def test_narrow_width_drops_phase_and_assignee_columns(seeded):
    async def scenario(app, pilot):
        labels = [str(col.label) for col in app.query_one("#tasks").columns.values()]
        assert labels == ["status", "task", "wave"]

    _run(seeded, 60, scenario)


def test_wide_width_shows_phase_and_assignee_columns(seeded):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        labels = [str(col.label) for col in table.columns.values()]
        assert labels == ["status", "task", "wave", "phase", "assignee"]
        assert "agent-7" in str(table.get_row_at(0)[4])

    _run(seeded, 120, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_needs_you_panel_and_activity_feed_show_their_items(seeded, width):
    async def scenario(app, pilot):
        assert app.query_one("#needs-you").display
        assert "which backend" in _text(app, "#needs-you")
        activity = _text(app, "#activity")
        assert "check: pass" in activity
        assert "now" in activity or "ago" in activity

    _run(seeded, width, scenario)


def test_needs_you_panel_is_hidden_when_nothing_needs_you(store, cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="calm", extra_payload={"goal": "stay calm", "kind": "deliver"},
    )

    async def scenario(app, pilot):
        assert not app.query_one("#needs-you").display

    _run(store, 60, scenario)


def test_empty_store_shows_the_empty_state(store):
    async def scenario(app, pilot):
        await _until(pilot, lambda: app.query_one("#empty").display)
        assert "No live efforts" in _text(app, "#empty")

    async def go():
        app = app_module.DashboardApp(artifact_store.resolve(store), interval=60.0)
        async with app.run_test(size=(60, 40)) as pilot:
            await scenario(app, pilot)

    asyncio.run(go())


def test_redraws_when_the_store_changes(seeded, cli, defs):
    async def scenario(app, pilot):
        assert app.query_one("#tasks").row_count == 4
        _work_item(cli, defs, "alpha", "a-fresh", "two")
        await _until(pilot, lambda: app.query_one("#tasks").row_count == 5)
        titles = [str(app.query_one("#tasks").get_row_at(i)[1]) for i in range(5)]
        assert any("title of a-fresh" in title for title in titles)

    _run(seeded, 120, scenario, interval=0.3)


def test_keeps_the_cursor_row_across_a_refresh(seeded, cli, defs):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        table.move_cursor(row=2)
        key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        _work_item(cli, defs, "alpha", "a-fresh", "two")
        await _until(pilot, lambda: table.row_count == 5)
        assert table.coordinate_to_cell_key(table.cursor_coordinate).row_key == key

    _run(seeded, 120, scenario, interval=0.3)


def test_q_quits(seeded):
    async def go():
        app = app_module.DashboardApp(artifact_store.resolve(seeded), interval=60.0)
        async with app.run_test(size=(60, 40)) as pilot:
            await pilot.press("q")
            await pilot.pause()
        assert not app.is_running

    asyncio.run(go())


def test_once_prints_a_plain_text_frame(seeded):
    result = subprocess.run(
        ["uv", "run", "--script", str(SCRIPT), "--once"], capture_output=True, text=True, cwd=str(seeded),
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "\x1b" not in out
    for needle in ("alpha", "ship the alpha dashboard", "✓ Phase one", "Running", "title of a-running", "which backend"):
        assert needle in out
    assert max(len(line) for line in out.splitlines()) <= 100


def test_once_without_a_store_exits_one(tmp_path):
    result = subprocess.run(
        ["uv", "run", "--script", str(SCRIPT), "--once"], capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 1
    assert "store" in result.stdout + result.stderr
