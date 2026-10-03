# Project Verification

> Derived view — not authoritative. Edit underlying records, not this file.
> Store state: sha256:d22a6f0d01ace265bfeb03f89b5e0eba764c7384f5d74dcf11e22337e3f5e2f1

## activity-failures

### Acceptance
- **activity-failures**: Model test sets failed for a failed check-run and a failed report only; pilot test shows a failed line in the error colour with ✗; the tests fail before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py tests/test_dashboard_app.py -q -k fail _(id: [rec-7d228e89-762a-4794-9c56-adfca651899a](./records/project__acceptance/rec-7d228e89-762a-4794-9c56-adfca651899a.md))_

### Check
- **activity-failures**: rec-7d228e89-762a-4794-9c56-adfca651899a; 6c723d89c0a95f1c261cd940f48e51f9a731bfd1; pass; tdd _(id: [rec-2a089a7b-872b-465c-9b46-aaa8ae7f5812](./records/project__check-run/rec-2a089a7b-872b-465c-9b46-aaa8ae7f5812.md))_

## add-dashboard-view

### Acceptance
- **add-dashboard-view**: The contract resolves with the dashboard view and passes the contract and skill consistency tests; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-b6ae7140-2e58-4194-9294-6cc47d132fb4](./records/project__acceptance/rec-b6ae7140-2e58-4194-9294-6cc47d132fb4.md))_

### Check
- **add-dashboard-view**: rec-1dceda28-8bfd-43df-b3ca-53d3a7740286; c993c1b8159c0a5a28827c63e588a86f40a0971b; pass; tdd _(id: [rec-31267407-87d0-4234-b4bb-761394266851](./records/project__check-run/rec-31267407-87d0-4234-b4bb-761394266851.md))_
- **add-dashboard-view**: rec-b6ae7140-2e58-4194-9294-6cc47d132fb4; c993c1b8159c0a5a28827c63e588a86f40a0971b; pass; tdd _(id: [rec-c2cd5a62-cd01-4fe9-9a3d-83ce6a3b6abc](./records/project__check-run/rec-c2cd5a62-cd01-4fe9-9a3d-83ce6a3b6abc.md))_

## add-dashboard-view-render

### Acceptance
- **add-dashboard-view-render**: Against a seeded store with one record per section, view --id project:dashboard renders every section in order with labeled fields, and a done item older than 24h is absent; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests -q -k dashboard _(id: [rec-1dceda28-8bfd-43df-b3ca-53d3a7740286](./records/project__acceptance/rec-1dceda28-8bfd-43df-b3ca-53d3a7740286.md))_

## ag-aggregate-cli

### Acceptance
- **ag-aggregate-cli**: On a fixture report the command prints valid JSON with efforts, tools, skills, outliers and caveats; on the real report it exits 0 and lists every effort that has a session.; tdd; session-analysis; python3 -m pytest -q tests/test_session_aggregate.py _(id: [rec-efaa257a-446d-4f97-a738-4d098747043f](./records/project__acceptance/rec-efaa257a-446d-4f97-a738-4d098747043f.md))_

### Check
- **ag-aggregate-cli**: rec-efaa257a-446d-4f97-a738-4d098747043f; dirty; pass; tdd _(id: [rec-2d90d015-36ae-4873-a6d1-98bdecf0a0ec](./records/project__check-run/rec-2d90d015-36ae-4873-a6d1-98bdecf0a0ec.md))_

## ag-effort-rollup

### Acceptance
- **ag-effort-rollup**: A fixture of three sessions and two efforts, one session touching both, yields exact per-effort totals with shared and exclusive cost split.; tdd; session-analysis; python3 -m pytest -q tests/test_effort_rollup.py _(id: [rec-d0cbaaf6-d767-45f6-aa4d-f32b9415b6bc](./records/project__acceptance/rec-d0cbaaf6-d767-45f6-aa4d-f32b9415b6bc.md))_

### Check
- **ag-effort-rollup**: rec-d0cbaaf6-d767-45f6-aa4d-f32b9415b6bc; dirty; pass; tdd _(id: [rec-2a7118de-ad03-4568-9f13-c9f5b4c3be61](./records/project__check-run/rec-2a7118de-ad03-4568-9f13-c9f5b4c3be61.md))_

## ag-outliers

### Acceptance
- **ag-outliers**: A fixture yields the top sessions per metric in the expected order, with references and values only, and fewer than top entries when there are fewer sessions.; tdd; session-analysis; python3 -m pytest -q tests/test_session_outliers.py _(id: [rec-4b4378e7-5443-435e-86ab-02ad515ebb4d](./records/project__acceptance/rec-4b4378e7-5443-435e-86ab-02ad515ebb4d.md))_

### Check
- **ag-outliers**: rec-4b4378e7-5443-435e-86ab-02ad515ebb4d; dirty; pass; tdd _(id: [rec-46e8a5f9-0acc-4f97-8a6e-c630b856a816](./records/project__check-run/rec-46e8a5f9-0acc-4f97-8a6e-c630b856a816.md))_

## ag-tool-skill-rollup

### Acceptance
- **ag-tool-skill-rollup**: A fixture yields exact per-tool calls, errors, error rate, retries and session counts, and per-skill invocation and session counts, in sorted order.; tdd; session-analysis; python3 -m pytest -q tests/test_tool_skill_rollup.py _(id: [rec-f283ff9c-78e6-439b-ae65-90ef88690304](./records/project__acceptance/rec-f283ff9c-78e6-439b-ae65-90ef88690304.md))_

### Check
- **ag-tool-skill-rollup**: rec-f283ff9c-78e6-439b-ae65-90ef88690304; dirty; pass; tdd _(id: [rec-d83cb7ea-fdf5-43ff-963d-6a25570a2de5](./records/project__check-run/rec-d83cb7ea-fdf5-43ff-963d-6a25570a2de5.md))_

## as-cost-null

### Acceptance
- **as-cost-null**: Every session whose transcript has a cost-state line with a numeric cost reports a non-null cost_usd, and a regression test covers the cause.; tdd; session-analysis; python3 -m pytest -q tests/test_session_fields.py _(id: [rec-36001c1e-b274-4757-b5b3-44fd1a44e292](./records/project__acceptance/rec-36001c1e-b274-4757-b5b3-44fd1a44e292.md))_

### Check
- **as-cost-null**: rec-36001c1e-b274-4757-b5b3-44fd1a44e292; dirty; pass; tdd _(id: [rec-cdcd7553-bfa6-4461-8cc7-fb0bce6b615c](./records/project__check-run/rec-cdcd7553-bfa6-4461-8cc7-fb0bce6b615c.md))_

### Finding
- **as-cost-null**: Null cost_usd on 140 of 247 sessions is a data gap: those transcripts have no cost-state line, so cost totals are a lower bound over 107 sessions.; Streamed all 140 null transcripts: 0 cost-state lines and 0 cost-named keys. The 107 non-null sessions parse correctly.; Claude Code starts writing cost-state lines for more sessions, or a different cost field appears in transcripts.; none _(id: [rec-8aa9b9e5-9088-4e73-a8ec-facffa2d3833](./records/project__finding/rec-8aa9b9e5-9088-4e73-a8ec-facffa2d3833.md))_

## as-dry-run

### Acceptance
- **as-dry-run**: The dry run lists candidates that each cite a metric and a session reference, and the user accepts the list.; manual; session-analysis _(id: [rec-2fa1b9d2-53f0-4a38-bc7f-ace90efeb566](./records/project__acceptance/rec-2fa1b9d2-53f0-4a38-bc7f-ace90efeb566.md))_

### Check
- **as-dry-run**: rec-2fa1b9d2-53f0-4a38-bc7f-ace90efeb566; dirty; pass; manual _(id: [rec-23dbd684-3ad1-481e-ac44-afd9f4a53263](./records/project__check-run/rec-23dbd684-3ad1-481e-ac44-afd9f4a53263.md))_
- **as-dry-run**: rec-2fa1b9d2-53f0-4a38-bc7f-ace90efeb566; dirty; pass; manual; Andrew Yin _(id: [rec-37f7dd93-e369-4875-9188-d90fef4007c4](./records/project__check-run/rec-37f7dd93-e369-4875-9188-d90fef4007c4.md))_

### Finding
- **as-dry-run**: The analyze-sessions skill yields 4 specific, metric-backed candidates on real data, but it lacks rules the agent had to guess: temp directory, pattern and noise, severity, and tool-level session ids.; Dry run over 243 sessions: 4 candidates each with a metric, session references and a target; 4 patterns dropped; 6 of 7 done-when criteria met (step 7 deferred to the caller). I re-checked the Bash, jira_create_issue and error-outlier numbers against a fresh run and they match.; SKILL.md defines the missing rules and a second dry run needs no manual report.jsonl lookups.; human _(id: [rec-1e84d081-a11f-4cf3-b588-672c9f99d52b](./records/project__finding/rec-1e84d081-a11f-4cf3-b588-672c9f99d52b.md))_

## as-dry-run-rerun

### Finding
- **as-dry-run-rerun**: After the rules fix the skill needs no guessed rules for pattern, noise, severity or tool-level session references, but two gaps remain: project identity for worktree paths, and candidate edits that need a transcript read.; Second dry run over 243 sessions: 2 candidates with full session ids and targets, 2 patterns dropped, 1 noise session. The agent named remaining gaps: worktree project strings, double counting of slots across patterns, edits that cannot be named from metrics, cost outliers with empty efforts have no target, cross-repo fix locations.; SKILL.md and targets.md state the project-identity, double counting, evidence-needed and cross-repo rules and a third run needs no guesses.; human _(id: [rec-b393a226-8a19-4952-abff-ecfaf8532b8b](./records/project__finding/rec-b393a226-8a19-4952-abff-ecfaf8532b8b.md))_

## as-skill

### Acceptance
- **as-skill**: SKILL.md has name and a user-invoked flag, names both scripts at paths that exist, links targets.md, has no store-writing command, stays under 80 lines, and the skill contract consistency test passes.; tdd; session-analysis; python3 -m pytest -q tests/test_analyze_sessions_skill.py tests/test_skill_contract_consistency.py _(id: [rec-d186eb9e-852f-4f75-96aa-313e576c0f8b](./records/project__acceptance/rec-d186eb9e-852f-4f75-96aa-313e576c0f8b.md))_

### Check
- **as-skill**: rec-d186eb9e-852f-4f75-96aa-313e576c0f8b; dirty; pass; tdd _(id: [rec-f0d0b94f-0628-4826-a559-1d534622f347](./records/project__check-run/rec-f0d0b94f-0628-4826-a559-1d534622f347.md))_

## as-skill-rules

