"""Drive scripts/tmux-dashboard.conf in an isolated tmux server with a client attached in a pty."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import helpers as h
from conftest import AA_ROOT, REPO_ROOT
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
    done = tmux.screen_text(["done"])
    assert "done" in done, done[-2000:]
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


def test_status_segment_counts_match_the_seeded_store(home, seeded):
    env = dict(os.environ, HOME=str(home), ADAPTIVE_ARTIFACTS_BIN=str(AA_ROOT / "bin" / "adaptive-artifacts"))
    expected = f"{EFFORT} · 1 running · 1 ready · 1 needs you\n"
    by_arg = subprocess.run([str(STATUS), str(seeded)], capture_output=True, text=True, env=env, timeout=30, input="")
    by_json = subprocess.run(
        [str(STATUS)], capture_output=True, text=True, env=env, timeout=30,
        input=json.dumps({"workspace": {"current_dir": str(seeded)}}), cwd="/",
    )
    assert (by_arg.stdout, by_json.stdout) == (expected, expected), by_arg.stderr + by_json.stderr
