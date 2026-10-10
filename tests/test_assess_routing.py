"""verify-work splits verify from assess and routes the next stage from evidence."""

from __future__ import annotations

import re

import pytest

import helpers as h
from conftest import REPO_ROOT
from skill_extraction import check_skill_text, extract_invocations

SKILLS = REPO_ROOT / "skills"

ROUTES = (
    ("the cause is the task's code", "failed", "implementation", "execute"),
    ("the design cannot satisfy the requirement", "failed", "design", "design"),
    ("no task covers the requirement", "failed", "plan", "plan"),
    ("the requirement is ambiguous or contradicted", "failed", "specification", "specify"),
    ("integration-report `fail`, and a task must change", "failed", "integration", "execute"),
    ("integration-report `fail`, otherwise", "failed", "integration", "integrate"),
    ("the criterion was not exercised", "insufficient", "verification", "verify"),
    ("every check the requirement needs passed", "verified", None, "release"),
)


def _text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text()


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _writes(name: str, record_type: str, subcommands: set[str] | None = None) -> list[dict]:
    wanted = subcommands or {"create", "supersede"}
    return [
        inv
        for inv in extract_invocations(_text(name))
        if inv["subcommand"] in wanted and inv["type"] == record_type and inv["payload"]
    ]


@pytest.fixture()
def contract_indexes(resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    bundles_by_id = {b["id"]: b for b in resolved_contract.get("bundles", [])}
    return defs, bundles_by_id


def test_verify_and_assess_are_separate_steps():
    text = _text("verify-work")
    assert "Verify and assess are two steps." in text
    assert "## Verify" in text and "## Assess" in text
    verify_at = text.index("## Verify")
    assess_at = text.index("## Assess")
    assert verify_at < assess_at
    flat = _normalized(text)
    assert "Verify asks what happened." in flat
    assert "Assess asks what that evidence means" in flat
    assert "A check-run has no `level` and no `next`." in flat
    assert "`result` is not a contract enum." in flat
    for result in ("pass", "fail", "blocked", "insufficient"):
        assert f"`{result}`" in flat
    assert "`insufficient` — the criterion was not exercised." in flat
    assert "A failing concurrency test does not itself claim the design is wrong." in flat

    check_runs = _writes("verify-work", "project:check-run", {"create"})
    assert check_runs
    for inv in check_runs:
        assert "level" not in inv["payload"]
        assert "next" not in inv["payload"]
        for field in ("criterion_id", "revision", "result", "effort", "method", "signed_by"):
            assert field in inv["payload"]
    bearing = [inv for inv in check_runs if "requirement" in inv["payload"]]
    plain = [inv for inv in check_runs if "requirement" not in inv["payload"]]
    assert len(bearing) == 1 and len(plain) == 1
    assert bearing[0]["payload"]["evidence_kind"]
    assert "evidence_kind" not in plain[0]["payload"]


def test_routing_table_chooses_next_from_the_evidence():
    text = _text("verify-work")
    assert "Choose the first `next` from the evidence." in text
    assert "Do not send every failure to execute." in text
    for cause, status, level, nxt in ROUTES:
        assert cause in text
        row = next(line for line in text.splitlines() if cause in line and line.startswith("|"))
        assert f"`{status}`" in row
        assert f"`{nxt}`" in row
        if level is None:
            assert "omit" in row
        else:
            assert f"`{level}`" in row
    assert "Do not set `next` to `execute`." in _normalized(text)
    assert "`environment` or `unknown`" in text
    assert "acceptance, integration, unit, property, fuzz, review" in _normalized(text)

    by_next = {(inv["payload"].get("level"), inv["payload"]["next"], inv["payload"]["status"])
               for inv in _writes("verify-work", "project:assessment")}
    assert ("implementation", "execute", "failed") in by_next
    assert ("design", "design", "failed") in by_next
    assert ("verification", "verify", "insufficient") in by_next
    assert ("environment", "verify", "blocked") in by_next
    assert (None, "release", "verified") in by_next


def test_evidence_escalation_ladder():
    text = _normalized(_text("verify-work"))
    assert "Decision evidence-escalation." in text
    assert "`implementation` → `design` → `specification`" in text
    assert "The evidence did not increase." in text
    assert "Do not use a failure count." in text
    assert "a new `evidence_kind`" in text
    assert "a narrower failing case" in text
    assert "a cause that was unnamed and is now named" in text
    assert "the previous cause is resolved" in text
    assert "They are not inserted under a repeated implementation failure." in text
    assert "raises `implementation` to `design`" in text
    assert "When `specification` repeats and the evidence still did not increase" in text
    assert "needs` `human`" in text or '`needs` `human`' in text

    raised = [
        inv for inv in _writes("verify-work", "project:assessment", {"supersede"})
        if inv["payload"].get("level") == "design" and inv["payload"]["next"] == "design"
    ]
    assert len(raised) == 1
    assert "The evidence did not increase." in raised[0]["raw"]
    assert "implementation" not in raised[0]["payload"].values()

    questions = _writes("verify-work", "project:continuity-question", {"create"})
    assert len(questions) == 1
    assert questions[0]["payload"]["blocking"] is True
    findings = [
        inv for inv in _writes("verify-work", "project:finding", {"create"})
        if "specification repeated" in inv["payload"]["claim"]
    ]
    assert len(findings) == 1
    assert findings[0]["payload"]["needs"] == "human"


def test_release_ready_only_when_every_requirement_is_verified():
    text = _text("verify-work")
    assert "Decision release-ready." in text
    assert "`ready` means the evidence is sufficient." in text
    assert "When every assessment for the phase is `verified`" in text
    assert "Do not write `merged`, `deployed`, or any other state" in text
    assert "Do not deploy." in text
    releases = _writes("verify-work", "project:release", {"create"})
    assert len(releases) == 1
    assert releases[0]["payload"]["state"] == "ready"
    assert set(releases[0]["payload"]) >= {"state", "phase", "effort"}
    for inv in extract_invocations(text):
        if inv["type"] == "project:release" and inv["payload"]:
            assert inv["payload"]["state"] == "ready"


def test_two_modes_skip_assessment_and_release():
    text = _normalized(_text("verify-work"))
    assert "A phase with no specification, and incidental work, skip assessment and release" in text
    assert "keep pass/fail check-runs" in text
    assert "Do not write `project:assessment` or `project:release` on that path." in text


def test_assessment_examples_carry_required_fields_and_sections():
    for inv in _writes("verify-work", "project:assessment"):
        payload = inv["payload"]
        for field in ("requirement", "status", "next", "confidence", "phase", "effort"):
            assert field in payload
        assert "level" not in payload or payload["status"] != "verified"
        if payload["status"] == "verified":
            assert "level" not in payload
            assert payload["confidence"] == "high"
            assert payload["next"] == "release"
        else:
            assert payload["confidence"] == "low"
            assert payload.get("level")
        for section in ("## Evidence", "## Missing", "## Reason"):
            assert section in inv["raw"]


def test_engage_routes_feedback_through_discuss():
    text = _text("engage")
    assert "A `project:feedback` record is new intent for the effort it names" in text
    assert "Route it through `discuss` (specify)" in text
    assert "Do not collect feedback." in text
    lists = [
        inv for inv in extract_invocations(text)
        if inv["subcommand"] == "list" and inv["type"] == "project:feedback"
    ]
    assert len(lists) == 1
    assert not [
        inv for inv in extract_invocations(text)
        if inv["subcommand"] == "create" and inv["type"] == "project:feedback"
    ]


def test_engage_documents_backlog_item_list_create_supersede():
    text = _text("engage")
    assert "Do not create `project:feedback`" in text
    assert "project:backlog-item" in text
    assert "**Park**" in text or "Park" in text
    assert "promoted" in text and "dismissed" in text
    invs = extract_invocations(text)
    backlog_lists = [
        inv for inv in invs
        if inv["subcommand"] == "list" and inv["type"] == "project:backlog-item"
    ]
    assert len(backlog_lists) == 1
    assert "payload.status=open" in backlog_lists[0]["raw"]
    creates = [
        inv for inv in invs
        if inv["subcommand"] == "create" and inv["type"] == "project:backlog-item"
    ]
    assert len(creates) == 1
    assert creates[0]["payload"]["status"] == "open"
    assert creates[0]["payload"]["effort"]
    supersedes = [
        inv for inv in invs
        if inv["subcommand"] == "supersede" and inv["type"] == "project:backlog-item"
    ]
    statuses = {inv["payload"]["status"] for inv in supersedes if inv["payload"]}
    assert statuses == {"promoted", "dismissed"}
    assert not [
        inv for inv in invs
        if inv["subcommand"] == "create" and inv["type"] == "project:feedback"
    ]


@pytest.mark.parametrize("skill_name", ["verify-work", "engage"])
def test_documented_invocations_are_contract_legal(contract_indexes, skill_name):
    defs, bundles_by_id = contract_indexes
    violations = check_skill_text(_text(skill_name), defs, bundles_by_id)
    assert not violations, "\n".join(violations)


def test_assessment_and_check_run_enums_match_the_contract(contract_indexes):
    defs, _ = contract_indexes
    assessment_enum = defs["project:assessment"]["payload_enum"]
    evidence_kinds = set(defs["project:check-run"]["payload_enum"]["evidence_kind"])
    for inv in _writes("verify-work", "project:check-run", {"create"}):
        kind = inv["payload"].get("evidence_kind")
        if kind is not None:
            assert kind in evidence_kinds
    for inv in _writes("verify-work", "project:assessment"):
        payload = inv["payload"]
        assert payload["status"] in assessment_enum["status"]
        assert payload["next"] in assessment_enum["next"]
        assert payload["confidence"] in assessment_enum["confidence"]
        if "level" in payload:
            assert payload["level"] in assessment_enum["level"]
    release_states = set(defs["project:release"]["payload_enum"]["state"])
    for inv in _writes("verify-work", "project:release", {"create"}):
        assert inv["payload"]["state"] in release_states
        assert inv["payload"]["state"] == "ready"
