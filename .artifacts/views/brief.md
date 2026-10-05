# Project Brief

> Derived view — not authoritative. Edit underlying records, not this file.
> Store state: sha256:2bf85f8a54219ed8f0f36f6e7e57f8de2fc03cd11ea8b2ec9aa1f8e4faebf4f0

## activity-failures

### Acceptance
- **activity-failures**: Model test sets failed for a failed check-run and a failed report only; pilot test shows a failed line in the error colour with ✗; the tests fail before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py tests/test_dashboard_app.py -q -k fail _(id: [rec-7d228e89-762a-4794-9c56-adfca651899a](.artifacts/records/project__acceptance/rec-7d228e89-762a-4794-9c56-adfca651899a.md))_

## adaptive-artifacts-change-gate

### Constraint
- **adaptive-artifacts-change-gate**: Runtime changes in the adaptive-artifacts repo follow its AGENTS.md gate: capture them in that repo's store and apply only with human approval; work-items that edit ~/adaptive-artifacts; dashboard _(id: [rec-0b5620e8-3bf4-45f3-9de4-6d10a46c578b](.artifacts/records/project__constraint/rec-0b5620e8-3bf4-45f3-9de4-6d10a46c578b.md))_

## add-dashboard-view

### Acceptance
- **add-dashboard-view**: The contract resolves with the dashboard view and passes the contract and skill consistency tests; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-b6ae7140-2e58-4194-9294-6cc47d132fb4](.artifacts/records/project__acceptance/rec-b6ae7140-2e58-4194-9294-6cc47d132fb4.md))_

## add-dashboard-view-render

### Acceptance
- **add-dashboard-view-render**: Against a seeded store with one record per section, view --id project:dashboard renders every section in order with labeled fields, and a done item older than 24h is absent; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests -q -k dashboard _(id: [rec-1dceda28-8bfd-43df-b3ca-53d3a7740286](.artifacts/records/project__acceptance/rec-1dceda28-8bfd-43df-b3ca-53d3a7740286.md))_

## ag-aggregate-cli

### Acceptance
- **ag-aggregate-cli**: On a fixture report the command prints valid JSON with efforts, tools, skills, outliers and caveats; on the real report it exits 0 and lists every effort that has a session.; tdd; session-analysis; python3 -m pytest -q tests/test_session_aggregate.py _(id: [rec-efaa257a-446d-4f97-a738-4d098747043f](.artifacts/records/project__acceptance/rec-efaa257a-446d-4f97-a738-4d098747043f.md))_

## ag-effort-rollup

### Acceptance
- **ag-effort-rollup**: A fixture of three sessions and two efforts, one session touching both, yields exact per-effort totals with shared and exclusive cost split.; tdd; session-analysis; python3 -m pytest -q tests/test_effort_rollup.py _(id: [rec-d0cbaaf6-d767-45f6-aa4d-f32b9415b6bc](.artifacts/records/project__acceptance/rec-d0cbaaf6-d767-45f6-aa4d-f32b9415b6bc.md))_

## ag-outliers

### Acceptance
- **ag-outliers**: A fixture yields the top sessions per metric in the expected order, with references and values only, and fewer than top entries when there are fewer sessions.; tdd; session-analysis; python3 -m pytest -q tests/test_session_outliers.py _(id: [rec-4b4378e7-5443-435e-86ab-02ad515ebb4d](.artifacts/records/project__acceptance/rec-4b4378e7-5443-435e-86ab-02ad515ebb4d.md))_

## ag-tool-skill-rollup

### Acceptance
- **ag-tool-skill-rollup**: A fixture yields exact per-tool calls, errors, error rate, retries and session counts, and per-skill invocation and session counts, in sorted order.; tdd; session-analysis; python3 -m pytest -q tests/test_tool_skill_rollup.py _(id: [rec-f283ff9c-78e6-439b-ae65-90ef88690304](.artifacts/records/project__acceptance/rec-f283ff9c-78e6-439b-ae65-90ef88690304.md))_

## as-cost-null

### Acceptance
- **as-cost-null**: Every session whose transcript has a cost-state line with a numeric cost reports a non-null cost_usd, and a regression test covers the cause.; tdd; session-analysis; python3 -m pytest -q tests/test_session_fields.py _(id: [rec-36001c1e-b274-4757-b5b3-44fd1a44e292](.artifacts/records/project__acceptance/rec-36001c1e-b274-4757-b5b3-44fd1a44e292.md))_

### Finding
- **as-cost-null**: Null cost_usd on 140 of 247 sessions is a data gap: those transcripts have no cost-state line, so cost totals are a lower bound over 107 sessions.; Streamed all 140 null transcripts: 0 cost-state lines and 0 cost-named keys. The 107 non-null sessions parse correctly.; Claude Code starts writing cost-state lines for more sessions, or a different cost field appears in transcripts.; none _(id: [rec-8aa9b9e5-9088-4e73-a8ec-facffa2d3833](.artifacts/records/project__finding/rec-8aa9b9e5-9088-4e73-a8ec-facffa2d3833.md))_

## as-dry-run

### Acceptance
- **as-dry-run**: The dry run lists candidates that each cite a metric and a session reference, and the user accepts the list.; manual; session-analysis _(id: [rec-2fa1b9d2-53f0-4a38-bc7f-ace90efeb566](.artifacts/records/project__acceptance/rec-2fa1b9d2-53f0-4a38-bc7f-ace90efeb566.md))_

### Finding
- **as-dry-run**: The analyze-sessions skill yields 4 specific, metric-backed candidates on real data, but it lacks rules the agent had to guess: temp directory, pattern and noise, severity, and tool-level session ids.; Dry run over 243 sessions: 4 candidates each with a metric, session references and a target; 4 patterns dropped; 6 of 7 done-when criteria met (step 7 deferred to the caller). I re-checked the Bash, jira_create_issue and error-outlier numbers against a fresh run and they match.; SKILL.md defines the missing rules and a second dry run needs no manual report.jsonl lookups.; human _(id: [rec-1e84d081-a11f-4cf3-b588-672c9f99d52b](.artifacts/records/project__finding/rec-1e84d081-a11f-4cf3-b588-672c9f99d52b.md))_

## as-dry-run-rerun

### Finding
- **as-dry-run-rerun**: After the rules fix the skill needs no guessed rules for pattern, noise, severity or tool-level session references, but two gaps remain: project identity for worktree paths, and candidate edits that need a transcript read.; Second dry run over 243 sessions: 2 candidates with full session ids and targets, 2 patterns dropped, 1 noise session. The agent named remaining gaps: worktree project strings, double counting of slots across patterns, edits that cannot be named from metrics, cost outliers with empty efforts have no target, cross-repo fix locations.; SKILL.md and targets.md state the project-identity, double counting, evidence-needed and cross-repo rules and a third run needs no guesses.; human _(id: [rec-b393a226-8a19-4952-abff-ecfaf8532b8b](.artifacts/records/project__finding/rec-b393a226-8a19-4952-abff-ecfaf8532b8b.md))_

## as-skill

### Acceptance
- **as-skill**: SKILL.md has name and a user-invoked flag, names both scripts at paths that exist, links targets.md, has no store-writing command, stays under 80 lines, and the skill contract consistency test passes.; tdd; session-analysis; python3 -m pytest -q tests/test_analyze_sessions_skill.py tests/test_skill_contract_consistency.py _(id: [rec-d186eb9e-852f-4f75-96aa-313e576c0f8b](.artifacts/records/project__acceptance/rec-d186eb9e-852f-4f75-96aa-313e576c0f8b.md))_

## as-skill-rules

### Acceptance
- **as-skill-rules**: SKILL.md defines the temp directory, pattern, noise, severity, tool-level session references and bounded slices, stays under 80 lines, and the skill tests and the skill contract consistency test pass.; tdd; session-analysis; python3 -m pytest -q tests/test_analyze_sessions_skill.py tests/test_skill_contract_consistency.py _(id: [rec-f0c76da5-b91f-4660-bcc7-e221a00ac3e8](.artifacts/records/project__acceptance/rec-f0c76da5-b91f-4660-bcc7-e221a00ac3e8.md))_

## as-targets

### Acceptance
- **as-targets**: targets.md has one section per target and each section lists at least one pattern whose metric field names all exist in the real aggregate output.; tdd; session-analysis; python3 -m pytest -q tests/test_analyze_sessions_targets.py _(id: [rec-9c15a1e4-c392-4ce0-8482-7bea7dd7f367](.artifacts/records/project__acceptance/rec-9c15a1e4-c392-4ce0-8482-7bea7dd7f367.md))_

## close-step-skill

### Acceptance
- **close-step-skill**: execute-phase documents the close step with a payload the contract accepts; skill/contract consistency tests pass; tdd; workflow-loop; python3 -m pytest tests/test_skill_contract_consistency.py -q _(id: [rec-8bcac210-20bd-42a8-b0ea-953bd412937a](.artifacts/records/project__acceptance/rec-8bcac210-20bd-42a8-b0ea-953bd412937a.md))_

## column-resize

