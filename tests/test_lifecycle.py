"""State transitions for the evidence-driven lifecycle.

These tests drive lifecycle.loop directly. They do not stand in for the
store: record shapes are covered separately.
"""

from __future__ import annotations

import pytest

from lifecycle.loop import (
    MAX_REPAIRS,
    Chain,
    CriterionResult,
    LayerResult,
    LifecycleError,
    LoopState,
    TaskClaim,
    advance,
    apply_release_status,
    decisions_for_task,
    depth_for,
    diagnosis_action,
    evidence_for_requirement,
    failure_action,
    integrate_claims,
    judge,
    repair_history,
    requirements_for_task,
    requirements_without_evidence,
    uncertain_requirements,
)


def _walk(depth: str, *, parallel: bool = False, design_weight: str = "light") -> list[str]:
    state = LoopState(stage="intent", depth=depth, parallel=parallel, design_weight=design_weight)
    seen = [state.stage]
    for _ in range(12):
        kwargs = {}
        if state.stage == "integrate":
            kwargs["integration_verdict"] = "pass"
        elif state.stage == "verify":
            kwargs["verdict"] = "pass"
        state, step = advance(state, **kwargs)
        seen.append(state.stage)
        if step.stage == "release":
            break
    return seen


def test_full_happy_path_reaches_release_through_integration():
    assert _walk("full") == [
        "intent",
        "specify",
        "design",
        "plan",
        "execute",
        "integrate",
        "verify",
        "release",
    ]


def test_standard_serial_path_skips_integration():
    assert _walk("standard") == [
        "intent",
        "specify",
        "design",
        "plan",
        "execute",
        "verify",
        "release",
    ]


def test_standard_parallel_path_integrates_before_verify():
    assert _walk("standard", parallel=True) == [
        "intent",
        "specify",
        "design",
        "plan",
        "execute",
        "integrate",
        "verify",
        "release",
    ]


def test_trivial_path_skips_specification_design_plan_and_integration():
    assert _walk("trivial") == ["intent", "execute", "verify", "release"]


def test_skipped_design_is_a_step_not_a_missing_record_of_the_decision():
    state, step = advance(LoopState(stage="design", design_weight="skipped"))
    assert state.stage == "plan"
    assert step.skipped is True
    assert step.reason == "design skipped"


def test_depth_defaults_keep_incidental_work_trivial_and_delivery_standard():
    assert depth_for("incidental") == "trivial"
    assert depth_for("deliver", trivial=True) == "trivial"
    assert depth_for("deliver") == "standard"
    assert depth_for("repair") == "standard"
    assert depth_for("incidental", requested="full") == "full"


def test_failure_path_repairs_through_integration_then_passes():
    state = LoopState(stage="verify", depth="full", parallel=True)
    state, step = advance(state, verdict="fail", failure_signature="oauth-401")
    assert step.stage == "diagnose"
    assert state.diagnosis is None
    assert state.failure_signatures == ("oauth-401",)

    state, step = advance(state, diagnosis="token check runs outside the session", diagnosis_written=True)
    assert step.stage == "repair"
    assert step.reason == "diagnosis recorded"
    assert state.repair_attempts == 1

    state, step = advance(state)
    assert state.stage == "integrate"
    assert step.reason == "repair returns through integration"

    state, step = advance(state, integration_verdict="pass")
    assert state.stage == "verify"

    state, step = advance(state, verdict="pass")
    assert state.stage == "release"
    assert step.reason == "evidence is sufficient"
    assert state.release_status == "ready_to_merge"


def test_repeated_failure_escalates_without_another_repair():
    state = LoopState(stage="verify", depth="full")
    state, _ = advance(state, verdict="fail", failure_signature="same")
    state, _ = advance(state, diagnosis="boundary is wrong", diagnosis_written=True)
    state, _ = advance(state)
    state, _ = advance(state, integration_verdict="pass")
    state, step = advance(state, verdict="fail", failure_signature="same")
    assert step.escalated is True
    assert step.reason == "repeated failure"
    assert state.stage == "verify"
    assert state.repair_attempts == 1


