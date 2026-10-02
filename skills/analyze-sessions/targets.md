# Fix targets

Read this at the mapping step. Map each metric pattern to one target. Output is proposals only.

## se-workflow skills

Fix goes in `skills/*/SKILL.md`.

- Skill steps that cause retries (`outliers.retries`, `tools[].retries`) -> reword or split the step in that SKILL.md, because the retry sessions show where the step is unclear.
- Skill invoked often but sessions end without records (`skills[].invocations`, `skills[].sessions`, `efforts.*.exclusive_sessions`) -> shorten or re-aim the skill description and first step, because users start it and drop it.
- Skill never invoked (`skills[].name`, `skills[].sessions`, `sessions`) -> fix its trigger description or remove it, because no session reaches it.
- Not for: tool errors that repeat across all skills.

## artifact contract

Fix goes in `contract/project-design.json` and the record shapes.

- High share of records tied to several efforts (`caveats.ambiguous_share`, `caveats.ambiguous_records`) -> add a session id or effort field to the record shape, because the join cannot pick one effort.
- Records that cannot attach to any session (`caveats.attached_records`, `caveats.bad_input_lines`) -> fix the record shape so it carries a join key, because the reader drops or miscounts them.
- Effort with high shared cost and few exclusive sessions (`efforts.*.cost_shared`, `efforts.*.cost_exclusive`, `efforts.*.exclusive_sessions`) -> split the effort subject in the contract, because sessions overlap and cost is double counted.
- Not for: a single noisy session in `outliers.cost`.

## CLAUDE.md and steering files

Fix goes in `CLAUDE.md` and steering files. Prefer a pointer to one source over an inline rule.

- Same avoidable tool error across many sessions (`tools[].error_rate`, `tools[].sessions`) -> add one line or a pointer for that tool, because the mistake repeats and a rule prevents it.
- Efforts with high cost and many turns that show no drop after a rule exists (`efforts.*.cost_exclusive`, `efforts.*.turns`) -> cut or merge that rule, because large steering that changes nothing costs context.
- Retries clustered in a project (`outliers.retries`, `outliers.errors`) -> add a project-level pointer to the right doc, because the sessions lack a fact they need.
- Not for: errors a script can catch; use an automated check.

## automated checks

Fix goes in a lint, test, hook or CI job.

- Tool with high error rate on one pattern (`tools[].error_rate`, `tools[].errors`, `tools[].calls`) -> add a hook or lint that rejects that pattern, because a machine can catch it before the call.
- Same mistake retried in many sessions (`tools[].retries`, `tools[].sessions`) -> add a test or CI step for it, because the failure is mechanical.
- Effort with many errors per tool call (`efforts.*.errors`, `efforts.*.tool_calls`) -> add a validation step to that effort's flow, because errors surface late.
- Not for: judgment calls that need a human or a skill rewrite.