### Acceptance
- **as-skill-rules**: SKILL.md defines the temp directory, pattern, noise, severity, tool-level session references and bounded slices, stays under 80 lines, and the skill tests and the skill contract consistency test pass.; tdd; session-analysis; python3 -m pytest -q tests/test_analyze_sessions_skill.py tests/test_skill_contract_consistency.py _(id: [rec-f0c76da5-b91f-4660-bcc7-e221a00ac3e8](./records/project__acceptance/rec-f0c76da5-b91f-4660-bcc7-e221a00ac3e8.md))_

### Check
- **as-skill-rules**: rec-f0c76da5-b91f-4660-bcc7-e221a00ac3e8; dirty; pass; tdd _(id: [rec-9b88c13a-abba-4c98-ba93-556c2280ccaa](./records/project__check-run/rec-9b88c13a-abba-4c98-ba93-556c2280ccaa.md))_

## as-targets

### Acceptance
- **as-targets**: targets.md has one section per target and each section lists at least one pattern whose metric field names all exist in the real aggregate output.; tdd; session-analysis; python3 -m pytest -q tests/test_analyze_sessions_targets.py _(id: [rec-9c15a1e4-c392-4ce0-8482-7bea7dd7f367](./records/project__acceptance/rec-9c15a1e4-c392-4ce0-8482-7bea7dd7f367.md))_

### Check
- **as-targets**: rec-9c15a1e4-c392-4ce0-8482-7bea7dd7f367; dirty; pass; tdd _(id: [rec-aeb76e26-4633-45f2-8afb-47c8a383a79c](./records/project__check-run/rec-aeb76e26-4633-45f2-8afb-47c8a383a79c.md))_

## close-step-skill

### Acceptance
- **close-step-skill**: execute-phase documents the close step with a payload the contract accepts; skill/contract consistency tests pass; tdd; workflow-loop; python3 -m pytest tests/test_skill_contract_consistency.py -q _(id: [rec-8bcac210-20bd-42a8-b0ea-953bd412937a](./records/project__acceptance/rec-8bcac210-20bd-42a8-b0ea-953bd412937a.md))_

### Check
- **close-step-skill**: rec-8bcac210-20bd-42a8-b0ea-953bd412937a; 8f1c9bbbb89ef3dc90f3fa36d00c83b924f2a721; pass; tdd _(id: [rec-624fc8c3-8603-42f5-b7bb-ab21d051cbc3](./records/project__check-run/rec-624fc8c3-8603-42f5-b7bb-ab21d051cbc3.md))_

## column-resize

### Acceptance
- **column-resize**: Resize 120 to 60 columns: the table shows status, task, wave with no reload; resize back: phase and assignee return; the test fails before the fix; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k resize _(id: [rec-4b32e614-7d7e-4a55-be85-301c98fe6ef9](./records/project__acceptance/rec-4b32e614-7d7e-4a55-be85-301c98fe6ef9.md))_

### Check
- **column-resize**: rec-4b32e614-7d7e-4a55-be85-301c98fe6ef9; b104980765db3920237082612a4d1aa5eda6a5b7; pass; tdd _(id: [rec-92efe161-3980-4dc2-b0ce-32eca9e0f501](./records/project__check-run/rec-92efe161-3980-4dc2-b0ce-32eca9e0f501.md))_

### Observation
- **column-resize**: On resize, DashboardApp.on_resize runs before App.size updates, so paint() used the old width; EffortPane.on_resize replayed the stored stale width. Columns stayed wide until reload.; dashboard-bugfix _(id: [rec-c526251e-c035-426f-abf2-b9604030e7fa](./records/project__investigation-observation/rec-c526251e-c035-426f-abf2-b9604030e7fa.md))_

## commit-stat-width

### Acceptance
- **commit-stat-width**: A pilot test at 60 and 80 columns shows every stat line of a commit with a long path on one line; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-de68bee3-9f99-4495-8545-8aa7b453e373](./records/project__acceptance/rec-de68bee3-9f99-4495-8545-8aa7b453e373.md))_

### Check
- **commit-stat-width**: rec-de68bee3-9f99-4495-8545-8aa7b453e373; da2d120; pass; tdd _(id: [rec-b7acff16-1849-4e7f-a841-2a9bd821afd0](./records/project__check-run/rec-b7acff16-1849-4e7f-a841-2a9bd821afd0.md))_

## copy-and-commit-actions

### Acceptance
- **copy-and-commit-actions**: Pilot tests copy the selected slug from the dashboard and the detail screen, open the commit screen with the message and stat for a task's latest revision in a temp git repo, show a message for a dirty or unknown revision, and return on Esc; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-b0782695-b6a8-443a-b1ed-fd39a65b5de8](./records/project__acceptance/rec-b0782695-b6a8-443a-b1ed-fd39a65b5de8.md))_

### Check
- **copy-and-commit-actions**: rec-b0782695-b6a8-443a-b1ed-fd39a65b5de8; 9822923; pass; tdd _(id: [rec-fb98930f-0a3a-4841-95db-46f171e68f36](./records/project__check-run/rec-fb98930f-0a3a-4841-95db-46f171e68f36.md))_

## dashboard-app

### Acceptance
- **dashboard-app**: A Textual pilot test at 60 and 120 columns finds the goal, progress, tiles, task rows, needs-you items, and activity for a temp store, and sees a redraw after a store change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-607927c0-6e77-499d-ae1f-ee7a890cfd07](./records/project__acceptance/rec-607927c0-6e77-499d-ae1f-ee7a890cfd07.md))_

### Check
- **dashboard-app**: rec-607927c0-6e77-499d-ae1f-ee7a890cfd07; f84a229; pass; tdd _(id: [rec-3b1bf0ad-45ab-4b9b-8c35-152bc2cd0bad](./records/project__check-run/rec-3b1bf0ad-45ab-4b9b-8c35-152bc2cd0bad.md))_

## dashboard-closed-goals

### Acceptance
- **dashboard-closed-goals**: build_model leaves out an effort whose goal has status closed; tdd; workflow-loop; python3 -m pytest tests/test_dashboard_model.py -q _(id: [rec-f02ec3b2-3bd6-496f-933a-1506d3b4a877](./records/project__acceptance/rec-f02ec3b2-3bd6-496f-933a-1506d3b4a877.md))_

### Check
- **dashboard-closed-goals**: rec-f02ec3b2-3bd6-496f-933a-1506d3b4a877; 8f1c9bbbb89ef3dc90f3fa36d00c83b924f2a721; pass; tdd _(id: [rec-d8041aec-d887-49ea-aa27-693636929bb6](./records/project__check-run/rec-d8041aec-d887-49ea-aa27-693636929bb6.md))_

## dashboard-launcher

### Acceptance
- **dashboard-launcher**: Given a temp repo: with ~/.artifacts/<repo> it uses that store; with only <repo>/.artifacts it uses that; with none it prints a no-store message; with a store whose contract lacks project:dashboard it prints a missing-view message; ADAPTIVE_ARTIFACTS_BIN overrides the binary; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-e4e1b7a5-4c4b-45ce-8a02-bb12452e15ea](./records/project__acceptance/rec-e4e1b7a5-4c4b-45ce-8a02-bb12452e15ea.md))_

### Check
- **dashboard-launcher**: rec-e4e1b7a5-4c4b-45ce-8a02-bb12452e15ea; f4cf9dc; pass; tdd _(id: [rec-c4dc7668-a282-42b6-bfa7-6669d2e8e89d](./records/project__check-run/rec-c4dc7668-a282-42b6-bfa7-6669d2e8e89d.md))_

## dashboard-launcher-switch

### Acceptance
- **dashboard-launcher-switch**: Launcher and tmux tests pass with scripts/dashboard running the Textual app; tdd; dashboard; python3 -m pytest tests/test_dashboard_launcher.py tests/test_tmux_integration.py -q _(id: [rec-7fbf25bf-c639-424e-a4a2-66a5d640f23a](./records/project__acceptance/rec-7fbf25bf-c639-424e-a4a2-66a5d640f23a.md))_

### Check
- **dashboard-launcher-switch**: rec-7fbf25bf-c639-424e-a4a2-66a5d640f23a; 3e52964; pass; tdd _(id: [rec-886e6cd6-162c-4c11-a70f-08b1d3cb20b9](./records/project__check-run/rec-886e6cd6-162c-4c11-a70f-08b1d3cb20b9.md))_

## dashboard-snapshot

### Acceptance
- **dashboard-snapshot**: Tests against a temp store show the snapshot groups records per effort and classifies tasks, needs-you items, phase progress, and recent activity correctly; tdd; dashboard; python3 -m pytest tests/test_dashboard_model.py -q _(id: [rec-8f27fb0c-0113-4d37-9083-5f9767e2d6e6](./records/project__acceptance/rec-8f27fb0c-0113-4d37-9083-5f9767e2d6e6.md))_

### Check
- **dashboard-snapshot**: rec-8f27fb0c-0113-4d37-9083-5f9767e2d6e6; 1e88c65; pass; tdd _(id: [rec-2bc92ccd-0454-477e-b1db-644874232b6c](./records/project__check-run/rec-2bc92ccd-0454-477e-b1db-644874232b6c.md))_

## dashboard-status-segment

### Acceptance
- **dashboard-status-segment**: Against a seeded store the segment prints the correct running, ready and needs-you counts within 1 s; with no store it prints nothing and exits 0; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-e7e94ca1-9742-44b2-9fe1-7a014b58ef3d](./records/project__acceptance/rec-e7e94ca1-9742-44b2-9fe1-7a014b58ef3d.md))_

### Check
- **dashboard-status-segment**: rec-e7e94ca1-9742-44b2-9fe1-7a014b58ef3d; 79fda7a; pass; tdd _(id: [rec-9b7aa254-a191-4196-a918-8e364893a451](./records/project__check-run/rec-9b7aa254-a191-4196-a918-8e364893a451.md))_

## detail-redraw-race

### Acceptance
- **detail-redraw-race**: The root cause is named, and test_detail_screen_redraws_when_the_store_changes passes 30 times in a row alone and in two full-suite runs; check; dashboard; for i in $(seq 30); do uv run --with textual --with pytest python -m pytest 'tests/test_dashboard_app.py::test_detail_screen_redraws_when_the_store_changes' -q || exit 1; done _(id: [rec-c4742568-196f-4b86-89ea-4a12a7490978](./records/project__acceptance/rec-c4742568-196f-4b86-89ea-4a12a7490978.md))_

### Check
- **detail-redraw-race**: rec-c4742568-196f-4b86-89ea-4a12a7490978; 03d561c; pass; check _(id: [rec-83577b2a-8ec0-4648-b7d9-2d706b7959bd](./records/project__check-run/rec-83577b2a-8ec0-4648-b7d9-2d706b7959bd.md))_

