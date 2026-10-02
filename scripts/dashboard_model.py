"""Dashboard snapshot built from `adaptive-artifacts list` output, one call per record type."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
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
FULL_TYPES = ("project:continuity-question", "project:finding", "project:check-run", "project:work-item")


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
    id: str = ""
    awaiting_signoff: bool = False


@dataclass(frozen=True)
class TaskRow:
    id: str
    subject: str
    title: str
    phase: str
    assignee: str
    wave: int | None
    status: str
    waits_on: tuple[str, ...] = ()
    running_since: datetime | None = None


@dataclass(frozen=True)
class NeedsYouItem:
    kind: str
    id: str
    subject: str
    text: str
    record_type: str = ""
    body: str = ""
    task_id: str = ""


@dataclass(frozen=True)
class ActivityItem:
    kind: str
    id: str
    subject: str
    recorded_at: datetime
    summary: str
    failed: bool = False


@dataclass
class EffortView:
    effort: str
    goal: str
    phases: list[PhaseRow] = field(default_factory=list)
    tasks: list[TaskRow] = field(default_factory=list)
    needs_you: list[NeedsYouItem] = field(default_factory=list)
    activity: list[ActivityItem] = field(default_factory=list)

    @property
    def finished(self) -> bool:
        counted = [task for task in self.tasks if task.status != "withdrawn"]
        if not self.phases and not counted:
            return False
        return all(phase.state == "done" for phase in self.phases) and all(task.status == "done" for task in counted)


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


def _run(target: Target, *args: str) -> dict[str, Any]:
    command = [binary(), *target.cli_args(), *args]
    label = " ".join(args[:3])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ModelError(f"cannot run {command[0]}: {exc}") from exc
    if result.returncode != 0:
        raise ModelError(f"{label} failed: {result.stdout}{result.stderr}".strip())
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise ModelError(f"{label} returned unreadable output") from exc


def _list(target: Target, record_type: str) -> list[dict[str, Any]]:
    output = _run(target, "list", "--type", record_type, *(("--full",) if record_type in FULL_TYPES else ()))
    try:
        return output["records"]
    except (KeyError, TypeError) as exc:
        raise ModelError(f"list {record_type} returned unreadable output") from exc


_SNAPSHOT_TYPES = (
    "project:active-goal", "project:phase", "project:work-item", "project:continuity-question",
    "project:finding", "project:check-run", "project:assignment", "project:execution-report",
)


def _list_all(target: Target, record_types: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(zip(record_types, pool.map(lambda record_type: _list(target, record_type), record_types)))


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


def _assigned_at(assignments: list[dict[str, Any]], record: dict[str, Any]) -> datetime | None:
    names = {record["id"], record["subject"]}
    stamps = [_recorded_at(a) for a in assignments if _payload(a).get("work_item") in names]
    return max(stamps, default=None)


def _task_rows(records: list[dict[str, Any]], assignments: list[dict[str, Any]] | None = None) -> list[TaskRow]:
    by_id = {record["id"]: record for record in records}
    rows = []
    for record in records:
        status = _task_status(record)
        if status is None:
            continue
        payload = _payload(record)
        depends_on = [by_id[ref] for ref in (record.get("relationships") or {}).get("depends_on", []) if ref in by_id]
        rows.append(TaskRow(
            id=record["id"], subject=record["subject"], title=payload.get("title", ""),
            phase=payload.get("phase", ""), assignee=payload.get("assignee", ""),
            wave=_derived(record).get("wave"), status=status,
            waits_on=tuple(dep["subject"] for dep in depends_on if dep["lifecycle_state"] != "done"),
            running_since=_assigned_at(assignments or [], record) if status == "running" else None,
        ))
    rows.sort(key=lambda row: (TASK_ORDER.index(row.status), row.wave if row.wave is not None else 0, row.subject))
    return rows


def _awaits_signoff(
    task: dict[str, Any], others: list[str], acceptances: list[dict[str, Any]], latest: dict[str, "CheckRun"],
) -> bool:
    effort = _payload(task).get("effort", "")
    mine = [
        record for record in acceptances
        if record["lifecycle_state"] not in INACTIVE_STATES and _belongs(record, task["subject"], effort, others)
    ]
    runs = [latest.get(record["id"]) for record in mine]
    if not mine or any(run is None or run.result != "pass" for run in runs):
        return False
    return any(run is not None and run.method == "manual" and not run.signed_by for run in runs)


def _phase_rows(
    records: list[dict[str, Any]], tasks: list[dict[str, Any]],
    acceptances: list[dict[str, Any]] | None = None, checks: list[dict[str, Any]] | None = None,
) -> list[PhaseRow]:
    latest = _latest_checks(checks or [])
    subjects = [task["subject"] for task in tasks]
    counted = [task for task in tasks if task["lifecycle_state"] in COUNTED_TASK_STATES]
    rows = []
    for record in records:
        if record["lifecycle_state"] not in LIVE_PHASE_STATES:
            continue
        members = [task for task in counted if _payload(task).get("phase") == record["subject"]]
        payload = _payload(record)
        open_tasks = [task for task in members if task["lifecycle_state"] != "done"]
        awaiting = record["lifecycle_state"] != "done" and bool(open_tasks) and all(
            _awaits_signoff(task, [s for s in subjects if s != task["subject"]], acceptances or [], latest)
            for task in open_tasks
        )
        rows.append(PhaseRow(
            subject=record["subject"], title=payload.get("title", ""), ordinal=payload.get("ordinal", 0),
            state=record["lifecycle_state"], done=sum(t["lifecycle_state"] == "done" for t in members),
            total=len(members), id=record["id"], awaiting_signoff=awaiting,
        ))
    rows.sort(key=lambda row: (row.ordinal, row.subject))
    return rows


def _task_for(subject: str, tasks: list[dict[str, Any]]) -> str:
    matches = [task for task in tasks if subject == task["subject"] or subject.startswith(task["subject"] + "-")]
    return max(matches, key=lambda task: len(task["subject"]))["id"] if matches else ""


def _needs_you(
    questions: list[dict[str, Any]], findings: list[dict[str, Any]], checks: list[dict[str, Any]],
    acceptances: dict[str, dict[str, Any]] | None = None, tasks: list[dict[str, Any]] | None = None,
) -> list[NeedsYouItem]:
    acceptances = acceptances or {}
    tasks = tasks or []

    def item(kind: str, record: dict[str, Any], subject: str, text: str) -> NeedsYouItem:
        return NeedsYouItem(
            kind, record["id"], subject, text, record_type=record.get("record_type", ""),
            body=record.get("body") or "", task_id=_task_for(subject, tasks),
        )

    items = []
    for record in questions:
        if record["lifecycle_state"] == "open":
            kind = "blocking-question" if _payload(record).get("blocking") is True else "open-question"
            items.append(item(kind, record, record["subject"], _payload(record).get("scope", "")))
    for record in findings:
        if _payload(record).get("needs") == "human" and record["lifecycle_state"] in ("asserted", "supported", "disputed"):
            items.append(item("needs-human", record, record["subject"], _payload(record).get("claim", "")))
    for record in checks:
        payload = _payload(record)
        if payload.get("method") == "manual" and payload.get("signed_by") == "" and not _derived(record).get("corrected"):
            acceptance = acceptances.get(payload.get("criterion_id", ""))
            subject = acceptance["subject"] if acceptance else record["subject"]
            criterion = _payload(acceptance).get("criterion", "") if acceptance else ""
            text = f"{criterion} {payload.get('result', '')}".strip()
            items.append(item("unsigned-check", record, subject, text))
    items.sort(key=lambda entry: NEEDS_ORDER.index(entry.kind))
    return items


def _activity(
    assignments: list[dict[str, Any]], reports: list[dict[str, Any]], checks: list[dict[str, Any]],
    efforts_by_work_item: dict[str, tuple[str, str]], since: datetime,
) -> dict[str, list[ActivityItem]]:
    by_effort: dict[str, list[ActivityItem]] = {}

    def add(effort: str | None, kind: str, record: dict[str, Any], summary: str, failed: bool = False) -> None:
        if effort is not None and _recorded_at(record) >= since:
            by_effort.setdefault(effort, []).append(
                ActivityItem(kind, record["id"], record["subject"], _recorded_at(record), summary, failed)
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
        add(effort, "execution-report", record, f"{subject} reported {payload.get('verdict', '')}",
            "fail" in (payload.get("result"), payload.get("verdict")))
    for record in checks:
        payload = _payload(record)
        outcome = CHECK_RESULT.get(payload.get("result", ""), payload.get("result", ""))
        method = payload.get("method", "").replace("check", "").strip()
        label = " ".join(part for part in (record["subject"], method, "check", outcome) if part)
        add(payload.get("effort"), "check-run", record, label, payload.get("result") == "fail")
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
    listed = _list_all(target, _SNAPSHOT_TYPES)
    goals = [r for r in listed["project:active-goal"] if r["lifecycle_state"] == "active"]
    phases = _by_effort(listed["project:phase"])
    all_tasks = listed["project:work-item"]
    tasks = _by_effort(all_tasks)
    questions = _by_effort(listed["project:continuity-question"], "subject")
    findings = _by_effort(listed["project:finding"])
    checks_all = listed["project:check-run"]
    checks = _by_effort(checks_all)
    acceptances_all = _list(target, "project:acceptance")
    acceptances = _by_effort(acceptances_all)
    acceptances_by_id = {record["id"]: record for record in acceptances_all}
    efforts_by_work_item = {}
    for task in all_tasks:
        entry = (_payload(task).get("effort"), task["subject"])
        efforts_by_work_item[task["id"]] = entry
        efforts_by_work_item.setdefault(task["subject"], entry)
    activity = _activity(
        listed["project:assignment"], listed["project:execution-report"], checks_all,
        efforts_by_work_item, now - RECENT,
    )
    efforts = []
    for goal in sorted(goals, key=lambda record: record["subject"]):
        effort = goal["subject"]
        efforts.append(EffortView(
            effort=effort,
            goal=_payload(goal).get("goal", ""),
            phases=_phase_rows(
                phases.get(effort, []), tasks.get(effort, []), acceptances.get(effort, []), checks.get(effort, []),
            ),
            tasks=_task_rows(tasks.get(effort, []), listed["project:assignment"]),
            needs_you=_needs_you(
                questions.get(effort, []), findings.get(effort, []), checks.get(effort, []), acceptances_by_id,
                tasks.get(effort, []),
            ),
            activity=activity.get(effort, []),
        ))
    efforts.sort(key=lambda view: view.finished)
    return Snapshot(efforts, token, now)



@dataclass(frozen=True)
class LinkedTask:
    id: str
    subject: str
    title: str
    status: str


@dataclass(frozen=True)
class CheckRun:
    id: str
    result: str
    method: str
    signed_by: str
    revision: str
    recorded_at: datetime


@dataclass(frozen=True)
class AcceptanceRow:
    id: str
    subject: str
    criterion: str
    method: str
    verify_command: str
    check: CheckRun | None


@dataclass(frozen=True)
class TimelineEvent:
    kind: str
    id: str
    recorded_at: datetime
    summary: str
    body: str
    revision: str = ""


@dataclass(frozen=True)
class RelatedRecord:
    kind: str
    id: str
    subject: str
    text: str


@dataclass(frozen=True)
class TaskDetail:
    id: str
    subject: str
    effort: str
    title: str
    status: str
    phase: str
    wave: int | None
    assignee: str
    body: str
    depends_on: list[LinkedTask]
    blocks: list[LinkedTask]
    acceptances: list[AcceptanceRow]
    timeline: list[TimelineEvent]
    related: list[RelatedRecord]


RELATED_TEXT = {
    "project:finding": ("finding", "claim"),
    "project:decision": ("decision", "choice"),
    "project:failed-attempt": ("failed-attempt", "attempted_action"),
    "project:investigation-observation": ("observation", "what_was_observed"),
}
INACTIVE_STATES = ("superseded", "retracted")


def _linked(ids: list[str], rows: dict[str, TaskRow]) -> list[LinkedTask]:
    return [LinkedTask(row.id, row.subject, row.title, row.status) for i in ids if (row := rows.get(i))]


def _belongs(record: dict[str, Any], slug: str, effort: str, others: list[str]) -> bool:
    subject = record["subject"]
    if subject != slug and not subject.startswith(slug + "-"):
        return False
    if any(subject == other or subject.startswith(other + "-") for other in others):
        return False
    return _payload(record).get("effort", effort) == effort


def _refers_to(record: dict[str, Any], key: str, names: set[str]) -> bool:
    return _payload(record).get(key) in names


def _latest_checks(checks: list[dict[str, Any]]) -> dict[str, CheckRun]:
    latest: dict[str, CheckRun] = {}
    for record in sorted(checks, key=_recorded_at):
        if record["lifecycle_state"] in INACTIVE_STATES:
            continue
        payload = _payload(record)
        latest[payload.get("criterion_id", "")] = CheckRun(
            record["id"], payload.get("result", ""), payload.get("method", ""),
            payload.get("signed_by", ""), payload.get("revision", ""), _recorded_at(record),
        )
    return latest


def _timeline(
    assignments: list[dict[str, Any]], amendments: list[dict[str, Any]], reports: list[dict[str, Any]],
    checks: list[dict[str, Any]],
) -> list[TimelineEvent]:
    events = []
    for record in assignments:
        events.append(("assignment", record, f"assigned to {_payload(record).get('executor', '')}"))
    for record in amendments:
        events.append(("assignment-amendment", record, "amended"))
    for record in reports:
        payload = _payload(record)
        events.append(("execution-report", record, f"reported {payload.get('verdict', '')}"))
    for record in checks:
        payload = _payload(record)
        outcome = CHECK_RESULT.get(payload.get("result", ""), payload.get("result", ""))
        events.append(("check-run", record, f"{payload.get('method', '')} check {outcome}".strip()))
    timeline = [
        TimelineEvent(
            kind, record["id"], _recorded_at(record), summary, record.get("body") or "",
            _payload(record).get("revision", "") if kind in ("execution-report", "check-run") else "",
        )
        for kind, record, summary in events
    ]
    timeline.sort(key=lambda event: event.recorded_at)
    return timeline


def load_task_detail(target: Target, work_item_id: str) -> TaskDetail:
    """Load one task's records with three CLI calls.

    `get` yields the subject, effort, body, and outbound depends_on; one `list --subject --full`
    yields every record for the slug; one work-item `list` for the effort names linked tasks.
    """
    item = _run(target, "get", "--type", "project:work-item", "--id", work_item_id)
    if "subject" not in item:
        raise ModelError(f"get project:work-item {work_item_id} returned unreadable output")
    slug, payload = item["subject"], _payload(item)
    effort = payload.get("effort", "")
    records = _run(target, "list", "--subject", slug, "--full").get("records", [])
    efforts = _run(target, "list", "--type", "project:work-item", "--where", f"payload.effort={effort}")
    rows = {row.id: row for row in _task_rows(efforts.get("records", []))}
    mine = next((r for r in records if r["id"] == work_item_id), item)
    others = [r["subject"] for r in records if r["record_type"] == "project:work-item" and r["id"] != work_item_id]
    names = {work_item_id, slug}
    of_type: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if record["id"] != work_item_id and _belongs(record, slug, effort, others):
            of_type.setdefault(record["record_type"], []).append(record)
    assignments = [r for r in of_type.get("project:assignment", []) if _refers_to(r, "work_item", names)]
    assignment_names = names | {r["id"] for r in assignments} | {r["subject"] for r in assignments}
    amendments = [r for r in of_type.get("project:assignment-amendment", []) if _refers_to(r, "assignment", assignment_names)]
    reports = [r for r in of_type.get("project:execution-report", []) if _refers_to(r, "work_item", names)]
    checks = of_type.get("project:check-run", [])
    latest = _latest_checks(checks)
    acceptances = [
        AcceptanceRow(
            r["id"], r["subject"], _payload(r).get("criterion", ""), _payload(r).get("method", ""),
            _payload(r).get("verify_command", ""), latest.get(r["id"]),
        )
        for r in sorted(of_type.get("project:acceptance", []), key=_recorded_at)
    ]
    related = [
        RelatedRecord(kind, r["id"], r["subject"], _payload(r).get(field, ""))
        for record_type, (kind, field) in RELATED_TEXT.items()
        for r in of_type.get(record_type, [])
    ]
    return TaskDetail(
        id=work_item_id, subject=slug, effort=effort, title=payload.get("title", ""),
        status=_task_status(mine) or mine["lifecycle_state"], phase=payload.get("phase", ""),
        wave=_derived(mine).get("wave"), assignee=payload.get("assignee", ""), body=item.get("body") or "",
        depends_on=_linked((item.get("relationships") or {}).get("depends_on", []), rows),
        blocks=_linked((_derived(mine).get("referenced_by") or {}).get("depends_on", []), rows),
        acceptances=acceptances, timeline=_timeline(assignments, amendments, reports, checks), related=related,
    )


@dataclass(frozen=True)
class PhaseDetail:
    subject: str
    effort: str
    title: str
    state: str
    awaiting_signoff: bool
    body: str
    decisions: list[RelatedRecord]
    constraints: list[RelatedRecord]
    tasks: list[TaskRow]


def load_phase_detail(target: Target, effort: str, phase_subject: str) -> PhaseDetail:
    """Load one phase with its body, decisions, constraints, and tasks."""
    snapshot_phases = _by_effort(_list(target, "project:phase")).get(effort, [])
    record = next((r for r in snapshot_phases if r["subject"] == phase_subject), None)
    if record is None:
        raise ModelError(f"phase {phase_subject} not found in {effort}")
    item = _run(target, "get", "--type", "project:phase", "--id", record["id"])
    tasks = _by_effort(_list(target, "project:work-item")).get(effort, [])
    row = next(
        (p for p in _phase_rows(
            [record], tasks, _by_effort(_list(target, "project:acceptance")).get(effort, []),
            _by_effort(_list(target, "project:check-run")).get(effort, []),
        )),
        None,
    )
    decisions = [
        RelatedRecord("decision", r["id"], r["subject"], _payload(r).get("choice", ""))
        for r in _by_effort(_list(target, "project:decision")).get(effort, [])
        if _payload(r).get("phase") == phase_subject and r["lifecycle_state"] not in INACTIVE_STATES
    ]
    constraints = [
        RelatedRecord("constraint", r["id"], r["subject"], _payload(r).get("statement", ""))
        for r in _by_effort(_list(target, "project:constraint")).get(effort, [])
        if _payload(r).get("applies_to") == phase_subject and r["lifecycle_state"] not in INACTIVE_STATES
    ]
    payload = _payload(record)
    return PhaseDetail(
        subject=phase_subject, effort=effort, title=payload.get("title", ""), state=record["lifecycle_state"],
        awaiting_signoff=bool(row and row.awaiting_signoff), body=item.get("body") or "",
        decisions=decisions, constraints=constraints,
        tasks=[t for t in _task_rows(tasks) if t.phase == phase_subject],
    )
