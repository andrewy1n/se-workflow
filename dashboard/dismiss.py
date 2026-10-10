"""Dismiss human Needs-you items via the adaptive-artifacts CLI."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass

from dashboard.artifact_store import Target, binary
from dashboard.model import NeedsYouItem

HUMAN_DISMISSIBLE = frozenset({
    "blocking-question", "open-question", "needs-human", "unsigned-check",
})

DEFAULT_SIGNER_ENV = "SE_WORKFLOW_SIGNED_BY"


class DismissError(Exception):
    """CLI or validation failure while dismissing."""


class DismissRefused(DismissError):
    """Item kind is not human-dismissible from the dashboard."""


@dataclass(frozen=True)
class DismissResult:
    ok: bool
    message: str = ""


def is_dismissible(kind: str) -> bool:
    return kind in HUMAN_DISMISSIBLE


def default_signer() -> str:
    return (
        os.environ.get(DEFAULT_SIGNER_ENV)
        or os.environ.get("USER")
        or os.environ.get("USERNAME")
        or "dashboard"
    )


def _cli(target: Target, *args: str) -> subprocess.CompletedProcess[str]:
    command = [binary(), *target.cli_args(), *args]
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DismissError(f"cannot run {command[0]}: {exc}") from exc


def _fail(result: subprocess.CompletedProcess[str], label: str) -> None:
    detail = (result.stdout or result.stderr or "").strip() or f"exit {result.returncode}"
    raise DismissError(f"{label} failed: {detail.splitlines()[0]}")


def _question_args(item: NeedsYouItem) -> list[str]:
    record_type = item.record_type or "project:continuity-question"
    return [
        "update", "--type", record_type, "--id", item.id,
        "--transition", "answered", "--expected-revision", "@current",
    ]


def _finding_args(item: NeedsYouItem) -> list[str]:
    # Findings advertise supersedes but have no superseded lifecycle state, so
    # the supersede command is illegal; update needs to none is the clear.
    record_type = item.record_type or "project:finding"
    return [
        "update", "--type", record_type, "--id", item.id,
        "--expected-revision", "@current",
        "--payload", json.dumps({"needs": "none"}),
    ]


def _check_args(item: NeedsYouItem, signer: str) -> list[str]:
    record_type = item.record_type or "project:check-run"
    return [
        "correct", "--type", record_type, "--id", item.id,
        "--payload", json.dumps({"signed_by": signer}),
    ]


def dismiss_command(item: NeedsYouItem, *, signer: str | None = None) -> list[str]:
    """Return the adaptive-artifacts argv (after root/store/contract) for this item."""
    if not is_dismissible(item.kind):
        raise DismissRefused(f"cannot dismiss {item.kind}")
    if item.kind in ("blocking-question", "open-question"):
        return _question_args(item)
    if item.kind == "needs-human":
        return _finding_args(item)
    return _check_args(item, signer or default_signer())


def dismiss_item(target: Target, item: NeedsYouItem, *, signer: str | None = None) -> None:
    """Invoke adaptive-artifacts to clear a human-dismissible Needs-you item.

    Raises DismissRefused for non-human kinds and DismissError when the CLI fails.
    """
    args = dismiss_command(item, signer=signer)
    result = _cli(target, *args)
    if result.returncode != 0:
        _fail(result, " ".join(args[:3]))
