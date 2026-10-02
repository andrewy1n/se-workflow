import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from effort_rollup import effort_rollup


def row(efforts, turns, cost, calls, errors, retries):
    return {
        "turns": turns,
        "cost_usd": cost,
        "tools": {"tools": {}, "totals": {"calls": calls, "errors": errors, "retries": retries}},
        "records": {"total": len(efforts), "by_type": {}, "efforts": efforts, "tasks": [], "ambiguous": 0},
    }


def test_three_sessions_two_efforts_split_shared_and_exclusive_cost():
    rows = [
        row(["a"], 10, 1.0, 5, 1, 0),
        row(["a", "b"], 20, 2.0, 7, 2, 1),
        row(["b"], 30, None, 11, 0, 3),
    ]
    assert effort_rollup(rows) == {
        "a": {"sessions": 2, "exclusive_sessions": 1, "turns": 30, "tool_calls": 12,
              "errors": 3, "retries": 1, "cost_shared": 3.0, "cost_exclusive": 1.0},
        "b": {"sessions": 2, "exclusive_sessions": 1, "turns": 50, "tool_calls": 18,
              "errors": 2, "retries": 4, "cost_shared": 2.0, "cost_exclusive": 0.0},
    }


def test_rows_with_error_or_without_records_are_skipped():
    rows = [
        {"error": "boom", "records": {"efforts": ["a"]}},
        {"turns": 3},
        row([], 4, 1.0, 1, 0, 0),
    ]
    assert effort_rollup(rows) == {}


def test_effort_names_are_sorted():
    rows = [row(["z", "m"], 1, 0.0, 0, 0, 0)]
    assert list(effort_rollup(rows)) == ["m", "z"]
