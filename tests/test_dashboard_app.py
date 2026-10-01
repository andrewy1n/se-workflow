"""Tests for scripts/dashboard_app: the Textual dashboard and its --once frame."""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
import time

import pytest

pytest.importorskip("textual")

import helpers as h  # noqa: E402
from conftest import REPO_ROOT, git  # noqa: E402

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
        cli, defs, "project:assignment", subject="a-assign",
        extra_payload={"work_item": running["id"], "executor": "sub-1", "effort": "alpha"},
    )
    h.create_generic_record(
        cli, defs, "project:execution-report", subject="a-report",
        extra_payload={"work_item": done["id"], "result": "done it", "verdict": "pass"},
    )
    h.create_generic_record(
        cli, defs, "project:check-run", subject="a-check",
        extra_payload={"method": "check", "signed_by": "", "result": "pass", "effort": "alpha"},
    )
    return store


def _text(app, selector):
    return str(app.query_one(selector).render())


def _run(store, width, scenario, interval=60.0, height=40):
    async def go():
        app = app_module.DashboardApp(artifact_store.resolve(store), interval=interval)
        async with app.run_test(size=(width, height)) as pilot:
            await _until(pilot, lambda: bool(app.query("#goal")) and bool(_text(app, "#goal")))
            await scenario(app, pilot)

    asyncio.run(go())


async def _until(pilot, condition, timeout=20.0):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        await pilot.pause(0.1)


