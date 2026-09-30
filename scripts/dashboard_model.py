"""Dashboard snapshot built from `adaptive-artifacts list` output, one call per record type."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from artifact_store import Target, binary

RECENT = timedelta(hours=24)
TASK_ORDER = ("running", "ready", "waiting", "done", "withdrawn")
NEEDS_ORDER = ("blocking-question", "needs-human", "unsigned-check", "open-question")
LIVE_PHASE_STATES = ("planned", "in_progress", "done")
COUNTED_TASK_STATES = ("planned", "in_progress", "done")
CHECK_RESULT = {"pass": "passed", "fail": "failed"}
TOKEN_DIRS = ("records", "history")


class ModelError(RuntimeError):
    pass


@dataclass(frozen=True)
class PhaseRow:
    subject: str
    title: str
    ordinal: int
    state: str
    done: int
    total: int


@dataclass(frozen=True)
class TaskRow:
    id: str
    subject: str
    title: str
    phase: str
    assignee: str
    wave: int | None
    status: str


@dataclass(frozen=True)
class NeedsYouItem:
    kind: str
    id: str
    subject: str
    text: str


@dataclass(frozen=True)
class ActivityItem:
    kind: str
    id: str
    subject: str
    recorded_at: datetime
    summary: str


@dataclass
class EffortView:
    effort: str
    goal: str
    phases: list[PhaseRow] = field(default_factory=list)
    tasks: list[TaskRow] = field(default_factory=list)
    needs_you: list[NeedsYouItem] = field(default_factory=list)
    activity: list[ActivityItem] = field(default_factory=list)


@dataclass
class Snapshot:
    efforts: list[EffortView]
    token: str
    generated_at: datetime


def change_token(target: Target) -> str:
    """Hash of (path, mtime_ns, size) for every file under the store's records and history.

    One directory walk, no CLI call, and any create, update, or supersede rewrites or adds a file.
    """
    digest = hashlib.sha1()
    assert target.store is not None
    for name in TOKEN_DIRS:
        for directory, subdirs, files in os.walk(target.store / name):
            subdirs.sort()
            for file in sorted(files):
                path = os.path.join(directory, file)
                try:
                    stat = os.stat(path)
                except OSError:
                    continue
                digest.update(f"{path}\0{stat.st_mtime_ns}\0{stat.st_size}\n".encode())
    return digest.hexdigest()


def _list(target: Target, record_type: str) -> list[dict[str, Any]]:
    command = [binary(), *target.cli_args(), "list", "--type", record_type]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ModelError(f"cannot run {command[0]}: {exc}") from exc
    if result.returncode != 0:
        raise ModelError(f"list {record_type} failed: {result.stdout}{result.stderr}".strip())
    try:
        return json.loads(result.stdout)["records"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ModelError(f"list {record_type} returned unreadable output") from exc


def _payload(record: dict[str, Any]) -> dict[str, Any]:
    return record.get("payload") or {}


def _derived(record: dict[str, Any]) -> dict[str, Any]:
    return record.get("derived") or {}


def _recorded_at(record: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(record["recorded_at"])


def _task_status(record: dict[str, Any]) -> str | None:
    state = record["lifecycle_state"]
    if state == "planned":
        return "ready" if _derived(record).get("ready") else "waiting"
    return {"in_progress": "running", "done": "done", "withdrawn": "withdrawn"}.get(state)


def _task_rows(records: list[dict[str, Any]]) -> list[TaskRow]:
    rows = []
    for record in records:
        status = _task_status(record)
        if status is None:
            continue
        payload = _payload(record)
        rows.append(TaskRow(
            id=record["id"], subject=record["subject"], title=payload.get("title", ""),
            phase=payload.get("phase", ""), assignee=payload.get("assignee", ""),
            wave=_derived(record).get("wave"), status=status,
        ))
    rows.sort(key=lambda row: (TASK_ORDER.index(row.status), row.wave if row.wave is not None else 0, row.subject))
    return rows


def _phase_rows(records: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> list[PhaseRow]:
    counted = [task for task in tasks if task["lifecycle_state"] in COUNTED_TASK_STATES]
    rows = []
    for record in records:
        if record["lifecycle_state"] not in LIVE_PHASE_STATES:
            continue
        members = [task for task in counted if _payload(task).get("phase") == record["subject"]]
        payload = _payload(record)
        rows.append(PhaseRow(
            subject=record["subject"], title=payload.get("title", ""), ordinal=payload.get("ordinal", 0),
            state=record["lifecycle_state"], done=sum(t["lifecycle_state"] == "done" for t in members),
            total=len(members),
        ))
    rows.sort(key=lambda row: (row.ordinal, row.subject))
    return rows


def _needs_you(
    questions: list[dict[str, Any]], findings: list[dict[str, Any]], checks: list[dict[str, Any]],
) -> list[NeedsYouItem]:
    items = []
    for record in questions:
        if record["lifecycle_state"] == "open":
            kind = "blocking-question" if _payload(record).get("blocking") is True else "open-question"
            items.append(NeedsYouItem(kind, record["id"], record["subject"], _payload(record).get("scope", "")))
    for record in findings:
        if _payload(record).get("needs") == "human" and record["lifecycle_state"] in ("asserted", "supported", "disputed"):
            items.append(NeedsYouItem("needs-human", record["id"], record["subject"], _payload(record).get("claim", "")))
    for record in checks:
        payload = _payload(record)
        if payload.get("method") == "manual" and payload.get("signed_by") == "" and not _derived(record).get("corrected"):
            text = f"{payload.get('criterion_id', '')} {payload.get('result', '')}".strip()
            items.append(NeedsYouItem("unsigned-check", record["id"], record["subject"], text))
    items.sort(key=lambda item: NEEDS_ORDER.index(item.kind))
    return items


def _activity(
    assignments: list[dict[str, Any]], reports: list[dict[str, Any]], checks: list[dict[str, Any]],
    efforts_by_work_item: dict[str, tuple[str, str]], since: datetime,
) -> dict[str, list[ActivityItem]]:
    by_effort: dict[str, list[ActivityItem]] = {}

    def add(effort: str | None, kind: str, record: dict[str, Any], summary: str) -> None:
        if effort is not None and _recorded_at(record) >= since:
            by_effort.setdefault(effort, []).append(
                ActivityItem(kind, record["id"], record["subject"], _recorded_at(record), summary)
            )

    def work_item(record: dict[str, Any]) -> tuple[str | None, str]:
        ref = _payload(record).get("work_item", "")
        effort, subject = efforts_by_work_item.get(ref, (None, ref))
        return effort, subject

    for record in assignments:
        effort, subject = work_item(record)
        add(_payload(record).get("effort") or effort, "assignment", record,
            f"{subject} assigned to {_payload(record).get('executor', '')}")
    for record in reports:
        effort, subject = work_item(record)
        payload = _payload(record)
        add(effort, "execution-report", record, f"{subject} reported {payload.get('verdict', '')}")
    for record in checks:
        payload = _payload(record)
        outcome = CHECK_RESULT.get(payload.get("result", ""), payload.get("result", ""))
        method = payload.get("method", "").replace("check", "").strip()
        label = " ".join(part for part in (record["subject"], method, "check", outcome) if part)
        add(payload.get("effort"), "check-run", record, label)
    for items in by_effort.values():
        items.sort(key=lambda item: item.recorded_at, reverse=True)
    return by_effort


def _by_effort(records: list[dict[str, Any]], key: str = "effort") -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        effort = record["subject"] if key == "subject" else _payload(record).get(key)
        grouped.setdefault(effort, []).append(record)
    return grouped


def load_snapshot(target: Target, now: datetime | None = None) -> Snapshot:
    now = now or datetime.now(timezone.utc)
    token = change_token(target)
    goals = [r for r in _list(target, "project:active-goal") if r["lifecycle_state"] == "active"]
    phases = _by_effort(_list(target, "project:phase"))
    all_tasks = _list(target, "project:work-item")
    tasks = _by_effort(all_tasks)
    questions = _by_effort(_list(target, "project:continuity-question"), "subject")
    findings = _by_effort(_list(target, "project:finding"))
    checks_all = _list(target, "project:check-run")
    checks = _by_effort(checks_all)
    efforts_by_work_item = {}
    for task in all_tasks:
        entry = (_payload(task).get("effort"), task["subject"])
        efforts_by_work_item[task["id"]] = entry
        efforts_by_work_item.setdefault(task["subject"], entry)
    activity = _activity(
        _list(target, "project:assignment"), _list(target, "project:execution-report"), checks_all,
        efforts_by_work_item, now - RECENT,
    )
    efforts = []
    for goal in sorted(goals, key=lambda record: record["subject"]):
        effort = goal["subject"]
        efforts.append(EffortView(
            effort=effort,
            goal=_payload(goal).get("goal", ""),
            phases=_phase_rows(phases.get(effort, []), tasks.get(effort, [])),
            tasks=_task_rows(tasks.get(effort, [])),
            needs_you=_needs_you(questions.get(effort, []), findings.get(effort, []), checks.get(effort, [])),
            activity=activity.get(effort, []),
        ))
    return Snapshot(efforts, token, now)

