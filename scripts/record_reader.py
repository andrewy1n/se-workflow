"""Read record metadata through the adaptive-artifacts CLI, never bodies."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Iterable
from datetime import datetime, timezone

DEFAULT_TYPES = tuple(
    f"project:{name}"
    for name in (
        "acceptance",
        "active-goal",
        "assignment",
        "assignment-amendment",
        "check-run",
        "constraint",
        "continuity-question",
        "current-position",
        "decision",
        "execution-report",
        "finding",
        "investigation-observation",
        "phase",
        "work-item",
    )
)


class RecordReadError(RuntimeError):
    pass


def subprocess_runner(argv: list[str]) -> str:
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RecordReadError(f"exit code {proc.returncode}")
    return proc.stdout


def _utc(ts: str) -> datetime:
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _metadata(raw: dict, store: str) -> dict:
    payload = raw.get("payload") or {}
    return {
        "id": raw["id"],
        "record_type": raw["record_type"],
        "subject": raw.get("subject"),
        "effort": payload.get("effort"),
        "recorded_at": _utc(raw["recorded_at"]),
        "lifecycle_state": raw.get("lifecycle_state"),
        "store": store,
    }


def read_records(
    root: str,
    types: Iterable[str] | None = None,
    run: Callable[[list[str]], str] = subprocess_runner,
) -> list[dict]:
    store = os.path.basename(os.path.abspath(root))
    store_path = os.path.join(os.path.expanduser("~"), ".artifacts", store)
    rows: list[dict] = []
    for record_type in types if types is not None else DEFAULT_TYPES:
        argv = [
            "adaptive-artifacts", "--root", root, "--store", store_path,
            "--read-only",
            "list", "--type", record_type,
        ]
        try:
            records = json.loads(run(argv))["records"]
            rows.extend(_metadata(r, store) for r in records)
        except Exception as exc:
            raise RecordReadError(
                f"cannot read records of type {record_type} ({type(exc).__name__})"
            ) from None
    return rows
