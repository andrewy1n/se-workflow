---
name: feedback
description: >-
  Records a runtime or user signal and routes it back to intent.
  Use when a deployed or released phase produces an error, regression,
  alert, or report. Does not implement the fix.
---

# Feedback

Requires `artifact-runtime` and a live se-workflow store. Follow
[lifecycle.md](../lifecycle.md). Parent session writes records. This
skill is the intake extension point. It is not a monitoring product.

## Rules

- `kind` is `error` | `performance` | `security` | `user_report` |
  `anomaly` | `edge_case`.
- One signal, one record. Do not bundle an unrelated alert into it.
- The record does not fix the product. Next is `engage`: a new phase
  on the effort that owns the behavior, or a new effort when no live
  goal covers it. That phase starts at specify unless depth is
  `trivial`.

## Steps

1. Write the signal. `effort` is the owning effort when one exists.
   Omit `effort` when the signal is not yet tied to one.

```bash
adaptive-artifacts create --type project:feedback \
  --subject "<signal-slug>" \
  --payload '{"source":"<monitor, log, or user>","kind":"error","summary":"<what happened>","effort":"<effort-slug>"}' \
  --body "## Signal

<what was observed, including when and where>

## Suggested intake

<the specification question this should become>"
```

2. Set `stage` to `feedback` on the phase position when the signal
   belongs to a phase that is still open. Then hand off to `engage`
   with the summary as the ask. Do not skip specify for a
   production failure unless the user calls the response trivial.

## Do not

- Open a repair from a stack trace before specify has named the
  required behavior
- Treat this record as a check-run
- Page a human automatically; the parent shows the signal and lets
  `engage` classify it
