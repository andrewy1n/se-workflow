import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from session_tools import tool_metrics  # noqa: E402


def use(tid, name, **inp):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tid, "name": name, "input": inp}]}}


def result(tid, is_error=False, text="SECRET"):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tid, "content": text, "is_error": is_error}]}}


def fixture():
    return [
        use("1", "Bash", cmd="make"),
        result("1", True),
        use("2", "Bash", cmd="make"),
        result("2", False),
        use("3", "Read", path="a"),
        result("3", True),
        use("4", "Read", path="b"),
        result("4", False),
        use("5", "Edit", path="a"),
        result("5", False),
    ]


def test_counts_five_calls_two_errors_one_retry_per_tool():
    m = tool_metrics(fixture())
    assert m["tools"] == {
        "Bash": {"calls": 2, "errors": 1, "retries": 1},
        "Read": {"calls": 2, "errors": 1, "retries": 0},
        "Edit": {"calls": 1, "errors": 0, "retries": 0},
    }
    assert m["totals"] == {"calls": 5, "errors": 2, "retries": 1}


def test_repeat_without_prior_error_is_not_a_retry():
    events = [use("1", "Bash", cmd="x"), result("1"), use("2", "Bash", cmd="x"), result("2")]
    assert tool_metrics(events)["totals"]["retries"] == 0


def test_same_tool_different_input_is_not_a_retry():
    events = [use("1", "Bash", cmd="x"), result("1", True), use("2", "Bash", cmd="y"), result("2")]
    assert tool_metrics(events)["totals"]["retries"] == 0


def test_output_holds_no_input_or_result_text():
    out = json.dumps(tool_metrics(fixture()))
    assert "SECRET" not in out and "make" not in out


def test_unmatched_result_and_malformed_events_are_ignored():
    events = [result("zzz", True), {"type": "user"}, {"message": {"content": "text"}}, use("1", "Bash")]
    m = tool_metrics(events)
    assert m["totals"] == {"calls": 1, "errors": 0, "retries": 0}
