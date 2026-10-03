---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-8aa9b9e5-9088-4e73-a8ec-facffa2d3833",
  "identity": "unknown",
  "lifecycle_state": "asserted",
  "payload": {
    "basis": "Streamed all 140 null transcripts: 0 cost-state lines and 0 cost-named keys. The 107 non-null sessions parse correctly.",
    "claim": "Null cost_usd on 140 of 247 sessions is a data gap: those transcripts have no cost-state line, so cost totals are a lower bound over 107 sessions.",
    "effort": "session-analysis",
    "invalidated_when": "Claude Code starts writing cost-state lines for more sessions, or a different cost field appears in transcripts.",
    "needs": "none"
  },
  "provenance": {
    "sources": [
      "Streamed all 140 null transcripts: 0 cost-state lines and 0 cost-named keys. The 107 non-null sessions parse correctly."
    ]
  },
  "record_type": "project:finding",
  "recorded_at": "2026-10-02T02:18:26+00:00",
  "relationships": {},
  "revision": "sha256:7e17cf721e7b5212e4b8924257cdfc7043d1675a3760638a23a9e39afe321f2d",
  "subject": "as-cost-null"
}
---

## Evidence

Subagent diagnosis over the 140 null transcripts found no cost-state line and no cost-named key. No code path drops cost data. I re-ran the 6 tests in tests/test_session_fields.py and they pass.

## Consequence

Cost totals in the aggregate cover only sessions with a cost-state line. The parent added sessions_with_cost, sessions_without_cost and a cost_note to the aggregate caveats so readers see the gap. A test covers it.

## Follow-up

None. Re-check if transcript format changes.
