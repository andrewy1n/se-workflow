"""Stage transitions, evidence, integration, repair limits, and traceability.

A passing test is not proof the specification holds. A clean git merge is
not semantic integration. Verified is not deployed. Repair does not run
without a diagnosis, and it does not repeat a failure without a limit.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Mapping

STAGES = (
    "intent",
    "specify",
    "design",
    "plan",
    "execute",
    "integrate",
    "verify",
    "diagnose",
    "repair",
    "release",
    "deploy",
    "monitor",
    "feedback",
)

DEPTHS = ("trivial", "standard", "full")
VERDICTS = ("pass", "fail", "blocked", "unknown")
LAYERS = (
    "build",
    "unit",
    "integration",
    "acceptance",
    "static",
    "types",
    "security",
    "regression",
    "design",
    "behavior",
)
RELEASE_STATUSES = (
    "ready_to_merge",
    "merged",
    "artifact_produced",
    "deployment_initiated",
    "deployment_succeeded",
    "deployment_failed",
)
MAX_REPAIRS = 3
UNRESOLVED = "unresolved"

_RELEASE_EVENTS = {
    None: {"ready": "ready_to_merge"},
    "ready_to_merge": {"merge": "merged"},
    "merged": {"artifact": "artifact_produced", "deploy": "deployment_initiated"},
    "artifact_produced": {"deploy": "deployment_initiated"},
    "deployment_initiated": {"succeed": "deployment_succeeded", "fail": "deployment_failed"},
    "deployment_failed": {"deploy": "deployment_initiated"},
    "deployment_succeeded": {},
}

_FOLLOW = {
    "release": {"deploy"},
    "deploy": {"monitor"},
    "monitor": {"feedback"},
    "feedback": {"new_work"},
}


class LifecycleError(ValueError):
    """A stage, verdict, or release event the lifecycle does not define."""


@dataclass(frozen=True)
class LoopState:
    stage: str
    depth: str = "standard"
    parallel: bool = False
    verdict: str | None = None
    integration_verdict: str | None = None
    design_weight: str = "light"
    repair_attempts: int = 0
    failure_signatures: tuple[str, ...] = ()
    diagnosis: str | None = None
    uncertainties: tuple[str, ...] = ()
    accepted_uncertainties: tuple[str, ...] = ()
    max_repairs: int = MAX_REPAIRS
    release_status: str | None = None

    def __post_init__(self) -> None:
        if self.stage not in STAGES:
            raise LifecycleError(f"unknown stage {self.stage!r}")
        if self.depth not in DEPTHS:
            raise LifecycleError(f"unknown depth {self.depth!r}")
        if self.verdict is not None and self.verdict not in VERDICTS:
            raise LifecycleError(f"unknown verdict {self.verdict!r}")
        if self.integration_verdict is not None and self.integration_verdict not in VERDICTS:
            raise LifecycleError(f"unknown integration verdict {self.integration_verdict!r}")
        if self.design_weight not in ("light", "full", "skipped"):
            raise LifecycleError(f"unknown design weight {self.design_weight!r}")
        if self.release_status is not None and self.release_status not in RELEASE_STATUSES:
            raise LifecycleError(f"unknown release status {self.release_status!r}")
        if self.max_repairs < 1:
            raise LifecycleError("max_repairs must be at least 1")


@dataclass(frozen=True)
class Step:
    stage: str
    reason: str
    escalated: bool = False
    skipped: bool = False


def depth_for(kind: str, *, requested: str | None = None, trivial: bool = False) -> str:
    """Pick a depth. An explicit request wins. Incidental and trivial work stay short."""
    if requested in DEPTHS:
        return requested
    if kind == "incidental" or trivial:
        return "trivial"
    return "standard"


def failure_action(
    *,
    attempts: int,
    signature: str | None,
    prior_signatures: Iterable[str],
    max_repairs: int = MAX_REPAIRS,
) -> str:
    """What a verification or integration failure may do next.

    Returns ``diagnose``, ``escalate_limit``, or ``escalate_repeat``.
    """
    if attempts >= max_repairs:
        return "escalate_limit"
    if signature and signature in tuple(prior_signatures):
        return "escalate_repeat"
    return "diagnose"


def diagnosis_action(diagnosis: str | None) -> str:
    """What a diagnosis allows. Observation of a failure is not a diagnosis.

    Returns ``wait``, ``escalate_unresolved``, or ``repair``.
    """
    if diagnosis is None:
        return "wait"
    if diagnosis == "" or diagnosis == UNRESOLVED:
        return "escalate_unresolved"
    return "repair"


def _needs_integrate(state: LoopState) -> bool:
    return state.depth == "full" or (state.depth == "standard" and state.parallel)


def _stay(state: LoopState, reason: str, *, escalated: bool = False) -> tuple[LoopState, Step]:
    return state, Step(state.stage, reason, escalated=escalated)


def _fail(state: LoopState, *, signature: str | None, reason: str) -> tuple[LoopState, Step]:
    action = failure_action(
        attempts=state.repair_attempts,
        signature=signature,
        prior_signatures=state.failure_signatures,
        max_repairs=state.max_repairs,
    )
    if action == "escalate_limit":
        return _stay(state, "repair limit", escalated=True)
    if action == "escalate_repeat":
        return _stay(state, "repeated failure", escalated=True)
    signatures = state.failure_signatures
    if signature and signature not in signatures:
        signatures = signatures + (signature,)
    diagnosed = replace(
        state,
        stage="diagnose",
        failure_signatures=signatures,
        diagnosis=None,
        verdict=None,
        integration_verdict=None,
    )
    return diagnosed, Step("diagnose", reason)


def advance(
    state: LoopState,
    *,
    verdict: str | None = None,
    integration_verdict: str | None = None,
    diagnosis: str | None = None,
    failure_signature: str | None = None,
    accept_uncertainty: str | None = None,
    follow: str | None = None,
    design_weight: str | None = None,
    release_status: str | None = None,
    diagnosis_written: bool = False,
) -> tuple[LoopState, Step]:
    """Take one step. Each call leaves at most one stage behind.

    Pass ``diagnosis_written=True`` when ``diagnosis`` is intentionally set,
    including to ``unresolved``. Omitting it leaves the previous diagnosis.
    """
    updates: dict = {}
    if verdict is not None:
        if verdict not in VERDICTS:
            raise LifecycleError(f"unknown verdict {verdict!r}")
        updates["verdict"] = verdict
    if integration_verdict is not None:
        if integration_verdict not in VERDICTS:
            raise LifecycleError(f"unknown integration verdict {integration_verdict!r}")
        updates["integration_verdict"] = integration_verdict
    if diagnosis_written:
        updates["diagnosis"] = diagnosis
    if design_weight is not None:
        if design_weight not in ("light", "full", "skipped"):
            raise LifecycleError(f"unknown design weight {design_weight!r}")
        updates["design_weight"] = design_weight
    if release_status is not None:
        if release_status not in RELEASE_STATUSES:
            raise LifecycleError(f"unknown release status {release_status!r}")
        updates["release_status"] = release_status
    if accept_uncertainty is not None:
        if accept_uncertainty not in state.uncertainties:
            raise LifecycleError(f"unknown uncertainty {accept_uncertainty!r}")
        updates["uncertainties"] = tuple(
            item for item in state.uncertainties if item != accept_uncertainty
        )
        updates["accepted_uncertainties"] = state.accepted_uncertainties + (accept_uncertainty,)
    if updates:
        state = replace(state, **updates)

    if follow is not None:
        allowed = _FOLLOW.get(state.stage, set())
        if follow not in allowed:
            raise LifecycleError(f"cannot follow {follow!r} from {state.stage}")

    if state.stage == "intent":
        if state.depth == "trivial":
            return replace(state, stage="execute"), Step(
                "execute",
                "trivial depth skips specification, design, plan, and integration",
            )
        return replace(state, stage="specify"), Step("specify", "intent needs a specification")

    if state.stage == "specify":
        return replace(state, stage="design"), Step("design", "specification is ready for design")

    if state.stage == "design":
        if state.design_weight == "skipped":
            return replace(state, stage="plan"), Step("plan", "design skipped", skipped=True)
        return replace(state, stage="plan"), Step("plan", "design is ready to plan")

    if state.stage == "plan":
        return replace(state, stage="execute"), Step("execute", "plan is ready to execute")

    if state.stage == "execute":
        if _needs_integrate(state):
            return replace(state, stage="integrate", integration_verdict=None), Step(
                "integrate", "execution needs a semantic integration checkpoint"
            )
        return replace(state, stage="verify", verdict=None), Step(
            "verify", "serial standard or trivial work skips integration"
        )

    if state.stage == "integrate":
        if state.integration_verdict is None:
            return _stay(state, "integration has no verdict")
        if state.integration_verdict == "pass":
            return replace(state, stage="verify", verdict=None), Step(
                "verify", "integration passed"
            )
        if state.integration_verdict == "fail":
            return _fail(state, signature=failure_signature, reason="integration failed")
        if state.integration_verdict == "blocked":
            return _stay(state, "integration blocked")
        return _stay(state, "insufficient evidence")

    if state.stage == "verify":
        if state.verdict is None:
            return _stay(state, "verification has no verdict")
        if state.verdict == "blocked":
            return _stay(state, "verification blocked")
        if state.verdict == "unknown":
            return _stay(state, "insufficient evidence")
        if state.verdict == "fail":
            return _fail(state, signature=failure_signature, reason="verification failed")
        if state.uncertainties:
            return _stay(state, "insufficient evidence")
        status = state.release_status or "ready_to_merge"
        return replace(state, stage="release", release_status=status), Step(
            "release", "evidence is sufficient"
        )

    if state.stage == "diagnose":
        action = diagnosis_action(state.diagnosis)
        if action == "wait":
            return _stay(state, "diagnosis has not been written")
        if action == "escalate_unresolved":
            return _stay(state, "unresolved diagnosis", escalated=True)
        return replace(state, stage="repair", repair_attempts=state.repair_attempts + 1), Step(
            "repair", "diagnosis recorded"
        )

    if state.stage == "repair":
        if state.depth == "trivial":
            return replace(state, stage="verify", verdict=None), Step(
                "verify", "trivial repair returns to verification"
            )
        return replace(state, stage="integrate", integration_verdict=None, verdict=None), Step(
            "integrate", "repair returns through integration"
        )

    if state.stage == "release":
        if follow is None:
            return _stay(state, "verified is not deployed")
        return replace(state, stage="deploy"), Step("deploy", "deployment initiated")

    if state.stage == "deploy":
        if follow is None:
            return _stay(state, "deployment is not being watched")
        if state.release_status != "deployment_succeeded":
            return _stay(state, "deployment has not succeeded")
        return replace(state, stage="monitor"), Step("monitor", "watching a succeeded deployment")

    if state.stage == "monitor":
        if follow is None:
            return _stay(state, "no feedback")
        return replace(state, stage="feedback"), Step("feedback", "runtime signal received")

    if follow is None:
        return _stay(state, "feedback has not been taken up")
    fresh = LoopState(
        stage="intent",
        depth=state.depth,
        parallel=state.parallel,
        design_weight=state.design_weight,
        max_repairs=state.max_repairs,
    )
    return fresh, Step("intent", "feedback became new work")


def apply_release_status(status: str | None, event: str) -> str:
    """Move a release record's status. Deployment is not implied by verification."""
    if status is not None and status not in RELEASE_STATUSES:
        raise LifecycleError(f"unknown release status {status!r}")
    nxt = _RELEASE_EVENTS.get(status, {}).get(event)
    if nxt is None:
        raise LifecycleError(f"cannot {event} from release status {status!r}")
    return nxt


