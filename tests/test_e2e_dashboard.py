"""Adopt a scratch repo through the CLI and follow one effort in the live prefix+S side pane and the status segment."""

from __future__ import annotations

import json
import os
import re
import select
import shutil
import subprocess
import time
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


EFFORT_EV = "ev"
PHASE_EV = f"{EFFORT_EV}-phase"
REQ_TEXT = "popup requirement holds"


def _sections(record_def: dict, fills: dict[str, str]) -> str:
    required = record_def.get("required_sections") or []
    return "\n\n".join(f"## {name}\n\n{fills.get(name, 'placeholder.')}" for name in required)


def _create(cli, defs, record_type: str, subject: str, payload: dict, body: str | None = None) -> dict:
    args = ["create", "--type", record_type, "--subject", subject, "--payload", json.dumps(payload)]
    if body is None:
        body = h.generic_body(defs[record_type])
    if body:
        args.extend(["--body", body])
    result = cli(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def _assessment(cli, defs, requirement: str, **fields) -> dict:
    payload = {
        "requirement": requirement, "phase": PHASE_EV, "effort": EFFORT_EV, "missing": "",
        "confidence": "high", "status": "failed", "next": "execute", "level": "implementation",
    }
    payload.update(fields)
    if payload.get("status") == "verified":
        payload.pop("level", None)
    return _create(cli, defs, "project:assessment", f"{PHASE_EV}-{requirement}", payload)


def _supersede_assessment(cli, defs, record: dict, **fields) -> dict:
    payload = {**record["payload"], **fields}
    if payload.get("status") == "verified":
        payload.pop("level", None)
    result = cli(
        "supersede", "--type", "project:assessment", "--id", record["id"],
        "--expected-revision", record["revision"], "--payload", json.dumps(payload),
        "--body", h.generic_body(defs["project:assessment"]),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


@pytest.mark.tmux
def test_prefix_a_popup_evidence_view_shows_unassessed_then_a_design_route_then_verified_release(
    home, store, cli, resolved_contract, tmp_path,
):
    defs = h.record_defs_by_id(resolved_contract)
    _goal(cli, defs, EFFORT_EV)
    phase = h.create_generic_record(
        cli, defs, "project:phase", subject=PHASE_EV,
        extra_payload={"title": "Evidence phase", "ordinal": 1, "effort": EFFORT_EV},
    )
    h.transition(cli, "project:phase", phase, "in_progress")
    _create(cli, defs, "project:specification", PHASE_EV, {
        "weight": "light", "phase": PHASE_EV, "effort": EFFORT_EV, "requirements": "R1, R2",
    }, _sections(defs["project:specification"], {
        "Requirements": f"R1: {REQ_TEXT}\nR2: the second requirement holds",
    }))
    _create(cli, defs, "project:work-item", "ev-task", {
        "title": "title of ev-task", "phase": PHASE_EV, "kind": "deliver", "assignee": "",
        "effort": EFFORT_EV, "requirements": "R1",
    })

    tmux = h.Tmux(home, tmp_path, cols=200, rows=50)
    try:
        tmux.start("main", store)
        tmux.attach("main")
        h.wait_for(
            lambda: tmux("display", "-p", "-t", "main", "#{pane_current_path}").strip() == str(store),
            "shell cwd",
        )

        def shown(*needles: str, absent: tuple[str, ...] = ()) -> str:
            tmux.screen_text(list(needles))
            while select.select([tmux.client_fd], [], [], 0.2)[0]:
                os.read(tmux.client_fd, 65536)
            tmux.output = b""
            tmux("refresh-client")
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if select.select([tmux.client_fd], [], [], 0.2)[0]:
                    try:
                        tmux.output += os.read(tmux.client_fd, 65536)
                    except OSError:
                        break
                elif tmux.output:
                    break
            text = h.plain_terminal(tmux.output)
            missing = [needle for needle in needles if needle not in text]
            extra = [item for item in absent if item in text]
            assert not missing and not extra, f"missing {missing} extra {extra} in {text[-2500:]}"
            return text

        def press(keys: bytes, *needles: str, absent: tuple[str, ...] = ()) -> str:
            tmux.output = b""
            os.write(tmux.client_fd, keys)
            return shown(*needles, absent=absent)

        tmux.press("A")
        shown("Evidence phase", "· design", absent=("Needs you", "Release ready", "unassessed"))
        press(b"]", "R 0/2 verified", absent=("unassessed",))
        # Selected-phase stepper keeps R n/m verified + glyphs (evidence-matrix R7).
        press(b"[", "· design", "R 0/2 verified")
        press(b"e", "unassessed", "R1", "R2", absent=("Needs you", "Release ready"))
        press(b"\x1b", "· design", absent=("unassessed",))

        tmux.output = b""
        routed = _assessment(
            cli, defs, "R1", status="failed", level="design", next="design", confidence="high",
        )
        shown("Needs you", "R1 failed design", absent=("Release ready", "R 2/2 verified"))

        tmux.output = b""
        _supersede_assessment(
            cli, defs, routed, status="verified", next="release", confidence="high",
        )
        _assessment(cli, defs, "R2", status="verified", next="release", confidence="high")
        _create(cli, defs, "project:release", PHASE_EV, {"state": "ready", "phase": PHASE_EV, "effort": EFFORT_EV})
        shown(" · release", "Release ready", absent=("Needs you", "unassessed"))
        press(b"]", "R 2/2 verified")
        press(b"[", " · release")

        tmux.output = b""
        os.write(tmux.client_fd, b"j\r")
        shown("Requirement: R1", "Phase: ev-phase", absent=("R 2/2 verified",))
        os.write(tmux.client_fd, b"l")
        time.sleep(0.5)
        press(b"j\r", REQ_TEXT, "verified", absent=("Requirement: R1", "R 2/2 verified"))
        assert len(tmux("list-panes", "-t", "main", "-F", "#{pane_id}").split()) == 1
    finally:
        tmux.kill()