### Acceptance
- **column-resize**: Resize 120 to 60 columns: the table shows status, task, wave with no reload; resize back: phase and assignee return; the test fails before the fix; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k resize _(id: [rec-4b32e614-7d7e-4a55-be85-301c98fe6ef9](.artifacts/records/project__acceptance/rec-4b32e614-7d7e-4a55-be85-301c98fe6ef9.md))_

## commit-stat-width

### Acceptance
- **commit-stat-width**: A pilot test at 60 and 80 columns shows every stat line of a commit with a long path on one line; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-de68bee3-9f99-4495-8545-8aa7b453e373](.artifacts/records/project__acceptance/rec-de68bee3-9f99-4495-8545-8aa7b453e373.md))_

## copy-and-commit-actions

### Acceptance
- **copy-and-commit-actions**: Pilot tests copy the selected slug from the dashboard and the detail screen, open the commit screen with the message and stat for a task's latest revision in a temp git repo, show a message for a dirty or unknown revision, and return on Esc; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-b0782695-b6a8-443a-b1ed-fd39a65b5de8](.artifacts/records/project__acceptance/rec-b0782695-b6a8-443a-b1ed-fd39a65b5de8.md))_

## dashboard

### Position
- **dashboard**: Phases 1-18 done. quiet-header is on main at dccb4d1. No phase is planned.; effort _(id: [rec-c5404f0b-e8a8-4abc-8097-5b1640f585c8](.artifacts/records/project__current-position/rec-c5404f0b-e8a8-4abc-8097-5b1640f585c8.md))_

## dashboard-app

### Acceptance
- **dashboard-app**: A Textual pilot test at 60 and 120 columns finds the goal, progress, tiles, task rows, needs-you items, and activity for a temp store, and sees a redraw after a store change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-607927c0-6e77-499d-ae1f-ee7a890cfd07](.artifacts/records/project__acceptance/rec-607927c0-6e77-499d-ae1f-ee7a890cfd07.md))_

### Amendment
- **dashboard-app**: dashboard-app; dashboard-ui _(id: [rec-28e50357-bdf1-45e3-8b4c-eecbdd3839d2](.artifacts/records/project__assignment-amendment/rec-28e50357-bdf1-45e3-8b4c-eecbdd3839d2.md))_

## dashboard-autonomy-dashboard-bugfix

### Constraint
- **dashboard-autonomy-dashboard-bugfix**: Plan and promote each next phase without asking once the current one closes; stop only for failures, needs-human findings, or a push or merge; dashboard-bugfix; dashboard _(id: [rec-d758928c-9ec7-4707-8093-e9ba5a5a7cc4](.artifacts/records/project__constraint/rec-d758928c-9ec7-4707-8093-e9ba5a5a7cc4.md))_

## dashboard-autonomy-dashboard-features

### Constraint
- **dashboard-autonomy-dashboard-features**: Plan and promote each next phase without asking once the current one closes; stop only for failures, needs-human findings, or a push or merge; dashboard-features; dashboard _(id: [rec-b67f5d65-3a49-440a-b695-c02c2b1bd644](.artifacts/records/project__constraint/rec-b67f5d65-3a49-440a-b695-c02c2b1bd644.md))_

## dashboard-branches-dashboard-bugfix

### Constraint
- **dashboard-branches-dashboard-bugfix**: Work on stacked branches: fix/dashboard-bugfix from main, feat/dashboard-features from it; one commit per task; commit at each effort end; no merge to main until both efforts are done and the user says so; dashboard-bugfix; dashboard _(id: [rec-c99978db-a6a5-496c-a8ea-6f88e1bdcc4b](.artifacts/records/project__constraint/rec-c99978db-a6a5-496c-a8ea-6f88e1bdcc4b.md))_

## dashboard-branches-dashboard-features

### Constraint
- **dashboard-branches-dashboard-features**: Work on stacked branches: fix/dashboard-bugfix from main, feat/dashboard-features from it; one commit per task; commit at each effort end; no merge to main until both efforts are done and the user says so; dashboard-features; dashboard _(id: [rec-c1e52997-e4a1-4599-a252-2f9b0f7f5de9](.artifacts/records/project__constraint/rec-c1e52997-e4a1-4599-a252-2f9b0f7f5de9.md))_

## dashboard-closed-goals

### Acceptance
- **dashboard-closed-goals**: build_model leaves out an effort whose goal has status closed; tdd; workflow-loop; python3 -m pytest tests/test_dashboard_model.py -q _(id: [rec-f02ec3b2-3bd6-496f-933a-1506d3b4a877](.artifacts/records/project__acceptance/rec-f02ec3b2-3bd6-496f-933a-1506d3b4a877.md))_

## dashboard-launcher

### Acceptance
- **dashboard-launcher**: Given a temp repo: with ~/.artifacts/<repo> it uses that store; with only <repo>/.artifacts it uses that; with none it prints a no-store message; with a store whose contract lacks project:dashboard it prints a missing-view message; ADAPTIVE_ARTIFACTS_BIN overrides the binary; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-e4e1b7a5-4c4b-45ce-8a02-bb12452e15ea](.artifacts/records/project__acceptance/rec-e4e1b7a5-4c4b-45ce-8a02-bb12452e15ea.md))_

## dashboard-launcher-switch

### Acceptance
- **dashboard-launcher-switch**: Launcher and tmux tests pass with scripts/dashboard running the Textual app; tdd; dashboard; python3 -m pytest tests/test_dashboard_launcher.py tests/test_tmux_integration.py -q _(id: [rec-7fbf25bf-c639-424e-a4a2-66a5d640f23a](.artifacts/records/project__acceptance/rec-7fbf25bf-c639-424e-a4a2-66a5d640f23a.md))_

## dashboard-read-only

### Constraint
- **dashboard-read-only**: The dashboard never writes to the artifact store; actions that change records go through the parent Claude session; scripts/dashboard_app.py and scripts/dashboard_model.py; dashboard _(id: [rec-b4685bf6-c27e-4989-9815-9a2559ab8fee](.artifacts/records/project__constraint/rec-b4685bf6-c27e-4989-9815-9a2559ab8fee.md))_

## dashboard-read-only-dashboard-bugfix

### Constraint
- **dashboard-read-only-dashboard-bugfix**: The dashboard never writes to the store; copy actions hand work to the agent; dashboard-bugfix; dashboard _(id: [rec-47aeb7b3-42ac-450d-876f-63029610f77d](.artifacts/records/project__constraint/rec-47aeb7b3-42ac-450d-876f-63029610f77d.md))_

## dashboard-read-only-dashboard-features

### Constraint
- **dashboard-read-only-dashboard-features**: The dashboard never writes to the store; copy actions hand work to the agent; dashboard-features; dashboard _(id: [rec-641107fa-4a3f-4d31-b739-36fe0e4ad9db](.artifacts/records/project__constraint/rec-641107fa-4a3f-4d31-b739-36fe0e4ad9db.md))_

## dashboard-snapshot

### Acceptance
- **dashboard-snapshot**: Tests against a temp store show the snapshot groups records per effort and classifies tasks, needs-you items, phase progress, and recent activity correctly; tdd; dashboard; python3 -m pytest tests/test_dashboard_model.py -q _(id: [rec-8f27fb0c-0113-4d37-9083-5f9767e2d6e6](.artifacts/records/project__acceptance/rec-8f27fb0c-0113-4d37-9083-5f9767e2d6e6.md))_

### Amendment
- **dashboard-snapshot**: dashboard-snapshot; dashboard-ui _(id: [rec-4c7d0765-e159-46f2-b4d4-c84dbbcd2d15](.artifacts/records/project__assignment-amendment/rec-4c7d0765-e159-46f2-b4d4-c84dbbcd2d15.md))_

## dashboard-status-segment

### Acceptance
- **dashboard-status-segment**: Against a seeded store the segment prints the correct running, ready and needs-you counts within 1 s; with no store it prints nothing and exits 0; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-e7e94ca1-9742-44b2-9fe1-7a014b58ef3d](.artifacts/records/project__acceptance/rec-e7e94ca1-9742-44b2-9fe1-7a014b58ef3d.md))_

## detail-redraw-race

### Acceptance
- **detail-redraw-race**: The root cause is named, and test_detail_screen_redraws_when_the_store_changes passes 30 times in a row alone and in two full-suite runs; check; dashboard; for i in $(seq 30); do uv run --with textual --with pytest python -m pytest 'tests/test_dashboard_app.py::test_detail_screen_redraws_when_the_store_changes' -q || exit 1; done _(id: [rec-c4742568-196f-4b86-89ea-4a12a7490978](.artifacts/records/project__acceptance/rec-c4742568-196f-4b86-89ea-4a12a7490978.md))_

### Finding
- **detail-redraw-race**: The detail screen paint queried #related after awaits without re-checking that the screen was still attached, so a poll-triggered redraw racing teardown raised NoMatches; Traceback apply -> paint query_one(#related) in 5 of 25 loaded runs; 30/30 loaded and 30/30 alone after re-checking is_attached after the awaits; The test fails again with NoMatches after 03d561c; none _(id: [rec-5018f385-7ec4-40ba-9736-d651d7b2af88](.artifacts/records/project__finding/rec-5018f385-7ec4-40ba-9736-d651d7b2af88.md))_

## discuss-skill

