"""plan-phase records the recipe, one shared wave executor, and phase run facts before plan review."""

from __future__ import annotations

import json
import re

from conftest import REPO_ROOT
from skill_extraction import extract_invocations

SKILLS = REPO_ROOT / "skills"


def _text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text()


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _work_item_payloads(text: str) -> list[dict]:
    payloads = []
    for inv in extract_invocations(text):
        if inv["type"] == "project:work-item" and inv["payload"]:
            payloads.append(inv["payload"])
        for part in inv["records"] or []:
            if part.get("type") == "project:work-item":
                payloads.append(part["payload"])
    return payloads


def _work_item_def() -> dict:
    design = json.loads((REPO_ROOT / "contract" / "project-design.json").read_text())
    return next(record for record in design["records"] if record["name"] == "work-item")


def test_executor_is_inline_or_subagent_and_approach_stays_optional():
    work_item = _work_item_def()
    assert work_item["payload_enum"]["executor"] == ["inline", "subagent"]
    assert "executor" in work_item["payload"]
    assert "executor" in work_item["optional_payload"]
    assert "Approach" not in work_item["required_sections"]

    raw = _text("plan-phase")
    text = _flat(raw)
    assert "payload `executor` is `inline` or `subagent`" in text
    assert "Missing `executor` means `subagent`." in text
    payloads = _work_item_payloads(raw)
    assert payloads
    assert {payload["executor"] for payload in payloads} <= {"inline", "subagent"}
    for inv in extract_invocations(raw):
        if inv["subcommand"] == "create" and inv["type"] == "project:work-item":
            assert "## Approach" in inv["raw"]
            assert "implementation recipe" in inv["raw"]
        for part in inv["records"] or []:
            if part.get("type") == "project:work-item":
                assert "## Approach" in part["body"]
                assert "implementation recipe" in part["body"]


def test_every_task_in_a_wave_uses_the_same_executor():
    assert "Every task in a wave uses the same executor." in _flat(_text("plan-phase"))
    for path in (SKILLS / "kinds-and-focus.md", REPO_ROOT / "README.md"):
        doc = _flat(path.read_text())
        assert "`inline` or `subagent`" in doc
        assert "Every task in a wave uses the same executor." in doc
        assert "Missing `executor` means `subagent`." in doc
    executors = {payload["executor"] for payload in _work_item_payloads(_text("plan-phase"))}
    assert len(executors) == 1


def test_phase_body_records_size_stops_and_collision_notes():
    text = _flat(_text("plan-phase"))
    assert "size as `one sitting` or `more than one`" in text
    assert "the human stops" in text
    assert "the areas parallel tasks share" in text
    assert "collision notes" in text


def test_plan_review_stays_closed_until_recipe_executor_and_run_facts_are_present():
    text = _text("plan-phase")
    flat = _flat(text)
    gate = "Do not open the plan-review question until those are present"
    question = next(
        inv
        for inv in extract_invocations(text)
        if inv["subcommand"] == "create" and inv["type"] == "project:continuity-question"
    )
    assert question["payload"]["blocking"] is True
    assert question["payload"]["scope"].startswith("plan-review:")
    question_at = flat.index("adaptive-artifacts create --type project:continuity-question")
    gate_at = flat.rindex(gate)
    assert gate_at < question_at
    window = flat[gate_at:question_at]
    assert "implementation recipe" in window
    assert "`inline` or `subagent`" in window
    assert "one sitting" in window
    assert "human stops" in window
    assert "areas parallel tasks share" in window
