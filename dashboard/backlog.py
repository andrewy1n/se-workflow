"""Promote and dismiss backlog items via the adaptive-artifacts CLI."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

from dashboard.artifact_store import Target, binary
from dashboard.model import BacklogItem

BACKLOG_TYPE = "project:backlog-item"


class BacklogError(Exception):
    """CLI or validation failure while changing a backlog item."""


class BacklogRefused(BacklogError):
    """Record is not an open backlog item the dashboard can act on."""


@dataclass(frozen=True)
class BacklogResult:
    ok: bool
    message: str = ""


def is_backlog(item: BacklogItem) -> bool:
    record_type = item.record_type or BACKLOG_TYPE
    return record_type == BACKLOG_TYPE and item.status == "open"


def prompt(item: BacklogItem, effort: str | None = None) -> str:
    """Agent prompt to continue with discuss (or incidental) after promote."""
    named = effort or item.effort
    return (
        f"Promote backlog item {item.subject} (effort {named}): "
        f"start discuss for a new phase, or an incidental work-item if that fits."
    )


def _cli(target: Target, *args: str) -> subprocess.CompletedProcess[str]:
    command = [binary(), *target.cli_args(), *args]
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BacklogError(f"cannot run {command[0]}: {exc}") from exc


def _fail(result: subprocess.CompletedProcess[str], label: str) -> None:
    detail = (result.stdout or result.stderr or "").strip() or f"exit {result.returncode}"
    raise BacklogError(f"{label} failed: {detail.splitlines()[0]}")


def _successor_payload(item: BacklogItem, status: str, *, phase: str | None = None) -> dict:
    payload: dict = {"effort": item.effort, "status": status}
    if item.source:
        payload["source"] = item.source
    chosen = phase if phase is not None else item.phase
    if chosen:
        payload["phase"] = chosen
    return payload


def _supersede_args(item: BacklogItem, status: str, *, phase: str | None = None) -> list[str]:
    if not is_backlog(item):
        raise BacklogRefused(f"cannot act on {item.record_type or 'non-backlog'}")
    return [
        "supersede", "--type", BACKLOG_TYPE, "--id", item.id,
        "--expected-revision", "@current",
        "--payload", json.dumps(_successor_payload(item, status, phase=phase)),
    ]


def promote_command(item: BacklogItem, *, phase: str | None = None) -> list[str]:
    """Return adaptive-artifacts argv to supersede status=promoted."""
    return _supersede_args(item, "promoted", phase=phase)


def dismiss_command(item: BacklogItem) -> list[str]:
    """Return adaptive-artifacts argv to supersede status=dismissed."""
    return _supersede_args(item, "dismissed")


def promote_item(target: Target, item: BacklogItem, *, phase: str | None = None) -> None:
    """Supersede an open backlog item to promoted."""
    args = promote_command(item, phase=phase)
    result = _cli(target, *args)
    if result.returncode != 0:
        _fail(result, " ".join(args[:3]))


def dismiss_item(target: Target, item: BacklogItem) -> None:
    """Supersede an open backlog item to dismissed."""
    args = dismiss_command(item)
    result = _cli(target, *args)
    if result.returncode != 0:
        _fail(result, " ".join(args[:3]))
