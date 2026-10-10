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

from dashboard.artifact_store import Target, binary

RECENT = timedelta(hours=24)
TASK_ORDER = ("running", "ready", "waiting", "done", "withdrawn")
NEEDS_ORDER = (
    "blocking-question", "loop-route", "integration", "merge-branch",
    "needs-human", "unsigned-check", "open-question",
)
LIVE_PHASE_STATES = ("planned", "in_progress", "done")
COUNTED_TASK_STATES = ("planned", "in_progress", "done")
CHECK_RESULT = {"pass": "passed", "fail": "failed"}
TOKEN_DIRS = ("records", "history")
FULL_TYPES = (
    "project:continuity-question", "project:finding", "project:check-run", "project:work-item",
    "project:phase", "project:specification", "project:assessment", "project:integration-report",
    "project:backlog-item",
)
SOFT_TYPES = frozenset({
    "project:specification", "project:design", "project:assessment", "project:integration-report",
    "project:release", "project:current-position", "project:backlog-item",
})
UPSTREAM_NEXT = frozenset({"specify", "design", "plan"})
LOOP_NEXT = ("specify", "design", "plan", "execute", "integrate", "verify", "release")


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
    evidence: "PhaseEvidence | None" = None
    sitting: str = ""
    body: str = ""
    elapsed_minutes: int | None = None
    unset_estimates: int = 0


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
    size: str = ""
    estimate_minutes: int | None = None
    executor: str = "subagent"
    last_record_at: datetime | None = None


@dataclass(frozen=True)
class NeedsYouItem:
    kind: str
    id: str
    subject: str
    text: str
    record_type: str = ""
    body: str = ""
    task_id: str = ""
    phase: str = ""
    requirement: str = ""
    status: str = ""
    next: str = ""
    result: str = ""


@dataclass(frozen=True)
class BacklogItem:
    id: str
    subject: str
    effort: str
    text: str
    status: str = "open"
    source: str = ""
    phase: str = ""
    body: str = ""
    record_type: str = "project:backlog-item"


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
    release_ready: bool = False
    position: str = ""
    kind: str = ""
    journal_open: list = field(default_factory=list)
    backlog: list[BacklogItem] = field(default_factory=list)

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


def _list(
    target: Target,
    record_type: str,
    *,
    state: str | None = None,
    where: tuple[str, ...] = (),
    full: bool | None = None,
) -> list[dict[str, Any]]:
    args = ["list", "--type", record_type]
    use_full = record_type in FULL_TYPES if full is None else full
    if use_full:
        args.append("--full")
    if state:
        args.extend(["--state", state])
    for clause in where:
        args.extend(["--where", clause])
    try:
        output = _run(target, *args)
    except ModelError:
        if record_type in SOFT_TYPES:
            return []
        raise
    try:
        return output["records"]
    except (KeyError, TypeError) as exc:
        raise ModelError(f"list {record_type} returned unreadable output") from exc


_SNAPSHOT_TYPES = (
    "project:active-goal", "project:phase", "project:work-item", "project:continuity-question",
    "project:finding", "project:check-run", "project:assignment", "project:assignment-amendment",
    "project:execution-report",
    "project:specification", "project:design", "project:assessment", "project:integration-report", "project:release",
    "project:current-position", "project:backlog-item",
)