@pytest.mark.parametrize("width", WIDTHS)
def test_shows_goal_stepper_and_progress(seeded, width):
    async def scenario(app, pilot):
        assert "ship the alpha dashboard" in _text(app, "#goal")
        stepper = _text(app, "#stepper")
        assert "✓ Phase one" in stepper and "● Phase two 0/3" in stepper and "○ Phase three" in stepper
        assert stepper.index("one") < stepper.index("two") < stepper.index("three")
        assert _text(app, "#progress-label") == "phase 2/3 · 1 of 4 tasks"
        bar = app.query_one("#progress")
        assert (bar.progress, bar.total) == (1, 4)

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_task_table_lists_rows_by_status_with_task_id_keys(seeded, width):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        rows = [table.get_row_at(i) for i in range(table.row_count) if not _is_section(list(table.rows)[i].value)]
        statuses = [str(row[0]).split()[-1] for row in rows]
        assert statuses == ["running", "ready", "waiting"]
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
        assert "agent-7" in str(table.get_row_at(1)[4])

    _run(seeded, 120, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_needs_you_panel_and_activity_feed_show_their_items(seeded, width):
    async def scenario(app, pilot):
        assert app.query_one("#needs-you").display
        assert "which backend" in _text(app, "#needs-you")
        activity = _text(app, "#activity")
        lines = activity.splitlines()
        assert len(lines) == 3
        assert any(line.endswith("a-check check passed") for line in lines)
        assert any(line.endswith("a-done reported pass") for line in lines)
        assert any(line.endswith("a-running assigned to sub-1") for line in lines)
        assert "(" not in activity
        assert "now" in activity or "ago" in activity

    _run(seeded, width, scenario)


def test_long_activity_lines_are_clipped_not_wrapped_at_60_columns(store, cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="alpha", extra_payload={"goal": "g", "kind": "deliver"},
    )
    item = _work_item(cli, defs, "alpha", "a-very-long-task-name-for-wrapping", "p")
    h.create_generic_record(
        cli, defs, "project:assignment", subject="a-assign",
        extra_payload={"work_item": item["id"], "executor": "sub-with-an-equally-long-executor-name", "effort": "alpha"},
    )

    async def scenario(app, pilot):
        lines = _text(app, "#activity").splitlines()
        assert len(lines) == 1
        assert lines[0].endswith("…") and len(lines[0]) <= 54

    _run(store, 60, scenario)


def test_footer_has_no_palette_and_every_binding_fits_at_60_columns(seeded):
    async def scenario(app, pilot):
        await pilot.pause()
        keys = list(app.query("FooterKey"))
        assert sorted(str(key.description) for key in keys) == ["copy", "filter", "open", "phase", "quit", "status", "switch"]
        assert all(key.region.right <= 60 for key in keys)

    _run(seeded, 60, scenario)


def test_task_title_uses_spare_width_at_120_columns(store, cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="alpha", extra_payload={"goal": "g", "kind": "deliver"},
    )
    title = "Integration-test the readable layout and verify 54ch"[:54]
    payload = {"title": title, "phase": "readable-layout", "kind": "deliver", "assignee": "sub-dashboard-snapshot", "effort": "alpha"}
    result = cli("create", "--type", "project:work-item", "--subject", "a-long", "--payload", json.dumps(payload),
                 "--body", h.generic_body(defs["project:work-item"]))
    assert result.returncode == 0, result.stdout

    async def scenario(app, pilot):
        await pilot.pause(0.5)
        assert str(app.query_one("#tasks").get_row_at(0)[1]) == title

    _run(store, 120, scenario)


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
        await _until(pilot, lambda: table.row_count == 4)
        assert table.coordinate_to_cell_key(table.cursor_coordinate).row_key == key

    _run(seeded, 120, scenario, interval=0.3)


def _titles(app):
    table = app.query_one("#tasks")
    return [
        str(table.get_row_at(i)[1]).strip() for i in range(table.row_count)
        if not _is_section(list(table.rows)[i].value)
    ]


def _is_section(key):
    return key == "fold" or key.startswith("phase:")


def _all_titles():
    return ["title of a-running", "title of a-ready", "title of a-waiting"]


def _second_effort(cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="beta", extra_payload={"goal": "ship beta", "kind": "deliver"},
    )
    _phase(cli, defs, "beta", "b-one", 1, "in_progress")
    _work_item(cli, defs, "beta", "b-task", "b-one")


@pytest.mark.parametrize("width", WIDTHS)
def test_slash_filter_narrows_rows_as_you_type_and_shows_in_the_title(seeded, width):
    async def scenario(app, pilot):
        await pilot.press("slash")
        await pilot.press(*"READY")
        await pilot.pause()
        assert _titles(app) == ["title of a-ready"]
        assert app.query_one("#tasks").border_title == "Tasks · 1 of 3 · /READY"
        assert app.query_one("#filter").has_focus

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_filter_matches_the_subject_as_well_as_the_title(seeded, width):
    async def scenario(app, pilot):
        await pilot.press("slash")
        await pilot.press(*"a-wait")
        await pilot.pause()
        assert _titles(app) == ["title of a-waiting"]

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_escape_in_the_filter_input_clears_the_filter(seeded, width):
    async def scenario(app, pilot):
        await pilot.press("slash")
        await pilot.press(*"ready")
        await pilot.press("escape")
        await pilot.pause()
        assert _titles(app) == _all_titles()
        assert app.query_one("#tasks").border_title == "Tasks"
        assert not app.query_one("#filter").display
        assert app.query_one("#tasks").has_focus

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_enter_keeps_the_filter_returns_focus_and_does_not_open_a_task(seeded, width):
    async def scenario(app, pilot):
        await pilot.press("slash")
        await pilot.press(*"ready")
        await pilot.press("enter")
        await pilot.pause(0.3)
        assert len(app.screen_stack) == 1
        assert _titles(app) == ["title of a-ready"]
        assert not app.query_one("#filter").display
        assert app.query_one("#tasks").has_focus
        assert app.query_one("#tasks").border_title == "Tasks · 1 of 3 · /ready"

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_escape_on_the_dashboard_clears_a_kept_filter(seeded, width):
    async def scenario(app, pilot):
        await pilot.press("slash")
        await pilot.press(*"ready")
        await pilot.press("enter")
        await pilot.press("escape")
        await pilot.pause()
        assert _titles(app) == _all_titles()
        assert app.query_one("#tasks").border_title == "Tasks"

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_slash_reopens_the_input_with_the_current_filter(seeded, width):
    async def scenario(app, pilot):
        await pilot.press("slash")
        await pilot.press(*"ready")
        await pilot.press("enter")
        await pilot.press("slash")
        await pilot.pause()
        box = app.query_one("#filter")
        assert box.display and box.has_focus and box.value == "ready"

    _run(seeded, width, scenario)


def _tab_labels(app):
    return {tab.tab_name: _text(app, f"#status-{tab.tab_name}") for tab in app.query(app_module.StatusTab)}


def _selected(app):
    return [tab.tab_name for tab in app.query(app_module.StatusTab) if tab.has_class("selected")]


def _needs_task(cli, defs):
    _record(cli, defs, "project:finding", "a-waiting",
            {"claim": "need a call", "basis": "b", "needs": "human", "effort": "alpha", "invalidated_when": "w"})


@pytest.mark.parametrize("width", WIDTHS)
def test_status_tabs_show_a_count_on_every_tab_and_default_to_active(seeded, cli, defs, width):
    _needs_task(cli, defs)

    async def scenario(app, pilot):
        await _until(pilot, lambda: _tab_labels(app).get("needs", "").endswith("1"))
        labels = _tab_labels(app)
        assert {k: v.split() for k, v in labels.items()} == {
            "active": ["Active", "3"], "running": ["Running", "1"], "ready": ["Ready", "1"],
            "waiting": ["Waiting", "1"], "needs": ["Needs", "you", "1"], "done": ["Done", "1"], "all": ["All", "4"],
        }
        assert all(tab.region.right <= width for tab in app.query(app_module.StatusTab))
        assert _selected(app) == ["active"]
        assert _titles(app) == _all_titles()
        assert not list(app.query("#tiles"))

    _run(seeded, width, scenario, interval=0.3)


@pytest.mark.parametrize("width", WIDTHS)
def test_number_keys_filter_the_table_by_status_tab(seeded, cli, defs, width):
    _needs_task(cli, defs)

    async def scenario(app, pilot):
        await _until(pilot, lambda: len(_titles(app)) == 3 and _tab_labels(app)["needs"].endswith("1"))
        expected = {
            "2": ("running", ["title of a-running"]), "3": ("ready", ["title of a-ready"]),
            "4": ("waiting", ["title of a-waiting"]), "5": ("needs", ["title of a-waiting"]),
            "6": ("done", ["title of a-done"]), "7": ("all", ["title of a-done"] + _all_titles()),
            "1": ("active", _all_titles()),
        }
        for key, (name, titles) in expected.items():
            await pilot.press(key)
            if key == "6":
                await pilot.press("enter")
            await pilot.pause()
            assert _titles(app) == titles
            assert _selected(app) == [name]

    _run(seeded, width, scenario, interval=0.3)


@pytest.mark.parametrize("width", WIDTHS)
def test_clicking_a_status_tab_filters_the_table(seeded, width):
    async def scenario(app, pilot):
        await pilot.click("#status-done")
        await pilot.press("enter")
        await pilot.pause()
        assert _titles(app) == ["title of a-done"]
        assert _selected(app) == ["done"]
        await pilot.click("#status-ready")
        await pilot.pause()
        assert _titles(app) == ["title of a-ready"]

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_needs_you_tab_is_empty_when_no_open_item_names_a_task(seeded, width):
    async def scenario(app, pilot):
        await pilot.press("5")
        await pilot.pause()
        assert _titles(app) == []
        assert app.query_one("#tasks-empty").display

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_status_tab_combines_with_the_slash_filter(seeded, width):
    async def scenario(app, pilot):
        await pilot.press("slash")
        await pilot.press(*"a-")
        await pilot.press("enter")
        await pilot.press("6")
        await pilot.press("enter")
        await pilot.pause()
        assert _titles(app) == ["title of a-done"]
        assert app.query_one("#tasks").border_title == "Tasks · 1 of 1 · /a-"
        await pilot.press("slash")
        await pilot.press(*"zz")
        await pilot.pause()
        assert _titles(app) == []
        await pilot.press("escape")
        await pilot.pause()
        assert _titles(app) == ["title of a-done"]
        assert _selected(app) == ["done"]

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_d_is_not_bound(seeded, width):
    async def scenario(app, pilot):
        before = _titles(app)
        await pilot.press("d")
        await pilot.pause()
        assert _titles(app) == before
        assert "d" not in app._bindings.key_to_bindings

    _run(seeded, width, scenario)

@pytest.mark.parametrize("width", WIDTHS)
def test_no_tasks_match_replaces_an_empty_table(seeded, width):
    async def scenario(app, pilot):
        await pilot.press("slash")
        await pilot.press(*"zzz")
        await pilot.pause()
        assert not app.query_one("#tasks").display
        assert app.query_one("#tasks-empty").display
        assert "No tasks match" in _text(app, "#tasks-empty")
        assert app.query_one("#tasks-empty").border_title == "Tasks · 0 of 3 · /zzz"
        await pilot.press("escape")
        await pilot.pause()
        assert app.query_one("#tasks").display
        assert not app.query_one("#tasks-empty").display

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_keeps_the_cursor_on_the_same_task_when_filtering(seeded, width):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        table.move_cursor(row=2)
        key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        await pilot.press("3")
        await pilot.pause()
        assert table.coordinate_to_cell_key(table.cursor_coordinate).row_key == key

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_status_tab_is_per_effort_tab(seeded, cli, defs, width):
    _second_effort(cli, defs)

    async def scenario(app, pilot):
        await _until(pilot, lambda: len(app.panes) == 2)
        tabs = app.query_one("#efforts")
        first = tabs.active
        await pilot.press("6")
        await pilot.press("enter")
        await pilot.press("tab")
        await pilot.pause()
        assert tabs.active != first
        other = tabs.active_pane.query_one("#tasks")
        assert other.border_title == "Tasks" and other.row_count == 2
        await pilot.press("shift+tab")
        await pilot.pause()
        assert tabs.active == first
        assert _titles(app) == ["title of a-done"]
        assert "selected" not in other.query_ancestor(app_module.EffortPane).query_one("#status-done").classes

    _run(seeded, width, scenario)


def _record(cli, defs, record_type, subject, payload, body=None, *rels):
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
def detailed(store, cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="alpha", extra_payload={"goal": "ship it", "kind": "deliver"},
    )
    _phase(cli, defs, "alpha", "det-phase", 1, "in_progress")
    busy = _work_item(cli, defs, "alpha", "det-busy", "det-phase")
    h.transition(cli, "project:work-item", busy, "in_progress")
    dep = _work_item(cli, defs, "alpha", "det-dep", "det-phase")
    h.transition(cli, "project:work-item", dep, "in_progress", "done")
    payload = {"title": "Detail task", "phase": "det-phase", "kind": "deliver", "assignee": "sub-d", "effort": "alpha"}
    task = _record(
        cli, defs, "project:work-item", "det-task", payload,
        "## Description\n\nBuild the **detail** screen.\n\n- first point\n- second point", f"depends_on:{dep['id']}",
    )
    h.transition(cli, "project:work-item", task, "in_progress")
    _work_item(cli, defs, "alpha", "det-blocked", "det-phase", f"depends_on:{task['id']}")
    tests = _record(cli, defs, "project:acceptance", "det-task", {
        "criterion": "unit tests pass", "method": "check", "verify_command": "pytest -q", "effort": "alpha", "phase": "det-phase"})
    review = _record(cli, defs, "project:acceptance", "det-task-review", {
        "criterion": "reviewer approves", "method": "manual", "verify_command": "", "effort": "alpha", "phase": "det-phase"})
    _record(cli, defs, "project:acceptance", "det-task-docs", {
        "criterion": "docs updated", "method": "manual", "verify_command": "", "effort": "alpha", "phase": "det-phase"})
    assignment = _record(
        cli, defs, "project:assignment", "det-task",
        {"work_item": task["id"], "executor": "sub-d", "effort": "alpha"}, "## Orientation\n\nstart in the app module",
    )
    _record(cli, defs, "project:assignment-amendment", "det-task",
            {"assignment": "det-task", "effort": "alpha"}, "## Correction\n\nuse the loader")
    h.run_cli_48h_ago(
        store, "create", "--type", "project:execution-report", "--subject", "det-task-first", "--body", "first attempt notes",
        "--payload", json.dumps({"work_item": task["id"], "assignment": assignment["id"], "result": "no", "verdict": "fail", "revision": "r1"}),
    )
    _record(cli, defs, "project:execution-report", "det-task",
            {"work_item": task["id"], "assignment": assignment["id"], "result": "ok", "verdict": "pass", "revision": "r2"},
            "```\nsubject: det-task\nresult: pass\nevidence: second attempt notes that run long enough to wrap "
            "under the value column at sixty columns\nverdict: pass\nneeds_human: false\n```\n\nclosing **remarks**")
    _record(cli, defs, "project:check-run", "det-task", {
        "criterion_id": tests["id"], "method": "check", "result": "pass", "signed_by": "", "revision": "abc1234", "effort": "alpha"})
    _record(cli, defs, "project:check-run", "det-task-review", {
        "criterion_id": review["id"], "method": "manual", "result": "pass", "signed_by": "", "revision": "def5678", "effort": "alpha"})
    _record(cli, defs, "project:finding", "det-task",
            {"claim": "parser drops tabs", "basis": "b", "needs": "agent", "effort": "alpha", "invalidated_when": "w"})
    return store, task, tests


DETAIL_SIZES = ((60, 40), (160, 50))


def _row_offset(table, key):
    return 4, 2 + table.get_row_index(key)


def _cursor_key(table):
    return table.coordinate_to_cell_key(table.cursor_coordinate).row_key


def _detail_run(store, size, scenario, interval=60.0):
    async def go():
        app = app_module.DashboardApp(artifact_store.resolve(store), interval=interval)
        async with app.run_test(size=size) as pilot:
            await _until(pilot, lambda: app.query("#tasks") and app.query_one("#tasks").row_count >= 3)
            await scenario(app, pilot)

    asyncio.run(go())


async def _open_by_enter(app, pilot, key):
    table = app.query_one("#tasks")
    table.focus()
    table.move_cursor(row=table.get_row_index(key))
    await pilot.pause()
    await pilot.press("enter")


async def _open_by_click(app, pilot, key):
    table = app.query_one("#tasks")
    assert table.get_row_index(key) > 0
    await pilot.click("#tasks", offset=_row_offset(table, key))


async def _shown(app, pilot):
    await _until(pilot, lambda: isinstance(app.screen, app_module.TaskDetailScreen) and app.screen.loaded)
    await pilot.pause(0.3)
    return app.screen


def _acceptance_rows(screen):
    return [
        f"{row.query_one('.mark').render()} {row.query_one('.body').render()}"
        for row in screen.query(".acceptance") if row.query(".mark") and row.query(".body")
    ]


def _lines(screen, selector):
    return str(screen.query_one(selector).render()).splitlines()


OPENERS = pytest.mark.parametrize("opener", (_open_by_enter, _open_by_click))


@OPENERS
@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_detail_screen_shows_header_chips_and_linked_tasks(detailed, size, opener):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await opener(app, pilot, task["id"])
        screen = await _shown(app, pilot)
        assert "Detail task" in _text(screen, "#detail-title")
        chips = _text(screen, "#detail-chips")
        assert "▶ running" in chips and "phase det-phase" in chips and "w2" in chips and "assignee sub-d" in chips
        assert _text(screen, "#detail-depends").strip() == "Depends on: ✓ det-dep"
        assert _text(screen, "#detail-blocks").strip() == "Blocks: ◌ det-blocked"
        assert "det-task" in _text(screen, "#detail-bar") and "alpha" in _text(screen, "#detail-bar")

    _detail_run(store, size, scenario)


@OPENERS
@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_detail_screen_renders_the_description_as_markdown_without_its_heading(detailed, size, opener):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await opener(app, pilot, task["id"])
        screen = await _shown(app, pilot)
        markdown = screen.query_one("#description Markdown")
        assert "Build the **detail** screen." in markdown.source
        assert "## Description" not in markdown.source
        assert len(markdown.query("MarkdownBulletList")) == 1
        assert screen.query_one("#description").border_title == "Description"

    _detail_run(store, size, scenario)


@OPENERS
@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_detail_screen_lists_acceptances_with_result_glyphs_and_method_lines(detailed, size, opener):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await opener(app, pilot, task["id"])
        screen = await _shown(app, pilot)
        rows = _acceptance_rows(screen)
        by_criterion = {row.splitlines()[0]: row.splitlines() for row in rows}
        assert by_criterion["✓ unit tests pass"] == ["✓ unit tests pass", "check · pytest -q", "rev abc1234"]
        assert by_criterion["✓ reviewer approves"] == ["✓ reviewer approves", "manual", "rev def5678 · unsigned"]
        assert by_criterion["– docs updated"] == ["– docs updated", "manual"]
        assert len(rows) == 3

    _detail_run(store, size, scenario)


@OPENERS
@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_detail_timeline_is_oldest_first_with_only_the_newest_report_expanded(detailed, size, opener):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await opener(app, pilot, task["id"])
        screen = await _shown(app, pilot)
        titles = [str(widget.title) if hasattr(widget, "title") else str(widget.render()) for widget in screen.query(".event")]
        summaries = ["reported fail", "assigned to sub-d", "amended", "reported pass"]
        positions = [next(i for i, title in enumerate(titles) if summary in title) for summary in summaries]
        assert positions == sorted(positions)
        assert sorted(i for i, title in enumerate(titles) if "check passed" in title) == [4, 5]
        by_title = {re.search(r"[≡→·◇] .*", str(c.title)).group(): c for c in screen.query("Collapsible")}
        assert not by_title["≡ reported pass"].collapsed
        assert by_title["≡ reported fail"].collapsed and by_title["→ assigned to sub-d"].collapsed
        assert by_title["· amended"].collapsed
        assert by_title["≡ reported fail"].query_one("Markdown").source == "first attempt notes"
        assert "now" in titles[-1] or "ago" in titles[-1]

    _detail_run(store, size, scenario)


@OPENERS
@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_report_body_renders_fenced_fields_as_a_key_value_list_and_the_rest_as_markdown(detailed, size, opener):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await opener(app, pilot, task["id"])
        screen = await _shown(app, pilot)
        newest = next(c for c in screen.query("Collapsible") if "reported pass" in str(c.title))
        rows = [(str(r.query_one(".key").render()), str(r.query_one(".value").render())) for r in newest.query(".field")]
        assert [key for key, _ in rows] == ["subject", "result", "evidence", "verdict", "needs_human"]
        assert dict(rows)["evidence"].endswith("under the value column at sixty columns")
        assert not newest.query("MarkdownFence")
        assert [m.source for m in newest.query("Markdown")] == ["closing **remarks**"]
        styles = {key: r.query_one(".value").render().spans for (key, _), r in zip(rows, newest.query(".field"))}
        assert styles["result"] and not styles["subject"]

    _detail_run(store, size, scenario)


def test_split_fields_joins_continuation_lines_and_ignores_plain_markdown():
    assert app_module.split_fields("```\na: 1\nb: two\n  more\n```") == ([("a", "1"), ("b", "two more")], "")
    assert app_module.split_fields("```\na: 1\n```\n\nafter") == ([("a", "1")], "after")
    assert app_module.split_fields("plain **text**") is None
    assert app_module.split_fields("```python\nprint(1)\n```") is None


def test_chips_never_split_a_label_from_its_value_when_narrow():
    detail = app_module.model.TaskDetail(
        "i", "s", "e", "t", "done", "task-details", 1, "sub-task-detail-model", "", [], [], [], [], [])
    colors = app_module.ANSI_PALETTE
    lines = app_module.detail_chips(detail, colors, 40).plain.splitlines()
    assert lines == ["✓ done · phase task-details · w1", "assignee sub-task-detail-model"]
    assert app_module.detail_chips(detail, colors, 100).plain == "✓ done · phase task-details · w1 · assignee sub-task-detail-model"


@OPENERS
@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_detail_related_panel_lists_related_records(detailed, size, opener):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await opener(app, pilot, task["id"])
        screen = await _shown(app, pilot)
        assert _lines(screen, "#related") == ["finding: parser drops tabs"]

    _detail_run(store, size, scenario)


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_detail_related_panel_is_hidden_without_related_records(detailed, cli, size):
    store, task, _ = detailed

    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        blocked = next(k.value for k in table.rows if "det-blocked" in str(table.get_row(k.value)[1]))
        await _open_by_click(app, pilot, blocked)
        screen = await _shown(app, pilot)
        assert not screen.query_one("#related").display

    _detail_run(store, size, scenario)


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_detail_screen_redraws_when_the_store_changes(detailed, cli, defs, size):
    store, task, tests = detailed

    async def scenario(app, pilot):
        await _open_by_enter(app, pilot, task["id"])
        screen = await _shown(app, pilot)
        assert "✗" not in "".join(_acceptance_rows(screen))
        _record(cli, defs, "project:check-run", "det-task", {
            "criterion_id": tests["id"], "method": "check", "result": "fail", "signed_by": "", "revision": "fff9999", "effort": "alpha"})
        await _until(pilot, lambda: "✗ unit tests pass" in "\n".join(_acceptance_rows(screen)))
        await _until(pilot, lambda: any("check failed" in str(w.render()) for w in screen.query(".event") if not hasattr(w, "title")))

    _detail_run(store, size, scenario, interval=0.3)


def test_detail_paint_is_skipped_when_the_screen_is_torn_down_mid_render(detailed):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await _open_by_enter(app, pilot, task["id"])
        screen = await _shown(app, pilot)
        detail = screen.detail
        await screen.query_one("#related").remove()
        await screen.paint(detail)

    _detail_run(store, (160, 50), scenario)


@pytest.mark.parametrize("opener", (_open_by_enter, _open_by_click))
@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_escape_returns_to_the_dashboard_on_the_same_row(detailed, size, opener):
    store, task, _ = detailed

    async def scenario(app, pilot):
        dashboard = app.screen
        tab = app.query_one("#efforts").active
        await opener(app, pilot, task["id"])
        await _shown(app, pilot)
        await pilot.press("escape")
        await _until(pilot, lambda: app.screen is dashboard)
        table = app.query_one("#tasks")
        assert _cursor_key(table).value == task["id"]
        assert app.query_one("#efforts").active == tab
        assert len(app.screen_stack) == 1

    _detail_run(store, size, scenario)


def test_one_click_pushes_a_single_detail_screen(detailed):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await _open_by_click(app, pilot, task["id"])
        await _shown(app, pilot)
        assert len(app.screen_stack) == 2

    _detail_run(store, (60, 40), scenario)


def test_detail_footer_shows_back_copy_commit_refresh_and_quit_within_60_columns(detailed):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await _open_by_enter(app, pilot, task["id"])
        await _shown(app, pilot)
        keys = list(app.screen.query("FooterKey"))
        assert sorted(str(key.description) for key in keys) == ["back", "commit", "copy", "quit", "refresh"]
        assert all(key.region.right <= 60 for key in keys)

    _detail_run(store, (60, 40), scenario)


def test_detail_shows_loading_then_content(detailed):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await _open_by_enter(app, pilot, task["id"])
        screen = app.screen
        assert "Loading" in _text(screen, "#detail-loading") or screen.loaded
        await _shown(app, pilot)
        assert not screen.query_one("#detail-loading").display

    _detail_run(store, (60, 40), scenario)


@pytest.fixture()
def committed(store, cli, defs):
    (store / "feature.txt").write_text("one\ntwo\n")
    git(store, "add", "feature.txt")
    done = git(store, "commit", "-q", "-m", "add the feature file", "-m", "Body line for the feature.")
    assert done.returncode == 0, done.stderr
    sha = git(store, "rev-parse", "HEAD").stdout.strip()
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="alpha", extra_payload={"goal": "ship it", "kind": "deliver"},
    )
    _phase(cli, defs, "alpha", "c-phase", 1, "in_progress")
    tasks = {}
    for name, revisions in {
        "c-good": ("dirty", sha), "c-dirty": ("dirty",), "c-unknown": ("0123456789abcdef0123456789abcdef01234567",), "c-none": (),
    }.items():
        tasks[name] = _work_item(cli, defs, "alpha", name, "c-phase")
        for index, revision in enumerate(revisions):
            _record(cli, defs, "project:execution-report", f"{name}-{index}", {
                "work_item": tasks[name]["id"], "assignment": "x", "result": "ok", "verdict": "pass", "revision": revision})
    return store, tasks, sha


