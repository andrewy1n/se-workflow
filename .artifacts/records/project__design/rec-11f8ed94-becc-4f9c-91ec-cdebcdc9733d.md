---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-11f8ed94-becc-4f9c-91ec-cdebcdc9733d",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "decisions": "phase-screen-tabs,spec-full-text,decision-log-scope,pager-temp-file,simple-phase-spec-tab",
    "effort": "dashboard",
    "phase": "spec-view"
  },
  "record_type": "project:design",
  "recorded_at": "2026-10-05T07:45:19+00:00",
  "relationships": {},
  "revision": "sha256:df55ef5cc6009f0ed0e1f18acd8b421d181d9aeeb5a349a079da8684f17a810f",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "spec-view",
  "time": {
    "as_of": "2026-10-05T07:45:19+00:00"
  }
}
---

## Architecture

A new `dashboard/phase_screen.py` holds `PhaseScreen(target, effort, phase, tab)`, replacing `PhaseDetailScreen` in `app.py`. It composes a Textual `TabbedContent` with one `TabPane` per tab; tabs not in `tabs_for(detail)` are removed before mount (R1). Each pane is its own widget class (`OverviewPane`, `SpecPane`, `DesignPane`, `DecisionsPane`, `EvidencePane`, `TasksPane`) with a `show(detail, colors, width)` method, so reloads update in place and keep scroll and cursor (R13). The existing stage strip, chips, requirement list, and task list code moves from `app.py` into these panes unchanged (R3, R8, R9).

`model.load_phase_detail` grows to return the specification body, design body, phase constraints, and a `DecisionLog`. The specification and design come from one `list --where payload.phase=<phase> --full` each. `load_decision_log(target, effort, scope, history)` lists decisions for the effort (active, plus superseded when `history`), groups them by `payload.phase` in phase ordinal order, and attaches each superseded record to its successor through the supersede link (R7). It is loaded lazily when the Decisions tab first shows or a toggle changes.

`SpecPane` splits the specification body: the `## Requirements` section becomes an `OptionList` of `R<n>` rows (selected opens `RequirementDetailScreen`, R4), and every other section renders through `Markdown`. For a simple phase it renders the phase body and constraints instead (R5). `DesignPane` is one `Markdown` (R6).

`DashboardApp.action_open_phase(tab)` resolves the phase from the selection (or the cursor row on All phases) and pushes `PhaseScreen` at `tab`; `p`, `s`, `e` bind to it with `overview`, `spec`, `evidence` (R2). On the phase screen `[` and `]` replace the screen with the neighbouring phase at the same tab (R10). Child screens are pushed on top, so Esc pops back to the same `PhaseScreen` instance and its state (R12).

`o` calls `pager_text(tab)` on the active pane, writes it to `tempfile.NamedTemporaryFile(suffix=".md", delete=False)`, then runs the pager inside `App.suspend()`, and unlinks the file in a `finally` (R11). `pager_command()` returns `["glow", "-p", path]`, else `shlex.split($PAGER) + [path]`, else `["less", "-R", path]`.

## Interfaces

- `PhaseScreen(target, effort: str, phase: str, tab: str = "overview")`
- `TABS = ("overview", "spec", "design", "decisions", "evidence", "tasks")`; `tabs_for(detail: PhaseDetail) -> tuple[str, ...]`
- `PhaseDetail` gains `spec_body: str`, `design_body: str`, `structured: bool`
- `DecisionEntry(subject, phase, choice, alternatives, rationale, counter, superseded: tuple[DecisionEntry, ...])`
- `DecisionLog(groups: tuple[tuple[str, tuple[DecisionEntry, ...]], ...])`
- `load_decision_log(target, effort: str, phase: str | None, history: bool) -> DecisionLog` (`phase` `None` is the whole effort)
- Pane protocol: `show(detail, colors, width)`, `pager_text() -> str`
- `pager_command(path: str) -> list[str]`
- Keys on `PhaseScreen`: `left`/`right`, `p` `s` `d` `e` `t`, `[` `]`, `a` and `h` on Decisions, `o`, `escape`

## Decisions

phase-screen-tabs, spec-full-text, decision-log-scope, pager-temp-file, simple-phase-spec-tab.

## Invariants

`PhaseScreen` reads only; the temp file is created outside the store and always removed. A missing specification or design type in the contract degrades to the simple tab set, not an error. The requirement detail and task detail screens are reused unchanged.

## Assumptions

Textual `TabbedContent` supports removing panes before mount and switching with `left`/`right` when the tab bar has focus; the panes bind `left`/`right` explicitly so it works from content focus too. `App.suspend()` is available in the resolved Textual version.

## Tradeoffs

A simple phase shows its body on the Spec tab, not on Overview, so Overview is thinner for simple phases. Showing full Markdown in a 40% pane wraps heavily; `o` is the escape hatch. Lazy decision-log loading costs one extra CLI call when the tab opens.

## Risks

`p`, `s`, `e`, and `d` on the main screen and on the phase screen must not shadow each other or `c`, `r`, `g`; a binding test lists both screens' keys. Existing phase detail tests assert its panel layout and must move to the tab layout in the same change. Long specifications may make the `R<n>` list and Markdown sections scroll as two regions; the pane uses one scroll container for both.
