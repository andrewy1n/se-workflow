import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from session_outliers import outliers


def row(sid, errors=0, retries=0, cost=0.0, efforts=None, **extra):
    r = {
        "project": "p",
        "file": f"{sid}.jsonl",
        "session_id": sid,
        "branch": "main",
        "cost_usd": cost,
        "tools": {"tools": {}, "totals": {"calls": 9, "errors": errors, "retries": retries}},
        "records": {"total": 1, "by_type": {}, "efforts": efforts or [], "tasks": 0, "ambiguous": 0},
    }
    r.update(extra)
    return r


def test_ranks_each_metric_descending_with_ties_by_session_id():
    rows = [
        row("c", errors=2, retries=1, cost=0.5),
        row("a", errors=2, retries=3, cost=0.25),
        row("b", errors=5, retries=0, cost=1.0),
    ]
    out = outliers(rows)
    assert [e["session_id"] for e in out["errors"]] == ["b", "a", "c"]
    assert [e["session_id"] for e in out["retries"]] == ["a", "c"]
    assert [e["session_id"] for e in out["cost"]] == ["b", "c", "a"]


def test_entry_holds_references_and_value_only():
    out = outliers([row("a", errors=1, efforts=["x", "y"], branch="feat")])
    assert out["errors"] == [
        {"session_id": "a", "file": "a.jsonl", "project": "p", "branch": "feat",
         "efforts": ["x", "y"], "value": 1}
    ]


def test_top_limits_entries_and_fewer_sessions_yield_fewer_entries():
    rows = [row(str(i), errors=i + 1) for i in range(4)]
    assert len(outliers(rows, top=2)["errors"]) == 2
    assert len(outliers(rows[:1], top=5)["errors"]) == 1
    assert outliers([]) == {"errors": [], "retries": [], "cost": []}


def test_zero_values_and_error_rows_are_skipped():
    rows = [row("a"), {"project": "p", "file": "bad", "error": "boom"}, row("b", errors=1)]
    out = outliers(rows)
    assert [e["session_id"] for e in out["errors"]] == ["b"]
    assert out["cost"] == []


def test_null_cost_counts_as_zero_and_cost_rounds_to_four_places():
    out = outliers([row("a", cost=None), row("b", cost=0.123456)])
    assert [(e["session_id"], e["value"]) for e in out["cost"]] == [("b", 0.1235)]


def test_missing_records_gives_empty_efforts():
    r = row("a", errors=1)
    del r["records"]
    assert outliers([r])["errors"][0]["efforts"] == []
