#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["textual>=0.80"]
# ///
"""Textual dashboard for the project's artifact store. `--once` prints one plain-text frame."""

from __future__ import annotations

import argparse
import asyncio
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifact_store  # noqa: E402
import dashboard_model as model  # noqa: E402
from rich.console import Console, Group  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402
from textual import events, work  # noqa: E402
from textual.binding import Binding  # noqa: E402
from textual.app import App, ComposeResult  # noqa: E402
from textual.containers import Horizontal, Vertical, VerticalScroll  # noqa: E402
from textual.coordinate import Coordinate  # noqa: E402
from textual.screen import Screen  # noqa: E402
from textual.widget import Widget  # noqa: E402
from textual.widgets._tabbed_content import ContentTabs  # noqa: E402
from textual.widgets import (  # noqa: E402
    Collapsible, DataTable, Footer, Input, Markdown, ProgressBar, Static, TabbedContent, TabPane,
)

WIDE = 90
ACTIVITY_LINES = 10
REDRAW_SECONDS = 30
STATUS_GLYPH = {"running": "▶", "ready": "●", "waiting": "◌", "done": "✓", "withdrawn": "✕"}
PHASE_GLYPH = {"done": "✓", "in_progress": "●", "planned": "○"}
ACTIVITY_GLYPH = {"assignment": "→", "execution-report": "≡", "check-run": "◇"}
RESULT_GLYPH = {"pass": "✓", "fail": "✗"}
NEEDS_LABEL = {
    "blocking-question": "blocking", "needs-human": "needs you",
    "unsigned-check": "unsigned", "open-question": "question",
}
ANSI_PALETTE = {
    "primary": "cyan", "success": "green", "warning": "yellow", "error": "red", "muted": "dim",
    "running": "cyan", "ready": "green", "waiting": "dim", "done": "dim", "withdrawn": "red",
}


def palette_from(variables: dict[str, str]) -> dict[str, str]:
    colors = {
        name: variables.get(name, ANSI_PALETTE[name]) for name in ("primary", "success", "warning", "error")
    }
    colors["muted"] = "dim"
    return {
        **colors, "running": colors["primary"], "ready": colors["success"],
        "waiting": colors["muted"], "done": colors["muted"], "withdrawn": colors["error"],
    }


def relative_time(then: datetime, now: datetime) -> str:
    seconds = max(0, int((now - then).total_seconds()))
    if seconds < 60:
        return "now"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    return f"{seconds // 3600}h ago"


def current_phase(view: model.EffortView) -> tuple[int, model.PhaseRow] | None:
    for state in ("in_progress", "planned"):
        for index, phase in enumerate(view.phases, 1):
            if phase.state == state:
                return index, phase
    if view.phases:
        return len(view.phases), view.phases[-1]
    return None


def stepper_text(view: model.EffortView, colors: dict[str, str], width: int = 100) -> Text:
    style = {"done": colors["success"], "in_progress": colors["primary"], "planned": colors["muted"]}
    text = Text()
    used = 0
    for index, phase in enumerate(view.phases):
        label = f"{PHASE_GLYPH[phase.state]} {phase.title or phase.subject}"
        if phase.state == "in_progress":
            label += f" {phase.done}/{phase.total}"
        if index:
            if used + 3 + len(label) > width:
                text.append("\n")
                used = 0
            else:
                text.append("   ")
                used += 3
        text.append(label, style=style[phase.state])
        used += len(label)
    return text


def effort_progress(view: model.EffortView) -> tuple[int, int]:
    return sum(phase.done for phase in view.phases), sum(phase.total for phase in view.phases)


def progress_label(view: model.EffortView) -> str:
    found = current_phase(view)
    if found is None:
        return ""
    done, total = effort_progress(view)
    return f"phase {found[0]}/{len(view.phases)} · {done} of {total} tasks"


STATUS_TABS = (
    ("active", "Active", "1"), ("running", "Running", "2"), ("ready", "Ready", "3"),
    ("waiting", "Waiting", "4"), ("needs", "Needs you", "5"), ("done", "Done", "6"), ("all", "All", "7"),
)
TAB_STATUSES = {
    "active": ("running", "ready", "waiting"), "running": ("running",), "ready": ("ready",),
    "waiting": ("waiting",), "done": ("done", "withdrawn"),
}


def tab_tasks(view: model.EffortView, tab: str) -> list[model.TaskRow]:
    if tab == "all":
        return list(view.tasks)
    if tab == "needs":
        subjects = {item.subject for item in view.needs_you}
        return [task for task in view.tasks if task.subject in subjects]
    return [task for task in view.tasks if task.status in TAB_STATUSES[tab]]


def counts(view: model.EffortView) -> dict[str, int]:
    return {name: len(tab_tasks(view, name)) for name, _, _ in STATUS_TABS}


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
) -> list[SectionRow]:
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


def status_cell(task: model.TaskRow, colors: dict[str, str]) -> Text:
    return Text(f"{STATUS_GLYPH[task.status]} {task.status}", style=colors[task.status])


def wave_cell(task: model.TaskRow) -> str:
    return "" if task.wave is None else f"w{task.wave}"


def clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: max(width - 1, 1)] + "…"


def task_columns(width: int) -> list[str]:
    columns = ["status", "task", "wave"]
    return columns + ["phase", "assignee"] if width >= WIDE else columns


def task_cells(
    task: model.TaskRow, columns: list[str], title_width: int, colors: dict[str, str], indent: str = "",
) -> list[Text | str]:
    values: dict[str, Text | str] = {
        "status": status_cell(task, colors), "task": indent + clip(task.title or task.subject, title_width - len(indent)),
        "wave": wave_cell(task), "phase": task.phase, "assignee": task.assignee,
    }
    return [values[name] for name in columns]


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
        label = f"{phase.title or phase.subject} {phase.done}/{phase.total}"
        if phase.awaiting_signoff:
            label += " · awaiting sign-off"
        values = {
            "status": Text(f"{marker} {PHASE_GLYPH[phase.state]}", style=style),
            "task": Text(clip(label, title_width), style=style),
        }
    return [values.get(name, "") for name in columns]


