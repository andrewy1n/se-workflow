"""Print one JSON summary per session transcript: counts and references only."""

from __future__ import annotations

import json
import queue
import sys
import threading
from pathlib import Path

from record_join import join
from record_reader import subprocess_runner, read_records
from session_fields import session_fields
from session_metrics import ReadStats, read_events
from session_tools import tool_metrics

_DONE = object()


def _drain(q, state):
    while not state["done"]:
        item = q.get()
        if item is _DONE:
            state["done"] = True
            return
        yield item


def summarize(path: Path) -> dict:
    stats = ReadStats()
    q: queue.Queue = queue.Queue(maxsize=256)
    box: dict = {}
    state = {"done": False}

    def worker():
        try:
            box["tools"] = tool_metrics(_drain(q, state))
        finally:
            for _ in _drain(q, state):
                pass

    thread = threading.Thread(target=worker)
    thread.start()

    def fan_out():
        try:
            for event in read_events(path, stats):
                q.put(event)
                yield event
        finally:
            q.put(_DONE)

    try:
        fields = session_fields(fan_out())
    finally:
        thread.join()
    return {**fields, "tools": box["tools"], "bad_lines": stats.bad_lines}


def _store_root() -> Path:
    return Path.home() / ".artifacts"


def _read_all(rows, run, store_root):
    records = []
    cwds = {r["cwd"] for r in rows if r.get("cwd")}
    for cwd in sorted(cwds):
        if not (store_root / Path(cwd).name).is_dir():
            continue
        try:
            records.extend(read_records(cwd, run=run))
        except Exception:
            continue
    return records


def _record_summary(ids, by_id, ambiguous):
    matched = [by_id[i] for i in ids]
    by_type: dict = {}
    for rec in matched:
        by_type[rec["record_type"]] = by_type.get(rec["record_type"], 0) + 1
    return {
        "total": len(matched),
        "by_type": by_type,
        "efforts": sorted({r["effort"] for r in matched if r["effort"]}),
        "tasks": sorted({
            r["subject"] for r in matched
            if r["record_type"] == "project:work-item" and r["subject"]
        }),
        "ambiguous": len(ambiguous),
    }


def _attach_records(rows, run, store_root):
    sessions = [r for r in rows if r.get("session_id")]
    records = _read_all(sessions, run, store_root)
    by_id = {}
    for rec in records:
        by_id.setdefault(rec["id"], rec)
    joined = join(sessions, records)["by_session"]
    for row in sessions:
        hit = joined[row["session_id"]]
        row["records"] = _record_summary(hit["records"], by_id, hit["ambiguous"])


def main(argv: list[str], run=subprocess_runner, store_root: Path | None = None) -> int:
    with_records = "--records" in argv
    args = [a for a in argv if a != "--records"]
    root = Path(args[0]) if args else Path.home() / ".claude" / "projects"
    rows = []
    for path in sorted(root.glob("*/*.jsonl")):
        head = {"project": path.parent.name, "file": path.name}
        try:
            row = {**head, **summarize(path)}
        except Exception as exc:
            row = {**head, "error": type(exc).__name__}
        if with_records:
            rows.append(row)
        else:
            print(json.dumps(row), flush=True)
    if with_records:
        _attach_records(rows, run, store_root or _store_root())
        for row in rows:
            print(json.dumps(row), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
