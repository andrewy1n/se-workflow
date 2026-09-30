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
        assert sorted(str(key.description) for key in keys) == ["open", "quit", "refresh", "switch"]
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
        await _until(pilot, lambda: table.row_count == 5)
        assert table.coordinate_to_cell_key(table.cursor_coordinate).row_key == key

    _run(seeded, 120, scenario, interval=0.3)


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
            await _until(pilot, lambda: app.query("#tasks") and app.query_one("#tasks").row_count >= 4)
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


def test_detail_footer_shows_back_refresh_and_quit_within_60_columns(detailed):
    store, task, _ = detailed

    async def scenario(app, pilot):
        await _open_by_enter(app, pilot, task["id"])
        await _shown(app, pilot)
        keys = list(app.screen.query("FooterKey"))
        assert sorted(str(key.description) for key in keys) == ["back", "quit", "refresh"]
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
