"""Contract-driven helpers shared by the test modules.

Nothing here hardcodes today's record type names or counts — every helper
walks whatever `records`/`bundles` the resolved contract currently declares,
so the suite keeps working as the contract gains or changes record types.
"""

from __future__ import annotations

import itertools
import json
import subprocess
import sys
from collections import deque
from typing import Any

from conftest import CLI, REPO_ROOT

_COUNTER = itertools.count()

# The CLI has no clock option, so shift datetime.now inside a CLI subprocess to write a past recorded_at.
_PAST_CLOCK = """
import datetime as _dt, runpy, sys
_real = _dt.datetime
class _Past(_real):
    @classmethod
    def now(cls, tz=None):
        return _real.now(tz) - _dt.timedelta(hours=48)
_dt.datetime = _Past
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
"""


def run_cli_48h_ago(store, *args: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-c", _PAST_CLOCK, str(CLI), "--root", str(store), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def transition(cli, record_type: str, record: dict, *states: str) -> dict:
    for state in states:
        result = cli(
            "update", "--type", record_type, "--id", record["id"],
            "--transition", state, "--expected-revision", record["revision"],
        )
        assert result.returncode == 0, result.stdout + result.stderr
        record = json.loads(result.stdout)["record"]
    return record


def record_defs_by_id(contract: dict) -> dict[str, dict]:
    return {r["id"]: r for r in contract["records"]}


def advertises_supersedes(record_def: dict) -> bool:
    return "supersedes" in record_def.get("relationships", [])


def generic_payload_value(field: str) -> Any:
    if field == "blocking":
        return True
    if field == "ordinal":
        return 1
    return f"test-{field}"


def generic_body(record_def: dict) -> str | None:
    required = record_def.get("required_sections") or []
    if not required:
        return None
    parts = [f"## {name}\n\nplaceholder text for {name}." for name in required]
    return "\n\n".join(parts)


def unique_subject(record_def: dict) -> str:
    name = record_def["name"]
    return f"test-{name}-{next(_COUNTER)}"


def create_generic_record(
    cli,
    defs: dict[str, dict],
    record_type: str,
    *,
    subject: str | None = None,
    extra_payload: dict | None = None,
    target_cache: dict[str, str] | None = None,
) -> dict:
    """Create a minimal-but-valid record of `record_type`, recursively
    satisfying any `payload_references` it declares. Returns the parsed
    `record` dict from the CLI's JSON response.
    """
    if target_cache is None:
        target_cache = {}
    record_def = defs[record_type]
    subject = subject or unique_subject(record_def)
    payload_refs = record_def.get("payload_references", {})
    payload: dict[str, Any] = {}
    for field in record_def.get("payload", []):
        if field == "subject":
            continue
        if field in payload_refs:
            target_type = payload_refs[field]
            if target_type not in target_cache:
                target_record = create_generic_record(cli, defs, target_type, target_cache=target_cache)
                target_cache[target_type] = target_record["subject"]
            payload[field] = target_cache[target_type]
        else:
            payload[field] = generic_payload_value(field)
    if extra_payload:
        payload.update(extra_payload)
    args = ["create", "--type", record_type, "--subject", subject, "--payload", json.dumps(payload)]
    body = generic_body(record_def)
    if body:
        args.extend(["--body", body])
    result = cli(*args)
    assert result.returncode == 0, (
        f"create {record_type} failed (exit {result.returncode}): {result.stdout}\n{result.stderr}"
    )
    return json.loads(result.stdout)["record"]


def transitions_graph(record_def: dict) -> dict[str, list[str]]:
    return record_def.get("lifecycle", {}).get("transitions", {}) or {}


def all_edges(record_def: dict) -> list[tuple[str, str]]:
    graph = transitions_graph(record_def)
    return [(src, dest) for src, dests in graph.items() for dest in dests]


def shortest_path(record_def: dict, target_state: str) -> list[str]:
    """BFS shortest path of states from the lifecycle's initial state to
    `target_state`, inclusive of both endpoints."""
    initial = record_def["lifecycle"]["initial"]
    if target_state == initial:
        return [initial]
    graph = transitions_graph(record_def)
    frontier = deque([[initial]])
    seen = {initial}
    while frontier:
        path = frontier.popleft()
        node = path[-1]
        for nxt in graph.get(node, []):
            if nxt in seen:
                continue
            new_path = path + [nxt]
            if nxt == target_state:
                return new_path
            seen.add(nxt)
            frontier.append(new_path)
    raise AssertionError(f"no path from {initial!r} to {target_state!r} in {graph!r}")


def drive_to_state(cli, defs: dict[str, dict], record_type: str, target_state: str) -> dict:
    """Create a fresh record of `record_type` and drive it along a shortest
    path to `target_state`, using `supersede` where the contract requires it
    and plain `update --transition` otherwise. Returns the record dict at
    `target_state` (note: `supersede` mints a new id, so the returned record's
    id can differ from the one `create` produced)."""
    record_def = defs[record_type]
    path = shortest_path(record_def, target_state)
    record = create_generic_record(cli, defs, record_type)
    for dest in path[1:]:
        record = _apply_transition(cli, record_def, record_type, record, dest)
    assert record["lifecycle_state"] == target_state
    return record


def _apply_transition(cli, record_def: dict, record_type: str, record: dict, dest: str) -> dict:
    """Drive `record` from its current state to `dest` and return the record
    that actually reached `dest`.

    `supersede` reaches "superseded" by retiring the *old* id (the new id it
    mints stays at the initial state) -- so for that op the record "at dest"
    is the predecessor, read back fresh to prove the write really landed.
    """
    if dest == "superseded" and advertises_supersedes(record_def):
        result = cli(
            "supersede",
            "--type", record_type,
            "--id", record["id"],
            "--expected-revision", record["revision"],
            "--payload", json.dumps(record["payload"]),
        )
        assert result.returncode == 0, (
            f"supersede {record_type} -> {dest} failed (exit {result.returncode}): "
            f"{result.stdout}\n{result.stderr}"
        )
        readback = cli("get", "--type", record_type, "--id", record["id"])
        assert readback.returncode == 0, readback.stdout + readback.stderr
        return json.loads(readback.stdout)
    result = cli(
        "update",
        "--type", record_type,
        "--id", record["id"],
        "--transition", dest,
        "--expected-revision", record["revision"],
    )
    assert result.returncode == 0, (
        f"transition {record_type} -> {dest} failed (exit {result.returncode}): "
        f"{result.stdout}\n{result.stderr}"
    )
    return json.loads(result.stdout)["record"]
