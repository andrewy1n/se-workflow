"""Drive se-workflow.tmux in an isolated tmux server with a client attached in a pty."""

from __future__ import annotations

import fcntl
import json
import os
import select
import shlex
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

STATUS = REPO_ROOT / "dashboard" / "bin" / "dashboard-status"
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


def _refreshed(server, *needles: str) -> str:
    """Popup text after a client redraw. A live write omits cells that did not change."""
    end = time.monotonic() + h.DEADLINE
    last = ""
    while True:
        server.output = b""
        server("refresh-client")
        if select.select([server.client_fd], [], [], 0.5)[0]:
            try:
                server.output += os.read(server.client_fd, 65536)
            except OSError:
                pass
        last = h.plain_terminal(server.output)
        if all(needle in last for needle in needles) or time.monotonic() > end:
            return last
        time.sleep(0.3)


def test_prefix_s_opens_a_side_pane_with_the_pane_repo_dashboard_and_a_stepper_that_never_splits_a_glyph_from_its_label(
    tmux, seeded, cli, resolved_contract,
):
    defs = h.record_defs_by_id(resolved_contract)
    titles = ("Gather the inputs", "Shape the store", "Draw the dashboard", "Wire every tmux binding into the popup and the side pane")
    for ordinal, title in enumerate(titles, 1):
        phase = h.create_generic_record(
            cli, defs, "project:phase", subject=f"sx-{ordinal}", extra_payload={"title": title, "ordinal": ordinal, "effort": EFFORT},
        )
        h.transition(cli, "project:phase", phase, *{1: ("in_progress", "done"), 2: ("in_progress",)}.get(ordinal, ()))
    side = tmux.open_side_pane("main")

    def capture() -> str:
        return tmux("capture-pane", "-p", "-J", "-t", side)

    def screen() -> str | None:
        text = capture()
        markers = [marker for marker in _markers() if not marker.startswith("title of ")]
        return text if all(marker in text for marker in markers) else None

    h.wait_for(screen, "side pane dashboard", capture)
    assert tmux("display", "-p", "-t", side, "#{pane_current_path}").strip() == str(seeded)
    assert 40 <= int(tmux("display", "-p", "-t", side, "#{pane_width}")) <= 60
    def collapsed() -> str | None:
        text = capture()
        if "1 done" in text and "● Shape the store" in text and "○ Draw the dashboard" in text:
            return text
        return None

    lines = [line.strip() for line in h.wait_for(collapsed, "selector", capture).splitlines()]
    goal = lines.index(f"ship {EFFORT}")
    progress = next(i for i, line in enumerate(lines) if "effort" in line)
    stepper = [line for line in lines[goal + 1:progress] if line]
    joined = " ".join(stepper)
    assert "1 done" in joined and "● Shape the store" in joined and "○ Draw the dashboard" in joined
    assert "Wire every" not in joined and "✓" not in joined, stepper


def test_prefix_a_binding_is_a_popup_of_the_launcher_in_the_pane_directory(tmux):
    binding = tmux("list-keys", "-T", "prefix", "A")
    assert "display-popup" in binding
    assert '-d "#{pane_current_path}"' in binding
    assert "/dashboard" in binding


