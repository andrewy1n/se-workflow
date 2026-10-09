"""Pure helpers for the Evidence matrix, release line, and requirement strip."""

from __future__ import annotations

from rich.text import Text

from dashboard.model import UPSTREAM_NEXT, PhaseEvidence, RequirementRow

FULL_COLUMNS = ("id", "text", "tasks", "check", "kind", "age", "status", "next")


def row_tone(row: RequirementRow) -> str:
    failed_check = row.latest_check is not None and row.latest_check.result == "fail"
    if failed_check or row.status == "blocked":
        return "error"
    if row.next in UPSTREAM_NEXT or row.confidence == "low":
        return "warning"
    if row.status == "unassessed":
        return "muted"
    return "default"


def glyph(row: RequirementRow) -> str:
    failed_check = row.latest_check is not None and row.latest_check.result == "fail"
    if row.status == "verified":
        return "✓"
    if failed_check or row.status == "blocked":
        return "✗"
    if row.next in UPSTREAM_NEXT:
        return "↑"
    if row.status == "unassessed":
        return "◌"
    return "·"


def blockers(evidence: PhaseEvidence) -> list[str]:
    items: list[str] = []
    for row in evidence.requirements:
        if row.status == "verified":
            continue
        if row.next:
            items.append(f"{row.id} → {row.next}")
        else:
            items.append(f"{row.id} {row.status}")
    return items


def matrix_columns(width: int) -> list[str]:
    columns = list(FULL_COLUMNS)
    if width < 60:
        columns = [name for name in columns if name != "text"]
    if width < 45:
        columns = [name for name in columns if name not in ("kind", "age")]
    return columns


def release_line(evidence: PhaseEvidence, width: int) -> Text:
    state = evidence.release_state or "no release"
    total = len(evidence.requirements)
    verified = sum(1 for row in evidence.requirements if row.status == "verified")
    prefix = f"{state} · {verified}/{total} verified"
    width = max(width, 1)
    items = blockers(evidence)

    def join(shown: list[str], more: int) -> str:
        parts = [prefix, *shown]
        if more:
            parts.append(f"+{more} more")
        return " · ".join(parts)

    shown: list[str] = []
    for index, item in enumerate(items):
        if len(join(shown + [item], 0)) <= width:
            shown.append(item)
            continue
        more = len(items) - index
        line = join(shown, more)
        while shown and len(line) > width:
            shown.pop()
            line = join(shown, more)
        if len(line) > width:
            line = prefix if len(prefix) <= width else prefix[: max(width - 1, 1)] + "…"
            if len(line) > width:
                line = line[:width]
        return Text(line)
    line = join(shown, 0)
    if len(line) > width:
        line = line[: max(width - 1, 1)] + "…"
    return Text(line)
