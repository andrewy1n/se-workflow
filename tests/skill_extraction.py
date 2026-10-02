"""Extract `adaptive-artifacts` CLI invocations out of skill markdown and
check each against what the resolved contract actually permits.

Parses fenced bash blocks only. A new invocation starts at each line that
begins with `adaptive-artifacts <subcommand>`; everything up to the next such
line (or the end of the fence) belongs to it, so multi-line continuations and
heredoc bodies (e.g. `--records "$(cat <<'EOF' ... EOF)"`) stay attached to
the invocation that opened them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import helpers as h

_FENCE_RE = re.compile(r"```(?:bash)?\n(.*?)```", re.DOTALL)
_INVOCATION_START_RE = re.compile(r"(?m)^adaptive-artifacts\s+(\S+)")
_FLAG_RE = lambda flag: re.compile(rf"--{flag}\s+(\S+)")
_PAYLOAD_RE = re.compile(r"--payload\s+'(\{.*?\})'", re.DOTALL)
_HEREDOC_RE = re.compile(r"<<'?\"?EOF'?\"?\s*\n(.*?)\nEOF", re.DOTALL)


def skill_markdown_files(skills_root: Path) -> list[Path]:
    return sorted(skills_root.rglob("*.md"))


def extract_invocations(text: str) -> list[dict]:
    invocations = []
    for block in _FENCE_RE.findall(text):
        starts = [m.start() for m in _INVOCATION_START_RE.finditer(block)]
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(block)
            invocations.append(_parse_chunk(block[start:end]))
    return invocations


def _parse_chunk(chunk: str) -> dict:
    subcommand = _INVOCATION_START_RE.match(chunk).group(1)

    def flag(name: str) -> str | None:
        m = _FLAG_RE(name).search(chunk)
        return m.group(1).strip("\"'") if m else None

    payload = None
    pm = _PAYLOAD_RE.search(chunk)
    if pm:
        try:
            payload = json.loads(pm.group(1))
        except json.JSONDecodeError:
            payload = None

    records = None
    if "--records" in chunk:
        hm = _HEREDOC_RE.search(chunk)
        if hm:
            try:
                records = json.loads(hm.group(1))
            except json.JSONDecodeError:
                records = None

    return {
        "subcommand": subcommand,
        "type": flag("type"),
        "transition": flag("transition"),
        "bundle": flag("bundle"),
        "rels": re.findall(r"--rel\s+(\S+)", chunk),
        "payload": payload,
        "records": records,
        "raw": chunk.strip(),
    }


_TYPE_BEARING_SUBCOMMANDS = {"create", "update", "supersede", "get", "list", "correct", "contradict"}


def check_invocation(inv: dict, defs: dict[str, dict], bundles_by_id: dict[str, dict]) -> list[str]:
    """Return violation messages, or [] if this invocation is permitted by
    the contract. Deliberately does not check payload keys beyond required-
    field presence -- extra payload keys are not rejected by the runtime, so
    flagging them would not be a genuine contract violation."""
    violations: list[str] = []
    sub = inv["subcommand"]
    rtype = inv["type"]

    if sub in _TYPE_BEARING_SUBCOMMANDS and rtype:
        if rtype not in defs:
            violations.append(f"unknown record type {rtype!r}")
            return violations

    if sub == "update" and inv["transition"] and rtype and rtype in defs:
        record_def = defs[rtype]
        dest = inv["transition"]
        states = set(record_def["lifecycle"]["states"])
        reachable = {d for dests in h.transitions_graph(record_def).values() for d in dests}
        if dest == "superseded" and h.advertises_supersedes(record_def):
            violations.append(
                f"update --type {rtype} --transition superseded is rejected at runtime: "
                f"{rtype} advertises 'supersedes', so reaching 'superseded' requires the "
                "`supersede` subcommand, not a plain `update --transition`"
            )
        elif dest not in states:
            violations.append(
                f"update --type {rtype} --transition {dest!r}: not a declared lifecycle state"
            )
        elif dest not in reachable:
            violations.append(
                f"update --type {rtype} --transition {dest!r}: no declared transition edge reaches this state"
            )

    if sub == "supersede" and rtype and rtype in defs:
        if not h.advertises_supersedes(defs[rtype]):
            violations.append(
                f"supersede --type {rtype}: rejected outright -- {rtype} does not advertise a "
                "'supersedes' relationship"
            )

    if sub == "correct" and rtype and rtype in defs:
        if defs[rtype].get("correction") != "successor_record":
            violations.append(
                f"correct --type {rtype}: rejected -- correction is not 'successor_record' for this type"
            )

    if sub == "contradict" and rtype and rtype in defs:
        if defs[rtype].get("contradiction") != "separate_record":
            violations.append(
                f"contradict --type {rtype}: rejected -- contradiction is not 'separate_record' for this type"
            )

    if inv["rels"] and rtype and rtype in defs:
        allowed = set(defs[rtype].get("relationships", []))
        for rel in inv["rels"]:
            reltype = rel.split(":", 1)[0]
            if reltype not in allowed:
                violations.append(
                    f"--rel {reltype}:... on --type {rtype}: {reltype!r} not in declared "
                    f"relationships {sorted(allowed)}"
                )

    if sub == "capture" and inv["bundle"]:
        bundle_id = inv["bundle"]
        if bundle_id not in bundles_by_id:
            violations.append(f"capture --bundle {bundle_id}: unknown bundle")
        else:
            allowed_types = set(bundles_by_id[bundle_id].get("records", []))
            for part in inv["records"] or []:
                ptype = part.get("type")
                if ptype not in defs:
                    violations.append(f"capture --bundle {bundle_id}: part type {ptype!r} does not exist")
                elif ptype not in allowed_types:
                    violations.append(
                        f"capture --bundle {bundle_id}: part type {ptype!r} is not declared in "
                        f"this bundle's records {sorted(allowed_types)}"
                    )

    if sub == "create" and inv["payload"] and rtype and rtype in defs:
        # only `create` needs a complete payload up front -- `update`/`supersede`
        # merge onto an already-valid record, so a partial payload there is fine.
        required = set(defs[rtype].get("payload", [])) - {"subject"} - set(defs[rtype].get("optional_payload", []))
        missing = required - set(inv["payload"].keys())
        if missing:
            violations.append(
                f"--type {rtype} --payload is missing required field(s) {sorted(missing)}"
            )

    return violations


def check_skill_text(text: str, defs: dict[str, dict], bundles_by_id: dict[str, dict]) -> list[str]:
    """Return one message per violation found in `text`, prefixed with the
    offending invocation's first line."""
    messages = []
    for inv in extract_invocations(text):
        for violation in check_invocation(inv, defs, bundles_by_id):
            first_line = inv["raw"].splitlines()[0]
            messages.append(f"[{first_line}] {violation}")
    return messages
