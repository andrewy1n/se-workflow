"""The discuss skill settles the approach before planning, and plan review gates dispatch."""

from __future__ import annotations

from conftest import REPO_ROOT
from skill_extraction import extract_invocations

SKILLS = REPO_ROOT / "skills"
WRITES = {"create", "update", "supersede", "capture", "apply", "correct", "contradict"}


def _text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text()


def test_discuss_skill_is_discoverable():
    text = _text("discuss")
    assert text.startswith("---\nname: discuss\n")
    assert "description:" in text.split("---")[1]


def test_discuss_writes_only_decisions_phase_bodies_and_questions():
    written = {inv["type"] for inv in extract_invocations(_text("discuss")) if inv["subcommand"] in WRITES}
    assert written == {"project:decision", "project:phase", "project:continuity-question"}


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
