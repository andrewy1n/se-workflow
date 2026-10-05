"""Constants and formatting helpers shared by the dashboard modules."""

from __future__ import annotations

import re
from datetime import datetime

WIDE = 90
STATUS_GLYPH = {"running": "▶", "ready": "●", "waiting": "◌", "done": "✓", "withdrawn": "✕"}
PHASE_GLYPH = {"done": "✓", "in_progress": "●", "planned": "○"}
ACTIVITY_LINES = 10


def elapsed(then: datetime, now: datetime) -> str:
    seconds = max(0, int((now - then).total_seconds()))
    if seconds < 60:
        return "now"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h"


def clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: max(width - 1, 1)] + "…"


REDRAW_SECONDS = 30


ACTIVITY_GLYPH = {"assignment": "→", "execution-report": "≡", "check-run": "◇"}


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
    age = elapsed(then, now)
    return age if age == "now" else f"{age} ago"


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)
