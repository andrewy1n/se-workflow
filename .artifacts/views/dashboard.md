# Project Dashboard

> Derived view — not authoritative. Edit underlying records, not this file.
> Store state: sha256:8e1072e16a36d0542059e4929912a2d9b960622bc818ba28452ddfbe50d59f56

## dashboard

### Goal
- **dashboard**: goal: A live terminal dashboard, openable from tmux, shows each effort's phases, tasks and what needs you, lets you move from any item to its related records, and works correctly in every state; scope: effort; kind: deliver _(id: [rec-39db526b-abbb-4753-b9ff-40b8c05662c2](.artifacts/records/project__active-goal/rec-39db526b-abbb-4753-b9ff-40b8c05662c2.md))_

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

### Phase
- **evidence-loop**: title: Assess evidence and route the loop; ordinal: 9 _(id: [rec-292167f8-cd32-4ade-8ac5-cdd7942a05e4](.artifacts/records/project__phase/rec-292167f8-cd32-4ade-8ac5-cdd7942a05e4.md))_

### Blocking Question
- **workflow-loop**: blocking: True; scope: plan-review:evidence-loop _(id: [rec-b9b19713-05d0-4e3a-95f6-d70c864b81bb](.artifacts/records/project__continuity-question/rec-b9b19713-05d0-4e3a-95f6-d70c864b81bb.md))_

### Ready
- **contract-loop**: title: Add evidence-loop record types; phase: evidence-loop _(id: [rec-2ff3de0f-4884-4df0-973b-2d94bc0919d6](.artifacts/records/project__work-item/rec-2ff3de0f-4884-4df0-973b-2d94bc0919d6.md))_

### Waiting
- **assess-route**: title: Assess evidence and choose the next stage; phase: evidence-loop _(id: [rec-ff520a97-9aeb-4abf-a227-2af9bbc2cd58](.artifacts/records/project__work-item/rec-ff520a97-9aeb-4abf-a227-2af9bbc2cd58.md))_
- **integrate-execute**: title: Record semantic integration after parallel execution; phase: evidence-loop _(id: [rec-32979a5f-7e1e-426d-a07b-648f806bf77e](.artifacts/records/project__work-item/rec-32979a5f-7e1e-426d-a07b-648f806bf77e.md))_
- **loop-scenarios**: title: Test the evidence loop through the CLI; phase: evidence-loop _(id: [rec-84aec53d-9d7a-4ab3-8a2a-02318e951bba](.artifacts/records/project__work-item/rec-84aec53d-9d7a-4ab3-8a2a-02318e951bba.md))_
- **readme-lifecycle**: title: Document the evidence loop; phase: evidence-loop _(id: [rec-0a346ce9-d543-40c6-bffd-977250e063c5](.artifacts/records/project__work-item/rec-0a346ce9-d543-40c6-bffd-977250e063c5.md))_
- **specify-design**: title: Write specification and design from discuss; phase: evidence-loop _(id: [rec-c38456f3-9e59-46f8-a9a4-5c05961544e8](.artifacts/records/project__work-item/rec-c38456f3-9e59-46f8-a9a4-5c05961544e8.md))_
- **trace-plan**: title: Stamp tasks with requirements and decisions; phase: evidence-loop _(id: [rec-07bdba9f-ea31-402b-ace5-9f21b6c8930c](.artifacts/records/project__work-item/rec-07bdba9f-ea31-402b-ace5-9f21b6c8930c.md))_
- **verify-evidence-loop**: title: Verify the evidence loop; phase: evidence-loop _(id: [rec-1ed5449a-0cff-4806-aea0-c527992f2e80](.artifacts/records/project__work-item/rec-1ed5449a-0cff-4806-aea0-c527992f2e80.md))_
