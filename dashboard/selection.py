"""Phase selection state and derived rendering for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from rich.text import Text

from dashboard import gates, matrix as matrix_mod, model
from dashboard.display import (
    ACTIVITY_GLYPH, ACTIVITY_LINES, ANSI_PALETTE, PHASE_GLYPH, STATUS_GLYPH, clip, relative_time,
)


@dataclass(frozen=True)
class PhaseSelection:
    """Pinned phase selection for one effort. pinned=None and all_phases=False means follow the default."""

    pinned: str | None = None
    all_phases: bool = False


@dataclass(frozen=True)
class MergedActivity:
    kind: str
    subjects: tuple[str, ...]
    summary: str
    recorded_at: datetime
    failed: bool


def _task_phase_map(view: model.EffortView) -> dict[str, str]:
    return {task.subject: task.phase for task in view.tasks}


def _phase_activity_time(view: model.EffortView, phase: str) -> datetime | None:
    by_subject = _task_phase_map(view)
    stamps = [
        item.recorded_at for item in view.activity
        if by_subject.get(item.subject) == phase
    ]
    return max(stamps) if stamps else None


def default_phase(view: model.EffortView) -> str | None:
    """Return the default phase subject, or None for All phases."""
    if not view.phases:
        return None
    in_progress = [phase for phase in view.phases if phase.state == "in_progress"]
    if in_progress:
        if len(in_progress) == 1:
            return in_progress[0].subject
        ranked = [
            (phase, _phase_activity_time(view, phase.subject))
            for phase in in_progress
        ]

        def key(item: tuple[model.PhaseRow, datetime | None]) -> tuple:
            phase, stamp = item
            if stamp is None:
                return (1, 0, phase.ordinal, phase.subject)
            return (0, -stamp.timestamp(), phase.ordinal, phase.subject)

        return min(ranked, key=key)[0].subject
    planned = [phase for phase in view.phases if phase.state == "planned"]
    if planned:
        return min(planned, key=lambda phase: (phase.ordinal, phase.subject)).subject
    return None


def resolve_selection(view: model.EffortView, selection: PhaseSelection) -> str | None:
    """Resolve a selection to a phase subject, or None for All phases."""
    default = default_phase(view)
    if selection.all_phases:
        return None
    if selection.pinned is None:
        return default
    if any(phase.subject == selection.pinned for phase in view.phases):
        return selection.pinned
    return default


def pick(view: model.EffortView, target: str | None) -> PhaseSelection:
    """Select a phase; choosing the current default resumes following it."""
    if target == default_phase(view):
        return PhaseSelection()
    if target is None:
        return PhaseSelection(all_phases=True)
    return PhaseSelection(pinned=target)


def step_selection(view: model.EffortView, selection: PhaseSelection, delta: int) -> PhaseSelection:
    """Step to the previous/next phase in ordinal order, with All phases last; stop at ends."""
    current = resolve_selection(view, selection)
    subjects = [phase.subject for phase in sorted(view.phases, key=lambda p: (p.ordinal, p.subject))]
    options: list[str | None] = subjects + [None]
    try:
        index = options.index(current)
    except ValueError:
        index = -1
    new_index = max(0, min(len(options) - 1, index + delta))
    return pick(view, options[new_index])


def scoped(view: model.EffortView, subject: str | None) -> model.EffortView:
    """Return a view whose task list is scoped to one phase, or the original for All phases."""
    if subject is None:
        return view
    return model.EffortView(
        effort=view.effort,
        goal=view.goal,
        phases=view.phases[:],
        tasks=[task for task in view.tasks if task.phase == subject],
        needs_you=view.needs_you[:],
        activity=view.activity[:],
        release_ready=view.release_ready,
        position=view.position,
    )


def _phase_segment(
    phase: model.PhaseRow, selected: str | None, colors: dict[str, str], *, planned: bool = False,
    landing_suffix: str = "",
) -> Text:
    glyph = PHASE_GLYPH.get(phase.state, "·")
    title = phase.title or phase.subject
    head = f"{glyph} {title}"
    if phase.state == "in_progress":
        head += f" {phase.done}/{phase.total}"
    text = Text(head)
    if phase.state == "in_progress" and phase.evidence is not None and not planned:
        text.append(f" · {phase.evidence.stage}")
    is_selected = phase.subject == selected
    base = colors["primary"] if phase.state == "in_progress" else colors["muted"]
    if planned:
        base = colors["muted"]
    text.stylize(base)
    if is_selected:
        text.stylize("reverse")
    if landing_suffix and phase.subject == selected:
        text.append(f" · {landing_suffix}", style=colors["muted"])
    text.apply_meta({"target": f"phase:{phase.subject}"})
    return text


def _requirement_strip(phase: model.PhaseRow, colors: dict[str, str]) -> Text | None:
    evidence = phase.evidence
    if evidence is None or not evidence.requirements:
        return None
    verified = sum(row.status == "verified" for row in evidence.requirements)
    total = len(evidence.requirements)
    text = Text(f"R {verified}/{total} verified ", style=colors["muted"])
    for row in evidence.requirements:
        tone = matrix_mod.row_tone(row)
        style = "" if tone == "default" else colors.get(tone, "")
        text.append(matrix_mod.glyph(row), style=style)
    text.apply_meta({"target": f"evidence:{phase.subject}"})
    return text


def selector_segments(
    view: model.EffortView, selected: str | None, colors: dict[str, str],
    landing_suffix: str = "",
) -> list[Text]:
    """Build clickable selector segments: done count/selected done, in-progress, next, All phases."""
    segments: list[Text] = []
    done_phases = [phase for phase in view.phases if phase.state == "done"]
    selected_phase = next((phase for phase in view.phases if phase.subject == selected), None)

    if selected_phase is not None and selected_phase.state == "done":
        segments.append(_phase_segment(selected_phase, selected, colors, landing_suffix=landing_suffix))
        strip = _requirement_strip(selected_phase, colors)
        if strip is not None:
            segments.append(strip)
    elif done_phases:
        done_text = Text(f"{len(done_phases)} done", style=colors["muted"])
        done_text.apply_meta({"target": "picker"})
        segments.append(done_text)

    for phase in view.phases:
        if phase.state == "in_progress":
            segments.append(_phase_segment(phase, selected, colors, landing_suffix=landing_suffix))
            if phase.subject == selected:
                strip = _requirement_strip(phase, colors)
                if strip is not None:
                    segments.append(strip)

    planned = [phase for phase in view.phases if phase.state == "planned"]
    if planned:
        next_phase = min(planned, key=lambda phase: (phase.ordinal, phase.subject))
        segments.append(_phase_segment(next_phase, selected, colors, planned=True, landing_suffix=landing_suffix))
        if next_phase.subject == selected:
            strip = _requirement_strip(next_phase, colors)
            if strip is not None:
                segments.append(strip)

    all_style = colors["primary"] if selected is None else colors["muted"]
    all_text = Text("All phases", style=all_style)
    if selected is None:
        all_text.stylize("reverse")
    all_text.apply_meta({"target": "all"})
    segments.append(all_text)
    return segments


def selector_text(
    view: model.EffortView, selected: str | None, colors: dict[str, str], width: int,
    landing_suffix: str = "",
) -> Text:
    """Lay out selector segments with wrapping and clipping to the given width."""
    segments = selector_segments(view, selected, colors, landing_suffix=landing_suffix)
    text = Text()
    used = 0
    for index, label in enumerate(segments):
        label.truncate(max(width, 3), overflow="ellipsis")
        if index:
            gap = 3
            if used + gap + label.cell_len > width:
                text.append("\n")
                used = 0
            else:
                text.append("   ")
                used += gap
        text.append_text(label)
        used += label.cell_len
    return text


_FINISH_RANK = {"waiting": 0, "ready": 1, "running": 2, "done": 3, "withdrawn": 4}


def _least_finished(tasks: list[model.TaskRow]) -> model.TaskRow:
    return min(tasks, key=lambda task: _FINISH_RANK.get(task.status, len(_FINISH_RANK)))


def wave_strip(
    view: model.EffortView,
    subject: str,
    width: int,
    colors: dict[str, str] | None = None,
    now: datetime | None = None,
) -> Text:
    """Render a wave strip for the selected phase."""
    colors = colors or ANSI_PALETTE
    now = now or datetime.now(timezone.utc)
    tasks = [task for task in view.tasks if task.phase == subject and task.status != "withdrawn"]
    groups: dict[Any, list[model.TaskRow]] = {}
    for task in tasks:
        key = task.wave if task.wave is not None else 0
        groups.setdefault(key, []).append(task)
    if not groups:
        return Text()

    def order(key: Any) -> tuple:
        return (0, key) if isinstance(key, int) else (1, str(key))

    ordered = sorted(groups.items(), key=order)

    def append_glyph(text: Text, task: model.TaskRow) -> None:
        glyph = STATUS_GLYPH.get(task.status, "·")
        if gates.is_quiet(task, now):
            text.append(glyph, style=colors["warning"])
        else:
            text.append(glyph)

    def render(compact: bool) -> Text:
        text = Text()
        for wave, members in ordered:
            if text:
                text.append("  ")
            text.append(f"w{wave} ")
            if compact:
                append_glyph(text, _least_finished(members))
            else:
                for task in sorted(members, key=lambda t: model.TASK_ORDER.index(t.status)):
                    append_glyph(text, task)
        return text

    full = render(False)
    return full if full.cell_len <= width else render(True)


def _activity_parts(item: model.ActivityItem) -> tuple[str, str]:
    parts = item.summary.split(None, 1)
    subject = parts[0]
    tail = parts[1] if len(parts) > 1 else ""
    return subject, tail


def merge_activity(items: list[model.ActivityItem]) -> list[MergedActivity]:
    """Merge consecutive activity items of the same kind and outcome."""
    if not items:
        return []
    groups: list[list[model.ActivityItem]] = []
    current: list[model.ActivityItem] = [items[0]]
    for item in items[1:]:
        same = (
            item.kind == current[-1].kind
            and item.failed == current[-1].failed
            and _activity_parts(item)[1] == _activity_parts(current[-1])[1]
        )
        if same:
            current.append(item)
        else:
            groups.append(current)
            current = [item]
    groups.append(current)

    result: list[MergedActivity] = []
    for group in groups:
        first = group[0]
        subjects = tuple(_activity_parts(item)[0] for item in group)
        tail = _activity_parts(first)[1]
        result.append(MergedActivity(first.kind, subjects, tail, first.recorded_at, first.failed))
    return result


def activity_lines(view: model.EffortView, now: datetime, colors: dict[str, str], width: int = 100) -> list[Text]:
    """Render merged activity lines for an effort view."""
    lines: list[Text] = []
    for item in merge_activity(view.activity[:ACTIVITY_LINES]):
        line = Text(no_wrap=True, overflow="ellipsis")
        line.append(f"{relative_time(item.recorded_at, now):>7}", style=colors["muted"])
        style = colors["error"] if item.failed else ""
        glyph = "✗" if item.failed else ACTIVITY_GLYPH.get(item.kind, "·")
        line.append(f" {glyph} ", style=style)
        if item.kind == "assessment":
            text = f"{' '.join(item.subjects)} {item.summary}"
        else:
            if len(item.subjects) == 1:
                text = f"{item.subjects[0]} {item.summary}"
            else:
                joined = ", ".join(item.subjects)
                text = f"{len(item.subjects)} {item.summary}: {joined}"
        line.append(clip(text, max(width - 10, 10)), style=style)
        lines.append(line)
    return lines


def visible_efforts(snapshot: model.Snapshot, show_finished: bool) -> tuple[list[model.EffortView], int]:
    """Return the efforts to display and the count of hidden finished efforts."""
    live = [view for view in snapshot.efforts if not view.finished]
    finished = [view for view in snapshot.efforts if view.finished]
    always_visible = [view for view in finished if view.needs_you]
    optional = [view for view in finished if not view.needs_you]
    shown = live + always_visible + (optional if show_finished else [])
    hidden = len(optional) if not show_finished else 0
    return shown, hidden
