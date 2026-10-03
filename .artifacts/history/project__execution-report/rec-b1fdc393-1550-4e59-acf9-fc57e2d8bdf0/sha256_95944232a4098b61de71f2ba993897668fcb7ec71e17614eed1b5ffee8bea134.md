---
{
  "base_kind": "observation",
  "id": "rec-b1fdc393-1550-4e59-acf9-fc57e2d8bdf0",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "assignment": "verify-needs-you-data-phase",
    "result": "pass",
    "revision": "e4484c4",
    "verdict": "pass",
    "work_item": "verify-needs-you-data-phase"
  },
  "provenance": {
    "sources": [
      "verify-needs-you-data-phase"
    ]
  },
  "record_type": "project:execution-report",
  "recorded_at": "2026-10-02T00:07:13+00:00",
  "relationships": {},
  "revision": "sha256:95944232a4098b61de71f2ba993897668fcb7ec71e17614eed1b5ffee8bea134",
  "subject": "verify-needs-you-data-phase",
  "time": {
    "observed": "2026-10-02T00:07:13+00:00",
    "recorded": "2026-10-02T00:07:13+00:00"
  }
}
---

subject: verify-needs-you-data-phase
kind: repair
result: pass
revision: e4484c4
evidence: uv run --with textual --with pytest --with pytest-xdist python -m pytest tests -q -n 4 -m 'not tmux' -> 297 passed in 42.33s; uv run --with textual --with pytest python -m pytest tests -q -m tmux -> 10 passed, 297 deselected in 45.30s. Mutation checks: reverting 3ca5175's dashboard_model.py change fails the extended test (1 failed, 11.38s); reverting 7fbde9c's dashboard_app.py change also fails it (1 failed, 11.41s); both reverts restored.
observations: After 7fbde9c, tests/test_tmux_integration.py only remapped tab keys (6->5, 5->4). It did not assert the tab labels, the panel count, or the unsigned line. I extended the existing popup focus/resize test, so no new tmux server starts. It is renamed test_prefix_a_popup_walks_six_tabs_counts_needs_you_reads_unsigned_checks_regains_focus_and_narrows_on_resize. It seeds a manual acceptance on fx-ready ("pages render on mobile") and an unsigned manual check-run with a different subject (fx-check), through h.create_generic_record. On open it asserts six tab labels with counts: Active 2, Running 1, Ready 1, Waiting 0, Done 0, All 2. It asserts the panel title "Needs you 2" and that "Needs you" appears exactly once on screen, so there is no Needs you tab. It asserts the line "unsigned pages render on mobile pass fx-ready" and that "rec-" is absent from the screen. It then walks keys 2, 3, 5, 6 and 4 and checks each tab's contents, then keeps the existing focus and resize steps. No product code changed.
root_cause: n/a
verdict: pass
claim: none
needs_human: false