### Acceptance
- **discuss-skill**: skills/discuss/SKILL.md exists and every adaptive-artifacts invocation in it passes the skill/contract consistency test; tdd; workflow-loop; python3 -m pytest tests/test_skill_contract_consistency.py tests/test_discuss_skill.py -q _(id: [rec-29f17960-fd84-4c12-9d0b-9589e7b71980](.artifacts/records/project__acceptance/rec-29f17960-fd84-4c12-9d0b-9589e7b71980.md))_

## e2e-real-execute-run

### Acceptance
- **e2e-real-execute-run**: The frame log shows task one go ready, running, done and task two go waiting, ready, running, done, driven by real subagent dispatch; the user signs after reading it; manual; dashboard _(id: [rec-70f9c43d-01d7-438e-8df6-ad97b7fd46ce](.artifacts/records/project__acceptance/rec-70f9c43d-01d7-438e-8df6-ad97b7fd46ce.md))_

## e2e-scripted-run

### Acceptance
- **e2e-scripted-run**: After each step the live side pane shows exactly the expected section map within 5 s and the status segment shows the matching counts; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests -q -k e2e _(id: [rec-5f7f36da-ec22-4619-b31b-8ff7fb3b85ee](.artifacts/records/project__acceptance/rec-5f7f36da-ec22-4619-b31b-8ff7fb3b85ee.md))_

## effort-switch-focus

### Acceptance
- **effort-switch-focus**: Pilot test: with an effort-level question on a live effort, tab and shift+tab reach a finished effort and stay there; the test fails before the fix; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k switch _(id: [rec-768f3192-cdcf-45d9-9421-2282f78e8bef](.artifacts/records/project__acceptance/rec-768f3192-cdcf-45d9-9421-2282f78e8bef.md))_

## execute-landing

### Acceptance
- **execute-landing**: execute-phase creates the worktree, confines code writes to it, keeps store writes on the primary checkout, commits the branch, merges to main, commits the store, and does not push unless Landing names push as a stop; a phase with no Landing stays in the current checkout; tdd; workflow-loop; python3 -m pytest tests/test_execute_landing.py -q _(id: [rec-b89f9c9f-d9f4-4db9-8375-3f877388c961](.artifacts/records/project__acceptance/rec-b89f9c9f-d9f4-4db9-8375-3f877388c961.md))_

## execute-wave-dispatch

### Acceptance
- **execute-wave-dispatch**: execute-phase runs an inline wave in this session and a subagent wave as one worker per task, treats a missing executor as subagent, and does not ask for a recipe when Approach is present; tdd; workflow-loop; python3 -m pytest tests/test_execute_wave_dispatch.py -q _(id: [rec-c95855b2-e077-44d7-ab61-b8b70ec6f7df](.artifacts/records/project__acceptance/rec-c95855b2-e077-44d7-ab61-b8b70ec6f7df.md))_

## finished-effort-view

### Acceptance
- **finished-effort-view**: Model test: finished is true only when every phase and counted task is done. Pilot tests: a finished effort shows All N tasks done under Active, sorts after a live effort, and has a dimmed label; a live effort with an empty filter still shows No tasks match; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py tests/test_dashboard_app.py -q -k finished _(id: [rec-cc216932-78bb-4df8-b80d-8da0eb287a9c](.artifacts/records/project__acceptance/rec-cc216932-78bb-4df8-b80d-8da0eb287a9c.md))_

## goal-status-field

### Acceptance
- **goal-status-field**: A goal and position superseded with status closed are absent from handoff and dashboard views; records without status still render; tdd; workflow-loop; python3 -m pytest tests/test_goal_close.py -q _(id: [rec-1f0b047c-50e6-4c2d-8c91-10a6c7d220e0](.artifacts/records/project__acceptance/rec-1f0b047c-50e6-4c2d-8c91-10a6c7d220e0.md))_

## handoff-by-effort

### Acceptance
- **handoff-by-effort**: A work-item and a phase position render under their effort section in handoff, not under their own subject; tdd; workflow-loop; python3 -m pytest tests/test_phase_position.py -q _(id: [rec-ca16958b-e8a5-4605-a0cd-7bf1a556bd31](.artifacts/records/project__acceptance/rec-ca16958b-e8a5-4605-a0cd-7bf1a556bd31.md))_

## header-chrome

### Acceptance
- **header-chrome**: Six status tabs at 120 columns read Active (3) with no leading digit, a highlighted selected word, and a dim tally; keys 1-6 still filter; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k "tab_row or tab_labels or number_keys_filter or status_tabs_are_six" _(id: [rec-82ce4065-bcee-43f2-97b2-dfd7a995d323](.artifacts/records/project__acceptance/rec-82ce4065-bcee-43f2-97b2-dfd7a995d323.md))_

## header-chrome-headers

### Acceptance
- **header-chrome-headers**: Done phase header rows show the disclosure marker and no check glyph; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k done_phases_collapse _(id: [rec-c5330e71-ef6d-401a-856d-dbdfdeb167d6](.artifacts/records/project__acceptance/rec-c5330e71-ef6d-401a-856d-dbdfdeb167d6.md))_

## header-chrome-once

### Acceptance
- **header-chrome-once**: dashboard --once prints the parenthetical tab line and the collapsed stepper; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k once_tally _(id: [rec-f93137e4-8a54-4459-a68a-59963e362cbd](.artifacts/records/project__acceptance/rec-f93137e4-8a54-4459-a68a-59963e362cbd.md))_

## header-chrome-stepper

### Acceptance
- **header-chrome-stepper**: A stepper with more than two done phases shows N done, the current phase, and one next phase, with no green check, and click expands the finished titles; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k stepper _(id: [rec-c87d332c-5c16-49a9-9ebe-8991ae8c0060](.artifacts/records/project__acceptance/rec-c87d332c-5c16-49a9-9ebe-8991ae8c0060.md))_

## heading-spacing

### Acceptance
- **heading-spacing**: Pilot test: in phase detail the line above each body heading is not blank (except the first line of the panel); the test fails before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k heading _(id: [rec-e3cb339f-2f12-42bd-9dab-4439494334aa](.artifacts/records/project__acceptance/rec-e3cb339f-2f12-42bd-9dab-4439494334aa.md))_

## keyboard-focus

### Acceptance
- **keyboard-focus**: Keyboard-only pilot tests move the cursor to a task below the first row and open it with enter, keep table focus after tab switch and after esc from detail, scroll to Activity with PgDn, and scroll the detail screen with arrows; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-97f2e49d-f874-4969-929c-d6c37a1ec61b](.artifacts/records/project__acceptance/rec-97f2e49d-f874-4969-929c-d6c37a1ec61b.md))_

### Finding
- **keyboard-focus**: Nothing focused the task table; the effort tab strip kept focus, so arrows never moved the cursor and enter always opened row 0; Real-store probe and 7 red keys-only tests before 2d1a3be; all pass after; A keys-only test fails to move or open a task after 2d1a3be; none _(id: [rec-60d1962e-aeb0-4972-8002-f424c61f615a](.artifacts/records/project__finding/rec-60d1962e-aeb0-4972-8002-f424c61f615a.md))_

## label-view-fields

### Acceptance
- **label-view-fields**: A view with label_fields true renders field: value pairs; a view without it renders exactly as before; tdd; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q _(id: [rec-0a970468-5d80-49a0-bf80-d5481a65814b](.artifacts/records/project__acceptance/rec-0a970468-5d80-49a0-bf80-d5481a65814b.md))_

## model-fixture-reuse

### Acceptance
- **model-fixture-reuse**: Every test in tests/test_dashboard_model.py still passes and no test setup takes longer than 0.3s; check; test-suite-speed; python3 -m pytest tests/test_dashboard_model.py -q --durations=5 _(id: [rec-660d84e9-e3f2-421c-8094-db9c8427c8da](.artifacts/records/project__acceptance/rec-660d84e9-e3f2-421c-8094-db9c8427c8da.md))_

## model-fixture-reuse-total

### Acceptance
- **model-fixture-reuse-total**: The full suite wall time is under 50s (baseline 101s) and user+sys CPU time does not exceed the baseline of 58s; check; test-suite-speed; time python3 -m pytest -q _(id: [rec-db700c2c-4b03-4fb5-9aec-9517316abf2b](.artifacts/records/project__acceptance/rec-db700c2c-4b03-4fb5-9aec-9517316abf2b.md))_

## needs-you-list

### Acceptance
- **needs-you-list**: Pilot tests: n focuses the list, arrows move, enter opens the task detail for a linked item and the Needs-you detail with full text for a question, esc returns, c copies the subject; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k needs_you _(id: [rec-7c8645dc-e818-4d9d-b2d1-807437c46a90](.artifacts/records/project__acceptance/rec-7c8645dc-e818-4d9d-b2d1-807437c46a90.md))_

## needs-you-records

### Acceptance
- **needs-you-records**: Model tests show the new item fields, task linking for slug and slug-prefix subjects, and no link for effort-level questions; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py -q -k needs _(id: [rec-79256814-feaf-46b4-b5da-3c97ec0838c0](.artifacts/records/project__acceptance/rec-79256814-feaf-46b4-b5da-3c97ec0838c0.md))_

## needs-you-tab-removal

