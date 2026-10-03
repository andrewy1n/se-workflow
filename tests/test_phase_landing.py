"""plan-phase and execute-phase name the same phase landing."""

from __future__ import annotations

import re

from conftest import REPO_ROOT

SKILLS = REPO_ROOT / "skills"

SHARED = (
    "branch `phase/<phase-slug>`",
    "worktree `<repo-parent>/<repo-name>--<phase-slug>`",
    "base `main`",
    "into `main`",
    "the primary checkout",
    "human stop",
)


def _text(name: str) -> str:
    raw = (SKILLS / name / "SKILL.md").read_text()
    return re.sub(r"\s+", " ", raw)


def test_both_skills_name_the_same_landing():
    plan = _text("plan-phase")
    execute = _text("execute-phase")
    for phrase in SHARED:
        assert phrase in plan
        assert phrase in execute
    assert "merge that branch into `main`" in plan
    assert "commit the store on the primary checkout" in plan
    assert "one of the human stops" in plan
    assert "merge into `main`" in execute
    assert "store commit on the primary checkout" in execute
    assert "push only when it is a human stop" in execute
