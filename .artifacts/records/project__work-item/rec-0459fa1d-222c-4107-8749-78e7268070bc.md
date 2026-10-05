---
{
  "base_kind": "task",
  "id": "rec-0459fa1d-222c-4107-8749-78e7268070bc",
  "identity": "unknown",
  "lifecycle_state": "planned",
  "payload": {
    "assignee": "model",
    "decisions": "estimate-titles,task-agent-estimate",
    "effort": "dashboard",
    "estimate_minutes": 30,
    "executor": "subagent",
    "kind": "deliver",
    "phase": "estimate-view",
    "requirements": "R1,R2,R3,R4,R7",
    "size": "M",
    "title": "Load size and estimate minutes into the dashboard model"
  },
  "record_type": "project:work-item",
  "recorded_at": "2026-10-05T06:20:47+00:00",
  "relationships": {},
  "revision": "sha256:724a39e7f4f27eb0b0dbf5f9f57a1b8dcb10ce4e8ccd9bf739e8be80e5cc29ee",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "estimate-model"
}
---

## Description

Load `size`, `estimate_minutes`, and the phase `Size:` line into the dashboard model, and compute the wave-rule elapsed minutes. No rendering change.

## Approach

Read design `estimate-view`, Interfaces. Edit only `dashboard/model.py` and `tests/test_dashboard_model.py`. Do not edit `dashboard/tasks.py`, `dashboard/task_detail.py`, or `contract/`.

Write the tests first. Name them `test_estimate_view_sitting_phrase`, `test_estimate_view_wave_rule`, `test_estimate_view_unset_count`, `test_estimate_view_row_fields`, and `test_estimate_view_blank_executor`.

1. `sitting_phrase(body: str) -> str`. On the first line that contains `Size:`, look at the text after the colon. `more than one` returns `more than one`, including the line `Size: more than one sitting`. Otherwise `one sitting` returns `one sitting`. Any other body returns `""`. Check `more than one` before `one sitting`, because `more than one sitting` contains `one sitting`.
2. `phase_elapsed(tasks: list[TaskRow]) -> tuple[int | None, int]`. The tasks are already the counted ones (`planned`, `in_progress`, `done`). The second value is how many of them have `estimate_minutes is None`. Group by `wave`. A task whose `wave` is `None` is its own group, keyed by id, not merged with other wave-less tasks. A group is inline only when every member's `executor` is `inline`; otherwise it is subagent. An inline group sums `estimate_minutes`, skipping `None`. A subagent group takes the max, skipping `None`. `0` counts. A group with no estimate contributes nothing. Phase elapsed minutes are those group figures added together. When no group has an estimate, return `(None, unset_count)`.
3. Add defaulted fields so existing constructors keep working: `PhaseRow.sitting: str = ""`, `PhaseRow.elapsed_minutes: int | None = None`, `PhaseRow.unset_estimates: int = 0`, `TaskRow.size: str = ""`, `TaskRow.estimate_minutes: int | None = None`, `TaskRow.executor: str = "subagent"`, and the same three on `TaskDetail`.
4. Add `project:phase` to `FULL_TYPES` so the snapshot list includes the phase body. In `_phase_rows`, set `sitting` from `sitting_phrase` on that body, and set `elapsed_minutes` and `unset_estimates` from `phase_elapsed` on `TaskRow`s built for the counted members. In `_task_rows` and `load_task_detail`, read payload `size` (missing or `""` stays `""`), `estimate_minutes` (missing or JSON null stays `None`; `0` stays `0`; do not use `or`), and `executor` (missing or `""` becomes `subagent`).
5. The wave-rule test uses hand-built `TaskRow`s: an inline wave of 10 and 15, a subagent wave of 10 and 40, a blank in that subagent wave, and a `0`. Elapsed minutes are `10 + 15 + 40`, not the sum of every task. The unset test has two counted tasks with no estimate and one with 25, and a separate case where every estimate is missing. The row test passes record dicts through `_task_rows` and `_phase_rows` with a phase `body` of `Size: more than one sitting.` The blank test builds a `TaskDetail` through `load_task_detail` or the same payload reader for a work-item that omits both fields and asserts `executor == "subagent"`, `size == ""`, and `estimate_minutes is None`. One snapshot test creates a phase and work-items through the CLI, with that `Size:` line in the phase body and `size` plus `estimate_minutes` on a work-item, and reads them back from `load_snapshot`.
