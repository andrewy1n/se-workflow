# Project Dashboard

> Derived view — not authoritative. Edit underlying records, not this file.
> Store state: sha256:b6df86c1bf81bb745c38c5e24bcad142b31109a6035a7c354ebb88fcd92d01da

## dashboard

### Goal
- **dashboard**: goal: A live terminal dashboard, openable from tmux, shows each effort's phases, tasks and what needs you, lets you move from any item to its related records, and works correctly in every state; scope: effort; kind: deliver _(id: [rec-39db526b-abbb-4753-b9ff-40b8c05662c2](.artifacts/records/project__active-goal/rec-39db526b-abbb-4753-b9ff-40b8c05662c2.md))_

### Phase
- **human-gates**: title: Show the human gates: action labels, copy prompt, next step, landing; ordinal: 23 _(id: [rec-c52c1f18-8b64-4731-9d21-2e74eabf7366](.artifacts/records/project__phase/rec-c52c1f18-8b64-4731-9d21-2e74eabf7366.md))_

### Ready
- **gates-landing**: title: Read-only phase Landing git state; phase: human-gates _(id: [rec-7670ae47-9b16-4a83-bba8-adc230411a8d](.artifacts/records/project__work-item/rec-7670ae47-9b16-4a83-bba8-adc230411a8d.md))_
- **gates-vocab**: title: Gate vocabulary: labels, prompts, next step, quiet; phase: human-gates _(id: [rec-72a1fc93-f49b-4f59-bc6a-e45cd50e7d03](.artifacts/records/project__work-item/rec-72a1fc93-f49b-4f59-bc6a-e45cd50e7d03.md))_

### Waiting
- **gates-model**: title: Wire landing merge, last_record_at, and quiet into the model; phase: human-gates _(id: [rec-ac8585d0-b933-4316-9117-d0a07db48860](.artifacts/records/project__work-item/rec-ac8585d0-b933-4316-9117-d0a07db48860.md))_
- **gates-status**: title: tmux status-right needs-you count segment; phase: human-gates _(id: [rec-1749a417-d901-4efd-89eb-bd7bab403426](.artifacts/records/project__work-item/rec-1749a417-d901-4efd-89eb-bd7bab403426.md))_
- **gates-ui**: title: Next-step line, copy prompt, and new-item alerts; phase: human-gates _(id: [rec-6230a7c9-c054-4825-8f76-92e8f21bdcd5](.artifacts/records/project__work-item/rec-6230a7c9-c054-4825-8f76-92e8f21bdcd5.md))_
- **verify-human-gates**: title: Verify human-gates phase; phase: human-gates _(id: [rec-4821ded2-c229-49eb-beff-3e0bd580544f](.artifacts/records/project__work-item/rec-4821ded2-c229-49eb-beff-3e0bd580544f.md))_

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