def title_width(columns: list[str], width: int, tasks: list[model.TaskRow]) -> int:
    fixed = {"status": 9, "wave": 4, "phase": max([len(t.phase) for t in tasks] + [5]), "assignee": max([len(t.assignee) for t in tasks] + [8])}
    used = sum(fixed[name] for name in columns if name != "task") + 2 * len(columns)
    return max(width - used, 12)


def needs_lines(view: model.EffortView, colors: dict[str, str], width: int = 100) -> list[Text]:
    lines = []
    for item in view.needs_you:
        color = colors["error"] if item.kind == "blocking-question" else colors["warning"]
        line = Text(no_wrap=True, overflow="ellipsis")
        line.append(f"{NEEDS_LABEL[item.kind]:<9}", style=color)
        line.append(f" {clip(item.text, max(width - 12 - len(item.subject) - 2, 10))}")
        line.append(f"  {clip(item.subject, max(width - 12, 10))}", style=colors["muted"])
        lines.append(line)
    return lines


def activity_lines(view: model.EffortView, now: datetime, colors: dict[str, str], width: int = 100) -> list[Text]:
    lines = []
    for item in view.activity[:ACTIVITY_LINES]:
        line = Text(no_wrap=True, overflow="ellipsis")
        line.append(f"{relative_time(item.recorded_at, now):>7}", style=colors["muted"])
        line.append(f" {ACTIVITY_GLYPH.get(item.kind, '·')} ")
        line.append(clip(item.summary, max(width - 10, 10)))
        lines.append(line)
    return lines


def header_text(target: artifact_store.Target, stamp: datetime | None, colors: dict[str, str], width: int = 100) -> Text:
    updated = f"  updated {stamp.astimezone().strftime('%H:%M:%S')}" if stamp is not None else ""
    room = width - len(target.root.name) - len(updated) - 4
    text = Text(no_wrap=True, overflow="ellipsis")
    text.append(target.root.name, style="bold")
    if room >= 12:
        text.append(f"  {clip(str(target.store), room)}", style=colors["muted"])
    text.append(updated, style=colors["muted"])
    return text


def tab_label(view: model.EffortView) -> str:
    return f"⚠ {view.effort}" if view.needs_you else view.effort


def render_once(target: artifact_store.Target, snapshot: model.Snapshot, console: Console) -> None:
    colors = ANSI_PALETTE
    console.print(header_text(target, snapshot.generated_at, colors))
    if not snapshot.efforts:
        console.print(f"\nNo live efforts in {target.store}")
    for view in snapshot.efforts:
        console.print()
        console.rule(Text(tab_label(view), style="bold"), align="left")
        console.print(Text(view.goal, style=colors["muted"]))
        console.print(stepper_text(view, colors, console.width))
        label = progress_label(view)
        if label:
            console.print(Text(label, style=colors["muted"]))
        tally = counts(view)
        console.print("   ".join(f"{label} {tally[name]}" for name, label, _ in STATUS_TABS))
        if view.tasks:
            columns = task_columns(console.width)
            table = Table(box=None, pad_edge=False, header_style=colors["muted"])
            for name in columns:
                table.add_column(name, no_wrap=name != "task", overflow="ellipsis")
            for task in view.tasks:
                table.add_row(*task_cells(task, columns, console.width, colors))
            console.print(Group(Text(), table))
        if view.needs_you:
            console.print(Text("\nNeeds you", style=colors["warning"]))
            for line in needs_lines(view, colors):
                console.print(line)
        lines = activity_lines(view, snapshot.generated_at, colors)
        if lines:
            console.print(Text("\nActivity", style=colors["muted"]))
            for line in lines:
                console.print(line)


def status_chip(status: str, colors: dict[str, str]) -> tuple[str, str]:
    return f"{STATUS_GLYPH.get(status, '·')} {status}", colors.get(status, colors["muted"])


def detail_chips(detail: model.TaskDetail, colors: dict[str, str], width: int = 100) -> Text:
    label, style = status_chip(detail.status, colors)
    chips = [(label, style)]
    if detail.phase:
        chips.append((f"phase {detail.phase}", colors["muted"]))
    if detail.wave is not None:
        chips.append((f"w{detail.wave}", colors["muted"]))
    if detail.assignee:
        chips.append((f"assignee {detail.assignee}", colors["muted"]))
    text = Text()
    used = 0
    for index, (chip, chip_style) in enumerate(chips):
        if index:
            if used + 3 + len(chip) > width:
                text.append("\n")
                used = 0
            else:
                text.append(" · ", style=colors["muted"])
                used += 3
        text.append(chip, style=chip_style)
        used += len(chip)
    return text


def phase_chips(detail: model.PhaseDetail, colors: dict[str, str]) -> Text:
    done = sum(task.status == "done" for task in detail.tasks)
    total = sum(task.status != "withdrawn" for task in detail.tasks)
    text = Text()
    text.append(f"{PHASE_GLYPH.get(detail.state, '·')} {detail.state}", style=colors["muted"])
    if detail.awaiting_signoff:
        text.append(" · ", style=colors["muted"])
        text.append("awaiting sign-off", style=colors["warning"])
    text.append(f" · {done}/{total} tasks", style=colors["muted"])
    return text


def phase_task_lines(tasks: list[model.TaskRow], colors: dict[str, str]) -> Text:
    text = Text(no_wrap=True, overflow="ellipsis")
    for index, task in enumerate(tasks):
        text.append("\n" if index else "")
        text.append(f"{STATUS_GLYPH.get(task.status, '·')} ", style=colors.get(task.status, colors["muted"]))
        text.append(task.title or task.subject)
    return text


def linked_line(label: str, tasks: list[model.LinkedTask], colors: dict[str, str]) -> Text:
    text = Text(f"{label} ")
    for index, task in enumerate(tasks):
        text.append("   " if index else "")
        text.append(f"{STATUS_GLYPH.get(task.status, '·')} ", style=colors.get(task.status, colors["muted"]))
        text.append(task.subject, style=colors["muted"])
    return text


def description_source(body: str) -> str:
    return re.sub(r"\A\s*##\s+Description[ \t]*\n+", "", body).strip()


def acceptance_mark(row: model.AcceptanceRow, colors: dict[str, str]) -> Text:
    if row.check is None:
        return Text("–", style=colors["muted"])
    if row.check.result == "pass":
        return Text("✓", style=colors["success"])
    return Text("✗", style=colors["error"])