### Acceptance
- **needs-you-tab-removal**: Six status tabs on keys 1-6 with no Needs you tab; the panel title reads Needs you N for N items, including effort-level questions; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py tests/test_dashboard_view.py -q _(id: [rec-e781be72-47b4-4705-8bb4-82f57f1391ef](.artifacts/records/project__acceptance/rec-e781be72-47b4-4705-8bb4-82f57f1391ef.md))_

## package-install

### Acceptance
- **package-install**: A plugin install made with sync-plugin.sh runs bin/dashboard --once and prints a frame.; check; dashboard; d=$(mktemp -d) && bash scripts/sync-plugin.sh "$d/p" && test -d "$d/p/dashboard" && "$d/p/dashboard/bin/dashboard" --once _(id: [rec-0379e3d0-879a-4bc5-982a-7ed054623149](.artifacts/records/project__acceptance/rec-0379e3d0-879a-4bc5-982a-7ed054623149.md))_

## package-install-docs

### Acceptance
- **package-install-docs**: The README and tmux conf name no path under scripts/ for the dashboard.; check; dashboard; ! grep -nE 'scripts/(dashboard|tmux-dashboard)' README.md dashboard/tmux.conf _(id: [rec-67e721d5-5b8f-482f-b2d7-f9f25c8ec7e3](.artifacts/records/project__acceptance/rec-67e721d5-5b8f-482f-b2d7-f9f25c8ec7e3.md))_

## package-move

### Acceptance
- **package-move**: The dashboard files are in dashboard/, none remain in scripts/, and the non-tmux dashboard tests pass at the new paths.; tdd; dashboard; test ! -e scripts/dashboard_app.py && test ! -e scripts/dashboard_model.py && test ! -e scripts/artifact_store.py && uv run --with pytest --with textual pytest tests/test_dashboard_app.py tests/test_dashboard_model.py tests/test_dashboard_launcher.py tests/test_dashboard_status.py tests/test_dashboard_view.py tests/test_dashboard_integration.py _(id: [rec-976f8b89-c8c7-4ced-855d-c8c5b3c6c2fb](.artifacts/records/project__acceptance/rec-976f8b89-c8c7-4ced-855d-c8c5b3c6c2fb.md))_

## pane-width-stable

### Acceptance
- **pane-width-stable**: The stepper test passes 20 of 20 runs of the full app test file under -n 4, and a new test that toggles the pane scrollbar fails before the fix; tdd; dashboard; for i in $(seq 20); do uv run -q --with textual --with pytest --with pytest-xdist python -m pytest tests/test_dashboard_app.py -q -n 4 -p no:cacheprovider || break; done _(id: [rec-ef569598-f20a-4623-ba96-4f0c32edf9f1](.artifacts/records/project__acceptance/rec-ef569598-f20a-4623-ba96-4f0c32edf9f1.md))_

## phase-detail-tasks

### Acceptance
- **phase-detail-tasks**: Pilot tests: in a phase detail, arrows move through tasks, enter opens the task detail, and esc returns to the phase detail; the tests fail before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k phase_task _(id: [rec-2356a60d-0eda-499f-b3ab-ee4746d6aa45](.artifacts/records/project__acceptance/rec-2356a60d-0eda-499f-b3ab-ee4746d6aa45.md))_

## phase-position-skills

### Acceptance
- **phase-position-skills**: Skills document the per-phase position with payloads the contract accepts; skill/contract consistency tests pass; tdd; workflow-loop; python3 -m pytest tests/test_skill_contract_consistency.py tests/test_phase_position.py -q _(id: [rec-9f326a41-7f0f-4d28-89c6-069154ad5a65](.artifacts/records/project__acceptance/rec-9f326a41-7f0f-4d28-89c6-069154ad5a65.md))_

## phase-sections

### Acceptance
- **phase-sections**: Model and pilot tests group tasks by phase, collapse done and planned phases, fold older done phases, toggle headers by key and click, open a phase detail with body and decisions, show awaiting sign-off, and show effort-wide progress; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py tests/test_dashboard_model.py -q _(id: [rec-611e26b5-b891-4e71-8951-3ebf07ecc715](.artifacts/records/project__acceptance/rec-611e26b5-b891-4e71-8951-3ebf07ecc715.md))_

## plan-landing-rules

### Acceptance
- **plan-landing-rules**: plan-phase requires a Landing section with branch, worktree, base, close, and push only as a named stop before plan review, and incidental work skips it; tdd; workflow-loop; python3 -m pytest tests/test_plan_landing.py -q _(id: [rec-9f4b54cc-334e-4b5c-92fa-df0b713d662e](.artifacts/records/project__acceptance/rec-9f4b54cc-334e-4b5c-92fa-df0b713d662e.md))_

## plan-wave-rules

### Acceptance
- **plan-wave-rules**: plan-phase requires a recipe, one shared executor of inline or subagent per wave, and phase size, stops, and collision notes, and it does not open plan review until those are present; tdd; workflow-loop; python3 -m pytest tests/test_plan_wave_rules.py -q _(id: [rec-b1c39c5f-6758-426d-bdcf-0ff6c57bcbc5](.artifacts/records/project__acceptance/rec-b1c39c5f-6758-426d-bdcf-0ff6c57bcbc5.md))_

## readme-quickstart

### Acceptance
- **readme-quickstart**: The README has a Quick start section that shows the TPM plugin line and a run-shell line, and names no dashboard/tmux.conf or SE_WORKFLOW_DASHBOARD.; check; dashboard; grep -q '^## Quick start' README.md && grep -q "@plugin 'andrewy1n/se-workflow'" README.md && grep -q 'run-shell' README.md && ! grep -nE 'dashboard/tmux\.conf|SE_WORKFLOW_DASHBOARD|source-file' README.md _(id: [rec-757d4417-3c33-4df0-a29e-03c1c09bb8ad](.artifacts/records/project__acceptance/rec-757d4417-3c33-4df0-a29e-03c1c09bb8ad.md))_

## recency-selection

### Acceptance
- **recency-selection**: A role with a 24h recorded_at window selects a record recorded 1h ago and skips one recorded 48h ago; a malformed window fails contract resolution; tdd; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q _(id: [rec-d854ca7d-767b-4729-92e1-18ef8853d92c](.artifacts/records/project__acceptance/rec-d854ca7d-767b-4729-92e1-18ef8853d92c.md))_

## rj-join

### Acceptance
- **rj-join**: A fixture with two sessions and five records attaches each record correctly, marks the overlap record ambiguous on both sessions, and leaves the outside and other-project records unattached.; tdd; session-analysis; python3 -m pytest -q tests/test_record_join.py _(id: [rec-fa22cc2f-06e1-491e-a277-9c9ab01fa21e](.artifacts/records/project__acceptance/rec-fa22cc2f-06e1-491e-a277-9c9ab01fa21e.md))_

## rj-record-reader

### Acceptance
- **rj-record-reader**: Stub CLI output yields metadata rows with parsed UTC times and no body text.; tdd; session-analysis; python3 -m pytest -q tests/test_record_reader.py _(id: [rec-f89ab522-1803-4881-b257-f9a885c2d0de](.artifacts/records/project__acceptance/rec-f89ab522-1803-4881-b257-f9a885c2d0de.md))_

## rj-report-records

### Acceptance
- **rj-report-records**: With --records the report adds record counts per session on a fixture, and without the flag the output is byte-identical to before.; tdd; session-analysis; python3 -m pytest -q tests/test_session_report.py _(id: [rec-193dfd71-f09c-43b5-95db-e685a4a80e4f](.artifacts/records/project__acceptance/rec-193dfd71-f09c-43b5-95db-e685a4a80e4f.md))_

### Finding
- **rj-report-records**: The project-plus-time-window join leaves 70% of attached records ambiguous (386 of 553), so per-session record counts are unreliable for overlapping sessions.; Real run of session_report.py --records over 247 sessions: 8 sessions have records, 553 records attach, 386 attach to two or more sessions.; Records carry a session id, or sessions get narrower activity windows that remove the overlap.; human _(id: [rec-b8213c07-3cf9-4b56-a2a5-e9f56bd93f78](.artifacts/records/project__finding/rec-b8213c07-3cf9-4b56-a2a5-e9f56bd93f78.md))_

## route-through-discuss

### Acceptance
- **route-through-discuss**: engage, plan-phase, execute-phase and README route through discuss and the review gate; consistency tests pass; tdd; workflow-loop; python3 -m pytest tests/test_skill_contract_consistency.py tests/test_discuss_skill.py -q _(id: [rec-aac400ee-30c6-4fd2-a3ba-9fbd756f740a](.artifacts/records/project__acceptance/rec-aac400ee-30c6-4fd2-a3ba-9fbd756f740a.md))_

## sa-code-in-plugin-repo

### Constraint
- **sa-code-in-plugin-repo**: The code lives in this plugin repo under scripts/ and skills/.; session-analysis; session-analysis _(id: [rec-1c7e8113-66b4-44e2-9183-b441364268a4](.artifacts/records/project__constraint/rec-1c7e8113-66b4-44e2-9183-b441364268a4.md))_

## sa-propose-only

### Constraint
- **sa-propose-only**: The analysis skill proposes edits and changes nothing until the user picks a candidate.; analysis-skill; session-analysis _(id: [rec-f0c6d77a-de74-4f43-a52c-28afe55af78c](.artifacts/records/project__constraint/rec-f0c6d77a-de74-4f43-a52c-28afe55af78c.md))_