### Observation
- **detail-redraw-race**: test_detail_screen_redraws_when_the_store_changes[size1] failed with NoMatches: No nodes match '#related' on TaskDetailScreen(); 1 of 2 full runs, 1 of 4 isolated runs; earlier it timed out under load in two other full runs; dashboard-ui _(id: [rec-cf05a87a-e78b-48fb-ad15-132bd63bb053](./records/project__investigation-observation/rec-cf05a87a-e78b-48fb-ad15-132bd63bb053.md))_

### Finding
- **detail-redraw-race**: The detail screen paint queried #related after awaits without re-checking that the screen was still attached, so a poll-triggered redraw racing teardown raised NoMatches; Traceback apply -> paint query_one(#related) in 5 of 25 loaded runs; 30/30 loaded and 30/30 alone after re-checking is_attached after the awaits; The test fails again with NoMatches after 03d561c; none _(id: [rec-5018f385-7ec4-40ba-9736-d651d7b2af88](./records/project__finding/rec-5018f385-7ec4-40ba-9736-d651d7b2af88.md))_

## discuss-skill

### Acceptance
- **discuss-skill**: skills/discuss/SKILL.md exists and every adaptive-artifacts invocation in it passes the skill/contract consistency test; tdd; workflow-loop; python3 -m pytest tests/test_skill_contract_consistency.py tests/test_discuss_skill.py -q _(id: [rec-29f17960-fd84-4c12-9d0b-9589e7b71980](./records/project__acceptance/rec-29f17960-fd84-4c12-9d0b-9589e7b71980.md))_

### Check
- **discuss-skill**: rec-29f17960-fd84-4c12-9d0b-9589e7b71980; 8c697bc88db7147f17a058311b0323cd4a191fee; pass; tdd _(id: [rec-94e86670-ccc6-4d19-bc2f-38158169ceeb](./records/project__check-run/rec-94e86670-ccc6-4d19-bc2f-38158169ceeb.md))_

## e2e-real-execute-run

### Acceptance
- **e2e-real-execute-run**: The frame log shows task one go ready, running, done and task two go waiting, ready, running, done, driven by real subagent dispatch; the user signs after reading it; manual; dashboard _(id: [rec-70f9c43d-01d7-438e-8df6-ad97b7fd46ce](./records/project__acceptance/rec-70f9c43d-01d7-438e-8df6-ad97b7fd46ce.md))_

### Check
- **e2e-real-execute-run**: rec-70f9c43d-01d7-438e-8df6-ad97b7fd46ce; dirty; pass; manual; ayin _(id: [rec-fd14f0b7-0adc-4394-8deb-14db551d0328](./records/project__check-run/rec-fd14f0b7-0adc-4394-8deb-14db551d0328.md))_

## e2e-scripted-run

### Acceptance
- **e2e-scripted-run**: After each step the live side pane shows exactly the expected section map within 5 s and the status segment shows the matching counts; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests -q -k e2e _(id: [rec-5f7f36da-ec22-4619-b31b-8ff7fb3b85ee](./records/project__acceptance/rec-5f7f36da-ec22-4619-b31b-8ff7fb3b85ee.md))_

### Check
- **e2e-scripted-run**: rec-5f7f36da-ec22-4619-b31b-8ff7fb3b85ee; a3b4ee2; pass; tdd _(id: [rec-0bb17e22-8556-465f-b71b-26bf65439808](./records/project__check-run/rec-0bb17e22-8556-465f-b71b-26bf65439808.md))_

### Observation
- **e2e-scripted-run**: One of ten full-suite runs failed on the e2e test before the status check became a poll; likely cause is the dashboard-status 2 s view timeout under load, which makes the status line print nothing; watch-dashboard _(id: [rec-a77f0052-dde9-486a-8cd7-d29c9576f5a4](./records/project__investigation-observation/rec-a77f0052-dde9-486a-8cd7-d29c9576f5a4.md))_

## effort-switch-focus

### Acceptance
- **effort-switch-focus**: Pilot test: with an effort-level question on a live effort, tab and shift+tab reach a finished effort and stay there; the test fails before the fix; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k switch _(id: [rec-768f3192-cdcf-45d9-9421-2282f78e8bef](./records/project__acceptance/rec-768f3192-cdcf-45d9-9421-2282f78e8bef.md))_

### Check
- **effort-switch-focus**: rec-768f3192-cdcf-45d9-9421-2282f78e8bef; 9da847f3ed9909af06213792ab542bdd582422a3; pass; tdd _(id: [rec-f46731c5-7318-4e68-8d68-c07a955c4d00](./records/project__check-run/rec-f46731c5-7318-4e68-8d68-c07a955c4d00.md))_

## finished-effort-view

### Acceptance
- **finished-effort-view**: Model test: finished is true only when every phase and counted task is done. Pilot tests: a finished effort shows All N tasks done under Active, sorts after a live effort, and has a dimmed label; a live effort with an empty filter still shows No tasks match; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py tests/test_dashboard_app.py -q -k finished _(id: [rec-cc216932-78bb-4df8-b80d-8da0eb287a9c](./records/project__acceptance/rec-cc216932-78bb-4df8-b80d-8da0eb287a9c.md))_

### Check
- **finished-effort-view**: rec-cc216932-78bb-4df8-b80d-8da0eb287a9c; 11fdbbe31fe4a60f1985ccc24fa41788fa83d1d5; pass; tdd _(id: [rec-9e17ccb9-1b70-4843-ade6-cabf22d52de2](./records/project__check-run/rec-9e17ccb9-1b70-4843-ade6-cabf22d52de2.md))_

## goal-status-field

### Acceptance
- **goal-status-field**: A goal and position superseded with status closed are absent from handoff and dashboard views; records without status still render; tdd; workflow-loop; python3 -m pytest tests/test_goal_close.py -q _(id: [rec-1f0b047c-50e6-4c2d-8c91-10a6c7d220e0](./records/project__acceptance/rec-1f0b047c-50e6-4c2d-8c91-10a6c7d220e0.md))_

### Check
- **goal-status-field**: rec-1f0b047c-50e6-4c2d-8c91-10a6c7d220e0; 8f1c9bbbb89ef3dc90f3fa36d00c83b924f2a721; pass; tdd _(id: [rec-700a7fec-ed34-4ade-8cb4-1f5c163aad2d](./records/project__check-run/rec-700a7fec-ed34-4ade-8cb4-1f5c163aad2d.md))_

## handoff-by-effort

### Acceptance
- **handoff-by-effort**: A work-item and a phase position render under their effort section in handoff, not under their own subject; tdd; workflow-loop; python3 -m pytest tests/test_phase_position.py -q _(id: [rec-ca16958b-e8a5-4605-a0cd-7bf1a556bd31](./records/project__acceptance/rec-ca16958b-e8a5-4605-a0cd-7bf1a556bd31.md))_

### Check
- **handoff-by-effort**: rec-ca16958b-e8a5-4605-a0cd-7bf1a556bd31; 8d0b7fd43309d93b0b7f2b3db0a3f8a1022e405b; pass; tdd _(id: [rec-19b91624-50af-404d-b9b4-31576913a4be](./records/project__check-run/rec-19b91624-50af-404d-b9b4-31576913a4be.md))_

## heading-spacing

### Acceptance
- **heading-spacing**: Pilot test: in phase detail the line above each body heading is not blank (except the first line of the panel); the test fails before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k heading _(id: [rec-e3cb339f-2f12-42bd-9dab-4439494334aa](./records/project__acceptance/rec-e3cb339f-2f12-42bd-9dab-4439494334aa.md))_

### Check
- **heading-spacing**: rec-e3cb339f-2f12-42bd-9dab-4439494334aa; d6f518bc2b5c2f8f4ae54c678c9ffaf5c8949b6c; pass; tdd _(id: [rec-fb47b275-bf18-4ae2-8c81-21e6ebe99fce](./records/project__check-run/rec-fb47b275-bf18-4ae2-8c81-21e6ebe99fce.md))_

## keyboard-focus

### Acceptance
- **keyboard-focus**: Keyboard-only pilot tests move the cursor to a task below the first row and open it with enter, keep table focus after tab switch and after esc from detail, scroll to Activity with PgDn, and scroll the detail screen with arrows; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-97f2e49d-f874-4969-929c-d6c37a1ec61b](./records/project__acceptance/rec-97f2e49d-f874-4969-929c-d6c37a1ec61b.md))_

### Check
- **keyboard-focus**: rec-97f2e49d-f874-4969-929c-d6c37a1ec61b; 2d1a3be; pass; tdd _(id: [rec-45530a2e-0c6f-4115-ad97-6032f7040919](./records/project__check-run/rec-45530a2e-0c6f-4115-ad97-6032f7040919.md))_

### Finding
- **keyboard-focus**: Nothing focused the task table; the effort tab strip kept focus, so arrows never moved the cursor and enter always opened row 0; Real-store probe and 7 red keys-only tests before 2d1a3be; all pass after; A keys-only test fails to move or open a task after 2d1a3be; none _(id: [rec-60d1962e-aeb0-4972-8002-f424c61f615a](./records/project__finding/rec-60d1962e-aeb0-4972-8002-f424c61f615a.md))_

## label-view-fields

### Acceptance
- **label-view-fields**: A view with label_fields true renders field: value pairs; a view without it renders exactly as before; tdd; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q _(id: [rec-0a970468-5d80-49a0-bf80-d5481a65814b](./records/project__acceptance/rec-0a970468-5d80-49a0-bf80-d5481a65814b.md))_

### Check
- **label-view-fields**: rec-0a970468-5d80-49a0-bf80-d5481a65814b; 3ecceba31d1cb6a750fd59320ccc43bee095a686; pass; tdd _(id: [rec-8a416f43-46fb-47fc-aeb5-7d656b99024c](./records/project__check-run/rec-8a416f43-46fb-47fc-aeb5-7d656b99024c.md))_

## model-fixture-reuse

### Acceptance
- **model-fixture-reuse**: Every test in tests/test_dashboard_model.py still passes and no test setup takes longer than 0.3s; check; test-suite-speed; python3 -m pytest tests/test_dashboard_model.py -q --durations=5 _(id: [rec-660d84e9-e3f2-421c-8094-db9c8427c8da](./records/project__acceptance/rec-660d84e9-e3f2-421c-8094-db9c8427c8da.md))_

## model-fixture-reuse-total

### Acceptance
- **model-fixture-reuse-total**: The full suite wall time is under 50s (baseline 101s) and user+sys CPU time does not exceed the baseline of 58s; check; test-suite-speed; time python3 -m pytest -q _(id: [rec-db700c2c-4b03-4fb5-9aec-9517316abf2b](./records/project__acceptance/rec-db700c2c-4b03-4fb5-9aec-9517316abf2b.md))_

