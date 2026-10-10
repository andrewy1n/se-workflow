"""Journal model and screens: load, scope, open-first order, JournalScreen, RecordDetailScreen."""

from __future__ import annotations

import time
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Input, Markdown, OptionList, Static
from textual.widgets.option_list import Option

from dashboard.artifact_store import Target
from dashboard import model
from dashboard import pager
from dashboard.display import REDRAW_SECONDS, clip, palette_from, relative_time
from dashboard.task_detail import TaskDetailScreen

JOURNAL_TYPES = (
    "project:failed-attempt",
    "project:investigation-observation",
    "project:finding",
    "project:continuity-question",
    "project:assignment-amendment",
)
PLAN_REVIEW_PREFIX = "plan-review:"
FINDING_OPEN_STATES = ("asserted", "supported", "disputed")
KIND_JOURNAL = frozenset({"repair", "evaluate"})
SEPARATOR_KEY = "__separator__"
TYPE_LABEL = {
    "project:failed-attempt": ("✗", "attempt"),
    "project:investigation-observation": ("◉", "observation"),
    "project:finding": ("!", "finding"),
    "project:continuity-question": ("?", "question"),
    "project:assignment-amendment": ("△", "amendment"),
}


@dataclass(frozen=True)
class JournalItem:
    id: str
    record_type: str
    subject: str
    phase: str | None
    recorded_at: datetime
    text: str
    open: bool
    task_id: str = ""


