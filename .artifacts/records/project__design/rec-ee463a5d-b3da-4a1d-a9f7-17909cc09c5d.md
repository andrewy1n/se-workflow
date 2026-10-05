---
{
  "base_kind": "claim",
  "epistemic_status": "asserted",
  "id": "rec-ee463a5d-b3da-4a1d-a9f7-17909cc09c5d",
  "identity": "unknown",
  "lifecycle_state": "active",
  "payload": {
    "decisions": "estimate-titles",
    "effort": "dashboard",
    "phase": "estimate-view"
  },
  "record_type": "project:design",
  "recorded_at": "2026-10-05T05:31:33+00:00",
  "relationships": {},
  "revision": "sha256:2ad9ff3bc597a0926b1567581b13f75694a75349800d010f35b906cdeb0292ca",
  "stewardship": {
    "steward": "agent"
  },
  "subject": "estimate-view",
  "time": {
    "as_of": "2026-10-05T05:31:33+00:00"
  }
}
---

## Architecture

`dashboard/model.py` reads `size` and `estimate_minutes` from each work-item payload and the `Size:` line from each phase body. The phase list uses `--full` so the body is in the snapshot. It computes elapsed minutes and the unset count per phase. `dashboard/tasks.py` appends the sitting phrase, elapsed minutes, and unset count to the phase header, and the size, minutes, and executor to the task title. `dashboard/task_detail.py` adds the chips. No contract change.

This phase starts after `run-facts` and `evidence-view` are on main.

## Interfaces

- `sitting_phrase(body: str) -> str`. Returns `one sitting`, `more than one`, or `""`. `Size: more than one sitting` returns `more than one`.
- `phase_elapsed(tasks) -> tuple[int | None, int]`. The int is elapsed minutes, or none when no task has an estimate. The second int is how many counted tasks lack `estimate_minutes`.
- Wave rule: group counted tasks by derived wave. A task with no wave is its own group. An inline group sums `estimate_minutes`, skipping blanks. A subagent group takes the max, skipping blanks. A missing or empty executor is subagent. Phase elapsed minutes are those group figures added in wave order, skipping a group with no estimate.
- `PhaseRow.sitting: str = ""`, `PhaseRow.elapsed_minutes: int | None = None`, `PhaseRow.unset_estimates: int = 0`.
- `TaskRow.size: str = ""`, `TaskRow.estimate_minutes: int | None = None`, `TaskRow.executor: str`. `TaskDetail` gains the same three.
- Phase header, after `{done}/{total}`: ` · {sitting}` when sitting is set, then ` · {n}m` when elapsed is not none, then ` · {k} unset` when k is greater than zero and elapsed is not none. Then any later suffixes.
- Task title: clip the title, then a dim suffix of the set fields in order ` · {size}`, ` · {n}m`, ` · {executor}`, then the waits-on note.
- Chips, after assignee when assignee is set: the size, `{n}m`, and `executor {executor}`.

## Decisions

estimate-titles.

## Invariants

Header minutes are the wave rule, not the sum of every task. A missing estimate is omitted on the task and counted as unset on the phase. A missing size is omitted. A missing executor is `subagent`. Suffixes survive clipping. The dashboard stays read-only.

## Assumptions

`run-facts` has shipped `size` and `estimate_minutes`. Counted tasks are `planned`, `in_progress`, and `done`. The `Size:` line is the one `plan-phase` already writes. Work-items are listed with `--full`.

## Tradeoffs

Every task title gains an executor word, including tasks with no estimate. The suffix crowds a 60-column title, and the title is what gets cut. The unset count makes a partial total visible without showing a second, raw sum. Phase detail is unchanged, because the body already contains the sitting line and the header carries the elapsed minutes.

## Risks

`evidence-view` and this phase both edit `dashboard/model.py`, `dashboard/tasks.py`, and `dashboard/task_detail.py`. Starting before that branch is on main will conflict. If `run-facts` has not added the payload fields, every task shows only its executor. A reader can still mistake a partial `{n}m` for the finished phase if they skip the unset count.
