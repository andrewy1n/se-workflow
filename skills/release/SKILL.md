---
name: release
description: >-
  Records that a verified phase is ready to merge, and later release
  statuses if a human reports them. Use after verify passes with no
  open uncertainty. Does not deploy.
---

# Release

Requires `artifact-runtime` and a live se-workflow store. Follow
[lifecycle.md](../lifecycle.md). Parent session writes records.

Verified is not deployed. This skill writes posture. It does not
build artifacts, call a host, or watch production.

## Rules

- Enter only when the phase gate holds, integration is `pass` or
  was skipped for this depth, and no `project:uncertainty` for the
  phase is `status` `open`.
- Initial `status` is `ready_to_merge`. Later statuses, only when
  the corresponding fact is true: `merged`, `artifact_produced`,
  `deployment_initiated`, `deployment_succeeded`,
  `deployment_failed`. Change them with `supersede`, which merges
  payload.
- `deployment_succeeded` is not inferred from tests.

## Steps

1. Confirm the gate in `execute-phase` and the absence of open
   uncertainties:

```bash
adaptive-artifacts list --type project:uncertainty --where payload.effort=<effort-slug> --state active
```

   An active row with `status` `open` blocks release. The user may
   accept it:

```bash
adaptive-artifacts supersede --type project:uncertainty --id <uncertainty-id> \
  --expected-revision <revision> \
  --payload '{"status":"accepted"}'
```

2. Create the release at `ready_to_merge`:

```bash
adaptive-artifacts create --type project:release \
  --subject "release-<phase-slug>" \
  --payload '{"phase":"<phase-slug>","effort":"<effort-slug>","status":"ready_to_merge","note":"<what was verified and what was not deployed>"}'
```

3. Set the phase position `stage` to `release`. When a human later
   reports a real merge or deployment event, supersede `status`.
   Do not invent the event.

```bash
adaptive-artifacts supersede --type project:release --id <release-id> \
  --expected-revision <revision> \
  --payload '{"status":"merged"}'
```

4. Validate. `deploy` and `monitor` stay extension points: set
   `stage` to those names only alongside a truthful `status`. A
   runtime signal after that is `feedback`, which starts a new
   intent.

## Do not

- Deploy
- Set `deployment_succeeded` because verify passed
- Release with an open uncertainty the user has not accepted
