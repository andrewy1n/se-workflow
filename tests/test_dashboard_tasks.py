"""Tests for dashboard.tasks: the task filter, status tabs, phase sections and row cells."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from conftest import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT))
from dashboard import model  # noqa: E402
from dashboard import tasks  # noqa: E402
from dashboard.display import WIDE  # noqa: E402

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
COLORS = {"muted": "dim", "primary": "cyan", "warning": "yellow", "running": "cyan", "waiting": "dim"}


def task(subject: str, status: str = "ready", phase: str = "p1", **fields) -> model.TaskRow:
    return model.TaskRow(
        id=f"id-{subject}", subject=subject, title=fields.pop("title", subject), phase=phase, assignee="",
        wave=fields.pop("wave", 1), status=status, **fields,
    )


def phase(subject: str, state: str, ordinal: int, done: int = 0, total: int = 1) -> model.PhaseRow:
    return model.PhaseRow(subject=subject, title=subject, ordinal=ordinal, state=state, done=done, total=total)


def test_visible_tasks_matches_title_or_subject_case_insensitively():
    rows = [task("alpha", title="Build Table"), task("beta", title="Other"), task("gamma-table", title="x")]
    shown = tasks.visible_tasks(rows, tasks.TaskFilter(text="TABLE"))
    assert [row.subject for row in shown] == ["alpha", "gamma-table"]


def test_tab_tasks_active_excludes_done_and_withdrawn():
    view = model.EffortView(
        "e", "g", tasks=[task("a", "running"), task("b", "done"), task("c", "withdrawn"), task("d", "waiting")],
    )
    assert [row.subject for row in tasks.tab_tasks(view, "active")] == ["a", "d"]
    assert [row.subject for row in tasks.tab_tasks(view, "done")] == ["b", "c"]
    assert tasks.counts(view)["all"] == 4


def test_section_rows_fold_done_phases_older_than_the_last_two():
    phases = [phase(f"d{i}", "done", i, 1, 1) for i in range(1, 5)] + [phase("now", "in_progress", 5)]
    rows = [task(f"t{i}", "done", f"d{i}") for i in range(1, 5)] + [task("live", "running", "now")]
    view = model.EffortView("e", "g", phases=phases, tasks=rows)
    sections = tasks.section_rows(view, rows, {}, show_empty=False)
    assert [(row.kind, row.key) for row in sections if row.kind != "task"] == [
        ("fold", tasks.FOLD_KEY), ("phase", "phase:d3"), ("phase", "phase:d4"), ("phase", "phase:now"),
    ]
    assert sections[0].hidden == 2
    assert [row.task.subject for row in sections if row.kind == "task"] == ["live"]


def test_section_rows_open_the_fold_and_expand_a_done_phase_on_request():
    phases = [phase(f"d{i}", "done", i, 1, 1) for i in range(1, 4)]
    rows = [task(f"t{i}", "done", f"d{i}") for i in range(1, 4)]
    view = model.EffortView("e", "g", phases=phases, tasks=rows)
    sections = tasks.section_rows(view, rows, {tasks.FOLD_KEY: True, "phase:d1": True}, show_empty=False)
    assert [row.key for row in sections] == [tasks.FOLD_KEY, "phase:d1", "id-t1", "phase:d2", "phase:d3"]


def test_section_rows_append_tasks_of_unknown_phases_last():
    view = model.EffortView("e", "g", phases=[phase("p1", "in_progress", 1)], tasks=[task("a"), task("b", phase="gone")])
    sections = tasks.section_rows(view, view.tasks, {}, show_empty=False)
    assert [row.key for row in sections] == ["phase:p1", "id-a", "id-b"]


def test_task_columns_add_assignee_only_at_wide_widths():
    assert tasks.task_columns(WIDE - 1) == ["status", "task"]
    assert tasks.task_columns(WIDE) == ["status", "task", "assignee"]


def test_tab_tasks_scoped_to_selected_phase():
    view = model.EffortView(
        "e", "g",
        phases=[phase("p1", "in_progress", 1), phase("p2", "planned", 2)],
        tasks=[task("a", "running", "p1"), task("b", "done", "p1"), task("c", "ready", "p2")],
    )
    assert [row.subject for row in tasks.tab_tasks(view, "active", "p1")] == ["a"]
    assert tasks.counts(view, "p1") == {"active": 1, "running": 1, "ready": 0, "waiting": 0, "done": 1, "all": 2}


def test_phase_progress_counts_done_and_total():
    view = model.EffortView(
        "e", "g",
        tasks=[task("a", "done", "p1"), task("b", "running", "p1"), task("c", "withdrawn", "p1"), task("d", "ready", "p2")],
    )
    assert tasks.phase_progress(view, "p1") == (1, 2)


def test_section_rows_selected_phase_returns_flat_task_rows():
    view = model.EffortView(
        "e", "g",
        phases=[phase("p1", "in_progress", 1), phase("p2", "planned", 2)],
        tasks=[task("a", "running", "p1"), task("b", "ready", "p2")],
    )
    rows = tasks.section_rows(view, view.tasks, {}, show_empty=False, selected_phase="p1")
    assert [(row.kind, row.task.subject if row.task else None) for row in rows] == [("task", "a")]


def test_status_label_shows_elapsed_time_for_a_running_task():
    assert tasks.status_label("running", NOW - timedelta(minutes=5), NOW) == "▶ running 5m"
    assert tasks.status_label("ready", None, NOW) == "● ready"


def test_gates_quiet_status_label_and_wave_strip_use_warning_colour():
    from dashboard import selection

    quiet = task(
        "quiet", "running",
        running_since=NOW - timedelta(minutes=5),
        estimate_minutes=10,
        last_record_at=NOW - timedelta(minutes=25),
    )
    fresh = task(
        "fresh", "running",
        running_since=NOW - timedelta(minutes=5),
        estimate_minutes=10,
        last_record_at=NOW - timedelta(minutes=5),
    )
    label = tasks.status_label(
        quiet.status, quiet.running_since, NOW, quiet=True,
    )
    assert label == "▶ running 5m · quiet"
    cell = tasks.status_cell(quiet, COLORS, NOW)
    assert "quiet" in cell.plain
    assert cell.style == COLORS["warning"]
    fresh_cell = tasks.status_cell(fresh, COLORS, NOW)
    assert "quiet" not in fresh_cell.plain
    assert fresh_cell.style == COLORS["running"]

    view = model.EffortView(
        "e", "g",
        phases=[phase("p1", "in_progress", 1)],
        tasks=[quiet, fresh],
    )
    strip = selection.wave_strip(view, "p1", 80, COLORS, NOW)
    assert "▶" in strip.plain
    warning_spans = [span for span in strip.spans if span.style == COLORS["warning"]]
    assert warning_spans
    assert view.needs_you == []


def test_title_cell_clips_and_omits_waits_on_for_a_waiting_task():
    row = task("w", "waiting", title="Wait", waits_on=("b", "a"))
    cell = tasks.title_cell(row, 40, COLORS)
    assert cell.plain == "Wait · subagent"
    assert "waits on" not in cell.plain
    assert cell.plain.endswith(" · subagent")
    muted_start = len("Wait")
    assert any(span.start == muted_start and span.style == COLORS["muted"] for span in cell.spans)
    many = task("m", "waiting", title="Wait", waits_on=tuple(f"dep-{i}" for i in range(8)))
    for width in (60, 120):
        plain = tasks.title_cell(many, width, COLORS).plain
        assert "waits on" not in plain
        assert "\n" not in plain
        assert plain.endswith(" · subagent")
    clipped = tasks.title_cell(task("x", title="y" * 30), 10, COLORS, indent="  ")
    assert clipped.plain == "  … · subagent"
    assert clipped.plain.split(" · subagent")[0].endswith("…")


def test_tasks_title_counts_only_while_a_filter_is_active():
    assert tasks.tasks_title(3, 9, tasks.TaskFilter()) == "Tasks"
    assert tasks.tasks_title(3, 9, tasks.TaskFilter(text="ab")) == "Tasks · 3 of 9 · /ab"