def test_distinct_failures_stop_at_the_repair_limit():
    state = LoopState(stage="verify", depth="standard", max_repairs=MAX_REPAIRS)
    for index in range(MAX_REPAIRS):
        state, step = advance(state, verdict="fail", failure_signature=f"sig-{index}")
        assert step.stage == "diagnose"
        state, step = advance(state, diagnosis=f"cause {index}", diagnosis_written=True)
        assert step.stage == "repair"
        state, _ = advance(state)
        state, _ = advance(state, integration_verdict="pass")
    state, step = advance(state, verdict="fail", failure_signature="sig-new")
    assert step.escalated is True
    assert step.reason == "repair limit"
    assert state.repair_attempts == MAX_REPAIRS


def test_unresolved_diagnosis_does_not_repair():
    state = LoopState(stage="diagnose", depth="full")
    state, waiting = advance(state)
    assert waiting.stage == "diagnose"
    assert waiting.reason == "diagnosis has not been written"
    assert diagnosis_action(None) == "wait"

    state, step = advance(state, diagnosis="unresolved", diagnosis_written=True)
    assert step.escalated is True
    assert step.reason == "unresolved diagnosis"
    assert state.stage == "diagnose"
    assert state.repair_attempts == 0


def test_blocked_and_unknown_do_not_enter_the_repair_loop():
    blocked, blocked_step = advance(LoopState(stage="verify"), verdict="blocked")
    assert blocked.stage == "verify"
    assert blocked_step.escalated is False
    assert blocked_step.reason == "verification blocked"

    unknown, unknown_step = advance(LoopState(stage="verify"), verdict="unknown")
    assert unknown.stage == "verify"
    assert unknown_step.reason == "insufficient evidence"


def test_passing_checks_with_open_uncertainty_do_not_release():
    state = LoopState(stage="verify", uncertainties=("oauth-provider-down",))
    state, step = advance(state, verdict="pass")
    assert state.stage == "verify"
    assert step.reason == "insufficient evidence"

    state, step = advance(state, verdict="pass", accept_uncertainty="oauth-provider-down")
    assert state.stage == "release"
    assert state.uncertainties == ()
    assert state.accepted_uncertainties == ("oauth-provider-down",)


def test_release_does_not_deploy_until_asked_and_monitor_waits_for_success():
    state, step = advance(LoopState(stage="release", release_status="ready_to_merge"))
    assert state.stage == "release"
    assert step.reason == "verified is not deployed"

    state, step = advance(state, follow="deploy")
    assert state.stage == "deploy"
    assert step.reason == "deployment initiated"

    state, step = advance(state, follow="monitor")
    assert state.stage == "deploy"
    assert step.reason == "deployment has not succeeded"

    state, step = advance(state, follow="monitor", release_status="deployment_succeeded")
    assert state.stage == "monitor"

    state, step = advance(state, follow="feedback")
    assert state.stage == "feedback"

    state, step = advance(state, follow="new_work")
    assert state.stage == "intent"
    assert state.repair_attempts == 0
    assert state.failure_signatures == ()
    assert step.reason == "feedback became new work"


def test_release_status_machine_rejects_deploying_a_verification():
    assert apply_release_status(None, "ready") == "ready_to_merge"
    assert apply_release_status("ready_to_merge", "merge") == "merged"
    assert apply_release_status("merged", "artifact") == "artifact_produced"
    assert apply_release_status("artifact_produced", "deploy") == "deployment_initiated"
    assert apply_release_status("deployment_initiated", "succeed") == "deployment_succeeded"
    assert apply_release_status("deployment_initiated", "fail") == "deployment_failed"
    with pytest.raises(LifecycleError):
        apply_release_status("ready_to_merge", "succeed")
    with pytest.raises(LifecycleError):
        apply_release_status(None, "deploy")


def test_unit_pass_without_the_required_acceptance_layer_is_unknown():
    evidence = judge(
        [CriterionResult("oauth", (LayerResult("unit", "pass"),))],
        required_layers={"oauth": ("acceptance",)},
    )
    assert evidence.by_criterion["oauth"] == "unknown"
    assert evidence.verdict == "unknown"
    assert evidence.quality == "insufficient"


def test_passed_layers_plus_an_open_uncertainty_are_not_sufficient():
    evidence = judge(
        [
            CriterionResult(
                "link",
                (LayerResult("acceptance", "pass"), LayerResult("unit", "pass")),
                uncertainties=("provider outage",),
            )
        ],
        required_layers={"link": ("acceptance",)},
    )
    assert evidence.verdict == "pass"
    assert evidence.quality == "insufficient"
    assert evidence.uncertainties == ("provider outage",)


