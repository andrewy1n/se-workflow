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


def _headings(store: Path) -> list[str]:
    return ["Project Dashboard", f"## {EFFORT}", "### Running", "### Ready", "### Needs Human", str(store / ".artifacts")]


def test_prefix_s_opens_a_side_pane_with_the_pane_repo_dashboard(tmux, seeded):
    side = tmux.open_side_pane("main")

    def capture() -> str:
        return tmux("capture-pane", "-p", "-t", side)

    def screen() -> str | None:
        text = capture()
        return text if all(heading in text for heading in _headings(seeded)) else None

    text = h.wait_for(screen, "side pane dashboard", capture)
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