## needs-you-list

### Acceptance
- **needs-you-list**: Pilot tests: n focuses the list, arrows move, enter opens the task detail for a linked item and the Needs-you detail with full text for a question, esc returns, c copies the subject; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k needs_you _(id: [rec-7c8645dc-e818-4d9d-b2d1-807437c46a90](./records/project__acceptance/rec-7c8645dc-e818-4d9d-b2d1-807437c46a90.md))_

### Check
- **needs-you-list**: rec-7c8645dc-e818-4d9d-b2d1-807437c46a90; 206678413361ffed9978beeaac5dbc557fc5d774; pass; tdd _(id: [rec-0c7f3233-7865-46a8-abf9-dd6a6f6a6ced](./records/project__check-run/rec-0c7f3233-7865-46a8-abf9-dd6a6f6a6ced.md))_

## needs-you-records

### Acceptance
- **needs-you-records**: Model tests show the new item fields, task linking for slug and slug-prefix subjects, and no link for effort-level questions; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py -q -k needs _(id: [rec-79256814-feaf-46b4-b5da-3c97ec0838c0](./records/project__acceptance/rec-79256814-feaf-46b4-b5da-3c97ec0838c0.md))_

### Check
- **needs-you-records**: rec-79256814-feaf-46b4-b5da-3c97ec0838c0; fa6d87206996583b3d87e54147d655e5bddf32f5; pass; tdd _(id: [rec-a6d17cef-9df4-4b82-b9b7-3379e10d87d0](./records/project__check-run/rec-a6d17cef-9df4-4b82-b9b7-3379e10d87d0.md))_

### Observation
- **needs-you-records**: list --full for questions, findings and check-runs keeps dashboard-status at about 0.36 s on the real store with 56 check-runs (parent timing after merge).; dashboard-features _(id: [rec-6a8a8cb5-dd1b-42c3-a8fa-8b3b5baa06f1](./records/project__investigation-observation/rec-6a8a8cb5-dd1b-42c3-a8fa-8b3b5baa06f1.md))_

## needs-you-tab-removal

### Acceptance
- **needs-you-tab-removal**: Six status tabs on keys 1-6 with no Needs you tab; the panel title reads Needs you N for N items, including effort-level questions; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py tests/test_dashboard_view.py -q _(id: [rec-e781be72-47b4-4705-8bb4-82f57f1391ef](./records/project__acceptance/rec-e781be72-47b4-4705-8bb4-82f57f1391ef.md))_

### Check
- **needs-you-tab-removal**: rec-e781be72-47b4-4705-8bb4-82f57f1391ef; 7fbde9ccd60decd8e171bbdd46d83d598cfd2adf; pass; tdd _(id: [rec-1d2fada7-d72d-4924-97ce-8e7317d3a0fa](./records/project__check-run/rec-1d2fada7-d72d-4924-97ce-8e7317d3a0fa.md))_

### Observation
- **needs-you-tab-removal**: The Needs you tab matched needs-you subjects against task slugs, so effort-level questions and non-task subjects never counted and the tab disagreed with the panel.; dashboard-bugfix _(id: [rec-613913b9-0be9-46f8-a9b5-5f59739f368b](./records/project__investigation-observation/rec-613913b9-0be9-46f8-a9b5-5f59739f368b.md))_

## pane-width-stable

### Acceptance
- **pane-width-stable**: The stepper test passes 20 of 20 runs of the full app test file under -n 4, and a new test that toggles the pane scrollbar fails before the fix; tdd; dashboard; for i in $(seq 20); do uv run -q --with textual --with pytest --with pytest-xdist python -m pytest tests/test_dashboard_app.py -q -n 4 -p no:cacheprovider || break; done _(id: [rec-ef569598-f20a-4623-ba96-4f0c32edf9f1](./records/project__acceptance/rec-ef569598-f20a-4623-ba96-4f0c32edf9f1.md))_

### Check
- **pane-width-stable**: rec-ef569598-f20a-4623-ba96-4f0c32edf9f1; 8d1ef88f88d964b4fc3a400ca293e63ac5fcf1fc; pass; tdd _(id: [rec-d3f599ae-0312-45ec-a47b-f4bcbb2dddd9](./records/project__check-run/rec-d3f599ae-0312-45ec-a47b-f4bcbb2dddd9.md))_

### Observation
- **pane-width-stable**: Parent reran the acceptance loop on 8d1ef88: 20/20 clean, 204 passed each. Textual sends no Resize when a widget's own scrollbar toggles; the pane now refits on show_vertical_scrollbar.; dashboard-features _(id: [rec-9b177ada-79ac-4e14-b264-102f00afbf0c](./records/project__investigation-observation/rec-9b177ada-79ac-4e14-b264-102f00afbf0c.md))_

## phase-detail-tasks

### Acceptance
- **phase-detail-tasks**: Pilot tests: in a phase detail, arrows move through tasks, enter opens the task detail, and esc returns to the phase detail; the tests fail before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k phase_task _(id: [rec-2356a60d-0eda-499f-b3ab-ee4746d6aa45](./records/project__acceptance/rec-2356a60d-0eda-499f-b3ab-ee4746d6aa45.md))_

### Check
- **phase-detail-tasks**: rec-2356a60d-0eda-499f-b3ab-ee4746d6aa45; 1a9ce2781018b688d55b0d949f3e18a2aca70873; pass; tdd _(id: [rec-f9db072e-5521-4e3a-9f86-d1675f5f4775](./records/project__check-run/rec-f9db072e-5521-4e3a-9f86-d1675f5f4775.md))_

### Observation
- **phase-detail-tasks**: Cherry-pick onto task-detail-links conflicted only where both added a list class (LinkList, PhaseTaskList); parent kept both; the combined app tests pass (190).; dashboard-features _(id: [rec-31107cb0-d8f3-457b-acd6-e04ed4f3508f](./records/project__investigation-observation/rec-31107cb0-d8f3-457b-acd6-e04ed4f3508f.md))_

## phase-position-skills

### Acceptance
- **phase-position-skills**: Skills document the per-phase position with payloads the contract accepts; skill/contract consistency tests pass; tdd; workflow-loop; python3 -m pytest tests/test_skill_contract_consistency.py tests/test_phase_position.py -q _(id: [rec-9f326a41-7f0f-4d28-89c6-069154ad5a65](./records/project__acceptance/rec-9f326a41-7f0f-4d28-89c6-069154ad5a65.md))_

### Check
- **phase-position-skills**: rec-9f326a41-7f0f-4d28-89c6-069154ad5a65; 8d0b7fd43309d93b0b7f2b3db0a3f8a1022e405b; pass; tdd _(id: [rec-77842b73-9ccb-479a-b84e-5cfd5dab3508](./records/project__check-run/rec-77842b73-9ccb-479a-b84e-5cfd5dab3508.md))_

## phase-sections

### Acceptance
- **phase-sections**: Model and pilot tests group tasks by phase, collapse done and planned phases, fold older done phases, toggle headers by key and click, open a phase detail with body and decisions, show awaiting sign-off, and show effort-wide progress; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py tests/test_dashboard_model.py -q _(id: [rec-611e26b5-b891-4e71-8951-3ebf07ecc715](./records/project__acceptance/rec-611e26b5-b891-4e71-8951-3ebf07ecc715.md))_

### Check
- **phase-sections**: rec-611e26b5-b891-4e71-8951-3ebf07ecc715; 78548daa0ea66a4347d31d675b3f6fbd8c3b86f1; pass; tdd _(id: [rec-d0d98c8c-7d91-4cde-ac81-547b807803e4](./records/project__check-run/rec-d0d98c8c-7d91-4cde-ac81-547b807803e4.md))_

## recency-selection

### Acceptance
- **recency-selection**: A role with a 24h recorded_at window selects a record recorded 1h ago and skips one recorded 48h ago; a malformed window fails contract resolution; tdd; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q _(id: [rec-d854ca7d-767b-4729-92e1-18ef8853d92c](./records/project__acceptance/rec-d854ca7d-767b-4729-92e1-18ef8853d92c.md))_

### Check
- **recency-selection**: rec-d854ca7d-767b-4729-92e1-18ef8853d92c; 6de1ff4; pass; tdd _(id: [rec-a9d8a1d2-3bb1-478b-9164-bad3436d3a9a](./records/project__check-run/rec-a9d8a1d2-3bb1-478b-9164-bad3436d3a9a.md))_

### Observation
- **recency-selection**: View state digests hash store contents only; a recorded_at within-window role changes membership with time alone, so a digest-driven watch will not redraw when a done item ages out; watch-dashboard _(id: [rec-5b58d86c-922d-4747-8533-4f3b685d1c0d](./records/project__investigation-observation/rec-5b58d86c-922d-4747-8533-4f3b685d1c0d.md))_

## rj-join

### Acceptance
- **rj-join**: A fixture with two sessions and five records attaches each record correctly, marks the overlap record ambiguous on both sessions, and leaves the outside and other-project records unattached.; tdd; session-analysis; python3 -m pytest -q tests/test_record_join.py _(id: [rec-fa22cc2f-06e1-491e-a277-9c9ab01fa21e](./records/project__acceptance/rec-fa22cc2f-06e1-491e-a277-9c9ab01fa21e.md))_

### Check
- **rj-join**: rec-fa22cc2f-06e1-491e-a277-9c9ab01fa21e; dirty; pass; tdd _(id: [rec-c6653684-ddd4-40ea-b5bf-2f494fe9e3bd](./records/project__check-run/rec-c6653684-ddd4-40ea-b5bf-2f494fe9e3bd.md))_

## rj-record-reader

### Acceptance
- **rj-record-reader**: Stub CLI output yields metadata rows with parsed UTC times and no body text.; tdd; session-analysis; python3 -m pytest -q tests/test_record_reader.py _(id: [rec-f89ab522-1803-4881-b257-f9a885c2d0de](./records/project__acceptance/rec-f89ab522-1803-4881-b257-f9a885c2d0de.md))_

### Check
- **rj-record-reader**: rec-f89ab522-1803-4881-b257-f9a885c2d0de; dirty; pass; tdd _(id: [rec-d0f1920c-4142-43ce-a7e2-a539e6d1ff02](./records/project__check-run/rec-d0f1920c-4142-43ce-a7e2-a539e6d1ff02.md))_

## rj-report-records

### Acceptance
- **rj-report-records**: With --records the report adds record counts per session on a fixture, and without the flag the output is byte-identical to before.; tdd; session-analysis; python3 -m pytest -q tests/test_session_report.py _(id: [rec-193dfd71-f09c-43b5-95db-e685a4a80e4f](./records/project__acceptance/rec-193dfd71-f09c-43b5-95db-e685a4a80e4f.md))_