def acceptance_body(row: model.AcceptanceRow, colors: dict[str, str]) -> Text:
    text = Text(row.criterion)
    how = " · ".join(part for part in (row.method, row.verify_command) if part)
    if how:
        text.append(f"\n{how}", style=colors["muted"])
    if row.check is not None:
        text.append(f"\nrev {row.check.revision}", style=colors["muted"])
        if row.check.signed_by:
            text.append(f" · signed by {row.check.signed_by}", style=colors["muted"])
        elif row.check.method == "manual":
            text.append(" · ", style=colors["muted"])
            text.append("unsigned", style=colors["warning"])
    return text


FIELD_BLOCK = re.compile(r"\A\s*```[^\n]*\n(.*?)\n?```[ \t]*(?:\n(.*))?\Z", re.DOTALL)
FIELD_LINE = re.compile(r"([A-Za-z_][\w-]*):[ \t]*(.*)")


def split_fields(body: str) -> tuple[list[tuple[str, str]], str] | None:
    found = FIELD_BLOCK.match(body)
    if found is None:
        return None
    fields: list[list[str]] = []
    for line in found.group(1).splitlines():
        match = FIELD_LINE.fullmatch(line)
        if match:
            fields.append([match.group(1), match.group(2)])
        elif fields and line.strip():
            fields[-1][1] += " " + line.strip()
        elif not fields and line.strip():
            return None
    if not fields:
        return None
    return [(key, value) for key, value in fields], (found.group(2) or "").strip()


def field_value(key: str, value: str, colors: dict[str, str]) -> Text:
    style = {"pass": colors["success"], "fail": colors["error"]}.get(value) if key in ("result", "verdict") else None
    return Text(value, style=style or "")


def event_label(event: model.TimelineEvent, now: datetime) -> str:
    stamp = event.recorded_at.astimezone().strftime("%H:%M")
    return f"{stamp} {relative_time(event.recorded_at, now)}"


def related_text(related: list[model.RelatedRecord], colors: dict[str, str]) -> Text:
    text = Text()
    for index, record in enumerate(related):
        text.append("\n" if index else "")
        text.append(f"{record.kind}: ", style=colors["muted"])
        text.append(record.text)
    return text


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)


@dataclass(frozen=True)
class Commit:
    sha: str
    author: str
    date: str
    subject: str
    message: str
    stat: list[str]


def latest_revision(events: list[model.TimelineEvent]) -> str | None:
    usable = [e for e in events if e.kind in ("execution-report", "check-run") and e.revision and e.revision != "dirty"]
    return max(usable, key=lambda e: e.recorded_at).revision if usable else None


def load_commit(root: Path, revision: str, width: int = 80) -> Commit | None:
    if revision.startswith("-"):
        return None
    command = ["git", "-C", str(root), "show", f"--stat={max(width, 20)}", "--format=%H%x1f%an%x1f%aI%x1f%s%x1f%b%x1e", revision, "--"]
    try:
        done = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    head, _, stat = done.stdout.partition("\x1e")
    fields = head.split("\x1f")
    if len(fields) != 5:
        return None
    return Commit(*fields[:4], fields[4].strip(), [line for line in stat.splitlines() if line.strip()])


def stat_width(app: App) -> int:
    return app.size.width - 4


def stat_line(line: str, colors: dict[str, str]) -> Text:
    text = Text(no_wrap=True, overflow="ellipsis")
    name, bar, graph = line.partition("|")
    text.append(name + bar)
    for match in re.finditer(r"\++|-+|[^+-]+", graph):
        piece = match.group()
        style = colors["success"] if piece[0] == "+" else colors["error"] if piece[0] == "-" else ""
        text.append(piece, style=style)
    return text


def commit_header(commit: Commit, colors: dict[str, str]) -> Text:
    text = Text()
    for index, (label, value) in enumerate((
        ("commit", commit.sha), ("author", commit.author), ("date", commit.date), ("subject", commit.subject),
    )):
        text.append("\n" if index else "")
        text.append(f"{label:<8}", style=colors["muted"])
        text.append(value)
    return text


