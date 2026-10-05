"""Evidence-driven software lifecycle.

The parent session follows `skills/lifecycle.md`. This package is the
transition authority those skills describe: stage order, evidence
quality, semantic integration, repair limits, and traceability.
"""

from lifecycle.loop import (
    LAYERS,
    MAX_REPAIRS,
    RELEASE_STATUSES,
    STAGES,
    UNRESOLVED,
    VERDICTS,
    Chain,
    CriterionResult,
    Evidence,
    Integration,
    LayerResult,
    LifecycleError,
    LoopState,
    Step,
    TaskClaim,
    advance,
    apply_release_status,
    depth_for,
    diagnosis_action,
    failure_action,
    integrate_claims,
    judge,
)

__all__ = [
    "LAYERS",
    "MAX_REPAIRS",
    "RELEASE_STATUSES",
    "STAGES",
    "UNRESOLVED",
    "VERDICTS",
    "Chain",
    "CriterionResult",
    "Evidence",
    "Integration",
    "LayerResult",
    "LifecycleError",
    "LoopState",
    "Step",
    "TaskClaim",
    "advance",
    "apply_release_status",
    "depth_for",
    "diagnosis_action",
    "failure_action",
    "integrate_claims",
    "judge",
]
