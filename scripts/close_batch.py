#!/usr/bin/env python3
"""Build the NDJSON `apply` batch that closes a work-item.

Reads a close-request JSON describing the work-item's active acceptances,
the judged result for each one, and the transition to apply; emits one
`project:check-run` create per judged criterion (linked `informed_by` both
its acceptance and the execution-report it came from, when there is one),
an optional `project:finding`, and the work-item transition, in that
order -- ready to feed straight into `adaptive-artifacts apply`.

The judgement itself (which result each criterion gets, and whether a
deferred close is legitimate) is made by whatever builds the close-request
-- this script does not second-guess it. What it does enforce: closing to
`done` while a criterion is unmet or was never checked requires a
`finding` in the same request, or the batch is refused outright rather
than silently written without one. A criterion with `result` `pass` and
`verdict` `fail`, `blocked`, or `unknown` is unmet. Omitting `verdict`
keeps the older meaning: `result` `pass` is met.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


class CloseRequestError(Exception):
    """Malformed close-request -- exit 1, distinct from a policy refusal."""


class CloseRefused(Exception):
    """Policy refusal -- exit 2, distinct from a malformed request."""


def _criterion_met(entry: dict[str, Any]) -> bool:
    """A pass result is not met when the evidence verdict says otherwise.

    Requests that omit `verdict` stay met on `result=pass`, so older
    close requests keep their meaning.
    """
    if entry.get("result") != "pass":
        return False
    verdict = entry.get("verdict")
    return verdict in (None, "", "pass")


def build_batch(request: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        subject = request["subject"]
        effort = request["effort"]
        work_item_id = request["work_item_id"]
        transition = request["transition"]
        acceptance_ids = list(request["acceptance_ids"])
        criteria = list(request.get("criteria", []))
    except KeyError as exc:
        raise CloseRequestError(f"missing field: {exc}") from exc

    execution_report_id = request.get("execution_report_id")
    finding = request.get("finding")

    for entry in criteria:
        criterion_id = entry.get("criterion_id")
        if criterion_id not in acceptance_ids:
            raise CloseRequestError(
                f"criteria entry {criterion_id!r} is not in acceptance_ids {acceptance_ids}"
            )

    passed_ids = {
        entry["criterion_id"] for entry in criteria if _criterion_met(entry)
    }
    unmet = [aid for aid in acceptance_ids if aid not in passed_ids]

    if transition == "done" and unmet and not finding:
        raise CloseRefused(
            "closing to done with unmet or unverified criterion(s) "
            f"{unmet} and no finding -- refusing. Either resolve those "
            "criteria first, or supply `finding` (claim, basis, "
            "invalidated_when, body) to close anyway."
        )

    ops: list[dict[str, Any]] = []
    for entry in criteria:
        try:
            payload = {
                "criterion_id": entry["criterion_id"],
                "revision": entry["revision"],
                "result": entry["result"],
                "effort": effort,
                "method": entry["method"],
                "signed_by": entry.get("signed_by", ""),
            }
        except KeyError as exc:
            raise CloseRequestError(f"criteria entry missing field: {exc}") from exc
        for field in ("verdict", "layer", "uncertainty"):
            if entry.get(field):
                payload[field] = entry[field]
        rels = [f"informed_by:{entry['criterion_id']}"]
        if execution_report_id:
            rels.append(f"informed_by:{execution_report_id}")
        ops.append(
            {
                "op": "create",
                "type": "project:check-run",
                "subject": subject,
                "payload": payload,
                "rel": rels,
            }
        )

    if finding:
        try:
            finding_payload = {
                "claim": finding["claim"],
                "basis": finding["basis"],
                "invalidated_when": finding["invalidated_when"],
                "effort": effort,
                # Hardcoded, not passed through: this finding exists to
                # surface a deferred/unmet criterion under handoff's Needs
                # Human role, which only fires on needs="human".
                "needs": "human",
            }
            finding_body = finding["body"]
        except KeyError as exc:
            raise CloseRequestError(f"finding missing field: {exc}") from exc
        ops.append(
            {
                "op": "create",
                "type": "project:finding",
                "subject": subject,
                "payload": finding_payload,
                "body": finding_body,
            }
        )

    ops.append(
        {
            "op": "update",
            "type": "project:work-item",
            "id": work_item_id,
            "transition": transition,
            "expected_revision": "@current",
        }
    )
    return ops


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _write(path: str, text: str) -> None:
    if path == "-":
        sys.stdout.write(text)
        return
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", default="-", help="close-request JSON path, or '-' for stdin (default)"
    )
    parser.add_argument(
        "--out", default="-", help="NDJSON output path, or '-' for stdout (default)"
    )
    args = parser.parse_args(argv)

    try:
        request = json.loads(_read(args.input))
    except json.JSONDecodeError as exc:
        print(f"close-request is not valid JSON: {exc}", file=sys.stderr)
        return 1

    try:
        ops = build_batch(request)
    except CloseRefused as exc:
        print(f"close refused: {exc}", file=sys.stderr)
        return 2
    except CloseRequestError as exc:
        print(f"close-request malformed: {exc}", file=sys.stderr)
        return 1

    _write(args.out, "\n".join(json.dumps(op) for op in ops) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
