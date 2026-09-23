"""Contract self-consistency checks.

Every check here is derived from whatever `contract/project-design.json`
currently resolves to -- none hardcode today's record type names or count,
so the suite keeps proving the same properties as the contract grows.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

import helpers as h
from conftest import CONTRACT_PATH, make_git_repo, run_cli


def _resolve_once() -> dict:
    """Resolve the live contract once, at collection time, purely to get the
    record/bundle ids needed for parametrization. Each test still builds its
    own fresh store via the `store` fixture -- this is not shared state."""
    tmp = Path(tempfile.mkdtemp(prefix="se-workflow-collect-"))
    design_dir = tmp / ".artifacts"
    design_dir.mkdir()
    (design_dir / "project-design.json").write_text(CONTRACT_PATH.read_text())
    result = run_cli("resolve", root=tmp)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((design_dir / "resolved-contract.json").read_text())


_CONTRACT_AT_COLLECTION = _resolve_once()
_RECORD_IDS = [r["id"] for r in _CONTRACT_AT_COLLECTION["records"]]
_BUNDLE_IDS = [b["id"] for b in _CONTRACT_AT_COLLECTION.get("bundles", [])]


@pytest.mark.parametrize("record_id", _RECORD_IDS)
def test_record_type_creates_and_reads_back(cli, resolved_contract, record_id):
    defs = h.record_defs_by_id(resolved_contract)
    record = h.create_generic_record(cli, defs, record_id)
    assert record["record_type"] == record_id
    assert record["lifecycle_state"] == defs[record_id]["lifecycle"]["initial"]

    readback = cli("get", "--type", record_id, "--id", record["id"])
    assert readback.returncode == 0, readback.stdout + readback.stderr
    stored = json.loads(readback.stdout)
    assert stored["id"] == record["id"]
    assert stored["subject"] == record["subject"]
    assert stored["lifecycle_state"] == record["lifecycle_state"]


@pytest.mark.parametrize("record_id", _RECORD_IDS)
def test_every_lifecycle_state_is_reachable_from_initial(record_id):
    """Pure graph check: every declared state is reachable from `initial`
    by following declared transitions -- no orphan states."""
    record_def = _CONTRACT_AT_COLLECTION["records"][_RECORD_IDS.index(record_id)]
    states = set(record_def["lifecycle"]["states"])
    initial = record_def["lifecycle"]["initial"]
    graph = h.transitions_graph(record_def)
    seen = {initial}
    frontier = [initial]
    while frontier:
        node = frontier.pop()
        for nxt in graph.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    unreachable = states - seen
    assert not unreachable, (
        f"{record_id}: states {unreachable} are declared but no transition path "
        f"from initial state {initial!r} reaches them"
    )


def _edge_cases():
    cases = []
    for record_def in _CONTRACT_AT_COLLECTION["records"]:
        for src, dest in h.all_edges(record_def):
            cases.append((record_def["id"], src, dest))
    return cases


@pytest.mark.parametrize("record_id,src,dest", _edge_cases(), ids=lambda v: str(v))
def test_lifecycle_transition_is_exercisable(cli, resolved_contract, record_id, src, dest):
    """Every declared (src, dest) transition edge is actually reachable and
    executable through the CLI -- not just present in the JSON graph."""
    defs = h.record_defs_by_id(resolved_contract)
    record_def = defs[record_id]
    record = h.drive_to_state(cli, defs, record_id, src)
    reached = h._apply_transition(cli, record_def, record_id, record, dest)
    assert reached["lifecycle_state"] == dest


@pytest.mark.parametrize("bundle_id", _BUNDLE_IDS)
def test_bundle_relationships_name_existing_types_and_relations(bundle_id):
    defs = {r["id"]: r for r in _CONTRACT_AT_COLLECTION["records"]}
    bundle = next(b for b in _CONTRACT_AT_COLLECTION["bundles"] if b["id"] == bundle_id)
    for part in bundle.get("records", []):
        assert part in defs, f"{bundle_id}: declares record type {part!r} which does not exist"
    for link in bundle.get("relationships", []):
        assert link["from"] in defs, f"{bundle_id}: relationship 'from' {link['from']!r} does not exist"
        assert link["to"] in defs, f"{bundle_id}: relationship 'to' {link['to']!r} does not exist"
        allowed = defs[link["from"]].get("relationships", [])
        assert link["type"] in allowed, (
            f"{bundle_id}: relationship {link['type']!r} from {link['from']!r} is not in that "
            f"type's declared relationships {allowed}"
        )


def _payload_reference_cases():
    cases = []
    for record_def in _CONTRACT_AT_COLLECTION["records"]:
        for field, target_type in record_def.get("payload_references", {}).items():
            cases.append((record_def["id"], field, target_type))
    return cases


@pytest.mark.parametrize(
    "record_id,field,target_type", _payload_reference_cases(), ids=lambda v: str(v)
)
def test_payload_reference_target_type_exists(record_id, field, target_type):
    defs = {r["id"]: r for r in _CONTRACT_AT_COLLECTION["records"]}
    assert target_type in defs, (
        f"{record_id}.payload_references[{field!r}] points at {target_type!r}, "
        "which is not a declared record type"
    )


@pytest.mark.parametrize(
    "record_id,field,target_type", _payload_reference_cases(), ids=lambda v: str(v)
)
def test_payload_reference_resolves_to_a_real_subject(cli, resolved_contract, record_id, field, target_type):
    defs = h.record_defs_by_id(resolved_contract)
    target = h.create_generic_record(cli, defs, target_type)
    record = h.create_generic_record(
        cli, defs, record_id, extra_payload={field: target["subject"]}
    )
    result = cli("validate")
    assert result.returncode == 0, (
        f"validate failed with a correct payload reference "
        f"{record_id}.{field} -> {target_type}: {result.stdout}\n{result.stderr}"
    )
    payload = json.loads(result.stdout)
    assert payload.get("status") == "valid", payload


def test_payload_reference_violation_is_caught_by_validate(cli, resolved_contract):
    """Negative case: at least one payload reference pointed at a subject that
    does not exist must make `validate` fail -- proves the check has teeth."""
    cases = _payload_reference_cases()
    if not cases:
        pytest.skip("this contract declares no payload_references")
    record_id, field, _target_type = cases[0]
    defs = h.record_defs_by_id(resolved_contract)
    h.create_generic_record(cli, defs, record_id, extra_payload={field: "does-not-exist-anywhere"})
    result = cli("validate")
    payload = json.loads(result.stdout)
    assert payload.get("status") != "valid", (
        f"validate accepted a payload reference to a nonexistent subject: {payload}"
    )
