"""Tests for dashboard.app: the Textual dashboard and its --once frame."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("textual")

from rich.style import Style  # noqa: E402
from textual.widgets._markdown import MarkdownHeader  # noqa: E402

import helpers as h  # noqa: E402
from conftest import REPO_ROOT, git, stamped_store  # noqa: E402

sys.path.insert(0, str(REPO_ROOT))
from dashboard import artifact_store  # noqa: E402
from dashboard import model as model_module  # noqa: E402
from dashboard import app as app_module  # noqa: E402
from dashboard import commit as commit_module  # noqa: E402
from dashboard import task_detail as detail_module  # noqa: E402
from dashboard import tasks as tasks_module
from test_dashboard_model import (  # noqa: E402
    ROW_SPEC,
    _accept,
    _assessment,
    _check,
    _decision,
    _design,
    _release,
    _report,
    _spec,
    _task,
)  # noqa: E402

SCRIPT = REPO_ROOT / "dashboard" / "__main__.py"
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


def _seed_alpha(cli, defs):
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
    real = model_module._run

    def run(target, *args):
        key = (args, _store_digest(target.store))
        if key not in _CLI_CACHE:
            _CLI_CACHE[key] = real(target, *args)
        return copy.deepcopy(_CLI_CACHE[key])

    monkeypatch.setattr(model_module, "_run", run)


@pytest.fixture()
def seeded(store):
    stamped_store(store, "seeded", lambda root, cli, defs: _seed_alpha(cli, defs))
    return store


def _text(app, selector):
    return str(app.query_one(selector).render())


def _run(store, width, scenario, interval=60.0, height=40):
    async def go():
        app = app_module.DashboardApp(artifact_store.resolve(store), interval=interval)
        async with app.run_test(size=(width, height)) as pilot:
            await _until(pilot, lambda: bool(app.query("#goal")) and bool(_text(app, "#goal")))
            await app.workers.wait_for_complete()
            await scenario(app, pilot)

    asyncio.run(go())


async def _until(pilot, condition, timeout=20.0):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        await pilot.pause(0.02)


@pytest.mark.parametrize("width", WIDTHS)
def test_shows_goal_stepper_and_progress(seeded, width):
    async def scenario(app, pilot):
        assert "ship the alpha dashboard" in _text(app, "#goal")
        stepper = _text(app, "#stepper")
        assert "1 done" in stepper and "● Phase two 0/3" in stepper and "○ Phase three" in stepper
        assert "✓" not in stepper and "Phase one" not in stepper
        assert stepper.index("done") < stepper.index("two") < stepper.index("three")
        assert _text(app, "#progress-label") == "phase 2/3 · 1 of 4 tasks"
        bar = app.query_one("#progress")
        assert (bar.progress, bar.total) == (1, 4)

    _run(seeded, width, scenario)


LONG_PHASES = (
    ("invoice", "Invoice schema", ("in_progress", "done")),
    ("csv", "CSV export", ("in_progress", "done")),
    ("pdf", "PDF export", ("in_progress",)),
    ("admin", "Admin console button", ()),
    ("rollout", "Rollout", ()),
    ("audit", "Audit trail for every export with retention rules and a long tail", ()),
)


def _seed_long_phases(cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="billing",
        extra_payload={"goal": "ship billing exports", "kind": "deliver"},
    )
    for ordinal, (subject, title, states) in enumerate(LONG_PHASES, 1):
        record = h.create_generic_record(
            cli, defs, "project:phase", subject=subject,
            extra_payload={"title": title, "ordinal": ordinal, "effort": "billing"},
        )
        h.transition(cli, "project:phase", record, *states)
    for index in range(4):
        _work_item(cli, defs, "billing", f"pdf-{index}", "pdf")


def _stepper_lines(app):
    stepper = app.query_one("#stepper")
    lines = [stepper.render_line(y).text.rstrip() for y in range(stepper.size.height)]
    return [line.lstrip() for line in lines if line.strip()]


async def _pane_settled(app, pilot):
    pane = app.query_one(app_module.EffortPane)
    stepper = app.query_one("#stepper")
    await _until(pilot, lambda: pane.inner == pane.scrollable_content_region.width == stepper.size.width, timeout=5.0)
    await pilot.pause()


def test_stepper_wraps_by_pane_width_and_keeps_glyph_with_label(store):
    stamped_store(store, "long-phases", lambda root, cli, defs: _seed_long_phases(cli, defs))

    async def scenario(app, pilot):
        pane = app.query_one(app_module.EffortPane)
        await _pane_settled(app, pilot)
        lines = _stepper_lines(app)
        joined = " ".join(lines)
        assert "2 done" in joined and "● PDF export 0/4" in joined and "○ Admin console button" in joined
        assert "Invoice schema" not in joined and "Rollout" not in joined and "Audit" not in joined
        assert "✓" not in joined
        assert all(len(line) <= pane.scrollable_content_region.width for line in lines), lines
        await pilot.click("#stepper")
        await pilot.pause()
        expanded = " ".join(_stepper_lines(app))
        assert "Invoice schema" in expanded and "CSV export" in expanded
        assert "● PDF export 0/4" in expanded and "○ Admin console button" in expanded
        assert "2 done" not in expanded and "Rollout" not in expanded and "Audit" not in expanded
        assert "✓" not in expanded
        await pilot.resize_terminal(22, 30)
        await _pane_settled(app, pilot)
        width = pane.scrollable_content_region.width
        clipped = _stepper_lines(app)
        assert width < len("○ Admin console button")
        assert any(line.startswith("○") and "…" in line for line in clipped), clipped
        assert not any(line.endswith(("●", "○", "✓")) for line in clipped), clipped
        assert all(len(line) <= width for line in clipped), clipped

    _run(store, 60, scenario, height=20)


def test_stepper_fits_the_pane_after_its_scrollbar_appears(store):
    stamped_store(store, "long-phases", lambda root, cli, defs: _seed_long_phases(cli, defs))

    async def scenario(app, pilot):
        pane = app.query_one(app_module.EffortPane)
        assert not pane.show_vertical_scrollbar
        before = pane.scrollable_content_region.width
        app.query_one("#goal").styles.height = 80
        await _until(pilot, lambda: pane.show_vertical_scrollbar)
        await _pane_settled(app, pilot)
        width = pane.scrollable_content_region.width
        assert width < before
        view, _, _, colors = pane.last
        expected = app_module.stepper_text(view, colors, width).plain.split("\n")
        assert _stepper_lines(app) == expected

    _run(store, 60, scenario, height=40)


@pytest.mark.parametrize("width", WIDTHS)
def test_task_table_lists_rows_by_status_with_task_id_keys(seeded, width):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        rows = [table.get_row_at(i) for i in range(table.row_count) if not _is_section(list(table.rows)[i].value)]
        statuses = [str(row[0]).split()[1] for row in rows]
        assert statuses == ["running", "ready", "waiting"]
        assert "title of a-running" in str(rows[0][1])
        assert "w" in str(rows[0][2])
        assert all(key.value for key in table.rows)

    _run(seeded, width, scenario)


def _labels(app):
    return [str(col.label) for col in app.query_one("#tasks").columns.values()]


@pytest.mark.parametrize(("width", "expected"), ((60, ["status", "task", "wave"]), (120, ["status", "task", "wave", "assignee"])))
def test_grouped_task_table_has_no_phase_column(seeded, width, expected):
    async def scenario(app, pilot):
        assert _labels(app) == expected

    _run(seeded, width, scenario)


def test_wide_width_shows_the_assignee_without_a_phase_column(seeded):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        assert "agent-7" in str(table.get_row_at(1)[3])

    _run(seeded, 120, scenario)


def test_resize_rebuilds_task_columns_without_a_phase_column(seeded):
    async def scenario(app, pilot):
        wide = ["status", "task", "wave", "assignee"]
        assert _labels(app) == wide
        await pilot.resize_terminal(60, 40)
        await _until(pilot, lambda: _labels(app) == ["status", "task", "wave"])
        await pilot.resize_terminal(120, 40)
        await _until(pilot, lambda: _labels(app) == wide)

    _run(seeded, 120, scenario)


def test_once_keeps_the_phase_column_when_wide(seeded):
    result = subprocess.run(
        ["uv", "run", "--script", str(SCRIPT), "--once"], capture_output=True, text=True, cwd=str(seeded),
        env={**os.environ, "COLUMNS": "120"},
    )
    assert result.returncode == 0, result.stderr
    header = next(line for line in result.stdout.splitlines() if line.lstrip().startswith("status"))
    assert header.split() == ["status", "task", "wave", "phase", "assignee"]


def _seed_waits_and_running(root, cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="alpha", extra_payload={"goal": "g", "kind": "deliver"},
    )
    _phase(cli, defs, "alpha", "two", 1, "in_progress")
    running = _work_item(cli, defs, "alpha", "w-running", "two")
    h.transition(cli, "project:work-item", running, "in_progress")
    other = _work_item(cli, defs, "alpha", "w-other", "two")
    h.transition(cli, "project:work-item", other, "in_progress")
    done = _work_item(cli, defs, "alpha", "w-done", "two")
    h.transition(cli, "project:work-item", done, "in_progress", "done")
    _work_item(cli, defs, "alpha", "w-waiting", "two", f"depends_on:{running['id']}", f"depends_on:{other['id']}", f"depends_on:{done['id']}")
    _work_item(cli, defs, "alpha", "w-ready", "two", f"depends_on:{done['id']}")
    h.run_cli_48h_ago(
        root, "create", "--type", "project:assignment", "--subject", "w-running",
        "--payload", json.dumps({"work_item": running["id"], "executor": "sub-w", "effort": "alpha"}),
        "--body", h.generic_body(defs["project:assignment"]),
    )
    return running


@pytest.fixture()
def waits(store):
    running = stamped_store(store, "waits-running", _seed_waits_and_running)
    return store, running


def _row_by_title(table, title):
    return next(table.get_row(k.value) for k in table.rows if title in str(table.get_row(k.value)[1]))


@pytest.mark.parametrize("width", WIDTHS)
def test_waiting_row_title_ends_with_muted_waits_on_its_unfinished_dependencies(waits, width):
    store, _ = waits

    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        cell = next(
            table.get_row(key.value)[1] for key in table.rows if "waits on" in str(table.get_row(key.value)[1])
        )
        tail = " · subagent  waits on w-other, w-running"
        plain = str(cell).strip()
        assert plain.endswith(tail)
        if width == 120:
            assert plain == "title of w-waiting" + tail
        else:
            assert "…" in plain[: plain.index(tail)]
        start = str(cell).index("waits on")
        muted = app_module.palette_from(app.get_css_variables())["muted"]
        assert any(span.start <= start and str(span.style) == muted for span in cell.spans)
        assert "waits on" not in str(_row_by_title(table, "title of w-ready")[1])

    _run(store, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_running_row_status_shows_its_running_time(waits, width):
    store, _ = waits

    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        row = _row_by_title(table, "title of w-running")
        assert str(row[0]) == "▶ running 48h"
        assert str(row[1]).strip().endswith(" · subagent")
        assert str(_row_by_title(table, "title of w-other")[0]) == "▶ running"

    _run(store, width, scenario)


def test_detail_chips_show_running_time_from_the_running_since_stamp():
    since = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    detail = app_module.model.TaskDetail(
        "i", "s", "e", "t", "running", "", None, "", "", [], [], [], [], [], running_since=since)
    chips = detail_module.detail_chips(detail, app_module.ANSI_PALETTE, 100, since + timedelta(minutes=14))
    assert chips.plain == "▶ running 14m · executor subagent"


@pytest.mark.parametrize("width", WIDTHS)
def test_needs_you_panel_and_activity_feed_show_their_items(seeded, width):
    async def scenario(app, pilot):
        assert app.query_one("#needs-you").display
        assert "which backend" in _needs_text(app)
        activity = _text(app, "#activity")
        lines = activity.splitlines()
        assert len(lines) == 3
        assert any(line.endswith("a-check check passed") for line in lines)
        assert any(line.endswith("a-done reported pass") for line in lines)
        assert any(line.endswith("a-running assigned to sub-1") for line in lines)
        assert "(" not in activity
        assert "now" in activity or "ago" in activity

    _run(seeded, width, scenario)


def _seed_failed_check(store):
    def seed(root, cli, defs):
        _seed_alpha(cli, defs)
        h.create_generic_record(
            cli, defs, "project:check-run", subject="a-broken",
            extra_payload={"method": "check", "signed_by": "", "result": "fail", "effort": "alpha"},
        )

    stamped_store(store, "failed-check", seed)
    return store


@pytest.mark.parametrize("width", WIDTHS)
def test_failed_activity_line_uses_the_error_colour_and_a_cross(store, width):
    _seed_failed_check(store)

    async def scenario(app, pilot):
        error = app_module.palette_from(app.get_css_variables())["error"]
        rendered = app.query_one("#activity").render()
        lines = str(rendered).splitlines()
        failed = next(line for line in lines if line.endswith("a-broken check failed"))
        assert " ✗ " in failed
        assert not any("✗" in line for line in lines if line != failed)
        start = str(rendered).index(failed)
        colours = {
            Style.parse(str(span.style)).color.get_truecolor()
            for span in rendered.spans if span.start < start + len(failed) and span.end > start + 8
        }
        assert colours == {Style.parse(error).color.get_truecolor()}

    _run(store, width, scenario)


def test_once_marks_failed_activity_with_a_cross(store):
    _seed_failed_check(store)
    result = subprocess.run(
        ["uv", "run", "--script", str(SCRIPT), "--once"], capture_output=True, text=True, cwd=str(store),
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert any("✗" in line and line.endswith("a-broken check failed") for line in lines)
    assert not any("✗" in line and "a-check check passed" in line for line in lines)


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

    _run(store, 60, scenario, height=20)


def test_footer_has_no_palette_and_every_binding_fits_at_60_columns(seeded):
    async def scenario(app, pilot):
        await pilot.pause()
        keys = list(app.query("FooterKey"))
        assert sorted(str(key.description) for key in keys) == ["copy", "filter", "needs", "phase", "quit", "status", "switch"]
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
        tasks = app.query_one("#tasks")
        shown = title + " · subagent"
        await _until(pilot, lambda: tasks.row_count and str(tasks.get_row_at(0)[1]) == shown)
        assert str(tasks.get_row_at(0)[1]) == shown

    _run(store, 120, scenario)


def test_needs_you_panel_is_hidden_when_nothing_needs_you(store, cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="calm", extra_payload={"goal": "stay calm", "kind": "deliver"},
    )

    async def scenario(app, pilot):
        assert not app.query_one("#needs-you").display

    _run(store, 60, scenario, height=20)


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


def _task_cells(app):
    table = app.query_one("#tasks")
    return [
        str(table.get_row_at(i)[1])
        for i in range(table.row_count)
        if not _is_section(list(table.rows)[i].value)
    ]


def _titles(app):
    titles = []
    for text in _task_cells(app):
        text = text.split("  waits on")[0]
        titles.append(text.split(" · ")[0].strip())
    return titles


def _same_tasks(app, expected):
    cells = _task_cells(app)
    if len(cells) != len(expected):
        return False
    for cell, title in zip(cells, expected):
        head = cell.split("  waits on")[0].split(" · ")[0].strip()
        if head == title:
            continue
        if not (head.endswith("…") and (head == "…" or title.startswith(head[:-1]))):
            return False
        if head == "…" and "  waits on" not in cell:
            return False
    return True


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
        assert _same_tasks(app, ["title of a-waiting"])

    _run(seeded, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_escape_in_the_filter_input_clears_the_filter(seeded, width):
    async def scenario(app, pilot):
        await pilot.press("slash")
        await pilot.press(*"ready")
        await pilot.press("escape")
        await pilot.pause()
        assert _same_tasks(app, _all_titles())
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
        await _until(pilot, lambda: len(app.screen_stack) == 1)
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
        assert _same_tasks(app, _all_titles())
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
def test_status_tabs_show_a_count_on_every_tab_and_default_to_active(seeded, width):
    async def scenario(app, pilot):
        labels = _tab_labels(app)
        assert {k: v.split() for k, v in labels.items()} == {
            "active": ["Active", "(3)"], "running": ["Running", "(1)"], "ready": ["Ready", "(1)"],
            "waiting": ["Waiting", "(1)"], "done": ["Done", "(1)"], "all": ["All", "(4)"],
        }
        assert all(tab.region.right <= width for tab in app.query(app_module.StatusTab))
        assert _selected(app) == ["active"]
        assert _same_tasks(app, _all_titles())
        assert not list(app.query("#tiles"))

    _run(seeded, width, scenario)


def _tab_rows(app):
    return sorted({tab.region.y for tab in app.query(app_module.StatusTab)})


def test_tab_row_holds_all_six_tabs_on_one_row_at_120_columns(seeded):
    async def scenario(app, pilot):
        assert len(list(app.query(app_module.StatusTab))) == 6
        assert len(_tab_rows(app)) == 1

    _run(seeded, 120, scenario)


def test_tab_row_wraps_inside_the_pane_at_60_columns(seeded):
    async def scenario(app, pilot):
        tabs = list(app.query(app_module.StatusTab))
        assert all(tab.region.right <= 60 for tab in tabs)
        order = sorted(tabs, key=lambda tab: (tab.region.y, tab.region.x))
        assert [tab.tab_name for tab in order] == [name for name, _, _ in tasks_module.STATUS_TABS]

    _run(seeded, 60, scenario)


def test_tab_row_unwraps_when_the_pane_grows(seeded):
    async def scenario(app, pilot):
        await pilot.resize_terminal(120, 40)
        await _until(pilot, lambda: len(_tab_rows(app)) == 1)

    _run(seeded, 60, scenario)


def _styles_covering(content, start, end):
    return [span.style for span in content.spans if span.start < end and span.end > start]


@pytest.mark.parametrize("width", WIDTHS)
def test_tab_labels_are_the_word_and_a_dim_parenthetical_tally(seeded, width):
    async def scenario(app, pilot):
        labels = _tab_labels(app)
        assert labels == {
            "active": "Active (3)", "running": "Running (1)", "ready": "Ready (1)",
            "waiting": "Waiting (1)", "done": "Done (1)", "all": "All (4)",
        }
        assert all(not label[0].isdigit() for label in labels.values())
        assert all(tab.region.width == len(labels[tab.tab_name]) for tab in app.query(app_module.StatusTab))
        selected = app.query_one("#status-active").render()
        word_end = selected.plain.index(" ")
        tally_at = selected.plain.index("(")
        word = _styles_covering(selected, 0, word_end)
        tally = _styles_covering(selected, tally_at, tally_at + 1)
        assert any(style.bold and style.reverse for style in word)
        assert any(style.dim for style in tally)
        assert not any(style.reverse for style in tally)
        other = app.query_one("#status-running").render()
        other_tally = other.plain.index("(")
        assert any(style.dim for style in _styles_covering(other, other_tally, other_tally + 1))
        assert not any(style.reverse for style in _styles_covering(other, 0, other.plain.index(" ")))
        assert "text-style: bold reverse" not in app_module.DashboardApp.CSS

    _run(seeded, width, scenario)


def test_tab_row_once_tally_shows_number_keys(seeded):
    result = subprocess.run(
        ["uv", "run", "--script", str(SCRIPT), "--once"], capture_output=True, text=True, cwd=str(seeded),
        env={**os.environ, "COLUMNS": "120"},
    )
    assert result.returncode == 0, result.stderr
    assert "Active (3)   Running (1)   Ready (1)   Waiting (1)   Done (1)   All (4)" in result.stdout
    assert "1 done" in result.stdout and "● Phase two 0/3" in result.stdout and "○ Phase three" in result.stdout
    assert "✓ Phase one" not in result.stdout


def test_status_tabs_are_six_on_keys_one_to_six_without_a_needs_you_tab():
    assert [(name, key) for name, _, key in tasks_module.STATUS_TABS] == [
        ("active", "1"), ("running", "2"), ("ready", "3"), ("waiting", "4"), ("done", "5"), ("all", "6"),
    ]
    keys = {binding.key: binding for binding in app_module.DashboardApp.BINDINGS
            if isinstance(binding, app_module.Binding) and binding.action.startswith("status_tab(")}
    assert sorted(keys) == ["1", "2", "3", "4", "5", "6"]
    assert keys["1"].key_display == "1-6"
    assert not any("needs" in binding.action for binding in keys.values())


@pytest.mark.parametrize("width", WIDTHS)
def test_needs_you_panel_title_counts_every_item_including_effort_level_questions(seeded, cli, defs, width):
    async def scenario(app, pilot):
        panel = app.query_one("#needs-you")
        assert panel.border_title == "Needs you 1"
        assert "which backend" in _needs_text(app)
        _needs_task(cli, defs)
        await _until(pilot, lambda: panel.border_title == "Needs you 2")
        assert not list(app.query("#status-needs"))

    _run(seeded, width, scenario, interval=0.3)


@pytest.mark.parametrize("width", WIDTHS)
def test_number_keys_filter_the_table_by_status_tab(seeded, width):
    async def scenario(app, pilot):
        expected = {
            "2": ("running", ["title of a-running"]), "3": ("ready", ["title of a-ready"]),
            "4": ("waiting", ["title of a-waiting"]), "5": ("done", ["title of a-done"]),
            "6": ("all", ["title of a-done"] + _all_titles()), "1": ("active", _all_titles()),
        }
        for key, (name, titles) in expected.items():
            await pilot.press(key)
            if key == "5":
                await pilot.press("enter")
            await pilot.pause()
            assert _same_tasks(app, titles)
            assert _selected(app) == [name]

    _run(seeded, width, scenario)


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


def _seed_unwaited(cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="alpha", extra_payload={"goal": "ship it", "kind": "deliver"},
    )
    _phase(cli, defs, "alpha", "two", 1, "in_progress")
    running = _work_item(cli, defs, "alpha", "u-running", "two")
    h.transition(cli, "project:work-item", running, "in_progress")
    _work_item(cli, defs, "alpha", "u-ready", "two")


@pytest.fixture()
def unwaited(store):
    stamped_store(store, "unwaited", lambda root, cli, defs: _seed_unwaited(cli, defs))
    return store


@pytest.mark.parametrize("width", WIDTHS)
def test_table_regains_focus_when_a_tab_shows_it_after_an_empty_tab(unwaited, width):
    async def scenario(app, pilot):
        table = app.query_one("#tasks")
        await pilot.press("4")
        await pilot.pause()
        assert _titles(app) == []
        assert not table.display
        await pilot.press("1")
        await pilot.pause()
        assert app.focused is table
        await pilot.press("down")
        await pilot.pause()
        assert table.cursor_row == 1
        key = _cursor_key(table).value
        assert not _is_section(key)
        await pilot.press("enter")
        await _until(pilot, lambda: isinstance(app.screen, detail_module.TaskDetailScreen))
        assert app.screen.task_id == key

    _run(unwaited, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_status_tab_combines_with_the_slash_filter(seeded, width):
    async def scenario(app, pilot):
        await pilot.press("slash")
        await pilot.press(*"a-")
        await pilot.press("enter")
        await pilot.press("5")
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
        await pilot.press("5")
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


def _build_detailed(store, cli, defs):
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
    return task, tests


@pytest.fixture()
def detailed(store):
    task, tests = stamped_store(store, "detailed", _build_detailed)
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
            await app.workers.wait_for_complete()
            await pilot.pause()
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
    deadline = time.monotonic() + 20.0
    while not isinstance(app.screen, detail_module.TaskDetailScreen):
        assert time.monotonic() < deadline, "click never opened the task"
        await pilot.click("#tasks", offset=_row_offset(table, key))
        await pilot.pause(0.05)


async def _settled(app, pilot):
    await app.workers.wait_for_complete()
    widgets = -1
    while widgets != len(app.screen.query("*")):
        widgets = len(app.screen.query("*"))
        await pilot.pause(0.02)


async def _shown(app, pilot):
    await _until(pilot, lambda: isinstance(app.screen, detail_module.TaskDetailScreen) and app.screen.loaded)
    await _settled(app, pilot)
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
        assert _link_lines(screen) == ["Depends on: ✓ det-dep", "Blocks: ◌ det-blocked", "Phase: det-phase"]
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
    assert detail_module.split_fields("```\na: 1\nb: two\n  more\n```") == ([("a", "1"), ("b", "two more")], "")
    assert detail_module.split_fields("```\na: 1\n```\n\nafter") == ([("a", "1")], "after")
    assert detail_module.split_fields("plain **text**") is None
    assert detail_module.split_fields("```python\nprint(1)\n```") is None


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_task_detail_chips_show_the_running_time(waits, size):
    store, running = waits

    async def scenario(app, pilot):
        await _open_by_enter(app, pilot, running["id"])
        screen = await _shown(app, pilot)
        assert str(screen.query_one("#detail-chips").render()).startswith("▶ running 48h")

    _detail_run(store, size, scenario)


def test_chips_never_split_a_label_from_its_value_when_narrow():
    detail = app_module.model.TaskDetail(
        "i", "s", "e", "t", "done", "task-details", 1, "sub-task-detail-model", "", [], [], [], [], [])
    colors = app_module.ANSI_PALETTE
    lines = detail_module.detail_chips(detail, colors, 40).plain.splitlines()
    assert lines == [
        "✓ done · phase task-details · w1",
        "assignee sub-task-detail-model",
        "executor subagent",
    ]
    assert detail_module.detail_chips(detail, colors, 100).plain == (
        "✓ done · phase task-details · w1 · assignee sub-task-detail-model · executor subagent"
    )


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
        blocked = next(
            k.value for k in table.rows
            if "det-blocked" in str(table.get_row(k.value)[1]) or "waits on det-task" in str(table.get_row(k.value)[1])
        )
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


def test_detail_footer_shows_back_links_copy_commit_refresh_and_quit_within_60_columns(detailed):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await _open_by_enter(app, pilot, task["id"])
        await _shown(app, pilot)
        keys = list(app.screen.query("FooterKey"))
        assert sorted(str(key.description) for key in keys) == ["back", "commit", "copy", "links", "quit", "refresh"]
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


def _link_lines(screen):
    links = screen.query_one("#detail-links")
    return [str(links.get_option_at_index(index).prompt).strip() for index in range(links.option_count)]


async def _focus_links(app, pilot, screen):
    await pilot.press("l")
    await _until(pilot, lambda: app.focused is screen.query_one("#detail-links"))


async def _open_link(app, pilot, screen, *moves):
    await _focus_links(app, pilot, screen)
    await pilot.press(*moves, "enter")
    await _until(pilot, lambda: app.screen is not screen)
    if isinstance(app.screen, detail_module.TaskDetailScreen):
        return await _shown(app, pilot)
    return await _phase_shown(app, pilot)


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_enter_on_a_dependency_link_opens_that_task(detailed, size):
    store, task, _ = detailed

    async def scenario(app, pilot):
        screen = await _open_task(app, pilot, task)
        dep = screen.detail.depends_on[0]
        opened = await _open_link(app, pilot, screen)
        assert isinstance(opened, detail_module.TaskDetailScreen)
        assert opened.task_id == dep.id and opened.detail.subject == "det-dep"
        assert len(app.screen_stack) == 3

    _detail_run(store, size, scenario)


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_enter_on_a_blocked_task_link_opens_it(detailed, size):
    store, task, _ = detailed

    async def scenario(app, pilot):
        screen = await _open_task(app, pilot, task)
        opened = await _open_link(app, pilot, screen, "down")
        assert isinstance(opened, detail_module.TaskDetailScreen)
        assert opened.detail.subject == "det-blocked"

    _detail_run(store, size, scenario)


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_enter_on_the_phase_link_opens_the_phase_detail(detailed, size):
    store, task, _ = detailed

    async def scenario(app, pilot):
        screen = await _open_task(app, pilot, task)
        opened = await _open_link(app, pilot, screen, "j", "j")
        assert isinstance(opened, app_module.PhaseDetailScreen)
        assert opened.phase_subject == "det-phase" and opened.effort == "alpha"

    _detail_run(store, size, scenario)


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_task_description_headings_have_no_blank_line_above(detailed, size):
    store, task, _ = detailed

    async def scenario(app, pilot):
        screen = await _open_task(app, pilot, task)
        await _assert_headings_follow_text(app, pilot, screen.query_one("#description Markdown"), HEADED_BODY)

    _detail_run(store, size, scenario)


def test_link_list_skips_empty_groups_and_keeps_scroll_focus_on_open(detailed):
    store, task, _ = detailed

    async def scenario(app, pilot):
        screen = await _open_task(app, pilot, task)
        assert app.focused is screen.query_one("#detail")
        dep = await _open_link(app, pilot, screen)
        assert _link_lines(dep) == ["Blocks: ▶ det-task", "Phase: det-phase"]
        assert app.focused is dep.query_one("#detail")

    _detail_run(store, (120, 40), scenario)


def test_escape_walks_back_through_linked_screens_one_at_a_time(detailed):
    store, task, _ = detailed

    async def scenario(app, pilot):
        dashboard = app.screen
        first = await _open_task(app, pilot, task)
        dep = await _open_link(app, pilot, first)
        phase = await _open_link(app, pilot, dep, "down")
        assert phase.phase_subject == "det-phase"
        assert len(app.screen_stack) == 4
        await pilot.press("escape")
        await _until(pilot, lambda: app.screen is dep)
        await pilot.pause(0.1)
        assert app.focused is dep.query_one("#detail-links")
        await pilot.press("escape")
        await _until(pilot, lambda: app.screen is first)
        await pilot.pause(0.1)
        assert app.focused is first.query_one("#detail-links")
        assert len(app.screen_stack) == 2
        await pilot.press("escape")
        await _until(pilot, lambda: app.screen is dashboard)
        await _until(pilot, lambda: app.focused is app.query_one("#tasks"))
        assert _cursor_key(app.query_one("#tasks")).value == task["id"]

    _detail_run(store, (120, 40), scenario)


def _build_committed(store, cli, defs):
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
    return tasks, sha


@pytest.fixture()
def committed(store):
    tasks, sha = stamped_store(store, "committed", _build_committed)
    return store, tasks, sha


def _notices(app):
    return [note.message for note in app._notifications]


async def _open_task(app, pilot, task):
    await _open_by_enter(app, pilot, task["id"])
    return await _shown(app, pilot)


async def _commit_shown(app, pilot):
    await _until(pilot, lambda: isinstance(app.screen, commit_module.CommitScreen) and app.screen.loaded)
    await _settled(app, pilot)
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
        app.push_screen(commit_module.CommitScreen(commit_module.load_commit(store, wide, commit_module.stat_width(app)), store, wide))
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
        app.push_screen(commit_module.CommitScreen(commit_module.load_commit(store, rev, 76), store, rev))
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
        await _until(pilot, lambda: app.focused is app.query_one("#tasks"))

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
        await _until(pilot, lambda: isinstance(app.screen, detail_module.TaskDetailScreen))
        assert app.screen.task_id == key

    _run(seeded, 120, scenario)


def test_table_keeps_focus_after_switching_effort_tabs(seeded, cli, defs):
    _second_effort(cli, defs)

    async def scenario(app, pilot):
        await _until(pilot, lambda: len(app.panes) == 2 and len(app.query("TabPane")) == 2)
        await _until(pilot, lambda: app.focused is app.active_pane().query_one("#tasks"))
        tabs = app.query_one("#efforts")

        async def switched():
            if tabs.active != "effort-beta":
                await pilot.press("tab")
            return tabs.active == "effort-beta"

        deadline = time.monotonic() + 20.0
        while not await switched():
            assert time.monotonic() < deadline, "tab never switched to beta"
            await pilot.pause(0.05)
        await _until(pilot, lambda: app.focused is app.active_pane().query_one("#tasks"))
        await pilot.press("shift+tab")
        await _until(pilot, lambda: app.query_one("#efforts").active == "effort-alpha")
        await _until(pilot, lambda: app.focused is app.active_pane().query_one("#tasks"))
        await pilot.press("down")
        await _until(pilot, lambda: app.query_one("#efforts").active_pane.query_one("#tasks").cursor_row == 1)

    _run(seeded, 120, scenario)


def test_table_keeps_focus_after_escape_from_detail(detailed):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await pilot.press("down")
        await pilot.press("enter")
        await _shown(app, pilot)
        await pilot.press("escape")
        await _until(pilot, lambda: app.focused is app.query_one("#tasks"))
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
        await _until(pilot, lambda: pane.scroll_y > 0)
        assert pane.scroll_y > 0
        await pilot.press("end")
        await _until(pilot, lambda: pane.scroll_y == pane.max_scroll_y)
        assert pane.scroll_y == pane.max_scroll_y
        assert pane.query_one("#activity").region.bottom <= pane.region.bottom
        await pilot.press("pageup")
        await _until(pilot, lambda: pane.scroll_y < pane.max_scroll_y)
        assert pane.scroll_y < pane.max_scroll_y
        await pilot.press("home")
        await _until(pilot, lambda: pane.scroll_y == 0)
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
        await _until(pilot, lambda: scroll.scroll_y > 0)
        assert scroll.scroll_y > 0
        await pilot.press("home")
        await _until(pilot, lambda: scroll.scroll_y == 0)
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
        await _until(pilot, lambda: scroll.scroll_y > 0)
        assert scroll.scroll_y > 0
        await pilot.press("end")
        await _until(pilot, lambda: scroll.scroll_y == scroll.max_scroll_y)
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
    for needle in ("alpha", "ship the alpha dashboard", "1 done", "Running", "title of a-running", "which backend", "Needs you 1"):
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
        await pilot.press("5")
        await pilot.press("enter")
        _work_item(cli, defs, "alpha", "a-fresh", "two")
        await _until(pilot, lambda: _tab_labels(app)["all"] == "All (5)")
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
        await pilot.press("6")
        await pilot.pause()
        keys = _keys(app)
        assert keys[:3] == ["fold", "phase:d3", "phase:d4"]
        assert "2 earlier phases done" in _row_text(app, "fold")
        assert not any(key.startswith("phase:d1") or key.startswith("phase:d2") for key in keys)
        assert all("-task" not in key for key in keys[:3])
        assert str(app.query_one("#tasks").get_row("phase:d4")[0]) == "▸"
        assert "✓" not in _row_text(app, "phase:d3") and "✓" not in _row_text(app, "phase:d4")
        assert "●" in str(app.query_one("#tasks").get_row("phase:cur")[0])
        assert "○" in str(app.query_one("#tasks").get_row("phase:later")[0])

    _run(phased, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_enter_on_the_fold_row_expands_and_collapses_the_older_phases(phased, width):
    async def scenario(app, pilot):
        await pilot.press("6")
        await pilot.pause()
        app.query_one("#tasks").move_cursor(row=0)
        await pilot.press("enter")
        await pilot.pause()
        assert _keys(app)[:5] == ["fold", "phase:d1", "phase:d2", "phase:d3", "phase:d4"]
        assert not isinstance(app.screen, detail_module.TaskDetailScreen)
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
        await pilot.press("6")
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
        assert not isinstance(app.screen, detail_module.TaskDetailScreen)

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
        assert not isinstance(app.screen, detail_module.TaskDetailScreen)
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
        await _until(pilot, lambda: _tab_labels(app)["all"] == "All (9)")
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
        tasks = " ".join(_phase_task_titles(screen))
        assert "title of cur-run" in tasks and "title of cur-ready" in tasks and "later-task" not in tasks
        await pilot.press("escape")
        await pilot.pause(0.3)
        assert not isinstance(app.screen, app_module.PhaseDetailScreen)
        assert app.focused is app.query_one("#tasks")

    _detail_run(phased, size, scenario)


def _phase_task_titles(screen):
    tasks = screen.query_one("#phase-tasks")
    return [str(tasks.get_option_at_index(index).prompt) for index in range(tasks.option_count)]


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_phase_task_list_takes_focus_and_arrows_move_through_the_tasks(phased, size):
    async def scenario(app, pilot):
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        tasks = screen.query_one("#phase-tasks")
        assert app.focused is tasks
        assert tasks.highlighted == 0
        await pilot.press("down")
        assert tasks.highlighted == 1
        await pilot.press("up")
        assert tasks.highlighted == 0

    _detail_run(phased, size, scenario)


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_phase_task_enter_opens_the_task_detail_and_escape_returns_to_the_phase_detail(phased, size):
    async def scenario(app, pilot):
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        await pilot.press("down", "enter")
        detail = await _shown(app, pilot)
        assert detail.task_id == screen.detail.tasks[1].id
        assert detail.detail.title in _phase_task_titles(screen)[1]
        await pilot.press("escape")
        await _until(pilot, lambda: app.screen is screen)
        await pilot.pause(0.3)
        assert app.screen is screen
        assert app.focused is screen.query_one("#phase-tasks")
        assert screen.query_one("#phase-tasks").highlighted == 1

    _detail_run(phased, size, scenario)


def test_phase_task_list_leaves_page_keys_scrolling_the_phase_detail(phased):
    async def scenario(app, pilot):
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        scroll = screen.query_one("#phase")
        assert scroll.max_scroll_y > 0
        await pilot.press("home")
        await _until(pilot, lambda: scroll.scroll_y == 0)
        await pilot.press("pagedown")
        await _until(pilot, lambda: scroll.scroll_y > 0)
        await pilot.press("home")
        await _until(pilot, lambda: scroll.scroll_y == 0)
        assert app.focused is screen.query_one("#phase-tasks")

    _detail_run(phased, (60, 20), scenario)


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
        await pilot.press("6")
        await pilot.pause()
        app.query_one("#tasks").move_cursor(row=0)
        await pilot.press("p")
        await pilot.pause(0.3)
        assert not isinstance(app.screen, app_module.PhaseDetailScreen)

    _detail_run(phased, (120, 40), scenario)


HEADED_BODY = "## Problem\n\nText one.\n\n- a point\n\n## Approach\n\nText two.\n\n### Detail\n\nText three."


def _headings_after_a_blank_line(markdown):
    blocks = list(markdown.children)
    headings = [block for block in blocks if isinstance(block, MarkdownHeader)]
    assert headings and all(heading.region.height for heading in headings)
    filled = {y for block in blocks for y in range(block.region.y, block.region.bottom)}
    return [str(heading.region.y) for heading in headings
            if heading.region.y > markdown.region.y and heading.region.y - 1 not in filled]


async def _assert_headings_follow_text(app, pilot, markdown, source=None):
    if source is not None:
        await markdown.update(source)
        await _settled(app, pilot)
    assert markdown.children[0].region.y == markdown.region.y
    assert _headings_after_a_blank_line(markdown) == []


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_phase_body_headings_have_no_blank_line_above(phased, size):
    async def scenario(app, pilot):
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        await _assert_headings_follow_text(app, pilot, screen.query_one("#phase-body Markdown"))
        await _assert_headings_follow_text(app, pilot, screen.query_one("#phase-body Markdown"), HEADED_BODY)

    _detail_run(phased, size, scenario)


def _seed_finished(cli, defs):
    for effort in ("alpha", "beta"):
        h.create_generic_record(
            cli, defs, "project:active-goal", subject=effort, extra_payload={"goal": f"ship {effort}", "kind": "deliver"},
        )
    _phase(cli, defs, "alpha", "a-one", 1, "in_progress", "done")
    for subject in ("a-first", "a-second"):
        done = _work_item(cli, defs, "alpha", subject, "a-one")
        h.transition(cli, "project:work-item", done, "in_progress", "done")
    withdrawn = _work_item(cli, defs, "alpha", "a-dropped", "a-one")
    h.transition(cli, "project:work-item", withdrawn, "withdrawn")
    phase = h.create_generic_record(
        cli, defs, "project:phase", subject="b-one", extra_payload={"title": "Phase b-one", "ordinal": 1, "effort": "beta"},
    )
    phase = h.transition(cli, "project:phase", phase, "in_progress")
    task = _work_item(cli, defs, "beta", "b-task", "b-one")
    return {"phase": phase, "task": task}


@pytest.fixture()
def finished(store):
    records = stamped_store(store, "finished", lambda root, cli, defs: _seed_finished(cli, defs))
    return store, records


def _tab_ids(app):
    return [pane.id for pane in app.query_one("#efforts").query("TabPane")]


def _finished_tab(app, effort):
    return app.query_one("#efforts").get_tab(f"effort-{effort}").has_class("finished")


@pytest.mark.parametrize("width", WIDTHS)
def test_finished_effort_says_all_tasks_done_under_active(finished, width):
    store, _ = finished

    async def scenario(app, pilot):
        app.query_one("#efforts").active = "effort-alpha"
        await pilot.pause()
        pane = app.panes["alpha"]
        assert not pane.query_one("#tasks").display
        assert pane.query_one("#tasks-empty").display
        assert str(pane.query_one("#tasks-empty").render()) == "All 2 tasks done"

    _run(store, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_finished_effort_with_a_text_filter_says_no_tasks_match(finished, width):
    store, _ = finished

    async def scenario(app, pilot):
        app.query_one("#efforts").active = "effort-alpha"
        await pilot.pause()
        await pilot.press("slash", *"zzz")
        await pilot.pause()
        assert str(app.panes["alpha"].query_one("#tasks-empty").render()) == "No tasks match"

    _run(store, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_live_effort_beside_a_finished_one_still_says_no_tasks_match(finished, width):
    store, _ = finished

    async def scenario(app, pilot):
        assert app.query_one("#efforts").active == "effort-beta"
        await pilot.press("slash", *"zzz")
        await pilot.pause()
        pane = app.panes["beta"]
        assert pane.query_one("#tasks-empty").display
        assert str(pane.query_one("#tasks-empty").render()) == "No tasks match"

    _run(store, width, scenario)


def test_finished_effort_sorts_after_a_live_effort_with_a_dimmed_label(finished):
    store, _ = finished

    async def scenario(app, pilot):
        assert _tab_ids(app) == ["effort-beta", "effort-alpha"]
        assert _finished_tab(app, "alpha")
        assert not _finished_tab(app, "beta")
        await pilot.press("tab")
        await pilot.pause()
        assert app.query_one("#efforts").active == "effort-alpha"

    _run(store, 120, scenario)


def test_tab_and_shift_tab_switch_to_a_finished_effort_beside_live_needs_you_items(finished, cli, defs):
    store, _ = finished
    _record(cli, defs, "project:continuity-question", "beta", {"subject": "beta", "owner": "ayin", "blocking": False, "scope": "which one"})

    async def scenario(app, pilot):
        tabs = app.query_one("#efforts")
        await _until(pilot, lambda: app.panes["beta"].query_one("#needs-you").option_count == 1)
        assert tabs.active == "effort-beta"
        for key in ("tab", "shift+tab"):
            await pilot.press(key)
            await pilot.pause(0.3)
            assert tabs.active == "effort-alpha"
            await pilot.press(key)
            await pilot.pause(0.3)
            assert tabs.active == "effort-beta"
            assert isinstance(app.focused, tasks_module.TaskTable)

    _run(store, 120, scenario)


def test_effort_finished_mid_session_moves_last_and_dims(finished, cli):
    store, records = finished

    async def scenario(app, pilot):
        app.filters["beta"] = tasks_module.TaskFilter(tab="done")
        h.transition(cli, "project:work-item", records["task"], "in_progress", "done")
        h.transition(cli, "project:phase", records["phase"], "done")
        await _until(pilot, lambda: _tab_ids(app) == ["effort-alpha", "effort-beta"] and _finished_tab(app, "beta"))
        await _until(pilot, lambda: app.panes["beta"].query_one("#tasks").row_count == 1)
        assert app.filters["beta"].tab == "done"
        assert app.query_one("#efforts").active == "effort-beta"

    _run(store, 120, scenario, interval=0.3)


def test_once_lists_finished_efforts_last(finished):
    store, _ = finished
    result = subprocess.run(
        ["uv", "run", "--script", str(SCRIPT), "--once"], capture_output=True, text=True, cwd=str(store),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.index("ship beta") < result.stdout.index("ship alpha")


LONG_SCOPE = (
    "which storage backend should the dashboard read when both the home store and the repo store exist and disagree"
    " about the live goal, the phases, and every open work-item in the effort"
)


def _needs_text(app):
    return "\n".join(str(app.query_one("#needs-you").get_option_at_index(i).prompt)
                     for i in range(app.query_one("#needs-you").option_count))


def _needy(cli, defs):
    _needs_task(cli, defs)
    return _record(cli, defs, "project:continuity-question", "alpha",
                   {"subject": "alpha", "owner": "ayin", "blocking": False, "scope": LONG_SCOPE},
                   "Pick the **home** store unless the repo pins one.")


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_needs_you_body_headings_have_no_blank_line_above(seeded, cli, defs, size):
    _needy(cli, defs)

    async def scenario(app, pilot):
        await _until(pilot, lambda: app.query_one("#needs-you").option_count == 3)
        await _focus_needs(app, pilot, LONG_SCOPE)
        await pilot.press("enter")
        screen = await _needs_shown(app, pilot)
        await _assert_headings_follow_text(app, pilot, screen.query_one("#needs-body Markdown"), HEADED_BODY)

    _detail_run(seeded, size, scenario)


def _item(app, text):
    return next(item for view in app.snapshot.efforts for item in view.needs_you if item.text == text)


async def _focus_needs(app, pilot, text):
    await pilot.press("n")
    await pilot.pause()
    needs = app.query_one("#needs-you")
    wanted = [option.id for option in needs.options].index(_item(app, text).id)
    for _ in range(wanted):
        await pilot.press("down")
    await pilot.pause()
    return needs


async def _needs_shown(app, pilot):
    await _until(pilot, lambda: isinstance(app.screen, app_module.NeedsYouDetailScreen) and app.screen.loaded)
    await _settled(app, pilot)
    return app.screen


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_n_focuses_the_needs_you_list_and_esc_returns_to_the_task_table(seeded, cli, defs, size):
    _needy(cli, defs)

    async def scenario(app, pilot):
        await _until(pilot, lambda: app.query_one("#needs-you").option_count == 3)
        assert app.focused is app.query_one("#tasks")
        await pilot.press("n")
        await pilot.pause()
        needs = app.query_one("#needs-you")
        assert app.focused is needs
        assert needs.highlighted == 0
        await pilot.press("down")
        assert needs.highlighted == 1
        await pilot.press("up")
        assert needs.highlighted == 0
        await pilot.press("escape")
        await pilot.pause()
        assert app.focused is app.query_one("#tasks")

    _detail_run(seeded, size, scenario)


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_needs_you_enter_on_a_linked_item_opens_its_task_detail(seeded, cli, defs, size):
    _needy(cli, defs)

    async def scenario(app, pilot):
        await _until(pilot, lambda: app.query_one("#needs-you").option_count == 3)
        await _focus_needs(app, pilot, "need a call")
        await pilot.press("enter")
        screen = await _shown(app, pilot)
        assert screen.task_id == _item(app, "need a call").task_id
        assert screen.detail.subject == "a-waiting"

    _detail_run(seeded, size, scenario)


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_needs_you_enter_on_a_question_opens_the_needs_you_detail_with_full_text_and_body(seeded, cli, defs, size):
    _needy(cli, defs)

    async def scenario(app, pilot):
        await _until(pilot, lambda: app.query_one("#needs-you").option_count == 3)
        needs = app.query_one("#needs-you")
        shown = [needs.render_line(y).text for y in range(needs.option_count)]
        assert not any(LONG_SCOPE in line for line in shown) and any("which storage" in line for line in shown)
        item = _item(app, LONG_SCOPE)
        assert item.task_id == ""
        await _focus_needs(app, pilot, LONG_SCOPE)
        await pilot.press("enter")
        screen = await _needs_shown(app, pilot)
        assert str(screen.query_one("#needs-bar").render()).startswith("alpha")
        chips = str(screen.query_one("#needs-chips").render())
        assert chips.startswith("question") and "project:continuity-question" in chips
        assert screen.query_one("#needs-text Markdown").source == LONG_SCOPE
        assert screen.query_one("#needs-body Markdown").source == "Pick the **home** store unless the repo pins one."
        await pilot.press("escape")
        await pilot.pause(0.3)
        assert not isinstance(app.screen, app_module.NeedsYouDetailScreen)
        assert app.focused is app.query_one("#needs-you")
        await pilot.press("escape")
        await pilot.pause()
        assert app.focused is app.query_one("#tasks")

    _detail_run(seeded, size, scenario)


@pytest.mark.parametrize("size", DETAIL_SIZES)
def test_c_on_the_needs_you_list_and_detail_copies_the_item_subject(seeded, cli, defs, size):
    _needy(cli, defs)

    async def scenario(app, pilot):
        await _until(pilot, lambda: app.query_one("#needs-you").option_count == 3)
        await _focus_needs(app, pilot, "need a call")
        await pilot.press("c")
        await pilot.pause()
        assert app.clipboard == "a-waiting"
        assert "Copied a-waiting" in _notices(app)
        await pilot.press("escape")
        await _focus_needs(app, pilot, LONG_SCOPE)
        await pilot.press("enter")
        await _needs_shown(app, pilot)
        await pilot.press("c")
        await pilot.pause()
        assert app.clipboard == "alpha"

    _detail_run(seeded, size, scenario)


def test_needs_you_detail_follows_the_store_and_blocks_dashboard_keys(seeded, cli, defs):
    record = _needy(cli, defs)

    async def scenario(app, pilot):
        await _until(pilot, lambda: app.query_one("#needs-you").option_count == 3)
        await _focus_needs(app, pilot, LONG_SCOPE)
        await pilot.press("enter")
        screen = await _needs_shown(app, pilot)
        for key in ("tab", "n", "p", "slash", "1"):
            await pilot.press(key)
            await pilot.pause()
            assert app.screen is screen
        result = cli("update", "--type", "project:continuity-question", "--id", record["id"],
                     "--expected-revision", record["revision"],
                     "--payload", json.dumps({**record["payload"], "scope": "which backend, revised"}))
        assert result.returncode == 0, result.stdout + result.stderr
        await _until(pilot, lambda: screen.query_one("#needs-text Markdown").source == "which backend, revised")

    _detail_run(seeded, (120, 40), scenario, interval=0.3)


def _evidence_goal(cli, defs, effort="alpha"):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject=effort,
        extra_payload={"goal": f"ship {effort}", "kind": "deliver"},
    )


def _widget_lines(widget):
    return [widget.render_line(y).text.rstrip() for y in range(widget.size.height)]


def _plain_lines(widget):
    rendered = widget.render()
    if hasattr(rendered, "plain"):
        text = rendered.plain
    elif hasattr(rendered, "renderable"):
        inner = rendered.renderable
        text = inner.plain if hasattr(inner, "plain") else str(inner)
    elif hasattr(widget, "option_count"):
        text = "\n".join(_prompt_plain(widget.get_option_at_index(i).prompt) for i in range(widget.option_count))
    else:
        text = str(rendered)
    return text.splitlines()


def _prompt_plain(prompt):
    return prompt.plain if hasattr(prompt, "plain") else str(prompt)


def _is_dim(style):
    if isinstance(style, str):
        return "dim" in style.split()
    return bool(getattr(style, "dim", False))


def _error_colours(rendered, line, error):
    start = str(rendered).index(line)
    return {
        Style.parse(str(span.style)).color.get_truecolor()
        for span in rendered.spans if span.start < start + len(line) and span.end > start + 8
    }


@pytest.mark.parametrize("width", WIDTHS)
def test_evidence_tally_shows_verified_count_at_both_widths(store, cli, defs, width):
    _evidence_goal(cli, defs)
    _phase(cli, defs, "alpha", "t", 1, "in_progress")
    _spec(cli, defs, "t", "R1, R2")
    _task(cli, defs, "t-one", "t", "R1")
    _task(cli, defs, "t-two", "t", "R2")
    _assessment(cli, defs, "t", "R1", status="verified", next="release", confidence="high")

    async def scenario(app, pilot):
        row = _row_text(app, "phase:t")
        assert "R 1/2 verified" in row
        assert "Release ready" not in row

    _run(store, width, scenario)


def test_evidence_activity_shows_new_kinds_in_error_colour(store, cli, defs):
    _evidence_goal(cli, defs)
    _phase(cli, defs, "alpha", "act", 1, "in_progress")
    _spec(cli, defs, "act", "R1, R2")
    _assessment(cli, defs, "act", "R1", status="failed", level="implementation", next="execute", confidence="high")
    _assessment(cli, defs, "act", "R2", status="blocked", level="plan", next="plan", confidence="high")
    _report(cli, defs, "act", "fail", "ports disagree")
    _release(cli, defs, "act", "failed")
    _phase(cli, defs, "alpha", "blk", 2, "in_progress")
    _spec(cli, defs, "blk")
    _report(cli, defs, "blk", "blocked", "stuck")
    _phase(cli, defs, "alpha", "ok", 3, "in_progress")
    _spec(cli, defs, "ok")
    _assessment(cli, defs, "ok", "R1", status="verified", next="release", confidence="high")
    _report(cli, defs, "ok", "pass", "clean")
    _release(cli, defs, "ok", "ready")

    async def scenario(app, pilot):
        error = app_module.palette_from(app.get_css_variables())["error"]
        rendered = app.query_one("#activity").render()
        lines = str(rendered).splitlines()
        failed = [
            "R1 failed execute", "R2 blocked plan upstream", "act fail", "blk blocked", "act failed",
        ]
        quiet = ["R1 verified release", "ok pass", "ok ready"]
        for suffix in failed:
            line = next(item for item in lines if item.endswith(suffix))
            assert " ✗ " in line
            assert _error_colours(rendered, line, error) == {Style.parse(error).color.get_truecolor()}
        for suffix in quiet:
            line = next(item for item in lines if item.endswith(suffix))
            assert "✗" not in line

    _run(store, 60, scenario)


def test_evidence_needs_shows_loop_and_integration_lines(store, cli, defs):
    _evidence_goal(cli, defs)
    _phase(cli, defs, "alpha", "up", 1, "in_progress")
    _spec(cli, defs, "up")
    _task(cli, defs, "up-task", "up", "R1")
    _assessment(cli, defs, "up", "R1", status="failed", level="design", next="design", confidence="high")
    _phase(cli, defs, "alpha", "bad", 2, "in_progress")
    _spec(cli, defs, "bad")
    _task(cli, defs, "bad-task", "bad", "R1")
    _report(cli, defs, "bad", "blocked", "stuck")

    async def scenario(app, pilot):
        text = _needs_text(app)
        route = next(line for line in text.splitlines() if "R1" in line and "design" in line)
        assert "failed" in route
        blocked = next(line for line in text.splitlines() if "bad" in line and "blocked" in line)
        assert "R1" not in blocked or "design" not in blocked
        pane = app.query_one(app_module.EffortPane)
        limit = pane.size.width
        assert limit <= 60
        for line in _widget_lines(app.query_one("#needs-you")):
            assert len(line) <= limit, line

    _run(store, 60, scenario)


def test_evidence_strip_marks_the_current_stage_and_fits(store, cli, defs):
    _evidence_goal(cli, defs)
    _phase(cli, defs, "alpha", "strip", 1, "in_progress")
    _spec(cli, defs, "strip", "R1", weight="full", non_goals="No new screen.")
    _design(cli, defs, "strip", "use-columns")
    _decision(cli, defs, "use-columns", "strip", "two")
    _task(cli, defs, "strip-task", "strip", "R1", done=True)
    _report(cli, defs, "strip", "fail", "ports disagree")
    _phase(cli, defs, "alpha", "plain", 2, "in_progress")
    _spec(cli, defs, "plain")
    _task(cli, defs, "plain-task", "plain", "R1")

    async def scenario(app, pilot):
        await pilot.press("6")
        await pilot.pause()
        table = app.query_one("#tasks")
        table.move_cursor(row=table.get_row_index("phase:strip"))
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        stage = screen.query_one("#phase-stage").render()
        plain = stage.plain
        for name in ("specify", "design", "plan", "execute", "integrate", "verify", "assess", "release"):
            assert name in plain
        marked = plain.index("assess")
        assert any(style.bold for style in _styles_covering(stage, marked, marked + len("assess")))
        other = plain.index("specify")
        assert not any(style.bold for style in _styles_covering(stage, other, other + len("specify")))
        spec = str(screen.query_one("#phase-spec").render())
        assert "full" in spec and "No new screen." in spec
        design = str(screen.query_one("#phase-design").render())
        assert "use-columns" in design and "two" in design
        report = str(screen.query_one("#phase-integration").render())
        assert "fail" in report and "Conflicts" in report and "ports disagree" in report
        limit = screen.query_one("#phase").scrollable_content_region.width
        assert limit <= 60
        for selector in ("#phase-stage", "#phase-spec", "#phase-design", "#phase-integration", "#phase-requirements"):
            widget = screen.query_one(selector)
            assert widget.display
            for line in _plain_lines(widget):
                assert len(line) <= limit, (selector, line)
            for line in _widget_lines(widget):
                assert len(line) <= screen.query_one("#phase").size.width, (selector, line)
        await pilot.press("escape")
        await _until(pilot, lambda: not isinstance(app.screen, app_module.PhaseDetailScreen))
        table = app.query_one("#tasks")
        table.move_cursor(row=table.get_row_index("phase:plain"))
        await pilot.press("p")
        bare = await _phase_shown(app, pilot)
        assert bare.query_one("#phase-stage").display
        assert not bare.query_one("#phase-integration").display

    _run(store, 60, scenario, height=40)


@pytest.mark.parametrize("width", WIDTHS)
def test_evidence_release_marks_the_tab_and_phase_row(store, cli, defs, width):
    _evidence_goal(cli, defs, "alpha")
    _phase(cli, defs, "alpha", "rel", 1, "in_progress")
    _spec(cli, defs, "rel", effort="alpha")
    _task(cli, defs, "rel-task", "rel", "R1", effort="alpha")
    _release(cli, defs, "rel", "ready", effort="alpha")
    _evidence_goal(cli, defs, "gamma")
    _phase(cli, defs, "gamma", "nof", 1, "in_progress")
    _spec(cli, defs, "nof", effort="gamma")
    _task(cli, defs, "nof-task", "nof", "R1", effort="gamma")
    _release(cli, defs, "nof", "failed", effort="gamma")
    _evidence_goal(cli, defs, "beta")
    _phase(cli, defs, "beta", "ship", 1, "in_progress", "done")
    _spec(cli, defs, "ship", effort="beta")
    _task(cli, defs, "ship-task", "ship", "R1", done=True, effort="beta")
    _release(cli, defs, "ship", "ready", effort="beta")

    def row(app, effort, key):
        table = app.panes[effort].query_one("#tasks")
        return " ".join(str(cell) for cell in table.get_row(key))

    async def scenario(app, pilot):
        tabs = app.query_one("#efforts")
        alpha = tabs.get_tab("effort-alpha")
        assert "Release ready" in str(alpha.label)
        assert "finished" not in alpha.classes
        assert "Release ready" in row(app, "alpha", "phase:rel")
        await pilot.press("tab")
        await pilot.pause()
        gamma = tabs.get_tab("effort-gamma")
        assert "Release ready" not in str(gamma.label)
        assert "finished" not in gamma.classes
        assert "Release ready" not in row(app, "gamma", "phase:nof")
        await pilot.press("tab")
        await pilot.pause()
        beta = tabs.get_tab("effort-beta")
        assert "Release ready" in str(beta.label)
        assert "finished" in beta.classes
        await pilot.press("6")
        await pilot.pause()
        assert "Release ready" in row(app, "beta", "phase:ship")

    _run(store, width, scenario)


def test_evidence_requirement_list_shows_status_next_and_dim_check(store, cli, defs):
    _evidence_goal(cli, defs)
    _phase(cli, defs, "alpha", "rows", 1, "in_progress")
    _spec(cli, defs, "rows", "R1, R2", weight="full", body=ROW_SPEC)
    _task(cli, defs, "row-a", "rows", "R1")
    _task(cli, defs, "row-b", "rows", "R1")
    _task(cli, defs, "row-c", "rows", "R2")
    _assessment(cli, defs, "rows", "R1", status="failed", level="design", next="design", confidence="high")
    own = _accept(cli, defs, "row-c-check", "rows", "R2")
    _check(cli, defs, "row-c-fail", own["id"], "fail", "R2", "integration")

    async def scenario(app, pilot):
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        reqs = screen.query_one("#phase-requirements")
        prompts = [reqs.get_option_at_index(index).prompt for index in range(reqs.option_count)]
        by_id = {prompt.plain.split()[0]: prompt for prompt in prompts}
        assert set(by_id) == {"R1", "R2"}
        assert by_id["R1"].plain.split() == ["R1", "failed", "design", "2"]
        assert by_id["R2"].plain.split()[:3] == ["R2", "unassessed", "1"]
        assert by_id["R2"].plain.split()[-1] == "fail"
        start = by_id["R2"].plain.rindex("fail")
        assert any(_is_dim(span.style) for span in by_id["R2"].spans if span.start <= start < span.end)
        failed_at = by_id["R1"].plain.index("failed")
        assert not any(_is_dim(span.style) for span in by_id["R1"].spans if span.start <= failed_at < span.end)

    _run(store, 60, scenario)


def test_evidence_simple_phase_matches_the_previous_frame(seeded):
    async def scenario(app, pilot):
        assert "ship the alpha dashboard" in _text(app, "#goal")
        row = _row_text(app, "phase:two")
        assert "Phase two" in row and "0/3" in row
        assert "verified" not in row and "Release ready" not in row
        stepper = _text(app, "#stepper")
        assert "1 done" in stepper and "● Phase two 0/3" in stepper and "○ Phase three" in stepper
        assert "✓" not in stepper and "Phase one" not in stepper
        assert " · " not in stepper
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        assert "Phase two" in str(screen.query_one("#phase-bar").render())
        assert "in_progress" in str(screen.query_one("#phase-chips").render())
        for selector in ("#phase-stage", "#phase-spec", "#phase-design", "#phase-integration", "#phase-requirements"):
            assert not screen.query_one(selector).display

    _run(seeded, 60, scenario)
    result = subprocess.run(
        ["uv", "run", "--script", str(SCRIPT), "--once"], capture_output=True, text=True, cwd=str(seeded),
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "\x1b" not in out
    for needle in ("alpha", "ship the alpha dashboard", "1 done", "Running", "title of a-running", "which backend", "Needs you 1"):
        assert needle in out
    assert "Active (3)   Running (1)   Ready (1)   Waiting (1)   Done (1)   All (4)" in out
    assert "● Phase two 0/3" in out and "○ Phase three" in out
    assert "✓ Phase one" not in out
    stepper_line = next(line for line in out.splitlines() if "Phase two" in line)
    assert " · " not in stepper_line
    assert "verified" not in out and "Release ready" not in out
    assert max(len(line) for line in out.splitlines()) <= 100


def _option_index(widget, prefix):
    for index in range(widget.option_count):
        if str(widget.get_option_at_index(index).id).startswith(prefix):
            return index
    raise AssertionError(prefix)


async def _requirement_shown(app, pilot):
    from dashboard.requirement_detail import RequirementDetailScreen

    await _until(pilot, lambda: type(app.screen) is RequirementDetailScreen and app.screen.loaded)
    await _settled(app, pilot)
    return app.screen


def test_evidence_link_task_opens_the_requirement(store, cli, defs):
    _evidence_goal(cli, defs)
    _phase(cli, defs, "alpha", "linked", 1, "in_progress")
    _spec(cli, defs, "linked", "R1")
    _decision(cli, defs, "pick-a", "linked", "keep the list")
    task = _task(cli, defs, "linked-task", "linked", "R1, R2", "pick-a, pick-b")

    async def scenario(app, pilot):
        screen = await _open_task(app, pilot, task)
        lines = _link_lines(screen)
        assert "Requirement: R1" in lines
        assert "Requirement: R2" in lines
        assert "Decision: pick-a" in lines
        assert "Decision: pick-b" in lines
        links = screen.query_one("#detail-links")
        assert links.get_option_at_index(_option_index(links, "req:linked:R1")).id == "req:linked:R1"
        assert links.get_option_at_index(_option_index(links, "decision:pick-a")).id == "decision:pick-a"
        await _focus_links(app, pilot, screen)
        links.highlighted = _option_index(links, "decision:pick-a")
        await pilot.press("enter")
        await pilot.pause()
        assert type(app.screen) is detail_module.TaskDetailScreen
        assert len(app.screen_stack) == 2
        links.highlighted = _option_index(links, "req:linked:R1")
        await pilot.press("enter")
        opened = await _requirement_shown(app, pilot)
        assert (opened.effort, opened.phase, opened.requirement) == ("alpha", "linked", "R1")
        assert "text of R1" in str(opened.query_one("#requirement-text").render())
        await pilot.press("escape")
        await _until(pilot, lambda: type(app.screen) is detail_module.TaskDetailScreen and app.screen.loaded)
        assert app.screen is screen
        assert len(app.screen_stack) == 2

    _run(store, 60, scenario)


def test_evidence_link_needs_opens_the_requirement(store, cli, defs):
    _evidence_goal(cli, defs)
    _phase(cli, defs, "alpha", "up", 1, "in_progress")
    _spec(cli, defs, "up")
    _task(cli, defs, "up-task", "up", "R1")
    _assessment(cli, defs, "up", "R1", status="failed", level="design", next="design", confidence="high")
    _phase(cli, defs, "alpha", "bad", 2, "in_progress")
    _spec(cli, defs, "bad")
    _task(cli, defs, "bad-task", "bad", "R1")
    _report(cli, defs, "bad", "blocked", "stuck")

    async def scenario(app, pilot):
        await pilot.press("n", "enter")
        opened = await _requirement_shown(app, pilot)
        assert (opened.phase, opened.requirement) == ("up", "R1")
        assert "text of R1" in str(opened.query_one("#requirement-text").render())
        await pilot.press("escape")
        await _until(pilot, lambda: type(app.screen) is not type(opened))
        await pilot.press("n", "j", "enter")
        await _until(pilot, lambda: type(app.screen) is app_module.NeedsYouDetailScreen)
        assert app.screen.item.kind == "integration"
        assert (app.screen.item.phase, app.screen.item.result) == ("bad", "blocked")

    _run(store, 60, scenario)


def test_evidence_link_phase_opens_the_requirement(store, cli, defs):
    _evidence_goal(cli, defs)
    _phase(cli, defs, "alpha", "rows", 1, "in_progress")
    _spec(cli, defs, "rows", "R1")
    _task(cli, defs, "row-a", "rows", "R1")

    async def scenario(app, pilot):
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        reqs = screen.query_one("#phase-requirements")
        reqs.focus()
        if reqs.highlighted is None:
            reqs.highlighted = 0
        await pilot.press("enter")
        opened = await _requirement_shown(app, pilot)
        assert (opened.effort, opened.phase, opened.requirement) == ("alpha", "rows", "R1")
        assert "text of R1" in str(opened.query_one("#requirement-text").render())
        await pilot.press("escape")
        await _until(pilot, lambda: type(app.screen) is app_module.PhaseDetailScreen and app.screen.loaded)
        assert app.screen is screen
        assert len(app.screen_stack) == 2

    _run(store, 60, scenario)


def test_evidence_stepper_shows_the_stage_word_within_60_columns(store, cli, defs):
    _evidence_goal(cli, defs)
    _phase(cli, defs, "alpha", "old", 1, "in_progress", "done")
    done = _task(cli, defs, "old-task", "old", done=True)
    assert done["lifecycle_state"] == "done"
    _phase(cli, defs, "alpha", "step", 2, "in_progress")
    _spec(cli, defs, "step")
    _task(cli, defs, "step-task", "step", "R1")
    _assessment(cli, defs, "step", "R1", status="failed", level="implementation", next="execute", confidence="high")
    _phase(cli, defs, "alpha", "later", 3)

    async def scenario(app, pilot):
        await _pane_settled(app, pilot)
        pane = app.query_one(app_module.EffortPane)
        lines = _stepper_lines(app)
        limit = pane.scrollable_content_region.width
        assert limit <= 60
        assert all(len(line) <= limit for line in lines), lines
        joined = " ".join(lines)
        assert "● Phase step 0/1 · execute" in joined
        tail = joined.split("○", 1)[1]
        assert tail.strip() == "Phase later"
        assert " · " not in tail

    _run(store, 60, scenario)


def _estimate_goal(cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject="alpha",
        extra_payload={"goal": "g", "kind": "deliver"},
    )


def _phase_body(defs, size_line=None):
    approach = size_line if size_line else "placeholder text for Approach."
    return (
        "## Problem\n\nplaceholder text for Problem.\n\n"
        f"## Approach\n\n{approach}\n\n"
        "## Exit criteria\n\nplaceholder text for Exit criteria.\n"
    )


def _open_phase(cli, defs, subject, ordinal, title, body):
    record = _record(
        cli, defs, "project:phase", subject,
        {"title": title, "ordinal": ordinal, "effort": "alpha"}, body,
    )
    return h.transition(cli, "project:phase", record, "in_progress")


def _estimate_task(cli, defs, subject, phase, **payload):
    fields = {
        "title": payload.pop("title", f"title of {subject}"),
        "phase": phase, "kind": "deliver", "assignee": "", "effort": "alpha",
    }
    fields.update(payload)
    rels = []
    depends = fields.pop("depends_on", None)
    if depends:
        rels.append(f"depends_on:{depends}")
    return _record(cli, defs, "project:work-item", subject, fields, None, *rels)


def _task_plain(app, task_id):
    return str(app.query_one("#tasks").get_row(task_id)[1]).strip()


def test_estimate_view_header_sitting(store, cli, defs):
    _estimate_goal(cli, defs)
    _open_phase(cli, defs, "wide", 1, "Wide phase", _phase_body(defs, "Size: more than one sitting."))
    _open_phase(cli, defs, "plain", 2, "Plain phase", _phase_body(defs))
    _estimate_task(cli, defs, "wide-task", "wide")
    _estimate_task(cli, defs, "plain-task", "plain")

    async def scenario(app, pilot):
        wide = _row_text(app, "phase:wide")
        plain = _row_text(app, "phase:plain")
        assert re.search(r"0/1 · more than one", wide)
        assert "one sitting" not in wide
        assert "more than one" not in plain
        assert "one sitting" not in plain

    _run(store, 60, scenario)


def test_estimate_view_header_elapsed(store, cli, defs):
    _estimate_goal(cli, defs)
    _open_phase(cli, defs, "sub", 1, "Sub phase", _phase_body(defs))
    _open_phase(cli, defs, "add", 2, "Inline phase", _phase_body(defs))
    _estimate_task(cli, defs, "sub-short", "sub", estimate_minutes=10, executor="subagent")
    _estimate_task(cli, defs, "sub-long", "sub", estimate_minutes=40, executor="subagent")
    _estimate_task(cli, defs, "add-a", "add", estimate_minutes=10, executor="inline")
    _estimate_task(cli, defs, "add-b", "add", estimate_minutes=15, executor="inline")

    async def scenario(app, pilot):
        sub = _row_text(app, "phase:sub")
        inline = _row_text(app, "phase:add")
        assert re.search(r"40m", sub) and "50m" not in sub
        assert re.search(r"25m", inline) and "15m" not in inline

    _run(store, 60, scenario)


def test_estimate_view_header_partial(store, cli, defs):
    _estimate_goal(cli, defs)
    _open_phase(cli, defs, "part", 1, "Partial phase", _phase_body(defs))
    _open_phase(cli, defs, "none", 2, "None phase", _phase_body(defs))
    _estimate_task(cli, defs, "part-a", "part")
    _estimate_task(cli, defs, "part-b", "part")
    _estimate_task(cli, defs, "part-c", "part", estimate_minutes=25)
    _estimate_task(cli, defs, "none-a", "none")
    _estimate_task(cli, defs, "none-b", "none")

    async def scenario(app, pilot):
        partial = _row_text(app, "phase:part")
        blank = _row_text(app, "phase:none")
        assert re.search(r"25m · 2 unset", partial)
        assert not re.search(r"\d+m", blank)
        assert "unset" not in blank

    _run(store, 60, scenario)


def test_estimate_view_title_suffix(store, cli, defs):
    _estimate_goal(cli, defs)
    _open_phase(cli, defs, "suf", 1, "Suffix phase", _phase_body(defs))
    blocker = _estimate_task(cli, defs, "blocker", "suf", title="Blocker")
    full = _estimate_task(
        cli, defs, "full", "suf", title="Full", size="M", estimate_minutes=25,
        executor="inline", depends_on=blocker["id"],
    )
    nosize = _estimate_task(cli, defs, "nosize", "suf", title="Nosize", estimate_minutes=10, executor="inline")
    zero = _estimate_task(cli, defs, "zero", "suf", title="Zero", estimate_minutes=0)
    blank = _estimate_task(cli, defs, "blank", "suf", title="Blank")

    async def scenario(app, pilot):
        full_plain = _task_plain(app, full["id"])
        assert " · M · 25m · inline  waits on blocker" in full_plain
        assert full_plain.index(" · M") < full_plain.index("  waits on")
        cell = app.query_one("#tasks").get_row(full["id"])[1]
        start = str(cell).index(" · M")
        muted = app_module.palette_from(app.get_css_variables())["muted"]
        assert any(span.start <= start and str(span.style) == muted for span in cell.spans)
        assert _task_plain(app, nosize["id"]).endswith(" · 10m · inline")
        assert _task_plain(app, zero["id"]).endswith(" · 0m · subagent")
        blank_plain = _task_plain(app, blank["id"])
        assert blank_plain.endswith(" · subagent")
        assert not re.search(r"\d+m", blank_plain)

    _run(store, 60, scenario)


def test_estimate_view_clip(store, cli, defs):
    _estimate_goal(cli, defs)
    phase_title = "Long phase " + "word " * 40
    task_title = "Long task " + "word " * 40
    _open_phase(cli, defs, "clip", 1, phase_title, _phase_body(defs, "Size: more than one sitting."))
    long = _estimate_task(
        cli, defs, "long", "clip", title=task_title, size="M", estimate_minutes=25, executor="inline",
    )
    _estimate_task(cli, defs, "clip-a", "clip", title="Unset one")
    _estimate_task(cli, defs, "clip-b", "clip", title="Unset two")

    async def scenario(app, pilot):
        header = _row_text(app, "phase:clip")
        assert re.search(r"0/3 · more than one · 25m · 2 unset", header)
        assert header.index("…") < header.index("more than one")
        assert "…" not in header.split("…", 1)[1]
        plain = _task_plain(app, long["id"])
        assert " · M · 25m · inline" in plain
        assert plain.index("…") < plain.index(" · M · 25m · inline")
        assert "…" not in plain.split("…", 1)[1]

    _run(store, 60, scenario)