class EffortPane(VerticalScroll):
    def __init__(self, effort: str) -> None:
        super().__init__(classes="effort")
        self.effort = effort
        self.sections: dict[str, SectionRow] = {}

    def compose(self) -> ComposeResult:
        yield Static(id="goal")
        yield Static(id="stepper")
        yield Static(id="progress-label")
        yield ProgressBar(id="progress", show_eta=False, show_percentage=False)
        with Vertical(id="status-tabs"):
            for row in (STATUS_TABS[:4], STATUS_TABS[4:]):
                with Horizontal(classes="status-row"):
                    for name, label, _ in row:
                        yield StatusTab(name, label)
        filter_input = FilterInput(placeholder="filter tasks", id="filter")
        filter_input.display = False
        yield filter_input
        tasks = TaskTable(id="tasks", cursor_type="row", zebra_stripes=False)
        tasks.border_title = "Tasks"
        yield tasks
        none = Static("No tasks match", id="tasks-empty")
        none.border_title = "Tasks"
        none.display = False
        yield none
        needs = Static(id="needs-you")
        needs.border_title = "Needs you"
        yield needs
        activity = Static(id="activity")
        activity.border_title = "Activity"
        yield activity

    def show(self, view: model.EffortView, now: datetime, width: int, colors: dict[str, str]) -> None:
        self.last = (view, now, width, colors)
        inner = self.scrollable_content_region.width or width - 2
        self.inner = inner
        self.query_one("#goal", Static).update(Text(view.goal, style=colors["muted"]))
        self.query_one("#stepper", Static).update(stepper_text(view, colors, width - 4))
        found = current_phase(view)
        self.query_one("#progress-label", Static).update(progress_label(view))
        bar = self.query_one("#progress", ProgressBar)
        bar.display = found is not None
        self.query_one("#progress-label").display = found is not None
        if found is not None:
            done, total = effort_progress(view)
            bar.update(total=max(total, 1), progress=done)
        tally = counts(view)
        selected = self.app.filters.get(self.effort, TaskFilter()).tab
        for tab in self.query(StatusTab):
            tab.show(tally[tab.tab_name], tab.tab_name == selected)
        self.fill_tasks(view, width, inner, colors)
        self.fill_panel("#needs-you", needs_lines(view, colors, inner - 4))
        self.fill_panel("#activity", activity_lines(view, now, colors, inner - 4))

    def mark_status_tab(self, selected: str) -> None:
        for tab in self.query(StatusTab):
            tab.set_class(tab.tab_name == selected, "selected")

    def on_resize(self) -> None:
        last = getattr(self, "last", None)
        if last is not None and self.scrollable_content_region.width != self.inner:
            view, now, _, colors = last
            self.show(view, now, self.app.size.width, colors)

    def fill_panel(self, selector: str, lines: list[Text]) -> None:
        panel = self.query_one(selector, Static)
        panel.display = bool(lines)
        joined = Text(no_wrap=True, overflow="ellipsis")
        for index, line in enumerate(lines):
            joined.append("\n" if index else "")
            joined.append_text(line)
        panel.update(joined)

    def fill_tasks(self, view: model.EffortView, width: int, room: int, colors: dict[str, str]) -> None:
        table = self.query_one("#tasks", DataTable)
        task_filter = self.app.filters.get(self.effort, TaskFilter())
        pool = tab_tasks(view, task_filter.tab)
        tasks = visible_tasks(pool, task_filter)
        title = tasks_title(len(tasks), len(pool), task_filter)
        table.display = bool(tasks)
        table.border_title = title
        empty = self.query_one("#tasks-empty", Static)
        empty.display = not tasks
        empty.border_title = title
        keep = None
        if table.row_count:
            keep = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        table.clear(columns=True)
        columns = task_columns(width)
        for name in columns:
            table.add_column(name, key=name)
        room = title_width(columns, room - 4, tasks)
        show_empty = task_filter.tab == "all" and not task_filter.text
        self.sections = {}
        for row in section_rows(view, tasks, task_filter.sections, show_empty):
            self.sections[row.key] = row
            if row.task is None:
                table.add_row(*section_cells(row, columns, room, colors), key=row.key)
            else:
                grouped = row.task.phase in {phase.subject for phase in view.phases}
                table.add_row(*task_cells(row.task, columns, room, colors, "  " if grouped else ""), key=row.key)
        if keep is not None and keep in table.rows:
            table.move_cursor(row=table.get_row_index(keep))


class StatusTab(Static):
    def __init__(self, name: str, label: str) -> None:
        super().__init__(id=f"status-{name}", classes="status-tab")
        self.tab_name = name
        self.tab_label = label

    def show(self, number: int, selected: bool) -> None:
        self.update(Text.assemble((self.tab_label, ""), " ", (str(number), "bold")))
        self.set_class(selected, "selected")

    def on_click(self) -> None:
        self.app.select_status_tab(self.tab_name)


class FilterInput(Input):
    BINDINGS = [Binding("escape", "cancel", "clear", show=False)]

    def action_cancel(self) -> None:
        self.app.clear_filter()


