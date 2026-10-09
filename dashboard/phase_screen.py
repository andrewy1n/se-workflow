"""Tabbed phase screen: Overview, Spec, Design, Decisions, Evidence, Tasks."""

from __future__ import annotations

import textwrap
import time
from contextlib import nullcontext
from datetime import datetime, timezone

from rich.text import Text
from textual import work
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.geometry import Region
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import (
    DataTable, Footer, Markdown, OptionList, ProgressBar, Static, TabbedContent, TabPane,
)
from textual.widgets.option_list import Option

from dashboard import artifact_store
from dashboard import gates
from dashboard import matrix as matrix_mod
from dashboard import model
from dashboard import pager
from dashboard.display import PHASE_GLYPH, REDRAW_SECONDS, STATUS_GLYPH, elapsed, palette_from
from dashboard.task_detail import TaskDetailScreen

STAGE_NAMES = ("specify", "design", "plan", "execute", "integrate", "verify", "assess", "release")
TAB_LABELS = {
    "overview": "Overview",
    "spec": "Spec",
    "design": "Design",
    "decisions": "Decisions",
    "evidence": "Evidence",
    "tasks": "Tasks",
}


def stage_strip(stage: str, colors: dict[str, str], width: int) -> Text:
    width = max(width, 8)
    text = Text()
    used = 0
    for name in STAGE_NAMES:
        style = "bold " + colors["primary"] if name == stage else colors["muted"]
        gap = 3 if used else 0
        if used and used + gap + len(name) > width:
            text.append("\n")
            used = 0
            gap = 0
        if gap:
            text.append(" · ", style=colors["muted"])
            used += 3
        text.append(name, style=style)
        used += len(name)
    return text


def wrap_block(text: str, width: int) -> str:
    width = max(width, 8)
    return "\n".join(
        "\n".join(textwrap.wrap(paragraph, width) or [""])
        for paragraph in text.splitlines() or [""]
    )


def requirement_line(row: model.RequirementRow, width: int) -> Text:
    parts = [row.id, row.status]
    if row.next:
        parts.append(row.next)
    parts.append(str(row.tasks))
    text = Text("  ".join(parts), no_wrap=True, overflow="ellipsis")
    if row.status == "unassessed" and row.latest_check is not None:
        text.append("  ")
        text.append(row.latest_check.result, style="dim")
    text.truncate(max(width, 8), overflow="ellipsis")
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


def phase_task_line(task: model.TaskRow, colors: dict[str, str]) -> Text:
    text = Text(no_wrap=True, overflow="ellipsis")
    text.append(f"{STATUS_GLYPH.get(task.status, '·')} ", style=colors.get(task.status, colors["muted"]))
    text.append(task.title or task.subject)
    return text


def _drop_section(body: str, heading: str) -> str:
    """Return body with a `## heading` section removed."""
    target = heading.strip().lower()
    lines = (body or "").splitlines()
    kept: list[str] = []
    skipping = False
    for line in lines:
        if line.startswith("## "):
            skipping = line[3:].strip().lower() == target
            if skipping:
                continue
        if not skipping:
            kept.append(line)
    return "\n".join(kept).strip()


def _spec_markdown(body: str) -> str:
    return _drop_section(body, "Requirements")


class PhaseTaskList(OptionList):
    BINDINGS = [
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
        Binding("pageup", "scroll_phase('page_up')", "page up", show=False),
        Binding("pagedown", "scroll_phase('page_down')", "page down", show=False),
        Binding("home", "scroll_phase('home')", "top", show=False),
        Binding("end", "scroll_phase('end')", "bottom", show=False),
    ]

    def __init__(self, id: str) -> None:
        super().__init__(id=id)
        self.tasks: list[model.TaskRow] = []

    def fill(self, tasks: list[model.TaskRow], colors: dict[str, str]) -> None:
        kept = self.tasks[self.highlighted].id if self.highlighted is not None and self.highlighted < len(self.tasks) else None
        self.tasks = list(tasks)
        self.clear_options()
        self.add_options(Option(phase_task_line(task, colors), id=task.id) for task in self.tasks)
        ids = [task.id for task in self.tasks]
        if ids:
            self.highlighted = ids.index(kept) if kept in ids else 0

    def action_scroll_phase(self, where: str) -> None:
        scroll = self.query_ancestor(VerticalScroll)
        if scroll is not None:
            getattr(scroll, f"scroll_{where}")(animate=False)

    def action_cursor_down(self) -> None:
        super().action_cursor_down()
        self.follow()

    def action_cursor_up(self) -> None:
        super().action_cursor_up()
        self.follow()

    def follow(self) -> None:
        if self.highlighted is None:
            return
        scroll = self.query_ancestor(VerticalScroll)
        if scroll is None:
            return
        top = self.content_region.y - scroll.content_region.y + int(scroll.scroll_y) + self.highlighted
        scroll.scroll_to_region(Region(0, top, 1, 1), animate=False, immediate=True)


