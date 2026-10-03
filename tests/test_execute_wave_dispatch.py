"""execute-phase runs a wave inline in this session or as one subagent per task."""

from __future__ import annotations

import re

from conftest import REPO_ROOT

SKILLS = REPO_ROOT / "skills"


def _text(name: str) -> str:
    raw = (SKILLS / name / "SKILL.md").read_text()
    return re.sub(r"\s+", " ", raw)


def test_missing_executor_means_subagent_and_disagreement_stops():
    text = _text("execute-phase")
    assert "read `payload.executor` on each ready task" in text
    assert "Missing or empty means `subagent`" in text
    assert "If the tasks in the wave disagree, stop and name them. Do not spawn anything." in text


def test_subagent_wave_is_one_worker_per_task():
    text = _text("execute-phase")
    assert "one `generalPurpose` subagent per task, in parallel within the wave" in text


def test_inline_wave_runs_in_this_session_and_still_verifies():
    text = _text("execute-phase")
    assert (
        "`inline` does not spawn a subagent. This session implements the task, "
        "then still writes the execution-report and runs `verify-work`"
    ) in text
    assert "The parent remains the only writer." in text


def test_approach_is_followed_without_asking_for_a_recipe():
    text = _text("execute-phase")
    assert "Follow `## Approach`" in text
    assert (
        "Do not ask the user for an implementation recipe when `## Approach` is present."
    ) in text