def _soft_list(target: Target, record_type: str, *, where: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    try:
        return model._list(target, record_type, where=where, full=True)
    except model.ModelError:
        return []


def _phase_for_task(subject: str, tasks: list[dict[str, Any]]) -> tuple[str | None, str]:
    matches = [
        task for task in tasks
        if subject == task["subject"] or subject.startswith(task["subject"] + "-")
    ]
    if not matches:
        return None, ""
    task = max(matches, key=lambda item: len(item["subject"]))
    return model._payload(task).get("phase") or None, task["id"]


def _plan_review_slug(scope: str) -> str | None:
    if not scope.startswith(PLAN_REVIEW_PREFIX):
        return None
    return scope[len(PLAN_REVIEW_PREFIX):]


def _question_scope_text(scope: str, phase_titles: dict[str, str]) -> str:
    slug = _plan_review_slug(scope)
    if slug is not None:
        return phase_titles.get(slug, slug)
    return scope


def _question_open(record: dict[str, Any]) -> bool:
    return record.get("lifecycle_state") == "open"


def _finding_open(record: dict[str, Any]) -> bool:
    return (
        model._payload(record).get("needs") == "human"
        and record.get("lifecycle_state") in FINDING_OPEN_STATES
    )


def _first_line(text: str) -> str:
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def _attempt_text(payload: dict[str, Any]) -> str:
    parts = [payload.get("attempted_action") or "", "don't retry"]
    retry = payload.get("retry_when") or ""
    if retry:
        parts.append(f"retry when {retry}")
    return " · ".join(part for part in parts if part)


def _finding_text(payload: dict[str, Any]) -> str:
    claim = payload.get("claim") or ""
    needs = payload.get("needs") or ""
    if claim and needs:
        return f"{claim} · needs {needs}"
    return claim or needs


def _question_text(record: dict[str, Any], phase_titles: dict[str, str]) -> str:
    scope = model._payload(record).get("scope") or ""
    shown = _question_scope_text(scope, phase_titles)
    state = record.get("lifecycle_state") or ""
    if shown and state:
        return f"{shown} · {state}"
    return shown or state


def _amendment_text(record: dict[str, Any], task_subject: str) -> str:
    correction = _first_line(model._section(record.get("body") or "", "Correction"))
    if correction and task_subject:
        return f"{correction} · {task_subject}"
    return correction or task_subject


def _belongs_to_effort(
    record: dict[str, Any], effort: str, *, sole_goal: bool, by_subject: bool = False,
) -> bool:
    if by_subject:
        return record.get("subject") == effort
    payload_effort = model._payload(record).get("effort")
    if payload_effort:
        return payload_effort == effort
    return sole_goal


def _assignment_task(
    record: dict[str, Any],
    assignments: dict[str, dict[str, Any]],
    tasks_by_id: dict[str, dict[str, Any]],
    tasks_by_subject: dict[str, dict[str, Any]],
) -> tuple[str | None, str, str]:
    ref = model._payload(record).get("assignment") or ""
    assignment = assignments.get(ref)
    if assignment is None:
        phase, task_id = _phase_for_task(record["subject"], list(tasks_by_subject.values()))
        return phase, task_id, record["subject"] if task_id else ""
    work_ref = model._payload(assignment).get("work_item") or ""
    task = tasks_by_id.get(work_ref) or tasks_by_subject.get(work_ref)
    if task is None:
        phase, task_id = _phase_for_task(assignment["subject"], list(tasks_by_subject.values()))
        return phase, task_id, assignment["subject"] if task_id else assignment["subject"]
    return model._payload(task).get("phase") or None, task["id"], task["subject"]


def load_journal(target: Target, effort: str) -> list[JournalItem]:
    """List the five journal types for an effort; missing types become empty (R9)."""
    aliases = model._merge_aliases(model._list(target, "project:active-goal"))
    goals = [
        record for record in model._list(target, "project:active-goal")
        if record.get("lifecycle_state") == "active"
        and model._payload(record).get("status") != "closed"
    ]
    sole_goal = len(goals) == 1 and (not goals or goals[0]["subject"] == effort)

    tasks = model._remapped(
        _soft_list(target, "project:work-item", where=(f"payload.effort={effort}",)),
        aliases,
    )
    if not tasks:
        tasks = [
            record for record in model._remapped(_soft_list(target, "project:work-item"), aliases)
            if model._payload(record).get("effort") == effort
        ]
    tasks_by_id = {task["id"]: task for task in tasks}
    tasks_by_subject = {task["subject"]: task for task in tasks}

    phases = model._remapped(
        _soft_list(target, "project:phase", where=(f"payload.effort={effort}",)),
        aliases,
    )
    phase_titles = {
        record["subject"]: model._payload(record).get("title") or record["subject"]
        for record in phases
    }

    assignments_listed = model._remapped(_soft_list(target, "project:assignment"), aliases)
    assignments: dict[str, dict[str, Any]] = {}
    for record in assignments_listed:
        assignments[record["id"]] = record
        assignments[record["subject"]] = record

    listed: dict[str, list[dict[str, Any]]] = {}
    for record_type in JOURNAL_TYPES:
        raw = model._remapped(_soft_list(target, record_type), aliases)
        by_subject = record_type == "project:continuity-question"
        listed[record_type] = [
            record for record in raw
            if record.get("lifecycle_state") not in model.INACTIVE_STATES
            and _belongs_to_effort(record, effort, sole_goal=sole_goal, by_subject=by_subject)
        ]

    finding_subjects = {record["subject"] for record in listed["project:finding"]}
    items: list[JournalItem] = []

    for record in listed["project:failed-attempt"]:
        phase, task_id = _phase_for_task(record["subject"], tasks)
        items.append(JournalItem(
            record["id"], record["record_type"], record["subject"], phase,
            model._recorded_at(record), _attempt_text(model._payload(record)), False, task_id,
        ))

    for record in listed["project:investigation-observation"]:
        phase, task_id = _phase_for_task(record["subject"], tasks)
        open_item = record["subject"] not in finding_subjects
        items.append(JournalItem(
            record["id"], record["record_type"], record["subject"], phase,
            model._recorded_at(record),
            model._payload(record).get("what_was_observed") or "",
            open_item, task_id,
        ))

    for record in listed["project:finding"]:
        phase, task_id = _phase_for_task(record["subject"], tasks)
        items.append(JournalItem(
            record["id"], record["record_type"], record["subject"], phase,
            model._recorded_at(record), _finding_text(model._payload(record)),
            _finding_open(record), task_id,
        ))

    for record in listed["project:continuity-question"]:
        scope = model._payload(record).get("scope") or ""
        slug = _plan_review_slug(scope)
        phase = slug if slug is not None else None
        items.append(JournalItem(
            record["id"], record["record_type"], record["subject"], phase,
            model._recorded_at(record), _question_text(record, phase_titles),
            _question_open(record), "",
        ))

    for record in listed["project:assignment-amendment"]:
        phase, task_id, task_subject = _assignment_task(
            record, assignments, tasks_by_id, tasks_by_subject,
        )
        items.append(JournalItem(
            record["id"], record["record_type"], record["subject"], phase,
            model._recorded_at(record), _amendment_text(record, task_subject),
            False, task_id,
        ))

    return items


def journal_scope(items: list[JournalItem], phase: str | None) -> list[JournalItem]:
    """Phase items plus effort-only open questions; None returns every item (R2)."""
    if phase is None:
        return list(items)
    scoped: list[JournalItem] = []
    for item in items:
        if item.phase == phase:
            scoped.append(item)
        elif item.phase is None and item.open and item.record_type == "project:continuity-question":
            scoped.append(item)
    return scoped


def ordered(items: list[JournalItem]) -> tuple[list[JournalItem], list[JournalItem]]:
    """Open items newest first, then every other item newest first (R4)."""
    open_items = sorted((item for item in items if item.open), key=lambda item: item.recorded_at, reverse=True)
    rest = sorted((item for item in items if not item.open), key=lambda item: item.recorded_at, reverse=True)
    return open_items, rest


def filter_items(items: list[JournalItem], needle: str) -> list[JournalItem]:
    """Keep items whose subject or text contains *needle* (case-insensitive) (R6)."""
    needle = needle.strip().lower()
    if not needle:
        return list(items)
    return [
        item for item in items
        if needle in item.subject.lower() or needle in item.text.lower()
    ]


def load_record(target: Target, record_id: str) -> dict[str, Any]:
    """Fetch one record by id (type optional on the CLI)."""
    record = model._run(target, "get", "--id", record_id)
    if "subject" not in record:
        raise model.ModelError(f"get {record_id} returned unreadable output")
    return record


def type_cells(item: JournalItem, colors: dict[str, str]) -> Text:
    glyph, label = TYPE_LABEL.get(item.record_type, ("·", item.record_type.split(":")[-1]))
    text = Text(no_wrap=True, overflow="ellipsis")
    style = colors["warning"] if item.open else colors["muted"]
    text.append(f"{glyph} {label}", style=style)
    return text


def list_markdown(items: list[JournalItem], *, scope: str) -> str:
    """Markdown for the whole journal list (pager)."""
    open_items, rest = ordered(items)
    lines = [f"# Journal ({scope})", ""]
    if open_items:
        lines.append("## Open")
        lines.append("")
        for item in open_items:
            _, label = TYPE_LABEL.get(item.record_type, ("·", item.record_type))
            lines.append(f"- **{label}** `{item.subject}` — {item.text}")
        lines.append("")
    if rest:
        lines.append("## Rest")
        lines.append("")
        for item in rest:
            _, label = TYPE_LABEL.get(item.record_type, ("·", item.record_type))
            lines.append(f"- **{label}** `{item.subject}` — {item.text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def record_markdown(record: dict[str, Any]) -> str:
    """Markdown for one record: type, subject, payload, body (R5)."""
    payload = model._payload(record)
    lines = [
        f"# {record.get('record_type', '')}",
        "",
        f"**subject:** `{record.get('subject', '')}`",
        "",
    ]
    if payload:
        lines.append("## Payload")
        lines.append("")
        for key, value in payload.items():
            lines.append(f"- **{key}:** {value}")
        lines.append("")
    body = (record.get("body") or "").strip()
    if body:
        lines.append("## Body")
        lines.append("")
        lines.append(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


class JournalFilterInput(Input):
    BINDINGS = [Binding("escape", "cancel", "clear", show=False)]

    def action_cancel(self) -> None:
        screen = self.screen
        if isinstance(screen, JournalScreen):
            screen.clear_filter()


class JournalTable(DataTable):
    BINDINGS = [
        Binding("enter", "select_cursor", "open", show=False),
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
    ]

    def __init__(self, id: str) -> None:
        super().__init__(id=id, cursor_type="row", zebra_stripes=False)
        self.items: list[JournalItem] = []
        self._keys: list[str] = []

    def fill(self, items: list[JournalItem], colors: dict[str, str], now: datetime) -> None:
        kept = None
        if self.row_count and self.cursor_row is not None and self.cursor_row < len(self._keys):
            kept = self._keys[self.cursor_row]
        open_items, rest = ordered(items)
        self.items = []
        self._keys = []
        self.clear(columns=True)
        self.add_column("type", key="type", width=14)
        self.add_column("subject", key="subject", width=16)
        self.add_column("age", key="age", width=8)
        self.add_column("text", key="text")
        for item in open_items:
            self._add_item(item, colors, now)
        if open_items and rest:
            sep = Text("─" * 12, style=colors["muted"])
            self.add_row(sep, Text(""), Text(""), Text("───", style=colors["muted"]), key=SEPARATOR_KEY)
            self._keys.append(SEPARATOR_KEY)
            self.items.append(JournalItem("", "", "", None, datetime.min.replace(tzinfo=timezone.utc), "", False))
        for item in rest:
            self._add_item(item, colors, now)
        if kept is not None and kept in self._keys and kept != SEPARATOR_KEY:
            self.move_cursor(row=self._keys.index(kept))
        elif self._keys:
            first = next((i for i, key in enumerate(self._keys) if key != SEPARATOR_KEY), 0)
            self.move_cursor(row=first)

    def _add_item(self, item: JournalItem, colors: dict[str, str], now: datetime) -> None:
        age = Text(relative_time(item.recorded_at, now), style=colors["muted"], no_wrap=True)
        subject = Text(clip(item.subject, 16), no_wrap=True, overflow="ellipsis")
        body = Text(item.text, no_wrap=True, overflow="ellipsis")
        self.add_row(type_cells(item, colors), subject, age, body, key=item.id)
        self._keys.append(item.id)
        self.items.append(item)

    def cursor_item(self) -> JournalItem | None:
        if self.cursor_row is None or self.cursor_row >= len(self._keys):
            return None
        key = self._keys[self.cursor_row]
        if key == SEPARATOR_KEY:
            return None
        return next((item for item in self.items if item.id == key), None)


class JournalScreen(Screen[None]):
    CSS = """
    #journal-bar { height: 1; padding: 0 1; background: $panel; }
    #journal-error { height: auto; padding: 0 1; background: $error 20%; color: $error; display: none; }
    #journal-filter { height: 1; margin: 1 1 0 1; padding: 0 1; border: none; background: $panel; }
    #journal-filter:focus { border: none; background: $panel; }
    #journal-table { height: 1fr; margin: 1 1; border: round $panel; border-title-color: $text-muted; }
    #journal-empty { height: 1fr; content-align: center middle; color: $text-muted; display: none; }
    """
    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("a", "toggle_scope", "scope", show=False),
        Binding("slash", "filter", "filter"),
        Binding("o", "page", "pager", show=False),
        Binding("r", "app.refresh", "refresh"),
        Binding("c", "app.copy_slug", "copy"),
    ]

    def __init__(self, target: Target, effort: str, phase: str | None) -> None:
        super().__init__()
        self.target = target
        self.effort = effort
        self.anchor_phase = phase
        self.phase = phase
        self.all_items: list[JournalItem] = []
        self.filter_text = ""
        self.loaded = False
        self.token: str | None = None
        self.loaded_at = 0.0

    def compose(self) -> ComposeResult:
        yield Static(id="journal-bar")
        yield Static(id="journal-error")
        filt = JournalFilterInput(placeholder="filter journal", id="journal-filter")
        filt.display = False
        yield filt
        table = JournalTable(id="journal-table")
        table.border_title = "Journal"
        yield table
        yield Static("No journal items", id="journal-empty")
        yield Footer()

    def on_mount(self) -> None:
        self.load()

    def action_back(self) -> None:
        self.app.pop_screen()
        self.app.call_after_refresh(self.app.focus_tasks)

    def action_toggle_scope(self) -> None:
        if self.anchor_phase is None:
            return
        self.phase = None if self.phase is not None else self.anchor_phase
        self.repaint()

    def action_filter(self) -> None:
        box = self.query_one("#journal-filter", Input)
        box.value = self.filter_text
        box.display = True
        box.focus()
        box.cursor_position = len(box.value)

    def clear_filter(self) -> None:
        self.filter_text = ""
        box = self.query_one("#journal-filter", Input)
        box.display = False
        box.value = ""
        self.repaint()
        self.query_one("#journal-table", JournalTable).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "journal-filter":
            return
        if event.input.display and event.value != self.filter_text:
            self.filter_text = event.value
            self.repaint()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "journal-filter":
            return
        event.input.display = False
        self.query_one("#journal-table", JournalTable).focus()

    def action_page(self) -> None:
        items = filter_items(journal_scope(self.all_items, self.phase), self.filter_text)
        scope = "effort" if self.phase is None else self.phase
        text = list_markdown(items, scope=scope)
        self._page(text)

    def _page(self, text: str) -> None:
        suspend = getattr(self.app, "suspend", None)
        context = suspend() if callable(suspend) else nullcontext()
        try:
            with context:
                pager.page_text(text)
        except Exception:
            pager.page_text(text)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = event.data_table
        if not isinstance(table, JournalTable):
            return
        event.stop()
        item = table.cursor_item()
        if item is None:
            return
        self.app.push_screen(RecordDetailScreen(self.target, item.id, task_id=item.task_id))

    @work(thread=True, exclusive=True, group="journal")
    def load(self) -> None:
        self.loaded_at = time.monotonic()
        try:
            self.token = model.change_token(self.target)
            items = load_journal(self.target, self.effort)
        except (OSError, model.ModelError) as exc:
            self.app.call_from_thread(self.show_error, str(exc))
            return
        self.app.call_from_thread(self.apply, items)

    def poll(self, token: str) -> None:
        if token != self.token or time.monotonic() - self.loaded_at > REDRAW_SECONDS:
            self.load()

    def show_error(self, message: str) -> None:
        if not self.is_attached:
            return
        banner = self.query_one("#journal-error", Static)
        banner.update(Text(message.splitlines()[0] if message else "error", no_wrap=True, overflow="ellipsis"))
        banner.display = True

    def apply(self, items: list[JournalItem]) -> None:
        if not self.is_attached:
            return
        self.all_items = items
        self.query_one("#journal-error", Static).display = False
        self.repaint()
        if not self.loaded:
            self.query_one("#journal-table", JournalTable).focus()
        self.loaded = True

    def repaint(self) -> None:
        colors = palette_from(self.app.get_css_variables())
        scope = "effort" if self.phase is None else self.phase
        bar = Text(no_wrap=True, overflow="ellipsis")
        bar.append("Journal", style="bold")
        bar.append(f"  {self.effort}", style=colors["muted"])
        bar.append(f"  · {scope}", style=colors["muted"])
        self.query_one("#journal-bar", Static).update(bar)
        items = filter_items(journal_scope(self.all_items, self.phase), self.filter_text)
        table = self.query_one("#journal-table", JournalTable)
        empty = self.query_one("#journal-empty", Static)
        table.display = bool(items)
        empty.display = not items
        if items:
            now = datetime.now(timezone.utc)
            table.fill(items, colors, now)
            table.border_title = f"Journal {len(items)}"


class RecordDetailScreen(Screen[None]):
    CSS = """
    #record-bar { height: 1; padding: 0 1; background: $panel; }
    #record-error { height: auto; padding: 0 1; background: $error 20%; color: $error; display: none; }
    #record-detail { padding: 0 1; scrollbar-gutter: stable; }
    #record-title { margin-top: 1; text-style: bold; }
    .record-panel { height: auto; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; }
    .record-panel Markdown { margin: 0; padding: 0; background: transparent; }
    .record-panel Markdown > MarkdownBlock { margin: 1 0 0 0; }
    .record-panel Markdown > MarkdownHeader { margin: 0; }
    .record-panel Markdown > MarkdownBlock:first-child { margin-top: 0; }
    #record-links { height: auto; max-height: 8; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("o", "page", "pager", show=False),
        Binding("r", "app.refresh", "refresh"),
        Binding("c", "app.copy_slug", "copy"),
        Binding("l", "focus_links", "links", show=False),
    ]

    def __init__(self, target: Target, record_id: str, task_id: str = "") -> None:
        super().__init__()
        self.target = target
        self.record_id = record_id
        self.task_id = task_id
        self.record: dict[str, Any] | None = None
        self.loaded = False
        self.token: str | None = None
        self.loaded_at = 0.0

    def compose(self) -> ComposeResult:
        yield Static(id="record-bar")
        yield Static(id="record-error")
        with VerticalScroll(id="record-detail"):
            yield Static("Loading…", id="record-loading")
            with Vertical(id="record-content"):
                yield Static(id="record-title")
                yield Static(id="record-chips")
                payload = Vertical(Markdown(), id="record-payload", classes="record-panel")
                payload.border_title = "Payload"
                yield payload
                body = Vertical(Markdown(), id="record-body", classes="record-panel")
                body.border_title = "Body"
                yield body
                links = OptionList(id="record-links")
                links.border_title = "Links"
                links.display = False
                yield links
        yield Footer()

    def on_mount(self) -> None:
        self.load()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_focus_links(self) -> None:
        links = self.query_one("#record-links", OptionList)
        if not links.display or not links.option_count:
            return
        if links.highlighted is None:
            links.highlighted = 0
        links.focus()

    def action_page(self) -> None:
        if self.record is None:
            return
        text = record_markdown(self.record)
        suspend = getattr(self.app, "suspend", None)
        context = suspend() if callable(suspend) else nullcontext()
        try:
            with context:
                pager.page_text(text)
        except Exception:
            pager.page_text(text)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id != "record-links":
            return
        event.stop()
        key = event.option.id or ""
        if key.startswith("task:"):
            self.app.push_screen(TaskDetailScreen(self.target, key[len("task:"):]))

    @work(thread=True, exclusive=True, group="record-detail")
    def load(self) -> None:
        self.loaded_at = time.monotonic()
        try:
            self.token = model.change_token(self.target)
            record = load_record(self.target, self.record_id)
        except (OSError, model.ModelError) as exc:
            self.app.call_from_thread(self.show_error, str(exc))
            return
        self.app.call_from_thread(self.apply, record)

    def poll(self, token: str) -> None:
        if token != self.token or time.monotonic() - self.loaded_at > REDRAW_SECONDS:
            self.load()

    def show_error(self, message: str) -> None:
        if not self.is_attached:
            return
        banner = self.query_one("#record-error", Static)
        banner.update(Text(message.splitlines()[0] if message else "error", no_wrap=True, overflow="ellipsis"))
        banner.display = True

    async def apply(self, record: dict[str, Any]) -> None:
        if not self.is_attached:
            return
        colors = palette_from(self.app.get_css_variables())
        self.record = record
        self.query_one("#record-error", Static).display = False
        self.query_one("#record-loading", Static).display = False
        self.query_one("#record-content").display = True
        bar = Text(no_wrap=True, overflow="ellipsis")
        bar.append(record.get("subject") or record["id"], style="bold")
        bar.append(f"  {record.get('record_type', '')}", style=colors["muted"])
        self.query_one("#record-bar", Static).update(bar)
        self.query_one("#record-title", Static).update(Text(record.get("subject") or "", style="bold"))
        chips = Text.assemble(
            (record.get("record_type") or "", colors["primary"]),
            "  ",
            (record.get("lifecycle_state") or "", colors["muted"]),
        )
        self.query_one("#record-chips", Static).update(chips)
        payload = model._payload(record)
        payload_md = "\n".join(f"- **{key}:** {value}" for key, value in payload.items()) if payload else ""
        payload_panel = self.query_one("#record-payload")
        payload_panel.display = bool(payload_md)
        await self.query_one("#record-payload Markdown", Markdown).update(payload_md)
        body = (record.get("body") or "").strip()
        body_panel = self.query_one("#record-body")
        body_panel.display = bool(body)
        await self.query_one("#record-body Markdown", Markdown).update(body)
        links = self.query_one("#record-links", OptionList)
        links.clear_options()
        if self.task_id:
            links.add_option(Option(Text(f"Task: {record.get('subject', self.task_id)}"), id=f"task:{self.task_id}"))
            links.display = True
            links.highlighted = 0
        else:
            links.display = False
        self.loaded = True
