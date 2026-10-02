---
name: analyze-sessions
description: Analyze past Claude Code sessions and propose fixes to the workflow, ranked by severity.
disable-model-invocation: true
---

# Analyze sessions

Read session metrics, find patterns, and propose fixes. Propose only. Edit nothing until the user picks a candidate.

The plugin root `<plugin>` is two directories above this file. The scripts live in `<plugin>/scripts`.

## Steps

1. Run both scripts. Create the temp directory first and write the report into it.

   ```
   TMP=$(mktemp -d)
   python3 <plugin>/scripts/session_report.py --records > "$TMP/report.jsonl"
   python3 <plugin>/scripts/session_aggregate.py "$TMP/report.jsonl" > "$TMP/aggregate.json"
   ```

   Done when `aggregate.json` parses and `sessions` is greater than 0.

2. Read `caveats` first. Open the output with one line on how far to trust per-effort and cost numbers, citing `ambiguous_share` and `sessions_without_cost`.
   Done when that line holds both values.

3. Find patterns across `tools`, `skills`, `efforts` and `outliers`.
   Pattern: two or more outlier sessions from `outliers.*` that share a project, tool or skill.
   Noise: a single session that shares none of those.
   The aggregate has no per-tool session ids. For a tool, read the rows of `report.jsonl` whose `tools.tools.<name>.errors` is greater than 0, most errors first.
   Outlier rows often show `efforts: []`. Look up efforts in the same `report.jsonl` rows.
   Done when every outlier session in `outliers.*` is in a pattern or marked as noise.

4. Map each pattern to one target using [targets.md](targets.md).
   When a pattern fits two targets, choose the one whose "Fix goes in" location the user controls most directly. Name it in the candidate.
   Done when every pattern has one target or is dropped.

5. Read one session transcript only when a candidate needs more evidence. Name the session and read bounded slices: at most two sessions, at most 200 transcript lines per slice. Keep only counts, tool names and line positions.
   Done when the evidence is a number or a position. Quote no transcript text and no record bodies.

6. Present candidates, most severe first. Severity: rank by how many outlier slots (across `outliers.errors`, `outliers.retries`, `outliers.cost`) the pattern covers, then by the size of its metric. Each candidate has:
   - the target
   - one aggregate field and its value
   - session references: `session_id`, file, project
   - the proposed edit, in one or two sentences

   Drop any candidate that lacks a metric or a session reference.
   Done when every listed candidate has all four parts.

7. Stop and ask the user to pick a candidate. Edit nothing until they answer.
