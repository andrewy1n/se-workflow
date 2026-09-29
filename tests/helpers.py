"""Contract-driven helpers shared by the test modules.

Nothing here hardcodes today's record type names or counts — every helper
walks whatever `records`/`bundles` the resolved contract currently declares,
so the suite keeps working as the contract gains or changes record types.
"""

from __future__ import annotations

import fcntl
import itertools
import json
import os
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any

from conftest import AA_ROOT, CLI, REPO_ROOT

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


TMUX_CONF = REPO_ROOT / "scripts" / "tmux-dashboard.conf"
DEADLINE = 10.0
ANSI = re.compile(r"\x1b(\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(\x07|\x1b\\)|[()][0-9A-Za-z]|[=>78DEHMc])")
_DASHBOARD_ITEM = re.compile(r"^- (?:\*\*(.+?)\*\*|([^*:][^:]*):)")


def section_map(text: str, effort: str) -> dict[str, list[str]]:
    """Map each `### <section>` under `## <effort>` to its sorted item subjects.

    Accepts both `view` markdown (`- **subject**`) and formatted `watch` text (`- subject:`).
    """
    sections: dict[str, list[str]] = {}
    group = current = None
    for line in ANSI.sub("", text).splitlines():
        line = line.rstrip()
        if line.startswith("## "):
            group, current = line[3:], None
        elif line.startswith("### "):
            current = line[4:]
        elif match := _DASHBOARD_ITEM.match(line):
            assert group == effort and current is not None, text
            sections.setdefault(current, []).append(match.group(1) or match.group(2))
    return {name: sorted(subjects) for name, subjects in sections.items()}


def wait_for(probe, what: str, show=lambda: "", deadline: float = DEADLINE):
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        value = probe()
        if value:
            return value
        time.sleep(0.1)
    raise AssertionError(f"timed out waiting for {what}\n{show()}")


class Tmux:
    """An isolated tmux server on its own socket, loaded with the dashboard conf, with a pty client."""

    def __init__(self, home: Path, cwd: Path, cols: int = 120, rows: int = 40):
        self.socket = f"se-wf-test-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("TMUX")}
        self.env.update(
            HOME=str(home), SHELL="/bin/sh", TERM="xterm-256color",
            ADAPTIVE_ARTIFACTS_BIN=str(AA_ROOT / "bin" / "adaptive-artifacts"),
        )
        self.cwd = cwd
        self.cols, self.rows = cols, rows
        self.socket_path: str | None = None
        self.client_pid: int | None = None
        self.client_fd: int | None = None
        self.output = b""

    def __call__(self, *args: str, check: bool = True) -> str:
        result = subprocess.run(
            ["tmux", "-L", self.socket, "-f", str(TMUX_CONF), *args],
            capture_output=True, text=True, env=self.env, cwd=str(self.cwd), timeout=10,
        )
        if check:
            assert result.returncode == 0, f"tmux {args}: {result.stdout}{result.stderr}"
        return result.stdout

    def start(self, session: str, directory: Path) -> None:
        self("new-session", "-d", "-s", session, "-x", str(self.cols), "-y", str(self.rows), "-c", str(directory))
        self.socket_path = self("display", "-p", "#{socket_path}").strip()

    def attach(self, session: str) -> None:
        pid, fd = pty.fork()
        if pid == 0:
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", self.rows, self.cols, 0, 0))
            os.execvpe("tmux", ["tmux", "-L", self.socket, "attach", "-t", session], self.env)
        self.client_pid, self.client_fd = pid, fd
        wait_for(lambda: self("list-clients", "-F", "#{client_tty}").strip(), "client attach")

    def press(self, key: str) -> None:
        prefix = self("show", "-gv", "prefix").strip()
        assert prefix == "C-b", prefix
        self.output = b""
        os.write(self.client_fd, b"\x02" + key.encode())

    def open_side_pane(self, session: str) -> str:
        self.press("S")
        panes = wait_for(lambda: self("list-panes", "-t", session, "-F", "#{pane_id}").split()[1:], "side pane")
        return panes[0]

    def screen_text(self, needles: list[str]) -> str:
        deadline = time.monotonic() + DEADLINE
        while True:
            text = " ".join(ANSI.sub(" ", self.output.decode("utf-8", "replace")).split())
            if all(needle in text for needle in needles) or time.monotonic() > deadline:
                return text
            ready, _, _ = select.select([self.client_fd], [], [], 0.2)
            if ready:
                try:
                    self.output += os.read(self.client_fd, 65536)
                except OSError:
                    return text

    def kill(self) -> None:
        self("kill-server", check=False)
        if self.client_pid is not None:
            try:
                os.kill(self.client_pid, signal.SIGKILL)
                os.waitpid(self.client_pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass
            os.close(self.client_fd)
        if self.socket_path:
            Path(self.socket_path).unlink(missing_ok=True)
