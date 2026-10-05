"""Task detail screen and the helpers that render a task's chips, acceptance, links and timeline."""

from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timezone

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Collapsible, Footer, Markdown, OptionList, Static
from textual.widgets.option_list import Option

from dashboard import artifact_store, model
from dashboard.commit import CommitScreen, latest_revision, load_commit, stat_width
from dashboard.display import (
    ACTIVITY_GLYPH, REDRAW_SECONDS, STATUS_GLYPH, palette_from, relative_time, slug,
)
from dashboard.tasks import PHASE_PREFIX, status_label


def detail_chips(detail: model.TaskDetail, colors: dict[str, str], width: int = 100, now: datetime | None = None) -> Text:
    label = status_label(detail.status, detail.running_since, now or datetime.now(timezone.utc))
    chips = [(label, colors.get(detail.status, colors["muted"]))]
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


def link_options(detail: model.TaskDetail, colors: dict[str, str]) -> list[Option]:
    options = []
    for label, tasks in (("Depends on:", detail.depends_on), ("Blocks:", detail.blocks)):
        for task in tasks:
            text = Text(f"{label} ", no_wrap=True, overflow="ellipsis")
            text.append(f"{STATUS_GLYPH.get(task.status, '·')} ", style=colors.get(task.status, colors["muted"]))
            text.append(task.subject, style=colors["muted"])
            options.append(Option(text, id=f"task:{task.id}"))
    if detail.phase:
        text = Text("Phase: ", no_wrap=True, overflow="ellipsis")
        text.append(detail.phase, style=colors["muted"])
        options.append(Option(text, id=f"{PHASE_PREFIX}{detail.phase}"))
    for requirement in _csv(detail.requirements):
        text = Text("Requirement: ", no_wrap=True, overflow="ellipsis")
        text.append(requirement, style=colors["muted"])
        options.append(Option(text, id=f"req:{detail.phase}:{requirement}"))
    for decision in _csv(detail.decisions):
        text = Text("Decision: ", no_wrap=True, overflow="ellipsis")
        text.append(decision, style=colors["muted"])
        options.append(Option(text, id=f"decision:{decision}"))
    return options


def _csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


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


class LinkList(OptionList):
    BINDINGS = [
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
    ]

    def fill(self, options: list[Option]) -> None:
        index = self.highlighted
        self.display = bool(options)
        self.clear_options()
        self.add_options(options)
        if index is not None and options:
            self.highlighted = min(index, len(options) - 1)
        if not options and self.has_focus:
            self.screen.set_focus(self.screen.query_one("#detail"))


class TaskDetailScreen(Screen[None]):
    CSS = """
    #detail-bar { height: 1; padding: 0 1; background: $panel; }
    #detail-error { height: auto; padding: 0 1; background: $error 20%; color: $error; display: none; }
    #detail { padding: 0 1; scrollbar-gutter: stable; }
    #detail-loading { margin-top: 1; color: $text-muted; }
    #detail-content { height: auto; display: none; }
    #detail-title { margin-top: 1; text-style: bold; }
    #detail-links { height: auto; margin-top: 1; border: none; padding: 0; background: transparent; }
    #detail-links:focus { border: none; background-tint: $foreground 0%; }
    #detail-links > .option-list--option-highlighted { background: transparent; color: $foreground; text-style: none; }
    #detail-links:focus > .option-list--option-highlighted { background: $block-cursor-background; color: $block-cursor-foreground; text-style: $block-cursor-text-style; }
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
    Markdown > MarkdownBlock { margin: 1 0 0 0; }
    Markdown > MarkdownHeader { margin: 0; }
    Markdown > MarkdownBlock:first-child { margin-top: 0; }
    """
    AUTO_FOCUS = "#detail"
    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("l", "focus_links", "links"),
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
                yield LinkList(id="detail-links")
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

    def action_focus_links(self) -> None:
        links = self.query_one("#detail-links", LinkList)
        if not links.option_count:
            return
        if links.highlighted is None:
            links.highlighted = 0
        links.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if not isinstance(event.option_list, LinkList) or self.detail is None:
            return
        event.stop()
        key = event.option.id or ""
        if key.startswith(PHASE_PREFIX):
            from dashboard.app import PhaseDetailScreen

            self.app.push_screen(PhaseDetailScreen(self.target, self.detail.effort, key[len(PHASE_PREFIX):]))
        elif key.startswith("task:"):
            self.app.push_screen(TaskDetailScreen(self.target, key[len("task:"):]))
        elif key.startswith("req:"):
            from dashboard.requirement_detail import RequirementDetailScreen

            phase, _, requirement = key[len("req:"):].partition(":")
            if phase and requirement:
                self.app.push_screen(
                    RequirementDetailScreen(self.target, self.detail.effort, phase, requirement)
                )

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
        self.query_one("#detail-links", LinkList).fill(link_options(detail, colors))
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