def _notices(app):
    return [note.message for note in app._notifications]


async def _open_task(app, pilot, task):
    await _open_by_enter(app, pilot, task["id"])
    return await _shown(app, pilot)


async def _commit_shown(app, pilot):
    await _until(pilot, lambda: isinstance(app.screen, app_module.CommitScreen) and app.screen.loaded)
    await pilot.pause(0.2)
    return app.screen


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_c_on_the_dashboard_copies_the_cursor_row_slug_and_notifies(committed, size):
    store, tasks, _ = committed

    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        table.focus()
        table.move_cursor(row=table.get_row_index(tasks["c-dirty"]["id"]))
        await pilot.pause()
        await pilot.press("c")
        await pilot.pause()
        assert app.clipboard == "c-dirty"
        assert "Copied c-dirty" in _notices(app)

    _detail_run(store, size, scenario)


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_c_on_the_detail_screen_copies_the_shown_slug_and_notifies(committed, size):
    store, tasks, _ = committed

    async def scenario(app, pilot):
        await _open_task(app, pilot, tasks["c-unknown"])
        await pilot.press("c")
        await pilot.pause()
        assert app.clipboard == "c-unknown"
        assert "Copied c-unknown" in _notices(app)

    _detail_run(store, size, scenario)


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_g_opens_the_commit_screen_with_the_message_and_stat_of_the_latest_revision(committed, size):
    store, tasks, sha = committed

    async def scenario(app, pilot):
        await _open_task(app, pilot, tasks["c-good"])
        await pilot.press("g")
        screen = await _commit_shown(app, pilot)
        assert str(screen.query_one("#commit-bar").render()).split()[:4] == [sha[:7], "add", "the", "feature"]
        header = str(screen.query_one("#commit-header").render())
        assert sha in header and "test" in header and "add the feature file" in header
        assert "Body line for the feature." in str(screen.query_one("#commit-message").render())
        stat = str(screen.query_one("#commit-stat").render())
        assert "feature.txt" in stat and "++" in stat

    _detail_run(store, size, scenario)


