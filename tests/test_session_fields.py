import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from session_fields import session_fields
from session_metrics import read_events


def base(type_, ts, **extra):
    return {"type": type_, "timestamp": ts, "sessionId": "s-1", "cwd": "/w", "gitBranch": "feat/x", **extra}


def tool_use(name, **inp):
    return {"message": {"role": "assistant", "content": [{"type": "tool_use", "name": name, "input": inp}]}}


EVENTS = [
    {"type": "mode", "mode": "normal"},
    base("user", "2026-09-22T06:00:00.000Z", message={"role": "user", "content": "do it"}),
    base("assistant", "2026-09-22T06:00:05.000Z", **tool_use("Skill", skill="se-workflow:init")),
    base("user", "2026-09-22T06:00:06.000Z", message={"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}),
    base("user", "2026-09-22T06:00:07.000Z", isMeta=True, message={"role": "user", "content": "caveat"}),
    base("assistant", "2026-09-22T06:00:10.000Z", **tool_use("Skill", skill="se-workflow:init")),
    base("user", "2026-09-22T06:01:00.000Z", message={"role": "user", "content": [{"type": "text", "text": "again"}]}),
    base("assistant", "2026-09-22T06:01:30.000Z", **tool_use("Skill", skill="simplify"), attributionSkill="simplify"),
    base("assistant", "2026-09-22T06:01:31.000Z", **tool_use("Bash", command="ls")),
    {"type": "cost-state", "sessionId": "s-1", "totalCostUSD": 0.25},
    {"type": "cost-state", "sessionId": "s-1", "totalCostUSD": 0.75},
]

EXPECTED = {
    "session_id": "s-1",
    "cwd": "/w",
    "branch": "feat/x",
    "start": "2026-09-22T06:00:00.000Z",
    "end": "2026-09-22T06:01:31.000Z",
    "duration_seconds": 91.0,
    "turns": 2,
    "cost_usd": 0.75,
    "skills": {"se-workflow:init": 2, "simplify": 1},
}


def test_fixture_yields_identity_time_turns_cost_and_skills():
    assert session_fields(EVENTS) == EXPECTED


def test_fields_survive_jsonl_round_trip(tmp_path):
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in EVENTS) + "\n")
    assert session_fields(read_events(path)) == EXPECTED


def test_empty_stream_gives_null_fields_and_zero_counts():
    out = session_fields([])
    assert out["session_id"] is None
    assert out["duration_seconds"] is None
    assert out["cost_usd"] is None
    assert out["turns"] == 0
    assert out["skills"] == {}


def test_output_holds_no_message_text():
    assert "do it" not in json.dumps(session_fields(EVENTS))


def test_transcript_without_cost_state_reports_null_cost():
    events = [
        base("user", "2026-09-22T06:00:00.000Z", message={"role": "user", "content": "hi"}),
        base("assistant", "2026-09-22T06:00:01.000Z", **tool_use("Bash", command="ls")),
    ]
    assert session_fields(events)["cost_usd"] is None


def test_cost_state_with_non_numeric_total_keeps_earlier_numeric_cost():
    events = [
        {"type": "cost-state", "totalCostUSD": 0.5},
        {"type": "cost-state", "totalCostUSD": None},
    ]
    assert session_fields(events)["cost_usd"] == 0.5