COLUMN_LABELS = {
    "id": "id",
    "text": "text",
    "tasks": "tasks",
    "check": "✓",
    "kind": "kind",
    "age": "age",
    "status": "status",
    "next": "next",
}


def _check_glyph(row: model.RequirementRow) -> str:
    if row.latest_check is None:
        return ""
    if row.latest_check.result == "pass":
        return "✓"
    if row.latest_check.result == "fail":
        return "✗"
    return row.latest_check.result


def _check_age(row: model.RequirementRow, now: datetime) -> str:
    if row.check_at is None:
        return ""
    return elapsed(row.check_at, now)


def _tone_style(tone: str, colors: dict[str, str]) -> str:
    if tone == "default":
        return ""
    return colors.get(tone, "")


def matrix_cell(row: model.RequirementRow, column: str, colors: dict[str, str], now: datetime) -> Text:
    style = _tone_style(matrix_mod.row_tone(row), colors)
    if column == "id":
        value = row.id
    elif column == "text":
        value = row.text
    elif column == "tasks":
        value = f"{row.tasks_done}/{row.tasks}"
    elif column == "check":
        value = _check_glyph(row)
    elif column == "kind":
        value = row.check_kind
    elif column == "age":
        value = _check_age(row, now)
    elif column == "status":
        value = row.status
    elif column == "next":
        value = row.next
    else:
        value = ""
    return Text(value, style=style, no_wrap=True, overflow="ellipsis")


