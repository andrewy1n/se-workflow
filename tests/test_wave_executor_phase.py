"""plan-phase and execute-phase agree on inline and subagent waves."""

from __future__ import annotations

import re

from conftest import REPO_ROOT

SKILLS = REPO_ROOT / "skills"


def _text(name: str) -> str:
    raw = (SKILLS / name / "SKILL.md").read_text()
    return re.sub(r"\s+", " ", raw)


def test_both_skills_name_the_same_executors():
    plan = _text("plan-phase")
    execute = _text("execute-phase")
    for text in (plan, execute):
        assert "`inline`" in text
        assert "`subagent`" in text


def test_both_skills_treat_a_missing_executor_as_subagent():
    assert "Missing `executor` means `subagent`" in _text("plan-phase")
    assert "Missing or empty means `subagent`" in _text("execute-phase")


def test_execute_stops_when_a_wave_disagrees():
    text = _text("execute-phase")
    assert "If the tasks in the wave disagree, stop and name them. Do not spawn anything." in text
