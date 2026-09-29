"""Drive scripts/tmux-dashboard.conf in an isolated tmux server with a client attached in a pty."""

from __future__ import annotations

import fcntl
import json
import os
import pty
import re
import select
import shutil
import signal
import struct
import subprocess
import termios
import time
import uuid
from pathlib import Path

import pytest

import helpers as h
from conftest import AA_ROOT, REPO_ROOT
from test_dashboard_status import _goal, _work_item

pytestmark = pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux is not installed")

CONF = REPO_ROOT / "scripts" / "tmux-dashboard.conf"
STATUS = REPO_ROOT / "scripts" / "dashboard-status"
EFFORT = "tmuxfx"
COLS, ROWS = 120, 40
DEADLINE = 10.0
_ANSI = re.compile(r"\x1b(\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(\x07|\x1b\\)|[()][0-9A-Za-z]|[=>78DEHMc])")


class Tmux:
    def __init__(self, home: Path, cwd: Path):
        self.socket = f"se-wf-test-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("TMUX")}
        self.env.update(
            HOME=str(home), SHELL="/bin/sh", TERM="xterm-256color",
            ADAPTIVE_ARTIFACTS_BIN=str(AA_ROOT / "bin" / "adaptive-artifacts"),
        )
        self.cwd = cwd
        self.socket_path: str | None = None
        self.client_pid: int | None = None
        self.client_fd: int | None = None
        self.output = b""

    def __call__(self, *args: str, check: bool = True) -> str:
        result = subprocess.run(
            ["tmux", "-L", self.socket, "-f", str(CONF), *args],
            capture_output=True, text=True, env=self.env, cwd=str(self.cwd), timeout=10,
        )
        if check:
            assert result.returncode == 0, f"tmux {args}: {result.stdout}{result.stderr}"
        return result.stdout

    def start(self, session: str, directory: Path) -> None:
        self("new-session", "-d", "-s", session, "-x", str(COLS), "-y", str(ROWS), "-c", str(directory))
        self.socket_path = self("display", "-p", "#{socket_path}").strip()

    def attach(self, session: str) -> None:
        pid, fd = pty.fork()
        if pid == 0:
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
            os.execvpe("tmux", ["tmux", "-L", self.socket, "attach", "-t", session], self.env)
        self.client_pid, self.client_fd = pid, fd
        wait_for(lambda: self("list-clients", "-F", "#{client_tty}").strip(), "client attach")

    def press(self, key: str) -> None:
        prefix = self("show", "-gv", "prefix").strip()
        assert prefix == "C-b", prefix
        self.output = b""
        os.write(self.client_fd, b"\x02" + key.encode())

    def screen_text(self, needles: list[str]) -> str:
        deadline = time.monotonic() + DEADLINE
        while True:
            text = " ".join(_ANSI.sub(" ", self.output.decode("utf-8", "replace")).split())
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


def wait_for(probe, what: str, show=lambda: ""):
    deadline = time.monotonic() + DEADLINE
    while time.monotonic() < deadline:
        value = probe()
        if value:
            return value
        time.sleep(0.1)
    raise AssertionError(f"timed out waiting for {what}\n{show()}")


@pytest.fixture()
def seeded(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _goal(cli, defs, EFFORT)
    running = _work_item(cli, defs, EFFORT, "fx-running")
    h.transition(cli, "project:work-item", running, "in_progress")
    _work_item(cli, defs, EFFORT, "fx-ready")
    h.create_generic_record(
        cli, defs, "project:finding", subject="fx-finding",
        extra_payload={"claim": "a human must decide", "needs": "human", "effort": EFFORT},
    )
    return store


@pytest.fixture()
def home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    return home


@pytest.fixture()
def tmux(home, seeded, tmp_path):
    server = Tmux(home, tmp_path)
    try:
        server.start("main", seeded)
        server.attach("main")
        wait_for(lambda: server("display", "-p", "-t", "main", "#{pane_current_path}").strip() == str(seeded), "shell cwd")
        yield server
    finally:
        server.kill()


def _headings(store: Path) -> list[str]:
    return ["Project Dashboard", f"## {EFFORT}", "### Running", "### Ready", "### Needs Human", str(store / ".artifacts")]


def test_prefix_s_opens_a_side_pane_with_the_pane_repo_dashboard(tmux, seeded):
    tmux.press("S")
    panes = wait_for(lambda: tmux("list-panes", "-t", "main", "-F", "#{pane_id}").split()[1:], "side pane")
    side = panes[0]

    def capture() -> str:
        return tmux("capture-pane", "-p", "-t", side)

    def screen() -> str | None:
        text = capture()
        return text if all(heading in text for heading in _headings(seeded)) else None

    text = wait_for(screen, "side pane dashboard", capture)
    assert "fx-running" in text and "fx-ready" in text and "fx-finding" in text
    assert tmux("display", "-p", "-t", side, "#{pane_current_path}").strip() == str(seeded)


def test_prefix_a_binding_is_a_popup_of_the_launcher_in_the_pane_directory(tmux):
    binding = tmux("list-keys", "-T", "prefix", "A")
    assert "display-popup" in binding
    assert '-d "#{pane_current_path}"' in binding
    assert "/dashboard" in binding
    scripts = tmux("show-environment", "-g", "SE_WORKFLOW_SCRIPTS").strip()
    assert scripts == f"SE_WORKFLOW_SCRIPTS={REPO_ROOT / 'scripts'}"


def test_prefix_a_popup_renders_the_pane_repo_dashboard_on_the_client(tmux, seeded):
    tmux.press("A")
    needles = [" ".join(heading.split()) for heading in _headings(seeded)]
    text = tmux.screen_text(needles)
    missing = [needle for needle in needles if needle not in text]
    assert not missing, f"missing {missing} in client output: {text[-2000:]}"
    assert len(tmux("list-panes", "-t", "main", "-F", "#{pane_id}").split()) == 1


def test_status_segment_counts_match_the_seeded_store(home, seeded):
    env = dict(os.environ, HOME=str(home), ADAPTIVE_ARTIFACTS_BIN=str(AA_ROOT / "bin" / "adaptive-artifacts"))
    expected = f"{EFFORT} · 1 running · 1 ready · 1 needs you\n"
    by_arg = subprocess.run([str(STATUS), str(seeded)], capture_output=True, text=True, env=env, timeout=30, input="")
    by_json = subprocess.run(
        [str(STATUS)], capture_output=True, text=True, env=env, timeout=30,
        input=json.dumps({"workspace": {"current_dir": str(seeded)}}), cwd="/",
    )
    assert (by_arg.stdout, by_json.stdout) == (expected, expected), by_arg.stderr + by_json.stderr