class TaskTable(DataTable):
    BINDINGS = [
        Binding("enter", "select_cursor", "open"),
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


class TaskDetailScreen(Screen[None]):
    CSS = """
    #detail-bar { height: 1; padding: 0 1; background: $panel; }
    #detail-error { height: auto; padding: 0 1; background: $error 20%; color: $error; display: none; }
    #detail { padding: 0 1; scrollbar-gutter: stable; }
    #detail-loading { margin-top: 1; color: $text-muted; }
    #detail-content { height: auto; display: none; }
    #detail-title { margin-top: 1; text-style: bold; }
    #detail-depends, #detail-blocks { margin-top: 0; }
    #detail-depends { margin-top: 1; }
    .panel { height: auto; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; }
    .acceptance { height: auto; margin-bottom: 1; }
    .acceptance:last-child { margin-bottom: 0; }
    .mark { width: 2; }
    .body { width: 1fr; }
    .event { height: auto; }
    .fields { height: auto; }
    .field { height: auto; }
    .value { width: 1fr; }
    Static.event { padding-left: 2; }
    Collapsible { padding: 0; border-top: none; background: transparent; }
    CollapsibleTitle { padding: 0; background: transparent; }
    Collapsible > Contents { padding: 0 0 0 2; }
    Markdown { margin: 0; padding: 0; background: transparent; }
    Markdown > MarkdownBlock:last-child { margin-bottom: 0; }
    """
    AUTO_FOCUS = "#detail"
    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("c", "app.copy_slug", "copy"),
        Binding("g", "commit", "commit"),
        Binding("r", "app.refresh", "refresh"),
    ]

    def __init__(self, target: artifact_store.Target, task_id: str) -> None:
        super().__init__()
        self.target = target
        self.task_id = task_id
        self.detail: model.TaskDetail | None = None
        self.loaded = False
        self.expanded: dict[str, bool] = {}
        self.painting = asyncio.Lock()
        self.token: str | None = None
        self.loaded_at = 0.0

    def compose(self) -> ComposeResult:
        yield Static(id="detail-bar")
        yield Static(id="detail-error")
        with VerticalScroll(id="detail"):
            yield Static("Loading…", id="detail-loading")
            with Vertical(id="detail-content"):
                yield Static(id="detail-title")
                yield Static(id="detail-chips")
                yield Static(id="detail-depends")
                yield Static(id="detail-blocks")
                description = Vertical(Markdown(), id="description", classes="panel")
                description.border_title = "Description"
                yield description
                acceptances = Vertical(id="acceptances", classes="panel")
                acceptances.border_title = "Acceptance"
                yield acceptances
                timeline = Vertical(id="timeline", classes="panel")
                timeline.border_title = "Timeline"
                yield timeline
                related = Static(id="related", classes="panel")
                related.border_title = "Related"
                yield related
        yield Footer()

    def on_mount(self) -> None:
        self.load()

    def action_back(self) -> None:
        self.app.pop_screen()
        self.app.call_after_refresh(self.app.focus_tasks)

    def action_commit(self) -> None:
        if self.detail is None:
            return
        revision = latest_revision(self.detail.timeline)
        if revision is not None:
            self.open_commit(revision)
        elif any(e.revision for e in self.detail.timeline):
            self.app.notify("Only uncommitted (dirty) revisions recorded", timeout=4)
        else:
            self.app.notify(f"No revision recorded for {self.detail.subject}", timeout=4)

    @work(thread=True, exclusive=True, group="commit")
    def open_commit(self, revision: str) -> None:
        commit = load_commit(self.target.root, revision, stat_width(self.app))
        if commit is None:
            self.app.call_from_thread(
                self.app.notify, f"Commit {revision} not found in {self.target.root}", timeout=4,
            )
            return
        self.app.call_from_thread(self.app.push_screen, CommitScreen(commit, self.target.root, revision))

    @work(thread=True, exclusive=True, group="detail")
    def load(self) -> None:
        self.loaded_at = time.monotonic()
        try:
            self.token = model.change_token(self.target)
            detail = model.load_task_detail(self.target, self.task_id)
        except (OSError, model.ModelError) as exc:
            self.app.call_from_thread(self.show_error, str(exc))
            return
        self.app.call_from_thread(self.apply, detail)

    def poll(self, token: str) -> None:
        if token != self.token or time.monotonic() - self.loaded_at > REDRAW_SECONDS:
            self.load()

    def show_error(self, message: str) -> None:
        if not self.is_attached:
            return
        banner = self.query_one("#detail-error", Static)
        banner.update(Text(message.splitlines()[0] if message else "error", no_wrap=True, overflow="ellipsis"))
        banner.display = True

    async def apply(self, detail: model.TaskDetail) -> None:
        async with self.painting:
            if self.is_attached:
                await self.paint(detail)

    async def paint(self, detail: model.TaskDetail) -> None:
        colors = palette_from(self.app.get_css_variables())
        now = datetime.now(timezone.utc)
        scroll = self.query_one("#detail", VerticalScroll)
        offset = scroll.scroll_y
        self.detail = detail
        self.query_one("#detail-error", Static).display = False
        self.query_one("#detail-loading", Static).display = False
        self.query_one("#detail-content").display = True
        bar = Text(no_wrap=True, overflow="ellipsis")
        bar.append(detail.subject, style="bold")
        bar.append(f"  {detail.effort}", style=colors["muted"])
        self.query_one("#detail-bar", Static).update(bar)
        self.query_one("#detail-title", Static).update(Text(detail.title or detail.subject, style="bold"))
        self.paint_chips()
        for name, label, tasks in (
            ("depends", "Depends on:", detail.depends_on), ("blocks", "Blocks:", detail.blocks),
        ):
            line = self.query_one(f"#detail-{name}", Static)
            line.display = bool(tasks)
            line.update(linked_line(label, tasks, colors))
        await self.query_one("#description Markdown", Markdown).update(description_source(detail.body))
        await self.fill_acceptances(detail, colors)
        await self.fill_timeline(detail, now, colors)
        if not self.is_attached or not self.query("#related"):
            return
        related = self.query_one("#related", Static)
        related.display = bool(detail.related)
        related.update(related_text(detail.related, colors))
        self.loaded = True
        self.call_after_refresh(scroll.scroll_to, y=offset, animate=False)

    def paint_chips(self) -> None:
        if self.detail is None:
            return
        chips = self.query_one("#detail-chips", Static)
        colors = palette_from(self.app.get_css_variables())
        chips.update(detail_chips(self.detail, colors, chips.size.width or self.size.width - 4))

    def on_resize(self) -> None:
        self.paint_chips()

    async def fill_acceptances(self, detail: model.TaskDetail, colors: dict[str, str]) -> None:
        panel = self.query_one("#acceptances", Vertical)
        panel.display = bool(detail.acceptances)
        await panel.remove_children()
        await panel.mount_all(
            Horizontal(
                Static(acceptance_mark(row, colors), classes="mark"),
                Static(acceptance_body(row, colors), classes="body"), classes="acceptance",
            )
            for row in detail.acceptances
        )

    def body_widgets(self, body: str, colors: dict[str, str]) -> list[Widget]:
        split = split_fields(body)
        if split is None:
            return [Markdown(body)]
        fields, rest = split
        room = min(max(len(key) for key, _ in fields), 14) + 2
        rows = []
        for key, value in fields:
            label = Static(Text(key, style=colors["muted"]), classes="key")
            label.styles.width = room
            rows.append(Horizontal(label, Static(field_value(key, value, colors), classes="value"), classes="field"))
        block = Vertical(*rows, classes="fields")
        block.styles.margin = (0, 0, 1 if rest else 0, 0)
        widgets: list[Widget] = [block]
        if rest:
            widgets.append(Markdown(rest))
        return widgets

    async def fill_timeline(self, detail: model.TaskDetail, now: datetime, colors: dict[str, str]) -> None:
        panel = self.query_one("#timeline", Vertical)
        panel.display = bool(detail.timeline)
        for box in panel.query(Collapsible):
            self.expanded[box.id or ""] = not box.collapsed
        newest = next((e.id for e in reversed(detail.timeline) if e.kind == "execution-report"), None)
        widgets = []
        for event in detail.timeline:
            label = event_label(event, now)
            glyph = ACTIVITY_GLYPH.get(event.kind, "·")
            if event.body.strip():
                open_now = self.expanded.get(f"event-{slug(event.id)}", event.id == newest)
                widgets.append(Collapsible(
                    *self.body_widgets(event.body.strip(), colors), title=f"{label} {glyph} {event.summary}",
                    collapsed=not open_now, id=f"event-{slug(event.id)}", classes="event",
                ))
            else:
                line = Text()
                line.append(f"{label} ", style=colors["muted"])
                line.append(f"{glyph} {event.summary}")
                widgets.append(Static(line, classes="event"))
        await panel.remove_children()
        await panel.mount_all(widgets)


