#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["textual>=0.80"]
# ///
"""Textual dashboard for the project's artifact store. `--once` prints one plain-text frame."""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifact_store  # noqa: E402
import dashboard_model as model  # noqa: E402
from rich.console import Console, Group  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402
from textual import work  # noqa: E402
from textual.binding import Binding  # noqa: E402
from textual.app import App, ComposeResult  # noqa: E402
from textual.containers import Horizontal, VerticalScroll  # noqa: E402
from textual.widgets import DataTable, Footer, ProgressBar, Static, TabbedContent, TabPane  # noqa: E402

WIDE = 90
ACTIVITY_LINES = 10
REDRAW_SECONDS = 30
STATUS_GLYPH = {"running": "▶", "ready": "●", "waiting": "◌", "done": "✓", "withdrawn": "✕"}
PHASE_GLYPH = {"done": "✓", "in_progress": "●", "planned": "○"}
ACTIVITY_GLYPH = {"assignment": "→", "execution-report": "≡", "check-run": "◇"}
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


def progress_label(view: model.EffortView) -> str:
    found = current_phase(view)
    if found is None:
        return ""
    index, phase = found
    return f"phase {index}/{len(view.phases)} · {phase.done} of {phase.total} tasks"


def counts(view: model.EffortView) -> dict[str, int]:
    tally = {status: 0 for status in model.TASK_ORDER}
    for task in view.tasks:
        tally[task.status] += 1
    return {
        "running": tally["running"], "ready": tally["ready"],
        "needs": len(view.needs_you), "done": tally["done"],
    }


def status_cell(task: model.TaskRow, colors: dict[str, str]) -> Text:
    return Text(f"{STATUS_GLYPH[task.status]} {task.status}", style=colors[task.status])


def wave_cell(task: model.TaskRow) -> str:
    return "" if task.wave is None else f"w{task.wave}"


def clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: max(width - 1, 1)] + "…"


def task_columns(width: int) -> list[str]:
    columns = ["status", "task", "wave"]
    return columns + ["phase", "assignee"] if width >= WIDE else columns


def task_cells(task: model.TaskRow, columns: list[str], title_width: int, colors: dict[str, str]) -> list[Text | str]:
    values: dict[str, Text | str] = {
        "status": status_cell(task, colors), "task": clip(task.title or task.subject, title_width),
        "wave": wave_cell(task), "phase": task.phase, "assignee": task.assignee,
    }
    return [values[name] for name in columns]


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


def tile_class(name: str, view: model.EffortView) -> str:
    if name == "needs" and view.needs_you:
        return "blocking" if any(i.kind == "blocking-question" for i in view.needs_you) else "attention"
    return name


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
        console.print(
            f"Running {tally['running']}   Ready {tally['ready']}   Needs you {tally['needs']}   Done {tally['done']}"
        )
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


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)


class EffortPane(VerticalScroll):
    def __init__(self, effort: str) -> None:
        super().__init__(classes="effort")
        self.effort = effort

    def compose(self) -> ComposeResult:
        yield Static(id="goal")
        yield Static(id="stepper")
        yield Static(id="progress-label")
        yield ProgressBar(id="progress", show_eta=False, show_percentage=False)
        with Horizontal(id="tiles"):
            for name, label in (("running", "Running"), ("ready", "Ready"), ("needs", "Needs you"), ("done", "Done")):
                tile = Static(id=f"tile-{name}", classes="tile")
                tile.tile_label = label
                yield tile
        tasks = DataTable(id="tasks", cursor_type="row", zebra_stripes=False)
        tasks.border_title = "Tasks"
        yield tasks
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
            bar.update(total=max(found[1].total, 1), progress=found[1].done)
        tally = counts(view)
        for name, number in tally.items():
            tile = self.query_one(f"#tile-{name}", Static)
            tile.update(Text.assemble((f"{number}\n", "bold"), (tile.tile_label, "")))
            tile.set_classes(f"tile {tile_class(name, view)}" if number or name != "needs" else "tile quiet")
        self.fill_tasks(view, width, inner, colors)
        self.fill_panel("#needs-you", needs_lines(view, colors, inner - 4))
        self.fill_panel("#activity", activity_lines(view, now, colors, inner - 4))

    def on_resize(self) -> None:
        last = getattr(self, "last", None)
        if last is not None and self.scrollable_content_region.width != self.inner:
            self.show(*last)

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
        table.display = bool(view.tasks)
        keep = None
        if table.row_count:
            keep = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        table.clear(columns=True)
        columns = task_columns(width)
        for name in columns:
            table.add_column(name, key=name)
        room = title_width(columns, room - 4, view.tasks)
        for task in view.tasks:
            table.add_row(*task_cells(task, columns, room, colors), key=task.id)
        if keep is not None and keep in table.rows:
            table.move_cursor(row=table.get_row_index(keep))


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
    #tiles { height: 5; margin-top: 1; }
    .tile { width: 1fr; height: 5; margin-right: 1; border: round $panel; content-align: center middle; text-align: center; }
    .tile:last-child { margin-right: 0; }
    .tile.running { border: round $primary; color: $primary; }
    .tile.ready { border: round $success; color: $success; }
    .tile.attention { border: round $warning; color: $warning; }
    .tile.blocking { border: round $error; color: $error; }
    .tile.done, .tile.quiet { color: $text-muted; }
    #tasks { height: auto; max-height: 16; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; background: $surface; }
    #needs-you { height: auto; margin-top: 1; border: round $warning; border-title-color: $warning; padding: 0 1; }
    #activity { height: auto; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; }
    """
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        ("q", "quit", "quit"),
        Binding("tab", "next_effort", "switch", priority=True),
        Binding("shift+tab", "previous_effort", "previous", show=False, priority=True),
        ("r", "refresh", "refresh"),
    ]

    def __init__(self, target: artifact_store.Target, interval: float = 2.0) -> None:
        super().__init__()
        self.target = target
        self.interval = interval
        self.snapshot: model.Snapshot | None = None
        self.token: str | None = None
        self.loaded_at = 0.0
        self.panes: dict[str, EffortPane] = {}

    def compose(self) -> ComposeResult:
        yield Static(id="header")
        yield Static(id="error")
        yield Static(id="empty")
        yield TabbedContent(id="efforts")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#header", Static).update(header_text(self.target, None, palette_from(self.get_css_variables())))
        self.query_one("#empty", Static).update(f"No live efforts in {self.target.store}")
        self.set_interval(self.interval, self.poll)
        self.reload()

    def poll(self) -> None:
        try:
            token = model.change_token(self.target)
        except OSError:
            return
        if token != self.token or time.monotonic() - self.loaded_at > REDRAW_SECONDS:
            self.reload()

    def action_refresh(self) -> None:
        self.reload()

    def action_next_effort(self) -> None:
        self.step_effort(1)

    def action_previous_effort(self) -> None:
        self.step_effort(-1)

    def step_effort(self, delta: int) -> None:
        tabs = self.query_one("#efforts", TabbedContent)
        ids = [pane.id for pane in tabs.query(TabPane)]
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

    def paint(self) -> None:
        snapshot = self.snapshot
        if snapshot is None:
            return
        colors = palette_from(self.get_css_variables())
        tabs = self.query_one("#efforts", TabbedContent)
        self.query_one("#header", Static).update(header_text(self.target, snapshot.generated_at, colors, self.size.width))
        for view in snapshot.efforts:
            tabs.get_tab(f"effort-{slug(view.effort)}").label = Text(tab_label(view))
            self.panes[view.effort].show(view, snapshot.generated_at, self.size.width, colors)

    def on_resize(self) -> None:
        self.paint()


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