def _list_all(target: Target, record_types: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(zip(record_types, pool.map(lambda record_type: _list(target, record_type), record_types)))


def _payload(record: dict[str, Any]) -> dict[str, Any]:
    return record.get("payload") or {}


def _merge_aliases(goals: list[dict[str, Any]]) -> dict[str, str]:
    return {old: goal["subject"] for goal in goals for old in _payload(goal).get("merged_from") or []}


def _remapped(records: list[dict[str, Any]], aliases: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {**record, "payload": {**_payload(record), "effort": aliases[_payload(record)["effort"]]}}
        if _payload(record).get("effort") in aliases else record
        for record in records
    ]


def _derived(record: dict[str, Any]) -> dict[str, Any]:
    return record.get("derived") or {}


def _recorded_at(record: dict[str, Any]) -> datetime:
    stamp = record.get("recorded_at")
    return datetime.fromisoformat(stamp) if stamp else datetime.min.replace(tzinfo=timezone.utc)


def _split_csv(value: Any) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _section(body: str, heading: str) -> str:
    collected: list[str] = []
    collecting = False
    target = heading.strip().lower()
    for line in (body or "").splitlines():
        if line.startswith("## "):
            if collecting:
                break
            collecting = line[3:].strip().lower() == target
            continue
        if collecting:
            collected.append(line)
    return "\n".join(collected).strip()


def _without_section(body: str, heading: str) -> str:
    """Body with one ## heading section removed; other text kept as stored."""
    kept: list[str] = []
    skipping = False
    target = heading.strip().lower()
    for line in (body or "").splitlines():
        if line.startswith("## "):
            skipping = line[3:].strip().lower() == target
            if skipping:
                continue
        if not skipping:
            kept.append(line)
    return "\n".join(kept).strip()


def _requirement_texts(body: str) -> dict[str, str]:
    texts = {}
    for line in _section(body, "Requirements").splitlines():
        ident, sep, text = line.partition(":")
        if sep and ident.strip():
            texts[ident.strip()] = text.strip()
    return texts


def _live(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records if record.get("lifecycle_state") not in INACTIVE_STATES]


def _newest(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(records, key=_recorded_at) if records else None


def _oldest_first(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order a supersede chain from the original record to the active one.

    Supersede rewrites the predecessor's recorded_at to the moment it is retired,
    which is after the successor's recorded_at was chosen.
    """
    by_id = {record["id"]: record for record in records}
    previous: dict[str, str] = {}
    pointed: set[str] = set()
    for record in records:
        links = [ref for ref in (record.get("relationships") or {}).get("supersedes") or [] if ref in by_id]
        if links:
            previous[record["id"]] = links[0]
            pointed.add(links[0])
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for start in sorted((record for record in records if record["id"] not in pointed), key=_recorded_at):
        chain: list[dict[str, Any]] = []
        current: dict[str, Any] | None = start
        while current is not None and current["id"] not in seen:
            seen.add(current["id"])
            chain.append(current)
            current = by_id.get(previous.get(current["id"], ""))
        chain.reverse()
        ordered.extend(chain)
    ordered.extend(sorted((record for record in records if record["id"] not in seen), key=_recorded_at))
    return ordered


def _for_phase(records: list[dict[str, Any]], phase: str, effort: str) -> list[dict[str, Any]]:
    matched = []
    for record in _live(records):
        payload = _payload(record)
        record_effort = payload.get("effort")
        if record_effort and record_effort != effort:
            continue
        if payload.get("phase") == phase:
            matched.append(record)
    return matched


def _structured_phases(specs: list[dict[str, Any]]) -> set[tuple[str, str]]:
    found = set()
    for record in _live(specs):
        payload = _payload(record)
        effort, phase = payload.get("effort") or "", payload.get("phase") or ""
        if effort and phase:
            found.add((effort, phase))
    return found


def _check_from(record: dict[str, Any]) -> "CheckRun":
    payload = _payload(record)
    return CheckRun(
        record["id"], payload.get("result", ""), payload.get("method", ""),
        payload.get("signed_by", ""), payload.get("revision", ""), _recorded_at(record),
        payload.get("evidence_kind") or "",
    )


def _latest_assessment_map(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for record in sorted(_live(records), key=_recorded_at):
        payload = _payload(record)
        grouped[(payload.get("phase", ""), payload.get("requirement", ""))] = record
    return grouped


def _traced_records(tasks: list[dict[str, Any]], phase: str, requirement: str) -> list[dict[str, Any]]:
    return [
        task for task in tasks
        if task.get("lifecycle_state") != "superseded"
        and _payload(task).get("phase") == phase
        and requirement in _split_csv(_payload(task).get("requirements"))
    ]


def _choices(subjects: list[str], decisions: list[dict[str, Any]]) -> tuple["DecisionChoice", ...]:
    by_subject: dict[str, dict[str, Any]] = {}
    for record in sorted(_live(decisions), key=_recorded_at):
        by_subject[record["subject"]] = record
    return tuple(
        DecisionChoice(subject, _payload(by_subject[subject]).get("choice", "") if subject in by_subject else "")
        for subject in subjects
    )


def _latest_requirement_check(
    requirement: str, phase: str, acceptances: list[dict[str, Any]], checks: list[dict[str, Any]],
) -> "CheckRun | None":
    acceptance_ids = {
        record["id"]
        for record in acceptances
        if record.get("lifecycle_state") not in INACTIVE_STATES and _payload(record).get("phase") == phase
    }
    matched = [
        record for record in checks
        if record.get("lifecycle_state") not in INACTIVE_STATES
        and _payload(record).get("requirement") == requirement
        and _payload(record).get("criterion_id") in acceptance_ids
    ]
    record = _newest(matched)
    return _check_from(record) if record else None


def _needs_route(record: dict[str, Any]) -> bool:
    payload = _payload(record)
    status, nxt, confidence = payload.get("status", ""), payload.get("next", ""), payload.get("confidence", "")
    if status == "insufficient" or nxt == "execute":
        return False
    if nxt == "verify" and status != "blocked":
        return False
    return nxt in UPSTREAM_NEXT or status == "blocked" or confidence == "low"


def _assessment_summary(record: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> tuple[str, bool]:
    payload = _payload(record)
    summary = f"{payload.get('requirement', '')} {payload.get('status', '')} {payload.get('next', '')}"
    if payload.get("next") in UPSTREAM_NEXT:
        summary += " upstream"
    links = (record.get("relationships") or {}).get("supersedes") or []
    previous = by_id.get(links[0]) if links else None
    if previous is not None:
        old, new = _payload(previous).get("level") or "", payload.get("level") or ""
        if old != new:
            summary += f" level {old} to {new}"
    return summary, payload.get("status") in ("failed", "blocked")


def sitting_phrase(body: str) -> str:
    """Return the phase sitting phrase from the first Size: line, or empty."""
    for line in (body or "").splitlines():
        if "Size:" not in line:
            continue
        text = line.split("Size:", 1)[1]
        if "more than one" in text:
            return "more than one"
        if "one sitting" in text:
            return "one sitting"
        return ""
    return ""


def phase_elapsed(tasks: list[TaskRow]) -> tuple[int | None, int]:
    """Wave-rule minutes for already-counted tasks, plus how many lack an estimate.

    An inline wave sums its estimates. Any other wave contributes its longest.
    A task with no wave is its own group. Blank estimates are skipped, and zero counts.
    """
    unset = sum(task.estimate_minutes is None for task in tasks)
    groups: dict[Any, list[TaskRow]] = {}
    for task in tasks:
        key = task.wave if task.wave is not None else task.id
        groups.setdefault(key, []).append(task)

    def order(key: Any) -> tuple:
        return (0, key) if isinstance(key, int) else (1, str(key))

    figures: list[int] = []
    for key in sorted(groups, key=order):
        members = groups[key]
        values = [task.estimate_minutes for task in members if task.estimate_minutes is not None]
        if not values:
            continue
        if all(task.executor == "inline" for task in members):
            figures.append(sum(values))
        else:
            figures.append(max(values))
    if not figures:
        return (None, unset)
    return (sum(figures), unset)


def _size(payload: dict[str, Any]) -> str:
    size = payload.get("size")
    return size if isinstance(size, str) and size else ""


def _estimate_minutes(payload: dict[str, Any]) -> int | None:
    if "estimate_minutes" not in payload:
        return None
    value = payload["estimate_minutes"]
    if value is None:
        return None
    return value


def _executor(payload: dict[str, Any]) -> str:
    executor = payload.get("executor")
    return executor if executor else "subagent"


def _task_status(record: dict[str, Any]) -> str | None:
    state = record["lifecycle_state"]
    if state == "planned":
        return "ready" if _derived(record).get("ready") else "waiting"
    return {"in_progress": "running", "done": "done", "withdrawn": "withdrawn"}.get(state)


def _assigned_at(assignments: list[dict[str, Any]], record: dict[str, Any]) -> datetime | None:
    names = {record["id"], record["subject"]}
    stamps = [_recorded_at(a) for a in assignments if _payload(a).get("work_item") in names]
    return max(stamps, default=None)


def _task_assignments(assignments: list[dict[str, Any]], record: dict[str, Any]) -> list[dict[str, Any]]:
    names = {record["id"], record["subject"]}
    return [a for a in assignments if _payload(a).get("work_item") in names]


def _last_record_at(
    record: dict[str, Any],
    assignments: list[dict[str, Any]],
    amendments: list[dict[str, Any]],
    reports: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    others: list[str],
) -> datetime | None:
    """Latest assignment / amendment / execution-report / check-run stamp for a running task."""
    names = {record["id"], record["subject"]}
    mine = _task_assignments(assignments, record)
    stamps = [_recorded_at(a) for a in mine]
    assignment_names = names | {a["id"] for a in mine} | {a["subject"] for a in mine}
    stamps.extend(
        _recorded_at(a) for a in amendments if _payload(a).get("assignment") in assignment_names
    )
    stamps.extend(_recorded_at(r) for r in reports if _payload(r).get("work_item") in names)
    slug, effort = record["subject"], _payload(record).get("effort", "")
    stamps.extend(
        _recorded_at(c) for c in checks if _belongs(c, slug, effort, others)
    )
    return max(stamps, default=None)


def _task_rows(
    records: list[dict[str, Any]],
    assignments: list[dict[str, Any]] | None = None,
    amendments: list[dict[str, Any]] | None = None,
    reports: list[dict[str, Any]] | None = None,
    checks: list[dict[str, Any]] | None = None,
) -> list[TaskRow]:
    by_id = {record["id"]: record for record in records}
    assignments = assignments or []
    amendments = amendments or []
    reports = reports or []
    checks = checks or []
    subjects = [record["subject"] for record in records]
    rows = []
    for record in records:
        status = _task_status(record)
        if status is None:
            continue
        payload = _payload(record)
        depends_on = [by_id[ref] for ref in (record.get("relationships") or {}).get("depends_on", []) if ref in by_id]
        running_since = _assigned_at(assignments, record) if status == "running" else None
        others = [s for s in subjects if s != record["subject"]]
        last_record_at = (
            _last_record_at(record, assignments, amendments, reports, checks, others)
            if running_since is not None else None
        )
        rows.append(TaskRow(
            id=record["id"], subject=record["subject"], title=payload.get("title", ""),
            phase=payload.get("phase", ""), assignee=payload.get("assignee", ""),
            wave=_derived(record).get("wave"), status=status,
            waits_on=tuple(dep["subject"] for dep in depends_on if dep["lifecycle_state"] != "done"),
            running_since=running_since,
            size=_size(payload), estimate_minutes=_estimate_minutes(payload), executor=_executor(payload),
            last_record_at=last_record_at,
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
    evidence_by_phase: dict[str, "PhaseEvidence"] | None = None,
) -> list[PhaseRow]:
    latest = _latest_checks(checks or [])
    evidence_by_phase = evidence_by_phase or {}
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
        elapsed_minutes, unset_estimates = phase_elapsed(_task_rows(members))
        body = record.get("body") or ""
        rows.append(PhaseRow(
            subject=record["subject"], title=payload.get("title", ""), ordinal=payload.get("ordinal", 0),
            state=record["lifecycle_state"], done=sum(t["lifecycle_state"] == "done" for t in members),
            total=len(members), id=record["id"], awaiting_signoff=awaiting,
            evidence=evidence_by_phase.get(record["subject"]),
            sitting=sitting_phrase(body), body=body,
            elapsed_minutes=elapsed_minutes, unset_estimates=unset_estimates,
        ))
    rows.sort(key=lambda row: (row.ordinal, row.subject))
    return rows


def _task_for(subject: str, tasks: list[dict[str, Any]]) -> str:
    matches = [task for task in tasks if subject == task["subject"] or subject.startswith(task["subject"] + "-")]
    return max(matches, key=lambda task: len(task["subject"]))["id"] if matches else ""


def _backlog_text(record: dict[str, Any]) -> str:
    for line in (record.get("body") or "").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return record.get("subject") or ""


def _backlog_items(records: list[dict[str, Any]]) -> list[BacklogItem]:
    items = []
    for record in records:
        if record.get("lifecycle_state") in INACTIVE_STATES:
            continue
        payload = _payload(record)
        if payload.get("status") != "open":
            continue
        items.append(BacklogItem(
            id=record["id"],
            subject=record["subject"],
            effort=payload.get("effort") or "",
            text=_backlog_text(record),
            status=payload.get("status") or "open",
            source=payload.get("source") or "",
            phase=payload.get("phase") or "",
            body=record.get("body") or "",
            record_type=record.get("record_type") or "project:backlog-item",
        ))
    items.sort(key=lambda item: (item.subject, item.id))
    return items


def _needs_you(
    questions: list[dict[str, Any]], findings: list[dict[str, Any]], checks: list[dict[str, Any]],
    acceptances: dict[str, dict[str, Any]] | None = None, tasks: list[dict[str, Any]] | None = None,
    assessments: list[dict[str, Any]] | None = None, integrations: list[dict[str, Any]] | None = None,
    spec_phases: set[str] | None = None,
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
    spec_phases = spec_phases or set()
    for (phase, requirement), record in sorted(_latest_assessment_map(assessments or []).items()):
        if phase not in spec_phases or not _needs_route(record):
            continue
        payload = _payload(record)
        status, nxt = payload.get("status", ""), payload.get("next", "")
        text = " ".join(part for part in (requirement, status, nxt) if part)
        items.append(NeedsYouItem(
            "loop-route", record["id"], record["subject"], text, record_type=record.get("record_type", ""),
            phase=phase, requirement=requirement, status=status, next=nxt,
        ))
    reports_by_phase: dict[str, list[dict[str, Any]]] = {}
    for record in _live(integrations or []):
        phase = _payload(record).get("phase", "")
        if phase in spec_phases:
            reports_by_phase.setdefault(phase, []).append(record)
    for phase, records in reports_by_phase.items():
        latest = _newest(records)
        if latest is None:
            continue
        result = _payload(latest).get("result", "")
        if result not in ("fail", "blocked"):
            continue
        items.append(NeedsYouItem(
            "integration", latest["id"], latest["subject"], f"{phase} {result}",
            record_type=latest.get("record_type", ""), phase=phase, result=result,
        ))
    items.sort(key=lambda entry: NEEDS_ORDER.index(entry.kind))
    return items


def _activity(
    assignments: list[dict[str, Any]], reports: list[dict[str, Any]], checks: list[dict[str, Any]],
    efforts_by_work_item: dict[str, tuple[str, str]], since: datetime,
    assessments: list[dict[str, Any]] | None = None, integrations: list[dict[str, Any]] | None = None,
    releases: list[dict[str, Any]] | None = None, structured: set[tuple[str, str]] | None = None,
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
    structured = structured or set()
    assessment_by_id = {record["id"]: record for record in assessments or []}
    for record in assessments or []:
        payload = _payload(record)
        if (payload.get("effort"), payload.get("phase")) not in structured:
            continue
        summary, failed = _assessment_summary(record, assessment_by_id)
        add(payload.get("effort"), "assessment", record, summary, failed)
    for record in integrations or []:
        payload = _payload(record)
        if (payload.get("effort"), payload.get("phase")) not in structured:
            continue
        result = payload.get("result", "")
        add(payload.get("effort"), "integration", record, f"{payload.get('phase', '')} {result}", result in ("fail", "blocked"))
    for record in releases or []:
        payload = _payload(record)
        if (payload.get("effort"), payload.get("phase")) not in structured:
            continue
        state = payload.get("state", "")
        add(payload.get("effort"), "release", record, f"{payload.get('phase', '')} {state}", state == "failed")
    for items in by_effort.values():
        items.sort(key=lambda item: item.recorded_at, reverse=True)
    return by_effort


def _by_effort(records: list[dict[str, Any]], key: str = "effort") -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        effort = record["subject"] if key == "subject" else _payload(record).get(key)
        grouped.setdefault(effort, []).append(record)
    return grouped


@dataclass(frozen=True)
class DecisionChoice:
    subject: str
    choice: str


@dataclass(frozen=True)
class IntegrationView:
    result: str
    conflicts: str


@dataclass(frozen=True)
class RequirementRow:
    phase: str
    id: str
    text: str
    status: str
    next: str
    latest_check: "CheckRun | None"
    tasks: int
    tasks_done: int = 0
    confidence: str = ""
    check_kind: str = ""
    check_at: datetime | None = None


@dataclass(frozen=True)
class PhaseEvidence:
    phase: str
    weight: str
    requirements: tuple[RequirementRow, ...]
    stage: str
    integration: IntegrationView | None
    release_ready: bool
    decisions: tuple[DecisionChoice, ...]
    non_goals: str
    release_state: str = ""


@dataclass(frozen=True)
class AssessmentView:
    id: str
    status: str
    level: str
    next: str
    confidence: str


@dataclass(frozen=True)
class RequirementDetail:
    phase: str
    id: str
    text: str
    status: str
    next: str
    decisions: tuple[DecisionChoice, ...]
    tasks: tuple["TaskRow", ...]
    acceptances: tuple["AcceptanceRow", ...]
    assessments: tuple[AssessmentView, ...]


def _stage(
    phase: str, effort: str, spec_ids: list[str], designs: list[dict[str, Any]], tasks: list[dict[str, Any]],
    acceptances: list[dict[str, Any]], checks: list[dict[str, Any]], assessments: list[dict[str, Any]],
    reports: list[dict[str, Any]], releases: list[dict[str, Any]],
) -> tuple[str, bool]:
    latest_release = _newest(_for_phase(releases, phase, effort))
    if latest_release and _payload(latest_release).get("state") == "ready":
        return "release", True
    latest = {
        requirement: record
        for (record_phase, requirement), record in _latest_assessment_map(assessments).items()
        if record_phase == phase
    }
    non_verified = [record for record in latest.values() if _payload(record).get("status") != "verified"]
    if non_verified:
        def rank(record: dict[str, Any]) -> int:
            nxt = _payload(record).get("next", "")
            return LOOP_NEXT.index(nxt) if nxt in LOOP_NEXT else len(LOOP_NEXT)

        return _payload(min(non_verified, key=rank)).get("next", ""), False
    if spec_ids and all(_payload(latest.get(req) or {}).get("status") == "verified" for req in spec_ids):
        return "release", False
    if not _for_phase(designs, phase, effort):
        return "design", False
    counted = [
        task for task in tasks
        if _payload(task).get("phase") == phase and task.get("lifecycle_state") in COUNTED_TASK_STATES
    ]
    if not counted:
        return "plan", False
    if any(task.get("lifecycle_state") != "done" for task in counted):
        return "execute", False
    waves: dict[Any, int] = {}
    for task in counted:
        wave = _derived(task).get("wave")
        waves[wave] = waves.get(wave, 0) + 1
    passing = any(_payload(report).get("result") == "pass" for report in _for_phase(reports, phase, effort))
    if any(count > 1 for count in waves.values()) and not passing:
        return "integrate", False
    checked = {
        _payload(check).get("criterion_id")
        for check in checks
        if check.get("lifecycle_state") not in INACTIVE_STATES
    }
    if any(
        _payload(record).get("requirement") and record["id"] not in checked
        for record in _for_phase(acceptances, phase, effort)
    ):
        return "verify", False
    return "assess", False


def _phase_evidence(
    phase: str, effort: str, specs: list[dict[str, Any]], designs: list[dict[str, Any]],
    decisions: list[dict[str, Any]], tasks: list[dict[str, Any]], acceptances: list[dict[str, Any]],
    checks: list[dict[str, Any]], assessments: list[dict[str, Any]], reports: list[dict[str, Any]],
    releases: list[dict[str, Any]],
) -> PhaseEvidence | None:
    spec = _newest(_for_phase(specs, phase, effort))
    if spec is None:
        return None
    spec_ids = _split_csv(_payload(spec).get("requirements"))
    texts = _requirement_texts(spec.get("body") or "")
    latest = {
        requirement: record
        for (record_phase, requirement), record in _latest_assessment_map(assessments).items()
        if record_phase == phase
    }
    rows = []
    for requirement in spec_ids:
        assessment = latest.get(requirement)
        if assessment is None:
            status, nxt, confidence = "unassessed", "", ""
        else:
            payload = _payload(assessment)
            status = payload.get("status", "")
            nxt = "" if status == "verified" else payload.get("next", "")
            confidence = payload.get("confidence", "")
        traced = _traced_records(tasks, phase, requirement)
        check = _latest_requirement_check(requirement, phase, acceptances, checks)
        rows.append(RequirementRow(
            phase, requirement, texts.get(requirement, ""), status, nxt, check, len(traced),
            tasks_done=sum(1 for task in traced if task.get("lifecycle_state") == "done"),
            confidence=confidence,
            check_kind=check.evidence_kind if check else "",
            check_at=check.recorded_at if check else None,
        ))
    design = _newest(_for_phase(designs, phase, effort))
    subjects = _split_csv(_payload(design).get("decisions")) if design else []
    report = _newest(_for_phase(reports, phase, effort))
    integration = None
    if report is not None:
        integration = IntegrationView(_payload(report).get("result", ""), _section(report.get("body") or "", "Conflicts"))
    stage, release_ready = _stage(
        phase, effort, spec_ids, designs, tasks, acceptances, checks, assessments, reports, releases,
    )
    latest_release = _newest(_for_phase(releases, phase, effort))
    release_state = _payload(latest_release).get("state", "") if latest_release else ""
    return PhaseEvidence(
        phase, _payload(spec).get("weight", ""), tuple(rows), stage, integration, release_ready,
        _choices(subjects, decisions), _section(spec.get("body") or "", "Non-goals"),
        release_state=release_state,
    )


def load_snapshot(target: Target, now: datetime | None = None) -> Snapshot:
    now = now or datetime.now(timezone.utc)
    token = change_token(target)
    listed = _list_all(target, _SNAPSHOT_TYPES)
    aliases = _merge_aliases(listed["project:active-goal"])
    listed = {record_type: _remapped(records, aliases) for record_type, records in listed.items()}
    goals = [
        r for r in listed["project:active-goal"]
        if r["lifecycle_state"] == "active" and _payload(r).get("status") != "closed"
    ]
    phases = _by_effort(listed["project:phase"])
    all_tasks = listed["project:work-item"]
    tasks = _by_effort(all_tasks)
    questions = _by_effort(listed["project:continuity-question"], "subject")
    findings = _by_effort(listed["project:finding"])
    checks_all = listed["project:check-run"]
    checks = _by_effort(checks_all)
    acceptances_all = _remapped(_list(target, "project:acceptance"), aliases)
    acceptances = _by_effort(acceptances_all)
    acceptances_by_id = {record["id"]: record for record in acceptances_all}
    efforts_by_work_item = {}
    for task in all_tasks:
        entry = (_payload(task).get("effort"), task["subject"])
        efforts_by_work_item[task["id"]] = entry
        efforts_by_work_item.setdefault(task["subject"], entry)
    specs = listed["project:specification"]
    designs = listed["project:design"]
    assessments = listed["project:assessment"]
    integrations = listed["project:integration-report"]
    releases = listed["project:release"]
    backlog_by_effort = _by_effort(listed.get("project:backlog-item") or [])
    decisions = _remapped(_list(target, "project:decision"), aliases) if designs else []
    structured = _structured_phases(specs)
    specs_by_effort = _by_effort(specs)
    designs_by_effort = _by_effort(designs)
    assessments_by_effort = _by_effort(assessments)
    integrations_by_effort = _by_effort(integrations)
    releases_by_effort = _by_effort(releases)
    decisions_by_effort = _by_effort(decisions)
    activity = _activity(
        listed["project:assignment"], listed["project:execution-report"], checks_all,
        efforts_by_work_item, now - RECENT, assessments, integrations, releases, structured,
    )
    positions = {
        record["subject"]: _payload(record).get("position", "")
        for record in listed["project:current-position"]
        if record["lifecycle_state"] == "active"
        and _payload(record).get("status") != "closed"
        and _payload(record).get("scope") == "effort"
    }
    from dashboard.journal import KIND_JOURNAL, load_journal, ordered as journal_ordered

    efforts = []
    for goal in sorted(goals, key=lambda record: record["subject"]):
        effort = goal["subject"]
        effort_tasks = tasks.get(effort, [])
        effort_acceptances = acceptances.get(effort, [])
        effort_checks = checks.get(effort, [])
        evidence_by_phase = {}
        for spec_effort, phase in structured:
            if spec_effort != effort:
                continue
            evidence = _phase_evidence(
                phase, effort, specs_by_effort.get(effort, []), designs_by_effort.get(effort, []),
                decisions_by_effort.get(effort, []), effort_tasks, effort_acceptances, effort_checks,
                assessments_by_effort.get(effort, []), integrations_by_effort.get(effort, []),
                releases_by_effort.get(effort, []),
            )
            if evidence is not None:
                evidence_by_phase[phase] = evidence
        phase_rows = _phase_rows(
            phases.get(effort, []), effort_tasks, effort_acceptances, effort_checks, evidence_by_phase,
        )
        kind = _payload(goal).get("kind") or ""
        journal_open = []
        if kind in KIND_JOURNAL:
            open_items, _ = journal_ordered(load_journal(target, effort))
            journal_open = open_items
        efforts.append(EffortView(
            effort=effort,
            goal=_payload(goal).get("goal", ""),
            phases=phase_rows,
            tasks=_task_rows(
                effort_tasks,
                listed["project:assignment"],
                listed["project:assignment-amendment"],
                listed["project:execution-report"],
                effort_checks,
            ),
            needs_you=_needs_you(
                questions.get(effort, []), findings.get(effort, []), effort_checks, acceptances_by_id,
                effort_tasks, assessments_by_effort.get(effort, []), integrations_by_effort.get(effort, []),
                {phase for spec_effort, phase in structured if spec_effort == effort},
            ),
            activity=activity.get(effort, []),
            release_ready=any(row.evidence is not None and row.evidence.release_ready for row in phase_rows),
            position=positions.get(effort, ""),
            kind=kind,
            journal_open=journal_open,
            backlog=_backlog_items(backlog_by_effort.get(effort, [])),
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
    evidence_kind: str = ""


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
class AgentAssignment:
    id: str
    subject: str
    recorded_at: datetime
    executor: str
    orientation: str
    body: str


@dataclass(frozen=True)
class AgentAmendment:
    id: str
    recorded_at: datetime
    correction: str


@dataclass(frozen=True)
class AgentReport:
    id: str
    recorded_at: datetime
    result: str
    verdict: str
    body: str


@dataclass(frozen=True)
class AgentWork:
    assignment: AgentAssignment
    amendments: tuple[AgentAmendment, ...]
    report: AgentReport | None


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
    running_since: datetime | None = None
    requirements: str = ""
    decisions: str = ""
    size: str = ""
    estimate_minutes: int | None = None
    executor: str = "subagent"
    agent_work: tuple[AgentWork, ...] = ()


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
        latest[payload.get("criterion_id", "")] = _check_from(record)
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


def _amendments_for(
    assignment: dict[str, Any], amendments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    keys = {assignment["id"], assignment["subject"]}
    matched = [record for record in amendments if _payload(record).get("assignment") in keys]
    matched.sort(key=_recorded_at)
    return matched


def _report_for(
    assignment: dict[str, Any], reports: list[dict[str, Any]],
) -> dict[str, Any] | None:
    keys = {assignment["id"], assignment["subject"]}
    matched = [record for record in reports if _payload(record).get("assignment") in keys]
    return max(matched, key=_recorded_at) if matched else None


def _agent_work(
    assignments: list[dict[str, Any]],
    amendments: list[dict[str, Any]],
    reports: list[dict[str, Any]],
) -> tuple[AgentWork, ...]:
    """Group assignment bodies, amendments by payload.assignment, and reports; newest first."""
    works: list[AgentWork] = []
    for record in sorted(assignments, key=_recorded_at, reverse=True):
        body = record.get("body") or ""
        assignment = AgentAssignment(
            id=record["id"],
            subject=record["subject"],
            recorded_at=_recorded_at(record),
            executor=_payload(record).get("executor", ""),
            orientation=_section(body, "Orientation"),
            body=_without_section(body, "Orientation"),
        )
        amend_rows = tuple(
            AgentAmendment(
                record_a["id"],
                _recorded_at(record_a),
                _section(record_a.get("body") or "", "Correction"),
            )
            for record_a in _amendments_for(record, amendments)
        )
        report_record = _report_for(record, reports)
        report = None
        if report_record is not None:
            payload = _payload(report_record)
            report = AgentReport(
                id=report_record["id"],
                recorded_at=_recorded_at(report_record),
                result=payload.get("result", ""),
                verdict=payload.get("verdict", ""),
                body=report_record.get("body") or "",
            )
        works.append(AgentWork(assignment, amend_rows, report))
    return tuple(works)


def load_task_detail(target: Target, work_item_id: str) -> TaskDetail:
    """Load one task's records with four CLI calls.

    `get` yields the subject, effort, body, and outbound depends_on; one `list --subject --full`
    yields every record for the slug; one work-item `list` for the effort names linked tasks; one goal `list` maps merged efforts.
    """
    item = _run(target, "get", "--type", "project:work-item", "--id", work_item_id)
    if "subject" not in item:
        raise ModelError(f"get project:work-item {work_item_id} returned unreadable output")
    aliases = _merge_aliases(_list(target, "project:active-goal"))
    item = _remapped([item], aliases)[0]
    slug, payload = item["subject"], _payload(item)
    effort = payload.get("effort", "")
    records = _remapped(_run(target, "list", "--subject", slug, "--full").get("records", []), aliases)
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
    status = _task_status(mine) or mine["lifecycle_state"]
    return TaskDetail(
        id=work_item_id, subject=slug, effort=effort, title=payload.get("title", ""),
        status=status, phase=payload.get("phase", ""),
        wave=_derived(mine).get("wave"), assignee=payload.get("assignee", ""), body=item.get("body") or "",
        depends_on=_linked((item.get("relationships") or {}).get("depends_on", []), rows),
        blocks=_linked((_derived(mine).get("referenced_by") or {}).get("depends_on", []), rows),
        acceptances=acceptances, timeline=_timeline(assignments, amendments, reports, checks), related=related,
        running_since=max(map(_recorded_at, assignments), default=None) if status == "running" else None,
        requirements=payload.get("requirements") or "", decisions=payload.get("decisions") or "",
        size=_size(payload), estimate_minutes=_estimate_minutes(payload), executor=_executor(payload),
        agent_work=_agent_work(assignments, amendments, reports),
    )


TABS = ("overview", "spec", "design", "decisions", "evidence", "tasks")
SIMPLE_TABS = ("overview", "spec", "decisions", "tasks")


@dataclass(frozen=True)
class DecisionEntry:
    subject: str
    phase: str
    choice: str
    alternatives: str
    rationale: str
    counter: str
    superseded: tuple["DecisionEntry", ...] = ()


@dataclass(frozen=True)
class DecisionLog:
    groups: tuple[tuple[str, tuple[DecisionEntry, ...]], ...]


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
    evidence: PhaseEvidence | None = None
    spec_body: str = ""
    design_body: str = ""
    structured: bool = False


def tabs_for(detail: PhaseDetail) -> tuple[str, ...]:
    """Full tab set for a structured phase; simple set otherwise (R1)."""
    return TABS if detail.structured else SIMPLE_TABS


def _decision_entry(
    record: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    history: bool,
) -> DecisionEntry:
    payload = _payload(record)
    body = record.get("body") or ""
    superseded: tuple[DecisionEntry, ...] = ()
    if history:
        kids = []
        for ref in (record.get("relationships") or {}).get("supersedes") or []:
            predecessor = by_id.get(ref)
            if predecessor is not None:
                kids.append(_decision_entry(predecessor, by_id, history))
        superseded = tuple(kids)
    return DecisionEntry(
        subject=record["subject"],
        phase=payload.get("phase", ""),
        choice=payload.get("choice", ""),
        alternatives=payload.get("alternatives", "") or "",
        rationale=_section(body, "Rationale"),
        counter=_section(body, "Counter-argument"),
        superseded=superseded,
    )


def load_decision_log(
    target: Target, effort: str, phase: str | None, history: bool,
) -> DecisionLog:
    """Phase- or effort-scoped decisions, with optional superseded chains (R7)."""
    aliases = _merge_aliases(_list(target, "project:active-goal"))
    phase_records = [
        record for record in _remapped(_list(target, "project:phase"), aliases)
        if _payload(record).get("effort") == effort
    ]
    phase_records.sort(key=lambda record: (_payload(record).get("ordinal", 0), record["subject"]))
    titles = {
        record["subject"]: _payload(record).get("title") or record["subject"]
        for record in phase_records
    }

    listed = _remapped(
        _list(target, "project:decision", where=(f"payload.effort={effort}",), full=True),
        aliases,
    )
    by_id = {record["id"]: record for record in listed}
    if history:
        for record in _remapped(
            _list(
                target, "project:decision", state="superseded",
                where=(f"payload.effort={effort}",), full=True,
            ),
            aliases,
        ):
            by_id.setdefault(record["id"], record)

    active = [
        record for record in by_id.values()
        if record.get("lifecycle_state") not in INACTIVE_STATES
        and _payload(record).get("effort") in (None, "", effort)
        and (phase is None or _payload(record).get("phase") == phase)
    ]
    active.sort(key=lambda record: (record["subject"], record["id"]))

    grouped: dict[str, list[DecisionEntry]] = {}
    for record in active:
        phase_subject = _payload(record).get("phase") or ""
        title = titles.get(phase_subject, phase_subject)
        grouped.setdefault(title, []).append(_decision_entry(record, by_id, history))

    ordered_titles = [
        titles[record["subject"]]
        for record in phase_records
        if titles[record["subject"]] in grouped
    ]
    for title in grouped:
        if title not in ordered_titles:
            ordered_titles.append(title)
    return DecisionLog(tuple(
        (title, tuple(grouped[title])) for title in ordered_titles
    ))


def load_phase_detail(target: Target, effort: str, phase_subject: str) -> PhaseDetail:
    """Load one phase with its body, decisions, constraints, and tasks."""
    aliases = _merge_aliases(_list(target, "project:active-goal"))

    def by_effort(record_type: str) -> dict[str, list[dict[str, Any]]]:
        return _by_effort(_remapped(_list(target, record_type), aliases))

    snapshot_phases = by_effort("project:phase").get(effort, [])
    record = next((r for r in snapshot_phases if r["subject"] == phase_subject), None)
    if record is None:
        raise ModelError(f"phase {phase_subject} not found in {effort}")
    item = _run(target, "get", "--type", "project:phase", "--id", record["id"])
    tasks = _by_effort(_list(target, "project:work-item")).get(effort, [])
    effort_acceptances = by_effort("project:acceptance").get(effort, [])
    effort_checks = by_effort("project:check-run").get(effort, [])
    decision_records = by_effort("project:decision").get(effort, [])
    row = next(
        (p for p in _phase_rows([record], tasks, effort_acceptances, effort_checks)),
        None,
    )
    phase_specs = _remapped(
        _list(target, "project:specification", where=(f"payload.phase={phase_subject}",), full=True),
        aliases,
    )
    phase_designs = _remapped(
        _list(target, "project:design", where=(f"payload.phase={phase_subject}",), full=True),
        aliases,
    )
    spec = _newest(_for_phase(phase_specs, phase_subject, effort))
    design = _newest(_for_phase(phase_designs, phase_subject, effort))
    evidence = _phase_evidence(
        phase_subject, effort,
        phase_specs,
        phase_designs,
        decision_records, tasks, effort_acceptances, effort_checks,
        by_effort("project:assessment").get(effort, []),
        by_effort("project:integration-report").get(effort, []),
        by_effort("project:release").get(effort, []),
    )
    decisions = [
        RelatedRecord("decision", r["id"], r["subject"], _payload(r).get("choice", ""))
        for r in decision_records
        if _payload(r).get("phase") == phase_subject and r["lifecycle_state"] not in INACTIVE_STATES
    ]
    constraints = [
        RelatedRecord("constraint", r["id"], r["subject"], _payload(r).get("statement", ""))
        for r in by_effort("project:constraint").get(effort, [])
        if _payload(r).get("applies_to") == phase_subject and r["lifecycle_state"] not in INACTIVE_STATES
    ]
    payload = _payload(record)
    return PhaseDetail(
        subject=phase_subject, effort=effort, title=payload.get("title", ""), state=record["lifecycle_state"],
        awaiting_signoff=bool(row and row.awaiting_signoff), body=item.get("body") or "",
        decisions=decisions, constraints=constraints,
        tasks=[t for t in _task_rows(tasks) if t.phase == phase_subject],
        evidence=evidence,
        spec_body=(spec.get("body") or "") if spec else "",
        design_body=(design.get("body") or "") if design else "",
        structured=spec is not None,
    )


def load_requirement_detail(target: Target, effort: str, phase: str, requirement: str) -> RequirementDetail:
    """Load one requirement, including superseded assessments oldest first."""
    aliases = _merge_aliases(_list(target, "project:active-goal"))

    def listed(record_type: str, state: str | None = None) -> list[dict[str, Any]]:
        return _remapped(_list(target, record_type, state=state), aliases)

    specs = listed("project:specification")
    by_id = {record["id"]: record for record in listed("project:assessment")}
    for record in listed("project:assessment", "superseded"):
        by_id.setdefault(record["id"], record)
    history = [
        record for record in by_id.values()
        if _payload(record).get("phase") == phase
        and _payload(record).get("requirement") == requirement
        and _payload(record).get("effort") in (None, "", effort)
    ]
    history = _oldest_first(history)
    active = [record for record in history if record.get("lifecycle_state") not in INACTIVE_STATES]
    latest = _newest(active)
    if latest is None:
        status, nxt = "unassessed", ""
    else:
        status, nxt = _payload(latest).get("status", ""), _payload(latest).get("next", "")
    spec = _newest(_for_phase(specs, phase, effort))
    text = _requirement_texts(spec.get("body") or "").get(requirement, "") if spec else ""
    traced = [
        task for task in _traced_records(listed("project:work-item"), phase, requirement)
        if _payload(task).get("effort") in (None, "", effort)
    ]
    traced.sort(key=lambda record: record["subject"])
    subjects: list[str] = []
    for task in traced:
        for subject in _split_csv(_payload(task).get("decisions")):
            if subject not in subjects:
                subjects.append(subject)
    acceptances = [
        record for record in _for_phase(listed("project:acceptance"), phase, effort)
        if _payload(record).get("requirement") == requirement
    ]
    acceptances.sort(key=_recorded_at)
    latest_checks = _latest_checks(listed("project:check-run"))
    return RequirementDetail(
        phase, requirement, text, status, nxt,
        _choices(subjects, listed("project:decision")),
        tuple(row for row in _task_rows(traced) if row.phase == phase),
        tuple(
            AcceptanceRow(
                record["id"], record["subject"], _payload(record).get("criterion", ""),
                _payload(record).get("method", ""), _payload(record).get("verify_command", ""),
                latest_checks.get(record["id"]),
            )
            for record in acceptances
        ),
        tuple(
            AssessmentView(
                record["id"], _payload(record).get("status", ""), _payload(record).get("level") or "",
                _payload(record).get("next", ""), _payload(record).get("confidence", ""),
            )
            for record in history
        ),
    )
