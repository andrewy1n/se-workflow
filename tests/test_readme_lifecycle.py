"""README states the lifecycle the skills already describe."""

from __future__ import annotations

import re

from conftest import REPO_ROOT


def _lifecycle() -> str:
    text = (REPO_ROOT / "README.md").read_text()
    start = text.index("## Lifecycle")
    rest = text[start + len("## Lifecycle") :]
    end = rest.find("\n## ")
    section = rest if end < 0 else rest[:end]
    return re.sub(r"\s+", " ", section).strip()


def test_two_modes():
    text = _lifecycle()
    assert "Decision two-modes is the rule." in text
    assert "Structured work is a phase with a specification." in text
    assert (
        "specify, design, plan, execute, integrate when a wave is parallel, "
        "verify, assess, and release `ready`"
    ) in text
    assert "Simple work is incidental, or a phase with no specification." in text
    assert "It runs execute, then verify as pass or fail." in text
    assert "skip assessment and release and keep pass/fail check-runs" in text


def test_verify_assess_split():
    text = _lifecycle()
    assert "Verify and assess are two steps." in text
    assert "Verify asks what happened." in text
    assert "A check-run records what happened and which requirement it bears on." in text
    assert "It has no `level` and no `next`." in text
    assert "An assessment records what that evidence means and which stage is next." in text
    assert "A failing test does not itself choose the stage." in text
    assert "implementation to execute" in text
    assert "design to design" in text
    assert "plan to plan" in text
    assert "specification to specify" in text
    assert "integration to integrate or execute" in text
    assert "insufficient evidence to verify" in text


def test_escalation_ladder():
    text = _lifecycle()
    assert "Decision evidence-escalation." in text
    assert (
        "The same level repeats only when evidence increased or the cause was resolved."
    ) in text
    assert "the ladder is implementation, then design, then specification" in text
    assert "`plan` and `integration` are direct diagnoses." in text
    assert "They are not inserted under a repeated implementation failure." in text
    assert "Do not use a failure count." in text


def test_ready_is_not_deployed():
    text = _lifecycle()
    assert "Decision release-ready." in text
    assert "Release state `ready` means every requirement is verified." in text
    assert "It does not mean merged or deployed." in text
    assert "Do not deploy." in text
    assert "means deployed" not in text
    assert "means merged" not in text
