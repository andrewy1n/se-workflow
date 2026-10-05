"""plan-phase stamps requirements and decisions when a specification exists."""

from __future__ import annotations

import json

import helpers as h
from conftest import REPO_ROOT
from skill_extraction import check_skill_text, extract_invocations

SKILL = REPO_ROOT / "skills" / "plan-phase" / "SKILL.md"

REQUIRED_WORK_ITEM = {"title", "phase", "kind", "assignee", "effort"}
REQUIRED_ACCEPTANCE = {"criterion", "method", "phase", "effort", "verify_command"}
WRITES = {"create", "update", "supersede", "capture"}


def _text() -> str:
    return SKILL.read_text()


def _flat(text: str) -> str:
    return " ".join(text.split())


def _payloads(text: str, record_type: str) -> list[dict]:
    payloads = []
    for inv in extract_invocations(text):
        if inv["type"] == record_type and inv["payload"]:
            payloads.append(inv["payload"])
        for part in inv["records"] or []:
            if part.get("type") == record_type:
                payloads.append(part["payload"])
    return payloads


def _record(name: str) -> dict:
    design = json.loads((REPO_ROOT / "contract" / "project-design.json").read_text())
    return next(record for record in design["records"] if record["name"] == name)


def test_trace_fields_are_optional_in_the_contract():
    work_item = _record("work-item")
    acceptance = _record("acceptance")
    assert {"requirements", "decisions"} <= set(work_item["optional_payload"])
    assert "requirement" in acceptance["optional_payload"]
    work_required = set(work_item["payload"]) - set(work_item["optional_payload"])
    acceptance_required = set(acceptance["payload"]) - set(acceptance["optional_payload"])
    assert "requirements" not in work_required
    assert "decisions" not in work_required
    assert "requirement" not in acceptance_required


def test_specification_examples_stamp_trace_fields_on_create_payloads():
    text = _text()
    flat = _flat(text)
    assert "When a `project:specification` exists for the phase" in flat
    assert (
        "When no specification exists, omit `requirements`, `decisions`, and `requirement`."
        in flat
    )

    work_items = _payloads(text, "project:work-item")
    acceptances = _payloads(text, "project:acceptance")
    assert work_items and acceptances
    covered = set()
    for payload in work_items:
        assert REQUIRED_WORK_ITEM <= set(payload)
        assert payload["requirements"]
        assert payload["decisions"]
        assert "ready" not in payload and "wave" not in payload
        covered.update(part.strip() for part in payload["requirements"].split(",") if part.strip())
    for payload in acceptances:
        assert REQUIRED_ACCEPTANCE <= set(payload)
        assert payload["requirement"] in covered
        assert "," not in payload["requirement"]

    acceptance_subjects = []
    written = set()
    for inv in extract_invocations(text):
        if inv["subcommand"] in WRITES and inv["type"]:
            written.add(inv["type"])
        if inv["type"] == "project:work-item":
            assert all(rel.split(":", 1)[0] == "depends_on" for rel in inv["rels"])
        for part in inv["records"] or []:
            if inv["subcommand"] != "capture":
                continue
            written.add(part.get("type"))
            if part.get("type") == "project:acceptance":
                acceptance_subjects.append(part["subject"])
    assert "project:assessment" not in written
    assert "project:integration-report" not in written
    assert "<task-slug>" in acceptance_subjects
    assert "<task-slug>-perf" in acceptance_subjects


def test_plan_phase_trace_invocations_are_contract_legal(resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    bundles = {bundle["id"]: bundle for bundle in resolved_contract.get("bundles", [])}
    violations = check_skill_text(_text(), defs, bundles)
    assert not violations, "\n".join(violations)
