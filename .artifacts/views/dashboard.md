# Project Dashboard

> Derived view — not authoritative. Edit underlying records, not this file.
> Store state: sha256:230caf9e05a9d0c9bbed501d8d0746bb2a879c80401ec00090b95d84e19b94f1

## dashboard

### Goal
- **dashboard**: goal: A live terminal dashboard, openable from tmux, shows each effort's phases, tasks and what needs you, lets you move from any item to its related records, and works correctly in every state; scope: effort; kind: deliver _(id: [rec-39db526b-abbb-4753-b9ff-40b8c05662c2](/home/andrewyin/se-workflow/.artifacts/records/project__active-goal/rec-39db526b-abbb-4753-b9ff-40b8c05662c2.md))_

### Done Recent
- **header-chrome**: title: Quiet status tabs and a collapsed phase stepper; phase: quiet-header _(id: [rec-08a2cce2-5dda-4b6d-a262-2eadcfc20f42](/home/andrewyin/se-workflow/.artifacts/records/project__work-item/rec-08a2cce2-5dda-4b6d-a262-2eadcfc20f42.md))_
- **verify-quiet-header**: title: Verify quiet status tabs and a collapsed phase stepper; phase: quiet-header _(id: [rec-5af4a9a2-d370-4cc2-8851-7c7a19028f78](/home/andrewyin/se-workflow/.artifacts/records/project__work-item/rec-5af4a9a2-d370-4cc2-8851-7c7a19028f78.md))_

## session-analysis

### Goal
- **session-analysis**: goal: One command aggregates Claude Code transcripts and se-workflow artifact records across sessions, and a skill proposes evidence-backed edits to se-workflow and adaptive-artifacts.; scope: repo; kind: deliver _(id: [rec-ad4c0def-1d0c-4d40-b4d6-48d9d4b0c011](/home/andrewyin/se-workflow/.artifacts/records/project__active-goal/rec-ad4c0def-1d0c-4d40-b4d6-48d9d4b0c011.md))_

### Open Question
- **session-analysis**: blocking: False; scope: repo _(id: [rec-bf1f4351-3e7c-4c18-8cfb-dbe118a490ab](/home/andrewyin/se-workflow/.artifacts/records/project__continuity-question/rec-bf1f4351-3e7c-4c18-8cfb-dbe118a490ab.md))_

### Needs Human
- **as-dry-run**: claim: The analyze-sessions skill yields 4 specific, metric-backed candidates on real data, but it lacks rules the agent had to guess: temp directory, pattern and noise, severity, and tool-level session ids.; needs: human _(id: [rec-1e84d081-a11f-4cf3-b588-672c9f99d52b](/home/andrewyin/se-workflow/.artifacts/records/project__finding/rec-1e84d081-a11f-4cf3-b588-672c9f99d52b.md))_
- **as-dry-run-rerun**: claim: After the rules fix the skill needs no guessed rules for pattern, noise, severity or tool-level session references, but two gaps remain: project identity for worktree paths, and candidate edits that need a transcript read.; needs: human _(id: [rec-b393a226-8a19-4952-abff-ecfaf8532b8b](/home/andrewyin/se-workflow/.artifacts/records/project__finding/rec-b393a226-8a19-4952-abff-ecfaf8532b8b.md))_
- **rj-report-records**: claim: The project-plus-time-window join leaves 70% of attached records ambiguous (386 of 553), so per-session record counts are unreliable for overlapping sessions.; needs: human _(id: [rec-b8213c07-3cf9-4b56-a2a5-e9f56bd93f78](/home/andrewyin/se-workflow/.artifacts/records/project__finding/rec-b8213c07-3cf9-4b56-a2a5-e9f56bd93f78.md))_

### Unsigned Manual Check
- **as-dry-run**: criterion_id: rec-2fa1b9d2-53f0-4a38-bc7f-ace90efeb566; result: pass; method: manual _(id: [rec-23dbd684-3ad1-481e-ac44-afd9f4a53263](/home/andrewyin/se-workflow/.artifacts/records/project__check-run/rec-23dbd684-3ad1-481e-ac44-afd9f4a53263.md))_

## test-suite-speed

### Goal
- **test-suite-speed**: goal: The full test suite runs much faster without adding CPU load; scope: effort; kind: incidental _(id: [rec-6d9a848c-b4a7-4bfd-ac0c-45187ea8180f](/home/andrewyin/se-workflow/.artifacts/records/project__active-goal/rec-6d9a848c-b4a7-4bfd-ac0c-45187ea8180f.md))_

## workflow-loop

### Goal
- **workflow-loop**: goal: The se-workflow loop maps efforts to product areas, closes finished efforts, runs phases in parallel, and settles the approach with the user before planning; scope: effort; kind: deliver _(id: [rec-65213e61-dda6-4955-95bc-8c9c4b289af1](/home/andrewyin/se-workflow/.artifacts/records/project__active-goal/rec-65213e61-dda6-4955-95bc-8c9c4b289af1.md))_

### Done Recent
- **execute-landing**: title: Land the phase branch when the gate holds; phase: phase-landing _(id: [rec-94264b82-7ed0-434c-80ce-71f1a7d85821](/home/andrewyin/se-workflow/.artifacts/records/project__work-item/rec-94264b82-7ed0-434c-80ce-71f1a7d85821.md))_
- **execute-wave-dispatch**: title: Dispatch each wave inline or as subagents; phase: wave-executor _(id: [rec-b9536deb-8dcc-45d3-93d4-910f32be06e3](/home/andrewyin/se-workflow/.artifacts/records/project__work-item/rec-b9536deb-8dcc-45d3-93d4-910f32be06e3.md))_
- **plan-landing-rules**: title: Record phase landing before plan review; phase: phase-landing _(id: [rec-51225c8f-9709-4f03-a5f5-05d88b70b55e](/home/andrewyin/se-workflow/.artifacts/records/project__work-item/rec-51225c8f-9709-4f03-a5f5-05d88b70b55e.md))_
- **plan-wave-rules**: title: Record recipe, executor, and phase run facts in plan-phase; phase: wave-executor _(id: [rec-00ad8c6d-818c-4832-abcd-44337b36efdf](/home/andrewyin/se-workflow/.artifacts/records/project__work-item/rec-00ad8c6d-818c-4832-abcd-44337b36efdf.md))_
- **verify-phase-landing**: title: Verify phase landing; phase: phase-landing _(id: [rec-ee75a24d-3394-4d24-bd8b-122822cea232](/home/andrewyin/se-workflow/.artifacts/records/project__work-item/rec-ee75a24d-3394-4d24-bd8b-122822cea232.md))_
- **verify-wave-executor**: title: Verify inline and subagent waves agree; phase: wave-executor _(id: [rec-303a813d-f447-4633-acc4-c803a58792af](/home/andrewyin/se-workflow/.artifacts/records/project__work-item/rec-303a813d-f447-4633-acc4-c803a58792af.md))_
