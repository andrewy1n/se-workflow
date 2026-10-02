"""Extract identity, time, cost and skill fields from transcript events."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import datetime


def _parse(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _is_human_prompt(event: dict) -> bool:
    if event.get("isMeta") or event.get("isSidechain"):
        return False
    content = (event.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return any(isinstance(b, dict) and b.get("type") != "tool_result" for b in content)
    return False


def _skill_names(event: dict) -> Iterable[str]:
    content = (event.get("message") or {}).get("content")
    if not isinstance(content, list):
        return
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Skill":
            name = (block.get("input") or {}).get("skill")
            if isinstance(name, str) and name:
                yield name


def session_fields(events: Iterable[dict]) -> dict:
    session_id = cwd = branch = None
    first = last = None
    turns = 0
    cost = None
    skills: Counter[str] = Counter()
    for event in events:
        session_id = session_id or event.get("sessionId")
        cwd = cwd or event.get("cwd")
        branch = branch or event.get("gitBranch")
        kind = event.get("type")
        if kind == "cost-state":
            value = event.get("totalCostUSD")
            if isinstance(value, (int, float)):
                cost = float(value)
            continue
        stamp = _parse(event.get("timestamp"))
        if stamp is not None:
            raw = event["timestamp"]
            if first is None or stamp < first[0]:
                first = (stamp, raw)
            if last is None or stamp > last[0]:
                last = (stamp, raw)
        if kind == "user" and _is_human_prompt(event):
            turns += 1
        elif kind == "assistant":
            skills.update(_skill_names(event))
    return {
        "session_id": session_id,
        "cwd": cwd,
        "branch": branch,
        "start": first[1] if first else None,
        "end": last[1] if last else None,
        "duration_seconds": (last[0] - first[0]).total_seconds() if first else None,
        "turns": turns,
        "cost_usd": cost,
        "skills": dict(skills),
    }
