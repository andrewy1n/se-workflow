import json
import sys

from effort_rollup import effort_rollup
from session_outliers import outliers
from tool_skill_rollup import tool_skill_rollup

NOTE = (
    "Per-session record counts are approximate: a session counts toward an effort "
    "when a record of that effort falls inside its window, so cost can double-count across efforts."
)


COST_NOTE = (
    "Cost is a lower bound: sessions without a cost-state line in the transcript have no cost data."
)


def read_rows(lines):
    rows, bad = [], 0
    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if isinstance(obj, dict):
            rows.append(obj)
        else:
            bad += 1
    return rows, bad


def caveats(rows, bad):
    attached = ambiguous = with_cost = 0
    for r in rows:
        if "error" not in r and r.get("cost_usd") is not None:
            with_cost += 1
        rec = r.get("records")
        if isinstance(rec, dict):
            attached += rec.get("total") or 0
            ambiguous += rec.get("ambiguous") or 0
    return {
        "attached_records": attached,
        "ambiguous_records": ambiguous,
        "ambiguous_share": round(ambiguous / attached, 4) if attached else 0.0,
        "note": NOTE,
        "sessions_with_cost": with_cost,
        "sessions_without_cost": sum("error" not in r for r in rows) - with_cost,
        "cost_note": COST_NOTE,
        "bad_input_lines": bad,
    }


def aggregate(lines):
    rows, bad = read_rows(lines)
    ts = tool_skill_rollup(rows)
    return {
        "sessions": len(rows),
        "efforts": effort_rollup(rows),
        "tools": ts["tools"],
        "skills": ts["skills"],
        "outliers": outliers(rows),
        "caveats": caveats(rows, bad),
    }


def main(argv):
    if len(argv) > 1:
        with open(argv[1]) as f:
            doc = aggregate(f)
    else:
        doc = aggregate(sys.stdin)
    print(json.dumps(doc, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