### Check
- **rj-report-records**: rec-193dfd71-f09c-43b5-95db-e685a4a80e4f; dirty; pass; tdd _(id: [rec-4ba0fea6-e2d0-4a40-a875-158c1643e93b](./records/project__check-run/rec-4ba0fea6-e2d0-4a40-a875-158c1643e93b.md))_

### Finding
- **rj-report-records**: The project-plus-time-window join leaves 70% of attached records ambiguous (386 of 553), so per-session record counts are unreliable for overlapping sessions.; Real run of session_report.py --records over 247 sessions: 8 sessions have records, 553 records attach, 386 attach to two or more sessions.; Records carry a session id, or sessions get narrower activity windows that remove the overlap.; human _(id: [rec-b8213c07-3cf9-4b56-a2a5-e9f56bd93f78](./records/project__finding/rec-b8213c07-3cf9-4b56-a2a5-e9f56bd93f78.md))_

## route-through-discuss

### Acceptance
- **route-through-discuss**: engage, plan-phase, execute-phase and README route through discuss and the review gate; consistency tests pass; tdd; workflow-loop; python3 -m pytest tests/test_skill_contract_consistency.py tests/test_discuss_skill.py -q _(id: [rec-aac400ee-30c6-4fd2-a3ba-9fbd756f740a](./records/project__acceptance/rec-aac400ee-30c6-4fd2-a3ba-9fbd756f740a.md))_

### Check
- **route-through-discuss**: rec-aac400ee-30c6-4fd2-a3ba-9fbd756f740a; 8c697bc88db7147f17a058311b0323cd4a191fee; pass; tdd _(id: [rec-4faad849-e58b-43c3-971c-0273f995955c](./records/project__check-run/rec-4faad849-e58b-43c3-971c-0273f995955c.md))_

## status-line-from-snapshot

### Acceptance
- **status-line-from-snapshot**: For a seeded store, every status line names an effort in the app snapshot with matching counts, and an effort with no goal prints nothing; the test fails before the fix; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_status.py -q _(id: [rec-fb5c210c-4e78-42c4-8fb9-f8f585e3f5f8](./records/project__acceptance/rec-fb5c210c-4e78-42c4-8fb9-f8f585e3f5f8.md))_

### Check
- **status-line-from-snapshot**: rec-fb5c210c-4e78-42c4-8fb9-f8f585e3f5f8; afd60845e9ffcfcd44d028603b46bdcffadc313a; pass; tdd _(id: [rec-dc270731-1127-4bab-9491-3793856d02ff](./records/project__check-run/rec-dc270731-1127-4bab-9491-3793856d02ff.md))_

### Observation
- **status-line-from-snapshot**: dashboard-status listed efforts from the contract dashboard view (grouped by work-item effort) while the app lists efforts with an active goal, so goal-less efforts appeared only in the status line.; dashboard-bugfix _(id: [rec-34b1b626-5692-42e3-87e5-d7c8562d6cf5](./records/project__investigation-observation/rec-34b1b626-5692-42e3-87e5-d7c8562d6cf5.md))_

## status-tab-row

### Acceptance
- **status-tab-row**: Pilot tests: six tabs on one row at 120 columns, wrapped at 60, each label starts with its number key; the tests fail before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k tab_row _(id: [rec-ba223a32-d09b-4dd0-9256-101bd04d0ea1](./records/project__acceptance/rec-ba223a32-d09b-4dd0-9256-101bd04d0ea1.md))_

### Check
- **status-tab-row**: rec-ba223a32-d09b-4dd0-9256-101bd04d0ea1; ee6469389256ef6d9cf8f8e9c80cd93ef5fcb5aa; pass; tdd _(id: [rec-146b610c-0238-4e4b-9049-a5bb6d569c98](./records/project__check-run/rec-146b610c-0238-4e4b-9049-a5bb6d569c98.md))_

## status-tabs

### Acceptance
- **status-tabs**: Pilot tests at 60 and 120 columns show counts on every tab, default to Active, filter the table by each tab via keys and click, show Needs you tasks from open items, combine with the / filter, and have no d binding; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-5a31e5b1-1af0-4738-bf89-20d16bf3dcaa](./records/project__acceptance/rec-5a31e5b1-1af0-4738-bf89-20d16bf3dcaa.md))_

### Check
- **status-tabs**: rec-5a31e5b1-1af0-4738-bf89-20d16bf3dcaa; 75e530c1e06c4584efe45adfad12d926e8843849; pass; check _(id: [rec-0734553d-7a25-4dd7-af9b-6ef24e128a1d](./records/project__check-run/rec-0734553d-7a25-4dd7-af9b-6ef24e128a1d.md))_
- **status-tabs**: rec-5a31e5b1-1af0-4738-bf89-20d16bf3dcaa; f6153cee88400795bfb23fb4d0d97e48e69438c9; pass; check _(id: [rec-4bb08f27-39d2-46a7-9b11-69a848dc6b79](./records/project__check-run/rec-4bb08f27-39d2-46a7-9b11-69a848dc6b79.md))_

### Finding
- **status-tabs**: status-tabs gap closed: 7 tabs, keys 1-7, left/right and README landed at 75e530c; Execution report rec-10a142d4 and a parent re-run of 116 passing tests at 75e530c; A tab, key or README row from the description is missing; none _(id: [rec-94362ae8-0f01-4ad1-bfcd-cffa426566b8](./records/project__finding/rec-94362ae8-0f01-4ad1-bfcd-cffa426566b8.md))_

## stepper-wrap

### Acceptance
- **stepper-wrap**: Pilot test at 60 columns: every stepper line starts with a phase glyph and no line ends with a bare glyph, and no line is wider than the pane; the test fails before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k stepper _(id: [rec-c2df3f61-8b0b-44d8-89b3-f3033ebcf9d0](./records/project__acceptance/rec-c2df3f61-8b0b-44d8-89b3-f3033ebcf9d0.md))_

### Check
- **stepper-wrap**: rec-c2df3f61-8b0b-44d8-89b3-f3033ebcf9d0; 0ec0a8bb801ff9f528cfd6366bd5c08208282ff4; pass; tdd _(id: [rec-6a6b6040-193a-42e4-b5fc-4bab45d162e8](./records/project__check-run/rec-6a6b6040-193a-42e4-b5fc-4bab45d162e8.md))_

### Observation
- **stepper-wrap**: test_stepper_wraps_by_pane_width_and_keeps_glyph_with_label failed 3/10: stepper lines were wider than pane.scrollable_content_region.width. Hypothesis: the status-tab grid wraps, the pane overflows 20 rows, a vertical scrollbar appears after the stepper rendered, narrowing the content region without a pane resize, so EffortPane.on_resize never re-shows.; dashboard-features _(id: [rec-b3951803-56a0-4f76-aefb-68962a329e8a](./records/project__investigation-observation/rec-b3951803-56a0-4f76-aefb-68962a329e8a.md))_

## table-focus

### Acceptance
- **table-focus**: Pick an empty tab, pick Active, press down: the cursor is on row 1 and enter opens that row; the test fails before the fix; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k focus _(id: [rec-2536ed50-f949-40fe-a914-f283c9633975](./records/project__acceptance/rec-2536ed50-f949-40fe-a914-f283c9633975.md))_

### Check
- **table-focus**: rec-2536ed50-f949-40fe-a914-f283c9633975; 1aeb3058d93fa9ac486dd0d6de690d7c0d681388; pass; tdd _(id: [rec-d9988bf2-7166-422b-beb2-94ee365a1a0b](./records/project__check-run/rec-d9988bf2-7166-422b-beb2-94ee365a1a0b.md))_

### Observation
- **table-focus**: After an empty status tab hides #tasks, a tab that shows it again leaves app.focused None; arrows do nothing and enter opens row 0. Root cause: select_status_tab never refocuses the table after fill_tasks hides it.; dashboard-bugfix _(id: [rec-2c0c2c80-ff18-40fe-801a-e3f95f11e0e0](./records/project__investigation-observation/rec-2c0c2c80-ff18-40fe-801a-e3f95f11e0e0.md))_

## task-detail-links

### Acceptance
- **task-detail-links**: Pilot tests: in a task detail, enter on a dependency opens that task, enter on a blocked task opens it, enter on the phase opens the phase detail, and esc walks back one screen at a time; the tests fail before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k link _(id: [rec-79b9e2f6-49a8-4d48-8788-0da94d698726](./records/project__acceptance/rec-79b9e2f6-49a8-4d48-8788-0da94d698726.md))_

### Check
- **task-detail-links**: rec-79b9e2f6-49a8-4d48-8788-0da94d698726; f1d91299f3812c61327da0d352b1541bebdc0d38; pass; tdd _(id: [rec-3c74b663-3b9f-4872-b3ef-a3e4e8acec7a](./records/project__check-run/rec-3c74b663-3b9f-4872-b3ef-a3e4e8acec7a.md))_

## task-detail-model

### Acceptance
- **task-detail-model**: Tests against a temp store show the loader returns the work-item, dependency links, acceptances with their latest check-run, the ordered timeline with report bodies, and related findings, and ignores another task whose slug shares a prefix; tdd; dashboard; python3 -m pytest tests/test_dashboard_model.py -q _(id: [rec-8f020a2f-f7de-43e3-b46f-423d52e44fe4](./records/project__acceptance/rec-8f020a2f-f7de-43e3-b46f-423d52e44fe4.md))_

### Check
- **task-detail-model**: rec-8f020a2f-f7de-43e3-b46f-423d52e44fe4; 38c2399; pass; tdd _(id: [rec-93b50136-8ef3-4e78-a5fd-29d38ee008b8](./records/project__check-run/rec-93b50136-8ef3-4e78-a5fd-29d38ee008b8.md))_

## task-detail-screen

### Acceptance
- **task-detail-screen**: Textual pilot tests at 60 and 160 columns open the detail screen by Enter and by click, find every section's content for a seeded task, see a redraw after a store change, and return to the same row on Esc; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-421586f5-5f49-4a47-b715-eeb09ad69b90](./records/project__acceptance/rec-421586f5-5f49-4a47-b715-eeb09ad69b90.md))_

### Check
- **task-detail-screen**: rec-421586f5-5f49-4a47-b715-eeb09ad69b90; e6cf774; pass; tdd _(id: [rec-d4342ee2-0473-4fa8-b8b8-4abc42c914ec](./records/project__check-run/rec-d4342ee2-0473-4fa8-b8b8-4abc42c914ec.md))_

## task-list-filters

### Acceptance
- **task-list-filters**: Pilot tests at 60 and 120 columns narrow the table by typed text, clear it with Esc, hide and show done tasks with d, keep both across a store refresh, and show them in the panel title; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q _(id: [rec-982fcf31-6ef8-41aa-97a6-03ec860bfccb](./records/project__acceptance/rec-982fcf31-6ef8-41aa-97a6-03ec860bfccb.md))_