class RequirementMatrix(DataTable):
    BINDINGS = [
        Binding("enter", "select_cursor", "open", show=False),
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
    ]

    def __init__(self, id: str) -> None:
        super().__init__(id=id, cursor_type="row", zebra_stripes=False)
        self.requirements: list[model.RequirementRow] = []
        self._column_names: list[str] = []

    def fill(
        self,
        rows: list[model.RequirementRow] | tuple[model.RequirementRow, ...],
        width: int,
        colors: dict[str, str],
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(timezone.utc)
        kept = None
        if (
            self.row_count
            and self.cursor_row is not None
            and self.cursor_row < len(self.requirements)
        ):
            kept = self.requirements[self.cursor_row].id
        self.requirements = list(rows)
        columns = matrix_mod.matrix_columns(width)
        self.clear(columns=True)
        self._column_names = columns
        for name in columns:
            self.add_column(COLUMN_LABELS[name], key=name)
        for row in self.requirements:
            cells = [matrix_cell(row, name, colors, now) for name in columns]
            self.add_row(*cells, key=row.id)
        if kept is not None and kept in {row.id for row in self.requirements}:
            self.move_cursor(row=self.get_row_index(kept))
        elif self.requirements:
            self.move_cursor(row=0)


class SpecRequirementList(OptionList):
    BINDINGS = [
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
    ]

    def __init__(self, id: str) -> None:
        super().__init__(id=id)
        self.rows: list[model.RequirementRow] = []

    def fill(self, rows: list[model.RequirementRow] | tuple[model.RequirementRow, ...]) -> None:
        kept = self.rows[self.highlighted].id if self.highlighted is not None and self.highlighted < len(self.rows) else None
        self.rows = list(rows)
        self.clear_options()
        for row in self.rows:
            prompt = Text(f"{row.id} {row.text}", no_wrap=True, overflow="ellipsis")
            self.add_option(Option(prompt, id=row.id))
        ids = [row.id for row in self.rows]
        if kept is not None and kept in ids:
            self.highlighted = ids.index(kept)
        elif ids:
            self.highlighted = 0


class DecisionsList(OptionList):
    BINDINGS = [
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
        Binding("enter", "toggle_expand", "expand", show=False),
    ]

    def __init__(self, id: str) -> None:
        super().__init__(id=id)
        self.id_to_stable: dict[str, str] = {}
        self.expanded: set[str] = set()
        self._history = False
        self._seq = 0

    def fill(self, log: model.DecisionLog, colors: dict[str, str], *, history: bool, show_groups: bool) -> None:
        kept_stable = None
        if self.highlighted is not None and self.highlighted < self.option_count:
            option = self.get_option_at_index(self.highlighted)
            kept_stable = self.id_to_stable.get(option.id or "")
        self._history = history
        self.id_to_stable = {}
        self._seq = 0
        self.clear_options()
        for title, group in log.groups:
            if show_groups:
                header = Text(title, style="bold")
                self.add_option(Option(header, id=f"group:{title}", disabled=True))
            for entry in group:
                self._add_entry(entry, colors, depth=0)
        if kept_stable is not None:
            for index in range(self.option_count):
                oid = self.get_option_at_index(index).id or ""
                if self.id_to_stable.get(oid) == kept_stable:
                    self.highlighted = index
                    break
        elif self.option_count:
            for index in range(self.option_count):
                if not self.get_option_at_index(index).disabled:
                    self.highlighted = index
                    break

    def _add_entry(self, entry: model.DecisionEntry, colors: dict[str, str], depth: int) -> None:
        self._seq += 1
        option_id = f"dec:{self._seq}"
        stable = f"{depth}\0{entry.subject}\0{entry.choice}"
        self.id_to_stable[option_id] = stable
        indent = "  " * depth
        dim = depth > 0
        style = colors["muted"] if dim else ""
        line = Text(no_wrap=True, overflow="ellipsis")
        if depth:
            line.append(f"{indent}supersedes ", style=colors["muted"])
        prefix = "▾ " if stable in self.expanded else "▸ "
        line.append(f"{indent}{prefix}{entry.subject}: {entry.choice}", style=style)
        self.add_option(Option(line, id=option_id))
        if stable in self.expanded:
            for label, value in (
                ("alternatives", entry.alternatives),
                ("rationale", entry.rationale),
                ("counter", entry.counter),
            ):
                if value:
                    detail = Text(f"{indent}  {label}: {value}", style=colors["muted"])
                    self.add_option(Option(detail, id=f"detail:{self._seq}:{label}", disabled=True))
        if self._history:
            for child in entry.superseded:
                self._add_entry(child, colors, depth=depth + 1)

    def action_toggle_expand(self) -> None:
        if self.highlighted is None or self.highlighted >= self.option_count:
            return
        option = self.get_option_at_index(self.highlighted)
        option_id = option.id or ""
        stable = self.id_to_stable.get(option_id)
        if stable is None:
            return
        if stable in self.expanded:
            self.expanded.discard(stable)
        else:
            self.expanded.add(stable)
        screen = self.screen
        if isinstance(screen, PhaseScreen):
            screen.refresh_decisions()


class OverviewPane(VerticalScroll):
    def compose(self):
        yield Static(id="phase-title")
        yield Static(id="phase-chips")
        stage = Static(id="phase-stage")
        stage.display = False
        yield stage
        yield Static(id="phase-progress-label")
        yield ProgressBar(id="phase-progress", show_eta=False, show_percentage=False)
        yield Static(id="phase-next-step")
        yield Static(id="phase-landing")
        integration = Static(id="phase-integration", classes="phase-panel")
        integration.border_title = "Integration"
        integration.display = False
        yield integration
        body = Vertical(Markdown(), id="phase-body", classes="phase-panel")
        body.border_title = "Phase"
        body.display = False
        yield body

    async def show(self, detail: model.PhaseDetail, colors: dict[str, str], width: int) -> None:
        self.query_one("#phase-title", Static).update(Text(detail.title or detail.subject, style="bold"))
        self.query_one("#phase-chips", Static).update(phase_chips(detail, colors))
        evidence = detail.evidence
        stage = self.query_one("#phase-stage", Static)
        stage.display = evidence is not None
        if evidence is not None:
            stage.update(stage_strip(evidence.stage, colors, width))
        done = sum(task.status == "done" for task in detail.tasks)
        total = sum(task.status != "withdrawn" for task in detail.tasks)
        self.query_one("#phase-progress-label", Static).update(
            Text(f"{done}/{total} tasks", style=colors["muted"])
        )
        bar = self.query_one("#phase-progress", ProgressBar)
        bar.update(total=max(total, 1), progress=done)

        view = None
        landing = {}
        app = self.app
        if hasattr(app, "effort_view"):
            view = app.effort_view(detail.effort)
            landing = getattr(app, "landings", {}).get(detail.effort, {})
        next_widget = self.query_one("#phase-next-step", Static)
        landing_widget = self.query_one("#phase-landing", Static)
        if view is not None:
            step = gates.next_step(view, landing)
            text = Text(no_wrap=True, overflow="ellipsis")
            if step:
                text.append(f"next: {step}")
            if view.position:
                if text.plain:
                    text.append("  ")
                text.append(view.position, style=colors["muted"])
            next_widget.update(text)
            next_widget.display = bool(text.plain)
            summary = gates.landing_summary(landing[detail.subject]) if detail.subject in landing else ""
            landing_widget.update(Text(summary, style=colors["muted"]) if summary else Text())
            landing_widget.display = bool(summary)
        else:
            next_widget.display = False
            landing_widget.display = False

        integration = self.query_one("#phase-integration", Static)
        report = evidence.integration if evidence is not None else None
        integration.display = report is not None
        if report is not None:
            integration.update(wrap_block(f"{report.result}\nConflicts\n{report.conflicts}", max(width - 4, 8)))

        body = self.query_one("#phase-body")
        show_body = detail.structured and bool(detail.body.strip())
        body.display = show_body
        if show_body:
            await self.query_one("#phase-body Markdown", Markdown).update(detail.body.strip())

    def pager_text(self) -> str:
        detail = self.screen.detail if isinstance(self.screen, PhaseScreen) else None
        if detail is None:
            return ""
        parts = [f"# {detail.title or detail.subject}", "", phase_chips(detail, {"muted": "", "warning": ""}).plain]
        if detail.structured and detail.body.strip():
            parts.extend(["", detail.body.strip()])
        if detail.evidence and detail.evidence.integration is not None:
            report = detail.evidence.integration
            parts.extend(["", "## Integration", "", f"{report.result}\n\nConflicts\n\n{report.conflicts}"])
        return "\n".join(parts).strip() + "\n"


class SpecPane(VerticalScroll):
    def compose(self):
        yield Vertical(Markdown(), id="spec-markdown", classes="phase-panel")
        requirements = SpecRequirementList(id="spec-requirements")
        requirements.add_class("phase-panel")
        requirements.border_title = "Requirements"
        requirements.display = False
        yield requirements
        constraints = Static(id="spec-constraints", classes="phase-panel")
        constraints.border_title = "Constraints"
        constraints.display = False
        yield constraints

    async def show(self, detail: model.PhaseDetail, colors: dict[str, str], width: int) -> None:
        md = self.query_one("#spec-markdown Markdown", Markdown)
        requirements = self.query_one("#spec-requirements", SpecRequirementList)
        constraints = self.query_one("#spec-constraints", Static)
        if detail.structured:
            body = detail.spec_body.strip()
            await md.update(_spec_markdown(body) if body else "")
            self.query_one("#spec-markdown").display = bool(body)
            rows = detail.evidence.requirements if detail.evidence is not None else ()
            requirements.display = bool(rows)
            if rows:
                requirements.fill(rows)
            constraints.display = bool(detail.constraints)
            if detail.constraints:
                constraints.update(Text("\n".join(record.text for record in detail.constraints)))
        else:
            body = detail.body.strip()
            await md.update(body)
            self.query_one("#spec-markdown").display = bool(body)
            requirements.display = False
            constraints.display = bool(detail.constraints)
            if detail.constraints:
                constraints.update(Text("\n".join(record.text for record in detail.constraints)))

    def pager_text(self) -> str:
        detail = self.screen.detail if isinstance(self.screen, PhaseScreen) else None
        if detail is None:
            return ""
        if detail.structured:
            parts = [detail.spec_body.strip()]
            if detail.constraints:
                parts.append("## Constraints\n\n" + "\n".join(f"- {c.text}" for c in detail.constraints))
            return "\n\n".join(p for p in parts if p).strip() + "\n"
        parts = [detail.body.strip()]
        if detail.constraints:
            parts.append("## Constraints\n\n" + "\n".join(f"- {c.text}" for c in detail.constraints))
        return "\n\n".join(p for p in parts if p).strip() + "\n"


class DesignPane(VerticalScroll):
    def compose(self):
        yield Markdown(id="design-markdown")

    async def show(self, detail: model.PhaseDetail, colors: dict[str, str], width: int) -> None:
        await self.query_one("#design-markdown", Markdown).update(detail.design_body.strip())

    def pager_text(self) -> str:
        detail = self.screen.detail if isinstance(self.screen, PhaseScreen) else None
        if detail is None:
            return ""
        return (detail.design_body.strip() + "\n") if detail.design_body.strip() else ""


class DecisionsPane(VerticalScroll):
    def compose(self):
        yield Static(id="decisions-hint")
        yield DecisionsList(id="phase-decisions-list")

    def show(self, detail: model.PhaseDetail, colors: dict[str, str], width: int) -> None:
        screen = self.screen
        if not isinstance(screen, PhaseScreen):
            return
        hint = Text(no_wrap=True, overflow="ellipsis")
        scope = "effort" if screen.decisions_effort else "phase"
        hist = "on" if screen.decisions_history else "off"
        hint.append(f"scope {scope} (a) · history {hist} (h)", style=colors["muted"])
        self.query_one("#decisions-hint", Static).update(hint)
        if screen.decision_log is None:
            screen.load_decisions()
            return
        self.query_one("#phase-decisions-list", DecisionsList).fill(
            screen.decision_log, colors,
            history=screen.decisions_history,
            show_groups=screen.decisions_effort,
        )

    def pager_text(self) -> str:
        screen = self.screen
        if not isinstance(screen, PhaseScreen) or screen.decision_log is None:
            return ""
        lines: list[str] = ["# Decisions", ""]
        for title, group in screen.decision_log.groups:
            if screen.decisions_effort:
                lines.extend([f"## {title}", ""])
            for entry in group:
                lines.append(f"### {entry.subject}")
                lines.append(f"Choice: {entry.choice}")
                if entry.alternatives:
                    lines.append(f"Alternatives: {entry.alternatives}")
                if entry.rationale:
                    lines.append(f"Rationale: {entry.rationale}")
                if entry.counter:
                    lines.append(f"Counter: {entry.counter}")
                if screen.decisions_history and entry.superseded:
                    for child in entry.superseded:
                        lines.append(f"- supersedes {child.subject}: {child.choice}")
                lines.append("")
        return "\n".join(lines).strip() + "\n"


class EvidencePane(VerticalScroll):
    def compose(self):
        yield Static(id="phase-spec", classes="phase-panel")
        design = Static(id="phase-design", classes="phase-panel")
        design.border_title = "Design"
        design.display = False
        yield design
        release = Static(id="evidence-release")
        release.display = False
        yield release
        requirements = RequirementMatrix(id="phase-requirements")
        requirements.add_class("phase-panel")
        requirements.border_title = "Requirements"
        requirements.display = False
        yield requirements
        integration = Static(id="evidence-integration", classes="phase-panel")
        integration.border_title = "Integration"
        integration.display = False
        yield integration

    def show(self, detail: model.PhaseDetail, colors: dict[str, str], width: int) -> None:
        evidence = detail.evidence
        inner = max(width - 4, 8)
        spec = self.query_one("#phase-spec", Static)
        design = self.query_one("#phase-design", Static)
        release = self.query_one("#evidence-release", Static)
        integration = self.query_one("#evidence-integration", Static)
        requirements = self.query_one("#phase-requirements", RequirementMatrix)
        if evidence is None:
            spec.display = False
            design.display = False
            release.display = False
            integration.display = False
            requirements.display = False
            return
        spec.border_title = "Specification"
        spec_text = evidence.weight
        if evidence.non_goals.strip():
            spec_text = f"{spec_text}\n{evidence.non_goals.strip()}"
        spec.update(wrap_block(spec_text, inner))
        spec.display = True
        design.display = bool(evidence.decisions)
        if design.display:
            design.update(wrap_block(
                "\n".join(f"{item.subject}: {item.choice}" for item in evidence.decisions), inner,
            ))
        release.display = True
        release.update(matrix_mod.release_line(evidence, inner))
        requirements.display = bool(evidence.requirements)
        if requirements.display:
            requirements.fill(evidence.requirements, inner, colors)
        integration.display = evidence.integration is not None
        if integration.display and evidence.integration is not None:
            report = evidence.integration
            integration.update(wrap_block(f"{report.result}\nConflicts\n{report.conflicts}", inner))

    def pager_text(self) -> str:
        detail = self.screen.detail if isinstance(self.screen, PhaseScreen) else None
        if detail is None or detail.evidence is None:
            return ""
        evidence = detail.evidence
        lines = ["# Evidence", "", f"Weight: {evidence.weight}", ""]
        if evidence.non_goals.strip():
            lines.extend(["## Non-goals", "", evidence.non_goals.strip(), ""])
        lines.append(matrix_mod.release_line(evidence, 120).plain)
        lines.append("")
        if evidence.requirements:
            lines.append("## Requirements")
            lines.append("")
            for row in evidence.requirements:
                lines.append(
                    f"- {row.id} {row.text} ({row.tasks_done}/{row.tasks}) "
                    f"{_check_glyph(row)} {row.status} {row.next}".rstrip()
                )
            lines.append("")
        if evidence.integration is not None:
            lines.extend([
                "## Integration", "",
                evidence.integration.result, "",
                "Conflicts", "", evidence.integration.conflicts, "",
            ])
        return "\n".join(lines).strip() + "\n"


class TasksPane(VerticalScroll):
    def compose(self):
        tasks = PhaseTaskList(id="phase-tasks")
        tasks.add_class("phase-panel")
        tasks.border_title = "Tasks"
        yield tasks

    def show(self, detail: model.PhaseDetail, colors: dict[str, str], width: int) -> None:
        tasks = self.query_one("#phase-tasks", PhaseTaskList)
        tasks.display = bool(detail.tasks)
        tasks.fill(detail.tasks, colors)

    def pager_text(self) -> str:
        detail = self.screen.detail if isinstance(self.screen, PhaseScreen) else None
        if detail is None:
            return ""
        lines = ["# Tasks", ""]
        for task in detail.tasks:
            lines.append(f"- {task.status}: {task.title or task.subject}")
        return "\n".join(lines).strip() + "\n"


PANE_TYPES = {
    "overview": OverviewPane,
    "spec": SpecPane,
    "design": DesignPane,
    "decisions": DecisionsPane,
    "evidence": EvidencePane,
    "tasks": TasksPane,
}


class PhaseScreen(Screen[None]):
    CSS = """
    #phase-bar { height: 1; padding: 0 1; background: $panel; }
    #phase-error { height: auto; padding: 0 1; background: $error 20%; color: $error; display: none; }
    #phase-tabs { height: 1fr; }
    #phase-tabs ContentSwitcher { height: 1fr; }
    #phase-tabs TabPane { padding: 0 1; height: 1fr; }
    #phase-loading { margin-top: 1; color: $text-muted; }
    .phase-panel { height: auto; margin-top: 1; border: round $panel; border-title-color: $text-muted; padding: 0 1; }
    #phase-body Markdown { margin: 0; padding: 0; background: transparent; }
    #phase-body Markdown > MarkdownBlock { margin: 1 0 0 0; }
    #phase-body Markdown > MarkdownHeader { margin: 0; }
    #phase-body Markdown > MarkdownBlock:first-child { margin-top: 0; }
    #spec-markdown Markdown { margin: 0; padding: 0; background: transparent; }
    #spec-markdown Markdown > MarkdownBlock { margin: 1 0 0 0; }
    #spec-markdown Markdown > MarkdownHeader { margin: 0; }
    #spec-markdown Markdown > MarkdownBlock:first-child { margin-top: 0; }
    #design-markdown { margin-top: 1; }
    #design-markdown MarkdownBlock { margin: 1 0 0 0; }
    #design-markdown MarkdownHeader { margin: 0; }
    #phase-tasks { height: auto; max-height: 1000; background: transparent; }
    #phase-tasks:focus { border: round $accent; }
    #evidence-release { margin-top: 1; }
    #phase-requirements { height: auto; max-height: 1000; background: transparent; }
    #phase-requirements:focus { border: round $accent; }
    #spec-requirements { height: auto; max-height: 1000; background: transparent; }
    #spec-requirements:focus { border: round $accent; }
    #phase-decisions-list { height: auto; max-height: 1000; background: transparent; }
    #phase-decisions-list:focus { border: round $accent; }
    #phase-progress { height: 1; margin-top: 1; }
    #phase-progress-label { margin-top: 1; color: $text-muted; }
    #phase-next-step { margin-top: 1; }
    #phase-landing { margin-top: 1; color: $text-muted; }
    #decisions-hint { margin-top: 1; color: $text-muted; }
    """
    BINDINGS = [
        Binding("escape", "back", "back"),
        Binding("c", "app.copy_slug", "copy"),
        Binding("r", "app.refresh", "refresh"),
        Binding("left", "step_tab(-1)", "prev tab", show=False),
        Binding("right", "step_tab(1)", "next tab", show=False),
        Binding("p", "goto_tab('overview')", "overview", show=False),
        Binding("s", "goto_tab('spec')", "spec", show=False),
        Binding("d", "goto_tab('decisions')", "decisions", show=False),
        Binding("e", "goto_tab('evidence')", "evidence", show=False),
        Binding("t", "goto_tab('tasks')", "tasks", show=False),
        Binding("[", "neighbor_phase(-1)", "prev phase", show=False),
        Binding("]", "neighbor_phase(1)", "next phase", show=False),
        Binding("a", "toggle_decisions_effort", "effort scope", show=False),
        Binding("h", "toggle_decisions_history", "history", show=False),
        Binding("o", "page_tab", "pager", show=False),
    ]

    def __init__(
        self,
        target: artifact_store.Target,
        effort: str,
        phase: str,
        tab: str = "overview",
    ) -> None:
        super().__init__()
        self.target = target
        self.effort = effort
        self.phase_subject = phase
        self.initial_tab = tab if tab in model.TABS else "overview"
        self.detail: model.PhaseDetail | None = None
        self.loaded = False
        self.token: str | None = None
        self.loaded_at = 0.0
        self.available_tabs: tuple[str, ...] = model.TABS
        self._trimmed = False
        self.decisions_effort = False
        self.decisions_history = False
        self.decision_log: model.DecisionLog | None = None
        self._decisions_loading = False

    def compose(self):
        yield Static(id="phase-bar")
        yield Static(id="phase-error")
        yield Static("Loading…", id="phase-loading")
        with TabbedContent(id="phase-tabs"):
            for name in model.TABS:
                with TabPane(TAB_LABELS[name], id=name):
                    yield PANE_TYPES[name](id=f"pane-{name}")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#phase-tabs").display = False
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
        self.available_tabs = model.tabs_for(detail)
        self.query_one("#phase-error", Static).display = False
        self.query_one("#phase-loading", Static).display = False
        tabs = self.query_one("#phase-tabs", TabbedContent)
        tabs.display = True
        if not self._trimmed:
            for name in model.TABS:
                if name not in self.available_tabs:
                    await tabs.remove_pane(name)
            self._trimmed = True
        bar = Text(no_wrap=True, overflow="ellipsis")
        bar.append(detail.title or detail.subject, style="bold")
        bar.append(f"  {detail.effort}", style=colors["muted"])
        self.query_one("#phase-bar", Static).update(bar)
        width = max(self.size.width - 4, 20)
        for name in self.available_tabs:
            pane = self.query_one(f"#pane-{name}", Widget)
            result = pane.show(detail, colors, width)
            if hasattr(result, "__await__"):
                await result
        want = self.initial_tab if self.initial_tab in self.available_tabs else "overview"
        if not self.loaded:
            tabs.active = want
            self.initial_tab = want
            if want == "tasks" and detail.tasks:
                self.query_one("#phase-tasks", PhaseTaskList).focus(scroll_visible=False)
            elif want == "evidence" and detail.evidence and detail.evidence.requirements:
                self.query_one("#phase-requirements", RequirementMatrix).focus(scroll_visible=False)
            elif want == "decisions":
                self.load_decisions()
        else:
            current = tabs.active
            if current not in self.available_tabs:
                tabs.active = "overview"
        self.loaded = True

    def active_tab(self) -> str:
        tabs = self.query_one("#phase-tabs", TabbedContent)
        active = tabs.active or "overview"
        return active if active in self.available_tabs else "overview"

    def active_pane(self) -> Widget | None:
        name = self.active_tab()
        try:
            return self.query_one(f"#pane-{name}", Widget)
        except Exception:
            return None

    def action_goto_tab(self, name: str) -> None:
        if name not in self.available_tabs:
            return
        self.query_one("#phase-tabs", TabbedContent).active = name
        self.initial_tab = name
        if name == "decisions":
            self.load_decisions()
        elif name == "tasks" and self.detail and self.detail.tasks:
            self.query_one("#phase-tasks", PhaseTaskList).focus(scroll_visible=False)
        elif (
            name == "evidence"
            and self.detail
            and self.detail.evidence
            and self.detail.evidence.requirements
        ):
            self.query_one("#phase-requirements", RequirementMatrix).focus(scroll_visible=False)

    def action_step_tab(self, delta: int) -> None:
        if not self.available_tabs:
            return
        current = self.active_tab()
        index = self.available_tabs.index(current) if current in self.available_tabs else 0
        self.action_goto_tab(self.available_tabs[(index + delta) % len(self.available_tabs)])

    def action_neighbor_phase(self, delta: int) -> None:
        view = self.app.effort_view(self.effort) if hasattr(self.app, "effort_view") else None
        if view is None or not view.phases:
            return
        ordered = sorted(view.phases, key=lambda row: (row.ordinal, row.subject))
        subjects = [row.subject for row in ordered]
        if self.phase_subject not in subjects:
            return
        index = subjects.index(self.phase_subject) + delta
        if index < 0 or index >= len(subjects):
            return
        neighbor = subjects[index]
        tab = self.active_tab()
        target = self.target
        effort = self.effort
        app = self.app
        app.pop_screen()
        app.push_screen(PhaseScreen(target, effort, neighbor, tab=tab))

    def action_toggle_decisions_effort(self) -> None:
        if self.active_tab() != "decisions":
            return
        self.decisions_effort = not self.decisions_effort
        self.decision_log = None
        self.load_decisions()

    def action_toggle_decisions_history(self) -> None:
        if self.active_tab() != "decisions":
            return
        self.decisions_history = not self.decisions_history
        self.decision_log = None
        self.load_decisions()

    def refresh_decisions(self) -> None:
        if self.detail is None or self.decision_log is None:
            return
        colors = palette_from(self.app.get_css_variables())
        width = max(self.size.width - 4, 20)
        self.query_one("#pane-decisions", DecisionsPane).show(self.detail, colors, width)

    @work(thread=True, exclusive=True, group="phase-decisions")
    def load_decisions(self) -> None:
        if self._decisions_loading:
            return
        self._decisions_loading = True
        try:
            phase = None if self.decisions_effort else self.phase_subject
            log = model.load_decision_log(self.target, self.effort, phase, self.decisions_history)
        except (OSError, model.ModelError) as exc:
            self.app.call_from_thread(self.show_error, str(exc))
            return
        finally:
            self._decisions_loading = False
        self.app.call_from_thread(self._apply_decisions, log)

    def _apply_decisions(self, log: model.DecisionLog) -> None:
        if not self.is_attached:
            return
        self.decision_log = log
        if self.detail is None:
            return
        colors = palette_from(self.app.get_css_variables())
        width = max(self.size.width - 4, 20)
        self.query_one("#pane-decisions", DecisionsPane).show(self.detail, colors, width)

    def action_page_tab(self) -> None:
        pane = self.active_pane()
        if pane is None or not hasattr(pane, "pager_text"):
            return
        text = pane.pager_text()
        suspend = getattr(self.app, "suspend", None)
        context = suspend() if callable(suspend) else nullcontext()
        try:
            with context:
                pager.page_text(text)
        except Exception:
            pager.page_text(text)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        selected = event.option_list
        if isinstance(selected, SpecRequirementList):
            if event.option_index >= len(selected.rows):
                return
            event.stop()
            from dashboard.requirement_detail import RequirementDetailScreen

            row = selected.rows[event.option_index]
            self.app.push_screen(
                RequirementDetailScreen(self.target, self.effort, self.phase_subject, row.id)
            )
            return
        if isinstance(selected, DecisionsList):
            event.stop()
            selected.action_toggle_expand()
            return
        if not isinstance(selected, PhaseTaskList) or event.option_index >= len(selected.tasks):
            return
        event.stop()
        self.app.push_screen(TaskDetailScreen(self.target, selected.tasks[event.option_index].id))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = event.data_table
        if not isinstance(table, RequirementMatrix):
            return
        event.stop()
        key = event.row_key.value if event.row_key is not None else None
        if not key:
            return
        from dashboard.requirement_detail import RequirementDetailScreen

        self.app.push_screen(
            RequirementDetailScreen(self.target, self.effort, self.phase_subject, str(key))
        )


# Backward-compatible name used by older tests and task_detail imports.
PhaseDetailScreen = PhaseScreen
