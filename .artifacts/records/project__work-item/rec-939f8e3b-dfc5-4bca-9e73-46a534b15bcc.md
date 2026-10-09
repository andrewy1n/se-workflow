---
{
  "base_kind": "task",
  "id": "rec-939f8e3b-dfc5-4bca-9e73-46a534b15bcc",
  "identity": "unknown",
  "lifecycle_state": "planned",
  "payload": {
    "assignee": "",
    "decisions": "journal-types,journal-order,kind-journal-panel",
    "effort": "dashboard",
    "estimate_minutes": 35,
    "executor": "subagent",
    "kind": "deliver",
    "phase": "journal-view",
    "requirements": "R2,R3,R4,R7,R9",
    "size": "M",
    "title": "Journal load, scope, open-first order, kind panel data"
  },
  "record_type": "project:work-item",
  "recorded_at": "2026-10-09T20:50:48+00:00",
  "relationships": {},
  "revision": "sha256:21f22956ca06ce386933ef3b9b26777df892f745ae1f38540a6db7a7b16fea08",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "journal-model"
}
---

## Description

Add load_journal, journal_scope, ordered, and snapshot kind/journal_open for repair and evaluate efforts.

## Approach

1. Add dashboard/journal.py model functions listing the five types with --full; missing types become empty (R9).
2. Map task-scoped subjects to phases; build JournalItem text and open flags per R2-R4 using Needs you predicates.
3. Attach EffortView.kind and journal_open only for repair/evaluate (R7).
4. Cover with -k journal model tests. Do not edit screens.
