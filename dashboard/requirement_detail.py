"""Requirement detail screen: text, decisions, traced tasks, acceptances, and assessment history."""

from __future__ import annotations

import asyncio
import time

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, OptionList, Static
from textual.widgets.option_list import Option

from dashboard import artifact_store, model
from dashboard.display import STATUS_GLYPH, clip, palette_from
from dashboard.task_detail import TaskDetailScreen


class RequirementTasks(OptionList):
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


def latest_check(detail: model.RequirementDetail) -> model.CheckRun | None:
    checks = [row.check for row in detail.acceptances if row.check is not None]
    return max(checks, key=lambda check: check.recorded_at) if checks else None


def requirement_chips(detail: model.RequirementDetail, colors: dict[str, str], width: int) -> Text:
    status_style = {"verified": colors["success"], "failed": colors["error"], "blocked": colors["error"]}.get(detail.status, "")
    chips = [(detail.id, colors["primary"]), (detail.status, status_style)]
    if detail.status == "unassessed":
        check = latest_check(detail)
        if check is not None and check.result:
            chips.append((check.result, colors["muted"]))
    if detail.next:
        chips.append((detail.next, colors["muted"]))
    chips.append((f"phase {detail.phase}", colors["muted"]))
    text = Text()
    used = 0
    limit = max(width, 1)
    for index, (chip, chip_style) in enumerate(chips):
        shown = clip(chip, limit)
        if index:
            if used + 3 + len(shown) > limit:
                text.append("\n")
                used = 0
            else:
                text.append(" · ", style=colors["muted"])
                used += 3
        text.append(shown, style=chip_style or "")
        used += len(shown)
    return text


def task_options(detail: model.RequirementDetail, colors: dict[str, str]) -> list[Option]:
    options = []
    for task in detail.tasks:
        text = Text(no_wrap=True, overflow="ellipsis")
        text.append(f"{STATUS_GLYPH.get(task.status, '·')} ", style=colors.get(task.status, colors["muted"]))
        text.append(task.subject)
        if task.title and task.title != task.subject:
            text.append(f"  {task.title}", style=colors["muted"])
        options.append(Option(text, id=f"task:{task.id}"))
    return options


def acceptance_mark(row: model.AcceptanceRow, colors: dict[str, str]) -> Text:
    if row.check is None:
        return Text("–", style=colors["muted"])
    if row.check.result == "pass":
        return Text("✓", style=colors["success"])
    return Text("✗", style=colors["error"])


def acceptance_body(row: model.AcceptanceRow, colors: dict[str, str]) -> Text:
    text = Text(row.criterion)
    if row.check is not None:
        result_style = colors["success"] if row.check.result == "pass" else colors["error"]
        text.append("\n")
        text.append(row.check.result, style=result_style)
        if row.check.evidence_kind:
            text.append(" · ", style=colors["muted"])
            text.append(row.check.evidence_kind, style=colors["muted"])
    return text


def decision_text(detail: model.RequirementDetail) -> Text:
    return Text("\n".join(f"{item.subject}: {item.choice}" for item in detail.decisions))


def history_text(detail: model.RequirementDetail, colors: dict[str, str]) -> Text:
    text = Text()
    for index, item in enumerate(detail.assessments):
        if index:
            text.append("\n")
        parts = [part for part in (item.status, item.level, item.next, item.confidence) if part]
        style = colors["success"] if item.status == "verified" else colors["error"] if item.status in ("failed", "blocked") else ""
        text.append(" · ".join(parts), style=style or "")
    return text


