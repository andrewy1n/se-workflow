"""Drive one effort through its lifecycle via the CLI and check the dashboard after each step."""

from __future__ import annotations

import json
import os
import re
import subprocess

import helpers as h
from conftest import REPO_ROOT, git

EFFORT = "flow"
PHASE = "flow-phase-1"

_ID = re.compile(r"_\(id: \[(rec-[^\]]+)\]")


def _dashboard(cli) -> dict[str, list[str]]:
    result = cli("view", "--id", "project:dashboard")
    assert result.returncode == 0, result.stdout + result.stderr
    ids = _ID.findall(result.stdout)
    assert len(ids) == len(set(ids)), result.stdout
    return h.section_map(result.stdout, EFFORT)


def _expect(cli, **sections: list[str]) -> str:
    expected = {name.replace("_", " "): sorted(subjects) for name, subjects in sections.items()}
    rendered = cli("view", "--id", "project:dashboard").stdout
    assert _dashboard(cli) == expected, rendered
    return rendered


def _work_item(cli, defs, subject: str, *rels: str) -> dict:
    payload = {"title": f"title of {subject}", "phase": PHASE, "kind": "deliver", "assignee": "", "effort": EFFORT}
    args = ["create", "--type", "project:work-item", "--subject", subject, "--payload", json.dumps(payload)]
    for rel in rels:
        args.extend(["--rel", rel])
    result = cli(*args, "--body", h.generic_body(defs["project:work-item"]))
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def test_every_record_sits_in_exactly_its_lifecycle_section_after_each_step(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    base = {"Goal": [EFFORT], "Phase": [PHASE]}

    h.create_generic_record(
        cli, defs, "project:active-goal", subject=EFFORT,
        extra_payload={"goal": "ship the flow", "kind": "deliver"},
    )
    phase = h.create_generic_record(
        cli, defs, "project:phase", subject=PHASE,
        extra_payload={"title": "first phase", "ordinal": 1, "effort": EFFORT},
    )
    _expect(cli, Goal=[EFFORT])
    h.transition(cli, "project:phase", phase, "in_progress")
    _expect(cli, **base)

    item_a = _work_item(cli, defs, "item-a")
    item_b = _work_item(cli, defs, "item-b", f"depends_on:{item_a['id']}")
    _expect(cli, **base, Ready=["item-a"], Waiting=["item-b"])

    result = cli(
        "update", "--type", "project:work-item", "--id", item_a["id"], "--transition", "in_progress",
        "--expected-revision", item_a["revision"], "--payload", json.dumps({"assignee": "agent-a"}),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    item_a = json.loads(result.stdout)["record"]
    rendered = _expect(cli, **base, Running=["item-a"], Waiting=["item-b"])
    assert "assignee: agent-a" in rendered.split("### Running\n", 1)[1].split("\n### ", 1)[0]

    h.transition(cli, "project:work-item", item_a, "done")
    _expect(cli, **base, Ready=["item-b"], Done_Recent=["item-a"])

    question = h.create_generic_record(
        cli, defs, "project:continuity-question", subject=EFFORT,
        extra_payload={"blocking": True, "scope": "flow-scope"},
    )
    _expect(cli, **base, Blocking_Question=[EFFORT], Ready=["item-b"], Done_Recent=["item-a"])
    h.transition(cli, "project:continuity-question", question, "answered")
    _expect(cli, **base, Ready=["item-b"], Done_Recent=["item-a"])

    h.create_generic_record(
        cli, defs, "project:finding", subject="flow-finding",
        extra_payload={"claim": "a human must decide", "needs": "human", "effort": EFFORT},
    )
    h.create_generic_record(
        cli, defs, "project:check-run", subject="flow-check",
        extra_payload={"method": "manual", "signed_by": "", "result": "pass", "effort": EFFORT},
    )
    _expect(
        cli, **base, Needs_Human=["flow-finding"], Unsigned_Manual_Check=["flow-check"],
        Ready=["item-b"], Done_Recent=["item-a"],
    )

    item_b = h.transition(cli, "project:work-item", item_b, "in_progress")
    h.run_cli_48h_ago(
        store, "update", "--type", "project:work-item", "--id", item_b["id"],
        "--transition", "done", "--expected-revision", item_b["revision"],
    )
    _expect(
        cli, **base, Needs_Human=["flow-finding"], Unsigned_Manual_Check=["flow-check"],
        Done_Recent=["item-a"],
    )

    result = cli("validate")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "valid"


def test_once_prints_the_selector_line_and_wave_strip(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    h.create_generic_record(
        cli, defs, "project:active-goal", subject=EFFORT,
        extra_payload={"goal": "ship the flow", "kind": "deliver"},
    )
    phase = h.create_generic_record(
        cli, defs, "project:phase", subject=PHASE,
        extra_payload={"title": "first phase", "ordinal": 1, "effort": EFFORT},
    )
    h.transition(cli, "project:phase", phase, "in_progress")
    _work_item(cli, defs, "item-a")
    script = REPO_ROOT / "dashboard" / "__main__.py"
    result = subprocess.run(
        ["uv", "run", "--script", str(script), "--once"],
        capture_output=True, text=True, cwd=str(store),
    )
    assert result.returncode == 0, result.stderr
    assert "All phases" in result.stdout
    assert "● first phase" in result.stdout
    assert "w1" in result.stdout


def test_gates_once_shows_action_verbs_next_step_and_landing(store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    phase_slug = "gates-phase"
    branch = f"phase/{phase_slug}"
    git(store, "branch", "-M", "main")
    git(store, "checkout", "-qb", branch)
    (store / "gates-landing.txt").write_text("ahead\n")
    git(store, "add", "gates-landing.txt")
    git(store, "commit", "-qm", "landing-ahead")
    git(store, "checkout", "-q", "main")

    h.create_generic_record(
        cli, defs, "project:active-goal", subject=EFFORT,
        extra_payload={"goal": "ship human gates", "kind": "deliver"},
    )
    body = (
        "## Problem\n\nNeed human gates.\n\n"
        "## Approach\n\nShow verbs, next step, and landing.\n\n"
        f"## Landing\n\n- Branch: `{branch}`\n"
        f"- Worktree: `/tmp/example--{phase_slug}`\n"
        "- Base: `main`\n\n"
        "## Exit criteria\n\nSelector shows landing.\n"
    )
    result = cli(
        "create", "--type", "project:phase", "--subject", phase_slug,
        "--payload", json.dumps({"title": "Gates phase", "ordinal": 1, "effort": EFFORT}),
        "--body", body,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    phase = json.loads(result.stdout)["record"]
    h.transition(cli, "project:phase", phase, "in_progress")

    payload = {
        "title": "quiet runner", "phase": phase_slug, "kind": "deliver",
        "assignee": "", "effort": EFFORT, "estimate_minutes": 10,
    }
    result = cli(
        "create", "--type", "project:work-item", "--subject", "quiet-run",
        "--payload", json.dumps(payload),
        "--body", h.generic_body(defs["project:work-item"]),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    task = json.loads(result.stdout)["record"]
    h.transition(cli, "project:work-item", task, "in_progress")
    h.run_cli_48h_ago(
        store, "create", "--type", "project:assignment", "--subject", "quiet-run",
        "--payload", json.dumps({"work_item": task["id"], "executor": "agent", "effort": EFFORT}),
        "--body", h.generic_body(defs["project:assignment"]),
    )
    h.create_generic_record(
        cli, defs, "project:continuity-question", subject=EFFORT,
        extra_payload={"blocking": True, "scope": f"plan-review:{phase_slug}"},
    )

    script = REPO_ROOT / "dashboard" / "bin" / "dashboard"
    result = subprocess.run(
        [str(script), "--once"],
        capture_output=True, text=True, cwd=str(store),
        env={**os.environ, "COLUMNS": "120"},
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "Review plan" in out
    assert "next: review the gates-phase plan (plan-phase)" in out
    selector = next(line for line in out.splitlines() if "Gates phase" in line)
    assert branch in selector
    assert "1 ahead" in selector
    assert "not merged" in selector
    assert "quiet" in out