@pytest.mark.parametrize("size", ((60, 40), (80, 40)))
def test_commit_stat_lines_with_a_long_path_fit_on_one_line_at_the_pane_width(committed, size):
    store, tasks, _ = committed
    long_path = store / "scripts/some/really/long/directory/name/dashboard_model_extension.py"
    long_path.parent.mkdir(parents=True)
    long_path.write_text("x\n" * 300)
    (store / "short.py").write_text("y\n" * 200)
    git(store, "add", "scripts", "short.py")
    assert git(store, "commit", "-q", "-m", "wide stat").returncode == 0
    wide = git(store, "rev-parse", "HEAD").stdout.strip()

    async def scenario(app, pilot):
        app.push_screen(app_module.CommitScreen(app_module.load_commit(store, wide, app_module.stat_width(app)), store, wide))
        screen = await _commit_shown(app, pilot)
        stat = screen.query_one("#commit-stat")
        lines = str(stat.render()).splitlines()
        assert len(lines) == 3
        assert all(len(line) <= stat.size.width for line in lines)
        assert all(line.rstrip().split("|")[1].split()[0].isdigit() and line.rstrip()[-1] in "+-" for line in lines[:2])

    _detail_run(store, size, scenario)


def test_commit_stat_reloads_at_the_new_width_after_a_resize(committed):
    store, tasks, _ = committed
    (store / "scripts").mkdir()
    (store / "scripts/a_really_long_file_name_for_the_stat_width_check.py").write_text("x\n" * 300)
    git(store, "add", "scripts")
    assert git(store, "commit", "-q", "-m", "resize stat").returncode == 0
    rev = git(store, "rev-parse", "HEAD").stdout.strip()

    async def scenario(app, pilot):
        app.push_screen(app_module.CommitScreen(app_module.load_commit(store, rev, 76), store, rev))
        screen = await _commit_shown(app, pilot)
        await pilot.resize_terminal(60, 40)
        await _until(pilot, lambda: all(len(l) <= 56 for l in str(screen.query_one("#commit-stat").render()).splitlines()))

    _detail_run(store, (80, 40), scenario)


