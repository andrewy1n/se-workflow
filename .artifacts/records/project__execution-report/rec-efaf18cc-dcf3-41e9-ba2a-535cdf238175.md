---
{
  "base_kind": "observation",
  "id": "rec-efaf18cc-dcf3-41e9-ba2a-535cdf238175",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "assignment": "verify-table-state-phase",
    "result": "pass",
    "revision": "3d740d2b7c02175520ca2f03e713c70c450c6603",
    "verdict": "pass",
    "work_item": "verify-table-state-phase"
  },
  "provenance": {
    "sources": [
      "verify-table-state-phase"
    ]
  },
  "record_type": "project:execution-report",
  "recorded_at": "2026-10-01T23:28:24+00:00",
  "relationships": {},
  "revision": "sha256:91402df289272197eefec05c3d11d02e541a4d9ef1ba49de2fd148478cb3ee18",
  "subject": "verify-table-state-phase",
  "time": {
    "observed": "2026-10-01T23:28:24+00:00",
    "recorded": "2026-10-01T23:28:24+00:00"
  }
}
---

subject: verify-table-state-phase
kind: repair
result: pass
revision: 3d740d2b7c02175520ca2f03e713c70c450c6603
evidence: New test tests/test_tmux_integration.py::test_prefix_a_popup_regains_table_focus_after_an_empty_tab_and_narrows_its_columns_on_resize ran alone 5 times on HEAD: 5/5 passed, about 4.0s each. Full suite: `uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux'` gave 295 passed in 42.75s. `uv run --with textual --with pytest python -m pytest tests -q -m tmux` gave 10 passed in 42.89s. Mutation checks (dashboard_app.py restored afterwards): code before both fixes (5b6f983) failed at the Enter-opens-second-row step, 1/1 run. Code with only the focus fix (1aeb305) failed at the narrow-columns step in 4 of 5 runs and passed in 1.
observations: The test opens the prefix-A popup at 96 cols, where the wide columns show "assignee". It then presses 5 to reach the empty Needs-you tab ("No tasks match"), presses 1 to return, presses Down and Enter, and gets the fx-ready detail. Esc returns to the table. The test then narrows the client pty to 80 cols with TIOCSWINSZ. tmux clamps the popup to the client, so the inner width drops below WIDE=90. The narrow column set (no "assignee") appears in about 0.4s, well before the next poll or the 30s redraw, so no reload is involved. Popup sizes are fixed by display-popup, so resize-pane/resize-window would not reach the popup. Resizing the client is the way to narrow it. The test adds no product code and no store writes. Only tests/test_tmux_integration.py changed (+32 lines, adds fcntl/struct/termios imports).
root_cause: n/a
verdict: pass
claim: The old resize defect is a race: without b104980 the stale width sometimes wins, so the tmux test catches it in about 4 of 5 runs, not every run. The unit test from b104980 is the deterministic guard.
needs_human: false
blocker:
