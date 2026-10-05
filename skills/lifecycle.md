# Lifecycle

Shared stage rules for every se-workflow skill. Kinds stay
`deliver` | `repair` | `evaluate` | `incidental`. Depth chooses how
much of the lifecycle runs. The transition authority is
`lifecycle/loop.py`: `STAGES`, `VERDICTS`, `LAYERS`, `MAX_REPAIRS`
(3), and `RELEASE_STATUSES`. Do not invent a different repair limit
or treat a passing test as proof the specification holds.

## Depth

`depth` is `trivial` | `standard` | `full`. Put it on `active-goal`.
Missing `depth` means `standard`, except `kind=incidental`, which is
`trivial`.

| Depth | Path |
|---|---|
| `trivial` | intent → execute → verify → release |
| `standard` | intent → specify → design → plan → execute → verify → release. Insert integrate when more than one task runs in a wave. |
| `full` | intent → specify → design → plan → execute → integrate → verify → release |

`trivial` writes no specification, design, or integration-report.
A skipped design on `standard` still writes a `project:design` with
`weight` `skipped` and a real reason in every section. `full` does
not skip design or integrate.

## Stages

Each stage reduces uncertainty about what to build, how to build it,
whether it was built, or what to do when it was not.

| Stage | Artifact | Agent |
|---|---|---|
| intent | `active-goal` (`engage`) | parent |
| specify | `specification` + acceptance criteria | parent, `specify` |
| design | `design` + `decision` | parent, `discuss` then `design` |
| plan | `phase` + `work-item` | parent, `plan-phase` |
| execute | `assignment` + `execution-report` | parent plus one executor per task |
| integrate | `integration-report` | parent, `integrate` |
| verify | `check-run` + `uncertainty` | parent, `verify-work` |
| diagnose | `investigation-observation` + `finding` | parent, `diagnose` |
| repair | repair `work-item`, then `repair-attempt` | parent, then `execute-phase` |
| release | `release` | parent, `release` |
| deploy / monitor | `release.status` only | no deployer in this plugin |
| feedback | `feedback` → new intent | parent, `feedback` |

Set the phase position's `stage` when the stage changes. `scope`
stays `phase`:

```bash
adaptive-artifacts supersede --type project:current-position --id <phase-position-id> \
  --expected-revision <revision> \
  --payload '{"stage":"verify"}'
```

`stage` is `intent` | `specify` | `design` | `plan` | `execute` |
`integrate` | `verify` | `diagnose` | `repair` | `release` |
`deploy` | `monitor` | `feedback`.

## Evidence

`verdict` is `pass` | `fail` | `blocked` | `unknown`.

`pass` means the layers the strategy required for that criterion
passed and no open uncertainty remains on it. `fail` means a required
behavior failed. `blocked` means the check could not run. `unknown`
means the check did not cover the criterion. A green unit suite is
`unknown` on a criterion whose strategy required `acceptance`.

Layers, used only when the strategy names them: `build`, `unit`,
`integration`, `acceptance`, `static`, `types`, `security`,
`regression`, `design`, `behavior`.

An open `project:uncertainty` keeps the phase out of release. The
user accepts it by supersede (`status` `accepted` or `resolved`).
That is a human decision, not a pass.

## Repair

A failure is an observation (`investigation-observation`). A
diagnosis is a `finding` that names the cause. `unresolved` is not a
cause. Do not repair an unresolved diagnosis.

Before another repair, list `project:repair-attempt` for the task.
The repair limit is 3 (`MAX_REPAIRS`). Escalate, and do not repair,
when any of these hold:

- the count is already 3 (`MAX_REPAIRS`)
- `failure_signature` matches an earlier attempt
- the diagnosis is `unresolved`

Escalation writes a blocking `continuity-question` with `scope`
`repair-limit:<phase-slug>` and a `finding` with `needs` `human`.
The parent asks the user. It does not start another repair.

A repair returns through `integrate` unless depth is `trivial`, then
through `verify` again. Write `repair-attempt` when that verification
finishes (`outcome` `repaired`, `failed_again`, `unresolved`, or
`escalated`).

## Integration

Git merge success is not semantic integration success. A git merge
that succeeds is not an integration pass. `integrate`
reads the combined tree and the interfaces and assumptions the
executors reported. Disagreeing interfaces, or an assumption that is
`not` what another task assumed, is `verdict` `fail` even when the
merge was clean.

## Release and feedback

`release.status` is `ready_to_merge` | `merged` | `artifact_produced`
| `deployment_initiated` | `deployment_succeeded` |
`deployment_failed`. Creating `ready_to_merge` does not deploy.
`deploy` and `monitor` are status values and stage names only. This
plugin does not ship a deployer or a metrics stack.

`feedback` records a runtime or user signal. The next step is a new
intent: `engage` on a new phase, or a new effort when no live goal
covers it.

## Traceability

Keep the chain in payload fields, not a second database:

- acceptance `specification` → the specification subject
- decision `serves` → comma-separated acceptance subjects
- work-item `satisfies` → comma-separated acceptance subjects
- work-item `design` → the design subject, omitted when design was not written
- check-run `criterion_id` → the acceptance record id
- repair-attempt `work_item` → the work-item subject, `diagnosis` → the cause

A specification acceptance that no work-item `satisfies`, including
the verification task, is not planned yet. A criterion with no
check-run, or whose latest verdict is `unknown`, is not verified.
