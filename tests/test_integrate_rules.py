"""execute-phase records semantic integration and does not treat a git merge as pass."""

from __future__ import annotations

import re

import helpers as h
from conftest import REPO_ROOT
from skill_extraction import check_skill_text, extract_invocations

SKILL = REPO_ROOT / "skills" / "execute-phase" / "SKILL.md"


def _text() -> str:
    return re.sub(r"\s+", " ", SKILL.read_text())


def _integration_creates(text: str) -> list[dict]:
    return [
        inv
        for inv in extract_invocations(text)
        if inv["subcommand"] == "create" and inv["type"] == "project:integration-report"
    ]


def test_integration_report_create_matches_the_contract(resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    bundles_by_id = {b["id"]: b for b in resolved_contract.get("bundles", [])}
    text = SKILL.read_text()
    violations = check_skill_text(text, defs, bundles_by_id)
    assert not violations, "\n".join(violations)

    creates = _integration_creates(text)
    assert len(creates) == 1
    record = defs["project:integration-report"]
    payload = creates[0]["payload"]
    required = set(record["payload"]) - {"subject"} - set(record.get("optional_payload") or [])
    assert required <= set(payload)
    documented = payload["result"].strip("<>").split("|")
    assert documented == record["payload_enum"]["result"]
    for section in record["required_sections"]:
        assert f"## {section}" in creates[0]["raw"]


def test_a_git_merge_is_not_a_pass():
    text = _text()
    assert "A clean git merge does not by itself write `pass`" in text
    assert "On `fail` or `blocked`, do not dispatch the verification task." in text


def test_integration_report_is_skipped_for_incidental_and_serial_waves():
    text = _text()
    assert (
        "Skip the report when incidental, or when no implementation wave "
        "has more than one task."
    ) in text