def test_failure_dominates_a_sibling_pass():
    evidence = judge(
        [
            CriterionResult("ok", (LayerResult("unit", "pass"),)),
            CriterionResult("bad", (LayerResult("unit", "fail"),)),
        ]
    )
    assert evidence.verdict == "fail"
    assert evidence.quality == "failing"


def test_parallel_claims_conflict_after_a_clean_merge_and_can_be_reconciled():
    conflict = integrate_claims(
        (
            TaskClaim("A", {"Auth.login": "token"}),
            TaskClaim("B", {"Auth.login": "session"}, assumptions=("operation Y runs inside the transaction",)),
            TaskClaim("C", {"Auth.login": "token"}, assumptions=("not operation Y runs inside the transaction",)),
        ),
        git_merged=True,
    )
    assert conflict.git_merged is True
    assert conflict.verdict == "fail"
    assert any("Auth.login" in item for item in conflict.conflicts)
    assert any("operation Y" in item for item in conflict.conflicts)

    state = LoopState(stage="integrate", depth="full", parallel=True)
    state, step = advance(state, integration_verdict=conflict.verdict, failure_signature=conflict.conflicts[0])
    assert step.stage == "diagnose"
    state, _ = advance(state, diagnosis="B issued a session while A and C issued a token", diagnosis_written=True)
    state, _ = advance(state)
    assert state.stage == "integrate"

    reconciled = integrate_claims(
        (
            TaskClaim("A", {"Auth.login": "token"}, assumptions=("operation Y runs inside the transaction",)),
            TaskClaim("B", {"Auth.login": "token"}, assumptions=("operation Y runs inside the transaction",)),
            TaskClaim("C", {"Auth.login": "token"}, assumptions=("operation Y runs inside the transaction",)),
        ),
        git_merged=True,
    )
    assert reconciled.verdict == "pass"
    state, _ = advance(state, integration_verdict="pass")
    evidence = judge(
        [
            CriterionResult("login", (LayerResult("integration", "pass"), LayerResult("acceptance", "pass"))),
        ],
        required_layers={"login": ("acceptance",)},
    )
    assert evidence.quality == "sufficient"
    state, step = advance(state, verdict=evidence.verdict)
    assert state.stage == "release"
    assert step.reason == "evidence is sufficient"


def test_git_merge_without_claims_is_unknown():
    result = integrate_claims((), git_merged=True)
    assert result.git_merged is True
    assert result.verdict == "unknown"


def test_traceability_names_gaps_decisions_and_repairs():
    chain = Chain(
        requirements={"auth": "Add authentication"},
        criteria={"oauth": "auth", "link": "auth", "expiry": "auth"},
        decisions={"use-oauth": ("auth",)},
        tasks={"issue-token": ("oauth", "expiry"), "link-identity": ("link",)},
        task_decisions={"issue-token": ("use-oauth",), "link-identity": ()},
        evidence={"oauth": "pass", "link": "unknown"},
        repairs={"issue-token": ("check ran outside the transaction",)},
    )
    assert requirements_for_task(chain, "issue-token") == ["auth"]
    assert evidence_for_requirement(chain, "auth") == [
        ("oauth", "pass"),
        ("link", "unknown"),
        ("expiry", None),
    ]
    assert requirements_without_evidence(chain) == ["auth"]
    assert uncertain_requirements(chain) == ["auth"]
    assert decisions_for_task(chain, "issue-token") == ["use-oauth"]
    assert repair_history(chain, "issue-token") == ("check ran outside the transaction",)
    assert failure_action(attempts=0, signature="x", prior_signatures=()) == "diagnose"
    assert failure_action(attempts=0, signature="x", prior_signatures=("x",)) == "escalate_repeat"
    assert failure_action(attempts=3, signature="y", prior_signatures=()) == "escalate_limit"


def test_unknown_follow_and_verdict_are_rejected():
    with pytest.raises(LifecycleError):
        advance(LoopState(stage="verify"), follow="deploy")
    with pytest.raises(LifecycleError):
        advance(LoopState(stage="verify"), verdict="maybe")
