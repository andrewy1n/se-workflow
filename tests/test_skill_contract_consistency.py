"""Assert every `adaptive-artifacts` invocation documented in skills/ names a
record type, transition, relationship, or bundle membership that the
resolved contract actually permits.

This is a regression guard against the bug class "a skill instructs an
operation the contract does not allow" (e.g. selecting by a field the
contract does not track that way, or calling a subcommand a record type does
not support).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import helpers as h
from conftest import REPO_ROOT
from skill_extraction import check_skill_text, skill_markdown_files

SKILLS_ROOT = REPO_ROOT / "skills"


@pytest.fixture()
def contract_indexes(resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    bundles_by_id = {b["id"]: b for b in resolved_contract.get("bundles", [])}
    return defs, bundles_by_id


def _skill_files():
    return skill_markdown_files(SKILLS_ROOT)


@pytest.mark.parametrize("skill_file", _skill_files(), ids=lambda p: str(p.relative_to(SKILLS_ROOT)))
def test_skill_invocations_are_permitted_by_contract(contract_indexes, skill_file):
    defs, bundles_by_id = contract_indexes
    text = skill_file.read_text()
    violations = check_skill_text(text, defs, bundles_by_id)
    assert not violations, (
        f"{skill_file.relative_to(SKILLS_ROOT)} instructs an operation the current contract "
        "does not permit:\n" + "\n".join(f"  - {v}" for v in violations)
    )
