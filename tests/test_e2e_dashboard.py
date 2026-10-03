"""Adopt a scratch repo through the CLI and follow one effort in the live prefix+S side pane and the status segment."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import helpers as h
from conftest import AA_ROOT, CONTRACT_PATH, REPO_ROOT, make_git_repo, run_cli
from test_dashboard_status import _goal, _work_item

pytestmark = pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux is not installed")

STATUS = REPO_ROOT / "dashboard" / "bin" / "dashboard-status"
EFFORT = "e2e"
PHASE = f"{EFFORT}-phase"
REDRAW = 5.0
TASK_ROW = re.compile(r"[▶●◌✓✕] (running|ready|waiting|done|withdrawn)\s+title of (\S+)")


def _task_map(screen: str) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for status, subject in TASK_ROW.findall(screen):
        rows.setdefault(status, []).append(subject)
    return {status: sorted(subjects) for status, subjects in rows.items()}


@pytest.fixture()
def home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    return home


@pytest.fixture()
def adopted(home):
    repo = make_git_repo()
    try:
        (repo / ".artifacts").mkdir()
        shutil.copy(CONTRACT_PATH, repo / ".artifacts" / "project-design.json")
        store = home / ".artifacts" / repo.name
        for args in (["resolve"], ["--store", str(store), "init"]):
            result = run_cli(*args, root=repo)
            assert result.returncode == 0, result.stdout + result.stderr
        assert (store / "meta.json").is_file() and not (repo / ".artifacts" / "meta.json").exists()
        yield repo, store
    finally:
        shutil.rmtree(repo, ignore_errors=True)


@pytest.fixture()
def side_pane(home, adopted, tmp_path):
    repo, _ = adopted
    server = h.Tmux(home, tmp_path, cols=520, rows=50)
    try:
        server.start("main", repo)
        server.attach("main")
        side = server.open_side_pane("main")
        width = int(server("display", "-p", "-t", side, "#{pane_width}"))
        assert width >= 200, width
        yield lambda: server("capture-pane", "-p", "-J", "-t", side)
    finally:
        server.kill()


def _status(home: Path, repo: Path) -> str:
    env = dict(os.environ, HOME=str(home), ADAPTIVE_ARTIFACTS_BIN=str(AA_ROOT / "bin" / "adaptive-artifacts"))
    result = subprocess.run([str(STATUS), str(repo)], capture_output=True, text=True, env=env, timeout=30, input="")
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_e2e_side_pane_and_status_follow_every_lifecycle_step(home, adopted, side_pane):
    repo, store = adopted

    def cli(*args: str) -> subprocess.CompletedProcess:
        return run_cli("--store", str(store), *args, root=repo)

    defs = h.record_defs_by_id(json.loads((repo / ".artifacts" / "resolved-contract.json").read_text()))

    def expect(status: str, needs: bool = False, **tasks: list[str]) -> None:
        finished = tasks.pop("done", [])
        expected = {name: sorted(subjects) for name, subjects in tasks.items()}
        tab = f"⚠ {EFFORT}" if needs else EFFORT
        last: dict = {}

        def redrawn():
            screen = side_pane()
            last["map"] = _task_map(screen)
            return last["map"] == expected and f"Done ({len(finished)})" in screen and f"ship {EFFORT}" in screen and tab in screen and (needs or "⚠" not in screen)

        h.wait_for(redrawn, f"side pane tasks {expected}", lambda: f"{last.get('map')}\n{side_pane()}", REDRAW)
        want = f"{EFFORT} · {status}\n"
        h.wait_for(lambda: _status(home, repo) == want, f"status {want!r}", lambda: repr(_status(home, repo)), REDRAW)

    _goal(cli, defs, EFFORT)
    phase = h.create_generic_record(
        cli, defs, "project:phase", subject=PHASE,
        extra_payload={"title": "first phase", "ordinal": 1, "effort": EFFORT},
    )
    h.transition(cli, "project:phase", phase, "in_progress")
    a = _work_item(cli, defs, EFFORT, "a")
    b = _work_item(cli, defs, EFFORT, "b", f"depends_on:{a['id']}")
    _work_item(cli, defs, EFFORT, "c", f"depends_on:{b['id']}")
    expect("1 ready", ready=["a"], waiting=["b", "c"])

    a = h.transition(cli, "project:work-item", a, "in_progress")
    expect("1 running", running=["a"], waiting=["b", "c"])

    h.transition(cli, "project:work-item", a, "done")
    expect("1 ready", ready=["b"], waiting=["c"], done=["a"])

    question = h.create_generic_record(
        cli, defs, "project:continuity-question", subject=EFFORT,
        extra_payload={"blocking": True, "scope": f"{EFFORT}-scope"},
    )
    expect("1 ready · 1 needs you", needs=True, ready=["b"], waiting=["c"], done=["a"])

    h.transition(cli, "project:continuity-question", question, "answered")
    expect("1 ready", ready=["b"], waiting=["c"], done=["a"])

    b = h.transition(cli, "project:work-item", b, "in_progress")
    expect("1 running", running=["b"], waiting=["c"], done=["a"])

    h.transition(cli, "project:work-item", b, "done")
    expect("1 ready", ready=["c"], done=["a", "b"])
