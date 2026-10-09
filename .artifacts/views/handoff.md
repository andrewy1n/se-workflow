# Project Handoff

> Derived view — not authoritative. Edit underlying records, not this file.
> Store state: sha256:78141b1b47b2584ce404d70a79118e412b142452cd81a4e570838c85816ed2c4

## dashboard

### Goal
- **dashboard**: A live terminal dashboard, openable from tmux, shows each effort's phases, tasks and what needs you, lets you move from any item to its related records, and works correctly in every state; effort; deliver _(id: [rec-39db526b-abbb-4753-b9ff-40b8c05662c2](/home/andrewyin/se-workflow/.artifacts/records/project__active-goal/rec-39db526b-abbb-4753-b9ff-40b8c05662c2.md))_

### Position
- **dashboard**: human-gates done; next up: spec-view; effort _(id: [rec-6fb92033-f209-429b-8a59-7deb20531c27](/home/andrewyin/se-workflow/.artifacts/records/project__current-position/rec-6fb92033-f209-429b-8a59-7deb20531c27.md))_
- **evidence-matrix**: evidence-matrix plan approved; ready for execute after prior UX deps; phase _(id: [rec-0b1d1d93-6cfa-4a53-9c95-1f70dba0fc2b](/home/andrewyin/se-workflow/.artifacts/records/project__current-position/rec-0b1d1d93-6cfa-4a53-9c95-1f70dba0fc2b.md))_
- **journal-view**: journal-view plan approved; ready for execute after prior UX deps; phase _(id: [rec-214e4e33-f72b-4aed-bced-7e71015a63d2](/home/andrewyin/se-workflow/.artifacts/records/project__current-position/rec-214e4e33-f72b-4aed-bced-7e71015a63d2.md))_
- **spec-view**: spec-view plan approved; ready for execute after prior UX deps; phase _(id: [rec-df06b9c4-1371-47b2-8db5-29e582d40101](/home/andrewyin/se-workflow/.artifacts/records/project__current-position/rec-df06b9c4-1371-47b2-8db5-29e582d40101.md))_

### In Progress
- **verify-spec-view**: Verify spec-view phase; spec-view; deliver; dashboard _(id: [rec-79a4e4c1-cfcb-421b-a023-64563ff645f3](/home/andrewyin/se-workflow/.artifacts/records/project__work-item/rec-79a4e4c1-cfcb-421b-a023-64563ff645f3.md))_

## session-analysis

### Goal
- **session-analysis**: One command aggregates Claude Code transcripts and se-workflow artifact records across sessions, and a skill proposes evidence-backed edits to se-workflow and adaptive-artifacts.; repo; deliver _(id: [rec-ad4c0def-1d0c-4d40-b4d6-48d9d4b0c011](/home/andrewyin/se-workflow/.artifacts/records/project__active-goal/rec-ad4c0def-1d0c-4d40-b4d6-48d9d4b0c011.md))_

### Position
- **session-analysis**: All four phases done. Run the analyze-sessions skill to review sessions. Code and skill are uncommitted. Two findings are open: the join is approximate, and the skill has minor judgment gaps.; repo _(id: [rec-428082e4-c07e-4c73-81c0-ffcb6c5e876c](/home/andrewyin/se-workflow/.artifacts/records/project__current-position/rec-428082e4-c07e-4c73-81c0-ffcb6c5e876c.md))_

### Needs Human
- **as-dry-run**: The analyze-sessions skill yields 4 specific, metric-backed candidates on real data, but it lacks rules the agent had to guess: temp directory, pattern and noise, severity, and tool-level session ids.; human _(id: [rec-1e84d081-a11f-4cf3-b588-672c9f99d52b](/home/andrewyin/se-workflow/.artifacts/records/project__finding/rec-1e84d081-a11f-4cf3-b588-672c9f99d52b.md))_
- **as-dry-run-rerun**: After the rules fix the skill needs no guessed rules for pattern, noise, severity or tool-level session references, but two gaps remain: project identity for worktree paths, and candidate edits that need a transcript read.; human _(id: [rec-b393a226-8a19-4952-abff-ecfaf8532b8b](/home/andrewyin/se-workflow/.artifacts/records/project__finding/rec-b393a226-8a19-4952-abff-ecfaf8532b8b.md))_
- **rj-report-records**: The project-plus-time-window join leaves 70% of attached records ambiguous (386 of 553), so per-session record counts are unreliable for overlapping sessions.; human _(id: [rec-b8213c07-3cf9-4b56-a2a5-e9f56bd93f78](/home/andrewyin/se-workflow/.artifacts/records/project__finding/rec-b8213c07-3cf9-4b56-a2a5-e9f56bd93f78.md))_

### Unsigned Manual Check
- **as-dry-run**: rec-2fa1b9d2-53f0-4a38-bc7f-ace90efeb566; pass; manual _(id: [rec-23dbd684-3ad1-481e-ac44-afd9f4a53263](/home/andrewyin/se-workflow/.artifacts/records/project__check-run/rec-23dbd684-3ad1-481e-ac44-afd9f4a53263.md))_

## test-suite-speed

### Goal
- **test-suite-speed**: The full test suite runs much faster without adding CPU load; effort; incidental _(id: [rec-6d9a848c-b4a7-4bfd-ac0c-45187ea8180f](/home/andrewyin/se-workflow/.artifacts/records/project__active-goal/rec-6d9a848c-b4a7-4bfd-ac0c-45187ea8180f.md))_

## workflow-loop

### Goal
- **workflow-loop**: The se-workflow loop maps efforts to product areas, closes finished efforts, runs phases in parallel, and settles the approach with the user before planning; effort; deliver _(id: [rec-65213e61-dda6-4955-95bc-8c9c4b289af1](/home/andrewyin/se-workflow/.artifacts/records/project__active-goal/rec-65213e61-dda6-4955-95bc-8c9c4b289af1.md))_

### Position
- **workflow-loop**: verify-budget done.; effort _(id: [rec-bb2dd87e-2fc5-403e-a2d5-0341bab63178](/home/andrewyin/se-workflow/.artifacts/records/project__current-position/rec-bb2dd87e-2fc5-403e-a2d5-0341bab63178.md))_
