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
    assert tasks.task_columns(WIDE - 1) == ["status", "task", "wave"]
    assert tasks.task_columns(WIDE) == ["status", "task", "wave", "assignee"]


def test_status_label_shows_elapsed_time_for_a_running_task():
    assert tasks.status_label("running", NOW - timedelta(minutes=5), NOW) == "▶ running 5m"
    assert tasks.status_label("ready", None, NOW) == "● ready"


def test_title_cell_clips_and_notes_what_a_waiting_task_waits_on():
    row = task("w", "waiting", title="Wait", waits_on=("b", "a"))
    assert tasks.title_cell(row, 40, COLORS).plain == "Wait · subagent  waits on a, b"
    clipped = tasks.title_cell(task("x", title="y" * 30), 10, COLORS, indent="  ")
    assert clipped.plain == "  … · subagent"
    assert clipped.plain.split(" · subagent")[0].endswith("…")


def test_tasks_title_counts_only_while_a_filter_is_active():
    assert tasks.tasks_title(3, 9, tasks.TaskFilter()) == "Tasks"
    assert tasks.tasks_title(3, 9, tasks.TaskFilter(text="ab")) == "Tasks · 3 of 9 · /ab"
