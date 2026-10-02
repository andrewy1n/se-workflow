"""Guard the analyze-sessions skill: frontmatter, script paths, link, size."""

from __future__ import annotations

import re

from conftest import REPO_ROOT

SKILL_DIR = REPO_ROOT / "skills" / "analyze-sessions"
SKILL = SKILL_DIR / "SKILL.md"


def _split():
    text = SKILL.read_text()
    match = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    assert match, "SKILL.md needs frontmatter"
    meta = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, match.group(2)


def test_frontmatter_names_skill_and_is_user_invoked():
    meta, _ = _split()
    assert meta["name"] == "analyze-sessions"
    assert meta["disable-model-invocation"] == "true"


def test_body_names_both_scripts_that_exist():
    _, body = _split()
    for script in ("scripts/session_report.py", "scripts/session_aggregate.py"):
        assert script in body
        assert (REPO_ROOT / script).is_file()


def test_body_links_existing_targets_md():
    _, body = _split()
    assert "(targets.md)" in body
    assert (SKILL_DIR / "targets.md").is_file()


def test_no_artifact_store_command():
    assert not any("adaptive-artifacts" in l for l in SKILL.read_text().splitlines())


def test_skill_stays_under_80_lines():
    assert len(SKILL.read_text().splitlines()) < 80


def test_skill_creates_temp_directory_with_mktemp():
    assert "mktemp -d" in SKILL.read_text()


def test_skill_defines_pattern_and_noise():
    text = SKILL.read_text()
    assert "Pattern:" in text
    assert "Noise:" in text


def test_skill_defines_severity():
    assert "severity" in SKILL.read_text().lower()


def test_skill_sources_tool_session_references_from_report_file():
    assert "tools.tools" in SKILL.read_text()


def test_skill_defines_bounded_slices():
    assert "200" in SKILL.read_text()
