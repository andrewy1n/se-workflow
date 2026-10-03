---
{
  "base_kind": "phase",
  "id": "rec-f2497e16-4c1b-4b0c-b8ed-1277bebab99b",
  "identity": "unknown",
  "lifecycle_state": "planned",
  "payload": {
    "effort": "dashboard",
    "ordinal": 18,
    "title": "Quiet status tabs and a collapsed phase stepper"
  },
  "record_type": "project:phase",
  "recorded_at": "2026-10-03T09:49:57+00:00",
  "relationships": {},
  "revision": "sha256:ce794ce8f3dec4da6ed0c60b53bf280e2e193c7ae194c9befe2d3a58dce4bc60",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "quiet-header"
}
---

## Problem

Status tabs render as `1 Active 3`: a shortcut digit, a word, and a bold count. That row sits next to `phase 12/17` and task counts like `4/6`, so the digit you press and the tally you read look like task indexes. The phase stepper prints every phase as a green check plus its title, so a long history wraps into a stack of checks. Done phase headers in the task table repeat the check. The task table already folds older done phases into one row; the stepper lists every phase.

## Approach

Decision: quiet-header.

Status tabs show the word and a dim parenthetical tally, for example `Active (3)`. The selected word is the highlight. The tally stays dim on the selected tab. Keys `1`-`6`, left/right, and click still switch tabs. The leading digit leaves the label; the footer keeps `1-6`.

The stepper collapses done phases to a muted count (`16 done`), shows the current phase with its glyph, title, and done/total, and shows one next planned phase by name. Activating the done count expands the finished phase titles, the same fold as the task table's earlier-phases row. Done phase headers in the task table drop the check glyph and stay muted. Green stays on the in-progress phase.

`--once` prints the same tab line and the collapsed stepper.

## Exit criteria

1. A pilot test in `tests/test_dashboard_app.py` shows six tabs at 120 columns as `Active (3)` with no leading digit, a highlighted selected word, and a dim tally on every tab. The test fails before the change.
2. Keys `1`-`6`, left/right, and click still filter the table, and the footer still shows `1-6`. Covered by the existing status-tab tests, updated for the new labels.
3. An effort with more than two done phases shows `N done`, the current phase, and one next phase on the stepper, with no per-phase green check. Activating `N done` expands the finished titles. A pilot test in `tests/test_dashboard_app.py` covers this.
4. Done phase header rows in the task table have no check glyph. Covered by `tests/test_dashboard_tasks.py`.
5. `dashboard/bin/dashboard --once` prints the parenthetical tab line and the collapsed stepper. Covered by the `--once` test in `tests/test_dashboard_app.py`.
6. The full suite passes, including the tmux tests that currently expect number-key tab labels and a check on every stepper phase.
