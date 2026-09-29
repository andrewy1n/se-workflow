"""Drive one effort through its lifecycle via the CLI and check the dashboard after each step."""

from __future__ import annotations

import json
import re

import helpers as h

EFFORT = "flow"
PHASE = "flow-phase-1"

_SECTION = re.compile(r"^### (.+)$")
_ITEM = re.compile(r"^- \*\*(.+?)\*\*.*_\(id: \[(rec-[^\]]+)\]")


def _dashboard(cli) -> dict[str, list[str]]:
    result = cli("view", "--id", "project:dashboard")
    assert result.returncode == 0, result.stdout + result.stderr
    sections: dict[str, list[str]] = {}
    ids: list[str] = []
    group = current = None
    for line in result.stdout.splitlines():
        if line.startswith("## "):
            group = line[3:]
            current = None
        elif match := _SECTION.match(line):
            current = match.group(1)
        elif match := _ITEM.match(line):
            assert group == EFFORT and current is not None, result.stdout
            sections.setdefault(current, []).append(match.group(1))
            ids.append(match.group(2))
    assert len(ids) == len(set(ids)), result.stdout
    return {name: sorted(subjects) for name, subjects in sections.items()}


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
