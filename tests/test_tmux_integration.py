"""Drive scripts/tmux-dashboard.conf in an isolated tmux server with a client attached in a pty."""

from __future__ import annotations

import fcntl
import json
import os
import select
import shutil
import struct
import subprocess
import termios
import time
from pathlib import Path

import pytest

import helpers as h
from conftest import AA_ROOT, REPO_ROOT, git
from test_dashboard_status import _goal, _work_item

pytestmark = pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux is not installed")

STATUS = REPO_ROOT / "scripts" / "dashboard-status"
EFFORT = "tmuxfx"


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
    server = h.Tmux(home, tmp_path)
    try:
        server.start("main", seeded)
        server.attach("main")
        h.wait_for(lambda: server("display", "-p", "-t", "main", "#{pane_current_path}").strip() == str(seeded), "shell cwd")
        yield server
    finally:
        server.kill()


def _markers() -> list[str]:
    return [EFFORT, f"ship {EFFORT}", "title of fx-running", "title of fx-ready", "Running", "Ready", "Needs you", "Done"]


def test_prefix_s_opens_a_side_pane_with_the_pane_repo_dashboard(tmux, seeded):
    side = tmux.open_side_pane("main")

    def capture() -> str:
        return tmux("capture-pane", "-p", "-J", "-t", side)

    def screen() -> str | None:
        text = capture()
        return text if all(marker in text for marker in _markers()) else None

    h.wait_for(screen, "side pane dashboard", capture)
    assert tmux("display", "-p", "-t", side, "#{pane_current_path}").strip() == str(seeded)


def test_prefix_a_binding_is_a_popup_of_the_launcher_in_the_pane_directory(tmux):
    binding = tmux("list-keys", "-T", "prefix", "A")
    assert "display-popup" in binding
    assert '-d "#{pane_current_path}"' in binding
    assert "/dashboard" in binding
    scripts = tmux("show-environment", "-g", "SE_WORKFLOW_SCRIPTS").strip()
    assert scripts == f"SE_WORKFLOW_SCRIPTS={REPO_ROOT / 'scripts'}"


def test_prefix_a_popup_renders_the_pane_repo_dashboard_on_the_client(tmux):
    tmux.press("A")
    needles = _markers()
    text = tmux.screen_text(needles)
    missing = [needle for needle in needles if needle not in text]
    assert not missing, f"missing {missing} in client output: {text[-2000:]}"
    assert len(tmux("list-panes", "-t", "main", "-F", "#{pane_id}").split()) == 1


