"""Textual dashboard for the project's artifact store. `--once` prints one plain-text frame."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dashboard import artifact_store
from dashboard import gates
from dashboard import model
from dashboard import selection
from dashboard.commit import CommitScreen
from dashboard.landing import Landing
from dashboard.display import (
    ANSI_PALETTE, PHASE_GLYPH, REDRAW_SECONDS, WIDE, clip, palette_from, relative_time, slug,
)
from dashboard.phase_screen import PhaseScreen
from dashboard.task_detail import TaskDetailScreen
from dashboard.tasks import (
    FOLD_KEY, PHASE_PREFIX, STATUS_TABS, SectionRow, TaskFilter, TaskTable, counts, empty_text, phase_progress,
    section_cells, section_rows, task_cells, task_columns, tasks_title, tab_tasks, title_width, visible_tasks,
)
from rich.console import Console, Group
from rich.table import Table
from rich.text import Text
from textual import events, work
from textual.binding import Binding
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets._tabbed_content import ContentTabs
from textual.widgets import (
    DataTable, Footer, Input, Markdown, OptionList, ProgressBar, Static, TabbedContent, TabPane,
)
from textual.widgets.option_list import Option

RESULT_GLYPH = {"pass": "✓", "fail": "✗"}
NEEDS_TEXT_TITLE = {
    "blocking-question": "Question", "open-question": "Question", "needs-human": "Claim", "unsigned-check": "Check",
    "loop-route": "Assessment", "integration": "Report", "merge-branch": "Branch",
}
# Compat for tests and task_detail that still import the old name.
PhaseDetailScreen = PhaseScreen


def effort_progress(view: model.EffortView) -> tuple[int, int]:
    return sum(phase.done for phase in view.phases), sum(phase.total for phase in view.phases)


def progress_label(view: model.EffortView, selected_phase: str | None) -> str:
    if not view.phases:
        return ""
    phase_done, phase_total = phase_progress(view, selected_phase) if selected_phase is not None else effort_progress(view)
    effort_done, effort_total = effort_progress(view)
    if selected_phase is None:
        return f"{effort_done} of {effort_total} tasks"
    return f"{phase_done}/{phase_total} tasks · {effort_done}/{effort_total} effort"



def _needs_detail(item: model.NeedsYouItem) -> str | None:
    if item.kind == "loop-route":
        return " ".join(part for part in (item.requirement, item.status, item.next) if part)
    if item.kind == "integration":
        return " ".join(part for part in (item.phase, item.result) if part)
    return None


def needs_lines(view: model.EffortView, colors: dict[str, str], width: int = 100) -> list[Text]:
    lines = []
    for item in view.needs_you:
        color = colors["error"] if item.kind == "blocking-question" else colors["warning"]
        line = Text(no_wrap=True, overflow="ellipsis")
        label = gates.action_label(item, view)
        line.append(label, style=color)
        detail = _needs_detail(item)
        shown = gates.item_text(item, view)
        if detail is None:
            room = max(width - len(label) - len(item.subject) - 4, 10)
            line.append(f" {clip(shown, room)}")
            line.append(f"  {clip(item.subject, max(width - len(label) - 2, 10))}", style=colors["muted"])
        else:
            line.append(" " + clip(detail, max(width - len(label) - 1, 10)))
        lines.append(line)
    return lines


def next_step_text(view: model.EffortView, landing: dict[str, Landing], colors: dict[str, str]) -> Text:
    step = gates.next_step(view, landing)
    text = Text(no_wrap=True, overflow="ellipsis")
    if step:
        text.append(f"next: {step}")
    if view.position:
        if text.plain:
            text.append("  ")
        text.append(view.position, style=colors["muted"])
    return text


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
    label = f"⚠ {view.effort}" if view.needs_you else view.effort
    if view.release_ready:
        label += " · Release ready"
    return label



def render_once(target: artifact_store.Target, snapshot: model.Snapshot, console: Console) -> None:
    colors = ANSI_PALETTE
    landings = gates.landings_for_snapshot(target.root, snapshot)
    snapshot = gates.apply_landing_needs(snapshot, landings)
    console.print(header_text(target, snapshot.generated_at, colors))
    if not snapshot.efforts:
        console.print(f"\nNo live efforts in {target.store}")
    for view in snapshot.efforts:
        console.print()
        console.rule(Text(tab_label(view), style="dim" if view.finished else "bold"), align="left")
        console.print(Text(view.goal, style=colors["muted"]))
        landing = landings.get(view.effort, {})
        selected = selection.default_phase(view)
        step = next_step_text(view, landing, colors)
        if step.plain:
            console.print(step)
        suffix = ""
        if selected is not None and selected in landing:
            suffix = gates.landing_summary(landing[selected])
        console.print(selection.selector_text(view, selected, colors, console.width, landing_suffix=suffix))
        strip = (
            selection.wave_strip(view, selected, console.width, colors, snapshot.generated_at)
            if selected is not None else Text()
        )
        if strip.plain:
            console.print(strip)
        label = progress_label(view, selected)
        if label:
            console.print(Text(label, style=colors["muted"]))
        scoped = selection.scoped(view, selected)
        tally = counts(scoped)
        console.print("   ".join(f"{word} ({tally[name]})" for name, word, _key in STATUS_TABS))
        if scoped.tasks:
            columns = ["status", "task", "phase", "assignee"] if console.width >= WIDE else task_columns(console.width)
            table = Table(box=None, pad_edge=False, header_style=colors["muted"])
            for name in columns:
                table.add_column(name, no_wrap=name != "task", overflow="ellipsis")
            for task in scoped.tasks:
                table.add_row(*task_cells(task, columns, console.width, colors, snapshot.generated_at))
            console.print(Group(Text(), table))
        if view.needs_you:
            console.print(Text(f"\nNeeds you {len(view.needs_you)}", style=colors["warning"]))
            for line in needs_lines(view, colors):
                console.print(line)
        lines = selection.activity_lines(view, snapshot.generated_at, colors)
        if lines:
            console.print(Text("\nActivity", style=colors["muted"]))
            for line in lines:
                console.print(line)



class PhaseSelector(Static):
    def on_click(self, event: events.Click) -> None:
        target = event.style.meta.get("target")
        pane = self.query_ancestor(EffortPane)
        if pane is None or target is None:
            return
        if target == "picker":
            self.app.push_screen(PhasePickerScreen(pane.effort))
            return
        if target == "all":
            self.app.select_phase(pane.effort, None)
            return
        if isinstance(target, str) and target.startswith("evidence:"):
            self.app.select_phase(pane.effort, target[len("evidence:"):])
            self.app.action_open_phase("evidence")
            return
        if isinstance(target, str) and target.startswith("phase:"):
            self.app.select_phase(pane.effort, target[len("phase:"):])
            return
        self.app.select_phase(pane.effort, target)


class EffortPane(VerticalScroll):
    def __init__(self, effort: str) -> None:
        super().__init__(classes="effort")
        self.effort = effort
        self.sections: dict[str, SectionRow] = {}

    def compose(self) -> ComposeResult:
        yield Static(id="goal")
        yield Static(id="next-step")
        yield PhaseSelector(id="stepper")
        yield Static(id="waves")
        yield Static(id="progress-label")
        yield ProgressBar(id="progress", show_eta=False, show_percentage=False)
        with Container(id="status-tabs"):
            for name, label, key in STATUS_TABS:
                yield StatusTab(name, label, key)
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
        needs = NeedsList(id="needs-you")
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
        landing = self.app.landings.get(self.effort, {})
        step = next_step_text(view, landing, colors)
        step_widget = self.query_one("#next-step", Static)
        step_widget.update(step)
        step_widget.display = bool(step.plain)
        has_phases = bool(view.phases)
        selector_widget = self.query_one("#stepper", Static)
        waves_widget = self.query_one("#waves", Static)
        selector_widget.display = has_phases
        waves_widget.display = has_phases
        selected = selection.resolve_selection(view, self.app.selections.get(self.effort, selection.PhaseSelection()))
        if has_phases:
            suffix = ""
            if selected is not None and selected in landing:
                suffix = gates.landing_summary(landing[selected])
            selector_widget.update(selection.selector_text(view, selected, colors, inner, landing_suffix=suffix))
            strip = selection.wave_strip(view, selected, inner) if selected is not None else Text()
            waves_widget.update(strip)
            waves_widget.display = bool(strip.plain)
        self.query_one("#progress-label", Static).update(progress_label(view, selected))
        bar = self.query_one("#progress", ProgressBar)
        bar.display = has_phases
        self.query_one("#progress-label").display = has_phases
        if has_phases:
            if selected is None:
                done, total = effort_progress(view)
            else:
                done, total = phase_progress(view, selected)
            bar.update(total=max(total, 1), progress=done)
        scoped = selection.scoped(view, selected)
        tally = counts(scoped)
        selected_tab = self.app.filters.get(self.effort, TaskFilter()).tab
        tabs = list(self.query(StatusTab))
        for tab in tabs:
            tab.show(tally[tab.tab_name], tab.tab_name == selected_tab)
        widths = [tab.label_width() for tab in tabs]
        self.query_one("#status-tabs").styles.grid_size_columns = tab_columns(widths, inner)
        self.fill_tasks(scoped, view, now, width, inner, colors, selected)
        self.query_one("#needs-you", NeedsList).fill(view, colors, inner - 4)
        self.fill_panel("#activity", selection.activity_lines(view, now, colors, inner - 4))

    def mark_status_tab(self, selected: str) -> None:
        for tab in self.query(StatusTab):
            tab.set_class(tab.tab_name == selected, "selected")

    def on_resize(self) -> None:
        self.refit()

    def watch_show_vertical_scrollbar(self) -> None:
        self.call_after_refresh(self.refit)

    def refit(self) -> None:
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

    def fill_tasks(
        self, scoped: model.EffortView, full: model.EffortView, now: datetime, width: int, room: int,
        colors: dict[str, str], selected_phase: str | None,
    ) -> None:
        table = self.query_one("#tasks", DataTable)
        task_filter = self.app.filters.get(self.effort, TaskFilter())
        pool = tab_tasks(scoped, task_filter.tab)
        tasks = visible_tasks(pool, task_filter)
        title = tasks_title(len(tasks), len(pool), task_filter)
        table.display = bool(tasks)
        table.border_title = title
        empty = self.query_one("#tasks-empty", Static)
        empty.display = not tasks
        empty.border_title = title
        empty.update(empty_text(full, task_filter))
        focused = table.has_focus
        keep = None
        if table.row_count:
            keep = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        table.clear(columns=True)
        columns = task_columns(width)
        for name in columns:
            table.add_column(name, key=name)
        room = title_width(columns, room - 4, tasks, now)
        show_empty = task_filter.tab == "all" and not task_filter.text
        self.sections = {}
        for row in section_rows(full, tasks, task_filter.sections, show_empty, selected_phase):
            self.sections[row.key] = row
            if row.task is None:
                table.add_row(*section_cells(row, columns, room, colors), key=row.key)
            else:
                grouped = selected_phase is None and row.task.phase in {phase.subject for phase in full.phases}
                table.add_row(*task_cells(row.task, columns, room, colors, now, "  " if grouped else ""), key=row.key)
        if keep is not None and keep in table.rows:
            table.move_cursor(row=table.get_row_index(keep))
        if focused:
            table.focus(scroll_visible=False)


def tab_columns(widths: list[int], room: int) -> int:
    for columns in (6, 3, 2):
        rows = [widths[start:start + columns] for start in range(0, len(widths), columns)]
        if sum(max(column) for column in zip(*rows)) + columns - 1 <= room:
            return columns
    return 1


class StatusTab(Static):
    def __init__(self, name: str, label: str, key: str) -> None:
        super().__init__(id=f"status-{name}", classes="status-tab")
        self.tab_name = name
        self.tab_label = label
        self.tab_key = key
        self.text = Text()

    def show(self, number: int, selected: bool) -> None:
        word = "bold reverse" if selected else ""
        self.text = Text.assemble((self.tab_label, word), (f" ({number})", "dim"))
        self.update(self.text)
        self.set_class(selected, "selected")

    def label_width(self) -> int:
        return self.text.cell_len

    def on_click(self) -> None:
        self.app.select_status_tab(self.tab_name)


class FilterInput(Input):
    BINDINGS = [Binding("escape", "cancel", "clear", show=False)]

    def action_cancel(self) -> None:
        self.app.clear_filter()


class NeedsList(OptionList):
    BINDINGS = [
        Binding("escape", "app.leave_needs", "back", show=False),
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
    ]

    def __init__(self, id: str) -> None:
        super().__init__(id=id)
        self.items: list[model.NeedsYouItem] = []

    def fill(self, view: model.EffortView, colors: dict[str, str], width: int) -> None:
        kept = self.highlighted_item()
        index = self.highlighted
        self.items = list(view.needs_you)
        self.border_title = f"Needs you {len(self.items)}"
        self.display = bool(self.items)
        self.clear_options()
        self.add_options(Option(line, id=item.id) for item, line in zip(self.items, needs_lines(view, colors, width)))
        ids = [item.id for item in self.items]
        if kept is not None and kept.id in ids:
            self.highlighted = ids.index(kept.id)
        elif index is not None and ids:
            self.highlighted = min(index, len(ids) - 1)
        if not self.items and self.has_focus:
            self.app.leave_needs()

    def highlighted_item(self) -> model.NeedsYouItem | None:
        if self.highlighted is None or self.highlighted >= len(self.items):
            return None
        return self.items[self.highlighted]



class NeedsYouDetailScreen(Screen[None]):
    CSS = """
    #needs-bar { height: 1; padding: 0 1; background: $panel; }
    #needs-error { height: auto; padding: 0 1; background: $warning 20%; color: $warning; display: none; }
    #needs-detail { padding: 0 1; scrollbar-gutter: stable; }
    #needs-title { margin-top: 1; text-style: bold; }
    .needs-panel { height: auto; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; }
    .needs-panel Markdown { margin: 0; padding: 0; background: transparent; }
    .needs-panel Markdown > MarkdownBlock { margin: 1 0 0 0; }
    .needs-panel Markdown > MarkdownHeader { margin: 0; }
    .needs-panel Markdown > MarkdownBlock:first-child { margin-top: 0; }
    """
    AUTO_FOCUS = "#needs-detail"
    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("c", "app.copy_slug", "copy prompt"),
        Binding("r", "app.refresh", "refresh"),
    ]

    def __init__(self, item: model.NeedsYouItem, effort: str) -> None:
        super().__init__()
        self.item = item
        self.effort = effort
        self.loaded = False

    def compose(self) -> ComposeResult:
        yield Static(id="needs-bar")
        yield Static(id="needs-error")
        with VerticalScroll(id="needs-detail"):
            yield Static(id="needs-title")
            yield Static(id="needs-chips")
            yield Vertical(Markdown(), id="needs-text", classes="needs-panel")
            body = Vertical(Markdown(), id="needs-body", classes="needs-panel")
            body.border_title = "Body"
            yield body
        yield Footer()

    async def on_mount(self) -> None:
        await self.show(self.item)

    def action_back(self) -> None:
        self.app.pop_screen()
        self.app.call_after_refresh(self.app.refocus)

    async def follow(self, snapshot: model.Snapshot) -> None:
        found = next((i for v in snapshot.efforts for i in v.needs_you if i.id == self.item.id), None)
        if found is None:
            banner = self.query_one("#needs-error", Static)
            banner.update(Text("No longer needs you", no_wrap=True, overflow="ellipsis"))
            banner.display = True
        elif found != self.item or not self.loaded:
            await self.show(found)

    async def show(self, item: model.NeedsYouItem) -> None:
        if not self.is_attached:
            return
        colors = palette_from(self.app.get_css_variables())
        self.item = item
        self.query_one("#needs-error", Static).display = False
        bar = Text(no_wrap=True, overflow="ellipsis")
        bar.append(item.subject, style="bold")
        if self.effort != item.subject:
            bar.append(f"  {self.effort}", style=colors["muted"])
        self.query_one("#needs-bar", Static).update(bar)
        self.query_one("#needs-title", Static).update(Text(item.subject, style="bold"))
        color = colors["error"] if item.kind == "blocking-question" else colors["warning"]
        view = self.app.effort_view(self.effort)
        label = gates.action_label(item, view) if view is not None else item.kind
        chips = Text.assemble((label, color), "  ", (item.record_type, colors["muted"]))
        self.query_one("#needs-chips", Static).update(chips)
        self.query_one("#needs-text").border_title = NEEDS_TEXT_TITLE.get(item.kind, "Detail")
        await self.query_one("#needs-text Markdown", Markdown).update(item.text)
        self.query_one("#needs-body").display = bool(item.body.strip())
        await self.query_one("#needs-body Markdown", Markdown).update(item.body.strip())
        self.loaded = True


class _PickerCancel:
    pass


PICKER_CANCEL = _PickerCancel()


class KeyHelpScreen(Screen[None]):
    BINDINGS = [
        Binding("escape", "close", "close", show=False),
        Binding("question_mark", "close", "close", show=False),
    ]

    def __init__(self, text: str) -> None:
        super().__init__(name="_help")
        self.help_text = text

    def compose(self) -> ComposeResult:
        yield Static(self.help_text, id="key-help", markup=False)

    def action_close(self) -> None:
        self.dismiss()


class PhasePickerScreen(Screen[str | None]):
    CSS = """
    #picker-bar { height: 1; padding: 0 1; background: $panel; }
    #picker-input { height: 1; margin-top: 1; }
    #picker-options { height: 1fr; border: round $panel; }
    """
    BINDINGS = [
        Binding("escape", "escape", "close", show=False),
    ]

    def __init__(self, effort: str) -> None:
        super().__init__()
        self.effort = effort

    def compose(self) -> ComposeResult:
        yield Static("Select phase", id="picker-bar")
        yield Input(placeholder="filter phases", id="picker-input")
        yield OptionList(id="picker-options")

    def on_mount(self) -> None:
        self._fill("")
        self.query_one("#picker-input", Input).focus()

    def _fill(self, needle: str) -> None:
        options = self.query_one("#picker-options", OptionList)
        options.clear_options()
        view = self._view()
        if view is None:
            return
        needle = needle.lower()
        choices: list[tuple[str | None, str]] = [(None, "All phases")]
        for phase in sorted(view.phases, key=lambda p: (p.ordinal, p.subject)):
            line = f"{phase.ordinal} {PHASE_GLYPH[phase.state]} {phase.title or phase.subject} {phase.done}/{phase.total}"
            if needle and needle not in line.lower() and needle not in phase.subject.lower():
                continue
            choices.append((phase.subject, line))
        for subject, line in choices:
            options.add_option(Option(line, id=subject if subject is not None else "__all__"))
        if options.option_count:
            options.highlighted = 0

    def _view(self) -> model.EffortView | None:
        app = self.app
        if not isinstance(app, DashboardApp) or app.snapshot is None:
            return None
        return next((v for v in app.snapshot.efforts if v.effort == self.effort), None)

    def on_input_changed(self, event: Input.Changed) -> None:
        self._fill(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        options = self.query_one("#picker-options", OptionList)
        if options.highlighted is None or not options.option_count:
            return
        option = options.get_option_at_index(options.highlighted)
        self.dismiss(None if option.id == "__all__" else option.id)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        option = event.option
        self.dismiss(None if option.id == "__all__" else option.id)

    def action_escape(self) -> None:
        self.dismiss(PICKER_CANCEL)


class DashboardApp(App[None]):
    CSS = """
    #header { height: 1; padding: 0 1; background: $panel; layout: horizontal; }
    #header-path { width: 1fr; }
    #header-finished { width: auto; color: $text-muted; }
    #error { height: auto; padding: 0 1; background: $error 20%; color: $error; display: none; }
    #empty { width: 100%; height: 1fr; content-align: center middle; color: $text-muted; display: none; }
    TabbedContent { height: 1fr; }
    TabPane { padding: 0; }
    #efforts Tab.finished { text-style: dim; }
    .effort { padding: 0 1; }
    #goal { margin-top: 1; color: $text-muted; }
    #next-step { margin-top: 1; }
    #stepper { margin-top: 1; }
    #waves { height: auto; margin-top: 1; color: $text-muted; }
    #progress-label { margin-top: 1; color: $text-muted; }
    #progress { height: 1; }
    #progress Bar { width: 1fr; }
    #status-tabs { layout: grid; grid-size: 6; grid-columns: auto; grid-rows: 1; grid-gutter: 0 1; height: auto; margin-top: 1; }
    .status-tab { width: auto; height: 1; color: $text-muted; }
    .status-tab.selected { color: $text; }
    #tasks { height: auto; max-height: 16; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; background: $surface; }
    #filter { height: 1; margin-top: 1; padding: 0 1; border: none; background: $panel; }
    #filter:focus { border: none; background: $panel; }
    #tasks-empty { height: auto; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; color: $text-muted; }
    #needs-you { height: auto; max-height: 12; margin-top: 1; border: round $warning; border-title-color: $warning; padding: 0 1; background: transparent; }
    #needs-you:focus { border: round $warning; background-tint: $foreground 0%; }
    #needs-you > .option-list--option-highlighted { background: transparent; color: $foreground; text-style: none; }
    #needs-you:focus > .option-list--option-highlighted { background: $block-cursor-background; color: $block-cursor-foreground; text-style: $block-cursor-text-style; }
    #activity { height: auto; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; }
    """
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        ("q", "quit", "quit"),
        Binding("tab", "next_effort", "switch", priority=True),
        Binding("shift+tab", "previous_effort", "previous", show=False, priority=True),
        Binding("r", "refresh", "refresh", show=False),
        Binding("c", "copy_slug", "copy"),
        Binding("enter", "open_task", "open", show=False),
        Binding("p", "open_phase('overview')", "phase"),
        Binding("s", "open_phase('spec')", "spec", show=False),
        Binding("e", "open_phase('evidence')", "evidence", show=False),
        Binding("n", "focus_needs", "needs"),
        Binding("slash", "filter", "filter"),
        Binding("1", "status_tab('active')", "status", key_display="1-6"),
        Binding("2", "status_tab('running')", "running", show=False),
        Binding("3", "status_tab('ready')", "ready", show=False),
        Binding("4", "status_tab('waiting')", "waiting", show=False),
        Binding("5", "status_tab('done')", "done", show=False),
        Binding("6", "status_tab('all')", "all", show=False),
        Binding("[", "select_phase(-1)", "previous phase", show=False),
        Binding("]", "select_phase(1)", "next phase", show=False),
        Binding("P", "open_picker", "phase picker", show=False),
        Binding("f", "toggle_finished", "toggle finished", show=False),
        Binding("question_mark", "toggle_help", "help", show=False),
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
        self.selections: dict[str, selection.PhaseSelection] = {}
        self.show_finished = False
        self.landings: dict[str, dict[str, Landing]] = {}
        self._landing_token: str | None = None
        self.seen_needs: set[str] = set()
        self._seen_needs_ready = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="header"):
            yield Static(id="header-path")
            yield Static(id="header-finished")
        yield Static(id="error")
        yield Static(id="empty")
        yield TabbedContent(id="efforts")
        yield Footer(compact=True)

    def on_mount(self) -> None:
        self.query_one("#header-path", Static).update(header_text(self.target, None, palette_from(self.get_css_variables())))
        self.query_one("#empty", Static).update(f"No live efforts in {self.target.store}")
        for tabs in self.query(ContentTabs):
            tabs.can_focus = False
        self.set_interval(self.interval, self.poll)
        self.reload()

    def focus_tasks(self) -> None:
        pane = self.active_pane()
        if pane is None or isinstance(self.screen, DETAIL_SCREENS) or not pane.query("#tasks"):
            return
        table = pane.query_one("#tasks", DataTable)
        if table.display:
            table.focus(scroll_visible=False)

    def action_focus_needs(self) -> None:
        pane = self.active_pane()
        needs = pane.query_one("#needs-you", NeedsList) if pane is not None else None
        if needs is None or not needs.display:
            return
        if needs.highlighted is None:
            needs.highlighted = 0
        needs.focus()

    def action_leave_needs(self) -> None:
        self.leave_needs()

    def leave_needs(self) -> None:
        self.focus_tasks()
        if isinstance(self.focused, NeedsList):
            self.set_focus(None)

    def refocus(self) -> None:
        if self.focused is None or not self.focused.display:
            self.focus_tasks()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        needs = event.option_list
        if not isinstance(needs, NeedsList) or event.option_index >= len(needs.items):
            return
        item = needs.items[event.option_index]
        if item.kind == "loop-route" and item.phase and item.requirement:
            from dashboard.requirement_detail import RequirementDetailScreen

            event.stop()
            self.push_screen(RequirementDetailScreen(
                self.target, needs.query_ancestor(EffortPane).effort, item.phase, item.requirement,
            ))
            return
        if item.task_id:
            self.open_task(item.task_id)
        elif not isinstance(self.screen, DETAIL_SCREENS):
            self.push_screen(NeedsYouDetailScreen(item, needs.query_ancestor(EffortPane).effort))

    def action_scroll_pane(self, where: str) -> None:
        pane = self.active_pane()
        if pane is not None:
            getattr(pane, f"scroll_{where}")(animate=False)

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if self.screen_stack and not isinstance(self.focused, Input):
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

    def effort_view(self, effort: str) -> model.EffortView | None:
        if self.snapshot is None:
            return None
        return next((view for view in self.snapshot.efforts if view.effort == effort), None)

    def _needs_copy_focus(self) -> bool:
        return isinstance(self.focused, NeedsList) or isinstance(self.screen, NeedsYouDetailScreen)

    def _refresh_copy_binding(self) -> None:
        description = "copy prompt" if self._needs_copy_focus() else "copy"
        self._bindings.key_to_bindings["c"] = [
            Binding("c", "copy_slug", description, show=True),
        ]
        self.refresh_bindings()

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        self._refresh_copy_binding()

    def on_descendant_blur(self, event: events.DescendantBlur) -> None:
        self.call_after_refresh(self._refresh_copy_binding)

    def action_copy_slug(self) -> None:
        screen = self.screen
        if isinstance(screen, TaskDetailScreen):
            name = screen.detail.subject if screen.detail is not None else None
        elif isinstance(screen, PhaseDetailScreen):
            name = screen.phase_subject
        elif isinstance(screen, NeedsYouDetailScreen):
            view = self.effort_view(screen.effort)
            name = gates.prompt(screen.item, view) if view is not None else screen.item.subject
        elif isinstance(self.focused, NeedsList):
            item = self.focused.highlighted_item()
            pane = self.focused.query_ancestor(EffortPane)
            view = self.effort_view(pane.effort) if pane is not None else None
            name = gates.prompt(item, view) if item is not None and view is not None else None
        else:
            name = self.cursor_subject()
        if name:
            self.copy_to_clipboard(name)
            shown = name if len(name) <= 60 else name[:57] + "..."
            self.notify(f"Copied {shown}", timeout=2)

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
        detail = isinstance(self.screen, (TaskDetailScreen, PhaseDetailScreen, NeedsYouDetailScreen))
        if detail and action in (
            "next_effort", "previous_effort", "open_task", "open_phase", "filter", "status_tab", "step_status_tab", "clear_filter",
            "focus_needs", "leave_needs", "select_phase", "open_picker", "toggle_finished",
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

    def show_effort(self, effort: str) -> None:
        if self.snapshot is None:
            return
        pane = self.panes.get(effort)
        view = next((item for item in self.snapshot.efforts if item.effort == effort), None)
        if pane is None or view is None:
            return
        pane.show(view, self.snapshot.generated_at, self.size.width, palette_from(self.get_css_variables()))

    def repaint_pane(self, pane: EffortPane) -> None:
        if self.snapshot is None:
            return
        for view in self.snapshot.efforts:
            if view.effort == pane.effort:
                selected = selection.resolve_selection(
                    view, self.selections.get(pane.effort, selection.PhaseSelection()),
                )
                scoped = selection.scoped(view, selected)
                pane.fill_tasks(
                    scoped, view, self.snapshot.generated_at, self.size.width, pane.inner,
                    palette_from(self.get_css_variables()), selected,
                )
                break

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
        if event.input.id != "filter":
            return
        pane = event.input.query_ancestor(EffortPane)
        if event.input.display and event.value != self.filters.get(pane.effort, TaskFilter()).text:
            self.filters.setdefault(pane.effort, TaskFilter()).text = event.value
            self.repaint_pane(pane)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "filter":
            return
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

    def action_open_phase(self, tab: str = "overview") -> None:
        pane = self.active_pane()
        if pane is None or self.snapshot is None:
            return
        view = next((v for v in self.snapshot.efforts if v.effort == pane.effort), None)
        if view is None:
            return
        selected = selection.resolve_selection(view, self.selections.get(pane.effort, selection.PhaseSelection()))
        subject = selected
        if subject is None:
            key = self.cursor_key()
            if key is None or key == FOLD_KEY:
                return
            if key.startswith(PHASE_PREFIX):
                subject = key[len(PHASE_PREFIX):]
            else:
                subject = next((t.phase for v in self.snapshot.efforts for t in v.tasks if t.id == key), "")
        if not subject or isinstance(self.screen, DETAIL_SCREENS):
            return
        open_tab = tab
        if tab == "evidence":
            phase_row = next((p for p in view.phases if p.subject == subject), None)
            if phase_row is None or phase_row.evidence is None:
                open_tab = "overview"
        self.push_screen(PhaseScreen(self.target, pane.effort, subject, tab=open_tab))

    def select_phase(self, effort: str, target: str | None) -> None:
        pane = self.panes.get(effort)
        if pane is None or self.snapshot is None:
            return
        view = next((v for v in self.snapshot.efforts if v.effort == effort), None)
        if view is None or not view.phases:
            return
        self.selections[effort] = selection.pick(view, target)
        self.show_effort(effort)

    def action_select_phase(self, delta: int) -> None:
        pane = self.active_pane()
        if pane is None or self.snapshot is None:
            return
        view = next((v for v in self.snapshot.efforts if v.effort == pane.effort), None)
        if view is None or not view.phases:
            return
        self.selections[pane.effort] = selection.step_selection(
            view, self.selections.get(pane.effort, selection.PhaseSelection()), delta,
        )
        self.show_effort(pane.effort)

    def action_open_picker(self) -> None:
        pane = self.active_pane()
        if pane is None:
            return

        def on_pick(target: str | None | _PickerCancel) -> None:
            if isinstance(target, _PickerCancel):
                return
            self.select_phase(pane.effort, target)

        self.push_screen(PhasePickerScreen(pane.effort), callback=on_pick)

    async def action_toggle_finished(self) -> None:
        self.show_finished = not self.show_finished
        if self.snapshot is not None:
            await self.apply(self.snapshot)

    def _key_help(self) -> str:
        focused = self.focused
        blocks = ["Dashboard", *self._format_bindings(type(self))]
        if focused is not None and type(focused) is not DashboardApp:
            blocks.extend(["", type(focused).__name__, *self._format_bindings(type(focused))])
        return "\n".join(blocks)

    def _format_bindings(self, cls: type) -> list[str]:
        lines = []
        for binding in getattr(cls, "BINDINGS", []):
            if isinstance(binding, tuple):
                key = binding[0]
                description = binding[2] if len(binding) > 2 else binding[1]
            else:
                key = binding.key
                description = binding.description
            if key == "c" and cls is DashboardApp and self._needs_copy_focus():
                description = "copy prompt"
            lines.append(f"{key}  {description}")
        return lines

    def action_toggle_help(self) -> None:
        if isinstance(self.screen, KeyHelpScreen):
            self.pop_screen()
        else:
            self.push_screen(KeyHelpScreen(self._key_help()))

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
            tabs.screen.set_focus(None)
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

    @work(thread=True, exclusive=True, group="landing")
    def refresh_landing(self) -> None:
        snapshot = self.snapshot
        if snapshot is None:
            return
        root = self.target.root
        token = gates.landing_cache_token(root, snapshot)
        if token is not None and token == self._landing_token and self.landings:
            landings = self.landings
        else:
            landings = gates.landings_for_snapshot(root, snapshot)
            self._landing_token = token
        self.call_from_thread(self.apply_landing, landings)

    def apply_landing(self, landings: dict[str, dict[str, Landing]]) -> None:
        if not self.is_attached or self.snapshot is None or not self.screen_stack:
            return
        if not self.query("#header-path"):
            return
        self.landings = landings
        self.snapshot = gates.apply_landing_needs(self.snapshot, landings)
        self.paint()
        self._alert_new_needs(self.snapshot)

    def _alert_new_needs(self, snapshot: model.Snapshot) -> None:
        current = {item.id for view in snapshot.efforts for item in view.needs_you}
        if self._seen_needs_ready:
            for view in snapshot.efforts:
                for item in view.needs_you:
                    if item.id in self.seen_needs:
                        continue
                    self.bell()
                    label = gates.action_label(item, view)
                    self._tmux_needs_message(view.effort, label, item.subject)
        self.seen_needs |= current
        self._seen_needs_ready = True

    def _tmux_needs_message(self, effort: str, label: str, subject: str) -> None:
        if not os.environ.get("TMUX"):
            return
        message = f"{effort}: {label} {subject}"
        try:
            subprocess.run(
                ["tmux", "display-message", "-d", "4000", message],
                check=False, capture_output=True, timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return

    def show_error(self, message: str) -> None:
        banner = self.query_one("#error", Static)
        banner.update(Text(message.splitlines()[0] if message else "error", no_wrap=True, overflow="ellipsis"))
        banner.display = True

    async def apply(self, snapshot: model.Snapshot) -> None:
        if self.landings:
            snapshot = gates.apply_landing_needs(snapshot, self.landings)
        self.snapshot = snapshot
        if not self.is_attached or not self.screen_stack or not self.query("#header-path"):
            return
        self.query_one("#error", Static).display = False
        shown, hidden = selection.visible_efforts(snapshot, self.show_finished)
        tabs = self.query_one("#efforts", TabbedContent)
        names = [view.effort for view in shown]
        active = tabs.active
        kept = [name for name in self.panes if name in names]
        moved = next((i for i, (old, new) in enumerate(zip(kept, names)) if old != new), len(kept))
        for name in [name for name in self.panes if name not in names] + kept[moved:]:
            await tabs.remove_pane(f"effort-{slug(name)}")
            del self.panes[name]
        for view in shown:
            if view.effort not in self.panes:
                pane = EffortPane(view.effort)
                self.panes[view.effort] = pane
                await tabs.add_pane(TabPane(tab_label(view), pane, id=f"effort-{slug(view.effort)}"))
        if not self.is_attached or not self.screen_stack or not self.query("#header-path"):
            return
        if kept[moved:] and active in [pane.id for pane in tabs.query(TabPane)]:
            self.set_focus(None)
            tabs.active = active
        self.query_one("#header-finished", Static).update(Text(f"+{hidden} finished", style="dim") if hidden else Text())
        self.query_one("#empty", Static).display = not names
        tabs.display = bool(names)
        self.paint()
        for screen in self.screen_stack:
            if isinstance(screen, NeedsYouDetailScreen):
                await screen.follow(self.snapshot)
        self.refresh_landing()
        if self.focused is None:
            self.focus_tasks()
            self.call_after_refresh(self.focus_tasks)

    def paint(self, width: int | None = None) -> None:
        snapshot = self.snapshot
        if snapshot is None or not self.is_attached or not self.screen_stack:
            return
        if not self.query("#header-path"):
            return
        width = width or self.size.width
        colors = palette_from(self.get_css_variables())
        tabs = self.query_one("#efforts", TabbedContent)
        shown, hidden = selection.visible_efforts(snapshot, self.show_finished)
        self.query_one("#header-path", Static).update(header_text(self.target, snapshot.generated_at, colors, width))
        self.query_one("#header-finished", Static).update(Text(f"+{hidden} finished", style="dim") if hidden else Text())
        for view in shown:
            tab = tabs.get_tab(f"effort-{slug(view.effort)}")
            tab.label = Text(tab_label(view))
            tab.set_class(view.finished, "finished")
            self.panes[view.effort].show(view, snapshot.generated_at, width, colors)

    def on_resize(self, event: events.Resize) -> None:
        self.paint(event.size.width)


DETAIL_SCREENS = (TaskDetailScreen, PhaseDetailScreen, NeedsYouDetailScreen, CommitScreen)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="dashboard")
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
