# Project Dashboard

> Derived view — not authoritative. Edit underlying records, not this file.
> Store state: sha256:09845f7963a088c5c73a6527bd9a1f624dfb4553475aba3a434bf0d71fb01308

## dashboard

### Goal
- **dashboard**: goal: A live terminal dashboard, openable from tmux, shows each effort's phases, tasks and what needs you, lets you move from any item to its related records, and works correctly in every state; scope: effort; kind: deliver _(id: [rec-39db526b-abbb-4753-b9ff-40b8c05662c2](.artifacts/records/project__active-goal/rec-39db526b-abbb-4753-b9ff-40b8c05662c2.md))_

### Phase
- **estimate-view**: title: Show size and time estimates on the task table; ordinal: 21 _(id: [rec-5ba99c40-4b06-4a9f-a6c9-7aa755e22eb4](.artifacts/records/project__phase/rec-5ba99c40-4b06-4a9f-a6c9-7aa755e22eb4.md))_

### Ready
- **estimate-model**: title: Load size and estimate minutes into the dashboard model; phase: estimate-view _(id: [rec-0459fa1d-222c-4107-8749-78e7268070bc](.artifacts/records/project__work-item/rec-0459fa1d-222c-4107-8749-78e7268070bc.md))_

### Waiting
- **estimate-chips**: title: Show size, minutes, and executor as task detail chips; phase: estimate-view _(id: [rec-a5afd59d-ced8-4b93-a273-77482086696d](.artifacts/records/project__work-item/rec-a5afd59d-ced8-4b93-a273-77482086696d.md))_
- **estimate-table**: title: Show estimates on the phase header and task title; phase: estimate-view _(id: [rec-da0b731d-b175-40af-83ed-117bd79bfc74](.artifacts/records/project__work-item/rec-da0b731d-b175-40af-83ed-117bd79bfc74.md))_
- **verify-estimate-view**: title: Verify size and time estimates on the task table; phase: estimate-view _(id: [rec-5a9871bf-f6d1-4c04-8724-09143892ca29](.artifacts/records/project__work-item/rec-5a9871bf-f6d1-4c04-8724-09143892ca29.md))_

### Done Recent
- **estimate-contract**: title: Allow size and estimate_minutes on work-items; phase: run-facts _(id: [rec-06631dac-f66b-4c00-bc9f-f0fcd3d9b071](.artifacts/records/project__work-item/rec-06631dac-f66b-4c00-bc9f-f0fcd3d9b071.md))_
- **estimate-skill**: title: Require plan-phase to record size and estimate_minutes; phase: run-facts _(id: [rec-035c4162-7907-4319-9655-154cdbbe7062](.artifacts/records/project__work-item/rec-035c4162-7907-4319-9655-154cdbbe7062.md))_
- **evidence-model**: title: Load evidence-loop records into the dashboard model; phase: evidence-view _(id: [rec-cd9dccf6-ffc0-4aaa-a157-b54aa7d10fa7](.artifacts/records/project__work-item/rec-cd9dccf6-ffc0-4aaa-a157-b54aa7d10fa7.md))_
- **evidence-surfaces**: title: Show evidence on the main pane, phase detail, Needs you, and activity; phase: evidence-view _(id: [rec-eae64d17-f10b-415e-b311-d01de72be53c](.artifacts/records/project__work-item/rec-eae64d17-f10b-415e-b311-d01de72be53c.md))_
- **requirement-links**: title: Open the requirement screen from phase detail, Needs you, and task detail; phase: evidence-view _(id: [rec-53721903-e653-4295-a5fa-aa6d774d9442](.artifacts/records/project__work-item/rec-53721903-e653-4295-a5fa-aa6d774d9442.md))_
- **requirement-screen**: title: Requirement detail screen; phase: evidence-view _(id: [rec-84297b1d-931b-4155-a7db-defae8356207](.artifacts/records/project__work-item/rec-84297b1d-931b-4155-a7db-defae8356207.md))_
- **verify-evidence-view**: title: Verify the evidence view; phase: evidence-view _(id: [rec-f1c9b3ac-caa5-4eaf-831b-bf8c2fae6f8e](.artifacts/records/project__work-item/rec-f1c9b3ac-caa5-4eaf-831b-bf8c2fae6f8e.md))_
- **verify-run-facts**: title: Verify run-facts; phase: run-facts _(id: [rec-1644993c-06a8-4178-9ca9-ea39b522dce4](.artifacts/records/project__work-item/rec-1644993c-06a8-4178-9ca9-ea39b522dce4.md))_

## session-analysis

### Goal
- **session-analysis**: goal: One command aggregates Claude Code transcripts and se-workflow artifact records across sessions, and a skill proposes evidence-backed edits to se-workflow and adaptive-artifacts.; scope: repo; kind: deliver _(id: [rec-ad4c0def-1d0c-4d40-b4d6-48d9d4b0c011](.artifacts/records/project__active-goal/rec-ad4c0def-1d0c-4d40-b4d6-48d9d4b0c011.md))_

