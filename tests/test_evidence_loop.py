"""Drive the evidence loop through the adaptive-artifacts CLI on a fresh store.

Each scenario builds its own git-backed store from the worktree contract
(the `cli` fixture) and asserts `validate` accepts it. Record bodies come
from that contract's `required_sections`.
"""

from __future__ import annotations

import json
import re

import helpers as h
from conftest import REPO_ROOT

EFFORT = "workflow-loop"
SKILL = REPO_ROOT / "skills" / "verify-work" / "SKILL.md"


def _skill_text() -> str:
    return re.sub(r"\s+", " ", SKILL.read_text())


def _body(record_def: dict, fills: dict[str, str] | None = None) -> str | None:
    required = record_def.get("required_sections") or []
    if not required:
        return None
    fills = fills or {}
    parts = [f"## {name}\n\n{fills.get(name, f'placeholder for {name}.')}" for name in required]
    return "\n\n".join(parts)


def _create(cli, defs, record_type: str, subject: str, payload: dict, *, fills=None, rel=None) -> dict:
    args = ["create", "--type", record_type, "--subject", subject, "--payload", json.dumps(payload)]
    body = _body(defs[record_type], fills)
    if body:
        args.extend(["--body", body])
    for item in rel or []:
        args.extend(["--rel", item])
    result = cli(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def _assert_valid(cli) -> None:
    result = cli("validate")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload.get("status") == "valid", payload


def _records(cli, record_type: str) -> list[dict]:
    result = cli("list", "--type", record_type, "--full")
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["records"]


def _phase(cli, defs, subject: str) -> dict:
    return _create(
        cli, defs, "project:phase", subject,
        {"title": f"title of {subject}", "ordinal": 1, "effort": EFFORT},
    )


def _work_item(cli, defs, subject: str, phase: str, *, requirements: str | None = None) -> dict:
    payload = {
        "title": subject,
        "phase": phase,
        "kind": "deliver",
        "assignee": "loop-scenarios",
        "effort": EFFORT,
    }
    if requirements is not None:
        payload["requirements"] = requirements
    record = _create(cli, defs, "project:work-item", subject, payload)
    return h.transition(cli, "project:work-item", record, "in_progress")


def _acceptance(cli, defs, subject: str, phase: str, *, requirement: str | None = None) -> dict:
    payload = {
        "criterion": f"{subject} meets its criterion",
        "method": "check",
        "phase": phase,
        "effort": EFFORT,
        "verify_command": "uv run --with textual --with pytest python -m pytest tests/test_evidence_loop.py -q",
    }
    if requirement is not None:
        payload["requirement"] = requirement
    return _create(cli, defs, "project:acceptance", subject, payload)


def _check_run(
    cli, defs, subject: str, acceptance_id: str, result: str, *,
    requirement: str | None = None, evidence_kind: str | None = None,
) -> dict:
    payload = {
        "criterion_id": acceptance_id,
        "revision": "dirty",
        "result": result,
        "effort": EFFORT,
        "method": "check",
        "signed_by": "",
    }
    if requirement is not None:
        payload["requirement"] = requirement
    if evidence_kind is not None:
        payload["evidence_kind"] = evidence_kind
    record = _create(
        cli, defs, "project:check-run", subject, payload,
        rel=[f"informed_by:{acceptance_id}"],
    )
    assert "level" not in record["payload"]
    assert "next" not in record["payload"]
    return record


def _assessment(cli, defs, phase: str, requirement: str, payload: dict) -> dict:
    full = {
        "requirement": requirement,
        "phase": phase,
        "effort": EFFORT,
        "missing": "",
    }
    full.update(payload)
    return _create(cli, defs, "project:assessment", f"{phase}-{requirement}", full)


def _supersede_assessment(cli, defs, record: dict, payload: dict, reason: str) -> dict:
    body = _body(defs["project:assessment"], {"Reason": reason})
    result = cli(
        "supersede",
        "--type", "project:assessment",
        "--id", record["id"],
        "--expected-revision", record["revision"],
        "--payload", json.dumps({**record["payload"], **payload}),
        "--body", body,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def _scaffold(cli, defs, phase: str, task: str, *, requirements: str | None = "R1"):
    _phase(cli, defs, phase)
    if requirements is not None:
        _create(
            cli, defs, "project:specification", phase,
            {"weight": "light", "phase": phase, "effort": EFFORT, "requirements": requirements},
            fills={"Requirements": f"{requirements}: the requirement under test."},
        )
        _create(
            cli, defs, "project:design", phase,
            {"phase": phase, "effort": EFFORT, "decisions": "release-ready"},
        )
    work_item = _work_item(cli, defs, task, phase, requirements=requirements)
    acceptance = _acceptance(cli, defs, task, phase, requirement=requirements)
    return work_item, acceptance


def test_happy_path_reaches_release_ready(cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    check_def = defs["project:check-run"]
    assert "result" not in check_def.get("payload_enum", {})
    assert "unit" in check_def["payload_enum"]["evidence_kind"]
    release_states = defs["project:release"]["payload_enum"]["state"]
    assert "ready" in release_states and "deployed" in release_states

    phase, task = "happy-phase", "happy-task"
    work_item, acceptance = _scaffold(cli, defs, phase, task)
    spec = _records(cli, "project:specification")[0]
    assert spec["payload"]["requirements"] == "R1"
    assert work_item["payload"]["requirements"] == "R1"
    assert acceptance["payload"]["requirement"] == "R1"

    check = _check_run(
        cli, defs, task, acceptance["id"], "pass", requirement="R1", evidence_kind="unit",
    )
    assert check["payload"]["result"] == "pass"
    assert check["payload"]["evidence_kind"] == "unit"

    assessment = _assessment(cli, defs, phase, "R1", {
        "status": "verified",
        "next": "release",
        "confidence": "high",
    })
    assert assessment["payload"]["status"] == "verified"
    assert assessment["payload"]["next"] == "release"
    assert assessment["payload"]["confidence"] == "high"
    assert "level" not in assessment["payload"]

    release = _create(
        cli, defs, "project:release", phase,
        {"state": "ready", "phase": phase, "effort": EFFORT},
    )
    assert release["payload"]["state"] == "ready"
    assert release["payload"]["state"] != "deployed"

    closed = h.transition(cli, "project:work-item", work_item, "done")
    assert closed["lifecycle_state"] == "done"
    _assert_valid(cli)


def test_implementation_failure_stays_in_progress(cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    phase, task = "impl-phase", "impl-task"
    work_item, acceptance = _scaffold(cli, defs, phase, task)
    check = _check_run(
        cli, defs, task, acceptance["id"], "fail", requirement="R1", evidence_kind="unit",
    )
    assert check["payload"]["result"] == "fail"
    assert "level" not in defs["project:check-run"]["payload"]
    assert "next" not in defs["project:check-run"]["payload"]

    assessment = _assessment(cli, defs, phase, "R1", {
        "status": "failed",
        "level": "implementation",
        "next": "execute",
        "confidence": "low",
    })
    assert assessment["payload"]["level"] == "implementation"
    assert assessment["payload"]["next"] == "execute"
    assert assessment["record_type"] != check["record_type"]

    stored = json.loads(cli("get", "--type", "project:work-item", "--id", work_item["id"]).stdout)
    assert stored["lifecycle_state"] == "in_progress"
    _assert_valid(cli)


def test_design_failure_does_not_close_the_work_item(cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    phase, task = "design-phase", "design-task"
    work_item, acceptance = _scaffold(cli, defs, phase, task)
    check = _check_run(
        cli, defs, task, acceptance["id"], "fail", requirement="R1", evidence_kind="unit",
    )
    assert "level" not in check["payload"] and "next" not in check["payload"]

    assessment = _assessment(cli, defs, phase, "R1", {
        "status": "failed",
        "level": "design",
        "next": "design",
        "confidence": "low",
    })
    assert assessment["payload"]["level"] == "design"
    assert assessment["payload"]["next"] == "design"

    stored = json.loads(cli("get", "--type", "project:work-item", "--id", work_item["id"]).stdout)
    assert stored["lifecycle_state"] == "in_progress"
    assert stored["lifecycle_state"] != "done"
    _assert_valid(cli)


def test_repeat_without_new_evidence_supersedes_to_design(cli, resolved_contract):
    text = _skill_text()
    assert "A repeat that adds no evidence raises `implementation` to `design`" in text
    assert "or the previous cause is resolved" in text
    assert "When the new check-run adds an `evidence_kind`" in text
    assert "stay at `implementation` / `execute`" in text

    defs = h.record_defs_by_id(resolved_contract)
    phase, task = "escalate-phase", "escalate-task"
    _work_item_ignored, acceptance = _scaffold(cli, defs, phase, task)
    _check_run(
        cli, defs, task, acceptance["id"], "fail", requirement="R1", evidence_kind="unit",
    )
    first = _assessment(cli, defs, phase, "R1", {
        "status": "failed",
        "level": "implementation",
        "next": "execute",
        "confidence": "low",
    })
    assert first["payload"]["level"] == "implementation"
    assert first["payload"]["next"] == "execute"

    successor = _supersede_assessment(
        cli, defs, first,
        {"status": "failed", "level": "design", "next": "design", "confidence": "low"},
        "The evidence did not increase. The same cause is unchanged.",
    )
    assert successor["id"] != first["id"]
    assert successor["subject"] == first["subject"]
    assert successor["lifecycle_state"] == "active"
    assert successor["payload"]["level"] == "design"
    assert successor["payload"]["next"] == "design"
    assert first["id"] in successor["relationships"]["supersedes"]

    predecessor = json.loads(cli("get", "--type", "project:assessment", "--id", first["id"]).stdout)
    assert predecessor["lifecycle_state"] == "superseded"
    _assert_valid(cli)


def test_new_evidence_kind_stays_on_execute(cli, resolved_contract):
    text = _skill_text()
    assert "adds an `evidence_kind`" in text
    assert "stay at `implementation` / `execute`" in text

    defs = h.record_defs_by_id(resolved_contract)
    kinds = defs["project:check-run"]["payload_enum"]["evidence_kind"]
    assert "unit" in kinds and "integration" in kinds

    phase, task = "evidence-phase", "evidence-task"
    _work, acceptance = _scaffold(cli, defs, phase, task)
    first_check = _check_run(
        cli, defs, task, acceptance["id"], "fail", requirement="R1", evidence_kind="unit",
    )
    assessment = _assessment(cli, defs, phase, "R1", {
        "status": "failed",
        "level": "implementation",
        "next": "execute",
        "confidence": "low",
    })
    second_check = _check_run(
        cli, defs, task, acceptance["id"], "fail", requirement="R1", evidence_kind="integration",
    )
    assert first_check["payload"]["evidence_kind"] != second_check["payload"]["evidence_kind"]

    stayed = _supersede_assessment(
        cli, defs, assessment,
        {"status": "failed", "level": "implementation", "next": "execute", "confidence": "low"},
        "A new evidence_kind appeared, so this stays on execute.",
    )
    assert stayed["subject"] == assessment["subject"]
    assert stayed["payload"]["level"] == "implementation"
    assert stayed["payload"]["next"] == "execute"
    _assert_valid(cli)


def test_integration_fail_then_pass_is_a_new_record(cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    results = defs["project:integration-report"]["payload_enum"]["result"]
    assert "fail" in results and "pass" in results

    phase = "integrate-phase"
    _phase(cli, defs, phase)
    failed = _create(
        cli, defs, "project:integration-report", phase,
        {"phase": phase, "effort": EFFORT, "result": "fail", "revision": "dirty"},
    )
    assert failed["payload"]["result"] == "fail"

    edited = cli(
        "update",
        "--type", "project:integration-report",
        "--id", failed["id"],
        "--expected-revision", failed["revision"],
        "--payload", json.dumps({"result": "pass"}),
    )
    assert edited.returncode != 0
    assert json.loads(edited.stdout)["error"] == "append_only"

    passed = _create(
        cli, defs, "project:integration-report", phase,
        {"phase": phase, "effort": EFFORT, "result": "pass", "revision": "dirty"},
    )
    assert passed["id"] != failed["id"]
    assert passed["payload"]["result"] == "pass"

    unchanged = json.loads(
        cli("get", "--type", "project:integration-report", "--id", failed["id"]).stdout
    )
    assert unchanged["payload"]["result"] == "fail"
    assert {record["payload"]["result"] for record in _records(cli, "project:integration-report")} == {
        "fail", "pass",
    }
    _assert_valid(cli)


def test_insufficient_evidence_is_not_forced_verified(cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    phase, task = "insufficient-phase", "insufficient-task"
    _work, acceptance = _scaffold(cli, defs, phase, task)
    assessment = _assessment(cli, defs, phase, "R1", {
        "status": "insufficient",
        "level": "verification",
        "next": "verify",
        "confidence": "low",
        "missing": "acceptance",
    })
    assert assessment["payload"]["missing"] == "acceptance"

    check = _check_run(
        cli, defs, task, acceptance["id"], "pass", requirement="R1", evidence_kind="unit",
    )
    assert check["payload"]["evidence_kind"] != assessment["payload"]["missing"]
    assert check["payload"]["result"] == "pass"

    stored = json.loads(cli("get", "--type", "project:assessment", "--id", assessment["id"]).stdout)
    assert stored["lifecycle_state"] == "active"
    assert stored["payload"]["status"] == "insufficient"
    assert stored["payload"]["level"] == "verification"
    assert stored["payload"]["next"] == "verify"
    assert stored["payload"]["status"] != "verified"
    _assert_valid(cli)


def test_simple_mode_pass_omits_requirement_and_evidence_kind(cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    phase, task = "simple-phase", "simple-task"
    _work, acceptance = _scaffold(cli, defs, phase, task, requirements=None)
    assert _records(cli, "project:specification") == []

    check = _check_run(cli, defs, task, acceptance["id"], "pass")
    assert check["payload"]["result"] == "pass"
    assert "requirement" not in check["payload"]
    assert "evidence_kind" not in check["payload"]
    assert "level" not in check["payload"] and "next" not in check["payload"]

    assert _records(cli, "project:assessment") == []
    assert _records(cli, "project:release") == []
    _assert_valid(cli)
