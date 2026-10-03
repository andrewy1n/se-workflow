---
{
  "base_kind": "observation",
  "id": "rec-7eea9f9e-d9bc-4c70-abb9-73ea2f20bede",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "assignment": "activity-failures",
    "result": "pass",
    "revision": "b72a4501f216a791f1723d0d726c70d70286a5da",
    "verdict": "pass",
    "work_item": "activity-failures"
  },
  "provenance": {
    "sources": [
      "activity-failures"
    ]
  },
  "record_type": "project:execution-report",
  "recorded_at": "2026-10-02T01:25:22+00:00",
  "relationships": {},
  "revision": "sha256:51fc70e3ce775380105dbf7e4693adff3009acf33b86ceac0c8f62469e7a0fb4",
  "subject": "activity-failures",
  "time": {
    "observed": "2026-10-02T01:25:22+00:00",
    "recorded": "2026-10-02T01:25:22+00:00"
  }
}
---

subject: activity-failures
kind: deliver
result: pass
revision: b72a4501f216a791f1723d0d726c70d70286a5da
evidence: Failing-before run: `uv run --with textual --with pytest python -m pytest tests/test_dashboard_model.py tests/test_dashboard_app.py -q -k fail` gave 4 failed, 1 passed. The failures were AttributeError 'failed' on ActivityItem, no ✗ on the pilot line at widths 60 and 120, and no ✗ in the --once output. After the change, the same command gave 5 passed, 204 deselected. Full run: `uv run --with textual --with pytest --with pytest-xdist python -m pytest tests/test_dashboard_model.py tests/test_dashboard_app.py -q -n 4` gave 209 passed.
observations: ActivityItem gains `failed: bool = False`. It is the last field, so existing constructors still work. In _activity, a check-run is failed when payload result == "fail". An execution-report is failed when payload result or verdict == "fail". Assignments are never failed. activity_lines draws a failed item with the ✗ glyph in place of the kind glyph, and gives the glyph and summary the colors["error"] style. render_once uses activity_lines, so --once output shows ✗ too. New tests: test_activity_marks_failed_check_runs_and_failed_reports_only (model; checks one passing and one failing check-run, plus three reports: pass, result fail, verdict fail), test_failed_activity_line_uses_the_error_colour_and_a_cross[60/120] (pilot; compares span colours as truecolor with the error colour from palette_from), and test_once_marks_failed_activity_with_a_cross. TaskRow and the work-item listing are unchanged.
verdict: pass
claim: none
needs_human: false
