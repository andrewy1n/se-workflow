"""Tests for scripts/close_batch.py -- the batch builder behind the
verify-work `close` procedure.

The pure `build_batch` tests exercise the refusal policy directly; the
`test_end_to_end_*` tests drive the real `adaptive-artifacts` CLI (via the
shared `cli`/`resolved_contract` fixtures) to prove the emitted NDJSON is
actually accepted by `apply` and lands the record shape the skill promises.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import helpers as h
from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "close_batch.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import close_batch  # noqa: E402


def _request(**overrides):
    base = {
        "subject": "task-1",
        "effort": "effort-1",
        "work_item_id": "rec-wi",
        "transition": "done",
        "execution_report_id": "rec-er",
        "acceptance_ids": ["rec-ac1"],
        "criteria": [
            {
                "criterion_id": "rec-ac1",
                "result": "pass",
                "method": "tdd",
                "revision": "abc123",
                "signed_by": "",
            }
        ],
        "finding": None,
    }
    base.update(overrides)
    return base


def _run_script(request: dict, tmp_path: Path) -> tuple[subprocess.CompletedProcess, Path]:
    input_path = tmp_path / "close-request.json"
    input_path.write_text(json.dumps(request))
    out_path = tmp_path / "close-batch.ndjson"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(input_path), "--out", str(out_path)],
        capture_output=True,
        text=True,
    )
    return result, out_path


# -- build_batch: pure policy tests -----------------------------------


def test_all_pass_batch_is_one_check_run_then_the_transition():
    ops = close_batch.build_batch(_request())
    assert [op["op"] for op in ops] == ["create", "update"]
    check_run = ops[0]
    assert check_run["type"] == "project:check-run"
    assert check_run["subject"] == "task-1"
    assert check_run["payload"]["result"] == "pass"
    assert check_run["rel"] == ["informed_by:rec-ac1", "informed_by:rec-er"]
    assert ops[-1] == {
        "op": "update",
        "type": "project:work-item",
        "id": "rec-wi",
        "transition": "done",
        "expected_revision": "@current",
    }


def test_refuses_done_when_result_passes_but_verdict_is_unknown():
    request = _request(
        criteria=[
            {
                "criterion_id": "rec-ac1",
                "result": "pass",
                "verdict": "unknown",
                "layer": "unit",
                "method": "tdd",
                "revision": "abc123",
                "signed_by": "",
            }
        ]
    )
    with pytest.raises(close_batch.CloseRefused):
        close_batch.build_batch(request)


def test_check_run_payload_carries_verdict_and_layer():
    request = _request(
        criteria=[
            {
                "criterion_id": "rec-ac1",
                "result": "pass",
                "verdict": "pass",
                "layer": "acceptance",
                "uncertainty": "provider outage is untested",
                "method": "tdd",
                "revision": "abc123",
                "signed_by": "",
            }
        ]
    )
    payload = close_batch.build_batch(request)[0]["payload"]
    assert payload["verdict"] == "pass"
    assert payload["layer"] == "acceptance"
    assert payload["uncertainty"] == "provider outage is untested"


def test_refuses_done_with_failing_criterion_and_no_finding():
    request = _request(
        criteria=[
            {
                "criterion_id": "rec-ac1",
                "result": "fail",
                "method": "check",
                "revision": "abc123",
                "signed_by": "",
            }
        ]
    )
    with pytest.raises(close_batch.CloseRefused):
        close_batch.build_batch(request)


def test_refuses_done_with_a_criterion_never_checked_at_all():
    request = _request(
        acceptance_ids=["rec-ac1", "rec-ac2"],
        criteria=[
            {
                "criterion_id": "rec-ac1",
                "result": "pass",
                "method": "tdd",
                "revision": "abc123",
                "signed_by": "",
            }
        ],
    )
    with pytest.raises(close_batch.CloseRefused):
        close_batch.build_batch(request)


def test_withdrawn_does_not_require_a_finding_for_a_failing_criterion():
    request = _request(
        transition="withdrawn",
        criteria=[
            {
                "criterion_id": "rec-ac1",
                "result": "fail",
                "method": "check",
                "revision": "abc123",
                "signed_by": "",
            }
        ],
    )
    ops = close_batch.build_batch(request)
    assert ops[-1]["transition"] == "withdrawn"


def test_finding_permits_the_close_and_needs_is_forced_to_human():
    request = _request(
        criteria=[
            {
                "criterion_id": "rec-ac1",
                "result": "fail",
                "method": "check",
                "revision": "abc123",
                "signed_by": "",
            }
        ],
        finding={
            "claim": "closed with a known gap",
            "basis": "deferred deliberately",
            "invalidated_when": "when re-verified",
            "needs": "none",  # deliberately wrong -- the script must override this
            "body": "## Evidence\n\nx\n\n## Consequence\n\ny\n\n## Follow-up\n\nz",
        },
    )
    ops = close_batch.build_batch(request)
    finding_op = next(op for op in ops if op["type"] == "project:finding")
    assert finding_op["payload"]["needs"] == "human"
    assert ops[-1]["op"] == "update" and ops[-1]["transition"] == "done"


def test_no_execution_report_omits_the_second_informed_by():
    ops = close_batch.build_batch(_request(execution_report_id=None))
    assert ops[0]["rel"] == ["informed_by:rec-ac1"]


def test_criteria_entry_outside_acceptance_ids_is_malformed():
    request = _request(
        criteria=[
            {
                "criterion_id": "rec-not-active",
                "result": "pass",
                "method": "tdd",
                "revision": "abc",
                "signed_by": "",
            }
        ]
    )
    with pytest.raises(close_batch.CloseRequestError):
        close_batch.build_batch(request)


def test_missing_top_level_field_is_malformed_not_refused():
    request = _request()
    del request["work_item_id"]
    with pytest.raises(close_batch.CloseRequestError):
        close_batch.build_batch(request)


# -- CLI wrapper: exit codes and output-file behavior ------------------


def test_cli_refusal_exits_2_prints_why_and_writes_no_file(tmp_path):
    request = _request(
        criteria=[
            {
                "criterion_id": "rec-ac1",
                "result": "fail",
                "method": "check",
                "revision": "abc123",
                "signed_by": "",
            }
        ]
    )
    result, out_path = _run_script(request, tmp_path)
    assert result.returncode == 2
    assert "rec-ac1" in result.stderr
    assert not out_path.exists()


def test_cli_success_exits_0_and_writes_ndjson(tmp_path):
    result, out_path = _run_script(_request(), tmp_path)
    assert result.returncode == 0, result.stderr
    lines = out_path.read_text().splitlines()
    assert len(lines) == 2
    ops = [json.loads(line) for line in lines]
    assert [op["op"] for op in ops] == ["create", "update"]


def test_cli_malformed_json_exits_1(tmp_path):
    input_path = tmp_path / "close-request.json"
    input_path.write_text("{not json")
    out_path = tmp_path / "close-batch.ndjson"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(input_path), "--out", str(out_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert not out_path.exists()


# -- end to end against the real CLI -----------------------------------


def _build_work_item_family(cli, defs, subject: str, effort: str):
    phase = h.create_generic_record(cli, defs, "project:phase", extra_payload={"effort": effort})
    work_item = h.create_generic_record(
        cli,
        defs,
        "project:work-item",
        subject=subject,
        extra_payload={"effort": effort, "phase": phase["subject"], "kind": "deliver"},
    )
    work_item = h._apply_transition(
        cli, defs["project:work-item"], "project:work-item", work_item, "in_progress"
    )
    acceptance = h.create_generic_record(
        cli,
        defs,
        "project:acceptance",
        subject=subject,
        extra_payload={"effort": effort, "phase": phase["subject"], "method": "tdd"},
    )
    assignment = h.create_generic_record(
        cli,
        defs,
        "project:assignment",
        subject=subject,
        extra_payload={"effort": effort, "work_item": subject},
    )
    execution_report = h.create_generic_record(
        cli,
        defs,
        "project:execution-report",
        subject=subject,
        extra_payload={
            "work_item": subject,
            "assignment": assignment["subject"],
            "result": "pass",
            "verdict": "pass",
            "revision": "deadbeef",
        },
    )
    return work_item, acceptance, execution_report


def test_end_to_end_all_pass_closes_the_work_item_to_done(cli, resolved_contract, tmp_path):
    defs = h.record_defs_by_id(resolved_contract)
    subject = "demo-close-task"
    effort = "demo-effort"
    work_item, acceptance, execution_report = _build_work_item_family(cli, defs, subject, effort)

    request = {
        "subject": subject,
        "effort": effort,
        "work_item_id": work_item["id"],
        "transition": "done",
        "execution_report_id": execution_report["id"],
        "acceptance_ids": [acceptance["id"]],
        "criteria": [
            {
                "criterion_id": acceptance["id"],
                "result": "pass",
                "method": "tdd",
                "revision": "deadbeef",
                "signed_by": "",
            }
        ],
        "finding": None,
    }
    result, out_path = _run_script(request, tmp_path)
    assert result.returncode == 0, result.stderr

    apply_result = cli("apply", str(out_path))
    assert apply_result.returncode == 0, apply_result.stdout + apply_result.stderr
    applied = json.loads(apply_result.stdout)
    assert applied["ok"] is True
    assert applied["applied"] == 2
    assert applied["failed"] == 0

    final_work_item = json.loads(cli("get", "--type", "project:work-item", "--id", work_item["id"]).stdout)
    assert final_work_item["lifecycle_state"] == "done"

    check_runs = json.loads(
        cli("list", "--type", "project:check-run", "--subject", subject, "--full").stdout
    )["records"]
    assert len(check_runs) == 1
    check_run = check_runs[0]
    assert check_run["payload"]["result"] == "pass"
    assert sorted(check_run["relationships"]["informed_by"]) == sorted(
        [acceptance["id"], execution_report["id"]]
    )


def test_end_to_end_refusal_leaves_the_work_item_in_progress(cli, resolved_contract, tmp_path):
    defs = h.record_defs_by_id(resolved_contract)
    subject = "demo-refuse-task"
    effort = "demo-effort"
    work_item, acceptance, execution_report = _build_work_item_family(cli, defs, subject, effort)

    request = {
        "subject": subject,
        "effort": effort,
        "work_item_id": work_item["id"],
        "transition": "done",
        "execution_report_id": execution_report["id"],
        "acceptance_ids": [acceptance["id"]],
        "criteria": [
            {
                "criterion_id": acceptance["id"],
                "result": "fail",
                "method": "check",
                "revision": "deadbeef",
                "signed_by": "",
            }
        ],
        "finding": None,
    }
    result, out_path = _run_script(request, tmp_path)
    assert result.returncode == 2
    assert not out_path.exists()

    # Nothing to apply -- following the skill's instructions, `apply` is
    # never invoked, so the work-item must still be sitting in_progress.
    final_work_item = json.loads(cli("get", "--type", "project:work-item", "--id", work_item["id"]).stdout)
    assert final_work_item["lifecycle_state"] == "in_progress"

    check_runs = json.loads(
        cli("list", "--type", "project:check-run", "--subject", subject, "--full").stdout
    )["records"]
    assert check_runs == []


def test_end_to_end_failing_criterion_with_finding_closes_and_surfaces_needs_human(
    cli, resolved_contract, tmp_path
):
    defs = h.record_defs_by_id(resolved_contract)
    subject = "demo-deferred-task"
    effort = "demo-effort"
    work_item, acceptance, execution_report = _build_work_item_family(cli, defs, subject, effort)

    request = {
        "subject": subject,
        "effort": effort,
        "work_item_id": work_item["id"],
        "transition": "done",
        "execution_report_id": execution_report["id"],
        "acceptance_ids": [acceptance["id"]],
        "criteria": [
            {
                "criterion_id": acceptance["id"],
                "result": "fail",
                "method": "check",
                "revision": "deadbeef",
                "signed_by": "",
            }
        ],
        "finding": {
            "claim": f"{subject} closed done with an unmet or unverified criterion",
            "basis": "live verification deliberately deferred",
            "invalidated_when": "the criterion is re-run and passes",
            "body": "## Evidence\n\nthe check-run above\n\n## Consequence\n\nunverified in prod\n\n## Follow-up\n\nre-run before next release",
        },
    }
    result, out_path = _run_script(request, tmp_path)
    assert result.returncode == 0, result.stderr

    apply_result = cli("apply", str(out_path))
    assert apply_result.returncode == 0, apply_result.stdout + apply_result.stderr
    applied = json.loads(apply_result.stdout)
    assert applied["applied"] == 3

    final_work_item = json.loads(cli("get", "--type", "project:work-item", "--id", work_item["id"]).stdout)
    assert final_work_item["lifecycle_state"] == "done"

    findings = json.loads(
        cli("list", "--type", "project:finding", "--subject", subject, "--full").stdout
    )["records"]
    assert len(findings) == 1
    assert findings[0]["payload"]["needs"] == "human"