## sa-reports-local

### Constraint
- **sa-reports-local**: Reports hold metrics and references, not raw transcript text, and stay local.; report output; session-analysis _(id: [rec-2f9e4b33-f25f-4f27-b860-1939df3fe318](.artifacts/records/project__constraint/rec-2f9e4b33-f25f-4f27-b860-1939df3fe318.md))_

## sa-script-read-only

### Constraint
- **sa-script-read-only**: The analysis script reads the store and never writes to it.; scripts; session-analysis _(id: [rec-bcd11e56-a54f-4d85-9055-63d13bb03ee8](.artifacts/records/project__constraint/rec-bcd11e56-a54f-4d85-9055-63d13bb03ee8.md))_

## session-analysis

### Position
- **session-analysis**: All four phases done. Run the analyze-sessions skill to review sessions. Code and skill are uncommitted. Two findings are open: the join is approximate, and the skill has minor judgment gaps.; repo _(id: [rec-428082e4-c07e-4c73-81c0-ffcb6c5e876c](.artifacts/records/project__current-position/rec-428082e4-c07e-4c73-81c0-ffcb6c5e876c.md))_

## status-line-from-snapshot

### Acceptance
- **status-line-from-snapshot**: For a seeded store, every status line names an effort in the app snapshot with matching counts, and an effort with no goal prints nothing; the test fails before the fix; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_status.py -q _(id: [rec-fb5c210c-4e78-42c4-8fb9-f8f585e3f5f8](.artifacts/records/project__acceptance/rec-fb5c210c-4e78-42c4-8fb9-f8f585e3f5f8.md))_

## status-tab-row

### Acceptance
- **status-tab-row**: Pilot tests: six tabs on one row at 120 columns, wrapped at 60, each label starts with its number key; the tests fail before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k tab_row _(id: [rec-ba223a32-d09b-4dd0-9256-101bd04d0ea1](.artifacts/records/project__acceptance/rec-ba223a32-d09b-4dd0-9256-101bd04d0ea1.md))_

## status-tabs

### Acceptance
- **status-tabs**: Pilot tests at 60 and 120 columns show counts on every tab, default to Active, filter the table by each tab via keys and click, show Needs you tasks from open items, combine with the / filter, and have no d binding; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-5a31e5b1-1af0-4738-bf89-20d16bf3dcaa](.artifacts/records/project__acceptance/rec-5a31e5b1-1af0-4738-bf89-20d16bf3dcaa.md))_

### Finding
- **status-tabs**: status-tabs gap closed: 7 tabs, keys 1-7, left/right and README landed at 75e530c; Execution report rec-10a142d4 and a parent re-run of 116 passing tests at 75e530c; A tab, key or README row from the description is missing; none _(id: [rec-94362ae8-0f01-4ad1-bfcd-cffa426566b8](.artifacts/records/project__finding/rec-94362ae8-0f01-4ad1-bfcd-cffa426566b8.md))_

### Amendment
- **status-tabs**: status-tabs; dashboard-ui _(id: [rec-9d00fbec-bc87-40b3-b37b-38e00bea73db](.artifacts/records/project__assignment-amendment/rec-9d00fbec-bc87-40b3-b37b-38e00bea73db.md))_
- **status-tabs**: status-tabs; dashboard-ui _(id: [rec-e076f208-265b-4f3a-8365-0f04b6b421a8](.artifacts/records/project__assignment-amendment/rec-e076f208-265b-4f3a-8365-0f04b6b421a8.md))_

## stepper-wrap

### Acceptance
- **stepper-wrap**: Pilot test at 60 columns: every stepper line starts with a phase glyph and no line ends with a bare glyph, and no line is wider than the pane; the test fails before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k stepper _(id: [rec-c2df3f61-8b0b-44d8-89b3-f3033ebcf9d0](.artifacts/records/project__acceptance/rec-c2df3f61-8b0b-44d8-89b3-f3033ebcf9d0.md))_

## table-focus

### Acceptance
- **table-focus**: Pick an empty tab, pick Active, press down: the cursor is on row 1 and enter opens that row; the test fails before the fix; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k focus _(id: [rec-2536ed50-f949-40fe-a914-f283c9633975](.artifacts/records/project__acceptance/rec-2536ed50-f949-40fe-a914-f283c9633975.md))_

## task-detail-links

### Acceptance
- **task-detail-links**: Pilot tests: in a task detail, enter on a dependency opens that task, enter on a blocked task opens it, enter on the phase opens the phase detail, and esc walks back one screen at a time; the tests fail before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k link _(id: [rec-79b9e2f6-49a8-4d48-8788-0da94d698726](.artifacts/records/project__acceptance/rec-79b9e2f6-49a8-4d48-8788-0da94d698726.md))_

## task-detail-model

### Acceptance
- **task-detail-model**: Tests against a temp store show the loader returns the work-item, dependency links, acceptances with their latest check-run, the ordered timeline with report bodies, and related findings, and ignores another task whose slug shares a prefix; tdd; dashboard; python3 -m pytest tests/test_dashboard_model.py -q _(id: [rec-8f020a2f-f7de-43e3-b46f-423d52e44fe4](.artifacts/records/project__acceptance/rec-8f020a2f-f7de-43e3-b46f-423d52e44fe4.md))_

## task-detail-module

### Acceptance
- **task-detail-module**: TaskDetailScreen is defined in dashboard/task_detail.py, not app.py, and the dashboard app tests pass.; tdd; dashboard; ! grep -n '^class TaskDetailScreen' dashboard/app.py && grep -c '^class TaskDetailScreen' dashboard/task_detail.py && uv run --with pytest --with textual pytest tests/test_dashboard_app.py _(id: [rec-7f83addf-fb83-4129-9116-b02371346c5d](.artifacts/records/project__acceptance/rec-7f83addf-fb83-4129-9116-b02371346c5d.md))_

## task-detail-screen

### Acceptance
- **task-detail-screen**: Textual pilot tests at 60 and 160 columns open the detail screen by Enter and by click, find every section's content for a seeded task, see a redraw after a store change, and return to the same row on Esc; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-421586f5-5f49-4a47-b715-eeb09ad69b90](.artifacts/records/project__acceptance/rec-421586f5-5f49-4a47-b715-eeb09ad69b90.md))_

### Amendment
- **task-detail-screen**: task-detail-screen; dashboard-ui _(id: [rec-6956b3e6-05e0-49a3-92ed-79f0db8c4db8](.artifacts/records/project__assignment-amendment/rec-6956b3e6-05e0-49a3-92ed-79f0db8c4db8.md))_

## task-list-filters

### Acceptance
- **task-list-filters**: Pilot tests at 60 and 120 columns narrow the table by typed text, clear it with Esc, hide and show done tasks with d, keep both across a store refresh, and show them in the panel title; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-982fcf31-6ef8-41aa-97a6-03ec860bfccb](.artifacts/records/project__acceptance/rec-982fcf31-6ef8-41aa-97a6-03ec860bfccb.md))_

## task-row-cells

### Acceptance
- **task-row-cells**: Pilot tests: a waiting row shows waits on with its unfinished dependencies, a running row shows its running time, the task detail shows it, and the grouped table has no phase column at 60 and 120 columns; the tests fail before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k 'waits or running or phase_column' _(id: [rec-daa1a988-73f2-45f9-8cde-f795662613c1](.artifacts/records/project__acceptance/rec-daa1a988-73f2-45f9-8cde-f795662613c1.md))_

## task-row-model

### Acceptance
- **task-row-model**: Model tests: waits_on lists only unfinished dependency slugs, running_since is the latest assignment time for an in-progress task and None otherwise; the tests fail before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py -q -k 'waits or running' _(id: [rec-60e78986-208c-43d5-8207-9803afeab4df](.artifacts/records/project__acceptance/rec-60e78986-208c-43d5-8207-9803afeab4df.md))_

## task-table-module

### Acceptance
- **task-table-module**: The task table, filter, section and cell code is defined in dashboard/tasks.py, not app.py, and the dashboard app tests pass.; tdd; dashboard; ! grep -nE '^(class TaskFilter|class SectionRow|def section_rows|def visible_tasks|class TaskTable)' dashboard/app.py && grep -c 'class TaskFilter' dashboard/tasks.py && uv run --with pytest --with textual pytest tests/test_dashboard_app.py tests/test_dashboard_tasks.py _(id: [rec-9a70606f-50c9-40b0-9b8c-107ff6573a06](.artifacts/records/project__acceptance/rec-9a70606f-50c9-40b0-9b8c-107ff6573a06.md))_

## terminal-view-format

### Acceptance
- **terminal-view-format**: Given a rendered dashboard, the formatter output has no id suffixes or banner, headings are bold only with colour on, no line exceeds the width, and an empty view gives the empty-state line; tdd; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q _(id: [rec-afb68d05-d961-45dd-813e-948c8e137722](.artifacts/records/project__acceptance/rec-afb68d05-d961-45dd-813e-948c8e137722.md))_

## test-suite-speed

