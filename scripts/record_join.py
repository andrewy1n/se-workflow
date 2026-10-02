from datetime import datetime, timezone
from pathlib import PurePosixPath


def _parse(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def _window(session):
    start, end = _parse(session.get("start")), _parse(session.get("end"))
    if start is None or end is None:
        return None
    return start, end


def join(sessions, records):
    by_session = {s["session_id"]: {"records": [], "ambiguous": []} for s in sessions}
    windows = [
        (s["session_id"], PurePosixPath(s.get("cwd") or "").name, _window(s))
        for s in sessions
    ]
    unattached = []
    for rec in records:
        when = _parse(rec["recorded_at"])
        hits = [
            sid for sid, name, win in windows
            if win and name == rec["store"] and win[0] <= when <= win[1]
        ]
        for sid in hits:
            by_session[sid]["records"].append(rec["id"])
            if len(hits) > 1:
                by_session[sid]["ambiguous"].append(rec["id"])
        if not hits:
            unattached.append(rec["id"])
    return {"by_session": by_session, "unattached": unattached}