def test_escape_on_the_commit_screen_returns_to_the_detail_screen(committed):
    store, tasks, _ = committed

    async def scenario(app, pilot):
        detail = await _open_task(app, pilot, tasks["c-good"])
        await pilot.press("g")
        await _commit_shown(app, pilot)
        await pilot.press("escape")
        await _until(pilot, lambda: app.screen is detail)
        assert len(app.screen_stack) == 2

    _detail_run(store, (60, 40), scenario)


def test_commit_footer_shows_back_and_quit_within_60_columns(committed):
    store, tasks, _ = committed

    async def scenario(app, pilot):
        await _open_task(app, pilot, tasks["c-good"])
        await pilot.press("g")
        screen = await _commit_shown(app, pilot)
        keys = list(screen.query("FooterKey"))
        assert sorted(str(key.description) for key in keys) == ["back", "quit"]
        assert all(key.region.right <= 60 for key in keys)

    _detail_run(store, (60, 40), scenario)


@pytest.mark.parametrize("name, message", [
    ("c-none", "No revision recorded for c-none"),
    ("c-dirty", "Only uncommitted (dirty) revisions recorded"),
    ("c-unknown", "not found in"),
])
def test_g_shows_a_message_and_stays_on_the_detail_for_missing_dirty_or_unknown_revisions(committed, name, message):
    store, tasks, _ = committed

    async def scenario(app, pilot):
        detail = await _open_task(app, pilot, tasks[name])
        await pilot.press("g")
        await _until(pilot, lambda: any(message in note for note in _notices(app)))
        assert app.screen is detail

    _detail_run(store, (60, 40), scenario)