@dataclass(frozen=True)
class LayerResult:
    layer: str
    verdict: str

    def __post_init__(self) -> None:
        if self.layer not in LAYERS:
            raise LifecycleError(f"unknown layer {self.layer!r}")
        if self.verdict not in VERDICTS:
            raise LifecycleError(f"unknown verdict {self.verdict!r}")


@dataclass(frozen=True)
class CriterionResult:
    criterion_id: str
    layers: tuple[LayerResult, ...] = ()
    uncertainties: tuple[str, ...] = ()


@dataclass(frozen=True)
class Evidence:
    verdict: str
    quality: str
    by_criterion: dict[str, str]
    uncertainties: tuple[str, ...]


def _dominate(verdicts: Iterable[str]) -> str:
    found = tuple(verdicts)
    if not found:
        return "unknown"
    for verdict in ("fail", "blocked", "unknown"):
        if verdict in found:
            return verdict
    return "pass"


def judge(
    results: Iterable[CriterionResult],
    *,
    required_layers: Mapping[str, Iterable[str]] | None = None,
) -> Evidence:
    """Judge criteria from the layers the strategy required.

    A pass on some other layer does not satisfy a missing required layer.
    Open uncertainties keep quality ``insufficient`` even when every
    recorded layer passed.
    """
    required_layers = required_layers or {}
    results = tuple(results)
    by_criterion: dict[str, str] = {}
    uncertainties: list[str] = []
    for result in results:
        seen: dict[str, str] = {}
        for layer in result.layers:
            if layer.layer in seen:
                raise LifecycleError(f"duplicate layer {layer.layer!r} on {result.criterion_id}")
            seen[layer.layer] = layer.verdict
        missing = [name for name in required_layers.get(result.criterion_id, ()) if name not in seen]
        if any(verdict == "fail" for verdict in seen.values()):
            verdict = "fail"
        elif any(verdict == "blocked" for verdict in seen.values()):
            verdict = "blocked"
        elif missing or any(verdict == "unknown" for verdict in seen.values()) or not seen:
            verdict = "unknown"
        else:
            verdict = "pass"
        by_criterion[result.criterion_id] = verdict
        uncertainties.extend(result.uncertainties)
    overall = _dominate(by_criterion.values())
    if overall == "fail":
        quality = "failing"
    elif overall == "blocked":
        quality = "blocked"
    elif overall == "unknown" or uncertainties:
        quality = "insufficient"
    else:
        quality = "sufficient"
    return Evidence(overall, quality, by_criterion, tuple(uncertainties))