class RequirementDetailScreen(TaskDetailScreen):
    """TaskDetailScreen subclass so the app's detail poll, refresh, and binding checks include this screen."""

    CSS = """
    #detail-links { border: round $panel; border-title-color: $text-muted; padding: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("l", "focus_links", "links"),
        Binding("c", "app.copy_slug", "copy"),
        Binding("g", "commit", "commit", show=False),
        Binding("r", "app.refresh", "refresh"),
    ]

    def __init__(self, target: artifact_store.Target, effort: str, phase: str, requirement: str) -> None:
        Screen.__init__(self)
        self.target = target
        self.effort = effort
        self.phase = phase
        self.requirement = requirement
        self.detail: model.RequirementDetail | None = None
        self.loaded = False
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
                text = Static(id="requirement-text", classes="panel")
                text.border_title = "Requirement"
                yield text
                decisions = Static(id="requirement-decisions", classes="panel")
                decisions.border_title = "Decisions"
                yield decisions
                links = RequirementTasks(id="detail-links")
                links.border_title = "Tasks"
                yield links
                acceptances = Vertical(id="acceptances", classes="panel")
                acceptances.border_title = "Acceptance"
                yield acceptances
                history = Static(id="requirement-history", classes="panel")
                history.border_title = "Assessments"
                yield history
        yield Footer()

    def action_commit(self) -> None:
        return

    def action_focus_links(self) -> None:
        links = self.query_one("#detail-links", RequirementTasks)
        if not links.option_count:
            return
        if links.highlighted is None:
            links.highlighted = 0
        links.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if not isinstance(event.option_list, RequirementTasks) or self.detail is None:
            return
        event.stop()
        key = event.option.id or ""
        if key.startswith("task:"):
            self.app.push_screen(TaskDetailScreen(self.target, key[len("task:"):]))

    @work(thread=True, exclusive=True, group="requirement-detail")
    def load(self) -> None:
        self.loaded_at = time.monotonic()
        try:
            self.token = model.change_token(self.target)
            detail = model.load_requirement_detail(self.target, self.effort, self.phase, self.requirement)
        except (OSError, model.ModelError) as exc:
            self.app.call_from_thread(self.show_error, str(exc))
            return
        object.__setattr__(detail, "subject", detail.id)  # copy reads detail.subject
        self.app.call_from_thread(self.apply, detail)

    async def apply(self, detail: model.RequirementDetail) -> None:
        async with self.painting:
            if self.is_attached:
                await self.paint(detail)

    async def paint(self, detail: model.RequirementDetail) -> None:
        colors = palette_from(self.app.get_css_variables())
        scroll = self.query_one("#detail", VerticalScroll)
        offset = scroll.scroll_y
        self.detail = detail
        self.query_one("#detail-error", Static).display = False
        self.query_one("#detail-loading", Static).display = False
        self.query_one("#detail-content").display = True
        bar = Text(no_wrap=True, overflow="ellipsis")
        bar.append(detail.id, style="bold")
        bar.append(f"  {self.effort}", style=colors["muted"])
        self.query_one("#detail-bar", Static).update(bar)
        self.query_one("#detail-title", Static).update(Text(detail.id, style="bold"))
        self.paint_chips()
        requirement = self.query_one("#requirement-text", Static)
        requirement.display = bool(detail.text)
        requirement.update(detail.text)
        decisions = self.query_one("#requirement-decisions", Static)
        decisions.display = bool(detail.decisions)
        decisions.update(decision_text(detail))
        links = self.query_one("#detail-links", RequirementTasks)
        links.fill(task_options(detail, colors))
        if detail.tasks and links.highlighted is None:
            links.highlighted = 0
        await self.fill_acceptances(detail, colors)
        history = self.query_one("#requirement-history", Static)
        history.display = bool(detail.assessments)
        history.update(history_text(detail, colors))
        if not self.loaded and detail.tasks:
            links.focus()
        self.loaded = True
        self.call_after_refresh(scroll.scroll_to, y=offset, animate=False)

    def paint_chips(self) -> None:
        if self.detail is None:
            return
        chips = self.query_one("#detail-chips", Static)
        colors = palette_from(self.app.get_css_variables())
        chips.update(requirement_chips(self.detail, colors, chips.size.width or self.size.width - 4))

    async def fill_acceptances(self, detail: model.RequirementDetail, colors: dict[str, str]) -> None:
        panel = self.query_one("#acceptances", Vertical)
        panel.display = bool(detail.acceptances)
        await panel.remove_children()
        await panel.mount_all(
            Horizontal(
                Static(acceptance_mark(row, colors), classes="mark"),
                Static(acceptance_body(row, colors), classes="body"),
                classes="acceptance",
            )
            for row in detail.acceptances
        )