### Acceptance
- **test-suite-speed**: All 262 tests pass, full suite wall time is at most 158s (half of the 317s clean-HEAD baseline), CPU time stays under 250s, and no timeout or deadline value is larger than before the change; check; test-suite-speed; time uv run --with textual --with pytest python -m pytest tests -q _(id: [rec-6e6e5c69-9ab0-44f3-9016-49c3512fcd99](.artifacts/records/project__acceptance/rec-6e6e5c69-9ab0-44f3-9016-49c3512fcd99.md))_

## tm-cli

### Acceptance
- **tm-cli**: The command over a fixture projects directory prints valid JSON with one summary per session and no message text.; tdd; session-analysis; python3 -m pytest -q tests/test_session_report.py _(id: [rec-be629630-2798-4a55-92ca-322aba930e94](.artifacts/records/project__acceptance/rec-be629630-2798-4a55-92ca-322aba930e94.md))_

## tm-parse-events

### Acceptance
- **tm-parse-events**: A fixture with a malformed line and an unknown event type yields all valid events and a bad-line count of 1.; tdd; session-analysis; python3 -m pytest -q tests/test_session_metrics.py -k parse _(id: [rec-2df7a704-c3ba-43a0-966d-42474d3c2318](.artifacts/records/project__acceptance/rec-2df7a704-c3ba-43a0-966d-42474d3c2318.md))_

## tm-session-fields

### Acceptance
- **tm-session-fields**: A fixture yields the expected session id, branch, duration, turn count, cost and skill names.; tdd; session-analysis; python3 -m pytest -q tests/test_session_fields.py _(id: [rec-5f8ebfcf-f591-4f07-932d-65fabc8871fb](.artifacts/records/project__acceptance/rec-5f8ebfcf-f591-4f07-932d-65fabc8871fb.md))_

## tm-tool-metrics

### Acceptance
- **tm-tool-metrics**: A fixture with 5 tool calls, 2 errors and 1 retry yields exactly those counts per tool name.; tdd; session-analysis; python3 -m pytest -q tests/test_session_tools.py _(id: [rec-eb5399be-74fd-4403-bf2d-69fb1cb5bce9](.artifacts/records/project__acceptance/rec-eb5399be-74fd-4403-bf2d-69fb1cb5bce9.md))_

## tmux-conf-removal

### Acceptance
- **tmux-conf-removal**: No code, test or script refers to dashboard/tmux.conf or SE_WORKFLOW_DASHBOARD, and the file is gone.; check; dashboard; test ! -e dashboard/tmux.conf && ! grep -rnE 'dashboard/tmux\.conf|SE_WORKFLOW_DASHBOARD' dashboard scripts tests _(id: [rec-3aa70906-2826-4ae6-86f0-1b6d7a206306](.artifacts/records/project__acceptance/rec-3aa70906-2826-4ae6-86f0-1b6d7a206306.md))_

## tmux-conf-removal-install

### Acceptance
- **tmux-conf-removal-install**: A plugin install made with sync-plugin.sh contains an executable se-workflow.tmux.; check; dashboard; d=$(mktemp -d) && bash scripts/sync-plugin.sh "$d/p" && test -x "$d/p/se-workflow.tmux" _(id: [rec-202b31bb-dba8-4bb0-ab9b-cae95af2386e](.artifacts/records/project__acceptance/rec-202b31bb-dba8-4bb0-ab9b-cae95af2386e.md))_

## tmux-entry-script

### Acceptance
- **tmux-entry-script**: With no options set, prefix A is a popup and prefix S a side pane of the launcher, both in the pane directory, using the path of the script's own directory.; tdd; dashboard; uv run --with pytest --with textual pytest -m tmux tests/test_tmux_entry.py -k default _(id: [rec-f6564330-b301-4302-a1d2-6e9c206c489b](.artifacts/records/project__acceptance/rec-f6564330-b301-4302-a1d2-6e9c206c489b.md))_

## tmux-entry-script-options

### Acceptance
- **tmux-entry-script-options**: Setting @dashboard-popup-key and @dashboard-pane-key before the script runs rebinds the keys and leaves A and S unbound.; tdd; dashboard; uv run --with pytest --with textual pytest -m tmux tests/test_tmux_entry.py -k custom_keys _(id: [rec-a19b9fe0-d373-4e93-a176-b941fa8236f0](.artifacts/records/project__acceptance/rec-a19b9fe0-d373-4e93-a176-b941fa8236f0.md))_

## tmux-suite-flake

### Finding
- **tmux-suite-flake**: One tmux integration test fails rarely: 1 of 19 serial tmux runs on e4484c4, test name not captured; Parent reruns on fix/dashboard-bugfix: 1 failed of 10 right after the xdist run, then 18 clean runs (15 full tmux runs, 3 full sequences); the extended popup test passed 12/12 alone; A tmux failure is captured with -rf and fixed, or 50 consecutive clean runs _(id: [rec-68330501-7b9a-446c-b24a-bf84af04e8e8](.artifacts/records/project__finding/rec-68330501-7b9a-446c-b24a-bf84af04e8e8.md))_

## tmux-test-waits

### Acceptance
- **tmux-test-waits**: The six failing tmux and e2e tests pass, and each tmux popup test takes under 4s; check; test-suite-speed; python3 -m pytest tests/test_tmux_integration.py tests/test_e2e_dashboard.py -q --durations=6 _(id: [rec-572fa450-b4a2-45bb-b52e-b5198f0e9b91](.artifacts/records/project__acceptance/rec-572fa450-b4a2-45bb-b52e-b5198f0e9b91.md))_

## unsigned-check-label

### Acceptance
- **unsigned-check-label**: An unsigned check reads as its acceptance criterion and task slug, never a rec- id, with a fallback when the acceptance is missing; the test fails before the fix; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py -q -k unsigned _(id: [rec-403febb3-cbe5-474d-8413-5687934c29d2](.artifacts/records/project__acceptance/rec-403febb3-cbe5-474d-8413-5687934c29d2.md))_

## verify-dashboard-actions-phase

### Acceptance
- **verify-dashboard-actions-phase**: The full test suite passes, including a tmux test that filters, copies a slug into the tmux buffer, and opens a commit view in the popup; check; dashboard; uv run --with textual --with pytest python -m pytest tests -q _(id: [rec-468f8719-9cf5-4262-aea7-6d372a9cd6a9](.artifacts/records/project__acceptance/rec-468f8719-9cf5-4262-aea7-6d372a9cd6a9.md))_

## verify-dashboard-actions-phase-signoff

### Acceptance
- **verify-dashboard-actions-phase-signoff**: The user tries filter, hide-done, copy, and commit view in the popup and the side pane and signs off; manual; dashboard _(id: [rec-aa7012e9-f5d9-427c-a0d5-74e173544519](.artifacts/records/project__acceptance/rec-aa7012e9-f5d9-427c-a0d5-74e173544519.md))_

## verify-dashboard-package

### Acceptance
- **verify-dashboard-package**: The dashboard launcher in the new package prints a frame for a seeded store (real entry point).; tdd; dashboard; uv run --with pytest --with textual pytest tests/test_dashboard_launcher.py tests/test_dashboard_integration.py _(id: [rec-f6216dac-0349-43a1-86a4-f5dd48eb2f51](.artifacts/records/project__acceptance/rec-f6216dac-0349-43a1-86a4-f5dd48eb2f51.md))_

## verify-dashboard-package-entry-points

### Acceptance
- **verify-dashboard-package-entry-points**: The tmux conf and a plugin install start the dashboard through the tmux tests.; check; dashboard; uv run --with pytest --with textual pytest -m tmux tests/test_tmux_integration.py tests/test_e2e_dashboard.py _(id: [rec-92205670-6c11-4582-8a88-f1b38046ccb8](.artifacts/records/project__acceptance/rec-92205670-6c11-4582-8a88-f1b38046ccb8.md))_

## verify-dashboard-package-full-suite

### Acceptance
- **verify-dashboard-package-full-suite**: The full suite passes.; check; dashboard; uv run --with pytest --with textual pytest _(id: [rec-02b72b32-48e0-46c4-a910-8b9d64ded6a5](.artifacts/records/project__acceptance/rec-02b72b32-48e0-46c4-a910-8b9d64ded6a5.md))_

## verify-dashboard-package-outside-scripts

### Acceptance
- **verify-dashboard-package-outside-scripts**: The dashboard code lives in dashboard/ and no dashboard file remains in scripts/.; check; dashboard; test -f dashboard/app.py && test -f dashboard/model.py && ! ls scripts | grep -i dashboard _(id: [rec-78759ece-bf5a-4584-9ce1-17650f1217c6](.artifacts/records/project__acceptance/rec-78759ece-bf5a-4584-9ce1-17650f1217c6.md))_

## verify-dashboard-package-task-modules

### Acceptance
- **verify-dashboard-package-task-modules**: The task code is in dashboard/tasks.py and dashboard/task_detail.py, not app.py.; check; dashboard; test -f dashboard/tasks.py && test -f dashboard/task_detail.py && ! grep -nE '^class (TaskFilter|TaskTable|TaskDetailScreen)' dashboard/app.py _(id: [rec-1d30f9a6-5236-45c6-8ba7-265bc6a9ca53](.artifacts/records/project__acceptance/rec-1d30f9a6-5236-45c6-8ba7-265bc6a9ca53.md))_

