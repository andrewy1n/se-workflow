# Project Dashboard

> Derived view — not authoritative. Edit underlying records, not this file.
> Store state: sha256:5ef95f38ae6e9ca7b544c0f8e00a1ac92e233d9091ec0687528d94f6133997b1

## dashboard

### Goal
- **dashboard**: goal: A live terminal dashboard, openable from tmux, shows each effort's phases, tasks and what needs you, lets you move from any item to its related records, and works correctly in every state; scope: effort; kind: deliver _(id: [rec-39db526b-abbb-4753-b9ff-40b8c05662c2](.artifacts/records/project__active-goal/rec-39db526b-abbb-4753-b9ff-40b8c05662c2.md))_

### Done Recent
- **package-install**: title: Update the plugin install, tmux conf and README; phase: dashboard-package _(id: [rec-fd456adc-607d-40fd-8215-e01cee50bd2d](.artifacts/records/project__work-item/rec-fd456adc-607d-40fd-8215-e01cee50bd2d.md))_
- **package-move**: title: Move the dashboard files into dashboard/; phase: dashboard-package _(id: [rec-11458acf-aa6f-4f59-9e01-9bfdf7775c84](.artifacts/records/project__work-item/rec-11458acf-aa6f-4f59-9e01-9bfdf7775c84.md))_
- **readme-quickstart**: title: Write the README quick start; phase: tmux-plugin-entry _(id: [rec-89b3f196-2e9d-4d61-b949-cc0d3d115249](.artifacts/records/project__work-item/rec-89b3f196-2e9d-4d61-b949-cc0d3d115249.md))_
- **task-detail-module**: title: Split the task detail code out of app.py; phase: dashboard-package _(id: [rec-e4ba2299-b1c1-49e1-9b96-347d67c9a8e9](.artifacts/records/project__work-item/rec-e4ba2299-b1c1-49e1-9b96-347d67c9a8e9.md))_
- **task-table-module**: title: Split the task table code out of app.py; phase: dashboard-package _(id: [rec-43489199-dd56-4be8-a238-9903276a117d](.artifacts/records/project__work-item/rec-43489199-dd56-4be8-a238-9903276a117d.md))_
- **tmux-conf-removal**: title: Move the tmux tests and sync-plugin.sh to the script and delete tmux.conf; phase: tmux-plugin-entry _(id: [rec-6c985f64-da0c-4112-a5ea-f0abb0e315b0](.artifacts/records/project__work-item/rec-6c985f64-da0c-4112-a5ea-f0abb0e315b0.md))_
- **tmux-entry-script**: title: Write the se-workflow.tmux entry script; phase: tmux-plugin-entry _(id: [rec-37c83088-9e03-48f3-8ccf-dfb5facf3e12](.artifacts/records/project__work-item/rec-37c83088-9e03-48f3-8ccf-dfb5facf3e12.md))_
- **verify-dashboard-package**: title: Verify Move the dashboard code out of scripts; phase: dashboard-package _(id: [rec-75cd523e-7383-4d8b-b045-6ea551e21cba](.artifacts/records/project__work-item/rec-75cd523e-7383-4d8b-b045-6ea551e21cba.md))_
- **verify-tmux-plugin-entry**: title: Verify TPM entry script and quick start; phase: tmux-plugin-entry _(id: [rec-624555dc-a6c2-470c-8c29-08cecff29655](.artifacts/records/project__work-item/rec-624555dc-a6c2-470c-8c29-08cecff29655.md))_

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
- **execute-landing**: title: Land the phase branch when the gate holds; phase: phase-landing _(id: [rec-94264b82-7ed0-434c-80ce-71f1a7d85821](.artifacts/records/project__work-item/rec-94264b82-7ed0-434c-80ce-71f1a7d85821.md))_
- **execute-wave-dispatch**: title: Dispatch each wave inline or as subagents; phase: wave-executor _(id: [rec-b9536deb-8dcc-45d3-93d4-910f32be06e3](.artifacts/records/project__work-item/rec-b9536deb-8dcc-45d3-93d4-910f32be06e3.md))_
- **plan-landing-rules**: title: Record phase landing before plan review; phase: phase-landing _(id: [rec-51225c8f-9709-4f03-a5f5-05d88b70b55e](.artifacts/records/project__work-item/rec-51225c8f-9709-4f03-a5f5-05d88b70b55e.md))_
- **plan-wave-rules**: title: Record recipe, executor, and phase run facts in plan-phase; phase: wave-executor _(id: [rec-00ad8c6d-818c-4832-abcd-44337b36efdf](.artifacts/records/project__work-item/rec-00ad8c6d-818c-4832-abcd-44337b36efdf.md))_
- **verify-phase-landing**: title: Verify phase landing; phase: phase-landing _(id: [rec-ee75a24d-3394-4d24-bd8b-122822cea232](.artifacts/records/project__work-item/rec-ee75a24d-3394-4d24-bd8b-122822cea232.md))_
- **verify-wave-executor**: title: Verify inline and subagent waves agree; phase: wave-executor _(id: [rec-303a813d-f447-4633-acc4-c803a58792af](.artifacts/records/project__work-item/rec-303a813d-f447-4633-acc4-c803a58792af.md))_