### Open Question
- **session-analysis**: blocking: False; scope: repo _(id: [rec-bf1f4351-3e7c-4c18-8cfb-dbe118a490ab](.artifacts/records/project__continuity-question/rec-bf1f4351-3e7c-4c18-8cfb-dbe118a490ab.md))_

### Needs Human
- **as-dry-run**: claim: The analyze-sessions skill yields 4 specific, metric-backed candidates on real data, but it lacks rules the agent had to guess: temp directory, pattern and noise, severity, and tool-level session ids.; needs: human _(id: [rec-1e84d081-a11f-4cf3-b588-672c9f99d52b](.artifacts/records/project__finding/rec-1e84d081-a11f-4cf3-b588-672c9f99d52b.md))_
- **as-dry-run-rerun**: claim: After the rules fix the skill needs no guessed rules for pattern, noise, severity or tool-level session references, but two gaps remain: project identity for worktree paths, and candidate edits that need a transcript read.; needs: human _(id: [rec-b393a226-8a19-4952-abff-ecfaf8532b8b](.artifacts/records/project__finding/rec-b393a226-8a19-4952-abff-ecfaf8532b8b.md))_
- **rj-report-records**: claim: The project-plus-time-window join leaves 70% of attached records ambiguous (386 of 553), so per-session record counts are unreliable for overlapping sessions.; needs: human _(id: [rec-b8213c07-3cf9-4b56-a2a5-e9f56bd93f78](.artifacts/records/project__finding/rec-b8213c07-3cf9-4b56-a2a5-e9f56bd93f78.md))_

### Unsigned Manual Check
- **as-dry-run**: criterion_id: rec-2fa1b9d2-53f0-4a38-bc7f-ace90efeb566; result: pass; method: manual _(id: [rec-23dbd684-3ad1-481e-ac44-afd9f4a53263](.artifacts/records/project__check-run/rec-23dbd684-3ad1-481e-ac44-afd9f4a53263.md))_

## test-suite-speed

### Goal
- **test-suite-speed**: goal: The full test suite runs much faster without adding CPU load; scope: effort; kind: incidental _(id: [rec-6d9a848c-b4a7-4bfd-ac0c-45187ea8180f](.artifacts/records/project__active-goal/rec-6d9a848c-b4a7-4bfd-ac0c-45187ea8180f.md))_

## workflow-loop

### Goal
- **workflow-loop**: goal: The se-workflow loop maps efforts to product areas, closes finished efforts, runs phases in parallel, and settles the approach with the user before planning; scope: effort; kind: deliver _(id: [rec-65213e61-dda6-4955-95bc-8c9c4b289af1](.artifacts/records/project__active-goal/rec-65213e61-dda6-4955-95bc-8c9c4b289af1.md))_

### Done Recent
- **assess-route**: title: Assess evidence and choose the next stage; phase: evidence-loop _(id: [rec-ff520a97-9aeb-4abf-a227-2af9bbc2cd58](.artifacts/records/project__work-item/rec-ff520a97-9aeb-4abf-a227-2af9bbc2cd58.md))_
- **contract-loop**: title: Add evidence-loop record types; phase: evidence-loop _(id: [rec-2ff3de0f-4884-4df0-973b-2d94bc0919d6](.artifacts/records/project__work-item/rec-2ff3de0f-4884-4df0-973b-2d94bc0919d6.md))_
- **integrate-execute**: title: Record semantic integration after parallel execution; phase: evidence-loop _(id: [rec-32979a5f-7e1e-426d-a07b-648f806bf77e](.artifacts/records/project__work-item/rec-32979a5f-7e1e-426d-a07b-648f806bf77e.md))_
- **loop-scenarios**: title: Test the evidence loop through the CLI; phase: evidence-loop _(id: [rec-84aec53d-9d7a-4ab3-8a2a-02318e951bba](.artifacts/records/project__work-item/rec-84aec53d-9d7a-4ab3-8a2a-02318e951bba.md))_
- **readme-lifecycle**: title: Document the evidence loop; phase: evidence-loop _(id: [rec-0a346ce9-d543-40c6-bffd-977250e063c5](.artifacts/records/project__work-item/rec-0a346ce9-d543-40c6-bffd-977250e063c5.md))_
- **specify-design**: title: Write specification and design from discuss; phase: evidence-loop _(id: [rec-c38456f3-9e59-46f8-a9a4-5c05961544e8](.artifacts/records/project__work-item/rec-c38456f3-9e59-46f8-a9a4-5c05961544e8.md))_
- **trace-plan**: title: Stamp tasks with requirements and decisions; phase: evidence-loop _(id: [rec-07bdba9f-ea31-402b-ace5-9f21b6c8930c](.artifacts/records/project__work-item/rec-07bdba9f-ea31-402b-ace5-9f21b6c8930c.md))_
- **verify-evidence-loop**: title: Verify the evidence loop; phase: evidence-loop _(id: [rec-1ed5449a-0cff-4806-aea0-c527992f2e80](.artifacts/records/project__work-item/rec-1ed5449a-0cff-4806-aea0-c527992f2e80.md))_
