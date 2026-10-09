"""Pure gate vocabulary for Needs you labels, prompts, next-step, and quiet."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from dashboard.landing import Landing, landing_branch, phase_landing, rev_parse_token
from dashboard.model import NEEDS_ORDER, EffortView, NeedsYouItem, PhaseRow, Snapshot, TaskRow

PLAN_REVIEW_PREFIX = "plan-review:"

_LOOP_SKILL = {
    "specify": "discuss",
    "design": "discuss",
    "plan": "plan-phase",
    "execute": "execute-phase",
    "integrate": "execute-phase",
    "verify": "verify-work",
}


class _LandingState(Protocol):
    exists: bool
    merged: bool


def _plan_review_slug(item: NeedsYouItem) -> str | None:
    if item.kind not in ("blocking-question", "open-question"):
        return None
    if not item.text.startswith(PLAN_REVIEW_PREFIX):
        return None
    return item.text[len(PLAN_REVIEW_PREFIX):]


def _phase_title(view: EffortView, slug: str) -> str:
    for phase in view.phases:
        if phase.subject == slug:
            return phase.title
    return slug


def item_text(item: NeedsYouItem, view: EffortView) -> str:
    """Text beside the action label; phase title for plan-review scopes (R2)."""
    slug = _plan_review_slug(item)
    if slug is not None:
        return _phase_title(view, slug)
    return item.text


def action_label(item: NeedsYouItem, view: EffortView) -> str:
    """Action verb for a Needs you item (R1); plan-review uses Review plan (R2)."""
    if _plan_review_slug(item) is not None:
        return "Review plan"
    if item.kind in ("blocking-question", "open-question"):
        return "Answer"
    if item.kind == "needs-human":
        return "Decide"
    if item.kind == "unsigned-check":
        return "Sign off"
    if item.kind == "loop-route":
        return f"Route to {item.next}" if item.next else "Route to"
    if item.kind == "integration":
        return "Fix integration"
    if item.kind == "merge-branch":
        return "Merge branch"
    return item.kind


def prompt(item: NeedsYouItem, view: EffortView) -> str:
    """Ready agent string naming the effort, subject or phase, and action (R3)."""
    effort = view.effort
    slug = _plan_review_slug(item)
    if slug is not None:
        return (
            f"Walk me through the plan for phase {slug} (effort {effort}) "
            f"so I can review it."
        )
    if item.kind == "unsigned-check":
        return f"Sign off the manual check for {item.subject} (effort {effort})."
    if item.kind == "blocking-question":
        return f"Answer the blocking question about {item.text} (effort {effort})."
    if item.kind == "open-question":
        return f"Answer the open question about {item.text} (effort {effort})."
    if item.kind == "needs-human":
        claim = f": {item.text}" if item.text else ""
        return f"Decide on the finding {item.subject} (effort {effort}){claim}."
    if item.kind == "loop-route":
        req = item.requirement or item.subject
        phase = item.phase or "phase"
        nxt = item.next or "next"
        return f"Route to {nxt} for {req} in phase {phase} (effort {effort})."
    if item.kind == "integration":
        phase = item.phase or item.subject
        result = item.result or "failed"
        return f"Fix the {result} integration for phase {phase} (effort {effort})."
    if item.kind == "merge-branch":
        phase = item.phase or item.subject
        return f"Merge the phase branch for phase {phase} (effort {effort})."
    return f"Act on {item.subject} (effort {effort})."


def _phase_tasks(view: EffortView, phase: str) -> list[TaskRow]:
    return [task for task in view.tasks if task.phase == phase and task.status != "withdrawn"]


def _has_decisions(phase: PhaseRow) -> bool:
    evidence = phase.evidence
    if evidence is None:
        return False
    return any(choice.choice for choice in evidence.decisions)


def _unmerged_done_slug(view: EffortView, landing: dict[str, Landing | _LandingState]) -> str | None:
    for phase in sorted(view.phases, key=lambda row: row.ordinal):
        if phase.state != "done":
            continue
        state = landing.get(phase.subject)
        if state is not None and state.exists and not state.merged:
            return phase.subject
    return None


def next_step(view: EffortView, landing: dict[str, Landing]) -> str:
    """First matching R4 skill-named line (no `next:` prefix; position is UI-only)."""
    for item in view.needs_you:
        slug = _plan_review_slug(item)
        if slug is not None and item.kind == "blocking-question":
            return f"review the {slug} plan (plan-phase)"
        if item.kind == "blocking-question":
            return f"answer: {item.text}"

    merge_slug = _unmerged_done_slug(view, landing)
    if merge_slug is not None:
        return f"merge phase/{merge_slug} (execute-phase)"

    for item in view.needs_you:
        if item.kind == "loop-route":
            nxt = item.next or "next"
            req = item.requirement or item.subject
            skill = _LOOP_SKILL.get(nxt, nxt)
            return f"{nxt} for {req} ({skill})"
        if item.kind == "unsigned-check":
            return f"sign off {item.subject} (verify-work)"

    running = [task for task in view.tasks if task.status == "running"]
    if running:
        waves = [task.wave for task in running if task.wave is not None]
        wave = min(waves) if waves else 0
        return f"wave {wave} running: {len(running)} tasks"

    ready = [task for task in view.tasks if task.status == "ready"]
    if ready:
        waves = [task.wave for task in ready if task.wave is not None]
        wave = min(waves) if waves else 0
        return f"execute-phase wave {wave}"

    for phase in sorted(view.phases, key=lambda row: row.ordinal):
        if phase.state != "in_progress":
            continue
        tasks = _phase_tasks(view, phase.subject)
        if tasks and all(task.status == "done" for task in tasks):
            return f"close {phase.subject} (verify-work)"

    for phase in sorted(view.phases, key=lambda row: row.ordinal):
        if phase.state != "planned":
            continue
        if _has_decisions(phase):
            return f"plan-phase {phase.subject}"
        return f"discuss {phase.subject}"

    if view.phases and all(phase.state == "done" for phase in view.phases):
        return "close the effort or add a phase"

    return ""


def is_quiet(task: TaskRow, now: datetime) -> bool:
    """True when a running task's last record is older than 2×estimate or 60m (R7)."""
    if task.status != "running":
        return False
    last = getattr(task, "last_record_at", None)
    if last is None:
        return False
    if task.estimate_minutes is not None:
        limit = timedelta(minutes=2 * task.estimate_minutes)
    else:
        limit = timedelta(minutes=60)
    return (now - last) > limit