### Check
- **task-list-filters**: rec-982fcf31-6ef8-41aa-97a6-03ec860bfccb; e3b7751; pass; tdd _(id: [rec-faa84f50-9fb4-422a-b887-7877e889ac3b](./records/project__check-run/rec-faa84f50-9fb4-422a-b887-7877e889ac3b.md))_

## task-row-cells

### Acceptance
- **task-row-cells**: Pilot tests: a waiting row shows waits on with its unfinished dependencies, a running row shows its running time, the task detail shows it, and the grouped table has no phase column at 60 and 120 columns; the tests fail before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k 'waits or running or phase_column' _(id: [rec-daa1a988-73f2-45f9-8cde-f795662613c1](./records/project__acceptance/rec-daa1a988-73f2-45f9-8cde-f795662613c1.md))_

### Check
- **task-row-cells**: rec-daa1a988-73f2-45f9-8cde-f795662613c1; ef6325fb4ef1128ad071f79e64d709bd1d28781d; pass; tdd _(id: [rec-79370462-4380-4f9b-94d2-a90ed8569ee7](./records/project__check-run/rec-79370462-4380-4f9b-94d2-a90ed8569ee7.md))_

## task-row-model

### Acceptance
- **task-row-model**: Model tests: waits_on lists only unfinished dependency slugs, running_since is the latest assignment time for an in-progress task and None otherwise; the tests fail before the change; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py -q -k 'waits or running' _(id: [rec-60e78986-208c-43d5-8207-9803afeab4df](./records/project__acceptance/rec-60e78986-208c-43d5-8207-9803afeab4df.md))_

### Check
- **task-row-model**: rec-60e78986-208c-43d5-8207-9803afeab4df; 865fc75f021559acf6184b145f73f5b8ca57c313; pass; tdd _(id: [rec-f112e2ec-e4d3-46b7-9e18-40531b7f5da2](./records/project__check-run/rec-f112e2ec-e4d3-46b7-9e18-40531b7f5da2.md))_

### Observation
- **task-row-model**: Withdrawn dependencies stay in waits_on, matching the engine: derived.ready only treats done as satisfied, so the task really is still waiting.; dashboard-features _(id: [rec-a6aba57e-2094-4cc5-9145-31dccbf7f288](./records/project__investigation-observation/rec-a6aba57e-2094-4cc5-9145-31dccbf7f288.md))_

## terminal-view-format

### Acceptance
- **terminal-view-format**: Given a rendered dashboard, the formatter output has no id suffixes or banner, headings are bold only with colour on, no line exceeds the width, and an empty view gives the empty-state line; tdd; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q _(id: [rec-afb68d05-d961-45dd-813e-948c8e137722](./records/project__acceptance/rec-afb68d05-d961-45dd-813e-948c8e137722.md))_

### Check
- **terminal-view-format**: rec-afb68d05-d961-45dd-813e-948c8e137722; 0f8791a808f1a5d81eb5beb6e03a7b56905f1644; pass; tdd _(id: [rec-0a4f74c4-1ca9-485b-ad92-c50608f178e5](./records/project__check-run/rec-0a4f74c4-1ca9-485b-ad92-c50608f178e5.md))_

## test-suite-speed

### Acceptance
- **test-suite-speed**: All 262 tests pass, full suite wall time is at most 158s (half of the 317s clean-HEAD baseline), CPU time stays under 250s, and no timeout or deadline value is larger than before the change; check; test-suite-speed; time uv run --with textual --with pytest python -m pytest tests -q _(id: [rec-6e6e5c69-9ab0-44f3-9016-49c3512fcd99](./records/project__acceptance/rec-6e6e5c69-9ab0-44f3-9016-49c3512fcd99.md))_

### Check
- **test-suite-speed**: rec-6e6e5c69-9ab0-44f3-9016-49c3512fcd99; 6cb58b4; pass; check _(id: [rec-e81acb74-ed4a-4e0f-bb5c-9ea42abfa56e](./records/project__check-run/rec-e81acb74-ed4a-4e0f-bb5c-9ea42abfa56e.md))_

## tm-cli

### Acceptance
- **tm-cli**: The command over a fixture projects directory prints valid JSON with one summary per session and no message text.; tdd; session-analysis; python3 -m pytest -q tests/test_session_report.py _(id: [rec-be629630-2798-4a55-92ca-322aba930e94](./records/project__acceptance/rec-be629630-2798-4a55-92ca-322aba930e94.md))_

### Check
- **tm-cli**: rec-be629630-2798-4a55-92ca-322aba930e94; dirty; pass; tdd _(id: [rec-4f4277b5-896a-4a11-a64f-5db71bc729fb](./records/project__check-run/rec-4f4277b5-896a-4a11-a64f-5db71bc729fb.md))_

## tm-parse-events

### Acceptance
- **tm-parse-events**: A fixture with a malformed line and an unknown event type yields all valid events and a bad-line count of 1.; tdd; session-analysis; python3 -m pytest -q tests/test_session_metrics.py -k parse _(id: [rec-2df7a704-c3ba-43a0-966d-42474d3c2318](./records/project__acceptance/rec-2df7a704-c3ba-43a0-966d-42474d3c2318.md))_

### Check
- **tm-parse-events**: rec-2df7a704-c3ba-43a0-966d-42474d3c2318; dirty; pass; tdd _(id: [rec-95a8ff7f-ad6e-4e72-8d4f-10f08cc8e68b](./records/project__check-run/rec-95a8ff7f-ad6e-4e72-8d4f-10f08cc8e68b.md))_

## tm-session-fields

### Acceptance
- **tm-session-fields**: A fixture yields the expected session id, branch, duration, turn count, cost and skill names.; tdd; session-analysis; python3 -m pytest -q tests/test_session_fields.py _(id: [rec-5f8ebfcf-f591-4f07-932d-65fabc8871fb](./records/project__acceptance/rec-5f8ebfcf-f591-4f07-932d-65fabc8871fb.md))_

### Check
- **tm-session-fields**: rec-5f8ebfcf-f591-4f07-932d-65fabc8871fb; dirty; pass; tdd _(id: [rec-da978d42-a6a0-4ac2-986b-6cc1e1121e13](./records/project__check-run/rec-da978d42-a6a0-4ac2-986b-6cc1e1121e13.md))_

## tm-tool-metrics

### Acceptance
- **tm-tool-metrics**: A fixture with 5 tool calls, 2 errors and 1 retry yields exactly those counts per tool name.; tdd; session-analysis; python3 -m pytest -q tests/test_session_tools.py _(id: [rec-eb5399be-74fd-4403-bf2d-69fb1cb5bce9](./records/project__acceptance/rec-eb5399be-74fd-4403-bf2d-69fb1cb5bce9.md))_

### Check
- **tm-tool-metrics**: rec-eb5399be-74fd-4403-bf2d-69fb1cb5bce9; dirty; pass; tdd _(id: [rec-61c34384-57d2-4cb4-9033-6a25173c9e45](./records/project__check-run/rec-61c34384-57d2-4cb4-9033-6a25173c9e45.md))_

## tmux-suite-flake

### Finding
- **tmux-suite-flake**: One tmux integration test fails rarely: 1 of 19 serial tmux runs on e4484c4, test name not captured; Parent reruns on fix/dashboard-bugfix: 1 failed of 10 right after the xdist run, then 18 clean runs (15 full tmux runs, 3 full sequences); the extended popup test passed 12/12 alone; A tmux failure is captured with -rf and fixed, or 50 consecutive clean runs _(id: [rec-68330501-7b9a-446c-b24a-bf84af04e8e8](./records/project__finding/rec-68330501-7b9a-446c-b24a-bf84af04e8e8.md))_

## tmux-test-waits

### Acceptance
- **tmux-test-waits**: The six failing tmux and e2e tests pass, and each tmux popup test takes under 4s; check; test-suite-speed; python3 -m pytest tests/test_tmux_integration.py tests/test_e2e_dashboard.py -q --durations=6 _(id: [rec-572fa450-b4a2-45bb-b52e-b5198f0e9b91](./records/project__acceptance/rec-572fa450-b4a2-45bb-b52e-b5198f0e9b91.md))_

## unsigned-check-label

### Acceptance
- **unsigned-check-label**: An unsigned check reads as its acceptance criterion and task slug, never a rec- id, with a fallback when the acceptance is missing; the test fails before the fix; tdd; dashboard; uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py -q -k unsigned _(id: [rec-403febb3-cbe5-474d-8413-5687934c29d2](./records/project__acceptance/rec-403febb3-cbe5-474d-8413-5687934c29d2.md))_

### Check
- **unsigned-check-label**: rec-403febb3-cbe5-474d-8413-5687934c29d2; 3ca5175c7dc8e6e60b0f501bf3c0e30309e9403d; pass; tdd _(id: [rec-7d02868c-4d2e-4265-8548-c3b0ab4de18c](./records/project__check-run/rec-7d02868c-4d2e-4265-8548-c3b0ab4de18c.md))_

### Observation
- **unsigned-check-label**: _needs_you built unsigned-check text from the raw criterion_id and used the check-run subject, so the panel showed a rec- id instead of the criterion and task.; dashboard-bugfix _(id: [rec-45a1d50b-0dae-47ec-88c3-19cab12238ba](./records/project__investigation-observation/rec-45a1d50b-0dae-47ec-88c3-19cab12238ba.md))_

## verify-dashboard-actions-phase

### Acceptance
- **verify-dashboard-actions-phase**: The full test suite passes, including a tmux test that filters, copies a slug into the tmux buffer, and opens a commit view in the popup; check; dashboard; uv run --with textual --with pytest python -m pytest tests -q _(id: [rec-468f8719-9cf5-4262-aea7-6d372a9cd6a9](./records/project__acceptance/rec-468f8719-9cf5-4262-aea7-6d372a9cd6a9.md))_

### Check
- **verify-dashboard-actions-phase**: rec-468f8719-9cf5-4262-aea7-6d372a9cd6a9; 03d561c; pass; check _(id: [rec-5d987a65-62e1-4cdf-b91a-3ecf881ab599](./records/project__check-run/rec-5d987a65-62e1-4cdf-b91a-3ecf881ab599.md))_

## verify-dashboard-actions-phase-signoff

### Acceptance
- **verify-dashboard-actions-phase-signoff**: The user tries filter, hide-done, copy, and commit view in the popup and the side pane and signs off; manual; dashboard _(id: [rec-aa7012e9-f5d9-427c-a0d5-74e173544519](./records/project__acceptance/rec-aa7012e9-f5d9-427c-a0d5-74e173544519.md))_