## verify-dashboard-view-phase

### Acceptance
- **verify-dashboard-view-phase**: The CLI integration test passes: after each lifecycle step every record appears in exactly its expected dashboard section; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests/test_dashboard_integration.py -q _(id: [rec-35c98548-4ccf-4c7c-8286-3a1e7ba21185](.artifacts/records/project__acceptance/rec-35c98548-4ccf-4c7c-8286-3a1e7ba21185.md))_

## verify-dashboard-view-phase-live

### Acceptance
- **verify-dashboard-view-phase-live**: The dashboard rendered from ~/.artifacts/se-workflow shows the watch-dashboard goal, phase dashboard-view, the open plugin question under needs-you, and each phase-1 task in the section its lifecycle implies; manual; dashboard; ~/adaptive-artifacts/bin/adaptive-artifacts --store ~/.artifacts/se-workflow view --id project:dashboard _(id: [rec-83fc3486-af5f-49af-9000-8d9fd6890f3c](.artifacts/records/project__acceptance/rec-83fc3486-af5f-49af-9000-8d9fd6890f3c.md))_

## verify-dashboard-view-phase-suites

### Acceptance
- **verify-dashboard-view-phase-suites**: Full test suites of both repos pass on the phase-1 changes; check; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q && cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-1a3c142c-b9c6-4f57-baf0-b38000b5bb9f](.artifacts/records/project__acceptance/rec-1a3c142c-b9c6-4f57-baf0-b38000b5bb9f.md))_

## verify-end-to-end-phase

### Acceptance
- **verify-end-to-end-phase**: Scripted end-to-end test and both full suites pass; check; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q && cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-a5e71d14-1f25-4868-a42e-3a2b17e16616](.artifacts/records/project__acceptance/rec-a5e71d14-1f25-4868-a42e-3a2b17e16616.md))_

## verify-end-to-end-phase-clear

### Acceptance
- **verify-end-to-end-phase-clear**: The watch-dashboard dashboard shows no Open Question, Needs Human, or Unsigned Manual Check; check; dashboard; ~/se-workflow/scripts/dashboard-status ~/se-workflow _(id: [rec-9dce7bb8-9cc7-4a4d-9ebd-48a749f7cc85](.artifacts/records/project__acceptance/rec-9dce7bb8-9cc7-4a4d-9ebd-48a749f7cc85.md))_

## verify-layout-phase

### Acceptance
- **verify-layout-phase**: The tmux popup layout test passes, README shows the tab row with number keys, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux -rf _(id: [rec-5d64f143-cdea-49dc-8cb4-7ca9fb9f2517](.artifacts/records/project__acceptance/rec-5d64f143-cdea-49dc-8cb4-7ca9fb9f2517.md))_

## verify-navigation-phase

### Acceptance
- **verify-navigation-phase**: The tmux popup navigation test passes, README documents detail links, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux -rf _(id: [rec-d1da938c-12b5-4cb9-9f02-e4a6731c1222](.artifacts/records/project__acceptance/rec-d1da938c-12b5-4cb9-9f02-e4a6731c1222.md))_

## verify-needs-you-data-phase

### Acceptance
- **verify-needs-you-data-phase**: The tmux popup tests pass with six tabs, a counted Needs you title and a readable unsigned line, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux _(id: [rec-fe83e6fe-5005-4c88-97e8-3c15e744047a](.artifacts/records/project__acceptance/rec-fe83e6fe-5005-4c88-97e8-3c15e744047a.md))_

## verify-needs-you-phase

### Acceptance
- **verify-needs-you-phase**: The tmux popup test for Needs you and finished efforts passes, README documents n and the Needs-you detail, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux _(id: [rec-d5958a14-e6a7-4c20-b110-5ae0c0ee54a3](.artifacts/records/project__acceptance/rec-d5958a14-e6a7-4c20-b110-5ae0c0ee54a3.md))_

### Amendment
- **verify-needs-you-phase**: verify-needs-you-phase; dashboard-features _(id: [rec-3192a53d-1a55-41cb-8f06-71bdbabdcbd2](.artifacts/records/project__assignment-amendment/rec-3192a53d-1a55-41cb-8f06-71bdbabdcbd2.md))_

## verify-phase-landing

### Acceptance
- **verify-phase-landing**: plan-phase and execute-phase name the same landing: branch phase/<phase-slug>, the sibling worktree, base main, merge into main, store commit on the primary checkout, and push only as a human stop; tdd; workflow-loop; python3 -m pytest tests/test_phase_landing.py tests/test_plan_landing.py tests/test_execute_landing.py -q _(id: [rec-5f277ff6-f5de-48ae-a3fa-43825f135561](.artifacts/records/project__acceptance/rec-5f277ff6-f5de-48ae-a3fa-43825f135561.md))_

## verify-phase-landing-execute

### Acceptance
- **verify-phase-landing-execute**: execute-phase creates the worktree, keeps the store on the primary checkout, merges the phase branch into main, and does not push unless Landing names push as a stop; tdd; workflow-loop; python3 -m pytest tests/test_execute_landing.py -q _(id: [rec-c376fad0-9993-4448-9e97-21adc7a1ec8d](.artifacts/records/project__acceptance/rec-c376fad0-9993-4448-9e97-21adc7a1ec8d.md))_

## verify-phase-landing-plan

### Acceptance
- **verify-phase-landing-plan**: plan-phase requires a Landing section before plan review, and incidental work skips it; tdd; workflow-loop; python3 -m pytest tests/test_plan_landing.py -q _(id: [rec-58522d3a-4f28-4cd8-bcf8-4f8ab951dd54](.artifacts/records/project__acceptance/rec-58522d3a-4f28-4cd8-bcf8-4f8ab951dd54.md))_

## verify-quiet-header

### Acceptance
- **verify-quiet-header**: dashboard --once prints the parenthetical tab line and the collapsed stepper; check; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k once_tally _(id: [rec-bc634371-b551-458a-a1c6-a010d02af538](.artifacts/records/project__acceptance/rec-bc634371-b551-458a-a1c6-a010d02af538.md))_

## verify-quiet-header-headers

### Acceptance
- **verify-quiet-header-headers**: Done phase header rows have no check glyph; check; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k done_phases_collapse _(id: [rec-47663207-ae0c-4fd9-a2f8-e127cd7a753c](.artifacts/records/project__acceptance/rec-47663207-ae0c-4fd9-a2f8-e127cd7a753c.md))_

## verify-quiet-header-keys

### Acceptance
- **verify-quiet-header-keys**: Keys 1-6, left/right, and click still filter the table, and the footer still shows 1-6; check; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k "number_keys_filter or status_tabs_are_six" _(id: [rec-6fe96e57-e909-4bac-8895-59df57721d8d](.artifacts/records/project__acceptance/rec-6fe96e57-e909-4bac-8895-59df57721d8d.md))_

## verify-quiet-header-stepper

### Acceptance
- **verify-quiet-header-stepper**: An effort with more than two done phases shows N done, the current phase, and one next phase, with no green check, and activating the stepper expands the finished titles; check; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k stepper _(id: [rec-ed5ce2ba-5329-44cc-9895-c8dc5586000b](.artifacts/records/project__acceptance/rec-ed5ce2ba-5329-44cc-9895-c8dc5586000b.md))_

## verify-quiet-header-suite

### Acceptance
- **verify-quiet-header-suite**: The full suite passes, including the tmux tests; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m "not tmux" && uv run --with textual --with pytest python -m pytest tests -q -m tmux _(id: [rec-40732634-5a9c-4595-bc25-89fe2a6a00cc](.artifacts/records/project__acceptance/rec-40732634-5a9c-4595-bc25-89fe2a6a00cc.md))_

## verify-quiet-header-tabs

### Acceptance
- **verify-quiet-header-tabs**: Six status tabs at 120 columns read Active (3) with no leading digit, a highlighted selected word, and a dim tally; check; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k "tab_row or tab_labels" _(id: [rec-b888f503-6a00-4777-899c-1887b314935d](.artifacts/records/project__acceptance/rec-b888f503-6a00-4777-899c-1887b314935d.md))_

## verify-readable-layout-phase

### Acceptance
- **verify-readable-layout-phase**: The full test suite passes with the new dashboard in the isolated tmux server; check; dashboard; uv run --with textual --with pytest python -m pytest tests -q _(id: [rec-b9c2eff5-a486-4b57-89bc-cc4a3aa95314](.artifacts/records/project__acceptance/rec-b9c2eff5-a486-4b57-89bc-cc4a3aa95314.md))_

## verify-readable-layout-phase-signoff

### Acceptance
- **verify-readable-layout-phase-signoff**: The user views the dashboard in the popup and the side pane and signs off that it is readable and clean; manual; dashboard _(id: [rec-83820e9f-6ff5-407c-aa8f-deb4e441d5a5](.artifacts/records/project__acceptance/rec-83820e9f-6ff5-407c-aa8f-deb4e441d5a5.md))_

## verify-status-line-phase

### Acceptance
- **verify-status-line-phase**: The tmux status segment and e2e tests pass with the rebuilt status line, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux _(id: [rec-2e2b15a3-c245-48ab-874a-9efbfd69ff60](.artifacts/records/project__acceptance/rec-2e2b15a3-c245-48ab-874a-9efbfd69ff60.md))_

