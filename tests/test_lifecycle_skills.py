"""Skills and the README name the same lifecycle the model implements."""

from __future__ import annotations

import re

from conftest import REPO_ROOT
from lifecycle.loop import LAYERS, MAX_REPAIRS, RELEASE_STATUSES, STAGES, VERDICTS

SKILLS = REPO_ROOT / "skills"


def _flat(path) -> str:
    return re.sub(r"\s+", " ", path.read_text())


def test_shared_rules_use_the_model_vocabulary():
    text = _flat(SKILLS / "lifecycle.md")
    for stage in STAGES:
        assert f"`{stage}`" in text
    for verdict in VERDICTS:
        assert f"`{verdict}`" in text
    for layer in LAYERS:
        assert f"`{layer}`" in text
    for status in RELEASE_STATUSES:
        assert f"`{status}`" in text
    assert f"The repair limit is {MAX_REPAIRS}" in text
    assert "A git merge" in text or "Git merge success is not" in text
    assert "Verified is not deployed" in text or "does not deploy" in text


def test_stage_skills_exist_and_point_at_the_shared_rules():
    for name in ("specify", "design", "integrate", "diagnose", "release", "feedback"):
        text = (SKILLS / name / "SKILL.md").read_text()
        assert text.startswith(f"---\nname: {name}\n")
        assert "lifecycle.md" in text


def test_repair_skill_states_the_limit_and_the_unresolved_stop():
    text = _flat(SKILLS / "diagnose" / "SKILL.md")
    assert f"The repair limit is {MAX_REPAIRS}" in text
    assert "unresolved" in text
    assert "failure_signature" in text
    assert "execute-phase" in text


def test_integrate_skill_rejects_a_clean_merge_as_proof():
    text = _flat(SKILLS / "integrate" / "SKILL.md")
    assert "Git merge success is not this verdict." in text
    assert "A clean merge with disagreeing interfaces or assumptions is `fail`." in text


def test_verify_records_unknown_separately_from_a_passing_command():
    text = _flat(SKILLS / "verify-work" / "SKILL.md")
    assert "`unknown` means the commands that ran do not cover the criterion." in text
    assert '"verdict":"pass"' in text
    assert "project:uncertainty" in text


def test_plan_traces_tasks_to_specification_criteria():
    text = _flat(SKILLS / "plan-phase" / "SKILL.md")
    assert "satisfies" in text
    assert "spec-<phase-slug>-<criterion>" in text


def test_execute_hands_specification_context_to_executors_and_gates_on_integration():
    text = _flat(SKILLS / "execute-phase" / "SKILL.md")
    assert "when a specification exists" in text
    assert "A git merge that succeeds is not that verdict." in text


def test_trivial_depth_skips_specification_and_design():
    engage = _flat(SKILLS / "engage" / "SKILL.md")
    assert "Skip `specify` and `design` for `trivial`" in engage
    assert "`discuss`" in engage


def test_readme_matches_the_implemented_stages():
    readme = _flat(REPO_ROOT / "README.md")
    assert "intent → specify → design → plan → execute → integrate → verify" in readme
    assert "There is no deployer and no metrics pipeline." in readme
    assert "A clean git merge is not this pass" in readme
    for name in ("specify", "design", "integrate", "diagnose", "release", "feedback"):
        assert f"`{name}`" in readme