class PhaseDetailScreen(Screen[None]):
    CSS = """
    #phase-bar { height: 1; padding: 0 1; background: $panel; }
    #phase-error { height: auto; padding: 0 1; background: $error 20%; color: $error; display: none; }
    #phase { padding: 0 1; scrollbar-gutter: stable; }
    #phase-loading { margin-top: 1; color: $text-muted; }
    #phase-content { height: auto; display: none; }
    #phase-title { margin-top: 1; text-style: bold; }
    .phase-panel { height: auto; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; }
    #phase-body Markdown { margin: 0; padding: 0; background: transparent; }
    """
    AUTO_FOCUS = "#phase"
    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("c", "app.copy_slug", "copy"),
        Binding("r", "app.refresh", "refresh"),
    ]

    def __init__(self, target: artifact_store.Target, effort: str, phase_subject: str) -> None:
        super().__init__()
        self.target = target
        self.effort = effort
        self.phase_subject = phase_subject
        self.detail: model.PhaseDetail | None = None
        self.loaded = False
        self.token: str | None = None
        self.loaded_at = 0.0

    def compose(self) -> ComposeResult:
        yield Static(id="phase-bar")
        yield Static(id="phase-error")
        with VerticalScroll(id="phase"):
            yield Static("Loading…", id="phase-loading")
            with Vertical(id="phase-content"):
                yield Static(id="phase-title")
                yield Static(id="phase-chips")
                for name, label in (("body", "Phase"), ("decisions", "Decisions"), ("constraints", "Constraints"), ("tasks", "Tasks")):
                    panel = Vertical(Markdown(), id="phase-body", classes="phase-panel") if name == "body" else Static(id=f"phase-{name}", classes="phase-panel")
                    panel.border_title = label
                    yield panel
        yield Footer()

    def on_mount(self) -> None:
        self.load()

    def action_back(self) -> None:
        self.app.pop_screen()
        self.app.call_after_refresh(self.app.focus_tasks)

    @work(thread=True, exclusive=True, group="phase-detail")
    def load(self) -> None:
        self.loaded_at = time.monotonic()
        try:
            self.token = model.change_token(self.target)
            detail = model.load_phase_detail(self.target, self.effort, self.phase_subject)
        except (OSError, model.ModelError) as exc:
            self.app.call_from_thread(self.show_error, str(exc))
            return
        self.app.call_from_thread(self.apply, detail)

    def poll(self, token: str) -> None:
        if token != self.token or time.monotonic() - self.loaded_at > REDRAW_SECONDS:
            self.load()

    def show_error(self, message: str) -> None:
        if not self.is_attached:
            return
        banner = self.query_one("#phase-error", Static)
        banner.update(Text(message.splitlines()[0] if message else "error", no_wrap=True, overflow="ellipsis"))
        banner.display = True

    async def apply(self, detail: model.PhaseDetail) -> None:
        if not self.is_attached:
            return
        colors = palette_from(self.app.get_css_variables())
        self.detail = detail
        self.query_one("#phase-error", Static).display = False
        self.query_one("#phase-loading", Static).display = False
        self.query_one("#phase-content").display = True
        bar = Text(no_wrap=True, overflow="ellipsis")
        bar.append(detail.title or detail.subject, style="bold")
        bar.append(f"  {detail.effort}", style=colors["muted"])
        self.query_one("#phase-bar", Static).update(bar)
        self.query_one("#phase-title", Static).update(Text(detail.title or detail.subject, style="bold"))
        self.query_one("#phase-chips", Static).update(phase_chips(detail, colors))
        body = self.query_one("#phase-body")
        body.display = bool(detail.body.strip())
        await self.query_one("#phase-body Markdown", Markdown).update(detail.body.strip())
        for name, records in (("decisions", detail.decisions), ("constraints", detail.constraints)):
            panel = self.query_one(f"#phase-{name}", Static)
            panel.display = bool(records)
            panel.update(Text("\n".join(record.text for record in records)))
        tasks = self.query_one("#phase-tasks", Static)
        tasks.display = bool(detail.tasks)
        tasks.update(phase_task_lines(detail.tasks, colors))
        self.loaded = True


class CommitScreen(Screen[None]):
    CSS = """
    #commit-bar { height: 1; padding: 0 1; background: $panel; }
    #commit { padding: 0 1; }
    #commit-header { margin-top: 1; }
    #commit-message { margin-top: 1; }
    #commit-stat { margin-top: 1; height: auto; }
    """
    AUTO_FOCUS = "#commit"
    BINDINGS = [Binding("escape", "back", "back")]

    def __init__(self, commit: Commit, root: Path, revision: str) -> None:
        super().__init__()
        self.commit = commit
        self.root = root
        self.revision = revision
        self.stat_cols = 0
        self.loaded = False

    def compose(self) -> ComposeResult:
        yield Static(id="commit-bar")
        with VerticalScroll(id="commit"):
            yield Static(id="commit-header")
            yield Static(id="commit-message")
            yield Static(id="commit-stat")
        yield Footer()

    def on_mount(self) -> None:
        self.stat_cols = stat_width(self.app)
        self.render_commit()

    def on_resize(self) -> None:
        if self.loaded and stat_width(self.app) != self.stat_cols:
            self.stat_cols = stat_width(self.app)
            self.reload_commit(self.stat_cols)

    @work(thread=True, exclusive=True, group="commit-stat")
    def reload_commit(self, width: int) -> None:
        commit = load_commit(self.root, self.revision, width)
        if commit is not None:
            self.app.call_from_thread(self.show_commit, commit)

    def show_commit(self, commit: Commit) -> None:
        self.commit = commit
        self.render_commit()

    def render_commit(self) -> None:
        colors = palette_from(self.app.get_css_variables())
        commit = self.commit
        bar = Text(no_wrap=True, overflow="ellipsis")
        bar.append(commit.sha[:7], style="bold")
        bar.append(f"  {commit.subject}")
        self.query_one("#commit-bar", Static).update(bar)
        self.query_one("#commit-header", Static).update(commit_header(commit, colors))
        message = self.query_one("#commit-message", Static)
        message.display = bool(commit.message)
        message.update(Text(commit.message))
        stat = self.query_one("#commit-stat", Static)
        stat.display = bool(commit.stat)
        joined = Text(no_wrap=True, overflow="ellipsis")
        for index, line in enumerate(commit.stat):
            joined.append("\n" if index else "")
            joined.append_text(stat_line(line, colors))
        stat.update(joined)
        self.loaded = True

    def action_back(self) -> None:
        self.app.pop_screen()


