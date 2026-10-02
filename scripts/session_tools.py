import json
from pathlib import Path
from typing import Iterable

from session_metrics import read_events


def _blocks(event):
    message = event.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict)]


def _key(name, tool_input):
    return name, json.dumps(tool_input, sort_keys=True, default=str)


def tool_metrics(events: Iterable[dict]) -> dict:
    tools: dict[str, dict[str, int]] = {}
    pending: dict[str, tuple] = {}
    errored: set[tuple] = set()
    for event in events:
        if not isinstance(event, dict):
            continue
        for block in _blocks(event):
            kind = block.get("type")
            if kind == "tool_use":
                name = block.get("name")
                if not isinstance(name, str):
                    continue
                key = _key(name, block.get("input"))
                row = tools.setdefault(name, {"calls": 0, "errors": 0, "retries": 0})
                row["calls"] += 1
                if key in errored:
                    row["retries"] += 1
                if isinstance(block.get("id"), str):
                    pending[block["id"]] = key
            elif kind == "tool_result":
                key = pending.get(block.get("tool_use_id"))
                if key is None:
                    continue
                if block.get("is_error") is True:
                    tools[key[0]]["errors"] += 1
                    errored.add(key)
                else:
                    errored.discard(key)
    totals = {f: sum(r[f] for r in tools.values()) for f in ("calls", "errors", "retries")}
    return {"tools": tools, "totals": totals}


def tool_metrics_for_path(path: Path) -> dict:
    return tool_metrics(read_events(path))
