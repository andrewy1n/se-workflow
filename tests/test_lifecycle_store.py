"""The lifecycle records round-trip through the public CLI.

Backward-compatible creates omit the new optional fields and still validate.
"""

from __future__ import annotations

import json

import pytest

import helpers as h


def test_trace_chain_validates_and_old_work_items_still_create(cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    phase = h.create_generic_record(
        cli, defs, "project:phase", subject="life-phase",
        extra_payload={"title": "Lifecycle", "ordinal": 1, "effort": "life"},
    )
    spec = h.create_generic_record(
        cli, defs, "project:specification", subject="spec-life-phase",
        extra_payload={"summary": "OAuth", "weight": "full", "phase": phase["subject"], "effort": "life"},
    )
    acceptance = h.create_generic_record(
        cli, defs, "project:acceptance", subject="spec-life-phase-oauth",
        extra_payload={
            "criterion": "Unauthenticated requests return 401",
            "method": "check",
            "phase": phase["subject"],
            "effort": "life",
            "verify_command": "pytest tests/test_oauth.py",
            "specification": spec["subject"],
        },
    )
    design = h.create_generic_record(
        cli, defs, "project:design", subject="design-life-phase",
        extra_payload={
            "summary": "Token session",
            "weight": "light",
            "phase": phase["subject"],
            "effort": "life",
            "specification": spec["subject"],
        },
    )
    h.create_generic_record(
        cli, defs, "project:decision", subject="use-token",
        extra_payload={
            "choice": "token",
            "alternatives": "session",
            "phase": phase["subject"],
            "effort": "life",
            "serves": acceptance["subject"],
        },
    )
    item = h.create_generic_record(
        cli, defs, "project:work-item", subject="issue-token",
        extra_payload={
            "title": "Issue token",
            "phase": phase["subject"],
            "kind": "deliver",
            "assignee": "",
            "effort": "life",
            "satisfies": acceptance["subject"],
            "design": design["subject"],
        },
    )
    h.create_generic_record(
        cli, defs, "project:check-run", subject="issue-token",
        extra_payload={
            "criterion_id": acceptance["id"],
            "revision": "abc",
            "result": "pass",
            "effort": "life",
            "method": "check",
            "signed_by": "",
            "verdict": "unknown",
            "layer": "unit",
            "uncertainty": "provider outage is untested",
        },
    )
    uncertainty = h.create_generic_record(
        cli, defs, "project:uncertainty", subject="issue-token-provider",
        extra_payload={
            "statement": "provider outage is untested",
            "effort": "life",
            "status": "open",
            "criterion_id": acceptance["id"],
        },
    )
    h.create_generic_record(
        cli, defs, "project:integration-report", subject="integrate-life-phase",
        extra_payload={
            "phase": phase["subject"],
            "effort": "life",
            "verdict": "fail",
            "revision": "abc",
            "summary": "Auth.login disagreed",
        },
    )
    h.create_generic_record(
        cli, defs, "project:repair-attempt", subject="issue-token",
        extra_payload={
            "work_item": item["subject"],
            "effort": "life",
            "attempt": "1",
            "failure_signature": "Auth.login",
            "outcome": "failed_again",
            "diagnosis": "B issued a session",
        },
    )
    h.create_generic_record(
        cli, defs, "project:release", subject="release-life-phase",
        extra_payload={
            "phase": phase["subject"],
            "effort": "life",
            "status": "ready_to_merge",
            "note": "verified, not deployed",
        },
    )
    h.create_generic_record(
        cli, defs, "project:feedback", subject="oauth-500",
        extra_payload={
            "source": "log",
            "kind": "error",
            "summary": "token endpoint 500s",
            "effort": "life",
        },
    )

    # Pre-lifecycle shape: no satisfies, design, specification, verdict, or depth.
    h.create_generic_record(
        cli, defs, "project:work-item", subject="old-task",
        extra_payload={
            "title": "Old task",
            "phase": phase["subject"],
            "kind": "deliver",
            "assignee": "",
            "effort": "life",
            "satisfies": "",
            "design": "",
        },
    )
    bare = cli(
        "create", "--type", "project:acceptance", "--subject", "old-acceptance",
        "--payload", json.dumps({
            "criterion": "it builds",
            "method": "check",
            "phase": phase["subject"],
            "effort": "life",
            "verify_command": "pytest",
        }),
    )
    assert bare.returncode == 0, bare.stdout + bare.stderr

    result = cli("validate")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "valid"

    view = cli("view", "--id", "project:lifecycle")
    assert view.returncode == 0, view.stdout + view.stderr
    assert "spec-life-phase" in view.stdout
    assert "design-life-phase" in view.stdout
    assert "issue-token-provider" in view.stdout
    assert "release-life-phase" in view.stdout

    accepted = cli(
        "supersede", "--type", "project:uncertainty", "--id", uncertainty["id"],
        "--expected-revision", uncertainty["revision"],
        "--payload", json.dumps({"status": "accepted"}),
    )
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    again = cli("view", "--id", "project:lifecycle")
    assert "issue-token-provider" not in again.stdout

    rejected = cli(
        "create", "--type", "project:check-run", "--subject", "bad-verdict",
        "--payload", json.dumps({
            "criterion_id": acceptance["id"],
            "revision": "abc",
            "result": "pass",
            "effort": "life",
            "method": "check",
            "signed_by": "",
            "verdict": "yes",
        }),
    )
    assert rejected.returncode != 0


def test_skipped_design_record_is_a_real_record(cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    phase = h.create_generic_record(
        cli, defs, "project:phase", subject="skip-phase",
        extra_payload={"title": "Skip", "ordinal": 1, "effort": "skip"},
    )
    record = h.create_generic_record(
        cli, defs, "project:design", subject="design-skip-phase",
        extra_payload={
            "summary": "no new interface",
            "weight": "skipped",
            "phase": phase["subject"],
            "effort": "skip",
            "specification": "",
        },
    )
    assert record["payload"]["weight"] == "skipped"
    result = cli("validate")
    assert result.returncode == 0, result.stdout + result.stderr