@dataclass(frozen=True)
class TaskClaim:
    task: str
    interfaces: dict[str, str]
    assumptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Integration:
    verdict: str
    git_merged: bool
    conflicts: tuple[str, ...]
    reason: str


def integrate_claims(claims: Iterable[TaskClaim], *, git_merged: bool = False) -> Integration:
    """Semantic integration. ``git_merged`` is recorded and does not grant a pass.

    Two claims conflict when they name the same interface with different
    descriptors, or when one assumption is ``not`` followed by another
    claim's assumption.
    """
    claims = tuple(claims)
    if not claims:
        return Integration("unknown", git_merged, (), "no task claims")
    conflicts: list[str] = []
    interfaces: dict[str, tuple[str, str]] = {}
    assumptions: list[tuple[str, str]] = []
    for claim in claims:
        for name, desc in claim.interfaces.items():
            prior = interfaces.get(name)
            if prior and prior[1] != desc:
                conflicts.append(
                    f"{name}: {prior[0]} claims {prior[1]!r} but {claim.task} claims {desc!r}"
                )
            elif prior is None:
                interfaces[name] = (claim.task, desc)
        for assumption in claim.assumptions:
            assumptions.append((claim.task, assumption))
    for task, assumption in assumptions:
        if not assumption.startswith("not "):
            continue
        negated = assumption[4:]
        for other_task, other in assumptions:
            if other_task != task and other == negated:
                conflicts.append(
                    f"{task} assumes {assumption!r} but {other_task} assumes {other!r}"
                )
    if conflicts:
        return Integration("fail", git_merged, tuple(conflicts), "semantic conflict")
    return Integration("pass", git_merged, (), "claims agree")


