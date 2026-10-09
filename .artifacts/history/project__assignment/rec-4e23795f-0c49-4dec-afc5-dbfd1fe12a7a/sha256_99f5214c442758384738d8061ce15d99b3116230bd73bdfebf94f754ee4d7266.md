---
{
  "base_kind": "instruction",
  "id": "rec-4e23795f-0c49-4dec-afc5-dbfd1fe12a7a",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "effort": "dashboard",
    "executor": "matrix-model-subagent",
    "work_item": "matrix-model"
  },
  "provenance": {
    "sources": [
      "matrix-model"
    ]
  },
  "record_type": "project:assignment",
  "recorded_at": "2026-10-09T22:59:48+00:00",
  "relationships": {},
  "revision": "sha256:99f5214c442758384738d8061ce15d99b3116230bd73bdfebf94f754ee4d7266",
  "subject": "matrix-model",
  "time": {
    "observed": "2026-10-09T22:59:48+00:00",
    "recorded": "2026-10-09T22:59:48+00:00"
  }
}
---

## Orientation

Repo path for code: `/home/andrewyin/se-workflow--evidence-matrix` (phase branch `phase/evidence-matrix`). Do not edit `.artifacts/`. Do not call `adaptive-artifacts`. Parent session writes the store on `/home/andrewyin/se-workflow`.

Territory: you own `RequirementRow` field extensions in `dashboard/model.py` (where `requirement_rows` already counts tasks / latest check) and new `dashboard/matrix.py` (`row_tone`, `glyph`, `blockers`, `release_line`, `matrix_columns`). Do not edit `phase_screen.py` UI, selector strip, or journal-view code. Parallel phase `journal-view` may also touch `dashboard/model.py` loaders in another chat — keep matrix field additions localized and do not rewrite unrelated loaders.

Kind: deliver. Follow `## Approach` in the work-item body. Cover with `-k matrix` model/requirement tests.

### Requirements (quoted)

R1: The Evidence tab of a structured phase shows one row per requirement id in the specification's order, with columns: id, requirement text, traced tasks as done/total, latest check-run for the requirement as result glyph, evidence kind, and age, assessment status (`unassessed` when none), and next stage (blank when verified).
R2: A row uses the error colour when its latest check-run failed or its status is `blocked`, the warning colour when its next stage is specify, design, or plan, or its confidence is low, the muted colour when unassessed, and the default colour when verified.
R3: Above the matrix a release line shows the latest release state (or `no release`), `n/m verified`, and the blockers: every requirement that is not verified, as `<id> <status>` or `<id> → <next>`, clipped to the pane width with a `+k more` tail.
R7: On the main screen, a selected structured phase shows after its `R n/m verified` tally one glyph per requirement in id order: verified `✓`, failed check or blocked `✗`, routed upstream `↑`, unassessed `◌`, otherwise `·`, coloured as in R2. Clicking the glyphs or pressing `e` opens the phase screen on Evidence.
R8: A phase with no specification has no Evidence tab and no strip, as before.

### Design Invariants

The matrix, the strip, the tally, and the requirement detail read the same `RequirementRow` values. No new CLI calls on the main snapshot path: the new fields come from records it already lists.

### Design Assumptions

`PhaseEvidence.release_ready` and the latest release state are available on the evidence model; the release line reads the state, not only the ready flag.

### Decisions

- evidence-matrix-rows: The Evidence tab is one row per requirement in id order (id, text, traced tasks done/total, latest check, status, next), with problem rows coloured; narrow panes drop text, then evidence kind and age
- evidence-release-line: A release line above the matrix shows release state, n/m verified, and the requirements that block ready
- evidence-strip: The main screen shows one glyph per requirement after the R tally for the selected structured phase; clicking it or e opens the Evidence tab