def test_prefix_a_popup_redraws_as_a_task_moves_from_ready_to_running_to_done(tmux, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    task = _work_item(cli, defs, EFFORT, "fx-moving")
    tmux.press("A")
    opening = tmux.screen_text(["ready", "title of fx-moving"])
    assert "ready" in opening and "title of fx-moving" in opening, opening[-2000:]

    task = h.transition(cli, "project:work-item", task, "in_progress")
    tmux.output = b""
    running = tmux.screen_text(["running"])
    assert "running" in running, running[-2000:]

    h.transition(cli, "project:work-item", task, "done")
    tmux.output = b""
    done = tmux.screen_text(["Done 1"])
    assert "Done 1" in done, done[-2000:]
    assert len(tmux("list-panes", "-t", "main", "-F", "#{pane_id}").split()) == 1


def test_prefix_a_popup_detail_screen_follows_a_task_through_its_lifecycle_and_esc_returns(tmux, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    task = _work_item(cli, defs, EFFORT, "fx-moving")
    criterion = h.create_generic_record(
        cli, defs, "project:acceptance", subject="fx-moving",
        extra_payload={"criterion": "unit tests pass", "method": "check", "verify_command": "pytest -q", "effort": EFFORT, "phase": f"{EFFORT}-phase"},
    )
    listed = cli("list", "--type", "project:work-item", "--subject", "fx-running")
    assert listed.returncode == 0, listed.stdout + listed.stderr
    h.transition(cli, "project:work-item", json.loads(listed.stdout)["records"][0], "done")
    tmux.press("A")
    assert "title of fx-moving" in tmux.screen_text(["title of fx-moving"])
    tmux.output = b""
    os.write(tmux.client_fd, b"\r")
    opening = tmux.screen_text(["Acceptance", "unit tests pass", "ready"])
    assert all(n in opening for n in ("Acceptance", "unit tests pass", "ready")), opening[-2000:]

    task = h.transition(cli, "project:work-item", task, "in_progress")
    tmux.output = b""
    running = tmux.screen_text(["running"])
    assert "running" in running, running[-2000:]

    h.create_generic_record(
        cli, defs, "project:execution-report", subject="fx-moving",
        extra_payload={"work_item": task["id"], "result": "ok", "verdict": "pass", "revision": "r1"},
    )
    h.create_generic_record(
        cli, defs, "project:check-run", subject="fx-moving",
        extra_payload={"criterion_id": criterion["id"], "method": "check", "result": "pass", "signed_by": "", "revision": "abc1234", "effort": EFFORT},
    )
    tmux.output = b""
    checked = tmux.screen_text(["check passed", "✓ unit tests pass"])
    assert all(n in checked for n in ("check passed", "✓ unit tests pass")), checked[-2000:]

    h.transition(cli, "project:work-item", task, "done")
    tmux.output = b""
    done = tmux.screen_text(["done"])
    assert "done" in done, done[-2000:]

    tmux.output = b""
    os.write(tmux.client_fd, b"\x1b")
    back = tmux.screen_text(["Running", "Ready", "Needs you"])
    assert all(n in back for n in ("Running", "Needs you")), back[-2000:]
    assert len(tmux("list-panes", "-t", "main", "-F", "#{pane_id}").split()) == 1


def test_prefix_a_popup_switches_status_tabs_filters_copies_a_slug_and_opens_a_commit_view(tmux, seeded, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    (seeded / "shipped.txt").write_text("shipped\n")
    assert git(seeded, "add", "shipped.txt").returncode == 0
    assert git(seeded, "commit", "-qm", "feat: ship the fx thing").returncode == 0
    sha = git(seeded, "rev-parse", "HEAD").stdout.strip()
    shipped = _work_item(cli, defs, EFFORT, "fx-shipped")
    h.create_generic_record(
        cli, defs, "project:execution-report", subject="fx-shipped",
        extra_payload={"work_item": shipped["id"], "result": "ok", "verdict": "pass", "revision": sha},
    )
    old = _work_item(cli, defs, EFFORT, "fx-old")
    h.transition(cli, "project:work-item", old, "in_progress", "done")
    tmux("set-option", "-s", "set-clipboard", "on")

    def full_screen(needles: list[str]) -> str:
        while select.select([tmux.client_fd], [], [], 0.5)[0]:
            os.read(tmux.client_fd, 65536)
        tmux.output = b""
        tmux("refresh-client")
        return tmux.screen_text([*needles, "Needs you"])

    tmux.press("A")
    assert "title of fx-shipped" in tmux.screen_text(["title of fx-shipped"])

    tmux.output = b""
    os.write(tmux.client_fd, b"5")
    done_tab = full_screen(["title of fx-old"])
    assert "title of fx-old" in done_tab and "title of fx-shipped" not in done_tab, done_tab[-2000:]

    tmux.output = b""
    os.write(tmux.client_fd, b"1")
    hidden = full_screen(["title of fx-shipped"])
    assert "title of fx-shipped" in hidden and "title of fx-old" not in hidden, hidden[-2000:]

    tmux.output = b""
    os.write(tmux.client_fd, b"/")
    assert "filter tasks" in tmux.screen_text(["filter tasks"])
    os.write(tmux.client_fd, b"shipped\r")
    filtered = full_screen(["/shipped", "title of fx-shipped"])
    assert "/shipped" in filtered and "title of fx-shipped" in filtered, filtered[-2000:]
    assert "title of fx-ready" not in filtered and "title of fx-running" not in filtered, filtered[-2000:]

    tmux.output = b""
    os.write(tmux.client_fd, b"c")
    assert "Copied fx-shipped" in tmux.screen_text(["Copied fx-shipped"])

    tmux.output = b""
    os.write(tmux.client_fd, b"\r")
    detail = tmux.screen_text(["Timeline"])
    assert "Timeline" in detail, detail[-2000:]
    tmux.output = b""
    os.write(tmux.client_fd, b"g")
    commit = tmux.screen_text([sha[:7], "feat: ship the fx thing", "shipped.txt"])
    assert all(n in commit for n in (sha[:7], "feat: ship the fx thing", "shipped.txt")), commit[-2000:]

    tmux.output = b""
    os.write(tmux.client_fd, b"\x1b")
    assert "Timeline" in tmux.screen_text(["Timeline"])
    tmux.output = b""
    os.write(tmux.client_fd, b"\x1b")
    back = full_screen(["/shipped", "title of fx-shipped"])
    assert "/shipped" in back and "title of fx-shipped" in back, back[-2000:]
    assert len(tmux("list-panes", "-t", "main", "-F", "#{pane_id}").split()) == 1

    os.write(tmux.client_fd, b"q")
    while select.select([tmux.client_fd], [], [], 1.0)[0]:
        os.read(tmux.client_fd, 65536)
    side = tmux.open_side_pane("main")

    def side_screen(needle: str):
        return lambda: needle in tmux("capture-pane", "-p", "-J", "-t", side)

    h.wait_for(side_screen("title of fx-shipped"), "side pane dashboard")
    tmux("send-keys", "-t", side, "/")
    h.wait_for(side_screen("filter tasks"), "side pane filter box")
    tmux("send-keys", "-t", side, "shipped", "Enter")
    h.wait_for(lambda: "title of fx-ready" not in tmux("capture-pane", "-p", "-J", "-t", side), "side pane filtered")
    tmux("send-keys", "-t", side, "c")
    copied = h.wait_for(lambda: tmux("show-buffer", check=False), "tmux buffer from OSC 52")
    assert copied == "fx-shipped", copied


def test_prefix_a_popup_keys_only_walks_status_tabs_phase_sections_phase_detail_and_the_second_task(tmux, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    h.create_generic_record(
        cli, defs, "project:phase", subject="px-later",
        extra_payload={"title": "Phase px-later", "ordinal": 1, "effort": EFFORT},
    )
    for name in ("px-first", "px-second"):
        payload = {"title": f"title of {name}", "phase": "px-later", "kind": "deliver", "assignee": "", "effort": EFFORT}
        created = cli("create", "--type", "project:work-item", "--subject", name, "--payload", json.dumps(payload),
                      "--body", h.generic_body(defs["project:work-item"]))
        assert created.returncode == 0, created.stdout + created.stderr

    def redraw() -> None:
        while select.select([tmux.client_fd], [], [], 0.3)[0]:
            os.read(tmux.client_fd, 65536)
        tmux.output = b""
        tmux("refresh-client")

    def press(keys: bytes, *needles: str, absent: tuple[str, ...] = ()) -> str:
        os.write(tmux.client_fd, keys)
        end = time.monotonic() + h.DEADLINE
        while True:
            redraw()
            text = tmux.screen_text(list(needles))
            if all(n in text for n in needles) and not any(a in text for a in absent):
                return text
            assert time.monotonic() < end, f"{keys!r} needs {needles} without {absent}: {text[-2000:]}"

    tmux.press("A")
    assert "Phase px-later" in tmux.screen_text(["Phase px-later"])

    press(b"1", "Phase px-later", "title of fx-running", "title of fx-ready", absent=("title of px-first", "title of px-second"))
    press(b"2", "title of fx-running", absent=("title of fx-ready", "px-later 0/2"))
    press(b"\x1b[C", "title of fx-ready", absent=("title of fx-running",))
    press(b"\x1b[D", "title of fx-running", absent=("title of fx-ready",))
    press(b"1", "Phase px-later", "title of fx-ready")

    for _ in range(3):
        press(b"\x1b[A", "px-later 0/2")
    press(b"\r", "Phase px-later", "title of px-first", "title of px-second")

    press(b"p", "planned · 0/2 tasks", "title of px-first", "title of px-second", absent=("px-later 0/2",))
    press(b"\x1b", "▾ ○ Phase px-later 0/2", "title of px-first", "title of px-second", absent=("planned · 0/2 tasks",))

    press(b"j", "px-later 0/2")
    press(b"j", "px-later 0/2")
    press(b"\r", "px-second tmuxfx", "title of px-second", "Description", absent=("px-later 0/2", "title of px-first", "title of fx-ready"))
    press(b"\x1b", "▾ ○ Phase px-later 0/2", "title of px-first", "title of px-second", absent=("Description",))
    assert len(tmux("list-panes", "-t", "main", "-F", "#{pane_id}").split()) == 1


def test_prefix_a_popup_regains_table_focus_after_an_empty_tab_and_narrows_its_columns_on_resize(tmux):
    def press(keys: bytes, *needles: str, absent: tuple[str, ...] = ()) -> str:
        os.write(tmux.client_fd, keys)
        end = time.monotonic() + h.DEADLINE
        while True:
            while select.select([tmux.client_fd], [], [], 0.3)[0]:
                os.read(tmux.client_fd, 65536)
            tmux.output = b""
            tmux("refresh-client")
            text = tmux.screen_text(list(needles))
            if all(n in text for n in needles) and not any(a in text for a in absent):
                return text
            assert time.monotonic() < end, f"{keys!r} needs {needles} without {absent}: {text[-2000:]}"

    tmux.press("A")
    assert "assignee" in tmux.screen_text(["title of fx-ready", "assignee"])

    press(b"4", "No tasks match", absent=("title of fx-running", "title of fx-ready"))
    press(b"1", "title of fx-running", "title of fx-ready", absent=("No tasks match",))
    press(b"\x1b[B", "title of fx-ready")
    press(b"\r", "fx-ready tmuxfx", "Description", absent=("title of fx-running",))
    press(b"\x1b", "title of fx-running", "assignee", absent=("Description",))

    fcntl.ioctl(tmux.client_fd, termios.TIOCSWINSZ, struct.pack("HHHH", tmux.rows, 80, 0, 0))
    narrow = press(b"", "title of fx-running", "title of fx-ready", "wave", absent=("assignee",))
    assert "No live efforts" not in narrow, narrow[-2000:]
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
