---
{
  "base_kind": "task",
  "id": "rec-0f99fdee-de15-4595-a563-0bf0ba9c3ace",
  "identity": "unknown",
  "lifecycle_state": "done",
  "payload": {
    "assignee": "matrix-model-subagent",
    "decisions": "evidence-matrix-rows,evidence-release-line,evidence-strip",
    "effort": "dashboard",
    "estimate_minutes": 30,
    "executor": "subagent",
    "kind": "deliver",
    "phase": "evidence-matrix",
    "requirements": "R1,R2,R3,R7,R8",
    "size": "M",
    "title": "RequirementRow fields and matrix pure helpers"
  },
  "record_type": "project:work-item",
  "recorded_at": "2026-10-09T23:02:23+00:00",
  "relationships": {},
  "revision": "sha256:4baa033e478f89bf89afa8920c03baa5f3d24b3909a80b9b5ccbf967ac675e90",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "matrix-model"
}
---

## Description

Extend RequirementRow with matrix fields and add dashboard/matrix.py helpers for tone, glyph, blockers, release line, and columns.

## Approach

1. Add tasks_done, confidence, check_kind, check_at on RequirementRow where requirement_rows already counts tasks and picks the latest check.
2. Add row_tone, glyph, blockers, release_line, matrix_columns in dashboard/matrix.py per the design.
3. Cover with -k matrix model and requirement tests. Do not edit phase_screen UI.