def test_the_task_table_has_focus_on_load(seeded):
    async def scenario(app, pilot):
        assert app.focused is app.query_one("#tasks")

    _run(seeded, 120, scenario)


@pytest.mark.parametrize("down, up", (("down", "up"), ("j", "k")))
def test_down_and_up_or_j_and_k_move_the_task_cursor(seeded, down, up):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        await pilot.press(down, down)
        assert table.cursor_row == 2
        await pilot.press(up)
        assert table.cursor_row == 1

    _run(seeded, 120, scenario)


def test_enter_opens_the_task_below_the_first_row_using_only_keys(seeded):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        await pilot.press("down", "down")
        key = _cursor_key(table).value
        assert table.cursor_row == 2
        await pilot.press("enter")
        await _until(pilot, lambda: isinstance(app.screen, app_module.TaskDetailScreen))
        assert app.screen.task_id == key

    _run(seeded, 120, scenario)


def test_table_keeps_focus_after_switching_effort_tabs(seeded, cli, defs):
    _second_effort(cli, defs)

    async def scenario(app, pilot):
        await _until(pilot, lambda: len(app.panes) == 2)
        await pilot.press("tab")
        await pilot.pause()
        assert app.focused is app.active_pane().query_one("#tasks")
        await pilot.press("shift+tab")
        await pilot.pause()
        assert app.focused is app.active_pane().query_one("#tasks")
        await pilot.press("down")
        assert app.query_one("#efforts").active_pane.query_one("#tasks").cursor_row == 1

    _run(seeded, 120, scenario)


def test_table_keeps_focus_after_escape_from_detail(detailed):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await pilot.press("down")
        await pilot.press("enter")
        await _shown(app, pilot)
        await pilot.press("escape")
        await pilot.pause(0.2)
        assert app.focused is app.query_one("#tasks")
        await pilot.press("down")
        assert app.query_one("#tasks").cursor_row == 2

    _detail_run(store, (120, 40), scenario)


def test_filter_input_takes_focus_and_hands_it_back_to_the_table(seeded):
    async def scenario(app, pilot):
        await pilot.press("slash")
        assert app.focused is app.query_one("#filter")
        await pilot.press("enter")
        assert app.focused is app.query_one("#tasks")
        await pilot.press("slash", "escape")
        assert app.focused is app.query_one("#tasks")

    _run(seeded, 120, scenario)


