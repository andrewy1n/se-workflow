---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-b639bcc1-8a6b-4104-accc-32efceb9b3bc",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "decisions": "phase-selection-scope,phase-selector-keys,phase-sections,quiet-header,selection-follow,parallel-phase-default,wave-strip,finished-effort-toggle,activity-merge,ux-phase-split",
    "effort": "dashboard",
    "phase": "phase-selector"
  },
  "record_type": "project:design",
  "recorded_at": "2026-10-05T07:34:47+00:00",
  "relationships": {},
  "revision": "sha256:cad8242306689221b3a732750c717b215ca52fe3b33fd47fb313d27cf758aa85",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "phase-selector",
  "time": {
    "as_of": "2026-10-05T07:34:47+00:00"
  }
}
---

## Architecture

Selection is UI state, not model state. `dashboard/model.py` keeps building the same `Snapshot`; a new pure module `dashboard/selection.py` takes an `EffortView` plus the user's selection and returns what to render. `DashboardApp` keeps a per-effort `PhaseSelection` next to its per-effort `TaskFilter`, so it survives effort switches and refreshes.

`default_phase(view)` resolves R1: among `in_progress` phases, the one whose tasks have the latest `ActivityItem.recorded_at` (activity subjects map to tasks, tasks to phases), ties to the lower ordinal; else the lowest-ordinal `planned` phase; else `None`, meaning All phases. `resolve(view, selection)` returns the selected subject: the pinned subject if it still exists, otherwise `default_phase(view)`. Picking a subject equal to `default_phase(view)` clears the pin (R7).

`scoped(view, subject)` returns a copy of the view whose `tasks` are only that phase's tasks, used for the table, status-tab counts, and phase progress. Needs you and Activity always read the unscoped view (R6). With `subject` `None`, the existing grouped path in `tasks.section_rows` runs unchanged (R5). With a subject, `fill_tasks` adds plain task rows with no indent and no section rows, so `activate` always opens a task (R4).

`PhaseStepper` becomes `PhaseSelector`. `selector_segments(view, selected, colors, width)` replaces `_stepper_segments`: done count (muted, excludes a selected done phase), the selected phase if done, every in-progress phase with `●` and its stage word, the next planned phase, then `All phases`; the selected segment is reverse-styled. Each segment carries Rich `meta` with its target (`phase:<subject>`, `all`, or `picker`), and `on_click` reads it (R2, R3). `stepper_open` and `toggle_stepper` go away.

A new `PhasePicker` modal screen holds an `Input` and an `OptionList` of All phases and every phase (`<ordinal> <glyph> <title> <done>/<total>`); typing filters by title and subject, Enter dismisses with the subject, Esc dismisses with nothing (R3).

`wave_strip(view, subject, width)` in `selection.py` groups the phase's tasks by `wave` and renders `w<n>` plus one `STATUS_GLYPH` per task; if the result exceeds `width`, each wave renders its least-finished glyph only (order running, waiting, ready, done). It renders on a new `#waves` line under the selector. `task_columns` drops `wave` (R9).

`merge_activity(items)` in `selection.py` folds runs of consecutive items with the same `kind`, `failed`, and summary-after-subject into one item whose subjects are joined; `activity_lines` formats a merged item as `<n> <summary>: a, b, …` or, for requirement assessments, `R1 R2 … <status> → <next>`, then clips (R10).

Finished efforts: `DashboardApp` holds `show_finished: bool = False`. `visible_efforts(snapshot, show_finished)` keeps live efforts, plus finished ones when shown or when `needs_you` is non-empty. The tab bar gets a trailing muted `+N finished` label when some are hidden. `f` toggles and rebuilds the tabs (R11).

`?` toggles Textual's key panel (`action_show_help_panel` / `action_hide_help_panel`); bindings for `[`, `]`, `P`, `f` are declared with descriptions so the panel lists them (R12). `p` uses the resolved selection when it is a phase, else the cursor row as today (R8). The plain `--once` renderer calls the same `resolve` with no pin and prints the selector line, wave strip, and scoped table (R14).

## Interfaces

- `PhaseSelection(pinned: str | None = None, all_phases: bool = False)`; `all_phases` pins the All phases stop.
- `default_phase(view: EffortView) -> str | None`
- `resolve(view: EffortView, selection: PhaseSelection) -> str | None` (`None` is All phases)
- `pick(view: EffortView, target: str | None) -> PhaseSelection` (clears the pin when `target` equals the default)
- `step(view: EffortView, selection: PhaseSelection, delta: int) -> PhaseSelection` (ordinal order, All phases last, stops at ends)
- `scoped(view: EffortView, subject: str | None) -> EffortView`
- `selector_segments(view, selected, colors, width) -> list[Text]`
- `wave_strip(view, subject, width) -> Text`
- `merge_activity(items: list[ActivityItem]) -> list[MergedActivity]`, with `MergedActivity(kind, subjects, summary, recorded_at, failed)`
- `visible_efforts(snapshot: Snapshot, show_finished: bool) -> tuple[list[EffortView], int]` (shown, hidden count)
- App bindings: `[` `select_phase(-1)`, `]` `select_phase(1)`, `P` `open_picker`, `f` `toggle_finished`, `?` `toggle_keys`.

## Decisions

phase-selection-scope, phase-selector-keys, phase-sections, quiet-header, selection-follow, parallel-phase-default, wave-strip, finished-effort-toggle, activity-merge, ux-phase-split.

## Invariants

`load_snapshot` output does not depend on any selection. Needs you and Activity content are identical for every selection. All phases renders the same rows as today's grouped table, minus the wave column. An effort with no phase records gets no selector, no wave strip, and its current flat table (R13). The status line segment is unchanged.

## Assumptions

Textual's key panel is available in the version `uv` resolves; if not, `?` pushes a small screen listing the active bindings instead. Activity items exist for running phases often enough to rank them; a phase with none ranks by ordinal.

## Tradeoffs

All phases shows no wave information once the column goes. Scoped counts mean the status tabs no longer show effort totals; the progress label keeps the effort's done/total so the whole-effort number stays visible. Merged activity lines lose per-item times; the line keeps the latest time.

## Risks

`estimate-view` edits the phase header and task title in `tasks.py` and `app.py`; starting before it lands would conflict, so this phase waits for it. Many tests assert today's stepper text, wave column, and grouped default; they need updating in the same change, which makes the diff wide. Rich `meta` on clickable segments must survive line wrapping; a test covers clicks on a wrapped second line.