class DashboardApp(App[None]):
    CSS = """
    #header { height: 1; padding: 0 1; background: $panel; }
    #error { height: auto; padding: 0 1; background: $error 20%; color: $error; display: none; }
    #empty { width: 100%; height: 1fr; content-align: center middle; color: $text-muted; display: none; }
    TabbedContent { height: 1fr; }
    TabPane { padding: 0; }
    .effort { padding: 0 1; }
    #goal { margin-top: 1; color: $text-muted; }
    #stepper { margin-top: 1; }
    #progress-label { margin-top: 1; color: $text-muted; }
    #progress { height: 1; }
    #progress Bar { width: 1fr; }
    #status-tabs { height: auto; margin-top: 1; }
    .status-row { height: 1; }
    .status-tab { width: auto; height: 1; margin-right: 1; color: $text-muted; }
    .status-tab.selected { color: $text; text-style: bold reverse; }
    #tasks { height: auto; max-height: 16; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; background: $surface; }
    #filter { height: 1; margin-top: 1; padding: 0 1; border: none; background: $panel; }
    #filter:focus { border: none; background: $panel; }
    #tasks-empty { height: auto; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; color: $text-muted; }
    #needs-you { height: auto; margin-top: 1; border: round $warning; border-title-color: $warning; padding: 0 1; }
    #activity { height: auto; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; }
    """
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        ("q", "quit", "quit"),
        Binding("tab", "next_effort", "switch", priority=True),
        Binding("shift+tab", "previous_effort", "previous", show=False, priority=True),
        Binding("r", "refresh", "refresh", show=False),
        Binding("c", "copy_slug", "copy"),
        Binding("enter", "open_task", "open"),
        Binding("p", "open_phase", "phase"),
        Binding("slash", "filter", "filter"),
        Binding("1", "status_tab('active')", "status", key_display="1-7"),
        Binding("2", "status_tab('running')", "running", show=False),
        Binding("3", "status_tab('ready')", "ready", show=False),
        Binding("4", "status_tab('waiting')", "waiting", show=False),
        Binding("5", "status_tab('needs')", "needs", show=False),
        Binding("6", "status_tab('done')", "done", show=False),
        Binding("7", "status_tab('all')", "all", show=False),
        Binding("escape", "clear_filter", "clear filter", show=False),
    ]

    def __init__(self, target: artifact_store.Target, interval: float = 2.0) -> None:
        super().__init__()
        self.target = target
        self.interval = interval
        self.snapshot: model.Snapshot | None = None
        self.token: str | None = None
        self.loaded_at = 0.0
        self.panes: dict[str, EffortPane] = {}
        self.filters: dict[str, TaskFilter] = {}

    def compose(self) -> ComposeResult:
        yield Static(id="header")
        yield Static(id="error")
        yield Static(id="empty")
        yield TabbedContent(id="efforts")
        yield Footer(compact=True)

    def on_mount(self) -> None:
        self.query_one("#header", Static).update(header_text(self.target, None, palette_from(self.get_css_variables())))
        self.query_one("#empty", Static).update(f"No live efforts in {self.target.store}")
        for tabs in self.query(ContentTabs):
            tabs.can_focus = False
        self.set_interval(self.interval, self.poll)
        self.reload()

    def focus_tasks(self) -> None:
        pane = self.active_pane()
        if pane is None or isinstance(self.screen, (TaskDetailScreen, PhaseDetailScreen, CommitScreen)):
            return
        table = pane.query_one("#tasks", DataTable)
        if table.display:
            table.focus(scroll_visible=False)

    def action_scroll_pane(self, where: str) -> None:
        pane = self.active_pane()
        if pane is not None:
            getattr(pane, f"scroll_{where}")(animate=False)

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if not isinstance(self.focused, Input):
            self.call_after_refresh(self.focus_tasks)

    def poll(self) -> None:
        try:
            token = model.change_token(self.target)
        except OSError:
            return
        if token != self.token or time.monotonic() - self.loaded_at > REDRAW_SECONDS:
            self.reload()
        for screen in self.screen_stack:
            if isinstance(screen, (TaskDetailScreen, PhaseDetailScreen)):
                screen.poll(token)

    def action_copy_slug(self) -> None:
        screen = self.screen
        if isinstance(screen, TaskDetailScreen):
            name = screen.detail.subject if screen.detail is not None else None
        elif isinstance(screen, PhaseDetailScreen):
            name = screen.phase_subject
        else:
            name = self.cursor_subject()
        if name:
            self.copy_to_clipboard(name)
            self.notify(f"Copied {name}", timeout=2)

    def cursor_subject(self) -> str | None:
        pane = self.active_pane()
        table = pane.query_one("#tasks", DataTable) if pane is not None else None
        if table is None or not table.row_count or self.snapshot is None:
            return None
        key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        return next((t.subject for v in self.snapshot.efforts for t in v.tasks if t.id == key), None)

    def action_refresh(self) -> None:
        self.reload()
        for screen in self.screen_stack:
            if isinstance(screen, (TaskDetailScreen, PhaseDetailScreen)):
                screen.load()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if isinstance(self.screen, CommitScreen):
            return action == "quit"
        detail = isinstance(self.screen, (TaskDetailScreen, PhaseDetailScreen))
        if detail and action in (
            "next_effort", "previous_effort", "open_task", "open_phase", "filter", "status_tab", "step_status_tab", "clear_filter",
        ):
            return False
        if action == "clear_filter":
            return self.active_filter().active
        return True

    def active_pane(self) -> EffortPane | None:
        pane = self.query_one("#efforts", TabbedContent).active_pane
        return pane.query_one(EffortPane) if pane is not None else None

    def active_filter(self) -> TaskFilter:
        pane = self.active_pane()
        return self.filters.get(pane.effort, TaskFilter()) if pane is not None else TaskFilter()

    def repaint_pane(self, pane: EffortPane) -> None:
        if self.snapshot is None:
            return
        for view in self.snapshot.efforts:
            if view.effort == pane.effort:
                pane.fill_tasks(view, self.size.width, pane.inner, palette_from(self.get_css_variables()))

    def action_filter(self) -> None:
        pane = self.active_pane()
        if pane is None:
            return
        box = pane.query_one("#filter", Input)
        box.value = self.filters.get(pane.effort, TaskFilter()).text
        box.display = True
        box.focus()
        box.cursor_position = len(box.value)

    def action_status_tab(self, name: str) -> None:
        self.select_status_tab(name)

    def action_step_status_tab(self, delta: int) -> None:
        names = [name for name, _, _ in STATUS_TABS]
        current = self.active_filter().tab
        self.select_status_tab(names[(names.index(current) + delta) % len(names)])

    def select_status_tab(self, name: str) -> None:
        pane = self.active_pane()
        if pane is None or isinstance(self.focused, Input):
            return
        self.filters.setdefault(pane.effort, TaskFilter()).tab = name
        self.repaint_pane(pane)
        pane.mark_status_tab(name)
        self.focus_tasks()

    def clear_filter(self) -> None:
        pane = self.active_pane()
        if pane is None:
            return
        self.filters.setdefault(pane.effort, TaskFilter()).text = ""
        self.close_filter(pane)
        self.repaint_pane(pane)

    def action_clear_filter(self) -> None:
        self.clear_filter()

    def close_filter(self, pane: EffortPane) -> None:
        box = pane.query_one("#filter", Input)
        box.display = False
        box.value = ""
        if box.has_focus:
            pane.query_one("#tasks", DataTable).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        pane = event.input.query_ancestor(EffortPane)
        if event.input.display and event.value != self.filters.get(pane.effort, TaskFilter()).text:
            self.filters.setdefault(pane.effort, TaskFilter()).text = event.value
            self.repaint_pane(pane)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        pane = event.input.query_ancestor(EffortPane)
        event.input.display = False
        pane.query_one("#tasks", DataTable).focus()

    def activate(self, key: str | None) -> None:
        if key is None:
            return
        if key == FOLD_KEY or key.startswith(PHASE_PREFIX):
            self.toggle_section(key)
        else:
            self.open_task(key)

    def toggle_section(self, key: str) -> None:
        pane = self.active_pane()
        row = pane.sections.get(key) if pane is not None else None
        if pane is None or row is None:
            return
        self.filters.setdefault(pane.effort, TaskFilter()).sections[key] = not row.expanded
        self.repaint_pane(pane)

    def cursor_key(self) -> str | None:
        pane = self.active_pane()
        table = pane.query_one("#tasks", DataTable) if pane is not None else None
        if table is None or not table.row_count:
            return None
        return table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value

    def action_open_phase(self) -> None:
        pane = self.active_pane()
        key = self.cursor_key()
        if pane is None or key is None or key == FOLD_KEY or self.snapshot is None:
            return
        if key.startswith(PHASE_PREFIX):
            subject = key[len(PHASE_PREFIX):]
        else:
            subject = next((t.phase for v in self.snapshot.efforts for t in v.tasks if t.id == key), "")
        if subject and not isinstance(self.screen, (TaskDetailScreen, PhaseDetailScreen)):
            self.push_screen(PhaseDetailScreen(self.target, pane.effort, subject))

    def open_task(self, task_id: str | None) -> None:
        if task_id and not isinstance(self.screen, TaskDetailScreen):
            self.push_screen(TaskDetailScreen(self.target, task_id))

    def action_open_task(self) -> None:
        self.activate(self.cursor_key())

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.activate(event.row_key.value)

    def action_next_effort(self) -> None:
        self.step_effort(1)

    def action_previous_effort(self) -> None:
        self.step_effort(-1)

    def step_effort(self, delta: int) -> None:
        tabs = self.query_one("#efforts", TabbedContent)
        ids = [pane.id for pane in tabs.query(TabPane)]
        for pane in self.panes.values():
            pane.query_one("#filter", Input).display = False
        if ids and tabs.active in ids:
            tabs.active = ids[(ids.index(tabs.active) + delta) % len(ids)]

    @work(thread=True, exclusive=True)
    def reload(self) -> None:
        self.loaded_at = time.monotonic()
        try:
            snapshot = model.load_snapshot(self.target, datetime.now(timezone.utc))
        except model.ModelError as exc:
            self.call_from_thread(self.show_error, str(exc))
            return
        self.token = snapshot.token
        self.call_from_thread(self.apply, snapshot)

    def show_error(self, message: str) -> None:
        banner = self.query_one("#error", Static)
        banner.update(Text(message.splitlines()[0] if message else "error", no_wrap=True, overflow="ellipsis"))
        banner.display = True

    async def apply(self, snapshot: model.Snapshot) -> None:
        self.snapshot = snapshot
        self.query_one("#error", Static).display = False
        tabs = self.query_one("#efforts", TabbedContent)
        names = [view.effort for view in snapshot.efforts]
        for name in [name for name in self.panes if name not in names]:
            await tabs.remove_pane(f"effort-{slug(name)}")
            del self.panes[name]
        for view in snapshot.efforts:
            if view.effort not in self.panes:
                pane = EffortPane(view.effort)
                self.panes[view.effort] = pane
                await tabs.add_pane(TabPane(tab_label(view), pane, id=f"effort-{slug(view.effort)}"))
        self.query_one("#empty", Static).display = not names
        tabs.display = bool(names)
        self.paint()
        if self.focused is None:
            self.focus_tasks()
            self.call_after_refresh(self.focus_tasks)

    def paint(self, width: int | None = None) -> None:
        snapshot = self.snapshot
        if snapshot is None:
            return
        width = width or self.size.width
        colors = palette_from(self.get_css_variables())
        tabs = self.query_one("#efforts", TabbedContent)
        self.query_one("#header", Static).update(header_text(self.target, snapshot.generated_at, colors, width))
        for view in snapshot.efforts:
            tabs.get_tab(f"effort-{slug(view.effort)}").label = Text(tab_label(view))
            self.panes[view.effort].show(view, snapshot.generated_at, width, colors)

    def on_resize(self, event: events.Resize) -> None:
        self.paint(event.size.width)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="dashboard_app")
    parser.add_argument("--once", action="store_true", help="print one plain-text frame and exit")
    parser.add_argument("--interval", type=float, default=2.0, metavar="S", help="seconds between change checks")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    target = artifact_store.resolve(Path.cwd())
    if target.store is None or target.contract is None:
        print(f"No artifact store found for {target.root}")
        return 1
    if args.once:
        tty = sys.stdout.isatty()
        console = Console(
            width=None if tty else 100, no_color=not tty, force_terminal=tty, highlight=False, soft_wrap=False,
        )
        try:
            snapshot = model.load_snapshot(target)
        except model.ModelError as exc:
            print(f"dashboard: {exc}")
            return 1
        render_once(target, snapshot, console)
        return 0
    DashboardApp(target, interval=args.interval).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