def test_pagedown_and_end_scroll_the_effort_pane_to_activity_and_home_returns(seeded):
    async def scenario(app, pilot):
        pane = app.active_pane()
        assert pane.max_scroll_y > 0 and pane.scroll_y == 0
        await pilot.press("pagedown")
        await pilot.pause(0.3)
        assert pane.scroll_y > 0
        await pilot.press("end")
        await pilot.pause(0.3)
        assert pane.scroll_y == pane.max_scroll_y
        assert pane.query_one("#activity").region.bottom <= pane.region.bottom
        await pilot.press("pageup")
        await pilot.pause(0.3)
        assert pane.scroll_y < pane.max_scroll_y
        await pilot.press("home")
        await pilot.pause(0.3)
        assert pane.scroll_y == 0
        assert app.query_one("#tasks").cursor_row == 0

    _run(seeded, 100, scenario, height=24)


@pytest.mark.parametrize("keys", (("down",), ("pagedown",), ("end",)))
def test_arrows_and_page_keys_scroll_the_detail_screen(detailed, keys):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await _open_task(app, pilot, task)
        scroll = app.screen.query_one("#detail")
        assert app.focused is scroll
        assert scroll.max_scroll_y > 0 and scroll.scroll_y == 0
        await pilot.press(*keys)
        await pilot.pause(0.3)
        assert scroll.scroll_y > 0
        await pilot.press("home")
        await pilot.pause(0.3)
        assert scroll.scroll_y == 0

    _detail_run(store, (60, 20), scenario)


def test_arrows_scroll_the_commit_screen(committed):
    store, tasks, _ = committed

    async def scenario(app, pilot):
        await _open_task(app, pilot, tasks["c-good"])
        await pilot.press("g")
        screen = await _commit_shown(app, pilot)
        scroll = screen.query_one("#commit")
        assert app.focused is scroll
        assert scroll.max_scroll_y > 0
        await pilot.press("down")
        await pilot.pause(0.3)
        assert scroll.scroll_y > 0
        await pilot.press("end")
        await pilot.pause(0.3)
        assert scroll.scroll_y == scroll.max_scroll_y

    _detail_run(store, (60, 10), scenario)


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


@pytest.mark.parametrize("width", WIDTHS)
def test_left_and_right_step_the_status_tabs_and_wrap(seeded, width):
    async def scenario(app, pilot):
        await pilot.press("right")
        await pilot.pause()
        assert _selected(app) == ["running"]
        assert _titles(app) == ["title of a-running"]
        await pilot.press("left", "left")
        await pilot.pause()
        assert _selected(app) == ["all"]
        assert len(_titles(app)) == 3 and "phase:one" in _keys(app)

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_status_tab_survives_a_store_refresh(seeded, cli, defs, width):
    async def scenario(app, pilot):
        await pilot.press("6")
        await pilot.press("enter")
        _work_item(cli, defs, "alpha", "a-fresh", "two")
        await _until(pilot, lambda: _tab_labels(app)["all"].split()[-1] == "5")
        assert _selected(app) == ["done"]
        assert _titles(app) == ["title of a-done"]

    _run(seeded, width, scenario, interval=0.3)


@pytest.fixture()
def phased(store, cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="alpha", extra_payload={"goal": "ship it", "kind": "deliver"},
    )
    for ordinal, name in enumerate(("d1", "d2", "d3", "d4"), 1):
        _phase(cli, defs, "alpha", name, ordinal, "in_progress", "done")
        done = _work_item(cli, defs, "alpha", f"{name}-task", name)
        h.transition(cli, "project:work-item", done, "in_progress", "done")
    _phase(cli, defs, "alpha", "cur", 5, "in_progress")
    _phase(cli, defs, "alpha", "sign", 6, "in_progress")
    _phase(cli, defs, "alpha", "later", 7)
    running = _work_item(cli, defs, "alpha", "cur-run", "cur")
    h.transition(cli, "project:work-item", running, "in_progress")
    _work_item(cli, defs, "alpha", "cur-ready", "cur")
    waiting = _work_item(cli, defs, "alpha", "sign-task", "sign")
    h.transition(cli, "project:work-item", waiting, "in_progress")
    acceptance = _record(cli, defs, "project:acceptance", "sign-task", {
        "criterion": "reviewed", "method": "manual", "verify_command": "", "effort": "alpha", "phase": "sign"})
    _record(cli, defs, "project:check-run", "sign-task", {
        "criterion_id": acceptance["id"], "method": "manual", "result": "pass", "signed_by": "", "revision": "r", "effort": "alpha"})
    _work_item(cli, defs, "alpha", "later-task", "later")
    _record(cli, defs, "project:decision", "cur-choice",
            {"choice": "go left", "alternatives": "right", "effort": "alpha", "phase": "cur"})
    _record(cli, defs, "project:constraint", "cur-limit",
            {"statement": "no network", "applies_to": "cur", "effort": "alpha"})
    return store


def _keys(app):
    table = app.query_one("#tasks")
    return [key.value for key in table.rows]


def _row_text(app, key):
    table = app.query_one("#tasks")
    return " ".join(str(cell) for cell in table.get_row(key))


def _sections(keys):
    return [key for key in keys if _is_section(key)]


