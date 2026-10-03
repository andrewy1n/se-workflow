"""execute-phase lands the phase branch when the phase body has a Landing section."""

from __future__ import annotations

import re

from conftest import REPO_ROOT

SKILLS = REPO_ROOT / "skills"


def _text(name: str) -> str:
    raw = (SKILLS / name / "SKILL.md").read_text()
    return re.sub(r"\s+", " ", raw)


def test_landing_worktree_confines_code_and_keeps_the_store_on_the_primary_checkout():
    text = _text("execute-phase")
    assert "<repo-parent>/<repo-name>--<phase-slug>" in text
    assert "code writes only under the worktree" in text
    assert "store writes on the primary checkout" in text


def test_gate_commits_the_phase_branch_merges_to_main_and_commits_the_store():
    text = _text("execute-phase")
    assert "commit the phase branch" in text
    assert "merge into `main`" in text
    assert "commit the store" in text


def test_push_only_when_it_is_a_human_stop():
    text = _text("execute-phase")
    assert "push only when it is a human stop" in text


def test_missing_landing_section_stays_in_the_current_checkout():
    text = _text("execute-phase")
    assert "a missing Landing section stays in the current checkout" in text
