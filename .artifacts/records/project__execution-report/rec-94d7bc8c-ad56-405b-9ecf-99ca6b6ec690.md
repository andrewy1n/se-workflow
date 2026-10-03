---
{
  "base_kind": "observation",
  "id": "rec-94d7bc8c-ad56-405b-9ecf-99ca6b6ec690",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "assignment": "needs-you-list",
    "result": "pass",
    "revision": "2066784",
    "verdict": "pass",
    "work_item": "needs-you-list"
  },
  "provenance": {
    "sources": [
      "needs-you-list"
    ]
  },
  "record_type": "project:execution-report",
  "recorded_at": "2026-10-02T00:48:18+00:00",
  "relationships": {},
  "revision": "sha256:cb2a260d9e5a2c2e95a4a87389381923a2382ae715692f9bea011ef7c9990053",
  "subject": "needs-you-list",
  "time": {
    "observed": "2026-10-02T00:48:18+00:00",
    "recorded": "2026-10-02T00:48:18+00:00"
  }
}
---

subject: needs-you-list
kind: deliver
result: pass
revision: 2066784
evidence: Failing-before run: the new pilot tests ran against the old scripts/dashboard_app.py (stashed), with `uv run --with textual --with pytest --with pytest-xdist python -m pytest tests/test_dashboard_app.py -q -k "needs_you or footer" -n 4`. Result: 14 failed, 4 passed. After the change: `uv run --with textual --with pytest python -m pytest tests/test_dashboard_app.py -q -k needs_you` gives 15 passed. The whole of tests/test_dashboard_app.py (-n 4) gives 164 passed. The tmux tests (`uv run -q --with textual --with pytest python -m pytest tests -q -m tmux -rf`, serial) give 10 passed.
observations: The `#needs-you` Static is now a NeedsList, which is an OptionList subclass. It keeps the "Needs you N" border title and still hides when there are no items. The highlight only shows when the list has focus, so the unfocused panel looks as before. It keeps the highlighted item across reloads. The same panel id is used, so nothing in the tmux tests changed. `n` focuses the list (app binding `focus_needs`, footer label "needs"). Arrows and j/k move. `esc` returns to the task table. `enter` or a click opens TaskDetailScreen when the item has a task_id. Otherwise it opens the new read-only NeedsYouDetailScreen. That screen has a bar, a warning banner, a kind label and the record type, the full text as Markdown (panel titled Question, Claim or Check), and the body as Markdown. It has esc back, c copy and r refresh. It updates from each dashboard snapshot through DashboardApp.apply, so it follows store changes and `r`. When the item resolves it shows "No longer needs you". check_action blocks dashboard keys on the new screen, including n. `c` copies the highlighted item's subject on the list and the shown subject on the detail screen. A DETAIL_SCREENS tuple replaces the repeated isinstance tuples. README key table: added `n`, enter on a Needs you item (with the detail screen), and updated `c`. New tests: n focus, arrows and esc; enter on a linked item; enter on a question (full untruncated text and body, esc back to the list); c on the list and the detail screen; the detail follows a store update and blocks tab, n, p, / and 1. I updated the existing panel tests to read the option prompts.
verdict: pass
claim: To fit "n needs" in the footer at 60 columns, the enter "open" hint is now hidden from the footer (show=False on the app and TaskTable enter bindings). Enter still works, and the README still documents it. The footer test now expects copy, filter, needs, phase, quit, status, switch. Revert this if "open" must stay visible; then another hint has to go instead. Also, the model groups continuity questions by subject == effort, so every question's subject is the effort name, and `c` on a question copies the effort name.
needs_human: false