def test_prefix_a_popup_renders_the_pane_repo_dashboard_with_waits_on_running_time_and_failed_activity(
    tmux, seeded, cli, resolved_contract,
):
    defs = h.record_defs_by_id(resolved_contract)
    listed = cli("list", "--type", "project:work-item", "--subject", "fx-running")
    assert listed.returncode == 0, listed.stdout + listed.stderr
    running = json.loads(listed.stdout)["records"][0]
    _work_item(cli, defs, EFFORT, "fx-waiting", f"depends_on:{running['id']}")
    h.run_cli_48h_ago(
        seeded, "create", "--type", "project:assignment", "--subject", "fx-running",
        "--payload", json.dumps({"work_item": running["id"], "executor": "sub-fx", "effort": EFFORT}),
        "--body", h.generic_body(defs["project:assignment"]),
    )
    h.create_generic_record(
        cli, defs, "project:check-run", subject="fx-broken",
        extra_payload={"method": "check", "result": "fail", "signed_by": "", "revision": "abc1234", "effort": EFFORT},
    )
    tmux.press("A")
    needles = [*_markers(), "running 48h", "waits on fx-running", "✗ fx-broken check failed", "status task assignee"]
    text = tmux.screen_text(needles)
    missing = [needle for needle in needles if needle not in text]
    assert not missing, f"missing {missing} in client output: {text[-2000:]}"
    assert "status task assignee" in text and "status task wave" not in text, text[-2000:]
    assert "running 48h" in text and "title of fx-running" in text, text[-2000:]
    assert "quiet" in text, text[-2000:]
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
    done = _refreshed(tmux, "Done (1)")
    assert "Done (1)" in done, done[-2000:]
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
    checked = _refreshed(tmux, "check passed", "✓ unit tests pass")
    assert all(n in checked for n in ("check passed", "✓ unit tests pass")), checked[-2000:]

    h.transition(cli, "project:work-item", task, "done")
    done = _refreshed(tmux, "done")
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

    h.wait_for(side_screen(" · subagent"), "side pane dashboard")
    tmux("send-keys", "-t", side, "/")
    h.wait_for(side_screen("filter tasks"), "side pane filter box")
    tmux("send-keys", "-t", side, "shipped", "Enter")
    h.wait_for(side_screen("/shipped"), "side pane filtered")
    h.wait_for(lambda: "title of fx-ready" not in tmux("capture-pane", "-p", "-J", "-t", side), "side pane hides ready")
    tmux("send-keys", "-t", side, "c")
    copied = h.wait_for(lambda: tmux("show-buffer", check=False), "tmux buffer from OSC 52")
    assert copied == "fx-shipped", copied


def test_prefix_a_popup_keys_only_walks_tabs_phase_sections_phase_detail_and_detail_links_back_with_esc(tmux, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    h.create_generic_record(
        cli, defs, "project:phase", subject="px-later",
        extra_payload={"title": "Phase px-later", "ordinal": 1, "effort": EFFORT},
    )
    rels: list[str] = []
    for name in ("px-first", "px-second"):
        payload = {"title": f"title of {name}", "phase": "px-later", "kind": "deliver", "assignee": "", "effort": EFFORT}
        args = ["create", "--type", "project:work-item", "--subject", name, "--payload", json.dumps(payload)]
        for rel in rels:
            args.extend(["--rel", rel])
        created = cli(*args, "--body", h.generic_body(defs["project:work-item"]))
        assert created.returncode == 0, created.stdout + created.stderr
        rels = [f"depends_on:{json.loads(created.stdout)['record']['id']}"]

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
    assert "Phase px-later" in tmux.screen_text(["Phase px-later", "title of px-first"])
    press(b"]", "title of fx-running", absent=("title of px-first",))
    assert "Phase px-later" in tmux.screen_text(["Phase px-later"])

    press(b"1", "Phase px-later", "title of fx-running", "title of fx-ready", absent=("title of px-first", "title of px-second"))
    press(b"2", "title of fx-running", absent=("title of fx-ready", "px-later 0/2"))
    press(b"\x1b[C", "title of fx-ready", absent=("title of fx-running",))
    press(b"\x1b[D", "title of fx-running", absent=("title of fx-ready",))
    press(b"1", "Phase px-later", "title of fx-ready")

    for _ in range(3):
        press(b"\x1b[A", "px-later 0/2")
    press(b"\r", "Phase px-later", "title of px-first", "title of px-second")

    press(b"p", "planned · 0/2 tasks", absent=("px-later 0/2",))
    press(b"t", "title of px-first", "title of px-second")
    press(b"\x1b", "▾ ○ Phase px-later 0/2", "title of px-first", "title of px-second", absent=("planned · 0/2 tasks",))

    press(b"j", "px-later 0/2")
    press(b"j", "px-later 0/2")
    second = press(b"\r", "px-second tmuxfx", "title of px-second", "Depends on:", "Phase: px-later",
                   absent=("px-later 0/2", "title of px-first", "title of fx-ready"))

    def pick(text: str, entry: str, *entries: str) -> bytes:
        rows = sorted((entry, *entries), key=text.index)
        return b"j" * rows.index(entry)

    def focus_links() -> None:
        press(b"l")
        time.sleep(0.5)

    focus_links()
    press(pick(second, "Depends on:", "Phase: px-later"))
    first = press(b"\r", "px-first tmuxfx", "title of px-first", "Blocks:", "Phase: px-later",
                  absent=("title of px-second", "Depends on:"))
    focus_links()
    press(pick(first, "Phase: px-later", "Blocks:"))
    press(b"\r", "planned · 0/2 tasks", absent=("Loading…", "Blocks:", "Description"))
    phase = press(b"t", "title of px-first", "title of px-second")
    time.sleep(0.5)
    press(pick(phase, "title of px-second", "title of px-first"))
    press(b"\r", "px-second tmuxfx", "Depends on:", "Description", absent=("planned · 0/2 tasks", "Blocks:"))

    press(b"\x1b", "title of px-first", "title of px-second", absent=("Description",))
    press(b"\x1b", "px-first tmuxfx", "Blocks:", absent=("title of px-second",))
    press(b"\x1b", "px-second tmuxfx", "Depends on:", absent=("Blocks:",))
    press(b"\x1b", "▾ ○ Phase px-later 0/2", "title of px-first", "title of px-second", absent=("Description",))
    assert len(tmux("list-panes", "-t", "main", "-F", "#{pane_id}").split()) == 1


def test_prefix_a_popup_walks_six_tabs_counts_needs_you_reads_unsigned_checks_regains_focus_and_narrows_on_resize(
    tmux, cli, resolved_contract,
):
    defs = h.record_defs_by_id(resolved_contract)
    criterion = h.create_generic_record(
        cli, defs, "project:acceptance", subject="fx-ready",
        extra_payload={"criterion": "pages render on mobile", "method": "manual", "verify_command": "", "effort": EFFORT, "phase": f"{EFFORT}-phase"},
    )
    h.create_generic_record(
        cli, defs, "project:check-run", subject="fx-check",
        extra_payload={"criterion_id": criterion["id"], "method": "manual", "result": "pass", "signed_by": "", "revision": "abc1234", "effort": EFFORT},
    )

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

    tabs = ("Active (2)", "Running (1)", "Ready (1)", "Waiting (0)", "Done (0)", "All (2)")
    opening = press(b"", *tabs, "Needs you 2", "Sign off pages render on mobile pass fx-ready")
    assert " ".join(tabs) in opening, opening[-2000:]
    assert opening.count("Needs you") == 1, opening[-2000:]
    assert "rec-" not in opening, opening[-2000:]

    press(b"2", "title of fx-running", absent=("title of fx-ready",))
    press(b"3", "title of fx-ready", absent=("title of fx-running",))
    press(b"5", "No tasks match", absent=("title of fx-running", "title of fx-ready"))
    press(b"6", "title of fx-running", "title of fx-ready", absent=("No tasks match",))
    press(b"4", "No tasks match", absent=("title of fx-running", "title of fx-ready"))
    press(b"1", "title of fx-running", "title of fx-ready", absent=("No tasks match",))
    press(b"\x1b[B", "title of fx-ready")
    press(b"\r", "fx-ready tmuxfx", "Description", absent=("title of fx-running",))
    press(b"\x1b", "title of fx-running", "assignee", absent=("Description",))

    # tmux 3.2 closes a popup when the client tty changes size, so reopen at the new size.
    os.write(tmux.client_fd, b"q")
    time.sleep(0.4)
    fcntl.ioctl(tmux.client_fd, termios.TIOCSWINSZ, struct.pack("HHHH", tmux.rows, 80, 0, 0))
    time.sleep(0.2)
    tmux.press("A")
    narrow = tmux.screen_text(["title of fx-running", "title of fx-ready"])
    assert "assignee" not in narrow, narrow[-2000:]
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


def test_status_right_gates_needs_segment_shows_flag_count_when_on(tmux, seeded):
    status = tmux("show-option", "-gv", "status-right")
    assert "dashboard-status" in status and "--tmux" in status
    assert "#{pane_current_path}" in status
    env = dict(
        os.environ,
        HOME=str(tmux.env["HOME"]),
        ADAPTIVE_ARTIFACTS_BIN=str(AA_ROOT / "bin" / "adaptive-artifacts"),
    )
    tmux("set-environment", "-g", "ADAPTIVE_ARTIFACTS_BIN", str(AA_ROOT / "bin" / "adaptive-artifacts"))
    direct = subprocess.run(
        [str(STATUS), "--tmux", str(seeded)], capture_output=True, text=True, env=env, timeout=30, input="",
    )
    assert direct.stdout == "⚑ 1\n", direct.stderr

    # #{T:status-right} from a control client stays "not ready" here; the attached
    # pty draws the real status line, so read the flag from client output.
    def on_client() -> str | None:
        tmux.output = b""
        tmux("refresh-client")
        if select.select([tmux.client_fd], [], [], 1.0)[0]:
            try:
                tmux.output += os.read(tmux.client_fd, 65536)
            except OSError:
                pass
        text = h.plain_terminal(tmux.output)
        return text if "⚑" in text else None

    rendered = h.wait_for(on_client, "client status-right needs flag", deadline=15.0)
    assert "⚑ 1" in rendered, rendered


def test_status_right_gates_needs_segment_absent_when_option_off(home, seeded, tmp_path):
    server = h.Tmux(home, tmp_path)
    try:
        server("new-session", "-d", "-s", "main", "-x", "120", "-y", "40", "-c", str(seeded))
        server("set-option", "-g", "@dashboard-status-right", "off")
        server("run-shell", shlex.quote(str(h.TMUX_ENTRY)))
        status = server("show-option", "-gv", "status-right", check=False)
        assert "dashboard-status" not in status
        rendered = server("display-message", "-p", "#{T:status-right}", check=False)
        assert "⚑" not in rendered
    finally:
        server.kill()


def test_prefix_a_popup_walks_needs_you_into_task_and_question_details_and_lists_a_finished_effort_last(
    tmux, cli, resolved_contract,
):
    defs = h.record_defs_by_id(resolved_contract)
    h.create_generic_record(
        cli, defs, "project:finding", subject="fx-ready",
        extra_payload={"claim": "pick the fx-ready rollout", "needs": "human", "effort": EFFORT},
    )
    h.create_generic_record(
        cli, defs, "project:continuity-question", subject=EFFORT,
        extra_payload={"blocking": False, "scope": "which store should the dashboard read when the home store and the repo store disagree about every open task quokka"},
    )
    _goal(cli, defs, "donefx")
    phase = h.create_generic_record(
        cli, defs, "project:phase", subject="donefx-phase", extra_payload={"title": "Phase donefx", "ordinal": 1, "effort": "donefx"},
    )
    h.transition(cli, "project:phase", phase, "in_progress", "done")
    for name in ("dx-first", "dx-second"):
        h.transition(cli, "project:work-item", _work_item(cli, defs, "donefx", name), "in_progress", "done")

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
    assert "Needs you 3" in tmux.screen_text(["Needs you 3"])

    opening = press(b"", "Needs you 3", "pick the fx-ready rollout", "which store should", "+1 finished", absent=("quokka", "donefx"))

    def focus_needs() -> None:
        press(b"n", "Needs you 3")
        time.sleep(0.5)

    rows = sorted(("a human must decide", "pick the fx-ready rollout", "which store should"), key=opening.index)
    linked, question = rows.index("pick the fx-ready rollout"), rows.index("which store should")
    focus_needs()
    press(b"j" * linked)
    press(b"\r", "fx-ready tmuxfx", "Description", absent=("Needs you 3",))
    press(b"\x1b", "Needs you 3", absent=("Description",))
    focus_needs()
    press((b"k" if question < linked else b"j") * abs(question - linked))
    press(b"\r", "question", "project:continuity-question", "quokka", absent=("Needs you 3",))
    press(b"\x1b", "Needs you 3", absent=("quokka",))
    press(b"\x1b", "Needs you 3")

    press(b"f", "donefx")
    finished = press(b"\t", "All 2 tasks done", absent=("title of fx-running",))
    assert finished.index(f"⚠ {EFFORT}") < finished.index("donefx"), finished[-2000:]
    assert len(tmux("list-panes", "-t", "main", "-F", "#{pane_id}").split()) == 1