@pytest.mark.parametrize("width", WIDTHS)
def test_tasks_group_under_phase_headers_with_planned_phases_collapsed(phased, width):
    async def scenario(app, pilot):
        keys = _keys(app)
        assert _sections(keys) == ["phase:cur", "phase:sign", "phase:later"]
        assert keys.index("phase:cur") < keys.index("phase:sign") < keys.index("phase:later")
        assert keys.index("phase:later") == len(keys) - 1
        assert len(keys) == 6
        assert "▾" in _row_text(app, "phase:cur") and "Phase cur" in _row_text(app, "phase:cur")
        assert "▸" in _row_text(app, "phase:later")

    _run(phased, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_a_phase_awaiting_sign_off_expands_and_says_so(phased, width):
    async def scenario(app, pilot):
        assert "awaiting sign-off" in _row_text(app, "phase:sign")
        assert "awaiting sign-off" not in _row_text(app, "phase:cur")
        assert "▾" in _row_text(app, "phase:sign")

    _run(phased, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_done_phases_collapse_and_older_ones_fold_into_one_row(phased, width):
    async def scenario(app, pilot):
        await pilot.press("7")
        await pilot.pause()
        keys = _keys(app)
        assert keys[:3] == ["fold", "phase:d3", "phase:d4"]
        assert "2 earlier phases done" in _row_text(app, "fold")
        assert not any(key.startswith("phase:d1") or key.startswith("phase:d2") for key in keys)
        assert all("-task" not in key for key in keys[:3])
        assert "▸" in _row_text(app, "phase:d4")

    _run(phased, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_enter_on_the_fold_row_expands_and_collapses_the_older_phases(phased, width):
    async def scenario(app, pilot):
        await pilot.press("7")
        await pilot.pause()
        app.query_one("#tasks").move_cursor(row=0)
        await pilot.press("enter")
        await pilot.pause()
        assert _keys(app)[:5] == ["fold", "phase:d1", "phase:d2", "phase:d3", "phase:d4"]
        assert not isinstance(app.screen, app_module.TaskDetailScreen)
        await pilot.press("enter")
        await pilot.pause()
        assert _keys(app)[:3] == ["fold", "phase:d3", "phase:d4"]

    _run(phased, 120, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_two_done_phases_do_not_fold(store, cli, defs, width):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="alpha", extra_payload={"goal": "ship it", "kind": "deliver"},
    )
    for ordinal, name in enumerate(("d1", "d2"), 1):
        _phase(cli, defs, "alpha", name, ordinal, "in_progress", "done")
        done = _work_item(cli, defs, "alpha", f"{name}-task", name)
        h.transition(cli, "project:work-item", done, "in_progress", "done")

    async def scenario(app, pilot):
        await pilot.press("7")
        await pilot.pause()
        assert _keys(app) == ["phase:d1", "phase:d2"]

    _run(store, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_enter_on_a_header_toggles_its_tasks_and_keeps_the_cursor_on_it(phased, width):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        assert _keys(app)[0] == "phase:cur"
        await pilot.press("enter")
        await pilot.pause()
        assert _keys(app) == ["phase:cur", "phase:sign", _keys(app)[2], "phase:later"]
        assert _cursor_key(table).value == "phase:cur"
        assert "▸" in _row_text(app, "phase:cur")
        await pilot.press("enter")
        await pilot.pause()
        assert len(_keys(app)) == 6
        assert not isinstance(app.screen, app_module.TaskDetailScreen)

    _run(phased, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_enter_on_a_collapsed_planned_header_shows_its_tasks(phased, width):
    async def scenario(app, pilot):
        await pilot.press("end")
        table = app.query_one("#tasks")
        table.move_cursor(row=table.get_row_index("phase:later"))
        await pilot.press("enter")
        await pilot.pause()
        keys = _keys(app)
        assert keys[-1] != "phase:later" and keys[-2] == "phase:later"

    _run(phased, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_clicking_a_header_toggles_it_once(phased, width):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        await pilot.click("#tasks", offset=_row_offset(table, "phase:sign"))
        await pilot.pause()
        keys = _keys(app)
        assert keys[keys.index("phase:sign") + 1] == "phase:later"
        assert not isinstance(app.screen, app_module.TaskDetailScreen)
        await pilot.click("#tasks", offset=_row_offset(table, "phase:sign"))
        await pilot.pause()
        assert len(_keys(app)) == 6

    _run(phased, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_a_collapsed_phase_stays_collapsed_across_a_store_refresh(phased, cli, defs, width):
    async def scenario(app, pilot):
        await pilot.press("enter")
        await pilot.pause()
        _work_item(cli, defs, "alpha", "cur-fresh", "cur")
        await _until(pilot, lambda: _tab_labels(app)["all"].split()[-1] == "9")
        assert "▸" in _row_text(app, "phase:cur")
        assert len(_keys(app)) == 4

    _run(phased, width, scenario, interval=0.3)


@pytest.mark.parametrize("width", WIDTHS)
def test_the_slash_filter_hides_phases_without_matching_tasks(phased, width):
    async def scenario(app, pilot):
        await pilot.press("slash")
        await pilot.press(*"cur-run")
        await pilot.pause()
        assert _sections(_keys(app)) == ["phase:cur"]
        assert _titles(app) == ["title of cur-run"]

    _run(phased, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_progress_covers_the_whole_effort(phased, width):
    async def scenario(app, pilot):
        assert _text(app, "#progress-label") == "phase 5/7 · 4 of 8 tasks"
        bar = app.query_one("#progress")
        assert (bar.progress, bar.total) == (4, 8)

    _run(phased, width, scenario)


async def _phase_shown(app, pilot):
    await _until(pilot, lambda: isinstance(app.screen, app_module.PhaseDetailScreen) and app.screen.loaded)
    await pilot.pause(0.3)
    return app.screen


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_p_on_a_header_opens_the_phase_detail_with_body_decisions_constraints_and_tasks(phased, size):
    async def scenario(app, pilot):
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        assert screen.phase_subject == "cur"
        assert "Phase cur" in str(screen.query_one("#phase-bar").render())
        assert "placeholder text for Problem" in screen.query_one("#phase-body Markdown").source
        assert "go left" in str(screen.query_one("#phase-decisions").render())
        assert "no network" in str(screen.query_one("#phase-constraints").render())
        tasks = str(screen.query_one("#phase-tasks").render())
        assert "title of cur-run" in tasks and "title of cur-ready" in tasks and "later-task" not in tasks
        await pilot.press("escape")
        await pilot.pause(0.3)
        assert not isinstance(app.screen, app_module.PhaseDetailScreen)
        assert app.focused is app.query_one("#tasks")

    _detail_run(phased, size, scenario)


def test_p_on_a_task_row_opens_the_detail_of_that_tasks_phase(phased):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        table.move_cursor(row=table.get_row_index("phase:sign") + 1)
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        assert screen.phase_subject == "sign"
        assert "awaiting sign-off" in str(screen.query_one("#phase-chips").render())

    _detail_run(phased, (120, 40), scenario)


def test_p_does_nothing_on_the_fold_row(phased):
    async def scenario(app, pilot):
        await pilot.press("7")
        await pilot.pause()
        app.query_one("#tasks").move_cursor(row=0)
        await pilot.press("p")
        await pilot.pause(0.3)
        assert not isinstance(app.screen, app_module.PhaseDetailScreen)

    _detail_run(phased, (120, 40), scenario)