## verify-table-state-phase

### Acceptance
- **verify-table-state-phase**: The tmux popup test for focus and resize passes, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux _(id: [rec-c31c7b82-4a88-43bf-877c-1ffabb4f08e3](.artifacts/records/project__acceptance/rec-c31c7b82-4a88-43bf-877c-1ffabb4f08e3.md))_

## verify-task-details-phase

### Acceptance
- **verify-task-details-phase**: The full test suite passes, including a tmux test that opens a task's detail screen in the popup and sees it update through a lifecycle; check; dashboard; uv run --with textual --with pytest python -m pytest tests -q _(id: [rec-98ab04e9-ab1a-488f-8712-716c9a11b7ba](.artifacts/records/project__acceptance/rec-98ab04e9-ab1a-488f-8712-716c9a11b7ba.md))_

## verify-task-details-phase-signoff

### Acceptance
- **verify-task-details-phase-signoff**: The user opens task details in the popup and the side pane and signs off that they show what the task needs and what happened on it; manual; dashboard _(id: [rec-11643a9d-4693-4761-b94a-ba3a6be27ad6](.artifacts/records/project__acceptance/rec-11643a9d-4693-4761-b94a-ba3a6be27ad6.md))_

## verify-task-navigation-phase

### Acceptance
- **verify-task-navigation-phase**: The full test suite passes, including a keys-only tmux test through status tabs, phase sections, and a task detail; check; dashboard; uv run --with textual --with pytest python -m pytest tests -q _(id: [rec-b9307639-88bf-43f4-8ad7-d0e4a77db060](.artifacts/records/project__acceptance/rec-b9307639-88bf-43f4-8ad7-d0e4a77db060.md))_

## verify-task-navigation-phase-signoff

### Acceptance
- **verify-task-navigation-phase-signoff**: The user navigates with the keyboard, status tabs, and phase sections in the popup and the side pane and signs off; manual; dashboard _(id: [rec-892a40a7-5d4e-4027-a096-a484d58b9787](.artifacts/records/project__acceptance/rec-892a40a7-5d4e-4027-a096-a484d58b9787.md))_

## verify-task-rows-phase

### Acceptance
- **verify-task-rows-phase**: The tmux popup test for task rows and activity passes, README describes waits-on, running time and failed activity, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux -rf _(id: [rec-92df6b15-9068-4342-b3fa-899bc28247b3](.artifacts/records/project__acceptance/rec-92df6b15-9068-4342-b3fa-899bc28247b3.md))_

## verify-tmux-integration-phase

### Acceptance
- **verify-tmux-integration-phase**: The isolated tmux test passes: the side pane shows the repo's dashboard, the popup binding runs the launcher in the pane directory and renders, and the status segment counts match; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests/test_tmux_integration.py -q _(id: [rec-66a8f44a-bfea-4ee2-aea0-cbe426d17d69](.artifacts/records/project__acceptance/rec-66a8f44a-bfea-4ee2-aea0-cbe426d17d69.md))_

## verify-tmux-integration-phase-suites

### Acceptance
- **verify-tmux-integration-phase-suites**: Full test suites of both repos pass on the phase-3 changes; check; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q && cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-4a323bc2-c820-4133-8409-d9be1a13b97a](.artifacts/records/project__acceptance/rec-4a323bc2-c820-4133-8409-d9be1a13b97a.md))_

## verify-tmux-plugin-entry

### Acceptance
- **verify-tmux-plugin-entry**: In a real tmux server loaded through se-workflow.tmux, prefix A and prefix S open the dashboard (real entry point).; tdd; dashboard; uv run --with pytest --with textual pytest -m tmux tests/test_tmux_integration.py tests/test_e2e_dashboard.py tests/test_tmux_entry.py _(id: [rec-307dcaee-56c1-444b-8e02-b54d47eb903a](.artifacts/records/project__acceptance/rec-307dcaee-56c1-444b-8e02-b54d47eb903a.md))_

## verify-tmux-plugin-entry-conf-gone

### Acceptance
- **verify-tmux-plugin-entry-conf-gone**: dashboard/tmux.conf is gone and nothing refers to it.; check; dashboard; test ! -e dashboard/tmux.conf && ! grep -rnE 'dashboard/tmux\.conf|SE_WORKFLOW_DASHBOARD' dashboard scripts tests README.md _(id: [rec-bc65d5e2-9428-4c8c-966d-4ebaa8e3cc34](.artifacts/records/project__acceptance/rec-bc65d5e2-9428-4c8c-966d-4ebaa8e3cc34.md))_

## verify-tmux-plugin-entry-full-suite

### Acceptance
- **verify-tmux-plugin-entry-full-suite**: The full suite passes, including the tmux tests.; check; dashboard; uv run --with pytest --with textual pytest && uv run --with pytest --with textual pytest -m tmux _(id: [rec-c78b573b-fc0f-4ab7-8f1a-52f73766dc61](.artifacts/records/project__acceptance/rec-c78b573b-fc0f-4ab7-8f1a-52f73766dc61.md))_

## verify-tmux-plugin-entry-key-options

### Acceptance
- **verify-tmux-plugin-entry-key-options**: The key options rebind the keys and the defaults are A and S.; check; dashboard; uv run --with pytest --with textual pytest -m tmux tests/test_tmux_entry.py -k 'default or custom_keys' _(id: [rec-22a2f699-9b2e-4971-8f8f-72f726491c0f](.artifacts/records/project__acceptance/rec-22a2f699-9b2e-4971-8f8f-72f726491c0f.md))_

## verify-tmux-plugin-entry-readme

### Acceptance
- **verify-tmux-plugin-entry-readme**: The README has a numbered Quick start that covers TPM and run-shell.; check; dashboard; grep -q '^## Quick start' README.md && grep -q "@plugin 'andrewy1n/se-workflow'" README.md && grep -q 'run-shell' README.md _(id: [rec-81b6561f-39c6-4892-91e4-e2a043e7dd9b](.artifacts/records/project__acceptance/rec-81b6561f-39c6-4892-91e4-e2a043e7dd9b.md))_

## verify-watch-renderer-phase

### Acceptance
- **verify-watch-renderer-phase**: The pty integration test passes: first frame shown, redraw within 3 s of a record write, zero redraws over an idle second, SIGINT exits 0; tdd; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q -k watch_integration _(id: [rec-cadda757-0424-444f-8ae1-31d415d18e6d](.artifacts/records/project__acceptance/rec-cadda757-0424-444f-8ae1-31d415d18e6d.md))_

## verify-watch-renderer-phase-suites

### Acceptance
- **verify-watch-renderer-phase-suites**: Full test suites of both repos pass on the phase-2 changes; check; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q && cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-02bac654-25f6-4bc0-b6ec-5efa03a4941e](.artifacts/records/project__acceptance/rec-02bac654-25f6-4bc0-b6ec-5efa03a4941e.md))_

## verify-wave-executor

### Acceptance
- **verify-wave-executor**: plan-phase and execute-phase name the same executors, inline and subagent, and a missing executor means subagent; tdd; workflow-loop; python3 -m pytest tests/test_wave_executor_phase.py -q _(id: [rec-5fe7bba7-cd21-447d-a698-ed9bb1379f58](.artifacts/records/project__acceptance/rec-5fe7bba7-cd21-447d-a698-ed9bb1379f58.md))_

## verify-wave-executor-execute

### Acceptance
- **verify-wave-executor-execute**: execute-phase runs an inline wave in this session and a subagent wave as one worker per task, and does not ask for a recipe when Approach is present; tdd; workflow-loop; python3 -m pytest tests/test_execute_wave_dispatch.py -q _(id: [rec-d8b61721-30cb-41fd-885d-85e673c7d6d7](.artifacts/records/project__acceptance/rec-d8b61721-30cb-41fd-885d-85e673c7d6d7.md))_

## verify-wave-executor-plan

### Acceptance
- **verify-wave-executor-plan**: plan-phase requires a recipe, one shared executor per wave, and phase size, stops, and collision notes before plan review; tdd; workflow-loop; python3 -m pytest tests/test_plan_wave_rules.py -q _(id: [rec-61bdf854-1a06-491f-8af6-aeda309ec357](.artifacts/records/project__acceptance/rec-61bdf854-1a06-491f-8af6-aeda309ec357.md))_

## watch-command

### Acceptance
- **watch-command**: With an injected clock, sleep and output stream: a changed render gives one redraw, an unchanged render gives none, a render error shows and the loop continues, KeyboardInterrupt returns exit 0, and --once prints one frame; tdd; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q _(id: [rec-ec792cef-650b-492a-ac2d-eed325546c19](.artifacts/records/project__acceptance/rec-ec792cef-650b-492a-ac2d-eed325546c19.md))_

## workflow-loop

### Position
- **workflow-loop**: evidence-loop is planned. The approach is settled. Tasks are not written.; effort _(id: [rec-e8b30aae-956a-4d62-b097-4cdbf4168bc0](.artifacts/records/project__current-position/rec-e8b30aae-956a-4d62-b097-4cdbf4168bc0.md))_
