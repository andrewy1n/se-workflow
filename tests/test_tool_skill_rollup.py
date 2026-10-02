import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from tool_skill_rollup import tool_skill_rollup  # noqa: E402


def row(tools, skills):
    return {"session_id": "s", "skills": skills, "tools": {"tools": tools, "totals": {}}}


def t(calls, errors=0, retries=0):
    return {"calls": calls, "errors": errors, "retries": retries}


def fixture():
    return [
        row({"Bash": t(4, 1, 1), "Read": t(2)}, {"commit": 2, "plan": 1}),
        row({"Bash": t(6, 2, 0), "Edit": t(4, 0, 2), "Zero": t(0)}, {"commit": 1, "idle": 0}),
        {"session_id": "bad", "error": "cannot open"},
        row({"Read": t(2, 1, 1)}, {}),
    ]


def test_tools_sorted_by_calls_then_name_with_exact_counts():
    out = tool_skill_rollup(fixture())
    assert out["tools"] == [
        {"name": "Bash", "calls": 10, "errors": 3, "error_rate": 0.3, "retries": 1, "sessions": 2},
        {"name": "Edit", "calls": 4, "errors": 0, "error_rate": 0.0, "retries": 2, "sessions": 1},
        {"name": "Read", "calls": 4, "errors": 1, "error_rate": 0.25, "retries": 1, "sessions": 2},
    ]


def test_skills_sorted_by_invocations_with_session_counts():
    out = tool_skill_rollup(fixture())
    assert out["skills"] == [
        {"name": "commit", "invocations": 3, "sessions": 2},
        {"name": "plan", "invocations": 1, "sessions": 1},
    ]


def test_error_rate_rounds_to_four_places():
    out = tool_skill_rollup([row({"A": t(3, 1)}, {})])
    assert out["tools"][0]["error_rate"] == 0.3333


def test_failed_rows_and_empty_input_give_empty_lists():
    assert tool_skill_rollup([{"error": "x"}]) == {"tools": [], "skills": []}
    assert tool_skill_rollup([]) == {"tools": [], "skills": []}
