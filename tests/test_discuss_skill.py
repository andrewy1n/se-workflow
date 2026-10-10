"""The discuss skill settles the approach before planning, and plan review gates dispatch."""

from __future__ import annotations

from conftest import REPO_ROOT
from skill_extraction import extract_invocations

SKILLS = REPO_ROOT / "skills"
WRITES = {"create", "update", "supersede", "capture", "apply", "correct", "contradict"}


def _text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text()


def _kinds() -> str:
    return (SKILLS / "kinds-and-focus.md").read_text()


def test_discuss_skill_is_discoverable():
    text = _text("discuss")
    assert text.startswith("---\nname: discuss\n")
    assert "description:" in text.split("---")[1]


def test_discuss_writes_specification_design_decisions_phase_and_questions():
    written = {inv["type"] for inv in extract_invocations(_text("discuss")) if inv["subcommand"] in WRITES}
    assert written == {
        "project:specification",
        "project:design",
        "project:decision",
        "project:phase",
        "project:continuity-question",
    }


def test_engage_routes_new_phases_through_discuss():
    assert "`discuss`" in _text("engage")


def test_plan_phase_opens_a_blocking_plan_review_question():
    reviews = [
        inv for inv in extract_invocations(_text("plan-phase"))
        if inv["subcommand"] == "create" and inv["type"] == "project:continuity-question"
    ]
    assert len(reviews) == 1
    payload = reviews[0]["payload"]
    assert payload["blocking"] is True and payload["scope"].startswith("plan-review:")


def test_execute_phase_scopes_plan_review_questions_to_their_phase():
    assert "plan-review:" in _text("execute-phase")


def test_kinds_and_focus_documents_human_dismissible_clears():
    text = _kinds().lower()
    for kind in ("blocking-question", "open-question", "needs-human", "unsigned-check"):
        assert kind in text
    asserts = extract_invocations(_kinds())
    answered = [
        inv for inv in asserts
        if inv["subcommand"] == "update"
        and inv["type"] == "project:continuity-question"
        and inv["transition"] == "answered"
    ]
    finding_clear = [
        inv for inv in asserts
        if inv["subcommand"] == "supersede"
        and inv["type"] == "project:finding"
        and inv.get("payload", {}).get("needs") == "none"
    ]
    signed = [
        inv for inv in asserts
        if inv["subcommand"] == "correct"
        and inv["type"] == "project:check-run"
        and inv.get("payload", {}).get("signed_by")
    ]
    assert answered and finding_clear and signed


def test_engage_lists_human_dismissible_needs_you_without_blocking_route():
    text = _text("engage")
    lower = text.lower()
    assert "human-dismissible" in lower or "needs-you" in lower or "needs you" in lower
    assert "remind" in lower
    assert "do not refuse" in lower or "does not refuse" in lower or "without blocking" in lower
    assert "route" in lower
    for token in ("continuity-question", "finding", "check-run", "signed_by"):
        assert token in lower or token.replace("-", " ") in lower or token.replace("_", " ") in lower


def test_skills_that_open_human_gates_document_matching_clears():
    discuss = extract_invocations(_text("discuss"))
    assert any(
        inv["subcommand"] == "update"
        and inv["type"] == "project:continuity-question"
        and inv["transition"] == "answered"
        for inv in discuss
    )
    plan = extract_invocations(_text("plan-phase"))
    assert any(
        inv["subcommand"] == "update"
        and inv["type"] == "project:continuity-question"
        and inv["transition"] == "answered"
        for inv in plan
    )
    verify = extract_invocations(_text("verify-work"))
    assert any(
        inv["subcommand"] == "update"
        and inv["type"] == "project:continuity-question"
        and inv["transition"] == "answered"
        for inv in verify
    )
    assert any(
        inv["subcommand"] == "supersede"
        and inv["type"] == "project:finding"
        and (inv.get("payload") or {}).get("needs") == "none"
        for inv in verify
    )
    assert any(
        inv["subcommand"] == "correct"
        and inv["type"] == "project:check-run"
        and (inv.get("payload") or {}).get("signed_by")
        for inv in verify
    )
    execute = extract_invocations(_text("execute-phase"))
    assert any(
        inv["subcommand"] == "update"
        and inv["type"] == "project:continuity-question"
        and inv["transition"] == "answered"
        for inv in execute
    )
    assert any(
        inv["subcommand"] == "correct"
        and inv["type"] == "project:check-run"
        and (inv.get("payload") or {}).get("signed_by")
        for inv in execute
    )
