# Project Handoff

> Derived view — not authoritative. Edit underlying records, not this file.
> Store state: sha256:e4ceb247fdac660abec9d050427399c56bcef33c00306cacdf5f37e48968d962

## dashboard

### Goal
- **dashboard**: A live terminal dashboard, openable from tmux, shows each effort's phases, tasks and what needs you, lets you move from any item to its related records, and works correctly in every state; effort; deliver _(id: [rec-39db526b-abbb-4753-b9ff-40b8c05662c2](.artifacts/records/project__active-goal/rec-39db526b-abbb-4753-b9ff-40b8c05662c2.md))_

### Position
- **dashboard**: phase-selector done; next up: human-gates; effort _(id: [rec-52fdd613-97d9-4cc3-ba41-e90707b45dc3](.artifacts/records/project__current-position/rec-52fdd613-97d9-4cc3-ba41-e90707b45dc3.md))_
- **evidence-matrix**: evidence-matrix planned; waiting on plan review; phase _(id: [rec-05197b6f-4d9d-4719-99f3-7269b2c23b6d](.artifacts/records/project__current-position/rec-05197b6f-4d9d-4719-99f3-7269b2c23b6d.md))_
- **human-gates**: human-gates plan approved; blocked on UX plan-before-execute until remaining phases planned; phase _(id: [rec-8ae183e6-1ece-4610-9102-9e3e147be23d](.artifacts/records/project__current-position/rec-8ae183e6-1ece-4610-9102-9e3e147be23d.md))_
- **journal-view**: journal-view planned; waiting on plan review; phase _(id: [rec-9abd8e4d-983c-4fb3-8deb-37e2cc84f334](.artifacts/records/project__current-position/rec-9abd8e4d-983c-4fb3-8deb-37e2cc84f334.md))_
- **spec-view**: spec-view planned; waiting on plan review; phase _(id: [rec-fd3fdd37-4968-46bb-8062-512a639a796c](.artifacts/records/project__current-position/rec-fd3fdd37-4968-46bb-8062-512a639a796c.md))_

### Blocking Question
- **dashboard**: True; plan-review:journal-view _(id: [rec-0ed360b4-e87e-43bd-9dda-bbbad7062652](.artifacts/records/project__continuity-question/rec-0ed360b4-e87e-43bd-9dda-bbbad7062652.md))_
- **dashboard**: True; plan-review:spec-view _(id: [rec-ab4c4c73-6f25-4ece-ad6d-a7480e753383](.artifacts/records/project__continuity-question/rec-ab4c4c73-6f25-4ece-ad6d-a7480e753383.md))_
- **dashboard**: True; plan-review:evidence-matrix _(id: [rec-e7b76af5-7663-4f7b-85b6-d49a14c9233d](.artifacts/records/project__continuity-question/rec-e7b76af5-7663-4f7b-85b6-d49a14c9233d.md))_

## session-analysis

### Goal
- **session-analysis**: One command aggregates Claude Code transcripts and se-workflow artifact records across sessions, and a skill proposes evidence-backed edits to se-workflow and adaptive-artifacts.; repo; deliver _(id: [rec-ad4c0def-1d0c-4d40-b4d6-48d9d4b0c011](.artifacts/records/project__active-goal/rec-ad4c0def-1d0c-4d40-b4d6-48d9d4b0c011.md))_

### Position
- **session-analysis**: All four phases done. Run the analyze-sessions skill to review sessions. Code and skill are uncommitted. Two findings are open: the join is approximate, and the skill has minor judgment gaps.; repo _(id: [rec-428082e4-c07e-4c73-81c0-ffcb6c5e876c](.artifacts/records/project__current-position/rec-428082e4-c07e-4c73-81c0-ffcb6c5e876c.md))_

### Needs Human
- **as-dry-run**: The analyze-sessions skill yields 4 specific, metric-backed candidates on real data, but it lacks rules the agent had to guess: temp directory, pattern and noise, severity, and tool-level session ids.; human _(id: [rec-1e84d081-a11f-4cf3-b588-672c9f99d52b](.artifacts/records/project__finding/rec-1e84d081-a11f-4cf3-b588-672c9f99d52b.md))_
- **as-dry-run-rerun**: After the rules fix the skill needs no guessed rules for pattern, noise, severity or tool-level session references, but two gaps remain: project identity for worktree paths, and candidate edits that need a transcript read.; human _(id: [rec-b393a226-8a19-4952-abff-ecfaf8532b8b](.artifacts/records/project__finding/rec-b393a226-8a19-4952-abff-ecfaf8532b8b.md))_
- **rj-report-records**: The project-plus-time-window join leaves 70% of attached records ambiguous (386 of 553), so per-session record counts are unreliable for overlapping sessions.; human _(id: [rec-b8213c07-3cf9-4b56-a2a5-e9f56bd93f78](.artifacts/records/project__finding/rec-b8213c07-3cf9-4b56-a2a5-e9f56bd93f78.md))_

### Unsigned Manual Check
- **as-dry-run**: rec-2fa1b9d2-53f0-4a38-bc7f-ace90efeb566; pass; manual _(id: [rec-23dbd684-3ad1-481e-ac44-afd9f4a53263](.artifacts/records/project__check-run/rec-23dbd684-3ad1-481e-ac44-afd9f4a53263.md))_

## test-suite-speed

### Goal
- **test-suite-speed**: The full test suite runs much faster without adding CPU load; effort; incidental _(id: [rec-6d9a848c-b4a7-4bfd-ac0c-45187ea8180f](.artifacts/records/project__active-goal/rec-6d9a848c-b4a7-4bfd-ac0c-45187ea8180f.md))_

## workflow-loop

### Goal
- **workflow-loop**: The se-workflow loop maps efforts to product areas, closes finished efforts, runs phases in parallel, and settles the approach with the user before planning; effort; deliver _(id: [rec-65213e61-dda6-4955-95bc-8c9c4b289af1](.artifacts/records/project__active-goal/rec-65213e61-dda6-4955-95bc-8c9c4b289af1.md))_

### Position
- **workflow-loop**: evidence-loop done.; effort _(id: [rec-12df4b07-1639-47f7-a2b9-273059dd4e03](.artifacts/records/project__current-position/rec-12df4b07-1639-47f7-a2b9-273059dd4e03.md))_