### Check
- **verify-dashboard-actions-phase-signoff**: rec-aa7012e9-f5d9-427c-a0d5-74e173544519; 03d561c; pass; manual; ayin _(id: [rec-78f4574a-6127-4ae1-96c4-73dc987b5fb5](./records/project__check-run/rec-78f4574a-6127-4ae1-96c4-73dc987b5fb5.md))_

## verify-dashboard-view-phase

### Acceptance
- **verify-dashboard-view-phase**: The CLI integration test passes: after each lifecycle step every record appears in exactly its expected dashboard section; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests/test_dashboard_integration.py -q _(id: [rec-35c98548-4ccf-4c7c-8286-3a1e7ba21185](./records/project__acceptance/rec-35c98548-4ccf-4c7c-8286-3a1e7ba21185.md))_

### Check
- **verify-dashboard-view-phase**: rec-83fc3486-af5f-49af-9000-8d9fd6890f3c; 5ba4e0a; pass; manual; ayin _(id: [rec-2141a70f-c8a2-4b54-ae34-9dc12cbf02f2](./records/project__check-run/rec-2141a70f-c8a2-4b54-ae34-9dc12cbf02f2.md))_
- **verify-dashboard-view-phase**: rec-83fc3486-af5f-49af-9000-8d9fd6890f3c; 5ba4e0a; pass; manual _(id: [rec-8a7977e1-dba3-47b2-a074-5f9b6b91fe15](./records/project__check-run/rec-8a7977e1-dba3-47b2-a074-5f9b6b91fe15.md))_
- **verify-dashboard-view-phase**: rec-1a3c142c-b9c6-4f57-baf0-b38000b5bb9f; 5ba4e0a; fail; check _(id: [rec-8c16b297-2e38-48b5-8259-b8c2211f2a1f](./records/project__check-run/rec-8c16b297-2e38-48b5-8259-b8c2211f2a1f.md))_
- **verify-dashboard-view-phase**: rec-1a3c142c-b9c6-4f57-baf0-b38000b5bb9f; aa:92f1e0d se:5ba4e0a; pass; check _(id: [rec-dd5cd8a1-81be-4583-a6a3-c30f14c9a1e4](./records/project__check-run/rec-dd5cd8a1-81be-4583-a6a3-c30f14c9a1e4.md))_
- **verify-dashboard-view-phase**: rec-35c98548-4ccf-4c7c-8286-3a1e7ba21185; 5ba4e0a; pass; tdd _(id: [rec-e8e1a102-2225-493f-9dfb-f1fa5c21e3f1](./records/project__check-run/rec-e8e1a102-2225-493f-9dfb-f1fa5c21e3f1.md))_

## verify-dashboard-view-phase-live

### Acceptance
- **verify-dashboard-view-phase-live**: The dashboard rendered from ~/.artifacts/se-workflow shows the watch-dashboard goal, phase dashboard-view, the open plugin question under needs-you, and each phase-1 task in the section its lifecycle implies; manual; dashboard; ~/adaptive-artifacts/bin/adaptive-artifacts --store ~/.artifacts/se-workflow view --id project:dashboard _(id: [rec-83fc3486-af5f-49af-9000-8d9fd6890f3c](./records/project__acceptance/rec-83fc3486-af5f-49af-9000-8d9fd6890f3c.md))_

## verify-dashboard-view-phase-suites

### Acceptance
- **verify-dashboard-view-phase-suites**: Full test suites of both repos pass on the phase-1 changes; check; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q && cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-1a3c142c-b9c6-4f57-baf0-b38000b5bb9f](./records/project__acceptance/rec-1a3c142c-b9c6-4f57-baf0-b38000b5bb9f.md))_

## verify-end-to-end-phase

### Acceptance
- **verify-end-to-end-phase**: Scripted end-to-end test and both full suites pass; check; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q && cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-a5e71d14-1f25-4868-a42e-3a2b17e16616](./records/project__acceptance/rec-a5e71d14-1f25-4868-a42e-3a2b17e16616.md))_

### Check
- **verify-end-to-end-phase**: rec-a5e71d14-1f25-4868-a42e-3a2b17e16616; aa:227523b se:a3b4ee2; pass; check _(id: [rec-01016663-beda-482a-810a-0d16bd2c46b8](./records/project__check-run/rec-01016663-beda-482a-810a-0d16bd2c46b8.md))_
- **verify-end-to-end-phase**: rec-a5e71d14-1f25-4868-a42e-3a2b17e16616; dirty; pass; check _(id: [rec-2e3f5376-89d0-4d9f-8029-3bb418ae2ef8](./records/project__check-run/rec-2e3f5376-89d0-4d9f-8029-3bb418ae2ef8.md))_
- **verify-end-to-end-phase**: rec-9dce7bb8-9cc7-4a4d-9ebd-48a749f7cc85; se:a3b4ee2; fail; check _(id: [rec-a746fedb-faa4-4de5-b32c-ba6466e9fad6](./records/project__check-run/rec-a746fedb-faa4-4de5-b32c-ba6466e9fad6.md))_
- **verify-end-to-end-phase**: rec-9dce7bb8-9cc7-4a4d-9ebd-48a749f7cc85; dirty; pass; check _(id: [rec-ae0525f6-a5fc-45bc-ba9e-b3798959856f](./records/project__check-run/rec-ae0525f6-a5fc-45bc-ba9e-b3798959856f.md))_

## verify-end-to-end-phase-clear

### Acceptance
- **verify-end-to-end-phase-clear**: The watch-dashboard dashboard shows no Open Question, Needs Human, or Unsigned Manual Check; check; dashboard; ~/se-workflow/scripts/dashboard-status ~/se-workflow _(id: [rec-9dce7bb8-9cc7-4a4d-9ebd-48a749f7cc85](./records/project__acceptance/rec-9dce7bb8-9cc7-4a4d-9ebd-48a749f7cc85.md))_

## verify-layout-phase

### Acceptance
- **verify-layout-phase**: The tmux popup layout test passes, README shows the tab row with number keys, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux -rf _(id: [rec-5d64f143-cdea-49dc-8cb4-7ca9fb9f2517](./records/project__acceptance/rec-5d64f143-cdea-49dc-8cb4-7ca9fb9f2517.md))_

### Check
- **verify-layout-phase**: rec-5d64f143-cdea-49dc-8cb4-7ca9fb9f2517; d9e3eebae5096d3bfd0852e9a910fe4e8df9a725; pass; check _(id: [rec-b2b9ebb8-5411-4a63-93c3-1028295a1ce7](./records/project__check-run/rec-b2b9ebb8-5411-4a63-93c3-1028295a1ce7.md))_

## verify-navigation-phase

### Acceptance
- **verify-navigation-phase**: The tmux popup navigation test passes, README documents detail links, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux -rf _(id: [rec-d1da938c-12b5-4cb9-9f02-e4a6731c1222](./records/project__acceptance/rec-d1da938c-12b5-4cb9-9f02-e4a6731c1222.md))_

### Check
- **verify-navigation-phase**: rec-d1da938c-12b5-4cb9-9f02-e4a6731c1222; b892587e80bbd40f785d3e104581a5587c250406; pass; check _(id: [rec-f864bb3e-40ce-4a6d-b048-471044f223c5](./records/project__check-run/rec-f864bb3e-40ce-4a6d-b048-471044f223c5.md))_

## verify-needs-you-data-phase

### Acceptance
- **verify-needs-you-data-phase**: The tmux popup tests pass with six tabs, a counted Needs you title and a readable unsigned line, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux _(id: [rec-fe83e6fe-5005-4c88-97e8-3c15e744047a](./records/project__acceptance/rec-fe83e6fe-5005-4c88-97e8-3c15e744047a.md))_

### Check
- **verify-needs-you-data-phase**: rec-fe83e6fe-5005-4c88-97e8-3c15e744047a; e4484c4c6ed29016f301e3e963957a2aa7bfdcac; pass; check _(id: [rec-0d607cff-8414-4a07-886b-115e54b99dbe](./records/project__check-run/rec-0d607cff-8414-4a07-886b-115e54b99dbe.md))_

## verify-needs-you-phase

### Acceptance
- **verify-needs-you-phase**: The tmux popup test for Needs you and finished efforts passes, README documents n and the Needs-you detail, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux _(id: [rec-d5958a14-e6a7-4c20-b110-5ae0c0ee54a3](./records/project__acceptance/rec-d5958a14-e6a7-4c20-b110-5ae0c0ee54a3.md))_

### Check
- **verify-needs-you-phase**: rec-d5958a14-e6a7-4c20-b110-5ae0c0ee54a3; 94e39818ef6151434de8ef1617c69e0c9dcbda6b; pass; check _(id: [rec-e5ff5760-6474-4fc5-8f68-9d1e0a3d4453](./records/project__check-run/rec-e5ff5760-6474-4fc5-8f68-9d1e0a3d4453.md))_

### Observation
- **verify-needs-you-phase**: tab from a live effort with Needs you items to a pane whose task table is hidden bounces back: Screen._reset_focus moves focus from the hidden TaskTable to the sibling NeedsList, and TabbedContent re-activates the pane holding focus. Reproduces every run; absent without Needs you items.; dashboard-features _(id: [rec-63c67821-d6d9-4012-8437-37c5beda8310](./records/project__investigation-observation/rec-63c67821-d6d9-4012-8437-37c5beda8310.md))_

## verify-readable-layout-phase

### Acceptance
- **verify-readable-layout-phase**: The full test suite passes with the new dashboard in the isolated tmux server; check; dashboard; uv run --with textual --with pytest python -m pytest tests -q _(id: [rec-b9c2eff5-a486-4b57-89bc-cc4a3aa95314](./records/project__acceptance/rec-b9c2eff5-a486-4b57-89bc-cc4a3aa95314.md))_

### Check
- **verify-readable-layout-phase**: rec-b9c2eff5-a486-4b57-89bc-cc4a3aa95314; 360ebcc; pass; check _(id: [rec-0efdae3e-e624-4a9e-9b04-d42daa11fd0f](./records/project__check-run/rec-0efdae3e-e624-4a9e-9b04-d42daa11fd0f.md))_

## verify-readable-layout-phase-signoff

### Acceptance
- **verify-readable-layout-phase-signoff**: The user views the dashboard in the popup and the side pane and signs off that it is readable and clean; manual; dashboard _(id: [rec-83820e9f-6ff5-407c-aa8f-deb4e441d5a5](./records/project__acceptance/rec-83820e9f-6ff5-407c-aa8f-deb4e441d5a5.md))_

### Check
- **verify-readable-layout-phase-signoff**: rec-83820e9f-6ff5-407c-aa8f-deb4e441d5a5; 360ebcc; pass; manual; ayin _(id: [rec-ca53b246-7587-4e4e-9c59-75ca4deed553](./records/project__check-run/rec-ca53b246-7587-4e4e-9c59-75ca4deed553.md))_

