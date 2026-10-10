"""Task table code: status tabs, filter, phase sections, row cells and the table widget."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from rich.text import Text
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.widgets import DataTable

from dashboard import gates, model
from dashboard.display import PHASE_GLYPH, STATUS_GLYPH, WIDE, clip, elapsed

STATUS_TABS = (
    ("active", "Active", "1"), ("running", "Running", "2"), ("ready", "Ready", "3"),
    ("waiting", "Waiting", "4"), ("done", "Done", "5"), ("all", "All", "6"),
)
TAB_STATUSES = {
    "active": ("running", "ready", "waiting"), "running": ("running",), "ready": ("ready",),
    "waiting": ("waiting",), "done": ("done", "withdrawn"),
}


def tab_tasks(view: model.EffortView, tab: str, selected_phase: str | None = None) -> list[model.TaskRow]:
    pool = [task for task in view.tasks if selected_phase is None or task.phase == selected_phase]
    if tab == "all":
        return pool
    return [task for task in pool if task.status in TAB_STATUSES[tab]]


def counts(view: model.EffortView, selected_phase: str | None = None) -> dict[str, int]:
    return {name: len(tab_tasks(view, name, selected_phase)) for name, _, _ in STATUS_TABS}


def phase_progress(view: model.EffortView, phase: str) -> tuple[int, int]:
    tasks = [task for task in view.tasks if task.phase == phase and task.status != "withdrawn"]
    return sum(task.status == "done" for task in tasks), len(tasks)


@dataclass


class TaskFilter:
    text: str = ""
    tab: str = "active"
    sections: dict[str, bool] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return bool(self.text)


def visible_tasks(tasks: list[model.TaskRow], task_filter: TaskFilter) -> list[model.TaskRow]:
    needle = task_filter.text.lower()
    return [
        task for task in tasks
        if not needle or needle in task.title.lower() or needle in task.subject.lower()
    ]

FOLD_KEY = "fold"
PHASE_PREFIX = "phase:"
FOLD_AFTER = 2


@dataclass(frozen=True)


class SectionRow:
    key: str
    kind: str
    expanded: bool = False
    phase: model.PhaseRow | None = None
    task: model.TaskRow | None = None
    hidden: int = 0


def phase_key(phase: model.PhaseRow) -> str:
    return PHASE_PREFIX + phase.subject


def opens_by_default(phase: model.PhaseRow) -> bool:
    return phase.state == "in_progress" or phase.awaiting_signoff


def section_rows(
    view: model.EffortView, tasks: list[model.TaskRow], sections: dict[str, bool], show_empty: bool,
    selected_phase: str | None = None,
) -> list[SectionRow]:
    if selected_phase is not None:
        return [SectionRow(task.id, "task", task=task) for task in tasks if task.phase == selected_phase]
    by_phase: dict[str, list[model.TaskRow]] = {}
    for task in tasks:
        by_phase.setdefault(task.phase, []).append(task)
    shown = [phase for phase in view.phases if by_phase.get(phase.subject) or show_empty]
    done = [phase for phase in shown if phase.state == "done"]
    folded = {phase.subject for phase in done[:-FOLD_AFTER]} if len(done) > FOLD_AFTER else set()
    fold_open = sections.get(FOLD_KEY, False)
    rows: list[SectionRow] = []
    for phase in shown:
        if phase.subject in folded:
            if not any(row.key == FOLD_KEY for row in rows):
                rows.append(SectionRow(FOLD_KEY, "fold", fold_open, hidden=len(folded)))
            if not fold_open:
                continue
        expanded = sections.get(phase_key(phase), opens_by_default(phase))
        rows.append(SectionRow(phase_key(phase), "phase", expanded, phase=phase))
        if expanded:
            rows.extend(SectionRow(task.id, "task", task=task) for task in by_phase.get(phase.subject, []))
    known = {phase.subject for phase in view.phases}
    rows.extend(SectionRow(task.id, "task", task=task) for task in tasks if task.phase not in known)
    return rows


def tasks_title(shown: int, total: int, task_filter: TaskFilter) -> str:
    parts = ["Tasks"]
    if task_filter.active:
        parts.append(f"{shown} of {total}")
        parts.append(f"/{task_filter.text}")
    return " · ".join(parts)


def empty_text(view: model.EffortView, task_filter: TaskFilter) -> str:
    if view.finished and task_filter.tab == "active" and not task_filter.text:
        return f"All {sum(task.status == 'done' for task in view.tasks)} tasks done"
    return "No tasks match"


def status_label(
    status: str, running_since: datetime | None, now: datetime, *, quiet: bool = False,
) -> str:
    label = f"{STATUS_GLYPH.get(status, '·')} {status}"
    if running_since is not None:
        label = f"{label} {elapsed(running_since, now)}"
    if quiet:
        label = f"{label} · quiet"
    return label


def status_cell(task: model.TaskRow, colors: dict[str, str], now: datetime) -> Text:
    quiet = gates.is_quiet(task, now)
    style = colors["warning"] if quiet else colors[task.status]
    return Text(status_label(task.status, task.running_since, now, quiet=quiet), style=style)


def task_columns(width: int) -> list[str]:
    columns = ["status", "task"]
    return columns + ["assignee"] if width >= WIDE else columns


def task_suffix(task: model.TaskRow) -> str:
    parts = []
    if task.size:
        parts.append(task.size)
    if task.estimate_minutes is not None:
        parts.append(f"{task.estimate_minutes}m")
    parts.append(task.executor or "subagent")
    return " · " + " · ".join(parts)


def title_cell(task: model.TaskRow, width: int, colors: dict[str, str], indent: str = "") -> Text:
    title = task.title or task.subject
    tail = task_suffix(task)
    room = width - len(indent)
    shown = "…" if len(tail) >= room else clip(title, room - len(tail))
    text = Text(indent + shown + tail)
    text.stylize(colors["muted"], len(indent) + len(shown))
    return text


def task_cells(
    task: model.TaskRow, columns: list[str], title_width: int, colors: dict[str, str], now: datetime, indent: str = "",
) -> list[Text | str]:
    values: dict[str, Text | str] = {
        "status": status_cell(task, colors, now), "task": title_cell(task, title_width, colors, indent),
        "phase": task.phase, "assignee": task.assignee,
    }
    return [values[name] for name in columns]


def phase_label(phase: model.PhaseRow, title_width: int) -> str:
    title = phase.title or phase.subject
    tail = f" {phase.done}/{phase.total}"
    if phase.sitting:
        tail += f" · {phase.sitting}"
    if phase.elapsed_minutes is not None:
        tail += f" · {phase.elapsed_minutes}m"
        if phase.unset_estimates > 0:
            tail += f" · {phase.unset_estimates} unset"
    if phase.awaiting_signoff:
        tail += " · awaiting sign-off"
    evidence = phase.evidence
    if evidence is not None:
        verified = sum(row.status == "verified" for row in evidence.requirements)
        tail += f" · R {verified}/{len(evidence.requirements)} verified"
        if evidence.release_ready:
            tail += " · Release ready"
    room = title_width - len(tail)
    if room < 1:
        return "…" + tail
    return clip(title, room) + tail


def section_cells(row: SectionRow, columns: list[str], title_width: int, colors: dict[str, str]) -> list[Text | str]:
    marker = "▾" if row.expanded else "▸"
    if row.phase is None:
        noun = "phase" if row.hidden == 1 else "phases"
        values: dict[str, Text | str] = {
            "status": Text(marker, style=colors["muted"]),
            "task": Text(clip(f"{row.hidden} earlier {noun} done", title_width), style=colors["muted"]),
        }
    else:
        phase = row.phase
        style = colors["warning"] if phase.awaiting_signoff else colors["muted"] if phase.state != "in_progress" else colors["primary"]
        status = Text(marker, style=colors["muted"]) if phase.state == "done" else Text(
            f"{marker} {PHASE_GLYPH[phase.state]}", style=style,
        )
        values = {
            "status": status,
            "task": Text(phase_label(phase, title_width), style=style),
        }
    return [values.get(name, "") for name in columns]


def title_width(columns: list[str], width: int, tasks: list[model.TaskRow], now: datetime) -> int:
    fixed = {
        "status": max([
            len(status_label(t.status, t.running_since, now, quiet=gates.is_quiet(t, now)))
            for t in tasks
        ] + [9]),
        "assignee": max([len(t.assignee) for t in tasks] + [8]),
    }
    used = sum(fixed[name] for name in columns if name != "task") + 2 * len(columns)
    return max(width - used, 12)


class TaskTable(DataTable):
    BINDINGS = [
        Binding("enter", "select_cursor", "open", show=False),
        Binding("left", "app.step_status_tab(-1)", "previous tab", show=False),
        Binding("right", "app.step_status_tab(1)", "next tab", show=False),
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
        Binding("pageup", "app.scroll_pane('page_up')", "page up", show=False),
        Binding("pagedown", "app.scroll_pane('page_down')", "page down", show=False),
        Binding("home", "app.scroll_pane('home')", "top", show=False),
        Binding("end", "app.scroll_pane('end')", "bottom", show=False),
    ]

    def on_click(self, event) -> None:
        row = event.style.meta.get("row", -1)
        if row >= 0 and row < self.row_count:
            event.prevent_default()
            self.move_cursor(row=row)
            self.app.activate(self.coordinate_to_cell_key(Coordinate(row, 0)).row_key.value)