@dataclass(frozen=True)
class Chain:
    """Traceability across the lifecycle. Values are ids the caller chooses.

    ``criteria`` maps a criterion id to its requirement id.
    ``decisions`` maps a decision id to the requirement ids it serves.
    ``tasks`` maps a task id to the criterion ids it satisfies.
    ``task_decisions`` maps a task id to the decision ids it implements.
    ``evidence`` maps a criterion id to a verdict.
    ``repairs`` maps a task id to diagnosis strings, oldest first.
    """

    requirements: dict[str, str]
    criteria: dict[str, str]
    decisions: dict[str, tuple[str, ...]]
    tasks: dict[str, tuple[str, ...]]
    task_decisions: dict[str, tuple[str, ...]]
    evidence: dict[str, str]
    repairs: dict[str, tuple[str, ...]]


def _requirement_criteria(chain: Chain, requirement: str) -> list[str]:
    return [criterion for criterion, owner in chain.criteria.items() if owner == requirement]


def requirements_for_task(chain: Chain, task: str) -> list[str]:
    owners = []
    for criterion in chain.tasks.get(task, ()):
        owner = chain.criteria.get(criterion)
        if owner and owner not in owners:
            owners.append(owner)
    return owners


def evidence_for_requirement(chain: Chain, requirement: str) -> list[tuple[str, str | None]]:
    return [
        (criterion, chain.evidence.get(criterion))
        for criterion in _requirement_criteria(chain, requirement)
    ]


def requirements_without_evidence(chain: Chain) -> list[str]:
    missing = []
    for requirement in chain.requirements:
        rows = evidence_for_requirement(chain, requirement)
        if not rows or any(verdict is None for _, verdict in rows):
            missing.append(requirement)
    return missing


def uncertain_requirements(chain: Chain) -> list[str]:
    """Requirements with no evidence, or evidence whose verdict is unknown."""
    uncertain = []
    for requirement in chain.requirements:
        rows = evidence_for_requirement(chain, requirement)
        if not rows or any(verdict in (None, "unknown") for _, verdict in rows):
            uncertain.append(requirement)
    return uncertain


def decisions_for_task(chain: Chain, task: str) -> list[str]:
    return list(chain.task_decisions.get(task, ()))


def repair_history(chain: Chain, task: str) -> tuple[str, ...]:
    return chain.repairs.get(task, ())
