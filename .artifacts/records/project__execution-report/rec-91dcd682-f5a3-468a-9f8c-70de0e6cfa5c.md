---
{
  "base_kind": "observation",
  "id": "rec-91dcd682-f5a3-468a-9f8c-70de0e6cfa5c",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "assignment": "tm-parse-events",
    "result": "pass",
    "revision": "dirty",
    "verdict": "pass",
    "work_item": "tm-parse-events"
  },
  "provenance": {
    "sources": [
      "tm-parse-events"
    ]
  },
  "record_type": "project:execution-report",
  "recorded_at": "2026-10-02T01:34:58+00:00",
  "relationships": {},
  "revision": "sha256:c8902f9177f085b421271451583ced9cd5b5449aa97c914ae86d9081cec8b391",
  "subject": "tm-parse-events",
  "time": {
    "observed": "2026-10-02T01:34:58+00:00",
    "recorded": "2026-10-02T01:34:58+00:00"
  }
}
---

subject: tm-parse-events
kind: deliver
result: pass
revision: dirty (base 865fc75; new files uncommitted: scripts/session_metrics.py, tests/test_session_metrics.py)
evidence: Ran `python3 -m pytest -q tests/test_session_metrics.py -k parse`. Result: 6 passed in 0.02s. The tests cover these cases: a fixture with one malformed line and one unknown event type yields all valid events with bad_lines == 1; non-object JSON counts as bad; blank lines are skipped and not counted; invalid UTF-8 is tolerated; the reader is a lazy generator (inspect.isgenerator, and bad_lines updates only as it is consumed); an empty file yields nothing. I did not run adaptive-artifacts and did not touch .artifacts/. The test file does no store access. I did not run it against a real transcript.
observations: API is read_events(path, stats=None) -> Iterator[dict], with ReadStats.bad_lines as the counter. The reader streams line by line, ignores unknown fields and event types, and decodes with errors="replace". It yields only dicts.
root_cause:
verdict: pass
metrics:
claim: The reader streams one JSONL file as events, counts bad lines (parse failures and non-objects), and does not fail on them.
needs_human: false
