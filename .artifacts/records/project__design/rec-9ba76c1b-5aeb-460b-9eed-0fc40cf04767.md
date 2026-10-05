---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-9ba76c1b-5aeb-460b-9eed-0fc40cf04767",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "decisions": "evidence-matrix-rows,evidence-release-line,evidence-strip",
    "effort": "dashboard",
    "phase": "evidence-matrix"
  },
  "record_type": "project:design",
  "recorded_at": "2026-10-05T07:46:39+00:00",
  "relationships": {},
  "revision": "sha256:5a40a091995d69afd72ef31b7f2aec5b9b51fbf4be3db6b592d3df52deac3006",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "evidence-matrix",
  "time": {
    "as_of": "2026-10-05T07:46:39+00:00"
  }
}
---

## Architecture

`model.RequirementRow` gains the fields the matrix needs: `tasks_done`, `confidence`, and the latest check's `evidence_kind` and `recorded_at` (the `CheckRun` already carries result). `requirement_rows` computes them where it already counts traced tasks and picks the latest check, so the main snapshot and phase screen share one source (R1, invariants).

A new pure module `dashboard/matrix.py` holds `row_tone(row)` (R2), `glyph(row)` (R7), `blockers(evidence)` (R3), `matrix_columns(width)` (R5), and `release_line(evidence, width)`. The phase screen's `EvidencePane` (from spec-view) replaces its requirement `OptionList` with a `DataTable` in row cursor mode built from these, keyed by requirement id, so Enter opens `RequirementDetailScreen` and the cursor survives reloads by key (R4). The integration panel stays below (R6).

On the main screen, `selection.selector_segments` appends the strip after the tally for the selected structured phase. The strip segment carries click `meta` `evidence:<phase>`, which `PhaseSelector.on_click` routes to `action_open_phase("evidence")` (R7).

## Interfaces

- `RequirementRow` gains `tasks_done: int`, `confidence: str`, `check_kind: str`, `check_at: datetime | None`
- `row_tone(row: RequirementRow) -> str` (`error` | `warning` | `muted` | `default`)
- `glyph(row: RequirementRow) -> str`
- `blockers(evidence: PhaseEvidence) -> list[str]`
- `release_line(evidence: PhaseEvidence, width: int) -> Text`
- `matrix_columns(width: int) -> list[str]`
- selector click meta `evidence:<phase>`

## Decisions

evidence-matrix-rows, evidence-release-line, evidence-strip.

## Invariants

The matrix, the strip, the tally, and the requirement detail read the same `RequirementRow` values. No new CLI calls on the main snapshot path: the new fields come from records it already lists.

## Assumptions

`PhaseEvidence.release_ready` and the latest release state are available on the evidence model; the release line reads the state, not only the ready flag.

## Tradeoffs

Id order keeps rows stable while evidence arrives, at the cost of problems not floating to the top; colour and the release line's blockers carry that instead. Dropping the text column in narrow panes makes rows depend on knowing the ids; Enter shows the text.

## Risks

A long specification (15+ requirements) makes the strip wide; it wraps with the selector line, and a test covers 20 requirements at 60 columns. Requirement rows with no check-run need a stable empty cell so columns do not shift between refreshes.
