"""Verification stays on the phase's checks, and a failing check does not edit."""

from __future__ import annotations

import re

from conftest import REPO_ROOT

SKILLS = REPO_ROOT / "skills"

FORBIDDEN_CHAIN = '-n 4 -m "not tmux"'


def _text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text()


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _testing_section(name: str) -> str:
    text = (REPO_ROOT / name).read_text()
    start = text.index("## Testing")
    rest = text[start + len("## Testing") :]
    end = rest.find("\n## ")
    section = rest if end < 0 else rest[:end]
    return _flat(section)


def test_plan_phase_limits_verification_to_phase_checks():
    text = _flat(_text("plan-phase"))
    assert "verification task's acceptances come from the phase exit criteria" in text
    assert "one is an integration check through the real entry point" in text


def test_plan_phase_rejects_whole_suite_and_unfiltered_app_file():
    text = _flat(_text("plan-phase"))
    assert "whole `tests` tree" in text
    assert "`tests/test_dashboard_app.py` without a `-k` filter for this phase" in text
    assert "is not a verification acceptance" in text


def test_close_instructions_use_the_task_command():
    for name in ("AGENTS.md", "CLAUDE.md"):
        section = _testing_section(name)
        assert "`verify_command`" in section
        chain_at = section.find(FORBIDDEN_CHAIN)
        assert chain_at < 0 or "-m tmux" not in section[chain_at:]
        assert "run the full suite" not in section
        assert "full suite" not in section or "clos" not in section


def test_verification_failure_does_not_edit():
    execute = _flat(_text("execute-phase"))
    assert "The verification executor returns `fail` and does not edit the tree." in execute

    verify = _flat(_text("verify-work"))
    assert (
        "leave the work-item `in_progress` and use assessment `next` `execute`"
        in verify
    )
    assert "a suite the acceptance does not name" in verify
