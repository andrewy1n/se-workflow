"""Tests for dashboard/bin/dashboard-status: the one-line status summary per live effort."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import helpers as h
from conftest import AA_ROOT, REPO_ROOT, make_git_repo

sys.path.insert(0, str(REPO_ROOT))
from dashboard import artifact_store  # noqa: E402
from dashboard import model as dashboard_model  # noqa: E402

SCRIPT = REPO_ROOT / "dashboard" / "bin" / "dashboard-status"


def _run(home: Path, *args: str, stdin: str | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, HOME=str(home), ADAPTIVE_ARTIFACTS_BIN=str(AA_ROOT / "bin" / "adaptive-artifacts"))
    return subprocess.run(
        [str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=30,
        input=stdin if stdin is not None else "", cwd=str(cwd or REPO_ROOT),
    )


@pytest.fixture()
def home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    return home


def _goal(cli, defs, effort: str) -> None:
    h.create_generic_record(
        cli, defs, "project:active-goal", subject=effort,
        extra_payload={"goal": f"ship {effort}", "kind": "deliver"},
    )


def _work_item(cli, defs, effort: str, subject: str, *rels: str) -> dict:
    payload = {"title": f"title of {subject}", "phase": f"{effort}-phase", "kind": "deliver", "assignee": "", "effort": effort}
    args = ["create", "--type", "project:work-item", "--subject", subject, "--payload", json.dumps(payload)]
    for rel in rels:
        args.extend(["--rel", rel])
    result = cli(*args, "--body", h.generic_body(defs["project:work-item"]))
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


@pytest.fixture()
def seeded(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _goal(cli, defs, "seg")
    running = _work_item(cli, defs, "seg", "seg-running")
    h.transition(cli, "project:work-item", running, "in_progress")
    _work_item(cli, defs, "seg", "seg-ready-1")
    _work_item(cli, defs, "seg", "seg-ready-2")
    _work_item(cli, defs, "seg", "seg-waiting", f"depends_on:{running['id']}")
    h.create_generic_record(
        cli, defs, "project:continuity-question", subject="seg",
        extra_payload={"blocking": True, "scope": "seg-scope"},
    )
    h.create_generic_record(
        cli, defs, "project:finding", subject="seg-finding",
        extra_payload={"claim": "a human must decide", "needs": "human", "effort": "seg"},
    )
    h.create_generic_record(
        cli, defs, "project:check-run", subject="seg-check",
        extra_payload={"method": "manual", "signed_by": "", "result": "pass", "effort": "seg"},
    )
    return store


def test_prints_counts_for_a_seeded_store_within_one_second(home, seeded):
    started = time.monotonic()
    result = _run(home, str(seeded))
    elapsed = time.monotonic() - started
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "seg · 1 running · 2 ready · 3 needs you\n"
    assert elapsed < 1.0, elapsed


def test_reads_workspace_current_dir_from_status_json(home, seeded):
    status = json.dumps({"cwd": "/", "workspace": {"current_dir": str(seeded)}})
    assert _run(home, stdin=status).stdout == "seg · 1 running · 2 ready · 3 needs you\n"


def test_falls_back_to_cwd_in_status_json(home, seeded):
    assert _run(home, stdin=json.dumps({"cwd": str(seeded)})).stdout.startswith("seg · ")


def test_omits_zero_counts(home, store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _goal(cli, defs, "quiet")
    _work_item(cli, defs, "quiet", "quiet-ready")
    assert _run(home, str(store)).stdout == "quiet · 1 ready\n"


def test_prints_one_line_per_live_effort(home, store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _goal(cli, defs, "alpha")
    _goal(cli, defs, "beta")
    _work_item(cli, defs, "beta", "beta-ready")
    assert sorted(_run(home, str(store)).stdout.splitlines()) == ["alpha", "beta · 1 ready"]


def test_prints_nothing_for_an_effort_without_a_goal(home, store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _work_item(cli, defs, "orphan", "orphan-ready")
    result = _run(home, str(store))
    assert (result.returncode, result.stdout) == (0, "")


def test_every_line_names_a_snapshot_effort_with_matching_counts(home, seeded, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _goal(cli, defs, "calm")
    _work_item(cli, defs, "orphan", "orphan-ready")
    snapshot = dashboard_model.load_snapshot(artifact_store.resolve(seeded))
    expected = []
    for view in snapshot.efforts:
        counts = {
            "running": sum(task.status == "running" for task in view.tasks),
            "ready": sum(task.status == "ready" for task in view.tasks),
            "needs you": len(view.needs_you),
        }
        expected.append(" · ".join([view.effort, *(f"{n} {key}" for key, n in counts.items() if n)]))
    assert _run(home, str(seeded)).stdout.splitlines() == expected
    assert expected == ["calm", "seg · 1 running · 2 ready · 3 needs you"]


def test_prints_nothing_without_a_store(home):
    result = _run(home, str(make_git_repo()))
    assert (result.returncode, result.stdout) == (0, "")


def test_prints_nothing_when_the_cli_fails(home):
    repo = make_git_repo()
    store = repo / ".artifacts"
    store.mkdir()
    (store / "resolved-contract.json").write_text(json.dumps({"views": [{"id": "project:handoff"}]}))
    (store / "meta.json").write_text(json.dumps({"contract": str(store / "resolved-contract.json")}))
    result = _run(home, str(repo))
    assert (result.returncode, result.stdout) == (0, "")


def test_prints_nothing_for_unreadable_status_json(home):
    result = _run(home, stdin="not json", cwd=Path("/"))
    assert (result.returncode, result.stdout) == (0, "")