## verify-status-line-phase

### Acceptance
- **verify-status-line-phase**: The tmux status segment and e2e tests pass with the rebuilt status line, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux _(id: [rec-2e2b15a3-c245-48ab-874a-9efbfd69ff60](./records/project__acceptance/rec-2e2b15a3-c245-48ab-874a-9efbfd69ff60.md))_

### Check
- **verify-status-line-phase**: rec-2e2b15a3-c245-48ab-874a-9efbfd69ff60; afd60845e9ffcfcd44d028603b46bdcffadc313a; pass; check _(id: [rec-43db24a6-a3a6-4320-b00e-64c22fd00fa5](./records/project__check-run/rec-43db24a6-a3a6-4320-b00e-64c22fd00fa5.md))_

## verify-table-state-phase

### Acceptance
- **verify-table-state-phase**: The tmux popup test for focus and resize passes, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux _(id: [rec-c31c7b82-4a88-43bf-877c-1ffabb4f08e3](./records/project__acceptance/rec-c31c7b82-4a88-43bf-877c-1ffabb4f08e3.md))_

### Check
- **verify-table-state-phase**: rec-c31c7b82-4a88-43bf-877c-1ffabb4f08e3; 3d740d2b7c02175520ca2f03e713c70c450c6603; pass; check _(id: [rec-cdcf77bc-e4da-4c06-8707-0180febff2ce](./records/project__check-run/rec-cdcf77bc-e4da-4c06-8707-0180febff2ce.md))_

### Observation
- **verify-table-state-phase**: Without b104980 the stale-width resize race fails the tmux test in about 4 of 5 runs; the pilot test from b104980 is the deterministic guard.; dashboard-bugfix _(id: [rec-9feddfcd-4869-456a-9597-16da85a789cc](./records/project__investigation-observation/rec-9feddfcd-4869-456a-9597-16da85a789cc.md))_

## verify-task-details-phase

### Acceptance
- **verify-task-details-phase**: The full test suite passes, including a tmux test that opens a task's detail screen in the popup and sees it update through a lifecycle; check; dashboard; uv run --with textual --with pytest python -m pytest tests -q _(id: [rec-98ab04e9-ab1a-488f-8712-716c9a11b7ba](./records/project__acceptance/rec-98ab04e9-ab1a-488f-8712-716c9a11b7ba.md))_

### Check
- **verify-task-details-phase**: rec-98ab04e9-ab1a-488f-8712-716c9a11b7ba; 70b0501; pass; check _(id: [rec-d63e8d3d-8054-4434-9f6a-908518f99237](./records/project__check-run/rec-d63e8d3d-8054-4434-9f6a-908518f99237.md))_

## verify-task-details-phase-signoff

### Acceptance
- **verify-task-details-phase-signoff**: The user opens task details in the popup and the side pane and signs off that they show what the task needs and what happened on it; manual; dashboard _(id: [rec-11643a9d-4693-4761-b94a-ba3a6be27ad6](./records/project__acceptance/rec-11643a9d-4693-4761-b94a-ba3a6be27ad6.md))_

### Check
- **verify-task-details-phase-signoff**: rec-11643a9d-4693-4761-b94a-ba3a6be27ad6; 03d561c; pass; manual; ayin _(id: [rec-3049cecc-9049-4792-b1d6-8d607534885f](./records/project__check-run/rec-3049cecc-9049-4792-b1d6-8d607534885f.md))_

## verify-task-navigation-phase

### Acceptance
- **verify-task-navigation-phase**: The full test suite passes, including a keys-only tmux test through status tabs, phase sections, and a task detail; check; dashboard; uv run --with textual --with pytest python -m pytest tests -q _(id: [rec-b9307639-88bf-43f4-8ad7-d0e4a77db060](./records/project__acceptance/rec-b9307639-88bf-43f4-8ad7-d0e4a77db060.md))_

### Check
- **verify-task-navigation-phase**: rec-892a40a7-5d4e-4027-a096-a484d58b9787; 671220afbe8e7adb39f8e250bfafed07823d11c4; pass; manual; Andrew Yin _(id: [rec-553ce6d1-ba21-49fc-9c32-cbab20dab9ca](./records/project__check-run/rec-553ce6d1-ba21-49fc-9c32-cbab20dab9ca.md))_
- **verify-task-navigation-phase**: rec-b9307639-88bf-43f4-8ad7-d0e4a77db060; 671220afbe8e7adb39f8e250bfafed07823d11c4; pass; check _(id: [rec-ac579a85-7728-4f68-9674-bdc27b578da9](./records/project__check-run/rec-ac579a85-7728-4f68-9674-bdc27b578da9.md))_
- **verify-task-navigation-phase**: rec-b9307639-88bf-43f4-8ad7-d0e4a77db060; 671220afbe8e7adb39f8e250bfafed07823d11c4; pass; check _(id: [rec-f5162a90-c6e6-48fe-b3ae-2aaffcf1ddae](./records/project__check-run/rec-f5162a90-c6e6-48fe-b3ae-2aaffcf1ddae.md))_

## verify-task-navigation-phase-signoff

### Acceptance
- **verify-task-navigation-phase-signoff**: The user navigates with the keyboard, status tabs, and phase sections in the popup and the side pane and signs off; manual; dashboard _(id: [rec-892a40a7-5d4e-4027-a096-a484d58b9787](./records/project__acceptance/rec-892a40a7-5d4e-4027-a096-a484d58b9787.md))_

## verify-task-rows-phase

### Acceptance
- **verify-task-rows-phase**: The tmux popup test for task rows and activity passes, README describes waits-on, running time and failed activity, and the full suite passes; check; dashboard; uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' && uv run --with textual --with pytest python -m pytest tests -q -m tmux -rf _(id: [rec-92df6b15-9068-4342-b3fa-899bc28247b3](./records/project__acceptance/rec-92df6b15-9068-4342-b3fa-899bc28247b3.md))_

### Check
- **verify-task-rows-phase**: rec-92df6b15-9068-4342-b3fa-899bc28247b3; e6591ab8dd58b85e63d1bed9702b6edaf0b236a1; pass; check _(id: [rec-07e2fbea-ed1f-4ea9-95b1-0b6416449996](./records/project__check-run/rec-07e2fbea-ed1f-4ea9-95b1-0b6416449996.md))_

## verify-tmux-integration-phase

### Acceptance
- **verify-tmux-integration-phase**: The isolated tmux test passes: the side pane shows the repo's dashboard, the popup binding runs the launcher in the pane directory and renders, and the status segment counts match; tdd; dashboard; cd ~/se-workflow && python3 -m pytest tests/test_tmux_integration.py -q _(id: [rec-66a8f44a-bfea-4ee2-aea0-cbe426d17d69](./records/project__acceptance/rec-66a8f44a-bfea-4ee2-aea0-cbe426d17d69.md))_

### Check
- **verify-tmux-integration-phase**: rec-66a8f44a-bfea-4ee2-aea0-cbe426d17d69; ea5a5c9; pass; tdd _(id: [rec-08b2c386-6b30-4edb-ae03-1e4897affc66](./records/project__check-run/rec-08b2c386-6b30-4edb-ae03-1e4897affc66.md))_
- **verify-tmux-integration-phase**: rec-4a323bc2-c820-4133-8409-d9be1a13b97a; aa:227523b se:ea5a5c9; pass; check _(id: [rec-9298f363-45b4-4925-a9fa-c1d4ab529196](./records/project__check-run/rec-9298f363-45b4-4925-a9fa-c1d4ab529196.md))_

## verify-tmux-integration-phase-suites

### Acceptance
- **verify-tmux-integration-phase-suites**: Full test suites of both repos pass on the phase-3 changes; check; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q && cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-4a323bc2-c820-4133-8409-d9be1a13b97a](./records/project__acceptance/rec-4a323bc2-c820-4133-8409-d9be1a13b97a.md))_

## verify-watch-renderer-phase

### Acceptance
- **verify-watch-renderer-phase**: The pty integration test passes: first frame shown, redraw within 3 s of a record write, zero redraws over an idle second, SIGINT exits 0; tdd; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q -k watch_integration _(id: [rec-cadda757-0424-444f-8ae1-31d415d18e6d](./records/project__acceptance/rec-cadda757-0424-444f-8ae1-31d415d18e6d.md))_

### Check
- **verify-watch-renderer-phase**: rec-02bac654-25f6-4bc0-b6ec-5efa03a4941e; 227523b; pass; check _(id: [rec-5e3ceb64-1808-4d83-b107-c53695f20ae2](./records/project__check-run/rec-5e3ceb64-1808-4d83-b107-c53695f20ae2.md))_
- **verify-watch-renderer-phase**: rec-cadda757-0424-444f-8ae1-31d415d18e6d; 227523b; pass; tdd _(id: [rec-61d5c15f-2e8c-444c-a58b-aa9eeccae777](./records/project__check-run/rec-61d5c15f-2e8c-444c-a58b-aa9eeccae777.md))_
- **verify-watch-renderer-phase**: rec-02bac654-25f6-4bc0-b6ec-5efa03a4941e; 227523b; tdd; check rec-cadda757-0424-444f-8ae1-31d415d18e6d _(id: [rec-c5dbe94f-0573-4d20-b91b-25ada50fd363](./records/project__check-run/rec-c5dbe94f-0573-4d20-b91b-25ada50fd363.md))_

## verify-watch-renderer-phase-suites

### Acceptance
- **verify-watch-renderer-phase-suites**: Full test suites of both repos pass on the phase-2 changes; check; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q && cd ~/se-workflow && python3 -m pytest tests -q _(id: [rec-02bac654-25f6-4bc0-b6ec-5efa03a4941e](./records/project__acceptance/rec-02bac654-25f6-4bc0-b6ec-5efa03a4941e.md))_

## watch-command

### Acceptance
- **watch-command**: With an injected clock, sleep and output stream: a changed render gives one redraw, an unchanged render gives none, a render error shows and the loop continues, KeyboardInterrupt returns exit 0, and --once prints one frame; tdd; dashboard; cd ~/adaptive-artifacts && python3 -m pytest tools/runtime/tests -q _(id: [rec-ec792cef-650b-492a-ac2d-eed325546c19](./records/project__acceptance/rec-ec792cef-650b-492a-ac2d-eed325546c19.md))_

### Check
- **watch-command**: rec-ec792cef-650b-492a-ac2d-eed325546c19; 846188f; pass; tdd _(id: [rec-f370db55-4f74-4981-bfae-1d39e925d6ff](./records/project__check-run/rec-f370db55-4f74-4981-bfae-1d39e925d6ff.md))_