def landing_summary(state: Landing) -> str:
    """Selector suffix for a phase Landing (R5): branch/ahead/merged, or no branch yet."""
    if not state.exists:
        return "no branch yet"
    status = "merged" if state.merged else "not merged"
    return f"{state.branch} · {state.ahead} ahead · {status}"


def merge_landing_needs(
    view: EffortView, landing: dict[str, Landing | _LandingState],
) -> EffortView:
    """Append merge-branch Needs you items for unmerged done phases (R6); re-sort by NEEDS_ORDER."""
    extras: list[NeedsYouItem] = []
    for phase in sorted(view.phases, key=lambda row: row.ordinal):
        if phase.state != "done":
            continue
        state = landing.get(phase.subject)
        if state is None or not state.exists or state.merged:
            continue
        extras.append(NeedsYouItem(
            kind="merge-branch",
            id=f"merge:{phase.subject}",
            subject=phase.subject,
            text=state.branch,
            body=f"{state.ahead} ahead",
            phase=phase.subject,
        ))
    items = [item for item in view.needs_you if item.kind != "merge-branch"] + extras
    items.sort(key=lambda entry: NEEDS_ORDER.index(entry.kind))
    fields = {
        "effort": view.effort,
        "goal": view.goal,
        "phases": view.phases,
        "tasks": view.tasks,
        "needs_you": items,
        "activity": view.activity,
        "release_ready": view.release_ready,
    }
    if hasattr(view, "position"):
        fields["position"] = view.position
    return EffortView(**fields)


def landing_for_view(root: Path, view: EffortView) -> dict[str, Landing]:
    """Compute phase_landing for each phase (same path the app and status use)."""
    landing: dict[str, Landing] = {}
    for phase in view.phases:
        state = phase_landing(root, phase.body, phase.subject)
        if state is not None:
            landing[phase.subject] = state
    return landing


def landings_for_snapshot(root: Path, snapshot: Snapshot) -> dict[str, dict[str, Landing]]:
    """Per-effort landing maps for a full snapshot."""
    return {view.effort: landing_for_view(root, view) for view in snapshot.efforts}


def landing_refs_for_snapshot(snapshot: Snapshot) -> list[str]:
    """main plus distinct Landing branch names from phase bodies (no git)."""
    refs: list[str] = ["main"]
    seen = {"main"}
    for view in snapshot.efforts:
        for phase in view.phases:
            branch = landing_branch(phase.body, phase.subject)
            if branch is not None and branch not in seen:
                seen.add(branch)
                refs.append(branch)
    return refs


def landing_cache_token(root: Path, snapshot: Snapshot) -> str | None:
    """Cache key from per-ref `git rev-parse` of main and Landing branches."""
    parts: list[str] = []
    for ref in landing_refs_for_snapshot(snapshot):
        sha = rev_parse_token(root, ref)
        parts.append(sha.strip() if sha else f"missing:{ref}")
    return "\n".join(parts) if parts else None


def apply_landing_needs(
    snapshot: Snapshot, landings: dict[str, dict[str, Landing]],
) -> Snapshot:
    """Return a snapshot whose Needs you lists include Merge branch items (shared with status)."""
    efforts = [
        merge_landing_needs(view, landings.get(view.effort, {}))
        for view in snapshot.efforts
    ]
    return Snapshot(efforts, snapshot.token, snapshot.generated_at)


def needs_you_count(view: EffortView, landing: dict[str, Landing | _LandingState]) -> int:
    """Needs you length after landing merge — same count the app and status segment use."""
    return len(merge_landing_needs(view, landing).needs_you)


def count_merged_needs(root: Path, snapshot: Snapshot) -> int:
    """Total Needs you items after merge_landing_needs, across live efforts."""
    total = 0
    for view in snapshot.efforts:
        total += needs_you_count(view, landing_for_view(root, view))
    return total
